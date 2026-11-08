/* Test-only POSIX boundary. No actual fork, wait, signal, or descriptor action. */
#include "guest_tree_release_owner.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

enum { FD_LIMIT = 64, CHILD = 41, PARENT = 23 };
enum event { RUNNING, EXITED, SIGNALED, STOPPED, INTERRUPTED, LOST, OTHER_CHILD };
static struct gtr_owner *owner;
static int opened[FD_LIMIT], closes[FD_LIMIT];
static int sockets[2] = {8, 9}, witnesses[GTR_WITNESSES] = {10, 11, 12};
static int rights[GTR_VIEW_RIGHTS] = {20, 21, 22, 23, 24, 25, 26};
static int checks, forks, waits, signals, close_failure = -1, signal_error;
static int pid = PARENT, tid = PARENT, bad_cloexec = -1, auto_reap, reenter_close;
static pid_t fork_result = CHILD;
static enum event child_event;

static void check(int condition, const char *text) {
    ++checks;
    if (!condition) {
        fprintf(stderr, "%s\n", text);
        exit(1);
    }
}

pid_t getpid(void) { return pid; }
pid_t gettid(void) { return tid; }

int fcntl(int fd, int command, ...) {
    check(command == F_GETFD && fd >= 0 && fd < FD_LIMIT, "exact bounded F_GETFD only");
    if (!opened[fd]) { errno = EBADF; return -1; }
    return fd == bad_cloexec ? 0 : FD_CLOEXEC;
}

int sigaction(int signal_number, const struct sigaction *input, struct sigaction *output) {
    check(signal_number == SIGCHLD && input == NULL && output != NULL, "inspect existing SIGCHLD only");
    output->sa_handler = SIG_DFL;
    output->sa_flags = auto_reap ? SA_NOCLDWAIT : 0;
    return 0;
}

pid_t fork(void) {
    ++forks;
    check(owner != NULL, "parent owner retained before fork");
    if (fork_result < 0) errno = EAGAIN;
    return fork_result;
}

pid_t waitpid(pid_t child, int *status, int options) {
    ++waits;
    check(child == CHILD && options == WNOHANG, "wait exact actual fork child");
    switch (child_event) {
        case RUNNING: return 0;
        case EXITED: *status = 0; return CHILD;
        case SIGNALED: *status = SIGTERM; return CHILD;
        case STOPPED: *status = 127; return CHILD;
        case INTERRUPTED: errno = EINTR; return -1;
        case LOST: errno = ECHILD; return -1;
        case OTHER_CHILD: *status = 0; return CHILD + 1;
    }
    abort();
}

int kill(pid_t child, int signal_number) {
    check(child == CHILD && (signal_number == SIGTERM || signal_number == SIGKILL), "signal only owned live child");
    ++signals;
    if (signal_error) { errno = signal_error; return -1; }
    return 0;
}

int close(int fd) {
    check(fd >= 0 && fd < FD_LIMIT && opened[fd], "close only actual outstanding cell");
    ++closes[fd];
    opened[fd] = 0;
    if (reenter_close && fd == 8) {
        check(gtr_poll_close(owner) == GTR_HOLD && errno == EBUSY, "reentrant poll refused");
        check(gtr_request_stop(owner) < 0 && errno == EBUSY, "reentrant cutoff refused");
    }
    if (fd == close_failure) { errno = EIO; return -1; }
    return 0;
}

static void seed(void) {
    for (int fd = 8; fd <= 12; ++fd) opened[fd] = 1;
    for (int fd = 20; fd <= 26; ++fd) opened[fd] = 1;
}

static void parent_fork(void) {
    check(gtr_fork(&owner, sockets, witnesses) == CHILD && owner != NULL && forks == 1, "actual parent branch");
    check(sockets[0] == -1 && sockets[1] == -1 && closes[9] == 1 && closes[8] == 0, "parent socket custody");
    for (int i = 0; i < GTR_WITNESSES; ++i) check(witnesses[i] == -1, "witness transfer");
}

static void take_rights(void) {
    check(gtr_take_view_rights(owner, rights) == 0, "valid rights transferred");
    for (int i = 0; i < GTR_VIEW_RIGHTS; ++i) check(rights[i] == -1, "caller right cell consumed");
}

