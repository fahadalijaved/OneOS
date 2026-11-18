#define _GNU_SOURCE
#include "guest_tree_stage_provider.h"

#include "guest_tree_source_mounts.h"
#include "guest_tree_stage_guard.h"
#ifdef ONEOS_FILE_TREE_BACKING
#include "guest_tree_file_stage.h"
#endif

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
enum { ROOT, HOST_DATA, STAGE, BACKING, TREE, DATA, PARENT_NS, SOURCE_COUNT };

struct stage_identity {
    struct statx directories[PARENT_NS];
    struct stat namespace;
};

struct gtsp_owner {
    pid_t parent;
    int source[SOURCE_COUNT], duplicates[GTR_WITNESSES];
    struct stage_identity initial;
    struct guest_tree_stage_guard *guard;
#ifdef ONEOS_FILE_TREE_BACKING
    struct gtfs_owner *file_backing;
#endif
    struct gtc_owner *control; /* borrowed from this exact retained guard */
    int available, armed, begin_ok, cutoff, close_error, stop_error, source_error;
    enum gtsp_release terminal;
};

static struct gtsp_owner one;
static int used;
static atomic_flag active = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

#ifdef ONEOS_FILE_TREE_BACKING
static void refuse_as_stage_drift(void) {
    if (errno == ENOENT || errno == ENOTDIR) errno = ESTALE;
}
#endif

