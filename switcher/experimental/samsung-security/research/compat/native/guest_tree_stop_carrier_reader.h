#ifndef ONEOS_GUEST_TREE_STOP_CARRIER_READER_H
#define ONEOS_GUEST_TREE_STOP_CARRIER_READER_H

#include <stdint.h>
#include <sys/stat.h>

struct guest_tree_stop_carrier_reader;

struct guest_tree_stop_carrier_sample {
    int stage_fd, carrier_fd, stage_access_flags, access_flags, ioctl_result;
    struct statx data_held;
    struct statx stage_held_before, stage_named_before, stage_held_after, stage_named_after;
    struct statx carrier_held_before, carrier_named_before, carrier_held_after, carrier_named_after;
    uint16_t digest_algorithm, digest_size;
    unsigned char digest[32];
    /* CLOCK_BOOTTIME milliseconds. measure_ms follows the ioctl return. */
    uint64_t stage_open_ms, carrier_open_ms, start_ms, measure_ms, end_ms;
};

/* Root process leader, one fixed path attempt. Initialize *out to NULL and
 * retain any returned owner on refusal so it can close its acquired cells. */
int guest_tree_stop_carrier_open(struct guest_tree_stop_carrier_reader **out);

/* Verify the same held path and exact kernel measurement in this interval.
 * Both descriptor numbers are borrowed while the owner is open. Zero a
 * nonnull sample on refusal. The caller separately authenticates the view. */
int guest_tree_stop_carrier_measure(struct guest_tree_stop_carrier_reader *reader,
        struct guest_tree_stop_carrier_sample *out);

/* Close the reader's local cells once. The caller has finished using borrows. */
int guest_tree_stop_carrier_close(struct guest_tree_stop_carrier_reader *reader);

#endif
