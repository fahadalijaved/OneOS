#ifndef ONEOS_GUEST_LINKERCONFIG_OUTPUT_H
#define ONEOS_GUEST_LINKERCONFIG_OUTPUT_H

#include <stddef.h>
#include <stdint.h>

enum { GUEST_LINKERCONFIG_OUTPUT_MAX_BYTES = 1024 * 1024 };

struct guest_linkerconfig_output_files {
    int root_fd, directory_fd, base_fd, companion_fd;
};

struct guest_linkerconfig_output_file_sample {
    uint64_t inode;
    size_t bytes;
    unsigned char sha256[32];
};

struct guest_linkerconfig_output_sample {
    uint64_t root_mount_id, root_inode, directory_mount_id, directory_inode;
    uint32_t directory_device_major, directory_device_minor;
    struct guest_linkerconfig_output_file_sample base, companion;
};

/* Observe the base and companion files in the active guest /linkerconfig.
 * Borrow the four distinct descriptors without opening, closing or moving
 * their cursors. Publish out only after both files and both directories
 * pass the final identity check. Accept a present zero-byte companion.
 * The owner proves the guest root, selected output mount and root:root
 * generation profile. It owns the fresh target, settled exact producer and
 * writer exclusion through later use. This samples bytes and identities.
 * Producer success, per-APEX outputs and loader selection are separate. */
int guest_linkerconfig_output_readback(const struct guest_linkerconfig_output_files *files,
        struct guest_linkerconfig_output_sample *out);

struct guest_linkerconfig_generation_node {
    uint64_t mount_id, inode;
    uint32_t device_major, device_minor, mode, uid, gid;
};

struct guest_linkerconfig_generation_start {
    int root_fd, directory_fd, base_fd;
    struct guest_linkerconfig_generation_node root, directory, base;
};

/* Sample the stock first-write baseline. The held base is exactly '#',
 * and the companion is absent by its fixed name in the visible directory.
 * The owner separately proves the rest of the destination is clean. */
int guest_linkerconfig_generation_begin(int root_fd, int directory_fd, int base_fd,
        struct guest_linkerconfig_generation_start *out);

/* Check the same three retained descriptors against the sampled baseline
 * before reading the generated pair. The donor overwrites the held base
 * inode in place. The owner retains all descriptors and excludes other
 * mount, pathname and file writers from begin through consumption. It
 * settles the exact generator between the calls. This API neither starts
 * nor authenticates a producer, and checks only the two fixed output names.
 * Each call leaves its output unchanged on refusal. */
int guest_linkerconfig_generation_readback(const struct guest_linkerconfig_generation_start *start,
        const struct guest_linkerconfig_output_files *files, struct guest_linkerconfig_output_sample *out);

struct guest_linkerconfig_system_section {
    uint32_t mapping_line, section_line, search_path_lines;
};

struct guest_linkerconfig_system_output_sample {
    struct guest_linkerconfig_output_sample output;
    struct guest_linkerconfig_system_section system;
};

/* Check the ordinary generator's first system mapping and its section
 * from the same base bytes that are hashed. Borrow disjoint scratch for
 * the base extent, up to GUEST_LINKERCONFIG_OUTPUT_MAX_BYTES. Scratch may
 * change on refusal. Publish the combined sample only after final identity
 * checks. This is a strict text profile, not full Bionic namespace parsing.
 * The owner proves /system/bin access and resolution in the actual guest. */
int guest_linkerconfig_generation_readback_system(const struct guest_linkerconfig_generation_start *start,
        const struct guest_linkerconfig_output_files *files, void *scratch, size_t capacity,
        struct guest_linkerconfig_system_output_sample *out);

#endif
