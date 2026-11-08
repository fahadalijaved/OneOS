#include "guest_tree_source_mounts.h"

#include <stdio.h>
#include <stdlib.h>

#define ROOT "1 1 8:1 / / ro - ext4 root ro\n"
#define DATA "20 1 8:2 / /data rw - f2fs data rw\n"
#define OLD "30 1 0:30 / /mnt rw - tmpfs old rw\n"
#define FRESH "31 1 0:31 / /mnt rw - tmpfs scaffold rw\n"
#define OVER_OLD "31 30 0:31 / /mnt rw - tmpfs scaffold rw\n"
#define BASE ROOT DATA FRESH
#define EROFS_ROW "50 20 253:1 / " GUEST_TREE_BACKING_PATH " ro - erofs /dev/block/dm-1 ro\n"
#define SOURCE {20, 8, 2}
#define TARGET {31, 0, 31}
#define CASE(name, text, result) \
    { name, text, sizeof(text) - 1, SOURCE, TARGET, result }
#define MATCH GUEST_TREE_SOURCE_MOUNTS_MATCHED
#define UNKNOWN GUEST_TREE_SOURCE_MOUNTS_UNKNOWN

static struct gpv_mount_row rows[24];
static unsigned checks;

static void expect(const char *name, const char *input, size_t length, size_t capacity,
        struct guest_tree_mount_identity source, struct guest_tree_mount_identity target,
        enum guest_tree_source_mount_result expected) {
    enum guest_tree_source_mount_result result =
        guest_tree_source_mounts_check(input, length, rows, capacity, source, target);
    ++checks;
    if (result != expected) {
        fprintf(stderr, "%s: expected %d, got %d\n", name, expected, result);
        exit(1);
    }
}

