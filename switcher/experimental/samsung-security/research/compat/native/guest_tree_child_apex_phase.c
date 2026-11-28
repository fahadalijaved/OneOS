#define _GNU_SOURCE
#include "guest_tree_child_apex_phase.h"

#include <errno.h>
#include <stdlib.h>

static struct { int entered, error; } one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int exact_status(int result) {
    return result == 0 ? 0 : refuse(result > 0 ? EPROTO : errno ? errno : EIO);
}

#ifndef GTCA_INERT
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_MNT_ID)

static int child_process(const struct guest_tree_child_apex_view *view) {
    if (getpid() != gettid() || getpid() != view->child || getppid() != view->parent
            || getuid() || geteuid() || getegid()) return refuse(EPERM);
    int signal;
    if (prctl(PR_GET_PDEATHSIG, &signal, 0L, 0L, 0L) < 0) return -1;
    return signal == SIGKILL ? 0 : refuse(EPERM);
}

static int same_ns(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int namespace_matches(int fd, const char *name, struct stat *held) {
    struct statfs fs;
    struct stat live;
    if (fstat(fd, held) < 0 || fstatfs(fd, &fs) < 0 || stat(name, &live) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !held->st_ino || !same_ns(held, &live)) return refuse(EXDEV);
    int kind = ioctl(fd, NS_GET_NSTYPE);
    if (kind < 0) return -1;
    return kind == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int directory(int fd, const char *name, struct statx *out) {
    if (statx(fd, name, AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW, MASK, out) < 0) return -1;
    return (out->stx_mask & MASK) == MASK && S_ISDIR(out->stx_mode) && out->stx_ino && out->stx_mnt_id
        ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int current(const struct guest_tree_child_apex_view *view, int property_fd) {
    struct stat parent, child;
    char path[48];
    if (child_process(view) < 0) return -1;
    int n = snprintf(path, sizeof(path), "/proc/%ld/ns/mnt", (long)view->parent);
    if (n < 0 || (size_t)n >= sizeof(path)) return refuse(EOVERFLOW);
    if (namespace_matches(view->parent_namespace_fd, path, &parent) < 0
            || namespace_matches(view->child_namespace_fd, "/proc/self/ns/mnt", &child) < 0) return -1;
    if (same_ns(&parent, &child)) return refuse(EXDEV);

    const struct guest_tree_root_readback *readback = &view->prepared.readback;
    struct statx root, clone, named, dev, property, actual_property;
    int fd = readback->root_fd;
    if (directory(fd, "", &root) < 0 || directory(view->prepared.attachment.clone_fd, "", &clone) < 0
            || directory(AT_FDCWD, GUEST_TREE_TARGET_PATH, &named) < 0 || directory(fd, "dev", &dev) < 0
            || directory(property_fd, "", &property) < 0 || directory(fd, "dev/__properties__", &actual_property) < 0)
        return -1;
    if (root.stx_mnt_id != readback->attached.id || root.stx_dev_major != readback->attached.major
            || root.stx_dev_minor != readback->attached.minor || !same_directory(&root, &clone)
            || !same_directory(&root, &named) || !same_mount(&dev, &property)
            || !same_directory(&property, &actual_property) || property.stx_mode != (S_IFDIR | 0500)
            || property.stx_uid || property.stx_gid) return refuse(ESTALE);
    return child_process(view);
}
#else
static int child_process(const struct guest_tree_child_apex_view *view);
static int current(const struct guest_tree_child_apex_view *view, int property_fd);
#endif

static int complete(const struct guest_core_apex_backing backing[GCA_COUNT]) {
    int seen[3 * GCA_COUNT];
    unsigned used = 0;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        const int fds[] = {backing[i].payload_fd, backing[i].loop_fd, backing[i].mounted_root_fd};
        for (unsigned j = 0; j < sizeof(fds) / sizeof(fds[0]); ++j) {
            if (fds[j] < 0) return refuse(EPROTO);
            for (unsigned k = 0; k < used; ++k) if (seen[k] == fds[j]) return refuse(EPROTO);
            seen[used++] = fds[j];
        }
    }
    return 0;
}

static int attach_and_stage(const struct guest_tree_child_apex_view *view,
        struct guest_core_apex_child_sources *sources, int property_fd) {
    struct guest_tree_mount_scratch scratch = {
        .text_capacity = GPV_MOUNTINFO_MAX_BYTES + 1U, .row_capacity = GPV_MOUNTINFO_MAX_ROWS,
    };
    struct guest_core_apex_inputs inputs = {
        .root = &view->prepared, .parent = view->parent,
        .parent_namespace_fd = view->parent_namespace_fd, .child_namespace_fd = view->child_namespace_fd,
    };
    for (unsigned i = 0; i < GCA_COUNT; ++i) inputs.backing[i] = (struct guest_core_apex_backing){-1, -1, -1};
    scratch.text = malloc(scratch.text_capacity);
    scratch.rows = malloc(scratch.row_capacity * sizeof(*scratch.rows));
    int error = 0;
    if (!scratch.text || !scratch.rows) error = ENOMEM;
    else if (current(view, property_fd) < 0
            || exact_status(guest_core_apex_child_attach(sources, &view->prepared, view->parent_namespace_fd,
                                                        view->child_namespace_fd, scratch)) < 0
            || exact_status(guest_core_apex_child_borrow(sources, scratch, inputs.backing)) < 0
            || complete(inputs.backing) < 0 || current(view, property_fd) < 0
            || exact_status(guest_core_apex_stage(&inputs, scratch)) < 0) error = errno ? errno : EIO;
    free(scratch.rows);
    free(scratch.text);
    return error ? refuse(error) : 0;
}

int guest_tree_child_apex_phase(const struct guest_tree_child_apex_view *view,
        struct guest_tree_property_child *property, struct guest_core_apex_child_sources *sources) {
    if (!view || !property || !sources || view->parent <= 1 || view->child <= 1 || view->parent == view->child
            || view->prepared.attachment.state != GUEST_TREE_ATTACH_MOVE_RETURNED) return refuse(EINVAL);
    if (child_process(view) < 0) return -1;
    if (one.entered) return refuse(one.error ? one.error : EALREADY);
    one.entered = 1;
    int original_property = -1, final_property = -1;
    if (exact_status(guest_tree_property_child_borrow(property, &original_property)) < 0) goto failed;
    if (original_property < 0) return refuse(one.error = EPROTO);
    if (attach_and_stage(view, sources, original_property) < 0
            || exact_status(guest_tree_property_child_borrow(property, &final_property)) < 0) goto failed;
    if (final_property != original_property) return refuse(one.error = ESTALE);
    if (current(view, final_property) < 0) goto failed;
    return 0;

failed:
    one.error = errno ? errno : EIO;
    return refuse(one.error);
}
