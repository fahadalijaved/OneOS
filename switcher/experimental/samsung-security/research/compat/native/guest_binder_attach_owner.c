#define _GNU_SOURCE
#include "guest_binder_attach_owner.h"
#include "guest_tree_dev_roles.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define BINDER_PATH GUEST_TREE_DEV_PATH "/binder"
#define BINDER_ROOT "/oneos-guest-binder"
#define LOOKUP_FLAGS (AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
#define STAT_MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK | STATX_MNT_ID)

static atomic_flag attempted = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_once(struct guest_binder_attach_owner *owner, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) {
        owner->close_error = errno ? errno : EIO;
    }
}

static int namespace_stat(int fd, struct stat *st) {
    struct statfs fs;
    if (fstat(fd, st) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !st->st_ino) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int same_namespace(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int check_namespaces(const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created) {
    struct stat parent, child, self, named_parent, creator;
    struct statfs proc;
    char path[64];
    pid_t actual_parent = getppid();
    if (actual_parent <= 1 || actual_parent != input->parent || created->source_pid != getpid()) {
        return refuse(ECHILD);
    }
    int size = snprintf(path, sizeof(path), "/proc/%ld/ns/mnt", (long)actual_parent);
    if (size < 0 || (size_t)size >= sizeof(path)) return refuse(EOVERFLOW);
    if (statfs("/proc", &proc) < 0) return -1;
    if ((unsigned long)proc.f_type != PROC_SUPER_MAGIC) return refuse(EXDEV);
    if (namespace_stat(input->witnesses[GTC_PARENT_NAMESPACE], &parent) < 0 ||
            namespace_stat(view->rights[GTC_NAMESPACE], &child) < 0 ||
            namespace_stat(created->namespace_fd, &creator) < 0 ||
            stat(path, &named_parent) < 0 || stat("/proc/self/ns/mnt", &self) < 0) return -1;
    if (getppid() != actual_parent || !same_namespace(&parent, &named_parent) ||
            same_namespace(&parent, &child) || !same_namespace(&child, &creator) ||
            !same_namespace(&child, &self) || (uint64_t)child.st_dev != view->observation.namespace_dev ||
            (uint64_t)child.st_ino != view->observation.namespace_inode) return refuse(EXDEV);
    return 0;
}

static int identity(int fd, const char *name, struct statx *st) {
    int flags = LOOKUP_FLAGS | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(fd, name, flags, STAT_MASK, st) < 0) return -1;
    if ((st->stx_mask & STAT_MASK) != STAT_MASK || !st->stx_ino || !st->stx_mnt_id ||
            !st->stx_nlink) return refuse(EXDEV);
    return 0;
}

static int same_fs(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return same_fs(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
            a->stx_nlink == b->stx_nlink && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid &&
            a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor;
}

static int same_path_object(const struct statx *a, const struct statx *b) {
    return same_inode(a, b) && a->stx_mnt_id == b->stx_mnt_id;
}

static int scratch_valid(struct guest_tree_mount_scratch scratch) {
    return scratch.text && scratch.rows && scratch.text_capacity &&
            scratch.text_capacity <= GPV_MOUNTINFO_MAX_BYTES && scratch.row_capacity &&
            scratch.row_capacity <= GPV_MOUNTINFO_MAX_ROWS;
}

static int sample_mounts(struct guest_binder_attach_owner *owner,
        struct guest_tree_mount_scratch scratch, size_t *rows) {
    struct statfs fs;
    struct statx proc, file;
    size_t used = 0;
    int error = 0;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || identity(AT_FDCWD, "/proc", &proc) < 0 ||
            identity(fd, "", &file) < 0) error = errno;
    else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISDIR(proc.stx_mode) ||
            !S_ISREG(file.stx_mode) || proc.stx_mnt_id != file.stx_mnt_id) error = EXDEV;
    while (!error && used < scratch.text_capacity) {
        ssize_t got = read(fd, scratch.text + used, scratch.text_capacity - used);
        if (got < 0) error = errno;
        else if (!got) break;
        else used += (size_t)got;
    }
    close_once(owner, &fd);
    if (error || owner->close_error) return refuse(error ? error : owner->close_error);
    if (!used || used == scratch.text_capacity ||
            gpv_parse_mountinfo(scratch.text, used, scratch.rows, scratch.row_capacity, rows) != GPV_OK) {
        return refuse(EPROTO);
    }
    return 0;
}

