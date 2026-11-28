#define _GNU_SOURCE
#include "guest_tree_stop_emit.h"

#include "guest_tree_stop_backing.h"
#include "guest_tree_stop_carrier_reader.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/fsverity.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/stat.h>

#define NODE_MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_MNT_ID)
#define CARRIER_MASK (NODE_MASK | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME)
#define STAGE_PATH "/data/local/tmp/oneos-viewprep"

struct output {
    char *buffer;
    size_t capacity, length;
};

static int append(struct output *out, const char *format, ...) __attribute__((format(printf, 2, 3)));

static int append(struct output *out, const char *format, ...) {
    size_t available = out->capacity - out->length;
    va_list args;
    va_start(args, format);
    int count = vsnprintf(out->buffer + out->length, available, format, args);
    va_end(args);
    if (count < 0) return -1;
    if ((size_t)count >= available) {
        errno = ENOSPC;
        return -1;
    }
    out->length += (size_t)count;
    return 0;
}

static int node(struct output *out, uint64_t mount, uint32_t major, uint32_t minor,
        uint64_t inode, uint32_t mode, uint32_t uid, uint32_t gid) {
    if (!mount || !inode) {
        errno = EINVAL;
        return -1;
    }
    return append(out, "{\"mountId\":%" PRIu64 ",\"deviceMajor\":%" PRIu32 ",\"deviceMinor\":%" PRIu32
            ",\"inode\":%" PRIu64 ",\"typeAndMode\":%" PRIu32 ",\"uid\":%" PRIu32 ",\"gid\":%" PRIu32 "}",
            mount, major, minor, inode, mode, uid, gid);
}

static int statx_node(struct output *out, const struct statx *sample) {
    if ((sample->stx_mask & NODE_MASK) != NODE_MASK) {
        errno = EINVAL;
        return -1;
    }
    return node(out, sample->stx_mnt_id, sample->stx_dev_major, sample->stx_dev_minor,
            sample->stx_ino, sample->stx_mode, sample->stx_uid, sample->stx_gid);
}

static int carrier_node(struct output *out, const struct statx *sample) {
    if ((sample->stx_mask & CARRIER_MASK) != CARRIER_MASK
            || sample->stx_mtime.tv_nsec >= 1000000000U || sample->stx_ctime.tv_nsec >= 1000000000U) {
        errno = EINVAL;
        return -1;
    }
    if (append(out, "{\"node\":") < 0 || statx_node(out, sample) < 0) return -1;
    return append(out, ",\"links\":%" PRIu32 ",\"sizeBytes\":%" PRIu64
            ",\"mtimeSec\":%" PRId64 ",\"mtimeNsec\":%" PRIu32
            ",\"ctimeSec\":%" PRId64 ",\"ctimeNsec\":%" PRIu32 "}",
            sample->stx_nlink, (uint64_t)sample->stx_size,
            (int64_t)sample->stx_mtime.tv_sec, sample->stx_mtime.tv_nsec,
            (int64_t)sample->stx_ctime.tv_sec, sample->stx_ctime.tv_nsec);
}

static int object(struct output *out, const char *path, int fd, int flags,
        const struct statx *const samples[4], bool is_carrier) {
    static const char *const keys[] = {"namedBefore", "heldBefore", "namedAfter", "heldAfter"};
    if (append(out, "{\"path\":\"%s\",\"fd\":%d,\"statusFlags\":%d", path, fd, flags) < 0) return -1;
    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); ++i) {
        if (append(out, ",\"%s\":", keys[i]) < 0) return -1;
        int result = is_carrier ? carrier_node(out, samples[i]) : statx_node(out, samples[i]);
        if (result < 0) return -1;
    }
    return append(out, "}");
}

static int measurement(struct output *out, const struct guest_tree_stop_carrier_sample *sample) {
    static const char hex[] = "0123456789abcdef";
    char digest[2 * sizeof(sample->digest) + 1];
    for (size_t i = 0; i < sizeof(sample->digest); ++i) {
        digest[2 * i] = hex[sample->digest[i] >> 4];
        digest[2 * i + 1] = hex[sample->digest[i] & 15];
    }
    digest[sizeof(digest) - 1] = '\0';
    return append(out, "{\"operation\":\"FS_IOC_MEASURE_VERITY\",\"fd\":%d,\"elapsedMs\":%" PRIu64
            ",\"status\":%d,\"algorithm\":%u,\"digestBytes\":%u,\"digestHex\":\"%s\"}",
            sample->carrier_fd, sample->measure_ms, sample->ioctl_result,
            (unsigned)sample->digest_algorithm, (unsigned)sample->digest_size, digest);
}

