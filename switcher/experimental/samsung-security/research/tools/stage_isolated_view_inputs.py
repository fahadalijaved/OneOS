#!/usr/bin/env python3
"""Emit a PC-only input manifest for the fixed isolated preparation profile."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import uuid


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "out/isolated-view-inputs"
STAGE = "/data/local/tmp/oneos-viewprep"
GUARD = "/dev/oneos-retained-viewprep"
IMAGE = WORKSPACE / "firmware/donor/OneOS_ColorOS17_FindX9Ultra_IN_Full.img"
IMAGE_BYTES = 14669168640
IMAGE_SHA = "92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6"
CONTROLLER_SHA = "1f47c5edb783c4a5b691326f8c2d94665bb9b1e963b8fcffcdbfe6d51c730180"
CONTROLLER_RUN = ROOT / "out/isolated-retained-view-controller/r-c88346bc"
CONTROLLER = CONTROLLER_RUN / "oneos_retained_root_view_isolated"
DONOR_INDEX = WORKSPACE / "inventory/donor-image.json"
EXT4_PROOF = ROOT / "out/guest-private-socket-view-plan/image-target/DIRECT-EXT4.json"
PAIR = ROOT / "out/isolated-retained-view-pair/r-bbb18fa1/receipt.json"
OLD_ID = ROOT / (
    "firmware/installed-oneos-stage-profile/"
    "20261106T021041297736Z-652828e6480c42f2b54d3f468d2175df/system.raw.id"
)
PINS = {
    DONOR_INDEX: "fa1734294e0d8a5d03a1a96a3b0f7ebbfdb0172838d7ca62f812f5ab9d606c3d",
    EXT4_PROOF: "7878ece9efd32aea5b68e09fc97ae19cdef8d6d7f345ca6024ec6ebd2749e8b4",
    CONTROLLER_RUN / "receipt.json": "ece49e0dd778ecd20f1c06a1cb54dc4ff94ca233e12823a8e583c485ad0e8e49",
    PAIR: "bf77aa07a33689b44d2ac02eee3f39131803576967a48ff2a44a290785a212b4",
    OLD_ID: "8d2d68f90884e17d7a5bde5397a0b8ec9facbd0c7f1b1671ef1ad57b6ee99221",
    CONTROLLER: CONTROLLER_SHA,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(path):
    path = Path(path)
    parts = path.relative_to(WORKSPACE).parts
    require(".." not in parts, "Workspace traversal refused")
    current = WORKSPACE
    for part in (None, *parts):
        if part is not None:
            current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
                "Workspace link or reparse point refused")
    return path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, data):
    return {
        "path": os.path.relpath(path, ROOT).replace("\\", "/"),
        "bytes": len(data),
        "sha256": digest(data),
    }


def capture(path, expected, limit=1_048_576):
    path = checked(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit, "Bounded regular evidence")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) == info.st_size and digest(data) == expected, f"Evidence changed: {path.name}")
    return data


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def read_at(stream, offset, count):
    require(0 <= offset and 0 < count <= 4096 and offset + count <= IMAGE_BYTES,
            "Exact bounded ext4 span")
    stream.seek(offset)
    data = stream.read(count)
    require(len(data) == count, "Short ext4 span")
    return data


def directory_entries(block):
    result = {}
    position = 0
    while position < len(block):
        require(len(block) - position >= 8, "Truncated ext4 entry")
        inode, length, size, kind = struct.unpack_from("<IHBB", block, position)
        require(8 <= length <= len(block) - position and length % 4 == 0 and size <= length - 8,
                "Invalid ext4 directory entry")
        if inode:
            name = block[position + 8:position + 8 + size].decode("utf-8")
            require(name and "/" not in name and "\0" not in name and name not in result,
                    "Invalid or duplicate ext4 directory name")
            result[name] = (inode, kind)
        position += length
    return result


def inspect_image(index, ext4):
    require(index["rawRelativePath"] == IMAGE.relative_to(WORKSPACE).as_posix()
            and index["rawBytes"] == IMAGE_BYTES and index["rawSha256"] == IMAGE_SHA,
            "Exact original ColorOS donor index")
    require(ext4["status"] == "ORIGINAL_PC_IMAGE_DEV_EMPTY"
            and ext4["imagePath"] == os.path.relpath(IMAGE, ROOT).replace("\\", "/")
            and ext4["imageBytes"] == IMAGE_BYTES
            and ext4["wholeImageSha256Inherited"] == IMAGE_SHA,
            "Same image as the frozen ext4 observation")
    image = checked(IMAGE)
    saved_stat = ext4["fileStatTuple"]
    before = image.lstat()
    require(stat.S_ISREG(before.st_mode) and identity(before) == saved_stat,
            "Same held PC image object and metadata")
    spans = {}
    regions = []
    with image.open("rb") as stream:
        opened_stat = identity(os.fstat(stream.fileno()))
        # The named and open Windows APIs expose different ctime values. Join
        # by volume/inode, length and mtime, then require each view to be stable.
        require(opened_stat[:4] == saved_stat[:4], "Actual opened PC image identity")
        require(len(ext4["reads"]) == 6, "Six admitted saved image spans")
        for row in ext4["reads"]:
            name = Path(row["path"]).name
            require(name not in spans and row["count"] == row["bytes"], "Unique saved span")
            data = read_at(stream, row["offset"], row["count"])
            require(digest(data) == row["sha256"], f"Actual held image span changed: {name}")
            spans[name] = data
            regions.append({"label": name, "offset": row["offset"], "bytes": len(data), "sha256": digest(data)})
        require(sum(row["bytes"] for row in regions) == 9760, "Expected span-read bound")
        superblock = spans["superblock.bin"]
        group = spans["group0-descriptor.bin"]
        u16 = lambda data, offset: struct.unpack_from("<H", data, offset)[0]
        u32 = lambda data, offset: struct.unpack_from("<I", data, offset)[0]
        filesystem = ext4["filesystem"]
        require(u16(superblock, 56) == 0xef53 and u32(superblock, 24) == 2
                and u16(superblock, 88) == 256 and u32(superblock, 40) == 8160
                and u32(superblock, 96) == 0x242 and u32(superblock, 100) == 0x7b
                and superblock[104:120].hex() == filesystem["uuid"]
                and u32(superblock, 4) * 4096 == index["filesystemBytes"]
                and u32(group, 8) == filesystem["group0InodeTableBlock"],
                "Exact observed ext4 layout")
        root = directory_entries(spans["root-block0.bin"])
        dev = directory_entries(spans["dev-block0.bin"])
        require(dev == {".": (24, 2), "..": (2, 2)}, "Actual image dev remains empty")
        targets = {}
        for name, number in (("data", 21), ("data_mirror", 22), ("dev", 24)):
            require(root.get(name) == (number, 2), f"Actual image root {name} binding")
            offset = u32(group, 8) * 4096 + (number - 1) * 256
            inode = spans["dev-inode.bin"] if name == "dev" else read_at(stream, offset, 256)
            if name != "dev":
                regions.append({"label": f"{name}-inode.bin", "offset": offset,
                                "bytes": len(inode), "sha256": digest(inode)})
            mode = u16(inode, 0)
            require(stat.S_ISDIR(mode), f"Actual image {name} inode is a directory")
            targets[name] = {
                "inode": number,
                "uid": u16(inode, 2) | u16(inode, 120) << 16,
                "gid": u16(inode, 24) | u16(inode, 122) << 16,
                "mode": f"{stat.S_IMODE(mode):04o}",
            }
        require(targets["dev"] == {"inode": 24, "uid": 0, "gid": 0, "mode": "0755"},
                "Exact root-owned dev target")
        require(identity(os.fstat(stream.fileno())) == opened_stat, "Held PC image changed during read")
    require(identity(checked(IMAGE).lstat()) == saved_stat, "Named PC image changed during read")
    return {
        "source": {"path": os.path.relpath(IMAGE, ROOT).replace("\\", "/"),
                   "bytes": IMAGE_BYTES, "sha256": IMAGE_SHA, "wholeHashRecomputed": False,
                   "sha256Basis": "Pinned original donor index and the same saved PC file identity",
                   "matchesSavedPcFileIdentity": True, "namedAndOpenDeviceInodeSizeMtimeMatch": True,
                   "namedAndOpenMetadataStableWithinEachView": True},
        "filesystem": {**filesystem, "type": "ext4", "filesystemBytes": index["filesystemBytes"],
                       "trailingBytesUninterpreted": index["trailingBytesUninterpreted"],
                       "rootDirectories": targets, "devNonDotChildren": [], "devSocketPresent": False},
        "boundedReadBytes": sum(row["bytes"] for row in regions),
        "boundedReadRegions": regions,
    }


def target_objects():
    return [
        {"path": STAGE, "kind": "directory", "uid": 0, "gid": 0, "mode": "0700"},
        {"path": STAGE + "/bin", "kind": "directory", "uid": 0, "gid": 0, "mode": "0700"},
        {"path": STAGE + "/bin/oneos_retained_root_handoff", "kind": "regular", "uid": 0, "gid": 0,
         "mode": "0755", "bytes": 663592, "sha256": CONTROLLER_SHA},
        {"path": STAGE + "/system.raw", "kind": "regular", "uid": 0, "gid": 0, "mode": "0600",
         "bytes": IMAGE_BYTES, "sha256": IMAGE_SHA},
        {"path": STAGE + "/system.raw.id", "kind": "regular", "uid": 0, "gid": 0, "mode": "0644",
         "bytes": None, "sha256": None},
        {"path": STAGE + "/data", "kind": "directory", "uid": 1000, "gid": 1000, "mode": "0771"},
        *({"path": STAGE + "/data/" + name, "kind": "directory"} for name in ("user", "user/0", "data")),
        {"path": GUARD, "kind": "directory", "uid": 0, "gid": 0, "mode": "0700"},
        {"path": GUARD + "/lease", "kind": "regular", "uid": 0, "gid": 0, "mode": "0600",
         "bytes": 0, "links": 1},
    ]


def prepare_plan():
    held = {path: capture(path, expected) for path, expected in PINS.items()}
    index = json.loads(held[DONOR_INDEX])
    ext4 = json.loads(held[EXT4_PROOF])
    controller_receipt = json.loads(held[CONTROLLER_RUN / "receipt.json"])
    pair = json.loads(held[PAIR])
    controller = pin(CONTROLLER, held[CONTROLLER])
    require(controller_receipt["status"] == "PASS_PC_ISOLATED_STAGE_CONTROLLER_STATIC_ONLY"
            and controller_receipt["artifact"] == controller and controller["bytes"] == 663592
            and not controller_receipt["outputExecuted"] and not controller_receipt["phoneActions"],
            "Actual isolated controller artifact and receipt")
    require(pair["status"] == "PASS_PC_SIBLING_APP_HOST_CONTROLLER_COHORT_ONLY"
            and pair["isolatedControllerSha256"] == CONTROLLER_SHA
            and pair["distinctPackage"] == "com.fahadali.oneos.viewprep"
            and not pair["controllerPreprovisioned"] and not pair["phoneActions"],
            "Exact isolated companion pairing")
    old_id = held[OLD_ID].decode("ascii").split()
    require(len(old_id) == 3 and old_id[0] == str(IMAGE_BYTES) and old_id[1] == IMAGE_SHA
            and re.fullmatch(r"[0-9]+:[0-9]+:[0-9]+:[0-9]+", old_id[2]),
            "Recorded stock sidecar declares the same image size and hash")
    image = inspect_image(index, ext4)
    return {
        "schema": "oneos-isolated-view-input-plan/v1",
        "status": "PC_INPUTS_PINNED_DEVICE_STAGE_UNPROVISIONED",
        "producer": pin(Path(__file__).resolve(), checked(Path(__file__).resolve()).read_bytes()),
        "evidence": [pin(path, data) for path, data in held.items()],
        "image": image,
        "controller": controller,
        "companionPackage": pair["distinctPackage"],
        "fixedTargets": {"stage": STAGE, "guard": GUARD, "childImageRoot": "/mnt/gvi/root"},
        "targetObjects": target_objects(),
        "sidecar": {
            "path": STAGE + "/system.raw.id",
            "grammar": "<bytes> <lowercase_sha256> <st_dev>:<st_ino>:<st_size>:<mtime_seconds> LF",
            "statFormat": "%d:%i:%s:%Y",
            "targetBytes": IMAGE_BYTES,
            "targetSha256": IMAGE_SHA,
            "targetStat": None,
            "materializedBytes": None,
            "source": "After full target-byte verification, derive stat values from the actual held target object",
            "oldStockSidecarDeclarationMatches": True,
            "oldStockStatReusable": False,
        },
        "conditions": [
            "Distinct stage, raw image, data tree and guard objects with no stock or host data alias",
            "No symlink or fallback, and no mounts at or below the test data tree",
            "Only the protected test guard may contain the lease, with all three reservation names absent initially",
            "Required image data, data_mirror and empty dev directories stay on the verified read-only image mount",
            "Verify actual device bytes, stat and mounts separately before any preparation",
        ],
        "guardMarkersInitiallyAbsent": ["writer-blocked", "legacy-blocked", "view-blocked"],
        "imageCopiedOrExtracted": False,
        "targetOrPermitCreated": False,
        "deviceAction": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-plan", action="store_true", required=True)
    parser.parse_args()
    plan = prepare_plan()
    path = checked(OUT / ("r-" + uuid.uuid4().hex[:8]) / "manifest.json")
    path.parent.parent.mkdir(exist_ok=True)
    path.parent.mkdir(exist_ok=False)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")
    print(json.dumps(pin(path, path.read_bytes())))


if __name__ == "__main__":
    main()
