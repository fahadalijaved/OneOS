#ifndef ONEOS_GUEST_TREE_ROOT_READBACK_H
#define ONEOS_GUEST_TREE_ROOT_READBACK_H

#include "guest_tree_root_attach.h"
#include "guest_tree_source_mounts.h"

struct guest_tree_root_readback {
    int root_fd;
    struct guest_tree_mount_identity source, scaffold, attached;
};

/* Join the named source and fresh scaffold paths to the held directories
 * before any mount operation. The caller has already walked them no-follow. */
int guest_tree_admit_root_fds(int source_fd, int scaffold_parent_fd, int target_fd,
                             struct guest_tree_mount_identity *source,
                             struct guest_tree_mount_identity *scaffold);

/* Call in the same isolated child immediately after a successful attach,
 * before attaching anything below root. The caller owns the admitted source,
 * exact /mnt/gvi parent and covered target FDs. Initialize result with
 * root_fd = -1. Any returned root FD remains owned even on refusal. IDs are
 * published only on success and must still be joined to current namespace
 * and mountinfo observations. This check does not establish tree provenance
 * or backing writer exclusion. */
int guest_tree_read_attached_root(int source_fd, int scaffold_parent_fd,
                                  int covered_target_fd,
                                  const struct guest_tree_attachment *attachment,
                                  struct guest_tree_root_readback *result);

#endif
