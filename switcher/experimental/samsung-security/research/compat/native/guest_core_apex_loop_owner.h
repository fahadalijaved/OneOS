#ifndef ONEOS_GUEST_CORE_APEX_LOOP_OWNER_H
#define ONEOS_GUEST_CORE_APEX_LOOP_OWNER_H

#include "guest_core_apex_backing.h"

struct guest_core_apex_loop_owner;

enum guest_core_apex_fs { GCA_APEX_EXT4 = 1, GCA_APEX_EROFS = 2 };

struct guest_core_apex_loop_pair {
    int payload_fd, loop_fd;
    enum guest_core_apex_fs filesystem;
};

enum guest_core_apex_loop_release {
    GCA_LOOP_HOLD = 1,
    GCA_LOOP_NO_REQUEST_LOCAL_CLOSED = 2,
    GCA_LOOP_LOCAL_CLOSED_KERNEL_UNCONFIRMED = 3
};

/*
 * Actual dedicated root controller only. The exact active stage guard,
 * verified source owner, and controller mount namespace must remain held.
 * Consumes the source owner's one-time verified payload duplicate transfer.
 * Requests one loop candidate per role and attempts one readonly AUTOCLEAR
 * configure only after an unbound readback. No mount or fallback.
 * Initialize *out to NULL. Retain a nonnull owner even on failure.
 */
int guest_core_apex_loop_begin(struct guest_core_apex_files *source,
        struct guest_tree_stage_guard *guard, int controller_namespace_fd,
        struct guest_core_apex_loop_owner **out);

/*
 * Recheck all three current source and block joins before lending the exact
 * pairs. Output FD cells must all be -1. The caller keeps this owner, source
 * owner and guard through actual downstream mount release. No FD transfer.
 */
int guest_core_apex_loop_borrow(struct guest_core_apex_loop_owner *owner,
        struct guest_core_apex_loop_pair out[GCA_COUNT]);

/*
 * After actual downstream release, or before any borrow, consume local
 * descriptors once. Kernel pool effects and AUTOCLEAR detach remain
 * unconfirmed. HOLD preserves ambiguous configuration or local cleanup.
 * Never issue LOOP_CLR_FD, remove a loop number, or release the stage guard.
 */
enum guest_core_apex_loop_release guest_core_apex_loop_close(struct guest_core_apex_loop_owner *owner);

#endif
