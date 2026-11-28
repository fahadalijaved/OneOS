"""Retarget the offline host's exact Stop-role controller identity."""

from hashlib import sha256
import json
from uuid import uuid4

from compose_exec_carrier_prepare_tester import (
    PREDECESSOR,
    PREDECESSOR_SHA,
    RESEARCH_SHA,
    verified_controller,
)
from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


def main():
    predecessor = json.loads(read_small(PREDECESSOR / "receipt.json", 256 * 1024, PREDECESSOR_SHA))
    artifact, _, _, _ = verified_controller()
    name = "RetainedHostNativeControlV2.java"
    pin = predecessor["cohorts"]["host"]["sourcePins"][name]
    source = read_small(PREDECESSOR / "host/src" / name, 64 * 1024, pin)
    old = predecessor["controller"]

    def predicate(controller):
        return (
            f'        stopRoleProfile = "{controller["sha256"]}".equals(loadedProfile.nativeSha256())\n'
            f'                && loadedProfile.nativeBytes() == {controller["bytes"]}L;'
        )

    changed = overlay(source, [(predicate(old), predicate(artifact))])
    run = ROOT / "out/exec-carrier-prepare-host-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / name).write_bytes(changed)
    receipt = {
        "schema": 1, "status": "PASS_RESEARCH_PREPARATION_HOST_SOURCE",
        "predecessorReceiptSha256": PREDECESSOR_SHA, "researchReceiptSha256": RESEARCH_SHA,
        "controller": artifact, "predecessorSourcePins": {name: pin},
        "sourcePins": {name: sha256(changed).hexdigest()},
        "inverse": True, "selected": False, "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
