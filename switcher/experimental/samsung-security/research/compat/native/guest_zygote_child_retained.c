#include "guest_zygote_child_retained.h"

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

enum { FIRST_RETAINED = 5, FD_COUNT = 1 + GTR_WITNESSES + GTR_VIEW_RIGHTS };

static int refuse(int error) {
    errno = error;
    return -1;
}

static int check_scope(const struct gtc_child_view *view, const struct guest_zygote_child_owner *entry) {
    if (entry->state != GUEST_ZYGOTE_CHILD_READY || entry->root.state != GUEST_ZYGOTE_ROOT_READY
            || entry->stdio.state != GUEST_ZYGOTE_STDIO_READY || entry->sockets.state != GUEST_ZYGOTE_SOCKETS_READY)
        return refuse(EPERM);
    if (entry->stdio.installed != 7 || entry->sockets.fds[0] != 3 || entry->sockets.fds[1] != 4
            || entry->sockets.node_fd != -1 || entry->sockets.close_error)
        return refuse(ESTALE);
    const struct guest_zygote_socket_view *socket = &entry->sockets.view;
    const uint64_t *mounts = view->observation.mounts;
    if (socket->root_fd != view->rights[GTC_GUEST_ROOT] || socket->dev_fd != view->rights[GTC_DEV]
            || socket->socket_dir_fd != view->rights[GTC_SOCKET] || !socket->root_mount_id || !socket->dev_mount_id
            || socket->root_mount_id != mounts[GTC_GUEST_ROOT] || socket->dev_mount_id != mounts[GTC_DEV]
            || socket->dev_mount_id != mounts[GTC_SOCKET]) return refuse(ESTALE);
    return 0;
}

static int check_fds(const struct guest_zygote_control_fds *fds, const struct gtc_child_view *view) {
    int originals[FD_COUNT] = {fds->control};
    memcpy(originals + 1, fds->witnesses, sizeof(fds->witnesses));
    memcpy(originals + 1 + GTR_WITNESSES, view->rights, sizeof(view->rights));
    for (size_t i = 0; i < FD_COUNT; ++i) {
        if (originals[i] < FIRST_RETAINED) return refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (originals[i] == originals[j]) return refuse(EINVAL);
        }
        int flags = fcntl(originals[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return refuse(EPERM);
    }
    return 0;
}

int guest_zygote_retire_inherited_view(struct guest_zygote_control_fds *fds,
        struct gtc_child_view *view, const struct guest_zygote_child_owner *entry) {
    if (!fds || !view || !entry) return refuse(EINVAL);
    if (check_scope(view, entry) < 0 || check_fds(fds, view) < 0) return -1;

    int *const retiring[] = {
        &view->rights[GTC_INHERITED_ROOT], &view->rights[GTC_NAMESPACE],
        &view->rights[GTC_DATA], &view->rights[GTC_MIRROR],
        &fds->witnesses[GTC_TREE], &fds->witnesses[GTC_PRIVATE_DATA], &fds->witnesses[GTC_PARENT_NAMESPACE],
    };
    for (size_t i = 0; i < sizeof(retiring) / sizeof(retiring[0]); ++i) {
        int fd = *retiring[i];
        *retiring[i] = -1;
        if (close(fd) < 0) return -1;
    }
    return 0;
}
