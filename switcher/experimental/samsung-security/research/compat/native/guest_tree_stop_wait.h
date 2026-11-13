#ifndef ONEOS_GUEST_TREE_STOP_WAIT_H
#define ONEOS_GUEST_TREE_STOP_WAIT_H

/* Borrow the observer's exclusive raw stdin stream. Return 0 only for the
 * exact after frame followed by EOF within one 150-second boottime deadline.
 * Return -1 with errno on refusal. The caller retains the descriptor. */
int guest_tree_stop_wait_after(void);

#endif
