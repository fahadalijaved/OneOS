#ifndef ONEOS_GUEST_LINKERCONFIG_STARTUP_H
#define ONEOS_GUEST_LINKERCONFIG_STARTUP_H

#include "guest_linkerconfig_app_process.h"
#include "guest_linkerconfig_property_readback.h"

enum { GUEST_LINKERCONFIG_STARTUP_INPUT_COUNT = 13 };

struct guest_linkerconfig_startup_files {
    struct guest_linkerconfig_property_files properties;
    struct guest_apex_runtime_files runtime;
    int output_directory_fd, output_base_fd;
};

struct guest_linkerconfig_startup_scratch {
    void *xml;
    size_t xml_capacity;
    void *work;
    size_t work_capacity;
};

struct guest_linkerconfig_startup_start {
    struct guest_linkerconfig_generation_start generation;
    struct guest_linkerconfig_property_sample properties;
    struct guest_apex_runtime_sample runtime;
    int input_fds[GUEST_LINKERCONFIG_STARTUP_INPUT_COUNT];
    unsigned char input_identity_sha256[32];
};

struct guest_linkerconfig_startup_sample {
    struct guest_linkerconfig_app_process_system_sample app;
    struct guest_linkerconfig_property_sample properties;
    struct guest_apex_runtime_sample runtime;
};

/* Observe the retained inputs and first-write target before generation.
 * The owner keeps one guest root/namespace and the same slots through use.
 * XML scratch remains available for the owner's full active-cohort check.
 * Work scratch is reused for properties and the generated base. Scratch,
 * inputs, prior sample and output are disjoint. Scratch can change on
 * refusal. The output is written only after the whole check succeeds. */
int guest_linkerconfig_startup_begin(const struct guest_linkerconfig_startup_files *files,
        const struct guest_linkerconfig_startup_scratch *scratch, struct guest_linkerconfig_startup_start *out);

/* Rejoin the first-write outputs and the same inputs after the owner's
 * exact generator has settled. The owner proves the phase, producer,
 * complete APEX/partition and effective consumer inputs, and excludes other
 * writers and mount/slot changes through use. This publishes observations
 * only. Executable-mount bits, actual loader success and entry authority
 * remain separate. */
int guest_linkerconfig_startup_readback(const struct guest_linkerconfig_startup_start *start,
        const struct guest_linkerconfig_startup_files *files, const struct guest_linkerconfig_app_process_files *app,
        const struct guest_linkerconfig_startup_scratch *scratch, struct guest_linkerconfig_startup_sample *out);

#endif
