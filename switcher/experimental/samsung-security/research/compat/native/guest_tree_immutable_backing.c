#define _GNU_SOURCE 1
#include "guest_tree_immutable_backing.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/magic.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <unistd.h>

/* Selected Linux EROFS v1, 4 KiB, with no secondary devices. */
enum {
    SUPER_OFFSET = 1024, SUPER_BYTES = 128, LOG_BLOCK_SIZE = 12,
    SUPER_BLOCK_SIZE_BITS = 12, SUPER_BLOCK_COUNT = 36, SUPER_FEATURE_INCOMPAT = 80,
    SUPER_EXTRA_DEVICES = 86, FEATURE_DEVICE_TABLE = 0x00000008
};

struct backing_state {
    struct statx tree;
    struct stat block;
    uint64_t block_bytes;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int has_option(const char *options, const char *key, int allow_value) {
    size_t key_length = strlen(key);
    while (*options) {
        const char *end = strchr(options, ',');
        size_t length = end ? (size_t)(end - options) : strlen(options);
        if (length >= key_length && memcmp(options, key, key_length) == 0
                && (length == key_length || (allow_value && options[key_length] == '='))) return 1;
        if (!end) break;
        options = end + 1;
    }
    return 0;
}

static int row_profile(const struct gpv_mount_row *row) {
    return row->id && row->major && strcmp(row->point, GUEST_TREE_BACKING_PATH) == 0
            && strcmp(row->root, "/") == 0 && strcmp(row->type, "erofs") == 0
            && has_option(row->options, "ro", 0) && has_option(row->super_options, "ro", 0)
            && !has_option(row->options, "rw", 1) && !has_option(row->super_options, "rw", 1)
            && !row->shared && !row->master && !row->propagate && !row->unbindable
            && !has_option(row->super_options, "dax", 1) && !has_option(row->super_options, "device", 1)
            && !has_option(row->super_options, "fsid", 1) && !has_option(row->super_options, "domain_id", 1);
}

static int close_on_exec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : refuse(EINVAL);
}

static int capture(int tree_fd, int block_fd, const struct gpv_mount_row *row,
                   struct backing_state *state) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_INO | STATX_UID | STATX_GID | STATX_MNT_ID;
    struct statfs fs;
    struct statvfs flags;
    int readonly = 0;

    if (close_on_exec(tree_fd) < 0 || close_on_exec(block_fd) < 0 ||
            statx(tree_fd, "", AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW,
                  mask, &state->tree) < 0) return -1;
    const struct statx *tree = &state->tree;
    if ((tree->stx_mask & mask) != mask || !S_ISDIR(tree->stx_mode) || !tree->stx_ino
            || tree->stx_uid || (tree->stx_mode & 0022) || tree->stx_mnt_id != row->id
            || tree->stx_dev_major != row->major || tree->stx_dev_minor != row->minor)
        return refuse(EXDEV);
    if (fstatfs(tree_fd, &fs) < 0 || fstatvfs(tree_fd, &flags) < 0) return -1;
    if ((unsigned long)fs.f_type != (unsigned long)EROFS_SUPER_MAGIC_V1 || !(flags.f_flag & ST_RDONLY))
        return refuse(EXDEV);

    if (fstat(block_fd, &state->block) < 0) return -1;
    if (!S_ISBLK(state->block.st_mode) || !state->block.st_ino
            || major(state->block.st_rdev) != row->major || minor(state->block.st_rdev) != row->minor)
        return refuse(EXDEV);
    int block_flags = fcntl(block_fd, F_GETFL);
    if (block_flags < 0) return -1;
    if ((block_flags & (O_ACCMODE | O_PATH | O_DIRECT)) != O_RDONLY) return refuse(EINVAL);
    if (ioctl(block_fd, BLKROGET, &readonly) < 0) return -1;
    if (readonly != 1) return refuse(EROFS);
    if (ioctl(block_fd, BLKGETSIZE64, &state->block_bytes) < 0) return -1;
    if (state->block_bytes < (UINT64_C(1) << LOG_BLOCK_SIZE)) return refuse(EPROTO);
    return 0;
}

static int same_capture(const struct backing_state *a, const struct backing_state *b) {
    const struct statx *x = &a->tree, *y = &b->tree;
    return a->block_bytes == b->block_bytes && a->block.st_ino == b->block.st_ino
            && a->block.st_dev == b->block.st_dev && a->block.st_rdev == b->block.st_rdev
            && a->block.st_mode == b->block.st_mode && a->block.st_uid == b->block.st_uid
            && a->block.st_gid == b->block.st_gid && x->stx_ino == y->stx_ino
            && x->stx_mode == y->stx_mode && x->stx_uid == y->stx_uid && x->stx_gid == y->stx_gid;
}

static uint32_t le32(const unsigned char *bytes) {
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8)
            | ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static int read_super(int block, unsigned char bytes[SUPER_BYTES]) {
    size_t used = 0;
    while (used < SUPER_BYTES) {
        ssize_t got = pread(block, bytes + used, SUPER_BYTES - used, (off_t)(SUPER_OFFSET + used));
        if (got < 0) return -1;
        if (!got || (size_t)got > SUPER_BYTES - used) return refuse(EPROTO);
        used += (size_t)got;
    }
    return 0;
}

static int super_profile(const unsigned char bytes[SUPER_BYTES], uint64_t block_bytes) {
    uint64_t blocks = le32(bytes + SUPER_BLOCK_COUNT);
    return le32(bytes) == EROFS_SUPER_MAGIC_V1 && bytes[SUPER_BLOCK_SIZE_BITS] == LOG_BLOCK_SIZE
            && blocks && blocks <= (block_bytes >> LOG_BLOCK_SIZE)
            && !(le32(bytes + SUPER_FEATURE_INCOMPAT) & FEATURE_DEVICE_TABLE)
            && !bytes[SUPER_EXTRA_DEVICES] && !bytes[SUPER_EXTRA_DEVICES + 1];
}

enum guest_tree_backing_sample guest_tree_immutable_backing_check(
        int tree_fd, int block_fd, const struct gpv_mount_row *row) {
    struct backing_state before, after;
    unsigned char first[SUPER_BYTES], again[SUPER_BYTES];
    if (!row || tree_fd < 0 || block_fd < 0 || tree_fd == block_fd) {
        errno = EINVAL;
        return GUEST_TREE_BACKING_REFUSED;
    }
    if (!row_profile(row)) {
        errno = EXDEV;
        return GUEST_TREE_BACKING_REFUSED;
    }
    if (capture(tree_fd, block_fd, row, &before) < 0 || read_super(block_fd, first) < 0)
        return GUEST_TREE_BACKING_REFUSED;
    if (!super_profile(first, before.block_bytes)) {
        errno = EPROTO;
        return GUEST_TREE_BACKING_REFUSED;
    }
    if (read_super(block_fd, again) < 0 || capture(tree_fd, block_fd, row, &after) < 0)
        return GUEST_TREE_BACKING_REFUSED;
    if (!same_capture(&before, &after) || memcmp(first, again, sizeof(first))) {
        errno = ESTALE;
        return GUEST_TREE_BACKING_REFUSED;
    }
    return GUEST_TREE_BACKING_EROFS_PROFILE;
}
