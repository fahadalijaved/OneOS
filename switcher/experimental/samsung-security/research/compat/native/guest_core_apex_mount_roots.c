#define _GNU_SOURCE
#include "guest_core_apex_mount_roots.h"

#include <stdint.h>

#define EXT4_MAGIC 0xef53UL
#define EROFS_MAGIC 0xe0f5e1e2UL

struct root_profile {
    const char *name;
    enum guest_core_apex_fs filesystem;
    unsigned long magic;
    uint64_t inode;
};

static const struct root_profile profiles[GCA_COUNT] = {
    [GCA_ART] = {"ext4", GCA_APEX_EXT4, EXT4_MAGIC, 2},
    [GCA_I18N] = {"erofs", GCA_APEX_EROFS, EROFS_MAGIC, 39},
    [GCA_RUNTIME] = {"erofs", GCA_APEX_EROFS, EROFS_MAGIC, 39},
};

struct root_facts {
    uint64_t mount, inode;
    unsigned major, minor, uid, gid, permissions;
    unsigned long magic;
    int mount_root, directory, readonly, nosuid, nodev, noexec;
};

static int root_matches(const struct root_facts *root, const struct root_profile *profile,
                        unsigned major, unsigned minor) {
    return root->mount && root->mount_root && root->directory && root->magic == profile->magic
        && root->inode == profile->inode && root->major == major && root->minor == minor
        && root->uid == 1000 && root->gid == 1000 && root->permissions == 0755
        && root->readonly && root->nosuid && root->nodev && !root->noexec;
}

static enum guest_core_apex_mount_release release_result(int create_attempted, int error) {
    if (error) return GCA_MOUNT_HOLD;
    return create_attempted ? GCA_MOUNT_LOCAL_CLOSED_KERNEL_UNCONFIRMED : GCA_MOUNT_NO_CREATE_LOCAL_CLOSED;
}

#ifndef GCAM_INERT
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/major.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <unistd.h>

/* Linux v6.12 UAPI linux/mount.h. The pinned NDK headers predate this
 * command. An older or restricted kernel must refuse this profile. */
enum { CREATE_EXCLUSIVE = 8 };
enum { OPENING = 1, READY, BORROWING, LENT, REFUSED, CLOSING, CLOSED };
static const int lookup = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
static const unsigned node_mask = STATX_TYPE | STATX_MODE | STATX_INO | STATX_MNT_ID;

struct mount_cell {
    struct guest_core_apex_backing backing;
    int context;
    uint64_t mount_id;
};

struct guest_core_apex_mount_roots {
    pid_t controller;
    struct guest_core_apex_loop_owner *loop;
    int proc, ns, state, create_attempted, error;
    enum guest_core_apex_mount_release terminal;
    struct mount_cell role[GCA_COUNT];
};

static struct guest_core_apex_mount_roots one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int hold(struct guest_core_apex_mount_roots *owner, int error) {
    if (!owner->error) owner->error = error ? error : EIO;
    return refuse(owner->error);
}

static int controller(void) {
    return getpid() == gettid() && !getuid() && !geteuid() ? 0 : refuse(EPERM);
}

static int owned(struct guest_core_apex_mount_roots *owner) {
    if (controller() < 0) return -1;
    return owner == &one && owner->controller == getpid() ? 0 : refuse(EINVAL);
}

static int sample(int base, const char *name, int flags, unsigned mask, struct statx *out) {
    if (statx(base, name, flags, mask, out) < 0) return -1;
    return (out->stx_mask & mask) == mask && out->stx_mnt_id && out->stx_ino ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor;
}

static int fs_magic(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : refuse(EXDEV);
}

