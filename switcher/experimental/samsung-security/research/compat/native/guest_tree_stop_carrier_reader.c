#define _GNU_SOURCE
#include "guest_tree_stop_carrier_reader.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fsverity.h>
#include <linux/magic.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/statfs.h>
#include <time.h>
#include <unistd.h>

#define DIR_FLAGS (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define PATH_DIR (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK \
                 | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID)
#define IMAGE_BYTES UINT64_C(13890850816)

enum { ROOT, DATA, LOCAL, TMP, STAGE, CARRIER, COUNT };
static const char *const names[COUNT] = {"/", "data", "local", "tmp", "oneos-viewprep", "guest.erofs"};

static const unsigned char expected_digest[32] = {
    0x9b, 0x2b, 0x66, 0x45, 0x82, 0x36, 0x0d, 0xec,
    0x66, 0x0e, 0x3e, 0x25, 0xc8, 0x40, 0x10, 0x4c,
    0x16, 0xb1, 0xe1, 0xa9, 0xcb, 0x4a, 0xad, 0xbf,
    0x8f, 0x46, 0x7e, 0x20, 0x0c, 0x52, 0x5b, 0xa9,
};

struct verity_reply {
    uint16_t algorithm, size;
    unsigned char digest[32];
};

_Static_assert(offsetof(struct verity_reply, digest) == sizeof(struct fsverity_digest)
        && offsetof(struct verity_reply, algorithm) == offsetof(struct fsverity_digest, digest_algorithm)
        && offsetof(struct verity_reply, size) == offsetof(struct fsverity_digest, digest_size)
        && sizeof(struct verity_reply) == sizeof(struct fsverity_digest) + 32, "fs-verity UAPI buffer layout");

struct guest_tree_stop_carrier_reader {
    pid_t pid;
    int fd[COUNT], available, close_error;
    struct statx initial[COUNT];
    uint64_t stage_open_ms, carrier_open_ms;
};

static struct guest_tree_stop_carrier_reader one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int control_thread(void) {
    return !getuid() && !geteuid() && getpid() == gettid() ? 0 : refuse(EPERM);
}

static int valid(const struct guest_tree_stop_carrier_reader *reader) {
    if (control_thread() < 0) return -1;
    return reader == &one && reader->pid == getpid() ? 0 : refuse(EINVAL);
}

static int now_ms(uint64_t *out) {
    struct timespec now;
    if (clock_gettime(CLOCK_BOOTTIME, &now) < 0) return -1;
    if (now.tv_sec < 0 || now.tv_nsec < 0 || now.tv_nsec >= 1000000000L
            || (uint64_t)now.tv_sec > (UINT64_MAX - 999) / 1000) return refuse(EOVERFLOW);
    *out = (uint64_t)now.tv_sec * 1000 + (uint64_t)now.tv_nsec / 1000000;
    return 0;
}

static int fs_type(int fd, unsigned long magic) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == magic ? 0 : refuse(EXDEV);
}

