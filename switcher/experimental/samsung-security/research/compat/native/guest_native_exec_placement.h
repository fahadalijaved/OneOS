#ifndef ONEOS_GUEST_NATIVE_EXEC_PLACEMENT_H
#define ONEOS_GUEST_NATIVE_EXEC_PLACEMENT_H

#include "guest_apex_info_readback.h"

enum guest_native_exec_phase {
    GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP,
    GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST,
};

enum guest_native_exec_dir {
    GNX_ROOT, GNX_SYSTEM, GNX_SYSTEM_BIN, GNX_SYSTEM_BOOTSTRAP_BIN,
    GNX_SYSTEM_LIB64, GNX_SYSTEM_BOOTSTRAP_LIB64, GNX_APEX, GNX_RUNTIME,
    GNX_RUNTIME_BIN, GNX_RUNTIME_LIB64, GNX_RUNTIME_BIONIC, GNX_DIR_COUNT,
};

struct guest_native_exec_view {
    int dirs[GNX_DIR_COUNT];
    uint64_t carrier_mount_id;
    const struct guest_apex_runtime_sample *runtime;
    const int *file_fds;
    size_t file_count;
};

struct guest_native_exec_sample {
    uint64_t noexec_objects;
    size_t object_count;
};

/* Borrow the selected phase's directory and file FDs, in fixed profile order,
 * under the retained guest root. Bootstrap uses the carrier directories only.
 * First linkerconfig uses the system (excluding bootstrap), apex and Runtime
 * directories and the admitted Runtime sample. Unused directory cells are
 * ignored. Keep input arrays, objects and mount view stable for this read.
 * No descriptors or cursors are changed. Publish only after complete readback.
 * A set bit reports NOEXEC for that file index, not loader or exec readiness. */
int guest_native_exec_placement_readback(enum guest_native_exec_phase phase,
        const struct guest_native_exec_view *view, struct guest_native_exec_sample *out);

#endif
