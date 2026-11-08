#define _GNU_SOURCE
#include "guest_core_apex_child_attach.h"

#include <string.h>

#define INPUT_NAME "apex-inputs"
#define INPUT_PATH "/mnt/gvi/" INPUT_NAME
#define FINAL_APEX GUEST_TREE_TARGET_PATH "/apex"

struct child_role {
    const char *name, *point, *filesystem;
    unsigned long magic;
    uint64_t bytes, root_inode;
};

#define ROLE(name, fs, magic, bytes, ino) {name, INPUT_PATH "/" name, fs, magic, bytes, ino}
static const struct child_role roles[GCA_COUNT] = {
    [GCA_ART] = ROLE("com.android.art", "ext4", 0xef53UL, 31633408, 2),
    [GCA_I18N] = ROLE("com.android.i18n", "erofs", 0xe0f5e1e2UL, 21409792, 39),
    [GCA_RUNTIME] = ROLE("com.android.runtime", "erofs", 0xe0f5e1e2UL, 5296128, 39),
};
#undef ROLE

static int below(const char *name, const char *root) {
    size_t size = strlen(root);
    return !strncmp(name, root, size) && (!name[size] || name[size] == '/');
}

static int option(const char *list, const char *wanted) {
    size_t size = strlen(wanted);
    while (*list) {
        size_t field = strcspn(list, ",");
        if (field == size && !memcmp(list, wanted, size)) return 1;
        list += field;
        if (*list) ++list;
    }
    return 0;
}

static int private_row(const struct gpv_mount_row *row) {
    return row && !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static int row_device(const struct gpv_mount_row *row, struct guest_tree_mount_identity value) {
    return row && row->id == value.id && row->major == value.major && row->minor == value.minor;
}

static int input_rows(const struct gpv_mount_row *rows, size_t count, uint64_t scaffold,
                      const struct guest_tree_mount_identity expected[GCA_COUNT], unsigned moved) {
    unsigned seen = 0;
    if (moved > GCA_COUNT) return 0;
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *row = &rows[i];
        if (below(row->point, FINAL_APEX)) return 0;
        unsigned role = 0;
        while (role < GCA_COUNT && expected[role].id != row->id) ++role;
        if (role == GCA_COUNT) {
            if (below(row->point, INPUT_PATH)) return 0;
            continue;
        }
        unsigned bit = 1U << role;
        if (role >= moved || (seen & bit) || !private_row(row) || !row_device(row, expected[role])
                || row->parent != scaffold || strcmp(row->root, "/") || strcmp(row->point, roles[role].point)
                || strcmp(row->type, roles[role].filesystem) || !option(row->super_options, "ro")
                || !option(row->options, "ro") || !option(row->options, "nosuid")
                || !option(row->options, "nodev") || option(row->options, "noexec")) return 0;
        seen |= bit;
    }
    return seen == ((1U << moved) - 1U);
}

#ifndef GCACA_INERT
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/loop.h>
#include <linux/magic.h>
#include <linux/major.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_MNT_ID)

enum { PAYLOAD, BLOCK, DETACHED, SOURCE_FDS };
enum { OPENING = 1, AVAILABLE, ATTACHING, ATTACHED, LENT, REFUSED, CLOSED };
enum { PARENT_NS, CHILD_NS, TREE, APEX, MNT, SCAFFOLD, INPUTS, ANCHORS };

struct child_cell {
    int fd[SOURCE_FDS], target, reopened;
    struct statx original[SOURCE_FDS];
};

struct guest_core_apex_child_sources {
    pid_t parent;
    struct stat original_ns;
    struct guest_tree_mount_identity tree, scaffold;
    struct statx mnt, gvi, apex, inputs;
    struct child_cell role[GCA_COUNT];
    int anchor[ANCHORS], state, error;
    unsigned moved;
};

static struct guest_core_apex_child_sources one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int fail(struct guest_core_apex_child_sources *source) {
    if (!source->error) source->error = errno ? errno : EIO;
    source->state = REFUSED;
    return refuse(source->error);
}

static int leader(void) {
    return getpid() == gettid() && !getuid() && !geteuid() && !getegid();
}

static int direct_child(const struct guest_core_apex_child_sources *source) {
    if (source != &one || source->parent <= 1 || !leader() || getppid() != source->parent)
        return refuse(EPERM);
    int signal;
    if (prctl(PR_GET_PDEATHSIG, &signal, 0L, 0L, 0L) < 0) return -1;
    return signal == SIGKILL ? 0 : refuse(EPERM);
}

