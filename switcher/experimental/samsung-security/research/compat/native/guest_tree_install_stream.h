#ifndef ONEOS_GUEST_TREE_INSTALL_STREAM_H
#define ONEOS_GUEST_TREE_INSTALL_STREAM_H

#include <errno.h>
#include <sys/socket.h>

static inline int guest_tree_connected_unix_stream(int fd) {
    int type;
    struct sockaddr_storage local, peer;
    socklen_t type_bytes = sizeof(type), local_bytes = sizeof(local), peer_bytes = sizeof(peer);
    if (getsockopt(fd, SOL_SOCKET, SO_TYPE, &type, &type_bytes) < 0
            || getsockname(fd, (struct sockaddr *)&local, &local_bytes) < 0
            || getpeername(fd, (struct sockaddr *)&peer, &peer_bytes) < 0) return -1;
    if (type_bytes != sizeof(type) || type != SOCK_STREAM
            || local_bytes < sizeof(local.ss_family) || local_bytes > sizeof(local)
            || peer_bytes < sizeof(peer.ss_family) || peer_bytes > sizeof(peer)
            || local.ss_family != AF_UNIX || peer.ss_family != AF_UNIX) {
        errno = EPERM;
        return -1;
    }
    return 0;
}

#endif
