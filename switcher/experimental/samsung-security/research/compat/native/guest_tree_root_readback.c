#define _GNU_SOURCE
#include "guest_tree_root_readback.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <unistd.h>

static int directory_stat(int fd, const char *path, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_NLINK | STATX_UID | STATX_GID |
                          STATX_INO | STATX_MTIME | STATX_CTIME | STATX_MNT_ID;
    if (statx(fd, path, AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT, mask, value) < 0)
        return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_mnt_id || !S_ISDIR(value->stx_mode)) {
        errno = EPROTO;
        return -1;
    }
    return 0;
}

static int directory_identity(int fd, struct statx *value) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    if (!(flags & FD_CLOEXEC)) {
        errno = EINVAL;
        return -1;
    }
    return directory_stat(fd, "", value);
}

static int same_device(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return same_device(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
           a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink &&
           a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec &&
           a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static struct guest_tree_mount_identity mount_identity(const struct statx *value) {
    return (struct guest_tree_mount_identity){value->stx_mnt_id, value->stx_dev_major, value->stx_dev_minor};
}

static int named_directory(int base, const char *path, const struct statx *held) {
    struct statx named;
    if (directory_stat(base, path, &named) < 0) return -1;
    if (held->stx_mnt_id != named.stx_mnt_id || !same_directory(held, &named)) {
        errno = ESTALE;
        return -1;
    }
    return 0;
}

int guest_tree_admit_root_fds(int source_fd, int scaffold_parent_fd, int target_fd,
                             struct guest_tree_mount_identity *source,
                             struct guest_tree_mount_identity *scaffold) {
    struct statx source_identity, scaffold_identity, target_identity;
    if (!source || !scaffold || source == scaffold) {
        errno = EINVAL;
        return -1;
    }
    if (directory_identity(source_fd, &source_identity) < 0 ||
        directory_identity(scaffold_parent_fd, &scaffold_identity) < 0 ||
        directory_identity(target_fd, &target_identity) < 0 ||
        named_directory(AT_FDCWD, GUEST_TREE_SOURCE_PATH, &source_identity) < 0 ||
        named_directory(AT_FDCWD, GUEST_TREE_TARGET_PATH, &target_identity) < 0 ||
        named_directory(scaffold_parent_fd, "root", &target_identity) < 0) return -1;
    if (scaffold_identity.stx_mnt_id != target_identity.stx_mnt_id ||
        !same_device(&scaffold_identity, &target_identity) ||
        scaffold_identity.stx_ino == target_identity.stx_ino) {
        errno = ESTALE;
        return -1;
    }
    *source = mount_identity(&source_identity);
    *scaffold = mount_identity(&target_identity);
    return 0;
}

int guest_tree_read_attached_root(int source_fd, int scaffold_parent_fd,
                                  int covered_target_fd,
                                  const struct guest_tree_attachment *attachment,
                                  struct guest_tree_root_readback *result) {
    struct statx source, scaffold, covered, clone, reopened;
    struct statvfs filesystem;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV;

    if (!attachment || attachment->state != GUEST_TREE_ATTACH_MOVE_RETURNED ||
        !result || result->root_fd != -1) {
        errno = EINVAL;
        return -1;
    }
    result->source = (struct guest_tree_mount_identity){0};
    result->scaffold = (struct guest_tree_mount_identity){0};
    result->attached = (struct guest_tree_mount_identity){0};
    if (directory_identity(source_fd, &source) < 0 || directory_identity(scaffold_parent_fd, &scaffold) < 0 ||
        directory_identity(covered_target_fd, &covered) < 0 || directory_identity(attachment->clone_fd, &clone) < 0)
        return -1;
    if (scaffold.stx_mnt_id != covered.stx_mnt_id || !same_device(&scaffold, &covered) ||
        scaffold.stx_ino == covered.stx_ino || same_device(&source, &scaffold) ||
        clone.stx_mnt_id == source.stx_mnt_id || clone.stx_mnt_id == scaffold.stx_mnt_id ||
        !same_directory(&source, &clone)) {
        errno = ESTALE;
        return -1;
    }

    int root_fd = openat(scaffold_parent_fd, "root", O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (root_fd < 0) return -1;
    result->root_fd = root_fd;
    if (directory_identity(root_fd, &reopened) < 0 || fstatvfs(root_fd, &filesystem) < 0) return -1;
    if (reopened.stx_mnt_id != clone.stx_mnt_id || !same_directory(&clone, &reopened) ||
        (filesystem.f_flag & required) != required) {
        errno = ESTALE;
        return -1;
    }
    result->source = mount_identity(&source);
    result->scaffold = mount_identity(&scaffold);
    result->attached = mount_identity(&reopened);
    return 0;
}