static int identify(int parent, const char *name, struct statx *id) {
    if (statx(parent, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_ino && id->stx_mnt_id ? 0 : refuse(EPROTO);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b, int full) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
        && (!full || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
            && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
            && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int capture_pair(const struct guest_tree_stop_carrier_reader *reader, int slot, int fd,
        struct statx *held, struct statx *named) {
    int parent = slot == ROOT ? AT_FDCWD : reader->fd[slot - 1];
    if (identify(fd, "", held) < 0 || identify(parent, names[slot], named) < 0) return -1;
    return same_node(held, named, slot >= STAGE) ? 0 : refuse(ESTALE);
}

static int exact_dir(const struct statx *id, unsigned mode, unsigned uid, unsigned gid) {
    return id->stx_mode == (S_IFDIR | mode) && id->stx_uid == uid && id->stx_gid == gid;
}

static int exact_carrier(const struct statx *id, const struct statx *data) {
    return id->stx_mode == (S_IFREG | 0600) && !id->stx_uid && !id->stx_gid && id->stx_nlink == 1
        && id->stx_size == IMAGE_BYTES && same_mount(id, data);
}

static int readonly_flags(int fd, int *out) {
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
    *out = flags;
    return 0;
}

static void close_cell(int *fd, int *error) {
    int saved = *fd;
    *fd = -1;
    if (saved >= 0 && close(saved) < 0 && !*error) *error = errno;
}

/* Reopen the verified O_PATH inode via the genuine process fd directory.
 * This avoids opening a replacement device or FIFO by the carrier name. */
static int reopen_file(int path_fd, int *read_fd, uint64_t *opened_ms) {
    int proc = -1, process = -1, fds = -1, error = 0;
    char pid[24], number[24], self[24];
    struct statx root, child, descriptors, link;
    int pid_length = snprintf(pid, sizeof(pid), "%ld", (long)getpid());
    int fd_length = snprintf(number, sizeof(number), "%d", path_fd);
    if (pid_length <= 0 || (size_t)pid_length >= sizeof(pid)
            || fd_length <= 0 || (size_t)fd_length >= sizeof(number)) return refuse(EOVERFLOW);
    proc = open("/proc", PATH_DIR);
    if (proc < 0 || fs_type(proc, PROC_SUPER_MAGIC) < 0 || identify(proc, "", &root) < 0) {
        error = errno;
        goto done;
    }
    if (root.stx_ino != 1 || !S_ISDIR(root.stx_mode)) { error = EXDEV; goto done; }
    ssize_t count = readlinkat(proc, "self", self, sizeof(self));
    if (count < 0) { error = errno; goto done; }
    if (count != pid_length || memcmp(self, pid, (size_t)pid_length)) { error = EXDEV; goto done; }
    process = openat(proc, pid, PATH_DIR);
    if (process < 0 || identify(process, "", &child) < 0) { error = errno; goto done; }
    fds = openat(process, "fd", PATH_DIR);
    if (fds < 0 || identify(fds, "", &descriptors) < 0) { error = errno; goto done; }
    if (!same_mount(&root, &child) || !same_mount(&root, &descriptors)) { error = EXDEV; goto done; }
    if (identify(fds, number, &link) < 0) { error = errno; goto done; }
    if (!same_mount(&root, &link) || !S_ISLNK(link.stx_mode)) { error = EXDEV; goto done; }
    *read_fd = openat(fds, number, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (*read_fd < 0 || now_ms(opened_ms) < 0) error = errno;
done:
    close_cell(&fds, &error);
    close_cell(&process, &error);
    close_cell(&proc, &error);
    return error ? refuse(error) : 0;
}

static int open_carrier(struct guest_tree_stop_carrier_reader *reader) {
    int path = openat(reader->fd[STAGE], names[CARRIER], O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (path < 0) return -1;
    struct statx held, named;
    int error = 0, flags;
    if (capture_pair(reader, CARRIER, path, &held, &named) < 0) error = errno;
    else if (!exact_carrier(&held, &reader->initial[DATA])) error = EXDEV;
    else if (reopen_file(path, &reader->fd[CARRIER], &reader->carrier_open_ms) < 0
            || readonly_flags(reader->fd[CARRIER], &flags) < 0
            || fs_type(reader->fd[CARRIER], F2FS_SUPER_MAGIC) < 0
            || capture_pair(reader, CARRIER, reader->fd[CARRIER], &reader->initial[CARRIER], &named) < 0) error = errno;
    else if (!same_node(&held, &reader->initial[CARRIER], 1)) error = ESTALE;
    close_cell(&path, &error);
    return error ? refuse(error) : 0;
}

int guest_tree_stop_carrier_open(struct guest_tree_stop_carrier_reader **out) {
    if (!out || *out) return refuse(EINVAL);
    if (control_thread() < 0) return -1;
    if (one.pid) return refuse(EALREADY);
    one.pid = getpid();
    for (int slot = ROOT; slot < COUNT; ++slot) one.fd[slot] = -1;
    *out = &one;

    for (int slot = ROOT; slot <= STAGE; ++slot) {
        int parent = slot == ROOT ? AT_FDCWD : one.fd[slot - 1];
        struct statx named;
        one.fd[slot] = openat(parent, names[slot], DIR_FLAGS);
        if (one.fd[slot] < 0 || (slot == STAGE && now_ms(&one.stage_open_ms) < 0)
                || capture_pair(&one, slot, one.fd[slot], &one.initial[slot], &named) < 0) return -1;
        if (!S_ISDIR(one.initial[slot].stx_mode)) return refuse(EXDEV);
    }
    const struct statx *id = one.initial;
    if (id[ROOT].stx_uid || (id[ROOT].stx_mode & 0022) || same_mount(&id[ROOT], &id[DATA])
            || !exact_dir(&id[DATA], 0771, 1000, 1000) || !exact_dir(&id[LOCAL], 0751, 0, 0)
            || !exact_dir(&id[TMP], 0771, 2000, 2000) || !exact_dir(&id[STAGE], 0700, 0, 0)) return refuse(EXDEV);
    for (int slot = LOCAL; slot <= STAGE; ++slot) {
        if (!same_mount(&id[DATA], &id[slot])) return refuse(EXDEV);
        for (int earlier = DATA; earlier < slot; ++earlier)
            if (id[earlier].stx_ino == id[slot].stx_ino) return refuse(EXDEV);
    }
    if (fs_type(one.fd[DATA], F2FS_SUPER_MAGIC) < 0 || open_carrier(&one) < 0) return -1;
    if (one.stage_open_ms > one.carrier_open_ms) return refuse(ESTALE);
    one.available = 1;
    return 0;
}

static int sample_current(const struct guest_tree_stop_carrier_reader *reader, struct statx *data,
        struct statx *stage_held, struct statx *stage_named, struct statx *carrier_held, struct statx *carrier_named,
        int *stage_flags, int *carrier_flags) {
    if (fs_type(reader->fd[DATA], F2FS_SUPER_MAGIC) < 0 || fs_type(reader->fd[CARRIER], F2FS_SUPER_MAGIC) < 0
            || readonly_flags(reader->fd[STAGE], stage_flags) < 0
            || readonly_flags(reader->fd[CARRIER], carrier_flags) < 0) return -1;
    for (int slot = ROOT; slot <= TMP; ++slot) {
        struct statx held, named;
        if (capture_pair(reader, slot, reader->fd[slot], &held, &named) < 0) return -1;
        if (!same_node(&reader->initial[slot], &held, 0)) return refuse(ESTALE);
        if (slot == DATA) *data = held;
    }
    if (capture_pair(reader, STAGE, reader->fd[STAGE], stage_held, stage_named) < 0
            || capture_pair(reader, CARRIER, reader->fd[CARRIER], carrier_held, carrier_named) < 0) return -1;
    return same_node(&reader->initial[STAGE], stage_held, 1)
        && same_node(&reader->initial[CARRIER], carrier_held, 1) ? 0 : refuse(ESTALE);
}

int guest_tree_stop_carrier_measure(struct guest_tree_stop_carrier_reader *reader,
        struct guest_tree_stop_carrier_sample *out) {
    if (!out) return refuse(EINVAL);
    *out = (struct guest_tree_stop_carrier_sample){0};
    if (valid(reader) < 0) return -1;
    if (!reader->available) return refuse(EBUSY);
    struct guest_tree_stop_carrier_sample sample = {
        .stage_fd = reader->fd[STAGE], .carrier_fd = reader->fd[CARRIER],
        .stage_open_ms = reader->stage_open_ms, .carrier_open_ms = reader->carrier_open_ms,
    };
    if (now_ms(&sample.start_ms) < 0
            || sample_current(reader, &sample.data_held, &sample.stage_held_before, &sample.stage_named_before,
                              &sample.carrier_held_before, &sample.carrier_named_before,
                              &sample.stage_access_flags, &sample.access_flags) < 0) return -1;
    struct verity_reply result = {.size = sizeof(result.digest)};
    sample.ioctl_result = ioctl(sample.carrier_fd, FS_IOC_MEASURE_VERITY, &result);
    if (sample.ioctl_result < 0 || now_ms(&sample.measure_ms) < 0) return -1;
    if (sample.ioctl_result || result.algorithm != FS_VERITY_HASH_ALG_SHA256 || result.size != sizeof(result.digest))
        return refuse(EPROTO);
    if (memcmp(result.digest, expected_digest, sizeof(result.digest))) return refuse(ESTALE);
    struct statx data_after;
    int stage_flags, carrier_flags;
    if (sample_current(reader, &data_after, &sample.stage_held_after, &sample.stage_named_after,
                       &sample.carrier_held_after, &sample.carrier_named_after, &stage_flags, &carrier_flags) < 0
            || now_ms(&sample.end_ms) < 0) return -1;
    if (!same_node(&sample.data_held, &data_after, 0) || sample.stage_access_flags != stage_flags
            || sample.access_flags != carrier_flags || sample.carrier_open_ms > sample.start_ms
            || sample.start_ms > sample.measure_ms || sample.measure_ms > sample.end_ms) return refuse(ESTALE);
    sample.digest_algorithm = result.algorithm;
    sample.digest_size = result.size;
    memcpy(sample.digest, result.digest, sizeof(sample.digest));
    *out = sample;
    return 0;
}

int guest_tree_stop_carrier_close(struct guest_tree_stop_carrier_reader *reader) {
    if (valid(reader) < 0) return -1;
    reader->available = 0;
    for (int slot = COUNT - 1; slot >= ROOT; --slot) close_cell(&reader->fd[slot], &reader->close_error);
    return reader->close_error ? refuse(reader->close_error) : 0;
}
