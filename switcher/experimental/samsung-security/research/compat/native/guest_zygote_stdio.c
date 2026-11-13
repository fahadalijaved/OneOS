#define _GNU_SOURCE
#include "guest_zygote_stdio.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>

int oneos_guest_zygote_stdio_validate(void) {
    struct stat expected = {0};

    for (int fd = 0; fd < 3; ++fd) {
        struct stat current;
        if (fstat(fd, &current) < 0) return -1;
        if (!S_ISCHR(current.st_mode) ||
            major(current.st_rdev) != 1 || minor(current.st_rdev) != 3) {
            errno = ENODEV;
            return -1;
        }
        int status = fcntl(fd, F_GETFL);
        if (status < 0) return -1;
        int descriptor = fcntl(fd, F_GETFD);
        if (descriptor < 0) return -1;
        if ((status & O_PATH) != 0 || (status & O_ACCMODE) != O_RDWR ||
            (descriptor & FD_CLOEXEC) != 0) {
            errno = EINVAL;
            return -1;
        }
        if (fd == 0) {
            expected = current;
        } else if (current.st_dev != expected.st_dev || current.st_ino != expected.st_ino) {
            errno = EXDEV;
            return -1;
        }
    }
    return 0;
}
