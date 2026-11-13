"""Check the held Find X9 Ultra IN Full linkerconfig inputs as data only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
EXTRACTED = DONOR / "extracted"
RUNTIME = DONOR / "apex/005-com.android.runtime"
OUTPUT = ROOT / "out/guest-linkerconfig-inputs"

# Literal profile from the prior readback plus the selected generator inputs.
INPUTS = {
    "entrySourceProof": (ROOT / "inventory/guest-entry-linker-proc.json", 8492, "5b8a49fb0dd6ac987d3ec91d8990b16241bd7ae32d1f56bc895661c0673296b0"),
    "runtimeApexInventory": (ROOT / "inventory/guest-runtime-apex.json", 1889, "2262552b5c68039513e726b5eb6283cb2cd79731f2b81baa8c6c384b94a6229d"),
    "runtimeApexReadback": (ROOT / "out/guest-runtime-apex/actual-source-check.json", 17079, "ec8d59bdc9453c08bb26b9b144f270338869d76386f0c5e5b63bdb698f13e705"),
    "donorInitRc": (EXTRACTED / "system/etc/init/hw/init.rc", 117704, "d14ca8301c0795a6fe10425a3d20bf8fbf628b0aeed4b7b6f560fd061e78dcd1"),
    "appProcess64": (EXTRACTED / "system/bin/app_process64", 51880, "78d3bf52333a151a6f4859f5144de5578adf009503b792a91db307435a0f21dc"),
    "runtimePayload": (RUNTIME / "apex_payload.img", 5296128, "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379"),
    "artPayload": (DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img", 31633408, "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148"),
    "runtimeLinker": (RUNTIME / "files/bin/linker64", 2640432, "97f31018817926c4997b77bd7f91372ecbe8345976cc2019d4168b00586430c8"),
    "runtimeGenerator": (RUNTIME / "files/bin/linkerconfig", 496480, "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb"),
    "runtimeApexManifest": (RUNTIME / "files/apex_manifest.pb", 143, "48e74bbf3dead7386e9a16ba8ff51cd9983c5d5ab6973bb7fb8c445a9653d0d9"),
    "runtimeApexConfig": (RUNTIME / "files/etc/linker.config.pb", 2, "27c24fcb8474773e2af799d0848495ff053272d33c432dc26277993df45c9276"),
    "systemConfig": (EXTRACTED / "system/etc/linker.config.pb", 1207, "f9782b93cc1e7bd9989fd145380850ff2df5196cb1a314b6a8a41fe78eec076c"),
    "productConfig": (EXTRACTED / "system/product/etc/linker.config.pb", 0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "systemPublicLibraries": (EXTRACTED / "system/etc/public.libraries.txt", 549, "63522af72a927a5edb7df539f0f3643f44a91fa11b64cac977796b8ee50bd96f"),
    "oplusExtensionConfig": (EXTRACTED / "system/system_ext/oplusex/ld.config.oplus.txt", 711, "817fe85345361028894cdbb6c0c41e0ccdae0fd450b8bdca51f66a4f5e1004ca"),
}


def relative(path):
    return Path(os.path.relpath(path, ROOT)).as_posix()


def checked_stat(path, type_check):
    info = path.lstat()
    if not type_check(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Unexpected local path type: {relative(path)}")
    return info


def checked_parents(path):
    for parent in reversed(path.parents):
        checked_stat(parent, stat.S_ISDIR)


def file_identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_pin(path, size, expected_digest):
    checked_parents(path)
    before = checked_stat(path, stat.S_ISREG)
    if before.st_size != size:
        raise ValueError(f"Held input length differs: {relative(path)}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or file_identity(opened) != file_identity(before):
            raise ValueError(f"Held input identity differs: {relative(path)}")
        data = stream.read(size + 1)
        finished = os.fstat(stream.fileno())
    after = checked_stat(path, stat.S_ISREG)
    if (file_identity(finished) != file_identity(opened) or file_identity(after) != file_identity(before)
            or finished.st_ctime_ns != opened.st_ctime_ns or after.st_ctime_ns != before.st_ctime_ns):
        raise ValueError(f"Held input changed: {relative(path)}")
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != size or digest != expected_digest:
        raise ValueError(f"Held input bytes differ: {relative(path)}")
    return {"path": relative(path), "bytes": size, "sha256": digest}


def observe_directory(path, known):
    checked_parents(path)
    before = checked_stat(path, stat.S_ISDIR)
    matches = []
    count = 0
    with os.scandir(path) as entries:
        for entry in entries:
            count += 1
            if count > 4096:
                raise ValueError(f"Directory entry bound exceeded: {relative(path)}")
            if entry.name in known:
                matches.append(entry.name)
    after = checked_stat(path, stat.S_ISDIR)
    if file_identity(before) != file_identity(after) or before.st_ctime_ns != after.st_ctime_ns:
        raise ValueError(f"Observed directory changed: {relative(path)}")
    return {"path": relative(path), "entries": count, "knownNamesPresent": sorted(matches)}


def check_inputs():
    held = {label: read_pin(*source) for label, source in INPUTS.items()}
    linker = observe_directory(EXTRACTED / "linkerconfig", {"ld.config.txt", "apex.libraries.config.txt"})
    apex = observe_directory(EXTRACTED / "apex", {"apex-info-list.xml"})
    static = observe_directory(EXTRACTED / "system/etc", {
        "ld.config.txt", "ld.config.arm64.txt", "ld.config.arm64-v8a.txt", "ld.config.vndk_lite.txt",
    })
    return {
        "schema": "guest-linkerconfig-input-check/v1",
        "status": "BLOCKED_NO_ADMITTED_EFFECTIVE_LINKERCONFIG",
        "profile": "Find X9 Ultra IN Full / x9u-in-sultra / app_process64",
        "verifiedHeldInputs": held,
        "cachePathObservations": {"generatedConfig": linker, "activeApex": apex, "systemFallbacks": static},
        "generatedConfigCandidateObserved": "ld.config.txt" in linker["knownNamesPresent"],
        "entryExecutable": "/system/bin/app_process64",
        "interpreterTarget": "/apex/com.android.runtime/bin/linker64",
        "missingAdmissionEvidence": [
            "Exact effective generated config and any companion files read by the selected entry cohort",
            "Selected guest partition, active APEX/alias and property view used to produce those bytes",
            "Reviewable exact producer source/build and invocation or a matching genuine captured output provenance",
            "Resolution and ownership proof tying the output to the held executable and interpreter in the same selected view",
        ],
        "outputManifest": None,
        "launchAdmitted": False,
        "generatorExecuted": False,
    }


def save_receipt(result):
    checked_parents(OUTPUT)
    OUTPUT.mkdir(exist_ok=True)
    checked_stat(OUTPUT, stat.S_ISDIR)
    run = OUTPUT / ("r-" + uuid.uuid4().hex)
    run.mkdir()
    path = run / "receipt.json"
    result["receipt"] = relative(path)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true", help="Keep this refusal receipt under the project out directory.")
    args = parser.parse_args()
    try:
        result = check_inputs()
        if args.record:
            save_receipt(result)
    except (OSError, ValueError) as failure:
        print(f"Linkerconfig input check failed: {failure}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
