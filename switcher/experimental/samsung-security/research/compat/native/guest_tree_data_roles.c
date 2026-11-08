#include "guest_tree_data_roles.h"

#include "guest_tree_control_owner.h"
#include "guest_tree_source_mounts.h"

#include <errno.h>
#include <string.h>

#define DATA_POINT "/data"
#define MIRROR_POINT "/data_mirror"

static int refuse(int error) {
    errno = error;
    return -1;
}

static int directory(const struct guest_tree_data_identity *fd) {
    return fd->mount_id && fd->inode && (fd->mode & 0170000U) == 0040000U;
}

static int same_object(const struct guest_tree_data_identity *a,
                       const struct guest_tree_data_identity *b) {
    return a->inode == b->inode && a->major == b->major && a->minor == b->minor;
}

static int same_directory(const struct guest_tree_data_identity *a,
                          const struct guest_tree_data_identity *b) {
    return same_object(a, b) && a->uid == b->uid && a->gid == b->gid && a->mode == b->mode;
}


static const struct gpv_mount_row *fd_row(const struct gpv_mount_row *rows,
        size_t count, const struct guest_tree_data_identity *fd) {
    const struct gpv_mount_row *row = gpv_mount_by_id(rows, count, fd->mount_id);
    return directory(fd) && row && row->major == fd->major && row->minor == fd->minor ? row : NULL;
}

static int no_slave(const struct gpv_mount_row *row) {
    return !row->master && !row->propagate && !row->unbindable;
}

static int private_mount(const struct gpv_mount_row *row) {
    return no_slave(row) && !row->shared;
}

static int same_backing(const struct gpv_mount_row *a, const struct gpv_mount_row *b) {
    return a->major == b->major && a->minor == b->minor && strcmp(a->type, b->type) == 0
            && strcmp(a->source, b->source) == 0 && strcmp(a->super_options, b->super_options) == 0;
}

static int below(const char *path, const char *parent) {
    size_t n = strlen(parent);
    if (n == 1 && parent[0] == '/') return path[0] == '/';
    return strncmp(path, parent, n) == 0 && (path[n] == '/' || path[n] == '\0');
}

static int root_projection(const char *projected, const char *root, const char *suffix) {
    size_t prefix = strcmp(root, "/") == 0 ? 0 : strlen(root);
    return strlen(projected) == prefix + strlen(suffix)
            && memcmp(projected, root, prefix) == 0 && strcmp(projected + prefix, suffix) == 0;
}

static int source_binding(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *source, const struct gpv_mount_row *native) {
    if (!below(GUEST_TREE_DATA_PATH, source->point) || strcmp(GUEST_TREE_DATA_PATH, source->point) == 0
            || !same_backing(source, native)) return 0;
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *row = &rows[i];
        if (below(row->point, GUEST_TREE_DATA_PATH) ||
                (row != source && below(GUEST_TREE_DATA_PATH, row->point)
                 && below(row->point, source->point))) return 0;
    }
    const char *suffix = GUEST_TREE_DATA_PATH;
    if (strcmp(source->point, "/") != 0) suffix += strlen(source->point);
    return root_projection(native->root, source->root, suffix);
}

static int point_count(const struct gpv_mount_row *rows, size_t count,
                       const struct gpv_mount_row *row, const char *point, size_t *found) {
    return strcmp(row->point, point) == 0 && gpv_mount_path_count(rows, count, point, found) == GPV_OK;
}

/* Native binds can cover the previous same-point mount. Count and follow the
 * actual covered IDs back to the inherited root. No line order is authority. */
static int native_stack(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *row, const struct gpv_mount_row *inherited, const char *point) {
    size_t at_point;
    if (!point_count(rows, count, row, point, &at_point)) return 0;
    for (size_t i = 1; i <= at_point; ++i) {
        row = gpv_mount_by_id(rows, count, row->parent);
        if (!row) return 0;
        if (row == inherited) return i == at_point;
        if (strcmp(row->point, point) != 0 || !private_mount(row)) return 0;
    }
    return 0;
}

static int exact_child(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *row, const struct gpv_mount_row *parent, const char *point) {
    size_t at_point;
    return row->parent == parent->id && point_count(rows, count, row, point, &at_point)
            && at_point == 1;
}

static int shared_pair(const struct gpv_mount_row *native, const struct gpv_mount_row *guest,
                       uint64_t group) {
    return native->id != guest->id && native->shared == group && guest->shared == group
            && no_slave(native) && no_slave(guest) && same_backing(native, guest)
            && strcmp(native->root, guest->root) == 0;
}

static int option(const char *options, const char *wanted) {
    size_t wanted_length = strlen(wanted);
    while (*options) {
        const char *end = strchr(options, ',');
        size_t length = end ? (size_t)(end - options) : strlen(options);
        if (length == wanted_length && memcmp(options, wanted, length) == 0) return 1;
        if (!end) break;
        options = end + 1;
    }
    return 0;
}

static int mirror_mount(const struct gpv_mount_row *row) {
    return strcmp(row->type, "tmpfs") == 0 && strcmp(row->source, "gvo-owned-mirror") == 0
            && strcmp(row->root, "/") == 0 && option(row->options, "rw")
            && option(row->super_options, "rw") && option(row->options, "nosuid")
            && option(row->options, "nodev") && option(row->options, "noexec");
}

