#define _GNU_SOURCE 1
#include "guest_tree_stop_backing.h"

#include "guest_tree_source_mounts.h"
#include "guest_tree_stage_guard.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define DIR_PATH (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define DIR_READ (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC | O_NOATIME)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_MNT_ID | \
                 STATX_NLINK | STATX_SIZE | STATX_MTIME | STATX_CTIME)

enum slot { ROOT, DATA, LOCAL, TMP, STAGE, BACKING, DEV, GUARD, COUNT };

struct location { int parent; const char *name; };

static const struct location locations[COUNT] = {
    [ROOT] = {AT_FDCWD, "/"},
    [DATA] = {ROOT, "data"},
    [LOCAL] = {DATA, "local"},
    [TMP] = {LOCAL, "tmp"},
    [STAGE] = {TMP, &GUEST_TREE_STAGE_PATH[sizeof("/data/local/tmp")]},
    [BACKING] = {STAGE, &GUEST_TREE_BACKING_PATH[sizeof(GUEST_TREE_STAGE_PATH)]},
    [DEV] = {ROOT, "dev"},
    [GUARD] = {DEV, &GUEST_TREE_GUARD_PATH[sizeof("/dev")]},
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int parent_fd(const int fds[COUNT], int slot) {
    int parent = locations[slot].parent;
    return parent == AT_FDCWD ? AT_FDCWD : fds[parent];
}

static int sample_dir(int fd, const char *name, struct statx *node) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, node) < 0) return -1;
    return (node->stx_mask & ID_MASK) == ID_MASK && node->stx_mnt_id && node->stx_ino &&
        S_ISDIR(node->stx_mode) ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major &&
        a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b, int full) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode &&
        a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid &&
        (!full || (a->stx_nlink == b->stx_nlink && a->stx_size == b->stx_size &&
                   a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec &&
                   a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec));
}

static int backing_reader_current(int fd, const struct statx *expected) {
    struct statx held;
    if (sample_dir(fd, "", &held) < 0) return -1;
    return same_node(expected, &held, 1) ? 0 : refuse(ESTALE);
}

static int anchors_current(const int fds[COUNT], const struct statx nodes[COUNT]) {
    for (int slot = ROOT; slot < COUNT; ++slot) {
        struct statx held, named;
        int full = slot == STAGE || slot == BACKING || slot == GUARD;
        if (sample_dir(fds[slot], "", &held) < 0 ||
                sample_dir(parent_fd(fds, slot), locations[slot].name, &named) < 0) return -1;
        if (!same_node(&nodes[slot], &held, full) || !same_node(&nodes[slot], &named, full))
            return refuse(ESTALE);
    }
    return 0;
}

static int fs_type(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : refuse(EXDEV);
}

static int profile(const struct statx *node, unsigned mode, unsigned uid, unsigned gid) {
    return node->stx_mode == (S_IFDIR | mode) && node->stx_uid == uid && node->stx_gid == gid;
}

static int profiles(const int fds[COUNT], const struct statx nodes[COUNT]) {
    if (nodes[ROOT].stx_uid || nodes[ROOT].stx_gid || (nodes[ROOT].stx_mode & 0022) ||
            !profile(&nodes[DATA], 0771, 1000, 1000) || !profile(&nodes[LOCAL], 0751, 0, 0) ||
            !profile(&nodes[TMP], 0771, 2000, 2000) || !profile(&nodes[STAGE], 0700, 0, 0) ||
            !profile(&nodes[BACKING], 0700, 0, 0) || !profile(&nodes[DEV], 0755, 0, 0) ||
            !profile(&nodes[GUARD], 0700, 0, 0)) return refuse(EPERM);
    for (int slot = LOCAL; slot <= BACKING; ++slot) {
        if (!same_mount(&nodes[DATA], &nodes[slot]) || nodes[slot].stx_ino == nodes[DATA].stx_ino)
            return refuse(EXDEV);
    }
    if (same_mount(&nodes[ROOT], &nodes[DATA]) || same_mount(&nodes[ROOT], &nodes[DEV]) ||
            !same_mount(&nodes[DEV], &nodes[GUARD]) || nodes[DEV].stx_ino == nodes[GUARD].stx_ino ||
            nodes[STAGE].stx_ino == nodes[BACKING].stx_ino) return refuse(EXDEV);
    if (nodes[BACKING].stx_nlink != 2 || nodes[GUARD].stx_nlink != 2) return refuse(EBUSY);
    if (fs_type(fds[DATA], F2FS_SUPER_MAGIC) < 0 || fs_type(fds[BACKING], F2FS_SUPER_MAGIC) < 0 ||
            fs_type(fds[DEV], TMPFS_MAGIC) < 0) return -1;
    return 0;
}

