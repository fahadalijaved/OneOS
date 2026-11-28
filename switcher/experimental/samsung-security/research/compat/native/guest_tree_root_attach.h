#ifndef ONEOS_GUEST_TREE_ROOT_ATTACH_H
#define ONEOS_GUEST_TREE_ROOT_ATTACH_H

enum guest_tree_attach_state {
    GUEST_TREE_ATTACH_EMPTY = 0,
    GUEST_TREE_ATTACH_CLONE_HELD,
    GUEST_TREE_ATTACH_MOVE_ATTEMPTED,
    GUEST_TREE_ATTACH_MOVE_RETURNED
};

struct guest_tree_attachment {
    int clone_fd;
    enum guest_tree_attach_state state;
};

/* Called once in the actual isolated preparation child after admitting its
 * namespace, reopened tree source, and exact fresh scaffold destination.
 * Both directory FDs are borrowed. Set attachment to {-1, EMPTY} before use.
 * A returned clone FD belongs to the existing child owner even on failure.
 * MOVE_RETURNED still needs post-move mount and reopened-root verification.
 * Closing the clone FD alone does not release an attached mount. */
int guest_tree_attach_root(int source_fd, int target_fd,
                           struct guest_tree_attachment *attachment);

#endif
