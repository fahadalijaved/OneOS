#!/usr/bin/env python3
"""Census the root-reachable namespace in the held 92c7 donor ext4 image."""

import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import uuid


ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT.parent / "firmware/donor/OneOS_ColorOS17_FindX9Ultra_IN_Full.img"
IMAGE_BYTES = 14_669_168_640
IMAGE_SHA = "92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6"
OUT = ROOT / "out/guest-tree-ext4-census"
PROOFS = {
    "out/isolated-view-image-verification/r-fead4221/receipt.json":
        "fa9d4c307a41f491f5a6e5e3ac779dc0a5f4b9874fdb300b71786ccab43c8d59",
    "out/guest-private-socket-view-plan/image-target/DIRECT-EXT4.json":
        "7878ece9efd32aea5b68e09fc97ae19cdef8d6d7f345ca6024ec6ebd2749e8b4",
}
NAMESPACE_RECEIPT = "out/guest-tree-ext4-census/r-55e26da9/receipt.json"
NAMESPACE_RECEIPT_SHA = "1013a572c13ecf439b4fd2e5f1f5ab5e8d178de8304d329de511924b2571a81c"
NAMESPACE_SHA = "124ad42d7de69bdd5691ce189bd5a48eb7c5d2d05727ca748312c60fafe27919"
FILE_COUNT = 11_864
FILE_LOGICAL_BYTES = 13_787_452_714
BLOCK = 4096
INODE = 256
MAX_READ = 128 * 1024 * 1024
MAX_OUTPUT = 64 * 1024 * 1024
MAX_PATHS = 65_536
PAYLOAD_CHUNK = 2 * 1024 * 1024
ZEROES = memoryview(bytes(PAYLOAD_CHUNK))
EXTENTS = 0x80000
DIR_INDEX = 0x1000
XATTR_MAGIC = 0xea020000
TYPES = {
    1: (stat.S_IFREG, "file"), 2: (stat.S_IFDIR, "directory"),
    3: (stat.S_IFCHR, "character-device"), 4: (stat.S_IFBLK, "block-device"),
    5: (stat.S_IFIFO, "fifo"), 6: (stat.S_IFSOCK, "socket"),
    7: (stat.S_IFLNK, "symlink"),
}
XATTR_NAMES = {1: b"user.", 4: b"trusted.", 6: b"security.", 7: b"system."}
ACL_NAMES = {2: b"system.posix_acl_access", 3: b"system.posix_acl_default"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def b64(data):
    return base64.b64encode(data).decode("ascii")


def u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def ordinary(path):
    require(path.resolve() == path, f"Noncanonical path: {path.name}")
    for entry in (path, *path.parents):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & 0x400,
                f"Path link or reparse refused: {entry.name}")
        if entry == ROOT.parent:
            break
    return path


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def read_proof(name, expected):
    path = ordinary(ROOT / name)
    require(stat.S_ISREG(path.lstat().st_mode), "Evidence is a regular file")
    with path.open("rb") as stream:
        data = stream.read(131_073)
    require(len(data) <= 131_072 and sha(data) == expected, f"Evidence changed: {name}")
    return json.loads(data)


def xattr_entries(data, position, value_base):
    """Decode local values only. Offsets are relative to the enclosing ext4 format."""
    entries = {}
    spans = []
    while True:
        require(position + 4 <= len(data), "Missing xattr terminator")
        if u32(data, position) == 0:
            position += 4
            break
        require(position + 16 <= len(data), "Truncated xattr entry")
        length, index, offset, value_inode, size, _ = struct.unpack_from("<BBHIII", data, position)
        following = position + ((16 + length + 3) & ~3)
        require(following <= len(data) and value_inode == 0, "External value inode or xattr entry bounds")
        suffix = data[position + 16:position + 16 + length]
        if index in ACL_NAMES:
            require(not suffix, "Unexpected POSIX ACL xattr suffix")
            name = ACL_NAMES[index]
        else:
            require(index in XATTR_NAMES and suffix and b"\0" not in suffix,
                    f"Unsupported xattr name index {index}")
            name = XATTR_NAMES[index] + suffix
        start = value_base + offset
        end = start + size
        require(name not in entries and offset % 4 == 0 and end <= len(data),
                "Duplicate xattr or out-of-bounds value")
        entries[name] = data[start:end]
        if size:
            spans.append((start, end))
        position = following
    for start, end in sorted(spans):
        require(start >= position, "Overlapping xattr entry or value spans")
        position = end
    return entries


