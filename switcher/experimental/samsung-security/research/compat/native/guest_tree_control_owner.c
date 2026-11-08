#define _GNU_SOURCE
#include "guest_tree_control_owner.h"
#include "guest_tree_child_view.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdatomic.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define GTC_MAGIC UINT32_C(0x47564f33)
#define GTC_PREPARE_MS UINT64_C(30000)
#define GTC_GRACE_MS UINT64_C(2000)
enum { W_PARTIAL = 1, W_ERROR = 2, W_CANCEL = 3 };
enum { S_PRIVATE = 2, S_READBACK = 11, S_IPC = 12, MAX_RIGHTS = 32 };

/* Exact private GVO v3 shape. Loop fields are reserved zero in the tree build. */
struct gtc_wire {
    uint32_t magic, version, kind, stage;
    int32_t error, pid;
    uint32_t uid, gid;
    struct gtc_observation view;
    uint64_t image_dev, image_inode, loop_device;
    uint32_t loop_number, loop_flags;
    uint64_t reserved[2];
};

_Static_assert(sizeof(struct gtc_wire) == 200 && offsetof(struct gtc_wire, view) == 32
               && offsetof(struct gtc_wire, reserved) == 184, "GVO v3 wire layout");

struct gtc_owner {
    struct gtr_owner *release;
    pid_t parent, child;
    uid_t uid;
    gid_t gid;
    int control, witness[GTR_WITNESSES]; /* borrowed until actual cutoff/drain */
    int cutoff, close_error, stop_error, held, receive_attempted, kill_due;
    uint64_t deadline, kill_at;
};

static struct gtc_owner one;
static int used;
static atomic_flag active = ATOMIC_FLAG_INIT;

static int enter(void) {
    if (getpid() != gettid()) { errno = EPERM; return -1; }
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) { errno = EBUSY; return -1; }
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(struct gtc_owner *owner) {
    if (enter() < 0) return -1;
    if (!used || owner != &one || getpid() != one.parent) {
        leave();
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static void close_cell(int *cell, int *error) {
    int fd = *cell;
    int saved = errno;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !*error) *error = errno ? errno : EIO;
    errno = saved;
}

static void close_received(int rights[MAX_RIGHTS], size_t count, int *error) {
    for (size_t n = 0; n < count; ++n) {
        if (rights[n] < 0) continue;
        for (size_t j = n + 1; j < count; ++j) {
            if (rights[j] == rights[n]) {
                rights[j] = -1;
                if (!*error) *error = EPROTO;
            }
        }
        close_cell(&rights[n], error);
    }
}

static int now_ms(uint64_t *value) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0) return -1;
    if (t.tv_sec < 0 || t.tv_nsec < 0 || t.tv_nsec >= 1000000000L
            || (uint64_t)t.tv_sec > (UINT64_MAX - 999) / 1000) { errno = EOVERFLOW; return -1; }
    *value = (uint64_t)t.tv_sec * 1000 + (uint64_t)t.tv_nsec / 1000000;
    return 0;
}

static int decimal(const char *text) {
    unsigned value = 0;
    if (!*text) return -1;
    while (*text) {
        unsigned digit = (unsigned char)*text++ - '0';
        if (digit > 9 || value > ((unsigned)INT_MAX - digit) / 10) return -1;
        value = value * 10 + digit;
    }
    return (int)value;
}

static int restrict_child_fds(int control, const int witness[GTR_WITNESSES]) {
    DIR *directory = opendir("/proc/self/fd");
    if (!directory) return -1;
    int self = dirfd(directory);
    int error = self < 0 ? errno : 0;
    while (!error) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) { error = errno; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        int fd = decimal(entry->d_name);
        if (fd < 0) { error = EPROTO; break; }
        if (fd != self && fd != control && fd != witness[0] && fd != witness[1] && fd != witness[2]) {
            close_cell(&fd, &error);
        }
    }
    if (closedir(directory) < 0 && !error) error = errno;
    if (error) { errno = error; return -1; }
    return 0;
}

