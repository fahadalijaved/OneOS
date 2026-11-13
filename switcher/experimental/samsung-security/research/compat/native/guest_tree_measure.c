#define _GNU_SOURCE
#include "guest_tree_measure.h"
#include "guest_tree_sha256.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/xattr.h>
#include <unistd.h>

#define DIRECTORY (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define STAT_MASK (STATX_TYPE | STATX_MODE | STATX_NLINK | STATX_UID | STATX_GID | STATX_INO | \
                   STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID)
#define STREAM_BYTES (256U * 1024U)

struct measurement {
    const struct gtm_manifest *manifest;
    struct statx root;
    unsigned char *seen, *buffer;
    int *close_error;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static void closed(int result, int *primary, int *uncertain) {
    if (result == 0) return;
    int error = errno ? errno : EIO;
    if (!*uncertain) *uncertain = error;
    if (!*primary) *primary = error;
}

static int stat_object(int base, const char *name, struct statx *result) {
    int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(base, name, flags, STAT_MASK, result) < 0) return -1;
    if ((result->stx_mask & STAT_MASK) != STAT_MASK || !result->stx_ino || !result->stx_mnt_id)
        return refuse(EPROTO);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major &&
           a->stx_dev_minor == b->stx_dev_minor;
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
           a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_size == b->stx_size &&
           a->stx_nlink == b->stx_nlink && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec &&
           a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec &&
           a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int recheck_object(int base, const char *name, const struct statx *expected) {
    struct statx now;
    if (stat_object(base, name, &now) < 0) return -1;
    return same_object(&now, expected) ? 0 : refuse(ESTALE);
}

static int matches_row(const struct measurement *state, const struct gtm_row *row,
                       const struct statx *actual) {
    static const unsigned types[] = {0, S_IFDIR, S_IFREG, S_IFLNK};
    return same_mount(&state->root, actual) && (actual->stx_mode & S_IFMT) == types[row->kind] &&
           (actual->stx_mode & 07777) == row->mode && actual->stx_uid == row->uid &&
           actual->stx_gid == row->gid && actual->stx_nlink == row->nlink &&
           (row->kind == GTM_DIRECTORY || actual->stx_size == row->size);
}

/* One exact attribute set. The optional path is used only for a symlink
 * checked against its held parent and the authenticated proc descriptor view. */
static int attributes(int fd, const char *path, const struct gtm_row *row) {
    char names[GTM_XATTR_MAX * (GTM_ATTR_NAME_MAX + 1U)];
    unsigned char value[GTM_ATTR_VALUE_MAX];
    struct gtm_attribute expected[GTM_XATTR_MAX];
    unsigned seen = 0;
    gtm_read_attributes(row, expected);
    ssize_t count = path ? llistxattr(path, names, sizeof(names)) : flistxattr(fd, names, sizeof(names));
    if (count < 0) return -1;
    if ((size_t)count > sizeof(names)) return refuse(EPROTO);
    for (size_t pos = 0; pos < (size_t)count;) {
        const char *name = names + pos;
        const char *end = memchr(name, 0, (size_t)count - pos);
        if (!end || end == name) return refuse(EPROTO);
        size_t length = (size_t)(end - name), index = 0;
        for (; index < row->attr_count; ++index) {
            if (length == expected[index].name_length && !memcmp(name, expected[index].name, length)) break;
        }
        if (index == row->attr_count || (seen & (1U << index))) return refuse(ESTALE);
        seen |= 1U << index;
        ssize_t got = path ? lgetxattr(path, name, value, sizeof(value)) : fgetxattr(fd, name, value, sizeof(value));
        if (got < 0) return -1;
        if (got != expected[index].value_length || memcmp(value, expected[index].value, (size_t)got))
            return refuse(ESTALE);
        pos += length + 1;
    }
    return seen == (1U << row->attr_count) - 1U ? 0 : refuse(ESTALE);
}

static int regular_file(struct measurement *state, int fd, const struct gtm_row *row) {
    struct guest_tree_sha256 hash;
    unsigned char digest[32];
    guest_tree_sha256_init(&hash);
    uint64_t remaining = row->size;
    while (remaining) {
        size_t request = remaining < STREAM_BYTES ? (size_t)remaining : STREAM_BYTES;
        ssize_t got = read(fd, state->buffer, request);
        if (got < 0) return -1;
        if (!got || (size_t)got > request) return refuse(ESTALE);
        guest_tree_sha256_update(&hash, state->buffer, (size_t)got);
        remaining -= (size_t)got;
    }
    ssize_t extra = read(fd, state->buffer, 1);
    if (extra < 0) return -1;
    if (extra) return refuse(ESTALE);
    guest_tree_sha256_final(&hash, digest);
    return memcmp(digest, row->payload, sizeof(digest)) ? refuse(ESTALE) : 0;
}

static int proc_descriptor_view(int *close_error) {
    int fd = open("/proc/self/fd", DIRECTORY);
    if (fd < 0) return -1;
    struct statx root, member;
    struct statfs filesystem;
    int primary = 0;
    if (fstatfs(fd, &filesystem) < 0 || stat_object(AT_FDCWD, "/proc", &root) < 0 ||
        stat_object(fd, "", &member) < 0) primary = errno;
    else if ((unsigned long)filesystem.f_type != PROC_SUPER_MAGIC || !same_mount(&root, &member)) primary = EXDEV;
    closed(close(fd), &primary, close_error);
    return primary ? refuse(primary) : 0;
}

static int symbolic_link(int parent, const char *name, const struct gtm_row *row, const struct statx *before) {
    char value[GTM_PATH_MAX + 1], path[GTM_PATH_MAX + 64];
    ssize_t got = readlinkat(parent, name, value, sizeof(value));
    if (got < 0) return -1;
    if (got != row->link_length || memcmp(value, row->payload, (size_t)got)) return refuse(ESTALE);
    int length = snprintf(path, sizeof(path), "/proc/self/fd/%d/%s", parent, name);
    if (length < 0 || (size_t)length >= sizeof(path)) return refuse(EOVERFLOW);
    if (recheck_object(AT_FDCWD, path, before) < 0 || attributes(-1, path, row) < 0 ||
        recheck_object(AT_FDCWD, path, before) < 0) return -1;
    return recheck_object(parent, name, before);
}

static int verify_directory(struct measurement *state, int fd, const struct gtm_row *row);

static int verify_child(struct measurement *state, int parent, const char *name, const struct gtm_row *row) {
    size_t index = (size_t)(row - state->manifest->rows);
    struct statx before;
    if (state->seen[index]) return refuse(ESTALE);
    state->seen[index] = 1;
    if (stat_object(parent, name, &before) < 0) return -1;
    if (!matches_row(state, row, &before)) return refuse(ESTALE);
    if (row->kind == GTM_SYMLINK) return symbolic_link(parent, name, row, &before);

    int flags = row->kind == GTM_DIRECTORY ? DIRECTORY : O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC;
    int fd = openat(parent, name, flags);
    if (fd < 0) return -1;
    int error = 0;
    if (recheck_object(fd, "", &before) < 0 || attributes(fd, NULL, row) < 0 ||
        (row->kind == GTM_DIRECTORY ? verify_directory(state, fd, row) : regular_file(state, fd, row)) < 0 ||
        recheck_object(fd, "", &before) < 0 || recheck_object(parent, name, &before) < 0) error = errno ? errno : EIO;
    closed(close(fd), &error, state->close_error);
    return error ? refuse(error) : 0;
}

static int verify_directory(struct measurement *state, int fd, const struct gtm_row *row) {
    int error = 0;
    size_t count = 0;
    char path[GTM_PATH_MAX + 1];
    size_t prefix = row->path_length;
    memcpy(path, row->path, prefix);
    if (prefix) path[prefix++] = '/';
    struct statx held;
    int readable = openat(fd, ".", DIRECTORY);
    if (readable < 0) return -1;
    DIR *entries = NULL;
    if (stat_object(fd, "", &held) < 0 || recheck_object(readable, "", &held) < 0 ||
        !(entries = fdopendir(readable))) { error = errno ? errno : EIO; goto done; }
    readable = -1;
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(entries);
        if (!entry) { error = errno; break; }
        const char *name = entry->d_name;
        if (!strcmp(name, ".") || !strcmp(name, "..")) continue;
        size_t length = strlen(name);
        if (!length || prefix + length > GTM_PATH_MAX || ++count > row->children) { error = ESTALE; break; }
        memcpy(path + prefix, name, length);
        const struct gtm_row *child = gtm_find(state->manifest, path, prefix + length);
        if (!child) { error = ESTALE; break; }
        if (verify_child(state, fd, name, child) < 0) { error = errno ? errno : EIO; break; }
    }
    if (!error && count != row->children) error = ESTALE;
done:
    if (entries) closed(closedir(entries), &error, state->close_error);
    if (readable >= 0) closed(close(readable), &error, state->close_error);
    return error ? refuse(error) : 0;
}

