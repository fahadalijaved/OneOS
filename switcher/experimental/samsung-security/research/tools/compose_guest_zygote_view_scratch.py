"""Track and retire the v7 child-view construction scratch before Partial."""

from hashlib import sha256
import json
import re
from uuid import uuid4

from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-post-entry-build/r-5b272267"
BASE_RECEIPT = "f1e217e598fd8bcfa25069f93ded8e268efba772ec77fe4e7914dc99461a8675"

ROLES = (
    "TREE", "SOURCE_DATA", "COVERED_DATA", "COVERED_MIRROR",
    "OLD_MNT", "FRESH_MNT", "WRITABLE_MNT", "SCAFFOLD", "ROOT_TARGET", "ATTACHED_CLONE",
    "DATA_TARGET", "GUEST_DATA",
    "ALIAS_SOURCE", "ALIAS_TARGET", "NATIVE_ALIAS", "GUEST_ALIAS",
    "MIRROR_TARGET", "MIRROR_WRITABLE", "GUEST_MIRROR",
    "INHERITED_DEV", "DEV_TARGET", "DEV_WRITABLE", "SOCKET_WRITABLE", "INHERITED_DEV_AFTER",
)


def tracked(assignment, role):
    head, tail = assignment.split(" = ", 1)
    return assignment, f"{head} = scratch[SCRATCH_{role}] = {tail}"


def section(text, start, end, pairs):
    first = text.index(start)
    last = text.index(end, first + len(start))
    original = text[first:last]
    updated = overlay(original.encode("ascii"), pairs).decode("ascii")
    return original, updated


def builder(raw):
    text = raw.decode("ascii").replace("\r\n", "\n")
    include = '#include "guest_tree_child_view.h"'
    roles = "enum {\n" + "".join(f"    SCRATCH_{role},\n" for role in ROLES) + "    SCRATCH_COUNT\n};\n"
    roles += """_Static_assert((int)SCRATCH_COUNT == (int)GUEST_ZYGOTE_VIEW_SCRATCH_COUNT,
        "One cell per retained construction descriptor");"""
    scaffold = section(text, "static int scaffold_root(", "struct peer_view {", [
        ("int *target) {", "int *target, int *scratch) {"),
        tracked('int old_mnt = openat(inherited_root, "mnt", O_DIR);', "OLD_MNT"),
        tracked('int fresh_mnt = openat(inherited_root, "mnt", O_DIR);', "FRESH_MNT"),
        tracked('int writable_mnt = openat(fresh_mnt, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);', "WRITABLE_MNT"),
        tracked('*scaffold = openat(writable_mnt, "gvi", O_DIR);', "SCAFFOLD"),
        tracked('*target = openat(*scaffold, "root", O_DIR);', "ROOT_TARGET"),
    ])
    data = section(text, "static int make_data_peers(", "struct alias_view {", [
        ("struct peer_view *data) {", "struct peer_view *data, int *scratch) {"),
        tracked('int target = openat(tree_root, "data", O_DIR);', "DATA_TARGET"),
        tracked('data->guest = openat(tree_root, "data", O_DIR);', "GUEST_DATA"),
    ])
    alias = section(text, "static int make_aliases(", "static int make_mirror_peers(", [
        ("struct alias_view *alias) {", "struct alias_view *alias, int *scratch) {"),
        tracked('alias->source = walk(data->native, "user/0");', "ALIAS_SOURCE"),
        tracked('int target = openat(data->native, "data", O_DIR);', "ALIAS_TARGET"),
        tracked('alias->native = openat(data->native, "data", O_DIR);', "NATIVE_ALIAS"),
        tracked('alias->guest = openat(data->guest, "data", O_DIR);', "GUEST_ALIAS"),
    ])
    mirror = section(text, "static int make_mirror_peers(", "static int make_dev(", [
        ("struct peer_view *mirror) {", "struct peer_view *mirror, int *scratch) {"),
        tracked('int target = openat(tree_root, "data_mirror", O_DIR);', "MIRROR_TARGET"),
        tracked('int writable = openat(mirror->native, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);', "MIRROR_WRITABLE"),
        tracked('mirror->guest = openat(tree_root, "data_mirror", O_DIR);', "GUEST_MIRROR"),
    ])
    dev = section(text, "static int make_dev(", "static int observe_aliases(", [
        ("int *socket) {", "int *socket, int *scratch) {"),
        tracked('int inherited = openat(inherited_root, "dev", O_DIR);', "INHERITED_DEV"),
        tracked('int target = openat(tree_root, "dev", O_DIR);', "DEV_TARGET"),
        tracked('int writable = openat(*dev, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);', "DEV_WRITABLE"),
        tracked('int socket_write = openat(writable, "socket", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);', "SOCKET_WRITABLE"),
        tracked('int inherited_after = openat(inherited_root, "dev", O_DIR);', "INHERITED_DEV_AFTER"),
    ])
    declaration = """int guest_tree_prepare_child_view(const struct gtc_child_inputs *input,
                                  struct gtc_child_view *view, void *context)"""
    typed = """int guest_tree_prepare_tracked_child_view(const struct gtc_child_inputs *input,
        struct gtc_child_view *view, const struct guest_zygote_view_context *context)"""
    changed = overlay(raw, [
        (include, include + '\n#include "guest_zygote_view_scratch.h"\n\n' + roles),
        scaffold, data, alias, mirror, dev,
        (declaration, typed),
        ("|| !view || context ||", "|| !view || !context ||"),
        ("    struct mount_sample before = {0}, after = {0};",
         """    int scratch[SCRATCH_COUNT];
    for (size_t i = 0; i < SCRATCH_COUNT; ++i) scratch[i] = -1;
    struct mount_sample before = {0}, after = {0};"""),
        tracked("int tree = walk(root, &TREE_PATH[1]);", "TREE"),
        tracked("int source_data = walk(root, &PRIVATE_DATA[1]);", "SOURCE_DATA"),
        tracked('int covered_data = openat(root, "data", O_DIR);', "COVERED_DATA"),
        tracked('int covered_mirror = openat(root, "data_mirror", O_DIR);', "COVERED_MIRROR"),
        ("scaffold_root(root, &after, &scaffold, &target)", "scaffold_root(root, &after, &scaffold, &target, scratch)"),
        ("    int guest = actual.rights[GTC_GUEST_ROOT]",
         "    scratch[SCRATCH_ATTACHED_CLONE] = prepared.attachment.clone_fd;\n    int guest = actual.rights[GTC_GUEST_ROOT]"),
        ("make_data_peers(root, guest, source_data, covered_data, &data)",
         "make_data_peers(root, guest, source_data, covered_data, &data, scratch)"),
        ("make_aliases(&data, &alias)", "make_aliases(&data, &alias, scratch)"),
        ("make_mirror_peers(root, guest, covered_mirror, &after, &mirror)",
         "make_mirror_peers(root, guest, covered_mirror, &after, &mirror, scratch)"),
        ("&actual.rights[GTC_SOCKET]) < 0", "&actual.rights[GTC_SOCKET], scratch) < 0"),
        ("    *view = actual;", """    if (guest_zygote_view_scratch_close(scratch, input, &actual, context) < 0
            || current_parent(input) < 0) goto done;
    *view = actual;"""),
        ("done:\n    /* The private child owns even failure-path mount references",
         "done: {\n    int primary = errno;\n    /* The private child owns even failure-path mount references"),
        ("    free(inherited.ids);\n    return result;\n}",
         "    free(inherited.ids);\n    if (result < 0) errno = primary;\n    return result;\n}\n}"),
    ])
    seen = re.findall(rb"scratch\[SCRATCH_([A-Z_]+)\] = ", changed)
    if len(seen) != len(ROLES) or set(seen) != {role.encode("ascii") for role in ROLES}:
        raise ValueError("Incomplete or duplicate construction roster")
    return changed


