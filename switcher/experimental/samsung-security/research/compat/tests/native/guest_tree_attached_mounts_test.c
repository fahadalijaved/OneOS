#include "guest_tree_attached_mounts.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ROOT "1 1 8:1 / / ro - ext4 root ro\n"
#define DATA "20 1 8:2 / /data rw,noatime - f2fs backing rw,seclabel\n"
#define OLD "30 1 0:30 / /mnt rw - tmpfs old rw\n"
#define SCAFFOLD "31 30 0:31 / /mnt rw - tmpfs scaffold rw\n"
#define BASE ROOT DATA OLD SCAFFOLD
#define EROFS_ROW "50 20 253:1 / " GUEST_TREE_BACKING_PATH " ro - erofs /dev/block/dm-1 ro\n"
#define RELATIVE "/local/tmp/oneos-viewprep/backing/tree"
#define ATTACH(id, parent, dev, root, point, options, type, source, super) \
    id " " parent " " dev " " root " " point " " options " - " type " " source " " super "\n"
#define ROW(root, opts, super) \
    ATTACH("40", "31", "8:2", root, GUEST_TREE_TARGET_PATH, opts, "f2fs", "backing", super)
#define VALID ROW(RELATIVE, "ro,nosuid,nodev,noatime", "rw,seclabel")
#define SOURCE {20, 8, 2}
#define TARGET {31, 0, 31}
#define ATTACHED {40, 8, 2}
#define SNAP(text) {text, sizeof(text) - 1, SOURCE, TARGET, 4, 127}
#define MATCH GUEST_TREE_ATTACHED_MOUNTS_MATCHED
#define UNKNOWN GUEST_TREE_ATTACHED_MOUNTS_UNKNOWN
#define CASE(label, text, status) {label, text, sizeof(text) - 1, status}

static struct gpv_mount_row before_rows[24], after_rows[24];
static const size_t capacity = sizeof(before_rows) / sizeof(before_rows[0]);
static unsigned checks;

static void expect(const char *label, int attach_result,
        const struct guest_tree_mount_snapshot *before,
        const struct guest_tree_mount_snapshot *after,
        struct guest_tree_mount_identity attached,
        struct gpv_mount_row *post_rows, size_t post_capacity,
        enum guest_tree_attached_mount_result expected) {
    enum guest_tree_attached_mount_result result = guest_tree_attached_mounts_check(
            attach_result, before, after, attached,
            before_rows, capacity, post_rows, post_capacity);
    ++checks;
    if (result != expected) {
        fprintf(stderr, "%s: expected %d, got %d\n", label, expected, result);
        exit(1);
    }
}