static int namespace_fd(int fd, struct stat *out) {
    struct statfs fs;
    if (fstat(fd, out) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS && out->st_ino ? 0 : refuse(EXDEV);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int current_child(const struct guest_core_apex_child_sources *source, int parent_fd, int child_fd) {
    struct stat parent, child, live_parent, live_child;
    char name[48];
    if (direct_child(source) < 0) return -1;
    int length = snprintf(name, sizeof(name), "/proc/%ld/ns/mnt", (long)source->parent);
    if (length < 0 || (size_t)length >= sizeof(name)) return refuse(EOVERFLOW);
    if (namespace_fd(parent_fd, &parent) < 0 || namespace_fd(child_fd, &child) < 0
            || stat(name, &live_parent) < 0 || stat("/proc/self/ns/mnt", &live_child) < 0) return -1;
    return same_ns(&source->original_ns, &parent) && same_ns(&parent, &live_parent)
        && same_ns(&child, &live_child) && !same_ns(&parent, &child) ? 0 : refuse(EXDEV);
}

static int sample(int base, const char *name, struct statx *out) {
    if (statx(base, name, LOOKUP | AT_EMPTY_PATH, MASK, out) < 0) return -1;
    return (out->stx_mask & MASK) == MASK && out->stx_mnt_id && out->stx_ino ? 0 : refuse(EXDEV);
}

static struct guest_tree_mount_identity mount_id(const struct statx *st) {
    return (struct guest_tree_mount_identity){st->stx_mnt_id, st->stx_dev_major, st->stx_dev_minor};
}

static int in_mount(const struct statx *st, struct guest_tree_mount_identity id) {
    return st->stx_mnt_id == id.id && st->stx_dev_major == id.major && st->stx_dev_minor == id.minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return in_mount(a, mount_id(b)) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid
        && a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor;
}

static int named(int base, const char *name, const struct statx *held) {
    struct statx actual;
    if (sample(base, name, &actual) < 0) return -1;
    return same_node(held, &actual) ? 0 : refuse(ESTALE);
}

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return flags & FD_CLOEXEC ? 0 : refuse(EXDEV);
}

static int mount_source(const struct child_cell *cell, unsigned role) {
    struct statx st[SOURCE_FDS];
    struct statfs fs;
    struct statvfs attrs;
    struct stat backing;
    struct loop_info64 loop;
    int readonly;
    uint64_t size;
    for (unsigned i = 0; i < SOURCE_FDS; ++i) {
        int mode = fcntl(cell->fd[i], F_GETFL);
        if (mode < 0) return -1;
        if ((mode & (O_PATH | O_ACCMODE)) != (i == DETACHED ? O_PATH : O_RDONLY)) return refuse(EXDEV);
        if (cloexec(cell->fd[i]) < 0 || sample(cell->fd[i], "", &st[i]) < 0) return -1;
        if (!same_node(&st[i], &cell->original[i])) return refuse(ESTALE);
    }
    if (fstat(cell->fd[PAYLOAD], &backing) < 0 || ioctl(cell->fd[BLOCK], LOOP_GET_STATUS64, &loop) < 0
            || ioctl(cell->fd[BLOCK], BLKROGET, &readonly) < 0
            || ioctl(cell->fd[BLOCK], BLKGETSIZE64, &size) < 0
            || fstatfs(cell->fd[DETACHED], &fs) < 0 || fstatvfs(cell->fd[DETACHED], &attrs) < 0) return -1;
    const unsigned long flags = ST_RDONLY | ST_NOSUID | ST_NODEV;
    const struct statx *block = &st[BLOCK], *root = &st[DETACHED];
    return S_ISREG(backing.st_mode) && backing.st_size >= 0 && (uint64_t)backing.st_size == roles[role].bytes
        && S_ISBLK(block->stx_mode) && block->stx_rdev_major == LOOP_MAJOR && size == roles[role].bytes
        && loop.lo_device == backing.st_dev && loop.lo_inode == backing.st_ino && !loop.lo_rdevice
        && loop.lo_number == block->stx_rdev_minor && !loop.lo_offset && !loop.lo_sizelimit && !loop.lo_encrypt_type
        && loop.lo_flags == (LO_FLAGS_READ_ONLY | LO_FLAGS_AUTOCLEAR) && readonly == 1
        && root->stx_dev_major == block->stx_rdev_major && root->stx_dev_minor == block->stx_rdev_minor
        && (root->stx_attributes_mask & root->stx_attributes & STATX_ATTR_MOUNT_ROOT)
        && root->stx_mode == (S_IFDIR | 0755) && root->stx_uid == 1000 && root->stx_gid == 1000
        && root->stx_ino == roles[role].root_inode && (unsigned long)fs.f_type == roles[role].magic
        && (attrs.f_flag & (flags | ST_NOEXEC)) == flags ? 0 : refuse(EXDEV);
}

int guest_core_apex_child_sources_prepare(struct guest_core_apex_mount_roots *mounts,
        struct guest_core_apex_child_sources **out) {
    if (!mounts || !out || *out) return refuse(EINVAL);
    if (!leader() || getpid() <= 1) return refuse(EPERM);
    if (one.state) return refuse(EALREADY);
    one.state = OPENING;
    one.parent = getpid();
    for (unsigned i = 0; i < ANCHORS; ++i) one.anchor[i] = -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        one.role[i].target = one.role[i].reopened = -1;
        for (unsigned j = 0; j < SOURCE_FDS; ++j) one.role[i].fd[j] = -1;
    }
    *out = &one;
    struct guest_core_apex_backing borrowed[GCA_COUNT];
    for (unsigned i = 0; i < GCA_COUNT; ++i) borrowed[i] = (struct guest_core_apex_backing){-1, -1, -1};
    if (stat("/proc/self/ns/mnt", &one.original_ns) < 0 || guest_core_apex_mount_borrow(mounts, borrowed) < 0)
        return fail(&one);
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        struct child_cell *cell = &one.role[i];
        const int fds[] = {borrowed[i].payload_fd, borrowed[i].loop_fd, borrowed[i].mounted_root_fd};
        for (unsigned j = 0; j < SOURCE_FDS; ++j) {
            cell->fd[j] = fcntl(fds[j], F_DUPFD_CLOEXEC, 3);
            if (cell->fd[j] < 0 || sample(fds[j], "", &cell->original[j]) < 0) return fail(&one);
        }
        if (mount_source(cell, i) < 0) return fail(&one);
    }
    one.state = AVAILABLE;
    return 0;
}

