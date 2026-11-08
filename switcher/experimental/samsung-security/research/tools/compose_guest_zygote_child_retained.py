"""Retire child startup witnesses before the v7 preparation acknowledgment."""

from hashlib import sha256
import json
from uuid import uuid4

from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-view-scratch-build/r-533194f2"
BASE_RECEIPT = "6315bcf041b0e9005d7563dbb5b68b8a9df7f6ffec63111a319a25f1ca7b44f8"


def controller(raw):
    include = '#include "guest_zygote_view_scratch.h"'
    signature = """static int prepare_child_entry(int control, struct guest_zygote_slot_owner *slots,
        struct guest_zygote_null_owner *null_source, struct guest_zygote_child_owner *entry,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        struct gtc_wire *packet) {"""
    call = """        if (prepare_child_entry(control, &launch_slots, &null_source, &entry,
                                &input, &view, &packet) < 0) _exit(2);"""
    after_null = """            || guest_zygote_null_close(null_source) < 0
            || child_entry_window() < 0) {"""
    return overlay(raw, [
        (include, include + '\n#include "guest_zygote_child_retained.h"'),
        (signature, signature.replace("int control,", "struct guest_zygote_control_fds *fds,")
         .replace("const struct gtc_child_view *view", "struct gtc_child_view *view")
         + "\n    int control = fds->control;"),
        (after_null, """            || guest_zygote_null_close(null_source) < 0
            || child_entry_window() < 0
            || guest_zygote_retire_inherited_view(fds, view, entry) < 0
            || child_entry_window() < 0) {"""),
        (call, call.replace("prepare_child_entry(control,", "prepare_child_entry(&launch_fds,")),
    ])


def main():
    receipt = (BASE / "receipt.json").read_bytes()
    if sha256(receipt).hexdigest() != BASE_RECEIPT:
        raise ValueError("Pinned tracked child-view build receipt changed")
    name = "guest_tree_control_owner.c"
    pin = json.loads(receipt.decode("utf-8-sig"))["sourcePins"][name]
    raw = (BASE / "src" / name).read_bytes()
    if sha256(raw).hexdigest() != pin:
        raise ValueError("Pinned tracked controller source changed")
    changed = controller(raw)
    run = ROOT / "out/guest-zygote-child-retained-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / name).write_bytes(changed)
    result = {
        "schema": 1, "status": "PASS_EXACT_CHILD_RETAINED_FD_SOURCE_OVERLAY",
        "selected": False, "deviceEligible": False, "targetExecuted": False,
        "inverse": True, "baseReceipt": BASE_RECEIPT, "wireChange": False,
        "inputs": {name: pin}, "sources": {name: sha256(changed).hexdigest()},
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