static void tracked_close(void) {
    for (int fd = 8; fd <= 12; ++fd) check(closes[fd] == 1, "original cell closed once");
}

static void success(void) {
    parent_fork();
    take_rights();
    check(gtr_signal_child(owner, SIGTERM) < 0 && signals == 0, "stop required before signal");
    check(gtr_request_stop(owner) == 0 && closes[8] == 1, "control consumed first");
    check(gtr_poll_close(owner) == GTR_HOLD && closes[10] == 0 && closes[20] == 0, "live child retains rights");
    check(gtr_signal_child(owner, SIGTERM) == 0 && gtr_signal_child(owner, SIGTERM) == 0 && signals == 1,
          "TERM one attempt");
    check(gtr_signal_child(owner, SIGKILL) == 0 && gtr_signal_child(owner, SIGKILL) == 0 && signals == 2,
          "KILL one attempt");
    child_event = EXITED;
    check(gtr_poll_close(owner) == GTR_TREE_LOCAL_RELEASED, "actual reap and close earn local tree terminal");
    int observed = waits;
    check(gtr_poll_close(owner) == GTR_TREE_LOCAL_RELEASED && gtr_signal_child(owner, SIGKILL) == 0
          && signals == 2 && waits == observed, "sticky terminal without syscalls");
    tracked_close();
    for (int fd = 20; fd <= 26; ++fd) check(closes[fd] == 1, "received right closed once");
}

static void fork_failure(void) {
    fork_result = -1;
    check(gtr_fork(&owner, sockets, witnesses) < 0 && errno == EAGAIN && owner != NULL, "retained failed fork");
    check(gtr_poll_close(owner) == GTR_NO_CHILD_LOCAL_CLOSED && waits == 0 && signals == 0, "known no child");
    tracked_close();
}

static void child_branch(void) {
    fork_result = 0;
    check(gtr_fork(&owner, sockets, witnesses) == 0 && owner == NULL, "child receives no release owner");
    check(sockets[0] == 8 && sockets[1] == 9 && witnesses[0] == 10 && witnesses[2] == 12,
          "inherited caller cells unchanged");
    check(waits == 0 && closes[8] == 0 && closes[9] == 0, "child branch performs no parent cleanup");
}

static void wait_loss(enum event event) {
    parent_fork();
    take_rights();
    child_event = event;
    check(gtr_poll_close(owner) == GTR_HOLD && closes[8] == 1 && closes[20] == 0, "lost waiter retains rights");
    int observed = waits;
    child_event = EXITED;
    check(gtr_poll_close(owner) == GTR_HOLD && gtr_signal_child(owner, SIGKILL) < 0
          && waits == observed && signals == 0, "permanent wait ambiguity no numeric retry or signal");
}

static void close_uncertain(void) {
    parent_fork();
    take_rights();
    child_event = EXITED;
    close_failure = 22;
    check(gtr_poll_close(owner) == GTR_HOLD && errno == EIO, "close-after-progress remains uncertain");
    opened[22] = 1; /* a number now represents a different resource */
    close_failure = -1;
    check(gtr_poll_close(owner) == GTR_HOLD && closes[22] == 1 && opened[22], "no close of reused number");
    tracked_close();
    for (int fd = 20; fd <= 26; ++fd) check(closes[fd] == 1, "all independent closes attempted");
}

static void early_uncertain(void) {
    close_failure = 9;
    check(gtr_fork(&owner, sockets, witnesses) < 0 && errno == EIO && owner != NULL,
          "postfork close error preserves actual parent custody");
    check(gtr_request_stop(owner) < 0 && closes[8] == 1, "stop still consumes exact parent endpoint");
    child_event = SIGNALED;
    check(gtr_poll_close(owner) == GTR_HOLD && waits == 1 && signals == 0, "real reap does not repair prior close");
    tracked_close();
}

