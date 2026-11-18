"""Bind the held preparation entry to a distinct offline research command."""

from hashlib import sha256
import json
from uuid import uuid4

from check_guest_tree_materialization_plan import read_small
from compose_guest_zygote_slot_release import ROOT, overlay


BASE = ROOT / "out/guest-exec-carrier-bootstrap-loader-build/r-18273101"
BASE_RECEIPT = "4eaae9488fc14fd271f8cb3cba129ab1b314a0afd4a9ae4c16338a1c2c147278"
ORIGINAL = ROOT / "out/file-stage-controller-successor-build/r-122795bb"
ORIGINAL_RECEIPT = "e0f0e28c7f7d9e7fde233d43b0c2266c849fce9968913c90a708483165a8b1b8"
ENTRY_SOURCE = "retained_root_handoff.c"
OLD_ARGUMENT = "--host-control-v2"
RESEARCH_ARGUMENT = "--exec-carrier-research-v1"
ARTIFACT_NAME = "oneos_exec_carrier_preflight"


def entry_source():
    base = json.loads(read_small(BASE / "receipt.json", 256 * 1024, BASE_RECEIPT))
    prior = json.loads(read_small(ORIGINAL / "receipt.json", 192 * 1024, ORIGINAL_RECEIPT))
    pin = base["sourcePins"][ENTRY_SOURCE]
    if pin != prior["sourcePins"][ENTRY_SOURCE]:
        raise ValueError("Research and original preparation entry sources differ")
    staged = read_small(BASE / "src" / ENTRY_SOURCE, 64 * 1024, pin)
    original = read_small(ORIGINAL / "source" / ENTRY_SOURCE, 64 * 1024, pin)
    if staged != original:
        raise ValueError("Held entry changed")
    gate = f'    if (argc!=2 || strcmp(argv[1],"{OLD_ARGUMENT}")) return 2;'
    return pin, overlay(staged, [(gate, gate.replace(OLD_ARGUMENT, RESEARCH_ARGUMENT))])


def main():
    pin, changed = entry_source()
    run = ROOT / "out/guest-exec-carrier-entry-source" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / ENTRY_SOURCE).write_bytes(changed)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_RESEARCH_PREPARATION_ENTRY_SOURCE",
        "baseReceiptSha256": BASE_RECEIPT, "originalReceiptSha256": ORIGINAL_RECEIPT,
        "inputSha256": pin, "sources": {ENTRY_SOURCE: sha256(changed).hexdigest()},
        "entryArgument": RESEARCH_ARGUMENT, "artifactName": ARTIFACT_NAME,
        "inverse": True, "wireChange": False, "selected": False,
        "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
