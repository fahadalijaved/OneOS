#define _POSIX_C_SOURCE 200809L

#include "guest_scope_events.h"

#include <unistd.h>

enum guest_scope_population guest_scope_events_read(int events_fd) {
    char bytes[GUEST_SCOPE_EVENTS_BYTES + 1];

    if (pread(events_fd, bytes, sizeof(bytes), 0) != GUEST_SCOPE_EVENTS_BYTES ||
        pread(events_fd, bytes + GUEST_SCOPE_EVENTS_BYTES, 1, GUEST_SCOPE_EVENTS_BYTES) != 0)
        return GUEST_SCOPE_POPULATION_UNKNOWN;

    return guest_scope_events_parse(bytes, GUEST_SCOPE_EVENTS_BYTES);
}
