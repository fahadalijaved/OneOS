#define _GNU_SOURCE

#include "guest_tree_stop_backing.h"
#include "guest_tree_stop_carrier_reader.h"
#include "guest_tree_stop_emit.h"
#include "guest_tree_stop_wait.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define READER "{\"schema\":\"oneos-file-stage-stop-reader/v1\","

static int write_window(const char *frame, int length, size_t capacity) {
    return length > 0 && (size_t)length < capacity
        && fwrite(frame, 1, (size_t)length, stdout) == (size_t)length && fflush(stdout) == 0 ? 0 : -1;
}

static int elapsed_ms(uint64_t *value) {
    struct timespec now;
    if (clock_gettime(CLOCK_BOOTTIME, &now) < 0 || now.tv_sec < 0
            || (uint64_t)now.tv_sec > (UINT64_MAX - 999U) / 1000U
            || now.tv_nsec < 0 || now.tv_nsec >= 1000000000L) return -1;
    *value = (uint64_t)now.tv_sec * 1000U + (uint64_t)now.tv_nsec / 1000000U;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--observe-carrier-stop-v1")) return 2;
    struct guest_tree_stop_carrier_reader *owner = NULL;
    struct guest_tree_stop_carrier_sample sample;
    struct guest_tree_stop_backing_sample backing;
    char frame[8192];
    int stage_fd = -1, carrier_fd = -1, post_length = 0;
    uint64_t pre_end = 0, closed_ms;
    const int owner_pid = (int)getpid();

    if (guest_tree_stop_carrier_open(&owner) < 0 || guest_tree_stop_carrier_measure(owner, &sample) < 0) goto close;
    stage_fd = sample.stage_fd;
    carrier_fd = sample.carrier_fd;
    pre_end = sample.end_ms;
    int length = guest_tree_stop_emit(frame, sizeof(frame), GUEST_TREE_STOP_WINDOW_PRE, &sample, NULL);
    if (length <= 0 || (size_t)length >= sizeof(frame)) goto close;
    if (fprintf(stdout, READER "\"event\":\"opened\",\"ownerPid\":%d,\"stageFd\":%d,\"carrierFd\":%d,"
                "\"stageOpenedElapsedMs\":%" PRIu64 ",\"carrierOpenedElapsedMs\":%" PRIu64 "}\n",
                owner_pid, stage_fd, carrier_fd, sample.stage_open_ms, sample.carrier_open_ms) < 0
            || write_window(frame, length, sizeof(frame)) < 0) goto close;

    if (guest_tree_stop_wait_after() < 0 || guest_tree_stop_carrier_measure(owner, &sample) < 0
            || sample.stage_fd != stage_fd || sample.carrier_fd != carrier_fd || sample.start_ms < pre_end
            || guest_tree_stop_backing_read(stage_fd, &backing) < 0) goto close;
    post_length = guest_tree_stop_emit(frame, sizeof(frame), GUEST_TREE_STOP_WINDOW_POST, &sample, &backing);

close:
    if (owner && guest_tree_stop_carrier_close(owner) < 0) return 3;
    if (post_length <= 0 || (size_t)post_length >= sizeof(frame) || elapsed_ms(&closed_ms) < 0
            || closed_ms < sample.end_ms || write_window(frame, post_length, sizeof(frame)) < 0) return 3;
    if (fprintf(stdout, READER "\"event\":\"closed\",\"ownerPid\":%d,\"stageFd\":%d,\"carrierFd\":%d,"
                "\"elapsedMs\":%" PRIu64 "}\n", owner_pid, stage_fd, carrier_fd, closed_ms) < 0) return 3;
    return fflush(stdout) == 0 ? 0 : 3;
}
