#define _GNU_SOURCE
#include "guest_classpath_jar_readback.h"

#include "guest_classpath_identity_digest.h"
#include "guest_readback_identity.h"

#include <string.h>
#include <unistd.h>

enum { PATH_BYTES = 241, MAX_ANCESTORS = GUEST_CLASSPATH_JAR_MAX_ANCESTORS };

struct jar_request {
    char path[PATH_BYTES], *parts[MAX_ANCESTORS];
    int fds[MAX_ANCESTORS + 1];
};

static int name_char(unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
            || c == '_' || c == '-' || c == '+' || c == '.';
}

static int path_components(char *path, char **parts, size_t count) {
    char *cursor = path + 1;
    for (size_t i = 0; i < count; ++i) {
        parts[i] = cursor;
        while (name_char((unsigned char)*cursor)) ++cursor;
        size_t length = (size_t)(cursor - parts[i]);
        if (!length || *parts[i] == '.' || *cursor != (i + 1 == count ? '\0' : '/'))
            return guest_readback_refuse(EINVAL);
        if (i + 1 < count) *cursor++ = '\0';
    }
    int system = count == 3 && !strcmp(parts[0], "system") && !strcmp(parts[1], "framework");
    int apex = count == 4 && !strcmp(parts[0], "apex") && !strcmp(parts[2], "javalib");
    if (!system && !apex) return guest_readback_refuse(EINVAL);
    size_t leaf = strlen(parts[count - 1]);
    if (leaf <= 4 || memcmp(parts[count - 1] + leaf - 4, ".jar", 4)) return guest_readback_refuse(EINVAL);
    return 0;
}

