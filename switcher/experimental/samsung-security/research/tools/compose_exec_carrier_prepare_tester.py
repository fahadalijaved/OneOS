"""Bind the held offline preparation tester to the research controller."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


PREDECESSOR = ROOT / "out/file-stage-stop-cleanup-sdk-6a3b3d83/r-4a2f4014"
PREDECESSOR_SHA = "7dc21bac04fa1d29c77c30f6ee7fce282464b2cb10f0ead491bce7515f6b5b77"
RESEARCH = ROOT / "out/guest-exec-carrier-recovery-build/r-370116f9"
RESEARCH_SHA = "bf1035f80bce20400926b9140365a81f02cd0b6005a0141c95a3e85bb06beb76"


def verified_controller():
    research = json.loads(read_small(RESEARCH / "receipt.json", 256 * 1024, RESEARCH_SHA))
    artifact = research["artifact"]
    binary = RESEARCH / "oneos_exec_carrier_preflight"
    if artifact["path"] != binary.relative_to(ROOT).as_posix():
        raise ValueError("Unexpected research artifact path")
    stage = research["stagePath"]
    entry = research["entryArgument"]
    if stage != "/data/local/tmp/oneos-exec-research" or entry != "--exec-carrier-research-v1":
        raise ValueError("Unexpected research launch identity")
    image = read_small(binary, artifact["bytes"], artifact["sha256"])
    if (len(image) != artifact["bytes"] or not image.startswith(b"\x7fELF")
            or any(value.encode("ascii") + b"\x00" not in image for value in (stage, entry))):
        raise ValueError("Research artifact differs from its launch receipt")
    return artifact, stage, entry, binary.name


def build_sources():
    predecessor = json.loads(read_small(PREDECESSOR / "receipt.json", 256 * 1024, PREDECESSOR_SHA))
    artifact, stage, entry, binary_name = verified_controller()
    pins = predecessor["cohorts"]["app"]["sourcePins"]
    config = "BuildConfig.java"
    command = "RetainedRootOfferCommand.java"
    sources = {name: read_small(PREDECESSOR / "app/src" / name, 16 * 1024, pins[name])
               for name in (config, command)}
    old = predecessor["controller"]
    sources[config] = overlay(sources[config], [
        (f'"{old["sha256"]}"', f'"{artifact["sha256"]}"'),
        (f' = {old["bytes"]}L;', f' = {artifact["bytes"]}L;'),
    ])
    sources[command] = overlay(sources[command], [
        ("S=/data/local/tmp/oneos-viewprep", f"S={stage}"),
        ("P=$B/oneos_retained_tree_preparation", f"P=$B/{binary_name}"),
        ("--host-control-v2", entry),
    ])
    return sources, {name: pins[name] for name in sources}, artifact, stage, entry


def main():
    sources, old_pins, artifact, stage, entry = build_sources()
    run = ROOT / "out/exec-carrier-prepare-tester-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    for name, raw in sources.items():
        (run / name).write_bytes(raw)
    receipt = {
        "schema": 1, "status": "PASS_RESEARCH_PREPARATION_TESTER_SOURCE",
        "predecessorReceiptSha256": PREDECESSOR_SHA, "researchReceiptSha256": RESEARCH_SHA,
        "controller": artifact, "stagePath": stage, "entryArgument": entry,
        "predecessorSourcePins": old_pins,
        "sourcePins": {name: sha256(raw).hexdigest() for name, raw in sources.items()},
        "inverse": True, "selected": False, "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