def header(raw):
    text = raw.decode("ascii").replace("\r\n", "\n")
    first = text.index("/* Fixed prepare-only callback")
    last = text.index("#endif", first)
    return overlay(raw, [(text[first:last], """struct guest_zygote_view_context;

/* Research controller only. Borrow the relocated witnesses and control
 * cell. Success closes construction scratch before exposing the seven
 * retained rights. The exact child owns retirement after refusal. */
int guest_tree_prepare_tracked_child_view(const struct gtc_child_inputs *input,
        struct gtc_child_view *view, const struct guest_zygote_view_context *context);

""")])


def controller(raw):
    include = '#include "guest_zygote_child_prepare.h"'
    old = "    if (guest_tree_prepare_child_view(&input, &view, NULL) != 0 || !valid_observation(&view.observation)) {"
    return overlay(raw, [
        (include, include + '\n#include "guest_zygote_view_scratch.h"'),
        (old, """    const struct guest_zygote_view_context scratch_context = {.control_fd = control};
    if (guest_tree_prepare_tracked_child_view(&input, &view, &scratch_context) != 0
            || !valid_observation(&view.observation)) {"""),
    ])


def main():
    receipt = (BASE / "receipt.json").read_bytes()
    if sha256(receipt).hexdigest() != BASE_RECEIPT:
        raise ValueError("Pinned post-entry build receipt changed")
    pins = json.loads(receipt.decode("utf-8-sig"))["sourcePins"]
    transforms = {
        "guest_tree_child_view.c": builder,
        "guest_tree_child_view.h": header,
        "guest_tree_control_owner.c": controller,
    }
    inputs = {name: (BASE / "src" / name).read_bytes() for name in transforms}
    if any(sha256(data).hexdigest() != pins[name] for name, data in inputs.items()):
        raise ValueError("Pinned child-view source changed")
    outputs = {name: transform(inputs[name]) for name, transform in transforms.items()}
    run = ROOT / "out/guest-zygote-view-scratch-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    result = {
        "schema": 1, "status": "PASS_EXACT_TRACKED_CHILD_VIEW_SOURCE_OVERLAY",
        "selected": False, "deviceEligible": False, "targetExecuted": False,
        "inverse": True, "baseReceipt": BASE_RECEIPT, "wireChange": False,
        "constructionRoles": ROLES, "inputs": {name: pins[name] for name in inputs},
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
