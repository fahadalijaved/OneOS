#define _GNU_SOURCE
#include "guest_zygote_null_owner.h"

#include "guest_readback_identity.h"

#include <linux/magic.h>
#include <stdio.h>
#include <string.h>
#include <sys/statfs.h>
#include <unistd.h>

enum { DEV, NULL_PATH, PROC, PROCESS, FDS, SCRATCH_COUNT };
enum { FIRST_RETAINED = 5 };
#define PATH_FLAGS (O_PATH | O_NOFOLLOW | O_CLOEXEC)
#define DIRECTORY_FLAGS (PATH_FLAGS | O_DIRECTORY)

_Static_assert(SCRATCH_COUNT == sizeof(((struct guest_zygote_null_owner *)0)->scratch) / sizeof(int),
        "Every scratch FD has an ownership slot");

static int check_cloexec(int fd) {
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    return flags & FD_CLOEXEC ? 0 : guest_readback_refuse(EPERM);
}

static int check_slots(const struct guest_zygote_slot_owner *slots) {
    if (slots->state != GUEST_ZYGOTE_SLOTS_HELD || slots->close_error || !slots->inode)
        return guest_readback_refuse(ESTALE);
    for (int fd = 0; fd < FIRST_RETAINED; ++fd) {
        if (slots->reserved[fd] != fd) return guest_readback_refuse(ESTALE);
        struct stat node;
        if (check_cloexec(fd) < 0 || fstat(fd, &node) < 0) return -1;
        int status = fcntl(fd, F_GETFL);
        if (status < 0) return -1;
        int expected = fd == 1 ? O_WRONLY : O_RDONLY;
        if (!S_ISFIFO(node.st_mode) || node.st_dev != slots->device || node.st_ino != slots->inode
                || (status & (O_PATH | O_ACCMODE)) != expected) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static int joined_node(int parent, const char *name, int fd, struct statx *held) {
    struct statx named;
    if (guest_readback_stat(fd, "", held) < 0 || guest_readback_stat(parent, name, &named) < 0) return -1;
    return guest_readback_same_node(held, &named) ? 0 : guest_readback_refuse(ESTALE);
}

static int root_node(int fd, uint64_t mount_id, struct statx *root) {
    if (check_cloexec(fd) < 0 || joined_node(AT_FDCWD, "/", fd, root) < 0) return -1;
    return S_ISDIR(root->stx_mode) && root->stx_mnt_id == mount_id ? 0 : guest_readback_refuse(EXDEV);
}

static int null_node(int dev, int fd, const struct statx *directory, struct statx *node) {
    if (joined_node(dev, "null", fd, node) < 0) return -1;
    if (!guest_readback_same_mount(directory, node)) return guest_readback_refuse(EXDEV);
    return S_ISCHR(node->stx_mode) && node->stx_rdev_major == 1 && node->stx_rdev_minor == 3
            ? 0 : guest_readback_refuse(ENODEV);
}

static int open_owned(int parent, const char *name, int flags, int *slot) {
    *slot = openat(parent, name, flags);
    if (*slot < 0) return -1;
    if (*slot < FIRST_RETAINED) return guest_readback_refuse(ESTALE);
    return check_cloexec(*slot);
}

static int proc_link(int fd, const char *name, const struct statx *proc, struct statx *link) {
    if (guest_readback_stat(fd, name, link) < 0) return -1;
    return S_ISLNK(link->stx_mode) && guest_readback_same_mount(proc, link)
            ? 0 : guest_readback_refuse(EXDEV);
}

static int proc_directory(int parent, const char *name, int fd, const struct statx *proc) {
    struct statx directory;
    if (joined_node(parent, name, fd, &directory) < 0) return -1;
    return S_ISDIR(directory.stx_mode) && guest_readback_same_mount(proc, &directory)
            ? 0 : guest_readback_refuse(EXDEV);
}

static int reopen_null(int inherited_root, struct guest_zygote_null_owner *owner) {
    char pid[24], number[24], self[24];
    int *fd = owner->scratch;
    int pid_length = snprintf(pid, sizeof(pid), "%ld", (long)getpid());
    int number_length = snprintf(number, sizeof(number), "%d", fd[NULL_PATH]);
    if (pid_length <= 0 || (size_t)pid_length >= sizeof(pid)
            || number_length <= 0 || (size_t)number_length >= sizeof(number))
        return guest_readback_refuse(EOVERFLOW);

    struct statfs filesystem;
    struct statx proc, self_link, before, after;
    if (open_owned(inherited_root, "proc", DIRECTORY_FLAGS, &fd[PROC]) < 0
            || fstatfs(fd[PROC], &filesystem) < 0 || joined_node(inherited_root, "proc", fd[PROC], &proc) < 0)
        return -1;
    if ((unsigned long)filesystem.f_type != PROC_SUPER_MAGIC || proc.stx_ino != 1 || !S_ISDIR(proc.stx_mode))
        return guest_readback_refuse(EXDEV);
    if (proc_link(fd[PROC], "self", &proc, &self_link) < 0) return -1;
    ssize_t length = readlinkat(fd[PROC], "self", self, sizeof(self));
    if (length < 0) return -1;
    if (length != pid_length || memcmp(self, pid, (size_t)pid_length)) return guest_readback_refuse(EXDEV);
    if (open_owned(fd[PROC], pid, DIRECTORY_FLAGS, &fd[PROCESS]) < 0
            || proc_directory(fd[PROC], pid, fd[PROCESS], &proc) < 0
            || open_owned(fd[PROCESS], "fd", DIRECTORY_FLAGS, &fd[FDS]) < 0
            || proc_directory(fd[PROCESS], "fd", fd[FDS], &proc) < 0
            || proc_link(fd[FDS], number, &proc, &before) < 0) return -1;

    /* Follow only the verified procfs link for the held O_PATH null FD. */
    if (open_owned(fd[FDS], number, O_RDWR | O_CLOEXEC, &owner->fd) < 0
            || proc_link(fd[FDS], number, &proc, &after) < 0) return -1;
    return guest_readback_same_node(&before, &after) ? 0 : guest_readback_refuse(ESTALE);
}

static void close_owned(int *slot, struct guest_zygote_null_owner *owner) {
    int fd = *slot;
    *slot = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error)
        owner->close_error = errno ? errno : EIO;
}

static void close_scratch(struct guest_zygote_null_owner *owner) {
    for (int i = SCRATCH_COUNT; i > 0; --i) close_owned(&owner->scratch[i - 1], owner);
}

int guest_zygote_null_acquire(int inherited_root_fd, uint64_t mount_id,
        const struct guest_zygote_slot_owner *slots, struct guest_zygote_null_owner *owner) {
    if (inherited_root_fd < FIRST_RETAINED || !mount_id || !slots || !owner)
        return guest_readback_refuse(EINVAL);
    if (owner->state != GUEST_ZYGOTE_NULL_NEW) return guest_readback_refuse(EALREADY);
    struct statx root, dev, path, current, readable;
    if (check_slots(slots) < 0 || root_node(inherited_root_fd, mount_id, &root) < 0) return -1;

    *owner = (struct guest_zygote_null_owner) {
        .state = GUEST_ZYGOTE_NULL_ACQUIRING, .fd = -1, .scratch = {-1, -1, -1, -1, -1},
    };
    int *fd = owner->scratch;
    if (open_owned(inherited_root_fd, "dev", DIRECTORY_FLAGS, &fd[DEV]) < 0
            || joined_node(inherited_root_fd, "dev", fd[DEV], &dev) < 0
            || open_owned(fd[DEV], "null", PATH_FLAGS, &fd[NULL_PATH]) < 0
            || null_node(fd[DEV], fd[NULL_PATH], &dev, &path) < 0
            || reopen_null(inherited_root_fd, owner) < 0
            || null_node(fd[DEV], owner->fd, &dev, &readable) < 0) goto retire;
    if (!guest_readback_same_node(&path, &readable)) { errno = ESTALE; goto retire; }
    int status = fcntl(owner->fd, F_GETFL);
    if (status < 0) goto retire;
    if ((status & (O_PATH | O_ACCMODE)) != O_RDWR) { errno = EPERM; goto retire; }
    if (joined_node(inherited_root_fd, "dev", fd[DEV], &current) < 0) goto retire;
    if (!guest_readback_same_node(&dev, &current)) { errno = ESTALE; goto retire; }
    if (root_node(inherited_root_fd, mount_id, &current) < 0) goto retire;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto retire; }
    if (check_slots(slots) < 0) goto retire;

    close_scratch(owner);
    if (owner->close_error) { errno = owner->close_error; goto retire; }
    owner->state = GUEST_ZYGOTE_NULL_READY;
    return 0;

retire: {
    int primary = errno ? errno : EIO;
    owner->state = GUEST_ZYGOTE_NULL_RETIRED;
    close_scratch(owner);
    return guest_readback_refuse(primary);
}
}

int guest_zygote_null_close(struct guest_zygote_null_owner *owner) {
    if (!owner) return guest_readback_refuse(EINVAL);
    if (owner->state == GUEST_ZYGOTE_NULL_CLOSED) return 0;
    if (owner->state != GUEST_ZYGOTE_NULL_READY && owner->state != GUEST_ZYGOTE_NULL_RETIRED)
        return guest_readback_refuse(EBUSY);
    close_scratch(owner);
    close_owned(&owner->fd, owner);
    if (owner->close_error) {
        owner->state = GUEST_ZYGOTE_NULL_RETIRED;
        return guest_readback_refuse(owner->close_error);
    }
    owner->state = GUEST_ZYGOTE_NULL_CLOSED;
    return 0;
}