static int read_dev_sample(int fd, const struct statx *st, struct guest_tree_dev_identity *sample) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    *sample = (struct guest_tree_dev_identity){
        .mount = {st->stx_mnt_id, st->stx_dev_major, st->stx_dev_minor},
        .ino = st->stx_ino, .nlink = st->stx_nlink, .fs_type = (unsigned long)fs.f_type,
        .fs_flags = (unsigned long)fs.f_flags, .mode = st->stx_mode, .uid = st->stx_uid,
        .gid = st->stx_gid
    };
    return 0;
}

static int check_dev_path(struct guest_binder_attach_owner *owner, const struct gtc_child_view *view,
        struct statx *root, struct statx *dev, struct guest_tree_dev_sample *sample) {
    struct statx socket, named_dev, named_socket;
    const int root_fd = view->rights[GTC_GUEST_ROOT];
    const int dev_fd = view->rights[GTC_DEV];
    const int socket_fd = view->rights[GTC_SOCKET];
    const int dir_flags = O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC;
    int reopened_dev = -1, reopened_socket = -1;
    int error = 0;
    if (identity(root_fd, "", root) < 0 || identity(dev_fd, "", dev) < 0 ||
            identity(socket_fd, "", &socket) < 0) return -1;
    if (!S_ISDIR(root->stx_mode) || root->stx_mnt_id != view->observation.mounts[GTC_GUEST_ROOT] ||
            dev->stx_mnt_id != view->observation.mounts[GTC_DEV] ||
            socket.stx_mnt_id != view->observation.mounts[GTC_SOCKET]) return refuse(EXDEV);

    reopened_dev = openat(root_fd, "dev", dir_flags);
    if (reopened_dev < 0) return -1;
    reopened_socket = openat(reopened_dev, "socket", dir_flags);
    if (reopened_socket < 0 || identity(reopened_dev, "", &named_dev) < 0 ||
            identity(reopened_socket, "", &named_socket) < 0) error = errno;
    else if (!same_path_object(dev, &named_dev) || !same_path_object(&socket, &named_socket)) error = EXDEV;
    else if (read_dev_sample(dev_fd, dev, &sample->dev) < 0 ||
            read_dev_sample(socket_fd, &socket, &sample->socket_dir) < 0 ||
            read_dev_sample(reopened_dev, &named_dev, &sample->reopened_dev) < 0 ||
            read_dev_sample(reopened_socket, &named_socket, &sample->reopened_socket) < 0) error = errno;
    close_once(owner, &reopened_socket);
    close_once(owner, &reopened_dev);
    if (error || owner->close_error) return refuse(error ? error : owner->close_error);
    return 0;
}

static int binder_flags(int fd) {
    struct statfs fs;
    struct statvfs flags;
    if (fstatfs(fd, &fs) < 0 || fstatvfs(fd, &flags) < 0) return -1;
    if ((unsigned long)fs.f_type != BINDERFS_SUPER_MAGIC ||
            (flags.f_flag & (ST_RDONLY | ST_NOSUID | ST_NOEXEC | ST_NODEV)) !=
                (ST_NOSUID | ST_NOEXEC)) return refuse(EXDEV);
    return 0;
}

