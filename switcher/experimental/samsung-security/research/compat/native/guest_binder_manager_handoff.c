#define _GNU_SOURCE
#include "guest_binder_manager_handoff.h"

#include <errno.h>
#include <fcntl.h>
#include <stdatomic.h>
#include <stddef.h>
#include <unistd.h>

#define ROLE_MASK (STATX_TYPE | STATX_MODE | STATX_INO | STATX_MNT_ID)

static atomic_flag attempted = ATOMIC_FLAG_INIT;
static const char *const manager_argv[] = {"/system/bin/servicemanager", "/dev/binder", NULL};
static const enum guest_binder_manager_entry_node source_nodes[] = {
    GBME_ROOT, GBME_EXECUTABLE, GBME_INTERPRETER, GBME_BINDER
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int source_fd(const struct guest_binder_manager_entry_owner *entry, size_t role) {
    return role == GBMH_WITNESS_NAMESPACE ? entry->namespace_fd : entry->nodes[source_nodes[role]];
}

static int check_role(int copy, size_t role, const struct guest_binder_manager_entry_owner *entry) {
    const int original = source_fd(entry, role);
    if (copy < 3 || copy == original) return refuse(EBADF);
    int cloexec = fcntl(copy, F_GETFD);
    if (cloexec < 0) return -1;
    if (!(cloexec & FD_CLOEXEC)) return refuse(EXDEV);
    if (role == GBMH_WITNESS_NAMESPACE) {
        struct stat actual, expected;
        if (fstat(copy, &actual) < 0 || fstat(original, &expected) < 0) return -1;
        if (actual.st_dev != expected.st_dev || actual.st_ino != expected.st_ino) return refuse(ESTALE);
        return 0;
    }
    int flags = fcntl(copy, F_GETFL);
    if (flags < 0) return -1;
    const int path = role == GBMH_PREEXEC_ROOT || role == GBMH_WITNESS_BINDER;
    if (!!(flags & O_PATH) != path || (!path && (flags & O_ACCMODE) != O_RDONLY)) return refuse(EXDEV);

    struct statx actual;
    const struct statx *held = &entry->identities[source_nodes[role]];
    if (statx(copy, "", AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW, ROLE_MASK, &actual) < 0) return -1;
    if ((actual.stx_mask & ROLE_MASK) != ROLE_MASK || !actual.stx_mnt_id ||
            actual.stx_mnt_id != held->stx_mnt_id || actual.stx_ino != held->stx_ino ||
            actual.stx_mode != held->stx_mode || actual.stx_dev_major != held->stx_dev_major ||
            actual.stx_dev_minor != held->stx_dev_minor || actual.stx_rdev_major != held->stx_rdev_major ||
            actual.stx_rdev_minor != held->stx_rdev_minor) return refuse(ESTALE);
    return 0;
}

static int recheck_roles(struct guest_binder_manager_handoff_owner *owner) {
    for (size_t i = 0; i < GBMH_ROLE_COUNT; ++i) {
        if (check_role(owner->fd[i], i, owner->entry) < 0) return -1;
    }
    return guest_binder_manager_entry_recheck(owner->entry);
}

int guest_binder_manager_handoff_prepare(struct guest_binder_manager_handoff_owner *owner,
        struct guest_binder_manager_entry_owner *entry) {
    if (!owner || owner->state != GBMH_EMPTY || owner->source_pid || owner->entry || owner->close_error ||
            !entry || entry->state != GBME_INPUTS_HELD) return refuse(EINVAL);
    for (size_t i = 0; i < GBMH_ROLE_COUNT; ++i) if (owner->fd[i] != -1) return refuse(EINVAL);
    pid_t self = getpid();
    if (entry->source_pid != self) return refuse(ECHILD);
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_relaxed)) return refuse(EALREADY);
    owner->source_pid = self;
    owner->entry = entry;
    owner->state = GBMH_STAGING;
    if (entry->noexec) {
        owner->state = GBMH_REFUSED;
        return refuse(EACCES);
    }
    if (guest_binder_manager_entry_recheck(entry) < 0) goto refused;
    for (size_t i = 0; i < GBMH_ROLE_COUNT; ++i) {
        owner->fd[i] = fcntl(source_fd(entry, i), F_DUPFD_CLOEXEC, 3);
        if (owner->fd[i] < 0) goto refused;
    }
    if (recheck_roles(owner) < 0) goto refused;
    owner->state = GBMH_HELD;
    return 0;

refused:
    owner->state = GBMH_REFUSED;
    return -1;
}

int guest_binder_manager_handoff_borrow(struct guest_binder_manager_handoff_owner *owner,
        struct guest_binder_manager_handoff_view *out) {
    if (!owner || owner->state != GBMH_HELD || !out || out->fds || out->argv ||
            owner->source_pid != getpid()) return refuse(EINVAL);
    if (guest_binder_manager_entry_recheck(owner->entry) < 0 || recheck_roles(owner) < 0) {
        owner->state = GBMH_REFUSED;
        return -1;
    }
    out->fds = owner->fd;
    out->argv = manager_argv;
    return 0;
}

int guest_binder_manager_handoff_close(struct guest_binder_manager_handoff_owner *owner) {
    if (!owner || owner->state == GBMH_EMPTY || owner->source_pid != getpid()) return refuse(EINVAL);
    if (owner->state != GBMH_RETIRED) {
        owner->state = GBMH_RETIRED;
        for (size_t i = GBMH_ROLE_COUNT; i > 0; --i) {
            int fd = owner->fd[i - 1];
            owner->fd[i - 1] = -1;
            if (fd >= 0 && close(fd) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
        }
    }
    return owner->close_error ? refuse(owner->close_error) : 0;
}