static void nonterminal(void) {
    parent_fork();
    take_rights();
    child_event = STOPPED;
    check(gtr_poll_close(owner) == GTR_HOLD && closes[20] == 0, "trace stop is not reap");
    child_event = INTERRUPTED;
    check(gtr_poll_close(owner) == GTR_HOLD && errno == EINTR && closes[20] == 0, "EINTR is not reap");
    child_event = SIGNALED;
    check(gtr_poll_close(owner) == GTR_TREE_LOCAL_RELEASED, "real signal-terminal status");
    tracked_close();
}

static void refuse_rights(void) {
    parent_fork();
    int alias[GTR_VIEW_RIGHTS] = {8, 21, 22, 23, 24, 25, 26};
    check(gtr_take_view_rights(owner, alias) < 0 && alias[0] == 8 && alias[6] == 26, "borrowed control alias refused");
    bad_cloexec = 24;
    check(gtr_take_view_rights(owner, rights) < 0 && rights[0] == 20 && rights[6] == 26, "missing CLOEXEC refuses all");
    bad_cloexec = -1;
    check(gtr_request_stop(owner) == 0 && gtr_take_view_rights(owner, rights) < 0, "cutoff forbids adoption");
    child_event = EXITED;
    check(gtr_poll_close(owner) == GTR_CHILD_REAPED_LOCAL_CLOSED && closes[20] == 0, "no accepted rights is distinct");
    tracked_close();
}

static void reentrant(void) {
    parent_fork();
    take_rights();
    tid = PARENT + 1;
    check(gtr_poll_close(owner) == GTR_HOLD && errno == EPERM && closes[8] == 0, "non-owner thread refused");
    tid = PARENT;
    reenter_close = 1;
    child_event = EXITED;
    check(gtr_poll_close(owner) == GTR_TREE_LOCAL_RELEASED && waits == 2, "outer wait only");
    tracked_close();
}

static void disposition(void) {
    auto_reap = 1;
    check(gtr_fork(&owner, sockets, witnesses) < 0 && !owner && forks == 0 && sockets[0] == 8,
          "auto-reap profile refuses before adoption");
    auto_reap = 0;
    parent_fork();
    struct gtr_owner *extra = NULL;
    int extra_sockets[2] = {8, 9};
    int extra_witnesses[GTR_WITNESSES] = {10, 11, 12};
    check(gtr_fork(&extra, extra_sockets, extra_witnesses) < 0 && !extra && forks == 1,
          "no second owner or fork");
    child_event = EXITED;
    check(gtr_poll_close(owner) == GTR_CHILD_REAPED_LOCAL_CLOSED, "first owner unaffected");
}

static void signal_race(int error) {
    parent_fork();
    take_rights();
    check(gtr_request_stop(owner) == 0, "request stop");
    signal_error = error;
    check(gtr_signal_child(owner, SIGTERM) < 0 && errno == error && signals == 1, "owned signal failure");
    check(gtr_poll_close(owner) == GTR_HOLD && closes[20] == 0, "signal error is not reap");
    child_event = EXITED;
    enum gtr_release terminal = error == ESRCH ? GTR_TREE_LOCAL_RELEASED : GTR_HOLD;
    check(gtr_poll_close(owner) == terminal, "only ESRCH is resolved by actual reap");
    tracked_close();
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    seed();
    const char *name = argv[1];
    if (!strcmp(name, "success")) success();
    else if (!strcmp(name, "fork-failure")) fork_failure();
    else if (!strcmp(name, "child-branch")) child_branch();
    else if (!strcmp(name, "lost")) wait_loss(LOST);
    else if (!strcmp(name, "other-child")) wait_loss(OTHER_CHILD);
    else if (!strcmp(name, "close-uncertain")) close_uncertain();
    else if (!strcmp(name, "early-uncertain")) early_uncertain();
    else if (!strcmp(name, "nonterminal")) nonterminal();
    else if (!strcmp(name, "refuse-rights")) refuse_rights();
    else if (!strcmp(name, "reentrant")) reentrant();
    else if (!strcmp(name, "disposition")) disposition();
    else if (!strcmp(name, "signal-esrch")) signal_race(ESRCH);
    else if (!strcmp(name, "signal-uncertain")) signal_race(EPERM);
    else return 2;
    printf("PASS %s %d\n", name, checks);
    return 0;
}