static int check_detached_device(const struct guest_binder_context_owner *created, struct statx *node) {
    struct statx mount;
    if (created->state != GUEST_BINDER_CONTEXT_DEVICE_HELD || created->close_error ||
            created->control_fd != -1 || created->fs_context_fd != -1) return refuse(EINVAL);
    int flags = fcntl(created->device_fd, F_GETFL);
    if (flags < 0 || identity(created->device_fd, "", node) < 0 ||
            identity(created->mount_fd, "", &mount) < 0 || binder_flags(created->device_fd) < 0 ||
            binder_flags(created->mount_fd) < 0) return -1;
    if (!(flags & O_PATH) || !S_ISDIR(mount.stx_mode) || !S_ISCHR(node->stx_mode) ||
            node->stx_nlink != 1 || !node->stx_rdev_major || !same_fs(&mount, node) ||
            mount.stx_mnt_id != node->stx_mnt_id || node->stx_mnt_id != created->device_mount_id ||
            node->stx_ino != created->device_inode || node->stx_rdev_major != created->device_major ||
            node->stx_rdev_minor != created->device_minor) return refuse(EXDEV);
    return 0;
}

static int same_row(const struct gpv_mount_row *a, const struct gpv_mount_row *b) {
    return b && a->id == b->id && a->parent == b->parent && a->shared == b->shared &&
            a->master == b->master && a->propagate == b->propagate && a->major == b->major &&
            a->minor == b->minor && a->unbindable == b->unbindable && !strcmp(a->root, b->root) &&
            !strcmp(a->point, b->point) && !strcmp(a->source, b->source) &&
            !strcmp(a->type, b->type) && !strcmp(a->options, b->options) &&
            !strcmp(a->super_options, b->super_options);
}

static int check_new_mount(const struct statx *node, const struct statx *dev,
        struct guest_tree_mount_scratch before, size_t old_count,
        struct guest_tree_mount_scratch after, size_t new_count) {
    const struct gpv_mount_row *row = gpv_mount_by_id(after.rows, new_count, node->stx_mnt_id);
    if (!row || new_count != old_count + 1 || gpv_mount_by_id(before.rows, old_count, row->id) ||
            row->parent != dev->stx_mnt_id || row->major != node->stx_dev_major ||
            row->minor != node->stx_dev_minor || strcmp(row->point, BINDER_PATH) ||
            strcmp(row->root, BINDER_ROOT) || strcmp(row->type, "binder") ||
            row->shared || row->master || row->propagate || row->unbindable) return refuse(EXDEV);
    for (size_t i = 0; i < old_count; ++i) {
        if (!same_row(&before.rows[i], gpv_mount_by_id(after.rows, new_count, before.rows[i].id))) {
            return refuse(ESTALE);
        }
    }
    return 0;
}

