#define _GNU_SOURCE
#include "guest_classpath_readback.h"

#include "guest_classpath_identity_digest.h"
#include "guest_readback_identity.h"

#include <string.h>
#include <unistd.h>

enum slot { ROOT, DATA, SYSTEM, ENVIRON, EXPORT, SLOTS };

static const char *const names[SLOTS] = { NULL, "data", "system", "environ", "classpath" };

static int check_fds(const int *fds, unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (fds[i] < 0) return guest_readback_refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (fds[i] == fds[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fds[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }
    if (count == SLOTS) {
        int flags = fcntl(fds[EXPORT], F_GETFL);
        if (flags < 0) return -1;
        if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    }
    return 0;
}

static int snapshot(const int *fds, struct statx *held, unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (guest_readback_stat(fds[i], "", &held[i]) < 0) return -1;
        if (i) {
            struct statx named;
            if (guest_readback_stat(fds[i - 1], names[i], &named) < 0) return -1;
            if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
        }
        for (unsigned j = 0; j < i; ++j) {
            if (held[i].stx_ino == held[j].stx_ino && held[i].stx_dev_major == held[j].stx_dev_major
                    && held[i].stx_dev_minor == held[j].stx_dev_minor) return guest_readback_refuse(EPERM);
        }
    }
    return 0;
}

static int absent(int directory, const char *name) {
    struct statx present;
    if (guest_readback_stat(directory, name, &present) == 0) return guest_readback_refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int unpublished(int directory) {
    if (absent(directory, names[EXPORT]) < 0) return -1;
    return absent(directory, "classpath.tmp");
}

static int directory_profile(const struct statx *held) {
    if (held[ROOT].stx_mnt_id == held[DATA].stx_mnt_id || !guest_readback_same_mount(&held[DATA], &held[SYSTEM])
            || !guest_readback_same_mount(&held[DATA], &held[ENVIRON])) return guest_readback_refuse(EXDEV);
    if (!S_ISDIR(held[ROOT].stx_mode) || !S_ISDIR(held[DATA].stx_mode)
            || held[SYSTEM].stx_mode != (S_IFDIR | 0775) || held[ENVIRON].stx_mode != (S_IFDIR | 0700)
            || held[SYSTEM].stx_uid != 1000 || held[SYSTEM].stx_gid != 1000
            || held[ENVIRON].stx_uid != 1000 || held[ENVIRON].stx_gid != 1000) return guest_readback_refuse(EPERM);
    return 0;
}

static int stable(const struct statx *before, const struct statx *after, unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

int guest_classpath_begin(const struct guest_classpath_directories *directories, struct guest_classpath_start *out) {
    if (!directories || !out) return guest_readback_refuse(EINVAL);
    const int fds[EXPORT] = { directories->root_fd, directories->data_fd, directories->system_fd, directories->environ_fd };
    struct statx before[EXPORT], after[EXPORT];
    if (check_fds(fds, EXPORT) < 0 || snapshot(fds, before, EXPORT) < 0 || directory_profile(before) < 0
            || unpublished(fds[ENVIRON]) < 0 || snapshot(fds, after, EXPORT) < 0
            || stable(before, after, EXPORT) < 0 || unpublished(fds[ENVIRON]) < 0) return -1;
    struct guest_classpath_start result = { .directories = *directories };
    for (unsigned i = 0; i < EXPORT; ++i) {
        const struct statx *node = &before[i];
        result.identity[i] = (struct guest_classpath_directory_identity) {
            node->stx_mnt_id, node->stx_ino, node->stx_dev_major, node->stx_dev_minor,
            node->stx_mode, node->stx_uid, node->stx_gid, node->stx_nlink,
        };
    }
    *out = result;
    return 0;
}

static int same_directories(const struct guest_classpath_start *start, const struct statx *held) {
    for (unsigned i = 0; i < EXPORT; ++i) {
        const struct guest_classpath_directory_identity *id = &start->identity[i];
        const struct statx *node = &held[i];
        if (id->mount_id != node->stx_mnt_id || id->inode != node->stx_ino || id->device_major != node->stx_dev_major
                || id->device_minor != node->stx_dev_minor || id->mode != node->stx_mode || id->uid != node->stx_uid
                || id->gid != node->stx_gid || id->links != node->stx_nlink) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static int compare_file(int fd, const unsigned char *expected, size_t bytes, unsigned char digest[32]) {
    unsigned char buffer[4096];
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    for (size_t used = 0; used < bytes;) {
        size_t remaining = bytes - used;
        ssize_t got = pread(fd, buffer, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)used);
        if (got < 0) return -1;
        if (!got) return guest_readback_refuse(EIO);
        if (memcmp(buffer, expected + used, (size_t)got)) return guest_readback_refuse(EPROTO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        used += (size_t)got;
    }
    ssize_t extra = pread(fd, buffer, 1, (off_t)bytes);
    if (extra < 0) return -1;
    if (extra) return guest_readback_refuse(ESTALE);
    guest_tree_sha256_final(&hash, digest);
    return 0;
}

static void hash_identity(const int fds[SLOTS], const struct statx *held, unsigned char digest[32]) {
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, fds, SLOTS * sizeof(*fds));
    for (unsigned i = 0; i < SLOTS; ++i) guest_classpath_hash_node(&hash, &held[i]);
    guest_tree_sha256_final(&hash, digest);
}

int guest_classpath_readback(const struct guest_classpath_start *start, int file_fd,
        const void *expected, size_t expected_bytes, struct guest_classpath_sample *out) {
    if (!start || !expected || !expected_bytes || !out) return guest_readback_refuse(EINVAL);
    if (expected_bytes > GUEST_CLASSPATH_MAX_BYTES) return guest_readback_refuse(EFBIG);
    const struct guest_classpath_directories *dirs = &start->directories;
    const int fds[SLOTS] = { dirs->root_fd, dirs->data_fd, dirs->system_fd, dirs->environ_fd, file_fd };
    struct statx before[SLOTS], after[SLOTS];
    if (check_fds(fds, SLOTS) < 0 || snapshot(fds, before, SLOTS) < 0 || directory_profile(before) < 0
            || same_directories(start, before) < 0 || absent(fds[ENVIRON], "classpath.tmp") < 0) return -1;

    const struct statx *file = &before[EXPORT];
    if (!guest_readback_same_mount(&before[ENVIRON], file)) return guest_readback_refuse(EXDEV);
    if (file->stx_mode != (S_IFREG | 0600) || file->stx_uid != 1000 || file->stx_gid != 1000 || file->stx_nlink != 1)
        return guest_readback_refuse(EPERM);
    if (file->stx_size != expected_bytes) return guest_readback_refuse(ESTALE);
    struct guest_classpath_sample result = { .mount_id = file->stx_mnt_id, .inode = file->stx_ino, .bytes = expected_bytes };
    if (compare_file(file_fd, expected, expected_bytes, result.sha256) < 0
            || absent(fds[ENVIRON], "classpath.tmp") < 0 || snapshot(fds, after, SLOTS) < 0
            || stable(before, after, SLOTS) < 0) return -1;
    hash_identity(fds, after, result.identity_sha256);
    *out = result;
    return 0;
}

int guest_classpath_recheck_file(const struct guest_classpath_start *start, int file_fd,
        const struct guest_classpath_sample *sample) {
    if (!start || !sample) return guest_readback_refuse(EINVAL);
    const struct guest_classpath_directories *dirs = &start->directories;
    const int fds[SLOTS] = { dirs->root_fd, dirs->data_fd, dirs->system_fd, dirs->environ_fd, file_fd };
    struct statx held[SLOTS];
    if (check_fds(fds, SLOTS) < 0 || absent(fds[ENVIRON], "classpath.tmp") < 0 || snapshot(fds, held, SLOTS) < 0)
        return -1;
    unsigned char digest[32];
    hash_identity(fds, held, digest);
    if (memcmp(digest, sample->identity_sha256, sizeof(digest))) return guest_readback_refuse(ESTALE);
    return absent(fds[ENVIRON], "classpath.tmp");
}

_Static_assert(EXPORT == sizeof(((struct guest_classpath_start *)0)->identity) / sizeof(struct guest_classpath_directory_identity),
        "Each directory role must have a start identity");
