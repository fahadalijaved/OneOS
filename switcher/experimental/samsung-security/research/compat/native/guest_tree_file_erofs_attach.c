#define _GNU_SOURCE
#include "guest_tree_file_erofs_attach.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define STAT_MASK (STATX_TYPE | STATX_MODE | STATX_INO | STATX_UID | STATX_GID | STATX_NLINK | STATX_MNT_ID)
#define EROFS_FLAGS (ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC)

static atomic_flag attempted = ATOMIC_FLAG_INIT;

/* Pure mount-table checks. */
static int private_row(const struct gpv_mount_row *row) {
    return !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static int below_stage(const char *path) {
    const size_t prefix = sizeof(GUEST_TREE_STAGE_PATH) - 1;
    return strncmp(path, GUEST_TREE_STAGE_PATH, prefix) == 0 &&
            (path[prefix] == '/' || path[prefix] == '\0');
}

static int row_device(const struct gpv_mount_row *row, struct guest_tree_mount_identity value) {
    return row->major == value.major && row->minor == value.minor;
}

static int mount_option(const char *options, const char *key, int valued) {
    size_t key_length = strlen(key);
    while (*options) {
        size_t length = strcspn(options, ",");
        if (length >= key_length && !memcmp(options, key, key_length) &&
                (length == key_length || (valued && options[key_length] == '='))) return 1;
        options += length;
        if (*options) ++options;
    }
    return 0;
}

static int same_row(const struct gpv_mount_row *a, const struct gpv_mount_row *b) {
    return b && a->id == b->id && a->parent == b->parent && a->shared == b->shared &&
            a->master == b->master && a->propagate == b->propagate && a->major == b->major &&
            a->minor == b->minor && a->unbindable == b->unbindable && !strcmp(a->root, b->root) &&
            !strcmp(a->point, b->point) && !strcmp(a->type, b->type) && !strcmp(a->source, b->source) &&
            !strcmp(a->options, b->options) && !strcmp(a->super_options, b->super_options);
}

static int before_matches(const struct gpv_mount_row *rows, size_t count,
        struct guest_tree_mount_identity stage, struct guest_tree_mount_identity erofs) {
    const struct gpv_mount_row *parent = gpv_mount_by_id(rows, count, stage.id);
    if (!parent || !row_device(parent, stage) || !erofs.id || erofs.id == stage.id ||
            !mount_option(parent->options, "rw", 0) || !mount_option(parent->super_options, "rw", 0) ||
            mount_option(parent->options, "ro", 1) || mount_option(parent->super_options, "ro", 1) ||
            gpv_mount_by_id(rows, count, erofs.id)) return 0;
    for (size_t i = 0; i < count; ++i) {
        if (!private_row(&rows[i]) || below_stage(rows[i].point) || row_device(&rows[i], erofs)) return 0;
    }
    return 1;
}

static int after_matches(const struct gpv_mount_row *before, size_t old_count,
        const struct gpv_mount_row *after, size_t new_count,
        struct guest_tree_mount_identity stage, struct guest_tree_mount_identity erofs) {
    const struct gpv_mount_row *row = gpv_mount_by_id(after, new_count, erofs.id);
    if (new_count != old_count + 1 || !row || !row_device(row, erofs) || !private_row(row) ||
            row->parent != stage.id || strcmp(row->point, GUEST_TREE_BACKING_PATH) ||
            strcmp(row->root, "/") || strcmp(row->type, "erofs") ||
            !mount_option(row->options, "ro", 0) || !mount_option(row->options, "nosuid", 0) ||
            !mount_option(row->options, "nodev", 0) || !mount_option(row->options, "noexec", 0) ||
            !mount_option(row->super_options, "ro", 0) || mount_option(row->options, "rw", 1) ||
            mount_option(row->super_options, "rw", 1) || mount_option(row->super_options, "dax", 1) ||
            mount_option(row->super_options, "device", 1) || mount_option(row->super_options, "fsid", 1) ||
            mount_option(row->super_options, "domain_id", 1)) return 0;
    for (size_t i = 0; i < old_count; ++i) {
        if (!same_row(&before[i], gpv_mount_by_id(after, new_count, before[i].id))) return 0;
    }
    return 1;
}

/* Live descriptor acquisition and ownership. */
static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_temp(struct guest_tree_file_erofs_attachment *owner, int fd) {
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
}

static int namespace_stat(int fd, struct stat *identity) {
    struct statfs fs;
    if (fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !identity->st_ino) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int namespace_current(const struct guest_tree_file_erofs_attach_inputs *input) {
    struct stat initial, child, named;
    struct statfs proc;
    if (getpid() != gettid()) return refuse(EPERM);
    if (statfs("/proc", &proc) < 0) return -1;
    if ((unsigned long)proc.f_type != PROC_SUPER_MAGIC) return refuse(EXDEV);
    if (namespace_stat(input->initial_namespace_fd, &initial) < 0 ||
            namespace_stat(input->current_namespace_fd, &child) < 0 ||
            stat("/proc/self/ns/mnt", &named) < 0) return -1;
    if (child.st_dev != named.st_dev || child.st_ino != named.st_ino ||
            (initial.st_dev == child.st_dev && initial.st_ino == child.st_ino)) return refuse(EXDEV);
    return 0;
}

static int identity(int fd, const char *name, struct statx *value) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), STAT_MASK, value) < 0) return -1;
    if ((value->stx_mask & STAT_MASK) != STAT_MASK || !value->stx_ino || !value->stx_mnt_id ||
            !value->stx_nlink || (value->stx_attributes & STATX_ATTR_AUTOMOUNT)) return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id &&
            a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return S_ISDIR(a->stx_mode) && same_mount(a, b) && a->stx_ino == b->stx_ino &&
            a->stx_mode == b->stx_mode && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid &&
            a->stx_nlink == b->stx_nlink;
}

