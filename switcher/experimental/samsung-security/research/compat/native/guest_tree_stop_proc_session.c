#define _GNU_SOURCE
#include "guest_tree_stop_proc_session.h"

#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

#define PROC_ROOT "/proc"
#define CONFIG_NAME "config.gz"
#define CONFIG_BYTES 48809U
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MODE | STATX_MNT_ID | STATX_INO)

/* Captured active Samsung config with CONFIG_PID_NS and CONFIG_USER_NS off. */
static const unsigned char expected_config_sha256[32] = {
    0xa0, 0xa8, 0x05, 0x28, 0xb7, 0x4a, 0x6d, 0xd7,
    0x2c, 0xd3, 0x70, 0x77, 0xbd, 0x7e, 0xc6, 0x0d,
    0x12, 0x91, 0xff, 0x0a, 0x8f, 0xc6, 0x48, 0x5b,
    0xb0, 0x73, 0x68, 0x7b, 0x46, 0xa4, 0x85, 0x87,
};

struct guest_tree_stop_proc_session {
    pid_t owner, controller_pid, child_pid;
    int proc, config, controller_fd, child_fd, ready, have_births, saw_absence, close_error;
    struct statx proc_id, config_id;
    struct guest_tree_stop_proc_birth controller, child;
};

static struct guest_tree_stop_proc_session one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int control_thread(void) {
    return !getuid() && !geteuid() && getpid() == gettid() ? 0 : refuse(EPERM);
}

static int valid(const struct guest_tree_stop_proc_session *session) {
    if (control_thread() < 0) return -1;
    return session == &one && session->owner == getpid() ? 0 : refuse(EINVAL);
}

static int now_ms(uint64_t *out) {
    struct timespec now;
    if (clock_gettime(CLOCK_BOOTTIME, &now) < 0) return -1;
    if (now.tv_sec < 0 || now.tv_nsec < 0 || now.tv_nsec >= 1000000000L
            || (uint64_t)now.tv_sec > (UINT64_MAX - 999) / 1000) return refuse(EOVERFLOW);
    *out = (uint64_t)now.tv_sec * 1000 + (uint64_t)now.tv_nsec / 1000000;
    return 0;
}

static int procfs(int fd) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == PROC_SUPER_MAGIC ? 0 : refuse(EXDEV);
}

static int identify(int fd, const char *name, mode_t type, struct statx *out) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, out) < 0) return -1;
    return (out->stx_mask & ID_MASK) == ID_MASK && out->stx_mnt_id && out->stx_ino
        && (out->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode;
}

static int current_node(int fd, int parent, const char *name, mode_t type, const struct statx *initial) {
    struct statx held, named;
    if (identify(fd, "", type, &held) < 0 || identify(parent, name, type, &named) < 0) return -1;
    return same_node(initial, &held) && same_node(initial, &named) ? 0 : refuse(ESTALE);
}

static int current_root(const struct guest_tree_stop_proc_session *session) {
    struct statx self_id;
    if (procfs(session->proc) < 0
            || current_node(session->proc, AT_FDCWD, PROC_ROOT, S_IFDIR, &session->proc_id) < 0
            || identify(session->proc, "self", S_IFLNK, &self_id) < 0) return -1;
    if (!same_mount(&session->proc_id, &self_id)) return refuse(EXDEV);
    char pid[24], self[24];
    int length = snprintf(pid, sizeof(pid), "%ld", (long)session->owner);
    if (length <= 0 || (size_t)length >= sizeof(pid)) return refuse(EOVERFLOW);
    ssize_t count = readlinkat(session->proc, "self", self, sizeof(self));
    if (count < 0) return -1;
    return count == length && !memcmp(self, pid, (size_t)length) ? 0 : refuse(EXDEV);
}

static int current_view(const struct guest_tree_stop_proc_session *session) {
    if (current_root(session) < 0 || procfs(session->config) < 0) return -1;
    return current_node(session->config, session->proc, CONFIG_NAME, S_IFREG, &session->config_id);
}

