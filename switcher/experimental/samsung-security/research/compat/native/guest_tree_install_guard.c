#define _GNU_SOURCE
#include "guest_tree_install_guard.h"

#include "guest_tree_fsverity_provision.h"
#include "guest_tree_source_mounts.h"
#include "guest_tree_stage_guard.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define WRITER_MARKER "writer-blocked"

enum { ROOT, DATA, LOCAL, TMP, STAGE, PROC, PROC_NS, DEV, GUARD, LEASE, MARKER, NS, COUNT };

struct location { int parent; const char *leaf, *path; };
static const struct location location[NS] = {
    [ROOT] = {AT_FDCWD, "/", "/"},
    [DATA] = {ROOT, "data", "/data"},
    [LOCAL] = {DATA, "local", "/data/local"},
    [TMP] = {LOCAL, "tmp", "/data/local/tmp"},
    [STAGE] = {TMP, &GUEST_TREE_STAGE_PATH[sizeof("/data/local/tmp")], GUEST_TREE_STAGE_PATH},
    [PROC] = {ROOT, "proc", "/proc"},
    [PROC_NS] = {PROC, "self/ns", "/proc/self/ns"},
    [DEV] = {ROOT, "dev", "/dev"},
    [GUARD] = {DEV, &GUEST_TREE_GUARD_PATH[sizeof("/dev")], GUEST_TREE_GUARD_PATH},
    [LEASE] = {GUARD, "lease", GUEST_TREE_GUARD_PATH "/lease"},
    [MARKER] = {GUARD, WRITER_MARKER, GUEST_TREE_GUARD_PATH "/" WRITER_MARKER},
};

struct guest_tree_install_guard {
    pid_t pid;
    int fd[COUNT];
    struct statx identity[NS];
    struct stat namespace;
    int stage_known, marker_attempted, ready, finished, error;
};

static struct guest_tree_install_guard one;
static atomic_flag active = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int hold(struct guest_tree_install_guard *guard, int error) {
    if (!guard->error) guard->error = error > 0 ? error : EIO;
    guard->ready = 0;
    return refuse(guard->error);
}

