#define _GNU_SOURCE
#include "guest_tree_install_bootstrap.h"

#include "guest_tree_source_mounts.h"
#include "guest_tree_stage_guard.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/magic.h>
#include <sched.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DIRECTORY (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define STAGE_NEW ".oneos-viewprep.new"
#define GUARD_NEW ".oneos-retained-viewprep.new"
#define STAGE_NAME (&GUEST_TREE_STAGE_PATH[sizeof("/data/local/tmp")])
#define GUARD_NAME (&GUEST_TREE_GUARD_PATH[sizeof("/dev")])

enum { ROOT, HOST_DATA, LOCAL, TMP, DEV, STAGE, BIN, BACKING, DATA, USER, ZERO, ALIAS, GUARD, LEASE, COUNT };

static const struct location { int parent; const char *name; } locations[COUNT] = {
    [ROOT] = {-1, "/"}, [HOST_DATA] = {ROOT, "data"}, [LOCAL] = {HOST_DATA, "local"},
    [TMP] = {LOCAL, "tmp"}, [DEV] = {ROOT, "dev"}, [STAGE] = {LOCAL, STAGE_NEW},
    [BIN] = {STAGE, "bin"}, [BACKING] = {STAGE, "backing"}, [DATA] = {STAGE, "data"},
    [USER] = {DATA, "user"}, [ZERO] = {USER, "0"}, [ALIAS] = {DATA, "data"},
    [GUARD] = {DEV, GUARD_NEW}, [LEASE] = {GUARD, "lease"},
};

struct guest_tree_install_bootstrap {
    pid_t pid;
    int fd[COUNT];
    struct statx initial[COUNT];
    int attempted, stage_published, guard_published, ready, error;
    enum guest_tree_install_bootstrap_release terminal;
};

static struct guest_tree_install_bootstrap one;
static atomic_flag active = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int hold(struct guest_tree_install_bootstrap *owner, int error) {
    if (!owner->error) owner->error = error ? error : EIO;
    owner->ready = 0;
    return refuse(owner->error);
}