static int pin_config(const struct guest_tree_stop_proc_session *session) {
    struct guest_tree_sha256 hash;
    unsigned char block[4096], digest[32];
    size_t total = 0;
    guest_tree_sha256_init(&hash);
    for (;;) {
        ssize_t count = read(session->config, block, sizeof(block));
        if (count < 0) return -1;
        if (!count) break;
        if ((size_t)count > CONFIG_BYTES - total) return refuse(EOVERFLOW);
        guest_tree_sha256_update(&hash, block, (size_t)count);
        total += (size_t)count;
    }
    guest_tree_sha256_final(&hash, digest);
    if (total != CONFIG_BYTES || memcmp(digest, expected_config_sha256, sizeof(digest))) return refuse(ESTALE);
    return current_view(session);
}

int guest_tree_stop_proc_session_open(pid_t controller_pid, pid_t child_pid,
        struct guest_tree_stop_proc_session **out) {
    if (!out || *out || controller_pid <= 0 || child_pid <= 0 || controller_pid == child_pid
            || (uint64_t)controller_pid > INT32_MAX || (uint64_t)child_pid > INT32_MAX) return refuse(EINVAL);
    if (control_thread() < 0) return -1;
    if (one.owner) return refuse(EALREADY);
    one.owner = getpid();
    one.controller_pid = controller_pid;
    one.child_pid = child_pid;
    one.proc = one.config = one.controller_fd = one.child_fd = -1;
    *out = &one;
    one.proc = open(PROC_ROOT, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (one.proc < 0 || identify(one.proc, "", S_IFDIR, &one.proc_id) < 0) return -1;
    if (one.proc_id.stx_ino != 1) return refuse(EXDEV);
    if (current_root(&one) < 0 || identify(one.proc, CONFIG_NAME, S_IFREG, &one.config_id) < 0) return -1;
    if (!same_mount(&one.proc_id, &one.config_id)) return refuse(EXDEV);
    one.config = openat(one.proc, CONFIG_NAME, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (one.config < 0 || current_view(&one) < 0 || pin_config(&one) < 0) return -1;
    one.ready = 1;
    return 0;
}

int guest_tree_stop_proc_session_fd(struct guest_tree_stop_proc_session *session) {
    if (valid(session) < 0) return -1;
    if (!session->ready) return refuse(EBUSY);
    if (current_view(session) < 0) return -1;
    return session->proc;
}

static int lookup(const struct guest_tree_stop_proc_session *session, pid_t pid,
        enum guest_tree_stop_proc_result expected, struct guest_tree_stop_proc_observation *out) {
    if (current_view(session) < 0 || now_ms(&out->started_ms) < 0) return -1;
    out->pid = pid;
    out->result = guest_tree_stop_proc_read(session->proc, pid, 1, &out->birth);
    if (out->result == GUEST_TREE_STOP_PROC_ERROR) return -1;
    out->lookup_errno = out->result == GUEST_TREE_STOP_PROC_ABSENT ? errno : 0;
    if (now_ms(&out->elapsed_ms) < 0 || current_view(session) < 0) return -1;
    if (out->result != expected || out->started_ms > out->elapsed_ms
            || (out->result == GUEST_TREE_STOP_PROC_ABSENT && out->lookup_errno != ENOENT)
            || (out->result == GUEST_TREE_STOP_PROC_LIVE && (out->birth.pid != pid || !out->birth.start_ticks
                || out->birth.pid_ns_dev || out->birth.pid_ns_ino))) return refuse(ESTALE);
    return 0;
}

static int same_birth(const struct guest_tree_stop_proc_birth *a, const struct guest_tree_stop_proc_birth *b) {
    return a->pid == b->pid && a->start_ticks == b->start_ticks
        && a->pid_ns_dev == b->pid_ns_dev && a->pid_ns_ino == b->pid_ns_ino;
}

static int poll_birth(int pidfd, enum guest_tree_stop_proc_result expected, int *rc, int *revents) {
    struct pollfd pending = {.fd = pidfd, .events = POLLIN};
    *rc = poll(&pending, 1, 0);
    if (*rc < 0) return -1;
    *revents = pending.revents;
    if (expected == GUEST_TREE_STOP_PROC_LIVE)
        return *rc == 0 && *revents == 0 ? 0 : refuse(ESTALE);
    return *rc == 1 && (*revents == POLLIN || *revents == (POLLIN | POLLHUP)) ? 0 : refuse(ESTALE);
}

static int observe(const struct guest_tree_stop_proc_session *session, pid_t pid, int *pidfd,
        enum guest_tree_stop_proc_result expected, struct guest_tree_stop_proc_observation *out) {
    struct guest_tree_stop_proc_observation before = {0};
    int opening = *pidfd < 0;
    if (opening) {
        if (expected != GUEST_TREE_STOP_PROC_LIVE) return refuse(EBUSY);
        if (lookup(session, pid, expected, &before) < 0) return -1;
        long acquired = syscall(SYS_pidfd_open, pid, 0U);
        if (acquired < 0) return -1;
        if ((unsigned long)acquired > INT32_MAX) return refuse(EOVERFLOW);
        *pidfd = (int)acquired;
    }
    out->pidfd = *pidfd;
    if (poll_birth(*pidfd, expected, &out->poll_before_rc, &out->poll_before_revents) < 0
            || lookup(session, pid, expected, out) < 0
            || poll_birth(*pidfd, expected, &out->poll_after_rc, &out->poll_after_revents) < 0) return -1;
    return !opening || same_birth(&before.birth, &out->birth) ? 0 : refuse(ESTALE);
}

int guest_tree_stop_proc_session_sample(struct guest_tree_stop_proc_session *session,
        enum guest_tree_stop_proc_result expected, struct guest_tree_stop_proc_session_sample *out) {
    if (!out) return refuse(EINVAL);
    *out = (struct guest_tree_stop_proc_session_sample){0};
    if (valid(session) < 0) return -1;
    if (expected != GUEST_TREE_STOP_PROC_LIVE && expected != GUEST_TREE_STOP_PROC_ABSENT) return refuse(EINVAL);
    if (!session->ready || (expected == GUEST_TREE_STOP_PROC_ABSENT && !session->have_births)
            || (expected == GUEST_TREE_STOP_PROC_LIVE && session->saw_absence)) return refuse(EBUSY);

    struct guest_tree_stop_proc_session_sample sample = {0};
    if (observe(session, session->controller_pid, &session->controller_fd, expected, &sample.controller) < 0
            || observe(session, session->child_pid, &session->child_fd, expected, &sample.child) < 0
            || current_view(session) < 0) goto failed;
    if (sample.controller.elapsed_ms > sample.child.started_ms) { errno = ESTALE; goto failed; }
    if (expected == GUEST_TREE_STOP_PROC_ABSENT) session->saw_absence = 1;
    else if (!session->have_births) {
        session->controller = sample.controller.birth;
        session->child = sample.child.birth;
        session->have_births = 1;
    } else if (!same_birth(&session->controller, &sample.controller.birth)
            || !same_birth(&session->child, &sample.child.birth)) { errno = ESTALE; goto failed; }
    *out = sample;
    return 0;
failed:
    session->ready = 0;
    return -1;
}

static void close_cell(int *fd, int *error) {
    int held = *fd;
    *fd = -1;
    if (held >= 0 && close(held) < 0 && !*error) *error = errno;
}

int guest_tree_stop_proc_session_close(struct guest_tree_stop_proc_session *session) {
    if (valid(session) < 0) return -1;
    session->ready = 0;
    close_cell(&session->child_fd, &session->close_error);
    close_cell(&session->controller_fd, &session->close_error);
    close_cell(&session->config, &session->close_error);
    close_cell(&session->proc, &session->close_error);
    return session->close_error ? refuse(session->close_error) : 0;
}
