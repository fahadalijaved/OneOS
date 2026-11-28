#ifndef ONEOS_GUEST_TREE_CONTROL_OWNER_H
#define ONEOS_GUEST_TREE_CONTROL_OWNER_H

#include <stdint.h>
#include <sys/types.h>

#include "guest_tree_release_owner.h"

enum gtc_witness_role { GTC_TREE = 0, GTC_PRIVATE_DATA, GTC_PARENT_NAMESPACE };
enum gtc_right_role {
    GTC_NAMESPACE = 0, GTC_INHERITED_ROOT, GTC_GUEST_ROOT, GTC_DATA, GTC_MIRROR, GTC_DEV, GTC_SOCKET
};

struct gtc_owner;
struct gtc_observation {
    uint64_t namespace_inode, namespace_dev;
    uint64_t mounts[GTR_VIEW_RIGHTS];
    uint64_t data_group, mirror_group, alias_native, alias_guest;
    uint64_t guest_data_mount, guest_mirror_mount;
};

struct gtc_child_inputs {
    pid_t parent;
    const int *witnesses;
};

struct gtc_child_view {
    struct gtc_observation observation;
    int rights[GTR_VIEW_RIGHTS];
};

/*
 * Fixed seven-role receiver for the tree variant. Joins root/namespace and
 * inherited-root/data/mirror/alias/dev/socket proof in one live-child sample.
 * No caller supplies a verifier, result flag, normalized snapshot or PID.
 * Record any uncertain close in the same close_error cell. No FD transfer.
 */
int guest_tree_verify_remaining_view(pid_t child, const int witnesses[GTR_WITNESSES],
                                     const int rights[GTR_VIEW_RIGHTS],
                                     const struct gtc_observation *observed, int *close_error);

/* Parent only. Pass owned duplicate tree/data/parent-namespace cells, not the
 * provider's original witnesses. Initialize *out to NULL. On a nonnull result
 * retain the owner even on refusal; inspect which cells were consumed. The
 * implementation owns the real control pair, invokes the fixed tree child,
 * and delegates its sole child reap/signals to gtr. Dedicated one-thread,
 * one-shot source lifetime. */
int gtc_begin(struct gtc_owner **out, int witnesses[GTR_WITNESSES]);

/* Bounded actual child receive and fixed parent validation. Returning zero
 * means a retained partial tree view, never launch, auth, or guest readiness.
 * A refusal cuts off this attempt; keep and drain the same owner. */
int gtc_receive_partial(struct gtc_owner *owner, struct gtc_observation *observed);

/* One STOP request and actual control cutoff, with no reap promise. */
int gtc_request_stop(struct gtc_owner *owner);

/* Advances actual sole waiter, grace and closes without blocking. The
 * no-rights terminal only describes local custody; it cannot establish a
 * pre-effect refusal. HOLD on uncertainty never permits source guard removal.
 * Positive local release still needs the provider's own lease and witnesses. */
enum gtr_release gtc_poll_close(struct gtc_owner *owner);

#endif
