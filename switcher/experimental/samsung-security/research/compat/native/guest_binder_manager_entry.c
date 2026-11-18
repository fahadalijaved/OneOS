#define _GNU_SOURCE
#include "guest_binder_manager_entry.h"
#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define LOOKUP (AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW)
#define MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_NLINK | STATX_SIZE | STATX_MNT_ID)
#define IMAGE_FLAGS (ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC)
#define DIR_OPEN (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define FILE_OPEN (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)

static atomic_flag attempted = ATOMIC_FLAG_INIT;

/* The exact original manager names /system/bin/bootstrap/linker64 in PT_INTERP. */
static const struct image_pin {
    size_t size;
    unsigned char sha256[32];
} manager = {137440, {
    0xfa,0x9f,0xc5,0x89,0x46,0xbf,0x6e,0x67,0x76,0x61,0xc3,0xa8,0xbb,0x00,0xed,0x0f,
    0x96,0xec,0x97,0x43,0xef,0x92,0xf1,0xeb,0x54,0xf8,0x88,0x82,0xd1,0x08,0x88,0x82
}}, linker = {2592216, {
    0x15,0x0c,0xcf,0x67,0x0e,0x2e,0xba,0x54,0x5c,0xf5,0x59,0xd7,0x9c,0x32,0x99,0x68,
    0x71,0x52,0x6c,0x7c,0xfd,0x4b,0x84,0x04,0xe4,0x29,0x97,0x5d,0x2b,0xe0,0x9f,0xd7
}};

static const struct named_node {
    enum guest_binder_manager_entry_node node, parent;
    const char *name;
} paths[] = {
    {GBME_DEV, GBME_ROOT, "dev"},
    {GBME_BINDER, GBME_DEV, "binder"},
    {GBME_SYSTEM, GBME_ROOT, "system"},
    {GBME_BIN, GBME_SYSTEM, "bin"},
    {GBME_BOOTSTRAP, GBME_BIN, "bootstrap"},
    {GBME_EXECUTABLE, GBME_BIN, "servicemanager"},
    {GBME_INTERPRETER, GBME_BOOTSTRAP, "linker64"},
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_once(struct guest_binder_manager_entry_owner *owner, int *cell) {
    int fd = *cell;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) {
        owner->close_error = errno ? errno : EIO;
    }
}

static int mount_namespace(int fd, struct stat *identity) {
    struct statfs fs;
    if (fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !identity->st_ino) return refuse(EXDEV);
    int kind = ioctl(fd, NS_GET_NSTYPE);
    if (kind < 0) return -1;
    return kind == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int same_namespace(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int namespaces(const struct guest_binder_manager_entry_owner *owner, struct stat *current) {
    struct stat parent, self, actual_parent;
    struct statfs proc;
    char path[64];
    if (getpid() != owner->source_pid || getppid() != owner->parent_pid || owner->parent_pid <= 1) {
        return refuse(ECHILD);
    }
    int size = snprintf(path, sizeof(path), "/proc/%ld/ns/mnt", (long)owner->parent_pid);
    if (size < 0 || (size_t)size >= sizeof(path)) return refuse(EOVERFLOW);
    if (statfs("/proc", &proc) < 0) return -1;
    if ((unsigned long)proc.f_type != PROC_SUPER_MAGIC) return refuse(EXDEV);
    if (mount_namespace(owner->parent_namespace_fd, &parent) < 0 ||
            mount_namespace(owner->namespace_fd, current) < 0 || stat("/proc/self/ns/mnt", &self) < 0 ||
            stat(path, &actual_parent) < 0) return -1;
    if (getppid() != owner->parent_pid || !same_namespace(&parent, &actual_parent) ||
            !same_namespace(current, &self) || same_namespace(current, &parent)) return refuse(EXDEV);
    return 0;
}

static int identity(int fd, const char *name, struct statx *value) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), MASK, value) < 0) return -1;
    if ((value->stx_mask & MASK) != MASK || !value->stx_mnt_id || !value->stx_nlink ||
            (value->stx_attributes & STATX_ATTR_AUTOMOUNT)) return refuse(EXDEV);
    return 0;
}

static int same_fs(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return same_fs(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
            a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid && a->stx_nlink == b->stx_nlink &&
            a->stx_rdev_major == b->stx_rdev_major && a->stx_rdev_minor == b->stx_rdev_minor &&
            (!S_ISREG(a->stx_mode) || a->stx_size == b->stx_size);
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_inode(a, b) && a->stx_mnt_id == b->stx_mnt_id;
}

static int filesystem(int fd, unsigned long magic, unsigned long mask, unsigned long expected) {
    struct statfs fs;
    struct statvfs options;
    if (fstatfs(fd, &fs) < 0 || fstatvfs(fd, &options) < 0) return -1;
    if ((unsigned long)fs.f_type != magic || (options.f_flag & mask) != expected) return refuse(EXDEV);
    return 0;
}

static int binder_witness(int fd) {
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0) return -1;
    if (!(flags & O_PATH)) return refuse(EXDEV);
    return filesystem(fd, BINDERFS_SUPER_MAGIC, IMAGE_FLAGS, ST_NOSUID | ST_NOEXEC);
}