static int sole_thread(void) {
    DIR *directory = opendir("/proc/self/task");
    if (!directory) return -1;
    unsigned count = 0;
    int error = 0;
    while (!error) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) { error = errno; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        if (decimal(entry->d_name) != getpid() || ++count != 1) error = EPERM;
    }
    if (closedir(directory) < 0 && !error) error = errno;
    if (!error && count != 1) error = EPERM;
    if (error) { errno = error; return -1; }
    return 0;
}

static void init_wire(struct gtc_wire *packet, uint32_t kind, uint32_t stage) {
    memset(packet, 0, sizeof(*packet));
    packet->magic = GTC_MAGIC;
    packet->version = 3;
    packet->kind = kind;
    packet->stage = stage;
    packet->pid = getpid();
    packet->uid = geteuid();
    packet->gid = getegid();
}

static int send_wire(int socket, struct gtc_wire *packet, const int *rights) {
    struct iovec iov = {packet, sizeof(*packet)};
    union { struct cmsghdr align; unsigned char bytes[CMSG_SPACE(GTR_VIEW_RIGHTS * sizeof(int))]; } control;
    struct msghdr message = {.msg_iov = &iov, .msg_iovlen = 1};
    if (rights) {
        memset(&control, 0, sizeof(control));
        message.msg_control = control.bytes;
        message.msg_controllen = sizeof(control.bytes);
        struct cmsghdr *c = CMSG_FIRSTHDR(&message);
        c->cmsg_level = SOL_SOCKET;
        c->cmsg_type = SCM_RIGHTS;
        c->cmsg_len = CMSG_LEN(GTR_VIEW_RIGHTS * sizeof(int));
        memcpy(CMSG_DATA(c), rights, GTR_VIEW_RIGHTS * sizeof(int));
    }
    ssize_t sent = sendmsg(socket, &message, MSG_NOSIGNAL | MSG_DONTWAIT);
    if (sent == (ssize_t)sizeof(*packet)) return 0;
    if (sent >= 0) errno = EPROTO;
    return -1;
}

static int receive_wire(int socket, struct gtc_wire *packet, int rights[MAX_RIGHTS], size_t *count,
                        pid_t pid, uid_t uid, gid_t gid, int *close_error) {
    union {
        struct cmsghdr align;
        unsigned char bytes[CMSG_SPACE(MAX_RIGHTS * sizeof(int)) + CMSG_SPACE(sizeof(struct ucred))];
    } control;
    struct iovec iov = {packet, sizeof(*packet)};
    struct msghdr message = {.msg_iov = &iov, .msg_iovlen = 1,
                             .msg_control = control.bytes, .msg_controllen = sizeof(control.bytes)};
    memset(packet, 0, sizeof(*packet));
    memset(&control, 0, sizeof(control));
    *count = 0;
    ssize_t length = recvmsg(socket, &message, MSG_CMSG_CLOEXEC | MSG_DONTWAIT);
    if (length < 0) return -1;
    int bad = length != (ssize_t)sizeof(*packet) || (message.msg_flags & (MSG_TRUNC | MSG_CTRUNC));
    unsigned credential_messages = 0, rights_messages = 0;
    struct ucred credentials = {0};
    if (message.msg_controllen > sizeof(control.bytes)) {
        message.msg_controllen = sizeof(control.bytes);
        if (!*close_error) *close_error = EPROTO;
        bad = 1;
    }
    for (struct cmsghdr *c = CMSG_FIRSTHDR(&message); c; c = CMSG_NXTHDR(&message, c)) {
        size_t offset = (size_t)((unsigned char *)c - control.bytes);
        if (offset > message.msg_controllen || c->cmsg_len < CMSG_LEN(0)
                || c->cmsg_len > message.msg_controllen - offset) {
            if (!*close_error) *close_error = EPROTO;
            bad = 1;
            break;
        }
        size_t bytes = c->cmsg_len - CMSG_LEN(0);
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS) {
            ++rights_messages;
            if (bytes % sizeof(int)) bad = 1;
            for (size_t n = 0; n + sizeof(int) <= bytes; n += sizeof(int)) {
                int fd;
                memcpy(&fd, CMSG_DATA(c) + n, sizeof(fd));
                if (*count < MAX_RIGHTS) rights[(*count)++] = fd;
                else { close_cell(&fd, close_error); bad = 1; }
            }
        } else if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_CREDENTIALS) {
            ++credential_messages;
            if (bytes == sizeof(credentials)) memcpy(&credentials, CMSG_DATA(c), bytes);
            else bad = 1;
        } else bad = 1;
    }
    if (credential_messages != 1 || rights_messages > 1
            || credentials.pid != pid || credentials.uid != uid || credentials.gid != gid
            || packet->magic != GTC_MAGIC || packet->version != 3 || packet->pid != pid
            || packet->uid != uid || packet->gid != gid || packet->reserved[0] || packet->reserved[1]
            || packet->image_dev || packet->image_inode || packet->loop_device || packet->loop_number
            || packet->loop_flags) bad = 1;
    for (size_t n = 0; n < *count; ++n) {
        int flags = fcntl(rights[n], F_GETFD);
        if (flags < 0 || !(flags & FD_CLOEXEC)) bad = 1;
        for (size_t j = 0; j < n; ++j) if (rights[j] == rights[n]) bad = 1;
    }
    if (bad) { errno = EPROTO; return -1; }
    return 0;
}

