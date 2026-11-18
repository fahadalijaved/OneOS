#ifndef ONEOS_GUEST_TREE_IMMUTABLE_BACKING_H
#define ONEOS_GUEST_TREE_IMMUTABLE_BACKING_H

#include "guest_private_view_mountinfo.h"

enum guest_tree_backing_sample {
    GUEST_TREE_BACKING_REFUSED = 0,
    GUEST_TREE_BACKING_EROFS_PROFILE
};

/*
 * Read-only sample of the exact held source and its dedicated block-backed
 * EROFS mount. The caller owns both descriptors and supplies the authenticated
 * current mount row. Both FDs are borrowed and are never duplicated or closed.
 *
 * The positive result identifies a single-device EROFS profile and its
 * sampled read-only block device. The caller still needs a source-owned
 * authenticated content generation and a live mapping/raw-writer exclusion
 * owner before admission. The result provides neither of those guarantees.
 * The refusal leaves errno from the first failed observation or comparison.
 */
enum guest_tree_backing_sample guest_tree_immutable_backing_check(
        int tree_fd, int block_fd, const struct gpv_mount_row *row);

#endif