static int image_pin_check(int fd, const struct image_pin *pin) {
    struct guest_tree_sha256 hash;
    unsigned char buffer[16384], digest[32];
    size_t offset = 0;
    guest_tree_sha256_init(&hash);
    while (offset < pin->size) {
        size_t count = pin->size - offset;
        if (count > sizeof(buffer)) count = sizeof(buffer);
        ssize_t got = pread(fd, buffer, count, (off_t)offset);
        if (got < 0) return -1;
        if (!got || (size_t)got > count) return refuse(EIO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        offset += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)offset);
    if (tail < 0) return -1;
    if (tail != 0) return refuse(ESTALE);
    guest_tree_sha256_final(&hash, digest);
    return memcmp(digest, pin->sha256, sizeof(digest)) ? refuse(EBADMSG) : 0;
}

static int open_image_nodes(struct guest_binder_manager_entry_owner *owner) {
    const struct statx *root = &owner->identities[GBME_ROOT];
    for (size_t i = 2; i < sizeof(paths) / sizeof(*paths); ++i) {
        const struct named_node *path = &paths[i];
        const int parent = owner->nodes[path->parent];
        struct statx named;
        const struct image_pin *pin = NULL;
        if (path->node == GBME_EXECUTABLE) pin = &manager;
        if (path->node == GBME_INTERPRETER) pin = &linker;
        if (identity(parent, path->name, &named) < 0) return -1;
        if (!same_fs(root, &named) || named.stx_mnt_id != root->stx_mnt_id) return refuse(EXDEV);
        if (pin ? (!S_ISREG(named.stx_mode) || named.stx_size != pin->size ||
                    !(named.stx_mode & S_IXOTH) || (named.stx_mode & (S_IWGRP | S_IWOTH | S_ISUID | S_ISGID)))
                : !S_ISDIR(named.stx_mode)) return refuse(EACCES);
        const int fd = owner->nodes[path->node] = openat(parent, path->name, pin ? FILE_OPEN : DIR_OPEN);
        struct statx *held = &owner->identities[path->node];
        if (fd < 0 || identity(fd, "", held) < 0) return -1;
        if (!same_object(held, &named)) return refuse(ESTALE);
    }
    return 0;
}

static int recheck_inputs(const struct guest_binder_manager_entry_owner *owner) {
    struct stat current;
    struct statx actual;
    const unsigned long flags = ST_RDONLY | ST_NOSUID | ST_NODEV | (owner->noexec ? ST_NOEXEC : 0);
    if (namespaces(owner, &current) < 0) return -1;
    for (size_t i = 0; i < GBME_NODE_COUNT; ++i) {
        if (identity(owner->nodes[i], "", &actual) < 0) return -1;
        if (!same_object(&owner->identities[i], &actual)) return refuse(ESTALE);
    }
    for (size_t i = 0; i < sizeof(paths) / sizeof(*paths); ++i) {
        const struct named_node *path = &paths[i];
        if (identity(owner->nodes[path->parent], path->name, &actual) < 0) return -1;
        if (!same_object(&owner->identities[path->node], &actual)) return refuse(ESTALE);
    }
    if (binder_witness(owner->nodes[GBME_CREATOR_NODE]) < 0 || binder_witness(owner->nodes[GBME_BINDER]) < 0 ||
            filesystem(owner->nodes[GBME_DEV], TMPFS_MAGIC, IMAGE_FLAGS, ST_NOSUID | ST_NODEV | ST_NOEXEC) < 0 ||
            filesystem(owner->nodes[GBME_ROOT], EROFS_SUPER_MAGIC_V1, IMAGE_FLAGS, flags) < 0 ||
            filesystem(owner->nodes[GBME_EXECUTABLE], EROFS_SUPER_MAGIC_V1, IMAGE_FLAGS, flags) < 0 ||
            filesystem(owner->nodes[GBME_INTERPRETER], EROFS_SUPER_MAGIC_V1, IMAGE_FLAGS, flags) < 0) return -1;
    return namespaces(owner, &current);
}