int guest_binder_attach(struct guest_binder_attach_owner *owner,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created,
        struct guest_tree_mount_scratch before, struct guest_tree_mount_scratch after) {
    struct statx root, dev, source, clone, target, named, attached, after_root, after_dev;
    struct guest_tree_dev_sample sample;
    size_t before_count, after_count;

    if (!owner || !input || !input->witnesses || !view || !created ||
            !scratch_valid(before) || !scratch_valid(after) || before.text == after.text ||
            before.rows == after.rows || owner->state != GUEST_BINDER_ATTACH_EMPTY ||
            owner->source_pid || owner->clone_fd != -1 || owner->target_fd != -1 ||
            owner->attached_fd != -1 || owner->close_error || owner->attached_mount_id) {
        return refuse(EINVAL);
    }
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_relaxed)) return refuse(EALREADY);
    owner->source_pid = getpid();
    owner->state = GUEST_BINDER_ATTACH_STARTED;
    if (check_namespaces(input, view, created) < 0 || check_detached_device(created, &source) < 0 ||
            check_dev_path(owner, view, &root, &dev, &sample) < 0 ||
            sample_mounts(owner, before, &before_count) < 0) return -1;
    const struct gpv_mount_row *root_row = gpv_mount_by_id(before.rows, before_count, root.stx_mnt_id);
    if (!root_row || root_row->shared || root_row->master || root_row->propagate || root_row->unbindable ||
            guest_tree_dev_roles_check(before.rows, before_count, root.stx_mnt_id, &sample) < 0 ||
            gpv_mount_by_id(before.rows, before_count, source.stx_mnt_id)) return refuse(EXDEV);

    /* Clone only the exact character-device subtree. No recursive or pathname fallback. */
    owner->clone_fd = (int)syscall(SYS_open_tree, created->device_fd, "",
            LOOKUP_FLAGS | AT_EMPTY_PATH | OPEN_TREE_CLONE | OPEN_TREE_CLOEXEC);
    if (owner->clone_fd < 0 || identity(owner->clone_fd, "", &clone) < 0 ||
            binder_flags(owner->clone_fd) < 0) return -1;
    if (!same_inode(&source, &clone) || clone.stx_mnt_id == source.stx_mnt_id ||
            gpv_mount_by_id(before.rows, before_count, clone.stx_mnt_id)) return refuse(EXDEV);

    int dev_fd = view->rights[GTC_DEV];
    owner->target_fd = openat(dev_fd, "binder", O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC | O_RDWR, 0600);
    if (owner->target_fd < 0 || identity(owner->target_fd, "", &target) < 0 ||
            identity(dev_fd, "binder", &named) < 0 || check_namespaces(input, view, created) < 0) return -1;
    if (!same_fs(&target, &dev) || target.stx_mnt_id != dev.stx_mnt_id ||
            target.stx_mode != (S_IFREG | 0600) || target.stx_uid || target.stx_gid ||
            target.stx_nlink != 1 || !same_path_object(&named, &target)) return refuse(EXDEV);

    owner->state = GUEST_BINDER_ATTACH_MOVE_ATTEMPTED;
    if (syscall(SYS_move_mount, owner->clone_fd, "", owner->target_fd, "",
                MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) return -1;

    owner->attached_fd = openat(dev_fd, "binder", O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (owner->attached_fd < 0 || identity(owner->attached_fd, "", &attached) < 0 ||
            binder_flags(owner->attached_fd) < 0 || identity(dev_fd, "binder", &named) < 0 ||
            check_dev_path(owner, view, &after_root, &after_dev, &sample) < 0 ||
            sample_mounts(owner, after, &after_count) < 0 || check_namespaces(input, view, created) < 0) return -1;
    if (!same_path_object(&root, &after_root) || !same_path_object(&dev, &after_dev) ||
            !same_path_object(&clone, &attached) || !same_path_object(&attached, &named)) return refuse(EXDEV);
    if (check_new_mount(&attached, &dev, before, before_count, after, after_count) < 0) return -1;

    owner->attached_mount_id = attached.stx_mnt_id;
    owner->state = GUEST_BINDER_ATTACH_NODE_HELD;
    return 0;
}

int guest_binder_attach_close(struct guest_binder_attach_owner *owner) {
    if (!owner || owner->state == GUEST_BINDER_ATTACH_EMPTY || owner->source_pid != getpid()) {
        return refuse(EINVAL);
    }
    if (owner->state != GUEST_BINDER_ATTACH_RETIRED &&
            owner->state != GUEST_BINDER_ATTACH_RETIRED_AFTER_MOVE) {
        owner->state = owner->state == GUEST_BINDER_ATTACH_MOVE_ATTEMPTED ||
                owner->state == GUEST_BINDER_ATTACH_NODE_HELD
                ? GUEST_BINDER_ATTACH_RETIRED_AFTER_MOVE : GUEST_BINDER_ATTACH_RETIRED;
        close_once(owner, &owner->attached_fd);
        close_once(owner, &owner->target_fd);
        close_once(owner, &owner->clone_fd);
    }
    return owner->close_error ? refuse(owner->close_error) : 0;
}
