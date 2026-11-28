#ifndef ONEOS_GUEST_CORE_APEX_PARENT_OBSERVE_H
#define ONEOS_GUEST_CORE_APEX_PARENT_OBSERVE_H

#include "guest_core_apex_child_attach.h"
#include "guest_tree_control_owner.h"

struct guest_core_apex_parent_observer;

struct guest_core_apex_parent_observation {
    uint64_t namespace_dev, namespace_inode, root, apex;
    struct {
        uint64_t sibling, stable, versioned;
    } role[GCA_COUNT];
};

/* Private fixed GTC path only. Capture after the existing accepted PARTIAL
 * verification and before sending any APEX request. Use the original actual
 * fork result and its sole waiter, original tree witnesses and authenticated
 * right cells, all from the same GTC attempt. Initialize *out to NULL. Retain
 * any published owner on failure. The selected GTC has no such call. */
int guest_core_apex_parent_capture(struct gtr_owner *release, pid_t child,
        const int witnesses[GTR_WITNESSES], const int rights[GTR_VIEW_RIGHTS],
        const struct gtc_observation *initial, struct guest_core_apex_child_sources *source,
        struct guest_core_apex_parent_observer **out, int *close_error);

/* After one authenticated same-child APEX completion on the still-owned
 * control channel, validate the stopped-at-this-boundary child. Output is
 * written only on success. Refusal is sticky, and neither outcome releases
 * custody or grants guest entry. */
int guest_core_apex_parent_observe(struct guest_core_apex_parent_observer *observer,
        struct guest_core_apex_parent_observation *out, int *close_error);

/* Only after actual child drain, consume this parent's local references.
 * Never reap, signal, unmount or close the original controller/source. */
int guest_core_apex_parent_observer_close(struct guest_core_apex_parent_observer *observer, int *close_error);

#endif
