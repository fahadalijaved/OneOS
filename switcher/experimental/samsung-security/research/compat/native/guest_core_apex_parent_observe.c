#define _GNU_SOURCE
#include "guest_core_apex_parent_observe.h"

#include <string.h>

#define SIBLINGS "/mnt/gvi/apex-inputs"
#define APEX GUEST_TREE_TARGET_PATH "/apex"

struct apex_role {
    const char *stable, *versioned, *sibling_path, *stable_path, *versioned_path, *type;
    unsigned long magic;
    uint64_t inode;
};

#define ROLE(name, version, type, magic, inode) \
    {name, name "@" version, SIBLINGS "/" name, APEX "/" name, APEX "/" name "@" version, type, magic, inode}
static const struct apex_role roles[GCA_COUNT] = {
    [GCA_ART] = ROLE("com.android.art", "371000140", "ext4", 0xef53UL, 2),
    [GCA_I18N] = ROLE("com.android.i18n", "1", "erofs", 0xe0f5e1e2UL, 39),
    [GCA_RUNTIME] = ROLE("com.android.runtime", "1", "erofs", 0xe0f5e1e2UL, 39),
};
#undef ROLE

enum { NEW_APEX_ROWS = 1 + 3 * GCA_COUNT };

struct added_rows {
    const struct gpv_mount_row *apex;
    const struct gpv_mount_row *sibling[GCA_COUNT], *stable[GCA_COUNT], *versioned[GCA_COUNT];
};

static int below(const char *path, const char *root) {
    size_t n = strlen(root);
    return !strncmp(path, root, n) && (path[n] == '/' || !path[n]);
}

static int option(const char *list, const char *token) {
    size_t n = strlen(token);
    while (*list) {
        size_t field = strcspn(list, ",");
        if (n == field && !memcmp(list, token, n)) return 1;
        list += field;
        if (*list) ++list;
    }
    return 0;
}

static int same_row(const struct gpv_mount_row *old, const struct gpv_mount_row *now) {
    return now && old->id == now->id && old->parent == now->parent && old->major == now->major
        && old->minor == now->minor && old->shared == now->shared && old->master == now->master
        && old->propagate == now->propagate && old->unbindable == now->unbindable
        && !strcmp(old->root, now->root) && !strcmp(old->point, now->point) && !strcmp(old->type, now->type)
        && !strcmp(old->source, now->source) && !strcmp(old->options, now->options)
        && !strcmp(old->super_options, now->super_options);
}

static int preserves(const struct gpv_mount_row *old, size_t old_count,
                     const struct gpv_mount_row *now, size_t now_count) {
    for (size_t i = 0; i < old_count; ++i)
        if (!same_row(&old[i], gpv_mount_by_id(now, now_count, old[i].id))) return 0;
    return 1;
}

static int private_root(const struct gpv_mount_row *row, uint64_t parent) {
    return row && row->parent == parent && !row->shared && !row->master && !row->propagate
        && !row->unbindable && !strcmp(row->root, "/");
}

static int module_row(const struct gpv_mount_row *row, uint64_t parent, const struct apex_role *role) {
    return private_root(row, parent) && row->major == 7 && !strcmp(row->type, role->type)
        && option(row->options, "ro") && option(row->options, "nosuid") && option(row->options, "nodev")
        && !option(row->options, "rw") && !option(row->options, "noexec")
        && option(row->super_options, "ro") && !option(row->super_options, "rw");
}

static int clone_of(const struct gpv_mount_row *row, const struct gpv_mount_row *original) {
    return row->major == original->major && row->minor == original->minor
        && !strcmp(row->source, original->source) && !strcmp(row->super_options, original->super_options);
}

static const struct gpv_mount_row **addition_slot(struct added_rows *added, const char *path) {
    if (!strcmp(path, APEX)) return &added->apex;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        if (!strcmp(path, roles[i].sibling_path)) return &added->sibling[i];
        if (!strcmp(path, roles[i].stable_path)) return &added->stable[i];
        if (!strcmp(path, roles[i].versioned_path)) return &added->versioned[i];
    }
    return NULL;
}