static int backing_object(struct output *out, const struct guest_tree_stop_backing_sample *sample) {
    static const char *const names[] = {"data", "stage", "backing", "dev", "guard"};
    const struct guest_tree_stop_backing_node *const nodes[] = {
        &sample->data, &sample->stage, &sample->backing, &sample->dev, &sample->guard,
    };
    if (sample->writer_errno != ENOENT || sample->legacy_errno != ENOENT || sample->view_errno != ENOENT) {
        errno = EINVAL;
        return -1;
    }
    if (append(out, "{") < 0) return -1;
    for (size_t i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {
        const struct guest_tree_stop_backing_node *current = nodes[i];
        if (append(out, "%s\"%s\":", i ? "," : "", names[i]) < 0
                || node(out, current->mount_id, current->device_major, current->device_minor,
                        current->inode, current->mode, current->uid, current->gid) < 0) return -1;
    }
    return append(out, ",\"writerErrno\":%d,\"legacyErrno\":%d,\"viewErrno\":%d}",
            sample->writer_errno, sample->legacy_errno, sample->view_errno);
}

static bool readonly(int flags) {
    return flags >= 0 && (flags & (O_ACCMODE | O_PATH)) == O_RDONLY;
}

int guest_tree_stop_emit(char *buffer, size_t capacity, enum guest_tree_stop_window window,
        const struct guest_tree_stop_carrier_sample *sample,
        const struct guest_tree_stop_backing_sample *backing) {
    if (buffer && capacity) buffer[0] = '\0';
    if (!buffer || !capacity || !sample || (window != GUEST_TREE_STOP_WINDOW_PRE
            && window != GUEST_TREE_STOP_WINDOW_POST) || (backing != NULL) != (window == GUEST_TREE_STOP_WINDOW_POST)
            || sample->stage_fd < 3 || sample->carrier_fd < 3 || sample->stage_fd == sample->carrier_fd
            || !readonly(sample->stage_access_flags) || !readonly(sample->access_flags)
            || sample->start_ms > sample->measure_ms || sample->measure_ms > sample->end_ms
            || sample->ioctl_result != 0 || sample->digest_algorithm != FS_VERITY_HASH_ALG_SHA256
            || sample->digest_size != sizeof(sample->digest)) {
        errno = EINVAL;
        return -1;
    }
    struct output out = {buffer, capacity, 0};
    const struct statx *const stage_samples[] = {
        &sample->stage_named_before, &sample->stage_held_before, &sample->stage_named_after, &sample->stage_held_after,
    };
    const struct statx *const carrier_samples[] = {
        &sample->carrier_named_before, &sample->carrier_held_before, &sample->carrier_named_after, &sample->carrier_held_after,
    };
    if (append(&out, "{\"schema\":\"oneos-file-stage-stop-window/v1\",\"window\":\"%s\""
            ",\"startElapsedMs\":%" PRIu64 ",\"endElapsedMs\":%" PRIu64
            ",\"dataMount\":{\"mountPoint\":\"/data\",\"filesystemType\":\"f2fs\",\"mountId\":%" PRIu64
            ",\"deviceMajor\":%" PRIu32 ",\"deviceMinor\":%" PRIu32 "},\"dataHeld\":",
            window == GUEST_TREE_STOP_WINDOW_PRE ? "pre" : "post", sample->start_ms, sample->end_ms,
            (uint64_t)sample->data_held.stx_mnt_id, sample->data_held.stx_dev_major, sample->data_held.stx_dev_minor) < 0
            || statx_node(&out, &sample->data_held) < 0 || append(&out, ",\"stage\":") < 0
            || object(&out, STAGE_PATH, sample->stage_fd, sample->stage_access_flags, stage_samples, false) < 0
            || append(&out, ",\"carrier\":") < 0
            || object(&out, STAGE_PATH "/guest.erofs", sample->carrier_fd, sample->access_flags, carrier_samples, true) < 0
            || append(&out, ",\"measurement\":") < 0 || measurement(&out, sample) < 0
            || append(&out, ",\"backing\":") < 0
            || (backing ? backing_object(&out, backing) : append(&out, "null")) < 0
            || append(&out, "}\n") < 0) {
        buffer[0] = '\0';
        return -1;
    }
    return (int)out.length;
}
