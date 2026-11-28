#define _GNU_SOURCE

#include "guest_tree_stop_backing.h"
#include "guest_tree_stop_carrier_reader.h"
#include "guest_tree_stop_emit.h"
#include "guest_tree_stop_proc_session.h"
#include "guest_tree_stop_reader_identity.h"
#include "guest_tree_stop_wait.h"

#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define READER "{\"schema\":\"oneos-file-stage-stop-reader/v1\","

static int parse_pid(const char *text, pid_t *pid) {
    unsigned value = 0;
    if (*text < '1' || *text > '9') return -1;
    for (; *text; ++text) {
        if (*text < '0' || *text > '9') return -1;
        unsigned digit = (unsigned)(*text - '0');
        if (value > ((unsigned)INT_MAX - digit) / 10U) return -1;
        value = 10U * value + digit;
    }
    *pid = (pid_t)value;
    return 0;
}

static int elapsed_ms(uint64_t *value) {
    struct timespec now;
    if (clock_gettime(CLOCK_BOOTTIME, &now) < 0 || now.tv_sec < 0
            || (uint64_t)now.tv_sec > (UINT64_MAX - 999U) / 1000U
            || now.tv_nsec < 0 || now.tv_nsec >= 1000000000L) return -1;
    *value = (uint64_t)now.tv_sec * 1000U + (uint64_t)now.tv_nsec / 1000000U;
    return 0;
}

static int write_window(const char *frame, int length, size_t capacity) {
    return length > 0 && (size_t)length < capacity
        && fwrite(frame, 1, (size_t)length, stdout) == (size_t)length ? 0 : -1;
}

static int write_identity(const char *phase, uint64_t elapsed, const struct guest_tree_stop_reader_identity *id) {
    if (printf("{\"schema\":\"oneos-file-stage-stop-identity/v2\",\"phase\":\"%s\",\"elapsedMs\":%" PRIu64 ","
                "\"bootId\":\"%s\",\"mountNamespace\":{\"deviceMajor\":%" PRIu32 ",\"deviceMinor\":%" PRIu32
                ",\"inode\":%" PRIu64 "},\"timeNamespace\":{\"deviceMajor\":%" PRIu32 ",\"deviceMinor\":%" PRIu32
                ",\"inode\":%" PRIu64 "},\"procRoot\":{\"mountId\":%" PRIu64
                ",\"deviceMajor\":%" PRIu32 ",\"deviceMinor\":%" PRIu32 ",\"inode\":%" PRIu64 "},"
                "\"reader\":{\"pid\":%d,\"startTicks\":%" PRIu64 ",\"uid\":%" PRIu32 ",\"euid\":%" PRIu32
                ",\"fsuid\":%" PRIu32 ",\"gid\":%" PRIu32 ",\"egid\":%" PRIu32 ",\"fsgid\":%" PRIu32 ",\"groups\":[",
                phase, elapsed, id->boot_id, id->mount_ns_device_major, id->mount_ns_device_minor, id->mount_ns_inode,
                id->time_ns_device_major, id->time_ns_device_minor, id->time_ns_inode,
                id->proc_mount_id, id->proc_device_major, id->proc_device_minor, id->proc_root_inode,
                (int)id->birth.pid, id->birth.start_ticks, id->uid, id->euid, id->fsuid, id->gid, id->egid, id->fsgid) < 0)
        return -1;
    for (uint32_t i = 0; i < id->group_count; ++i) {
        if (printf("%s%" PRIu32, i ? "," : "", id->groups[i]) < 0) return -1;
    }
    return printf("],\"selinuxContext\":\"%s\"}}\n", id->selinux_context) < 0 ? -1 : 0;
}

static int write_process(const char *phase, const char *role, const struct guest_tree_stop_proc_observation *sample) {
    return printf("{\"schema\":\"oneos-file-stage-stop-process/v2\",\"phase\":\"%s\",\"role\":\"%s\","
                "\"pid\":%d,\"startTicks\":%" PRIu64 ",\"errno\":%d,\"lookupStartedElapsedMs\":%" PRIu64
                ",\"sampleElapsedMs\":%" PRIu64 ",\"pidfd\":%d,\"pollBeforeCount\":%d,\"pollAfterCount\":%d,"
                "\"pollBeforeRevents\":%d,\"pollAfterRevents\":%d}\n",
                phase, role, (int)sample->pid, sample->birth.start_ticks, sample->lookup_errno,
                sample->started_ms, sample->elapsed_ms, sample->pidfd, sample->poll_before_rc, sample->poll_after_rc,
                sample->poll_before_revents, sample->poll_after_revents)
        < 0 ? -1 : 0;
}

static int write_processes(const char *phase, const struct guest_tree_stop_proc_session_sample *pair) {
    if (write_process(phase, "controller", &pair->controller) < 0) return -1;
    return write_process(phase, "child", &pair->child);
}

