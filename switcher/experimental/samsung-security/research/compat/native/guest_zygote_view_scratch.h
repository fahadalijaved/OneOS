#ifndef ONEOS_GUEST_ZYGOTE_VIEW_SCRATCH_H
#define ONEOS_GUEST_ZYGOTE_VIEW_SCRATCH_H

#include "guest_tree_control_owner.h"

enum { GUEST_ZYGOTE_VIEW_SCRATCH_COUNT = 24 };

struct guest_zygote_view_context {
    int control_fd;
};

/* Consume the exact scratch FDs enumerated by the child view preparer. The
 * caller owns the exclusive FD table and supplies its original witnesses,
 * view rights and relocated control FD. Preflight refusal leaves all cells
 * unchanged. Close in reverse order, consuming each cell before its call.
 * On the first close error, retire the child with all remaining cells held
 * for its exit. Never retry a consumed cell. */
int guest_zygote_view_scratch_close(int scratch[GUEST_ZYGOTE_VIEW_SCRATCH_COUNT],
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_zygote_view_context *context);

#endif
