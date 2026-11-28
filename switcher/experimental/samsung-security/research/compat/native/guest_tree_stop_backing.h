#ifndef ONEOS_GUEST_TREE_STOP_BACKING_H
#define ONEOS_GUEST_TREE_STOP_BACKING_H

#include <stdint.h>

struct guest_tree_stop_backing_node {
    uint64_t mount_id, inode;
    uint32_t device_major, device_minor, mode, uid, gid;
};

struct guest_tree_stop_backing_sample {
    struct guest_tree_stop_backing_node data, stage, backing, dev, guard;
    int writer_errno, legacy_errno, view_errno;
};

/* Borrow the current physical stage FD for one observation in the admitted
 * host mount namespace. Success means an empty, uncovered backing on /data
 * and direct no-follow ENOENT for the three markers at the sampled guard.
 * The caller joins the guard to its prior witness. The caller keeps stage_fd
 * open and closes it. On error, return -1 with errno and zero a nonnull out. */
int guest_tree_stop_backing_read(int stage_fd, struct guest_tree_stop_backing_sample *out);

#endif
