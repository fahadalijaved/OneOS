#define _GNU_SOURCE
#include "guest_core_apex_loop_owner.h"

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

enum { LOOP_READ_ONLY = 1, LOOP_AUTOCLEAR = 4 };

struct apex_loop_profile {
    uint64_t bytes;
    enum guest_core_apex_fs filesystem;
};

static const struct apex_loop_profile profiles[GCA_COUNT] = {
    [GCA_ART] = {31633408, GCA_APEX_EXT4},
    [GCA_I18N] = {21409792, GCA_APEX_EROFS},
    [GCA_RUNTIME] = {5296128, GCA_APEX_EROFS},
};

static int filesystem_matches(enum guest_core_apex_fs fs, const unsigned char *header, size_t count) {
    const unsigned char erofs[] = {0xe2, 0xe1, 0xf5, 0xe0};
    const unsigned char art_features[] = {0x28, 0, 0, 0, 0x42, 0, 0, 0, 0x7b, 0x40, 0, 0};
    if (fs == GCA_APEX_EROFS) return count >= 4 && !memcmp(header, erofs, 4);
    return fs == GCA_APEX_EXT4 && count >= 104 && header[56] == 0x53 && header[57] == 0xef
        && !memcmp(header + 92, art_features, sizeof(art_features));
}

struct loop_facts {
    uint64_t device, inode, offset, limit, bytes;
    uint32_t number, flags, encryption;
    int readonly;
};

static int attachment_matches(const struct loop_facts *actual, uint64_t device, uint64_t inode,
                              uint32_t number, uint64_t bytes) {
    return actual->device == device && actual->inode == inode && actual->number == number
        && !actual->offset && !actual->limit && !actual->encryption && actual->bytes == bytes
        && actual->readonly == 1 && actual->flags == (LOOP_READ_ONLY | LOOP_AUTOCLEAR);
}

static enum guest_core_apex_loop_release outcome(int pool_requested, int sticky_error) {
    if (sticky_error) return GCA_LOOP_HOLD;
    return pool_requested ? GCA_LOOP_LOCAL_CLOSED_KERNEL_UNCONFIRMED : GCA_LOOP_NO_REQUEST_LOCAL_CLOSED;
}

enum configure_observation { CONFIGURED, RACING_CLAIM, CONFIG_UNKNOWN };

static enum configure_observation configure_observation(int status, int error) {
    if (!status) return CONFIGURED;
    if (status < 0 && error == EBUSY) return RACING_CLAIM;
    return CONFIG_UNKNOWN;
}

#ifndef GCAL_INERT
#include "guest_tree_stage_guard.h"

#include <fcntl.h>
#include <linux/fs.h>
#include <linux/loop.h>
#include <linux/magic.h>
#include <linux/major.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define NODE_PATH (O_PATH | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define EROFS_MAGIC 0xe0f5e1e2UL
#define LOOP_CONTROL_MINOR 237U

_Static_assert((int)LOOP_READ_ONLY == (int)LO_FLAGS_READ_ONLY
        && (int)LOOP_AUTOCLEAR == (int)LO_FLAGS_AUTOCLEAR, "loop flag ABI");

enum { ROOT, DEV, BLOCK, PROC, PROC_FDS, NS, CONTROL_PATH, CONTROL, ANCHOR_COUNT };
enum { OPENING = 1, READY, BORROWING, REFUSED, CLOSING, CLOSED };
struct loop_cell {
    int path_fd, block_fd, number, attempted;
    struct stat payload, block;
};

struct guest_core_apex_loop_owner {
    pid_t parent;
    struct guest_tree_stage_guard *guard;
    int anchor[ANCHOR_COUNT], payload[GCA_COUNT], state, pool_requested, sticky;
    struct loop_cell role[GCA_COUNT];
    enum guest_core_apex_loop_release terminal;
};

static struct guest_core_apex_loop_owner one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static void sticky(struct guest_core_apex_loop_owner *owner, int error) {
    if (!owner->sticky) owner->sticky = error ? error : EIO;
}

