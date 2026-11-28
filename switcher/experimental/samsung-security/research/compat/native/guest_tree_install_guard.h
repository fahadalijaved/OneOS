#ifndef ONEOS_GUEST_TREE_INSTALL_GUARD_H
#define ONEOS_GUEST_TREE_INSTALL_GUARD_H

struct guest_tree_install_guard;

/* One attempt on the root installer process leader. Both input FDs are
 * borrowed. Retain any returned owner even when acquisition refuses. */
int guest_tree_install_guard_acquire(struct guest_tree_install_guard **out,
        int stage_fd, int controller_namespace_fd);

/* Compare both earlier directory FDs after acquiring the current lease and
 * before creating the writer reservation. All four input FDs are distinct
 * and borrowed. The caller keeps the retained witnesses open through the call
 * and retains any returned guard even on refusal. */
int guest_tree_install_guard_acquire_bound(struct guest_tree_install_guard **out,
        int stage_fd, int controller_namespace_fd, int retained_stage_fd, int retained_guard_fd);

/* Strong prerequisite for the fixed provisioner and publisher. */
int guest_tree_fsverity_check_install_guard(const struct guest_tree_install_guard *guard,
        int stage_fd, int controller_namespace_fd);

/* Retain the negative after an uncertain effect, before any finish attempt. */
int guest_tree_install_guard_hold(struct guest_tree_install_guard *guard, int error);

/* Caller first settles the composed provisioner/publisher's actual effects
 * and handles. Verify the fixed temporary leaf is absent and release only
 * this guard's own reservation. The guard never removes a candidate or image. */
int guest_tree_install_guard_finish(struct guest_tree_install_guard *guard);

#endif
