#define _GNU_SOURCE
#include "guest_tree_stage_namespace.h"

#include "guest_private_view_mountinfo.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MNT_ID | STATX_INO)

struct gtsn_owner {
    pid_t pid;
    int initial_fd, current_fd;
    struct stat initial, current;
    struct statx proc;
    int ready, error;
};

struct proc_view {
    int root, process;
    struct statx id;
};

static struct gtsn_owner one = {.initial_fd = -1, .current_fd = -1};
static atomic_flag active = ATOMIC_FLAG_INIT;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int lock(void) {
    if (getuid() || geteuid() || getpid() != gettid()) return refuse(EPERM);
    if (atomic_flag_test_and_set_explicit(&active, memory_order_acquire)) return refuse(EBUSY);
    return 0;
}

static void unlock(void) {
    atomic_flag_clear_explicit(&active, memory_order_release);
}

static int lock_owner(struct gtsn_owner *owner) {
    if (lock() < 0) return -1;
    if (owner == &one && one.pid == getpid()) return 0;
    unlock();
    return refuse(EINVAL);
}

static void poison(struct gtsn_owner *owner) {
    if (!owner->error) owner->error = errno ? errno : EIO;
    owner->ready = 0;
}

static void close_cell(struct gtsn_owner *owner, int *cell) {
    int fd = *cell, saved = errno;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0) poison(owner);
    errno = saved;
}

static int file_system(int fd, unsigned long magic) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == magic ? 0 : refuse(EXDEV);
}

