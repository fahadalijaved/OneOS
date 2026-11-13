#include "guest_scope_events.h"

#include <stdio.h>

#define ROW(bytes, expected) { #bytes, bytes, sizeof(bytes) - 1, expected }

static const struct {
    const char *name;
    const char *bytes;
    size_t length;
    enum guest_scope_population expected;
} fixtures[] = {
    ROW("populated 0\nfrozen 0\n", GUEST_SCOPE_POPULATION_EMPTY),
    ROW("populated 0\nfrozen 1\n", GUEST_SCOPE_POPULATION_EMPTY),
    ROW("populated 1\nfrozen 0\n", GUEST_SCOPE_POPULATION_LIVE),
    ROW("populated 1\nfrozen 1\n", GUEST_SCOPE_POPULATION_LIVE),
    ROW("frozen 0\npopulated 0\n", GUEST_SCOPE_POPULATION_EMPTY),
    ROW("frozen 1\npopulated 0\n", GUEST_SCOPE_POPULATION_EMPTY),
    ROW("frozen 0\npopulated 1\n", GUEST_SCOPE_POPULATION_LIVE),
    ROW("frozen 1\npopulated 1\n", GUEST_SCOPE_POPULATION_LIVE),
    ROW("", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("frozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\npopulated 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\npopulated 1\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("frozen 0\nfrozen 1\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0\npopulated 1\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 2\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated -1\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 00\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 2\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("frozen x\npopulated 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfuture 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("Populated 0\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated\t0\nfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen\t0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\rfrozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\r\nfrozen 0\r\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\0frozen 0\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0\0", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0\n\0", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0\n\n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen \n", GUEST_SCOPE_POPULATION_UNKNOWN),
    ROW("populated 0\nfrozen 0 ", GUEST_SCOPE_POPULATION_UNKNOWN),
};

int main(void) {
    const char exact[] = {
        'p', 'o', 'p', 'u', 'l', 'a', 't', 'e', 'd', ' ', '0', '\n',
        'f', 'r', 'o', 'z', 'e', 'n', ' ', '0', '\n'
    };
    const char reversed[] = "frozen 0\npopulated 0\n";
    size_t i;

    for (i = 0; i < sizeof(fixtures) / sizeof(fixtures[0]); ++i) {
        if (guest_scope_events_parse(fixtures[i].bytes, fixtures[i].length) != fixtures[i].expected) {
            fprintf(stderr, "unexpected result for %s\n", fixtures[i].name);
            return 1;
        }
    }

    for (i = 0; i < sizeof(exact); ++i) {
        if (guest_scope_events_parse(exact, i) != GUEST_SCOPE_POPULATION_UNKNOWN ||
                guest_scope_events_parse(reversed, i) != GUEST_SCOPE_POPULATION_UNKNOWN) {
            fprintf(stderr, "accepted partial input at length %zu\n", i);
            return 1;
        }
    }

    if (guest_scope_events_parse(NULL, GUEST_SCOPE_EVENTS_BYTES) != GUEST_SCOPE_POPULATION_UNKNOWN ||
            guest_scope_events_parse(exact, sizeof(exact)) != GUEST_SCOPE_POPULATION_EMPTY) {
        fprintf(stderr, "unexpected null or exact-span result\n");
        return 1;
    }

    printf("PASS %zu cgroup.events byte fixtures\n",
           sizeof(fixtures) / sizeof(fixtures[0]) + 2 * sizeof(exact) + 2);
    return 0;
}
