#ifndef ONEOS_GUEST_TREE_SOURCE_MOUNTS_H
#define ONEOS_GUEST_TREE_SOURCE_MOUNTS_H

#include "guest_private_view_mountinfo.h"

#define GUEST_TREE_STAGE_PATH "/data/local/tmp/oneos-viewprep"
#define GUEST_TREE_BACKING_PATH GUEST_TREE_STAGE_PATH "/backing"
#define GUEST_TREE_SOURCE_PATH GUEST_TREE_BACKING_PATH "/tree"
#define GUEST_TREE_DATA_PATH GUEST_TREE_STAGE_PATH "/data"
#define GUEST_TREE_TARGET_PATH "/mnt/gvi/root"

struct guest_tree_mount_identity {
    uint64_t id;
    uint32_t major, minor;
};

enum guest_tree_source_mount_result {
    GUEST_TREE_SOURCE_MOUNTS_UNKNOWN = 0,
    GUEST_TREE_SOURCE_MOUNTS_MATCHED
};

/*
 * Pure check of one complete recursively private mountinfo sample, before
 * attaching anything. Ambient shared, slave and propagate-from rows refuse.
 * The caller retains the source and fresh target directory FDs reached by
 * no-follow walks at the fixed paths, and samples their actual fdinfo mount
 * IDs and fstat st_dev in this namespace. Scratch follows the mountinfo
 * parser's capacity and non-overlap contract.
 *
 * MATCHED describes metadata only. It cannot establish FD/path custody,
 * namespace identity, tree content or immutability, mount freshness, or
 * exclusion of aliases outside the sampled mount table. Caller must retain
 * the same objects and exclude namespace changes through any later attach.
 */
enum guest_tree_source_mount_result guest_tree_source_mounts_check(
        const char *mountinfo, size_t length,
        struct gpv_mount_row *scratch, size_t capacity,
        struct guest_tree_mount_identity source,
        struct guest_tree_mount_identity target);

#endif
