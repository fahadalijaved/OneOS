#include "guest_tree_attached_mounts.h"

#include <string.h>

static int same_identity(struct guest_tree_mount_identity a,
        struct guest_tree_mount_identity b) {
    return a.id == b.id && a.major == b.major && a.minor == b.minor;
}

static int same_row(const struct gpv_mount_row *a, const struct gpv_mount_row *b) {
    return b && a->id == b->id && a->parent == b->parent
            && a->major == b->major && a->minor == b->minor
            && a->shared == b->shared && a->master == b->master
            && a->propagate == b->propagate && a->unbindable == b->unbindable
            && strcmp(a->root, b->root) == 0 && strcmp(a->point, b->point) == 0
            && strcmp(a->source, b->source) == 0 && strcmp(a->type, b->type) == 0
            && strcmp(a->options, b->options) == 0
            && strcmp(a->super_options, b->super_options) == 0;
}

/* Pre-attach validation already proved point is a strict ancestor. */
static int same_backing_root(const struct gpv_mount_row *source,
        const struct gpv_mount_row *attached) {
    const char *suffix = GUEST_TREE_SOURCE_PATH;
    size_t prefix = strlen(source->root);

    if (strcmp(source->point, "/") != 0) suffix += strlen(source->point);
    if (strcmp(source->root, "/") == 0) prefix = 0;
    return strlen(attached->root) == prefix + strlen(suffix)
            && memcmp(attached->root, source->root, prefix) == 0
            && strcmp(attached->root + prefix, suffix) == 0;
}

static size_t option_length(const char *token) {
    const char *end = strchr(token, ',');
    return end ? (size_t)(end - token) : strlen(token);
}

static int has_option(const char *options, const char *wanted, size_t length) {
    while (*options) {
        size_t n = option_length(options);
        if (n == length && memcmp(options, wanted, n) == 0) return 1;
        options += n;
        if (*options) ++options;
    }
    return 0;
}

/* The attach changes these per-mount flags only. The backing superblock
 * options are checked separately and can still say rw. */
static int other_options_in(const char *options, const char *expected) {
    while (*options) {
        size_t n = option_length(options);
        int changed = (n == 2 && (!memcmp(options, "ro", 2) || !memcmp(options, "rw", 2)))
                || (n == 6 && !memcmp(options, "nosuid", 6))
                || (n == 5 && !memcmp(options, "nodev", 5));
        if (!changed && !has_option(expected, options, n)) return 0;
        options += n;
        if (*options) ++options;
    }
    return 1;
}

static int attached_matches(const struct gpv_mount_row *row,
        const struct gpv_mount_row *source, struct guest_tree_mount_identity attached,
        uint64_t scaffold_id) {
    return row && row->parent == scaffold_id && row->major == attached.major
            && row->minor == attached.minor && row->major == source->major
            && row->minor == source->minor && strcmp(row->point, GUEST_TREE_TARGET_PATH) == 0
            && !row->shared && !row->master && !row->propagate && !row->unbindable
            && strcmp(row->type, source->type) == 0 && strcmp(row->source, source->source) == 0
            && strcmp(row->super_options, source->super_options) == 0
            && same_backing_root(source, row)
            && has_option(row->options, "ro", 2) && has_option(row->options, "nosuid", 6)
            && has_option(row->options, "nodev", 5)
            && other_options_in(source->options, row->options)
            && other_options_in(row->options, source->options);
}

enum guest_tree_attached_mount_result guest_tree_attached_mounts_check(
        int attach_result,
        const struct guest_tree_mount_snapshot *before,
        const struct guest_tree_mount_snapshot *after,
        struct guest_tree_mount_identity attached,
        struct gpv_mount_row *before_rows, size_t before_capacity,
        struct gpv_mount_row *after_rows, size_t after_capacity) {
    size_t before_count = 0, after_count;
    const struct gpv_mount_row *source, *row;

    if (attach_result != 0 || !before || !after || !attached.id
            || before_rows == after_rows || !before->namespace_ino
            || before->namespace_ino != after->namespace_ino
            || before->namespace_dev != after->namespace_dev
            || !same_identity(before->source, after->source)
            || !same_identity(before->scaffold, after->scaffold))
        return GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN;
    if (guest_tree_source_mounts_check(before->mountinfo, before->length,
            before_rows, before_capacity, before->source, before->scaffold)
            != GUEST_TREE_SOURCE_MOUNTS_MATCHED)
        return GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN;
    /* A successful parse populated one row per complete LF-terminated line. */
    for (size_t i = 0; i < before->length; ++i)
        if (before->mountinfo[i] == '\n') ++before_count;
    if (gpv_mount_by_id(before_rows, before_count, attached.id)
            || gpv_parse_mountinfo(after->mountinfo, after->length,
                                   after_rows, after_capacity, &after_count) != GPV_OK
            || after_count != before_count + 1)
        return GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN;
    source = gpv_mount_by_id(before_rows, before_count, before->source.id);
    row = gpv_mount_by_id(after_rows, after_count, attached.id);
    if (!source || !attached_matches(row, source, attached, before->scaffold.id))
        return GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN;
    /* With a single extra row, every other row must be the admitted one.
     * The pre-check already excluded competing mounts at the destination. */
    for (size_t i = 0; i < before_count; ++i)
        if (!same_row(&before_rows[i],
                gpv_mount_by_id(after_rows, after_count, before_rows[i].id)))
            return GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN;
    return GUEST_TREE_ATTACHED_MOUNTS_MATCHED;
}
