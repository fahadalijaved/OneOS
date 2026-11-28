#ifndef ONEOS_GUEST_CORE_APEX_BACKING_H
#define ONEOS_GUEST_CORE_APEX_BACKING_H

#include "guest_core_apex_owner.h"
#include "guest_tree_stage_provider.h"

struct guest_core_apex_files;

/*
 * Fixed GTSP source stage. Requires the actual current guard and stage/tree
 * witnesses. Opens art_payload.img, i18n_payload.img and runtime_payload.img
 * inside that same read-only EROFS backing mount and verifies their complete
 * contents. Initialize *out to NULL and retain a nonnull owner after refusal.
 * This does not replace the existing whole-tree content admission.
 */
int guest_core_apex_open_files(const struct gtsp_stage_witnesses *stage,
                              struct guest_core_apex_files **out);

/*
 * One transfer of owned read-only duplicates, ordered by guest_core_apex_role.
 * All output cells must start at -1. Failure publishes no FD and leaves all
 * partial acquisitions with files. Success transfers the descriptors to the
 * actual subsequent loop/child owner. The source owner and original stage
 * guard must remain retained until that work has drained.
 */
int guest_core_apex_take_payloads(struct guest_core_apex_files *files, int out[GCA_COUNT]);

/*
 * Close locally owned descriptors once. Available after open/transfer refusal
 * or after the actual downstream owner drains. No guard finish, file change,
 * loop configuration, mount, activation, or release proof.
 */
int guest_core_apex_close_files(struct guest_core_apex_files *files);

#endif
