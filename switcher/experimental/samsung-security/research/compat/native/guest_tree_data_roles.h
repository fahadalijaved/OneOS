#ifndef ONEOS_GUEST_TREE_DATA_ROLES_H
#define ONEOS_GUEST_TREE_DATA_ROLES_H

#include "guest_private_view_mountinfo.h"

struct gtc_observation;

/* Independently sampled FD facts. mode includes the file type. */
struct guest_tree_data_identity {
    uint64_t mount_id, inode;
    uint32_t major, minor, uid, gid, mode;
};

struct guest_tree_data_roles {
    struct guest_tree_data_identity inherited_root, guest_root, private_data;
    struct guest_tree_data_identity native_data, guest_data, native_mirror, guest_mirror;
    struct guest_tree_data_identity user_zero, native_alias, guest_alias;
};

/*
 * Check parsed current parent and child tables under the real parent's retained
 * namespace and source fences. The collector holds the authenticated child's
 * received root/data/mirror descriptors and the original private_data witness.
 * It samples guest_data and guest_mirror below guest_root, user_zero and
 * native_alias below native_data, and guest_alias below guest_data. No-follow
 * component walks and actual directory FD identity are collector obligations.
 *
 * Claims come from the authenticated packet; they never substitute for a
 * measured identity. Zero is a bounded data/mirror/alias sample, with no
 * namespace, dev/socket, launch, credential or release grant.
 */
int guest_tree_data_roles_check(const struct gpv_mount_row *parent_rows, size_t parent_count,
        const struct gpv_mount_row *child_rows, size_t child_count,
        const struct guest_tree_data_roles *roles, const struct gtc_observation *claims);

#endif
