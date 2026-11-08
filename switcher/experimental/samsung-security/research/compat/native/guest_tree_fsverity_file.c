#define _GNU_SOURCE
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { VERITY_SHA256 = 1, VERITY_SHA256_BYTES = 32 };

/* The UAPI header plus exactly the writable digest tail. */
struct measure_result {
    uint16_t algorithm, size;
    unsigned char bytes[VERITY_SHA256_BYTES];
};

static int measured_sha256(const struct measure_result *result, const unsigned char expected[32]) {
    return result->algorithm == VERITY_SHA256 && result->size == VERITY_SHA256_BYTES
        && !memcmp(result->bytes, expected, VERITY_SHA256_BYTES);
}

#ifndef GTVF_INERT
#include "guest_tree_fsverity_file.h"

#include "guest_tree_source_mounts.h"
#include "guest_tree_stage_guard.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fsverity.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define IMAGE_NAME "guest.erofs"
#define DIR_PATH (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define OBJECT_MASK (STATX_TYPE | STATX_MODE | STATX_NLINK | STATX_UID | STATX_GID | +                     STATX_INO | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID)

_Static_assert((int)VERITY_SHA256 == (int)FS_VERITY_HASH_ALG_SHA256, "SHA-256 UAPI identifier");
_Static_assert(sizeof(struct fsverity_digest) == offsetof(struct measure_result, bytes), "measure ABI head");
_Static_assert(offsetof(struct fsverity_digest, digest_algorithm) == offsetof(struct measure_result, algorithm)
        && offsetof(struct fsverity_digest, digest_size) == offsetof(struct measure_result, size),
        "measure ABI fields");
_Static_assert(sizeof(struct measure_result) == sizeof(struct fsverity_digest) + VERITY_SHA256_BYTES,
        "measure ABI extent");

enum { ROOT, HOST_DATA, LOCAL, TMP, NAMED_STAGE, STAGE, NS, PROC_ROOT, PROC_PID, PROC_FDS,
       IMAGE_PATH, IMAGE_READ, CELL_COUNT };
enum { OPENING = 1, AVAILABLE, REFUSED, CLOSED };

struct guest_tree_fsverity_file {
    pid_t parent;
    struct guest_tree_stage_guard *guard;
    struct guest_tree_fsverity_expected expected;
    struct statx data, stage, proc, image;
    int fd[CELL_COUNT], state, close_error;
};

static struct guest_tree_fsverity_file one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int control_thread(void) {
    return getpid() == gettid() && !getuid() && !geteuid() ? 0 : refuse(EPERM);
}

static int valid(struct guest_tree_fsverity_file *file) {
    if (control_thread() < 0) return -1;
    return file == &one && file->parent == getpid() ? 0 : refuse(EINVAL);
}

