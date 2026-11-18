#ifndef ONEOS_GUEST_LINKERCONFIG_PARENT_READBACK_H
#define ONEOS_GUEST_LINKERCONFIG_PARENT_READBACK_H

struct statx;

/* Borrow the live child's root, authenticated proc task directory and exact
 * transferred linkerconfig directory and base FDs. The sole waiter retains
 * the admitted private namespace, brackets child liveness and owns all four
 * FDs. Observe the projected mount rows and the stock '#' baseline. A task
 * mount-table close error is retained in the caller's sticky cell. */
int guest_linkerconfig_parent_readback(int live_root_fd, int task_fd,
        const struct statx *proc, int directory_fd, int base_fd, int *close_error);

#endif
