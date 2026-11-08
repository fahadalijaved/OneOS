#include "guest_scope_events.h"

#include <string.h>

static const char populated_key[] = "populated ";
static const char frozen_key[] = "frozen ";

/* Each row is its key and separator, one value byte, and LF. */
static int parse_flag(const char *row, const char *key, size_t key_length) {
    if (memcmp(row, key, key_length) != 0 || row[key_length + 1] != '\n')
        return -1;
    if (row[key_length] == '0')
        return 0;
    if (row[key_length] == '1')
        return 1;
    return -1;
}

enum guest_scope_population guest_scope_events_parse(const char *input, size_t length) {
    const char *populated;
    const char *frozen;
    int value;

    if (!input || length != GUEST_SCOPE_EVENTS_BYTES)
        return GUEST_SCOPE_POPULATION_UNKNOWN;

    /* Key order is immaterial. Each row still has to match exactly. */
    if (input[0] == 'f') {
        frozen = input;
        populated = input + sizeof(frozen_key) + 1;
    } else {
        populated = input;
        frozen = input + sizeof(populated_key) + 1;
    }

    value = parse_flag(populated, populated_key, sizeof(populated_key) - 1);
    if (value < 0 || parse_flag(frozen, frozen_key, sizeof(frozen_key) - 1) < 0)
        return GUEST_SCOPE_POPULATION_UNKNOWN;
    return value == 0 ? GUEST_SCOPE_POPULATION_EMPTY : GUEST_SCOPE_POPULATION_LIVE;
}
