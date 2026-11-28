"""Bind the five donor init property-context slots to the unchanged GTC source tree."""

import argparse
from base64 import b64decode
from hashlib import sha256
import json
import os
from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-property-partition-closure"
PLAN = "out/guest-tree-materialization-plan/r-b4e075c2/"
CENSUS = "out/guest-tree-ext4-census/r-55e26da9/"
LEGACY = "firmware/installed-oneos-code-profile/static/assets/guest_prepare.sh"
LABEL = b"u:object_r:property_contexts_file:s0\0"
ALIASES = {
    "/system_ext": (15579, "/system/system_ext"),
    "/product": (8596, "/system/product"),
    "/odm/etc": (8582, "/vendor/odm/etc"),
}
SLOTS = (
    ("/system/etc/selinux/plat_property_contexts",
     "/system/etc/selinux/plat_property_contexts", 9589),
    ("/system_ext/etc/selinux/system_ext_property_contexts",
     "/system/system_ext/etc/selinux/system_ext_property_contexts", 13431),
    ("/vendor/etc/selinux/vendor_property_contexts", "/vendor/etc", None),
    ("/product/etc/selinux/product_property_contexts",
     "/system/product/etc/selinux/product_property_contexts", 11717),
    ("/odm/etc/selinux/odm_property_contexts", "/vendor/odm", None),
)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def read_held(path, size):
    info = path.lstat()
    require(plain(info) and stat.S_ISREG(info.st_mode) and info.st_size == size,
            f"Plain fixed input: {path}")
    with path.open("rb") as stream:
        initial = os.fstat(stream.fileno())
        require(identity(initial)[:4] == identity(info)[:4], "Input identity on open")
        raw = stream.read(size + 1)
        require(len(raw) == size and identity(os.fstat(stream.fileno())) == identity(initial),
                "Input descriptor unchanged")
    final = path.lstat()
    require(plain(final) and identity(final) == identity(info), "Input name unchanged")
    return raw


def entries(raw):
    result = {}
    for line in raw.splitlines():
        entry = json.loads(line)
        parts = [b64decode(part, validate=True) for part in entry["pathB64"]]
        require(all(part and part not in (b".", b"..") and b"/" not in part and b"\0" not in part
                    for part in parts), "Canonical image namespace path")
        name = "/" + b"/".join(parts).decode("utf-8", "surrogateescape")
        require(name not in result, "Unique image namespace path")
        result[name] = entry
    return result


def resolve_slot(rows, path):
    """Interpret the three literal aliases under the donor root, without following PC paths."""
    pending = path[1:].split("/")
    prefix = ""
    chain = []
    seen = set()
    while pending:
        name = prefix + "/" + pending.pop(0)
        row = rows.get(name)
        if row is None:
            return name, None, chain
        chain.append({"path": name, "inode": row["inode"], "kind": row["kind"]})
        if row["kind"] == "symlink":
            require(name in ALIASES and name not in seen, "Only fixed donor alias edges")
            expected_inode, expected_target = ALIASES[name]
            require(row["inode"] == expected_inode and
                    b64decode(row["symlinkTargetB64"], validate=True) == expected_target.encode("ascii"),
                    "Exact rooted alias text")
            chain[-1]["absoluteGuestTarget"] = expected_target
            seen.add(name)
            prefix = ""
            pending = expected_target[1:].split("/") + pending
        else:
            require(row["kind"] == ("directory" if pending else "file"), "Exact slot path types")
            prefix = name
    return prefix, rows[prefix], chain


