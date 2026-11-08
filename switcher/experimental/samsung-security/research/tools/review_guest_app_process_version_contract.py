"""Compare file-declared ELF symbol versions across the pinned donor candidate graph."""

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from check_guest_tree_runtime_apex import held_reader
from guest_elf_version_contract import read_version_contract
from review_guest_app_process_dependency_graph import (
    ART_ROOT, Catalog, DONOR, FILE_LIMIT, STATSD_PAYLOAD, STATSD_ROOT, STATSD_SHA256,
    add_carrier_file, pinned_receipt, stable_file,
)
from review_guest_carrier_linker_inputs import CarrierView, Erofs, PLAN_SHA, READBACK, ROOT, load_plan, require, source
from review_guest_exec_mount_demand import ELF_READER, FRONTIER


GRAPH = "out/guest-app-process-dependency-graph/r-edbed514/receipt.json"
GRAPH_SHA256 = "689cff7eeccd603a7c1930589aa40a2e1b20fcb4703d56bc83ead3b50645c985"
BIONIC = "https://android.googlesource.com/platform/bionic/+/refs/tags/android-16.0.0_r1/linker/"


def apex_images(ext4, frontier):
    art = frontier["selectedArtPayload"]
    art_path = DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img"
    inputs = (
        (ART_ROOT, art_path, art["bytes"], art["sha256"], 96, 7660),
        (STATSD_ROOT, STATSD_PAYLOAD, 3444736, STATSD_SHA256, 48, 831),
    )
    result = {}
    for role, path, size, digest, inodes, blocks in inputs:
        payload = source.read_small(path, size, digest)
        fs = ext4(BytesIO(payload), len(payload), "7d1522e19dfa5edba43e98e3a4d20250", 0x42, inodes, blocks * 4096)
        result[role] = fs, digest
    return result


def object_bytes(catalog, view, images, path, item):
    pin = item["source"]
    kind = pin["kind"]
    if kind == "sealedCarrier":
        require(pin["path"] == path, f"Carrier role differs: {path}")
        add_carrier_file(catalog, view, path, None)
        read, evidence = catalog.files[path]
        raw = read()
        require(evidence["inode"] == pin["inode"], f"Carrier inode differs: {path}")
        return raw
    if kind == "rawApexExt4":
        parts = PurePosixPath(path).parts
        role = f"/apex/{parts[2]}"
        member = "/".join(parts[3:])
        fs, digest = images[role]
        require(member == pin["member"] and digest == pin["payloadSha256"], f"Raw APEX role differs: {path}")
        return fs.lookup(member, 1, item["bytes"])[0]
    require(kind in ("savedApexExtraction", "pinnedRuntimeInterpreter"), f"Unknown source kind: {path}")
    relative = PurePosixPath(pin["path"])
    require(not relative.is_absolute() and relative.parts[0] == "apex" and ".." not in relative.parts,
            f"Saved APEX path escaped: {path}")
    file = source.plain(DONOR.joinpath(*relative.parts))
    return stable_file(file, source.identity(file.lstat()))


def read_contracts(graph):
    previous, frontier = (pinned_receipt(pin) for pin in (READBACK, FRONTIER))
    ext4, _ = held_reader(source.read_small(ROOT / ELF_READER[0], 32768, ELF_READER[1]))
    images = apex_images(ext4, frontier)
    image = previous["image"]
    require(image["sha256"] == graph["inputs"]["carrierSha256"] and previous["planSha256"] == PLAN_SHA,
            "Pinned graph carrier differs")
    carrier = ROOT / image["path"]
    require(carrier.is_relative_to(ROOT / "out") and source.plain(carrier) == carrier, "Unsafe carrier path")
    named = source.identity(carrier.lstat())
    require(list(named) == image["identity"], "Named carrier differs")
    plan, _, _ = load_plan()
    backing = previous["expectedCoreApexFiles"]
    catalog = Catalog(None)
    objects = graph["expanded"]["objects"]
    require(len(objects) == graph["parsedUniqueObjects"] == 287
            and sum(row["bytes"] for row in objects.values()) == graph["parsedBytes"] == 112458432,
            "Pinned graph extent changed")
    contracts = {}
    with carrier.open("rb") as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        require(opened[:4] == named[:4], "Opened carrier differs")
        reader = Erofs(stream, image["bytes"], len(plan) + len(backing) + 1)
        require(reader.geometry == previous["geometry"], "Carrier geometry changed")
        view = CarrierView(reader, plan, backing)
        for path, item in objects.items():
            require(64 <= item["bytes"] <= FILE_LIMIT, f"Graph object size outside bound: {path}")
            raw = object_bytes(catalog, view, images, path, item)
            require(len(raw) == item["bytes"] and sha256(raw).hexdigest() == item["sha256"],
                    f"Pinned object changed: {path}")
            try:
                contracts[path] = read_version_contract(raw)
            except ValueError as error:
                raise ValueError(f"Version metadata refused for {path}: {error}") from error
        reader.check_geometry()
        require(source.identity(os.fstat(stream.fileno())) == opened and source.identity(carrier.lstat()) == named,
                "Carrier changed during version readback")
    return contracts