int guest_core_apex_child_sources_keep_in_child(struct guest_core_apex_child_sources *source, int fd) {
    if (direct_child(source) < 0) return -1;
    if (source->state != AVAILABLE || fd < 0) return refuse(EINVAL);
    for (unsigned i = 0; i < GCA_COUNT; ++i) for (unsigned j = 0; j < SOURCE_FDS; ++j) {
        if (source->role[i].fd[j] != fd) continue;
        if (cloexec(fd) < 0 || named(fd, "", &source->role[i].original[j]) < 0) return fail(source);
        return 1;
    }
    return 0;
}

int guest_core_apex_child_sources_match_parent(struct guest_core_apex_child_sources *source,
        enum guest_core_apex_role role, int named_sibling_fd) {
    if (source != &one || (unsigned)role >= GCA_COUNT || named_sibling_fd < 0)
        return refuse(EINVAL);
    if (!leader() || source->parent != getpid() || source->state != AVAILABLE)
        return refuse(EPERM);
    struct stat before, after;
    if (stat("/proc/self/ns/mnt", &before) < 0) return -1;
    if (!same_ns(&source->original_ns, &before)) return refuse(EXDEV);
    int flags = fcntl(named_sibling_fd, F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_PATH) return refuse(EXDEV);
    const struct child_cell *cell = &source->role[role];
    if (cloexec(named_sibling_fd) < 0 || mount_source(cell, (unsigned)role) < 0
            || named(named_sibling_fd, "", &cell->original[DETACHED]) < 0
            || stat("/proc/self/ns/mnt", &after) < 0) return -1;
    return same_ns(&before, &after) ? 0 : refuse(EXDEV);
}

static int workspace(struct guest_tree_mount_scratch scratch) {
    return scratch.text && scratch.rows && scratch.text_capacity && scratch.row_capacity
        && scratch.text_capacity <= GPV_MOUNTINFO_MAX_BYTES + 1U && scratch.row_capacity <= GPV_MOUNTINFO_MAX_ROWS;
}

