#ifndef ONEOS_GUEST_TREE_INSTALL_BOOTSTRAP_H
#define ONEOS_GUEST_TREE_INSTALL_BOOTSTRAP_H

#include <stdint.h>

struct guest_tree_install_bootstrap;

struct guest_tree_install_bootstrap_identity {
    uint64_t stage_mount, stage_inode, guard_mount, guard_inode;
    uint32_t stage_dev_major, stage_dev_minor, guard_dev_major, guard_dev_minor;
};

enum guest_tree_install_bootstrap_release {
    GUEST_TREE_INSTALL_BOOTSTRAP_HOLD = 1,
    GUEST_TREE_INSTALL_BOOTSTRAP_NO_EFFECT_LOCAL_CLOSED = 2,
    GUEST_TREE_INSTALL_BOOTSTRAP_PUBLISHED_LOCAL_CLOSED = 4,
};

/* One separately authorized first-use attempt on the root process leader.
 * Fixed initial stage and lease only. Existing final or temporary names
 * refuse without adoption. Retain any nonnull owner even on failure. The
 * caller already excludes unrelated privileged writers and stock operations.
 * No controller, image, mount, label change or cleanup is performed. */
int guest_tree_install_bootstrap_begin(struct guest_tree_install_bootstrap **out);

/* Borrow the exact stage only after both no-replace publications and syncs
 * are verified. Initialize *stage_fd to -1. The bootstrap still holds its
 * lease. The separate installer guard can acquire only after local close. */
int guest_tree_install_bootstrap_borrow(struct guest_tree_install_bootstrap *owner, int *stage_fd);

/* Close tracked descriptors once after verified publication or pre-effect
 * refusal. Uncertain progress stays in HOLD. No retry or partial removal. */
enum guest_tree_install_bootstrap_release
guest_tree_install_bootstrap_close(struct guest_tree_install_bootstrap *owner);

/* Copy the verified publication identities only after PUBLISHED_LOCAL_CLOSED.
 * This is the retained terminal snapshot. No paths or descriptors are read. */
int guest_tree_install_bootstrap_published_identity(struct guest_tree_install_bootstrap *owner,
        struct guest_tree_install_bootstrap_identity *out);

#endif