static int root_directory(const struct statx *value) {
    return S_ISDIR(value->stx_mode) && !value->stx_uid && !(value->stx_mode & 0022);
}

static struct guest_tree_mount_identity mount_identity(const struct statx *value) {
    return (struct guest_tree_mount_identity){value->stx_mnt_id, value->stx_dev_major, value->stx_dev_minor};
}

static int open_stage(struct guest_tree_file_erofs_attachment *owner, struct statx *stage) {
    static const char *const parts[] = {"data", "local", "tmp", "oneos-viewprep"};
    struct statx host_data, named;
    int fd = open("/", DIRECTORY);
    if (fd < 0) return -1;
    for (size_t i = 0; i < sizeof(parts) / sizeof(parts[0]); ++i) {
        int next = -1;
        if (identity(fd, parts[i], &named) == 0) {
            next = openat(fd, parts[i], DIRECTORY);
        }
        int failure = errno;
        close_temp(owner, fd);
        if (next < 0 || owner->close_error) {
            close_temp(owner, next);
            return refuse(next < 0 ? failure : owner->close_error);
        }
        fd = next;
        if (identity(fd, "", stage) < 0) {
            failure = errno;
            close_temp(owner, fd);
            return refuse(failure);
        }
        if (!same_directory(stage, &named) || (i && !same_mount(&host_data, stage))) {
            close_temp(owner, fd);
            return refuse(EXDEV);
        }
        if (!i) host_data = *stage;
    }
    if (!root_directory(stage)) {
        close_temp(owner, fd);
        return refuse(EXDEV);
    }
    return fd;
}

