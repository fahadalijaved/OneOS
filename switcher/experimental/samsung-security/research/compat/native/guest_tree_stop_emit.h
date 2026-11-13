#ifndef ONEOS_GUEST_TREE_STOP_EMIT_H
#define ONEOS_GUEST_TREE_STOP_EMIT_H

#include <stddef.h>

struct guest_tree_stop_backing_sample;
struct guest_tree_stop_carrier_sample;

enum guest_tree_stop_window {
    GUEST_TREE_STOP_WINDOW_PRE,
    GUEST_TREE_STOP_WINDOW_POST,
};

enum { GUEST_TREE_STOP_EMIT_CAPACITY = 8192 };

/* Format one newline-terminated JSON record in the caller's buffer. Returns
 * its byte length excluding NUL, or -1 with an empty output buffer and errno.
 * The caller supplies a successful carrier sample and, only for POST, a
 * successful backing sample. This formatter performs no writes to FDs. */
int guest_tree_stop_emit(char *out, size_t capacity, enum guest_tree_stop_window window,
        const struct guest_tree_stop_carrier_sample *carrier,
        const struct guest_tree_stop_backing_sample *backing);

#endif
