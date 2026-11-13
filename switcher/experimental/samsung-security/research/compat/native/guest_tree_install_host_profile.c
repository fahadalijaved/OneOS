#define _GNU_SOURCE
#include "guest_tree_install_host_profile.h"

#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define PROFILE "oneos_retained_root_link_v2"
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READ_FILE (O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC | O_NOATIME)

enum { PROFILE_BYTES = 288 };
static const unsigned char profile_sha256[32] = {
    0x74, 0xe8, 0x62, 0x3b, 0xe2, 0x0f, 0xfb, 0xa5,
    0x10, 0x6c, 0x4e, 0x3e, 0x75, 0x6f, 0x1f, 0x49,
    0x58, 0xc3, 0x9c, 0xd3, 0x65, 0x8c, 0x6b, 0x03,
    0x46, 0xda, 0x74, 0x76, 0x6d, 0xf9, 0x7b, 0x36
};

static atomic_flag claimed = ATOMIC_FLAG_INIT;

struct attempt {
    int root, data, system, temporary, named;
    struct statx root_id, data_id, system_id;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int sample(int fd, const char *name, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO
        | STATX_MNT_ID | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME;
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_ino || !value->stx_mnt_id)
        return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int same_time(const struct statx_timestamp *a, const struct statx_timestamp *b) {
    return a->tv_sec == b->tv_sec && a->tv_nsec == b->tv_nsec;
}

static int same_data(const struct statx *a, const struct statx *b) {
    return same_node(a, b) && a->stx_size == b->stx_size
        && same_time(&a->stx_mtime, &b->stx_mtime);
}

static int same_file(const struct statx *a, const struct statx *b) {
    return same_data(a, b) && a->stx_nlink == b->stx_nlink
        && same_time(&a->stx_ctime, &b->stx_ctime);
}

static int name_current(int fd, const char *name, const struct statx *expected) {
    struct statx actual;
    if (sample(fd, name, &actual) < 0) return -1;
    return same_node(expected, &actual) ? 0 : refuse(ESTALE);
}

static int current_dirs(const struct attempt *a) {
    return name_current(a->root, "", &a->root_id) < 0
        || name_current(AT_FDCWD, "/", &a->root_id) < 0
        || name_current(a->data, "", &a->data_id) < 0
        || name_current(a->root, "data", &a->data_id) < 0
        || name_current(AT_FDCWD, "/data", &a->data_id) < 0
        || name_current(a->system, "", &a->system_id) < 0
        || name_current(a->data, "system", &a->system_id) < 0
        || name_current(AT_FDCWD, "/data/system", &a->system_id) < 0 ? -1 : 0;
}

static int f2fs(int fd) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == F2FS_SUPER_MAGIC ? 0 : refuse(EXDEV);
}

static int open_dirs(struct attempt *a) {
    a->root = open("/", DIRECTORY);
    if (a->root < 0 || sample(a->root, "", &a->root_id) < 0) return -1;
    if (!S_ISDIR(a->root_id.stx_mode) || a->root_id.stx_uid || a->root_id.stx_gid
        || (a->root_id.stx_mode & 0022)) return refuse(EXDEV);
    a->data = openat(a->root, "data", DIRECTORY);
    if (a->data < 0 || sample(a->data, "", &a->data_id) < 0 || f2fs(a->data) < 0) return -1;
    if (a->data_id.stx_mode != (S_IFDIR | 0771) || a->data_id.stx_uid != 1000
        || a->data_id.stx_gid != 1000 || same_mount(&a->root_id, &a->data_id))
        return refuse(EXDEV);
    a->system = openat(a->data, "system",
                       O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC | O_NOATIME);
    if (a->system < 0 || sample(a->system, "", &a->system_id) < 0 || f2fs(a->system) < 0)
        return -1;
    if (a->system_id.stx_mode != (S_IFDIR | 0775) || a->system_id.stx_uid != 1000
        || a->system_id.stx_gid != 1000 || !same_mount(&a->data_id, &a->system_id)
        || a->data_id.stx_ino == a->system_id.stx_ino) return refuse(EXDEV);
    return current_dirs(a);
}

static int protected_file(const struct attempt *a, const struct statx *file, unsigned links) {
    return same_mount(&a->system_id, file) && file->stx_mode == (S_IFREG | 0440)
        && file->stx_uid == 0 && file->stx_gid == 1000 && file->stx_size == PROFILE_BYTES
        && file->stx_nlink == links ? 0 : refuse(ESTALE);
}

static int verify_bytes(int fd, const unsigned char *expected) {
    unsigned char actual[PROFILE_BYTES + 1];
    size_t length = 0;
    while (length < sizeof(actual)) {
        ssize_t n = pread(fd, actual + length, sizeof(actual) - length, (off_t)length);
        if (n < 0) return -1;
        if (!n) break;
        length += (size_t)n;
    }
    return length == PROFILE_BYTES && !memcmp(actual, expected, PROFILE_BYTES)
        ? 0 : refuse(EBADMSG);
}

static int stable_named(const struct attempt *a, const struct statx *expected) {
    struct statx named, held, absolute;
    if (sample(a->system, PROFILE, &named) < 0 || sample(a->named, "", &held) < 0
        || sample(AT_FDCWD, "/data/system/" PROFILE, &absolute) < 0) return -1;
    if (!same_file(expected, &named) || !same_file(expected, &held)
        || !same_file(expected, &absolute)) return refuse(ESTALE);
    return current_dirs(a);
}

