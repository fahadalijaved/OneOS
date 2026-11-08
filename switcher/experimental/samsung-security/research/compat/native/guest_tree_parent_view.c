#define _GNU_SOURCE
#include "guest_tree_parent_view.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_owned(int *cell, int *primary, int *close_error) {
    int fd = *cell;
    *cell = -1;
    if (fd < 0 || close(fd) == 0) return;
    if (!*close_error) *close_error = errno;
    if (!*primary) *primary = errno;
}

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : refuse(EINVAL);
}

static int mount_namespace(int fd, struct stat *identity) {
    struct statfs fs;
    if (cloexec(fd) < 0 || fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !identity->st_ino) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int namespace_equal(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int statx_type(int fd, const char *name, unsigned type, unsigned mask,
                      struct statx *result) {
    int flags = AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW | (*name ? 0 : AT_EMPTY_PATH);
    mask |= STATX_TYPE | STATX_MNT_ID;
    if (statx(fd, name, flags, mask, result) < 0) return -1;
    if ((result->stx_mask & mask) != mask || !result->stx_mnt_id ||
        (result->stx_mode & S_IFMT) != type) return refuse(EPROTO);
    return 0;
}

static int same_device(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int proc_member(int fd, const char *name, unsigned type, const struct statx *proc) {
    struct statx result;
    if (statx_type(fd, name, type, 0, &result) < 0) return -1;
    if (result.stx_mnt_id != proc->stx_mnt_id || !same_device(&result, proc))
        return refuse(EXDEV);
    return 0;
}

/* Open the kernel link only after checking the directory and link itself
 * against the held proc mount. The followed FD must be the same nsfs object. */
static int check_task_namespace(int task, const struct statx *proc,
                                const struct stat *expected, int *close_error) {
    struct stat observed;
    int failure = 0, live = -1;
    int dir = openat(task, "ns", O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dir < 0) return -1;
    if (proc_member(dir, "", S_IFDIR, proc) < 0 || proc_member(dir, "mnt", S_IFLNK, proc) < 0)
        failure = errno;
    else {
        live = openat(dir, "mnt", O_RDONLY | O_CLOEXEC);
        if (live < 0 || mount_namespace(live, &observed) < 0) failure = errno;
        else if (!namespace_equal(expected, &observed)) failure = ESTALE;
    }
    close_owned(&live, &failure, close_error);
    close_owned(&dir, &failure, close_error);
    return failure ? refuse(failure) : 0;
}

static int read_table(int task, const struct statx *proc, struct gpv_mount_row **rows,
                      size_t *count, int *close_error) {
    const size_t limit = GPV_MOUNTINFO_MAX_BYTES;
    size_t used = 0, lines = 0;
    char *text = NULL;
    int failure = 0;
    int fd = openat(task, "mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (proc_member(fd, "", S_IFREG, proc) < 0) failure = errno;
    else if (!(text = malloc(limit + 1))) failure = ENOMEM;
    while (!failure && used <= limit) {
        ssize_t got = read(fd, text + used, limit + 1 - used);
        if (got < 0) failure = errno;
        else if (got == 0) break;
        else if ((size_t)got > limit + 1 - used) failure = EIO;
        else used += (size_t)got;
    }
    close_owned(&fd, &failure, close_error);
    if (!failure && used > limit) failure = E2BIG;
    if (!failure) {
        for (size_t i = 0; i < used; ++i)
            if (text[i] == '\n') ++lines;
        if (!lines) failure = EPROTO;
        else if (lines > GPV_MOUNTINFO_MAX_ROWS) failure = E2BIG;
        else if (!(*rows = calloc(lines, sizeof(**rows)))) failure = ENOMEM;
        else {
            int result = gpv_parse_mountinfo(text, used, *rows, lines, count);
            if (result != GPV_OK) failure = result == GPV_LIMIT ? E2BIG : EPROTO;
        }
    }
    free(text);
    return failure ? refuse(failure) : 0;
}

static int tree_directory(int fd, struct statx *identity) {
    const unsigned mask = STATX_MODE | STATX_INO | STATX_UID | STATX_GID |
                          STATX_NLINK | STATX_MTIME | STATX_CTIME;
    if (cloexec(fd) < 0 || statx_type(fd, "", S_IFDIR, mask, identity) < 0) return -1;
    if (!identity->stx_ino || !identity->stx_nlink || identity->stx_uid ||
        (identity->stx_mode & 0022)) return refuse(EPERM);
    return 0;
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return same_device(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
           a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink &&
           a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec &&
           a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int row_device(const struct gpv_mount_row *row, const struct statx *value) {
    return row && row->major == value->stx_dev_major && row->minor == value->stx_dev_minor;
}

static int below(const char *path, const char *parent) {
    size_t n = strlen(parent);
    if (n == 1 && parent[0] == '/') return path[0] == '/';
    return strncmp(path, parent, n) == 0 && (path[n] == '/' || path[n] == 0);
}

static int source_row(const struct gpv_mount_row *rows, size_t count,
                      const struct statx *identity, struct gpv_mount_row *out) {
    const struct gpv_mount_row *row = gpv_mount_by_id(rows, count, identity->stx_mnt_id);
    if (!row_device(row, identity) || !below(GUEST_TREE_SOURCE_PATH, row->point)
        || strcmp(GUEST_TREE_SOURCE_PATH, row->point) == 0) return refuse(ESTALE);
    for (size_t i = 0; i < count; ++i)
        if (&rows[i] != row && below(GUEST_TREE_SOURCE_PATH, rows[i].point)
                && below(rows[i].point, row->point)) return refuse(ESTALE);
    *out = *row;
    return 0;
}

static int private_bindable(const struct gpv_mount_row *row) {
    return !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static size_t option_length(const char *token) {
    const char *end = strchr(token, ',');
    return end ? (size_t)(end - token) : strlen(token);
}

static int has_option(const char *options, const char *wanted, size_t size) {
    while (*options) {
        size_t n = option_length(options);
        if (n == size && memcmp(options, wanted, n) == 0) return 1;
        options += n;
        if (*options) ++options;
    }
    return 0;
}

static int other_options_in(const char *options, const char *expected) {
    while (*options) {
        size_t n = option_length(options);
        int changed = (n == 2 && (!memcmp(options, "ro", 2) || !memcmp(options, "rw", 2)))
                || (n == 6 && !memcmp(options, "nosuid", 6))
                || (n == 5 && !memcmp(options, "nodev", 5));
        if (!changed && !has_option(expected, options, n)) return 0;
        options += n;
        if (*options) ++options;
    }
    return 1;
}

static int projected_root(const struct gpv_mount_row *source, const struct gpv_mount_row *root) {
    const char *suffix = GUEST_TREE_SOURCE_PATH;
    size_t prefix = strlen(source->root);
    if (strcmp(source->point, "/") != 0) suffix += strlen(source->point);
    if (strcmp(source->root, "/") == 0) prefix = 0;
    return strlen(root->root) == prefix + strlen(suffix)
            && memcmp(root->root, source->root, prefix) == 0
            && strcmp(root->root + prefix, suffix) == 0;
}

static int scaffold_stack(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *scaffold, size_t at_mnt) {
    for (size_t i = 1; i <= at_mnt; ++i) {
        scaffold = gpv_mount_by_id(rows, count, scaffold->parent);
        if (!scaffold) return 0;
        if (strcmp(scaffold->point, "/mnt") != 0)
            return i == at_mnt && strcmp(scaffold->point, "/") == 0;
    }
    return 0;
}

static int check_child_root(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *source, const struct statx *identity) {
    const struct gpv_mount_row *root = gpv_mount_by_id(rows, count, identity->stx_mnt_id);
    size_t scaffold_rows = 0;
    if (!row_device(root, identity) || strcmp(root->point, GUEST_TREE_TARGET_PATH) != 0 ||
        !private_bindable(root) || strcmp(root->type, source->type) != 0 ||
        strcmp(root->source, source->source) != 0 ||
        strcmp(root->super_options, source->super_options) != 0 || !projected_root(source, root) ||
        !has_option(root->options, "ro", 2) || !has_option(root->options, "nosuid", 6) ||
        !has_option(root->options, "nodev", 5) ||
        !other_options_in(source->options, root->options) ||
        !other_options_in(root->options, source->options)) return refuse(ESTALE);
    const struct gpv_mount_row *scaffold = gpv_mount_by_id(rows, count, root->parent);
    if (!scaffold || strcmp(scaffold->point, "/mnt") || strcmp(scaffold->root, "/") ||
        strcmp(scaffold->type, "tmpfs") || !private_bindable(scaffold) ||
        (scaffold->major == root->major && scaffold->minor == root->minor)) return refuse(ESTALE);
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *row = &rows[i];
        if (strcmp(row->point, "/mnt") == 0) ++scaffold_rows;
        if (row != root && below(row->point, "/mnt/gvi") &&
            (!below(row->point, GUEST_TREE_TARGET_PATH) ||
             strcmp(row->point, GUEST_TREE_TARGET_PATH) == 0)) return refuse(ESTALE);
    }
    return scaffold_stack(rows, count, scaffold, scaffold_rows) ? 0 : refuse(ESTALE);
}

int guest_tree_parent_view_inspect(pid_t child, int source_fd, int parent_namespace_fd,
        int child_namespace_fd, int child_root_fd, uint64_t claimed_namespace_dev,
        uint64_t claimed_namespace_ino, uint64_t claimed_root_mount_id,
        guest_tree_parent_inspector inspector, void *context, int *close_error) {
    int failure = 0, proc = -1, self = -1, task = -1, live_root = -1;
    char pid[32];
    struct stat parent_ns, child_ns;
    struct statfs filesystem;
    struct statvfs flags;
    struct statx proc_identity, source, root, again;
    struct gpv_mount_row backing, *parent_rows = NULL, *child_rows = NULL;
    size_t parent_count, child_count;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV;

    if (!close_error || child <= 1 || child == getpid() || !claimed_root_mount_id ||
        !claimed_namespace_ino) return refuse(EINVAL);
    if (*close_error) return refuse(*close_error);
    if (mount_namespace(parent_namespace_fd, &parent_ns) < 0 ||
        mount_namespace(child_namespace_fd, &child_ns) < 0 ||
        tree_directory(source_fd, &source) < 0 || tree_directory(child_root_fd, &root) < 0) return -1;
    if (namespace_equal(&parent_ns, &child_ns) || (uint64_t)child_ns.st_dev != claimed_namespace_dev ||
        (uint64_t)child_ns.st_ino != claimed_namespace_ino || root.stx_mnt_id != claimed_root_mount_id ||
        source.stx_mnt_id == root.stx_mnt_id || !same_directory(&source, &root)) return refuse(ESTALE);
    int length = snprintf(pid, sizeof(pid), "%ld", (long)child);
    if (length < 0 || (size_t)length >= sizeof(pid)) return refuse(EOVERFLOW);
    proc = open("/proc", O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (proc < 0) return -1;
    if (fstatfs(proc, &filesystem) < 0 || statx_type(proc, "", S_IFDIR, 0, &proc_identity) < 0) goto failed;
    if ((unsigned long)filesystem.f_type != PROC_SUPER_MAGIC) { errno = EXDEV; goto failed; }
    if (proc_member(proc, "self", S_IFLNK, &proc_identity) < 0) goto failed;
    self = openat(proc, "self", O_PATH | O_DIRECTORY | O_CLOEXEC);
    if (self < 0 || proc_member(self, "", S_IFDIR, &proc_identity) < 0) goto failed;
    task = openat(proc, pid, O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (task < 0 || proc_member(task, "", S_IFDIR, &proc_identity) < 0 ||
        check_task_namespace(self, &proc_identity, &parent_ns, close_error) < 0 ||
        check_task_namespace(task, &proc_identity, &child_ns, close_error) < 0 ||
        read_table(self, &proc_identity, &parent_rows, &parent_count, close_error) < 0 ||
        source_row(parent_rows, parent_count, &source, &backing) < 0) goto failed;
    if (!inspector) {
        free(parent_rows);
        parent_rows = NULL;
    }
    if (read_table(task, &proc_identity, &child_rows, &child_count, close_error) < 0 ||
        check_child_root(child_rows, child_count, &backing, &root) < 0) goto failed;
    if (inspector) {
        if (proc_member(task, "root", S_IFLNK, &proc_identity) < 0) goto failed;
        live_root = openat(task, "root", O_PATH | O_DIRECTORY | O_CLOEXEC);
        if (live_root < 0) goto failed;
        const struct guest_tree_parent_sample sample = {
            .live_child_root = live_root, .parent_rows = parent_rows, .child_rows = child_rows,
            .parent_count = parent_count, .child_count = child_count,
        };
        if (inspector(&sample, context, close_error) != 0) goto failed;
        if (*close_error) { errno = *close_error; goto failed; }
    }
    if (check_task_namespace(task, &proc_identity, &child_ns, close_error) < 0 ||
        check_task_namespace(self, &proc_identity, &parent_ns, close_error) < 0 ||
        tree_directory(source_fd, &again) < 0) goto failed;
    if (source.stx_mnt_id != again.stx_mnt_id || !same_directory(&source, &again)) {
        errno = ESTALE;
        goto failed;
    }
    if (tree_directory(child_root_fd, &again) < 0 || fstatvfs(child_root_fd, &flags) < 0) goto failed;
    if (root.stx_mnt_id != again.stx_mnt_id || !same_directory(&root, &again) ||
        (flags.f_flag & required) != required) { errno = ESTALE; goto failed; }
    goto done;

failed:
    failure = errno ? errno : EIO;
done:
    free(child_rows);
    free(parent_rows);
    close_owned(&live_root, &failure, close_error);
    close_owned(&task, &failure, close_error);
    close_owned(&self, &failure, close_error);
    close_owned(&proc, &failure, close_error);
    return failure ? refuse(failure) : 0;
}

int guest_tree_parent_view_check(pid_t child, int source_fd, int parent_namespace_fd,
        int child_namespace_fd, int child_root_fd, uint64_t claimed_namespace_dev,
        uint64_t claimed_namespace_ino, uint64_t claimed_root_mount_id,
        int *close_error) {
    return guest_tree_parent_view_inspect(child, source_fd, parent_namespace_fd, child_namespace_fd,
            child_root_fd, claimed_namespace_dev, claimed_namespace_ino, claimed_root_mount_id,
            NULL, NULL, close_error);
}
