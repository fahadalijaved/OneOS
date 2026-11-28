#define _GNU_SOURCE 1
#include "guest_tree_stage_guard.h"

#include <errno.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

#define GUARD_NAME "oneos-retained-viewprep"
#define LEASE_NAME "lease"
#define MARKER_NAME "view-blocked"

struct guest_tree_stage_guard {
    pid_t parent;
    int root, dev, directory, lease, marker;
    int marker_attempted, verified, armed, begin_ok, control_closed, finished;
    int close_error, hold_error;
    struct stat root_stat, dev_stat, directory_stat, lease_stat, marker_stat;
    struct gtc_owner *control;
};

static struct guest_tree_stage_guard one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int main_process(void) {
    return getpid() == gettid();
}

static int valid(const struct guest_tree_stage_guard *guard) {
    if (!main_process()) return refuse(EPERM);
    if (guard != &one || guard->parent != getpid()) return refuse(EINVAL);
    return 0;
}

static int hold(struct guest_tree_stage_guard *guard, int error) {
    if (!guard->hold_error) guard->hold_error = error ? error : EIO;
    return refuse(guard->hold_error);
}

static void close_owned(struct guest_tree_stage_guard *guard, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !guard->close_error)
        guard->close_error = errno ? errno : EIO;
}

static int same_object(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino &&
            a->st_mode == b->st_mode && a->st_uid == b->st_uid && a->st_gid == b->st_gid;
}

static int same_identity(const struct stat *a, const struct stat *b) {
    return same_object(a, b) && a->st_nlink == b->st_nlink && a->st_size == b->st_size &&
            a->st_mtim.tv_sec == b->st_mtim.tv_sec && a->st_mtim.tv_nsec == b->st_mtim.tv_nsec &&
            a->st_ctim.tv_sec == b->st_ctim.tv_sec && a->st_ctim.tv_nsec == b->st_ctim.tv_nsec;
}

static int safe_anchor(int fd, struct stat *out) {
    if (fstat(fd, out) < 0) return -1;
    if (!S_ISDIR(out->st_mode) || !out->st_ino || out->st_uid || (out->st_mode & 0022))
        return refuse(EPERM);
    return 0;
}

static int protected_profile(int fd, int directory, struct stat *out) {
    if (fstat(fd, out) < 0) return -1;
    if (!out->st_ino || out->st_uid || out->st_gid ||
            (directory ? !S_ISDIR(out->st_mode) : !S_ISREG(out->st_mode)) ||
            (out->st_mode & 07777) != (directory ? 0700 : 0600) ||
            (!directory && (out->st_nlink != 1 || out->st_size))) return refuse(EPERM);
    return 0;
}

static int absent(int parent, const char *name) {
    struct stat value;
    if (fstatat(parent, name, &value, AT_SYMLINK_NOFOLLOW) == 0) return refuse(EBUSY);
    return errno == ENOENT ? 0 : -1;
}

static int named_identity(int parent, const char *name, const struct stat *expected, int full) {
    struct stat value;
    if (fstatat(parent, name, &value, AT_SYMLINK_NOFOLLOW) < 0) return -1;
    if (!(full ? same_identity(&value, expected) : same_object(&value, expected)))
        return refuse(ESTALE);
    return 0;
}

static int held_identity(int fd, const struct stat *expected) {
    struct stat value;
    if (fstat(fd, &value) < 0) return -1;
    return same_identity(&value, expected) ? 0 : refuse(ESTALE);
}

static int fixed_identity(const char *path, const struct stat *expected, int full) {
    struct stat value;
    if (lstat(path, &value) < 0) return -1;
    if (!(full ? same_identity(&value, expected) : same_object(&value, expected)))
        return refuse(ESTALE);
    return 0;
}

static int guard_current(struct guest_tree_stage_guard *guard) {
    if (fixed_identity("/", &guard->root_stat, 0) < 0 ||
            named_identity(guard->root, "dev", &guard->dev_stat, 0) < 0 ||
            named_identity(guard->dev, GUARD_NAME, &guard->directory_stat, 1) < 0 ||
            held_identity(guard->directory, &guard->directory_stat) < 0 ||
            held_identity(guard->lease, &guard->lease_stat) < 0 ||
            named_identity(guard->directory, LEASE_NAME, &guard->lease_stat, 1) < 0 ||
            held_identity(guard->marker, &guard->marker_stat) < 0 ||
            named_identity(guard->directory, MARKER_NAME, &guard->marker_stat, 1) < 0 ||
            absent(guard->directory, "writer-blocked") < 0 ||
            absent(guard->directory, "legacy-blocked") < 0 ||
            flock(guard->lease, LOCK_EX | LOCK_NB) < 0) return hold(guard, errno);
    return 0;
}

