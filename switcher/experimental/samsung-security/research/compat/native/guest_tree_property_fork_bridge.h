#ifndef ONEOS_GUEST_TREE_PROPERTY_FORK_BRIDGE_H
#define ONEOS_GUEST_TREE_PROPERTY_FORK_BRIDGE_H

#include "guest_tree_property_child.h"
#include "guest_tree_property_seed_source.h"

struct gtpb_owner;

/* Separate prepare-only composition. The fixed stage provider supplies the
 * same owned witness cells and retains its stage and writer exclusion through
 * the actual terminal reap. Keep any nonnull owner even if begin fails. */
int gtpb_begin(struct gtpb_owner **out, int witnesses[GTR_WITNESSES]);
int gtpb_receive_partial(struct gtpb_owner *owner, struct gtc_observation *observed);
int gtpb_request_stop(struct gtpb_owner *owner);
enum gtr_release gtpb_poll_close(struct gtpb_owner *owner);

/* Private calls from the pinned staged owner/verifier. */
int gtpb_prepare_child(const struct gtc_child_inputs *input, struct gtc_child_view *view,
        struct guest_tree_property_seed_source *source, struct guest_tree_property_child **property);
int gtpb_verify_property_files(int property, int *close_error);

#endif
