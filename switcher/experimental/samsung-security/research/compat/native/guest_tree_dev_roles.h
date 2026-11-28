#ifndef ONEOS_GUEST_TREE_DEV_ROLES_H
#define ONEOS_GUEST_TREE_DEV_ROLES_H

#include "guest_tree_source_mounts.h"

#define GUEST_TREE_DEV_PATH GUEST_TREE_TARGET_PATH "/dev"
#define GUEST_TREE_DEV_SOURCE "gvo-v3-owned-dev"

struct guest_tree_dev_identity {
    struct guest_tree_mount_identity mount;
    uint64_t ino, nlink, fs_type, fs_flags;
    uint32_t mode, uid, gid;
};

struct guest_tree_dev_sample {
    struct guest_tree_dev_identity dev, socket_dir;
    struct guest_tree_dev_identity reopened_dev, reopened_socket;
};

/*
 * Pure check of the empty GVO v3 dev/socket skeleton after its mkdir and
 * before any device, property or socket provider populates it. Supply one
 * complete successfully parsed child table and the independently admitted
 * tree root mount ID. Each observation joins the same actual FD's mount ID,
 * fstat (including st_dev major/minor and full st_mode), and Linux fstatfs
 * (f_type and raw f_flags). Preserve the held rights and use no-follow
 * single-component directory opens from the held root to dev and from the
 * held dev to socket for the two independent readbacks.
 *
 * The owner must read the complete directory shapes to EOF on readable
 * descriptors joined to the same objects and mount: dev has ., .. and
 * socket; socket has . and ... Count and link metadata cannot establish
 * emptiness on their own. Treat read, close, or namespace uncertainty as
 * refusal. A zero return describes the supplied sample only. The owner
 * retains all FDs and namespace lifetime and still owns the outer check.
 */
int guest_tree_dev_roles_check(const struct gpv_mount_row *child_rows,
        size_t child_count, uint64_t root_mount_id,
        const struct guest_tree_dev_sample *sample);

#endif
