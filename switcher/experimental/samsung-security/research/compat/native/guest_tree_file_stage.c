#define _GNU_SOURCE
#include "guest_tree_file_stage.h"

#include "guest_tree_file_erofs_attach.h"
#include "guest_tree_file_erofs_mount.h"
#include "guest_tree_file_erofs_release.h"
#include "guest_tree_fsverity_file.h"
#include "guest_tree_stage_guard.h"
#include "guest_tree_stage_namespace.h"

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

/* Selected only from the full independent raw readback and unsalted
 * 4 KiB fs-verity descriptor of the same PC carrier image. */
static const struct guest_tree_fsverity_expected carrier = {
    .bytes = UINT64_C(13890850816),
    .sha256 = {
        0x9b, 0x2b, 0x66, 0x45, 0x82, 0x36, 0x0d, 0xec,
        0x66, 0x0e, 0x3e, 0x25, 0xc8, 0x40, 0x10, 0x4c,
        0x16, 0xb1, 0xe1, 0xa9, 0xcb, 0x4a, 0xad, 0xbf,
        0x8f, 0x46, 0x7e, 0x20, 0x0c, 0x52, 0x5b, 0xa9
    }
};

struct gtfs_owner {
    pid_t pid;
    struct gtsn_owner *namespace;
    struct guest_tree_stage_guard *guard;
    struct guest_tree_fsverity_file *file;
    struct gtfm_owner *mount;
    struct guest_tree_file_erofs_attachment attached;
    struct guest_tree_file_erofs_release release;
    int attempted, closed, close_error;
};

static struct gtfs_owner one = {.attached = GUEST_TREE_FILE_EROFS_ATTACHMENT_INITIALIZER};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int current_process(struct gtfs_owner *owner) {
    if (getpid() != gettid()) return refuse(EPERM);
    if (owner != &one || owner->pid != getpid()) return refuse(EINVAL);
    return 0;
}

int gtfs_enter(struct gtfs_owner **out) {
    if (!out || *out || one.pid) return refuse(EINVAL);
    if (getpid() != gettid()) return refuse(EPERM);
    one.pid = getpid();
    *out = &one;
    return gtsn_enter(&one.namespace);
}

static int attach(struct gtfs_owner *owner, const struct guest_tree_file_erofs_attach_inputs *inputs) {
    const size_t text_bytes = GPV_MOUNTINFO_MAX_BYTES + 1U;
    const size_t count = GPV_MOUNTINFO_MAX_ROWS;
    char *text = malloc(2U * text_bytes);
    struct gpv_mount_row *rows = malloc(2U * count * sizeof(*rows));
    int result = -1;
    if (!text || !rows) errno = ENOMEM;
    else result = guest_tree_file_erofs_attach(&owner->attached, inputs,
            (struct guest_tree_mount_scratch){text, text_bytes, rows, count},
            (struct guest_tree_mount_scratch){text + text_bytes, text_bytes, rows + count, count});
    int saved = errno;
    free(rows);
    free(text);
    errno = saved;
    return result;
}

int gtfs_mount(struct gtfs_owner *owner, int stage_fd, struct guest_tree_stage_guard *guard) {
    if (current_process(owner) < 0) return -1;
    if (owner->attempted || owner->closed || !guard) return refuse(EINVAL);
    owner->attempted = 1;
    owner->guard = guard;
    struct gtsn_witnesses ns = {-1, -1};
    if (gtsn_borrow(owner->namespace, &ns) < 0) return -1;
    const struct guest_tree_fsverity_inputs stage = {stage_fd, ns.current_namespace_fd, guard};
    if (guest_tree_fsverity_open_file(&stage, &carrier, &owner->file) < 0) return -1;
    struct guest_tree_fsverity_borrow files = {-1, -1};
    if (guest_tree_fsverity_borrow_fds(owner->file, &files) < 0
            || gtfm_create(&owner->mount, files.image_fd, files.proc_root_fd) < 0) return -1;
    struct gtfm_identity birth;
    int detached = gtfm_borrow_root(owner->mount, &birth);
    if (detached < 0) return -1;
    if (birth.root_inode != 1U) return refuse(ESTALE);
    if (gtsn_borrow(owner->namespace, &ns) < 0 || guest_tree_stage_guard_check(guard) < 0) return -1;
    const struct guest_tree_file_erofs_attach_inputs inputs = {
        stage_fd, ns.initial_namespace_fd, ns.current_namespace_fd, detached
    };
    return attach(owner, &inputs);
}

