#ifndef ONEOS_GUEST_LINKERCONFIG_PROPERTY_READBACK_H
#define ONEOS_GUEST_LINKERCONFIG_PROPERTY_READBACK_H

#include "guest_tree_property_view.h"

#define GUEST_LINKERCONFIG_PROPERTY_SCRATCH_BYTES (2u * GUEST_TREE_PROP_AREA_BYTES)

struct guest_linkerconfig_property_files {
    int root_fd, dev_fd, directory_fd, info_fd, vndk_fd, debug_fd, serial_fd;
};

struct guest_linkerconfig_property_sample {
    uint64_t root_mount_id, root_inode, dev_mount_id, directory_inode;
    struct guest_tree_linker_property_sample properties;
    unsigned char vndk_sha256[32], debug_sha256[32], serial_sha256[32];
};

/* Borrow the final guest property files through the verified root and dev
 * names. The owner retains all slots, establishes the directory label and
 * intended reader credentials, and excludes mount, name, label and byte
 * writers (including writable mappings) through use. Serial comparison is
 * an additional drift check. It does not prove writer exclusion or the
 * effective mappings of another process.
 * Scratch is disjoint from files and out. Scratch may change on failure.
 * The complete result is published only after the final checks. */
int guest_linkerconfig_property_readback(const struct guest_linkerconfig_property_files *files,
        void *scratch, size_t capacity, struct guest_linkerconfig_property_sample *out);

#endif
