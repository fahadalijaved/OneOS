#ifndef ONEOS_GUEST_BINDER_ATTACH_OWNER_H
#define ONEOS_GUEST_BINDER_ATTACH_OWNER_H

#include "guest_binder_context_owner.h"
#include "guest_tree_control_owner.h"
#include "guest_tree_prepare_root.h"

enum guest_binder_attach_state {
    GUEST_BINDER_ATTACH_EMPTY = 0,
    GUEST_BINDER_ATTACH_STARTED,
    GUEST_BINDER_ATTACH_MOVE_ATTEMPTED,
    GUEST_BINDER_ATTACH_NODE_HELD,
    GUEST_BINDER_ATTACH_RETIRED,
    GUEST_BINDER_ATTACH_RETIRED_AFTER_MOVE
};

struct guest_binder_attach_owner {
    enum guest_binder_attach_state state;
    pid_t source_pid;
    int clone_fd, target_fd, attached_fd, close_error;
    uint64_t attached_mount_id;
};

#define GUEST_BINDER_ATTACH_OWNER_INITIALIZER { \
    .clone_fd = -1, .target_fd = -1, .attached_fd = -1 \
}

/*
 * Future fixed tree launch child only, after the existing socket-only view
 * has been admitted and before chroot or guest entry. Borrow its original
 * child input, retained rights and the exact detached creator. The dedicated
 * source child excludes other namespace, directory and descriptor writers.
 * Workspaces must be mutually disjoint and follow the mount parser contract.
 *
 * One attempt per process, including errors. A zero return retains one
 * character-device mount at the fixed guest /dev/binder path. No manager
 * claim, driver open, Binder object, execution or launch admission follows.
 * Retain this owner and the same borrowed resources through teardown.
 */
int guest_binder_attach(struct guest_binder_attach_owner *owner,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created,
        struct guest_tree_mount_scratch before, struct guest_tree_mount_scratch after);

/* Local descriptor retirement only, even after a failed move. The fixed child
 * owner must retain namespace/teardown custody. No unmount, unlink or retry. */
int guest_binder_attach_close(struct guest_binder_attach_owner *owner);

#endif
