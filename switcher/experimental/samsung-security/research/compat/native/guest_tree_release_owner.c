#define _GNU_SOURCE
#include "guest_tree_release_owner.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdatomic.h>
#include <stddef.h>
#include <sys/wait.h>
#include <unistd.h>

struct gtr_owner {
    pid_t parent, child;
    int control, child_control, witnesses[GTR_WITNESSES], rights[GTR_VIEW_RIGHTS];
    int cutoff, reaped, rights_taken, term_attempted, kill_attempted;
    int close_error, wait_error;
    enum gtr_release terminal;
};

static struct gtr_owner one;
static int used;
static atomic_flag active = ATOMIC_FLAG_INIT;

static int enter(void) {
    if (getpid() != gettid()) { errno = EPERM; return -1; }
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) {
        errno = EBUSY;
        return -1;
    }
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(struct gtr_owner *owner) {
    if (enter() < 0) return -1;
    if (!used || owner != &one || getpid() != one.parent) {
        leave();
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int consume(int *cell) {
    int fd = *cell;
    *cell = -1;
    return fd;
}

static void close_owned(struct gtr_owner *owner, int *cell) {
    int saved = errno;
    int fd = consume(cell);
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) {
        owner->close_error = errno ? errno : EIO;
    }
    errno = saved;
}

static int valid_fds(const int *fds, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        if (fds[i] < 0) { errno = EBADF; return -1; }
        for (size_t j = 0; j < i; ++j) {
            if (fds[i] == fds[j]) { errno = EINVAL; return -1; }
        }
        int flags = fcntl(fds[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) { errno = EPERM; return -1; }
    }
    return 0;
}

pid_t gtr_fork(struct gtr_owner **out, int sockets[2], int witnesses[GTR_WITNESSES]) {
    if (!out || !sockets || !witnesses || *out) { errno = EINVAL; return -1; }
    if (enter() < 0) return -1;
    pid_t result = -1;
    struct sigaction disposition;
    int fds[2 + GTR_WITNESSES] = {sockets[0], sockets[1], witnesses[0], witnesses[1], witnesses[2]};
    if (used) { errno = EBUSY; goto done; }
    if (valid_fds(fds, sizeof(fds) / sizeof(fds[0])) < 0
            || sigaction(SIGCHLD, NULL, &disposition) < 0) goto done;
    if (disposition.sa_handler != SIG_DFL || disposition.sa_flags & SA_NOCLDWAIT) {
        errno = EPERM;
        goto done;
    }

    used = 1;
    one.parent = getpid();
    one.control = one.child_control = -1;
    for (size_t i = 0; i < GTR_WITNESSES; ++i) one.witnesses[i] = -1;
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i) one.rights[i] = -1;
    *out = &one;
    result = fork();
    if (result == 0) {
        *out = NULL;
        goto done;
    }

    int birth_error = result < 0 ? (errno ? errno : EIO) : 0;
    one.child = result;
    one.control = consume(&sockets[0]);
    one.child_control = consume(&sockets[1]);
    for (size_t i = 0; i < GTR_WITNESSES; ++i) one.witnesses[i] = consume(&witnesses[i]);
    close_owned(&one, &one.child_control);
    if (birth_error || one.close_error) {
        errno = birth_error ? birth_error : one.close_error;
        result = -1;
    }
done:
    leave();
    return result;
}

static int observe_child(struct gtr_owner *owner) {
    if (owner->wait_error) { errno = owner->wait_error; return -1; }
    if (owner->reaped) return 0;
    if (owner->child <= 0) { errno = ECHILD; return -1; }
    int status;
    pid_t result = waitpid(owner->child, &status, WNOHANG);
    if (result == 0) return 1;
    if (result < 0) {
        if (errno != EINTR) owner->wait_error = errno ? errno : EIO;
        return -1;
    }
    if (result != owner->child) {
        owner->wait_error = errno = EPROTO;
        return -1;
    }
    if (!WIFEXITED(status) && !WIFSIGNALED(status)) {
        errno = EINPROGRESS;
        return -1;
    }
    owner->reaped = 1;
    return 0;
}

int gtr_child_live(struct gtr_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    int result = observe_child(owner);
    leave();
    return result;
}

int gtr_take_view_rights(struct gtr_owner *owner, int rights[GTR_VIEW_RIGHTS]) {
    if (!rights) { errno = EINVAL; return -1; }
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    if (owner->cutoff || owner->rights_taken || owner->child <= 0 || owner->close_error) {
        errno = EBUSY;
        goto done;
    }
    if (valid_fds(rights, GTR_VIEW_RIGHTS) < 0) goto done;
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i) {
        if (rights[i] == owner->control) { errno = EINVAL; goto done; }
        for (size_t j = 0; j < GTR_WITNESSES; ++j) {
            if (rights[i] == owner->witnesses[j]) { errno = EINVAL; goto done; }
        }
    }
    int live = observe_child(owner);
    if (live != 1) {
        if (live == 0) errno = ECHILD;
        goto done;
    }
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i) owner->rights[i] = consume(&rights[i]);
    owner->rights_taken = 1;
    result = 0;
done:
    leave();
    return result;
}

static void cut_off(struct gtr_owner *owner) {
    owner->cutoff = 1;
    close_owned(owner, &owner->control);
}

int gtr_request_stop(struct gtr_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    cut_off(owner);
    int error = owner->close_error;
    leave();
    if (error) { errno = error; return -1; }
    return 0;
}

int gtr_signal_child(struct gtr_owner *owner, int signal_number) {
    if (signal_number != SIGTERM && signal_number != SIGKILL) { errno = EINVAL; return -1; }
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    if (!owner->cutoff) { errno = EPERM; goto done; }
    if (owner->child <= 0) { result = 0; goto done; }
    int live = observe_child(owner);
    if (live <= 0) { result = live; goto done; }
    int *attempted = signal_number == SIGTERM ? &owner->term_attempted : &owner->kill_attempted;
    if (*attempted) { result = 0; goto done; }
    *attempted = 1;
    result = kill(owner->child, signal_number);
    if (result < 0 && errno != ESRCH && !owner->close_error) {
        owner->close_error = errno ? errno : EIO;
    }
done:
    leave();
    return result;
}

enum gtr_release gtr_poll_close(struct gtr_owner *owner) {
    if (enter_owner(owner) < 0) return GTR_HOLD;
    enum gtr_release result = GTR_HOLD;
    if (owner->terminal) { result = owner->terminal; goto done; }
    cut_off(owner);
    if (owner->child > 0) {
        int live = observe_child(owner);
        if (live != 0) {
            if (live > 0) errno = EINPROGRESS;
            goto done;
        }
    }
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i) close_owned(owner, &owner->rights[i]);
    for (size_t i = 0; i < GTR_WITNESSES; ++i) close_owned(owner, &owner->witnesses[i]);
    if (owner->close_error) { errno = owner->close_error; goto done; }
    if (owner->child <= 0) owner->terminal = GTR_NO_CHILD_LOCAL_CLOSED;
    else if (owner->rights_taken) owner->terminal = GTR_TREE_LOCAL_RELEASED;
    else owner->terminal = GTR_CHILD_REAPED_LOCAL_CLOSED;
    result = owner->terminal;
done:
    leave();
    return result;
}
