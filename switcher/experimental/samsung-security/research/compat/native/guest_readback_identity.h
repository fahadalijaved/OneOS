#ifndef ONEOS_GUEST_READBACK_IDENTITY_H
#define ONEOS_GUEST_READBACK_IDENTITY_H

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>

/* Internal Linux statx helpers for borrowed readback descriptors. */
static inline int guest_readback_refuse(int error) {
    errno = error;
    return -1;
}

static inline int guest_readback_stat(int fd, const char *name, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_INO | STATX_NLINK | STATX_UID | STATX_GID
            | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID;
    if (statx(fd, name, AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT, mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_ino || !value->stx_mnt_id)
        return guest_readback_refuse(ESTALE);
    return 0;
}

static inline int guest_readback_same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
            && a->stx_dev_minor == b->stx_dev_minor;
}

static inline int guest_readback_same_node(const struct statx *a, const struct statx *b) {
    return guest_readback_same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
            && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink
            && a->stx_size == b->stx_size && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec
            && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec
            && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

#endif
