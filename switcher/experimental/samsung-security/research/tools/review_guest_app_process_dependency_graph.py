"""Read the bounded app_process64 DT_NEEDED candidate graph from held donor data."""

from collections import defaultdict
from hashlib import sha256
from io import BytesIO
import argparse
import json
import os
from pathlib import Path
import stat
from uuid import uuid4

from audit_guest_linkerconfig_apex_inputs import manifest as apex_manifest
from check_guest_tree_runtime_apex import held_reader
from guest_elf_candidate import parse_elf_candidate
from guest_elf_dependency_graph import walk_graph
from review_guest_carrier_linker_inputs import CarrierView, Erofs, PLAN_SHA, READBACK, ROOT, load_plan, require, source
from review_guest_exec_mount_demand import ELF_READER, FRONTIER


DONOR = ROOT.parent / "firmware/donor"
APP = "/system/bin/app_process64"
INTERPRETER = "/apex/com.android.runtime/bin/linker64"
ART_ROOT = "/apex/com.android.art"
STATSD_ROOT = "/apex/com.android.os.statsd"
STATSD_PAYLOAD = DONOR / "apex/030-com.google.android.os.statsd_compressed/apex_payload.img"
STATSD_SHA256 = "250f13d639e9fa0b67fc3725927ba43b54bf90071bf4a4105bcd92125b480dc5"
FILE_LIMIT = 32 * 1024**2
TOTAL_LIMIT = 1024**3
CARRIER_DIRS = (
    "/system/lib64", "/system/lib64/bootstrap", "/system/system_ext/lib64",
    "/system/product/lib64", "/vendor/lib64", "/odm/lib64", "/my_product/lib64", "/my_stock/lib64",
)
APEX_DIRS = (
    ("001-com.android.compos", "com.android.compos", "lib64"),
    ("003-com.android.i18n", "com.android.i18n", "lib64"),
    ("004-com.android.npumanager", "com.android.npumanager", "lib64"),
    ("005-com.android.runtime", "com.android.runtime", "lib64"),
    ("005-com.android.runtime", "com.android.runtime", "lib64/bionic"),
    ("007-com.android.virt", "com.android.virt", "lib64"),
)


def library_name(name):
    return len(name) <= 192 and name.isascii() and name.endswith(".so") and all(
        char.isalnum() or char in "_.+@-" for char in name
    )


def ordinary_file(info):
    return stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def stable_file(path, expected):
    before = source.plain(path).lstat()
    require(ordinary_file(before) and source.identity(before) == expected, f"Input changed: {path.name}")
    require(64 <= before.st_size <= FILE_LIMIT, f"ELF size outside bound: {path.name}")
    with path.open("rb") as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        # Windows can expose different ctime representations for path and
        # handle stats. Check each full identity again through its own API.
        require(opened[:4] == expected[:4], f"Opened input changed: {path.name}")
        raw = stream.read(before.st_size + 1)
        require(len(raw) == before.st_size and source.identity(os.fstat(stream.fileno())) == opened,
                f"ELF bytes or open identity changed: {path.name}")
    require(source.identity(path.lstat()) == expected, f"Named input changed: {path.name}")
    return raw


class Catalog:
    def __init__(self, parse):
        self.parse = parse
        self.files = {}
        self.names = defaultdict(set)
        self.aliases = {}
        self.opaque_aliases = {}
        self.directories = {}
        self.extracted_directories = {}
        self.samples = {}
        self.read_bytes = 0

    def add(self, path, name, read, evidence):
        require(path not in self.files, f"Duplicate candidate path: {path}")
        self.files[path] = read, evidence
        if name:
            self.names[name].add(path)

    def candidates(self, name):
        return sorted(self.names.get(name, ()))

    def describe(self, path):
        if path in self.samples:
            return self.samples[path]
        read, evidence = self.files[path]
        raw = read()
        self.read_bytes += len(raw)
        require(self.read_bytes <= TOTAL_LIMIT, "Candidate byte budget exceeded")
        try:
            profile = parse_elf_candidate(raw, self.parse)
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"ELF candidate rejected: {path}: {error}") from error
        result = {**profile, "source": evidence}
        self.samples[path] = result
        return result