static int controller(void) {
    return getpid() == gettid() && !getuid() && !geteuid() ? 0 : refuse(EPERM);
}

static int valid(struct guest_core_apex_loop_owner *owner) {
    if (controller() < 0) return -1;
    return owner == &one && owner->parent == getpid() ? 0 : refuse(EINVAL);
}

static int same_node(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino && a->st_rdev == b->st_rdev
        && a->st_mode == b->st_mode && a->st_uid == b->st_uid && a->st_gid == b->st_gid;
}

static int same_payload(const struct stat *a, const struct stat *b) {
    return same_node(a, b) && a->st_nlink == b->st_nlink && a->st_size == b->st_size
        && a->st_mtim.tv_sec == b->st_mtim.tv_sec && a->st_mtim.tv_nsec == b->st_mtim.tv_nsec
        && a->st_ctim.tv_sec == b->st_ctim.tv_sec && a->st_ctim.tv_nsec == b->st_ctim.tv_nsec;
}

static int fs_type(int fd, unsigned long kind) {
    struct statfs value;
    if (fstatfs(fd, &value) < 0) return -1;
    return (unsigned long)value.f_type == kind ? 0 : refuse(EXDEV);
}

static int same_mount(int fd, int other) {
    const unsigned mask = STATX_MNT_ID;
    struct statx a, b;
    if (statx(fd, "", LOOKUP | AT_EMPTY_PATH, mask, &a) < 0
            || statx(other, "", LOOKUP | AT_EMPTY_PATH, mask, &b) < 0) return -1;
    if (!(a.stx_mask & mask) || !(b.stx_mask & mask) || !a.stx_mnt_id || a.stx_mnt_id != b.stx_mnt_id)
        return refuse(EXDEV);
    return 0;
}

static int named_node(int base, const char *name, int flags, int fd) {
    struct stat held, named;
    if (fstat(fd, &held) < 0 || fstatat(base, name, &named, flags) < 0) return -1;
    return same_node(&held, &named) ? 0 : refuse(ESTALE);
}

static int current_anchors(struct guest_core_apex_loop_owner *owner) {
    const int *a = owner->anchor;
    struct stat dev, block;
    if (guest_tree_stage_guard_check(owner->guard) < 0 || fs_type(a[NS], NSFS_MAGIC) < 0
            || fs_type(a[DEV], TMPFS_MAGIC) < 0 || fs_type(a[PROC], PROC_SUPER_MAGIC) < 0
            || same_mount(a[DEV], a[BLOCK]) < 0 || same_mount(a[PROC], a[PROC_FDS]) < 0
            || named_node(AT_FDCWD, "/", AT_SYMLINK_NOFOLLOW, a[ROOT]) < 0
            || named_node(a[ROOT], "dev", AT_SYMLINK_NOFOLLOW, a[DEV]) < 0
            || named_node(a[DEV], "block", AT_SYMLINK_NOFOLLOW, a[BLOCK]) < 0
            || named_node(a[ROOT], "proc", AT_SYMLINK_NOFOLLOW, a[PROC]) < 0
            || named_node(a[PROC], "self/fd", AT_SYMLINK_NOFOLLOW, a[PROC_FDS]) < 0
            || named_node(a[PROC], "self/ns/mnt", 0, a[NS]) < 0
            || fstat(a[DEV], &dev) < 0 || fstat(a[BLOCK], &block) < 0) return -1;
    int type = ioctl(a[NS], NS_GET_NSTYPE);
    if (type < 0) return -1;
    if (type != CLONE_NEWNS || !S_ISDIR(dev.st_mode) || !S_ISDIR(block.st_mode)
            || dev.st_uid || block.st_uid || ((dev.st_mode | block.st_mode) & 0022)) return refuse(EXDEV);
    return 0;
}

static int reopen(int proc_fds, int path_fd, int flags) {
    char name[24];
    int n = snprintf(name, sizeof(name), "%d", path_fd);
    if (n <= 0 || (size_t)n >= sizeof(name)) return refuse(EOVERFLOW);
    return openat(proc_fds, name, flags | O_CLOEXEC);
}

