"""Join the parked child's linkerconfig target to the research parent verifier."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-linkerconfig-target-build/r-19959000"
BASE_RECEIPT = "aa89362e56fb932006e5406aee03931d9c7984eb83a9db6b3ab821bd6981e0af"
HEADER = '#include "guest_linkerconfig_parent_readback.h"'


def mountinfo_reader(raw):
    include = '#include "guest_tree_parent_view.h"'
    return overlay(raw, [
        (include, include + "\n" + HEADER),
        ("static int read_table(int task,", "int guest_tree_read_task_mountinfo(int task,"),
        ("read_table(self, &proc_identity,", "guest_tree_read_task_mountinfo(self, &proc_identity,"),
        ("read_table(task, &proc_identity,", "guest_tree_read_task_mountinfo(task, &proc_identity,"),
    ])


def parent_reader(raw):
    include = '#include "guest_zygote_parent_readback.h"'
    start = "int guest_zygote_parent_readback(pid_t child,"
    first_links = """    if (follow_proc_link(fd[TASK], "root", PATH_DIRECTORY, &proc, &fd[LIVE_ROOT]) < 0
            || root_identity(fd[LIVE_ROOT], mount_id, &current) < 0) goto failed;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto failed; }
    if (follow_proc_link(fd[TASK], "cwd", PATH_DIRECTORY, &proc, &fd[LIVE_CWD]) < 0
            || root_identity(fd[LIVE_CWD], mount_id, &current) < 0) goto failed;
    if (!guest_readback_same_node(&root, &current)) { errno = ESTALE; goto failed; }
    if (follow_proc_link(fd[NS_DIR], "mnt", O_RDONLY | O_CLOEXEC, &proc, &fd[LIVE_NS]) < 0
            || namespace_identity(fd[LIVE_NS], admitted) < 0) goto failed;"""
    sample = """static int sample_live_links(int fd[SLOTS], const struct statx *proc,
        const struct statx *root, const struct gtc_observation *admitted) {
    struct statx current;
    uint64_t mount_id = root->stx_mnt_id;
""" + first_links.replace("&proc,", "proc,").replace("&root,", "root,").replace(
        "{ errno = ESTALE; goto failed; }", "return guest_readback_refuse(ESTALE);"
    ).replace("goto failed;", "return -1;") + """
    return 0;
}

"""
    final = '            || same_directory(fd[TASK], "ns", fd[NS_DIR], &ns_dir) < 0'
    return overlay(raw, [
        (include, include + "\n" + HEADER),
        (start, sample + start),
        (first_links, """    if (sample_live_links(fd, &proc, &root, admitted) < 0
            || guest_linkerconfig_parent_readback(fd[LIVE_ROOT], fd[TASK], &proc, close_error) < 0) goto failed;
    for (int i = SLOTS; i > LIVE_ROOT; --i) close_owned(&fd[i - 1], &primary, close_error);
    if (primary) goto done;"""),
        (final, final + "\n            || sample_live_links(fd, &proc, &root, admitted) < 0"),
    ])


def main():
    prior = json.loads(read_small(BASE / "receipt.json", 192 * 1024, BASE_RECEIPT))
    transforms = {
        "guest_tree_parent_view.c": mountinfo_reader,
        "guest_zygote_parent_readback.c": parent_reader,
    }
    inputs = {name: prior["sourcePins"][name] for name in transforms}
    outputs = {
        name: transform(read_small(BASE / "src" / name, 64 * 1024, inputs[name]))
        for name, transform in transforms.items()
    }
    run = ROOT / "out/guest-zygote-linkerconfig-observation-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_CHILD_LINKERCONFIG_OBSERVATION_OVERLAY",
        "baseReceiptSha256": BASE_RECEIPT, "inputs": inputs,
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
        "inverse": True, "wireChange": False, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
