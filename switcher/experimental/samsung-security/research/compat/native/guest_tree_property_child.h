#ifndef ONEOS_GUEST_TREE_PROPERTY_CHILD_H
#define ONEOS_GUEST_TREE_PROPERTY_CHILD_H

#include "guest_tree_dev_roles.h"
#include "guest_tree_property_stage.h"

struct guest_tree_property_child;

struct guest_tree_seeded_dev_sample {
    struct guest_tree_dev_sample skeleton;
    struct guest_tree_dev_identity property, reopened_property;
};

/* Pure topology/FD sample for the separate seeded profile. The source owner
 * supplies authentic parsed child rows, the admitted root mount, and complete
 * directory enumerations. This never substitutes for the socket-only check. */
int guest_tree_dev_roles_check_seeded(const struct gpv_mount_row *rows, size_t count,
        uint64_t root_mount_id, const struct guest_tree_seeded_dev_sample *sample);

/* One attempt in the actual dedicated fork child, before reporting rights or
 * starting a consumer. The fixed composition already owns the five read-only
 * CLOEXEC seed descriptors in this child. It must retain them through GTC's
 * inherited-FD restriction. This leaf takes the exact disjoint cells once
 * after initial admission, with no duplication and no new transport right.
 * Retain every nonnull owner even on refusal. Existing GTC rights are borrowed. */
int guest_tree_property_child_begin(const struct gtc_child_inputs *input,
        const struct gtc_child_view *view, int seeds[GTP_SEED_COUNT],
        struct guest_tree_property_child **out);

/* Borrow the same published property directory after current readback.
 * Initialize *directory_fd to -1. This is stored-byte/namespace evidence,
 * without label, property service, consumer access or guest-entry admission. */
int guest_tree_property_child_borrow(struct guest_tree_property_child *owner, int *directory_fd);

/* Local descriptors only, once the caller has stopped all users. Uncertain
 * staging/close remains a failure. Child/namespace drain is the actual outer
 * owner's responsibility. No unmount, retry, marker or pathname cleanup. */
int guest_tree_property_child_close(struct guest_tree_property_child *owner);

#endif
