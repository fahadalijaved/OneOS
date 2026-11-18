#ifndef ONEOS_GUEST_LINKERCONFIG_APP_PROCESS_H
#define ONEOS_GUEST_LINKERCONFIG_APP_PROCESS_H

#include "guest_apex_info_readback.h"
#include "guest_linkerconfig_output.h"

struct guest_linkerconfig_app_process_files {
    struct guest_linkerconfig_output_files output;
    int system_fd, system_bin_fd, system_etc_fd, app_process_fd;
    int apex_fd, runtime_fd, runtime_bin_fd, linker_fd;
};

enum guest_linkerconfig_executable_mount {
    GUEST_LINKERCONFIG_EXEC_APP = 1u,
    GUEST_LINKERCONFIG_EXEC_INTERPRETER = 2u,
};

struct guest_linkerconfig_app_process_sample {
    struct guest_linkerconfig_output_sample output;
    uint64_t app_process_inode, linker_inode, runtime_mount_id;
    uint32_t executable_mounts;
};

/* Check the pinned donor entry, its interpreter and the generated pair
 * in one retained guest view. The owner supplies its own same-occurrence
 * generation and Runtime samples, keeps all borrowed slots and mounts
 * stable, and excludes pathname and byte writers through consumption.
 * This checks path identity and config precedence and reports a separate
 * bit for each read-only, nosuid, nodev leaf mount with noexec clear.
 * Successful readback can report neither bit. Actual exec access, the
 * process environment, config parsing and loader selection are separate. */
int guest_linkerconfig_app_process_readback(const struct guest_linkerconfig_generation_start *start,
        const struct guest_apex_runtime_sample *runtime, const struct guest_linkerconfig_app_process_files *files,
        struct guest_linkerconfig_app_process_sample *out);

struct guest_linkerconfig_app_process_system_sample {
    struct guest_linkerconfig_app_process_sample entry;
    struct guest_linkerconfig_system_section system;
};

/* Add the strict generated system section check inside the entry bracket.
 * The caller owns disjoint scratch for the generated base extent. */
int guest_linkerconfig_app_process_readback_system(const struct guest_linkerconfig_generation_start *start,
        const struct guest_apex_runtime_sample *runtime, const struct guest_linkerconfig_app_process_files *files,
        void *scratch, size_t capacity, struct guest_linkerconfig_app_process_system_sample *out);

#endif
