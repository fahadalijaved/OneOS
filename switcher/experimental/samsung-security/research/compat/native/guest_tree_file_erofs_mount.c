#define _GNU_SOURCE
#include "guest_tree_file_erofs_mount.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <stdatomic.h>
#include <stdio.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

struct gtfm_owner {
    pid_t parent;
    int context_fd, mount_fd;
    int ready, close_error;
    struct gtfm_identity identity;
};

static struct gtfm_owner one;
static atomic_flag active = ATOMIC_FLAG_INIT;
static const int lookup = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
static const unsigned node_mask = STATX_TYPE | STATX_MODE | STATX_INO | STATX_MNT_ID;
static const unsigned image_mask = STATX_TYPE | STATX_MODE | STATX_INO | STATX_MNT_ID
    | STATX_UID | STATX_GID | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int enter(void) {
    if (getpid() != gettid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(struct gtfm_owner *owner) {
    if (enter() < 0) return -1;
    if (owner == &one && one.parent == getpid()) return 0;
    leave();
    return refuse(EINVAL);
}

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return flags & FD_CLOEXEC ? 0 : refuse(EINVAL);
}

static int sample(int dir, const char *path, int flags, unsigned mask, struct statx *value) {
    if (statx(dir, path, flags, mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_mnt_id) return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_image(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink
        && a->stx_size == b->stx_size && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec
        && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec
        && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int image_sample(int fd, struct statx *value) {
    struct statfs fs;
    if (cloexec(fd) < 0) return -1;
    int mode = fcntl(fd, F_GETFL);
    if (mode < 0) return -1;
    if ((mode & (O_ACCMODE | O_PATH | O_DIRECT)) != O_RDONLY) return refuse(EINVAL);
    if (fstatfs(fd, &fs) < 0 || sample(fd, "", lookup | AT_EMPTY_PATH, image_mask, value) < 0) return -1;
    if ((unsigned long)fs.f_type != F2FS_SUPER_MAGIC || !S_ISREG(value->stx_mode)
            || value->stx_uid || value->stx_gid || (value->stx_mode & 0022)
            || value->stx_nlink != 1 || !value->stx_size || !value->stx_ino) return refuse(EXDEV);
    return 0;
}

static int transport(int proc, const char *relative, const struct statx *image) {
    struct statfs fs;
    struct statx held, named, directory, link, target;
    if (cloexec(proc) < 0 || fstatfs(proc, &fs) < 0
            || sample(proc, "", lookup | AT_EMPTY_PATH, node_mask, &held) < 0
            || sample(AT_FDCWD, "/proc", lookup, node_mask, &named) < 0
            || sample(proc, "self/fd", lookup, node_mask, &directory) < 0
            || sample(proc, relative, lookup, node_mask, &link) < 0) return -1;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISDIR(held.stx_mode)
            || !S_ISDIR(named.stx_mode) || !held.stx_ino || held.stx_ino != named.stx_ino || !same_mount(&held, &named)
            || !S_ISDIR(directory.stx_mode) || !directory.stx_ino || !same_mount(&held, &directory)
            || !S_ISLNK(link.stx_mode) || !link.stx_ino || !same_mount(&held, &link)) return refuse(EXDEV);
    /* Follow the exact procfs magic link to the same referenced image. */
    if (sample(proc, relative, AT_NO_AUTOMOUNT, image_mask, &target) < 0) return -1;
    return same_image(image, &target) ? 0 : refuse(ESTALE);
}

static int mount_sample(int fd, struct gtfm_identity *value) {
    struct statfs fs;
    struct statvfs flags;
    struct statx root;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC;
    if (cloexec(fd) < 0) return -1;
    int mode = fcntl(fd, F_GETFL);
    if (mode < 0) return -1;
    if (!(mode & O_PATH)) return refuse(EXDEV);
    if (fstatfs(fd, &fs) < 0 || fstatvfs(fd, &flags) < 0
            || sample(fd, "", lookup | AT_EMPTY_PATH, node_mask | STATX_UID | STATX_GID, &root) < 0) return -1;
    if ((unsigned long)fs.f_type != EROFS_SUPER_MAGIC_V1 || (flags.f_flag & required) != required
            || !S_ISDIR(root.stx_mode) || root.stx_uid || root.stx_gid || (root.stx_mode & 0022)
            || !(root.stx_attributes_mask & root.stx_attributes & STATX_ATTR_MOUNT_ROOT)
            || root.stx_dev_major || !root.stx_dev_minor) return refuse(EXDEV);
    *value = (struct gtfm_identity){root.stx_mnt_id, root.stx_ino, root.stx_dev_major, root.stx_dev_minor};
    return 0;
}

static void close_cell(struct gtfm_owner *owner, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
}

int gtfm_create(struct gtfm_owner **out, int verified_image_fd, int proc_fd) {
    if (!out || *out || verified_image_fd < 0 || proc_fd < 0 || verified_image_fd == proc_fd)
        return refuse(EINVAL);
    if (enter() < 0) return -1;
    int result = -1;
    if (one.parent) { errno = EBUSY; goto done; }
    one.parent = getpid();
    one.context_fd = -1;
    one.mount_fd = -1;
    *out = &one;

    char source[64];
    int length = snprintf(source, sizeof(source), "/proc/self/fd/%d", verified_image_fd);
    if (length < 0 || (size_t)length >= sizeof(source)) { errno = EOVERFLOW; goto done; }
    const char *relative = &source[sizeof("/proc")];
    struct statx image, again;
    if (image_sample(verified_image_fd, &image) < 0 || transport(proc_fd, relative, &image) < 0) goto done;

    int context = (int)syscall(SYS_fsopen, "erofs", FSOPEN_CLOEXEC);
    if (context < 0) goto done;
    one.context_fd = context;
    if (cloexec(context) < 0
            || syscall(SYS_fsconfig, context, FSCONFIG_SET_STRING, "source", source, 0) < 0
            || syscall(SYS_fsconfig, context, FSCONFIG_CMD_CREATE, NULL, NULL, 0) < 0) goto done;
    int mount = (int)syscall(SYS_fsmount, context, FSMOUNT_CLOEXEC,
                            MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV | MOUNT_ATTR_NOEXEC);
    if (mount < 0) goto done;
    one.mount_fd = mount;
    close_cell(&one, &one.context_fd);
    if (one.close_error) { errno = one.close_error; goto done; }
    if (mount_sample(mount, &one.identity) < 0 || image_sample(verified_image_fd, &again) < 0) goto done;
    if (!same_image(&image, &again) || one.identity.mount_id == image.stx_mnt_id) {
        errno = ESTALE;
        goto done;
    }
    if (transport(proc_fd, relative, &again) < 0) goto done;
    one.ready = 1;
    result = 0;
done:
    leave();
    return result;
}

int gtfm_borrow_root(struct gtfm_owner *owner, struct gtfm_identity *out) {
    if (!out) return refuse(EINVAL);
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    struct gtfm_identity current;
    if (!owner->ready) { errno = ENODEV; goto done; }
    if (mount_sample(owner->mount_fd, &current) < 0) {
        owner->ready = 0;
        goto done;
    }
    const struct gtfm_identity *expected = &owner->identity;
    if (current.mount_id != expected->mount_id || current.root_inode != expected->root_inode
            || current.device_major != expected->device_major || current.device_minor != expected->device_minor) {
        owner->ready = 0;
        errno = ESTALE;
        goto done;
    }
    *out = current;
    result = owner->mount_fd;
done:
    leave();
    return result;
}

int gtfm_close(struct gtfm_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    owner->ready = 0;
    close_cell(owner, &owner->mount_fd);
    close_cell(owner, &owner->context_fd);
    int error = owner->close_error;
    leave();
    return error ? refuse(error) : 0;
}