def candidate_match(requirements, soname, owner, contract):
    counts = Counter()
    missing_strong, missing_weak = [], []
    for symbol, version, weak in requirements:
        if (symbol, version) in contract["exports"]:
            counts["exactVersion"] += 1
        elif version not in contract["versions"] and symbol in contract["unversioned_exports"]:
            counts["unversionedFallbackCandidate"] += 1
        else:
            (missing_weak if weak else missing_strong).append({"symbol": symbol, "version": version})
    return {
        "declaredSonameMatches": soname == owner,
        "exactVersion": counts["exactVersion"],
        "unversionedFallbackCandidate": counts["unversionedFallbackCandidate"],
        "missingStrong": missing_strong,
        "missingWeak": missing_weak,
    }


def export_profiles(objects, paths, contracts):
    result = {}
    for path in paths:
        contract = contracts[path]
        exports = sorted(contract["exports"])
        plain = sorted(contract["unversioned_exports"])
        canonical = json.dumps([exports, plain], separators=(",", ":")).encode("ascii")
        result[path] = {
            "objectSha256": objects[path]["sha256"],
            "exportSetSha256": sha256(canonical).hexdigest(),
            "hasVersym": contract["has_versym"],
            "versionedExports": len(exports),
            "unversionedExports": len(plain),
        }
    return result


def compare(graph, contracts):
    expanded = graph["expanded"]
    objects, edges = expanded["objects"], expanded["edges"]
    ambiguous = expanded["ambiguous"]
    summaries = {name: Counter() for name in ambiguous}
    outcomes = Counter()
    rows, outside = [], []
    for consumer, contract in sorted(contracts.items()):
        by_name = {edge["needed"]: edge["candidates"] for edge in edges[consumer]}
        outcomes["unversionedUndefinedSymbols"] += contract["unversioned_undefined"]
        for owner, requirements in sorted(contract["requirements"].items()):
            if not requirements:
                continue
            outcomes["versionedUndefinedSymbols"] += len(requirements)
            outcomes["consumerOwnerGroups"] += 1
            if owner not in by_name:
                outside.append({"consumer": consumer, "declaredOwner": owner, "symbols": len(requirements)})
                continue
            matches = {
                path: candidate_match(requirements, objects[path]["soname"], owner, contracts[path])
                for path in by_name[owner]
            }
            outcomes["candidateComparisons"] += len(matches)
            outcomes["candidateSonameMismatches"] += sum(not row["declaredSonameMatches"] for row in matches.values())
            outcomes["candidateStrongMisses"] += sum(bool(row["missingStrong"]) for row in matches.values())
            outcomes["candidateWeakMisses"] += sum(bool(row["missingWeak"]) for row in matches.values())
            outcomes["unversionedFallbackMatches"] += sum(row["unversionedFallbackCandidate"] for row in matches.values())
            if owner in ambiguous:
                covered = [path for path, row in matches.items()
                           if row["declaredSonameMatches"] and not row["missingStrong"]]
                summary = summaries[owner]
                summary["consumerGroups"] += 1
                summary["versionedSymbols"] += len(requirements)
                summary["groupsWithDifferentStrongCoverage"] += 0 < len(covered) < len(matches)
                summary["groupsWithNoCandidateCoverage"] += not covered
            if owner in ambiguous or any(not row["declaredSonameMatches"] or row["missingStrong"] or row["missingWeak"]
                                         or row["unversionedFallbackCandidate"] for row in matches.values()):
                rows.append({"consumer": consumer, "declaredOwner": owner, "symbols": len(requirements),
                             "candidates": matches})
    return {
        "summary": dict(sorted(outcomes.items())),
        "ambiguousNames": {
            name: {**summary, "exportProfiles": export_profiles(objects, ambiguous[name], contracts)}
            for name, summary in summaries.items()
        },
        "requirementsOutsideDeclaredEdges": outside,
        "candidateEvidence": rows,
    }


def derive():
    graph = json.loads(source.read_small(ROOT / GRAPH, 2 * 1024**2, GRAPH_SHA256))
    require(graph["status"] == "VERIFIED_BOUNDED_STATIC_CANDIDATE_GRAPH" and not graph["targetExecuted"],
            "Unexpected candidate graph receipt")
    for name in ("review_guest_app_process_dependency_graph.py", "guest_elf_candidate.py", "guest_elf_dependency_graph.py"):
        source.read_small(ROOT / "tools" / name, 128 * 1024, graph["toolSha256"][name])
    contracts = read_contracts(graph)
    findings = compare(graph, contracts)
    return {
        "schema": "oneos-app-process-declared-version-candidates/v1",
        "status": "VERIFIED_PINNED_DECLARED_SYMBOL_VERSION_CANDIDATES",
        "graphSha256": GRAPH_SHA256,
        "objectsRead": len(contracts),
        "bytesRead": graph["parsedBytes"],
        "toolSha256": {
            name: sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
            for name in (Path(__file__).name, "guest_elf_version_contract.py")
        },
        "referenceOnly": [BIONIC + "linker.cpp", BIONIC + "linker_soinfo.cpp"],
        "result": findings,
        "effectiveNamespaceSelected": False,
        "relocationsVerified": False,
        "targetExecuted": False,
        "deviceAction": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    result = derive()
    payload = json.dumps(result, indent=2) + "\n"
    if not args.record:
        print(payload, end="")
        return
    run = ROOT / "out/guest-app-process-version-contract" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / "receipt.json").write_text(payload, encoding="utf-8")
    print(run)
    print(result["objectsRead"], "objects", result["result"]["summary"])


if __name__ == "__main__":
    main()