def add_carrier_file(catalog, view, path, name):
    evidence = {"kind": "sealedCarrier", "path": path}

    def read():
        key, found = view.walk(path)
        require(found is not None and view.plan[key].kind == "file", f"Carrier file missing: {path}")
        nid, node = found
        plan = view.plan[key]
        require(node.links == 1 and 64 <= node.size == plan.size <= FILE_LIMIT, f"Carrier extent: {path}")
        raw = b"".join(view.reader.chunks(node.spans))
        require(len(raw) == node.size and sha256(raw).hexdigest() == plan.payload["sha256"], f"Carrier bytes: {path}")
        evidence["inode"] = nid
        return raw

    catalog.add(path, name, read, evidence)


def add_carrier(catalog, view):
    add_carrier_file(catalog, view, APP, None)
    for directory in CARRIER_DIRS:
        key, found = view.walk(directory)
        if found is None:
            catalog.directories[directory] = {"kind": "sealedCarrier", "present": False}
            continue
        if view.plan[key].kind == "symlink":
            _, target = view.file_bytes(directory, "symlink")
            catalog.aliases[directory] = target.decode("ascii")
            catalog.directories[directory] = {"kind": "sealedCarrierAlias", "followed": False}
            continue
        entries = view.entries(key)
        count = 0
        for raw_name in sorted(entries):
            name = raw_name.decode("ascii")
            if not library_name(name):
                continue
            path = f"{directory}/{name}"
            node = view.plan[key + (raw_name,)]
            if node.kind == "file":
                add_carrier_file(catalog, view, path, name)
                count += 1
            elif node.kind == "symlink":
                _, target = view.file_bytes(path, "symlink")
                catalog.aliases[path] = target.decode("ascii")
        catalog.directories[directory] = {"kind": "sealedCarrier", "present": True, "regularLibraries": count}
    for path in ("/product", "/system_ext", "/system/bin/linker64"):
        _, target = view.file_bytes(path, "symlink")
        catalog.aliases[path] = target.decode("ascii")


def add_saved_apex(catalog, folder, module, subdir):
    directory = source.plain(DONOR / "apex" / folder / "files" / subdir)
    root = f"/apex/{module}/{subdir}"
    before = directory.lstat()
    require(stat.S_ISDIR(before.st_mode), f"Saved APEX directory missing: {root}")
    identity = source.identity(before)
    catalog.extracted_directories[directory] = identity
    count = 0
    for file in sorted(directory.iterdir()):
        if not library_name(file.name):
            continue
        info = file.lstat()
        path = f"{root}/{file.name}"
        if stat.S_ISLNK(info.st_mode):
            catalog.aliases[path] = os.readlink(file)
            continue
        if getattr(info, "st_file_attributes", 0) & 0x400:
            catalog.opaque_aliases[path] = {
                "sourcePath": file.relative_to(DONOR).as_posix(),
                "reparseTag": getattr(info, "st_reparse_tag", None),
            }
            continue
        if not ordinary_file(info):
            continue
        pin = source.identity(info)
        catalog.add(path, file.name, lambda file=file, pin=pin: stable_file(file, pin), {
            "kind": "savedApexExtraction", "path": file.relative_to(DONOR).as_posix(), "module": module,
        })
        count += 1
    require(source.identity(directory.lstat()) == identity, f"APEX directory changed: {root}")
    catalog.directories[root] = {"kind": "savedApexExtraction", "present": True, "regularLibraries": count}


