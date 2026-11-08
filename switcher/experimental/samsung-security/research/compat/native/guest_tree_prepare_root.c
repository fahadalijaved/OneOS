#define _GNU_SOURCE
#include "guest_tree_prepare_root.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#include "guest_tree_attached_mounts.h"

static int mount_namespace(int fd, struct stat *identity) {
    struct statfs fs;
    int type;
    if (fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) {
        errno = EXDEV;
        return -1;
    }
    type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    if (type != CLONE_NEWNS) {
        errno = EXDEV;
        return -1;
    }
    return 0;
}

static int child_namespace(const struct guest_tree_root_inputs *input, struct stat *child) {
    struct stat parent, current;
    if (input->parent_pid <= 1 || getppid() != input->parent_pid) {
        errno = ECHILD;
        return -1;
    }
    if (mount_namespace(input->parent_namespace_fd, &parent) < 0 ||
        mount_namespace(input->child_namespace_fd, child) < 0 ||
        stat("/proc/self/ns/mnt", &current) < 0) return -1;
    if (child->st_dev != current.st_dev || child->st_ino != current.st_ino ||
        (parent.st_dev == child->st_dev && parent.st_ino == child->st_ino)) {
        errno = EXDEV;
        return -1;
    }
    return 0;
}

static int capture_mountinfo(char *text, size_t capacity, size_t *length) {
    struct statfs fs;
    struct statx proc, file;
    size_t used = 0;
    const unsigned mask = STATX_TYPE | STATX_MNT_ID;
    const int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    int failure = 0;
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || statx(AT_FDCWD, "/proc", flags, mask, &proc) < 0 ||
        statx(fd, "", flags | AT_EMPTY_PATH, mask, &file) < 0) failure = errno;
    else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || (proc.stx_mask & mask) != mask ||
             (file.stx_mask & mask) != mask || !proc.stx_mnt_id || proc.stx_mnt_id != file.stx_mnt_id ||
             !S_ISDIR(proc.stx_mode) || !S_ISREG(file.stx_mode)) failure = EXDEV;
    while (!failure && used < capacity) {
        ssize_t count = read(fd, text + used, capacity - used);
        if (count < 0) failure = errno;
        else if (count == 0) break;
        else used += (size_t)count;
    }
    if (!failure && (used == capacity || used == 0)) failure = EPROTO;
    if (close(fd) < 0 && !failure) failure = errno;
    if (failure) {
        errno = failure;
        return -1;
    }
    *length = used;
    return 0;
}

static int valid_workspace(struct guest_tree_mount_scratch scratch) {
    return scratch.text && scratch.text_capacity > 1 &&
           scratch.text_capacity <= GPV_MOUNTINFO_MAX_BYTES + 1U && scratch.rows &&
           scratch.row_capacity > 0 && scratch.row_capacity <= GPV_MOUNTINFO_MAX_ROWS;
}

int guest_tree_prepare_root(const struct guest_tree_root_inputs *input,
                            struct guest_tree_mount_scratch before,
                            struct guest_tree_mount_scratch after,
                            struct guest_tree_root_preparation *result) {
    struct guest_tree_mount_snapshot pre = {.mountinfo = before.text};
    struct guest_tree_mount_snapshot post = {.mountinfo = after.text};
    struct stat ns;
    if (!input || !result || result->attachment.clone_fd != -1 || result->readback.root_fd != -1 ||
        result->attachment.state != GUEST_TREE_ATTACH_EMPTY || !valid_workspace(before) ||
        !valid_workspace(after) || before.text == after.text || before.rows == after.rows) {
        errno = EINVAL;
        return -1;
    }
    if (child_namespace(input, &ns) < 0 ||
        guest_tree_admit_root_fds(input->source_fd, input->scaffold_parent_fd, input->target_fd,
                                 &pre.source, &pre.scaffold) < 0 ||
        capture_mountinfo(before.text, before.text_capacity, &pre.length) < 0) return -1;
    pre.namespace_dev = ns.st_dev;
    pre.namespace_ino = ns.st_ino;
    if (guest_tree_source_mounts_check(pre.mountinfo, pre.length, before.rows, before.row_capacity,
                                       pre.source, pre.scaffold) != GUEST_TREE_SOURCE_MOUNTS_MATCHED) {
        errno = EXDEV;
        return -1;
    }
    if (guest_tree_attach_root(input->source_fd, input->target_fd, &result->attachment) < 0 ||
        guest_tree_read_attached_root(input->source_fd, input->scaffold_parent_fd, input->target_fd,
                                      &result->attachment, &result->readback) < 0 ||
        capture_mountinfo(after.text, after.text_capacity, &post.length) < 0 ||
        child_namespace(input, &ns) < 0) return -1;
    post.source = result->readback.source;
    post.scaffold = result->readback.scaffold;
    post.namespace_dev = ns.st_dev;
    post.namespace_ino = ns.st_ino;
    if (guest_tree_attached_mounts_check(0, &pre, &post, result->readback.attached,
            before.rows, before.row_capacity, after.rows, after.row_capacity) != GUEST_TREE_ATTACHED_MOUNTS_MATCHED) {
        errno = ESTALE;
        return -1;
    }
    return 0;
}