class Census:
    def __init__(self, stream, proof, anchor):
        self.stream = stream
        self.limit = IMAGE_BYTES
        self.bytes_read = 0
        self.path = ()
        self.current_inode = 2
        self.groups = {}
        self.external = {}
        self.objects = {}
        self.references = Counter()
        self.mapping = Counter()
        self.inode_flags = Counter()
        self.rows = []
        self.used_external = Counter()
        for span in anchor["reads"]:
            require(sha(self.read(span["offset"], span["count"])) == span["sha256"],
                    "Previously observed ext4 byte span changed")
        sb = self.read(1024, 1024)
        require(sha(sb) == proof["ext4SuperblockObservation"]["sha256"]
                and u16(sb, 56) == 0xef53 and u16(sb, 58) == 1
                and u32(sb, 20) == 0 and u32(sb, 24) == 2 and u32(sb, 28) == 2
                and u16(sb, 88) == INODE and (u32(sb, 92), u32(sb, 96), u32(sb, 100)) == (56, 578, 123)
                and u32(sb, 232) == 0, "Exact clean ext4 source profile")
        self.inode_count = u32(sb, 0)
        self.blocks = u32(sb, 4)
        self.limit = self.blocks * BLOCK
        self.ipg = u32(sb, 40)
        bpg = u32(sb, 32)
        require(self.limit == 14_554_550_272 and self.ipg == 8160 and bpg == 32768,
                "Exact ext4 geometry")
        count = (self.blocks + bpg - 1) // bpg
        require(0 < count <= 128 and (count - 1) * self.ipg < self.inode_count <= count * self.ipg,
                "Group and inode bounds")
        self.descriptors = self.read(BLOCK, count * 32)

    def read(self, offset, count):
        require(0 <= offset and 0 < count <= BLOCK * 2 and offset + count <= self.limit
                and self.bytes_read + count <= MAX_READ, "Metadata read bounds exceeded")
        self.stream.seek(offset)
        data = self.stream.read(count)
        self.bytes_read += len(data)
        require(len(data) == count, "Short metadata read")
        return data

    def block(self, number):
        require(0 < number < self.blocks, "Physical block bounds")
        return self.read(number * BLOCK, BLOCK)

    def raw_inode(self, number):
        require(1 <= number <= self.inode_count, "Inode number out of bounds")
        group, index = divmod(number - 1, self.ipg)
        if group not in self.groups:
            bitmap, table = struct.unpack_from("<II", self.descriptors, group * 32 + 4)
            flags = u16(self.descriptors, group * 32 + 18)
            require(not flags & 1 and 0 < table <= self.blocks - self.ipg * INODE // BLOCK,
                    "Uninitialized inode group or invalid inode table")
            self.groups[group] = (table, self.block(bitmap))
        table, bitmap = self.groups[group]
        require(bitmap[index // 8] & (1 << (index % 8)), "Directory references an unallocated inode")
        return self.read(table * BLOCK + index * INODE, INODE)

    def xattrs(self, raw):
        extra = u16(raw, 128)
        require(extra % 4 == 0 and (extra == 0 or 4 <= extra <= INODE - 128), "Invalid inode extra size")
        start = 128 + extra
        entries = {}
        if start + 4 <= INODE and u32(raw, start) == XATTR_MAGIC:
            entries = xattr_entries(raw, start + 4, start + 4)
        elif extra and start + 4 <= INODE:
            require(u32(raw, start) == 0, "Unknown inode-body xattr header")
        block = u32(raw, 104) | (u16(raw, 118) << 32)
        if block:
            if block not in self.external:
                data = self.block(block)
                magic, refs, blocks, _, checksum, *reserved = struct.unpack_from("<8I", data)
                require(magic == XATTR_MAGIC and refs > 0 and blocks == 1
                        and checksum == 0 and not any(reserved), "Unsupported external xattr header")
                self.external[block] = (refs, xattr_entries(data, 32, 0))
            _, other = self.external[block]
            require(entries.keys().isdisjoint(other), "Duplicate inline and external xattr")
            entries.update(other)
            self.used_external[block] += 1
        return entries, block or None

    def extents(self, raw):
        result = []
        visited = set()
        last = 0

        def walk(data, depth):
            nonlocal last
            magic, count, capacity, actual = struct.unpack_from("<HHHH", data)
            require(magic == 0xf30a and 0 <= depth == actual <= 5
                    and count <= capacity <= (len(data) - 12) // 12
                    and (count > 0 or depth == 0 and len(data) == 60), "Extent node framing")
            first = None
            previous = -1
            for i in range(count):
                offset = 12 + i * 12
                logical = u32(data, offset)
                require(logical > previous, "Unordered extent keys")
                previous = logical
                if first is None:
                    first = logical
                if depth:
                    low, high, unused = struct.unpack_from("<IHH", data, offset + 4)
                    child = (high << 32) | low
                    require(unused == 0 and child not in visited and len(visited) < 4096
                            and logical >= last, "Repeated or overlapping extent-index child")
                    visited.add(child)
                    require(walk(self.block(child), depth - 1) == logical, "Extent child first-key mismatch")
                else:
                    length, high, low = struct.unpack_from("<HHI", data, offset + 4)
                    initialized = length <= 32768
                    blocks = length if initialized else length - 32768
                    physical = (high << 32) | low
                    require(last <= logical < logical + blocks <= 1 << 32
                            and 0 < physical < physical + blocks <= self.blocks,
                            "Extent allocation bounds or logical overlap")
                    result.append((logical, physical, blocks, initialized))
                    require(len(result) <= 16_384, "Extent count exceeds census bound")
                    last = logical + blocks
            return first

        depth = u16(raw, 46)
        walk(raw[40:100], depth)
        return depth, result

    def ordered_blocks(self, extents, count):
        require(0 < count <= 4096, "Directory or symlink metadata exceeds block bound")
        done = 0
        for logical, physical, length, initialized in extents:
            require(initialized and logical == done and done + length <= count,
                    "Metadata block map has a hole, unwritten span or excess extent")
            for block in range(physical, physical + length):
                yield self.block(block)
            done += length
        require(done == count, "Metadata block map incomplete")

    def object(self, number, file_type):
        self.references[number] += 1
        if number in self.objects:
            row, actual = self.objects[number]
            require(actual == file_type != 2, "Repeated directory or conflicting directory entry type")
            return row, []
        raw = self.raw_inode(number)
        mode = u16(raw, 0)
        flags = u32(raw, 32)
        nlink = u16(raw, 26)
        size = u32(raw, 4) | (u32(raw, 108) << 32)
        expected_mode, kind = TYPES[file_type]
        require(stat.S_IFMT(mode) == expected_mode and nlink > 0 and u32(raw, 20) == 0,
                "Dead inode or entry/inode type mismatch")
        entries, ea_block = self.xattrs(raw)
        row = {
            "inode": number, "kind": kind, "uid": u16(raw, 2) | (u16(raw, 120) << 16),
            "gid": u16(raw, 24) | (u16(raw, 122) << 16), "mode": stat.S_IMODE(mode),
            "size": size, "nlink": nlink, "hardlinkGroup": number if nlink > 1 and file_type != 2 else None,
            "xattrs": [{"nameB64": b64(name), "valueB64": b64(entries[name])} for name in sorted(entries)],
            "symlinkTargetB64": None,
        }
        self.inode_flags[f"0x{flags:x}"] += 1
        extents = []
        if file_type in (1, 2, 7) and flags & EXTENTS:
            require(flags & ~(EXTENTS | DIR_INDEX) == 0 and (file_type == 2 or not flags & DIR_INDEX),
                    f"Unsupported data flags 0x{flags:x}")
            depth, extents = self.extents(raw)
            self.mapping[f"{kind}:extent-depth-{depth}"] += 1
            if file_type == 1:
                initialized_blocks = sum(length for _, _, length, initialized in extents if initialized)
                if initialized_blocks < (size + BLOCK - 1) // BLOCK:
                    self.mapping["file:potential-sparse-or-unwritten"] += 1
            elif file_type == 7:
                require(0 < size < BLOCK, "Extent symlink target size")
                (block,) = self.ordered_blocks(extents, 1)
                row["symlinkTargetB64"] = self.symlink(block[:size])
        elif file_type == 7:
            require(flags == 0 and 0 < size <= 60 and u32(raw, 28) == (8 if ea_block else 0),
                    "Unsupported fast symlink framing")
            self.mapping["symlink:fast"] += 1
            row["symlinkTargetB64"] = self.symlink(raw[40:40 + size])
        elif file_type == 1 and size == 0 and flags == 0 and not any(raw[40:100]):
            self.mapping["file:empty-without-extents"] += 1
        elif file_type in (1, 2):
            raise ValueError(f"Unsupported legacy or inline {kind} map, flags 0x{flags:x}")
        else:
            require(flags == 0, f"Unsupported special inode flags 0x{flags:x}")
            if file_type in (3, 4):
                old, new = struct.unpack_from("<II", raw, 40)
                require(not (old and new) and old <= 0xffff, "Unsupported special device encoding")
                row["deviceMajor"] = old >> 8 if old else (new >> 8) & 0xfff
                row["deviceMinor"] = old & 0xff if old else (new & 0xff) | ((new >> 12) & 0xfff00)
        self.objects[number] = row, file_type
        return row, extents

    @staticmethod
    def symlink(target):
        require(b"\0" not in target, "Symlink target contains NUL")
        return b64(target)

    @staticmethod
    def directory_entries(block):
        offset = 0
        while offset < BLOCK:
            number, length, namesize, kind = struct.unpack_from("<IHBB", block, offset)
            require(length >= 8 and length % 4 == 0 and offset + length <= BLOCK,
                    "Directory record has invalid framing")
            if number:
                require(0 < namesize <= length - 8 and kind in TYPES, "Directory name or file type bounds")
                name = block[offset + 8:offset + 8 + namesize]
                require(b"/" not in name and b"\0" not in name, "Directory name contains slash or NUL")
                yield name, number, kind
            offset += length

    def directory(self, number, parent, row, extents):
        require(not u32(self.raw_inode(number), 32) & DIR_INDEX, "Indexed directory format requires a census reader")
        require(row["size"] % BLOCK == 0, "Directory length is not block-aligned")
        entries = {}
        for block in self.ordered_blocks(extents, row["size"] // BLOCK):
            for name, child, kind in self.directory_entries(block):
                require(name not in entries and len(entries) < MAX_PATHS, "Duplicate name or directory entry bound")
                entries[name] = child, kind
        require(entries.pop(b".", None) == (number, 2) and entries.pop(b"..", None) == (parent, 2),
                "Directory dot or parent inode mismatch")
        require(row["nlink"] == 2 + sum(kind == 2 for _, kind in entries.values()),
                "Directory link count mismatch or unsupported overflow")
        return entries

    def walk(self):
        stack = [((), 2, 2, 2)]
        while stack:
            path, number, file_type, parent = stack.pop()
            self.path, self.current_inode = path, number
            require(len(path) <= 64 and sum(len(p) + 1 for p in path) <= 4096
                    and len(self.rows) < MAX_PATHS, "Namespace depth, path or row bound")
            row, extents = self.object(number, file_type)
            self.rows.append({"pathB64": [b64(part) for part in path], **row})
            if file_type == 2:
                children = self.directory(number, parent, row, extents)
                require(len(stack) + len(self.rows) + len(children) <= MAX_PATHS, "Namespace path budget")
                for name, (child, kind) in sorted(children.items(), reverse=True):
                    stack.append((path + (name,), child, kind, number))
        for number, (row, file_type) in self.objects.items():
            self.current_inode = number
            require(file_type == 2 or row["nlink"] == self.references[number], "Non-directory link count mismatch")
        for block, count in self.used_external.items():
            require(count <= self.external[block][0], "External xattr reference count is smaller than observed")


def jsonl(rows):
    data = b"".join(json.dumps(row, separators=(",", ":")).encode("ascii") + b"\n" for row in rows)
    require(len(data) <= MAX_OUTPUT, "Manifest size bound exceeded")
    return data


def admitted_namespace():
    prior = read_proof(NAMESPACE_RECEIPT, NAMESPACE_RECEIPT_SHA)
    manifest = prior["namespace"]
    require(prior["status"] == "PASS_ROOT_REACHABLE_EXT4_METADATA_CENSUS"
            and prior["imageIdentityStable"] is True and prior["image"]["sha256"] == IMAGE_SHA
            and manifest["path"] == "namespace.jsonl" and manifest["sha256"] == NAMESPACE_SHA
            and manifest["paths"] == 15_574 and manifest["kinds"]["file"] == FILE_COUNT,
            "Saved namespace receipt does not describe the admitted donor")
    path = (ROOT / NAMESPACE_RECEIPT).with_name("namespace.jsonl")
    require(stat.S_ISREG(ordinary(path).lstat().st_mode) and manifest["bytes"] == 5_132_484,
            "Saved namespace is not the expected regular manifest")
    with path.open("rb") as stream:
        data = stream.read(manifest["bytes"] + 1)
    require(len(data) == manifest["bytes"] and sha(data) == NAMESPACE_SHA, "Saved namespace bytes changed")
    return data, {
        "receiptPath": NAMESPACE_RECEIPT, "receiptSha256": NAMESPACE_RECEIPT_SHA,
        "path": path.relative_to(ROOT).as_posix(), "sha256": NAMESPACE_SHA, "bytes": len(data),
    }


class PayloadReader:
    """Hash bounded initialized extents and the filesystem's logical zero ranges."""

    def __init__(self, stream, limit):
        self.stream = stream
        self.limit = limit
        self.data_bytes = 0

    def update_data(self, digest, physical, length):
        require(0 < physical < physical + length <= self.limit
                and self.data_bytes + length <= FILE_LOGICAL_BYTES, "Payload read bounds exceeded")
        self.stream.seek(physical)
        remaining = length
        while remaining:
            count = min(remaining, PAYLOAD_CHUNK)
            chunk = self.stream.read(count)
            require(len(chunk) == count, "Short initialized payload read")
            digest.update(chunk)
            self.data_bytes += count
            remaining -= count

    @staticmethod
    def update_zeroes(digest, length):
        while length:
            count = min(length, PAYLOAD_CHUNK)
            digest.update(ZEROES[:count])
            length -= count

    def hash_file(self, size, extents):
        require(0 <= size <= FILE_LOGICAL_BYTES, "Logical file size bound exceeded")
        digest = hashlib.sha256()
        offset = 0
        data_start = self.data_bytes
        hole_bytes = 0
        unwritten_bytes = 0
        for logical, physical, blocks, initialized in extents:
            start = min(logical * BLOCK, size)
            end = min((logical + blocks) * BLOCK, size)
            require(offset <= start <= end, "Logical extent order changed")
            gap = start - offset
            self.update_zeroes(digest, gap)
            hole_bytes += gap
            length = end - start
            if length and initialized:
                self.update_data(digest, physical * BLOCK, length)
            elif length:
                self.update_zeroes(digest, length)
                unwritten_bytes += length
            offset = end
        self.update_zeroes(digest, size - offset)
        hole_bytes += size - offset
        data_bytes = self.data_bytes - data_start
        require(data_bytes + hole_bytes + unwritten_bytes == size, "Logical payload length did not reconcile")
        return digest.hexdigest(), data_bytes, hole_bytes, unwritten_bytes


def hash_payloads(reader):
    files = [row for row in reader.rows if row["kind"] == "file"]
    require(len(files) == FILE_COUNT and sum(row["size"] for row in files) == FILE_LOGICAL_BYTES,
            "Pinned regular-file closure or total logical length changed")
    payload_reader = PayloadReader(reader.stream, reader.limit)
    rows = []
    total_holes = 0
    total_unwritten = 0
    for row in files:
        number = row["inode"]
        reader.path = tuple(base64.b64decode(part, validate=True) for part in row["pathB64"])
        reader.current_inode = number
        raw = reader.raw_inode(number)
        size = row["size"]
        require(stat.S_ISREG(u16(raw, 0)) and (u32(raw, 4) | u32(raw, 108) << 32) == size,
                "Opened inode type or size changed after namespace census")
        flags = u32(raw, 32)
        if flags == EXTENTS:
            _, extents = reader.extents(raw)
        else:
            require(flags == 0 and size == 0 and not any(raw[40:100]), "Unsupported regular payload map")
            extents = []
        digest, data, holes, unwritten = payload_reader.hash_file(size, extents)
        total_holes += holes
        total_unwritten += unwritten
        rows.append({"pathB64": row["pathB64"], "inode": number, "size": size, "sha256": digest,
                     "dataBytes": data, "zeroBytes": holes + unwritten, "extents": extents})
    require(payload_reader.data_bytes + total_holes + total_unwritten == FILE_LOGICAL_BYTES,
            "Total logical payload length did not reconcile")
    return rows, {
        "files": len(rows), "logicalBytes": FILE_LOGICAL_BYTES, "dataBytes": payload_reader.data_bytes,
        "zeroBytes": total_holes + total_unwritten, "holeBytes": total_holes, "unwrittenBytes": total_unwritten,
        "emptyFiles": sum(row["size"] == 0 for row in rows),
        "extentBlockBytes": BLOCK, "extentFields": ["logicalBlock", "physicalBlock", "blocks", "initialized"],
    }


def run(payloads=False):
    inputs = [read_proof(name, expected) for name, expected in PROOFS.items()]
    proof, anchor = inputs
    require(proof["status"] == "PASS_WHOLE_HELD_PC_IMAGE_SHA256_ONLY"
            and proof["image"]["sha256"] == anchor["wholeImageSha256Inherited"] == IMAGE_SHA
            and proof["image"]["bytes"] == anchor["imageBytes"] == IMAGE_BYTES
            and proof["namedAndHeldStable"] is True and anchor["fileStatStableBeforeAfter"] is True,
            "Image proof and held-file anchor disagree")
    image = ordinary(IMAGE)
    named = image.lstat()
    require(stat.S_ISREG(named.st_mode) and identity(named) == anchor["fileStatTuple"],
            "Held donor image no longer has the admitted PC file identity")
    namespace = admitted_namespace() if payloads else None
    ordinary(OUT.parent)
    OUT.mkdir(exist_ok=True)
    ordinary(OUT)
    job = OUT / f"r-{uuid.uuid4().hex[:8]}"
    job.mkdir()
    receipt = {
        "schema": "guest-tree-ext4-census/v1", "status": "FAILED_CENSUS", "sourcePins": PROOFS,
        "toolSha256": sha(Path(__file__).read_bytes()),
        "image": {"path": proof["image"]["path"], "bytes": IMAGE_BYTES, "sha256": IMAGE_SHA,
                  "wholeHashRecomputed": False, "namedFileIdentity": identity(named)},
        "scope": "Root-reachable namespace and inode metadata, without file payload hashes, journal recovery or mount.",
    }
    if payloads:
        receipt.update(schema="guest-tree-ext4-payload-hashes/v1", status="FAILED_PAYLOAD_HASHES",
                       namespaceSource=namespace[1],
                       scope="Root-reachable regular-file logical SHA-256 hashes and source extent metadata. No blobs written.")
    reader = None
    try:
        with image.open("rb") as stream:
            held = identity(os.fstat(stream.fileno()))
            require(held[:4] == identity(named)[:4], "Named and opened donor image differ")
            reader = Census(stream, proof, anchor)
            reader.walk()
            manifest = jsonl(reader.rows)
            if payloads:
                require(manifest == namespace[0], "Fresh namespace does not byte-match saved census")
                rows, stats = hash_payloads(reader)
                output = jsonl(rows)
            require(identity(os.fstat(stream.fileno())) == held
                    and identity(ordinary(image).lstat()) == identity(named), "Held or named donor image changed")
        if payloads:
            require(admitted_namespace()[0] == namespace[0], "Saved namespace changed during payload read")
            with (job / "payloads.jsonl").open("xb") as stream:
                require(stream.write(output) == len(output), "Short payload manifest write")
            receipt.update(status="PASS_ALL_ROOT_REACHABLE_REGULAR_PAYLOAD_HASHES", imageIdentityStable=True,
                           filesystemBytes=reader.limit, readBytes=reader.bytes_read,
                           payloads={"path": "payloads.jsonl", "sha256": sha(output), "bytes": len(output), **stats})
        else:
            counts = Counter(row["kind"] for row in reader.rows)
            xattrs = Counter(name for row, _ in reader.objects.values() for name in
                             (item["nameB64"] for item in row["xattrs"]))
            with (job / "namespace.jsonl").open("xb") as stream:
                require(stream.write(manifest) == len(manifest), "Short manifest write")
            receipt.update(
                status="PASS_ROOT_REACHABLE_EXT4_METADATA_CENSUS", imageIdentityStable=True,
                filesystemBytes=reader.limit, readBytes=reader.bytes_read,
                namespace={"path": "namespace.jsonl", "sha256": sha(manifest), "bytes": len(manifest),
                           "paths": len(reader.rows), "kinds": dict(sorted(counts.items())),
                           "uniqueInodes": len(reader.objects),
                           "hardlinkGroups": sum(row["hardlinkGroup"] is not None for row, _ in reader.objects.values()),
                           "xattrInodeCountsByNameB64": dict(sorted(xattrs.items())),
                           "externalXattrBlocks": len(reader.external),
                           "inodesWithoutSelinuxXattr": len(reader.objects) - xattrs[b64(b"security.selinux")],
                           "inodeFlagCounts": dict(sorted(reader.inode_flags.items())),
                           "mappingCounts": dict(sorted(reader.mapping.items()))},
            )
    except (OSError, ValueError, KeyError, struct.error) as exc:
        receipt.update(error=type(exc).__name__, reason=str(exc))
        if reader is not None:
            receipt.update(pathB64=[b64(part) for part in reader.path], inode=reader.current_inode,
                           readBytes=reader.bytes_read, visitedPaths=len(reader.rows))
    with (job / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(job / "receipt.json")
    print(receipt["status"])
    return 0 if receipt["status"].startswith("PASS_") else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash-payloads", action="store_true", help="Hash all regular logical file bytes against the saved census")
    return run(parser.parse_args().hash_payloads)


if __name__ == "__main__":
    raise SystemExit(main())
