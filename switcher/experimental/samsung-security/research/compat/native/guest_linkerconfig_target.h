#ifndef ONEOS_GUEST_LINKERCONFIG_TARGET_H
#define ONEOS_GUEST_LINKERCONFIG_TARGET_H

#include "guest_linkerconfig_output.h"

/* The caller owns the exact admitted EROFS guest root and exclusive private
 * child mount namespace. Borrow root_fd. Success transfers the attached
 * directory and read-only base FDs through out. Failure leaves out unchanged.
 * A failed move or later refusal may leave an attached mount. Retire the
 * exact child view on failure, without retry or pathname cleanup. */
int guest_linkerconfig_prepare_target(int root_fd, uint64_t root_mount_id,
        struct guest_linkerconfig_generation_start *out);

#endif
