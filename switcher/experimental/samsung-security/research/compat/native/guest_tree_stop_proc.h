#ifndef ONEOS_GUEST_TREE_STOP_PROC_H
#define ONEOS_GUEST_TREE_STOP_PROC_H

#include <stdint.h>
#include <sys/types.h>

struct guest_tree_stop_proc_birth {
    pid_t pid;
    uint64_t start_ticks;
    uint64_t pid_ns_dev;
    uint64_t pid_ns_ino;
};

enum guest_tree_stop_proc_result {
    GUEST_TREE_STOP_PROC_ERROR = -1,
    GUEST_TREE_STOP_PROC_ABSENT = 0,
    GUEST_TREE_STOP_PROC_LIVE = 1,
};

/* Borrow an authenticated procfs root FD for one bounded process observation.
 * ABSENT means direct numeric lookup returned ENOENT in that view. The caller
 * must separately establish visibility and namespace before using it as exit
 * evidence. A failure after opening the PID directory is always ERROR. LIVE
 * reports a sampled birth tuple, including for an extant zombie. On non-LIVE
 * results, zero a nonnull out and set errno. The caller retains proc_fd.
 * Pass expect_no_pid_namespace=0 for a real namespace witness. Pass 1 only
 * with a separately authenticated compiled-out profile. Mode 1 requires
 * direct ns/pid ENOENT and reports zero namespace fields. */
enum guest_tree_stop_proc_result guest_tree_stop_proc_read(int proc_fd, pid_t pid, int expect_no_pid_namespace,
        struct guest_tree_stop_proc_birth *out);

#endif
