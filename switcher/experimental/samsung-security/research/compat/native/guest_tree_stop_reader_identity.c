#define _GNU_SOURCE 1
#include "guest_tree_stop_reader_identity.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READ_FILE (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_INO | STATX_MNT_ID)
#define STATUS_CAPACITY 16385

enum slot { PROC, SYS, KERNEL, RANDOM, PROCESS, NS, ATTR, COUNT };

struct anchor {
    int fd, parent;
    const char *name;
    struct statx identity;
};

struct namespace_owner {
    int fd, kind;
    const char *name;
    struct statx link;
    struct stat identity;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int fs_type(int fd, unsigned long expected) {
    struct statfs value;
    if (fstatfs(fd, &value) < 0) return -1;
    return (unsigned long)value.f_type == expected ? 0 : refuse(EXDEV);
}

static int identify(int fd, const char *name, mode_t type, struct statx *id) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_ino && id->stx_mnt_id &&
        (id->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major &&
        a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino;
}

static int current(const struct anchor *node, mode_t type) {
    struct statx held, named;
    if (identify(node->fd, "", type, &held) < 0 || identify(node->parent, node->name, type, &named) < 0)
        return -1;
    return same_node(&node->identity, &held) && same_node(&node->identity, &named) ? 0 : refuse(ESTALE);
}

static int open_node(struct anchor *node, int flags, mode_t type, const struct statx *proc) {
    node->fd = openat(node->parent, node->name, flags);
    if (node->fd < 0 || identify(node->fd, "", type, &node->identity) < 0) return -1;
    return same_mount(&node->identity, proc) ? current(node, type) : refuse(EXDEV);
}

static int anchors_current(const struct anchor nodes[COUNT]) {
    for (int slot = PROC; slot < COUNT; ++slot) {
        if (current(&nodes[slot], S_IFDIR) < 0) return -1;
    }
    return 0;
}

static int namespace_current(const struct namespace_owner *owner, int parent) {
    struct statx link;
    struct stat held, named;
    if (identify(parent, owner->name, S_IFLNK, &link) < 0) return -1;
    if (!same_node(&owner->link, &link)) return refuse(ESTALE);
    if (fstat(owner->fd, &held) < 0 || fstatat(parent, owner->name, &named, 0) < 0 ||
            identify(parent, owner->name, S_IFLNK, &link) < 0) return -1;
    return same_node(&owner->link, &link) && held.st_dev == owner->identity.st_dev &&
        named.st_dev == held.st_dev && held.st_ino == owner->identity.st_ino &&
        named.st_ino == held.st_ino ? 0 : refuse(ESTALE);
}

static int open_namespace(struct namespace_owner *owner, int parent, const struct statx *proc) {
    if (identify(parent, owner->name, S_IFLNK, &owner->link) < 0) return -1;
    if (!same_mount(proc, &owner->link)) return refuse(EXDEV);
    /* Follow only the verified procfs namespace link. */
    owner->fd = openat(parent, owner->name, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
    if (owner->fd < 0 || fs_type(owner->fd, NSFS_MAGIC) < 0 || fstat(owner->fd, &owner->identity) < 0)
        return -1;
    int kind = ioctl(owner->fd, NS_GET_NSTYPE);
    if (kind < 0) return -1;
    if (kind != owner->kind || !S_ISREG(owner->identity.st_mode) || !owner->identity.st_ino)
        return refuse(EXDEV);
    return namespace_current(owner, parent);
}

static int read_text(int parent, const char *name, const struct statx *proc, char *text, size_t capacity,
        size_t *length) {
    struct anchor file = {.fd = -1, .parent = parent, .name = name};
    int failure = 0;
    size_t used = 0;
    if (open_node(&file, READ_FILE, S_IFREG, proc) < 0) failure = errno;
    while (!failure) {
        ssize_t count = read(file.fd, text + used, capacity - used);
        if (count < 0) { failure = errno; break; }
        if (!count) break;
        used += (size_t)count;
        if (used == capacity) failure = EOVERFLOW;
    }
    if (!failure && current(&file, S_IFREG) < 0) failure = errno;
    if (file.fd >= 0 && close(file.fd) < 0 && !failure) failure = errno;
    if (failure) return refuse(failure);
    *length = used;
    return 0;
}

static int digit(char c) { return c >= '0' && c <= '9'; }
static int space(char c) { return c == ' ' || c == '\t'; }

static int read_boot(int directory, const struct statx *proc, char boot[37]) {
    char text[38];
    size_t length;
    if (read_text(directory, "boot_id", proc, text, sizeof(text), &length) < 0) return -1;
    if (length != 37 || text[36] != '\n') return refuse(EPROTO);
    for (unsigned i = 0; i < 36; ++i) {
        char c = text[i];
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (c != '-') return refuse(EPROTO);
        } else if (!digit(c) && !(c >= 'a' && c <= 'f')) return refuse(EPROTO);
    }
    memcpy(boot, text, 36);
    boot[36] = '\0';
    return 0;
}

static int four_ids(const char *start, const char *end, uint32_t ids[4]) {
    for (unsigned field = 0; field < 4; ++field) {
        if (start == end || !space(*start)) return refuse(EPROTO);
        while (start != end && space(*start)) ++start;
        if (start == end || !digit(*start)) return refuse(EPROTO);
        uint32_t value = 0;
        while (start != end && digit(*start)) {
            unsigned next = (unsigned)(*start++ - '0');
            if (value > (UINT32_MAX - next) / 10) return refuse(EOVERFLOW);
            value = value * 10 + next;
        }
        ids[field] = value;
    }
    return start == end ? 0 : refuse(EPROTO);
}

static int read_credentials(int process, const struct statx *proc, struct guest_tree_stop_reader_identity *out) {
    char text[STATUS_CAPACITY];
    size_t length;
    if (read_text(process, "status", proc, text, sizeof(text), &length) < 0) return -1;
    if (!length || text[length - 1] != '\n' || memchr(text, '\0', length)) return refuse(EPROTO);
    uint32_t uid[4], gid[4];
    unsigned found = 0;
    for (const char *row = text, *end = text + length; row != end;) {
        const char *line = memchr(row, '\n', (size_t)(end - row));
        if (line - row >= 4 && !memcmp(row, "Uid:", 4)) {
            if (found & 1) return refuse(EPROTO);
            if (four_ids(row + 4, line, uid) < 0) return -1;
            found |= 1;
        } else if (line - row >= 4 && !memcmp(row, "Gid:", 4)) {
            if (found & 2) return refuse(EPROTO);
            if (four_ids(row + 4, line, gid) < 0) return -1;
            found |= 2;
        }
        row = line + 1;
    }
    if (found != 3) return refuse(EPROTO);
    uid_t real_uid, effective_uid, saved_uid;
    gid_t real_gid, effective_gid, saved_gid;
    if (getresuid(&real_uid, &effective_uid, &saved_uid) < 0 ||
            getresgid(&real_gid, &effective_gid, &saved_gid) < 0) return -1;
    if (uid[0] != real_uid || uid[1] != effective_uid || uid[2] != saved_uid ||
            gid[0] != real_gid || gid[1] != effective_gid || gid[2] != saved_gid) return refuse(ESTALE);
    out->uid = uid[0]; out->euid = uid[1]; out->fsuid = uid[3];
    out->gid = gid[0]; out->egid = gid[1]; out->fsgid = gid[3];

    gid_t groups[GUEST_TREE_STOP_READER_GROUP_CAPACITY];
    int count = getgroups(GUEST_TREE_STOP_READER_GROUP_CAPACITY, groups);
    if (count < 0) return -1;
    if (count > GUEST_TREE_STOP_READER_GROUP_CAPACITY) return refuse(EOVERFLOW);
    for (int i = 0; i < count; ++i) {
        if (i && groups[i - 1] >= groups[i]) return refuse(EPROTO);
        out->groups[i] = groups[i];
    }
    out->group_count = (uint32_t)count;
    return 0;
}

static int context_name(char c) {
    return digit(c) || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
        c == '_' || c == '.' || c == '-';
}

static int read_context(int directory, const struct statx *proc, char context[193]) {
    char text[194];
    size_t length;
    if (read_text(directory, "current", proc, text, sizeof(text), &length) < 0) return -1;
    if (length && (text[length - 1] == '\0' || text[length - 1] == '\n')) --length;
    if (!length || length > 192) return refuse(EPROTO);
    const char *p = text, *end = text + length;
    for (unsigned field = 0; field < 3; ++field) {
        const char *start = p;
        while (p < end && context_name(*p)) ++p;
        if (p == start || p == end || *p++ != ':') return refuse(EPROTO);
    }
    if (end - p < 2 || end - p > 82 || p[0] != 's' || !digit(p[1])) return refuse(EPROTO);
    for (p += 2; p < end; ++p) {
        if (!digit(*p) && *p != 's' && *p != 'c' && *p != ',' && *p != '.' && *p != ':' && *p != '-')
            return refuse(EPROTO);
    }
    memcpy(context, text, length);
    context[length] = '\0';
    return 0;
}

static int sample_identity(const struct anchor nodes[COUNT], const struct namespace_owner *mount,
        const struct namespace_owner *time, pid_t pid, struct guest_tree_stop_reader_identity *out) {
    const struct statx *proc = &nodes[PROC].identity;
    enum guest_tree_stop_proc_result result = guest_tree_stop_proc_read(nodes[PROC].fd, pid, 1, &out->birth);
    if (result != GUEST_TREE_STOP_PROC_LIVE) return result == GUEST_TREE_STOP_PROC_ABSENT ? refuse(ESTALE) : -1;
    if (out->birth.pid != pid || !out->birth.start_ticks || out->birth.pid_ns_dev || out->birth.pid_ns_ino)
        return refuse(ESTALE);
    if (read_boot(nodes[RANDOM].fd, proc, out->boot_id) < 0 ||
            read_credentials(nodes[PROCESS].fd, proc, out) < 0 ||
            read_context(nodes[ATTR].fd, proc, out->selinux_context) < 0) return -1;
    out->proc_mount_id = proc->stx_mnt_id;
    out->proc_root_inode = proc->stx_ino;
    out->proc_device_major = proc->stx_dev_major;
    out->proc_device_minor = proc->stx_dev_minor;
    out->mount_ns_inode = mount->identity.st_ino;
    out->mount_ns_device_major = major(mount->identity.st_dev);
    out->mount_ns_device_minor = minor(mount->identity.st_dev);
    out->time_ns_inode = time->identity.st_ino;
    out->time_ns_device_major = major(time->identity.st_dev);
    out->time_ns_device_minor = minor(time->identity.st_dev);
    return 0;
}

int guest_tree_stop_reader_identity_equal(const struct guest_tree_stop_reader_identity *a,
        const struct guest_tree_stop_reader_identity *b) {
    return a && b && a->birth.pid == b->birth.pid && a->birth.start_ticks == b->birth.start_ticks &&
        a->birth.pid_ns_dev == b->birth.pid_ns_dev && a->birth.pid_ns_ino == b->birth.pid_ns_ino &&
        a->proc_mount_id == b->proc_mount_id && a->proc_root_inode == b->proc_root_inode &&
        a->proc_device_major == b->proc_device_major && a->proc_device_minor == b->proc_device_minor &&
        a->mount_ns_inode == b->mount_ns_inode && a->mount_ns_device_major == b->mount_ns_device_major &&
        a->mount_ns_device_minor == b->mount_ns_device_minor && a->time_ns_inode == b->time_ns_inode &&
        a->time_ns_device_major == b->time_ns_device_major && a->time_ns_device_minor == b->time_ns_device_minor &&
        a->uid == b->uid && a->euid == b->euid && a->fsuid == b->fsuid &&
        a->gid == b->gid && a->egid == b->egid && a->fsgid == b->fsgid &&
        a->group_count == b->group_count && a->group_count <= GUEST_TREE_STOP_READER_GROUP_CAPACITY &&
        !memcmp(a->groups, b->groups, a->group_count * sizeof(a->groups[0])) &&
        !strncmp(a->boot_id, b->boot_id, sizeof(a->boot_id)) &&
        !strncmp(a->selinux_context, b->selinux_context, sizeof(a->selinux_context));
}

int guest_tree_stop_reader_identity_read(int proc_fd, struct guest_tree_stop_reader_identity *out) {
    if (!out) return refuse(EINVAL);
    memset(out, 0, sizeof(*out));
    if (proc_fd < 0) return refuse(EBADF);
    pid_t pid = getpid();
    if (pid <= 0 || pid != gettid()) return refuse(EPERM);
    char name[11];
    int length = snprintf(name, sizeof(name), "%ld", (long)pid);
    if (length <= 0 || (size_t)length >= sizeof(name)) return refuse(EOVERFLOW);

    struct anchor nodes[COUNT] = {
        [PROC] = {.fd = proc_fd, .parent = AT_FDCWD, .name = "/proc"},
        [SYS] = {.fd = -1, .name = "sys"}, [KERNEL] = {.fd = -1, .name = "kernel"},
        [RANDOM] = {.fd = -1, .name = "random"}, [PROCESS] = {.fd = -1, .name = name},
        [NS] = {.fd = -1, .name = "ns"}, [ATTR] = {.fd = -1, .name = "attr"},
    };
    const int parents[COUNT] = {[SYS] = PROC, [KERNEL] = SYS, [RANDOM] = KERNEL,
                                [PROCESS] = PROC, [NS] = PROCESS, [ATTR] = PROCESS};
    struct namespace_owner mount = {.fd = -1, .kind = CLONE_NEWNS, .name = "mnt"};
    struct namespace_owner time = {.fd = -1, .kind = CLONE_NEWTIME, .name = "time"};
    struct guest_tree_stop_reader_identity first = {0}, second = {0};
    const struct statx *proc = &nodes[PROC].identity;
    int failure = 0;
    if (fs_type(proc_fd, PROC_SUPER_MAGIC) < 0 || identify(proc_fd, "", S_IFDIR, &nodes[PROC].identity) < 0)
        goto refused;
    if (proc->stx_ino != 1) { errno = EXDEV; goto refused; }
    for (int slot = SYS; slot < COUNT; ++slot) {
        nodes[slot].parent = nodes[parents[slot]].fd;
        if (open_node(&nodes[slot], DIRECTORY, S_IFDIR, proc) < 0) goto refused;
    }
    if (anchors_current(nodes) < 0 || open_namespace(&mount, nodes[NS].fd, proc) < 0 ||
            open_namespace(&time, nodes[NS].fd, proc) < 0 ||
            sample_identity(nodes, &mount, &time, pid, &first) < 0 ||
            sample_identity(nodes, &mount, &time, pid, &second) < 0 ||
            namespace_current(&mount, nodes[NS].fd) < 0 || namespace_current(&time, nodes[NS].fd) < 0 ||
            anchors_current(nodes) < 0) goto refused;
    if (!guest_tree_stop_reader_identity_equal(&first, &second)) { errno = ESTALE; goto refused; }
    goto close_owned;

refused:
    failure = errno ? errno : EIO;
close_owned:
    if (time.fd >= 0 && close(time.fd) < 0 && !failure) failure = errno ? errno : EIO;
    if (mount.fd >= 0 && close(mount.fd) < 0 && !failure) failure = errno ? errno : EIO;
    for (int slot = COUNT - 1; slot > PROC; --slot) {
        if (nodes[slot].fd >= 0 && close(nodes[slot].fd) < 0 && !failure) failure = errno ? errno : EIO;
    }
    if (failure) return refuse(failure);
    *out = first;
    return 0;
}
