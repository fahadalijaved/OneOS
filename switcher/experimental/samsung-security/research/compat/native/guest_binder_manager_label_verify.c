#define _GNU_SOURCE
#include "guest_binder_manager_label_verify.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdio.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/xattr.h>
#include <unistd.h>

#define SECURITY_CONTEXT "security.selinux"
#define LABEL_CAP 128U
#define ID_MASK (STATX_TYPE | STATX_MODE | STATX_INO | STATX_MNT_ID)
#define LSM_GET_SELF_ATTR_ARM64 459L
#define LSM_ATTR_CURRENT 100U
#define LSM_ID_SELINUX 101U
#define LSM_FLAG_SINGLE 1U

static const char executable_context[] = "u:object_r:servicemanager_exec:s0";
static const char binder_context[] = "u:object_r:binder_device:s0";
static const char manager_context[] = "u:r:servicemanager:s0";

struct proc_source {
    struct statx root, self_link, fd_directory;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int exact_label(const char *text, size_t count, const char *expected, size_t expected_size) {
    return count == expected_size && !memcmp(text, expected, expected_size) ? 0 : refuse(EACCES);
}

static int actor(void) {
#if defined(__aarch64__)
    /* Same selected AArch64 LSM ABI as guest_tree_property_transition. */
    struct {
        uint64_t id, flags, len, context_len;
        char context[LABEL_CAP];
    } record = {.id = LSM_ID_SELINUX};
    uint32_t size = sizeof(record);
    const size_t header = sizeof(record) - sizeof(record.context);
    uid_t ru, eu, su;
    gid_t rg, eg, sg, groups[2];
    if (gettid() != getpid()) return refuse(ECHILD);
    if (getresuid(&ru, &eu, &su) < 0 || getresgid(&rg, &eg, &sg) < 0) return -1;
    if (ru != 1000 || eu != 1000 || su != 1000 || rg != 1000 || eg != 1000 || sg != 1000) return refuse(EACCES);
    int count = getgroups(2, groups);
    if (count < 0) return -1;
    /* Stock rc uses system as the primary GID and readproc as its supplement. */
    if (count != 1 || groups[0] != 3009) return refuse(EACCES);
    long records = syscall(LSM_GET_SELF_ATTR_ARM64, LSM_ATTR_CURRENT, &record, &size, LSM_FLAG_SINGLE);
    if (records < 0) return -1;
    if (records != 1 || record.id != LSM_ID_SELINUX || record.flags || size > sizeof(record) ||
            size < header || record.len != size || record.context_len != sizeof(manager_context) ||
            size != (header + sizeof(manager_context) + 7U) / 8U * 8U) return refuse(EPROTO);
    return exact_label(record.context, (size_t)record.context_len, manager_context, sizeof(manager_context));
#else
    return refuse(EOPNOTSUPP);
#endif
}

static int node(const char *name, int flags, struct statx *result) {
    if (statx(AT_FDCWD, name, AT_NO_AUTOMOUNT | flags, ID_MASK, result) < 0) return -1;
    if ((result->stx_mask & ID_MASK) != ID_MASK || !result->stx_ino || !result->stx_mnt_id ||
            (result->stx_attributes & STATX_ATTR_AUTOMOUNT)) return refuse(EXDEV);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major &&
            a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
            a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor;
}

static int proc_source(struct proc_source *proc) {
    struct statfs fs;
    if (statfs("/proc", &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC) return refuse(EXDEV);
    if (node("/proc", AT_SYMLINK_NOFOLLOW, &proc->root) < 0 ||
            node("/proc/self", AT_SYMLINK_NOFOLLOW, &proc->self_link) < 0 ||
            node("/proc/self/fd", AT_SYMLINK_NOFOLLOW, &proc->fd_directory) < 0) return -1;
    if (!S_ISDIR(proc->root.stx_mode) || !S_ISLNK(proc->self_link.stx_mode) ||
            !S_ISDIR(proc->fd_directory.stx_mode) ||
            (proc->root.stx_attributes_mask & STATX_ATTR_MOUNT_ROOT) == 0 ||
            (proc->root.stx_attributes & STATX_ATTR_MOUNT_ROOT) == 0 ||
            !same_mount(&proc->root, &proc->self_link) || !same_mount(&proc->root, &proc->fd_directory)) {
        return refuse(EXDEV);
    }
    char wanted[24], actual[24];
    int length = snprintf(wanted, sizeof(wanted), "%ld", (long)getpid());
    if (length <= 0 || (size_t)length >= sizeof(wanted)) return refuse(EOVERFLOW);
    ssize_t got = readlink("/proc/self", actual, sizeof(actual));
    if (got < 0) return -1;
    return got == length && !memcmp(actual, wanted, (size_t)length) ? 0 : refuse(ESTALE);
}

static int proc_binder_target(const char *path, const struct proc_source *proc, const struct statx *expected) {
    struct statx link, target;
    if (node(path, AT_SYMLINK_NOFOLLOW, &link) < 0 || node(path, 0, &target) < 0) return -1;
    if (!S_ISLNK(link.stx_mode) || !same_mount(&proc->fd_directory, &link) ||
            !S_ISCHR(target.stx_mode) || !same_node(&target, expected)) return refuse(ESTALE);
    return 0;
}

static int binder_label(int fd, const struct statx *expected) {
    struct proc_source before, after;
    char path[64], label[LABEL_CAP];
    int length = snprintf(path, sizeof(path), "/proc/self/fd/%d", fd);
    if (length <= 0 || (size_t)length >= sizeof(path)) return refuse(EOVERFLOW);
    if (proc_source(&before) < 0 || proc_binder_target(path, &before, expected) < 0) return -1;
    /* getxattr follows the verified proc magic link. It doesn't open a driver
     * description. fgetxattr on the original O_PATH is not our read path. */
    ssize_t count = getxattr(path, SECURITY_CONTEXT, label, sizeof(label));
    if (count < 0 || proc_source(&after) < 0 || proc_binder_target(path, &after, expected) < 0) return -1;
    if (!same_node(&before.root, &after.root) || !same_node(&before.self_link, &after.self_link) ||
            !same_node(&before.fd_directory, &after.fd_directory)) return refuse(ESTALE);
    return exact_label(label, (size_t)count, binder_context, sizeof(binder_context));
}

int guest_binder_manager_label_verify(struct guest_binder_manager_handoff_owner *handoff) {
    struct guest_binder_manager_handoff_view before = {0}, after = {0};
    char label[LABEL_CAP];
    if (guest_binder_manager_handoff_borrow(handoff, &before) < 0 || actor() < 0) return -1;
    const int executable = before.fds[GBMH_PREEXEC_EXECUTABLE], binder = before.fds[GBMH_WITNESS_BINDER];
    ssize_t count = fgetxattr(executable, SECURITY_CONTEXT, label, sizeof(label));
    if (count < 0 || exact_label(label, (size_t)count, executable_context, sizeof(executable_context)) < 0 ||
            binder_label(binder, &handoff->entry->identities[GBME_BINDER]) < 0 || actor() < 0 ||
            guest_binder_manager_handoff_borrow(handoff, &after) < 0) return -1;
    if (after.fds != before.fds || after.argv != before.argv ||
            after.fds[GBMH_PREEXEC_EXECUTABLE] != executable || after.fds[GBMH_WITNESS_BINDER] != binder) {
        return refuse(ESTALE);
    }
    return 0;
}