static const struct {
    const char *name, *input;
    size_t length;
    struct guest_tree_mount_identity source, target;
    enum guest_tree_source_mount_result expected;
} cases[] = {
    CASE("ordinary /data directory", BASE, MATCH),
    CASE("covered /mnt predecessor", ROOT DATA OLD OVER_OLD, MATCH),
    CASE("no line-order ownership", OVER_OLD DATA OLD ROOT, MATCH),
    CASE("covered same-point chain", ROOT DATA OLD
         "32 30 0:32 / /mnt rw - tmpfs old2 rw\n"
         "31 32 0:31 / /mnt rw - tmpfs scaffold rw\n", MATCH),
    CASE("other /mnt subtree", BASE
         "40 31 0:40 / /mnt/gvi-sibling rw - tmpfs extra rw\n", MATCH),
    CASE("source component boundary", BASE
         "40 20 8:3 / " GUEST_TREE_SOURCE_PATH "-sibling rw - f2fs extra rw\n", MATCH),
    CASE("unrelated same-device bind", BASE
         "40 20 8:2 /local/tmp/oneos-viewprep/backing/tree-peer /alias rw - f2fs data rw\n", MATCH),
    CASE("unrelated escaped mount point", BASE
         "40 1 0:40 / /unrelated\\040space rw - tmpfs extra rw\n", MATCH),
    CASE("ambient shared mount", BASE
         "40 1 0:40 / /unrelated rw shared:11 - tmpfs extra rw\n", UNKNOWN),
    CASE("ambient slave mount", BASE
         "40 1 0:40 / /unrelated rw master:11 - tmpfs extra rw\n", UNKNOWN),
    CASE("ambient propagate-from mount", BASE
         "40 1 0:40 / /unrelated rw master:11 propagate_from:12 - tmpfs extra rw\n", UNKNOWN),
    CASE("ambient unbindable mount cannot propagate", BASE
         "40 1 0:40 / /unrelated rw unbindable - tmpfs extra rw\n", MATCH),
    CASE("source row absent", ROOT FRESH, UNKNOWN),
    CASE("target row absent", ROOT DATA, UNKNOWN),
    CASE("duplicate IDs", BASE DATA, UNKNOWN),
    CASE("malformed record", BASE "not-a-row\n", UNKNOWN),
    CASE("missing terminal LF", ROOT DATA
         "31 1 0:31 / /mnt rw - tmpfs scaffold rw", UNKNOWN),
    CASE("dot alias in point", BASE
         "40 20 8:2 / /data/local/./tmp rw - f2fs data rw\n", UNKNOWN),
    CASE("dotdot alias in root", BASE
         "40 20 8:2 /local/../tmp /alias rw - f2fs data rw\n", UNKNOWN),
    CASE("double separator", BASE
         "40 20 8:2 / /data//local/tmp rw - f2fs data rw\n", UNKNOWN),
    CASE("trailing separator", BASE
         "40 20 8:2 / /data/local/tmp/ rw - f2fs data rw\n", UNKNOWN),
    CASE("stack at source backing mount", BASE
         "40 20 8:3 / /data rw - f2fs extra rw\n", UNKNOWN),
    CASE("intermediate source cover", BASE
         "40 20 8:3 / /data/local/tmp rw - f2fs extra rw\n", UNKNOWN),
    CASE("direct mount at source", BASE
         "40 20 8:3 / " GUEST_TREE_SOURCE_PATH " rw - f2fs extra rw\n", UNKNOWN),
    CASE("source submount", BASE
         "40 20 8:3 / " GUEST_TREE_SOURCE_PATH "/system rw - f2fs extra rw\n", UNKNOWN),
    CASE("alternate source bind", BASE
         "40 1 8:2 /local/tmp/oneos-viewprep/backing/tree /alias rw - f2fs data rw\n", UNKNOWN),
    CASE("alternate source ancestor projection", BASE
         "40 1 8:2 /local/tmp /alias rw - f2fs data rw\n", UNKNOWN),
    CASE("alternate source descendant bind", BASE
         "40 1 8:2 /local/tmp/oneos-viewprep/backing/tree/system /alias rw - f2fs data rw\n", UNKNOWN),
    CASE("whole source filesystem alias", BASE
         "40 1 8:2 / /alias rw - f2fs data rw\n", UNKNOWN),
    CASE("unrelated old /mnt row", BASE OLD, UNKNOWN),
    CASE("another /mnt covers selected", BASE
         "40 31 0:40 / /mnt rw - tmpfs extra rw\n", UNKNOWN),
    CASE("missing selected /mnt parent", ROOT DATA
         "31 30 0:31 / /mnt rw - tmpfs scaffold rw\n", UNKNOWN),
    CASE("self-parent scaffold", ROOT DATA
         "31 31 0:31 / /mnt rw - tmpfs scaffold rw\n", UNKNOWN),
    CASE("cyclic same-point target stack", ROOT DATA
         "30 31 0:30 / /mnt rw - tmpfs old rw\n" OVER_OLD, UNKNOWN),
    CASE("wrong terminal parent", ROOT DATA
         "31 20 0:31 / /mnt rw - tmpfs scaffold rw\n", UNKNOWN),
    CASE("target prefix cover", BASE
         "40 31 0:40 / /mnt/gvi rw - tmpfs extra rw\n", UNKNOWN),
    CASE("existing root attachment", BASE
         "40 31 0:40 / " GUEST_TREE_TARGET_PATH " rw - tmpfs extra rw\n", UNKNOWN),
    CASE("target descendant", BASE
         "40 31 0:40 / " GUEST_TREE_TARGET_PATH "/system rw - tmpfs extra rw\n", UNKNOWN),
    CASE("scaffold child sibling cover", BASE
         "40 31 0:40 / /mnt/gvi/foreign rw - tmpfs extra rw\n", UNKNOWN),
    CASE("covered predecessor target cover", ROOT DATA OLD OVER_OLD
         "40 30 0:40 / /mnt/gvi rw - tmpfs extra rw\n", UNKNOWN),
    CASE("selected scaffold is not tmpfs", ROOT DATA
         "31 1 0:31 / /mnt rw - ext4 wrong rw\n", UNKNOWN),
    CASE("selected scaffold is a subtree", ROOT DATA
         "31 1 0:31 /bind /mnt rw - tmpfs wrong rw\n", UNKNOWN),
    CASE("shared scaffold", ROOT DATA
         "31 1 0:31 / /mnt rw shared:11 - tmpfs wrong rw\n", UNKNOWN),
    CASE("slave scaffold", ROOT DATA
         "31 1 0:31 / /mnt rw master:11 - tmpfs wrong rw\n", UNKNOWN),
    CASE("unbindable scaffold", ROOT DATA
         "31 1 0:31 / /mnt rw unbindable - tmpfs wrong rw\n", UNKNOWN),
    CASE("shared source backing mount", ROOT FRESH
         "20 1 8:2 / /data rw shared:11 - f2fs data rw\n", UNKNOWN),
    CASE("slave source backing mount", ROOT FRESH
         "20 1 8:2 / /data rw master:11 - f2fs data rw\n", UNKNOWN),
    CASE("source propagate-from", ROOT FRESH
         "20 1 8:2 / /data rw master:11 propagate_from:12 - f2fs data rw\n", UNKNOWN),
    CASE("unbindable source backing mount", ROOT FRESH
         "20 1 8:2 / /data rw unbindable - f2fs data rw\n", UNKNOWN),
    CASE("selected row at wrong source point", ROOT FRESH
         "20 1 8:2 / /elsewhere rw - f2fs data rw\n", UNKNOWN),
    CASE("selected row itself is a source attachment", ROOT FRESH
         "20 1 8:2 / " GUEST_TREE_SOURCE_PATH " rw - f2fs data rw\n", UNKNOWN),
    { "same projection from real lexical ancestor", BASE
      "22 20 8:2 /local /data/local rw - f2fs data rw\n",
      sizeof(BASE "22 20 8:2 /local /data/local rw - f2fs data rw\n") - 1,
      {22, 8, 2}, TARGET, MATCH },
    { "visible root can be backing ancestor", ROOT FRESH, sizeof(ROOT FRESH) - 1,
      {1, 8, 1}, TARGET, MATCH },
    { "tree inside dedicated read-only backing", BASE EROFS_ROW, sizeof(BASE EROFS_ROW) - 1,
      {50, 253, 1}, TARGET, MATCH },
};