static int stat_object(int base, const char *path, struct statx *value) {
    if (statx(base, path, LOOKUP | (*path ? 0 : AT_EMPTY_PATH), OBJECT_MASK, value) < 0) return -1;
    return (value->stx_mask & OBJECT_MASK) == OBJECT_MASK && value->stx_ino && value->stx_mnt_id
        ? 0 : refuse(EPROTO);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id
        && a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int same_identity(const struct statx *a, const struct statx *b) {
    return same_node(a, b) && a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
        && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
        && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int named_node(int base, const char *path, const struct statx *expected, int full) {
    struct statx value;
    if (stat_object(base, path, &value) < 0) return -1;
    return (full ? same_identity(expected, &value) : same_node(expected, &value)) ? 0 : refuse(ESTALE);
}

static int check_type(int fd, unsigned long magic) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == magic ? 0 : refuse(EXDEV);
}

static int check_namespace(const struct guest_tree_fsverity_file *file) {
    struct stat held, named;
    int fd = file->fd[NS];
    if (check_type(fd, NSFS_MAGIC) < 0 || fstat(fd, &held) < 0
            || fstatat(file->fd[PROC_PID], "ns/mnt", &named, 0) < 0) return -1;
    if (held.st_dev != named.st_dev || held.st_ino != named.st_ino) return refuse(EXDEV);
    int kind = ioctl(fd, NS_GET_NSTYPE);
    if (kind < 0) return -1;
    return kind == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int check_anchors(struct guest_tree_fsverity_file *file, int initial) {
    struct statx root, data, local, tmp, stage, proc, pid, fds;
    const int *fd = file->fd;
    if (guest_tree_stage_guard_check(file->guard) < 0
            || check_type(fd[PROC_ROOT], PROC_SUPER_MAGIC) < 0 || check_type(fd[HOST_DATA], F2FS_SUPER_MAGIC) < 0
            || stat_object(fd[ROOT], "", &root) < 0 || stat_object(fd[HOST_DATA], "", &data) < 0
            || stat_object(fd[LOCAL], "", &local) < 0 || stat_object(fd[TMP], "", &tmp) < 0
            || stat_object(fd[STAGE], "", &stage) < 0 || stat_object(fd[PROC_ROOT], "", &proc) < 0
            || stat_object(fd[PROC_PID], "", &pid) < 0 || stat_object(fd[PROC_FDS], "", &fds) < 0)
        return -1;
    if (!S_ISDIR(root.stx_mode) || root.stx_uid || (root.stx_mode & 0022)
            || !S_ISDIR(data.stx_mode) || !S_ISDIR(local.stx_mode) || !S_ISDIR(tmp.stx_mode)
            || !S_ISDIR(stage.stx_mode) || stage.stx_uid || (stage.stx_mode & 0022)
            || stage.stx_ino == data.stx_ino || !same_mount(&data, &local) || !same_mount(&data, &tmp)
            || !same_mount(&data, &stage) || same_mount(&data, &root) || !S_ISDIR(proc.stx_mode)
            || !S_ISDIR(pid.stx_mode) || !S_ISDIR(fds.stx_mode)
            || !same_mount(&proc, &pid) || !same_mount(&proc, &fds)) return refuse(EXDEV);
    if (named_node(AT_FDCWD, "/", &root, 0) < 0 || named_node(fd[ROOT], "data", &data, 0) < 0
            || named_node(fd[HOST_DATA], "local", &local, 0) < 0 || named_node(fd[LOCAL], "tmp", &tmp, 0) < 0
            || named_node(AT_FDCWD, GUEST_TREE_STAGE_PATH, &stage, 1) < 0
            || named_node(fd[TMP], "oneos-viewprep", &stage, 1) < 0
            || named_node(fd[NAMED_STAGE], "", &stage, 1) < 0 || named_node(fd[ROOT], "proc", &proc, 0) < 0
            || named_node(fd[PROC_PID], "fd", &fds, 0) < 0 || check_namespace(file) < 0) return -1;
    if (!initial && (!same_node(&file->data, &data) || !same_identity(&file->stage, &stage)
            || !same_node(&file->proc, &proc))) return refuse(ESTALE);
    if (initial) {
        file->data = data;
        file->stage = stage;
        file->proc = proc;
    }
    return 0;
}

static int profile_image(const struct guest_tree_fsverity_file *file, const struct statx *image) {
    unsigned mode = image->stx_mode & 07777;
    if (!S_ISREG(image->stx_mode) || image->stx_uid || image->stx_gid || image->stx_nlink != 1
            || !(mode & 0400) || (mode & ~0644U) || image->stx_size != file->expected.bytes
            || !same_mount(&file->data, image)) return refuse(EPERM);
    return 0;
}

static int check_image(const struct guest_tree_fsverity_file *file) {
    int fd = file->fd[IMAGE_READ];
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
    if (check_type(fd, F2FS_SUPER_MAGIC) < 0 || named_node(fd, "", &file->image, 1) < 0
            || named_node(file->fd[IMAGE_PATH], "", &file->image, 1) < 0
            || named_node(file->fd[STAGE], IMAGE_NAME, &file->image, 1) < 0) return -1;
    return 0;
}

static int measure(const struct guest_tree_fsverity_file *file) {
    struct measure_result result = {.size = VERITY_SHA256_BYTES};
    int status = ioctl(file->fd[IMAGE_READ], FS_IOC_MEASURE_VERITY, &result);
    if (status < 0) return -1;
    if (status || result.algorithm != VERITY_SHA256 || result.size != VERITY_SHA256_BYTES)
        return refuse(EPROTO);
    return measured_sha256(&result, file->expected.sha256) ? 0 : refuse(ESTALE);
}

static int check_current(struct guest_tree_fsverity_file *file) {
    if (check_anchors(file, 0) < 0 || check_image(file) < 0 || measure(file) < 0
            || check_image(file) < 0 || check_anchors(file, 0) < 0) return -1;
    return guest_tree_stage_guard_check(file->guard);
}

static int acquire(struct guest_tree_fsverity_file *file, const struct guest_tree_fsverity_inputs *stage) {
    int *fd = file->fd;
    char decimal[24];
    if (guest_tree_stage_guard_check(file->guard) < 0) return -1;
    fd[STAGE] = fcntl(stage->stage_fd, F_DUPFD_CLOEXEC, 3);
    if (fd[STAGE] < 0) return -1;
    fd[NS] = fcntl(stage->controller_namespace_fd, F_DUPFD_CLOEXEC, 3);
    if (fd[NS] < 0) return -1;
    fd[ROOT] = open("/", DIR_PATH);
    if (fd[ROOT] < 0) return -1;
    fd[HOST_DATA] = openat(fd[ROOT], "data", DIR_PATH);
    if (fd[HOST_DATA] < 0) return -1;
    fd[LOCAL] = openat(fd[HOST_DATA], "local", DIR_PATH);
    if (fd[LOCAL] < 0) return -1;
    fd[TMP] = openat(fd[LOCAL], "tmp", DIR_PATH);
    if (fd[TMP] < 0) return -1;
    fd[NAMED_STAGE] = openat(fd[TMP], "oneos-viewprep", DIR_PATH);
    if (fd[NAMED_STAGE] < 0) return -1;
    fd[PROC_ROOT] = openat(fd[ROOT], "proc", DIR_PATH);
    if (fd[PROC_ROOT] < 0 || check_type(fd[PROC_ROOT], PROC_SUPER_MAGIC) < 0) return -1;
    int n = snprintf(decimal, sizeof(decimal), "%ld", (long)file->parent);
    if (n <= 0 || (size_t)n >= sizeof(decimal)) return refuse(EOVERFLOW);
    fd[PROC_PID] = openat(fd[PROC_ROOT], decimal, DIR_PATH);
    if (fd[PROC_PID] < 0) return -1;
    fd[PROC_FDS] = openat(fd[PROC_PID], "fd", DIR_PATH);
    if (fd[PROC_FDS] < 0 || check_anchors(file, 1) < 0) return -1;

    fd[IMAGE_PATH] = openat(fd[STAGE], IMAGE_NAME, O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (fd[IMAGE_PATH] < 0 || stat_object(fd[IMAGE_PATH], "", &file->image) < 0
            || profile_image(file, &file->image) < 0 || named_node(fd[STAGE], IMAGE_NAME, &file->image, 1) < 0)
        return -1;
    n = snprintf(decimal, sizeof(decimal), "%d", fd[IMAGE_PATH]);
    if (n <= 0 || (size_t)n >= sizeof(decimal)) return refuse(EOVERFLOW);
    /* The only followed link is our verified regular O_PATH fd's kernel link. */
    fd[IMAGE_READ] = openat(fd[PROC_FDS], decimal, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (fd[IMAGE_READ] < 0) return -1;
    return check_current(file);
}

int guest_tree_fsverity_open_file(const struct guest_tree_fsverity_inputs *stage,
        const struct guest_tree_fsverity_expected *expected, struct guest_tree_fsverity_file **out) {
    if (control_thread() < 0) return -1;
    if (!stage || !stage->guard || !expected || !expected->bytes || expected->bytes > INT64_MAX
            || !out || *out) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.parent = getpid();
    one.guard = stage->guard;
    one.expected = *expected;
    one.state = OPENING;
    for (unsigned i = 0; i < CELL_COUNT; ++i) one.fd[i] = -1;
    *out = &one;
    int result = acquire(&one, stage);
    one.state = result == 0 ? AVAILABLE : REFUSED;
    return result;
}

int guest_tree_fsverity_borrow_fds(struct guest_tree_fsverity_file *file,
                                  struct guest_tree_fsverity_borrow *out) {
    if (valid(file) < 0) return -1;
    if (!out || out->image_fd != -1 || out->proc_root_fd != -1) return refuse(EINVAL);
    if (file->state != AVAILABLE) return refuse(EBUSY);
    if (check_current(file) < 0) {
        file->state = REFUSED;
        return -1;
    }
    *out = (struct guest_tree_fsverity_borrow){file->fd[IMAGE_READ], file->fd[PROC_ROOT]};
    return 0;
}

int guest_tree_fsverity_close_file(struct guest_tree_fsverity_file *file) {
    if (valid(file) < 0) return -1;
    if (file->state == OPENING) return refuse(EBUSY);
    file->state = CLOSED;
    for (unsigned i = CELL_COUNT; i > 0; --i) {
        int fd = file->fd[i - 1];
        file->fd[i - 1] = -1;
        if (fd >= 0 && close(fd) < 0 && !file->close_error) file->close_error = errno ? errno : EIO;
    }
    return file->close_error ? refuse(file->close_error) : 0;
}
#endif
