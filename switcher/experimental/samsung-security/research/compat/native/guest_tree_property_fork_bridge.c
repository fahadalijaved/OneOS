#define _GNU_SOURCE
#include "guest_tree_property_fork_bridge.h"
#include "guest_tree_child_view.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define BLOB(role) \
    extern const unsigned char oneos_property_seed_##role[], oneos_property_seed_##role##_end[]
BLOB(info);
BLOB(build);
BLOB(default);
BLOB(vndk);
BLOB(serial);
#undef BLOB

struct seed_file {
    const char *name;
    const unsigned char *first, *end;
};
#define FILE_BYTES(name, role) {name, oneos_property_seed_##role, oneos_property_seed_##role##_end}
static const struct seed_file files[] = {
    FILE_BYTES("property_info", info),
    FILE_BYTES("u:object_r:build_prop:s0", build),
    FILE_BYTES("u:object_r:default_prop:s0", default),
    FILE_BYTES("u:object_r:vndk_prop:s0", vndk),
    FILE_BYTES("properties_serial", serial),
};
#undef FILE_BYTES
_Static_assert(sizeof(files) / sizeof(files[0]) == GTP_SEED_COUNT, "all seed roles");

#define NOFOLLOW (AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
#define READONLY (O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
#define META (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO \
              | STATX_MNT_ID | STATX_SIZE | STATX_NLINK | STATX_MTIME | STATX_CTIME)

static int refuse(int error) {
    errno = error;
    return -1;
}

int gtpb_prepare_child(const struct gtc_child_inputs *input, struct gtc_child_view *view,
        struct guest_tree_property_seed_source *source, struct guest_tree_property_child **property) {
    if (!input || !view || !source || !property || *property) return refuse(EINVAL);
    int seeds[GTP_SEED_COUNT] = {-1, -1, -1, -1, -1};
    if (guest_tree_property_seed_source_take_in_child(source, seeds) < 0
            || guest_tree_property_seed_source_close(source) < 0) return -1;
    /* A refusal from this function is terminal for the actual fork child.
     * Keep any unconsumed local cells until its process-exit cleanup. */
    if (guest_tree_prepare_child_view(input, view, NULL) != 0
            || guest_tree_property_child_begin(input, view, seeds, property) != 0) return -1;
    int fd = -1;
    return guest_tree_property_child_borrow(*property, &fd);
}

static int stat_object(int fd, const char *name, struct statx *value) {
    if (statx(fd, name, NOFOLLOW | (*name ? 0 : AT_EMPTY_PATH), META, value) < 0) return -1;
    return (value->stx_mask & META) == META && value->stx_mnt_id && value->stx_ino ? 0 : refuse(ESTALE);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int unchanged(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink
        && a->stx_size == b->stx_size && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec
        && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec
        && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static void closed(int result, int *error, int *close_error) {
    if (result == 0) return;
    int failure = errno ? errno : EIO;
    if (!*close_error) *close_error = failure;
    if (!*error) *error = failure;
}

static int bytes_equal(int fd, const unsigned char *data, size_t size) {
    unsigned char buffer[4096];
    size_t offset = 0;
    while (offset < size) {
        size_t available = size - offset;
        if (available > sizeof(buffer)) available = sizeof(buffer);
        ssize_t got = pread(fd, buffer, available, (off_t)offset);
        if (got < 0) return -1;
        if (!got || (size_t)got > available || memcmp(buffer, data + offset, (size_t)got))
            return refuse(EBADMSG);
        offset += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)size);
    if (tail < 0) return -1;
    return tail == 0 ? 0 : refuse(EBADMSG);
}

static int verify_file(int property, const struct statx *directory,
        const struct seed_file *profile, int *close_error) {
    struct statx named, opened, after;
    uintptr_t first = (uintptr_t)profile->first, end = (uintptr_t)profile->end;
    if (end <= first || end - first > 262144U) return refuse(EPROTO);
    size_t size = end - first;
    if (stat_object(property, profile->name, &named) < 0) return -1;
    if (named.stx_mode != (S_IFREG | 0444) || named.stx_uid || named.stx_gid || named.stx_nlink != 1
            || named.stx_size != size || !same_mount(directory, &named)) return refuse(ESTALE);
    int fd = openat(property, profile->name, READONLY);
    if (fd < 0) return -1;
    int error = 0;
    if (stat_object(fd, "", &opened) < 0) error = errno;
    else if (!unchanged(&named, &opened)) error = ESTALE;
    else if (bytes_equal(fd, profile->first, size) < 0 || stat_object(fd, "", &after) < 0) error = errno;
    else if (!unchanged(&opened, &after)) error = ESTALE;
    else if (stat_object(property, profile->name, &after) < 0) error = errno;
    else if (!unchanged(&named, &after)) error = ESTALE;
    closed(close(fd), &error, close_error);
    return error ? refuse(error) : 0;
}

int gtpb_verify_property_files(int property, int *close_error) {
    if (!close_error || *close_error) return refuse(EINVAL);
    struct statx held, opened;
    if (stat_object(property, "", &held) < 0) return -1;
    if (held.stx_mode != (S_IFDIR | 0500) || held.stx_uid || held.stx_gid || held.stx_nlink != 2)
        return refuse(ESTALE);
    int fd = openat(property, ".", READONLY | O_DIRECTORY);
    if (fd < 0) return -1;
    int error = 0;
    DIR *entries = NULL;
    if (stat_object(fd, "", &opened) < 0) error = errno;
    else if (!unchanged(&held, &opened)) error = ESTALE;
    else if (!(entries = fdopendir(fd))) error = errno;
    unsigned seen = 0;
    if (entries) {
        for (;;) {
            errno = 0;
            const struct dirent *entry = readdir(entries);
            if (!entry) { error = errno; break; }
            unsigned bit = 0;
            if (!strcmp(entry->d_name, ".")) bit = 1U;
            else if (!strcmp(entry->d_name, "..")) bit = 2U;
            else for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
                if (!strcmp(entry->d_name, files[i].name)) { bit = 1U << (i + 2); break; }
            if (!bit || (seen & bit)) { error = ESTALE; break; }
            seen |= bit;
        }
        closed(closedir(entries), &error, close_error);
    } else closed(close(fd), &error, close_error);
    if (error) return refuse(error);
    if (seen != ((1U << (GTP_SEED_COUNT + 2)) - 1U)) return refuse(ESTALE);
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
        if (verify_file(property, &held, &files[i], close_error) < 0) return -1;
    if (stat_object(property, "", &opened) < 0) return -1;
    return unchanged(&held, &opened) ? 0 : refuse(ESTALE);
}