int main(void) {
    const struct guest_tree_mount_identity source = SOURCE, target = TARGET;
    size_t full = sizeof(BASE) - 1;
    size_t capacity = sizeof(rows) / sizeof(rows[0]);

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        expect(cases[i].name, cases[i].input, cases[i].length, capacity,
               cases[i].source, cases[i].target, cases[i].expected);
    }
    expect("wrong source major", BASE, full, capacity,
           (struct guest_tree_mount_identity){20, 7, 2}, target, UNKNOWN);
    expect("wrong source minor", BASE, full, capacity,
           (struct guest_tree_mount_identity){20, 8, 3}, target, UNKNOWN);
    expect("wrong target dev", BASE, full, capacity,
           source, (struct guest_tree_mount_identity){31, 0, 32}, UNKNOWN);
    expect("no source mount id", BASE, full, capacity,
           (struct guest_tree_mount_identity){0, 8, 2}, target, UNKNOWN);
    expect("no target mount id", BASE, full, capacity,
           source, (struct guest_tree_mount_identity){0, 0, 31}, UNKNOWN);
    expect("same mount id", BASE, full, capacity, source, source, UNKNOWN);
    expect("null bytes", NULL, full, capacity, source, target, UNKNOWN);
    expect("zero bytes", BASE, 0, capacity, source, target, UNKNOWN);
    expect("insufficient scratch", BASE, full, 1, source, target, UNKNOWN);
    expect("oversize input", BASE, GPV_MOUNTINFO_MAX_BYTES + 1U, capacity,
           source, target, UNKNOWN);
    printf("PASS %u guest tree mount profile fixtures\n", checks);
    return 0;
}
