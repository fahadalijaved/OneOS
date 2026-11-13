#ifndef ONEOS_GUEST_TREE_PROPERTY_TRANSITION_H
#define ONEOS_GUEST_TREE_PROPERTY_TRANSITION_H

#include <stdint.h>

struct guest_tree_property_child;
struct guest_tree_property_transition;

/* The retained query describes one generation and six exact inodes. */
struct guest_tree_property_transition_sample {
    uint64_t mount_id, inodes[6];
    uint32_t policy_sequence, policy_load;
};

/*
 * One attempt inside the dedicated GTC child, before root entry. Borrow the
 * exact staged child and its GTC dev descriptor for this owner's lifetime.
 * Initialize *out to NULL. Retain any published result, including refusal,
 * until local close or the actual child drain.
 *
 * Runs the existing enforcing, non-permissive AV preflight and queries the
 * six exact SELinux validatetrans constraints on the same retained objects.
 * All object descriptors are read-only. Success does not admit a mutation,
 * prove filesystem association, or change the 0500 child profile.
 */
int guest_tree_property_transition_begin(struct guest_tree_property_child *child,
        int dev_fd, struct guest_tree_property_transition **out);

/* Return diagnostic scalars after a current custody and policy resample. */
int guest_tree_property_transition_read(struct guest_tree_property_transition *owner,
        struct guest_tree_property_transition_sample *sample);

/* Consume only this owner's local descriptors. Failure remains sticky. */
int guest_tree_property_transition_close(struct guest_tree_property_transition *owner);

#endif
