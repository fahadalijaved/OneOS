#define _GNU_SOURCE
#include "guest_tree_install_controller.h"

#include "guest_tree_install_guard.h"
#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

#define CONTROLLER_SIZE 746760U
#define FINAL "oneos_retained_tree_preparation"
#define CANDIDATE "." FINAL ".new"
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define READ_FILE (O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | O_NOATIME)

static const unsigned char controller_sha256[32] = {
    0x80, 0x36, 0x91, 0xc5, 0x5a, 0xc8, 0x76, 0xa4,
    0x2d, 0x57, 0x48, 0x8a, 0x1c, 0x10, 0xd7, 0x63,
    0x28, 0xaa, 0x33, 0xc3, 0xa4, 0xff, 0x6c, 0xf3,
    0x60, 0x6d, 0x16, 0xf8, 0xd2, 0x01, 0xd1, 0x25,
};

static atomic_flag attempted = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int sample(int fd, const char *name, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO
        | STATX_MNT_ID | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME;
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), mask, value) < 0) return -1;
    return (value->stx_mask & mask) == mask && value->stx_mnt_id && value->stx_ino
        ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino
        && a->stx_mode == b->stx_mode && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int same_time(const struct statx_timestamp *a, const struct statx_timestamp *b) {
    return a->tv_sec == b->tv_sec && a->tv_nsec == b->tv_nsec;
}

static int exact(const struct statx *a, const struct statx *b) {
    return same_inode(a, b) && a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
        && same_time(&a->stx_mtime, &b->stx_mtime) && same_time(&a->stx_ctime, &b->stx_ctime);
}

static int file_profile(const struct statx *file, const struct statx *bin, size_t size) {
    return S_ISREG(file->stx_mode) && (file->stx_mode & 07777) == 0500
        && !file->stx_uid && !file->stx_gid && file->stx_nlink == 1 && file->stx_size == size
        && same_mount(bin, file) ? 0 : refuse(ESTALE);
}

static int absent(int fd, const char *name) {
    struct statx ignored;
    if (statx(fd, name, LOOKUP, STATX_TYPE, &ignored) == 0) return refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int current_bin(int stage_fd, int bin_fd, const struct statx *identity) {
    struct statx held, named;
    if (sample(bin_fd, "", &held) < 0 || sample(stage_fd, "bin", &named) < 0) return -1;
    return same_inode(identity, &held) && exact(&held, &named) ? 0 : refuse(ESTALE);
}

static int private_directory(const struct statx *directory) {
    return S_ISDIR(directory->stx_mode) && (directory->stx_mode & 07777) == 0700
        && !directory->stx_uid && !directory->stx_gid;
}

static int open_bin(int stage_fd, const struct statx *stage, int flags, int *bin_fd, struct statx *bin) {
    *bin_fd = openat(stage_fd, "bin", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC | flags);
    if (*bin_fd < 0 || sample(*bin_fd, "", bin) < 0) return -1;
    if (!private_directory(bin) || !same_mount(stage, bin) || stage->stx_ino == bin->stx_ino)
        return refuse(EXDEV);
    return current_bin(stage_fd, *bin_fd, bin);
}

static int current_file(int bin, const char *name, int fd, const struct statx *identity) {
    struct statx held, named;
    if (sample(fd, "", &held) < 0 || sample(bin, name, &named) < 0) return -1;
    return exact(identity, &held) && exact(&held, &named) ? 0 : refuse(ESTALE);
}

static int pinned_hash(struct guest_tree_sha256 *hash) {
    unsigned char digest[32];
    guest_tree_sha256_final(hash, digest);
    return memcmp(digest, controller_sha256, sizeof(digest)) == 0 ? 0 : refuse(EBADMSG);
}

static int write_bytes(int fd, const unsigned char *bytes) {
    for (size_t offset = 0; offset < CONTROLLER_SIZE;) {
        ssize_t n = write(fd, bytes + offset, CONTROLLER_SIZE - offset);
        if (n < 0) return -1;
        if (n == 0) return refuse(EIO);
        offset += (size_t)n;
    }
    return 0;
}

static int read_bytes(int fd) {
    struct guest_tree_sha256 hash;
    unsigned char buffer[8192];
    guest_tree_sha256_init(&hash);
    for (size_t offset = 0; offset < CONTROLLER_SIZE;) {
        size_t remaining = CONTROLLER_SIZE - offset;
        ssize_t n = pread(fd, buffer, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)offset);
        if (n < 0) return -1;
        if (n == 0) return refuse(EBADMSG);
        guest_tree_sha256_update(&hash, buffer, (size_t)n);
        offset += (size_t)n;
    }
    ssize_t tail = pread(fd, buffer, 1, CONTROLLER_SIZE);
    if (tail < 0) return -1;
    if (tail != 0) return refuse(EBADMSG);
    return pinned_hash(&hash);
}

static int close_owned(int *cell) {
    int fd = *cell;
    *cell = -1;
    return fd < 0 ? 0 : close(fd);
}

