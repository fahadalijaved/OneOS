#ifndef ONEOS_GUEST_ZYGOTE_PARENT_READBACK_H
#define ONEOS_GUEST_ZYGOTE_PARENT_READBACK_H

#include "guest_tree_control_owner.h"

/* Observe the exact live child's root, cwd and mount namespace after root
 * entry. The controller owns the unreaped child and brackets this readback
 * with its actual liveness and deadline checks. Borrow the GTR-adopted root
 * and namespace FDs and their original admitted observation. Keep the same
 * child, view and descriptor table throughout. Record any uncertain local
 * close in the caller's sticky close_error cell, preserving a primary error.
 * This observes the process view only. It does not wait, signal or enter it. */
int guest_zygote_parent_readback(pid_t child, int root_fd, int namespace_fd,
        const struct gtc_observation *admitted, int *close_error);

#endif
