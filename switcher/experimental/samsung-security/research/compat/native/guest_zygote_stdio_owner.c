#define _GNU_SOURCE
#include "guest_zygote_stdio_owner.h"

#include "guest_zygote_stdio.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

static int refuse(int error) {
    errno = error;
    return -1;
}

static int check_source(int fd) {
    struct stat node;
    if (fstat(fd, &node) < 0) return -1;
    if (!S_ISCHR(node.st_mode) || major(node.st_rdev) != 1 || minor(node.st_rdev) != 3)
        return refuse(ENODEV);
    int status = fcntl(fd, F_GETFL);
    if (status < 0) return -1;
    if ((status & (O_PATH | O_ACCMODE)) != O_RDWR) return refuse(EINVAL);
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : refuse(EINVAL);
}

int guest_zygote_stdio_install(int null_fd, struct guest_zygote_stdio_owner *owner) {
    if (!owner || null_fd < 5) return refuse(EINVAL);
    if (owner->state != GUEST_ZYGOTE_STDIO_NEW || owner->installed) return refuse(EALREADY);
    if (check_source(null_fd) < 0) return -1;
    for (int slot = 0; slot < 3; ++slot) {
        if (fcntl(slot, F_GETFD) >= 0) return refuse(EBUSY);
        if (errno != EBADF) return -1;
    }

    owner->state = GUEST_ZYGOTE_STDIO_INSTALLING;
    for (int slot = 0; slot < 3; ++slot) {
        if (dup3(null_fd, slot, 0) < 0) goto retired;
        owner->installed |= 1u << slot;
    }
    if (oneos_guest_zygote_stdio_validate() < 0) goto retired;
    owner->state = GUEST_ZYGOTE_STDIO_READY;
    return 0;

retired:
    owner->state = GUEST_ZYGOTE_STDIO_RETIRED;
    return -1;
}
