#define _GNU_SOURCE
#include "guest_tree_fsverity_provision.h"

#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { SHA256_SIZE = 32, SHA256_ALG = 1 };

struct verity_reply {
    uint16_t algorithm, size;
    unsigned char digest[SHA256_SIZE];
};

static int digest_matches(const unsigned char actual[SHA256_SIZE], const unsigned char expected[SHA256_SIZE]) {
    return !memcmp(actual, expected, SHA256_SIZE);
}

static int reply_matches(int status, const struct verity_reply *reply, const unsigned char expected[SHA256_SIZE]) {
    return !status && reply->algorithm == SHA256_ALG && reply->size == SHA256_SIZE
        && digest_matches(reply->digest, expected);
}

static enum guest_tree_fsverity_provision_release close_outcome(int created, int published, int error) {
    if (error || created != published) return GTVP_HOLD;
    return published ? GTVP_PUBLISHED_LOCAL_CLOSED : GTVP_NO_EFFECT_LOCAL_CLOSED;
}

enum feed_kind { FEED_INVALID, FEED_REGULAR, FEED_PIPE, FEED_SOCKET };

static int feed_access(enum feed_kind kind, int read_only, int read_write, int nonblocking) {
    switch (kind) {
    case FEED_REGULAR: return read_only;
    case FEED_PIPE: return read_only && nonblocking;
    case FEED_SOCKET: return read_write && nonblocking;
    default: return 0;
    }
}

#ifndef GTVP_INERT
#include "guest_tree_sha256.h"
#include "guest_tree_install_stream.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/fsverity.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <poll.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define BLOCK_SIZE 4096U
#define CHUNK (64U * 1024U)
#define TOTAL_MS UINT64_C(3600000)
#define PIPE_IDLE_MS 30000U

_Static_assert(sizeof(struct fsverity_digest) == offsetof(struct verity_reply, digest)
        && sizeof(struct verity_reply) == sizeof(struct fsverity_digest) + SHA256_SIZE
        && offsetof(struct fsverity_digest, digest_algorithm) == offsetof(struct verity_reply, algorithm)
        && offsetof(struct fsverity_digest, digest_size) == offsetof(struct verity_reply, size), "fs-verity measure ABI");
_Static_assert((int)FS_VERITY_HASH_ALG_SHA256 == (int)SHA256_ALG, "SHA-256 UAPI ID");
_Static_assert(sizeof(struct fsverity_enable_arg) == 128
        && offsetof(struct fsverity_enable_arg, block_size) == 8, "fs-verity enable ABI");

enum { ROOT, DATA, LOCAL, TMP, NAMED_STAGE, STAGE, NS, PROC, PROC_FDS, WRITER, WITNESS, READER,
       SYNC_DIR, FINAL_PATH, FINAL_READ, FD_COUNT };
enum { STARTING = 1, VERIFIED, PUBLISHING, PUBLISHED, REFUSED, CLOSING, CLOSED };

struct guest_tree_fsverity_provision {
    pid_t parent;
    const struct guest_tree_install_guard *guard;
    struct guest_tree_fsverity_provision_expected expected;
    struct statx stage, image;
    uint64_t deadline;
    int fd[FD_COUNT], state, creation_attempted, enable_attempted, rename_attempted, sticky;
    enum guest_tree_fsverity_provision_release terminal;
};

static struct guest_tree_fsverity_provision one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int controller(void) {
    return getpid() == gettid() && !getuid() && !geteuid() && !getegid() ? 0 : refuse(EPERM);
}

static int valid(const struct guest_tree_fsverity_provision *p) {
    if (controller() < 0) return -1;
    return p == &one && p->parent == getpid() ? 0 : refuse(EINVAL);
}

static void sticky(struct guest_tree_fsverity_provision *p, int error) {
    if (!p->sticky) p->sticky = error ? error : EIO;
}

static int close_owned(struct guest_tree_fsverity_provision *p, int slot) {
    int fd = p->fd[slot];
    p->fd[slot] = -1;
    if (fd < 0 || close(fd) == 0) return 0;
    sticky(p, errno);
    return -1;
}

