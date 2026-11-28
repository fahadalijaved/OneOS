#define _GNU_SOURCE
#include "guest_tree_stop_proc.h"

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
#include <unistd.h>

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_INO | STATX_MNT_ID)
#define PROC_ROOT_INO 1
#define STAT_LIMIT 4096

static int refuse(int error) {
    errno = error;
    return -1;
}

static int fs_type(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : refuse(EXDEV);
}

static int identify(int fd, const char *name, mode_t type, struct statx *id) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, id) < 0) return -1;
    return (id->stx_mask & ID_MASK) == ID_MASK && id->stx_ino && id->stx_mnt_id
        && (id->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int current_node(int fd, int parent, const char *name, mode_t type, const struct statx *id) {
    struct statx held, named;
    if (identify(fd, "", type, &held) < 0 || identify(parent, name, type, &named) < 0) return -1;
    return same_mount(id, &held) && same_mount(id, &named) && held.stx_ino == id->stx_ino
        && named.stx_ino == id->stx_ino ? 0 : refuse(ESTALE);
}

static int digit(char c) { return c >= '0' && c <= '9'; }

static int parse_ticks(const char *text, size_t size, const char *pid, size_t pid_length, uint64_t *ticks) {
    if (size <= pid_length + 7 || memcmp(text, pid, pid_length) || text[pid_length] != ' '
        || text[pid_length + 1] != '(' || text[size - 1] != '\n' || memchr(text, '\0', size))
        return refuse(EPROTO);

    /* comm can contain spaces, newlines and either parenthesis. The suffix
     * contains only the state byte and numbers, so use its last close paren. */
    const char *end = text + size;
    const char *p = end;
    while (p > text + pid_length + 2 && p[-1] != ')') --p;
    if (p <= text + pid_length + 2 || end - p < 5 || p[0] != ' ' || p[2] != ' '
        || !p[1] || !strchr("RSDTtXZxPKWI", p[1])) return refuse(EPROTO);
    p += 3;

    /* Fields 4 through 21 precede the unsigned starttime at field 22. */
    for (int field = 4; field < 22; ++field) {
        if (p < end && *p == '-') ++p;
        const char *first = p;
        while (p < end && digit(*p)) ++p;
        if (p == first || p - first > 20 || p == end || *p != ' ') return refuse(EPROTO);
        ++p;
    }
    uint64_t value = 0;
    const char *first = p;
    while (p < end && digit(*p)) {
        unsigned next = (unsigned)(*p++ - '0');
        if (value > (UINT64_MAX - next) / 10) return refuse(EOVERFLOW);
        value = value * 10 + next;
    }
    if (p == first || p == end || *p != ' ' || !value) return refuse(EPROTO);
    *ticks = value;
    return 0;
}

static int read_ticks(int process, const struct statx *proc, const char *pid, size_t pid_length,
        uint64_t *ticks) {
    int fd = openat(process, "stat", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int error = 0;
    struct statx file;
    char text[STAT_LIMIT + 1];
    size_t used = 0;
    if (identify(fd, "", S_IFREG, &file) < 0) error = errno;
    else if (!same_mount(proc, &file)) error = EXDEV;
    else if (current_node(fd, process, "stat", S_IFREG, &file) < 0) error = errno;
    while (!error) {
        ssize_t got = read(fd, text + used, sizeof(text) - used);
        if (got < 0) { error = errno; break; }
        if (!got) break;
        used += (size_t)got;
        if (used > STAT_LIMIT) error = EOVERFLOW;
    }
    if (!error && (parse_ticks(text, used, pid, pid_length, ticks) < 0
            || current_node(fd, process, "stat", S_IFREG, &file) < 0)) error = errno;
    if (close(fd) < 0 && !error) error = errno;
    return error ? refuse(error) : 0;
}

static int read_namespace(int process, const struct statx *proc, int expect_no_pid_namespace, struct stat *id) {
    int directory = openat(process, "ns", DIRECTORY);
    if (directory < 0) return -1;
    int fd = -1, error = 0;
    struct statx dir_id, before, after;
    struct stat named;
    if (identify(directory, "", S_IFDIR, &dir_id) < 0) error = errno;
    else if (!same_mount(proc, &dir_id)) error = EXDEV;
    else if (current_node(directory, process, "ns", S_IFDIR, &dir_id) < 0) error = errno;
    else if (identify(directory, "pid", S_IFLNK, &before) < 0) {
        if (!expect_no_pid_namespace || errno != ENOENT) error = errno;
        else if (current_node(directory, process, "ns", S_IFDIR, &dir_id) < 0) error = errno;
        else *id = (struct stat){0};
    }
    else if (expect_no_pid_namespace) error = EXDEV;
    else if (!same_mount(proc, &before)) error = EXDEV;
    else {
        /* Follow only the kernel's pid magic link after proving its proc mount. */
        fd = openat(directory, "pid", O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0 || fs_type(fd, NSFS_MAGIC) < 0 || fstat(fd, id) < 0) error = errno;
        else {
            int type = ioctl(fd, NS_GET_NSTYPE);
            if (type < 0) error = errno;
            else if (type != CLONE_NEWPID || !S_ISREG(id->st_mode) || !id->st_ino) error = EXDEV;
            else if (fstatat(directory, "pid", &named, 0) < 0 || identify(directory, "pid", S_IFLNK, &after) < 0
                    || current_node(directory, process, "ns", S_IFDIR, &dir_id) < 0) error = errno;
            else if (named.st_dev != id->st_dev || named.st_ino != id->st_ino || !same_mount(&before, &after)
                    || before.stx_ino != after.stx_ino) error = ESTALE;
        }
    }
    if (fd >= 0 && close(fd) < 0 && !error) error = errno;
    if (close(directory) < 0 && !error) error = errno;
    return error ? refuse(error) : 0;
}

enum guest_tree_stop_proc_result guest_tree_stop_proc_read(int proc_fd, pid_t pid, int expect_no_pid_namespace,
        struct guest_tree_stop_proc_birth *out) {
    if (out) *out = (struct guest_tree_stop_proc_birth){0};
    if (!out || pid <= 0 || (uint64_t)pid > INT32_MAX
            || (expect_no_pid_namespace != 0 && expect_no_pid_namespace != 1)) {
        errno = EINVAL;
        return GUEST_TREE_STOP_PROC_ERROR;
    }
    char name[11];
    int length = snprintf(name, sizeof(name), "%ld", (long)pid);
    if (length <= 0 || (size_t)length >= sizeof(name)) {
        errno = EINVAL;
        return GUEST_TREE_STOP_PROC_ERROR;
    }
    struct statx root, node;
    if (fs_type(proc_fd, PROC_SUPER_MAGIC) < 0 || identify(proc_fd, "", S_IFDIR, &root) < 0)
        return GUEST_TREE_STOP_PROC_ERROR;
    if (root.stx_ino != PROC_ROOT_INO) {
        errno = EXDEV;
        return GUEST_TREE_STOP_PROC_ERROR;
    }

    int process = openat(proc_fd, name, DIRECTORY);
    if (process < 0) return errno == ENOENT ? GUEST_TREE_STOP_PROC_ABSENT : GUEST_TREE_STOP_PROC_ERROR;
    int error = 0;
    uint64_t ticks = 0, repeated = 0;
    struct stat ns, repeated_ns;
    if (identify(process, "", S_IFDIR, &node) < 0) error = errno;
    else if (!same_mount(&root, &node)) error = EXDEV;
    else if (current_node(process, proc_fd, name, S_IFDIR, &node) < 0
            || read_ticks(process, &root, name, (size_t)length, &ticks) < 0
            || read_namespace(process, &root, expect_no_pid_namespace, &ns) < 0
            || read_ticks(process, &root, name, (size_t)length, &repeated) < 0
            || read_namespace(process, &root, expect_no_pid_namespace, &repeated_ns) < 0
            || current_node(process, proc_fd, name, S_IFDIR, &node) < 0) error = errno;
    else if (ticks != repeated || ns.st_dev != repeated_ns.st_dev || ns.st_ino != repeated_ns.st_ino) error = ESTALE;
    if (close(process) < 0 && !error) error = errno;
    if (error) {
        errno = error;
        return GUEST_TREE_STOP_PROC_ERROR;
    }
    *out = (struct guest_tree_stop_proc_birth){pid, ticks, (uint64_t)ns.st_dev, (uint64_t)ns.st_ino};
    return GUEST_TREE_STOP_PROC_LIVE;
}
