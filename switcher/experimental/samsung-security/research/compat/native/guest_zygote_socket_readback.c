#define _GNU_SOURCE
#include "guest_zygote_socket_readback.h"

#include "guest_readback_identity.h"

#include <stddef.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>

enum { ROOT, DEV, SOCKET_DIR, ZYGOTE, USAP, NODES };

static const struct listener {
    int fd;
    const char *name, *address;
} listeners[] = {
    {3, "zygote", "/dev/socket/zygote"},
    {4, "usap_pool_primary", "/dev/socket/usap_pool_primary"},
};

static int check_directory_fd(int fd) {
    if (fd < 0 || fd == listeners[0].fd || fd == listeners[1].fd) return guest_readback_refuse(EINVAL);
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : guest_readback_refuse(EPERM);
}

static int join_directory(int parent, const char *name, int fd, struct statx *held) {
    struct statx named;
    if (guest_readback_stat(fd, "", held) < 0 || guest_readback_stat(parent, name, &named) < 0) return -1;
    if (!guest_readback_same_node(held, &named)) return guest_readback_refuse(ESTALE);
    if (held->stx_mode != (S_IFDIR | 0755) || held->stx_uid || held->stx_gid) return guest_readback_refuse(EPERM);
    return 0;
}

static int snapshot(const struct guest_zygote_socket_view *view, struct statx nodes[NODES]) {
    if (guest_readback_stat(view->root_fd, "", &nodes[ROOT]) < 0
            || join_directory(view->root_fd, "dev", view->dev_fd, &nodes[DEV]) < 0
            || join_directory(view->dev_fd, "socket", view->socket_dir_fd, &nodes[SOCKET_DIR]) < 0) return -1;
    if (!S_ISDIR(nodes[ROOT].stx_mode)) return guest_readback_refuse(EPERM);
    if (nodes[ROOT].stx_mnt_id != view->root_mount_id || nodes[DEV].stx_mnt_id != view->dev_mount_id
            || !guest_readback_same_mount(&nodes[DEV], &nodes[SOCKET_DIR])) return guest_readback_refuse(EXDEV);
    if (nodes[DEV].stx_ino == nodes[SOCKET_DIR].stx_ino) return guest_readback_refuse(EPERM);

    const struct guest_zygote_socket_pin *pins[] = { &view->zygote, &view->usap };
    for (unsigned i = 0; i < sizeof(listeners) / sizeof(listeners[0]); ++i) {
        struct statx *node = &nodes[ZYGOTE + i];
        if (guest_readback_stat(view->socket_dir_fd, listeners[i].name, node) < 0) return -1;
        if (!guest_readback_same_mount(&nodes[SOCKET_DIR], node)) return guest_readback_refuse(EXDEV);
        if (node->stx_mode != (S_IFSOCK | 0660) || node->stx_uid || node->stx_gid != 1000 || node->stx_nlink != 1)
            return guest_readback_refuse(EPERM);
        if (node->stx_ino != pins[i]->inode) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static int expect_int_option(int fd, int option, int expected) {
    int value;
    socklen_t bytes = sizeof(value);
    if (getsockopt(fd, SOL_SOCKET, option, &value, &bytes) < 0) return -1;
    return bytes == sizeof(value) && value == expected ? 0 : guest_readback_refuse(EPROTO);
}

static int check_listener(const struct listener *listener, uint64_t expected_cookie) {
    int fd = listener->fd;
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    if (flags & FD_CLOEXEC) return guest_readback_refuse(EPERM);
    flags = fcntl(fd, F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_ACCMODE | O_NONBLOCK | O_PATH)) != O_RDWR) return guest_readback_refuse(EPERM);
    if (expect_int_option(fd, SO_DOMAIN, AF_UNIX) < 0 || expect_int_option(fd, SO_TYPE, SOCK_STREAM) < 0
            || expect_int_option(fd, SO_PROTOCOL, 0) < 0 || expect_int_option(fd, SO_ACCEPTCONN, 1) < 0) return -1;

    struct sockaddr_un address = {0};
    socklen_t bytes = sizeof(address);
    if (getsockname(fd, (struct sockaddr *)&address, &bytes) < 0) return -1;
    size_t path_bytes = strlen(listener->address) + 1;
    if (bytes != offsetof(struct sockaddr_un, sun_path) + path_bytes || address.sun_family != AF_UNIX
            || memcmp(address.sun_path, listener->address, path_bytes)) return guest_readback_refuse(EPROTO);

    uint64_t cookie;
    bytes = sizeof(cookie);
    if (getsockopt(fd, SOL_SOCKET, SO_COOKIE, &cookie, &bytes) < 0) return -1;
    if (bytes != sizeof(cookie)) return guest_readback_refuse(EPROTO);
    return cookie == expected_cookie ? 0 : guest_readback_refuse(ESTALE);
}

int guest_zygote_validate_sockets(const struct guest_zygote_socket_view *view) {
    if (!view || !view->root_mount_id || !view->dev_mount_id || !view->zygote.cookie || !view->usap.cookie
            || !view->zygote.inode || !view->usap.inode || view->zygote.cookie == view->usap.cookie
            || view->zygote.inode == view->usap.inode || view->root_fd == view->dev_fd
            || view->root_fd == view->socket_dir_fd || view->dev_fd == view->socket_dir_fd)
        return guest_readback_refuse(EINVAL);
    if (view->root_mount_id == view->dev_mount_id) return guest_readback_refuse(EXDEV);
    if (check_directory_fd(view->root_fd) < 0 || check_directory_fd(view->dev_fd) < 0
            || check_directory_fd(view->socket_dir_fd) < 0) return -1;

    struct statx before[NODES], after[NODES];
    if (snapshot(view, before) < 0 || check_listener(&listeners[0], view->zygote.cookie) < 0
            || check_listener(&listeners[1], view->usap.cookie) < 0 || snapshot(view, after) < 0) return -1;
    for (unsigned i = 0; i < NODES; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    if (check_listener(&listeners[0], view->zygote.cookie) < 0) return -1;
    return check_listener(&listeners[1], view->usap.cookie);
}
