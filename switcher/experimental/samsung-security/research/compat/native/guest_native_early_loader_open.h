#ifndef ONEOS_GUEST_NATIVE_EARLY_LOADER_OPEN_H
#define ONEOS_GUEST_NATIVE_EARLY_LOADER_OPEN_H

#include "guest_native_early_loader.h"

/* Borrow the admitted baseline, Runtime sample (required for first
 * linkerconfig) and immutable proposed environment. The caller holds the
 * same private mount view and excludes competing writers and FD changes.
 * Publish readback only after all temporary FDs are closed. Refusal leaves
 * out untouched and preserves the first close error in the caller's cell. */
int guest_native_early_loader_open_readback(enum guest_native_exec_phase phase,
        const struct guest_linkerconfig_generation_start *baseline,
        const struct guest_apex_runtime_sample *runtime, const char *const *envp, size_t env_count,
        struct guest_native_early_loader_sample *out, int *close_error);

#endif
