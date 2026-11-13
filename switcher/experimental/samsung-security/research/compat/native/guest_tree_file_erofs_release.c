#define _GNU_SOURCE
#include "guest_tree_file_erofs_release.h"
#include "guest_tree_file_erofs_attach.h"
#include "guest_tree_file_erofs_mount.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#ifndef STATX_MNT_ID_UNIQUE
#define STATX_MNT_ID_UNIQUE 0x00004000U
#endif

static const int path_flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;

static int refuse(int error) { errno = error; return -1; }

static int directory(int fd, const char *path, unsigned id_flag, struct statx *out) {
    const unsigned mask = STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_INO | id_flag;
    if (statx(fd, path, path_flags | AT_EMPTY_PATH, mask, out) < 0) return -1;
    if ((out->stx_mask & mask) != mask || !S_ISDIR(out->stx_mode) || !out->stx_mnt_id)
        return refuse(ENOTSUP);
    return 0;
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_directory(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode
        && a->stx_uid == b->stx_uid && a->stx_gid == b->stx_gid;
}

static int namespace_type(int fd, struct stat *st) {
    struct statfs fs;
    if (fstat(fd, st) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    return type == CLONE_NEWNS ? 0 : type < 0 ? -1 : refuse(EXDEV);
}

static int current_namespace(pid_t owner, int initial_fd, int current_fd) {
    struct stat initial, current, named;
    if (owner <= 0 || getpid() != owner || gettid() != owner || geteuid() != 0)
        return refuse(EPERM);
    if (namespace_type(initial_fd, &initial) < 0 || namespace_type(current_fd, &current) < 0
            || stat("/proc/self/ns/mnt", &named) < 0) return -1;
    if ((initial.st_dev == current.st_dev && initial.st_ino == current.st_ino)
            || current.st_dev != named.st_dev || current.st_ino != named.st_ino) return refuse(EXDEV);
    return 0;
}

static int mountinfo(char *text, struct gpv_mount_row *rows, size_t *count) {
    const unsigned mask = STATX_TYPE | STATX_MNT_ID;
    struct statfs fs;
    struct statx proc, proc_fds, file;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    int result = -1;
    size_t used = 0;
    if (fstatfs(fd, &fs) < 0 || statx(AT_FDCWD, "/proc", path_flags, mask, &proc) < 0
            || statx(AT_FDCWD, "/proc/self/fd", path_flags, mask, &proc_fds) < 0
            || statx(fd, "", path_flags | AT_EMPTY_PATH, mask, &file) < 0) goto done;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || (proc.stx_mask & mask) != mask
            || (proc_fds.stx_mask & mask) != mask || (file.stx_mask & mask) != mask
            || !S_ISDIR(proc.stx_mode) || !S_ISDIR(proc_fds.stx_mode) || !S_ISREG(file.stx_mode)
            || !proc.stx_mnt_id || proc.stx_mnt_id != file.stx_mnt_id
            || proc.stx_mnt_id != proc_fds.stx_mnt_id) {
        errno = EXDEV;
        goto done;
    }
    while (used < GPV_MOUNTINFO_MAX_BYTES) {
        ssize_t n = read(fd, text + used, GPV_MOUNTINFO_MAX_BYTES - used);
        if (n < 0) goto done;
        if (n == 0) break;
        used += (size_t)n;
    }
    if (!used || used == GPV_MOUNTINFO_MAX_BYTES
            || gpv_parse_mountinfo(text, used, rows, GPV_MOUNTINFO_MAX_ROWS, count) != GPV_OK) {
        errno = EPROTO;
        goto done;
    }
    result = 0;
done:
    {
        int saved = errno;
        if (close(fd) < 0) return -1;
        errno = saved;
        return result;
    }
}

static int private_mount(const struct gpv_mount_row *row) {
    return row && !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static int has_option(const char *options, const char *wanted) {
    size_t size = strlen(wanted);
    while (*options) {
        size_t n = strcspn(options, ",");
        if (n == size && !memcmp(options, wanted, size)) return 1;
        options += n;
        if (*options) ++options;
    }
    return 0;
}

static int table_matches(char *text, struct gpv_mount_row *rows, const struct statx *stage,
                         const struct statx *attached, int before) {
    size_t count;
    if (mountinfo(text, rows, &count) < 0) return -1;
    const struct gpv_mount_row *parent = gpv_mount_by_id(rows, count, stage->stx_mnt_id);
    const struct gpv_mount_row *mount = gpv_mount_by_id(rows, count, attached->stx_mnt_id);
    if (!private_mount(parent) || parent->major != stage->stx_dev_major
            || parent->minor != stage->stx_dev_minor) return refuse(EXDEV);
    if (before) {
        if (!private_mount(mount) || mount->parent != parent->id
                || mount->major != attached->stx_dev_major || mount->minor != attached->stx_dev_minor
                || strcmp(mount->point, GUEST_TREE_BACKING_PATH) || strcmp(mount->root, "/")
                || strcmp(mount->type, "erofs") || !has_option(mount->options, "ro")
                || !has_option(mount->options, "nosuid") || !has_option(mount->options, "nodev")
                || has_option(mount->options, "rw") || !has_option(mount->super_options, "ro")
                || has_option(mount->super_options, "rw")) return refuse(EXDEV);
    } else if (mount) return refuse(ESTALE);
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *r = &rows[i];
        if (r == mount) continue;
        if ((r->major == attached->stx_dev_major && r->minor == attached->stx_dev_minor)
                || !strcmp(r->point, GUEST_TREE_BACKING_PATH)
                || !strncmp(r->point, GUEST_TREE_BACKING_PATH "/", sizeof(GUEST_TREE_BACKING_PATH)))
            return refuse(EBUSY);
    }
    return 0;
}

static int named_directory(int fd, const char *path, unsigned id_flag, const struct statx *expected) {
    struct statx named;
    if (directory(fd, path, id_flag, &named) < 0) return -1;
    return same_directory(&named, expected) ? 0 : refuse(ESTALE);
}

static int current_stage(int fd, const struct statx *stage) {
    if (named_directory(fd, "", STATX_MNT_ID, stage) < 0) return -1;
    return named_directory(AT_FDCWD, GUEST_TREE_STAGE_PATH, STATX_MNT_ID, stage);
}

static int check_cells(const int *fds, const uint64_t *inodes, size_t count,
                       const struct statx *attached) {
    for (size_t i = 0; i < count; ++i) {
        int flags = fcntl(fds[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) if (fds[j] == fds[i]) return refuse(EINVAL);
        struct statx value;
        if (directory(fds[i], "", STATX_MNT_ID_UNIQUE, &value) < 0) return -1;
        if (!same_mount(&value, attached) || value.stx_ino != inodes[i]) return refuse(EXDEV);
    }
    return 0;
}

int guest_tree_file_erofs_release(struct guest_tree_file_erofs_release *release,
        struct gtfm_owner *creator, struct guest_tree_file_erofs_attachment *attachment,
        int initial_namespace_fd, int current_namespace_fd) {
    if (!release || release->phase != GUEST_TREE_FILE_EROFS_RELEASE_EMPTY) return refuse(EINVAL);
    release->phase = GUEST_TREE_FILE_EROFS_RELEASE_CHECKING;
    char *text = NULL;
    struct gpv_mount_row *rows = NULL;
    struct statx stage, covered, attached, generation;
    struct statfs fs;
    struct statvfs vfs;
    char anchor[64], target[80];
    if (!creator || !attachment || attachment->state != GUEST_TREE_FILE_EROFS_BACKING_HELD
            || attachment->close_error || !attachment->backing_mount_id
            || attachment->backing_mount_id != attachment->expected_mount.id) {
        errno = EINVAL;
        goto fail;
    }
    const int stage_fd = attachment->stage_fd, covered_fd = attachment->covered_fd;
    const pid_t source_pid = attachment->source_pid;
    if (current_namespace(source_pid, initial_namespace_fd, current_namespace_fd) < 0) goto fail;
    struct gtfm_identity birth;
    int original = gtfm_borrow_root(creator, &birth);
    if (original < 0) goto fail;
    if (birth.mount_id != attachment->backing_mount_id || birth.root_inode != attachment->expected_root_inode
            || birth.device_major != attachment->expected_mount.major
            || birth.device_minor != attachment->expected_mount.minor) {
        errno = EXDEV;
        goto fail;
    }
    int a = snprintf(anchor, sizeof(anchor), "/proc/self/fd/%d", stage_fd);
    int b = snprintf(target, sizeof(target), "%s/backing", anchor);
    if (a < 0 || (size_t)a >= sizeof(anchor) || b < 0 || (size_t)b >= sizeof(target)) {
        errno = EOVERFLOW;
        goto fail;
    }
    const int backing_fd = attachment->backing_fd;
    if (directory(stage_fd, "", STATX_MNT_ID, &stage) < 0
            || directory(covered_fd, "", STATX_MNT_ID, &covered) < 0
            || directory(backing_fd, "", STATX_MNT_ID, &attached) < 0
            || directory(backing_fd, "", STATX_MNT_ID_UNIQUE, &generation) < 0
            || fstatfs(backing_fd, &fs) < 0 || fstatvfs(backing_fd, &vfs) < 0) goto fail;
    const unsigned long required = ST_RDONLY | ST_NOSUID | ST_NODEV;
    if ((unsigned long)fs.f_type != EROFS_SUPER_MAGIC_V1 || (vfs.f_flag & required) != required
            || attached.stx_mnt_id != birth.mount_id || attached.stx_dev_major != 0
            || attached.stx_dev_minor != birth.device_minor
            || attached.stx_mnt_id == stage.stx_mnt_id || !same_mount(&stage, &covered)
            || stage.stx_ino == covered.stx_ino || stage.stx_uid || covered.stx_uid
            || ((stage.stx_mode | covered.stx_mode) & 0022)) {
        errno = EXDEV;
        goto fail;
    }
    int *cells[] = {&attachment->mount_fd, &attachment->detached_tree_fd,
                   &attachment->backing_fd, &attachment->tree_fd};
    const int fds[] = {original, *cells[0], *cells[1], *cells[2], *cells[3]};
    const uint64_t root_inode = birth.root_inode, tree_inode = attachment->expected_tree_inode;
    const uint64_t inodes[] = {root_inode, root_inode, tree_inode, root_inode, tree_inode};
    if (current_stage(stage_fd, &stage) < 0
            || named_directory(stage_fd, "backing", STATX_MNT_ID_UNIQUE, &generation) < 0
            || named_directory(AT_FDCWD, target, STATX_MNT_ID_UNIQUE, &generation) < 0
            || check_cells(fds, inodes, sizeof(fds) / sizeof(fds[0]), &generation) < 0) goto fail;
    text = malloc(GPV_MOUNTINFO_MAX_BYTES);
    rows = malloc(GPV_MOUNTINFO_MAX_ROWS * sizeof(*rows));
    if (!text || !rows) { errno = ENOMEM; goto fail; }
    if (table_matches(text, rows, &stage, &attached, 1) < 0) goto fail;

    release->phase = GUEST_TREE_FILE_EROFS_RELEASE_CLOSING;
    int close_error = gtfm_close(creator) < 0 ? (errno ? errno : EIO) : 0;
    for (size_t i = 0; i < sizeof(cells) / sizeof(cells[0]); ++i) {
        int fd = *cells[i];
        *cells[i] = -1;
        if (close(fd) < 0 && !close_error) close_error = errno ? errno : EIO;
    }
    if (close_error) { attachment->close_error = close_error; errno = close_error; goto fail; }
    if (current_namespace(source_pid, initial_namespace_fd, current_namespace_fd) < 0
            || current_stage(stage_fd, &stage) < 0
            || table_matches(text, rows, &stage, &attached, 1) < 0
            || named_directory(AT_FDCWD, target, STATX_MNT_ID_UNIQUE, &generation) < 0) goto fail;

    release->phase = GUEST_TREE_FILE_EROFS_RELEASE_UNMOUNT_ATTEMPTED;
    if (umount2(target, UMOUNT_NOFOLLOW) < 0) goto fail;
    release->phase = GUEST_TREE_FILE_EROFS_RELEASE_UNMOUNT_RETURNED;
    if (current_namespace(source_pid, initial_namespace_fd, current_namespace_fd) < 0
            || current_stage(stage_fd, &stage) < 0
            || table_matches(text, rows, &stage, &attached, 0) < 0
            || named_directory(covered_fd, "", STATX_MNT_ID, &covered) < 0
            || named_directory(stage_fd, "backing", STATX_MNT_ID, &covered) < 0
            || named_directory(AT_FDCWD, target, STATX_MNT_ID, &covered) < 0) goto fail;
    release->phase = GUEST_TREE_FILE_EROFS_RELEASE_VERIFIED;
    free(rows);
    free(text);
    return 0;

fail:
    release->error = errno ? errno : EIO;
    free(rows);
    free(text);
    return refuse(release->error);
}
