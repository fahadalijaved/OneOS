#ifndef ONEOS_GUEST_TREE_PROPERTY_SEED_SOURCE_H
#define ONEOS_GUEST_TREE_PROPERTY_SEED_SOURCE_H

#include "guest_tree_property_stage.h"

struct guest_tree_property_seed_source;

/* Fixed, linked donor-v1 cohort. Initialize *out to NULL and retain any
 * returned owner through cleanup, even when preparation fails. Use the
 * dedicated root process leader with no competing descriptor-table writers. */
int guest_tree_property_seed_source_prepare(struct guest_tree_property_seed_source **out);

/* In the actual direct fork child, before GTC prepares its private view, the
 * future descriptor restriction must keep an FD only on result 1. Result 0
 * grants no keep, and -1 is a refusal. No relocation, dup, SCM_RIGHTS or exec
 * across this handoff. All five roles stay CLOEXEC.
 *
 * The fixed composition must use this same owner's fork copy as part of its
 * existing child control and witness allowlist, and treat missing cells as
 * failure. The selected socket-only GTC does not call this API. */
int guest_tree_property_seed_source_keep_in_child(struct guest_tree_property_seed_source *owner, int fd);

/* Once in that direct child, move all five exact inherited descriptors into
 * an array initialized to -1. Keep any unconsumed array cells on refusal from
 * guest_tree_property_child_begin. Never reopen or replace a lost cell.
 * The parent's descriptor cells are a separate copy after fork. */
int guest_tree_property_seed_source_take_in_child(struct guest_tree_property_seed_source *owner,
        int seeds[GTP_SEED_COUNT]);

/* Close this process's still-owned descriptor cells once. The parent must
 * close only after it no longer needs to fork the owner, and the child's
 * caller must handle any transferred cells separately. Neither successful
 * local close nor the seals prove a child/namespace drain. */
int guest_tree_property_seed_source_close(struct guest_tree_property_seed_source *owner);

#endif