static int check_fds(const int *fds, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        if (fds[i] < 0) return guest_readback_refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (fds[i] == fds[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fds[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }
    int flags = fcntl(fds[count - 1], F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    return 0;
}

static int prepare_request(const char *absolute_path, const int *ancestors,
        size_t depth, int jar_fd, struct jar_request *request) {
    if (!absolute_path || !ancestors || depth < 3 || depth > MAX_ANCESTORS || absolute_path[0] != '/')
        return guest_readback_refuse(EINVAL);
    size_t length = strnlen(absolute_path, sizeof(request->path));
    if (length == sizeof(request->path)) return guest_readback_refuse(ENAMETOOLONG);
    memcpy(request->path, absolute_path, length + 1);
    if (path_components(request->path, request->parts, depth) < 0) return -1;
    memcpy(request->fds, ancestors, depth * sizeof(*ancestors));
    request->fds[depth] = jar_fd;
    return check_fds(request->fds, depth + 1);
}

static int snapshot(const int *fds, char *const *parts, size_t depth, struct statx *held) {
    for (size_t i = 0; i <= depth; ++i) {
        if (guest_readback_stat(fds[i], "", &held[i]) < 0) return -1;
        if (i) {
            struct statx named;
            if (guest_readback_stat(fds[i - 1], parts[i - 1], &named) < 0) return -1;
            if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
        }
        int valid_type = i < depth ? S_ISDIR(held[i].stx_mode) : S_ISREG(held[i].stx_mode) && held[i].stx_nlink;
        if (!valid_type) return guest_readback_refuse(EPERM);
        for (size_t j = 0; j < i; ++j) {
            if (held[i].stx_ino == held[j].stx_ino && held[i].stx_dev_major == held[j].stx_dev_major
                    && held[i].stx_dev_minor == held[j].stx_dev_minor) return guest_readback_refuse(EPERM);
        }
    }
    return 0;
}

static int hash_jar(int fd, size_t bytes, unsigned char digest[32]) {
    unsigned char buffer[16384];
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    for (size_t offset = 0; offset < bytes;) {
        size_t remaining = bytes - offset;
        ssize_t got = pread(fd, buffer, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)offset);
        if (got < 0) return -1;
        if (!got) return guest_readback_refuse(EIO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        offset += (size_t)got;
    }
    ssize_t extra = pread(fd, buffer, 1, (off_t)bytes);
    if (extra < 0) return -1;
    if (extra) return guest_readback_refuse(ESTALE);
    guest_tree_sha256_final(&hash, digest);
    return 0;
}

static void hash_identity(const struct jar_request *request, size_t depth,
        const struct statx *held, unsigned char digest[32]) {
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, &depth, sizeof(depth));
    guest_tree_sha256_update(&hash, request->fds, (depth + 1) * sizeof(request->fds[0]));
    for (size_t i = 0; i < depth; ++i)
        guest_tree_sha256_update(&hash, request->parts[i], strlen(request->parts[i]) + 1);
    for (size_t i = 0; i <= depth; ++i) guest_classpath_hash_node(&hash, &held[i]);
    guest_tree_sha256_final(&hash, digest);
}

int guest_classpath_jar_readback(const char *absolute_path, const int *ancestors,
        size_t ancestor_count, int jar_fd, const struct guest_classpath_jar_pin *pin,
        struct guest_classpath_jar_sample *out) {
    if (!pin || !out || !pin->bytes || !pin->mount_id || !pin->backing_inode) return guest_readback_refuse(EINVAL);
    if (pin->bytes > GUEST_CLASSPATH_JAR_MAX_BYTES) return guest_readback_refuse(EFBIG);
    struct jar_request request;
    if (prepare_request(absolute_path, ancestors, ancestor_count, jar_fd, &request) < 0) return -1;
    for (size_t i = 0; i < ancestor_count; ++i) {
        if (!pin->ancestor_mount_ids[i]) return guest_readback_refuse(EINVAL);
    }
    struct statx before[MAX_ANCESTORS + 1], after[MAX_ANCESTORS + 1];
    if (snapshot(request.fds, request.parts, ancestor_count, before) < 0) return -1;
    for (size_t i = 0; i < ancestor_count; ++i) {
        if (before[i].stx_mnt_id != pin->ancestor_mount_ids[i]) return guest_readback_refuse(EXDEV);
    }
    const struct statx *file = &before[ancestor_count];
    if (file->stx_mnt_id != pin->mount_id) return guest_readback_refuse(EXDEV);
    if (file->stx_size != pin->bytes || file->stx_ino != pin->backing_inode
            || file->stx_dev_major != pin->backing_device_major || file->stx_dev_minor != pin->backing_device_minor)
        return guest_readback_refuse(ESTALE);
    struct guest_classpath_jar_sample result = {
        .mount_id = file->stx_mnt_id, .inode = file->stx_ino, .bytes = pin->bytes,
        .device_major = file->stx_dev_major, .device_minor = file->stx_dev_minor,
    };
    if (hash_jar(jar_fd, (size_t)pin->bytes, result.sha256) < 0) return -1;
    if (memcmp(result.sha256, pin->sha256, sizeof(result.sha256))) return guest_readback_refuse(EPROTO);
    if (snapshot(request.fds, request.parts, ancestor_count, after) < 0) return -1;
    for (size_t i = 0; i <= ancestor_count; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    hash_identity(&request, ancestor_count, after, result.identity_sha256);
    *out = result;
    return 0;
}

int guest_classpath_jar_recheck(const char *absolute_path, const int *ancestors,
        size_t ancestor_count, int jar_fd, const struct guest_classpath_jar_sample *sample) {
    if (!sample) return guest_readback_refuse(EINVAL);
    struct jar_request request;
    struct statx held[MAX_ANCESTORS + 1];
    if (prepare_request(absolute_path, ancestors, ancestor_count, jar_fd, &request) < 0
            || snapshot(request.fds, request.parts, ancestor_count, held) < 0) return -1;
    unsigned char digest[32];
    hash_identity(&request, ancestor_count, held, digest);
    return memcmp(digest, sample->identity_sha256, sizeof(digest)) ? guest_readback_refuse(ESTALE) : 0;
}
