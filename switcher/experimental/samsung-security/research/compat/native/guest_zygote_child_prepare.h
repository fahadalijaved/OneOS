#ifndef ONEOS_GUEST_ZYGOTE_CHILD_PREPARE_H
#define ONEOS_GUEST_ZYGOTE_CHILD_PREPARE_H

#include "guest_tree_control_owner.h"
#include "guest_zygote_root_entry.h"
#include "guest_zygote_socket_owner.h"
#include "guest_zygote_stdio_owner.h"

enum guest_zygote_child_state {
    GUEST_ZYGOTE_CHILD_NEW,
    GUEST_ZYGOTE_CHILD_PREPARING,
    GUEST_ZYGOTE_CHILD_READY,
    GUEST_ZYGOTE_CHILD_RETIRED,
};

struct guest_zygote_child_owner {
    enum guest_zygote_child_state state;
    struct guest_zygote_root_entry root;
    struct guest_zygote_stdio_owner stdio;
    struct guest_zygote_socket_owner sockets;
};

/* Called only in the exclusive preparation child after its exact parent
 * accepts this view. The child owns its FD table, filesystem state, trusted
 * inherited procfs and stable mount view. Supply the original live child
 * inputs, the admitted view, an owned higher null FD, and a zeroed owner.
 * All of 0-4 must be vacant. The same owner retains partial stdio/socket
 * progress for retirement. It borrows the view and null FD throughout.
 * READY observes only the rooted process, stdio and two private listeners.
 * No control acceptance, executable admission or exec follows here. */
int guest_zygote_child_prepare(const struct gtc_child_inputs *input,
        const struct gtc_child_view *view, int null_fd, struct guest_zygote_child_owner *owner);

#endif