def add_ext4_apex(catalog, ext4, payload, label, digest, version, inodes_per_group, filesystem_bytes):
    fs = ext4(BytesIO(payload), len(payload), "7d1522e19dfa5edba43e98e3a4d20250",
              0x42, inodes_per_group, filesystem_bytes)
    root, _ = fs.directory(2)
    manifest, _ = fs.lookup("apex_manifest.pb", 1, 4096)
    module = apex_manifest(manifest, label.rsplit("/", 1)[1], version)
    nid, kind = root["lib64"]
    require(kind == 2, f"Expected raw APEX library directory: {label}")
    names, _ = fs.directory(nid)
    count = 0
    for name, (_, kind) in sorted(names.items()):
        if not library_name(name):
            continue
        require(kind == 1, f"Unexpected raw APEX library type: {label}/{name}")
        member = "lib64/" + name
        catalog.add(f"{label}/{member}", name, lambda member=member: fs.lookup(member, 1, FILE_LIMIT)[0], {
            "kind": "rawApexExt4", "payloadSha256": digest, "member": member,
        })
        count += 1
    catalog.directories[f"{label}/lib64"] = {
        "kind": "rawApexExt4", "present": True, "regularLibraries": count, "manifest": module,
    }


def pinned_receipt(pin):
    path, digest = pin
    return json.loads(source.read_small(ROOT / path, 65536, digest))


def check_frontier(catalog, frontier, expanded):
    objects = expanded["objects"]
    expected = {APP: frontier["appProcess64"], INTERPRETER: frontier["interpreter"]}
    expected.update((row["candidate"], row) for row in frontier["directLibraryCandidates"].values())
    for path, row in expected.items():
        actual = objects[path]
        require(all(actual[field] == row[field] for field in ("bytes", "sha256", "needed", "soname", "interpreter")),
                f"Pinned entry or direct candidate changed: {path}")
    reachable_names = {edge["needed"] for edges in expanded["edges"].values() for edge in edges}
    require(set(frontier["nextHop"]["names"]) <= reachable_names, "Pinned next-hop names are missing from the scan")
    require(catalog.aliases["/system/bin/linker64"] == INTERPRETER, "Carrier interpreter alias differs")
    for library in ("libc.so", "libdl.so", "libm.so", "libdl_android.so"):
        target = f"/apex/com.android.runtime/lib64/bionic/{library}"
        require(catalog.aliases[f"/system/lib64/{library}"] == target and target in catalog.files,
                f"Carrier Runtime alias differs: {library}")
    pins = {
        "libstatssocket.so": "f8dd6b08afe42c1c28bb7327aa264a723929c8205aa5f416cc92a73caf3a93ab",
        "libstatspull.so": "7fd4d956013d13249530c17da0879fba4c26199e926184689ffb816aaf86a281",
    }
    for name, digest in pins.items():
        path = f"{STATSD_ROOT}/lib64/{name}"
        require(objects[path]["sha256"] == digest and objects[path]["soname"] == name, f"Statsd ELF pin changed: {name}")