static int valid_observation(const struct gtc_observation *view) {
    if (!view->namespace_inode || !view->namespace_dev || view->mounts[GTC_NAMESPACE]
            || !view->data_group || !view->mirror_group || view->data_group == view->mirror_group
            || !view->alias_native || !view->alias_guest || view->alias_native == view->alias_guest
            || !view->guest_data_mount || !view->guest_mirror_mount) return 0;
    for (size_t n = 1; n < GTR_VIEW_RIGHTS; ++n) if (!view->mounts[n]) return 0;
    return 1;
}

static _Noreturn void run_child(int control, const int witnesses[GTR_WITNESSES]) {
    struct gtc_wire packet;
    struct sigaction disposition = {.sa_handler = SIG_DFL};
    sigset_t mask;
    struct gtc_child_inputs input = {.parent = one.parent, .witnesses = witnesses};
    struct gtc_child_view view = {0};
    for (size_t n = 0; n < GTR_VIEW_RIGHTS; ++n) view.rights[n] = -1;
    if (sigemptyset(&disposition.sa_mask) < 0 || sigemptyset(&mask) < 0
            || sigaction(SIGTERM, &disposition, NULL) < 0 || sigaction(SIGINT, &disposition, NULL) < 0
            || sigaction(SIGHUP, &disposition, NULL) < 0 || sigprocmask(SIG_SETMASK, &mask, NULL) < 0
            || prctl(PR_SET_PDEATHSIG, SIGKILL) < 0 || getppid() != one.parent
            || restrict_child_fds(control, witnesses) < 0) _exit(2);
    if (guest_tree_prepare_child_view(&input, &view, NULL) != 0 || !valid_observation(&view.observation)) {
        int error = errno;
        init_wire(&packet, W_ERROR, S_PRIVATE);
        packet.error = error > 0 && error < 4096 ? error : EPROTO;
        (void)send_wire(control, &packet, NULL);
        _exit(2);
    }
    for (size_t n = 0; n < GTR_VIEW_RIGHTS; ++n) {
        if (view.rights[n] < 0 || view.rights[n] == control) _exit(2);
        for (size_t j = 0; j < n; ++j) if (view.rights[n] == view.rights[j]) _exit(2);
    }
    init_wire(&packet, W_PARTIAL, S_READBACK);
    packet.view = view.observation;
    if (getppid() != one.parent || send_wire(control, &packet, view.rights) < 0) _exit(2);
    for (;;) {
        struct pollfd pollfd = {control, POLLIN, 0};
        int ready = poll(&pollfd, 1, 250);
        if (getppid() != one.parent) break;
        if (ready == 0 || (ready < 0 && errno == EINTR)) continue;
        if (ready < 0 || !(pollfd.revents & POLLIN)) break;
        int rights[MAX_RIGHTS], close_error = 0;
        size_t count;
        int result = receive_wire(control, &packet, rights, &count, one.parent, one.uid, one.gid, &close_error);
        close_received(rights, count, &close_error);
        struct gtc_observation empty = {0};
        if (result < 0 || count || close_error || packet.kind != W_CANCEL || packet.stage || packet.error
                || memcmp(&packet.view, &empty, sizeof(empty))) _exit(2);
        break;
    }
    _exit(0);
}