enum guest_tree_install_controller_result guest_tree_install_controller(
        struct guest_tree_install_guard *guard, int stage_fd, int controller_namespace_fd,
        const void *bytes, size_t length) {
    if (!guard || stage_fd < 0 || controller_namespace_fd < 0 || !bytes || length != CONTROLLER_SIZE) {
        errno = EINVAL;
        return GTIC_NO_EFFECT_LOCAL_CLOSED;
    }
    if (guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0)
        return GTIC_HOLD;
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_acq_rel)) {
        (void)guest_tree_install_guard_hold(guard, EALREADY);
        errno = EALREADY;
        return GTIC_HOLD;
    }

    int bin_fd = -1, writer = -1, reader = -1;
    int create_attempted = 0, published = 0, error = 0, close_error = 0;
    struct statx stage, bin, birth, candidate, final;
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, bytes, length);
    if (pinned_hash(&hash) < 0 || sample(stage_fd, "", &stage) < 0) goto failed;

    if (open_bin(stage_fd, &stage, 0, &bin_fd, &bin) < 0
            || absent(bin_fd, FINAL) < 0 || absent(bin_fd, CANDIDATE) < 0
            || guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0)
        goto failed;

    create_attempted = 1;
    writer = openat(bin_fd, CANDIDATE, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0500);
    if (writer < 0 || sample(writer, "", &birth) < 0 || file_profile(&birth, &bin, 0) < 0
            || current_file(bin_fd, CANDIDATE, writer, &birth) < 0 || write_bytes(writer, bytes) < 0
            || fsync(writer) < 0 || sample(writer, "", &candidate) < 0
            || file_profile(&candidate, &bin, CONTROLLER_SIZE) < 0) goto failed;
    if (!same_inode(&birth, &candidate)) {
        errno = ESTALE;
        goto failed;
    }
    if (current_file(bin_fd, CANDIDATE, writer, &candidate) < 0) goto failed;
    reader = openat(bin_fd, CANDIDATE, READ_FILE);
    if (reader < 0 || current_file(bin_fd, CANDIDATE, reader, &candidate) < 0
            || close_owned(&writer) < 0 || read_bytes(reader) < 0
            || current_file(bin_fd, CANDIDATE, reader, &candidate) < 0
            || current_bin(stage_fd, bin_fd, &bin) < 0 || absent(bin_fd, FINAL) < 0
            || guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0) goto failed;

    long renamed = syscall(SYS_renameat2, bin_fd, CANDIDATE, bin_fd, FINAL, RENAME_NOREPLACE);
    if (renamed != 0) {
        if (renamed > 0) errno = EPROTO;
        goto failed;
    }
    if (sample(reader, "", &final) < 0 || file_profile(&final, &bin, CONTROLLER_SIZE) < 0) goto failed;
    /* The move may update ctime. The original inode, size and mtime must survive. */
    if (!same_inode(&candidate, &final) || !same_time(&candidate.stx_mtime, &final.stx_mtime)) {
        errno = ESTALE;
        goto failed;
    }
    if (current_file(bin_fd, FINAL, reader, &final) < 0 || read_bytes(reader) < 0
            || absent(bin_fd, CANDIDATE) < 0 || fsync(bin_fd) < 0
            || current_file(bin_fd, FINAL, reader, &final) < 0 || absent(bin_fd, CANDIDATE) < 0
            || current_bin(stage_fd, bin_fd, &bin) < 0
            || guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0) goto failed;
    published = 1;
    goto done;

failed:
    error = errno ? errno : EIO;
done:
    if (close_owned(&reader) < 0) close_error = errno;
    if (close_owned(&writer) < 0 && !close_error) close_error = errno;
    if (close_owned(&bin_fd) < 0 && !close_error) close_error = errno;
    if (close_error || (create_attempted && !published)) {
        if (!error) error = close_error ? close_error : EIO;
        (void)guest_tree_install_guard_hold(guard, error);
        errno = error;
        return GTIC_HOLD;
    }
    errno = error;
    return published ? GTIC_PUBLISHED_LOCAL_CLOSED : GTIC_NO_EFFECT_LOCAL_CLOSED;
}

static int check_installed_file(int stage_fd, int *bin_fd, int *reader) {
    struct statx stage, bin, final;
    if (sample(stage_fd, "", &stage) < 0) return -1;
    if (!private_directory(&stage)) return refuse(EXDEV);
    if (open_bin(stage_fd, &stage, O_NOATIME, bin_fd, &bin) < 0
            || absent(*bin_fd, CANDIDATE) < 0 || sample(*bin_fd, FINAL, &final) < 0
            || file_profile(&final, &bin, CONTROLLER_SIZE) < 0) return -1;

    *reader = openat(*bin_fd, FINAL, READ_FILE);
    if (*reader < 0 || current_file(*bin_fd, FINAL, *reader, &final) < 0
            || read_bytes(*reader) < 0 || current_file(*bin_fd, FINAL, *reader, &final) < 0
            || absent(*bin_fd, CANDIDATE) < 0) return -1;
    return current_bin(stage_fd, *bin_fd, &bin);
}

int guest_tree_verify_installed_controller(struct guest_tree_install_guard *guard,
        int stage_fd, int controller_namespace_fd) {
    if (!guard || stage_fd < 0 || controller_namespace_fd < 0) return refuse(EINVAL);
    if (guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0)
        return -1;

    int bin_fd = -1, reader = -1;
    int error = 0, close_error = 0;
    if (check_installed_file(stage_fd, &bin_fd, &reader) < 0) error = errno ? errno : EIO;
    if (guest_tree_fsverity_check_install_guard(guard, stage_fd, controller_namespace_fd) < 0 && !error)
        error = errno ? errno : EIO;
    if (close_owned(&reader) < 0) close_error = errno ? errno : EIO;
    if (close_owned(&bin_fd) < 0 && !close_error) close_error = errno ? errno : EIO;
    if (close_error) {
        (void)guest_tree_install_guard_hold(guard, close_error);
        if (!error) error = close_error;
    }
    return error ? refuse(error) : 0;
}
