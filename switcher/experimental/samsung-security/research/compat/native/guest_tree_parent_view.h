#ifndef ONEOS_GUEST_TREE_PARENT_VIEW_H
#define ONEOS_GUEST_TREE_PARENT_VIEW_H

#include <stdint.h>
#include <sys/types.h>

#include "guest_private_view_mountinfo.h"

struct guest_tree_parent_sample {
    int live_child_root;
    const struct gpv_mount_row *parent_rows, *child_rows;
    size_t parent_count, child_count;
};

/* Internal snapshot inspection in the same pinned namespace bracket.
 * All sample storage and the live child root are borrowed for this call. */
typedef int (*guest_tree_parent_inspector)(const struct guest_tree_parent_sample *, void *, int *close_error);

/*
 * Root-role corroboration after the sole parent receiver has authenticated
 * the actual successful PARTIAL and adopted its SCM_RIGHTS. child is the
 * still-owned unreaped fork result, not a PID accepted from the packet.
 * The source is the original fixed-tree witness from the same owner.
 * All four input FDs are borrowed. close_error is the parent's existing
 * first-close-error cell, initially zero. A temporary close error refuses
 * and latches without replacing a prior operation errno.
 *
 * The function reads actual proc tables in the current parent view and
 * checks both namespaces. The caller retains the peer, source writer
 * fence and all other right-role validation and wait ownership. Success
 * is a bounded root sample, without guest entry or cleanup credit.
 */
int guest_tree_parent_view_check(pid_t child, int source_fd, int parent_namespace_fd,
        int child_namespace_fd, int child_root_fd, uint64_t claimed_namespace_dev,
        uint64_t claimed_namespace_ino, uint64_t claimed_root_mount_id,
        int *close_error);

int guest_tree_parent_view_inspect(pid_t child, int source_fd, int parent_namespace_fd,
        int child_namespace_fd, int child_root_fd, uint64_t claimed_namespace_dev,
        uint64_t claimed_namespace_ino, uint64_t claimed_root_mount_id,
        guest_tree_parent_inspector inspector, void *context, int *close_error);

#endif
