#define _GNU_SOURCE
#include "guest_zygote_parent_readback.h"

#include "guest_readback_identity.h"

#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/statfs.h>
#include <unistd.h>

enum { PROC, TASK, NS_DIR, LIVE_ROOT, LIVE_CWD, LIVE_NS, SLOTS };
#define PATH_DIRECTORY (O_PATH | O_DIRECTORY | O_CLOEXEC)
#define DIRECTORY (PATH_DIRECTORY | O_NOFOLLOW)

static int cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return (flags & FD_CLOEXEC) ? 0 : guest_readback_refuse(EPERM);
}

static int root_identity(int fd, uint64_t mount_id, struct statx *root) {
    if (cloexec(fd) < 0 || guest_readback_stat(fd, "", root) < 0) return -1;
    return S_ISDIR(root->stx_mode) && root->stx_mnt_id == mount_id ? 0 : guest_readback_refuse(EXDEV);
}

static int namespace_identity(int fd, const struct gtc_observation *admitted) {
    struct stat node;
    struct statfs fs;
    if (cloexec(fd) < 0 || fstat(fd, &node) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) return guest_readback_refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    if (type != CLONE_NEWNS) return guest_readback_refuse(EXDEV);
    return (uint64_t)node.st_dev == admitted->namespace_dev && (uint64_t)node.st_ino == admitted->namespace_inode
            ? 0 : guest_readback_refuse(ESTALE);
}

static int directory_identity(int parent, const char *name, int fd, struct statx *out) {
    struct statx named;
    if (guest_readback_stat(fd, "", out) < 0 || guest_readback_stat(parent, name, &named) < 0) return -1;
    if (!S_ISDIR(out->stx_mode)) return guest_readback_refuse(ENOTDIR);
    return guest_readback_same_node(out, &named) ? 0 : guest_readback_refuse(ESTALE);
}

static int open_directory(int parent, const char *name, int *fd, struct statx *out) {
    *fd = openat(parent, name, DIRECTORY);
    return *fd < 0 ? -1 : directory_identity(parent, name, *fd, out);
}

static int proc_link(int fd, const char *name, const struct statx *proc, struct statx *out) {
    if (guest_readback_stat(fd, name, out) < 0) return -1;
    return S_ISLNK(out->stx_mode) && guest_readback_same_mount(proc, out) ? 0 : guest_readback_refuse(EXDEV);
}

static int proc_self(int fd, const struct statx *proc) {
    char expected[24], actual[24];
    int length = snprintf(expected, sizeof(expected), "%ld", (long)getpid());
    if (length <= 0 || (size_t)length >= sizeof(expected)) return guest_readback_refuse(EOVERFLOW);
    struct statx link;
    if (proc_link(fd, "self", proc, &link) < 0) return -1;
    ssize_t got = readlinkat(fd, "self", actual, sizeof(actual));
    if (got < 0) return -1;
    return got == length && !memcmp(expected, actual, (size_t)length) ? 0 : guest_readback_refuse(EXDEV);
}

static int follow_proc_link(int parent, const char *name, int flags, const struct statx *proc, int *fd) {
    struct statx before, after;
    if (proc_link(parent, name, proc, &before) < 0) return -1;
    /* Only the caller's fixed, authenticated procfs magic links reach here. */
    *fd = openat(parent, name, flags);
    if (*fd < 0 || proc_link(parent, name, proc, &after) < 0) return -1;
    return guest_readback_same_node(&before, &after) ? 0 : guest_readback_refuse(ESTALE);
}

static int same_directory(int parent, const char *name, int fd, const struct statx *before) {
    struct statx after;
    if (directory_identity(parent, name, fd, &after) < 0) return -1;
    return guest_readback_same_node(before, &after) ? 0 : guest_readback_refuse(ESTALE);
}

static void close_owned(int *slot, int *primary, int *close_error) {
    int fd = *slot;
    *slot = -1;
    if (fd < 0 || close(fd) == 0) return;
    int error = errno ? errno : EIO;
    if (!*close_error) *close_error = error;
    if (!*primary) *primary = error;
}

int guest_zygote_parent_readback(pid_t child, int root_fd, int namespace_fd,
        const struct gtc_observation *admitted, int *close_error) {
    if (child <= 1 || child == getpid() || root_fd < 0 || namespace_fd < 0 || root_fd == namespace_fd
            || !admitted || !close_error || !admitted->namespace_dev || !admitted->namespace_inode
            || !admitted->mounts[GTC_GUEST_ROOT]) return guest_readback_refuse(EINVAL);
    if (*close_error) return guest_readback_refuse(*close_error);
    char pid[24];
    int length = snprintf(pid, sizeof(pid), "%ld", (long)child);
    if (length <= 0 || (size_t)length >= sizeof(pid)) return guest_readback_refuse(EOVERFLOW);

    uint64_t mount_id = admitted->mounts[GTC_GUEST_ROOT];
    struct statx root, current, proc, task, ns_dir;
    if (root_identity(root_fd, mount_id, &root) < 0 || namespace_identity(namespace_fd, admitted) < 0) return -1;
    int fd[SLOTS] = {-1, -1, -1, -1, -1, -1};
    int primary = 0;
    struct statfs fs;
    if (open_directory(AT_FDCWD, "/proc", &fd[PROC], &proc) < 0 || fstatfs(fd[PROC], &fs) < 0) goto failed;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || proc.stx_ino != 1) { errno = EXDEV; goto failed; }
    if (proc_self(fd[PROC], &proc) < 0 || open_directory(fd[PROC], pid, &fd[TASK], &task) < 0) goto failed;
    if (!guest_readback_same_mount(&proc, &task)) { errno = EXDEV; goto failed; }
    if (open_directory(fd[TASK], "ns", &fd[NS_DIR], &ns_dir) < 0) goto failed;
    if (!guest_readback_same_mount(&proc, &ns_dir)) { errno = EXDEV; goto failed; }

    if (follow_proc_link(fd[TASK], "root", PATH_DIRECTORY, &proc, &fd[LIVE_ROOT]) < 0
            || root_identity(fd[LIVE_ROOT], mount_id, &current) < 0) goto failed;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto failed; }
    if (follow_proc_link(fd[TASK], "cwd", PATH_DIRECTORY, &proc, &fd[LIVE_CWD]) < 0
            || root_identity(fd[LIVE_CWD], mount_id, &current) < 0) goto failed;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto failed; }
    if (follow_proc_link(fd[NS_DIR], "mnt", O_RDONLY | O_CLOEXEC, &proc, &fd[LIVE_NS]) < 0
            || namespace_identity(fd[LIVE_NS], admitted) < 0) goto failed;

    if (same_directory(AT_FDCWD, "/proc", fd[PROC], &proc) < 0
            || same_directory(fd[PROC], pid, fd[TASK], &task) < 0
            || same_directory(fd[TASK], "ns", fd[NS_DIR], &ns_dir) < 0
            || root_identity(root_fd, mount_id, &current) < 0
            || namespace_identity(namespace_fd, admitted) < 0) goto failed;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto failed; }
    goto done;

failed:
    primary = errno ? errno : EIO;
done:
    for (int i = SLOTS; i > 0; --i) close_owned(&fd[i - 1], &primary, close_error);
    return primary ? guest_readback_refuse(primary) : 0;
}