static const struct {
    const char *label, *text;
    size_t length;
    enum guest_tree_attached_mount_result expected;
} cases[] = {
    CASE("per-mount read-only with writable backing", BASE VALID, MATCH),
    CASE("table ordering is not identity", VALID SCAFFOLD ROOT OLD DATA, MATCH),
    CASE("new row option order", BASE ROW(RELATIVE, "nodev,noatime,ro,nosuid", "rw,seclabel"), MATCH),
    CASE("no added mount", BASE, UNKNOWN),
    CASE("duplicate mount ID", BASE VALID VALID, UNKNOWN),
    CASE("competing stacked attachment", BASE VALID
         ATTACH("41", "40", "8:2", RELATIVE, GUEST_TREE_TARGET_PATH,
                "ro,nosuid,nodev,noatime", "f2fs", "backing", "rw,seclabel"), UNKNOWN),
    CASE("immediate descendant mount", BASE VALID
         "41 40 0:41 / " GUEST_TREE_TARGET_PATH "/dev rw - tmpfs unexpected rw\n", UNKNOWN),
    CASE("new mount outside target", BASE VALID
         "41 1 0:41 / /outside rw - tmpfs unexpected rw\n", UNKNOWN),
    CASE("extra mount alias under scaffold", BASE VALID
         "41 31 0:41 / /mnt/gvi/foreign rw - tmpfs unexpected rw\n", UNKNOWN),
    CASE("attachment has wrong device", BASE
         ATTACH("40", "31", "8:3", RELATIVE, GUEST_TREE_TARGET_PATH,
                "ro,nosuid,nodev,noatime", "f2fs", "backing", "rw,seclabel"), UNKNOWN),
    CASE("attachment names covered parent instead of selected scaffold", BASE
         ATTACH("40", "30", "8:2", RELATIVE, GUEST_TREE_TARGET_PATH,
                "ro,nosuid,nodev,noatime", "f2fs", "backing", "rw,seclabel"), UNKNOWN),
    CASE("attachment points at sibling", BASE
         ATTACH("40", "31", "8:2", RELATIVE, GUEST_TREE_TARGET_PATH "-other",
                "ro,nosuid,nodev,noatime", "f2fs", "backing", "rw,seclabel"), UNKNOWN),
    CASE("attachment root is backing root, not source directory", BASE
         ROW("/", "ro,nosuid,nodev,noatime", "rw,seclabel"), UNKNOWN),
    CASE("attachment root is namespace path", BASE
         ROW(GUEST_TREE_SOURCE_PATH, "ro,nosuid,nodev,noatime", "rw,seclabel"), UNKNOWN),
    CASE("attachment projects a nested directory", BASE
         ROW(RELATIVE "/system", "ro,nosuid,nodev,noatime", "rw,seclabel"), UNKNOWN),
    CASE("attachment inherits wrong filesystem type", BASE
         ATTACH("40", "31", "8:2", RELATIVE, GUEST_TREE_TARGET_PATH,
                "ro,nosuid,nodev,noatime", "ext4", "backing", "rw,seclabel"), UNKNOWN),
    CASE("attachment inherits wrong source field", BASE
         ATTACH("40", "31", "8:2", RELATIVE, GUEST_TREE_TARGET_PATH,
                "ro,nosuid,nodev,noatime", "f2fs", "other", "rw,seclabel"), UNKNOWN),
    CASE("superblock-only readonly does not count", BASE
         ROW(RELATIVE, "rw,nosuid,nodev,noatime", "ro,seclabel"), UNKNOWN),
    CASE("unexpected superblock change", BASE
         ROW(RELATIVE, "ro,nosuid,nodev,noatime", "ro,seclabel"), UNKNOWN),
    CASE("read-write attachment", BASE ROW(RELATIVE, "rw,nosuid,nodev,noatime", "rw,seclabel"), UNKNOWN),
    CASE("missing nosuid", BASE ROW(RELATIVE, "ro,nodev,noatime", "rw,seclabel"), UNKNOWN),
    CASE("missing nodev", BASE ROW(RELATIVE, "ro,nosuid,noatime", "rw,seclabel"), UNKNOWN),
    CASE("nodev parameter is not nodev flag", BASE
         ROW(RELATIVE, "ro,nosuid,nodev=1,noatime", "rw,seclabel"), UNKNOWN),
    CASE("unexpected noexec added", BASE
         ROW(RELATIVE, "ro,nosuid,nodev,noatime,noexec", "rw,seclabel"), UNKNOWN),
    CASE("inherited noatime removed", BASE ROW(RELATIVE, "ro,nosuid,nodev", "rw,seclabel"), UNKNOWN),
    CASE("inherited noatime replaced", BASE
         ROW(RELATIVE, "ro,nosuid,nodev,relatime", "rw,seclabel"), UNKNOWN),
    CASE("nonprivate attached mount", BASE
         "40 31 8:2 " RELATIVE " " GUEST_TREE_TARGET_PATH
         " ro,nosuid,nodev,noatime shared:12 - f2fs backing rw,seclabel\n", UNKNOWN),
    CASE("unrelated predecessor removed", ROOT DATA SCAFFOLD VALID
         "41 1 0:41 / /other rw - tmpfs unexpected rw\n", UNKNOWN),
    CASE("existing source row moves", ROOT OLD SCAFFOLD
         "20 1 8:2 / /other rw,noatime - f2fs backing rw,seclabel\n" VALID, UNKNOWN),
    CASE("existing scaffold parent changes", ROOT DATA OLD
         "31 1 0:31 / /mnt rw - tmpfs scaffold rw\n" VALID, UNKNOWN),
    CASE("existing source options change", ROOT OLD SCAFFOLD
         "20 1 8:2 / /data ro,noatime - f2fs backing rw,seclabel\n" VALID, UNKNOWN),
    CASE("existing visible root options change",
         "1 1 8:1 / / rw - ext4 root ro\n" DATA OLD SCAFFOLD VALID, UNKNOWN),
    CASE("extra garbage after otherwise matching table", BASE VALID "\n", UNKNOWN),
};

