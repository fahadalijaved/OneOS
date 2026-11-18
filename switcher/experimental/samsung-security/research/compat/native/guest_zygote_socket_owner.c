#define _GNU_SOURCE
#include "guest_zygote_socket_owner.h"

#include "guest_readback_identity.h"
#include "guest_zygote_stdio.h"

#include <linux/magic.h>
#include <stddef.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/un.h>
#include <unistd.h>

enum { FIRST_SLOT = 3, LISTENER_COUNT = 2, BACKLOG = 10 };

static const struct endpoint {
    const char *name, *address;
} endpoints[LISTENER_COUNT] = {
    {"zygote", "/dev/socket/zygote"},
    {"usap_pool_primary", "/dev/socket/usap_pool_primary"},
};

static int check_directory(int parent, const char *name, int fd, struct statx *held) {
    struct statx named;
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    if (guest_readback_stat(fd, "", held) < 0 || guest_readback_stat(parent, name, &named) < 0) return -1;
    if (!guest_readback_same_node(held, &named)) return guest_readback_refuse(ESTALE);
    return held->stx_mode == (S_IFDIR | 0755) && !held->stx_uid && !held->stx_gid
            ? 0 : guest_readback_refuse(EPERM);
}

static int check_root(const struct guest_zygote_socket_parent *parent, struct statx *socket_dir) {
    struct statx root, dev;
    if (check_directory(AT_FDCWD, "/", parent->root_fd, &root) < 0
            || check_directory(parent->root_fd, "dev", parent->dev_fd, &dev) < 0
            || check_directory(parent->dev_fd, "socket", parent->socket_dir_fd, socket_dir) < 0) return -1;
    if (root.stx_mnt_id != parent->root_mount_id || dev.stx_mnt_id != parent->dev_mount_id
            || !guest_readback_same_mount(&dev, socket_dir) || dev.stx_ino == socket_dir->stx_ino)
        return guest_readback_refuse(EXDEV);
    if (dev.stx_dev_major == parent->host_device_major && dev.stx_dev_minor == parent->host_device_minor)
        return guest_readback_refuse(EXDEV);
    struct statfs fs;
    struct statvfs flags;
    if (fstatfs(parent->dev_fd, &fs) < 0 || fstatvfs(parent->dev_fd, &flags) < 0) return -1;
    const unsigned long selected = ST_NOSUID | ST_NODEV | ST_NOEXEC;
    return fs.f_type == TMPFS_MAGIC && (flags.f_flag & (selected | ST_RDONLY)) == selected
            ? 0 : guest_readback_refuse(EXDEV);
}

