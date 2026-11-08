#ifndef ONEOS_GUEST_ZYGOTE_STDIO_H
#define ONEOS_GUEST_ZYGOTE_STDIO_H

/*
 * Check borrowed FDs 0, 1 and 2 in the owned single-threaded launch child
 * immediately before exec. Requires one null device inode, O_RDWR and no
 * FD_CLOEXEC. Returns 0 or -1 with errno. Does not establish custody.
 */
int oneos_guest_zygote_stdio_validate(void);

#endif
