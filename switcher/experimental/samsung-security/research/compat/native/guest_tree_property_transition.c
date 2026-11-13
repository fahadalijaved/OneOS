#define _GNU_SOURCE
#include "guest_tree_property_transition.h"

#include "guest_tree_property_child.h"
#include "guest_tree_property_label_owner.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/xattr.h>
#include <unistd.h>

#define SELINUX_PATH "/sys/fs/selinux"
#define PROPERTY_NAME "__properties__"
#define LABEL_NAME "security.selinux"
#define CONTEXT_BYTES 256U
#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READING (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
#define ID_MASK (STATX_TYPE | STATX_MNT_ID | STATX_INO)
#define MEMBER_COUNT 6U

/* Linux v6.12 AArch64 UAPI, including exact SELinux LSM selection. */
#define GTP_LSM_GET_SELF_ATTR 459
#define GTP_LSM_CURRENT 100U
#define GTP_LSM_SELINUX 101U
#define GTP_LSM_SINGLE 1U

static const struct {
    const char *name, *new_label;
} members[MEMBER_COUNT] = {
    {".", "u:object_r:properties_device:s0"},
    {"property_info", "u:object_r:property_info:s0"},
    {"u:object_r:build_prop:s0", "u:object_r:build_prop:s0"},
    {"u:object_r:default_prop:s0", "u:object_r:default_prop:s0"},
    {"u:object_r:vndk_prop:s0", "u:object_r:vndk_prop:s0"},
    {"properties_serial", "u:object_r:properties_serial:s0"},
};

struct policy_status {
    uint32_t version, sequence, enforcing, policyload, deny_unknown;
};

struct held_inode {
    int fd;
    struct statx id;
    char old_label[CONTEXT_BYTES];
};

struct guest_tree_property_transition {
    struct guest_tree_property_child *child;
    pid_t pid;
    int dev_fd, property_fd, selinux, status, ready, error;
    struct statx dev_id, selinux_id, status_id;
    struct held_inode inodes[MEMBER_COUNT];
    char actor[CONTEXT_BYTES];
    struct policy_status policy;
};

static struct guest_tree_property_transition one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int hold(struct guest_tree_property_transition *owner) {
    if (!owner->error) owner->error = errno ? errno : EIO;
    owner->ready = 0;
    return refuse(owner->error);
}

static void close_cell(int *fd, int *error) {
    int actual = *fd;
    *fd = -1;
    if (actual >= 0 && close(actual) < 0 && !*error) *error = errno ? errno : EIO;
}

static int identify(int dir, const char *name, struct statx *id) {
    int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | (*name ? 0 : AT_EMPTY_PATH);
    if (statx(dir, name, flags, ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_mnt_id && id->stx_ino ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major &&
           a->stx_dev_minor == b->stx_dev_minor;
}

static int same_name(int dir, const char *name, const struct statx *expected) {
    struct statx id;
    if (identify(dir, name, &id) < 0) return -1;
    return same_mount(&id, expected) && id.stx_ino == expected->stx_ino
        && (id.stx_mode & S_IFMT) == (expected->stx_mode & S_IFMT) ? 0 : refuse(ESTALE);
}

static int context_text(char text[CONTEXT_BYTES], size_t size) {
    if (!size || size > CONTEXT_BYTES || text[size - 1] != '\0') return refuse(EPROTO);
    unsigned colons = 0;
    for (size_t i = 0; i + 1 < size; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (c == ':') ++colons;
        else if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                (c >= '0' && c <= '9') || c == '_' || c == ',' || c == '.' || c == '-')) return refuse(EPROTO);
    }
    return colons >= 3 ? 0 : refuse(EPROTO);
}

static int actor_context(char text[CONTEXT_BYTES]) {
#if defined(__aarch64__)
    struct {
        uint64_t id, flags, len, context_len;
        char context[CONTEXT_BYTES];
    } record = {.id = GTP_LSM_SELINUX};
    uint32_t size = sizeof(record);
    const size_t header = sizeof(record) - sizeof(record.context);
    long count = syscall(GTP_LSM_GET_SELF_ATTR, GTP_LSM_CURRENT, &record, &size, GTP_LSM_SINGLE);
    if (count < 0) return -1;
    if (count != 1 || record.id != GTP_LSM_SELINUX || record.flags || size > sizeof(record)
            || size < header || record.len != size || !record.context_len
            || record.context_len > size - header
            || size != (header + record.context_len + 7U) / 8U * 8U) return refuse(EPROTO);
    memcpy(text, record.context, (size_t)record.context_len);
    return context_text(text, (size_t)record.context_len);
#else
    (void)text;
    return refuse(EOPNOTSUPP);
#endif
}