static int empty_backing(DIR *directory) {
    /* An uncovered directory with only dot entries has no nested mountpoint. */
    unsigned seen = 0;
    for (unsigned i = 0; i < 3; ++i) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) {
            if (errno) return -1;
            return seen == 3 ? 0 : refuse(EPROTO);
        }
        unsigned bit = !strcmp(entry->d_name, ".") ? 1 : !strcmp(entry->d_name, "..") ? 2 : 0;
        if (!bit || (seen & bit)) return refuse(EBUSY);
        seen |= bit;
    }
    return refuse(EBUSY);
}

static int absent(int guard_fd, const char *name, int *observed) {
    struct statx value;
    if (statx(guard_fd, name, LOOKUP, STATX_TYPE, &value) == 0) return refuse(EBUSY);
    if (errno != ENOENT) return -1;
    *observed = errno;
    return 0;
}

static struct guest_tree_stop_backing_node node(const struct statx *value) {
    return (struct guest_tree_stop_backing_node) {
        .mount_id = value->stx_mnt_id, .inode = value->stx_ino,
        .device_major = value->stx_dev_major, .device_minor = value->stx_dev_minor,
        .mode = value->stx_mode, .uid = value->stx_uid, .gid = value->stx_gid,
    };
}

int guest_tree_stop_backing_read(int stage_fd, struct guest_tree_stop_backing_sample *out) {
    if (!out) return refuse(EINVAL);
    memset(out, 0, sizeof(*out));
    if (stage_fd < 0) return refuse(EBADF);
    if (getuid() || geteuid() || getgid() || getegid()) return refuse(EPERM);
    int fds[COUNT];
    for (int slot = ROOT; slot < COUNT; ++slot) fds[slot] = -1;
    struct statx nodes[COUNT];
    struct guest_tree_stop_backing_sample observed = {0};
    DIR *backing = NULL;
    int reader_fd = -1, failure = 0;
    for (int slot = ROOT; slot < COUNT; ++slot) {
        fds[slot] = slot == STAGE ? stage_fd : openat(parent_fd(fds, slot), locations[slot].name, DIR_PATH);
        if (fds[slot] < 0 || sample_dir(fds[slot], "", &nodes[slot]) < 0) goto refused;
    }
    if (profiles(fds, nodes) < 0 || anchors_current(fds, nodes) < 0) goto refused;
    reader_fd = openat(fds[BACKING], ".", DIR_READ);
    if (reader_fd < 0 || backing_reader_current(reader_fd, &nodes[BACKING]) < 0) goto refused;
    backing = fdopendir(reader_fd);
    if (!backing) goto refused;
    reader_fd = -1;
    if (empty_backing(backing) < 0 || backing_reader_current(dirfd(backing), &nodes[BACKING]) < 0 ||
            absent(fds[GUARD], "writer-blocked", &observed.writer_errno) < 0 ||
            absent(fds[GUARD], "legacy-blocked", &observed.legacy_errno) < 0 ||
            absent(fds[GUARD], "view-blocked", &observed.view_errno) < 0 ||
            anchors_current(fds, nodes) < 0) goto refused;
    observed.data = node(&nodes[DATA]);
    observed.stage = node(&nodes[STAGE]);
    observed.backing = node(&nodes[BACKING]);
    observed.dev = node(&nodes[DEV]);
    observed.guard = node(&nodes[GUARD]);
    goto close_owned;

refused:
    failure = errno ? errno : EIO;
close_owned:
    if (backing && closedir(backing) < 0 && !failure) failure = errno ? errno : EIO;
    if (reader_fd >= 0 && close(reader_fd) < 0 && !failure) failure = errno ? errno : EIO;
    for (int slot = COUNT - 1; slot >= ROOT; --slot) {
        if (slot != STAGE && fds[slot] >= 0 && close(fds[slot]) < 0 && !failure) failure = errno ? errno : EIO;
    }
    if (failure) return refuse(failure);
    *out = observed;
    return 0;
}