def check_slots(rows, plan):
    require(rows.keys() == plan.keys() and len(rows) == 15574, "Complete source/destination path domains")
    require(rows["/"]["kind"] == "directory" and rows["/"]["inode"] == 2 and
            rows["/vendor"]["kind"] == "directory" and rows["/vendor"]["inode"] == 15581 and
            rows["/vendor"]["nlink"] == 2 and not any(p.startswith("/vendor/") for p in rows) and
            rows["/odm"]["kind"] == "directory" and rows["/odm"]["inode"] == 8578,
            "Donor-only vendor stub and ODM root")
    selected = []
    for init_path, expected, inode in SLOTS:
        resolved, row, chain = resolve_slot(rows, init_path)
        require(resolved == expected and (row["inode"] if row else None) == inode, "Exact resolved slot")
        for step in chain:
            name = step["path"]
            original, destination = rows[name], plan[name]
            require({k: destination[k] for k in original} == original, "Same destination metadata source")
        if row:
            xattrs = {b64decode(x["nameB64"], validate=True): b64decode(x["valueB64"], validate=True)
                      for x in row["xattrs"]}
            require(row["uid"] == row["gid"] == 0 and row["mode"] == 0o644 and row["nlink"] == 1 and
                    xattrs.get(b"security.selinux") == LABEL and plan[resolved]["destinationMode"] == 0o644,
                    "Source and planned file label, owner and mode")
        selected.append((init_path, resolved, row, chain))
    return selected


