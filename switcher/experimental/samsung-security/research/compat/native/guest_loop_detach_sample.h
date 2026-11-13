#ifndef ONEOS_GUEST_LOOP_DETACH_SAMPLE_H
#define ONEOS_GUEST_LOOP_DETACH_SAMPLE_H

#include <stddef.h>
#include <stdint.h>

struct guest_loop_sysfs_line {
    const char *bytes;
    size_t length;
};

enum guest_loop_group_observation {
    GUEST_LOOP_GROUP_UNOBSERVED = 0,
    GUEST_LOOP_GROUP_PRESENT,
    GUEST_LOOP_GROUP_ABSENT,
    GUEST_LOOP_GROUP_IO_ERROR
};

struct guest_loop_sysfs_sample {
    struct guest_loop_sysfs_line diskseq_before;
    struct guest_loop_sysfs_line dev;
    struct guest_loop_sysfs_line size;
    enum guest_loop_group_observation loop_group;
    struct guest_loop_sysfs_line diskseq_after;
};

enum guest_loop_detach_result {
    GUEST_LOOP_DETACH_UNKNOWN = 0,
    GUEST_LOOP_OLD_ATTACHMENT_DETACHED_SAMPLE
};

/*
 * Byte validation only. The owner supplies complete offset-zero-to-EOF
 * lines, with fresh diskseq reads before and after dev, size and the group
 * observation in EACH sample. Accepted lengths require readable buffers.
 * ABSENT means positively established absence in the held live directory,
 * not an I/O error, unreadable/deleted anchor or unattempted observation.
 *
 * The owner must establish same-boot, same-gendisk sysfs custody, exclusive
 * mutator scope and actual AUTOCLEAR opener retirement outside this helper.
 * held_dev values and held_diskseq come from the original owned block FD.
 * The original sample describes the confirmed nonempty attachment. The
 * later sample is after the original opener was consumed and the owner's
 * other local teardown gates completed. A matching result describes old
 * attachment detach only, with no Lo_unbound or cleanup proof.
 */
enum guest_loop_detach_result guest_loop_detach_sample_check(
        uint32_t held_major, uint32_t held_minor, uint64_t held_diskseq,
        const struct guest_loop_sysfs_sample *original,
        const struct guest_loop_sysfs_sample *later);

#endif
