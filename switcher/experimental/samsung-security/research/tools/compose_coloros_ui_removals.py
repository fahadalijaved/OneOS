"""Compose frozen, disjoint ColorOS code leaves as an UNSELECTED PC archive.

Every component must use the same immutable base. Only method instruction bytes
and DEX039 integrity fields may change. This produces no installable/signed APK,
runtime admission, authentication result or permission to modify a phone.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
UTILITY = ROOT / "tools/build_coloros_pin_metadata_leaf.py"
UTILITY_SHA = "9ff4731807dad9df99ba8468b17611bf21b03fd17d2db917d4ba204f67fab8a7"
PROFILES = {
    "systemui": {
        "source": "firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk",
        "sourceSha256": "0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77",
        "classes": 73080,
        "components": [
            ("inventory/coloros-rpmb-input-leaf.json", "be647c695c04f996559d6274e303f03e9d22c820e9df365886053d4ff8eeffe3"),
            ("inventory/coloros-ror-leaf.json", "fde8d3f9d1cf982d0d487b9de124aeeafe7ee7108e76fc32651b5627ec20ff65"),
        ],
    },
    "framework": {
        "source": "firmware/donor/extracted/system/framework/framework.jar",
        "sourceSha256": "d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2",
        "classes": 38870,
        "components": [
            ("inventory/coloros-pin-metadata-leaf.json", "a817eadc3fa41cd2e8fbf5b2ac1d704007d799a16be1b47b2f0e3554616b3517"),
            ("inventory/coloros-readiness.json", "0d8ce1db77e58fc7ef5853643c368eaf45db6c301c628869ea639662004b1472"),
        ],
    },
    "settings": {
        "source": "firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk",
        "sourceSha256": "33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b",
        "classes": 78960,
        # The admitted original resources.arsc is 123,768,068 bytes. Existing
        # framework/SystemUI profiles retain their smaller default entry bound.
        "maxEntryBytes": 128 * 1024 * 1024,
        "components": [
            ("inventory/coloros-settings-rpmb-leaf.json", "8d5e0dba53221b6c5720a4bac7e3c7f062ba8a0a148d3835176ffcfc84f9375e"),
            ("inventory/coloros-retrieval-capability-leaf.json", "749bb14c7a863df6d79bc830a44cb48dba3ceead6811a8abe8ce51c0ab68006b"),
        ],
    },
}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utility():
    if digest(UTILITY) != UTILITY_SHA:
        raise ValueError("Frozen DEX utility differs")
    spec = importlib.util.spec_from_file_location("frozen_pin_metadata_utility", UTILITY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_archive(path, max_entry_bytes=64 * 1024 * 1024):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)) or len(names) > 20000:
            raise ValueError("Duplicate or excessive archive entries")
        if sum(item.file_size for item in infos) > 512 * 1024 * 1024:
            raise ValueError("Expanded archive exceeds explicit bound")
        if any(item.file_size > max_entry_bytes for item in infos):
            raise ValueError("Expanded entry exceeds explicit bound")
        return infos, {item.filename: archive.read(item) for item in infos}


def method_ranges(raw, dex):
    """Index actual encoded code items; do not execute or load an OEM class."""
    dex.header(raw)
    result = []
    methods = dex.u32(raw, 92)
    classes = dex.u32(raw, 100)
    for class_index in range(dex.u32(raw, 96)):
        row = classes + 32 * class_index
        owner = dex.u32(raw, row)
        cursor = dex.u32(raw, row + 24)
        if not cursor:
            continue
        counts = []
        for _ in range(4):
            count, cursor = dex.uleb(raw, cursor)
            counts.append(count)
        if sum(counts) > 2000000:
            raise ValueError("Encoded-member bound")
        for count in counts[:2]:
            index = 0
            for _ in range(count):
                delta, cursor = dex.uleb(raw, cursor)
                index += delta
                _, cursor = dex.uleb(raw, cursor)
                if index >= dex.u32(raw, 80):
                    raise ValueError("Encoded-field index")
        for count in counts[2:]:
            index = 0
            for _ in range(count):
                delta, cursor = dex.uleb(raw, cursor)
                index += delta
                _, cursor = dex.uleb(raw, cursor)
                code, cursor = dex.uleb(raw, cursor)
                if index >= dex.u32(raw, 88) or dex.u16(raw, methods + 8 * index) != owner:
                    raise ValueError("Encoded-method identity")
                if not code:
                    continue
                if code % 4 or code < 112 or code + 16 > len(raw):
                    raise ValueError("Code-item bounds/alignment")
                start = code + 16
                end = start + 2 * dex.u32(raw, code + 12)
                if end > len(raw):
                    raise ValueError("Instruction extent")
                result.append((index, start, end))
    return result


def delta_spans(original, patched):
    if len(original) != len(patched):
        raise ValueError("Component changed a DEX extent")
    spans = []
    start = None
    for offset, (before, after) in enumerate(zip(original, patched)):
        changed = before != after and not 8 <= offset < 32
        if changed and start is None:
            start = offset
        elif not changed and start is not None:
            spans.append((start, offset))
            start = None
    if start is not None:
        spans.append((start, len(original)))
    return spans


def instruction_owner(ranges, start, end):
    # Full containment by one method is insufficient if another method overlaps
    # only part of the span. Reject every alias touching the edited bytes.
    owners = [item for item in ranges if max(start, item[1]) < min(end, item[2])]
    if len(owners) != 1 or not owners[0][1] <= start < end <= owners[0][2]:
        raise ValueError("Changed bytes do not have one non-aliased method owner")
    return owners[0][0]


def component_conditions(receipt, source_sha, allow_legacy_cold_restriction=False):
    if receipt["sourceArchiveSha256"] != source_sha or receipt["selected"] is not False:
        raise ValueError("Component is not an unselected leaf of this base")
    if receipt.get("coldStartOnly") is not True and not allow_legacy_cold_restriction:
        raise ValueError("Explicit cold-only scope required for new components")
    required = receipt["requiredSelectionConditions"]
    if not isinstance(required, list) or not required or any(not isinstance(item, str) or not item for item in required):
        raise ValueError("Explicit component selection conditions required")
    return required


def admitted_component_conditions(name, expected_sha, receipt, source_sha):
    """Normalize only the two individually pinned historical receipt schemas.

    The caller must verify the receipt bytes against expected_sha first. These
    exact legacy leaves acquire the parent's cold-process restriction; no other
    receipt may omit the cold flag or rename its condition field.
    """
    legacy_metadata = (name, expected_sha) == (
        "inventory/coloros-pin-metadata-leaf.json",
        "a817eadc3fa41cd2e8fbf5b2ac1d704007d799a16be1b47b2f0e3554616b3517")
    legacy_settings = (name, expected_sha) == (
        "inventory/coloros-settings-rpmb-leaf.json",
        "8d5e0dba53221b6c5720a4bac7e3c7f062ba8a0a148d3835176ffcfc84f9375e")
    if legacy_settings:
        if "requiredSelectionConditions" in receipt:
            raise ValueError("Frozen Settings receipt has an unexpected condition alias")
        normalized = dict(receipt)
        normalized["requiredSelectionConditions"] = receipt["selectionConditions"]
        return component_conditions(normalized, source_sha, True)
    return component_conditions(receipt, source_sha, legacy_metadata)


def local_artifact(path, out_root):
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_relative_to(out_root):
        raise ValueError("Component artifact escapes the admitted output root")
    return resolved


def combine_dex(original, components, dex):
    """Reject shared method ownership, aliases and edits outside instructions."""
    dex.header(original)
    ranges = method_ranges(original, dex)
    composed = bytearray(original)
    claimed = {}
    edits = []
    for label, patched in components:
        dex.header(patched)
        owned = set()
        for start, end in delta_spans(original, patched):
            method = instruction_owner(ranges, start, end)
            if method in claimed and claimed[method] != label:
                raise ValueError("Components modify the same encoded method")
            claimed[method] = label
            owned.add(method)
            composed[start:end] = patched[start:end]
            edits.append({"component": label, "methodId": method, "firstByte": start, "endExclusiveByte": end})
        if patched != original and not owned:
            raise ValueError("Integrity-only component is not a code leaf")
    output = dex.seal(composed)
    dex.header(output)
    inverse = bytearray(output)
    for edit in edits:
        a, b = edit["firstByte"], edit["endExclusiveByte"]
        inverse[a:b] = original[a:b]
    if dex.seal(inverse) != original:
        raise ValueError("Composition inverse differs from original DEX")
    roundtrip = bytearray(original)
    for edit in edits:
        a, b = edit["firstByte"], edit["endExclusiveByte"]
        roundtrip[a:b] = output[a:b]
    if dex.seal(roundtrip) != output:
        raise ValueError("Composition roundtrip differs")
    return output, edits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    if not profile["components"]:
        raise ValueError("Component receipts are not yet frozen for this profile")
    dex = utility()
    project_root = ROOT.resolve(strict=True)
    out_root = (ROOT / "out").resolve(strict=True)
    if not out_root.is_relative_to(project_root):
        raise ValueError("Output root escapes the repository")
    source = PARENT / profile["source"]
    if digest(source) != profile["sourceSha256"]:
        raise ValueError("Immutable source archive differs")
    max_entry_bytes = profile.get("maxEntryBytes", 64 * 1024 * 1024)
    infos, originals = load_archive(source, max_entry_bytes)
    components = []
    conditions = ["Apply only to a fresh cold process before original service, callback or authentication initialization; no hot replacement or live drain is proved"]
    pins = []
    for name, expected_sha in profile["components"]:
        receipt_path = ROOT / name
        if digest(receipt_path) != expected_sha:
            raise ValueError("Unreviewed component receipt: " + name)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        required = admitted_component_conditions(name, expected_sha, receipt, profile["sourceSha256"])
        conditions.extend(required)
        artifact = Path(receipt["patchedArchive"])
        artifact = local_artifact(artifact if artifact.is_absolute() else ROOT / artifact, out_root)
        if digest(artifact) != receipt["patchedArchiveSha256"]:
            raise ValueError("Exact repo-local component artifact required")
        child_infos, child = load_archive(artifact, max_entry_bytes)
        if [item.filename for item in child_infos] != [item.filename for item in infos]:
            raise ValueError("Component entry list/order differs")
        for entry, original in originals.items():
            if not re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", entry) and child[entry] != original:
                raise ValueError("Component changed a non-DEX payload")
        components.append((name, child))
        pins.append({"receipt": name, "receiptSha256": expected_sha, "artifact": artifact.relative_to(ROOT).as_posix(),
                     "artifactSha256": receipt["patchedArchiveSha256"]})
    output = dict(originals)
    edits = []
    class_count = 0
    for entry, original in originals.items():
        if not re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", entry):
            continue
        class_count += dex.header(original)["classes"]
        children = [(label, child[entry]) for label, child in components if child[entry] != original]
        if children:
            output[entry], changes = combine_dex(original, children, dex)
            edits.extend({"dex": entry, **change} for change in changes)
        if dex.header(output[entry])["classes"] != dex.header(original)["classes"]:
            raise ValueError("Class-definition count changed")
    if class_count != profile["classes"] or not edits:
        raise ValueError("Exact original class scope and actual edits required")
    destination = ROOT / "out/coloros-ui-removal-composition" / args.profile
    if not destination.resolve().is_relative_to(out_root):
        raise ValueError("Composition output escapes the admitted output root")
    destination.mkdir(parents=True, exist_ok=True)
    wrapper = destination / (args.profile + ".unselected-code.zip")
    if not wrapper.resolve().is_relative_to(out_root):
        raise ValueError("Composition wrapper escapes the admitted output root")
    with zipfile.ZipFile(wrapper, "w") as archive:
        for info in infos:
            archive.writestr(info, output[info.filename])
    _, reloaded = load_archive(wrapper, max_entry_bytes)
    if reloaded != output or digest(source) != profile["sourceSha256"] or digest(UTILITY) != UTILITY_SHA:
        raise ValueError("Final payload/source/utility readback differs")
    for pin in pins:
        if digest(ROOT / pin["receipt"]) != pin["receiptSha256"] or digest(ROOT / pin["artifact"]) != pin["artifactSha256"]:
            raise ValueError("Component changed during composition")
    report = {
        "schema": "coloros-removal-composition/v1", "profile": args.profile,
        "status": "UNSELECTED_PC_ONLY_COLD_CODE_COMPOSITION", "sourceArchive": profile["source"],
        "sourceArchiveSha256": profile["sourceSha256"], "components": pins,
        "output": wrapper.relative_to(ROOT).as_posix(), "outputSha256": digest(wrapper),
        "originalClassCount": class_count, "changedInstructionByteSpans": edits,
        "requiredSelectionConditions": sorted(set(conditions)), "coldStartOnly": True, "selected": False,
        "checks": {"sameImmutableBase": True, "noSharedMethodAcrossComponents": True,
                   "codeOnlyAndIntegrityChanges": True, "inverseAndRoundtrip": True,
                   "allPayloadsReadBack": True, "originalClassCountPreserved": True},
        "limits": ["Component source/semantic proofs remain required; composition is not an independent behavior proof",
                   "ZIP entry payloads are checked, not physical ZIP encoding; platform APK/JAR signatures are not preserved",
                   "Cold-only conditions do not prove live callback drain, authority readiness or any device security behavior"],
        "oemCodeExecuted": False, "phoneChanged": False, "producerSha256": digest(Path(__file__)),
        "utilitySha256": UTILITY_SHA,
    }
    (destination / "receipt.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    (ROOT / ("inventory/coloros-ui-removal-composition-" + args.profile + ".json")).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"profile": args.profile, "output": report["output"], "sha256": report["outputSha256"],
                      "changedByteSpans": len(edits), "classes": class_count, "selected": False}))


if __name__ == "__main__":
    main()
