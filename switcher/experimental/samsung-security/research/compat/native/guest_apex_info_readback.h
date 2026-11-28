#ifndef ONEOS_GUEST_APEX_INFO_READBACK_H
#define ONEOS_GUEST_APEX_INFO_READBACK_H

#include <stddef.h>
#include <stdint.h>

enum { GUEST_APEX_INFO_MAX_BYTES = 64 * 1024 };

struct guest_apex_info_sample {
    uint64_t mount_id, directory_inode, file_inode;
    uint32_t device_major, device_minor;
    size_t bytes;
    unsigned char sha256[32];
};

/* Borrow an already authenticated directory and its already-open read-only
 * XML file. The owner keeps both descriptor slots and open-file flags stable
 * throughout the call.
 * Read from offset zero without changing the borrowed cursor. Scratch and out
 * are disjoint. Scratch can change on failure, but the sample is written only
 * after all checks pass.
 * The owner separately proves the directory's guest occurrence and publisher.
 * This entry expects a root:root XML file. */
int guest_apex_info_readback(int apex_fd, int xml_fd, void *scratch, size_t capacity,
        struct guest_apex_info_sample *out);

/* Same borrowed-object contract for the donor apexd root:system 0644 file.
 * The owner must prove the selected donor publisher has finished writing. */
int guest_apex_info_readback_donor(int apex_fd, int xml_fd, void *scratch, size_t capacity,
        struct guest_apex_info_sample *out);

struct guest_apex_runtime_files {
    int apex_fd, xml_fd, runtime_fd, manifest_fd, etc_fd, config_fd;
};

struct guest_apex_runtime_sample {
    struct guest_apex_info_sample xml;
    uint64_t runtime_mount_id, runtime_inode, manifest_inode, etc_inode, config_inode;
};

/* Observe the donor XML and the pinned Runtime manifest and inner linker
 * config together. The owner retains all six distinct descriptors, proves
 * the live guest /apex, read-only Runtime backing and publisher occurrence,
 * and keeps mount and writer ownership throughout the call. On success
 * scratch holds the XML bytes and out records the checked local objects.
 * The owner still has to compare XML content to the complete active cohort. */
int guest_apex_info_readback_runtime(const struct guest_apex_runtime_files *files,
        void *scratch, size_t capacity, struct guest_apex_runtime_sample *out);

#endif
