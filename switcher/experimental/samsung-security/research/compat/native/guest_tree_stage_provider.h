#ifndef ONEOS_GUEST_TREE_STAGE_PROVIDER_H
#define ONEOS_GUEST_TREE_STAGE_PROVIDER_H

#include "guest_tree_control_owner.h"

struct guest_tree_stage_guard;
struct gtsp_owner;

enum gtsp_release {
    GTSP_HOLD = 1,
    GTSP_NEVER_BEGAN_LOCAL_CLOSED = 2,
    GTSP_TREE_LOCAL_RELEASED = 4
};

struct gtsp_stage_witnesses {
    int stage_fd, tree_fd, data_fd, parent_namespace_fd;
    struct guest_tree_stage_guard *guard;
};

/*
 * Deliberate strong link prerequisite. Admit the complete actual tree
 * content and writer exclusion for these exact borrowed descriptors under
 * this retained guard. No FD transfer, side effects, caller-provided pass,
 * pathname substitute, or text receipt as authority. Returning zero must
 * bind the actual pre-existing writer exclusion across this guard lifetime.
 * Repeated checks must refer to the same content generation. No runnable
 * tree provider can link until the real cohort supplies this implementation.
 */
int guest_tree_admit_stage_contents(const struct gtsp_stage_witnesses *witnesses);

/*
 * Fixed sibling stage, one attempt on the dedicated root controller thread.
 * Caller initializes *out to NULL. Retain a nonnull result even on refusal.
 * Opens and retains the actual guard and no-follow directory witnesses.
 */
int gtsp_open_existing(struct gtsp_owner **out);

/* The same guard admits the fixed GTC child once. A positive reply describes
 * the retained partial view after actual source, content and guard rechecks. */
int gtsp_begin_view(struct gtsp_owner *owner, struct gtc_observation *observed);

/* Cut off the same attempt; this only requests its actual child drain. */
int gtsp_request_stop(struct gtsp_owner *owner);

/*
 * Nonblocking child poll. After actual tree-local child release, confirm
 * the same stage/content/guard and close every provider source before exact
 * guard finish. Armed no-rights, drift and uncertain close stay in HOLD.
 * Local closure grants no guest execution, stock return or kernel-wide proof.
 */
enum gtsp_release gtsp_poll_close(struct gtsp_owner *owner);

#endif
