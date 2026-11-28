"""Require independent parent readback after the no-exec v7 preparation reply."""

from hashlib import sha256
import json
from uuid import uuid4

from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-zygote-child-phase-build/r-3794aebf"
BASE_RECEIPT = "6527cccd64c8ba08bfaac91c550bc7e9bad65dd5c36b6091d503171cf1f8bdd0"

VERIFY = """int gtr_verify_prepared_child(struct gtr_owner *owner,
        const struct gtc_observation *admitted, int *close_error) {
    if (!admitted || !close_error) { errno = EINVAL; return -1; }
    if (enter_owner(owner) < 0) return -1;
    int result = -1;
    if (owner->cutoff || !owner->rights_taken || owner->close_error || *close_error) {
        errno = EBUSY;
        goto done;
    }
    int live = observe_child(owner);
    if (live != 1) {
        if (live == 0) errno = ECHILD;
        goto done;
    }
    if (guest_zygote_parent_readback(owner->child, owner->rights[GTC_GUEST_ROOT],
                owner->rights[GTC_NAMESPACE], admitted, close_error) < 0) goto done;
    if (*close_error) { errno = *close_error; goto done; }
    live = observe_child(owner);
    if (live != 1) {
        if (live == 0) errno = ECHILD;
        goto done;
    }
    result = 0;
done:
    leave();
    return result;
}

"""


def controller(raw):
    end = """        if (slot_child_live(owner) < 0 || slot_phase_timeout(owner->deadline) < 0) return -1;
        return 0;
    }
}

int gtc_prepare_child_entry("""
    return overlay(raw, [(end, end.replace("        return 0;",
        """        if (gtr_verify_prepared_child(owner->release, &owner->slot_base, &owner->close_error) < 0
                || slot_phase_timeout(owner->deadline) < 0) return -1;
        return 0;""", 1))])


def release_owner(raw):
    include = '#include "guest_tree_release_owner.h"'
    before = "static void cut_off(struct gtr_owner *owner) {"
    return overlay(raw, [
        (include, include + '\n#include "guest_zygote_parent_readback.h"'),
        (before, VERIFY + before),
    ])


def release_header(raw):
    before = "int gtr_take_view_rights(struct gtr_owner *owner, int rights[GTR_VIEW_RIGHTS]);"
    return overlay(raw, [(before, before + """

/* Research variant only. Read the prepared child through the still-owned
 * exact guest-root and namespace roles and the sole waiter. */
struct gtc_observation;
int gtr_verify_prepared_child(struct gtr_owner *owner,
        const struct gtc_observation *admitted, int *close_error);""")])


def main():
    receipt = (BASE / "receipt.json").read_bytes()
    if sha256(receipt).hexdigest() != BASE_RECEIPT:
        raise ValueError("Pinned v7 build receipt changed")
    pins = json.loads(receipt.decode("utf-8-sig"))["sourcePins"]
    transforms = {
        "guest_tree_control_owner.c": controller,
        "guest_tree_release_owner.c": release_owner,
        "guest_tree_release_owner.h": release_header,
    }
    inputs = {name: (BASE / "src" / name).read_bytes() for name in transforms}
    if any(sha256(data).hexdigest() != pins[name] for name, data in inputs.items()):
        raise ValueError("Pinned v7 owner source changed")
    outputs = {name: transform(inputs[name]) for name, transform in transforms.items()}
    run = ROOT / "out/guest-zygote-post-entry-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, data in outputs.items():
        (run / name).write_bytes(data)
    result = {
        "schema": 1, "status": "PASS_EXACT_POST_ENTRY_SOURCE_OVERLAY",
        "selected": False, "deviceEligible": False, "targetExecuted": False,
        "inverse": True, "baseReceipt": BASE_RECEIPT, "wireChange": False,
        "inputs": {name: pins[name] for name in inputs},
        "sources": {name: sha256(data).hexdigest() for name, data in outputs.items()},
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