static int mountinfo(struct guest_tree_mount_scratch scratch, size_t *count) {
    struct statfs fs;
    struct statx proc, file;
    size_t used = 0;
    int error = 0;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || sample(fd, "", &file) < 0 || sample(AT_FDCWD, "/proc", &proc) < 0) error = errno;
    else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISREG(file.stx_mode)
            || !S_ISDIR(proc.stx_mode) || !in_mount(&file, mount_id(&proc))) error = EXDEV;
    while (!error && used < scratch.text_capacity) {
        ssize_t n = read(fd, scratch.text + used, scratch.text_capacity - used);
        if (n < 0) error = errno;
        else if (!n) break;
        else used += (size_t)n;
    }
    if (close(fd) < 0 && !error) error = errno;
    if (error) return refuse(error);
    return used < scratch.text_capacity && gpv_parse_mountinfo(scratch.text, used, scratch.rows,
        scratch.row_capacity, count) == GPV_OK ? 0 : refuse(EPROTO);
}

static int anchors(struct guest_core_apex_child_sources *source) {
    const int *a = source->anchor;
    struct statx tree;
    if (current_child(source, a[PARENT_NS], a[CHILD_NS]) < 0 || named(AT_FDCWD, "/mnt", &source->mnt) < 0
            || named(a[MNT], "gvi", &source->gvi) < 0 || sample(a[TREE], "", &tree) < 0
            || named(a[SCAFFOLD], "root", &tree) < 0 || named(a[TREE], "apex", &source->apex) < 0) return -1;
    if (!in_mount(&tree, source->tree)) return refuse(ESTALE);
    return a[INPUTS] < 0 ? 0 : named(a[SCAFFOLD], INPUT_NAME, &source->inputs);
}

static int readback(struct guest_core_apex_child_sources *source, struct guest_tree_mount_scratch scratch) {
    size_t count;
    if (anchors(source) < 0 || mountinfo(scratch, &count) < 0) return -1;
    const struct gpv_mount_row *scaffold = gpv_mount_by_id(scratch.rows, count, source->scaffold.id);
    const struct gpv_mount_row *tree = gpv_mount_by_id(scratch.rows, count, source->tree.id);
    if (!private_row(scaffold) || !row_device(scaffold, source->scaffold) || strcmp(scaffold->point, "/mnt")
            || strcmp(scaffold->root, "/") || strcmp(scaffold->type, "tmpfs")
            || strcmp(scaffold->source, "gvo-v2-scaffold") || !private_row(tree) || !row_device(tree, source->tree)
            || tree->parent != scaffold->id || strcmp(tree->point, GUEST_TREE_TARGET_PATH)) return refuse(ESTALE);
    struct guest_tree_mount_identity expected[GCA_COUNT];
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        const struct child_cell *cell = &source->role[i];
        expected[i] = mount_id(&cell->original[DETACHED]);
        if (mount_source(cell, i) < 0) return -1;
        if (i < source->moved && (named(cell->reopened, "", &cell->original[DETACHED]) < 0
                || named(source->anchor[INPUTS], roles[i].name, &cell->original[DETACHED]) < 0)) return -1;
    }
    if (!input_rows(scratch.rows, count, scaffold->id, expected, source->moved)) return refuse(ESTALE);
    return anchors(source);
}

static int open_anchors(struct guest_core_apex_child_sources *source,
        const struct guest_tree_root_preparation *prepared, int parent_ns, int child_ns) {
    int *a = source->anchor;
    struct statx root, clone;
    const int in[] = {parent_ns, child_ns, prepared->readback.root_fd};
    for (unsigned i = 0; i < sizeof(in) / sizeof(in[0]); ++i) {
        a[i] = fcntl(in[i], F_DUPFD_CLOEXEC, 3);
        if (a[i] < 0) return -1;
    }
    source->tree = prepared->readback.attached;
    source->scaffold = prepared->readback.scaffold;
    a[MNT] = open("/mnt", DIRECTORY);
    if (a[MNT] < 0) return -1;
    a[SCAFFOLD] = openat(a[MNT], "gvi", DIRECTORY);
    if (a[SCAFFOLD] < 0) return -1;
    a[APEX] = openat(a[TREE], "apex", DIRECTORY);
    if (a[APEX] < 0 || sample(a[MNT], "", &source->mnt) < 0 || sample(a[SCAFFOLD], "", &source->gvi) < 0
            || sample(a[APEX], "", &source->apex) < 0 || sample(a[TREE], "", &root) < 0
            || sample(prepared->attachment.clone_fd, "", &clone) < 0) return -1;
    if (!same_node(&root, &clone) || !in_mount(&root, source->tree) || !in_mount(&source->apex, source->tree)
            || !in_mount(&source->mnt, source->scaffold) || !in_mount(&source->gvi, source->scaffold)
            || source->gvi.stx_mode != (S_IFDIR | 0700) || source->gvi.stx_uid || source->gvi.stx_gid
            || source->apex.stx_mode != (S_IFDIR | 0755) || source->apex.stx_uid || source->apex.stx_gid)
        return refuse(EXDEV);
    return anchors(source);
}

