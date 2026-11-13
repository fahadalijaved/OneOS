#ifndef ONEOS_GUEST_CLASSPATH_JAR_READBACK_H
#define ONEOS_GUEST_CLASSPATH_JAR_READBACK_H

#include <stddef.h>
#include <stdint.h>

enum {
    GUEST_CLASSPATH_JAR_MAX_ANCESTORS = 4,
    GUEST_CLASSPATH_JAR_MAX_BYTES = 64 * 1024 * 1024,
};

struct guest_classpath_jar_pin {
    uint64_t mount_id, bytes;
    unsigned char sha256[32];
    uint64_t ancestor_mount_ids[GUEST_CLASSPATH_JAR_MAX_ANCESTORS];
    uint64_t backing_inode;
    uint32_t backing_device_major, backing_device_minor;
};

struct guest_classpath_jar_sample {
    uint64_t mount_id, inode, bytes;
    uint32_t device_major, device_minor;
    unsigned char sha256[32];
    unsigned char identity_sha256[32];
};

/* Borrow the guest root followed by each exact parent directory for a fixed
 * /system/framework or stable /apex/<module>/javalib path, plus the read FD.
 * The owner supplies the expected mounts in that namespace and the selected
 * cohort's independent size and digest. A separately admitted file bind can
 * have a mount ID distinct from its immediate parent. Supply its backing
 * device and inode from the independently held source. The owner proves the
 * source name and excludes namespace and file writers through use.
 * Compare names, identities and exact bytes without reopening or closing FDs
 * or moving their cursors. On refusal, out remains untouched. */
int guest_classpath_jar_readback(const char *absolute_path, const int *ancestors,
        size_t ancestor_count, int jar_fd, const struct guest_classpath_jar_pin *pin,
        struct guest_classpath_jar_sample *out);

/* Rejoin the same retained names and descriptors to the first observation.
 * Exclusion of writers remains an owner obligation through consumption. */
int guest_classpath_jar_recheck(const char *absolute_path, const int *ancestors,
        size_t ancestor_count, int jar_fd, const struct guest_classpath_jar_sample *sample);

#endif
