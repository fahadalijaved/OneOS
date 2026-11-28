#define _GNU_SOURCE
#include "guest_tree_sha256.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct payload_pin {
    const char *name, *sha256;
    uint64_t bytes;
};

/* Original donor payload bytes from the verified source cohort. */
static const struct payload_pin payloads[] = {
    {"art_payload.img", "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148", 31633408},
    {"i18n_payload.img", "1750220fbfa2af1611a8ed7b1b3526074953b3a863f0e066a3fede2a4ea7d756", 21409792},
    {"runtime_payload.img", "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379", 5296128},
};

static int matches_payload(const struct payload_pin *pin, uint64_t size, const unsigned char hash[32]) {
    static const char hex[] = "0123456789abcdef";
    char text[64];
    if (size != pin->bytes) return 0;
    for (size_t i = 0; i < 32; ++i) {
        text[2 * i] = hex[hash[i] >> 4];
        text[2 * i + 1] = hex[hash[i] & 15];
    }
    return !memcmp(text, pin->sha256, sizeof(text));
}

#ifndef GCA_BACKING_INERT
#include "guest_core_apex_backing.h"

#include "guest_tree_stage_guard.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define STAT_MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | +                   STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID)
#define EROFS_MAGIC 0xe0f5e1e2UL
#define HASH_BUFFER (64U * 1024U)

_Static_assert(sizeof(payloads) / sizeof(payloads[0]) == GCA_COUNT, "fixed core APEX cohort");

enum { STAGE, BACKING, TREE, MOUNT_NS, PROC_FDS, ANCHOR_COUNT };
enum { OPENING = 1, AVAILABLE, SPENT, REFUSED, CLOSED };
struct guest_core_apex_files {
    pid_t parent;
    struct guest_tree_stage_guard *guard;
    int state, close_error;
    int anchor[ANCHOR_COUNT], leaf[GCA_COUNT], fd[GCA_COUNT], transfer[GCA_COUNT];
    struct statx directory[3], identity[GCA_COUNT];
};

static struct guest_core_apex_files one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int control_thread(void) {
    return getpid() == gettid() && !getuid() && !geteuid() ? 0 : refuse(EPERM);
}

static int valid(struct guest_core_apex_files *files) {
    if (control_thread() < 0) return -1;
    return files == &one && files->parent == getpid() ? 0 : refuse(EINVAL);
}