int main(int argc, char **argv) {
    const pid_t self = getpid();
    pid_t controller, child;
    if (argc != 4 || strcmp(argv[1], "--observe-session-stop-v2")
            || parse_pid(argv[2], &controller) < 0 || parse_pid(argv[3], &child) < 0
            || controller == child || controller == self || child == self) return 2;

    struct guest_tree_stop_proc_session *proc = NULL;
    struct guest_tree_stop_carrier_reader *carrier = NULL;
    struct guest_tree_stop_reader_identity before_id, after_id;
    struct guest_tree_stop_carrier_sample before, after;
    struct guest_tree_stop_proc_session_sample prior, first, last;
    struct guest_tree_stop_backing_sample backing;
    uint64_t before_ms, after_ms, closed_ms;
    char frame[GUEST_TREE_STOP_EMIT_CAPACITY];
    int post_length = -1;

    if (guest_tree_stop_proc_session_open(controller, child, &proc) < 0) goto close;
    int proc_fd = guest_tree_stop_proc_session_fd(proc);
    if (proc_fd < 0 || guest_tree_stop_reader_identity_read(proc_fd, &before_id) < 0
            || before_id.birth.pid != self || elapsed_ms(&before_ms) < 0
            || guest_tree_stop_carrier_open(&carrier) < 0 || guest_tree_stop_carrier_measure(carrier, &before) < 0
            || before.stage_open_ms < before_ms
            || guest_tree_stop_proc_session_sample(proc, GUEST_TREE_STOP_PROC_LIVE, &prior) < 0
            || prior.controller.started_ms < before.end_ms) goto close;

    int length = guest_tree_stop_emit(frame, sizeof(frame), GUEST_TREE_STOP_WINDOW_PRE, &before, NULL);
    if (length <= 0 || (size_t)length >= sizeof(frame) || write_identity("pre", before_ms, &before_id) < 0
            || printf(READER "\"event\":\"opened\",\"ownerPid\":%d,\"stageFd\":%d,\"carrierFd\":%d,"
                "\"stageOpenedElapsedMs\":%" PRIu64 ",\"carrierOpenedElapsedMs\":%" PRIu64 "}\n",
                (int)self, before.stage_fd, before.carrier_fd, before.stage_open_ms, before.carrier_open_ms) < 0
            || write_window(frame, length, sizeof(frame)) < 0 || write_processes("pre", &prior) < 0
            || fflush(stdout) < 0) goto close;

    if (guest_tree_stop_wait_after() < 0
            || guest_tree_stop_reader_identity_read(proc_fd, &after_id) < 0
            || !guest_tree_stop_reader_identity_equal(&before_id, &after_id)
            || guest_tree_stop_proc_session_sample(proc, GUEST_TREE_STOP_PROC_ABSENT, &first) < 0
            || first.controller.started_ms <= prior.child.elapsed_ms
            || guest_tree_stop_carrier_measure(carrier, &after) < 0
            || after.stage_fd != before.stage_fd || after.carrier_fd != before.carrier_fd
            || after.start_ms < first.child.elapsed_ms || after.start_ms <= before.end_ms
            || guest_tree_stop_backing_read(after.stage_fd, &backing) < 0) goto close;
    length = guest_tree_stop_emit(frame, sizeof(frame), GUEST_TREE_STOP_WINDOW_POST, &after, &backing);
    if (length <= 0 || (size_t)length >= sizeof(frame)) goto close;
    int carrier_close = guest_tree_stop_carrier_close(carrier);
    carrier = NULL;
    if (carrier_close < 0 || guest_tree_stop_proc_session_sample(proc, GUEST_TREE_STOP_PROC_ABSENT, &last) < 0
            || last.controller.started_ms < after.end_ms || last.controller.elapsed_ms <= first.child.elapsed_ms
            || guest_tree_stop_reader_identity_read(proc_fd, &after_id) < 0
            || !guest_tree_stop_reader_identity_equal(&before_id, &after_id)
            || elapsed_ms(&after_ms) < 0 || after_ms < last.child.elapsed_ms) goto close;
    post_length = length;

close:
    if (carrier && guest_tree_stop_carrier_close(carrier) < 0) post_length = -1;
    if (proc && guest_tree_stop_proc_session_close(proc) < 0) post_length = -1;
    if (post_length <= 0 || (size_t)post_length >= sizeof(frame)
            || elapsed_ms(&closed_ms) < 0 || closed_ms < after_ms
            || write_processes("post-start", &first) < 0
            || write_window(frame, post_length, sizeof(frame)) < 0 || write_processes("post-end", &last) < 0
            || write_identity("post", after_ms, &after_id) < 0) return 3;
    if (printf(READER "\"event\":\"closed\",\"ownerPid\":%d,\"stageFd\":%d,\"carrierFd\":%d,"
                "\"elapsedMs\":%" PRIu64 "}\n", (int)self, before.stage_fd, before.carrier_fd, closed_ms) < 0)
        return 3;
    return fflush(stdout) == 0 ? 0 : 3;
}