int guest_tree_stage_guard_acquire(struct guest_tree_stage_guard **out) {
    const int dir_flags = O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC;
    struct guest_tree_stage_guard *guard = &one;
    if (!main_process()) return refuse(EPERM);
    if (!out || *out || guard->parent) return refuse(EINVAL);
    guard->parent = getpid();
    guard->root = guard->dev = guard->directory = guard->lease = guard->marker = -1;
    *out = guard;

    guard->root = open("/", dir_flags);
    if (guard->root < 0 || safe_anchor(guard->root, &guard->root_stat) < 0) return -1;
    guard->dev = openat(guard->root, "dev", dir_flags);
    if (guard->dev < 0 || safe_anchor(guard->dev, &guard->dev_stat) < 0) return -1;
    guard->directory = openat(guard->dev, GUARD_NAME, dir_flags);
    if (guard->directory < 0 ||
            protected_profile(guard->directory, 1, &guard->directory_stat) < 0) return -1;
    guard->lease = openat(guard->directory, LEASE_NAME, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
    if (guard->lease < 0 || protected_profile(guard->lease, 0, &guard->lease_stat) < 0 ||
            flock(guard->lease, LOCK_EX | LOCK_NB) < 0 ||
            named_identity(guard->root, "dev", &guard->dev_stat, 0) < 0 ||
            named_identity(guard->dev, GUARD_NAME, &guard->directory_stat, 0) < 0 ||
            named_identity(guard->directory, LEASE_NAME, &guard->lease_stat, 1) < 0 ||
            absent(guard->directory, "writer-blocked") < 0 ||
            absent(guard->directory, "legacy-blocked") < 0 ||
            absent(guard->directory, MARKER_NAME) < 0) return -1;

    /* This is a negative reservation. A failed or unobserved creation is
     * never converted into an owned marker or an unarmed release. */
    guard->marker_attempted = 1;
    if (mkdirat(guard->directory, MARKER_NAME, 0700) < 0) return hold(guard, errno);
    guard->marker = openat(guard->directory, MARKER_NAME, dir_flags);
    if (guard->marker < 0 || protected_profile(guard->marker, 1, &guard->marker_stat) < 0 ||
            protected_profile(guard->directory, 1, &guard->directory_stat) < 0) return hold(guard, errno);
    if (guard_current(guard) < 0) return -1;
    guard->verified = 1;
    return 0;
}

int guest_tree_stage_guard_check(struct guest_tree_stage_guard *guard) {
    if (valid(guard) < 0) return -1;
    if (guard->hold_error) return refuse(guard->hold_error);
    if (guard->finished || !guard->verified) return refuse(EINVAL);
    if (guard->armed && !guard->begin_ok && !guard->control_closed) return refuse(EINPROGRESS);
    return guard_current(guard);
}

int guest_tree_stage_guard_begin(struct guest_tree_stage_guard *guard,
        struct gtc_owner **out, int witnesses[GTR_WITNESSES]) {
    if (!out || *out || !witnesses) return refuse(EINVAL);
    if (guest_tree_stage_guard_check(guard) < 0) return -1;
    if (guard->armed) return refuse(EALREADY);
    guard->armed = 1;
    int result = gtc_begin(&guard->control, witnesses);
    int failure = errno;
    *out = guard->control;
    if (!guard->control) return hold(guard, result ? failure : EPROTO);
    if (result != 0) return refuse(failure ? failure : EIO);
    guard->begin_ok = 1;
    return 0;
}

int guest_tree_stage_guard_poll_control(struct guest_tree_stage_guard *guard) {
    if (valid(guard) < 0) return -1;
    if (guard->hold_error) return refuse(guard->hold_error);
    if (!guard->armed || !guard->control) return refuse(EINVAL);
    if (guard->control_closed) return 0;
    enum gtr_release progress = gtc_poll_close(guard->control);
    enum gtr_release expected = guard->begin_ok ? GTR_TREE_LOCAL_RELEASED : GTR_NO_CHILD_LOCAL_CLOSED;
    if (progress == GTR_HOLD) return refuse(EAGAIN);
    if (progress != expected) return hold(guard, EINPROGRESS);
    guard->control_closed = 1;
    return 0;
}

int guest_tree_stage_guard_finish(struct guest_tree_stage_guard *guard) {
    if (valid(guard) < 0) return -1;
    if (guard->finished) return 0;
    if (guard->hold_error) return refuse(guard->hold_error);
    if (guard->marker_attempted && !guard->verified) return hold(guard, EINPROGRESS);
    if (guard->armed && guest_tree_stage_guard_poll_control(guard) < 0) return -1;
    if (guard->verified && guard_current(guard) < 0) return -1;

    close_owned(guard, &guard->marker);
    close_owned(guard, &guard->directory);
    close_owned(guard, &guard->dev);
    close_owned(guard, &guard->root);
    if (guard->close_error) return hold(guard, guard->close_error);
    close_owned(guard, &guard->lease);
    if (guard->close_error) return hold(guard, guard->close_error);

    /* Every cooperative acquirer still refuses this exact negative after
     * the last close. Do not acquire another FD or retry any failed removal. */
    if (guard->verified &&
            (fixed_identity("/", &guard->root_stat, 0) < 0 ||
             fixed_identity("/dev", &guard->dev_stat, 0) < 0 ||
             fixed_identity(GUEST_TREE_GUARD_PATH, &guard->directory_stat, 1) < 0 ||
             fixed_identity(GUEST_TREE_GUARD_PATH "/" LEASE_NAME, &guard->lease_stat, 1) < 0 ||
             fixed_identity(GUEST_TREE_GUARD_PATH "/" MARKER_NAME, &guard->marker_stat, 1) < 0 ||
             rmdir(GUEST_TREE_GUARD_PATH "/" MARKER_NAME) < 0)) return hold(guard, errno);
    guard->finished = 1;
    return 0;
}