int guest_core_apex_child_attach(struct guest_core_apex_child_sources *source,
        const struct guest_tree_root_preparation *prepared, int parent_ns, int child_ns,
        struct guest_tree_mount_scratch scratch) {
    if (direct_child(source) < 0) return -1;
    if (!prepared || prepared->attachment.state != GUEST_TREE_ATTACH_MOVE_RETURNED || !workspace(scratch))
        return refuse(EINVAL);
    if (source->state != AVAILABLE) return refuse(EALREADY);
    source->state = ATTACHING;
    int *a = source->anchor;
    if (open_anchors(source, prepared, parent_ns, child_ns) < 0 || readback(source, scratch) < 0
            || mkdirat(a[SCAFFOLD], INPUT_NAME, 0700) < 0) return fail(source);
    a[INPUTS] = openat(a[SCAFFOLD], INPUT_NAME, DIRECTORY);
    if (a[INPUTS] < 0 || sample(a[INPUTS], "", &source->inputs) < 0) return fail(source);
    if (!in_mount(&source->inputs, source->scaffold) || source->inputs.stx_mode != (S_IFDIR | 0700)
            || source->inputs.stx_uid || source->inputs.stx_gid) {
        errno = EXDEV;
        return fail(source);
    }
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        struct child_cell *cell = &source->role[i];
        struct statx empty;
        if (mkdirat(a[INPUTS], roles[i].name, 0700) < 0) return fail(source);
        cell->target = openat(a[INPUTS], roles[i].name, DIRECTORY);
        if (cell->target < 0 || sample(cell->target, "", &empty) < 0 || readback(source, scratch) < 0
                || named(a[INPUTS], roles[i].name, &empty) < 0) return fail(source);
        if (!in_mount(&empty, source->scaffold) || empty.stx_mode != (S_IFDIR | 0700)
                || empty.stx_uid || empty.stx_gid) {
            errno = EXDEV;
            return fail(source);
        }
        /* The only writer is this child. mkdirat never adopts an existing
         * target. move_mount itself has no no-overmount flag. */
        if (syscall(SYS_move_mount, cell->fd[DETACHED], "", cell->target, "",
                    MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) return fail(source);
        cell->reopened = openat(a[INPUTS], roles[i].name, DIRECTORY);
        if (cell->reopened < 0) return fail(source);
        ++source->moved;
        if (readback(source, scratch) < 0) return fail(source);
    }
    source->state = ATTACHED;
    return 0;
}

int guest_core_apex_child_borrow(struct guest_core_apex_child_sources *source,
        struct guest_tree_mount_scratch scratch, struct guest_core_apex_backing out[GCA_COUNT]) {
    if (direct_child(source) < 0) return -1;
    if (!out || !workspace(scratch)) return refuse(EINVAL);
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        if (out[i].payload_fd != -1 || out[i].loop_fd != -1 || out[i].mounted_root_fd != -1) return refuse(EINVAL);
    if (source->state != ATTACHED) return refuse(source->error ? source->error : EALREADY);
    if (readback(source, scratch) < 0) return fail(source);
    source->state = LENT;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        const struct child_cell *cell = &source->role[i];
        out[i] = (struct guest_core_apex_backing){cell->fd[PAYLOAD], cell->fd[BLOCK], cell->reopened};
    }
    return 0;
}

int guest_core_apex_child_sources_close(struct guest_core_apex_child_sources *source) {
    if (!leader() || source != &one || source->parent != getpid()) return refuse(EPERM);
    if (source->state == OPENING) return refuse(EBUSY);
    source->state = CLOSED;
    for (unsigned i = GCA_COUNT; i; --i) for (unsigned j = SOURCE_FDS; j; --j) {
        int *slot = &source->role[i - 1].fd[j - 1];
        int fd = *slot;
        *slot = -1;
        if (fd >= 0 && close(fd) < 0 && !source->error) source->error = errno ? errno : EIO;
    }
    return source->error ? refuse(source->error) : 0;
}
#endif
