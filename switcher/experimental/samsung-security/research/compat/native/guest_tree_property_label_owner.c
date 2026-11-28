#define _GNU_SOURCE
#include "guest_tree_property_label_owner.h"

#include "guest_tree_property_child.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdint.h>
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
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define MASK (STATX_TYPE | STATX_MNT_ID | STATX_INO)

/* Linux v6.12 AArch64 UAPI, newer than the existing NDK headers. */
#define GTP_LSM_GET_SELF_ATTR 459
#define GTP_LSM_CURRENT 100U
#define GTP_LSM_SELINUX 101U
#define GTP_LSM_SINGLE 1U

struct member {
    const char *name, *label;
    off_t size;
};

/* Fixed donor labels. The first slot names the property directory itself. */
static const struct member targets[] = {
    {".", "u:object_r:properties_device:s0", 0},
    {"property_info", "u:object_r:property_info:s0", 171544},
    {"u:object_r:build_prop:s0", "u:object_r:build_prop:s0", 262144},
    {"u:object_r:default_prop:s0", "u:object_r:default_prop:s0", 262144},
    {"u:object_r:vndk_prop:s0", "u:object_r:vndk_prop:s0", 262144},
    {"properties_serial", "u:object_r:properties_serial:s0", 262144},
};

struct held_object {
    int fd;
    struct statx id;
    char context[CONTEXT_BYTES];
};

struct av_class {
    uint32_t id, from, to, setattr;
};

/* selinuxfs status ABI version 1, all five fields native-endian u32. */
struct policy_status {
    uint32_t version, sequence, enforcing, policyload, deny_unknown;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static void close_cell(int *fd, int *error) {
    int actual = *fd;
    *fd = -1;
    if (actual >= 0 && close(actual) < 0 && !*error) *error = errno ? errno : EIO;
}

static int identify(int fd, const char *name, struct statx *id) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), MASK, id) < 0) return -1;
    return (id->stx_mask & MASK) == MASK && id->stx_ino && id->stx_mnt_id ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
            && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && (a->stx_mode & S_IFMT) == (b->stx_mode & S_IFMT);
}

static int fstype(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : refuse(EXDEV);
}

static int same_named(int dir, const char *name, const struct statx *held) {
    struct statx current;
    if (identify(dir, name, &current) < 0) return -1;
    return same_object(held, &current) ? 0 : refuse(EXDEV);
}

static int bounded_read(int fd, void *buffer, size_t capacity, size_t *length) {
    unsigned char *data = buffer;
    size_t used = 0;
    while (used < capacity) {
        ssize_t n = read(fd, data + used, capacity - used);
        if (n < 0) return -1;
        if (!n) {
            *length = used;
            return 0;
        }
        used += (size_t)n;
    }
    return refuse(EOVERFLOW);
}

static int sample_read(int base, const char *name, const struct statx *mount,
                       void *bytes, size_t capacity, size_t *length) {
    int fd = openat(base, name, READING);
    if (fd < 0) return -1;
    struct statx file;
    int error = 0;
    if (identify(fd, "", &file) < 0) error = errno;
    else if (!same_mount(&file, mount) || !S_ISREG(file.stx_mode)) error = EXDEV;
    else if (bounded_read(fd, bytes, capacity, length) < 0) error = errno;
    close_cell(&fd, &error);
    return error ? refuse(error) : 0;
}

static int context_text(char text[CONTEXT_BYTES], size_t size) {
    if (size && text[size - 1] == '\0') --size;
    if (!size || size >= CONTEXT_BYTES) return refuse(EPROTO);
    unsigned colons = 0;
    for (size_t i = 0; i < size; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (c == ':') ++colons;
        else if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
                (c >= '0' && c <= '9') || c == '_' || c == ',' || c == '.' || c == '-')) return refuse(EPROTO);
    }
    if (colons < 3) return refuse(EPROTO);
    text[size] = '\0';
    return 0;
}

static int actor_context(char text[CONTEXT_BYTES]) {
#if defined(__aarch64__)
    struct {
        uint64_t id, flags, length, context_length;
        char context[CONTEXT_BYTES];
    } record = {.id = GTP_LSM_SELINUX};
    const size_t header = sizeof(record) - sizeof(record.context);
    uint32_t size = sizeof(record);
    long count = syscall(GTP_LSM_GET_SELF_ATTR, GTP_LSM_CURRENT, &record, &size, GTP_LSM_SINGLE);
    if (count < 0) return -1;
    if (count != 1 || record.id != GTP_LSM_SELINUX || record.flags || size > sizeof(record)
            || size < header || record.length != size || !record.context_length
            || record.context_length > size - header || record.context[record.context_length - 1] != '\0'
            || size != (header + record.context_length + 7U) / 8U * 8U) return refuse(EPROTO);
    memcpy(text, record.context, (size_t)record.context_length);
    return context_text(text, (size_t)record.context_length);
#else
    (void)text;
    return refuse(EOPNOTSUPP);
#endif
}

