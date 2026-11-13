#ifndef ONEOS_GUEST_TREE_ATTACHED_MOUNTS_H
#define ONEOS_GUEST_TREE_ATTACHED_MOUNTS_H

#include "guest_tree_source_mounts.h"

struct guest_tree_mount_snapshot {
    const char *mountinfo;
    size_t length;
    struct guest_tree_mount_identity source, scaffold;
    uint64_t namespace_dev, namespace_ino;
};

enum guest_tree_attached_mount_result {
    GUEST_TREE_ATTACHED_MOUNTS_MATCHED = 0,
    GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN = -1
};

/*
 * Pure immediate post-attach check, before any other namespace change.
 * before carries the exact admitted pre-attach bytes. Each snapshot's
 * identity fields come from fresh observations of the same retained
 * source, covered target and mount-namespace FDs. The owner has already
 * independently corroborated attached on the held clone and reopened
 * target FD, and has checked their inode and directory identity.
 *
 * All input and both scratch ranges are disjoint as required by the
 * mountinfo parser. Nonzero attach_result always refuses. MATCHED
 * describes sampled metadata, without creating any resource ownership
 * or authorizing cleanup, release, guest entry or a retry.
 */
enum guest_tree_attached_mount_result guest_tree_attached_mounts_check(
        int attach_result,
        const struct guest_tree_mount_snapshot *before,
        const struct guest_tree_mount_snapshot *after,
        struct guest_tree_mount_identity attached,
        struct gpv_mount_row *before_rows, size_t before_capacity,
        struct gpv_mount_row *after_rows, size_t after_capacity);

#endif