static int now_ms(uint64_t *ms) {
    struct timespec value;
    if (clock_gettime(CLOCK_BOOTTIME, &value) < 0) return -1;
    if (value.tv_sec < 0 || (uint64_t)value.tv_sec > (UINT64_MAX - TOTAL_MS - 999) / 1000)
        return refuse(EOVERFLOW);
    *ms = (uint64_t)value.tv_sec * 1000 + (uint64_t)value.tv_nsec / 1000000;
    return 0;
}

static int remaining(const struct guest_tree_fsverity_provision *p, uint64_t *ms) {
    uint64_t now;
    if (now_ms(&now) < 0) return -1;
    if (now >= p->deadline) return refuse(ETIMEDOUT);
    *ms = p->deadline - now;
    return 0;
}

static int stat_object(int fd, const char *name, struct statx *st) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK
        | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID;
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), mask, st) < 0) return -1;
    return (st->stx_mask & mask) == mask && st->stx_mnt_id && st->stx_ino ? 0 : refuse(EPROTO);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int same_image(const struct statx *a, const struct statx *b, int permit_effect_ctime) {
    return same_node(a, b) && a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
        && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
        && (permit_effect_ctime || (a->stx_ctime.tv_sec == b->stx_ctime.tv_sec
                                   && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int fs_type(int fd, unsigned long type) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == type ? 0 : refuse(EXDEV);
}

static int guard_check(const struct guest_tree_install_guard *guard, int stage, int ns) {
    errno = 0;
    int status = guest_tree_fsverity_check_install_guard(guard, stage, ns);
    if (status > 0) return refuse(EPERM);
    if (status < 0) return refuse(errno ? errno : EIO);
    return 0;
}

static int check_stage_anchors(struct guest_tree_fsverity_provision *p, int initial) {
    const int *fd = p->fd;
    static const char *const names[] = {"data", "local", "tmp", "oneos-viewprep"};
    struct statx physical[5], actual, proc, proc_fds;
    struct stat ns, named;
    if (fs_type(fd[DATA], F2FS_SUPER_MAGIC) < 0 || fs_type(fd[PROC], PROC_SUPER_MAGIC) < 0
            || fs_type(fd[NS], NSFS_MAGIC) < 0 || fstat(fd[NS], &ns) < 0
            || fstatat(fd[PROC], "self/ns/mnt", &named, 0) < 0) return -1;
    if (ns.st_dev != named.st_dev || ns.st_ino != named.st_ino || ioctl(fd[NS], NS_GET_NSTYPE) != CLONE_NEWNS)
        return refuse(EXDEV);
    for (unsigned i = ROOT; i <= NAMED_STAGE; ++i) {
        if (stat_object(fd[i], "", &physical[i]) < 0 || !S_ISDIR(physical[i].stx_mode))
            return refuse(EPROTO);
        if (i > DATA && !same_mount(&physical[i], &physical[DATA])) return refuse(EXDEV);
        if (i > ROOT) {
            if (stat_object(fd[i - 1], names[i - 1], &actual) < 0) return -1;
            if (!same_node(&physical[i], &actual)) return refuse(ESTALE);
        }
    }
    if (physical[ROOT].stx_uid || (physical[ROOT].stx_mode & 0022)
            || same_mount(&physical[ROOT], &physical[DATA]) || physical[NAMED_STAGE].stx_uid
            || ((physical[NAMED_STAGE].stx_mode & S_ISGID) && physical[NAMED_STAGE].stx_gid)
            || (physical[NAMED_STAGE].stx_mode & 0022)) return refuse(EPERM);
    if (stat_object(AT_FDCWD, "/", &actual) < 0) return -1;
    if (!same_node(&physical[ROOT], &actual)) return refuse(ESTALE);
    if (stat_object(AT_FDCWD, GUEST_TREE_STAGE_PATH, &actual) < 0) return -1;
    if (!same_node(&physical[NAMED_STAGE], &actual)) return refuse(ESTALE);
    if (stat_object(fd[STAGE], "", &actual) < 0) return -1;
    if (!same_node(&physical[NAMED_STAGE], &actual) || (!initial && !same_node(&p->stage, &actual)))
        return refuse(ESTALE);
    if (stat_object(fd[PROC], "", &proc) < 0 || stat_object(fd[PROC_FDS], "", &proc_fds) < 0) return -1;
    if (!same_mount(&proc, &proc_fds)) return refuse(EXDEV);
    if (initial) p->stage = actual;
    return 0;
}

static int current_stage(struct guest_tree_fsverity_provision *p, int initial) {
    if (guard_check(p->guard, p->fd[STAGE], p->fd[NS]) < 0) return -1;
    return check_stage_anchors(p, initial);
}

static int open_named_anchors(struct guest_tree_fsverity_provision *p) {
    int *fd = p->fd;
    static const char *const names[] = {"data", "local", "tmp", "oneos-viewprep"};
    fd[ROOT] = open("/", DIRECTORY);
    if (fd[ROOT] < 0) return -1;
    for (unsigned i = DATA; i <= NAMED_STAGE; ++i) {
        fd[i] = openat(fd[i - 1], names[i - 1], DIRECTORY);
        if (fd[i] < 0) return -1;
    }
    fd[PROC] = openat(fd[ROOT], "proc", DIRECTORY);
    if (fd[PROC] < 0 || fs_type(fd[PROC], PROC_SUPER_MAGIC) < 0) return -1;
    fd[PROC_FDS] = openat(fd[PROC], "self/fd", DIRECTORY);
    return fd[PROC_FDS] < 0 ? -1 : 0;
}

static int open_anchors(struct guest_tree_fsverity_provision *p,
                        const struct guest_tree_fsverity_provision_inputs *input) {
    int *fd = p->fd;
    if (guard_check(p->guard, input->stage_fd, input->controller_namespace_fd) < 0)
        return -1;
    fd[STAGE] = fcntl(input->stage_fd, F_DUPFD_CLOEXEC, 3);
    if (fd[STAGE] < 0) return -1;
    fd[NS] = fcntl(input->controller_namespace_fd, F_DUPFD_CLOEXEC, 3);
    if (fd[NS] < 0 || open_named_anchors(p) < 0) return -1;
    return current_stage(p, 1);
}

static int reopen(struct guest_tree_fsverity_provision *p, int source, int flags) {
    char name[24];
    int n = snprintf(name, sizeof(name), "%d", p->fd[source]);
    if (n <= 0 || (size_t)n >= sizeof(name)) return refuse(EOVERFLOW);
    return openat(p->fd[PROC_FDS], name, flags | O_CLOEXEC);
}

static int check_named_leaf(struct guest_tree_fsverity_provision *p, int live_slot, const char *name,
                            uint64_t bytes, struct statx *image) {
    struct statx named, witness;
    if (stat_object(p->fd[live_slot], "", image) < 0 || stat_object(p->fd[WITNESS], "", &witness) < 0
            || stat_object(p->fd[STAGE], name, &named) < 0) return -1;
    if (!S_ISREG(image->stx_mode) || (image->stx_mode & 07777) != 0600
            || image->stx_uid || image->stx_gid || image->stx_nlink != 1 || image->stx_size != bytes
            || !same_mount(&p->stage, image) || !same_image(&witness, image, 0)
            || !same_image(&named, image, 0)) return refuse(ESTALE);
    return 0;
}

static int check_leaf(struct guest_tree_fsverity_provision *p, int live_slot, uint64_t bytes, struct statx *image) {
    return check_named_leaf(p, live_slot, GUEST_TREE_FSVERITY_NEW_NAME, bytes, image);
}

static int require_absent(int fd, const char *name) {
    struct statx present;
    if (stat_object(fd, name, &present) == 0) return refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int check_feed(int fd, uint64_t bytes, int *stream) {
    struct stat feed;
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0 || fstat(fd, &feed) < 0) return -1;
    enum feed_kind kind = FEED_INVALID;
    if (S_ISREG(feed.st_mode)) kind = FEED_REGULAR;
    else if (S_ISFIFO(feed.st_mode)) kind = FEED_PIPE;
    else if (S_ISSOCK(feed.st_mode)) kind = FEED_SOCKET;
    int access = flags & O_ACCMODE;
    if ((flags & O_PATH) || !feed_access(kind, access == O_RDONLY, access == O_RDWR, flags & O_NONBLOCK))
        return refuse(EPERM);
    if (kind == FEED_REGULAR && (feed.st_size < 0 || (uint64_t)feed.st_size != bytes)) return refuse(ESTALE);
    if (kind == FEED_SOCKET && guest_tree_connected_unix_stream(fd) < 0) return -1;
    *stream = kind != FEED_REGULAR;
    return 0;
}

static ssize_t feed_read(struct guest_tree_fsverity_provision *p, int feed, int stream,
                         void *buffer, size_t length, uint64_t offset) {
    uint64_t ms;
    if (remaining(p, &ms) < 0) return -1;
    if (!stream) return pread(feed, buffer, length, (off_t)offset);
    struct pollfd input = {.fd = feed, .events = POLLIN};
    int status = poll(&input, 1, (int)(ms < PIPE_IDLE_MS ? ms : PIPE_IDLE_MS));
    if (status < 0) return -1;
    if (!status) return refuse(ETIMEDOUT);
    if ((input.revents & (POLLERR | POLLNVAL)) || !(input.revents & (POLLIN | POLLHUP))) return refuse(EIO);
    return read(feed, buffer, length);
}

static int copy_feed(struct guest_tree_fsverity_provision *p, int feed, int stream, unsigned char *buffer) {
    uint64_t offset = 0;
    while (offset < p->expected.bytes) {
        uint64_t left = p->expected.bytes - offset;
        size_t request = left < CHUNK ? (size_t)left : CHUNK;
        ssize_t n = feed_read(p, feed, stream, buffer, request, offset);
        if (n < 0) return -1;
        if (!n || (size_t)n > request) return refuse(ESTALE);
        size_t done = 0;
        while (done < (size_t)n) {
            uint64_t ms;
            if (remaining(p, &ms) < 0) return -1;
            ssize_t written = write(p->fd[WRITER], buffer + done, (size_t)n - done);
            if (written < 0) return -1;
            if (!written || (size_t)written > (size_t)n - done) return refuse(EIO);
            done += (size_t)written;
        }
        offset += (uint64_t)n;
    }
    ssize_t extra = feed_read(p, feed, stream, buffer, 1, offset);
    if (extra < 0) return -1;
    return extra ? refuse(EFBIG) : 0;
}

static int hash_candidate(struct guest_tree_fsverity_provision *p, unsigned char *buffer) {
    struct guest_tree_sha256 hash;
    unsigned char actual[SHA256_SIZE];
    uint64_t offset = 0, ms;
    guest_tree_sha256_init(&hash);
    while (offset < p->expected.bytes) {
        if (remaining(p, &ms) < 0) return -1;
        uint64_t left = p->expected.bytes - offset;
        size_t request = left < CHUNK ? (size_t)left : CHUNK;
        ssize_t n = pread(p->fd[READER], buffer, request, (off_t)offset);
        if (n < 0) return -1;
        if (!n || (size_t)n > request) return refuse(ESTALE);
        guest_tree_sha256_update(&hash, buffer, (size_t)n);
        offset += (uint64_t)n;
    }
    if (remaining(p, &ms) < 0) return -1;
    ssize_t extra = pread(p->fd[READER], buffer, 1, (off_t)offset);
    if (extra < 0) return -1;
    if (extra) return refuse(EFBIG);
    guest_tree_sha256_final(&hash, actual);
    return digest_matches(actual, p->expected.raw_sha256) ? 0 : refuse(ESTALE);
}

static int measure(struct guest_tree_fsverity_provision *p, int slot) {
    struct verity_reply reply = {.size = SHA256_SIZE};
    int result = ioctl(p->fd[slot], FS_IOC_MEASURE_VERITY, &reply);
    if (result < 0) return -1;
    if (result || reply.algorithm != SHA256_ALG || reply.size != SHA256_SIZE) return refuse(EPROTO);
    return reply_matches(result, &reply, p->expected.verity_sha256) ? 0 : refuse(ESTALE);
}

static int produce(struct guest_tree_fsverity_provision *p,
        const struct guest_tree_fsverity_provision_inputs *input, unsigned char *buffer) {
    const struct fsverity_enable_arg enable = {
        .version = 1, .hash_algorithm = FS_VERITY_HASH_ALG_SHA256, .block_size = BLOCK_SIZE
    };
    struct statx now, created;
    int stream;
    if (check_feed(input->feed_fd, p->expected.bytes, &stream) < 0) return -1;
    if (open_anchors(p, input) < 0 || current_stage(p, 0) < 0
            || require_absent(p->fd[STAGE], GUEST_TREE_FSVERITY_FINAL_NAME) < 0
            || require_absent(p->fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0) return -1;
    p->creation_attempted = 1;
    p->fd[WRITER] = openat(p->fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME,
            O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (p->fd[WRITER] < 0) return -1;
    p->fd[WITNESS] = reopen(p, WRITER, O_PATH);
    if (p->fd[WITNESS] < 0 || check_leaf(p, WRITER, 0, &created) < 0 || current_stage(p, 0) < 0
            || copy_feed(p, input->feed_fd, stream, buffer) < 0
            || check_leaf(p, WRITER, p->expected.bytes, &now) < 0 || fsync(p->fd[WRITER]) < 0) return -1;
    if (!same_node(&created, &now)) return refuse(ESTALE);
    if (close_owned(p, WRITER) < 0) return -1;
    p->fd[READER] = reopen(p, WITNESS, O_RDONLY | O_NONBLOCK);
    if (p->fd[READER] < 0) return -1;
    int flags = fcntl(p->fd[READER], F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
    if (check_leaf(p, READER, p->expected.bytes, &p->image) < 0) return -1;
    if (!same_node(&created, &p->image)) return refuse(ESTALE);
    if (hash_candidate(p, buffer) < 0 || check_leaf(p, READER, p->expected.bytes, &now) < 0) return -1;
    if (!same_image(&p->image, &now, 0)) return refuse(ESTALE);
    uint64_t ms;
    if (current_stage(p, 0) < 0 || check_leaf(p, READER, p->expected.bytes, &now) < 0
            || remaining(p, &ms) < 0) return -1;
    if (!same_image(&p->image, &now, 0)) return refuse(ESTALE);
    p->enable_attempted = 1;
    int result = ioctl(p->fd[READER], FS_IOC_ENABLE_VERITY, &enable);
    if (result < 0) return -1;
    if (result) return refuse(EPROTO);
    if (measure(p, READER) < 0 || current_stage(p, 0) < 0 || check_leaf(p, READER, p->expected.bytes, &now) < 0)
        return -1;
    if (!same_image(&p->image, &now, 1)) return refuse(ESTALE);
    p->image = now;
    return 0;
}

int guest_tree_fsverity_provision_new(const struct guest_tree_fsverity_provision_inputs *input,
        const struct guest_tree_fsverity_provision_expected *expected,
        struct guest_tree_fsverity_provision **out) {
    if (controller() < 0) return -1;
    if (!input || !input->guard || !expected || !expected->bytes || expected->bytes > INT64_MAX
            || !out || *out) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.parent = getpid();
    one.guard = input->guard;
    one.expected = *expected;
    one.state = STARTING;
    for (unsigned i = 0; i < FD_COUNT; ++i) one.fd[i] = -1;
    *out = &one;
    uint64_t start;
    unsigned char *buffer = malloc(CHUNK);
    int result = buffer ? now_ms(&start) : refuse(ENOMEM);
    if (!result) {
        one.deadline = start + TOTAL_MS;
        result = produce(&one, input, buffer);
    }
    int saved = errno;
    free(buffer);
    if (result < 0 && one.creation_attempted) sticky(&one, saved);
    one.state = result < 0 ? REFUSED : VERIFIED;
    errno = saved;
    return result;
}

static int check_sync_dir(struct guest_tree_fsverity_provision *p) {
    struct statx directory;
    int fd = p->fd[SYNC_DIR];
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0 || stat_object(fd, "", &directory) < 0 || fs_type(fd, F2FS_SUPER_MAGIC) < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY || !S_ISDIR(directory.stx_mode)
            || !same_node(&p->stage, &directory)) return refuse(ESTALE);
    return 0;
}

static int check_final_leaf(struct guest_tree_fsverity_provision *p, int permit_rename_ctime) {
    struct statx actual, held, original;
    int flags = fcntl(p->fd[FINAL_READ], F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
    if (check_named_leaf(p, FINAL_READ, GUEST_TREE_FSVERITY_FINAL_NAME, p->expected.bytes, &actual) < 0
            || stat_object(p->fd[FINAL_PATH], "", &held) < 0
            || stat_object(p->fd[READER], "", &original) < 0) return -1;
    if (!same_image(&p->image, &actual, permit_rename_ctime) || !same_image(&actual, &held, 0)
            || !same_image(&actual, &original, 0)) return refuse(ESTALE);
    if (require_absent(p->fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0) return -1;
    p->image = actual;
    return 0;
}

static int verify_publication(struct guest_tree_fsverity_provision *p) {
    if (current_stage(p, 0) < 0 || check_sync_dir(p) < 0 || check_final_leaf(p, 0) < 0
            || measure(p, FINAL_READ) < 0 || current_stage(p, 0) < 0
            || check_sync_dir(p) < 0 || check_final_leaf(p, 0) < 0) return -1;
    return 0;
}

static int publish(struct guest_tree_fsverity_provision *p) {
    struct statx now;
    int stage = p->fd[STAGE];
    if (current_stage(p, 0) < 0 || require_absent(stage, GUEST_TREE_FSVERITY_FINAL_NAME) < 0
            || check_leaf(p, READER, p->expected.bytes, &now) < 0) return -1;
    if (!same_image(&p->image, &now, 0)) return refuse(ESTALE);
    p->fd[SYNC_DIR] = openat(stage, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (p->fd[SYNC_DIR] < 0 || check_sync_dir(p) < 0 || measure(p, READER) < 0
            || fsync(p->fd[READER]) < 0 || current_stage(p, 0) < 0 || check_sync_dir(p) < 0
            || check_leaf(p, READER, p->expected.bytes, &now) < 0) return -1;
    if (!same_image(&p->image, &now, 0)) return refuse(ESTALE);
    if (require_absent(stage, GUEST_TREE_FSVERITY_FINAL_NAME) < 0) return -1;
    p->rename_attempted = 1;
    long renamed = syscall(SYS_renameat2, stage, GUEST_TREE_FSVERITY_NEW_NAME,
                           stage, GUEST_TREE_FSVERITY_FINAL_NAME, RENAME_NOREPLACE);
    if (renamed < 0) return -1;
    if (renamed) return refuse(EPROTO);
    if (current_stage(p, 0) < 0 || require_absent(stage, GUEST_TREE_FSVERITY_NEW_NAME) < 0) return -1;
    p->fd[FINAL_PATH] = openat(stage, GUEST_TREE_FSVERITY_FINAL_NAME, O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (p->fd[FINAL_PATH] < 0
            || check_named_leaf(p, FINAL_PATH, GUEST_TREE_FSVERITY_FINAL_NAME, p->expected.bytes, &now) < 0)
        return -1;
    if (!same_image(&p->image, &now, 1)) return refuse(ESTALE);
    p->fd[FINAL_READ] = reopen(p, FINAL_PATH, O_RDONLY | O_NONBLOCK);
    if (p->fd[FINAL_READ] < 0 || check_final_leaf(p, 1) < 0 || verify_publication(p) < 0
            || fsync(p->fd[SYNC_DIR]) < 0 || verify_publication(p) < 0) return -1;
    return 0;
}

int guest_tree_fsverity_provision_publish(struct guest_tree_fsverity_provision *p) {
    if (valid(p) < 0) return -1;
    if (p->state != VERIFIED || !p->enable_attempted || p->rename_attempted)
        return refuse(p->sticky ? p->sticky : EBUSY);
    p->state = PUBLISHING;
    if (publish(p) < 0) {
        sticky(p, errno);
        p->state = REFUSED;
        return refuse(p->sticky);
    }
    p->state = PUBLISHED;
    return 0;
}

enum guest_tree_fsverity_provision_release
guest_tree_fsverity_provision_close(struct guest_tree_fsverity_provision *p) {
    if (valid(p) < 0) return GTVP_HOLD;
    if (p->state == CLOSED) {
        if (p->sticky) errno = p->sticky;
        return p->terminal;
    }
    if (p->state == STARTING || p->state == PUBLISHING || p->state == CLOSING) {
        errno = EBUSY;
        return GTVP_HOLD;
    }
    int published = p->state == PUBLISHED && p->rename_attempted;
    p->state = CLOSING;
    if (published && verify_publication(p) < 0) sticky(p, errno);
    if (p->creation_attempted && !published) sticky(p, EINPROGRESS);
    for (unsigned i = FD_COUNT; i > 0; --i) (void)close_owned(p, (int)i - 1);
    p->terminal = close_outcome(p->creation_attempted, published, p->sticky);
    p->state = CLOSED;
    if (p->sticky) errno = p->sticky;
    return p->terminal;
}

static void copy_identity(const struct statx *image,
        struct guest_tree_fsverity_provision_identity *out) {
    out->mount_id = image->stx_mnt_id;
    out->dev_major = image->stx_dev_major;
    out->dev_minor = image->stx_dev_minor;
    out->inode = image->stx_ino;
    out->size = image->stx_size;
    out->mtime_sec = image->stx_mtime.tv_sec;
    out->mtime_nsec = image->stx_mtime.tv_nsec;
    out->ctime_sec = image->stx_ctime.tv_sec;
    out->ctime_nsec = image->stx_ctime.tv_nsec;
}

int guest_tree_fsverity_provision_published_identity(const struct guest_tree_fsverity_provision *p,
        struct guest_tree_fsverity_provision_identity *out) {
    if (!out) return refuse(EINVAL);
    memset(out, 0, sizeof(*out));
    if (valid(p) < 0) return -1;
    if (p->state != CLOSED) return refuse(EBUSY);
    if (p->terminal != GTVP_PUBLISHED_LOCAL_CLOSED) return refuse(ENODATA);
    copy_identity(&p->image, out);
    return 0;
}

static int check_observed_leaf(struct guest_tree_fsverity_provision *observation) {
    struct statx actual;
    if (check_stage_anchors(observation, 0) < 0
            || check_named_leaf(observation, FINAL_READ, GUEST_TREE_FSVERITY_FINAL_NAME,
                                observation->expected.bytes, &actual) < 0
            || require_absent(observation->fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0)
        return -1;
    if (!same_image(&observation->image, &actual, 0)) return refuse(ESTALE);
    observation->image = actual;
    return 0;
}

static int observe_current(struct guest_tree_fsverity_provision *observation) {
    int *fd = observation->fd;
    if (open_named_anchors(observation) < 0) return -1;
    fd[STAGE] = fcntl(fd[NAMED_STAGE], F_DUPFD_CLOEXEC, 3);
    if (fd[STAGE] < 0) return -1;
    fd[NS] = openat(fd[PROC], "self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (fd[NS] < 0 || check_stage_anchors(observation, 1) < 0) return -1;
    if (observation->stage.stx_gid || (observation->stage.stx_mode & 07777) != 0700)
        return refuse(EPERM);

    fd[WITNESS] = openat(fd[STAGE], GUEST_TREE_FSVERITY_FINAL_NAME, O_PATH | O_NOFOLLOW | O_CLOEXEC);
    if (fd[WITNESS] < 0 || check_named_leaf(observation, WITNESS, GUEST_TREE_FSVERITY_FINAL_NAME,
                                           observation->expected.bytes, &observation->image) < 0
            || require_absent(fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0
            || check_stage_anchors(observation, 0) < 0) return -1;
    fd[FINAL_READ] = reopen(observation, WITNESS, O_RDONLY | O_NONBLOCK);
    if (fd[FINAL_READ] < 0) return -1;
    int flags = fcntl(fd[FINAL_READ], F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY) return refuse(EPERM);
    if (check_observed_leaf(observation) < 0 || measure(observation, FINAL_READ) < 0)
        return -1;
    return check_observed_leaf(observation);
}

int guest_tree_fsverity_provision_observe_current(
        const struct guest_tree_fsverity_provision_expected *expected,
        struct guest_tree_fsverity_provision_identity *out) {
    if (!out) return refuse(EINVAL);
    memset(out, 0, sizeof(*out));
    if (controller() < 0) return -1;
    if (!expected || !expected->bytes || expected->bytes > INT64_MAX) return refuse(EINVAL);

    struct guest_tree_fsverity_provision observation = {.expected = *expected};
    for (unsigned i = 0; i < FD_COUNT; ++i) observation.fd[i] = -1;
    if (observe_current(&observation) < 0) sticky(&observation, errno);
    for (unsigned i = FD_COUNT; i > 0; --i) (void)close_owned(&observation, (int)i - 1);
    if (observation.sticky) return refuse(observation.sticky);
    copy_identity(&observation.image, out);
    return 0;
}
#endif