static int allowed_group(const struct gpv_mount_row *parent, uint64_t group) {
    return !group || (group != parent->shared && group != parent->master && group != parent->propagate);
}

int guest_tree_data_roles_check(const struct gpv_mount_row *parent_rows, size_t parent_count,
        const struct gpv_mount_row *child_rows, size_t child_count,
        const struct guest_tree_data_roles *roles, const struct gtc_observation *claims) {
    if (!parent_rows || !parent_count || parent_count > GPV_MOUNTINFO_MAX_ROWS
            || !child_rows || !child_count || child_count > GPV_MOUNTINFO_MAX_ROWS
            || !roles || !claims) return refuse(EINVAL);
    if (!claims->data_group || !claims->mirror_group || claims->data_group == claims->mirror_group)
        return refuse(EPROTO);

    const struct gpv_mount_row *source = fd_row(parent_rows, parent_count, &roles->private_data);
    const struct gpv_mount_row *inherited = fd_row(child_rows, child_count, &roles->inherited_root);
    const struct gpv_mount_row *root = fd_row(child_rows, child_count, &roles->guest_root);
    const struct gpv_mount_row *native_data = fd_row(child_rows, child_count, &roles->native_data);
    const struct gpv_mount_row *guest_data = fd_row(child_rows, child_count, &roles->guest_data);
    const struct gpv_mount_row *native_mirror = fd_row(child_rows, child_count, &roles->native_mirror);
    const struct gpv_mount_row *guest_mirror = fd_row(child_rows, child_count, &roles->guest_mirror);
    const struct gpv_mount_row *user_zero = fd_row(child_rows, child_count, &roles->user_zero);
    const struct gpv_mount_row *native_alias = fd_row(child_rows, child_count, &roles->native_alias);
    const struct gpv_mount_row *guest_alias = fd_row(child_rows, child_count, &roles->guest_alias);
    if (!source || !inherited || !root || !native_data || !guest_data || !native_mirror
            || !guest_mirror || !user_zero || !native_alias || !guest_alias) return refuse(EXDEV);
    if (claims->mounts[GTC_INHERITED_ROOT] != inherited->id || claims->mounts[GTC_GUEST_ROOT] != root->id
            || claims->mounts[GTC_DATA] != native_data->id || claims->mounts[GTC_MIRROR] != native_mirror->id
            || claims->guest_data_mount != guest_data->id || claims->guest_mirror_mount != guest_mirror->id
            || claims->alias_native != native_alias->id || claims->alias_guest != guest_alias->id)
        return refuse(EPROTO);
    if (!private_mount(inherited) || !private_mount(root) || strcmp(inherited->point, "/")
            || strcmp(root->point, GUEST_TREE_TARGET_PATH)
            || same_object(&roles->inherited_root, &roles->guest_root)) return refuse(EXDEV);

    if (roles->private_data.uid != 1000 || roles->private_data.gid != 1000
            || (roles->private_data.mode & 07777U) != 0771U
            || !same_directory(&roles->private_data, &roles->native_data)
            || !same_directory(&roles->native_data, &roles->guest_data)
            || !source_binding(parent_rows, parent_count, source, native_data)
            || !native_stack(child_rows, child_count, native_data, inherited, DATA_POINT)
            || !exact_child(child_rows, child_count, guest_data, root, GUEST_TREE_TARGET_PATH DATA_POINT)
            || !shared_pair(native_data, guest_data, claims->data_group)) return refuse(EXDEV);

    if (!same_directory(&roles->native_mirror, &roles->guest_mirror)
            || roles->native_mirror.uid || roles->native_mirror.gid
            || (roles->native_mirror.mode & 07777U) != 0700U
            || !native_stack(child_rows, child_count, native_mirror, inherited, MIRROR_POINT)
            || !exact_child(child_rows, child_count, guest_mirror, root, GUEST_TREE_TARGET_PATH MIRROR_POINT)
            || !shared_pair(native_mirror, guest_mirror, claims->mirror_group)
            || !mirror_mount(native_mirror) || !mirror_mount(guest_mirror)) return refuse(EXDEV);

    if (user_zero != native_data || !same_directory(&roles->user_zero, &roles->native_alias)
            || !same_directory(&roles->user_zero, &roles->guest_alias)
            || !exact_child(child_rows, child_count, native_alias, native_data, "/data/data")
            || !exact_child(child_rows, child_count, guest_alias, guest_data, GUEST_TREE_TARGET_PATH "/data/data")
            || !no_slave(native_alias) || !no_slave(guest_alias)
            || !same_backing(native_alias, guest_alias) || !same_backing(native_alias, native_data)
            || !root_projection(native_alias->root, native_data->root, "/user/0")
            || strcmp(native_alias->root, guest_alias->root)) return refuse(EXDEV);

    for (size_t i = 0; i < parent_count; ++i) {
        const struct gpv_mount_row *parent = &parent_rows[i];
        if ((parent->major == native_mirror->major && parent->minor == native_mirror->minor)
                || !allowed_group(parent, claims->data_group) || !allowed_group(parent, claims->mirror_group)
                || !allowed_group(parent, native_alias->shared) || !allowed_group(parent, guest_alias->shared))
            return refuse(EXDEV);
    }
    return 0;
}