int gtc_begin(struct gtc_owner **out, int witnesses[GTR_WITNESSES]) {
    if (!out || !witnesses || *out) { errno = EINVAL; return -1; }
    if (enter() < 0) return -1;
    int result = -1;
    int sockets[2] = {-1, -1}, pass = 1;
    uid_t uid, euid, suid;
    gid_t gid, egid, sgid;
    uint64_t now;
    if (used) { errno = EBUSY; goto done; }
    if (sole_thread() < 0 || getresuid(&uid, &euid, &suid) < 0 || getresgid(&gid, &egid, &sgid) < 0) goto done;
    if (uid || euid || suid || gid != egid || gid != sgid || getpid() <= 1) { errno = EPERM; goto done; }
    if (now_ms(&now) < 0) goto done;
    if (now > UINT64_MAX - GTC_PREPARE_MS) { errno = EOVERFLOW; goto done; }
    one.parent = getpid();
    one.uid = uid;
    one.gid = gid;
    one.control = -1;
    one.deadline = now + GTC_PREPARE_MS;
    used = 1;
    *out = &one;
    if (socketpair(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC | SOCK_NONBLOCK, 0, sockets) < 0
            || setsockopt(sockets[0], SOL_SOCKET, SO_PASSCRED, &pass, sizeof(pass)) < 0
            || setsockopt(sockets[1], SOL_SOCKET, SO_PASSCRED, &pass, sizeof(pass)) < 0) goto done;
    int control = sockets[0];
    for (size_t n = 0; n < GTR_WITNESSES; ++n) one.witness[n] = witnesses[n];
    pid_t child = gtr_fork(&one.release, sockets, witnesses);
    if (child == 0) run_child(sockets[1], witnesses);
    if (one.release) one.control = control;
    if (child < 0) goto done;
    one.child = child;
    result = 0;
done:
    if (*out) {
        close_cell(&sockets[0], &one.close_error);
        close_cell(&sockets[1], &one.close_error);
    }
    leave();
    return result;
}

static int request_stop(struct gtc_owner *owner) {
    if (owner->cutoff) {
        if (owner->stop_error) { errno = owner->stop_error; return -1; }
        return 0;
    }
    owner->cutoff = 1;
    if (!owner->release) return 0;
    int control = owner->control;
    owner->control = -1; /* borrowed alias consumed before underlying close */
    if (control >= 0 && owner->child > 0) {
        struct gtc_wire cancel;
        init_wire(&cancel, W_CANCEL, 0);
        (void)send_wire(control, &cancel, NULL); /* EOF is the cutoff if CANCEL could not queue */
    }
    int result = gtr_request_stop(owner->release);
    if (result < 0) owner->stop_error = errno ? errno : EIO;
    uint64_t now;
    if (now_ms(&now) < 0 || now > UINT64_MAX - GTC_GRACE_MS) {
        owner->kill_due = 1;
        (void)gtr_signal_child(owner->release, SIGKILL);
    } else {
        owner->kill_at = now + GTC_GRACE_MS;
        (void)gtr_signal_child(owner->release, SIGTERM);
    }
    if (owner->stop_error) errno = owner->stop_error;
    return result;
}

