#ifndef ONEOS_GUEST_TREE_STAGE_GUARD_H
#define ONEOS_GUEST_TREE_STAGE_GUARD_H

#include "guest_tree_control_owner.h"

#define GUEST_TREE_GUARD_PATH "/dev/oneos-retained-viewprep"

struct guest_tree_stage_guard;

/*
 * Dedicated controller main thread, one attempt per process. Requires the
 * existing protected guard directory and lease. Publishes the actual owner
 * before acquiring FDs or creating its negative marker. Retain a nonnull
 * result even after refusal.
 */
int guest_tree_stage_guard_acquire(struct guest_tree_stage_guard **out);

/* Check the same retained lease and marker before using the stage. */
int guest_tree_stage_guard_check(struct guest_tree_stage_guard *guard);

/*
 * Arm before the actual fixed GTC begin. The guard retains its exact control
 * owner on success or refusal. The provider borrows it for receive and stop.
 * Witness transfer follows gtc_begin.
 */
int guest_tree_stage_guard_begin(struct guest_tree_stage_guard *guard,
        struct gtc_owner **out, int witnesses[GTR_WITNESSES]);

/* Progress only the exact armed control owner during cleanup. A zero result
 * records its verified local terminal. The currentness check never polls. */
int guest_tree_stage_guard_poll_control(struct guest_tree_stage_guard *guard);

/*
 * Fixed provider only, after every provider-owned stage FD closed successfully.
 * An armed guard requires its exact retained control owner's tree-local
 * release after a successful begin, or proved no-child local closure after
 * a failed begin. Zero describes local guard cleanup only. A refusal preserves
 * the negative and any remaining custody.
 */
int guest_tree_stage_guard_finish(struct guest_tree_stage_guard *guard);

#endif
