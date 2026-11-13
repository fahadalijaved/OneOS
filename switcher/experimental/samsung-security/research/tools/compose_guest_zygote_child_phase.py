"""Compose the no-exec child preparation successor to the slot-release wire."""

from hashlib import sha256
import json
from uuid import uuid4

from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-slot-phase-source/r-2f113d5b"
BASE_RECEIPT = "a24d92b6d9d3a4ffffc9e7f2e1b3469430a13d8626a62674a13ef143486caec7"

CHILD = """static int child_entry_window(void) {
    if (getppid() != one.parent) { errno = ECHILD; return -1; }
    return slot_phase_timeout(one.deadline) > 0 ? 0 : -1;
}

static int prepare_child_entry(int control, struct guest_zygote_slot_owner *slots,
        struct guest_zygote_null_owner *null_source, struct guest_zygote_child_owner *entry,
        const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        struct gtc_wire *packet) {
    struct gtc_observation empty = {0};
    if (packet->kind != W_PREPARE_CHILD || packet->stage || packet->error
            || memcmp(&packet->view, &empty, sizeof(empty)) || slots->state != GUEST_ZYGOTE_SLOTS_HELD
            || null_source->state != GUEST_ZYGOTE_NULL_NEW || entry->state != GUEST_ZYGOTE_CHILD_NEW) {
        errno = EPROTO;
        return -1;
    }
    if (child_entry_window() < 0) return -1;
    if (guest_zygote_null_acquire(view->rights[GTC_INHERITED_ROOT],
                view->observation.mounts[GTC_INHERITED_ROOT], slots, null_source) < 0
            || child_entry_window() < 0
            || guest_zygote_slots_release(slots) < 0
            || child_entry_window() < 0
            || guest_zygote_child_prepare(input, view, null_source->fd, entry) < 0
            || guest_zygote_null_close(null_source) < 0
            || child_entry_window() < 0) {
        int error = errno ? errno : EIO;
        init_wire(packet, W_ERROR, S_CHILD_PREPARE);
        packet->error = error > 0 && error < 4096 ? error : EPROTO;
        if (child_entry_window() == 0) (void)send_wire(control, packet, NULL);
        errno = error;
        return -1;
    }
    init_wire(packet, W_CHILD_PREPARED, S_READBACK);
    packet->view = view->observation;
    return send_wire(control, packet, NULL);
}

"""


def rename(raw, pairs):
    changed = raw
    for before, after in pairs:
        if before not in changed or after in changed:
            raise ValueError(f"Unexpected child-phase name {before!r}")
        changed = changed.replace(before, after)
    restored = changed
    for before, after in reversed(pairs):
        restored = restored.replace(after, before)
    if restored != raw:
        raise ValueError("Child-phase name inverse differs")
    return changed


def controller(raw):
    raw = rename(raw, [
        (b"0x47545336", b"0x47545a37"), (b"packet->version = 6", b"packet->version = 7"),
        (b"packet->version != 6", b"packet->version != 7"),
        (b"GTS v6", b"GTZ v7"), (b"slot-release shape", b"child-preparation shape"),
        (b"W_RELEASE_SLOTS", b"W_PREPARE_CHILD"), (b"W_SLOTS_RELEASED", b"W_CHILD_PREPARED"),
        (b"S_SLOT_RELEASE", b"S_CHILD_PREPARE"), (b"slot_release_attempted", b"entry_prepare_attempted"),
        (b"confirm_slot_release", b"confirm_child_prepared"),
        (b"gtc_release_startup_slots", b"gtc_prepare_child_entry"),
    ])
    text = raw.decode("ascii").replace("\r\n", "\n")
    first = text.index("static int release_child_slots(")
    last = text.index("static _Noreturn void run_child(", first)
    include = '#include "guest_zygote_slot_owner.h"'
    old_call = "        if (release_child_slots(control, &launch_slots, &view.observation, &packet) < 0) _exit(2);"
    slots = "    struct guest_zygote_slot_owner launch_slots = {0};"
    return overlay(raw, [
        (include, include + '\n#include "guest_zygote_null_owner.h"\n#include "guest_zygote_child_prepare.h"'),
        (text[first:last], CHILD),
        (slots, slots + "\n    struct guest_zygote_null_owner null_source = {0};"
         "\n    struct guest_zygote_child_owner entry = {0};"),
        (old_call, """        if (prepare_child_entry(control, &launch_slots, &null_source, &entry,
                                &input, &view, &packet) < 0) _exit(2);"""),
    ])


def main():
    receipt = (BASE / "receipt.json").read_bytes()
    if sha256(receipt).hexdigest() != BASE_RECEIPT:
        raise ValueError("Pinned slot-release source receipt changed")
    pins = json.loads(receipt)["sources"]
    control = "guest_tree_control_owner.c"
    header = "guest_tree_control_owner.h"
    provider = "guest_tree_stage_provider.c"
    inputs = {name: (BASE / name).read_bytes() for name in (control, header, provider)}
    if any(sha256(data).hexdigest() != pins[name] for name, data in inputs.items()):
        raise ValueError("Pinned slot-release source changed")
    names = [(b"gtc_release_startup_slots", b"gtc_prepare_child_entry")]
    outputs = {
        control: controller(inputs[control]),
        header: rename(inputs[header], names),
        provider: rename(inputs[provider], names),
    }
    run = ROOT / "out/guest-zygote-child-phase-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    result = {
        "schema": 1, "status": "PASS_EXACT_CHILD_PREPARATION_SOURCE_OVERLAY",
        "selected": False, "deviceEligible": False, "targetExecuted": False,
        "inverse": True, "baseReceipt": BASE_RECEIPT, "wireVersion": 7,
        "inputs": pins, "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
