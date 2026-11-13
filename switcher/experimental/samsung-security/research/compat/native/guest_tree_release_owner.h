#ifndef ONEOS_GUEST_TREE_RELEASE_OWNER_H
#define ONEOS_GUEST_TREE_RELEASE_OWNER_H

#include <sys/types.h>

struct gtr_owner;

enum { GTR_WITNESSES = 3, GTR_VIEW_RIGHTS = 7 };
enum gtr_release {
    GTR_HOLD = 1,
    GTR_NO_CHILD_LOCAL_CLOSED,
    GTR_CHILD_REAPED_LOCAL_CLOSED,
    GTR_TREE_LOCAL_RELEASED
};

/*
 * Private to the single-thread tree controller. The main process thread is
 * the only caller and the only waiter/signaler of this actual child. Caller
 * initializes *out to NULL. Before fork, retain the one-shot owner in *out.
 * In the parent, consume socketpair and witness cells, including on a fork
 * failure. In the child, return zero with *out == NULL and unchanged inherited
 * cells. Child code must close its inherited parent-only cells before work.
 *
 * sockets[0] is the parent's control socket, sockets[1] the child's endpoint.
 * The three witnesses are the tree, private data and original namespace.
 * The parent may borrow its control number until STOP to send/receive, never
 * close it. A positive return is the actual PID for private credential/proc
 * readback. On error a nonnull owner still needs polling, even if fork or
 * closure of the parent's copy of the child endpoint failed.
 */
pid_t gtr_fork(struct gtr_owner **out, int sockets[2], int witnesses[GTR_WITNESSES]);

/*
 * Transfer the complete seven already authenticated SCM_RIGHTS cells from the
 * same child once, with no remaining caller aliases. On refusal the caller
 * still owns every cell and must account for it separately before publishing
 * any composed release. This function does not authenticate the received
 * roles, establish source identity, or validate the private mount graph.
 */
int gtr_take_view_rights(struct gtr_owner *owner, int rights[GTR_VIEW_RIGHTS]);

/* 1 only for actual waitpid no-progress, 0 for an actual terminal reap,
 * -1 for interrupted, nonterminal traced, unavailable, or invalid custody. */
int gtr_child_live(struct gtr_owner *owner);

/* Cut off admission and consume the exact parent control socket once. Socket
 * closure drops queued rights and requests child stop, with no reap promise. */
int gtr_request_stop(struct gtr_owner *owner);

/* Only SIGTERM and SIGKILL, once each, after cutoff. The caller owns grace
 * timing. Each attempt first checks the exact child with the sole waiter. */
int gtr_signal_child(struct gtr_owner *owner, int signal_number);

/* Nonblocking. Cut off first, then require actual terminal reap and successful
 * closure of tracked references. HOLD retains unresolved custody indefinitely.
 * Local-closed without received rights does not establish a pre-effect refusal.
 * TREE_LOCAL_RELEASED covers only our received rights, witnesses and child.
 * The tree provider separately accounts for rejected/partial rights, namespace
 * confinement, stage and guard custody. No guest return or global release. */
enum gtr_release gtr_poll_close(struct gtr_owner *owner);

#endif