static int empty_target(struct guest_tree_file_erofs_attachment *owner, const struct statx *target) {
    struct statx readable;
    int fd = openat(owner->covered_fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int error = 0;
    if (identity(fd, "", &readable) < 0) error = errno;
    else if (!same_directory(target, &readable)) error = ESTALE;
    DIR *dir = error ? NULL : fdopendir(fd);
    if (!dir) {
        if (!error) error = errno;
        close_temp(owner, fd);
        return refuse(error);
    }
    unsigned found = 0;
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(dir);
        if (!entry) { error = errno; break; }
        unsigned bit;
        if (!strcmp(entry->d_name, ".")) bit = 1;
        else if (!strcmp(entry->d_name, "..")) bit = 2;
        else { error = ENOTEMPTY; break; }
        if (found & bit) { error = EPROTO; break; }
        found |= bit;
    }
    if (closedir(dir) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
    if (error || owner->close_error) return refuse(error ? error : owner->close_error);
    return found == 3 ? 0 : refuse(EPROTO);
}

static int erofs_directory(int fd, struct statx *value) {
    struct statfs fs;
    struct statvfs flags;
    if (identity(fd, "", value) < 0 || fstatfs(fd, &fs) < 0 || fstatvfs(fd, &flags) < 0) return -1;
    if (!root_directory(value) || (unsigned long)fs.f_type != EROFS_SUPER_MAGIC_V1 ||
            (flags.f_flag & EROFS_FLAGS) != EROFS_FLAGS) return refuse(EXDEV);
    return 0;
}

static int valid_scratch(struct guest_tree_mount_scratch scratch) {
    return scratch.text && scratch.rows && scratch.text_capacity &&
            scratch.text_capacity <= GPV_MOUNTINFO_MAX_BYTES && scratch.row_capacity &&
            scratch.row_capacity <= GPV_MOUNTINFO_MAX_ROWS;
}

static int read_rows(struct guest_tree_file_erofs_attachment *owner,
        struct guest_tree_mount_scratch scratch, size_t *count) {
    struct statfs fs;
    struct statx proc, info;
    size_t used = 0;
    int error = 0;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || identity(AT_FDCWD, "/proc", &proc) < 0 || identity(fd, "", &info) < 0) {
        error = errno;
    } else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISDIR(proc.stx_mode) ||
            !S_ISREG(info.stx_mode) || !same_mount(&proc, &info)) error = EXDEV;
    while (!error && used < scratch.text_capacity) {
        ssize_t got = read(fd, scratch.text + used, scratch.text_capacity - used);
        if (got < 0) error = errno;
        else if (!got) break;
        else used += (size_t)got;
    }
    close_temp(owner, fd);
    if (error || owner->close_error) return refuse(error ? error : owner->close_error);
    if (!used || used == scratch.text_capacity ||
            gpv_parse_mountinfo(scratch.text, used, scratch.rows, scratch.row_capacity, count) != GPV_OK) {
        return refuse(EPROTO);
    }
    return 0;
}

