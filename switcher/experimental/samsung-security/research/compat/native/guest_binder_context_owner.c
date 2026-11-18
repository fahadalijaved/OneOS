#define _GNU_SOURCE
#include "guest_binder_context_owner.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/android/binderfs.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DEVICE_NAME "oneos-guest-binder"

_Static_assert(sizeof(struct binderfs_device) == 264, "binderfs add ABI");
_Static_assert(sizeof(DEVICE_NAME) <= BINDERFS_MAX_NAME + 1, "fixed name bound");

static atomic_flag attempted = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int close_once(struct guest_binder_context_owner *owner, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd < 0 || close(fd) == 0) return 0;
    if (!owner->close_error) owner->close_error = errno ? errno : EIO;
    return refuse(owner->close_error);
}

static int mount_namespace(int fd, struct stat *identity) {
    struct statfs fs;
    if (fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    if (type != CLONE_NEWNS || !identity->st_ino) return refuse(EXDEV);
    return 0;
}

static int same_inode(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int verify_current_namespace(const struct stat *expected) {
    struct stat current;
    struct statfs proc;
    if (statfs("/proc", &proc) < 0 || stat("/proc/self/ns/mnt", &current) < 0) return -1;
    if ((unsigned long)proc.f_type != PROC_SUPER_MAGIC || !same_inode(&current, expected)) {
        return refuse(EXDEV);
    }
    return 0;
}

static int binderfs_identity(int fd, struct statx *entry) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_NLINK | STATX_UID |
                          STATX_GID | STATX_INO | STATX_MNT_ID;
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0 || statx(fd, "", AT_EMPTY_PATH | AT_NO_AUTOMOUNT |
                AT_SYMLINK_NOFOLLOW, mask, entry) < 0) return -1;
    if ((unsigned long)fs.f_type != BINDERFS_SUPER_MAGIC ||
            (entry->stx_mask & mask) != mask || !entry->stx_ino || !entry->stx_mnt_id) {
        return refuse(EXDEV);
    }
    return 0;
}

static int same_fs(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && same_fs(a, b);
}

static int same_device_number(const struct statx *a, const struct statx *b) {
    return a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor;
}

int guest_binder_context_create(struct guest_binder_context_owner *owner,
        int parent_namespace_fd, int child_namespace_fd, int host_binder_fd) {
    struct stat parent, child, current;
    struct statx host, root, control, node;
    struct statvfs fs;
    struct binderfs_device added = {.name = DEVICE_NAME};
    int host_flags;

    if (!owner || owner->state != GUEST_BINDER_CONTEXT_EMPTY || owner->source_pid ||
            owner->namespace_fd != -1 || owner->fs_context_fd != -1 || owner->mount_fd != -1 ||
            owner->control_fd != -1 || owner->device_fd != -1 || owner->close_error ||
            owner->device_major || owner->device_minor || owner->device_inode || owner->device_mount_id) {
        return refuse(EINVAL);
    }
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_relaxed)) return refuse(EALREADY);
    owner->source_pid = getpid();
    owner->state = GUEST_BINDER_CONTEXT_STARTED;

    if (mount_namespace(parent_namespace_fd, &parent) < 0 ||
            mount_namespace(child_namespace_fd, &child) < 0 ||
            verify_current_namespace(&child) < 0) return -1;
    if (same_inode(&parent, &child)) return refuse(EXDEV);

    /* Retain an independent actual namespace FD before creating the filesystem. */
    owner->namespace_fd = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (owner->namespace_fd < 0 || mount_namespace(owner->namespace_fd, &current) < 0) return -1;
    if (!same_inode(&current, &child)) return refuse(EXDEV);

    host_flags = fcntl(host_binder_fd, F_GETFL);
    if (host_flags < 0 || binderfs_identity(host_binder_fd, &host) < 0) return -1;
    if (!(host_flags & O_PATH) || !S_ISCHR(host.stx_mode) || !host.stx_rdev_major) return refuse(EXDEV);

    /* Each kernel-returned descriptor belongs to this owner before later work. */
    owner->fs_context_fd = (int)syscall(SYS_fsopen, "binder", FSOPEN_CLOEXEC);
    if (owner->fs_context_fd < 0 ||
            syscall(SYS_fsconfig, owner->fs_context_fd, FSCONFIG_CMD_CREATE, NULL, NULL, 0) < 0) return -1;
    owner->mount_fd = (int)syscall(SYS_fsmount, owner->fs_context_fd, FSMOUNT_CLOEXEC,
                                  MOUNT_ATTR_NOSUID | MOUNT_ATTR_NOEXEC);
    if (owner->mount_fd < 0 || close_once(owner, &owner->fs_context_fd) < 0 ||
            binderfs_identity(owner->mount_fd, &root) < 0 || fstatvfs(owner->mount_fd, &fs) < 0) return -1;
    if (!S_ISDIR(root.stx_mode) || root.stx_mnt_id == host.stx_mnt_id || same_fs(&root, &host) ||
            (fs.f_flag & (ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC)) != (ST_NOSUID | ST_NOEXEC)) {
        return refuse(EXDEV);
    }

    owner->control_fd = openat(owner->mount_fd, "binder-control",
                               O_RDWR | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
    if (owner->control_fd < 0 || binderfs_identity(owner->control_fd, &control) < 0 ||
            verify_current_namespace(&child) < 0) return -1;
    if (!S_ISCHR(control.stx_mode) || !same_mount(&control, &root) ||
            same_device_number(&control, &host)) return refuse(EXDEV);

    owner->state = GUEST_BINDER_CONTEXT_ADD_ATTEMPTED;
    int add_result = ioctl(owner->control_fd, BINDER_CTL_ADD, &added);
    if (add_result < 0) return -1;
    if (close_once(owner, &owner->control_fd) < 0) return -1;
    if (add_result != 0 || !added.major ||
            memcmp(added.name, DEVICE_NAME, sizeof(DEVICE_NAME)) != 0) return refuse(EPROTO);

    owner->device_fd = openat(owner->mount_fd, DEVICE_NAME, O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (owner->device_fd < 0 || binderfs_identity(owner->device_fd, &node) < 0 ||
            verify_current_namespace(&child) < 0) return -1;
    if (!S_ISCHR(node.stx_mode) || node.stx_nlink != 1 ||
            node.stx_rdev_major != added.major || node.stx_rdev_minor != added.minor ||
            !same_mount(&node, &root) || node.stx_ino == control.stx_ino ||
            same_device_number(&node, &host) || same_device_number(&node, &control)) return refuse(EXDEV);

    owner->device_major = added.major;
    owner->device_minor = added.minor;
    owner->device_inode = node.stx_ino;
    owner->device_mount_id = node.stx_mnt_id;
    owner->state = GUEST_BINDER_CONTEXT_DEVICE_HELD;
    return 0;
}

int guest_binder_context_close(struct guest_binder_context_owner *owner) {
    if (!owner || owner->state == GUEST_BINDER_CONTEXT_EMPTY || owner->source_pid != getpid()) {
        return refuse(EINVAL);
    }
    if (owner->state != GUEST_BINDER_CONTEXT_RETIRED) {
        owner->state = GUEST_BINDER_CONTEXT_RETIRED;
        (void)close_once(owner, &owner->device_fd);
        (void)close_once(owner, &owner->control_fd);
        (void)close_once(owner, &owner->mount_fd);
        (void)close_once(owner, &owner->fs_context_fd);
        (void)close_once(owner, &owner->namespace_fd);
    }
    return owner->close_error ? refuse(owner->close_error) : 0;
}
