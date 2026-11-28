#define _GNU_SOURCE
#include "guest_linkerconfig_parent_readback.h"

#include "guest_linkerconfig_output.h"
#include "guest_private_view_mountinfo.h"
#include "guest_readback_identity.h"

#include <linux/magic.h>
#include <stdlib.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>

int guest_tree_read_task_mountinfo(int task, const struct statx *proc,
        struct gpv_mount_row **rows, size_t *count, int *close_error);

static const char directory_name[] = "linkerconfig";
static const char base_name[] = "ld.config.txt";
static const char mount_point[] = "/linkerconfig";

struct placement {
    struct statx root, directory, base;
};

static int matches_name(int parent, const char *name, const struct statx *held) {
    struct statx named;
    if (guest_readback_stat(parent, name, &named) < 0) return -1;
    return guest_readback_same_node(held, &named) ? 0 : guest_readback_refuse(ESTALE);
}

static int base_held(int fd, const struct statx *named) {
    struct statx held;
    int flags = fcntl(fd, F_GETFL);
    const int required = O_NOATIME | O_NONBLOCK;
    if (flags < 0 || guest_readback_stat(fd, "", &held) < 0) return -1;
    if ((flags & (O_ACCMODE | O_PATH | required)) != required) return guest_readback_refuse(EPERM);
    return guest_readback_same_node(named, &held) ? 0 : guest_readback_refuse(ESTALE);
}

static int sample_placement(int root, int directory, int base, struct placement *sample) {
    struct statfs root_fs, directory_fs;
    struct statvfs flags;
    const unsigned long required = ST_NOSUID | ST_NODEV | ST_NOEXEC;
    int directory_status = fcntl(directory, F_GETFL);
    if (directory_status < 0) return -1;
    if ((directory_status & (O_PATH | O_DIRECTORY)) != (O_PATH | O_DIRECTORY))
        return guest_readback_refuse(EPERM);
    if (fstatfs(root, &root_fs) < 0 || fstatfs(directory, &directory_fs) < 0
            || fstatvfs(directory, &flags) < 0
            || guest_readback_stat(root, "", &sample->root) < 0
            || guest_readback_stat(directory, "", &sample->directory) < 0) return -1;
    const struct statx *dir = &sample->directory;
    if ((unsigned long)root_fs.f_type != EROFS_SUPER_MAGIC_V1 || !S_ISDIR(sample->root.stx_mode)
            || (unsigned long)directory_fs.f_type != TMPFS_MAGIC || (flags.f_flag & (required | ST_RDONLY)) != required
            || dir->stx_mnt_id == sample->root.stx_mnt_id || dir->stx_mode != (S_IFDIR | 0755)
            || dir->stx_uid || dir->stx_gid || dir->stx_nlink != 2) return guest_readback_refuse(EXDEV);
    if (matches_name(root, directory_name, dir) < 0
            || guest_readback_stat(directory, base_name, &sample->base) < 0) return -1;
    const struct statx *file = &sample->base;
    if (!guest_readback_same_mount(dir, file) || file->stx_mode != (S_IFREG | 0644)
            || file->stx_uid || file->stx_gid || file->stx_nlink != 1 || file->stx_size != 1)
        return guest_readback_refuse(EXDEV);
    return base_held(base, file);
}

static int row_is_private(const struct gpv_mount_row *row, const struct statx *node) {
    return row->id == node->stx_mnt_id && row->major == node->stx_dev_major
            && row->minor == node->stx_dev_minor && !row->shared && !row->master
            && !row->propagate && !row->unbindable;
}

static int has_option(const char *options, const char *word) {
    size_t wanted = strlen(word);
    for (;;) {
        size_t length = strcspn(options, ",");
        if (length == wanted && !memcmp(options, word, length)) return 1;
        if (!options[length]) return 0;
        options += length + 1;
    }
}

static int check_rows(const struct gpv_mount_row *rows, size_t count, const struct placement *sample) {
    if (!rows || !count || count > GPV_MOUNTINFO_MAX_ROWS) return guest_readback_refuse(EPROTO);
    const struct gpv_mount_row *root = NULL, *directory = NULL;
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *row = &rows[i];
        if (!strcmp(row->point, "/")) {
            if (root) return guest_readback_refuse(EXDEV);
            root = row;
        } else if (!strcmp(row->point, mount_point)) {
            if (directory) return guest_readback_refuse(EXDEV);
            directory = row;
        } else if ((!strncmp(row->point, mount_point, sizeof(mount_point) - 1)
                    && row->point[sizeof(mount_point) - 1] == '/')
                || row->parent == sample->directory.stx_mnt_id) {
            return guest_readback_refuse(EXDEV);
        }
    }
    if (!root || !directory || !row_is_private(root, &sample->root) || strcmp(root->type, "erofs")
            || !row_is_private(directory, &sample->directory) || directory->parent != root->id
            || strcmp(directory->type, "tmpfs") || strcmp(directory->root, "/"))
        return guest_readback_refuse(EXDEV);
    const char *options = directory->options;
    if (!has_option(options, "rw") || has_option(options, "ro") || !has_option(options, "nosuid")
            || !has_option(options, "nodev") || !has_option(options, "noexec"))
        return guest_readback_refuse(EXDEV);
    return 0;
}

static int check_task_mounts(int task, const struct statx *proc, const struct placement *sample, int *close_error) {
    struct gpv_mount_row *rows = NULL;
    size_t count = 0;
    int result = guest_tree_read_task_mountinfo(task, proc, &rows, &count, close_error);
    if (result == 0)
        result = *close_error ? guest_readback_refuse(*close_error) : check_rows(rows, count, sample);
    int error = errno;
    free(rows);
    errno = error;
    return result;
}

int guest_linkerconfig_parent_readback(int live_root_fd, int task_fd,
        const struct statx *proc, int directory_fd, int base_fd, int *close_error) {
    if (!proc || !close_error) return guest_readback_refuse(EINVAL);
    const int descriptors[] = {live_root_fd, task_fd, directory_fd, base_fd};
    for (size_t i = 0; i < sizeof(descriptors) / sizeof(descriptors[0]); ++i) {
        if (descriptors[i] < 0) return guest_readback_refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (descriptors[i] == descriptors[j]) return guest_readback_refuse(EINVAL);
        }
    }
    if (*close_error) return guest_readback_refuse(*close_error);

    struct placement before, after;
    struct guest_linkerconfig_generation_start baseline;
    if (sample_placement(live_root_fd, directory_fd, base_fd, &before) < 0
            || check_task_mounts(task_fd, proc, &before, close_error) < 0
            || guest_linkerconfig_generation_begin(live_root_fd, directory_fd, base_fd, &baseline) < 0
            || check_task_mounts(task_fd, proc, &before, close_error) < 0
            || sample_placement(live_root_fd, directory_fd, base_fd, &after) < 0) return -1;
    if (!guest_readback_same_node(&before.root, &after.root)
            || !guest_readback_same_node(&before.directory, &after.directory)
            || !guest_readback_same_node(&before.base, &after.base)) return guest_readback_refuse(ESTALE);
    return 0;
}
