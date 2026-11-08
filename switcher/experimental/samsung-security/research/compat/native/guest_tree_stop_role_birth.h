#ifndef ONEOS_GUEST_TREE_STOP_ROLE_BIRTH_H
#define ONEOS_GUEST_TREE_STOP_ROLE_BIRTH_H

#include <stdint.h>
#include <sys/types.h>

/* Sample the caller's exact owned child. The caller brackets this observation
 * with its own child-liveness checks. Zero a nonnull output on refusal. */
int guest_tree_stop_role_birth(pid_t child, uint64_t *start_ticks);

#endif