static int check_device(int fd, int type, unsigned maj, unsigned min, struct stat *value) {
    if (fstat(fd, value) < 0) return -1;
    if ((value->st_mode & S_IFMT) != (mode_t)type || major(value->st_rdev) != maj || minor(value->st_rdev) != min)
        return refuse(ENODEV);
    return 0;
}

static int open_control(struct guest_core_apex_loop_owner *owner, int ns_fd) {
    int *a = owner->anchor;
    struct stat held, opened;
    if (guest_tree_stage_guard_check(owner->guard) < 0) return -1;
    a[NS] = fcntl(ns_fd, F_DUPFD_CLOEXEC, 3);
    if (a[NS] < 0) return -1;
    a[ROOT] = open("/", DIRECTORY);
    if (a[ROOT] < 0) return -1;
    a[DEV] = openat(a[ROOT], "dev", DIRECTORY);
    if (a[DEV] < 0) return -1;
    a[BLOCK] = openat(a[DEV], "block", DIRECTORY);
    if (a[BLOCK] < 0) return -1;
    a[PROC] = openat(a[ROOT], "proc", DIRECTORY);
    if (a[PROC] < 0 || fs_type(a[PROC], PROC_SUPER_MAGIC) < 0) return -1;
    a[PROC_FDS] = openat(a[PROC], "self/fd", DIRECTORY);
    if (a[PROC_FDS] < 0 || current_anchors(owner) < 0) return -1;
    a[CONTROL_PATH] = openat(a[DEV], "loop-control", NODE_PATH);
    if (a[CONTROL_PATH] < 0 || same_mount(a[CONTROL_PATH], a[DEV]) < 0
            || check_device(a[CONTROL_PATH], S_IFCHR, MISC_MAJOR, LOOP_CONTROL_MINOR, &held) < 0) return -1;
    a[CONTROL] = reopen(a[PROC_FDS], a[CONTROL_PATH], O_RDONLY | O_NONBLOCK);
    if (a[CONTROL] < 0 || check_device(a[CONTROL], S_IFCHR, MISC_MAJOR, LOOP_CONTROL_MINOR, &opened) < 0
            || named_node(a[DEV], "loop-control", AT_SYMLINK_NOFOLLOW, a[CONTROL_PATH]) < 0) return -1;
    return same_node(&held, &opened) ? 0 : refuse(ESTALE);
}

static int check_payload(struct guest_core_apex_loop_owner *owner, unsigned role, int initial) {
    int fd = owner->payload[role], flags = fcntl(fd, F_GETFL);
    struct stat value;
    struct statvfs fs;
    if (flags < 0 || fstat(fd, &value) < 0 || fstatvfs(fd, &fs) < 0 || fs_type(fd, EROFS_MAGIC) < 0) return -1;
    if ((flags & (O_PATH | O_ACCMODE)) != O_RDONLY || !(fs.f_flag & ST_RDONLY)
            || !S_ISREG(value.st_mode) || value.st_uid || value.st_gid || value.st_nlink != 1
            || (value.st_mode & 07777) != 0444 || value.st_size < 0
            || (uint64_t)value.st_size != profiles[role].bytes) return refuse(EPERM);
    if (!initial) return same_payload(&owner->role[role].payload, &value) ? 0 : refuse(ESTALE);
    unsigned char header[104];
    ssize_t got = pread(fd, header, sizeof(header), 1024);
    if (got < 0) return -1;
    if (!filesystem_matches(profiles[role].filesystem, header, (size_t)got)) return refuse(EPROTO);
    owner->role[role].payload = value;
    return 0;
}

