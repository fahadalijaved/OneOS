#ifndef ONEOS_GUEST_CLASSPATH_READBACK_H
#define ONEOS_GUEST_CLASSPATH_READBACK_H

#include <stddef.h>
#include <stdint.h>

enum { GUEST_CLASSPATH_MAX_BYTES = 64 * 1024 };

struct guest_classpath_directories {
    int root_fd, data_fd, system_fd, environ_fd;
};

struct guest_classpath_directory_identity {
    uint64_t mount_id, inode;
    uint32_t device_major, device_minor, mode, uid, gid, links;
};

struct guest_classpath_start {
    struct guest_classpath_directories directories;
    struct guest_classpath_directory_identity identity[4];
};

struct guest_classpath_sample {
    uint64_t mount_id, inode;
    size_t bytes;
    unsigned char sha256[32];
    unsigned char identity_sha256[32];
};

/* Borrow the four held directories and observe that classpath and classpath.tmp
 * are absent at the start of a fresh publication. The owner proves that the
 * root and data mounts belong to the intended isolated guest and retains them
 * through consumption. It excludes other writers and namespace changes. */
int guest_classpath_begin(const struct guest_classpath_directories *directories,
        struct guest_classpath_start *out);

/* After the owner settles the exact producer, borrow its final file opened
 * from the held environ directory. Compare exact canonical bytes from an
 * independently verified fragment/JAR cohort and effective property sample.
 * The start and expected bytes stay immutable. All descriptors are borrowed
 * without opening, closing or moving their cursors. Both calls leave output
 * untouched on refusal. This observes publication, not producer identity,
 * access labels, durability or effective consumer environment. */
int guest_classpath_readback(const struct guest_classpath_start *start, int file_fd,
        const void *expected, size_t expected_bytes, struct guest_classpath_sample *out);

/* Rejoin the exact post-publication sample after other launch checks. The
 * owner retains the descriptor and excludes writers through consumption. */
int guest_classpath_recheck_file(const struct guest_classpath_start *start, int file_fd,
        const struct guest_classpath_sample *sample);

#endif