static int inode_context(int fd, char text[CONTEXT_BYTES]) {
    ssize_t size = fgetxattr(fd, LABEL_NAME, text, CONTEXT_BYTES);
    return size < 0 ? -1 : context_text(text, (size_t)size);
}

static int capture(struct guest_tree_property_transition *owner) {
    if (guest_tree_property_child_borrow(owner->child, &owner->property_fd) < 0
            || identify(owner->dev_fd, "", &owner->dev_id) < 0) return -1;
    if (!S_ISDIR(owner->dev_id.stx_mode)) return refuse(EXDEV);
    for (size_t i = 0; i < MEMBER_COUNT; ++i) {
        struct held_inode *held = &owner->inodes[i];
        held->fd = openat(owner->property_fd, members[i].name, READING | (!i ? O_DIRECTORY : 0));
        if (held->fd < 0 || identify(held->fd, "", &held->id) < 0
                || same_name(owner->property_fd, members[i].name, &held->id) < 0
                || inode_context(held->fd, held->old_label) < 0) return -1;
        if (!same_mount(&held->id, &owner->dev_id)
                || (held->id.stx_mode & S_IFMT) != (i ? S_IFREG : S_IFDIR)) return refuse(EXDEV);
    }
    if (same_name(owner->dev_fd, PROPERTY_NAME, &owner->inodes[0].id) < 0
            || same_name(owner->property_fd, "", &owner->inodes[0].id) < 0) return -1;
    return same_name(owner->property_fd, "..", &owner->dev_id);
}

static int selinux_node(int dir, const char *name, const struct statx *root, struct statx *id) {
    if (identify(dir, name, id) < 0) return -1;
    return S_ISREG(id->stx_mode) && same_mount(id, root) ? 0 : refuse(EXDEV);
}

static int current_policy(int status, struct policy_status *out) {
    unsigned char bytes[sizeof(*out) + 1];
    ssize_t size = pread(status, bytes, sizeof(bytes), 0);
    if (size < 0) return -1;
    if ((size_t)size != sizeof(*out)) return refuse(EPROTO);
    memcpy(out, bytes, sizeof(*out));
    if (out->version != 1 || (out->sequence & 1) || out->deny_unknown > 1) return refuse(EPROTO);
    return out->enforcing == 1 ? 0 : refuse(EACCES);
}

static int capture_policy(struct guest_tree_property_transition *owner) {
    owner->selinux = open(SELINUX_PATH, DIRECTORY);
    if (owner->selinux < 0) return -1;
    struct statfs fs;
    if (fstatfs(owner->selinux, &fs) < 0 || identify(owner->selinux, "", &owner->selinux_id) < 0) return -1;
    if ((unsigned long)fs.f_type != SELINUX_MAGIC) return refuse(EXDEV);
    owner->status = openat(owner->selinux, "status", READING);
    if (owner->status < 0 || selinux_node(owner->status, "", &owner->selinux_id, &owner->status_id) < 0)
        return -1;
    return current_policy(owner->status, &owner->policy);
}

static int class_value(const char *digits, size_t size, uint16_t *value) {
    if (!size || size > 5 || digits[0] == '0') return refuse(EPROTO);
    unsigned index = 0;
    for (size_t i = 0; i < size; ++i) {
        if (digits[i] < '0' || digits[i] > '9') return refuse(EPROTO);
        index = index * 10U + (unsigned)(digits[i] - '0');
    }
    if (index > UINT16_MAX) return refuse(EPROTO);
    *value = (uint16_t)index;
    return 0;
}

static int read_class(struct guest_tree_property_transition *owner, const char *name, uint16_t *value) {
    int fd = openat(owner->selinux, name, READING);
    if (fd < 0) return -1;
    struct statx id;
    char text[6];
    int error = 0;
    if (selinux_node(fd, "", &owner->selinux_id, &id) < 0) error = errno;
    else {
        ssize_t size = pread(fd, text, sizeof(text), 0);
        if (size < 0 || class_value(text, (size_t)size, value) < 0) error = errno;
    }
    close_cell(&fd, &error);
    return error ? refuse(error) : 0;
}

static int request_text(char *output, size_t capacity, const char *old_label,
        const char *new_label, uint16_t class_id, const char *actor) {
    if (!class_id) return refuse(EPROTO);
    int size = snprintf(output, capacity, "%s %s %u %s", old_label, new_label, (unsigned)class_id, actor);
    return size > 0 && (size_t)size < capacity ? size : refuse(EOVERFLOW);
}