def derive():
    pins = {}

    def read(name, size, expected):
        raw = read_held(ROOT / name, size)
        require(digest(raw) == expected, f"Exact held source: {name}")
        pins[name] = {"bytes": size, "sha256": expected}
        return raw

    material = json.loads(read(PLAN + "receipt.json", 5951,
        "1e00a9deff87625902fadd54d955a3cce52a3617f9703974956cdada531bac95"))
    census = json.loads(read(CENSUS + "receipt.json", 1943,
        "1013a572c13ecf439b4fd2e5f1f5ab5e8d178de8304d329de511924b2571a81c"))
    native = json.loads(read("out/guest-tree-property-info/fixture-v1/receipt.json", 5898,
        "20ab070525549d3db9dabe27ffb06103471905c8389d66261f8ec33a8067a764"))
    require([row["initPath"] for row in native["modernInitContextInputOrder"]] ==
            [init_path for init_path, _, _ in SLOTS] and native["runtimePropertyInfo"] is None,
            "Original init input ordering from native readback")
    require(material["sourceImage"] == census["image"] and
            material["sourceImage"]["sha256"] == "92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6"
            and material["destinationEligible"] is False, "Same unmaterialized donor image cohort")
    rows = entries(read(CENSUS + "namespace.jsonl", 5132484,
        "124ad42d7de69bdd5691ce189bd5a48eb7c5d2d05727ca748312c60fafe27919"))
    plan = entries(read(PLAN + "plan.jsonl", 8490653,
        "0786e4682f7ac2f7b20e99154baa72baa289a03b8cafe22c6a0db37c36b3b259"))
    selected = check_slots(rows, plan)
    legacy = read(LEGACY, 278725, "000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70")
    lines = legacy.splitlines()
    require(b"for vb in vendor odm vendor_dlkm" in lines[329] and
            b'mount --bind "/$vb" "$ROOTFS/$vb"' in lines[330] and
            b'lowerdir=$NRV/up:$ROOTFS/vendor/etc' in lines[862],
            "Legacy imports external partitions and has a separate vendor overlay path")
    child = read("compat/native/guest_tree_child_view.c", 25501,
        "b5197c0b71d372a60e31cf301df9af660fbadd04915ca0627bcf582a182b8281")
    require(all(token in child for token in (b"guest_tree_prepare_root(", b"GTC_GUEST_ROOT",
                                             b"observe_view(", b"make_dev(")),
            "Same GTC prepare-only source")

    image = material["sourceImage"]
    image_path = ROOT / image["path"]
    named = image_path.lstat()
    require(plain(named) and stat.S_ISREG(named.st_mode) and
            list(identity(named)) == image["namedFileIdentity"], "Held raw image identity")
    manifest = []
    total = 0
    with image_path.open("rb") as stream:
        initial = os.fstat(stream.fileno())
        require(identity(initial)[:4] == identity(named)[:4], "Bound opened donor image")
        for (path, resolved, row, chain), prior in zip(selected, native["modernInitContextInputOrder"]):
            item = {"initPath": path, "walk": chain}
            if row is None:
                item.update(status="ABSENT_IN_BARE_DONOR_ROOT", firstAbsentComponent=resolved)
            else:
                source = plan[resolved]["fileSource"]
                ranges = source["ranges"]
                require(len(ranges) == 1 and ranges[0]["kind"] == "data" and ranges[0]["fileOffset"] == 0,
                        "Selected context payload has one exact initialized range")
                region = ranges[0]
                size, offset = region["bytes"], region["imageOffset"]
                require(size == row["size"] and 0 < size <= 131072 and offset % 4096 == 0 and
                        0 < offset < image["bytes"] - size and total + size <= 220000,
                        "Bounded raw image context read")
                total += size
                stream.seek(offset)
                raw = stream.read(size)
                held = "../firmware/donor/extracted" + resolved
                require(prior["heldDonorPath"] == held and len(raw) == size and
                        raw == read(held, size, source["sha256"]), "Raw image equals exact donor context file")
                item.update(status="PRESENT_DONOR_CONTEXT", resolved=resolved, source=held, inode=row["inode"],
                            bytes=size, sha256=source["sha256"], imageOffset=offset,
                            uid=0, gid=0, mode="0644", label=LABEL.rstrip(b"\0").decode("ascii"))
            manifest.append(item)
        require(identity(os.fstat(stream.fileno())) == identity(initial), "Image descriptor stable")
    require(identity(image_path.lstat()) == identity(named) and total == 215035,
            "Image name stable and exact finite payload budget")
    return {
        "schema": "guest-tree-property-context-partition-closure/v1",
        "status": "DONOR_ONLY_CONTEXT_SOURCES_COMPLETE_STAGED_VIEW_UNVERIFIED",
        "toolSha256": digest(Path(__file__).read_bytes()),
        "pins": pins, "sourceImage": image, "rawImageBytesRead": total,
        "contextSlots": manifest,
        "compilerInputOrder": [row["source"] for row in manifest if row["status"] == "PRESENT_DONOR_CONTEXT"],
        "wholeImageHashRecomputed": False,
        "runtimeBinding": [
            "After guest_tree_prepare_child_view has the exact GTC_GUEST_ROOT and before any consumer or partition overlay, bind the five slots to the retained namespace and attached tree.",
            "Verify the literal symlink objects with readlinkat. Resolve their absolute targets relative to the held guest root, with no additional symlinks and no mount crossing. Check context file object/metadata/hash on the reopened tree.",
            "Require complete actual mountinfo showing no covering or nested mounts across any selected component. Verify the exact /vendor and /odm entries and ENOENT at /vendor/etc and /vendor/odm, not EACCES or failure on a foreign root.",
            "Keep that view through private property_info compilation/admission and first use. Refuse a vendor/odm overlay or fallback; any deliberately selected replacement requires a different context cohort.",
        ],
        "savedOneOSNotSelected": {"script": LEGACY, "partitionBindLines": [330, 331, 332],
                                  "conditionalVendorOverlayLine": 863},
        "completeDonorSourceCohort": True, "actualStagedContextCohort": None,
        "compiledPropertyInfo": None, "entryAdmitted": False, "hostContextsUsed": False,
        "filesystemMounted": False, "targetExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--require-staged", action="store_true")
    args = parser.parse_args()
    try:
        result = derive()
        require(not args.require_staged or result["actualStagedContextCohort"] is not None,
                "Actual retained GTC property context mount readback is absent")
        raw = (json.dumps(result, indent=2) + "\n").encode("utf-8")
        for directory in (OUT.parent, OUT):
            if args.stage:
                directory.mkdir(exist_ok=True)
            info = directory.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain owned output directory")
        path = OUT / "receipt.json"
        if args.stage:
            with path.open("xb") as stream:
                stream.write(raw)
        require(read_held(path, len(raw)) == raw, "Exact saved closure receipt")
        print(f"{path.relative_to(ROOT).as_posix()} {len(raw)} {digest(raw)}")
    except (OSError, ValueError, KeyError, IndexError) as exc:
        parser.exit(2, f"Refused: {exc}\n")


if __name__ == "__main__":
    main()