int main(void) {
    const struct guest_tree_mount_snapshot original = SNAP(BASE), good = SNAP(BASE VALID);
    const struct guest_tree_mount_identity attached = ATTACHED;
    struct guest_tree_mount_snapshot pre, post;

    memset(before_rows, 0x34, sizeof(before_rows));
    memset(after_rows, 0x56, sizeof(after_rows));
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        post = good;
        post.mountinfo = cases[i].text;
        post.length = cases[i].length;
        expect(cases[i].label, 0, &original, &post, attached, after_rows, capacity, cases[i].expected);
    }
    expect("negative actual attach result", -1, &original, &good, attached, after_rows, capacity, UNKNOWN);
    expect("positive actual attach result", 1, &original, &good, attached, after_rows, capacity, UNKNOWN);
    expect("absent before record", 0, NULL, &good, attached, after_rows, capacity, UNKNOWN);
    expect("absent after record", 0, &original, NULL, attached, after_rows, capacity, UNKNOWN);
    expect("same scratch table", 0, &original, &good, attached, before_rows, capacity, UNKNOWN);
    expect("insufficient post rows", 0, &original, &good, attached, after_rows, 4, UNKNOWN);
    expect("observed root is old ID", 0, &original, &good, original.source, after_rows, capacity, UNKNOWN);
    expect("observed root is foreign ID", 0, &original, &good,
           (struct guest_tree_mount_identity){41, 8, 2}, after_rows, capacity, UNKNOWN);
    expect("observed root dev differs", 0, &original, &good,
           (struct guest_tree_mount_identity){40, 8, 3}, after_rows, capacity, UNKNOWN);
    post = good;
    post.namespace_ino++;
    expect("namespace inode changed", 0, &original, &post, attached, after_rows, capacity, UNKNOWN);
    post = good;
    post.namespace_dev++;
    expect("namespace device changed", 0, &original, &post, attached, after_rows, capacity, UNKNOWN);
    pre = original;
    post = good;
    pre.namespace_ino = post.namespace_ino = 0;
    expect("namespace identity missing", 0, &pre, &post, attached, after_rows, capacity, UNKNOWN);
    post = good;
    post.source.id++;
    expect("source FD mount changed", 0, &original, &post, attached, after_rows, capacity, UNKNOWN);
    post = good;
    post.scaffold.minor++;
    expect("scaffold FD device changed", 0, &original, &post, attached, after_rows, capacity, UNKNOWN);
    pre = good;
    expect("pre-attach bytes already contain attachment", 0, &pre, &good, attached, after_rows, capacity, UNKNOWN);
    post = good;
    post.length--;
    expect("post-attach table truncated", 0, &original, &post, attached, after_rows, capacity, UNKNOWN);
    pre = original;
    pre.length--;
    expect("pre-attach table truncated", 0, &pre, &good, attached, after_rows, capacity, UNKNOWN);

    const char ambient_shared[] = BASE "50 1 0:50 / /elsewhere rw shared:12 - tmpfs extra rw\n";
    const char ambient_shared_post[] = BASE "50 1 0:50 / /elsewhere rw shared:12 - tmpfs extra rw\n" VALID;
    pre = original;
    post = good;
    pre.mountinfo = ambient_shared;
    pre.length = sizeof(ambient_shared) - 1;
    post.mountinfo = ambient_shared_post;
    post.length = sizeof(ambient_shared_post) - 1;
    expect("otherwise matching tables cannot admit ambient sharing",
           0, &pre, &post, attached, after_rows, capacity, UNKNOWN);

    /* Keep a nontrivial source mount root when projecting the fixed path. */
    const char alternate[] = ROOT OLD SCAFFOLD
        "20 1 8:2 /volume/local /data/local rw,noatime,noexec - f2fs backing ro,seclabel\n";
    const char alternate_post[] = ROOT OLD SCAFFOLD
        "20 1 8:2 /volume/local /data/local rw,noatime,noexec - f2fs backing ro,seclabel\n"
        ROW("/volume" RELATIVE, "ro,nosuid,nodev,noatime,noexec", "ro,seclabel");
    pre = original;
    post = good;
    pre.mountinfo = alternate;
    pre.length = sizeof(alternate) - 1;
    post.mountinfo = alternate_post;
    post.length = sizeof(alternate_post) - 1;
    expect("non-root source backing projection, inherited noexec and ro superblock",
           0, &pre, &post, attached, after_rows, capacity, MATCH);
    const char super_only[] = ROOT OLD SCAFFOLD
        "20 1 8:2 /volume/local /data/local rw,noatime,noexec - f2fs backing ro,seclabel\n"
        ROW("/volume" RELATIVE, "rw,nosuid,nodev,noatime,noexec", "ro,seclabel");
    post.mountinfo = super_only;
    post.length = sizeof(super_only) - 1;
    expect("ro backing alone with exact same backing metadata",
           0, &pre, &post, attached, after_rows, capacity, UNKNOWN);

    const char root_backed[] = ROOT OLD SCAFFOLD;
    const char root_backed_post[] = ROOT OLD SCAFFOLD
        ATTACH("40", "31", "8:1", GUEST_TREE_SOURCE_PATH, GUEST_TREE_TARGET_PATH,
               "ro,nosuid,nodev", "ext4", "root", "ro");
    pre = original;
    post = good;
    pre.source = post.source = (struct guest_tree_mount_identity){1, 8, 1};
    pre.mountinfo = root_backed;
    pre.length = sizeof(root_backed) - 1;
    post.mountinfo = root_backed_post;
    post.length = sizeof(root_backed_post) - 1;
    expect("source under namespace root", 0, &pre, &post,
           (struct guest_tree_mount_identity){40, 8, 1}, after_rows, capacity, MATCH);
    const char erofs_before[] = BASE EROFS_ROW;
    const char erofs_after[] = BASE EROFS_ROW
        ATTACH("40", "31", "253:1", "/tree", GUEST_TREE_TARGET_PATH,
               "ro,nosuid,nodev", "erofs", "/dev/block/dm-1", "ro");
    pre.source = post.source = (struct guest_tree_mount_identity){50, 253, 1};
    pre.mountinfo = erofs_before;
    pre.length = sizeof(erofs_before) - 1;
    post.mountinfo = erofs_after;
    post.length = sizeof(erofs_after) - 1;
    expect("interior tree projects from dedicated EROFS backing", 0, &pre, &post,
           (struct guest_tree_mount_identity){40, 253, 1}, after_rows, capacity, MATCH);
    printf("PASS %u guest tree attached mount fixtures\n", checks);
    return 0;
}
