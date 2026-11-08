#ifndef ONEOS_GUEST_NATIVE_EARLY_LOADER_H
#define ONEOS_GUEST_NATIVE_EARLY_LOADER_H

#include "guest_linkerconfig_output.h"
#include "guest_native_exec_placement.h"

struct guest_native_early_loader_view {
    const struct guest_native_exec_view *placement;
    int system_etc_fd, output_directory_fd, output_base_fd, runtime_config_fd;
    const char *const *envp;
    size_t env_count;
};

struct guest_native_early_loader_sample {
    struct guest_native_exec_sample placement;
    struct guest_linkerconfig_generation_start baseline;
};

/* Borrow the phase's exact file view, first-write target and immutable
 * proposed envp (env_count entries followed by NULL). The owner retains the
 * same private view and excludes other writers, mount and FD changes. For
 * first linkerconfig, runtime_config_fd is -1 if its per-APEX config directory
 * is absent, or a held FD for that exact directory when present. Bootstrap
 * ignores this cell. This observes fixed early-loader prerequisites only.
 * On refusal, out is unchanged. No descriptors, cursors or environment change. */
int guest_native_early_loader_readback(enum guest_native_exec_phase phase,
        const struct guest_native_early_loader_view *view, struct guest_native_early_loader_sample *out);

#endif
