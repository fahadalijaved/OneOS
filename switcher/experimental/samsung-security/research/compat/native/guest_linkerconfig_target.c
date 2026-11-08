#define _GNU_SOURCE
#include "guest_linkerconfig_target.h"
#include "guest_linkerconfig_seed.h"
#include "guest_readback_identity.h"

#include <linux/magic.h>
#include <linux/mount.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

static const char target_name[] = "linkerconfig";
static const int directory_flags = O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC;

static int close_owned(int *fd) {
    int owned = *fd;
    *fd = -1;
    return owned < 0 ? 0 : close(owned);
}

static int sample_directory(int fd, unsigned long magic, struct statx *node) {
    struct statfs fs;
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0 || fstatfs(fd, &fs) < 0 || guest_readback_stat(fd, "", node) < 0) return -1;
    if (!(flags & FD_CLOEXEC) || (unsigned long)fs.f_type != magic
            || node->stx_mode != (S_IFDIR | 0755) || node->stx_uid || node->stx_gid)
        return guest_readback_refuse(EXDEV);
    return 0;
}

static int check_name(int root_fd, const struct statx *held) {
    struct statx named;
    if (guest_readback_stat(root_fd, target_name, &named) < 0) return -1;
    return guest_readback_same_node(held, &named) ? 0 : guest_readback_refuse(ESTALE);
}

static int sample_tmpfs(int fd, struct statx *node) {
    struct statvfs fs;
    const unsigned long required = ST_NOSUID | ST_NODEV | ST_NOEXEC;
    if (fstatvfs(fd, &fs) < 0 || sample_directory(fd, TMPFS_MAGIC, node) < 0) return -1;
    if ((fs.f_flag & (required | ST_RDONLY)) != required || node->stx_nlink != 2)
        return guest_readback_refuse(EXDEV);
    return 0;
}

static int same_generation_node(const struct guest_linkerconfig_generation_node *node, const struct statx *sample) {
    return node->mount_id == sample->stx_mnt_id && node->inode == sample->stx_ino
            && node->device_major == sample->stx_dev_major && node->device_minor == sample->stx_dev_minor
            && node->mode == sample->stx_mode && node->uid == sample->stx_uid && node->gid == sample->stx_gid;
}

int guest_linkerconfig_prepare_target(int root_fd, uint64_t root_mount_id,
        struct guest_linkerconfig_generation_start *out) {
    if (root_fd < 0 || !root_mount_id || !out) return guest_readback_refuse(EINVAL);

    struct statfs root_fs;
    struct statx root;
    int root_flags = fcntl(root_fd, F_GETFD);
    if (root_flags < 0 || fstatfs(root_fd, &root_fs) < 0 || guest_readback_stat(root_fd, "", &root) < 0)
        return -1;
    if (!(root_flags & FD_CLOEXEC) || (unsigned long)root_fs.f_type != EROFS_SUPER_MAGIC_V1
            || !S_ISDIR(root.stx_mode) || root.stx_mnt_id != root_mount_id)
        return guest_readback_refuse(EXDEV);

    int context_fd = -1, mount_fd = -1, directory_fd = -1, base_fd = -1;
    int covered_fd = openat(root_fd, target_name, directory_flags);
    if (covered_fd < 0) return -1;

    struct statx covered, detached, visible;
    if (sample_directory(covered_fd, EROFS_SUPER_MAGIC_V1, &covered) < 0) goto failed;
    if (!guest_readback_same_mount(&root, &covered) || root.stx_ino == covered.stx_ino
            || covered.stx_nlink != 2) {
        errno = EXDEV;
        goto failed;
    }
    if (check_name(root_fd, &covered) < 0) goto failed;

    context_fd = (int)syscall(SYS_fsopen, "tmpfs", FSOPEN_CLOEXEC);
    if (context_fd < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_SET_STRING, "mode", "0755", 0) < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_SET_STRING, "uid", "0", 0) < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_SET_STRING, "gid", "0", 0) < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_SET_STRING, "size", "8388608", 0) < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_SET_STRING, "nr_inodes", "64", 0) < 0
            || syscall(SYS_fsconfig, context_fd, FSCONFIG_CMD_CREATE, NULL, NULL, 0) < 0) goto failed;
    mount_fd = (int)syscall(SYS_fsmount, context_fd, FSMOUNT_CLOEXEC,
            MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV | MOUNT_ATTR_NOEXEC);
    if (mount_fd < 0 || close_owned(&context_fd) < 0 || sample_tmpfs(mount_fd, &detached) < 0) goto failed;
    if (detached.stx_mnt_id == root_mount_id) {
        errno = EXDEV;
        goto failed;
    }

    struct statx current;
    if (guest_readback_stat(covered_fd, "", &current) < 0) goto failed;
    if (!guest_readback_same_node(&covered, &current)) {
        errno = ESTALE;
        goto failed;
    }
    if (check_name(root_fd, &covered) < 0
            || syscall(SYS_move_mount, mount_fd, "", covered_fd, "",
                MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) goto failed;

    directory_fd = openat(root_fd, target_name, directory_flags);
    if (directory_fd < 0 || sample_tmpfs(directory_fd, &visible) < 0) goto failed;
    if (!guest_readback_same_node(&detached, &visible)) {
        errno = ESTALE;
        goto failed;
    }
    if (check_name(root_fd, &visible) < 0 || close_owned(&covered_fd) < 0) goto failed;

    struct guest_linkerconfig_generation_start result;
    if (guest_linkerconfig_seed_target(root_fd, directory_fd, &result) < 0) goto failed;
    base_fd = result.base_fd;
    if (sample_tmpfs(directory_fd, &visible) < 0) goto failed;
    if (!guest_readback_same_mount(&detached, &visible) || detached.stx_ino != visible.stx_ino
            || !same_generation_node(&result.root, &root) || !same_generation_node(&result.directory, &visible)) {
        errno = ESTALE;
        goto failed;
    }
    if (check_name(root_fd, &visible) < 0 || close_owned(&mount_fd) < 0) goto failed;
    *out = result;
    return 0;

failed: {
        int error = errno;
        (void)close_owned(&base_fd);
        (void)close_owned(&directory_fd);
        (void)close_owned(&mount_fd);
        (void)close_owned(&context_fd);
        (void)close_owned(&covered_fd);
        return guest_readback_refuse(error);
    }
}
