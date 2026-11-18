#define _GNU_SOURCE
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct apex_profile {
    const char *stable, *versioned, *fs;
    uint64_t payload_size;
    uint32_t version;
    size_t manifest_size;
};

/* Exact source-cohort.json roles. Version names are not caller inputs. */
static const struct apex_profile profiles[] = {
    {"com.android.art", "com.android.art@371000140", "ext4", 31633408, 371000140, 400},
    {"com.android.i18n", "com.android.i18n@1", "erofs", 21409792, 1, 151},
    {"com.android.runtime", "com.android.runtime@1", "erofs", 5296128, 1, 143},
};

static int donor_scans_name(const char *name, unsigned dtype) {
    /* Exact donor GetActivePackages filter, including its DT_DIR test. */
    return dtype == 4 && name[0] != '.' && !strchr(name, '@') && strcmp(name, "sharedlibs");
}

static int manifest_identity(const struct apex_profile *profile, const unsigned char *bytes, size_t size) {
    size_t length = strlen(profile->stable), at = length + 3;
    uint32_t version = 0;
    if (size != profile->manifest_size || at >= size || bytes[0] != 10 || bytes[1] != length
            || memcmp(bytes + 2, profile->stable, length) || bytes[length + 2] != 16) return 0;
    for (unsigned shift = 0; shift <= 28 && at < size; shift += 7) {
        unsigned char part = bytes[at++];
        if (shift == 28 && part > 15) return 0;
        version |= (uint32_t)(part & 127U) << shift;
        if (!(part & 128U)) return (!shift || part) && version == profile->version;
    }
    return 0;
}

#ifndef GCA_INERT_CHECKS
#include "guest_core_apex_owner.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/loop.h>
#include <linux/magic.h>
#include <linux/mount.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define DIR_PATH (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define DIR_READ (O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | AT_EMPTY_PATH)
#define APEX_PATH GUEST_TREE_TARGET_PATH "/apex"
#define EROFS_MAGIC 0xe0f5e1e2UL

_Static_assert(sizeof(profiles) / sizeof(profiles[0]) == GCA_COUNT, "fixed cohort");
_Static_assert(DT_DIR == 4, "donor and selected Linux dirent ABI");
_Static_assert(sizeof(struct mount_attr) == MOUNT_ATTR_SIZE_VER0, "mount_setattr v0 ABI");

/* Every persistent descriptor belongs to this actual child until its exit.
 * Read-only transient streams never supply authority to the retained set. */
static struct {
    int entered;
    size_t count;
    int fd[64];
} owner;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int retain(int fd) {
    if (fd < 0) return -1;
    /* The fixed operation consumes fewer than 40 cells, including failures. */
    if (owner.count == sizeof(owner.fd) / sizeof(owner.fd[0])) return refuse(EOVERFLOW);
    owner.fd[owner.count++] = fd;
    return fd;
}