/* Called only with successful, duplicate-ID-rejecting parser output. */
static int exact_delta(const struct gpv_mount_row *before, size_t before_count,
                       const struct gpv_mount_row *after, size_t after_count,
                       uint64_t root_id, struct added_rows *added) {
    *added = (struct added_rows){0};
    const struct gpv_mount_row *root = gpv_mount_by_id(before, before_count, root_id);
    if (!root || strcmp(root->point, GUEST_TREE_TARGET_PATH) || after_count != before_count + NEW_APEX_ROWS
            || !preserves(before, before_count, after, after_count)) return 0;
    for (size_t i = 0; i < before_count; ++i)
        if (below(before[i].point, APEX) || below(before[i].point, SIBLINGS)) return 0;
    for (size_t i = 0; i < after_count; ++i) {
        const struct gpv_mount_row *row = &after[i];
        if (gpv_mount_by_id(before, before_count, row->id)) continue;
        const struct gpv_mount_row **slot = addition_slot(added, row->point);
        if (!slot || *slot) return 0;
        *slot = row;
    }
    const struct gpv_mount_row *apex = added->apex;
    if (!private_root(apex, root_id) || apex->major || !apex->minor || strcmp(apex->type, "tmpfs")
            || strcmp(apex->source, "oneos-core-apex") || !option(apex->options, "rw")
            || option(apex->options, "ro") || !option(apex->options, "nosuid") || !option(apex->options, "nodev")
            || !option(apex->options, "noexec") || !option(apex->super_options, "rw")) return 0;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        const struct gpv_mount_row *sibling = added->sibling[i], *stable = added->stable[i], *versioned = added->versioned[i];
        if (!module_row(sibling, root->parent, &roles[i]) || !module_row(stable, apex->id, &roles[i])
                || !module_row(versioned, apex->id, &roles[i]) || !clone_of(stable, sibling)
                || !clone_of(versioned, sibling)) return 0;
        for (unsigned j = 0; j < i; ++j) if (sibling->minor == added->sibling[j]->minor) return 0;
    }
    return 1;
}

#ifndef GCAP_INERT
#include "guest_tree_parent_view.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define DIR_FLAGS (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
#define STAT_MASK (STATX_TYPE | STATX_MODE | STATX_MNT_ID | STATX_INO | STATX_UID | STATX_GID)

enum { SOURCE, ROOT, PARENT_NS, CHILD_NS, PROC, SELF, TASK, HELD };
enum { CAPTURING = 1, CAPTURED, OBSERVING, OBSERVED, REFUSED, CLOSED };

struct guest_core_apex_parent_observer {
    pid_t parent, child;
    struct gtr_owner *release;
    struct guest_core_apex_child_sources *source;
    int fd[HELD], state, error;
    char pid_name[32];
    struct stat parent_ns, child_ns;
    struct statx proc, task, tree, root;
    struct gpv_mount_row *parent_rows, *child_rows;
    size_t parent_count, child_count;
};

struct temporary {
    int fd[16];
    size_t count;
};

static struct guest_core_apex_parent_observer one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int fail(struct guest_core_apex_parent_observer *owner) {
    if (!owner->error) owner->error = errno ? errno : EIO;
    owner->state = REFUSED;
    return refuse(owner->error);
}

static int controller(void) {
    return getpid() == gettid() && !getuid() && !geteuid();
}

static int owned(const struct guest_core_apex_parent_observer *owner) {
    return owner == &one && controller() && owner->parent == getpid() ? 0 : refuse(EPERM);
}

static void close_fd(int *slot, int *error, int *close_error) {
    int fd = *slot;
    *slot = -1;
    if (fd < 0 || close(fd) == 0) return;
    int failure = errno ? errno : EIO;
    if (!*error) *error = failure;
    if (!*close_error) *close_error = failure;
}