static int same_namespace(int expected, int held) {
    struct stat a, b;
    if (fstat(expected, &a) < 0 || fstat(held, &b) < 0) return -1;
    return a.st_dev == b.st_dev && a.st_ino == b.st_ino ? 0 : refuse(EXDEV);
}

static int same_directory(int expected, int held) {
    const unsigned mask = STATX_TYPE | STATX_INO | STATX_MNT_ID;
    const int flags = AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
    struct statx a, b;
    if (statx(expected, "", flags, mask, &a) < 0 || statx(held, "", flags, mask, &b) < 0) return -1;
    if ((a.stx_mask & mask) != mask || (b.stx_mask & mask) != mask
            || !S_ISDIR(a.stx_mode) || !S_ISDIR(b.stx_mode) || !a.stx_mnt_id
            || a.stx_mnt_id != b.stx_mnt_id || a.stx_ino != b.stx_ino
            || a.stx_dev_major != b.stx_dev_major || a.stx_dev_minor != b.stx_dev_minor) return refuse(EXDEV);
    return 0;
}

int gtfs_check(struct gtfs_owner *owner, int stage_fd, int backing_fd, int tree_fd,
               int namespace_fd, struct guest_tree_stage_guard *guard) {
    if (current_process(owner) < 0) return -1;
    const struct guest_tree_file_erofs_attachment *attached = &owner->attached;
    if (owner->closed || owner->close_error || !guard || owner->guard != guard
            || attached->state != GUEST_TREE_FILE_EROFS_BACKING_HELD || attached->close_error
            || attached->expected_root_inode != 1U || attached->expected_tree_inode != 3U) return refuse(ESTALE);
    struct gtsn_witnesses ns = {-1, -1};
    struct guest_tree_fsverity_borrow files = {-1, -1};
    struct gtfm_identity birth;
    if (gtsn_borrow(owner->namespace, &ns) < 0 || same_namespace(ns.current_namespace_fd, namespace_fd) < 0
            || same_directory(attached->stage_fd, stage_fd) < 0
            || same_directory(attached->backing_fd, backing_fd) < 0
            || same_directory(attached->tree_fd, tree_fd) < 0
            || guest_tree_fsverity_borrow_fds(owner->file, &files) < 0
            || gtfm_borrow_root(owner->mount, &birth) < 0) return -1;
    if (birth.mount_id != attached->backing_mount_id || birth.root_inode != attached->expected_root_inode
            || birth.device_major != attached->expected_mount.major
            || birth.device_minor != attached->expected_mount.minor) return refuse(ESTALE);
    return guest_tree_stage_guard_check(guard);
}

static int hold(struct gtfs_owner *owner) {
    if (!owner->close_error) owner->close_error = errno ? errno : EIO;
    return refuse(owner->close_error);
}

static void close_cell(struct gtfs_owner *owner, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0) (void)hold(owner);
}

int gtfs_close(struct gtfs_owner *owner) {
    if (current_process(owner) < 0) return -1;
    if (owner->closed) return 0;
    if (owner->close_error) return refuse(owner->close_error);
    struct guest_tree_file_erofs_attachment *attached = &owner->attached;
    if (attached->close_error) {
        errno = attached->close_error;
        return hold(owner);
    }
    if (attached->state == GUEST_TREE_FILE_EROFS_BACKING_HELD) {
        struct gtsn_witnesses ns = {-1, -1};
        if (guest_tree_stage_guard_check(owner->guard) < 0 || gtsn_borrow(owner->namespace, &ns) < 0
                || guest_tree_file_erofs_release(&owner->release, owner->mount, attached,
                    ns.initial_namespace_fd, ns.current_namespace_fd) < 0) return hold(owner);
    } else {
        if (attached->state >= GUEST_TREE_FILE_EROFS_MOVE_ATTEMPTED) {
            errno = EINPROGRESS;
            return hold(owner);
        }
        close_cell(owner, &attached->tree_fd);
        close_cell(owner, &attached->backing_fd);
        close_cell(owner, &attached->detached_tree_fd);
        close_cell(owner, &attached->mount_fd);
        if (owner->mount && gtfm_close(owner->mount) < 0) return hold(owner);
    }
    close_cell(owner, &attached->covered_fd);
    close_cell(owner, &attached->stage_fd);
    if (owner->close_error) return refuse(owner->close_error);
    if (owner->file && guest_tree_fsverity_close_file(owner->file) < 0) return hold(owner);
    if (owner->namespace && gtsn_close_local(owner->namespace) < 0) return hold(owner);
    owner->closed = 1;
    return 0;
}
