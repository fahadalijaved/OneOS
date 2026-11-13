#include "guest_tree_dev_roles.h"

#include <string.h>

/* Linux stat/fstatfs values. Keep the pure sample verifier portable. */
#define TMPFS_MAGIC 0x01021994u
#define ST_RDONLY 0x01u
#define ST_NOSUID 0x02u
#define ST_NODEV 0x04u
#define ST_NOEXEC 0x08u
#define ROOT_DIRECTORY_0755 0040755u

static int same_device(struct guest_tree_mount_identity a,
        struct guest_tree_mount_identity b) {
    return a.major == b.major && a.minor == b.minor;
}

static int directory_profile(const struct guest_tree_dev_identity *entry,
        uint64_t links) {
    const uint64_t flags = ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC;
    return entry->mount.id && entry->ino && entry->nlink == links &&
            entry->uid == 0 && entry->gid == 0 && entry->mode == ROOT_DIRECTORY_0755 &&
            entry->fs_type == TMPFS_MAGIC &&
            (entry->fs_flags & flags) == (flags & ~ST_RDONLY);
}

static int same_directory(const struct guest_tree_dev_identity *a,
        const struct guest_tree_dev_identity *b) {
    return a->mount.id == b->mount.id && same_device(a->mount, b->mount) &&
            a->ino == b->ino && a->fs_flags == b->fs_flags;
}

static int has_option(const char *options, const char *wanted) {
    size_t length = strlen(wanted);
    for (;;) {
        const char *comma = strchr(options, ',');
        size_t token_length = comma ? (size_t)(comma - options) : strlen(options);
        if (token_length == length && memcmp(options, wanted, length) == 0) return 1;
        if (!comma) return 0;
        options = comma + 1;
    }
}

int guest_tree_dev_roles_check(const struct gpv_mount_row *child_rows,
        size_t child_count, uint64_t root_mount_id,
        const struct guest_tree_dev_sample *sample) {
    const struct gpv_mount_row *root, *dev;
    const size_t dev_path_length = sizeof(GUEST_TREE_DEV_PATH) - 1;

    if (!child_rows || !child_count || child_count > GPV_MOUNTINFO_MAX_ROWS ||
        !root_mount_id || !sample || !directory_profile(&sample->dev, 3) ||
        !directory_profile(&sample->socket_dir, 2) || !directory_profile(&sample->reopened_dev, 3) ||
        !directory_profile(&sample->reopened_socket, 2) ||
        sample->dev.mount.id != sample->socket_dir.mount.id ||
        !same_device(sample->dev.mount, sample->socket_dir.mount) ||
        sample->dev.ino == sample->socket_dir.ino || sample->dev.fs_flags != sample->socket_dir.fs_flags ||
        !same_directory(&sample->dev, &sample->reopened_dev) ||
        !same_directory(&sample->socket_dir, &sample->reopened_socket)) return -1;

    root = gpv_mount_by_id(child_rows, child_count, root_mount_id);
    dev = gpv_mount_by_id(child_rows, child_count, sample->dev.mount.id);
    if (!root || !dev || root == dev || strcmp(root->point, GUEST_TREE_TARGET_PATH) ||
        dev->parent != root_mount_id || dev->major != sample->dev.mount.major ||
        dev->minor != sample->dev.mount.minor || strcmp(dev->point, GUEST_TREE_DEV_PATH) ||
        strcmp(dev->root, "/") || strcmp(dev->type, "tmpfs") || strcmp(dev->source, GUEST_TREE_DEV_SOURCE) ||
        dev->shared || dev->master || dev->propagate || dev->unbindable ||
        !has_option(dev->options, "rw") || !has_option(dev->super_options, "rw") ||
        !has_option(dev->options, "nosuid") || !has_option(dev->options, "nodev") ||
        !has_option(dev->options, "noexec")) return -1;

    for (size_t i = 0; i < child_count; ++i) {
        const struct gpv_mount_row *row = &child_rows[i];
        if (row == dev) continue;
        if (row->parent == dev->id || (row->major == dev->major && row->minor == dev->minor) ||
            (strncmp(row->point, GUEST_TREE_DEV_PATH, dev_path_length) == 0 &&
             (row->point[dev_path_length] == '\0' || row->point[dev_path_length] == '/'))) return -1;
    }
    return 0;
}
