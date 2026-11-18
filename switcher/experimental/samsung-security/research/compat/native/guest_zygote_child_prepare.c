#define _GNU_SOURCE
#include "guest_zygote_child_prepare.h"

#include "guest_readback_identity.h"
#include "guest_zygote_stdio.h"

#include <unistd.h>

static int check_parent(pid_t expected) {
    return getppid() == expected ? 0 : guest_readback_refuse(ECHILD);
}

static int check_launch_slots(void) {
    for (int fd = 0; fd < 5; ++fd) {
        if (fcntl(fd, F_GETFD) >= 0) return guest_readback_refuse(EBUSY);
        if (errno != EBADF) return -1;
    }
    return 0;
}

static int read_inherited_dev(int inherited_root, int null_fd, struct statx *dev) {
    struct statx named_null, held_null;
    if (guest_readback_stat(inherited_root, "dev", dev) < 0) return -1;
    if (!S_ISDIR(dev->stx_mode)) return guest_readback_refuse(ENOTDIR);
    if (guest_readback_stat(inherited_root, "dev/null", &named_null) < 0
            || guest_readback_stat(null_fd, "", &held_null) < 0) return -1;
    if (!guest_readback_same_node(&named_null, &held_null) || !guest_readback_same_mount(dev, &held_null))
        return guest_readback_refuse(EXDEV);
    if (!S_ISCHR(held_null.stx_mode) || held_null.stx_rdev_major != 1 || held_null.stx_rdev_minor != 3)
        return guest_readback_refuse(ENODEV);
    int flags = fcntl(null_fd, F_GETFD);
    if (flags < 0) return -1;
    int status = fcntl(null_fd, F_GETFL);
    if (status < 0) return -1;
    return (flags & FD_CLOEXEC) && !(status & O_PATH) && (status & O_ACCMODE) == O_RDWR
            ? 0 : guest_readback_refuse(EPERM);
}

int guest_zygote_child_prepare(const struct gtc_child_inputs *input,
        const struct gtc_child_view *view, int null_fd, struct guest_zygote_child_owner *owner) {
    if (!input || !input->witnesses || input->parent <= 1 || !view || null_fd < 5 || !owner)
        return guest_readback_refuse(EINVAL);
    if (owner->state != GUEST_ZYGOTE_CHILD_NEW) return guest_readback_refuse(EALREADY);
    if (owner->root.state != GUEST_ZYGOTE_ROOT_NEW || owner->stdio.state != GUEST_ZYGOTE_STDIO_NEW
            || owner->sockets.state != GUEST_ZYGOTE_SOCKETS_NEW) return guest_readback_refuse(EINVAL);

    const uint64_t *mounts = view->observation.mounts;
    if (!mounts[GTC_DEV] || mounts[GTC_DEV] != mounts[GTC_SOCKET]) return guest_readback_refuse(EXDEV);
    for (unsigned i = 0; i < GTR_VIEW_RIGHTS; ++i) {
        if (view->rights[i] < 5 || view->rights[i] == null_fd) return guest_readback_refuse(EINVAL);
    }

    struct statx inherited_dev;
    if (check_parent(input->parent) < 0 || check_launch_slots() < 0
            || read_inherited_dev(view->rights[GTC_INHERITED_ROOT], null_fd, &inherited_dev) < 0) return -1;
    if (mounts[GTC_DEV] == inherited_dev.stx_mnt_id) return guest_readback_refuse(EXDEV);

    struct guest_zygote_root_view root = {
        .parent_namespace_fd = input->witnesses[GTC_PARENT_NAMESPACE],
        .private_namespace_fd = view->rights[GTC_NAMESPACE],
        .inherited_root_fd = view->rights[GTC_INHERITED_ROOT],
        .guest_root_fd = view->rights[GTC_GUEST_ROOT],
        .inherited_root_mount_id = mounts[GTC_INHERITED_ROOT],
        .guest_root_mount_id = mounts[GTC_GUEST_ROOT],
    };
    struct guest_zygote_socket_parent sockets = {
        .root_fd = root.guest_root_fd,
        .dev_fd = view->rights[GTC_DEV],
        .socket_dir_fd = view->rights[GTC_SOCKET],
        .root_mount_id = root.guest_root_mount_id,
        .dev_mount_id = mounts[GTC_DEV],
        .host_dev_mount_id = inherited_dev.stx_mnt_id,
        .host_device_major = inherited_dev.stx_dev_major,
        .host_device_minor = inherited_dev.stx_dev_minor,
    };
    owner->state = GUEST_ZYGOTE_CHILD_PREPARING;
    if (guest_zygote_enter_root(&root, &owner->root) < 0
            || check_parent(input->parent) < 0
            || guest_zygote_stdio_install(null_fd, &owner->stdio) < 0
            || guest_zygote_socket_prepare(&sockets, &owner->sockets) < 0
            || oneos_guest_zygote_stdio_validate() < 0
            || check_parent(input->parent) < 0) {
        owner->state = GUEST_ZYGOTE_CHILD_RETIRED;
        return -1;
    }
    owner->state = GUEST_ZYGOTE_CHILD_READY;
    return 0;
}
