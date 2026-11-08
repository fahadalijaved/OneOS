#define _GNU_SOURCE
#include "guest_zygote_root_entry.h"
#include "guest_readback_identity.h"

#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <sys/ioctl.h>
#include <sys/statfs.h>
#include <unistd.h>

static int check_descriptor(int fd) {
    if (fd < 5) return guest_readback_refuse(EINVAL);
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : guest_readback_refuse(EPERM);
}

static int namespace_identity(int fd, struct stat *identity) {
    struct statfs fs;
    if (check_descriptor(fd) < 0 || fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !identity->st_ino) return guest_readback_refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : guest_readback_refuse(EXDEV);
}

static int same_namespace(const struct stat *first, const struct stat *second) {
    return first->st_dev == second->st_dev && first->st_ino == second->st_ino;
}

static int check_current_namespace(const struct stat *expected) {
    struct stat actual;
    if (stat("/proc/self/ns/mnt", &actual) < 0) return -1;
    return same_namespace(&actual, expected) ? 0 : guest_readback_refuse(EXDEV);
}

static int root_identity(int fd, uint64_t mount_id, struct statx *identity) {
    if (check_descriptor(fd) < 0 || guest_readback_stat(fd, "", identity) < 0) return -1;
    if (!S_ISDIR(identity->stx_mode)) return guest_readback_refuse(ENOTDIR);
    return identity->stx_mnt_id == mount_id ? 0 : guest_readback_refuse(EXDEV);
}

static int check_named_root(const char *name, const struct statx *held) {
    struct statx actual;
    if (guest_readback_stat(AT_FDCWD, name, &actual) < 0) return -1;
    return guest_readback_same_node(&actual, held) ? 0 : guest_readback_refuse(EXDEV);
}

int guest_zygote_enter_root(const struct guest_zygote_root_view *view,
        struct guest_zygote_root_entry *entry) {
    if (!view || !entry) return guest_readback_refuse(EINVAL);
    if (entry->state != GUEST_ZYGOTE_ROOT_NEW) return guest_readback_refuse(EALREADY);
    if (!view->inherited_root_mount_id || !view->guest_root_mount_id
            || view->inherited_root_mount_id == view->guest_root_mount_id)
        return guest_readback_refuse(EINVAL);

    struct stat parent_ns, private_ns;
    if (namespace_identity(view->parent_namespace_fd, &parent_ns) < 0
            || namespace_identity(view->private_namespace_fd, &private_ns) < 0) return -1;
    if (same_namespace(&parent_ns, &private_ns)) return guest_readback_refuse(EXDEV);

    struct statx inherited, guest;
    if (root_identity(view->inherited_root_fd, view->inherited_root_mount_id, &inherited) < 0
            || root_identity(view->guest_root_fd, view->guest_root_mount_id, &guest) < 0) return -1;
    if (guest.stx_dev_major == inherited.stx_dev_major && guest.stx_dev_minor == inherited.stx_dev_minor)
        return guest_readback_refuse(EXDEV);
    if (check_current_namespace(&private_ns) < 0 || check_named_root("/", &inherited) < 0) return -1;

    entry->state = GUEST_ZYGOTE_ROOT_ENTERING;
    if (fchdir(view->guest_root_fd) < 0
            || check_named_root("/", &inherited) < 0
            || check_named_root(".", &guest) < 0
            || check_current_namespace(&private_ns) < 0
            || chroot(".") < 0
            || chdir("/") < 0
            || check_named_root("/", &guest) < 0
            || check_named_root(".", &guest) < 0) {
        entry->state = GUEST_ZYGOTE_ROOT_RETIRED;
        return -1;
    }
    entry->state = GUEST_ZYGOTE_ROOT_READY;
    return 0;
}
