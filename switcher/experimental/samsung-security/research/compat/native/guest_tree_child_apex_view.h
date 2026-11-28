#ifndef ONEOS_GUEST_TREE_CHILD_APEX_VIEW_H
#define ONEOS_GUEST_TREE_CHILD_APEX_VIEW_H

#include "guest_tree_control_owner.h"
#include "guest_tree_prepare_root.h"

struct guest_tree_child_apex_view {
    struct guest_tree_root_preparation prepared;
    pid_t parent, child;
    int parent_namespace_fd, child_namespace_fd;
};

#define GUEST_TREE_CHILD_APEX_VIEW_INIT { \
    .prepared = {.attachment = {.clone_fd = -1}, .readback = {.root_fd = -1}}, \
    .parent_namespace_fd = -1, .child_namespace_fd = -1, \
}

/* Private staged variant of the original child constructor. Use once in
 * the actual dedicated GTR fork child after the fixed inherited-FD restriction
 * and parent-death setup. Initialize every view right to -1 and the retained
 * output with GUEST_TREE_CHILD_APEX_VIEW_INIT. Both outputs commit only after
 * the original view observation succeeds. Refusal leaves their input cells
 * intact and any acquired references owned by the same child until its exit.
 *
 * The prepared root/clone FDs and both namespace FDs are borrowed from
 * that original occurrence. The root FD and child namespace FD are exactly
 * the two corresponding view rights, without duplication or FD transport.
 * Keep the actual child and provider witnesses held through any later phase.
 * The record alone grants no APEX action, mount, recovery, or guest entry. */
int guest_tree_prepare_child_apex_view(const struct gtc_child_inputs *input,
        struct gtc_child_view *view, struct guest_tree_child_apex_view *retained);

#endif
