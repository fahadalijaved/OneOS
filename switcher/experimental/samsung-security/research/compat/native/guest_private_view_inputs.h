#ifndef ONEOS_GUEST_PRIVATE_VIEW_INPUTS_H
#define ONEOS_GUEST_PRIVATE_VIEW_INPUTS_H
#include "guest_private_view_owner.h"

/* Dedicated one-thread, one-shot supervisor. No path/FD/hash input setters.
 * Existing-stage cached staging freshness only; NOT image authenticity. */
struct gvi_inputs;
struct gvi_observation {
    uint64_t namespace_inode, data_group, mirror_group;
};
enum { GVI_OK=0, GVI_NEED_PREPARED_STAGE=1, GVI_HOLD=2, GVI_LOCAL_RELEASED_KERNEL_UNCONFIRMED=3 };
/* A non-NULL result must be closed even on refusal; cleanup may be uncertain. */
/* Input adoption only: read-only opens/metadata/ioctls, no mount operation. */
int gvi_open_existing(struct gvi_inputs **out);
/* EFFECTFUL: calls the actual gvo fork/unshare/mount preparation path.
 * Stores the actual gvo owner internally even on an after-fork failure.
 * Returns 0 only after gvo_receive_partial, never launch/security readiness. */
int gvi_begin_view(struct gvi_inputs *, struct gvi_observation *);
/* Inputs close only after known gvo local terminal0 (no-own-config refusal)
 * or3 (confirmed AUTO config, child reap and local caps closed). Terminal3
 * remains3 permanently: no kernel unbound/full-return/runtime acceptance.
 * Unknown commit/local close/reap => HOLD with actual inputs retained.
 * No free, raw FD/PID accessor or nested/repeated begin. */
int gvi_close(struct gvi_inputs *);
#endif
