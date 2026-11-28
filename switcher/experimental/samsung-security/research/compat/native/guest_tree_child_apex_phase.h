#ifndef ONEOS_GUEST_TREE_CHILD_APEX_PHASE_H
#define ONEOS_GUEST_TREE_CHILD_APEX_PHASE_H

#include "guest_core_apex_child_attach.h"
#include "guest_tree_child_apex_view.h"
#include "guest_tree_property_child.h"

/* Fixed v5 action in the actual direct child after the controller has
 * authenticated and consumed its one APEX request. Pass the original
 * retained child-view record, live property owner and inherited APEX source
 * owner from this same fork. All three are borrowed through child exit.
 *
 * Zero follows actual sibling attachment, the exact three backing loans,
 * the final six-alias stage and a fresh property/child view recheck. No
 * new wire data or rights. Any refusal is terminal for the action. The
 * caller cuts off and drains the same child on failure, including after a
 * possibly successful mount. This API never closes a borrowed reference. */
int guest_tree_child_apex_phase(const struct guest_tree_child_apex_view *view,
        struct guest_tree_property_child *property, struct guest_core_apex_child_sources *sources);

#endif