static int stat_object(int fd, const char *path, struct statx *value) {
    int flags = LOOKUP | (*path ? 0 : AT_EMPTY_PATH);
    if (statx(fd, path, flags, STAT_MASK, value) < 0) return -1;
    if ((value->stx_mask & STAT_MASK) != STAT_MASK || !value->stx_ino || !value->stx_mnt_id)
        return refuse(EPROTO);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id
        && a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_identity(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink
        && a->stx_size == b->stx_size
        && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
        && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int check_named(int fd, const char *name, const struct statx *held) {
    struct statx value;
    if (stat_object(fd, name, &value) < 0) return -1;
    return same_identity(held, &value) ? 0 : refuse(ESTALE);
}

static int check_namespace(int fd) {
    struct stat held, named;
    struct statfs fs;
    if (fstat(fd, &held) < 0 || fstatfs(fd, &fs) < 0 || stat("/proc/self/ns/mnt", &named) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || held.st_dev != named.st_dev
            || held.st_ino != named.st_ino || ioctl(fd, NS_GET_NSTYPE) != CLONE_NEWNS) return refuse(EXDEV);
    return 0;
}

static int check_anchor(struct guest_core_apex_files *files, int initial) {
    struct statx value[3];
    struct statfs fs;
    struct statvfs flags;
    if (guest_tree_stage_guard_check(files->guard) < 0 || check_namespace(files->anchor[MOUNT_NS]) < 0)
        return -1;
    for (unsigned i = STAGE; i <= TREE; ++i) {
        if (stat_object(files->anchor[i], "", &value[i]) < 0) return -1;
        if (!S_ISDIR(value[i].stx_mode) || value[i].stx_uid || (value[i].stx_mode & 0022))
            return refuse(EPERM);
        if (!initial && !same_identity(&files->directory[i], &value[i])) return refuse(ESTALE);
    }
    if ((value[STAGE].stx_dev_major == value[BACKING].stx_dev_major
                && value[STAGE].stx_dev_minor == value[BACKING].stx_dev_minor)
            || value[STAGE].stx_mnt_id == value[BACKING].stx_mnt_id || !same_mount(&value[BACKING], &value[TREE])
            || value[BACKING].stx_ino == value[TREE].stx_ino) return refuse(EXDEV);
    if (fstatfs(files->anchor[BACKING], &fs) < 0 || fstatvfs(files->anchor[BACKING], &flags) < 0) return -1;
    if ((unsigned long)fs.f_type != EROFS_MAGIC || !(flags.f_flag & ST_RDONLY)) return refuse(EXDEV);
    if (check_named(AT_FDCWD, GUEST_TREE_STAGE_PATH, &value[STAGE]) < 0
            || check_named(files->anchor[STAGE], "backing", &value[BACKING]) < 0
            || check_named(files->anchor[BACKING], "tree", &value[TREE]) < 0) return -1;
    if (initial) memcpy(files->directory, value, sizeof(value));
    return 0;
}

static int check_leaf(struct guest_core_apex_files *files, unsigned role, int fd, int initial) {
    struct statx value;
    struct statvfs mount;
    const struct payload_pin *pin = &payloads[role];
    if (stat_object(fd, "", &value) < 0 || fstatvfs(fd, &mount) < 0) return -1;
    if (!(mount.f_flag & ST_RDONLY) || !same_mount(&files->directory[BACKING], &value)
            || !S_ISREG(value.stx_mode)
            || (value.stx_mode & 07777) != 0444 || value.stx_uid || value.stx_gid
            || value.stx_nlink != 1 || value.stx_size != pin->bytes) return refuse(EPERM);
    if (!initial && !same_identity(&files->identity[role], &value)) return refuse(ESTALE);
    if (check_named(files->anchor[BACKING], pin->name, &value) < 0) return -1;
    if (initial) files->identity[role] = value;
    return 0;
}

static int check_all(struct guest_core_apex_files *files) {
    if (check_anchor(files, 0) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        if (check_leaf(files, i, files->fd[i], 0) < 0) return -1;
    return guest_tree_stage_guard_check(files->guard);
}

static int measure_payload(int fd, const struct payload_pin *pin, unsigned char *buffer) {
    struct guest_tree_sha256 sha;
    unsigned char digest[32];
    uint64_t offset = 0;
    guest_tree_sha256_init(&sha);
    while (offset < pin->bytes) {
        uint64_t remaining = pin->bytes - offset;
        size_t request = remaining < HASH_BUFFER ? (size_t)remaining : HASH_BUFFER;
        ssize_t n = pread(fd, buffer, request, (off_t)offset);
        if (n < 0) return -1;
        if (!n || (size_t)n > request) return refuse(ESTALE);
        guest_tree_sha256_update(&sha, buffer, (size_t)n);
        offset += (uint64_t)n;
    }
    ssize_t extra = pread(fd, buffer, 1, (off_t)offset);
    if (extra < 0) return -1;
    if (extra) return refuse(ESTALE);
    guest_tree_sha256_final(&sha, digest);
    return matches_payload(pin, offset, digest) ? 0 : refuse(ESTALE);
}

static int acquire(struct guest_core_apex_files *files, const struct gtsp_stage_witnesses *stage,
                   unsigned char *buffer) {
    struct statfs proc;
    if (guest_tree_stage_guard_check(files->guard) < 0) return -1;
    files->anchor[STAGE] = fcntl(stage->stage_fd, F_DUPFD_CLOEXEC, 3);
    if (files->anchor[STAGE] < 0) return -1;
    files->anchor[BACKING] = openat(files->anchor[STAGE], "backing", DIRECTORY);
    if (files->anchor[BACKING] < 0) return -1;
    files->anchor[TREE] = fcntl(stage->tree_fd, F_DUPFD_CLOEXEC, 3);
    if (files->anchor[TREE] < 0) return -1;
    files->anchor[MOUNT_NS] = fcntl(stage->parent_namespace_fd, F_DUPFD_CLOEXEC, 3);
    if (files->anchor[MOUNT_NS] < 0 || check_anchor(files, 1) < 0) return -1;
    files->anchor[PROC_FDS] = open("/proc/self/fd", DIRECTORY);
    if (files->anchor[PROC_FDS] < 0 || fstatfs(files->anchor[PROC_FDS], &proc) < 0) return -1;
    if ((unsigned long)proc.f_type != PROC_SUPER_MAGIC) return refuse(EXDEV);
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        char name[24];
        files->leaf[i] = openat(files->anchor[BACKING], payloads[i].name, O_PATH | O_NOFOLLOW | O_CLOEXEC);
        if (files->leaf[i] < 0 || check_leaf(files, i, files->leaf[i], 1) < 0) return -1;
        int n = snprintf(name, sizeof(name), "%d", files->leaf[i]);
        if (n <= 0 || (size_t)n >= sizeof(name)) return refuse(EOVERFLOW);
        /* Follow only the kernel's self-fd link for the verified regular leaf. */
        files->fd[i] = openat(files->anchor[PROC_FDS], name, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (files->fd[i] < 0) return -1;
        int flags = fcntl(files->fd[i], F_GETFL);
        if (flags < 0) return -1;
        if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
        if (check_leaf(files, i, files->fd[i], 0) < 0
                || measure_payload(files->fd[i], &payloads[i], buffer) < 0
                || check_leaf(files, i, files->fd[i], 0) < 0) return -1;
    }
    return check_all(files);
}

int guest_core_apex_open_files(const struct gtsp_stage_witnesses *stage,
                              struct guest_core_apex_files **out) {
    if (control_thread() < 0) return -1;
    if (!stage || !stage->guard || !out || *out) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.parent = getpid();
    one.guard = stage->guard;
    one.state = OPENING;
    for (unsigned i = 0; i < ANCHOR_COUNT; ++i) one.anchor[i] = -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) one.leaf[i] = one.fd[i] = one.transfer[i] = -1;
    *out = &one;

    unsigned char *buffer = malloc(HASH_BUFFER);
    int result = buffer ? acquire(&one, stage, buffer) : refuse(ENOMEM);
    int saved = errno;
    free(buffer);
    one.state = result == 0 ? AVAILABLE : REFUSED;
    errno = saved;
    return result;
}

int guest_core_apex_take_payloads(struct guest_core_apex_files *files, int out[GCA_COUNT]) {
    if (valid(files) < 0) return -1;
    if (!out) return refuse(EINVAL);
    for (unsigned i = 0; i < GCA_COUNT; ++i) if (out[i] != -1) return refuse(EINVAL);
    if (files->state != AVAILABLE) return refuse(EBUSY);
    files->state = REFUSED;
    if (check_all(files) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        files->transfer[i] = fcntl(files->fd[i], F_DUPFD_CLOEXEC, 3);
        if (files->transfer[i] < 0 || check_named(files->transfer[i], "", &files->identity[i]) < 0) return -1;
    }
    if (check_all(files) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        out[i] = files->transfer[i];
        files->transfer[i] = -1;
    }
    files->state = SPENT;
    return 0;
}

static void close_owned(struct guest_core_apex_files *files, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !files->close_error)
        files->close_error = errno ? errno : EIO;
}

int guest_core_apex_close_files(struct guest_core_apex_files *files) {
    if (valid(files) < 0) return -1;
    if (files->state == OPENING) return refuse(EBUSY);
    files->state = CLOSED;
    for (unsigned i = GCA_COUNT; i > 0; --i) {
        close_owned(files, &files->transfer[i - 1]);
        close_owned(files, &files->fd[i - 1]);
        close_owned(files, &files->leaf[i - 1]);
    }
    for (unsigned i = ANCHOR_COUNT; i > 0; --i) close_owned(files, &files->anchor[i - 1]);
    return files->close_error ? refuse(files->close_error) : 0;
}
#endif
