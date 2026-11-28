#ifndef ONEOS_GUEST_ZYGOTE_SOCKET_READBACK_H
#define ONEOS_GUEST_ZYGOTE_SOCKET_READBACK_H

#include <stdint.h>

struct guest_zygote_socket_pin {
    uint64_t cookie, inode;
};

struct guest_zygote_socket_view {
    int root_fd, dev_fd, socket_dir_fd;
    uint64_t root_mount_id, dev_mount_id;
    struct guest_zygote_socket_pin zygote, usap;
};

/* Observe the fixed inheritable listener slots 3 and 4 and their names in
 * the held guest dev/socket directory. The owner supplies the private mount
 * and the listener-cookie/path-inode pins from each exclusive creation
 * occurrence. Hold the same root, namespace, descriptors and names through
 * exec. A socket's reported address is not proof of its current VFS binding.
 * This borrows all descriptors and performs no bind, connect or mutation. */
int guest_zygote_validate_sockets(const struct guest_zygote_socket_view *view);

#endif
