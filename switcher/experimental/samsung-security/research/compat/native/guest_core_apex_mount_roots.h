#ifndef ONEOS_GUEST_CORE_APEX_MOUNT_ROOTS_H
#define ONEOS_GUEST_CORE_APEX_MOUNT_ROOTS_H

#include "guest_core_apex_loop_owner.h"

struct guest_core_apex_mount_roots;

enum guest_core_apex_mount_release {
    GCA_MOUNT_HOLD = 1,
    GCA_MOUNT_NO_CREATE_LOCAL_CLOSED = 2,
    GCA_MOUNT_LOCAL_CLOSED_KERNEL_UNCONFIRMED = 3
};

/* Dedicated root controller, with its original mount namespace and live
 * source/loop/guard ownership. One attempt. Initialize *out to NULL and
 * retain the published owner even on refusal. Creates only detached roots. */
int guest_core_apex_mount_begin(struct guest_core_apex_loop_owner *loop,
        int controller_namespace_fd, struct guest_core_apex_mount_roots **out);

/* All output FD cells must start at -1. Lends exact same-payload backing once,
 * triples after rechecking the current loop owner and all detached roots.
 * A subsequent child owner must attach and read back its own mountinfo rows
 * before it may pass those rows to guest_core_apex_stage. */
int guest_core_apex_mount_borrow(struct guest_core_apex_mount_roots *owner,
        struct guest_core_apex_backing out[GCA_COUNT]);

/* Close once, only before borrow or after actual downstream drain. Local
 * closure does not prove kernel superblock release or loop detach. Keeps a
 * sticky HOLD on uncertainty, and never closes the original loop owner. */
enum guest_core_apex_mount_release guest_core_apex_mount_close(struct guest_core_apex_mount_roots *owner);

#endif
