"""Derive a separate whole-carrier research profile from the closed v8 link."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-v8-closure-build/r-a2a77cb6"
BASE_RECEIPT = "a9421dcf7b510cfc1bbebdeb5081267f1c8574f11497ea3c6868405e77cee7be"
OLD_STAGE = "oneos-viewprep"
STAGE = "oneos-exec-research"

EDITS = {
    "guest_tree_source_mounts.h": [
        ('#define GUEST_TREE_STAGE_PATH "/data/local/tmp/oneos-viewprep"',
         f'#define GUEST_TREE_STAGE_NAME "{STAGE}"\n'
         '#define GUEST_TREE_STAGE_PATH "/data/local/tmp/" GUEST_TREE_STAGE_NAME'),
    ],
    "guest_tree_fsverity_file.c": [
        ('named_node(fd[TMP], "oneos-viewprep",', 'named_node(fd[TMP], GUEST_TREE_STAGE_NAME,'),
        ('openat(fd[TMP], "oneos-viewprep",', 'openat(fd[TMP], GUEST_TREE_STAGE_NAME,'),
    ],
    "guest_tree_file_erofs_mount.c": [
        ("ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC;", "ST_RDONLY | ST_NOSUID | ST_NODEV;"),
        ("(flags.f_flag & required) != required", "(flags.f_flag & (required | ST_NOEXEC)) != required"),
        ("MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV | MOUNT_ATTR_NOEXEC);",
         "MOUNT_ATTR_RDONLY | MOUNT_ATTR_NOSUID | MOUNT_ATTR_NODEV);"),
    ],
    "guest_tree_file_erofs_attach.c": [
        ('"tmp", "oneos-viewprep"', '"tmp", GUEST_TREE_STAGE_NAME'),
        ("(ST_RDONLY | ST_NOSUID | ST_NODEV | ST_NOEXEC)", "(ST_RDONLY | ST_NOSUID | ST_NODEV)"),
        ('!mount_option(row->options, "noexec", 0)', 'mount_option(row->options, "noexec", 1)'),
        ("(flags.f_flag & EROFS_FLAGS) != EROFS_FLAGS",
         "(flags.f_flag & (EROFS_FLAGS | ST_NOEXEC)) != EROFS_FLAGS"),
    ],
    "guest_tree_root_attach.c": [
        ("(clone_fs.f_flag & required_flags) != required_flags",
         "(clone_fs.f_flag & (required_flags | ST_NOEXEC)) != required_flags"),
    ],
    "guest_tree_file_erofs_release.c": [
        ("(vfs.f_flag & required) != required", "(vfs.f_flag & (required | ST_NOEXEC)) != required"),
        ('|| has_option(mount->options, "rw") || !has_option(mount->super_options, "ro")',
         '|| has_option(mount->options, "noexec") || has_option(mount->options, "rw")\n'
         '                || !has_option(mount->super_options, "ro")'),
    ],
    "guest_tree_file_stage.c": [
        ("    if (gtsn_borrow(owner->namespace, &ns) < 0 || guest_tree_stage_guard_check(guard) < 0) return -1;",
         """    struct guest_tree_fsverity_borrow confirmed = {-1, -1};
    if (gtsn_borrow(owner->namespace, &ns) < 0 || guest_tree_stage_guard_check(guard) < 0
            || guest_tree_fsverity_borrow_fds(owner->file, &confirmed) < 0) return -1;
    if (confirmed.image_fd != files.image_fd || confirmed.proc_root_fd != files.proc_root_fd)
        return refuse(ESTALE);"""),
    ],
    "guest_linkerconfig_parent_readback.c": [
        ("    struct statvfs flags;", "    struct statvfs root_flags, flags;"),
        ("    if (fstatfs(root, &root_fs) < 0 || fstatfs(directory, &directory_fs) < 0",
         "    if (fstatfs(root, &root_fs) < 0 || fstatvfs(root, &root_flags) < 0\n"
         "            || fstatfs(directory, &directory_fs) < 0"),
        ("            || (unsigned long)directory_fs.f_type != TMPFS_MAGIC",
         "            || (root_flags.f_flag & (required | ST_RDONLY)) != (ST_RDONLY | ST_NOSUID | ST_NODEV)\n"
         "            || (unsigned long)directory_fs.f_type != TMPFS_MAGIC"),
        ('|| strcmp(root->type, "erofs")', '|| strcmp(root->type, "erofs")\n'
         '            || has_option(root->options, "noexec")'),
    ],
}


def derive():
    prior = json.loads(read_small(BASE / "receipt.json", 224 * 1024, BASE_RECEIPT))
    pins = prior["sourcePins"]
    outputs = {}
    for name, pin in pins.items():
        raw = read_small(BASE / "src" / name, 128 * 1024, pin)
        if name in EDITS:
            raw = overlay(raw, EDITS[name])
            outputs[name] = raw
        if OLD_STAGE.encode("ascii") in raw:
            raise ValueError(f"Old stage reference in {name}")
    if outputs.keys() != EDITS.keys():
        raise ValueError("Missing required research source")
    return pins, outputs


def main():
    pins, outputs = derive()
    run = ROOT / "out/guest-exec-carrier-research-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, raw in outputs.items():
        (run / name).write_bytes(raw)
    receipt = {
        "schema": 1, "status": "PASS_SEPARATE_EXEC_CARRIER_RESEARCH_SOURCE_OVERLAY",
        "baseReceiptSha256": BASE_RECEIPT, "stageName": STAGE,
        "sharedGuard": "/dev/oneos-retained-viewprep",
        "inputs": {name: pins[name] for name in outputs},
        "sources": {name: sha256(raw).hexdigest() for name, raw in outputs.items()},
        "inverse": True, "selected": False, "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