static int object_context(int fd, char text[CONTEXT_BYTES]) {
    ssize_t size = fgetxattr(fd, LABEL_NAME, text, CONTEXT_BYTES);
    return size < 0 ? -1 : context_text(text, (size_t)size);
}

static int object_mode(int fd, const struct member *member) {
    struct stat st;
    if (fstat(fd, &st) < 0) return -1;
    int directory = !member->size;
    mode_t mode = directory ? S_IFDIR | 0500 : S_IFREG | 0444;
    return st.st_mode == mode && !st.st_uid && !st.st_gid && st.st_nlink == (directory ? 2 : 1)
            && (directory || st.st_size == member->size) ? 0 : refuse(EXDEV);
}

static int held_objects(int prop_fd, int dev_fd, struct held_object *objects) {
    struct statx dev, prop;
    if (fstype(dev_fd, TMPFS_MAGIC) < 0 || identify(dev_fd, "", &dev) < 0 || identify(prop_fd, "", &prop) < 0
            || same_named(dev_fd, PROPERTY_NAME, &prop) < 0 || same_named(prop_fd, "..", &dev) < 0) return -1;
    if (!same_mount(&dev, &prop) || same_object(&dev, &prop)) return refuse(EXDEV);
    for (size_t i = 0; i < sizeof(targets) / sizeof(targets[0]); ++i) {
        const struct member *member = &targets[i];
        struct held_object *held = &objects[i];
        held->fd = openat(prop_fd, member->name, READING | (!i ? O_DIRECTORY : 0));
        if (held->fd < 0 || identify(held->fd, "", &held->id) < 0
                || object_mode(held->fd, member) < 0 || object_context(held->fd, held->context) < 0
                || same_named(prop_fd, member->name, &held->id) < 0) return -1;
        if (!same_mount(&prop, &held->id)) return refuse(EXDEV);
    }
    return same_named(dev_fd, PROPERTY_NAME, &objects[0].id);
}

/* selinuxfs returns unsigned digits without whitespace or terminator. */
static int number(const char **cursor, const char *end, unsigned base, uint32_t *result) {
    const char *start = *cursor;
    uint32_t value = 0;
    while (*cursor < end && **cursor != ' ') {
        unsigned char c = (unsigned char)**cursor;
        unsigned digit;
        if (c >= '0' && c <= '9') digit = c - '0';
        else if (c >= 'a' && c <= 'f') digit = c - 'a' + 10U;
        else return refuse(EPROTO);
        if (digit >= base || value > (UINT32_MAX - digit) / base) return refuse(EPROTO);
        value = value * base + digit;
        ++*cursor;
    }
    if (*cursor == start) return refuse(EPROTO);
    *result = value;
    return 0;
}

static int index_read(int fs, const struct statx *mount, const char *path, uint32_t limit, uint32_t *index) {
    char text[12];
    size_t length;
    if (sample_read(fs, path, mount, text, sizeof(text), &length) < 0) return -1;
    const char *cursor = text, *end = text + length;
    if (number(&cursor, end, 10, index) < 0) return -1;
    return cursor == end && *index && *index <= limit ? 0 : refuse(EPROTO);
}

static int class_read(int fs, const struct statx *mount, struct av_class classes[2]) {
    uint32_t from, to, attr;
    if (index_read(fs, mount, "class/dir/index", UINT16_MAX, &classes[0].id) < 0
            || index_read(fs, mount, "class/dir/perms/relabelfrom", 32, &from) < 0
            || index_read(fs, mount, "class/dir/perms/relabelto", 32, &to) < 0
            || index_read(fs, mount, "class/dir/perms/setattr", 32, &attr) < 0) return -1;
    if (from == to || from == attr || to == attr) return refuse(EPROTO);
    classes[0].from = UINT32_C(1) << (from - 1);
    classes[0].to = UINT32_C(1) << (to - 1);
    classes[0].setattr = UINT32_C(1) << (attr - 1);
    if (index_read(fs, mount, "class/file/index", UINT16_MAX, &classes[1].id) < 0
            || index_read(fs, mount, "class/file/perms/relabelfrom", 32, &from) < 0
            || index_read(fs, mount, "class/file/perms/relabelto", 32, &to) < 0) return -1;
    if (classes[1].id == classes[0].id || from == to) return refuse(EPROTO);
    classes[1].from = UINT32_C(1) << (from - 1);
    classes[1].to = UINT32_C(1) << (to - 1);
    classes[1].setattr = 0;
    return 0;
}

static int policy_read(int fs, const struct statx *mount, struct policy_status *state) {
    unsigned char bytes[sizeof(*state) + 1];
    size_t length;
    if (sample_read(fs, "status", mount, bytes, sizeof(bytes), &length) < 0) return -1;
    if (length != sizeof(*state)) return refuse(EPROTO);
    memcpy(state, bytes, sizeof(*state));
    if (state->version != 1 || (state->sequence & 1) || state->deny_unknown > 1) return refuse(EPROTO);
    return state->enforcing == 1 ? 0 : refuse(EACCES);
}

