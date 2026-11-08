"""Read and hash the exact held isolated-stage image without copying or mounting it."""

import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import time
import uuid


ROOT = Path(__file__).absolute().parents[1]
PLAN = ROOT / "out/isolated-view-inputs/r-b85ca77d/manifest.json"
PLAN_SHA = "441d314626cefb0b5386ae189871c0363867cfe56864672f0f20ae7e6525f97d"
EXPECTED_IMAGE = ROOT.parent / "firmware/donor/OneOS_ColorOS17_FindX9Ultra_IN_Full.img"
EXT4_SUPERBLOCK_OFFSET = 1024
EXT4_SUPERBLOCK_SIZE = 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ordinary(path):
    require(path.resolve() == path, "Expected an exact local path")
    for component in (path, *path.parents):
        info = component.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Reparse path refused")
    return path


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def superblock_fields(data):
    magic, state = struct.unpack_from("<HH", data, 0x38)
    compat, incompat, rocompat = struct.unpack_from("<III", data, 0x5C)
    orphan = struct.unpack_from("<I", data, 0xE8)[0]
    require(magic == 0xEF53, "Held image does not have an ext4 superblock")
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "state": state,
        "featureCompat": compat,
        "featureIncompat": incompat,
        "featureRoCompat": rocompat,
        "lastOrphan": orphan,
        "cleanStateBit": bool(state & 1),
        "errorOrOrphanStateBit": bool(state & 6),
        "journalPresent": bool(compat & 4),
        "journalRecoveryFlag": bool(incompat & 4),
        "orphanFileMayBeNonempty": bool(rocompat & 0x10000),
    }


def main():
    raw = ordinary(PLAN).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PLAN_SHA, "Exact staged input manifest")
    source = json.loads(raw)["image"]["source"]
    image = ordinary(EXPECTED_IMAGE)
    require((ROOT / source["path"]).resolve() == image, "Exact raw source path")
    named = image.stat()
    require(stat.S_ISREG(named.st_mode) and named.st_size == source["bytes"], "Held raw extent")

    start = time.monotonic()
    with image.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(identity(named) == identity(before), "Named and opened image differ")
        stream.seek(EXT4_SUPERBLOCK_OFFSET)
        header = stream.read(EXT4_SUPERBLOCK_SIZE)
        require(len(header) == EXT4_SUPERBLOCK_SIZE, "Truncated ext4 superblock")
        fields = superblock_fields(header)
        stream.seek(0)
        digest = hashlib.sha256()
        count = 0
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(block)
            count += len(block)
        actual = digest.hexdigest()
        require(count == before.st_size and actual == source["sha256"], "Actual raw bytes differ")
        stream.seek(EXT4_SUPERBLOCK_OFFSET)
        require(stream.read(EXT4_SUPERBLOCK_SIZE) == header and
                identity(before) == identity(os.fstat(stream.fileno())), "Held image changed during full read")
    require(identity(named) == identity(ordinary(image).stat()), "Named image changed during full read")

    work = ROOT / "out/isolated-view-image-verification" / ("r-" + uuid.uuid4().hex[:8])
    work.parent.mkdir(exist_ok=True)
    ordinary(work.parent)
    work.mkdir(exist_ok=False)
    receipt = {
        "status": "PASS_WHOLE_HELD_PC_IMAGE_SHA256_ONLY",
        "inputManifest": {"path": PLAN.relative_to(ROOT).as_posix(), "sha256": PLAN_SHA},
        "image": {"path": source["path"], "bytes": source["bytes"], "sha256": actual},
        "ext4SuperblockObservation": fields,
        "namedAndHeldStable": True,
        "imageCopiedOrMounted": False,
        "deviceStageVerified": False,
        "elapsedSeconds": round(time.monotonic() - start, 3),
    }
    output = work / "receipt.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(output.relative_to(ROOT).as_posix(), hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