static int identify(int dir, const char *name, struct statx *id) {
    int flags = LOOKUP | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(dir, name, flags, ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_mnt_id && id->stx_ino ? 0 : refuse(EXDEV);
}

static int same_device(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return same_device(a, b) && a->stx_mnt_id == b->stx_mnt_id;
}

static int proc_object(int dir, const char *name, const struct proc_view *proc, unsigned type, struct statx *id) {
    if (identify(dir, name, id) < 0) return -1;
    return same_mount(id, &proc->id) && (id->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int proc_still_named(const struct proc_view *proc) {
    struct statx named;
    if (proc_object(AT_FDCWD, "/proc", proc, S_IFDIR, &named) < 0) return -1;
    return named.stx_ino == proc->id.stx_ino ? 0 : refuse(EXDEV);
}

static int only_thread(struct gtsn_owner *owner, const struct proc_view *proc, const char *pid) {
    struct statx id;
    int fd = openat(proc->process, "task", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int result = -1;
    if (proc_object(fd, "", proc, S_IFDIR, &id) < 0) goto done;
    DIR *tasks = fdopendir(fd);
    if (!tasks) goto done;
    fd = -1; /* transferred to the stream */
    int seen = 0;
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(tasks);
        if (!entry) {
            if (!errno) result = seen ? 0 : refuse(ESRCH);
            break;
        }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        if (seen || strcmp(entry->d_name, pid)) {
            result = refuse(EBUSY);
            break;
        }
        seen = 1;
    }
    int saved = errno;
    if (closedir(tasks) < 0) poison(owner);
    errno = saved;
done:
    close_cell(owner, &fd);
    return owner->error ? refuse(owner->error) : result;
}

static int open_proc(struct gtsn_owner *owner, struct proc_view *proc) {
    struct statx self_id, process_id;
    char pid[32], self[32];
    int length = snprintf(pid, sizeof(pid), "%ld", (long)owner->pid);
    if (length <= 0 || (size_t)length >= sizeof(pid)) return refuse(EINVAL);
    proc->root = open("/proc", DIRECTORY);
    if (proc->root < 0 || file_system(proc->root, PROC_SUPER_MAGIC) < 0
            || identify(proc->root, "", &proc->id) < 0) return -1;
    if (!S_ISDIR(proc->id.stx_mode)) return refuse(EXDEV);
    if (proc_object(proc->root, "self", proc, S_IFLNK, &self_id) < 0) return -1;
    ssize_t got = readlinkat(proc->root, "self", self, sizeof(self));
    if (got < 0) return -1;
    if (got != length || memcmp(self, pid, (size_t)length)) return refuse(EXDEV);
    proc->process = openat(proc->root, pid, DIRECTORY);
    if (proc->process < 0 || proc_object(proc->process, "", proc, S_IFDIR, &process_id) < 0) return -1;
    return only_thread(owner, proc, pid);
}

static int ns_identity(int fd, struct stat *id) {
    if (file_system(fd, NSFS_MAGIC) < 0 || fstat(fd, id) < 0) return -1;
    if (!id->st_ino) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int capture_ns(struct gtsn_owner *owner, const struct proc_view *proc, int *fd, struct stat *id) {
    struct statx directory_id, before, after;
    struct stat named;
    int directory = openat(proc->process, "ns", DIRECTORY);
    if (directory < 0) return -1;
    int result = -1;
    if (proc_object(directory, "", proc, S_IFDIR, &directory_id) < 0
            || proc_object(directory, "mnt", proc, S_IFLNK, &before) < 0) goto done;
    /* This one kernel procfs link is deliberately followed. */
    *fd = openat(directory, "mnt", O_RDONLY | O_CLOEXEC);
    if (*fd < 0 || ns_identity(*fd, id) < 0 || fstatat(directory, "mnt", &named, 0) < 0
            || proc_object(directory, "mnt", proc, S_IFLNK, &after) < 0) goto done;
    if (!same_ns(id, &named) || before.stx_ino != after.stx_ino) {
        errno = EXDEV;
        goto done;
    }
    result = 0;
done:
    close_cell(owner, &directory);
    return owner->error ? refuse(owner->error) : result;
}

static int private_table(const struct gpv_mount_row *rows, size_t count,
                         const struct statx *root, const struct statx *proc) {
    const struct gpv_mount_row *root_row = gpv_mount_by_id(rows, count, root->stx_mnt_id);
    const struct gpv_mount_row *proc_row = gpv_mount_by_id(rows, count, proc->stx_mnt_id);
    if (!root_row || strcmp(root_row->point, "/") || root_row->major != root->stx_dev_major
            || root_row->minor != root->stx_dev_minor || !proc_row || strcmp(proc_row->root, "/")
            || strcmp(proc_row->point, "/proc") || strcmp(proc_row->type, "proc")
            || proc_row->major != proc->stx_dev_major || proc_row->minor != proc->stx_dev_minor) return 0;
    for (size_t i = 0; i < count; ++i) {
        if (rows[i].shared || rows[i].master || rows[i].propagate || rows[i].unbindable) return 0;
    }
    return 1;
}

static int read_private_table(struct gtsn_owner *owner, const struct proc_view *proc) {
    struct statx file, root;
    size_t used = 0, count;
    char *text = NULL;
    struct gpv_mount_row *rows = NULL;
    int fd = openat(proc->process, "mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int result = -1;
    if (proc_object(fd, "", proc, S_IFREG, &file) < 0 || file_system(fd, PROC_SUPER_MAGIC) < 0
            || identify(AT_FDCWD, "/", &root) < 0) goto done;
    if (!S_ISDIR(root.stx_mode)) {
        errno = EXDEV;
        goto done;
    }
    text = malloc(GPV_MOUNTINFO_MAX_BYTES + 1U);
    rows = malloc(sizeof(*rows) * GPV_MOUNTINFO_MAX_ROWS);
    if (!text || !rows) {
        errno = ENOMEM;
        goto done;
    }
    while (used <= GPV_MOUNTINFO_MAX_BYTES) {
        ssize_t got = read(fd, text + used, GPV_MOUNTINFO_MAX_BYTES + 1U - used);
        if (got < 0) goto done;
        if (!got) break;
        used += (size_t)got;
    }
    if (gpv_parse_mountinfo(text, used, rows, GPV_MOUNTINFO_MAX_ROWS, &count) != GPV_OK)
        errno = EPROTO;
    else if (!private_table(rows, count, &root, &proc->id))
        errno = EXDEV;
    else
        result = 0;
done:
    close_cell(owner, &fd);
    free(rows);
    free(text);
    return owner->error ? refuse(owner->error) : result;
}

static int sample(struct gtsn_owner *owner, int *fd, struct stat *ns, struct statx *proc_id, int require_private) {
    struct proc_view proc = {.root = -1, .process = -1};
    int result = -1;
    if (open_proc(owner, &proc) < 0 || capture_ns(owner, &proc, fd, ns) < 0) goto done;
    if (require_private && read_private_table(owner, &proc) < 0) goto done;
    if (proc_still_named(&proc) < 0) goto done;
    *proc_id = proc.id;
    result = 0;
done:
    close_cell(owner, &proc.process);
    close_cell(owner, &proc.root);
    return owner->error ? refuse(owner->error) : result;
}

static int check_current(struct gtsn_owner *owner) {
    struct stat initial, current, sampled;
    struct statx proc;
    int fresh = -1;
    if (ns_identity(owner->initial_fd, &initial) < 0 || ns_identity(owner->current_fd, &current) < 0) return -1;
    if (!same_ns(&initial, &owner->initial) || !same_ns(&current, &owner->current)
            || same_ns(&initial, &current)) return refuse(EXDEV);
    int result = sample(owner, &fresh, &sampled, &proc, 1);
    close_cell(owner, &fresh);
    if (owner->error) return refuse(owner->error);
    if (result < 0) return -1;
    return same_ns(&sampled, &current) && same_mount(&proc, &owner->proc)
            && proc.stx_ino == owner->proc.stx_ino ? 0 : refuse(EXDEV);
}

int gtsn_enter(struct gtsn_owner **out) {
    if (!out || *out) return refuse(EINVAL);
    if (lock() < 0) return -1;
    if (one.pid) {
        unlock();
        return refuse(EALREADY);
    }
    one.pid = getpid();
    *out = &one;
    struct statx initial_proc;
    int result = -1;
    if (sample(&one, &one.initial_fd, &one.initial, &initial_proc, 0) < 0) goto done;
    if (unshare(CLONE_NEWNS) < 0
            || sample(&one, &one.current_fd, &one.current, &one.proc, 0) < 0) goto uncertain;
    /* A cloned proc mount may receive a new mount ID but keeps its root identity. */
    if (same_ns(&one.initial, &one.current) || !same_device(&initial_proc, &one.proc)
            || initial_proc.stx_ino != one.proc.stx_ino) {
        errno = EXDEV;
        goto uncertain;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0 || check_current(&one) < 0) goto uncertain;
    one.ready = 1;
    result = 0;
    goto done;
uncertain:
    poison(&one);
done:
    unlock();
    return one.error ? refuse(one.error) : result;
}

int gtsn_borrow(struct gtsn_owner *owner, struct gtsn_witnesses *out) {
    if (!out) return refuse(EINVAL);
    *out = (struct gtsn_witnesses){-1, -1};
    if (lock_owner(owner) < 0) return -1;
    int result = -1;
    if (!owner->ready) errno = owner->error ? owner->error : EPERM;
    else if (check_current(owner) < 0) poison(owner);
    else {
        *out = (struct gtsn_witnesses){owner->initial_fd, owner->current_fd};
        result = 0;
    }
    unlock();
    return result;
}

int gtsn_close_local(struct gtsn_owner *owner) {
    if (lock_owner(owner) < 0) return -1;
    owner->ready = 0;
    close_cell(owner, &owner->current_fd);
    close_cell(owner, &owner->initial_fd);
    int error = owner->error;
    unlock();
    return error ? refuse(error) : 0;
}