static int sample(int dir, const char *name, int type, struct statx *out) {
    if (statx(dir, name, LOOKUP | AT_EMPTY_PATH, STAT_MASK, out) < 0) return -1;
    return (out->stx_mask & STAT_MASK) == STAT_MASK && out->stx_mnt_id && out->stx_ino
        && (out->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor
        && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && same_inode(a, b);
}

static int fs_type(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : refuse(EXDEV);
}

static int namespace_fd(int fd, struct stat *out) {
    if (fstat(fd, out) < 0 || fs_type(fd, NSFS_MAGIC) < 0) return -1;
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS && out->st_ino ? 0 : refuse(EXDEV);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int proc_member(const struct guest_core_apex_parent_observer *owner, int fd,
                       const char *name, int type, struct statx *out) {
    if (sample(fd, name, type, out) < 0) return -1;
    return same_mount(&owner->proc, out) ? 0 : refuse(EXDEV);
}

static int task_namespace(const struct guest_core_apex_parent_observer *owner, int task,
                          const struct stat *expected, int *close_error) {
    int error = 0, ns = -1;
    struct statx value;
    struct stat actual;
    int dir = openat(task, "ns", DIR_FLAGS);
    if (dir < 0) return -1;
    if (proc_member(owner, dir, "", S_IFDIR, &value) < 0 || proc_member(owner, dir, "mnt", S_IFLNK, &value) < 0)
        error = errno;
    else {
        ns = openat(dir, "mnt", O_RDONLY | O_CLOEXEC);
        if (ns < 0 || namespace_fd(ns, &actual) < 0) error = errno;
        else if (!same_ns(&actual, expected)) error = ESTALE;
    }
    close_fd(&ns, &error, close_error);
    close_fd(&dir, &error, close_error);
    return error ? refuse(error) : 0;
}

static int live(const struct guest_core_apex_parent_observer *owner, int *close_error) {
    int result = gtr_child_live(owner->release);
    if (result != 1) return result < 0 ? -1 : refuse(ECHILD);
    const int *fd = owner->fd;
    struct statx proc, task, tree, root;
    if (sample(AT_FDCWD, "/proc", S_IFDIR, &proc) < 0
            || proc_member(owner, fd[PROC], owner->pid_name, S_IFDIR, &task) < 0
            || task_namespace(owner, fd[SELF], &owner->parent_ns, close_error) < 0
            || task_namespace(owner, fd[TASK], &owner->child_ns, close_error) < 0
            || sample(fd[SOURCE], "", S_IFDIR, &tree) < 0 || sample(fd[ROOT], "", S_IFDIR, &root) < 0) return -1;
    return same_node(&proc, &owner->proc) && same_node(&task, &owner->task)
        && same_node(&tree, &owner->tree) && same_node(&root, &owner->root) ? 0 : refuse(ESTALE);
}

static int open_anchors(struct guest_core_apex_parent_observer *owner, const int witnesses[GTR_WITNESSES],
                        const int rights[GTR_VIEW_RIGHTS], const struct gtc_observation *initial) {
    int *fd = owner->fd;
    const int wanted[] = {witnesses[GTC_TREE], rights[GTC_GUEST_ROOT], witnesses[GTC_PARENT_NAMESPACE],
                          rights[GTC_NAMESPACE]};
    for (unsigned i = 0; i < sizeof(wanted) / sizeof(wanted[0]); ++i) {
        fd[i] = fcntl(wanted[i], F_DUPFD_CLOEXEC, 3);
        if (fd[i] < 0) return -1;
    }
    int length = snprintf(owner->pid_name, sizeof(owner->pid_name), "%ld", (long)owner->child);
    if (length < 0 || (size_t)length >= sizeof(owner->pid_name)) return refuse(EOVERFLOW);
    if (namespace_fd(fd[PARENT_NS], &owner->parent_ns) < 0 || namespace_fd(fd[CHILD_NS], &owner->child_ns) < 0
            || sample(fd[SOURCE], "", S_IFDIR, &owner->tree) < 0 || sample(fd[ROOT], "", S_IFDIR, &owner->root) < 0)
        return -1;
    if (same_ns(&owner->parent_ns, &owner->child_ns) || !same_inode(&owner->tree, &owner->root)
            || (uint64_t)owner->child_ns.st_ino != initial->namespace_inode
            || (uint64_t)owner->child_ns.st_dev != initial->namespace_dev
            || owner->root.stx_mnt_id != initial->mounts[GTC_GUEST_ROOT]) return refuse(ESTALE);
    fd[PROC] = open("/proc", DIR_FLAGS);
    struct statx value;
    if (fd[PROC] < 0 || fs_type(fd[PROC], PROC_SUPER_MAGIC) < 0
            || sample(fd[PROC], "", S_IFDIR, &owner->proc) < 0
            || proc_member(owner, fd[PROC], "self", S_IFLNK, &value) < 0) return -1;
    fd[SELF] = openat(fd[PROC], "self", O_PATH | O_DIRECTORY | O_CLOEXEC);
    fd[TASK] = openat(fd[PROC], owner->pid_name, DIR_FLAGS);
    if (fd[SELF] < 0 || fd[TASK] < 0 || proc_member(owner, fd[SELF], "", S_IFDIR, &value) < 0
            || proc_member(owner, fd[TASK], "", S_IFDIR, &owner->task) < 0) return -1;
    return 0;
}

struct initial_capture {
    struct guest_core_apex_parent_observer *owner;
    const int *rights;
    const struct gtc_observation *initial;
};

static int row_stat(const struct gpv_mount_row *row, const struct statx *st) {
    return row && row->id == st->stx_mnt_id && row->major == st->stx_dev_major && row->minor == st->stx_dev_minor;
}

static int copy_initial(const struct guest_tree_parent_sample *sampled, void *context, int *close_error) {
    const struct initial_capture *input = context;
    struct guest_core_apex_parent_observer *owner = input->owner;
    const struct gtc_observation *view = input->initial;
    if (*close_error || !sampled->parent_count || !sampled->child_count
            || sampled->child_count > GPV_MOUNTINFO_MAX_ROWS - NEW_APEX_ROWS) return refuse(ESTALE);
    for (unsigned i = 1; i < GTR_VIEW_RIGHTS; ++i) {
        struct statx st;
        if (sample(input->rights[i], "", S_IFDIR, &st) < 0) return -1;
        if (!row_stat(gpv_mount_by_id(sampled->child_rows, sampled->child_count, view->mounts[i]), &st))
            return refuse(ESTALE);
    }
    const uint64_t ids[] = {view->guest_data_mount, view->guest_mirror_mount, view->alias_guest, view->alias_native};
    const uint64_t parents[] = {owner->root.stx_mnt_id, owner->root.stx_mnt_id,
                               view->guest_data_mount, view->mounts[GTC_DATA]};
    const char *const points[] = {GUEST_TREE_TARGET_PATH "/data", GUEST_TREE_TARGET_PATH "/data_mirror",
                                  GUEST_TREE_TARGET_PATH "/data/data", "/data/data"};
    for (unsigned i = 0; i < sizeof(ids) / sizeof(ids[0]); ++i) {
        const struct gpv_mount_row *row = gpv_mount_by_id(sampled->child_rows, sampled->child_count, ids[i]);
        if (!row || row->parent != parents[i] || strcmp(row->point, points[i])) return refuse(ESTALE);
    }
    for (size_t i = 0; i < sampled->child_count; ++i) {
        const struct gpv_mount_row *row = &sampled->child_rows[i];
        if (below(row->point, SIBLINGS) || below(row->point, APEX)) return refuse(ESTALE);
        if (below(row->point, GUEST_TREE_TARGET_PATH) && row->id != owner->root.stx_mnt_id
                && row->id != view->guest_data_mount && row->id != view->guest_mirror_mount
                && row->id != view->alias_guest && row->id != view->mounts[GTC_DEV]) return refuse(ESTALE);
    }
    owner->parent_count = sampled->parent_count;
    owner->child_count = sampled->child_count;
    owner->parent_rows = malloc(owner->parent_count * sizeof(*owner->parent_rows));
    if (!owner->parent_rows) return refuse(ENOMEM);
    owner->child_rows = malloc(owner->child_count * sizeof(*owner->child_rows));
    if (!owner->child_rows) return refuse(ENOMEM);
    memcpy(owner->parent_rows, sampled->parent_rows, owner->parent_count * sizeof(*owner->parent_rows));
    memcpy(owner->child_rows, sampled->child_rows, owner->child_count * sizeof(*owner->child_rows));
    return 0;
}

int guest_core_apex_parent_capture(struct gtr_owner *release, pid_t child,
        const int witnesses[GTR_WITNESSES], const int rights[GTR_VIEW_RIGHTS],
        const struct gtc_observation *initial, struct guest_core_apex_child_sources *source,
        struct guest_core_apex_parent_observer **out, int *close_error) {
    if (!controller()) return refuse(EPERM);
    if (!release || child <= 1 || child == getpid() || !witnesses || !rights || !initial || !source
            || !out || *out || !close_error || *close_error) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.state = CAPTURING;
    one.parent = getpid();
    one.child = child;
    one.release = release;
    one.source = source;
    for (unsigned i = 0; i < HELD; ++i) one.fd[i] = -1;
    *out = &one;
    struct initial_capture input = {&one, rights, initial};
    int result = gtr_child_live(release);
    if (result == 0) errno = ECHILD;
    if (result != 1 || open_anchors(&one, witnesses, rights, initial) < 0
            || live(&one, close_error) < 0
            || guest_tree_parent_view_inspect(child, one.fd[SOURCE], one.fd[PARENT_NS], one.fd[CHILD_NS], one.fd[ROOT],
                initial->namespace_dev, initial->namespace_inode, initial->mounts[GTC_GUEST_ROOT],
                copy_initial, &input, close_error) < 0 || live(&one, close_error) < 0) return fail(&one);
    one.state = CAPTURED;
    return 0;
}

static int read_table(const struct guest_core_apex_parent_observer *owner, int task,
                       struct gpv_mount_row **rows, size_t *count, int *close_error) {
    const size_t limit = GPV_MOUNTINFO_MAX_BYTES;
    size_t used = 0, lines = 0;
    int error = 0;
    struct statx value;
    char *text = NULL;
    int fd = openat(task, "mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (proc_member(owner, fd, "", S_IFREG, &value) < 0) error = errno;
    else if (!(text = malloc(limit + 1))) error = ENOMEM;
    while (!error && used <= limit) {
        ssize_t n = read(fd, text + used, limit + 1 - used);
        if (n < 0) error = errno;
        else if (!n) break;
        else used += (size_t)n;
    }
    close_fd(&fd, &error, close_error);
    if (!error && used > limit) error = E2BIG;
    if (!error) {
        for (size_t i = 0; i < used; ++i) if (text[i] == '\n') ++lines;
        if (!lines || lines > GPV_MOUNTINFO_MAX_ROWS) error = EPROTO;
        else if (!(*rows = calloc(lines, sizeof(**rows)))) error = ENOMEM;
        else if (gpv_parse_mountinfo(text, used, *rows, lines, count) != GPV_OK) error = EPROTO;
    }
    free(text);
    return error ? refuse(error) : 0;
}

static int open_dir(struct temporary *local, int base, const char *name, int flags) {
    if (local->count == sizeof(local->fd) / sizeof(local->fd[0])) return refuse(EOVERFLOW);
    int fd = openat(base, name, flags);
    if (fd >= 0) local->fd[local->count++] = fd;
    return fd;
}

static int shape(int fd, const struct statx *held, int aliases, int *close_error) {
    unsigned seen = 0;
    int error = 0;
    struct statx st;
    int read_fd = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (read_fd < 0) return -1;
    if (sample(read_fd, "", S_IFDIR, &st) < 0) error = errno;
    else if (!same_node(&st, held)) error = ESTALE;
    DIR *dir = NULL;
    if (!error) {
        dir = fdopendir(read_fd);
        if (!dir) error = errno;
        else read_fd = -1;
    }
    while (!error) {
        errno = 0;
        struct dirent *entry = readdir(dir);
        if (!entry) { error = errno; break; }
        const char *name = entry->d_name;
        if (!strcmp(name, ".") || !strcmp(name, "..")) continue;
        unsigned bit = 0;
        for (unsigned i = 0; i < GCA_COUNT; ++i) {
            if (!strcmp(name, roles[i].stable)) bit = 1U << i;
            if (aliases && !strcmp(name, roles[i].versioned)) bit = 1U << (i + GCA_COUNT);
        }
        if (!bit || (seen & bit) || entry->d_type != DT_DIR) error = ESTALE;
        seen |= bit;
    }
    if (dir && closedir(dir) < 0) {
        int failure = errno ? errno : EIO;
        if (!error) error = failure;
        if (!*close_error) *close_error = failure;
    }
    close_fd(&read_fd, &error, close_error);
    if (error) return refuse(error);
    return seen == ((1U << (aliases ? 2 * GCA_COUNT : GCA_COUNT)) - 1) ? 0 : refuse(ESTALE);
}

static int module_fd(int fd, const struct gpv_mount_row *row, unsigned role, struct statx *st) {
    struct statvfs attrs;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV;
    if (sample(fd, "", S_IFDIR, st) < 0 || fs_type(fd, roles[role].magic) < 0 || fstatvfs(fd, &attrs) < 0) return -1;
    return row_stat(row, st) && st->stx_ino == roles[role].inode && st->stx_mode == (S_IFDIR | 0755)
        && st->stx_uid == 1000 && st->stx_gid == 1000 && (attrs.f_flag & (required | ST_NOEXEC)) == required
        && (st->stx_attributes_mask & st->stx_attributes & STATX_ATTR_MOUNT_ROOT) ? 0 : refuse(ESTALE);
}

static int names(const struct guest_core_apex_parent_observer *owner, const struct added_rows *added,
                 struct temporary *local, int *close_error) {
    struct statx link, mnt, gvi, guest, siblings, apex;
    struct statvfs flags;
    if (proc_member(owner, owner->fd[TASK], "root", S_IFLNK, &link) < 0) return -1;
    int child = open_dir(local, owner->fd[TASK], "root", O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (child < 0) return -1;
    int mnt_fd = open_dir(local, child, "mnt", DIR_FLAGS);
    if (mnt_fd < 0) return -1;
    int gvi_fd = open_dir(local, mnt_fd, "gvi", DIR_FLAGS);
    if (gvi_fd < 0) return -1;
    int guest_fd = open_dir(local, gvi_fd, "root", DIR_FLAGS);
    if (guest_fd < 0) return -1;
    int siblings_fd = open_dir(local, gvi_fd, "apex-inputs", DIR_FLAGS);
    if (siblings_fd < 0) return -1;
    int apex_fd = open_dir(local, guest_fd, "apex", DIR_FLAGS);
    if (apex_fd < 0 || sample(mnt_fd, "", S_IFDIR, &mnt) < 0 || sample(gvi_fd, "", S_IFDIR, &gvi) < 0
            || sample(guest_fd, "", S_IFDIR, &guest) < 0 || sample(siblings_fd, "", S_IFDIR, &siblings) < 0
            || sample(apex_fd, "", S_IFDIR, &apex) < 0 || fs_type(apex_fd, TMPFS_MAGIC) < 0
            || fstatvfs(apex_fd, &flags) < 0) return -1;
    if (!same_node(&guest, &owner->root) || mnt.stx_mnt_id != added->sibling[0]->parent
            || !same_mount(&mnt, &gvi) || !same_mount(&mnt, &siblings) || !row_stat(added->apex, &apex)
            || gvi.stx_uid || gvi.stx_gid || gvi.stx_mode != (S_IFDIR | 0700)
            || siblings.stx_uid || siblings.stx_gid || siblings.stx_mode != (S_IFDIR | 0700)
            || apex.stx_uid || apex.stx_gid || apex.stx_mode != (S_IFDIR | 0755)
            || (flags.f_flag & (ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC)) != (ST_NOSUID | ST_NODEV | ST_NOEXEC)
            || !(apex.stx_attributes_mask & apex.stx_attributes & STATX_ATTR_MOUNT_ROOT)) return refuse(ESTALE);
    if (shape(siblings_fd, &siblings, 0, close_error) < 0 || shape(apex_fd, &apex, 1, close_error) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        struct statx sibling, stable, versioned;
        int sibling_fd = open_dir(local, siblings_fd, roles[i].stable, DIR_FLAGS);
        if (sibling_fd < 0 || module_fd(sibling_fd, added->sibling[i], i, &sibling) < 0) return -1;
        int matched = guest_core_apex_child_sources_match_parent(owner->source, (enum guest_core_apex_role)i, sibling_fd);
        if (matched != 0) return matched < 0 ? -1 : refuse(EPROTO);
        int stable_fd = open_dir(local, apex_fd, roles[i].stable, DIR_FLAGS);
        if (stable_fd < 0 || module_fd(stable_fd, added->stable[i], i, &stable) < 0) return -1;
        int versioned_fd = open_dir(local, apex_fd, roles[i].versioned, DIR_FLAGS);
        if (versioned_fd < 0 || module_fd(versioned_fd, added->versioned[i], i, &versioned) < 0) return -1;
        if (!same_inode(&sibling, &stable) || !same_inode(&sibling, &versioned)) return refuse(ESTALE);
    }
    return 0;
}

int guest_core_apex_parent_observe(struct guest_core_apex_parent_observer *owner,
        struct guest_core_apex_parent_observation *out, int *close_error) {
    if (owned(owner) < 0) return -1;
    if (!out || !close_error) return refuse(EINVAL);
    if (owner->state != CAPTURED) return refuse(owner->error ? owner->error : EALREADY);
    owner->state = OBSERVING;
    int error = *close_error;
    struct gpv_mount_row *parent = NULL, *child = NULL;
    size_t parent_count, child_count;
    struct added_rows added;
    struct guest_core_apex_parent_observation actual = {0};
    struct temporary local = {0};
    if (error) goto done;
    if (live(owner, close_error) < 0
            || read_table(owner, owner->fd[SELF], &parent, &parent_count, close_error) < 0
            || read_table(owner, owner->fd[TASK], &child, &child_count, close_error) < 0) {
        error = errno ? errno : EIO;
        goto done;
    }
    if (owner->parent_count != parent_count || !preserves(owner->parent_rows, owner->parent_count, parent, parent_count)
            || !exact_delta(owner->child_rows, owner->child_count, child, child_count, owner->root.stx_mnt_id, &added)) {
        error = ESTALE;
        goto done;
    }
    if (names(owner, &added, &local, close_error) < 0 || live(owner, close_error) < 0) {
        error = errno ? errno : EIO;
        goto done;
    }
    actual.namespace_dev = (uint64_t)owner->child_ns.st_dev;
    actual.namespace_inode = (uint64_t)owner->child_ns.st_ino;
    actual.root = owner->root.stx_mnt_id;
    actual.apex = added.apex->id;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        actual.role[i].sibling = added.sibling[i]->id;
        actual.role[i].stable = added.stable[i]->id;
        actual.role[i].versioned = added.versioned[i]->id;
    }
done:
    free(child);
    free(parent);
    while (local.count) close_fd(&local.fd[--local.count], &error, close_error);
    if (error) {
        errno = error;
        return fail(owner);
    }
    owner->state = OBSERVED;
    *out = actual;
    return 0;
}

int guest_core_apex_parent_observer_close(struct guest_core_apex_parent_observer *owner, int *close_error) {
    if (owned(owner) < 0) return -1;
    if (!close_error) return refuse(EINVAL);
    if (owner->state == CAPTURING || owner->state == OBSERVING) return refuse(EBUSY);
    int error = owner->error ? owner->error : *close_error;
    owner->state = CLOSED;
    for (unsigned i = HELD; i; --i) close_fd(&owner->fd[i - 1], &error, close_error);
    free(owner->child_rows);
    free(owner->parent_rows);
    owner->child_rows = owner->parent_rows = NULL;
    if (error) owner->error = error;
    return error ? refuse(error) : 0;
}
#endif
