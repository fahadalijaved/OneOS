#ifndef ONEOS_GUEST_TREE_STOP_PROC_SESSION_H
#define ONEOS_GUEST_TREE_STOP_PROC_SESSION_H

#include "guest_tree_stop_proc.h"

struct guest_tree_stop_proc_session;

struct guest_tree_stop_proc_observation {
    pid_t pid;
    uint64_t started_ms, elapsed_ms; /* CLOCK_BOOTTIME around the lookup. */
    enum guest_tree_stop_proc_result result;
    int lookup_errno;
    int pidfd, poll_before_rc, poll_after_rc, poll_before_revents, poll_after_revents;
    struct guest_tree_stop_proc_birth birth;
};

struct guest_tree_stop_proc_session_sample {
    struct guest_tree_stop_proc_observation controller, child;
};

/* Root process leader. Initialize *out to NULL and keep any returned owner
 * for close. Pins the exact compiled-out kernel config on the same procfs. */
int guest_tree_stop_proc_session_open(pid_t controller_pid, pid_t child_pid,
        struct guest_tree_stop_proc_session **out);

/* Borrow the authentic held proc root. The caller must not close it. */
int guest_tree_stop_proc_session_fd(struct guest_tree_stop_proc_session *session);

/* Admit one pidfd between matching LIVE births and retain it across windows.
 * ABSENT requires direct lookup ENOENT between exit-ready polls of that same
 * pidfd (POLLIN, optionally with POLLHUP). The caller independently proves
 * current proc visibility. An observation failure ends sample admission. */
int guest_tree_stop_proc_session_sample(struct guest_tree_stop_proc_session *session,
        enum guest_tree_stop_proc_result expected, struct guest_tree_stop_proc_session_sample *out);

int guest_tree_stop_proc_session_close(struct guest_tree_stop_proc_session *session);

#endif