static int current(struct guest_core_apex_mount_roots *owner, struct statx *proc) {
    struct statx named, files, ns, self;
    if (fs_magic(owner->proc, PROC_SUPER_MAGIC) < 0 || fs_magic(owner->ns, NSFS_MAGIC) < 0
            || sample(owner->proc, "", lookup | AT_EMPTY_PATH, node_mask, proc) < 0
            || sample(AT_FDCWD, "/proc", lookup, node_mask, &named) < 0
            || sample(owner->proc, "self/fd", lookup, node_mask, &files) < 0
            || sample(owner->ns, "", lookup | AT_EMPTY_PATH, node_mask, &ns) < 0
            || sample(owner->proc, "self/ns/mnt", AT_NO_AUTOMOUNT, node_mask, &self) < 0) return -1;
    int type = ioctl(owner->ns, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return S_ISDIR(proc->stx_mode) && S_ISDIR(files.stx_mode) && same_node(proc, &named)
        && same_mount(proc, &files) && same_node(&ns, &self) && type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int loop_source(struct guest_core_apex_mount_roots *owner, int fd,
                       char source[48], struct statx *block) {
    struct statx proc, link, target;
    int n = snprintf(source, 48, "/proc/self/fd/%d", fd);
    if (n <= 0 || n >= 48) return refuse(EOVERFLOW);
    const char *relative = source + sizeof("/proc");
    if (current(owner, &proc) < 0
            || sample(fd, "", lookup | AT_EMPTY_PATH, node_mask, block) < 0
            || sample(owner->proc, relative, lookup, node_mask, &link) < 0
            || sample(owner->proc, relative, AT_NO_AUTOMOUNT, node_mask, &target) < 0) return -1;
    return S_ISLNK(link.stx_mode) && same_mount(&proc, &link) && S_ISBLK(block->stx_mode)
        && block->stx_rdev_major == LOOP_MAJOR && same_node(block, &target) ? 0 : refuse(EXDEV);
}

static int current_pairs(struct guest_core_apex_mount_roots *owner, int retain) {
    struct guest_core_apex_loop_pair pairs[GCA_COUNT];
    for (unsigned i = 0; i < GCA_COUNT; ++i) pairs[i] = (struct guest_core_apex_loop_pair){-1, -1, 0};
    if (guest_core_apex_loop_borrow(owner->loop, pairs) < 0) return -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        struct guest_core_apex_backing *held = &owner->role[i].backing;
        const int supplied[] = {pairs[i].payload_fd, pairs[i].loop_fd};
        int *const slots[] = {&held->payload_fd, &held->loop_fd};
        if (pairs[i].filesystem != profiles[i].filesystem) return refuse(EXDEV);
        for (unsigned j = 0; j < 2; ++j) {
            if (retain) *slots[j] = fcntl(supplied[j], F_DUPFD_CLOEXEC, 3);
            if (*slots[j] < 0) return -1;
            struct statx original, duplicate;
            if (sample(supplied[j], "", lookup | AT_EMPTY_PATH, node_mask, &original) < 0
                    || sample(*slots[j], "", lookup | AT_EMPTY_PATH, node_mask, &duplicate) < 0) return -1;
            if (!same_node(&original, &duplicate)) return refuse(ESTALE);
        }
    }
    return 0;
}

static int check_root(struct guest_core_apex_mount_roots *owner, unsigned role) {
    struct mount_cell *cell = &owner->role[role];
    int fd = cell->backing.mounted_root_fd;
    char source[48];
    struct statx block, root;
    struct statfs fs;
    struct statvfs flags;
    int mode = fcntl(fd, F_GETFL), fd_flags = fcntl(fd, F_GETFD);
    if (mode < 0 || fd_flags < 0 || loop_source(owner, cell->backing.loop_fd, source, &block) < 0
            || fstatfs(fd, &fs) < 0 || fstatvfs(fd, &flags) < 0
            || sample(fd, "", lookup | AT_EMPTY_PATH, node_mask | STATX_UID | STATX_GID, &root) < 0) return -1;
    const struct root_facts actual = {
        .mount = root.stx_mnt_id, .inode = root.stx_ino, .major = root.stx_dev_major, .minor = root.stx_dev_minor,
        .uid = root.stx_uid, .gid = root.stx_gid, .permissions = root.stx_mode & 07777,
        .magic = (unsigned long)fs.f_type, .directory = S_ISDIR(root.stx_mode),
        .mount_root = !!(root.stx_attributes_mask & root.stx_attributes & STATX_ATTR_MOUNT_ROOT),
        .readonly = !!(flags.f_flag & ST_RDONLY), .nosuid = !!(flags.f_flag & ST_NOSUID),
        .nodev = !!(flags.f_flag & ST_NODEV), .noexec = !!(flags.f_flag & ST_NOEXEC),
    };
    if (!(mode & O_PATH) || !(fd_flags & FD_CLOEXEC) || root.stx_mnt_id == block.stx_mnt_id
            || !root_matches(&actual, &profiles[role], block.stx_rdev_major, block.stx_rdev_minor)) return refuse(EXDEV);
    if (cell->mount_id && cell->mount_id != root.stx_mnt_id) return refuse(ESTALE);
    for (unsigned i = 0; i < role; ++i)
        if (owner->role[i].mount_id == root.stx_mnt_id) return refuse(ESTALE);
    cell->mount_id = root.stx_mnt_id;
    return 0;
}

static void close_fd(struct guest_core_apex_mount_roots *owner, int *slot) {
    int fd = *slot;
    *slot = -1;
    if (fd >= 0 && close(fd) < 0) (void)hold(owner, errno);
}

static int create_root(struct guest_core_apex_mount_roots *owner, unsigned role) {
    struct mount_cell *cell = &owner->role[role];
    char source[48];
    struct statx before, after;
    if (current_pairs(owner, 0) < 0 || loop_source(owner, cell->backing.loop_fd, source, &before) < 0) return -1;
    cell->context = (int)syscall(SYS_fsopen, profiles[role].name, FSOPEN_CLOEXEC);
    if (cell->context < 0) return -1;
    if (syscall(SYS_fsconfig, cell->context, FSCONFIG_SET_FLAG, "ro", NULL, 0) < 0
            || (role == GCA_ART && syscall(SYS_fsconfig, cell->context, FSCONFIG_SET_FLAG, "noload", NULL, 0) < 0)
            || syscall(SYS_fsconfig, cell->context, FSCONFIG_SET_STRING, "source", source, 0) < 0
            || current_pairs(owner, 0) < 0 || loop_source(owner, cell->backing.loop_fd, source, &after) < 0) return -1;
    if (!same_node(&before, &after)) return refuse(ESTALE);
    owner->create_attempted = 1;
    if (syscall(SYS_fsconfig, cell->context, CREATE_EXCLUSIVE, NULL, NULL, 0) < 0) return -1;
    cell->backing.mounted_root_fd = (int)syscall(SYS_fsmount, cell->context, FSMOUNT_CLOEXEC,
                                               MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV);
    if (cell->backing.mounted_root_fd < 0 || check_root(owner, role) < 0 || current_pairs(owner, 0) < 0) return -1;
    close_fd(owner, &cell->context);
    return owner->error ? refuse(owner->error) : 0;
}

int guest_core_apex_mount_begin(struct guest_core_apex_loop_owner *loop,
        int controller_namespace_fd, struct guest_core_apex_mount_roots **out) {
    if (controller() < 0) return -1;
    if (!loop || controller_namespace_fd < 0 || !out || *out) return refuse(EINVAL);
    if (one.state) return refuse(EALREADY);
    one.state = OPENING;
    one.controller = getpid();
    one.loop = loop;
    one.ns = one.proc = -1;
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        one.role[i] = (struct mount_cell){.backing = {-1, -1, -1}, .context = -1};
    *out = &one;
    struct statx proc;
    one.ns = fcntl(controller_namespace_fd, F_DUPFD_CLOEXEC, 3);
    if (one.ns < 0) goto failed;
    one.proc = open("/proc", O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (one.proc < 0 || current(&one, &proc) < 0 || current_pairs(&one, 1) < 0) goto failed;
    for (unsigned i = 0; i < GCA_COUNT; ++i) if (create_root(&one, i) < 0) goto failed;
    one.state = READY;
    return 0;
failed:
    one.state = REFUSED;
    return one.create_attempted ? hold(&one, errno) : -1;
}

int guest_core_apex_mount_borrow(struct guest_core_apex_mount_roots *owner,
        struct guest_core_apex_backing out[GCA_COUNT]) {
    if (owned(owner) < 0) return -1;
    if (!out) return refuse(EINVAL);
    for (unsigned i = 0; i < GCA_COUNT; ++i)
        if (out[i].payload_fd != -1 || out[i].loop_fd != -1 || out[i].mounted_root_fd != -1) return refuse(EINVAL);
    if (owner->state != READY) return refuse(owner->error ? owner->error : EBUSY);
    owner->state = BORROWING;
    for (unsigned i = 0; i < GCA_COUNT; ++i) if (check_root(owner, i) < 0) goto failed;
    if (current_pairs(owner, 0) < 0) goto failed;
    for (unsigned i = 0; i < GCA_COUNT; ++i) out[i] = owner->role[i].backing;
    owner->state = LENT;
    return 0;
failed:
    owner->state = REFUSED;
    return hold(owner, errno);
}

enum guest_core_apex_mount_release guest_core_apex_mount_close(struct guest_core_apex_mount_roots *owner) {
    if (owned(owner) < 0) return GCA_MOUNT_HOLD;
    if (owner->state == CLOSED) {
        if (owner->error) errno = owner->error;
        return owner->terminal;
    }
    if (owner->state == OPENING || owner->state == BORROWING || owner->state == CLOSING) {
        errno = EBUSY;
        return GCA_MOUNT_HOLD;
    }
    owner->state = CLOSING;
    struct statx proc;
    if (owner->create_attempted && (current(owner, &proc) < 0 || current_pairs(owner, 0) < 0))
        (void)hold(owner, errno);
    for (unsigned i = GCA_COUNT; i > 0; --i) {
        struct mount_cell *cell = &owner->role[i - 1];
        close_fd(owner, &cell->backing.mounted_root_fd);
        close_fd(owner, &cell->context);
        close_fd(owner, &cell->backing.loop_fd);
        close_fd(owner, &cell->backing.payload_fd);
    }
    close_fd(owner, &owner->ns);
    close_fd(owner, &owner->proc);
    owner->terminal = release_result(owner->create_attempted, owner->error);
    owner->state = CLOSED;
    if (owner->error) errno = owner->error;
    return owner->terminal;
}
#endif
