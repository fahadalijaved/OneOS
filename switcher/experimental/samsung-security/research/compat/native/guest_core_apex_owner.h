#ifndef ONEOS_GUEST_CORE_APEX_OWNER_H
#define ONEOS_GUEST_CORE_APEX_OWNER_H

#include "guest_tree_prepare_root.h"

enum guest_core_apex_role {
    GCA_ART = 0, GCA_I18N, GCA_RUNTIME, GCA_COUNT
};

struct guest_core_apex_backing {
    int payload_fd;
    int loop_fd;
    int mounted_root_fd;
};

struct guest_core_apex_inputs {
    const struct guest_tree_root_preparation *root;
    pid_t parent;
    int parent_namespace_fd, child_namespace_fd;
    struct guest_core_apex_backing backing[GCA_COUNT];
};

/*
 * Internal single-use GTC child stage, after guest_tree_prepare_root and
 * before any partial-view report. The same stage owner must already admit
 * the exact three payload files under its retained writer exclusion and
 * own their private, read-only loop-backed mounts. This function checks
 * the actual loop, file, filesystem and mount joins again. The recorded
 * byte extents and manifest IDs here are not a substitute for source
 * admission. No pathname discovery or host APEX fallback.
 *
 * Borrowed inputs and scratch must remain live during the call. All new
 * descriptor cells are retained in the actual child, including on
 * failure. After the first call, that child must either retain the stage
 * or follow the existing GTC process drain. No retry, cleanup by mount ID,
 * or readiness/activation grant. Success checks the three same-payload
 * stable/versioned pairs in this namespace only.
 */
int guest_core_apex_stage(const struct guest_core_apex_inputs *inputs,
                         struct guest_tree_mount_scratch scratch);

#endif
