#ifndef ONEOS_GUEST_TREE_INSTALL_CONTROLLER_H
#define ONEOS_GUEST_TREE_INSTALL_CONTROLLER_H

#include <stddef.h>

struct guest_tree_install_guard;

enum guest_tree_install_controller_result {
    GTIC_HOLD = 1,
    GTIC_NO_EFFECT_LOCAL_CLOSED = 2,
    GTIC_PUBLISHED_LOCAL_CLOSED = 3,
};

/*
 * One attempt on the actual root writer-guard owner. The guard, stage and
 * namespace descriptors and stable embedded bytes are borrowed. The caller
 * retains the guard and excludes unrelated privileged writers throughout.
 * errno is zero on publication, otherwise the first error. NO_EFFECT
 * describes this leaf only. HOLD can leave either fixed leaf present and
 * blocks guard release. No cleanup of either name or adoption is attempted.
 * The caller must finish the enclosing guard separately after local success.
 */
enum guest_tree_install_controller_result guest_tree_install_controller(
        struct guest_tree_install_guard *guard, int stage_fd, int controller_namespace_fd,
        const void *bytes, size_t length);

/*
 * Verify the fixed installed controller and absent temporary leaf under the
 * already-held guard. All inputs are borrowed. Returns 0 only after the
 * verification and local descriptor closes succeed. A mismatch refuses
 * without changing either leaf. Guard drift or an uncertain close retains HOLD.
 */
int guest_tree_verify_installed_controller(struct guest_tree_install_guard *guard,
        int stage_fd, int controller_namespace_fd);

#endif