static int check_attachment(struct guest_core_apex_loop_owner *owner, unsigned role) {
    struct loop_cell *cell = &owner->role[role];
    struct loop_info64 info;
    struct stat block;
    uint64_t bytes = 0;
    int readonly = 0;
    char name[32];
    int n = snprintf(name, sizeof(name), "loop%d", cell->number);
    if (n <= 0 || (size_t)n >= sizeof(name)) return refuse(EOVERFLOW);
    if (check_payload(owner, role, 0) < 0
            || named_node(owner->anchor[BLOCK], name, AT_SYMLINK_NOFOLLOW, cell->path_fd) < 0
            || check_device(cell->block_fd, S_IFBLK, LOOP_MAJOR, (unsigned)cell->number, &block) < 0
            || ioctl(cell->block_fd, LOOP_GET_STATUS64, &info) < 0
            || ioctl(cell->block_fd, BLKROGET, &readonly) < 0
            || ioctl(cell->block_fd, BLKGETSIZE64, &bytes) < 0) return -1;
    const struct loop_facts actual = {
        .device = info.lo_device, .inode = info.lo_inode, .offset = info.lo_offset,
        .limit = info.lo_sizelimit, .bytes = bytes, .number = info.lo_number,
        .flags = info.lo_flags, .encryption = info.lo_encrypt_type, .readonly = readonly
    };
    if (!same_node(&cell->block, &block) || info.lo_rdevice
            || !attachment_matches(&actual, cell->payload.st_dev, cell->payload.st_ino,
                                   (unsigned)cell->number, profiles[role].bytes)) return refuse(ESTALE);
    return 0;
}

static int configure_role(struct guest_core_apex_loop_owner *owner, unsigned role) {
    int *a = owner->anchor;
    struct loop_cell *cell = &owner->role[role];
    char name[32];
    struct loop_info64 probe;
    struct stat held;
    if (current_anchors(owner) < 0 || check_payload(owner, role, 0) < 0
            || named_node(a[DEV], "loop-control", AT_SYMLINK_NOFOLLOW, a[CONTROL_PATH]) < 0) return -1;
    owner->pool_requested = 1; /* GET_FREE can create a pool device. */
    cell->number = ioctl(a[CONTROL], LOOP_CTL_GET_FREE);
    if (cell->number < 0) { sticky(owner, errno); return -1; }
    for (unsigned i = 0; i < role; ++i)
        if (owner->role[i].number == cell->number) return refuse(EBUSY);
    int n = snprintf(name, sizeof(name), "loop%d", cell->number);
    if (n <= 0 || (size_t)n >= sizeof(name)) return refuse(EOVERFLOW);
    cell->path_fd = openat(a[BLOCK], name, NODE_PATH);
    if (cell->path_fd < 0 || same_mount(cell->path_fd, a[BLOCK]) < 0
            || check_device(cell->path_fd, S_IFBLK, LOOP_MAJOR, (unsigned)cell->number, &held) < 0) return -1;
    cell->block_fd = reopen(a[PROC_FDS], cell->path_fd, O_RDONLY | O_NONBLOCK);
    if (cell->block_fd < 0
            || check_device(cell->block_fd, S_IFBLK, LOOP_MAJOR, (unsigned)cell->number, &cell->block) < 0
            || named_node(a[BLOCK], name, AT_SYMLINK_NOFOLLOW, cell->path_fd) < 0) return -1;
    if (!same_node(&held, &cell->block)) return refuse(ESTALE);
    int status = ioctl(cell->block_fd, LOOP_GET_STATUS64, &probe);
    if (status == 0) return refuse(EBUSY); /* Never adopt an existing attachment. */
    if (status > 0) return refuse(EPROTO);
    if (errno != ENXIO) return -1;
    if (current_anchors(owner) < 0 || check_payload(owner, role, 0) < 0
            || named_node(a[BLOCK], name, AT_SYMLINK_NOFOLLOW, cell->path_fd) < 0) return -1;
    const struct loop_config config = {
        .fd = (uint32_t)owner->payload[role],
        .info = {.lo_flags = LO_FLAGS_READ_ONLY | LO_FLAGS_AUTOCLEAR},
    };
    cell->attempted = 1;
    status = ioctl(cell->block_fd, LOOP_CONFIGURE, &config);
    int saved = errno;
    enum configure_observation observed = configure_observation(status, saved);
    if (observed == RACING_CLAIM) return refuse(saved);
    if (observed == CONFIG_UNKNOWN) {
        sticky(owner, status > 0 ? EPROTO : saved);
        return refuse(owner->sticky);
    }
    if (check_attachment(owner, role) < 0) {
        sticky(owner, errno);
        return -1;
    }
    return 0;
}

