#ifndef ONEOS_STDIO_FIXTURE_SYSMACROS_H
#define ONEOS_STDIO_FIXTURE_SYSMACROS_H

#include <stdint.h>

/* Model Linux's split dev_t encoding, including high major/minor bits. */
static inline unsigned major(uint64_t device) {
    return (unsigned)(((device >> 32) & 0xfffff000U) | ((device >> 8) & 0xfffU));
}

static inline unsigned minor(uint64_t device) {
    return (unsigned)(((device >> 12) & 0xffffff00U) | (device & 0xffU));
}

#endif
