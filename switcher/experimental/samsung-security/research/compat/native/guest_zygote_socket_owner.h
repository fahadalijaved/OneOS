#ifndef ONEOS_GUEST_ZYGOTE_SOCKET_OWNER_H
#define ONEOS_GUEST_ZYGOTE_SOCKET_OWNER_H

#include "guest_zygote_socket_readback.h"

struct guest_zygote_socket_parent {
    int root_fd, dev_fd, socket_dir_fd;
    uint64_t root_mount_id, dev_mount_id, host_dev_mount_id;
    uint32_t host_device_major, host_device_minor;
};

enum guest_zygote_socket_state {
    GUEST_ZYGOTE_SOCKETS_NEW,
    GUEST_ZYGOTE_SOCKETS_PREPARING,
    GUEST_ZYGOTE_SOCKETS_READY,
    GUEST_ZYGOTE_SOCKETS_RETIRED,
    GUEST_ZYGOTE_SOCKETS_CLOSED,
};

struct guest_zygote_socket_owner {
    enum guest_zygote_socket_state state;
    int fds[2], node_fd, close_error;
    struct guest_zygote_socket_view view;
};

/* One attempt in the final single-threaded, already-rooted child. The
 * caller owns an independent FD table and filesystem context, the exact
 * private mount and names, and the inherited host dev mount witness from
 * this namespace. It excludes other writers and descriptor changes. Pass a
 * zeroed owner. After acquisition begins, the owner retains every live FD
 * on refusal and the entire private view must be retired. No path is
 * unlinked, no occupied FD is replaced, and READY only admits this pair. */
int guest_zygote_socket_prepare(const struct guest_zygote_socket_parent *parent,
        struct guest_zygote_socket_owner *owner);

/* Consume each owned FD once. A close failure is sticky. The caller must
 * separately drain the child and retire the private mount and its names. */
int guest_zygote_socket_close(struct guest_zygote_socket_owner *owner);

#endif
