#ifndef ONEOS_GUEST_BINDER_CONTEXT_OWNER_H
#define ONEOS_GUEST_BINDER_CONTEXT_OWNER_H

#include <stdint.h>
#include <sys/types.h>

enum guest_binder_context_state {
    GUEST_BINDER_CONTEXT_EMPTY = 0,
    GUEST_BINDER_CONTEXT_STARTED,
    GUEST_BINDER_CONTEXT_ADD_ATTEMPTED,
    GUEST_BINDER_CONTEXT_DEVICE_HELD,
    GUEST_BINDER_CONTEXT_RETIRED
};

struct guest_binder_context_owner {
    enum guest_binder_context_state state;
    pid_t source_pid;
    int namespace_fd, fs_context_fd, mount_fd, control_fd, device_fd;
    int close_error;
    uint32_t device_major, device_minor;
    uint64_t device_inode, device_mount_id;
};

#define GUEST_BINDER_CONTEXT_OWNER_INITIALIZER { \
    .namespace_fd = -1, .fs_context_fd = -1, .mount_fd = -1, \
    .control_fd = -1, .device_fd = -1 \
}

/*
 * Fixed dedicated launch-child source only, before chroot and Binder startup.
 * Borrow its actual parent and current mount namespace FDs and a retained O_PATH
 * witness of the actual host binderfs /dev/binderfs/binder node. The caller owns
 * their provenance and lifetime. An fd or numeric identity grants no authority.
 *
 * One attempt per process. Retain the same owner on success or failure. Success
 * holds a detached binderfs mount and one newly created O_PATH device on it.
 * This call does not attach a mount, open a Binder client, or claim a manager.
 * The eventual selected manager must prove the same device on its own fresh
 * Binder open and positively claim it in its actual owning process.
 */
int guest_binder_context_create(struct guest_binder_context_owner *owner,
        int parent_namespace_fd, int child_namespace_fd, int host_binder_fd);

/* Consumes each local descriptor once. A failed close is sticky. A return of
 * zero describes local close only, with no claim about external references or
 * release of a context used by a later owner. No reinitialization or retry. */
int guest_binder_context_close(struct guest_binder_context_owner *owner);

#endif
