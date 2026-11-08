#define _GNU_SOURCE
#include "guest_tree_root_attach.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

_Static_assert(sizeof(struct mount_attr) == MOUNT_ATTR_SIZE_VER0, "mount_setattr v0 ABI");

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    if (!(flags & FD_CLOEXEC)) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

int guest_tree_attach_root(int source_fd, int target_fd,
                           struct guest_tree_attachment *attachment) {
    struct stat source, target, clone;
    struct statfs target_fs;
    struct statvfs clone_fs;
    const struct mount_attr attributes = {
        .attr_set = MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV,
        .propagation = MS_PRIVATE,
    };
    const unsigned long required_flags = ST_RDONLY | ST_NOSUID | ST_NODEV;
    const unsigned lookup = AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;

    if (!attachment || attachment->clone_fd != -1 || attachment->state != GUEST_TREE_ATTACH_EMPTY) {
        errno = EINVAL;
        return -1;
    }
    if (cloexec(source_fd) < 0 || cloexec(target_fd) < 0 || fstat(source_fd, &source) < 0
            || fstat(target_fd, &target) < 0 || fstatfs(target_fd, &target_fs) < 0) return -1;
    if (!S_ISDIR(source.st_mode) || source.st_uid || (source.st_mode & 0022)
            || !S_ISDIR(target.st_mode) || target.st_uid || target.st_gid
            || (target.st_mode & 07777) != 0700
            || (unsigned long)target_fs.f_type != TMPFS_MAGIC || source.st_dev == target.st_dev) {
        errno = EPERM;
        return -1;
    }

    /* No recursive clone and no pathname fallback. Adopt before another call. */
    int clone_fd = (int)syscall(SYS_open_tree, source_fd, "", lookup | OPEN_TREE_CLONE | OPEN_TREE_CLOEXEC);
    if (clone_fd < 0) return -1;
    attachment->clone_fd = clone_fd;
    attachment->state = GUEST_TREE_ATTACH_CLONE_HELD;
    if (cloexec(clone_fd) < 0 || fstat(clone_fd, &clone) < 0) return -1;
    if (clone.st_dev != source.st_dev || clone.st_ino != source.st_ino || clone.st_mode != source.st_mode
            || clone.st_uid != source.st_uid || clone.st_gid != source.st_gid) {
        errno = ESTALE;
        return -1;
    }
    if (syscall(SYS_mount_setattr, clone_fd, "", lookup, &attributes, sizeof(attributes)) < 0
            || fstatvfs(clone_fd, &clone_fs) < 0) return -1;
    if ((clone_fs.f_flag & required_flags) != required_flags) {
        errno = EPERM;
        return -1;
    }

    attachment->state = GUEST_TREE_ATTACH_MOVE_ATTEMPTED;
    if (syscall(SYS_move_mount, clone_fd, "", target_fd, "",
                MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) return -1;
    attachment->state = GUEST_TREE_ATTACH_MOVE_RETURNED;
    return 0;
}