int guest_tree_file_erofs_attach(struct guest_tree_file_erofs_attachment *owner,
        const struct guest_tree_file_erofs_attach_inputs *input,
        struct guest_tree_mount_scratch before, struct guest_tree_mount_scratch after) {
    struct statx stage, held_stage, covered, named, detached, detached_tree;
    struct statx now_stage, backing, tree;
    size_t old_count, new_count;

    if (!owner || !input || !valid_scratch(before) || !valid_scratch(after) ||
            before.text == after.text || before.rows == after.rows ||
            owner->state != GUEST_TREE_FILE_EROFS_ATTACH_EMPTY || owner->source_pid ||
            owner->stage_fd != -1 || owner->covered_fd != -1 || owner->mount_fd != -1 ||
            owner->detached_tree_fd != -1 || owner->backing_fd != -1 || owner->tree_fd != -1 ||
            owner->close_error || owner->backing_mount_id || owner->expected_mount.id ||
            owner->expected_mount.major || owner->expected_mount.minor ||
            owner->expected_root_inode || owner->expected_tree_inode) return refuse(EINVAL);
    if (getpid() != gettid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_relaxed)) return refuse(EALREADY);
    owner->source_pid = getpid();
    owner->state = GUEST_TREE_FILE_EROFS_ATTACH_STARTED;
    if (namespace_current(input) < 0) return -1;
    owner->mount_fd = fcntl(input->detached_mount_fd, F_DUPFD_CLOEXEC, 3);
    if (owner->mount_fd < 0 || erofs_directory(owner->mount_fd, &detached) < 0) return -1;
    owner->detached_tree_fd = openat(owner->mount_fd, "tree", DIRECTORY);
    if (owner->detached_tree_fd < 0 || erofs_directory(owner->detached_tree_fd, &detached_tree) < 0) return -1;
    if (!same_mount(&detached, &detached_tree) || detached.stx_ino == detached_tree.stx_ino) return refuse(EXDEV);

    owner->stage_fd = open_stage(owner, &stage);
    if (owner->stage_fd < 0 || identity(input->stage_fd, "", &held_stage) < 0) return -1;
    if (!same_directory(&stage, &held_stage)) return refuse(ESTALE);
    const struct guest_tree_mount_identity stage_id = mount_identity(&stage);
    const struct guest_tree_mount_identity erofs_id = mount_identity(&detached);
    if (read_rows(owner, before, &old_count) < 0) return -1;
    if (!before_matches(before.rows, old_count, stage_id, erofs_id)) return refuse(EXDEV);
    if (identity(owner->stage_fd, "backing", &named) < 0) return -1;
    if (!root_directory(&named) || !same_mount(&stage, &named) ||
            stage.stx_ino == named.stx_ino || named.stx_nlink != 2) return refuse(EXDEV);
    owner->covered_fd = openat(owner->stage_fd, "backing", DIRECTORY);
    if (owner->covered_fd < 0 || identity(owner->covered_fd, "", &covered) < 0) return -1;
    if (!same_directory(&covered, &named)) return refuse(ESTALE);
    if (empty_target(owner, &covered) < 0 || identity(owner->stage_fd, "backing", &named) < 0 ||
            namespace_current(input) < 0) return -1;
    if (!same_directory(&covered, &named)) return refuse(ESTALE);

    owner->expected_mount = erofs_id;
    owner->expected_root_inode = detached.stx_ino;
    owner->expected_tree_inode = detached_tree.stx_ino;
    owner->state = GUEST_TREE_FILE_EROFS_MOVE_ATTEMPTED;
    if (syscall(SYS_move_mount, owner->mount_fd, "", owner->covered_fd, "",
                MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) return -1;
    owner->state = GUEST_TREE_FILE_EROFS_MOVE_RETURNED;

    int reopened_stage = open_stage(owner, &now_stage);
    if (reopened_stage < 0) return -1;
    close_temp(owner, reopened_stage);
    if (owner->close_error) return refuse(owner->close_error);
    if (!same_directory(&stage, &now_stage)) return refuse(ESTALE);
    owner->backing_fd = openat(owner->stage_fd, "backing", DIRECTORY);
    if (owner->backing_fd < 0 || erofs_directory(owner->backing_fd, &backing) < 0) return -1;
    owner->tree_fd = openat(owner->backing_fd, "tree", DIRECTORY);
    if (owner->tree_fd < 0 || erofs_directory(owner->tree_fd, &tree) < 0 ||
            identity(owner->stage_fd, "backing", &named) < 0) return -1;
    if (!same_directory(&detached, &backing) || !same_directory(&backing, &named) ||
            !same_directory(&detached_tree, &tree) || !same_mount(&backing, &tree)) return refuse(EXDEV);
    if (identity(owner->backing_fd, "tree", &named) < 0 ||
            read_rows(owner, after, &new_count) < 0 || namespace_current(input) < 0) return -1;
    if (!same_directory(&tree, &named) ||
            !after_matches(before.rows, old_count, after.rows, new_count, stage_id, erofs_id)) return refuse(EXDEV);

    owner->backing_mount_id = backing.stx_mnt_id;
    owner->state = GUEST_TREE_FILE_EROFS_BACKING_HELD;
    return 0;
}
