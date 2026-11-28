#ifndef ONEOS_GUEST_TREE_PREPARE_ROOT_H
#define ONEOS_GUEST_TREE_PREPARE_ROOT_H

#include <sys/types.h>

#include "guest_tree_root_readback.h"

struct guest_tree_root_inputs {
    pid_t parent_pid;
    int parent_namespace_fd, child_namespace_fd;
    int source_fd, scaffold_parent_fd, target_fd;
};

struct guest_tree_mount_scratch {
    char *text;
    size_t text_capacity;
    struct gpv_mount_row *rows;
    size_t row_capacity;
};

struct guest_tree_root_preparation {
    struct guest_tree_attachment attachment;
    struct guest_tree_root_readback readback;
};

/* Actual child-side prepare transaction. The caller is the sole task in its
 * distinct mount namespace, has installed parent-death handling, and holds
 * the original parent namespace plus current child namespace FDs. It retains
 * the source witness, exclusion of external backing writers and the exact
 * no-follow /mnt/gvi scaffold parent and freshly created root. Input FDs are
 * borrowed. Both workspaces are disjoint. Initialize output FDs to -1 and
 * attachment state to EMPTY. Both acquired output FDs transfer even on error.
 * Success only admits the immediate root view. Failure requires the child's
 * existing owner to drain it. Success grants no execution or return authority. */
int guest_tree_prepare_root(const struct guest_tree_root_inputs *input,
                            struct guest_tree_mount_scratch before,
                            struct guest_tree_mount_scratch after,
                            struct guest_tree_root_preparation *result);

#endif