int guest_tree_measure(int root_fd, const struct gtm_manifest *manifest, int *close_error) {
    if (root_fd < 0 || !manifest || !manifest->rows || !manifest->count || !close_error) return refuse(EINVAL);
    if (*close_error) return refuse(*close_error);
    struct measurement state = {.manifest = manifest, .close_error = close_error};
    if (stat_object(root_fd, "", &state.root) < 0 || proc_descriptor_view(close_error) < 0) return -1;
    if (!matches_row(&state, manifest->rows, &state.root)) return refuse(ESTALE);
    state.seen = calloc(manifest->count, 1);
    state.buffer = malloc(STREAM_BYTES);
    int error = 0;
    if (!state.seen || !state.buffer) { error = ENOMEM; goto done; }
    state.seen[0] = 1;
    int fd = openat(root_fd, ".", DIRECTORY);
    if (fd < 0) { error = errno; goto done; }
    if (recheck_object(fd, "", &state.root) < 0 || attributes(fd, NULL, manifest->rows) < 0 ||
        verify_directory(&state, fd, manifest->rows) < 0 || recheck_object(fd, "", &state.root) < 0 ||
        proc_descriptor_view(close_error) < 0) error = errno ? errno : EIO;
    closed(close(fd), &error, close_error);
    for (size_t i = 0; !error && i < manifest->count; ++i)
        if (!state.seen[i]) error = ESTALE;
done:
    free(state.buffer);
    free(state.seen);
    return error ? refuse(error) : 0;
}