static int enter(void) {
    if (getpid() != gettid() || getuid() || geteuid() || getegid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(struct guest_tree_install_bootstrap *owner) {
    if (enter() < 0) return -1;
    if (owner == &one && owner->pid == getpid()) return 0;
    leave();
    return refuse(EINVAL);
}

static int sample(int fd, const char *name, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK
        | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID;
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_mnt_id || !value->stx_ino) return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b, int stable) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
        && (!stable || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
            && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
            && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static struct location current_location(const struct guest_tree_install_bootstrap *owner, int slot) {
    if (slot == STAGE && owner->stage_published) return (struct location){TMP, STAGE_NAME};
    if (slot == GUARD && owner->guard_published) return (struct location){DEV, GUARD_NAME};
    return locations[slot];
}

static int current_node(const struct guest_tree_install_bootstrap *owner, int slot, int stable) {
    struct statx held, named;
    const struct location loc = current_location(owner, slot);
    const int parent = loc.parent < 0 ? AT_FDCWD : owner->fd[loc.parent];
    if (sample(owner->fd[slot], "", &held) < 0 || sample(parent, loc.name, &named) < 0) return -1;
    return same_node(&owner->initial[slot], &held, stable) && same_node(&held, &named, stable)
        ? 0 : refuse(ESTALE);
}

static int absent(int parent, const char *name) {
    struct statx ignored;
    if (statx(parent, name, LOOKUP, STATX_TYPE, &ignored) == 0) return refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int writable_fs(int fd, unsigned long expected) {
    struct statfs fs;
    struct statvfs flags;
    if (fstatfs(fd, &fs) < 0 || fstatvfs(fd, &flags) < 0) return -1;
    return (unsigned long)fs.f_type == expected && !(flags.f_flag & ST_RDONLY) ? 0 : refuse(EXDEV);
}

static int anchors_current(const struct guest_tree_install_bootstrap *owner) {
    for (int slot = ROOT; slot <= DEV; ++slot)
        if (current_node(owner, slot, 0) < 0) return -1;
    if (writable_fs(owner->fd[HOST_DATA], F2FS_SUPER_MAGIC) < 0) return -1;
    return writable_fs(owner->fd[DEV], TMPFS_MAGIC);
}

static int open_anchors(struct guest_tree_install_bootstrap *owner) {
    const struct statx *id = owner->initial;
    for (int slot = ROOT; slot <= DEV; ++slot) {
        const struct location loc = locations[slot];
        owner->fd[slot] = openat(loc.parent < 0 ? AT_FDCWD : owner->fd[loc.parent], loc.name, DIRECTORY);
        if (owner->fd[slot] < 0 || sample(owner->fd[slot], "", &owner->initial[slot]) < 0) return -1;
        if (!S_ISDIR(id[slot].stx_mode)) return refuse(EXDEV);
    }
    if (id[ROOT].stx_uid || (id[ROOT].stx_mode & 0022) || same_mount(&id[ROOT], &id[HOST_DATA])
        || !same_mount(&id[HOST_DATA], &id[LOCAL]) || !same_mount(&id[LOCAL], &id[TMP])
        || id[HOST_DATA].stx_ino == id[LOCAL].stx_ino || id[LOCAL].stx_ino == id[TMP].stx_ino
        || id[HOST_DATA].stx_ino == id[TMP].stx_ino
        || id[LOCAL].stx_uid || id[LOCAL].stx_gid || (id[LOCAL].stx_mode & 07777) != 0751
        || id[TMP].stx_uid != 2000 || id[TMP].stx_gid != 2000 || (id[TMP].stx_mode & 07777) != 0771
        || id[DEV].stx_uid || id[DEV].stx_gid || (id[DEV].stx_mode & 0022)) return refuse(EXDEV);
    return anchors_current(owner);
}

static int create_directory(struct guest_tree_install_bootstrap *owner, int slot) {
    const struct location loc = locations[slot];
    const int parent = owner->fd[loc.parent];
    struct statx born;
    owner->attempted = 1;
    if (mkdirat(parent, loc.name, 0700) < 0) return -1;
    int fd = owner->fd[slot] = openat(parent, loc.name, DIRECTORY);
    if (fd < 0 || sample(fd, "", &born) < 0) return -1;
    if (!S_ISDIR(born.stx_mode) || born.stx_uid || (born.stx_mode & 0077)
        || !same_mount(&owner->initial[loc.parent], &born)) return refuse(ESTALE);
    owner->initial[slot] = born;
    if (current_node(owner, slot, 1) < 0 || fchown(fd, 0, 0) < 0 || fchmod(fd, 0700) < 0) return -1;
    return sample(fd, "", &owner->initial[slot]);
}

static int create_lease(struct guest_tree_install_bootstrap *owner) {
    int fd = owner->fd[LEASE] = openat(owner->fd[GUARD], "lease",
            O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0 || fchown(fd, 0, 0) < 0 || fchmod(fd, 0600) < 0 || flock(fd, LOCK_EX | LOCK_NB) < 0)
        return -1;
    return sample(fd, "", &owner->initial[LEASE]);
}

static int exact_contents(struct guest_tree_install_bootstrap *owner, int slot) {
    const unsigned dot = 1U << COUNT, dotdot = 1U << (COUNT + 1);
    unsigned expected = dot | dotdot, seen = 0;
    for (int child = BIN; child < COUNT; ++child)
        if (locations[child].parent == slot) expected |= 1U << child;

    int fd = openat(owner->fd[slot], ".", DIRECTORY | O_NOATIME);
    if (fd < 0) return -1;
    struct statx held;
    int failure = 0;
    if (sample(fd, "", &held) < 0) failure = errno;
    else if (!same_node(&owner->initial[slot], &held, 1)) failure = ESTALE;
    DIR *dir = failure ? NULL : fdopendir(fd);
    if (!dir) {
        if (!failure) failure = errno;
        if (close(fd) < 0) return hold(owner, errno);
        return refuse(failure ? failure : EIO);
    }
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(dir);
        if (!entry) { failure = errno; break; }
        unsigned bit = 0;
        if (!strcmp(entry->d_name, ".")) bit = dot;
        else if (!strcmp(entry->d_name, "..")) bit = dotdot;
        else {
            for (int child = BIN; child < COUNT; ++child)
                if (locations[child].parent == slot && !strcmp(locations[child].name, entry->d_name))
                    bit = 1U << child;
        }
        if (!bit || (seen & bit)) { failure = ENOTEMPTY; break; }
        seen |= bit;
    }
    if (closedir(dir) < 0) return hold(owner, errno);
    if (failure) return refuse(failure);
    return seen == expected ? 0 : refuse(ESTALE);
}

static int capture_owned(struct guest_tree_install_bootstrap *owner) {
    for (int slot = STAGE; slot < COUNT; ++slot) {
        struct statx *value = &owner->initial[slot];
        struct statx current;
        if (sample(owner->fd[slot], "", &current) < 0) return -1;
        if (!same_mount(value, &current) || value->stx_ino != current.stx_ino) return refuse(ESTALE);
        if (slot == LEASE) {
            if (!S_ISREG(current.stx_mode) || (current.stx_mode & 07777) != 0600
                || current.stx_uid || current.stx_gid || current.stx_size || current.stx_nlink != 1)
                return refuse(EPERM);
        } else {
            const unsigned uid = slot == DATA ? 1000U : 0U;
            const unsigned mode = slot == DATA ? 0771U : 0700U;
            unsigned links = 2;
            for (int child = BIN; child < LEASE; ++child)
                if (locations[child].parent == slot) ++links;
            if (!S_ISDIR(current.stx_mode) || (current.stx_mode & 07777) != mode
                || current.stx_uid != uid || current.stx_gid != uid || current.stx_nlink != links)
                return refuse(EPERM);
        }
        *value = current;
    }
    return 0;
}

static int owned_current(struct guest_tree_install_bootstrap *owner) {
    if (anchors_current(owner) < 0) return -1;
    for (int slot = STAGE; slot < COUNT; ++slot)
        if (current_node(owner, slot, 1) < 0) return -1;
    return 0;
}

static int publish(struct guest_tree_install_bootstrap *owner, int slot, int dest,
                   const char *name, int *published) {
    const struct location from = locations[slot];
    if (owned_current(owner) < 0 || absent(owner->fd[dest], name) < 0) return -1;
    long moved = syscall(SYS_renameat2, owner->fd[from.parent], from.name,
                         owner->fd[dest], name, RENAME_NOREPLACE);
    if (moved != 0) return moved < 0 ? -1 : refuse(EPROTO);
    *published = 1;
    /* F2FS updates the moved stage directory's mtime and ctime when it
     * rewrites the parent entry. Only that cross-parent move can change mtime. */
    const int stage_parent_changed = slot == STAGE && from.parent != dest;
    struct statx after;
    if (current_node(owner, slot, 0) < 0 || sample(owner->fd[slot], "", &after) < 0) return -1;
    const struct statx *before = &owner->initial[slot];
    if (!same_node(before, &after, 0) || before->stx_nlink != after.stx_nlink || before->stx_size != after.stx_size
        || (!stage_parent_changed && (before->stx_mtime.tv_sec != after.stx_mtime.tv_sec
            || before->stx_mtime.tv_nsec != after.stx_mtime.tv_nsec)))
        return refuse(ESTALE);
    owner->initial[slot] = after;
    if (stage_parent_changed) {
        struct statx parent;
        if (sample(owner->fd[slot], "..", &parent) < 0) return -1;
        if (!same_node(&owner->initial[dest], &parent, 0)) return refuse(ESTALE);
        if (exact_contents(owner, slot) < 0) return -1;
    }
    if (absent(owner->fd[from.parent], from.name) < 0 || fsync(owner->fd[dest]) < 0) return -1;
    if (dest != from.parent && fsync(owner->fd[from.parent]) < 0) return -1;
    return owned_current(owner);
}

static int build(struct guest_tree_install_bootstrap *owner) {
    if (open_anchors(owner) < 0 || absent(owner->fd[LOCAL], STAGE_NEW) < 0
        || absent(owner->fd[TMP], STAGE_NAME) < 0 || absent(owner->fd[DEV], GUARD_NEW) < 0
        || absent(owner->fd[DEV], GUARD_NAME) < 0) return -1;
    for (int slot = STAGE; slot <= GUARD; ++slot)
        if (create_directory(owner, slot) < 0) return -1;
    if (fchown(owner->fd[DATA], 1000, 1000) < 0 || fchmod(owner->fd[DATA], 0771) < 0
        || create_lease(owner) < 0 || capture_owned(owner) < 0 || owned_current(owner) < 0) return -1;
    for (int slot = GUARD; slot >= STAGE; --slot)
        if (exact_contents(owner, slot) < 0) return -1;
    for (int slot = LEASE; slot >= STAGE; --slot)
        if (fsync(owner->fd[slot]) < 0) return -1;
    if (fsync(owner->fd[LOCAL]) < 0 || fsync(owner->fd[DEV]) < 0
        || publish(owner, STAGE, TMP, STAGE_NAME, &owner->stage_published) < 0
        || publish(owner, GUARD, DEV, GUARD_NAME, &owner->guard_published) < 0
        || absent(owner->fd[LOCAL], STAGE_NEW) < 0 || absent(owner->fd[DEV], GUARD_NEW) < 0)
        return -1;
    return owned_current(owner);
}

int guest_tree_install_bootstrap_begin(struct guest_tree_install_bootstrap **out) {
    if (!out || *out) return refuse(EINVAL);
    if (enter() < 0) return -1;
    int result = -1;
    if (one.pid) { errno = EALREADY; goto done; }
    one.pid = getpid();
    for (int slot = ROOT; slot < COUNT; ++slot) one.fd[slot] = -1;
    *out = &one;
    if (build(&one) < 0) {
        if (one.attempted) (void)hold(&one, errno);
        goto done;
    }
    one.ready = 1;
    result = 0;
done:
    leave();
    return result;
}

int guest_tree_install_bootstrap_borrow(struct guest_tree_install_bootstrap *owner, int *stage_fd) {
    if (!stage_fd || *stage_fd != -1) return refuse(EINVAL);
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    if (!owner->ready) errno = owner->error ? owner->error : EBUSY;
    else if (owned_current(owner) < 0) (void)hold(owner, errno);
    else { *stage_fd = owner->fd[STAGE]; result = 0; }
    leave();
    return result;
}

static int close_cell(struct guest_tree_install_bootstrap *owner, int slot) {
    int fd = owner->fd[slot];
    owner->fd[slot] = -1;
    return fd >= 0 && close(fd) < 0 ? hold(owner, errno) : 0;
}

enum guest_tree_install_bootstrap_release
guest_tree_install_bootstrap_close(struct guest_tree_install_bootstrap *owner) {
    if (enter_owner(owner) < 0) return GUEST_TREE_INSTALL_BOOTSTRAP_HOLD;
    enum guest_tree_install_bootstrap_release result = GUEST_TREE_INSTALL_BOOTSTRAP_HOLD;
    if (owner->terminal) { result = owner->terminal; goto done; }
    if (owner->error || (owner->attempted && !owner->ready)) {
        (void)hold(owner, owner->error ? owner->error : EINPROGRESS);
        goto done;
    }
    if (owner->ready && owned_current(owner) < 0) { (void)hold(owner, errno); goto done; }
    owner->ready = 0;
    for (int slot = LEASE - 1; slot >= ROOT; --slot)
        if (close_cell(owner, slot) < 0) goto done;
    if (close_cell(owner, LEASE) < 0) goto done;
    result = owner->terminal = owner->attempted ? GUEST_TREE_INSTALL_BOOTSTRAP_PUBLISHED_LOCAL_CLOSED
                                                : GUEST_TREE_INSTALL_BOOTSTRAP_NO_EFFECT_LOCAL_CLOSED;
done:
    leave();
    return result;
}

int guest_tree_install_bootstrap_published_identity(struct guest_tree_install_bootstrap *owner,
        struct guest_tree_install_bootstrap_identity *out) {
    if (!out) return refuse(EINVAL);
    *out = (struct guest_tree_install_bootstrap_identity){0};
    if (owner != &one) return refuse(EINVAL);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    if (owner->terminal != GUEST_TREE_INSTALL_BOOTSTRAP_PUBLISHED_LOCAL_CLOSED) {
        leave();
        return refuse(EBUSY);
    }
    const struct statx *stage = &owner->initial[STAGE];
    const struct statx *guard = &owner->initial[GUARD];
    *out = (struct guest_tree_install_bootstrap_identity){
        .stage_mount = stage->stx_mnt_id, .stage_inode = stage->stx_ino,
        .guard_mount = guard->stx_mnt_id, .guard_inode = guard->stx_ino,
        .stage_dev_major = stage->stx_dev_major, .stage_dev_minor = stage->stx_dev_minor,
        .guard_dev_major = guard->stx_dev_major, .guard_dev_minor = guard->stx_dev_minor,
    };
    leave();
    return 0;
}
