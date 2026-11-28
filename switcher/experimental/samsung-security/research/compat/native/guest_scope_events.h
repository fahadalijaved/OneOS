#ifndef ONEOS_GUEST_SCOPE_EVENTS_H
#define ONEOS_GUEST_SCOPE_EVENTS_H

#include <stddef.h>

enum { GUEST_SCOPE_EVENTS_BYTES = 21 };

enum guest_scope_population {
    GUEST_SCOPE_POPULATION_UNKNOWN = 0,
    GUEST_SCOPE_POPULATION_EMPTY,
    GUEST_SCOPE_POPULATION_LIVE
};

/* Parse the exact two-key cgroup2 events profile (populated and frozen, LF).
 * For the accepted length, input must point to that many readable bytes.
 * The owner must read the actual held generation from offset zero through
 * EOF and reject incomplete reads. EMPTY describes only this sample. */
enum guest_scope_population guest_scope_events_parse(const char *input, size_t length);

/* Borrow an already admitted, retained cgroup.events descriptor. Read from
 * offset zero and confirm EOF without changing its cursor or ownership.
 * Short reads, excess bytes, and read errors produce UNKNOWN. The caller
 * owns scope identity, ingress cutoff, and process-drain checks. */
enum guest_scope_population guest_scope_events_read(int events_fd);

#endif
