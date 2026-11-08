#define _GNU_SOURCE
#include "guest_zygote_slot_owner.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

enum { FIRST_RETAINED = 5 };

static int refuse(int error) {
    errno = error;
    return -1;
}

static int check_cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : refuse(EPERM);
}

static int check_vacant(int fd) {
    if (fcntl(fd, F_GETFD) >= 0) return refuse(EBUSY);
    return errno == EBADF ? 0 : -1;
}

static int check_control_fds(int *const cells[], unsigned count) {
    unsigned claimed = 0;
    for (unsigned i = 0; i < count; ++i) {
        int fd = *cells[i];
        if (fd < 0) return refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (*cells[j] == fd) return refuse(EINVAL);
        }
        if (check_cloexec(fd) < 0) return -1;
        if (fd < FIRST_RETAINED) claimed |= 1u << fd;
    }
    for (int fd = 0; fd < FIRST_RETAINED; ++fd) {
        if (!(claimed & (1u << fd)) && check_vacant(fd) < 0) return -1;
    }
    return 0;
}

static int close_owned(int *cell, struct guest_zygote_slot_owner *owner) {
    int fd = *cell;
    *cell = -1;
    if (close(fd) == 0) return 0;
    owner->close_error = errno;
    return -1;
}

static int lift_control_fd(int *cell, struct guest_zygote_slot_owner *owner) {
    if (*cell >= FIRST_RETAINED) return 0;
    int original = *cell;
    int high = fcntl(original, F_DUPFD_CLOEXEC, FIRST_RETAINED);
    if (high < 0) return -1;
    *cell = high;
    return close_owned(&original, owner);
}

static int check_reservations(const struct guest_zygote_slot_owner *owner) {
    for (int fd = 0; fd < FIRST_RETAINED; ++fd) {
        if (owner->reserved[fd] != fd) return refuse(ESTALE);
        struct stat current;
        if (check_cloexec(fd) < 0 || fstat(fd, &current) < 0) return -1;
        if (!S_ISFIFO(current.st_mode) || current.st_dev != owner->device || current.st_ino != owner->inode)
            return refuse(ESTALE);
        int status = fcntl(fd, F_GETFL);
        if (status < 0) return -1;
        int expected = fd == 1 ? O_WRONLY : O_RDONLY;
        if ((status & (O_PATH | O_ACCMODE)) != expected) return refuse(ESTALE);
    }
    return 0;
}

int guest_zygote_slots_reserve(struct guest_zygote_control_fds *owned,
        struct guest_zygote_slot_owner *owner) {
    if (!owned || !owner) return refuse(EINVAL);
    if (owner->state != GUEST_ZYGOTE_SLOTS_NEW) return refuse(EALREADY);

    int *const cells[] = {&owned->control, &owned->witnesses[0], &owned->witnesses[1], &owned->witnesses[2]};
    const unsigned count = sizeof(cells) / sizeof(cells[0]);
    if (check_control_fds(cells, count) < 0) return -1;
    *owner = (struct guest_zygote_slot_owner) {
        .state = GUEST_ZYGOTE_SLOTS_RESERVING, .reserved = {-1, -1, -1, -1, -1},
    };
    for (unsigned i = 0; i < count; ++i) {
        if (lift_control_fd(cells[i], owner) < 0) goto retire;
    }

    int pipe_fds[2];
    if (pipe2(pipe_fds, O_CLOEXEC) < 0) goto retire;
    owner->reserved[0] = pipe_fds[0];
    owner->reserved[1] = pipe_fds[1];
    if (pipe_fds[0] != 0 || pipe_fds[1] != 1) {
        errno = ESTALE;
        goto retire;
    }

    struct stat identity;
    if (fstat(pipe_fds[0], &identity) < 0) goto retire;
    if (!S_ISFIFO(identity.st_mode) || !identity.st_ino) {
        errno = ESTALE;
        goto retire;
    }
    owner->device = identity.st_dev;
    owner->inode = identity.st_ino;
    for (int fd = 2; fd < FIRST_RETAINED; ++fd) {
        owner->reserved[fd] = fcntl(pipe_fds[0], F_DUPFD_CLOEXEC, fd);
        if (owner->reserved[fd] < 0) goto retire;
        if (owner->reserved[fd] != fd) {
            errno = ESTALE;
            goto retire;
        }
    }
    if (check_reservations(owner) < 0) goto retire;
    owner->state = GUEST_ZYGOTE_SLOTS_HELD;
    return 0;

retire:
    owner->state = GUEST_ZYGOTE_SLOTS_RETIRED;
    return -1;
}

int guest_zygote_slots_release(struct guest_zygote_slot_owner *owner) {
    if (!owner) return refuse(EINVAL);
    if (owner->state != GUEST_ZYGOTE_SLOTS_HELD)
        return refuse(owner->close_error ? owner->close_error : EALREADY);

    owner->state = GUEST_ZYGOTE_SLOTS_RELEASING;
    if (check_reservations(owner) < 0) goto retire;
    for (int fd = 0; fd < FIRST_RETAINED; ++fd) {
        if (close_owned(&owner->reserved[fd], owner) < 0) goto retire;
    }
    for (int fd = 0; fd < FIRST_RETAINED; ++fd) {
        if (check_vacant(fd) < 0) goto retire;
    }
    owner->state = GUEST_ZYGOTE_SLOTS_RELEASED;
    return 0;

retire:
    owner->state = GUEST_ZYGOTE_SLOTS_RETIRED;
    return -1;
}
