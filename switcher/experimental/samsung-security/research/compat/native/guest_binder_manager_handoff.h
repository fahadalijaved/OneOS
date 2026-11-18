#ifndef ONEOS_GUEST_BINDER_MANAGER_HANDOFF_H
#define ONEOS_GUEST_BINDER_MANAGER_HANDOFF_H

#include "guest_binder_manager_entry.h"

enum guest_binder_manager_handoff_state {
    GBMH_EMPTY = 0, GBMH_STAGING, GBMH_HELD, GBMH_REFUSED, GBMH_RETIRED
};

enum guest_binder_manager_handoff_role {
    GBMH_PREEXEC_ROOT = 0, GBMH_PREEXEC_EXECUTABLE,
    GBMH_WITNESS_INTERPRETER, GBMH_WITNESS_BINDER, GBMH_WITNESS_NAMESPACE,
    GBMH_ROLE_COUNT
};

struct guest_binder_manager_handoff_owner {
    enum guest_binder_manager_handoff_state state;
    pid_t source_pid;
    struct guest_binder_manager_entry_owner *entry;
    int fd[GBMH_ROLE_COUNT];
    int close_error;
};

#define GUEST_BINDER_MANAGER_HANDOFF_OWNER_INITIALIZER { .fd = {-1, -1, -1, -1, -1} }

struct guest_binder_manager_handoff_view {
    const int *fds; /* GBMH_ROLE_COUNT borrowed cells, indexed by the roles above. */
    const char *const *argv; /* Two fixed strings followed by NULL. */
};

/* One attempt from the same private child as the real entry capture. Its
 * source owner excludes concurrent namespace, pathname and descriptor writers.
 * Borrow and retain the entry through this owner's lifetime. The owner holds
 * five CLOEXEC duplicates, including on partial failure. No launch occurs. */
int guest_binder_manager_handoff_prepare(struct guest_binder_manager_handoff_owner *owner,
        struct guest_binder_manager_entry_owner *entry);

/* Rechecks the current entry, descriptor roles and CLOEXEC before returning
 * this exact table. Initialize the output pointers to NULL. Only the first
 * two roles are potential pre-exec operands. The others remain witnesses.
 * No descriptor from this table survives exec; libbinder opens /dev/binder
 * itself. Stdio, environment, credentials, exec admission, real child/pidfd
 * custody and an observer for the original successful claim are external. */
int guest_binder_manager_handoff_borrow(struct guest_binder_manager_handoff_owner *owner,
        struct guest_binder_manager_handoff_view *out);

/* Consumes our duplicates once. Entry and namespace teardown stay owned by
 * their source. A zero return means local close only. */
int guest_binder_manager_handoff_close(struct guest_binder_manager_handoff_owner *owner);

#endif
