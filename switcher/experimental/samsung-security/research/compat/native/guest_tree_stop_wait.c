#define _GNU_SOURCE
#include "guest_tree_stop_wait.h"

#include <errno.h>
#include <poll.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define NS_PER_MS UINT64_C(1000000)
#define NS_PER_SECOND UINT64_C(1000000000)
#define WAIT_NS (150 * NS_PER_SECOND)
#define POLL_SLICE_NS (250 * NS_PER_MS)

static int refuse(int error) {
    errno = error;
    return -1;
}

static int boottime_ns(uint64_t *now) {
    struct timespec sample;
    if (clock_gettime(CLOCK_BOOTTIME, &sample) < 0) return -1;
    if (sample.tv_sec < 0 || sample.tv_nsec < 0 || (uint64_t)sample.tv_nsec >= NS_PER_SECOND
            || (uint64_t)sample.tv_sec > (UINT64_MAX - (uint64_t)sample.tv_nsec) / NS_PER_SECOND)
        return refuse(EOVERFLOW);
    *now = (uint64_t)sample.tv_sec * NS_PER_SECOND + (uint64_t)sample.tv_nsec;
    return 0;
}

static int poll_budget(uint64_t deadline) {
    uint64_t now;
    if (boottime_ns(&now) < 0) return -1;
    if (now >= deadline) return refuse(ETIMEDOUT);
    uint64_t remaining = deadline - now;
    /* Recheck BOOTTIME after a short poll because suspend can consume the budget. */
    if (remaining > POLL_SLICE_NS) remaining = POLL_SLICE_NS;
    return (int)((remaining + NS_PER_MS - 1) / NS_PER_MS);
}

int guest_tree_stop_wait_after(void) {
    static const char frame[] = "ONEOS_STOP_OBSERVE_AFTER_V1\n";
    const size_t frame_size = sizeof(frame) - 1;
    char input[sizeof(frame)];
    size_t used = 0;
    uint64_t start;
    if (boottime_ns(&start) < 0) return -1;
    if (start > UINT64_MAX - WAIT_NS) return refuse(EOVERFLOW);
    const uint64_t deadline = start + WAIT_NS;

    for (;;) {
        int budget = poll_budget(deadline);
        if (budget < 0) return -1;
        struct pollfd pending = { .fd = STDIN_FILENO, .events = POLLIN };
        int ready = poll(&pending, 1, budget);
        if (ready < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        if (!ready) continue;
        if (pending.revents & POLLNVAL) return refuse(EBADF);
        if (pending.revents & POLLERR || !(pending.revents & (POLLIN | POLLHUP))) return refuse(EIO);
        if (poll_budget(deadline) < 0) return -1;

        /* The final byte of this buffer admits only the extra-input probe. */
        ssize_t count = read(STDIN_FILENO, input + used, sizeof(input) - used);
        if (count < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        if (poll_budget(deadline) < 0) return -1;
        if (!count) return used == frame_size ? 0 : refuse(EPROTO);
        if ((size_t)count > frame_size - used || memcmp(input + used, frame + used, (size_t)count))
            return refuse(EPROTO);
        used += (size_t)count;
    }
}