static int capture_inputs(struct guest_binder_manager_entry_owner *owner,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created,
        const struct guest_binder_attach_owner *attached) {
    owner->parent_namespace_fd = fcntl(input->witnesses[GTC_PARENT_NAMESPACE], F_DUPFD_CLOEXEC, 3);
    if (owner->parent_namespace_fd < 0) return -1;
    owner->namespace_fd = fcntl(view->rights[GTC_NAMESPACE], F_DUPFD_CLOEXEC, 3);
    struct stat current, creator_namespace;
    if (owner->namespace_fd < 0 || namespaces(owner, &current) < 0 ||
            mount_namespace(created->namespace_fd, &creator_namespace) < 0) return -1;
    if (!same_namespace(&creator_namespace, &current) ||
            (uint64_t)current.st_dev != view->observation.namespace_dev ||
            (uint64_t)current.st_ino != view->observation.namespace_inode) return refuse(EXDEV);
    const int borrowed[] = {view->rights[GTC_GUEST_ROOT], view->rights[GTC_DEV], created->device_fd, attached->attached_fd};
    for (size_t i = 0; i < sizeof(borrowed) / sizeof(*borrowed); ++i) {
        int fd = owner->nodes[i] = fcntl(borrowed[i], F_DUPFD_CLOEXEC, 3);
        if (fd < 0 || identity(fd, "", &owner->identities[i]) < 0) return -1;
    }
    const struct statx *root = &owner->identities[GBME_ROOT], *dev = &owner->identities[GBME_DEV];
    const struct statx *source = &owner->identities[GBME_CREATOR_NODE], *binder = &owner->identities[GBME_BINDER];
    if (!S_ISDIR(root->stx_mode) || root->stx_mnt_id != view->observation.mounts[GTC_GUEST_ROOT] ||
            !S_ISDIR(dev->stx_mode) || dev->stx_mnt_id != view->observation.mounts[GTC_DEV] ||
            !S_ISCHR(binder->stx_mode) || !same_inode(source, binder) ||
            source->stx_mnt_id == binder->stx_mnt_id || source->stx_mnt_id != created->device_mount_id ||
            binder->stx_mnt_id != attached->attached_mount_id || binder->stx_mnt_id == dev->stx_mnt_id ||
            source->stx_ino != created->device_inode || source->stx_rdev_major != created->device_major ||
            source->stx_rdev_minor != created->device_minor) return refuse(EXDEV);

    struct statvfs options;
    if (fstatvfs(owner->nodes[GBME_ROOT], &options) < 0) return -1;
    owner->noexec = (options.f_flag & ST_NOEXEC) != 0;
    const unsigned long flags = ST_RDONLY | ST_NOSUID | ST_NODEV | (owner->noexec ? ST_NOEXEC : 0);
    if (filesystem(owner->nodes[GBME_ROOT], EROFS_SUPER_MAGIC_V1, IMAGE_FLAGS, flags) < 0 ||
            open_image_nodes(owner) < 0 || recheck_inputs(owner) < 0 ||
            image_pin_check(owner->nodes[GBME_EXECUTABLE], &manager) < 0 ||
            image_pin_check(owner->nodes[GBME_INTERPRETER], &linker) < 0) return -1;
    return recheck_inputs(owner);
}

int guest_binder_manager_entry_prepare(struct guest_binder_manager_entry_owner *owner,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        const struct guest_binder_context_owner *created,
        const struct guest_binder_attach_owner *attached) {
    if (!owner || owner->state != GBME_EMPTY || owner->source_pid || owner->parent_pid ||
            owner->parent_namespace_fd != -1 || owner->namespace_fd != -1 || owner->close_error || owner->noexec ||
            !input || !input->witnesses || !view || !created || !attached ||
            input->parent <= 1 || created->state != GUEST_BINDER_CONTEXT_DEVICE_HELD || created->close_error ||
            created->fs_context_fd != -1 || created->control_fd != -1 ||
            attached->state != GUEST_BINDER_ATTACH_NODE_HELD || attached->close_error) return refuse(EINVAL);
    for (size_t i = 0; i < GBME_NODE_COUNT; ++i) if (owner->nodes[i] != -1) return refuse(EINVAL);
    pid_t self = getpid();
    if (created->source_pid != self || attached->source_pid != self || getppid() != input->parent) return refuse(ECHILD);
    if (atomic_flag_test_and_set_explicit(&attempted, memory_order_relaxed)) return refuse(EALREADY);
    owner->state = GBME_STARTED;
    owner->source_pid = self;
    owner->parent_pid = input->parent;
    if (capture_inputs(owner, input, view, created, attached) < 0) {
        owner->state = GBME_REFUSED;
        return -1;
    }
    owner->state = GBME_INPUTS_HELD;
    return 0;
}

int guest_binder_manager_entry_recheck(struct guest_binder_manager_entry_owner *owner) {
    if (!owner || owner->state != GBME_INPUTS_HELD || owner->source_pid != getpid()) return refuse(EINVAL);
    if (owner->noexec || recheck_inputs(owner) < 0) {
        owner->state = GBME_REFUSED;
        return owner->noexec ? refuse(EACCES) : -1;
    }
    return 0;
}

int guest_binder_manager_entry_close(struct guest_binder_manager_entry_owner *owner) {
    if (!owner || owner->state == GBME_EMPTY || owner->source_pid != getpid()) return refuse(EINVAL);
    if (owner->state != GBME_RETIRED) {
        owner->state = GBME_RETIRED;
        for (size_t i = GBME_NODE_COUNT; i > 0; --i) close_once(owner, &owner->nodes[i - 1]);
        close_once(owner, &owner->namespace_fd);
        close_once(owner, &owner->parent_namespace_fd);
    }
    return owner->close_error ? refuse(owner->close_error) : 0;
}
