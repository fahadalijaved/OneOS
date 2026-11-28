#ifndef ONEOS_GUEST_LINKERCONFIG_SEED_H
#define ONEOS_GUEST_LINKERCONFIG_SEED_H

#include "guest_linkerconfig_output.h"

/*
 * Seed an already-admitted, exclusive empty tmpfs at the visible guest
 * /linkerconfig. The function borrows the caller's root_fd and directory_fd.
 * Success transfers the read-only base_fd in out. On failure, out stays
 * unchanged and the caller retires the private target, which may have
 * changed. This does not mount, select a bootstrap view, or run a producer.
 */
int guest_linkerconfig_seed_target(int root_fd, int directory_fd,
        struct guest_linkerconfig_generation_start *out);

#endif