static int open_named(struct attempt *a, const struct statx *expected,
                      const unsigned char *bytes) {
    if (protected_file(a, expected, 1) < 0) return -1;
    a->named = openat(a->system, PROFILE, READ_FILE);
    if (a->named < 0 || stable_named(a, expected) < 0 || verify_bytes(a->named, bytes) < 0)
        return -1;
    return stable_named(a, expected);
}

static int writable(const struct attempt *a) {
    struct statvfs fs;
    if (fstatvfs(a->system, &fs) < 0) return -1;
    return fs.f_flag & ST_RDONLY ? refuse(EROFS) : 0;
}

static int absent(const struct attempt *a) {
    struct statx file;
    if (sample(a->system, PROFILE, &file) == 0) return refuse(EEXIST);
    if (errno != ENOENT) return -1;
    if (sample(AT_FDCWD, "/data/system/" PROFILE, &file) == 0) return refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int write_bytes(int fd, const unsigned char *bytes) {
    size_t done = 0;
    while (done < PROFILE_BYTES) {
        ssize_t n = write(fd, bytes + done, PROFILE_BYTES - done);
        if (n < 0) return -1;
        if (!n) return refuse(EIO);
        done += (size_t)n;
    }
    return 0;
}

static int prepare_temporary(struct attempt *a, const unsigned char *bytes,
                             struct statx *ready) {
    struct statx created, after;
    a->temporary = openat(a->system, ".", O_TMPFILE | O_RDWR | O_CLOEXEC, 0600);
    if (a->temporary < 0 || sample(a->temporary, "", &created) < 0) return -1;
    if (!same_mount(&a->system_id, &created) || created.stx_mode != (S_IFREG | 0600)
        || created.stx_uid || created.stx_gid || created.stx_nlink || created.stx_size)
        return refuse(ESTALE);
    if (write_bytes(a->temporary, bytes) < 0 || fchown(a->temporary, 0, 1000) < 0
        || fchmod(a->temporary, 0440) < 0 || sample(a->temporary, "", ready) < 0
        || protected_file(a, ready, 0) < 0 || verify_bytes(a->temporary, bytes) < 0
        || fsync(a->temporary) < 0 || sample(a->temporary, "", &after) < 0) return -1;
    return same_file(ready, &after) ? 0 : refuse(ESTALE);
}

static int publish(struct attempt *a, const unsigned char *bytes) {
    struct statx ready, before_link, linked, after;
    if (prepare_temporary(a, bytes, &ready) < 0 || current_dirs(a) < 0 || absent(a) < 0
        || sample(a->temporary, "", &before_link) < 0) return -1;
    if (!same_file(&ready, &before_link)) return refuse(ESTALE);

    /* Link the exact synced anonymous inode. A name that appears concurrently
     * at the destination cannot be replaced by this syscall. */
    if (linkat(a->temporary, "", a->system, PROFILE, AT_EMPTY_PATH) < 0
        || sample(a->temporary, "", &linked) < 0 || protected_file(a, &linked, 1) < 0)
        return -1;
    /* The link changes nlink and can change ctime. Content and identity remain. */
    if (!same_data(&ready, &linked)) return refuse(ESTALE);
    if (open_named(a, &linked, bytes) < 0 || fsync(a->system) < 0
        || sample(a->temporary, "", &after) < 0) return -1;
    if (!same_file(&linked, &after)) return refuse(ESTALE);
    return stable_named(a, &linked);
}

static void close_once(int *cell, int *error) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !*error) *error = errno ? errno : EIO;
}

enum guest_tree_install_host_profile_result
guest_tree_install_host_profile(const void *bytes, size_t length) {
    if (getpid() != gettid() || getuid() || geteuid() || getegid()) {
        errno = EPERM;
        return GTHP_NO_EFFECT_LOCAL_CLOSED;
    }
    if (atomic_flag_test_and_set_explicit(&claimed, memory_order_acq_rel)) {
        errno = EALREADY;
        return GTHP_HOLD;
    }
    if (!bytes || length != PROFILE_BYTES) {
        errno = EINVAL;
        return GTHP_NO_EFFECT_LOCAL_CLOSED;
    }
    unsigned char selected[PROFILE_BYTES], digest[32];
    memcpy(selected, bytes, sizeof(selected));
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, selected, sizeof(selected));
    guest_tree_sha256_final(&hash, digest);
    if (memcmp(digest, profile_sha256, sizeof(digest))) {
        errno = EBADMSG;
        return GTHP_NO_EFFECT_LOCAL_CLOSED;
    }

    struct attempt a = {.root = -1, .data = -1, .system = -1, .temporary = -1, .named = -1};
    enum guest_tree_install_host_profile_result result = GTHP_NO_EFFECT_LOCAL_CLOSED;
    struct statx existing;
    if (open_dirs(&a) < 0) goto done;
    if (sample(a.system, PROFILE, &existing) == 0) {
        if (open_named(&a, &existing, selected) == 0) result = GTHP_ALREADY_MATCHES_LOCAL_CLOSED;
        goto done;
    }
    if (errno != ENOENT || writable(&a) < 0 || current_dirs(&a) < 0 || absent(&a) < 0)
        goto done;

    result = GTHP_HOLD;
    if (publish(&a, selected) == 0) result = GTHP_PUBLISHED_LOCAL_CLOSED;

done:;
    int failure = result == GTHP_NO_EFFECT_LOCAL_CLOSED || result == GTHP_HOLD
        ? (errno ? errno : EIO) : 0;
    int close_error = 0;
    close_once(&a.named, &close_error);
    close_once(&a.temporary, &close_error);
    close_once(&a.system, &close_error);
    close_once(&a.data, &close_error);
    close_once(&a.root, &close_error);
    errno = failure ? failure : close_error;
    return close_error ? GTHP_HOLD : result;
}
