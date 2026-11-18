"""Stage only the four source-bound donor APEX candidates for guest entry."""

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import uuid
import xml.etree.ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
OUTPUT = ROOT / "out/guest-apex-active-inputs"
REV = "45abb3df03cbd4a8b006519baaebefdb2c68658a"
UPSTREAM = ROOT / f"firmware/upstream-oneos-0.4.58/{REV}/raw/{REV}"
CANDIDATE = "apex-active-inputs.candidate.xml"

# Fixed original containers, exact payloads and inner manifest extents. CAPEX
# original_apex entries are joined to the separately held decompressed files.
MODULES = {
    "art": {
        "version": 371000140, "line": 3933,
        "held": "016-com.google.android.art_compressed",
        "container": ("com.google.android.art_compressed.apex", 13841002, "cdc914c23e8912e27ec7dfee6b7bde6ccfcd4ae57d8411e570cf5ed7fbc36cfe"),
        "outerManifestBytes": 468,
        "original": (31850496, "5a84faabd4a077baea25a24b2d62b63b1f69466e3e6674ff295ac111cac706c9"),
        "payload": (31633408, "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148"),
        "manifest": (400, "9139699f6df88f10297dfce7dd370e2be70b0fd948826dd8afa29a4b26540516"),
        "ext4": (96, 7660),
    },
    "i18n": {
        "version": 1, "line": 3934,
        "held": "003-com.android.i18n",
        "container": ("com.android.i18n.apex", 21557248, "3112df21cb7dab93e0b2866706502df6f624c96ea0aeb6bb83c83c4a552443c1"),
        "payload": (21409792, "1750220fbfa2af1611a8ed7b1b3526074953b3a863f0e066a3fede2a4ea7d756"),
        "manifest": (151, "b3f750cc2e929d6a665f734411052cce2b035780d2e8539fb0df5d7b681cbf58"),
    },
    "runtime": {
        "version": 1, "line": 3935,
        "held": "005-com.android.runtime",
        "container": ("com.android.runtime.apex", 5435392, "f92cbc75018c8620dff83afc47288aa3391f0cbbb1b6578279cd51156dd257d0"),
        "payload": (5296128, "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379"),
        "manifest": (143, "48e74bbf3dead7386e9a16ba8ff51cd9983c5d5ab6973bb7fb8c445a9653d0d9"),
    },
    "sdkext": {
        "version": 370547060, "line": 3936,
        "held": "036-com.google.android.sdkext_compressed",
        "container": ("com.google.android.sdkext_compressed.apex", 610920, "c83ce550b2b679113343f52a833645c67bc650241b715b9049ac4074c75eccf1"),
        "outerManifestBytes": 133,
        "original": (1384448, "915179f8aa39b48402e14aae1d3e3f044370dc9ca2cfa6505d880e8017b7ca12"),
        "payload": (1212416, "448f4909cc27a33be33ea85d3d950d38d285c2964c930c043eb3827c89ff267f"),
        "manifest": (65, "d4a500fd0f87070dea294bf3ce39dcebfa71aa31f3eb39314859ba11f611fcc9"),
        "ext4": (32, 290),
    },
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def check_directories(path):
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        require(plain(info) and stat.S_ISDIR(info.st_mode), f"Non-plain directory: {component.name}")


def read_helpers():
    path = ROOT / "tools/audit_guest_linkerconfig_apex_inputs.py"
    check_directories(path.parent)
    info = path.lstat()
    require(plain(info) and stat.S_ISREG(info.st_mode) and info.st_size == 12371, "Reader source profile")
    with path.open("rb") as stream:
        raw = stream.read(12372)
    digest = "c5b9f4dcb550d329f4a4b413b6d524c9eec7e7fc4eb48e0321a7f1ea5e081772"
    require(len(raw) == 12371 and hashlib.sha256(raw).hexdigest() == digest, "Reader source pin")
    names = {"require", "record", "relative", "plain_source", "pinned", "ext4_reader", "varint", "fields"}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(nodes) == len(names) and {node.name for node in nodes} == names, "Selected reader definitions")
    scope = {key: globals()[key] for key in ("ROOT", "hashlib", "os", "Path", "stat", "struct", "ast")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope, {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": digest}


def members(raw, wanted):
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.namelist()
        require(len(entries) <= 24 and len(set(entries)) == len(entries), "Selected APEX ZIP entries")
        result = {}
        for name, size in wanted.items():
            entry = archive.getinfo(name)
            require(not entry.is_dir() and entry.file_size == size, "APEX ZIP member extent")
            with archive.open(entry) as stream:
                result[name] = stream.read(size + 1)
            require(len(result[name]) == size, "APEX ZIP member length")
        return result


def selected_metadata(decoded, expected_name, expected_version):
    require(decoded.get(1) == [expected_name.encode("ascii")] and decoded.get(2) == [expected_version],
            "Exact APEX manifest identity")
    version_name = decoded.get(5, [b""])
    shared = decoded.get(11, [0])
    require(len(version_name) == 1 and isinstance(version_name[0], bytes)
            and len(shared) == 1 and shared[0] in (0, 1), "Selected manifest field shape")
    return {"versionName": version_name[0].decode("utf-8"), "provideSharedApexLibs": "true" if shared[0] else "false"}


def module_row(short, profile, helpers, ext4):
    read, fields, record = (helpers[key] for key in ("pinned", "fields", "record"))
    module = f"com.android.{short}"
    source_dir = DONOR / "apex" / profile["held"]
    container, size, digest = profile["container"]
    manifest_size, manifest_digest = profile["manifest"]
    relative_source = f"system/apex/{container}"
    outer, outer_pin = read(DONOR / "extracted" / relative_source, size, digest)
    proof = {"container": outer_pin}
    if "original" in profile:
        wrapped = members(outer, {"original_apex": profile["original"][0], "apex_manifest.pb": profile["outerManifestBytes"]})
        original, proof["originalApex"] = read(source_dir / "original.apex", *profile["original"])
        require(original == wrapped["original_apex"], "CAPEX to held original APEX join")
    else:
        original = outer
    contents = members(original, {"apex_payload.img": profile["payload"][0], "apex_manifest.pb": manifest_size})
    payload, proof["payload"] = read(source_dir / "apex_payload.img", *profile["payload"])
    require(payload == contents["apex_payload.img"], "Original APEX to held payload join")
    if "ext4" in profile:
        inodes, blocks = profile["ext4"]
        fs = ext4(io.BytesIO(payload), len(payload), "7d1522e19dfa5edba43e98e3a4d20250", 0x42, inodes, blocks * 4096)
        embedded, proof["manifest"] = fs.lookup("apex_manifest.pb", 1, 4096)
        require(record(embedded) == {"bytes": manifest_size, "sha256": manifest_digest}, "Embedded manifest pin")
        proof["manifestSource"] = "held ext4 inode"
    else:
        embedded, proof["manifest"] = read(source_dir / "files/apex_manifest.pb", *profile["manifest"])
        proof["manifestSource"] = "held EROFS extraction"
    require(embedded == contents["apex_manifest.pb"], "APEX ZIP manifest and payload manifest join")
    metadata = selected_metadata(fields(embedded), module, profile["version"])
    if "original" in profile:
        require(selected_metadata(fields(wrapped["apex_manifest.pb"]), module, profile["version"]) == metadata,
                "CAPEX selected identity fields")
        proof["capexManifest"] = record(wrapped["apex_manifest.pb"])
    row = {
        "moduleName": module,
        "versionCode": str(profile["version"]),
        **metadata,
        "preinstalledModulePath": "/" + relative_source,
        "preinstalledPartition": "SYSTEM",
        "proposedMountTarget": f"/apex/{module}",
        "payloadSha256": profile["payload"][1],
        "manifestSha256": manifest_digest,
    }
    return row, proof


def candidate_xml(rows):
    root = ET.Element("guest-apex-active-inputs", {"status": "candidate", "profile": "x9u-in-sultra", "schemaVersion": "1"})
    for row in rows:
        ET.SubElement(root, "module-candidate", row)
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def validate_candidate(raw, expected):
    require(0 < len(raw) <= 8192 and b"<!" not in raw, "Candidate XML size or markup")
    root = ET.fromstring(raw)
    require(root.tag == "guest-apex-active-inputs" and all(child.tag == "module-candidate" for child in root),
            "Candidate-only XML format")
    require([child.attrib for child in root] == expected and raw == candidate_xml(expected),
            "Candidate XML differs from exact proven cohort")


def prepare():
    helpers, reader_proof = read_helpers()
    read, record = helpers["pinned"], helpers["record"]
    ext4, ext4_proof = helpers["ext4_reader"]()
    set_bytes, set_proof = read(UPSTREAM / "app-android/packages/x9u-in-sultra.sha256", 4594,
                                "132a0db046d64d5056f8783611829159d0bdc2a822507b256eb4e298fce0790c")
    prep, prep_proof = read(UPSTREAM / "switcher/assets/guest_prepare.sh", 285232,
                            "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d")
    lines = prep.decode().splitlines()
    entries = [line.split() for line in set_bytes.decode().splitlines()]
    rows, evidence = [], {}
    for short, profile in MODULES.items():
        filename = short + "_payload.img"
        matching = [entry for entry in entries if entry and entry[-1] == filename]
        require(matching == [[profile["payload"][1], filename]], "Exact selected OneOS set row")
        require(lines[profile["line"] - 1] == f'mount_payload "{short}" "com.android.{short}"', "Proposed mount target source")
        row, proof = module_row(short, profile, helpers, ext4)
        rows.append(row)
        evidence[row["moduleName"]] = {"legacyMountLine": profile["line"], **proof}
    xml = candidate_xml(rows)
    validate_candidate(xml, rows)
    result = {
        "schema": "guest-apex-active-input-candidate/v1",
        "status": "FOUR_EXACT_DONOR_APEX_CANDIDATES",
        "source": {"set": set_proof, "mountPlacement": prep_proof, "reader": reader_proof, "ext4Reader": ext4_proof},
        "candidates": rows,
        "evidence": evidence,
        "xml": {"name": CANDIDATE, **record(xml)},
        "requiredModuleSetClosed": False,
        "runtimeApexInfoList": None,
        "missingForRuntimeList": ["Complete required module selection", "Actual unversioned/selected mounted names and payload identities",
                                  "Actual active source modulePath and activation/factory classification in the owned guest view"],
        "hostListUsed": False,
        "generatorExecuted": False,
        "candidateFilesWritten": False,
    }
    return result, xml


def stage(result, xml):
    check_directories(OUTPUT.parent)
    OUTPUT.mkdir(exist_ok=True)
    check_directories(OUTPUT)
    run = OUTPUT / ("r-" + uuid.uuid4().hex)
    run.mkdir()
    candidate = run / CANDIDATE
    with candidate.open("xb") as stream:
        stream.write(xml)
    with candidate.open("rb") as stream:
        validate_candidate(stream.read(8193), result["candidates"])
    receipt = run / "receipt.json"
    result["receipt"] = receipt.relative_to(ROOT).as_posix()
    result["candidateFilesWritten"] = True
    with receipt.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="store_true", help="Write candidate-only XML and its receipt into a new private run directory.")
    args = parser.parse_args()
    try:
        result, xml = prepare()
        if args.stage:
            stage(result, xml)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as failure:
        print(f"APEX input staging refused: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