def derive():
    previous, frontier = (pinned_receipt(pin) for pin in (READBACK, FRONTIER))
    ext4, elf = held_reader(source.read_small(ROOT / ELF_READER[0], 32768, ELF_READER[1]))
    catalog = Catalog(elf)
    image = previous["image"]
    require(previous["status"] == "PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY"
            and previous["planSha256"] == PLAN_SHA, "Unexpected carrier source receipt")
    carrier = ROOT / image["path"]
    require(carrier.is_relative_to(ROOT / "out") and source.plain(carrier) == carrier, "Unexpected carrier location")
    named = source.identity(carrier.lstat())
    require(list(named) == image["identity"], "Carrier identity changed")

    art_pin = frontier["selectedArtPayload"]
    art_image = DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img"
    art = source.read_small(art_image, art_pin["bytes"], art_pin["sha256"])
    statsd = source.read_small(STATSD_PAYLOAD, 3444736, STATSD_SHA256)
    runtime = frontier["selectedRuntimePayload"]
    source.read_small(DONOR / "apex/005-com.android.runtime/apex_payload.img", runtime["bytes"], runtime["sha256"])
    for folder, module, subdir in APEX_DIRS:
        add_saved_apex(catalog, folder, module, subdir)
    for name, target in frontier["runtimeExtractionSymlinks"].items():
        path = f"/apex/com.android.runtime/{name}"
        if path in catalog.opaque_aliases:
            catalog.opaque_aliases[path]["priorObservedTarget"] = target
    add_ext4_apex(catalog, ext4, art, ART_ROOT, art_pin["sha256"], 371000140, 96, 7660 * 4096)
    add_ext4_apex(catalog, ext4, statsd, STATSD_ROOT, STATSD_SHA256, 371020260, 48, 831 * 4096)

    interp_file = DONOR / "apex/005-com.android.runtime/files/bin/linker64"
    interp = frontier["interpreter"]
    catalog.add(INTERPRETER, "ld-android.so",
                lambda: source.read_small(interp_file, interp["bytes"], interp["sha256"]), {
                    "kind": "pinnedRuntimeInterpreter", "path": interp_file.relative_to(DONOR).as_posix(),
                    "candidateReason": "preloaded interpreter SONAME, distinct from the physical system stub",
                })

    plan, _, _ = load_plan()
    backing = previous["expectedCoreApexFiles"]
    with carrier.open("rb") as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        require(opened[:4] == named[:4], "Opened carrier changed")
        reader = Erofs(stream, image["bytes"], len(plan) + len(backing) + 1)
        require(reader.geometry == previous["geometry"], "Carrier geometry changed")
        add_carrier(catalog, CarrierView(reader, plan, backing))
        seeds = (APP, INTERPRETER)
        without_statsd = walk_graph(seeds, catalog.describe, lambda name: [
            path for path in catalog.candidates(name) if not path.startswith(STATSD_ROOT + "/")
        ])
        expanded = walk_graph(seeds, catalog.describe, catalog.candidates)
        check_frontier(catalog, frontier, expanded)
        reader.check_geometry()
        require(source.identity(os.fstat(stream.fileno())) == opened and source.identity(carrier.lstat()) == named,
                "Carrier changed during the candidate scan")
    for path, identity in catalog.extracted_directories.items():
        require(source.identity(source.plain(path).lstat()) == identity, f"Saved extraction changed: {path.name}")

    return {
        "schema": "oneos-app-process-declared-elf-candidate-graph/v1",
        "status": "VERIFIED_BOUNDED_STATIC_CANDIDATE_GRAPH",
        "inputs": {
            "carrierSha256": image["sha256"], "materializationPlanSha256": PLAN_SHA,
            "frontierReceiptSha256": FRONTIER[1], "elfReaderSha256": ELF_READER[1],
            "runtimePayloadSha256": runtime["sha256"], "artPayloadSha256": art_pin["sha256"],
            "statsdPayloadSha256": STATSD_SHA256,
        },
        "candidateDirectories": dict(sorted(catalog.directories.items())),
        "observedAliases": dict(sorted(catalog.aliases.items())),
        "opaqueSavedExtractionAliases": dict(sorted(catalog.opaque_aliases.items())),
        "toolSha256": {
            name: sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
            for name in (Path(__file__).name, "guest_elf_candidate.py", "guest_elf_dependency_graph.py")
        },
        "indexedPhysicalObjects": len(catalog.files),
        "parsedUniqueObjects": len(catalog.samples),
        "parsedBytes": catalog.read_bytes,
        "withoutStatsd": {
            "objects": len(without_statsd["objects"]), "edge_count": without_statsd["edge_count"],
            "unresolved": without_statsd["unresolved"],
        },
        "expanded": expanded,
        "effectiveNamespaceSelected": False,
        "runtimeSymbolOrDlopenClosureVerified": False,
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
    run = ROOT / "out/guest-app-process-dependency-graph" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / "receipt.json").write_text(payload, encoding="utf-8")
    graph = result["expanded"]
    print(run)
    print(f'{len(graph["objects"])} objects, {graph["edge_count"]} edges, '
          f'{len(graph["ambiguous"])} ambiguous names, {len(graph["unresolved"])} unresolved names')


if __name__ == "__main__":
    main()