static int verify_all(struct guest_core_apex_loop_owner *owner) {
    if (current_anchors(owner) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        if (!owner->role[i].attempted) return refuse(EPROTO);
        if (check_attachment(owner, i) < 0) return -1;
    }
    return guest_tree_stage_guard_check(owner->guard);
}

int guest_core_apex_loop_begin(struct guest_core_apex_files *source,
        struct guest_tree_stage_guard *guard, int controller_namespace_fd,
        struct guest_core_apex_loop_owner **out) {
    if (controller() < 0) return -1;
    if (!source || !guard || controller_namespace_fd < 0 || !out || *out) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.parent = getpid();
    one.state = OPENING;
    one.guard = guard;
    for (unsigned i = 0; i < ANCHOR_COUNT; ++i) one.anchor[i] = -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        one.payload[i] = one.role[i].path_fd = one.role[i].block_fd = one.role[i].number = -1;
    *out = &one;
    if (guest_tree_stage_guard_check(guard) < 0 || guest_core_apex_take_payloads(source, one.payload) < 0)
        goto refuse_open;
    for (unsigned i = 0; i < GCA_COUNT; ++i) if (check_payload(&one, i, 1) < 0) goto refuse_open;
    if (open_control(&one, controller_namespace_fd) < 0) goto refuse_open;
    for (unsigned i = 0; i < GCA_COUNT; ++i) if (configure_role(&one, i) < 0) goto refuse_open;
    if (verify_all(&one) < 0) {
        sticky(&one, errno);
        goto refuse_open;
    }
    one.state = READY;
    return 0;
refuse_open:
    one.state = REFUSED;
    return -1;
}

int guest_core_apex_loop_borrow(struct guest_core_apex_loop_owner *owner,
        struct guest_core_apex_loop_pair out[GCA_COUNT]) {
    if (valid(owner) < 0) return -1;
    if (!out) return refuse(EINVAL);
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        if (out[i].payload_fd != -1 || out[i].loop_fd != -1) return refuse(EINVAL);
    if (owner->state != READY) return refuse(owner->sticky ? owner->sticky : EBUSY);
    owner->state = BORROWING;
    if (verify_all(owner) < 0) {
        sticky(owner, errno);
        owner->state = REFUSED;
        return refuse(owner->sticky);
    }
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        out[i] = (struct guest_core_apex_loop_pair){owner->payload[i], owner->role[i].block_fd, profiles[i].filesystem};
    owner->state = READY;
    return 0;
}

static void close_owned(struct guest_core_apex_loop_owner *owner, int *slot) {
    int fd = *slot;
    *slot = -1;
    if (fd >= 0 && close(fd) < 0) sticky(owner, errno);
}

enum guest_core_apex_loop_release guest_core_apex_loop_close(struct guest_core_apex_loop_owner *owner) {
    if (valid(owner) < 0) return GCA_LOOP_HOLD;
    if (owner->state == CLOSED) {
        if (owner->sticky) errno = owner->sticky;
        return owner->terminal;
    }
    if (owner->state == OPENING || owner->state == BORROWING || owner->state == CLOSING) {
        errno = EBUSY;
        return GCA_LOOP_HOLD;
    }
    owner->state = CLOSING;
    if (owner->pool_requested && guest_tree_stage_guard_check(owner->guard) < 0) sticky(owner, errno);
    for (unsigned i = GCA_COUNT; i > 0; --i) {
        close_owned(owner, &owner->role[i - 1].block_fd);
        close_owned(owner, &owner->role[i - 1].path_fd);
        close_owned(owner, &owner->payload[i - 1]);
    }
    for (unsigned i = ANCHOR_COUNT; i > 0; --i) close_owned(owner, &owner->anchor[i - 1]);
    owner->terminal = outcome(owner->pool_requested, owner->sticky);
    owner->state = CLOSED;
    if (owner->sticky) errno = owner->sticky;
    return owner->terminal;
}
#endif