int gtc_receive_partial(struct gtc_owner *owner, struct gtc_observation *observed) {
    if (!observed) { errno = EINVAL; return -1; }
    if (enter_owner(owner) < 0) return -1;
    memset(observed, 0, sizeof(*observed));
    if (!owner->release || owner->child <= 0 || owner->cutoff || owner->receive_attempted) {
        leave();
        errno = EBUSY;
        return -1;
    }
    owner->receive_attempted = 1;
    int result = -1;
    int rights[MAX_RIGHTS];
    size_t count = 0;
    struct gtc_wire packet;
    for (;;) {
        uint64_t now;
        if (now_ms(&now) < 0) break;
        if (now >= owner->deadline) { errno = ETIMEDOUT; break; }
        int live = gtr_child_live(owner->release);
        if (live != 1) {
            if (live < 0 && errno == EINTR) continue;
            if (live == 0) errno = ECHILD;
            break;
        }
        struct pollfd p = {owner->control, POLLIN, 0};
        uint64_t remaining = owner->deadline - now;
        int ready = poll(&p, 1, (int)(remaining < 100 ? remaining : 100));
        if (ready < 0 && errno == EINTR) continue;
        if (ready < 0) break;
        if (!ready) continue;
        if (!(p.revents & POLLIN)) { errno = EPIPE; break; }
        if (receive_wire(owner->control, &packet, rights, &count, owner->child,
                         owner->uid, owner->gid, &owner->close_error) < 0) {
            if (!count && (errno == EAGAIN || errno == EINTR)) continue;
            break;
        }
        struct gtc_observation empty = {0};
        if (packet.kind == W_ERROR && packet.stage >= S_PRIVATE && packet.stage <= S_IPC
                && packet.error > 0 && packet.error < 4096 && !count
                && !memcmp(&packet.view, &empty, sizeof(empty))) { errno = packet.error; break; }
        if (packet.kind != W_PARTIAL || packet.stage != S_READBACK || packet.error
                || count != GTR_VIEW_RIGHTS || !valid_observation(&packet.view)) { errno = EPROTO; break; }
        if (guest_tree_verify_remaining_view(owner->child, owner->witness, rights, &packet.view,
                                             &owner->close_error) != 0 || owner->close_error) break;
        if (now_ms(&now) < 0) break;
        if (now >= owner->deadline) { errno = ETIMEDOUT; break; }
        if (gtr_take_view_rights(owner->release, rights) < 0) break;
        owner->held = 1;
        *observed = packet.view;
        result = 0;
        break;
    }
    if (result < 0) {
        int primary = errno ? errno : EIO;
        close_received(rights, count, &owner->close_error);
        (void)request_stop(owner);
        errno = primary;
    }
    leave();
    return result;
}

int gtc_request_stop(struct gtc_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    int result = request_stop(owner);
    if (owner->close_error) { errno = owner->close_error; result = -1; }
    leave();
    return result;
}

enum gtr_release gtc_poll_close(struct gtc_owner *owner) {
    if (enter_owner(owner) < 0) return GTR_HOLD;
    (void)request_stop(owner);
    enum gtr_release result = GTR_NO_CHILD_LOCAL_CLOSED;
    if (owner->release) {
        result = gtr_poll_close(owner->release);
        if (result == GTR_HOLD && !owner->kill_due) {
            uint64_t now;
            if (now_ms(&now) < 0 || now >= owner->kill_at) {
                owner->kill_due = 1;
                (void)gtr_signal_child(owner->release, SIGKILL);
                result = gtr_poll_close(owner->release);
            }
        }
    }
    if (owner->close_error || owner->stop_error || (result == GTR_TREE_LOCAL_RELEASED && !owner->held)) {
        errno = owner->close_error ? owner->close_error : owner->stop_error ? owner->stop_error : EPROTO;
        result = GTR_HOLD;
    }
    leave();
    return result;
}