static int av_decision(const char *text, size_t length, uint32_t needed, uint32_t *generation,
                       int *have_generation) {
    uint32_t columns[6];
    const char *cursor = text, *end = text + length;
    for (size_t i = 0; i < 6; ++i) {
        if (number(&cursor, end, i == 4 ? 10 : 16, &columns[i]) < 0) return -1;
        if (i < 5 && (cursor == end || *cursor++ != ' ')) return refuse(EPROTO);
    }
    if (cursor != end || columns[1] != UINT32_MAX) return refuse(EPROTO);
    /* Exact selected flags field. Permissive and unfamiliar flags refuse. */
    if (columns[5] || (columns[0] & needed) != needed) return refuse(EACCES);
    if (*have_generation && *generation != columns[4]) return refuse(ESTALE);
    *generation = columns[4];
    *have_generation = 1;
    return 0;
}

static int query(int fs, const struct statx *mount, const char *actor, const char *object,
                 uint32_t class_id, uint32_t needed, uint32_t *generation, int *have_generation) {
    char request[2 * CONTEXT_BYTES + 32], response[96];
    int length = snprintf(request, sizeof(request), "%s %s %u %x", actor, object, class_id, needed);
    if (length <= 0 || (size_t)length >= sizeof(request)) return refuse(EOVERFLOW);
    int fd = openat(fs, "access", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    struct statx file;
    int error = 0;
    if (identify(fd, "", &file) < 0) error = errno;
    else if (!same_mount(mount, &file) || !S_ISREG(file.stx_mode)) error = EXDEV;
    if (!error) {
        /* One transaction to the policy-query node, no inode or policy write. */
        ssize_t n = write(fd, request, (size_t)length);
        if (n < 0) error = errno;
        else if (n != length) error = EPROTO;
    }
    size_t size;
    if (!error && (bounded_read(fd, response, sizeof(response), &size) < 0
            || av_decision(response, size, needed, generation, have_generation) < 0)) error = errno;
    close_cell(&fd, &error);
    return error ? refuse(error) : 0;
}

int guest_tree_property_label_preflight(struct guest_tree_property_child *owner, int dev_fd) {
    struct held_object objects[sizeof(targets) / sizeof(targets[0])];
    struct statx mount;
    struct policy_status before, after;
    struct av_class classes[2];
    char actor[CONTEXT_BYTES], final_actor[CONTEXT_BYTES];
    uint32_t generation = 0;
    int have_generation = 0, prop_fd = -1, fs = -1, result = -1, error;
    for (size_t i = 0; i < sizeof(objects) / sizeof(objects[0]); ++i) objects[i].fd = -1;
    if (guest_tree_property_child_borrow(owner, &prop_fd) < 0 || held_objects(prop_fd, dev_fd, objects) < 0
            || actor_context(actor) < 0) goto done;
    fs = open(SELINUX_PATH, DIRECTORY);
    if (fs < 0 || fstype(fs, SELINUX_MAGIC) < 0 || identify(fs, "", &mount) < 0
            || policy_read(fs, &mount, &before) < 0 || class_read(fs, &mount, classes) < 0) goto done;
    for (size_t i = 0; i < sizeof(objects) / sizeof(objects[0]); ++i) {
        const struct av_class *class = &classes[i != 0];
        if (query(fs, &mount, actor, objects[i].context, class->id, class->from, &generation, &have_generation) < 0
                || query(fs, &mount, actor, targets[i].label, class->id, class->to | class->setattr,
                         &generation, &have_generation) < 0) goto done;
    }
    int again = -1;
    if (guest_tree_property_child_borrow(owner, &again) < 0 || actor_context(final_actor) < 0) goto done;
    if (again != prop_fd || strcmp(actor, final_actor)) { errno = ESTALE; goto done; }
    for (size_t i = 0; i < sizeof(objects) / sizeof(objects[0]); ++i) {
        char final_context[CONTEXT_BYTES];
        if (same_named(prop_fd, targets[i].name, &objects[i].id) < 0
                || object_mode(objects[i].fd, &targets[i]) < 0 || object_context(objects[i].fd, final_context) < 0) goto done;
        if (strcmp(objects[i].context, final_context)) { errno = ESTALE; goto done; }
    }
    if (same_named(dev_fd, PROPERTY_NAME, &objects[0].id) < 0 || same_named(AT_FDCWD, SELINUX_PATH, &mount) < 0
            || policy_read(fs, &mount, &after) < 0) goto done;
    if (memcmp(&before, &after, sizeof(before))) { errno = ESTALE; goto done; }
    result = 0;
done:
    error = result < 0 ? (errno ? errno : EIO) : 0;
    close_cell(&fs, &error);
    for (size_t i = 0; i < sizeof(objects) / sizeof(objects[0]); ++i) close_cell(&objects[i].fd, &error);
    return error ? refuse(error) : 0;
}