static int validate(struct guest_tree_property_transition *owner, size_t member, uint16_t class_id) {
    char text[3 * CONTEXT_BYTES + 16];
    int size = request_text(text, sizeof(text), owner->inodes[member].old_label,
            members[member].new_label, class_id, owner->actor);
    if (size < 0) return -1;
    int fd = openat(owner->selinux, "validatetrans", O_WRONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    struct statx id;
    int error = 0;
    if (selinux_node(fd, "", &owner->selinux_id, &id) < 0) error = errno;
    else {
        /* Kernel policy query. The response is the whole write count or an error. */
        ssize_t written = write(fd, text, (size_t)size);
        if (written < 0) error = errno;
        else if (written != size) error = EPROTO;
    }
    close_cell(&fd, &error);
    return error ? refuse(error) : 0;
}

static int check_current(struct guest_tree_property_transition *owner) {
    int property = -1;
    char actor[CONTEXT_BYTES];
    struct policy_status state;
    if (guest_tree_property_child_borrow(owner->child, &property) < 0
            || actor_context(actor) < 0 || same_name(owner->dev_fd, "", &owner->dev_id) < 0
            || same_name(owner->dev_fd, PROPERTY_NAME, &owner->inodes[0].id) < 0
            || same_name(AT_FDCWD, SELINUX_PATH, &owner->selinux_id) < 0
            || same_name(owner->selinux, "status", &owner->status_id) < 0) return -1;
    if (property != owner->property_fd || strcmp(actor, owner->actor)) return refuse(ESTALE);
    for (size_t i = 0; i < MEMBER_COUNT; ++i) {
        struct held_inode *held = &owner->inodes[i];
        char label[CONTEXT_BYTES];
        if (same_name(held->fd, "", &held->id) < 0 || same_name(property, members[i].name, &held->id) < 0
                || inode_context(held->fd, label) < 0) return -1;
        if (strcmp(label, held->old_label)) return refuse(ESTALE);
    }
    if (current_policy(owner->status, &state) < 0) return -1;
    return memcmp(&state, &owner->policy, sizeof(state)) ? refuse(ESTALE) : 0;
}

static int same_child(struct guest_tree_property_transition *owner) {
    return owner == &one && owner->pid == getpid() && getpid() == gettid();
}

int guest_tree_property_transition_begin(struct guest_tree_property_child *child,
        int dev_fd, struct guest_tree_property_transition **out) {
    if (!child || dev_fd < 0 || !out || *out) return refuse(EINVAL);
    if (getpid() != gettid()) return refuse(EPERM);
    if (one.pid) return refuse(EALREADY);
    one.pid = getpid();
    one.child = child;
    one.dev_fd = dev_fd;
    one.property_fd = one.selinux = one.status = -1;
    for (size_t i = 0; i < MEMBER_COUNT; ++i) one.inodes[i].fd = -1;
    *out = &one;

    uint16_t directory, file;
    if (capture(&one) < 0 || actor_context(one.actor) < 0 || capture_policy(&one) < 0
            || guest_tree_property_label_preflight(child, dev_fd) < 0
            || check_current(&one) < 0 || read_class(&one, "class/dir/index", &directory) < 0
            || read_class(&one, "class/file/index", &file) < 0) return hold(&one);
    if (directory == file) { errno = EPROTO; return hold(&one); }
    for (size_t i = 0; i < MEMBER_COUNT; ++i) {
        if (validate(&one, i, i ? file : directory) < 0) return hold(&one);
    }
    if (check_current(&one) < 0) return hold(&one);
    one.ready = 1;
    return 0;
}

int guest_tree_property_transition_read(struct guest_tree_property_transition *owner,
        struct guest_tree_property_transition_sample *sample) {
    if (!same_child(owner) || !sample) return refuse(EINVAL);
    *sample = (struct guest_tree_property_transition_sample){0};
    if (!owner->ready) return refuse(owner->error ? owner->error : EBADF);
    if (check_current(owner) < 0) return hold(owner);
    sample->mount_id = owner->dev_id.stx_mnt_id;
    sample->policy_sequence = owner->policy.sequence;
    sample->policy_load = owner->policy.policyload;
    for (size_t i = 0; i < MEMBER_COUNT; ++i) sample->inodes[i] = owner->inodes[i].id.stx_ino;
    return 0;
}

int guest_tree_property_transition_close(struct guest_tree_property_transition *owner) {
    if (!same_child(owner)) return refuse(EINVAL);
    owner->ready = 0;
    for (size_t i = MEMBER_COUNT; i; --i) close_cell(&owner->inodes[i - 1].fd, &owner->error);
    close_cell(&owner->status, &owner->error);
    close_cell(&owner->selinux, &owner->error);
    return owner->error ? refuse(owner->error) : 0;
}