static int enter(void) {
    if (getpid() != gettid() || getuid() || geteuid() || getegid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(const struct guest_tree_install_guard *guard) {
    if (enter() < 0) return -1;
    if (guard == &one && guard->pid == getpid()) return 0;
    leave();
    return refuse(EINVAL);
}

static void close_cell(struct guest_tree_install_guard *guard, int slot) {
    int fd = guard->fd[slot];
    guard->fd[slot] = -1;
    if (fd >= 0 && close(fd) < 0) (void)hold(guard, errno);
}

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return flags & FD_CLOEXEC ? 0 : refuse(EINVAL);
}

static int fs_type(int fd, unsigned long expected) {
    struct statfs value;
    if (fstatfs(fd, &value) < 0) return -1;
    return (unsigned long)value.f_type == expected ? 0 : refuse(EXDEV);
}

static int sample(int fd, const char *name, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO
        | STATX_MNT_ID | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME;
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_mnt_id || !value->stx_ino) return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b, int full) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
        && (!full || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
            && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
            && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int named(const struct guest_tree_install_guard *guard, int slot, int held, int full) {
    const struct location *where = &location[slot];
    const struct statx *expected = &guard->identity[slot];
    struct statx value;
    if (sample(AT_FDCWD, where->path, &value) < 0) return -1;
    if (!same_node(expected, &value, full)) return refuse(ESTALE);
    if (!held) return 0;
    if (sample(guard->fd[slot], "", &value) < 0) return -1;
    if (!same_node(expected, &value, full)) return refuse(ESTALE);
    if (where->parent == AT_FDCWD) return 0;
    if (sample(guard->fd[where->parent], where->leaf, &value) < 0) return -1;
    return same_node(expected, &value, full) ? 0 : refuse(ESTALE);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int ns_identity(int fd, struct stat *value) {
    if (cloexec(fd) < 0 || fs_type(fd, NSFS_MAGIC) < 0 || fstat(fd, value) < 0) return -1;
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS && value->st_ino ? 0 : refuse(EXDEV);
}

static int stage_current(const struct guest_tree_install_guard *guard, int held) {
    for (int slot = ROOT; slot <= PROC_NS; ++slot) {
        if (named(guard, slot, held, 0) < 0) return -1;
    }
    int base = held ? guard->fd[PROC_NS] : AT_FDCWD;
    const char *path = held ? "mnt" : "/proc/self/ns/mnt";
    struct statx link;
    struct stat live;
    if (sample(base, path, &link) < 0) return -1;
    if (!S_ISLNK(link.stx_mode) || !same_mount(&guard->identity[PROC], &link)) return refuse(EXDEV);
    /* Follow only the authenticated proc namespace link. */
    if (fstatat(base, path, &live, 0) < 0) return -1;
    if (!same_ns(&guard->namespace, &live)) return refuse(ESTALE);
    if (!held) return 0;
    struct statvfs flags;
    if (ns_identity(guard->fd[NS], &live) < 0 || fstatvfs(guard->fd[STAGE], &flags) < 0) return -1;
    return same_ns(&guard->namespace, &live) && !(flags.f_flag & ST_RDONLY) ? 0 : refuse(EXDEV);
}

static int absent(int fd, const char *path) {
    struct stat value;
    if (fstatat(fd, path, &value, AT_SYMLINK_NOFOLLOW) == 0) return refuse(EBUSY);
    return errno == ENOENT ? 0 : -1;
}

static int other_markers(const struct guest_tree_install_guard *guard, int held) {
    int base = held ? guard->fd[GUARD] : AT_FDCWD;
    const char *view = held ? "view-blocked" : GUEST_TREE_GUARD_PATH "/view-blocked";
    const char *legacy = held ? "legacy-blocked" : GUEST_TREE_GUARD_PATH "/legacy-blocked";
    return absent(base, view) < 0 ? -1 : absent(base, legacy);
}

static int guard_current(const struct guest_tree_install_guard *guard, int held, int marked) {
    for (int slot = DEV; slot <= (marked ? MARKER : LEASE); ++slot) {
        if (named(guard, slot, held, slot != DEV && (marked || slot != GUARD)) < 0) return -1;
    }
    if (other_markers(guard, held) < 0) return -1;
    return !held ? 0 : flock(guard->fd[LEASE], LOCK_EX | LOCK_NB);
}

static int open_node(struct guest_tree_install_guard *guard, int slot, int flags) {
    const struct location *where = &location[slot];
    int parent = where->parent == AT_FDCWD ? AT_FDCWD : guard->fd[where->parent];
    guard->fd[slot] = openat(parent, where->leaf, flags);
    if (guard->fd[slot] < 0) return -1;
    return sample(guard->fd[slot], "", &guard->identity[slot]);
}

static int open_stage(struct guest_tree_install_guard *guard, int stage, int ns) {
    struct statx *id = guard->identity;
    if (cloexec(stage) < 0 || cloexec(ns) < 0) return -1;
    for (int slot = ROOT; slot <= TMP; ++slot) {
        if (open_node(guard, slot, DIRECTORY) < 0) return -1;
    }
    guard->fd[STAGE] = fcntl(stage, F_DUPFD_CLOEXEC, 3);
    if (guard->fd[STAGE] < 0 || sample(guard->fd[STAGE], "", &id[STAGE]) < 0) return -1;
    for (int slot = PROC; slot <= PROC_NS; ++slot) {
        if (open_node(guard, slot, DIRECTORY) < 0) return -1;
    }
    guard->fd[NS] = fcntl(ns, F_DUPFD_CLOEXEC, 3);
    if (guard->fd[NS] < 0 || ns_identity(guard->fd[NS], &guard->namespace) < 0
            || fs_type(guard->fd[PROC], PROC_SUPER_MAGIC) < 0
            || fs_type(guard->fd[DATA], F2FS_SUPER_MAGIC) < 0) return -1;
    for (int slot = ROOT; slot <= PROC_NS; ++slot) {
        if (!S_ISDIR(id[slot].stx_mode)) return refuse(EXDEV);
    }
    if (id[ROOT].stx_uid || (id[ROOT].stx_mode & 0022) || id[STAGE].stx_uid
            || (id[STAGE].stx_mode & 0022) || ((id[STAGE].stx_mode & S_ISGID) && id[STAGE].stx_gid)
            || same_mount(&id[ROOT], &id[DATA]) || !same_mount(&id[PROC], &id[PROC_NS])) return refuse(EXDEV);
    for (int slot = LOCAL; slot <= STAGE; ++slot) {
        if (!same_mount(&id[DATA], &id[slot])) return refuse(EXDEV);
    }
    if (stage_current(guard, 1) < 0) return -1;
    guard->stage_known = 1;
    return 0;
}

static int private_directory(const struct statx *value) {
    return S_ISDIR(value->stx_mode) && !value->stx_uid && !value->stx_gid
        && (value->stx_mode & 07777) == 0700;
}

static int check_retained_directory(int fd, const struct statx *current) {
    struct statx held;
    if (cloexec(fd) < 0 || sample(fd, "", &held) < 0) return -1;
    if (!private_directory(&held)) return refuse(EPERM);
    return same_node(&held, current, 0) ? 0 : refuse(ESTALE);
}

static int acquire(struct guest_tree_install_guard **out, int stage_fd, int controller_namespace_fd,
        int retained_stage_fd, int retained_guard_fd) {
    if (!out || *out || stage_fd < 0 || controller_namespace_fd < 0 || stage_fd == controller_namespace_fd)
        return refuse(EINVAL);
    if (enter() < 0) return -1;
    int result = -1;
    if (one.pid) { errno = EALREADY; goto done; }
    one.pid = getpid();
    for (int slot = ROOT; slot < COUNT; ++slot) one.fd[slot] = -1;
    *out = &one;
    if (open_stage(&one, stage_fd, controller_namespace_fd) < 0
            || open_node(&one, DEV, DIRECTORY) < 0 || open_node(&one, GUARD, DIRECTORY) < 0
            || open_node(&one, LEASE, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC) < 0) goto done;
    const struct statx *dev = &one.identity[DEV], *lease = &one.identity[LEASE];
    struct statx *dir = &one.identity[GUARD];
    if (!S_ISDIR(dev->stx_mode) || dev->stx_uid || (dev->stx_mode & 0022) || !private_directory(dir)
            || !same_mount(dev, dir) || !same_mount(dir, lease) || !S_ISREG(lease->stx_mode)
            || lease->stx_uid || lease->stx_gid || (lease->stx_mode & 07777) != 0600
            || lease->stx_nlink != 1 || lease->stx_size) { errno = EPERM; goto done; }
    if (flock(one.fd[LEASE], LOCK_EX | LOCK_NB) < 0 || guard_current(&one, 1, 0) < 0
            || stage_current(&one, 1) < 0 || absent(one.fd[GUARD], WRITER_MARKER) < 0
            || absent(one.fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0) goto done;
    if (retained_stage_fd >= 0
            && (check_retained_directory(retained_stage_fd, &one.identity[STAGE]) < 0
                || check_retained_directory(retained_guard_fd, dir) < 0)) goto done;

    one.marker_attempted = 1;
    if (mkdirat(one.fd[GUARD], WRITER_MARKER, 0700) < 0 || open_node(&one, MARKER, DIRECTORY) < 0) goto uncertain;
    struct statx after;
    if (sample(one.fd[GUARD], "", &after) < 0) goto uncertain;
    if (!same_node(dir, &after, 0) || !same_mount(dir, &one.identity[MARKER])
            || !private_directory(&one.identity[MARKER])) { errno = ESTALE; goto uncertain; }
    *dir = after;
    if (guard_current(&one, 1, 1) < 0 || stage_current(&one, 1) < 0) goto uncertain;
    one.ready = 1;
    result = 0;
    goto done;
uncertain:
    (void)hold(&one, errno);
done:
    leave();
    return result;
}

int guest_tree_install_guard_acquire(struct guest_tree_install_guard **out,
        int stage_fd, int controller_namespace_fd) {
    return acquire(out, stage_fd, controller_namespace_fd, -1, -1);
}

int guest_tree_install_guard_acquire_bound(struct guest_tree_install_guard **out,
        int stage_fd, int controller_namespace_fd, int retained_stage_fd, int retained_guard_fd) {
    if (retained_stage_fd < 0 || retained_guard_fd < 0 || retained_stage_fd == retained_guard_fd
            || retained_stage_fd == stage_fd || retained_stage_fd == controller_namespace_fd
            || retained_guard_fd == stage_fd || retained_guard_fd == controller_namespace_fd)
        return refuse(EINVAL);
    /* A closed borrowed slot must not be filled by this acquisition's opens. */
    if (cloexec(retained_stage_fd) < 0 || cloexec(retained_guard_fd) < 0) return -1;
    return acquire(out, stage_fd, controller_namespace_fd, retained_stage_fd, retained_guard_fd);
}

int guest_tree_fsverity_check_install_guard(const struct guest_tree_install_guard *guard,
        int stage_fd, int controller_namespace_fd) {
    if (enter_owner(guard) < 0) return -1;
    int result = -1;
    struct statx stage;
    struct stat ns;
    if (guard->error) errno = guard->error;
    else if (!guard->ready) errno = EPERM;
    else if (cloexec(stage_fd) < 0 || sample(stage_fd, "", &stage) < 0
            || ns_identity(controller_namespace_fd, &ns) < 0) result = hold(&one, errno);
    else if (!same_node(&guard->identity[STAGE], &stage, 0) || !same_ns(&guard->namespace, &ns))
        result = hold(&one, ESTALE);
    else if (guard_current(guard, 1, 1) < 0 || stage_current(guard, 1) < 0) result = hold(&one, errno);
    else result = 0;
    leave();
    return result;
}

int guest_tree_install_guard_hold(struct guest_tree_install_guard *guard, int error) {
    if (enter_owner(guard) < 0) return -1;
    int result = guard->finished ? refuse(EALREADY) : hold(guard, error);
    leave();
    return result;
}

int guest_tree_install_guard_finish(struct guest_tree_install_guard *guard) {
    if (enter_owner(guard) < 0) return -1;
    int result = -1;
    if (guard->finished) { result = 0; goto done; }
    if (guard->error) { errno = guard->error; goto done; }
    if (guard->marker_attempted && !guard->ready) { (void)hold(guard, EINPROGRESS); goto done; }
    if (!guard->stage_known) (void)hold(guard, EINPROGRESS);
    else if (stage_current(guard, 1) < 0 || absent(guard->fd[STAGE], GUEST_TREE_FSVERITY_NEW_NAME) < 0) {
        (void)hold(guard, errno);
        if (guard->marker_attempted) goto done;
    }
    if (guard->marker_attempted && guard_current(guard, 1, 1) < 0) { (void)hold(guard, errno); goto done; }
    guard->ready = 0;
    for (int slot = COUNT - 1; slot >= ROOT; --slot) {
        if (slot != LEASE) close_cell(guard, slot);
    }
    if (!guard->error || !guard->marker_attempted) close_cell(guard, LEASE);
    if (guard->error) { errno = guard->error; goto done; }

    /* A cooperative peer still refuses this marker after the final close. */
    if (guard->marker_attempted && (stage_current(guard, 0) < 0 || guard_current(guard, 0, 1) < 0
            || absent(AT_FDCWD, GUEST_TREE_STAGE_PATH "/" GUEST_TREE_FSVERITY_NEW_NAME) < 0
            || rmdir(location[MARKER].path) < 0)) {
        (void)hold(guard, errno);
        goto done;
    }
    guard->finished = 1;
    result = 0;
done:
    leave();
    return result;
}
