"""Verify the saved research tester, host and profile without launching them."""

import argparse
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from check_guest_tree_materialization_plan import read_small
from check_retained_view_host_pair import signature_v3
from compose_exec_carrier_prepare_tester import RESEARCH, RESEARCH_SHA, verified_controller
from compose_guest_zygote_slot_release import ROOT
from file_stage_stop_status_cohort import _signature_log


PRIOR_APK_RECEIPTS = {
    "tester": (
        "out/file-stage-stop-cleanup-package/tester/r-f76885ea/receipt.json",
        "098b82eb9149917d487bea1f589da65acfd263a98706308694cfbb6d0b854c21",
    ),
    "host": (
        "out/file-stage-stop-cleanup-host-6c82d16a/r-ef8278ee/receipt.json",
        "1fa821e06db1c2f946f7ac6bdbfdbede5b4f4d9f1ae67c5c3fa31f914d7ff069",
    ),
}


def saved(path, digest, maximum):
    relative = Path(path)
    if not relative.parts or relative.parts[0] != "out" or ".." in relative.parts:
        raise ValueError("Expected repository-local output path")
    return read_small(ROOT / relative, maximum, digest)


def receipt(path, digest):
    row = json.loads(saved(path, digest, 512 * 1024))
    if row.get("selected") is not False or row.get("deviceEligible") is not False:
        raise ValueError("Expected a PC-only receipt")
    return row


def artifact(row, maximum=2 * 1024 * 1024):
    raw = saved(row["path"], row["sha256"], maximum)
    if len(raw) != row["bytes"]:
        raise ValueError("Artifact extent differs from receipt")
    return raw


def verify_package(role, path, digest, controller):
    current = receipt(path, digest)
    if current["schema"] != f"oneos-exec-carrier-prepare-{role}-package/v1":
        raise ValueError(f"Expected research {role} package receipt")
    prior = receipt(*PRIOR_APK_RECEIPTS[role])["package"]
    package = current["package"]
    for key in ("package", "versionCode", "versionName", "minSdk", "targetSdk"):
        if package[key] != prior[key]:
            raise ValueError(f"{role} package metadata changed: {key}")
    compile_pin = current["compileProof"]
    compiled = receipt(compile_pin["path"], compile_pin["sha256"])
    build_native = compiled["controller"]
    if any(build_native[key] != controller[key] for key in ("sha256", "bytes")):
        raise ValueError(f"{role} compiler receipt points to a different controller")
    built_dex = artifact(compiled["app" if role == "tester" else "host"]["dex"])
    if built_dex != artifact(package["dex"]):
        raise ValueError(f"{role} packaged DEX pin differs from the saved compiler output")
    raw = artifact(package["apk"])
    predecessor_raw = artifact(prior["apk"])
    with ZipFile(BytesIO(raw)) as apk, ZipFile(BytesIO(predecessor_raw)) as old:
        names = apk.namelist()
        if names != old.namelist() or len(set(names)) != len(names):
            raise ValueError(f"{role} APK members changed")
        for name in names:
            member = apk.getinfo(name)
            expected = built_dex if name == "classes.dex" else old.read(name)
            if member.file_size != len(expected) or apk.read(member) != expected:
                raise ValueError(f"{role} APK member mismatch: {name}")

    signer = signature_v3(raw)
    old_signer = signature_v3(predecessor_raw)
    if signer["certificateSha256"] != package["publicCertificate"]["sha256"]:
        raise ValueError(f"{role} signer certificate differs from its receipt")
    artifact(package["publicCertificate"], 16 * 1024)
    for scheme in (2, 3):
        output = artifact(current["signatureReadback"][f"v{scheme}"], 16 * 1024)
        _signature_log(output, scheme, signer)
    return package, signer, old_signer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ("tester", "host", "profile"):
        parser.add_argument(f"--{role}", required=True, nargs=2, metavar=("PATH", "SHA256"))
    args = parser.parse_args()
    controller, stage, entry, _ = verified_controller()
    tester, tester_signer, old_tester_signer = verify_package("tester", *args.tester, controller)
    host, host_signer, old_host_signer = verify_package("host", *args.host, controller)
    signers = tester_signer, host_signer, old_tester_signer, old_host_signer
    if any(len({signer[key] for signer in signers}) != 4
           for key in ("certificateSha256", "publicKeySha256")):
        raise ValueError("Expected four independent lab signing identities")
    profile_receipt = receipt(*args.profile)
    if profile_receipt["status"] != "PASS_UNSELECTED_RESEARCH_PROFILE_PURE_PARSER_ONLY":
        raise ValueError("Expected research profile parser receipt")
    tester_proof = profile_receipt["testerProof"]
    controller_proof = profile_receipt["controllerProof"]
    if ((tester_proof["path"], tester_proof["sha256"]) != tuple(args.tester)
            or controller_proof["path"] != (RESEARCH / "receipt.json").relative_to(ROOT).as_posix()
            or controller_proof["sha256"] != RESEARCH_SHA):
        raise ValueError("Profile parser receipt points to a different pair")
    profile = profile_receipt["profile"]["payload"]
    expected = (
        f"version=2\npackage={tester['package']}\nsigner={tester_signer['certificateSha256']}\n"
        f"apk={tester['apk']['sha256']}\ncode={tester['versionCode']}\n"
        f"native={controller['sha256']}\nbytes={controller['bytes']}\n"
    ).encode("ascii")
    if artifact(profile, 4096) != expected:
        raise ValueError("Profile differs from the exact saved tester and controller")
    run = ROOT / "out/exec-carrier-prepare-pair" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    result = {
        "schema": 1, "status": "PASS_RESEARCH_PREPARATION_PAIR_PC_ONLY",
        "controller": controller, "stagePath": stage, "entryArgument": entry,
        "testerApk": tester["apk"], "hostApk": host["apk"], "profile": profile,
        "proofs": {role: dict(zip(("path", "sha256"), getattr(args, role)))
                   for role in ("tester", "host", "profile")},
        "selected": False, "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