static int require_absent(int directory, const char *name) {
    struct statx node;
    if (guest_readback_stat(directory, name, &node) == 0) return guest_readback_refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int require_free_fd(int fd) {
    if (fcntl(fd, F_GETFD) >= 0) return guest_readback_refuse(EBUSY);
    return errno == EBADF ? 0 : -1;
}

static int close_once(int *fd, int *error) {
    int owned = *fd;
    *fd = -1;
    if (owned < 0 || close(owned) == 0) return 0;
    if (!*error) *error = errno ? errno : EIO;
    return guest_readback_refuse(*error);
}

static int socket_node(int directory, const char *name, int fd, const struct statx *parent, struct statx *node) {
    struct statx named;
    if (guest_readback_stat(fd, "", node) < 0 || guest_readback_stat(directory, name, &named) < 0) return -1;
    if (!guest_readback_same_node(node, &named)) return guest_readback_refuse(ESTALE);
    if (!guest_readback_same_mount(parent, node)) return guest_readback_refuse(EXDEV);
    return node->stx_mode == (S_IFSOCK | 0660) && !node->stx_uid && node->stx_nlink == 1
            ? 0 : guest_readback_refuse(EPERM);
}

static int bind_listener(const struct guest_zygote_socket_parent *parent, struct guest_zygote_socket_owner *owner,
        unsigned index, struct guest_zygote_socket_pin *pin) {
    const struct endpoint *endpoint = &endpoints[index];
    int fd = owner->fds[index];
    struct statx directory;
    if (check_root(parent, &directory) < 0 || require_absent(parent->socket_dir_fd, endpoint->name) < 0) return -1;

    struct sockaddr_un address = { .sun_family = AF_UNIX };
    size_t name_bytes = strlen(endpoint->address) + 1;
    memcpy(address.sun_path, endpoint->address, name_bytes);
    mode_t previous = umask(0117);
    int result = bind(fd, (const struct sockaddr *)&address,
                (socklen_t)(offsetof(struct sockaddr_un, sun_path) + name_bytes));
    int bind_error = errno;
    umask(previous);
    if (result < 0) return guest_readback_refuse(bind_error);

    owner->node_fd = openat(parent->socket_dir_fd, endpoint->name, O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (owner->node_fd < 0) return -1;
    struct statx before, after;
    if (check_root(parent, &directory) < 0
            || socket_node(parent->socket_dir_fd, endpoint->name, owner->node_fd, &directory, &before) < 0
            || fchownat(owner->node_fd, "", (uid_t)-1, 1000, AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW) < 0
            || socket_node(parent->socket_dir_fd, endpoint->name, owner->node_fd, &directory, &after) < 0) return -1;
    if (before.stx_ino != after.stx_ino) return guest_readback_refuse(ESTALE);
    if (after.stx_gid != 1000) return guest_readback_refuse(EPERM);
    if (close_once(&owner->node_fd, &owner->close_error) < 0 || listen(fd, BACKLOG) < 0) return -1;

    uint64_t cookie;
    socklen_t bytes = sizeof(cookie);
    if (getsockopt(fd, SOL_SOCKET, SO_COOKIE, &cookie, &bytes) < 0) return -1;
    if (bytes != sizeof(cookie) || !cookie) return guest_readback_refuse(EPROTO);
    *pin = (struct guest_zygote_socket_pin) { .cookie = cookie, .inode = after.stx_ino };
    return 0;
}

int guest_zygote_socket_prepare(const struct guest_zygote_socket_parent *parent,
        struct guest_zygote_socket_owner *owner) {
    if (!parent || !owner || owner->state != GUEST_ZYGOTE_SOCKETS_NEW
            || parent->root_fd < 5 || parent->dev_fd < 5 || parent->socket_dir_fd < 5
            || parent->root_fd == parent->dev_fd || parent->root_fd == parent->socket_dir_fd
            || parent->dev_fd == parent->socket_dir_fd || !parent->root_mount_id || !parent->dev_mount_id
            || !parent->host_dev_mount_id || (!parent->host_device_major && !parent->host_device_minor))
        return guest_readback_refuse(EINVAL);
    if (parent->root_mount_id == parent->dev_mount_id || parent->host_dev_mount_id == parent->dev_mount_id)
        return guest_readback_refuse(EXDEV);
    struct statx directory;
    if (check_root(parent, &directory) < 0 || oneos_guest_zygote_stdio_validate() < 0
            || require_free_fd(FIRST_SLOT) < 0 || require_free_fd(FIRST_SLOT + 1) < 0
            || require_absent(parent->socket_dir_fd, endpoints[0].name) < 0
            || require_absent(parent->socket_dir_fd, endpoints[1].name) < 0) return -1;

    *owner = (struct guest_zygote_socket_owner) {
        .state = GUEST_ZYGOTE_SOCKETS_PREPARING, .fds = {-1, -1}, .node_fd = -1,
    };
    for (unsigned i = 0; i < LISTENER_COUNT; ++i) {
        owner->fds[i] = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
        if (owner->fds[i] < 0) goto retire;
        if (owner->fds[i] != FIRST_SLOT + (int)i) {
            errno = ESTALE;
            goto retire;
        }
    }
    struct guest_zygote_socket_view view = {
        .root_fd = parent->root_fd, .dev_fd = parent->dev_fd, .socket_dir_fd = parent->socket_dir_fd,
        .root_mount_id = parent->root_mount_id, .dev_mount_id = parent->dev_mount_id,
    };
    if (bind_listener(parent, owner, 0, &view.zygote) < 0 || bind_listener(parent, owner, 1, &view.usap) < 0
            || check_root(parent, &directory) < 0 || fcntl(owner->fds[0], F_SETFD, 0) < 0
            || fcntl(owner->fds[1], F_SETFD, 0) < 0 || guest_zygote_validate_sockets(&view) < 0) goto retire;
    owner->view = view;
    owner->state = GUEST_ZYGOTE_SOCKETS_READY;
    return 0;

retire:
    owner->state = GUEST_ZYGOTE_SOCKETS_RETIRED;
    return -1;
}

int guest_zygote_socket_close(struct guest_zygote_socket_owner *owner) {
    if (!owner || owner->state == GUEST_ZYGOTE_SOCKETS_NEW) return guest_readback_refuse(EINVAL);
    if (owner->state == GUEST_ZYGOTE_SOCKETS_PREPARING) return guest_readback_refuse(EBUSY);
    if (owner->state != GUEST_ZYGOTE_SOCKETS_CLOSED) {
        owner->state = GUEST_ZYGOTE_SOCKETS_CLOSED;
        close_once(&owner->node_fd, &owner->close_error);
        for (unsigned i = 0; i < LISTENER_COUNT; ++i) close_once(&owner->fds[i], &owner->close_error);
    }
    return owner->close_error ? guest_readback_refuse(owner->close_error) : 0;
}
