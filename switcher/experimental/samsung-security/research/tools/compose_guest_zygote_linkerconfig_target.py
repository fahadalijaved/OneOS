"""Add the owned bootstrap target to the unselected v7 child controller."""

from hashlib import sha256
import json
from uuid import uuid4

from compose_guest_zygote_slot_release import ROOT, overlay
from check_guest_tree_materialization_plan import read_small


BASE = ROOT / "out/guest-zygote-child-retained-build/r-ac1b0146"
BASE_RECEIPT = "8a736d2bdeb578047b58f92edad829494e559c54fdf37ec092c5681500df65f9"
NAME = "guest_tree_control_owner.c"


def controller(raw):
    include = '#include "guest_zygote_child_retained.h"'
    signature_end = """        const struct gtc_child_inputs *input, struct gtc_child_view *view,
        struct gtc_wire *packet) {"""
    retire = "            || guest_zygote_retire_inherited_view(fds, view, entry) < 0"
    owners = "    struct guest_zygote_child_owner entry = {0};"
    call = """        if (prepare_child_entry(&launch_fds, &launch_slots, &null_source, &entry,
                                &input, &view, &packet) < 0) _exit(2);
    }
    _exit(0);"""
    return overlay(raw, [
        (include, include + '\n#include "guest_linkerconfig_target.h"'),
        (signature_end, """        const struct gtc_child_inputs *input, struct gtc_child_view *view,
        struct guest_linkerconfig_generation_start *target, struct gtc_wire *packet) {"""),
        (retire, """            || guest_linkerconfig_prepare_target(view->rights[GTC_GUEST_ROOT],
                    view->observation.mounts[GTC_GUEST_ROOT], target) < 0
            || child_entry_window() < 0
""" + retire),
        (owners, owners + """
    struct guest_linkerconfig_generation_start target = {.directory_fd = -1, .base_fd = -1};"""),
        (call, """        if (prepare_child_entry(&launch_fds, &launch_slots, &null_source, &entry,
                                &input, &view, &target, &packet) < 0) _exit(2);
    }
    int status = 0;
    if (target.base_fd >= 0 && close(target.base_fd) < 0) status = 2;
    if (target.directory_fd >= 0 && close(target.directory_fd) < 0) status = 2;
    _exit(status);"""),
    ])


def main():
    prior = json.loads(read_small(BASE / "receipt.json", 64 * 1024, BASE_RECEIPT))
    pin = prior["sourcePins"][NAME]
    changed = controller(read_small(BASE / "src" / NAME, 64 * 1024, pin))
    run = ROOT / "out/guest-zygote-linkerconfig-target-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / NAME).write_bytes(changed)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_CHILD_LINKERCONFIG_TARGET_OVERLAY",
        "baseReceiptSha256": BASE_RECEIPT, "inputSha256": pin,
        "sourceSha256": sha256(changed).hexdigest(),
        "inverse": True, "wireChange": False, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
