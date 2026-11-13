#include "guest_tree_source_mounts.h"

#include <string.h>

static const char scaffold[] = "/mnt";
static const char target_prefix[] = "/mnt/gvi";

static int canonical_absolute(const char *path) {
    const char *part;

    if (path[0] != '/') return 0;
    if (path[1] == 0) return 1;
    for (part = path + 1; ; ) {
        const char *end = strchr(part, '/');
        size_t length = end ? (size_t)(end - part) : strlen(part);
        if (!length || (length == 1 && part[0] == '.')
                || (length == 2 && part[0] == '.' && part[1] == '.')) return 0;
        if (!end) return 1;
        part = end + 1;
    }
}

static int below(const char *path, const char *parent) {
    size_t length = strlen(parent);
    if (length == 1 && parent[0] == '/') return path[0] == '/';
    return strncmp(path, parent, length) == 0
            && (path[length] == '/' || path[length] == 0);
}

/* path is already known to be at or below parent. */
static const char *suffix(const char *path, const char *parent) {
    if (parent[0] == '/' && parent[1] == 0 && path[1] != 0) return path;
    return path + strlen(parent);
}

static int join_path(const char *base, const char *tail, char out[GPV_PATH_CAPACITY]) {
    size_t a = strlen(base), b = strlen(tail);
    if (b && a == 1 && base[0] == '/') a = 0;
    if (a + b >= GPV_PATH_CAPACITY) return 0;
    memcpy(out, base, a);
    memcpy(out + a, tail, b + 1);
    return 1;
}

static int identity_matches(const struct gpv_mount_row *row,
        struct guest_tree_mount_identity expected) {
    return row && row->major == expected.major && row->minor == expected.minor;
}

static int private_bindable(const struct gpv_mount_row *row) {
    return !row->shared && !row->master && !row->propagate && !row->unbindable;
}

/* Every /mnt row must be the selected row or a covered parent at the same
 * point. The first distinct parent must be the visible root. */
static int scaffold_stack(const struct gpv_mount_row *rows, size_t count,
        const struct gpv_mount_row *selected, size_t same_point) {
    for (size_t depth = 1; depth <= same_point; ++depth) {
        selected = gpv_mount_by_id(rows, count, selected->parent);
        if (!selected) return 0;
        if (strcmp(selected->point, scaffold) != 0)
            return depth == same_point && strcmp(selected->point, "/") == 0;
    }
    return 0;
}

static int no_other_projection(const struct gpv_mount_row *row,
        const struct gpv_mount_row *source, const char *backing_path) {
    char projected[GPV_PATH_CAPACITY];

    if (row->major != source->major || row->minor != source->minor) return 1;
    if (below(row->root, backing_path)) return 0;
    if (!below(backing_path, row->root)) return 1;
    return join_path(row->point, suffix(backing_path, row->root), projected)
            && strcmp(projected, GUEST_TREE_SOURCE_PATH) == 0;
}

enum guest_tree_source_mount_result guest_tree_source_mounts_check(
        const char *mountinfo, size_t length,
        struct gpv_mount_row *scratch, size_t capacity,
        struct guest_tree_mount_identity source,
        struct guest_tree_mount_identity target) {
    const struct gpv_mount_row *source_mount, *target_mount;
    char backing_path[GPV_PATH_CAPACITY];
    size_t count, scaffold_rows = 0;

    if (!source.id || !target.id || source.id == target.id
            || gpv_parse_mountinfo(mountinfo, length, scratch, capacity, &count) != GPV_OK)
        return GUEST_TREE_SOURCE_MOUNTS_UNKNOWN;

    source_mount = gpv_mount_by_id(scratch, count, source.id);
    target_mount = gpv_mount_by_id(scratch, count, target.id);
    if (!identity_matches(source_mount, source) || !identity_matches(target_mount, target)
            || !private_bindable(source_mount) || !private_bindable(target_mount)
            || !canonical_absolute(source_mount->root) || !canonical_absolute(source_mount->point)
            || !below(GUEST_TREE_SOURCE_PATH, source_mount->point)
            || strcmp(GUEST_TREE_SOURCE_PATH, source_mount->point) == 0
            || strcmp(target_mount->point, scaffold) || strcmp(target_mount->root, "/")
            || strcmp(target_mount->type, "tmpfs")
            || !join_path(source_mount->root,
                          suffix(GUEST_TREE_SOURCE_PATH, source_mount->point), backing_path))
        return GUEST_TREE_SOURCE_MOUNTS_UNKNOWN;

    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *row = &scratch[i];
        if (row->shared || row->master || row->propagate
                || !canonical_absolute(row->point) || !canonical_absolute(row->root)
                || below(row->point, target_prefix))
            return GUEST_TREE_SOURCE_MOUNTS_UNKNOWN;
        if (strcmp(row->point, scaffold) == 0) ++scaffold_rows;
        if (row == source_mount) continue;
        if (below(row->point, GUEST_TREE_SOURCE_PATH)
                || (below(GUEST_TREE_SOURCE_PATH, row->point)
                    && below(row->point, source_mount->point))
                || !no_other_projection(row, source_mount, backing_path))
            return GUEST_TREE_SOURCE_MOUNTS_UNKNOWN;
    }

    return scaffold_stack(scratch, count, target_mount, scaffold_rows)
            ? GUEST_TREE_SOURCE_MOUNTS_MATCHED : GUEST_TREE_SOURCE_MOUNTS_UNKNOWN;
}