static int same_node(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int namespace_stat(int fd, struct stat *value) {
    struct statfs fs;
    if (fstat(fd, value) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || ioctl(fd, NS_GET_NSTYPE) != CLONE_NEWNS)
        return refuse(EXDEV);
    return 0;
}

static int current_child(const struct guest_core_apex_inputs *input) {
    struct stat parent, child, named_parent, named_child;
    char path[64];
    if (input->parent <= 1 || getppid() != input->parent) return refuse(ECHILD);
    int n = snprintf(path, sizeof(path), "/proc/%ld/ns/mnt", (long)input->parent);
    if (n <= 0 || (size_t)n >= sizeof(path)) return refuse(EOVERFLOW);
    if (namespace_stat(input->parent_namespace_fd, &parent) < 0
            || namespace_stat(input->child_namespace_fd, &child) < 0
            || stat(path, &named_parent) < 0 || stat("/proc/self/ns/mnt", &named_child) < 0) return -1;
    return !same_node(&parent, &child) && same_node(&parent, &named_parent)
        && same_node(&child, &named_child) ? 0 : refuse(EXDEV);
}

static int stat_directory_at(int fd, const char *path, int lookup, struct statx *st) {
    unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | STATX_MNT_ID;
    if (statx(fd, path, lookup, mask, st) < 0) return -1;
    if ((st->stx_mask & mask) != mask || !st->stx_mnt_id || !S_ISDIR(st->stx_mode)) return refuse(EPROTO);
    return 0;
}

static int stat_directory(int fd, struct statx *st) {
    return stat_directory_at(fd, "", LOOKUP, st);
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor
        && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int named_root(const struct guest_tree_root_preparation *prepared, struct statx *root) {
    struct statx named, clone;
    if (stat_directory(prepared->readback.root_fd, root) < 0
            || stat_directory(prepared->attachment.clone_fd, &clone) < 0
            || stat_directory_at(AT_FDCWD, GUEST_TREE_TARGET_PATH, AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT, &named) < 0)
        return -1;
    if (root->stx_mnt_id != prepared->readback.attached.id
            || root->stx_mnt_id != clone.stx_mnt_id || root->stx_mnt_id != named.stx_mnt_id
            || root->stx_dev_major != prepared->readback.attached.major
            || root->stx_dev_minor != prepared->readback.attached.minor
            || !same_directory(root, &clone) || !same_directory(root, &named)) return refuse(ESTALE);
    return 0;
}

static int private_row(const struct gpv_mount_row *row) {
    return row && !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static int option(const char *list, const char *name) {
    size_t length = strlen(name);
    while (*list) {
        size_t n = strcspn(list, ",");
        if (n == length && !memcmp(list, name, n)) return 1;
        list += n;
        if (*list) ++list;
    }
    return 0;
}

static int mount_sample(struct guest_tree_mount_scratch s, size_t *count) {
    struct statfs fs;
    size_t used = 0;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    int saved = 0;
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0) saved = errno;
    else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC) saved = EXDEV;
    while (!saved && used < s.text_capacity) {
        ssize_t n = read(fd, s.text + used, s.text_capacity - used);
        if (n < 0) saved = errno;
        else if (!n) break;
        else used += (size_t)n;
    }
    if (close(fd) < 0 && !saved) saved = errno;
    if (saved) return refuse(saved);
    if (!used || used == s.text_capacity ||
            gpv_parse_mountinfo(s.text, used, s.rows, s.row_capacity, count) != GPV_OK) return refuse(EPROTO);
    return 0;
}

static int require_apex_shape(int directory, int staged) {
    unsigned mask = 0;
    int fd = openat(directory, ".", DIR_READ);
    int saved = 0;
    if (fd < 0) return -1;
    DIR *entries = fdopendir(fd);
    if (!entries) {
        saved = errno;
        (void)close(fd);
        return refuse(saved);
    }
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(entries);
        if (!entry) { saved = errno; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        unsigned bit = 0;
        if (staged && entry->d_type == DT_DIR) {
            for (unsigned i = 0; i < GCA_COUNT; ++i) {
                if (!strcmp(entry->d_name, profiles[i].stable) && donor_scans_name(entry->d_name, entry->d_type))
                    bit = 1U << (2 * i);
                if (!strcmp(entry->d_name, profiles[i].versioned) && !donor_scans_name(entry->d_name, entry->d_type))
                    bit = 1U << (2 * i + 1);
            }
        }
        if (!bit || (mask & bit)) { saved = EPROTO; break; }
        mask |= bit;
    }
    if (closedir(entries) < 0 && !saved) saved = errno;
    if (saved) return refuse(saved);
    return mask == (staged ? (1U << (2 * GCA_COUNT)) - 1U : 0) ? 0 : refuse(EPROTO);
}

static int read_manifest(int root, const struct apex_profile *profile, struct stat *identity) {
    unsigned char bytes[401];
    size_t used = 0;
    int fd = retain(openat(root, "apex_manifest.pb", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC));
    if (fd < 0 || fstat(fd, identity) < 0) return -1;
    if (!S_ISREG(identity->st_mode) || identity->st_size != (off_t)profile->manifest_size) return refuse(EPROTO);
    while (used < sizeof(bytes)) {
        ssize_t n = read(fd, bytes + used, sizeof(bytes) - used);
        if (n < 0) return -1;
        if (!n) break;
        used += (size_t)n;
    }
    return manifest_identity(profile, bytes, used) ? 0 : refuse(EPROTO);
}

static int check_backing(const struct guest_core_apex_backing *backing, const struct apex_profile *profile,
                         struct statx *root, const struct gpv_mount_row *rows, size_t count) {
    struct stat file, loop;
    struct statfs fs;
    struct loop_info64 info;
    int flags = fcntl(backing->payload_fd, F_GETFL);
    if (flags < 0 || fstat(backing->payload_fd, &file) < 0 || fstat(backing->loop_fd, &loop) < 0
            || ioctl(backing->loop_fd, LOOP_GET_STATUS64, &info) < 0
            || stat_directory(backing->mounted_root_fd, root) < 0
            || fstatfs(backing->mounted_root_fd, &fs) < 0) return -1;
    if ((flags & O_ACCMODE) != O_RDONLY || !S_ISREG(file.st_mode) || file.st_size < 0
            || (uint64_t)file.st_size != profile->payload_size || !S_ISBLK(loop.st_mode)
            || !(info.lo_flags & LO_FLAGS_READ_ONLY) || info.lo_offset || info.lo_sizelimit
            || info.lo_device != file.st_dev || info.lo_inode != file.st_ino
            || root->stx_dev_major != major(loop.st_rdev) || root->stx_dev_minor != minor(loop.st_rdev)
            || root->stx_uid != 1000 || root->stx_gid != 1000 || (root->stx_mode & 07777) != 0755
            || (unsigned long)fs.f_type != (!strcmp(profile->fs, "ext4") ? EXT4_SUPER_MAGIC : EROFS_MAGIC))
        return refuse(EXDEV);
    const struct gpv_mount_row *row = gpv_mount_by_id(rows, count, root->stx_mnt_id);
    if (!private_row(row) || row->major != root->stx_dev_major || row->minor != root->stx_dev_minor
            || strcmp(row->root, "/") || strcmp(row->type, profile->fs) || !option(row->options, "ro")
            || !option(row->super_options, "ro") || option(row->options, "noexec")) return refuse(EXDEV);
    size_t length = strlen(row->point);
    if (length <= 1) return refuse(EXDEV);
    for (size_t i = 0; i < count; ++i) {
        if (rows[i].id == row->id) continue;
        if (!strncmp(rows[i].point, row->point, length)
                && (!rows[i].point[length] || rows[i].point[length] == '/')) return refuse(EXDEV);
    }
    return 0;
}

static int retain_backing(const struct guest_core_apex_backing *input, struct guest_core_apex_backing *actual) {
    actual->payload_fd = retain(fcntl(input->payload_fd, F_DUPFD_CLOEXEC, 3));
    if (actual->payload_fd < 0) return -1;
    actual->loop_fd = retain(fcntl(input->loop_fd, F_DUPFD_CLOEXEC, 3));
    if (actual->loop_fd < 0) return -1;
    actual->mounted_root_fd = retain(fcntl(input->mounted_root_fd, F_DUPFD_CLOEXEC, 3));
    return actual->mounted_root_fd < 0 ? -1 : 0;
}

static int attach(int apex, int source, const char *name) {
    const struct mount_attr attributes = {
        .attr_set = MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV,
        .propagation = MS_PRIVATE,
    };
    if (mkdirat(apex, name, 0755) < 0) return -1;
    int target = retain(openat(apex, name, DIR_PATH));
    if (target < 0) return -1;
    int clone = retain((int)syscall(SYS_open_tree, source, "", LOOKUP | OPEN_TREE_CLONE | OPEN_TREE_CLOEXEC));
    if (clone < 0 || syscall(SYS_mount_setattr, clone, "", LOOKUP, &attributes, sizeof(attributes)) < 0
            || syscall(SYS_move_mount, clone, "", target, "",
                       MOVE_MOUNT_F_EMPTY_PATH | MOVE_MOUNT_T_EMPTY_PATH) < 0) return -1;
    return 0;
}

int guest_core_apex_stage(const struct guest_core_apex_inputs *input, struct guest_tree_mount_scratch scratch) {
    const unsigned long executable = ST_RDONLY | ST_NOSUID | ST_NODEV;
    struct statx root, covered, locator, apex, backings[GCA_COUNT], aliases[GCA_COUNT][2];
    struct guest_core_apex_backing backing[GCA_COUNT];
    struct stat manifests[GCA_COUNT], actual;
    struct statvfs flags;
    size_t count;
    int root_fd, covered_fd, apex_fd;
    char path[64];
    if (!input || !input->root || !scratch.text || !scratch.rows || !scratch.text_capacity
            || scratch.text_capacity > GPV_MOUNTINFO_MAX_BYTES + 1U || !scratch.row_capacity
            || scratch.row_capacity > GPV_MOUNTINFO_MAX_ROWS) return refuse(EINVAL);
    if (owner.entered) return refuse(EALREADY);
    owner.entered = 1;
    if (current_child(input) < 0) return -1;
    const struct guest_tree_root_preparation *prepared = input->root;
    if (prepared->attachment.state != GUEST_TREE_ATTACH_MOVE_RETURNED) return refuse(EXDEV);
    root_fd = prepared->readback.root_fd;
    if (named_root(prepared, &root) < 0 || fstatvfs(root_fd, &flags) < 0) return -1;
    if ((flags.f_flag & executable) != executable) return refuse(ESTALE);
    covered_fd = retain(openat(root_fd, "apex", DIR_PATH));
    if (covered_fd < 0 || stat_directory(covered_fd, &covered) < 0 || require_apex_shape(covered_fd, 0) < 0
            || mount_sample(scratch, &count) < 0) return -1;
    const struct gpv_mount_row *row = gpv_mount_by_id(scratch.rows, count, root.stx_mnt_id);
    if (covered.stx_mnt_id != root.stx_mnt_id || covered.stx_uid || covered.stx_gid
            || (covered.stx_mode & 07777) != 0755 || !private_row(row)
            || strcmp(row->point, GUEST_TREE_TARGET_PATH)) return refuse(EXDEV);
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        if (retain_backing(&input->backing[i], &backing[i]) < 0
                || check_backing(&backing[i], &profiles[i], &backings[i], scratch.rows, count) < 0
                || read_manifest(backing[i].mounted_root_fd, &profiles[i], &manifests[i]) < 0) return -1;
        if (backings[i].stx_mnt_id == root.stx_mnt_id) return refuse(EXDEV);
    }
    if (current_child(input) < 0) return -1;
    int n = snprintf(path, sizeof(path), "/proc/self/fd/%d", covered_fd);
    if (n <= 0 || (size_t)n >= sizeof(path)) return refuse(EOVERFLOW);
    if (stat_directory_at(AT_FDCWD, path, AT_NO_AUTOMOUNT, &locator) < 0) return -1;
    if (locator.stx_mnt_id != covered.stx_mnt_id || !same_directory(&covered, &locator)) return refuse(EXDEV);
    if (mount("oneos-core-apex", path, "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "mode=0755,uid=0,gid=0,size=1048576,nr_inodes=64") < 0) return -1;
    apex_fd = retain(openat(root_fd, "apex", DIR_PATH));
    if (apex_fd < 0 || stat_directory(apex_fd, &apex) < 0 || require_apex_shape(apex_fd, 0) < 0
            || mount_sample(scratch, &count) < 0) return -1;
    row = gpv_mount_by_id(scratch.rows, count, apex.stx_mnt_id);
    if (apex.stx_mnt_id == covered.stx_mnt_id || !private_row(row) || row->parent != root.stx_mnt_id
            || strcmp(row->point, APEX_PATH) || strcmp(row->type, "tmpfs")) return refuse(EXDEV);
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        int source = backing[i].mounted_root_fd;
        if (current_child(input) < 0 || attach(apex_fd, source, profiles[i].stable) < 0
                || attach(apex_fd, source, profiles[i].versioned) < 0) return -1;
    }
    if (current_child(input) < 0 || named_root(prepared, &root) < 0 || require_apex_shape(apex_fd, 1) < 0
            || mount_sample(scratch, &count) < 0) return -1;
    row = gpv_mount_by_id(scratch.rows, count, apex.stx_mnt_id);
    if (!private_row(row) || row->parent != root.stx_mnt_id || strcmp(row->point, APEX_PATH)
            || strcmp(row->type, "tmpfs")) return refuse(EXDEV);
    for (unsigned i = 0; i < GCA_COUNT; ++i) {
        struct statx source;
        if (check_backing(&backing[i], &profiles[i], &source, scratch.rows, count) < 0) return -1;
        if (source.stx_mnt_id != backings[i].stx_mnt_id || !same_directory(&source, &backings[i]))
            return refuse(ESTALE);
        const char *const names[2] = {profiles[i].stable, profiles[i].versioned};
        for (unsigned j = 0; j < 2; ++j) {
            char point[96];
            n = snprintf(point, sizeof(point), APEX_PATH "/%s", names[j]);
            if (n <= 0 || (size_t)n >= sizeof(point)) return refuse(EOVERFLOW);
            int fd = retain(openat(apex_fd, names[j], DIR_PATH));
            struct statx *mounted = &aliases[i][j];
            if (fd < 0 || stat_directory(fd, mounted) < 0 || fstatvfs(fd, &flags) < 0
                    || read_manifest(fd, &profiles[i], &actual) < 0) return -1;
            row = gpv_mount_by_id(scratch.rows, count, mounted->stx_mnt_id);
            if (!private_row(row) || row->parent != apex.stx_mnt_id || strcmp(row->root, "/")
                    || strcmp(row->point, point) || strcmp(row->type, profiles[i].fs)
                    || (flags.f_flag & (executable | ST_NOEXEC)) != executable
                    || !same_directory(&backings[i], mounted) || !same_node(&manifests[i], &actual))
                return refuse(EXDEV);
        }
        if (aliases[i][0].stx_mnt_id == aliases[i][1].stx_mnt_id) return refuse(EXDEV);
    }
    return current_child(input);
}
#endif
