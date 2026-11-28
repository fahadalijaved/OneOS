#ifndef ONEOS_GUEST_ZYGOTE_STDIO_OWNER_H
#define ONEOS_GUEST_ZYGOTE_STDIO_OWNER_H

enum guest_zygote_stdio_state {
    GUEST_ZYGOTE_STDIO_NEW,
    GUEST_ZYGOTE_STDIO_INSTALLING,
    GUEST_ZYGOTE_STDIO_READY,
    GUEST_ZYGOTE_STDIO_RETIRED,
};

struct guest_zygote_stdio_owner {
    enum guest_zygote_stdio_state state;
    unsigned installed;
};

/* Install the admitted null description in empty slots 0 through 2. Pass a
 * zeroed owner and borrow a caller-owned CLOEXEC source FD of at least 5.
 * The caller owns the genuine source and the final single-threaded child's
 * independent FD table, and excludes FD changes throughout installation and
 * entry. The installed mask records successful dup3 calls. Preflight refusal
 * leaves the owner unchanged. Once installation begins, any failure retires
 * the owner and requires retirement of the actual child. No descriptor is
 * closed or restored here. */
int guest_zygote_stdio_install(int null_fd, struct guest_zygote_stdio_owner *owner);

#endif