static int enter(void) {
    if (getpid() != gettid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    return 0;
}

static void leave(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int enter_owner(struct gtsp_owner *owner) {
    if (enter() < 0) return -1;
    if (!used || owner != &one || one.parent != getpid()) {
        leave();
        return refuse(EINVAL);
    }
    return 0;
}

static void close_cell(struct gtsp_owner *owner, int *cell) {
    int fd = *cell;
    int saved = errno;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
    errno = saved;
}

static int walk(struct gtsp_owner *owner, int base, const char *relative) {
    int current = fcntl(base, F_DUPFD_CLOEXEC, 3);
    if (current < 0) return -1;
    while (*relative) {
        char name[64];
        size_t length = strcspn(relative, "/");
        if (!length || length >= sizeof(name)) {
            close_cell(owner, &current);
            return refuse(EINVAL);
        }
        memcpy(name, relative, length);
        name[length] = '\0';
        if (!strcmp(name, ".") || !strcmp(name, "..")) {
            close_cell(owner, &current);
            return refuse(EINVAL);
        }
        int next = openat(current, name, DIRECTORY);
        int saved = errno;
        close_cell(owner, &current);
        if (next < 0 || owner->close_error) {
            close_cell(owner, &next);
            return refuse(next < 0 && !owner->close_error ? saved : owner->close_error);
        }
        current = next;
        relative += length;
        if (*relative) ++relative;
    }
    return current;
}

static int open_base(struct gtsp_owner *owner, int source[SOURCE_COUNT]) {
    source[ROOT] = open("/", DIRECTORY);
    if (source[ROOT] < 0) return refuse(EPERM);
    source[HOST_DATA] = openat(source[ROOT], "data", DIRECTORY);
    if (source[HOST_DATA] < 0) return refuse(EPERM);
    source[STAGE] = walk(owner, source[ROOT], &GUEST_TREE_STAGE_PATH[1]);
    return source[STAGE] < 0 ? -1 : 0;
}

static int open_view(int source[SOURCE_COUNT]) {
    source[BACKING] = openat(source[STAGE], &GUEST_TREE_BACKING_PATH[sizeof(GUEST_TREE_STAGE_PATH)], DIRECTORY);
    if (source[BACKING] < 0) return -1;
    source[TREE] = openat(source[BACKING], &GUEST_TREE_SOURCE_PATH[sizeof(GUEST_TREE_BACKING_PATH)], DIRECTORY);
    if (source[TREE] < 0) return -1;
    source[DATA] = openat(source[STAGE], "data", DIRECTORY);
    if (source[DATA] < 0) return -1;
    source[PARENT_NS] = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    return source[PARENT_NS] < 0 ? refuse(EPERM) : 0;
}

static int open_fixed(struct gtsp_owner *owner, int source[SOURCE_COUNT]) {
    return open_base(owner, source) < 0 ? -1 : open_view(source);
}

static int directory(int fd, struct statx *value) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO
        | STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME | STATX_MNT_ID;
    if (fd < 0) return refuse(EBADF);
    if (statx(fd, "", AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW, mask, value) < 0) return -1;
    if ((value->stx_mask & mask) != mask || !value->stx_mnt_id || !S_ISDIR(value->stx_mode)) return refuse(EXDEV);
    return 0;
}

static int namespace(int fd, struct stat *value) {
    struct statfs fs;
    struct stat named;
    if (fd < 0) return refuse(EBADF);
    if (fstat(fd, value) < 0 || fstatfs(fd, &fs) < 0 || stat("/proc/self/ns/mnt", &named) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || value->st_dev != named.st_dev || value->st_ino != named.st_ino)
        return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int same_device(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && same_device(a, b);
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_device(a, b) && a->stx_ino == b->stx_ino;
}

static int same_directory(const struct statx *a, const struct statx *b, int stage) {
    return same_node(a, b) && a->stx_mnt_id == b->stx_mnt_id && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
        && (!stage || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size
            && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
            && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int sample(const int source[SOURCE_COUNT], struct stage_identity *sample) {
    for (size_t i = 0; i < PARENT_NS; ++i) if (directory(source[i], &sample->directories[i]) < 0) return -1;
    if (namespace(source[PARENT_NS], &sample->namespace) < 0) return -1;
    const struct statx *root = &sample->directories[ROOT], *host = &sample->directories[HOST_DATA];
    const struct statx *stage = &sample->directories[STAGE], *backing = &sample->directories[BACKING];
    const struct statx *tree = &sample->directories[TREE];
    const struct statx *data = &sample->directories[DATA];
    if (root->stx_uid || stage->stx_uid || backing->stx_uid || tree->stx_uid
            || ((stage->stx_mode | backing->stx_mode | tree->stx_mode) & 0022)
            || data->stx_uid != 1000 || data->stx_gid != 1000 || (data->stx_mode & 07777) != 0771
            || !same_mount(stage, host) || !same_mount(data, host) || !same_mount(tree, backing)
            || same_device(backing, host) || backing->stx_mnt_id == host->stx_mnt_id || same_node(tree, backing)
            || same_node(data, stage) || same_node(data, host) || same_node(stage, host)) return refuse(EXDEV);
    return 0;
}

static int read_mountinfo(struct gtsp_owner *owner, char *text, size_t capacity, size_t *length) {
    const unsigned mask = STATX_TYPE | STATX_MNT_ID;
    const int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
    struct statfs fs;
    struct statx proc, file;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int result = -1;
    size_t used = 0;
    if (fstatfs(fd, &fs) < 0 || statx(AT_FDCWD, "/proc", flags, mask, &proc) < 0
            || statx(fd, "", flags | AT_EMPTY_PATH, mask, &file) < 0) goto done;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || (proc.stx_mask & mask) != mask
            || (file.stx_mask & mask) != mask || !proc.stx_mnt_id || proc.stx_mnt_id != file.stx_mnt_id
            || !S_ISDIR(proc.stx_mode) || !S_ISREG(file.stx_mode)) {
        errno = EXDEV;
        goto done;
    }
    while (used < capacity) {
        ssize_t count = read(fd, text + used, capacity - used);
        if (count < 0) goto done;
        if (!count) break;
        used += (size_t)count;
    }
    if (!used || used == capacity) { errno = EPROTO; goto done; }
    *length = used;
    result = 0;
done:
    close_cell(owner, &fd);
    return owner->close_error ? refuse(owner->close_error) : result;
}

/* Exactly one mode token is required in each kernel options column. */
static int mount_mode(const char *options, char mode) {
    int seen = 0;
    while (*options) {
        size_t length = strcspn(options, ",");
        if (length == 2 && options[0] == 'r' && (options[1] == 'o' || options[1] == 'w')) {
            if (seen || options[1] != mode) return 0;
            seen = 1;
        }
        options += length;
        if (*options) ++options;
    }
    return seen;
}

static int row_device(const struct gpv_mount_row *row, const struct statx *fd) {
    return row->major == fd->stx_dev_major && row->minor == fd->stx_dev_minor;
}

static int check_backing_rows(const struct stage_identity *sample, const struct gpv_mount_row *rows, size_t count) {
    const struct statx *host = &sample->directories[HOST_DATA], *backing = &sample->directories[BACKING];
    const struct gpv_mount_row *writable = gpv_mount_by_id(rows, count, host->stx_mnt_id);
    const struct gpv_mount_row *readonly = gpv_mount_by_id(rows, count, backing->stx_mnt_id);
    if (!writable || !readonly || !row_device(writable, host) || !row_device(readonly, backing)
            || !mount_mode(writable->options, 'w') || !mount_mode(writable->super_options, 'w')
            || readonly->parent != writable->id || strcmp(readonly->point, GUEST_TREE_BACKING_PATH)
            || strcmp(readonly->root, "/") || strcmp(readonly->type, "erofs")
            || !mount_mode(readonly->options, 'o') || !mount_mode(readonly->super_options, 'o')) return refuse(EXDEV);
    for (size_t i = 0; i < count; ++i) {
        if (&rows[i] == readonly) continue;
        if (row_device(&rows[i], backing) || !strcmp(rows[i].point, GUEST_TREE_BACKING_PATH)
                || !strncmp(rows[i].point, GUEST_TREE_BACKING_PATH "/", sizeof(GUEST_TREE_BACKING_PATH)))
            return refuse(EXDEV);
    }
    return 0;
}

static int backing_profile(struct gtsp_owner *owner, const struct stage_identity *sample) {
    const size_t capacity = GPV_MOUNTINFO_MAX_BYTES + 1U;
    char *text = malloc(capacity);
    struct gpv_mount_row *rows = malloc(sizeof(*rows) * GPV_MOUNTINFO_MAX_ROWS);
    size_t length, count;
    int result = -1;
    if (!text || !rows) errno = ENOMEM;
    else if (read_mountinfo(owner, text, capacity, &length) == 0) {
        if (gpv_parse_mountinfo(text, length, rows, GPV_MOUNTINFO_MAX_ROWS, &count) != GPV_OK) errno = EPROTO;
        else result = check_backing_rows(sample, rows, count);
    }
    int saved = errno;
    free(rows);
    free(text);
    errno = saved;
    return result;
}

static int matches(const struct stage_identity *expected, const struct stage_identity *current) {
    if (expected->namespace.st_dev != current->namespace.st_dev
            || expected->namespace.st_ino != current->namespace.st_ino) return refuse(ESTALE);
    for (size_t i = 0; i < PARENT_NS; ++i) {
        if (!same_directory(&expected->directories[i], &current->directories[i], i >= STAGE)) return refuse(ESTALE);
    }
    return 0;
}

static int required_data_dirs(struct gtsp_owner *owner) {
    const uint64_t mount = owner->initial.directories[DATA].stx_mnt_id;
    int user = walk(owner, owner->source[DATA], "user/0");
    if (user < 0) return -1;
    int alias = openat(owner->source[DATA], "data", DIRECTORY);
    struct statx u, a;
    int result = alias < 0 || directory(user, &u) < 0 || directory(alias, &a) < 0 ? -1 : 0;
    if (!result && (u.stx_mnt_id != mount || a.stx_mnt_id != mount || same_node(&u, &a))) result = refuse(EXDEV);
    close_cell(owner, &alias);
    close_cell(owner, &user);
    return owner->close_error ? refuse(owner->close_error) : result;
}

static int current_stage(struct gtsp_owner *owner) {
    if (owner->close_error) return refuse(owner->close_error);
    struct stage_identity held, named;
    if (guest_tree_stage_guard_check(owner->guard) < 0 || sample(owner->source, &held) < 0
            || matches(&owner->initial, &held) < 0) return -1;
    int fresh[SOURCE_COUNT];
    for (size_t i = 0; i < SOURCE_COUNT; ++i) fresh[i] = -1;
    int result = -1;
    if (open_fixed(owner, fresh) == 0 && sample(fresh, &named) == 0 && matches(&owner->initial, &named) == 0
            && backing_profile(owner, &named) == 0)
        result = required_data_dirs(owner);
    for (size_t i = SOURCE_COUNT; i; --i) close_cell(owner, &fresh[i - 1]);
    if (owner->close_error) return refuse(owner->close_error);
    if (result < 0) return -1;
    return guest_tree_stage_guard_check(owner->guard);
}

static int admit_current(struct gtsp_owner *owner) {
    if (current_stage(owner) < 0) return -1;
#ifdef ONEOS_FILE_TREE_BACKING
    int result = gtfs_check(owner->file_backing, owner->source[STAGE], owner->source[BACKING],
            owner->source[TREE], owner->source[PARENT_NS], owner->guard);
#else
    const struct gtsp_stage_witnesses witnesses = {
        owner->source[STAGE], owner->source[TREE], owner->source[DATA], owner->source[PARENT_NS], owner->guard
    };
    int result = guest_tree_admit_stage_contents(&witnesses);
#endif
    if (result) return result > 0 ? refuse(EPERM) : -1;
    return current_stage(owner);
}

int gtsp_open_existing(struct gtsp_owner **out) {
    if (!out || *out) return refuse(EINVAL);
    if (enter() < 0) return -1;
    int result = -1;
    if (used) { errno = EBUSY; goto done; }
    if (getuid() || geteuid()) { errno = EPERM; goto done; }
    used = 1;
    one.parent = getpid();
    for (size_t i = 0; i < SOURCE_COUNT; ++i) one.source[i] = -1;
    for (size_t i = 0; i < GTR_WITNESSES; ++i) one.duplicates[i] = -1;
    *out = &one;
#ifdef ONEOS_FILE_TREE_BACKING
    if (gtfs_enter(&one.file_backing) < 0) {
        refuse_as_stage_drift();
        goto done;
    }
#endif
    if (guest_tree_stage_guard_acquire(&one.guard) != 0 || !one.guard) {
        if (!one.guard || errno == ENOENT || errno == ENOTDIR) errno = EPERM;
        goto done;
    }
#ifdef ONEOS_FILE_TREE_BACKING
    if (open_base(&one, one.source) < 0) goto done;
    if (gtfs_mount(one.file_backing, one.source[STAGE], one.guard) < 0 || open_view(one.source) < 0) {
        /* The controller maps a missing base stage to NEED_STAGE. A miss
         * after mount acquisition is a refusal with possible owned effects. */
        refuse_as_stage_drift();
        goto done;
    }
#else
    if (open_fixed(&one, one.source) < 0) goto done;
#endif
    if (sample(one.source, &one.initial) < 0 || admit_current(&one) < 0) {
        if (errno == ENOENT || errno == ENOTDIR) errno = ESTALE;
        goto done;
    }
    one.available = 1;
    result = 0;
done:
    leave();
    return result;
}

static int stop(struct gtsp_owner *owner) {
    if (!owner->cutoff) {
        owner->cutoff = 1;
        if (owner->control && gtc_request_stop(owner->control) < 0) owner->stop_error = errno ? errno : EIO;
    }
    return owner->stop_error ? refuse(owner->stop_error) : 0;
}

int gtsp_begin_view(struct gtsp_owner *owner, struct gtc_observation *observed) {
    if (!observed) return refuse(EINVAL);
    if (enter_owner(owner) < 0) return -1;
    memset(observed, 0, sizeof(*observed));
    int result = -1;
    if (!owner->available || owner->armed || owner->cutoff) {
        leave();
        return refuse(EBUSY);
    }
    owner->available = 0;
    if (admit_current(owner) < 0) goto done;
    static const int roles[GTR_WITNESSES] = {TREE, DATA, PARENT_NS};
    for (size_t i = 0; i < GTR_WITNESSES; ++i) {
        owner->duplicates[i] = fcntl(owner->source[roles[i]], F_DUPFD_CLOEXEC, 3);
        if (owner->duplicates[i] < 0) goto done;
    }
    if (current_stage(owner) < 0) goto done;
    owner->armed = 1;
    if (guest_tree_stage_guard_begin(owner->guard, &owner->control, owner->duplicates) < 0) goto done;
    owner->begin_ok = 1;
    struct gtc_observation actual;
    if (gtc_receive_partial(owner->control, &actual) < 0) goto done;
    if (admit_current(owner) < 0) {
        owner->source_error = errno ? errno : EIO;
        goto done;
    }
    *observed = actual;
    result = 0;
done:
    if (result < 0) {
        int primary = errno ? errno : EIO;
        (void)stop(owner);
        errno = primary;
    }
    leave();
    return result;
}

int gtsp_request_stop(struct gtsp_owner *owner) {
    if (enter_owner(owner) < 0) return -1;
    int result = stop(owner);
    leave();
    return result;
}

enum gtsp_release gtsp_poll_close(struct gtsp_owner *owner) {
    if (enter_owner(owner) < 0) return GTSP_HOLD;
    enum gtsp_release result = GTSP_HOLD;
    if (owner->terminal) { result = owner->terminal; goto done; }
    (void)stop(owner);
    if (owner->armed && guest_tree_stage_guard_poll_control(owner->guard) < 0) goto done;
    if (owner->close_error || owner->stop_error || owner->source_error) {
        errno = owner->close_error ? owner->close_error : owner->stop_error ? owner->stop_error : owner->source_error;
        goto done;
    }
    if (owner->armed && admit_current(owner) < 0) {
        owner->source_error = errno ? errno : EIO;
        goto done;
    }
    for (size_t i = GTR_WITNESSES; i; --i) close_cell(owner, &owner->duplicates[i - 1]);
    for (size_t i = SOURCE_COUNT; i; --i) close_cell(owner, &owner->source[i - 1]);
    if (owner->close_error) { errno = owner->close_error; goto done; }
#ifdef ONEOS_FILE_TREE_BACKING
    if (owner->file_backing && gtfs_close(owner->file_backing) < 0) {
        owner->close_error = errno ? errno : EIO;
        goto done;
    }
#endif
    if (owner->guard && guest_tree_stage_guard_finish(owner->guard) != 0) {
        owner->close_error = errno ? errno : EIO;
        goto done;
    }
    owner->terminal = owner->begin_ok ? GTSP_TREE_LOCAL_RELEASED : GTSP_NEVER_BEGAN_LOCAL_CLOSED;
    result = owner->terminal;
done:
    leave();
    return result;
}
