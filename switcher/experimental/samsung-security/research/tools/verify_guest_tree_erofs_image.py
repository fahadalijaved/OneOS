#!/usr/bin/env python3
"""Verify an uncompressed EROFS carrier against the exact sealed donor plan."""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import uuid

import build_guest_tree_native_manifest as native
import check_guest_tree_materialization_plan as source
from materialize_guest_tree import KIND, Node, PLAN_SHA, load_plan
import stream_guest_tree_core_apex_tar as core_apex


ROOT = Path(__file__).absolute().parents[1]
OUT = ROOT / 'out/guest-tree-erofs-image-readback'
MANIFEST = ROOT / 'out/guest-tree-native-manifest/r-62cc9c27/manifest.bin'
MANIFEST_SHA = '948b4f84a8718e73086b57e263a47ae0a0190049fa54b3f91dc64f81ce928698'
MANIFEST_SIZE = 2_430_550
BLOCK = 4096
CHUNK = 1024 * 1024
MAX_IMAGE = 16 * 1024**3
MAX_METADATA = 128 * 1024**2
SB_OFFSET, SB_SIZE = 1024, 128
MAGIC = 0xE0F5E1E2
FTYPE = {1: 'file', 2: 'directory', 7: 'symlink'}
ATTRS = {b'selinux', b'capability'}
require = source.require


def align(number, alignment):
    return (number + alignment - 1) // alignment * alignment


def crc32c(data):
    """EROFS uses initial ~0 and no final XOR."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82F63B78 if crc & 1 else 0)
    return crc


def xattr_filter_bit(suffix):
    """Short-input XXH32, seeded for the selected security namespace."""
    mask = 0xFFFFFFFF

    def rotl(value, bits):
        value &= mask
        return ((value << bits) | (value >> (32 - bits))) & mask

    require(suffix in ATTRS, 'Unsupported security xattr filter suffix')
    value = (0x25BBE08F + 6 + 0x165667B1 + len(suffix)) & mask
    pos = 0
    while pos + 4 <= len(suffix):
        lane = int.from_bytes(suffix[pos:pos + 4], 'little')
        value = rotl(value + lane * 0xC2B2AE3D, 17) * 0x27D4EB2F & mask
        pos += 4
    for byte in suffix[pos:]:
        value = rotl(value + byte * 0x165667B1, 11) * 0x9E3779B1 & mask
    value = (value ^ (value >> 15)) * 0x85EBCA77 & mask
    value = (value ^ (value >> 13)) * 0xC2B2AE3D & mask
    return 1 << ((value ^ (value >> 16)) & 31)


def directory_block(raw):
    require(12 <= len(raw) <= BLOCK, 'Bad directory block size')
    table, = struct.unpack_from('<H', raw, 8)
    require(12 <= table < len(raw) and table % 12 == 0, 'Bad directory name table offset')
    entries = list(struct.iter_unpack('<QHBB', raw[:table]))
    starts = [entry[1] for entry in entries] + [len(raw)]
    for i, (nid, begin, kind, reserved) in enumerate(entries):
        end = starts[i + 1]
        require(table <= begin < end <= len(raw) and nid and kind in FTYPE and reserved == 0,
                'Bad directory entry framing')
        name = raw[begin:end]
        if i + 1 == len(entries) and len(raw) == BLOCK:
            name = name.rstrip(b'\0')
        require(1 <= len(name) <= 255 and b'/' not in name and b'\0' not in name,
                'Bad raw directory name')
        yield name, nid, kind


@dataclass(frozen=True)
class Inode:
    mode: int
    uid: int
    gid: int
    links: int
    size: int
    attrs: tuple
    spans: tuple
    has_inline_tail: bool


class Erofs:
    def __init__(self, stream, size, count):
        self.stream = stream
        self.size = size
        self.metadata_read = 0
        self.extents = []
        self.xattr_cache = {}
        self.layouts = Counter()
        require(BLOCK <= size <= MAX_IMAGE and size % BLOCK == 0, 'Invalid bounded raw image length')
        first = self.read(0, BLOCK)
        sb = first[SB_OFFSET:SB_OFFSET + SB_SIZE]
        magic, checksum, self.compat, bits, ext_slots, self.root_nid, self.count = struct.unpack_from('<IIIBBHQ', sb)
        blocks, meta, shared = struct.unpack_from('<III', sb, 36)
        incompat, compr, devices, device_table, dir_bits = struct.unpack_from('<IHHHB', sb, 80)
        require(magic == MAGIC and bits == 12 and ext_slots == 0 and self.root_nid
                and self.count == count and blocks * BLOCK == size and meta < blocks and shared < blocks,
                'Unexpected single-image EROFS geometry or inode count')
        require(not self.compat & ~7 and not incompat & ~1 and not compr and not devices and not device_table
                and not any(sb[91:]) and not any(first[:SB_OFFSET]),
                'Unselected EROFS features, devices or reserved fields')
        require(dir_bits == 0, 'Nonzero directory block shift is unsupported')
        require(b'\0' in sb[64:80], 'EROFS volume name lacks a NUL terminator')
        if self.compat & 1:
            protected = bytearray(first[SB_OFFSET:])
            protected[4:8] = bytes(4)
            require(crc32c(protected) == checksum, 'EROFS superblock CRC32C differs')
        else:
            require(checksum == 0, 'Checksum stored with the feature disabled')
        self.claim(0, SB_OFFSET + SB_SIZE, 'superblock')
        self.meta, self.shared = meta * BLOCK, shared * BLOCK
        self.geometry = {'blocks': blocks, 'blockBytes': BLOCK, 'inodes': self.count, 'rootNid': self.root_nid,
                         'metaBlock': meta, 'sharedXattrBlock': shared, 'featureCompat': self.compat,
                         'featureIncompat': incompat, 'superblockChecksum': f'{checksum:08x}', 'uuidHex': sb[48:64].hex()}

    def read(self, offset, count, *, metadata=True):
        require(0 <= offset < offset + count <= self.size and count <= CHUNK, 'Read outside image or chunk bound')
        if metadata:
            self.metadata_read += count
            require(self.metadata_read <= MAX_METADATA, 'Metadata read budget exceeded')
        self.stream.seek(offset)
        raw = self.stream.read(count)
        require(len(raw) == count, 'Short raw image read')
        return raw

    def claim(self, offset, count, kind):
        require(0 <= offset < offset + count <= self.size, 'On-disk extent outside declared geometry')
        self.extents.append((offset, offset + count, kind))

    def xattr_entry(self, raw, pos):
        require(pos + 4 <= len(raw), 'Truncated xattr entry')
        name_size, index, value_size = struct.unpack_from('<BBH', raw, pos)
        name_end = pos + 4 + name_size
        end = name_end + value_size
        next_pos = align(end, 4)
        require(index == 6 and 1 <= name_size <= 10 and 1 <= value_size <= 51
                and next_pos <= len(raw) and not any(raw[end:next_pos]), 'Bad security xattr framing')
        name = raw[pos + 4:name_end]
        require(name in ATTRS, 'Unexpected security xattr name')
        return (b'security.' + name, raw[name_end:end]), next_pos

    def xattrs(self, offset, size):
        if not size:
            return ()
        require(12 < size <= 256, 'Unselected inode-body xattr size')
        raw = self.read(offset, size)
        name_filter, shared_count = struct.unpack_from('<IB', raw)
        pos = 12 + 4 * shared_count
        require(shared_count <= 2 and pos <= size and not any(raw[5:12]), 'Bad shared xattr header')
        entries = []
        for i in range(shared_count):
            xoff = self.shared + 4 * struct.unpack_from('<I', raw, 12 + 4 * i)[0]
            if xoff not in self.xattr_cache:
                header = self.read(xoff, 4)
                length, _, value_size = struct.unpack('<BBH', header)
                require(1 <= length <= 10 and 1 <= value_size <= 51, 'Bad shared xattr length')
                entry_size = align(4 + length + value_size, 4)
                entry, _ = self.xattr_entry(self.read(xoff, entry_size), 0)
                self.claim(xoff, entry_size, 'shared xattr')
                self.xattr_cache[xoff] = entry
            entries.append(self.xattr_cache[xoff])
        while pos < size:
            require(len(entries) < 2, 'Unexpected extra xattr')
            entry, pos = self.xattr_entry(raw, pos)
            entries.append(entry)
        require(1 <= len(entries) <= 2 and len({name for name, _ in entries}) == len(entries),
                'Duplicate or missing xattr records')
        if self.compat & 4:
            for name, _ in entries:
                require(not name_filter & xattr_filter_bit(name.removeprefix(b'security.')),
                        'EROFS xattr name filter hides an existing attribute')
        else:
            require(name_filter == 0, 'Name filter stored with feature disabled')
        return tuple(sorted(entries))

    def inode(self, nid):
        offset = self.meta + 32 * nid
        require(nid > 0 and offset >= SB_OFFSET + SB_SIZE, 'Invalid EROFS inode slot')
        raw = self.read(offset, 32)
        form, xcount, mode = struct.unpack_from('<HHH', raw)
        require(form in (0, 1, 4, 5), f'Unsupported non-flat EROFS inode format {form}')
        if form & 1:
            extra = self.read(offset + 32, 32)
            size, address, _, uid = struct.unpack_from('<QIII', raw, 8)
            gid, _, nanos, links = struct.unpack_from('<IQII', raw[28:] + extra)
            require(raw[6:8] == bytes(2) and nanos < 1_000_000_000 and not any(extra[16:]),
                    'Bad extended inode reserved fields or timestamp')
            inode_bytes = 64
        else:
            links, size, reserved, address, _, uid, gid, tail = struct.unpack_from('<HIIIIHHI', raw, 6)
            require(not reserved and not tail, 'Bad compact inode reserved fields')
            inode_bytes = 32
        xbytes = 12 + 4 * (xcount - 1) if xcount else 0
        attrs = self.xattrs(offset + inode_bytes, xbytes)
        spans = []
        inline = size % BLOCK if form & 4 else 0
        external = size - inline
        require(not form & 4 or inline > 0, 'Missing inline tail data')
        if external:
            require(0 < address < self.size // BLOCK, 'Invalid flat block address')
            self.claim(address * BLOCK, align(external, BLOCK), 'data blocks')
            spans.append((address * BLOCK, external))
        elif size:
            require(address == 0xFFFFFFFF, 'Inline-only file has a live block address')
        end = offset + inode_bytes + xbytes
        if inline:
            require(end // BLOCK == (end + inline - 1) // BLOCK, 'Inline tail crosses metadata block')
            spans.append((end, inline))
        self.claim(offset, inode_bytes + xbytes + inline, 'inode, attrs and inline tail')
        self.layouts[f'{"extended" if form & 1 else "compact"}/{"inline" if form & 4 else "plain"}'] += 1
        return Inode(mode, uid, gid, links, size, attrs, tuple(spans), bool(inline))

    def directory(self, node, nid, parent, count):
        require(27 <= node.size <= align((count + 2) * 267, BLOCK), 'Directory bytes exceed entry bound')
        entries = {}
        previous = b''
        for start, length in node.spans:
            for delta in range(0, length, BLOCK):
                logical = min(BLOCK, length - delta)
                block = self.read(start + delta, logical if node.has_inline_tail else BLOCK)
                # Kernel lookup compares the last flat name through the full block.
                require(not any(block[logical:]), 'Nonzero flat directory padding after logical EOF')
                for name, child, kind in directory_block(block[:logical]):
                    require(previous < name and len(entries) < count + 2, 'Unsorted, repeated or extra directory entry')
                    entries[name] = (child, kind)
                    previous = name
        require(entries.pop(b'.', None) == (nid, 2) and entries.pop(b'..', None) == (parent, 2),
                'Directory self or parent entry differs')
        return entries

    def check_geometry(self):
        end = 0
        for start, finish, kind in sorted(self.extents):
            require(start >= end, f'Overlapping on-disk extent at {start} ({kind})')
            end = finish

    def chunks(self, spans):
        for start, length in spans:
            for delta in range(0, length, CHUNK):
                yield self.read(start + delta, min(CHUNK, length - delta), metadata=False)


def verify_tree(reader, plan, core_files=None):
    # The tar adds one unlabeled carrier directory over the original donor root.
    expected = {(b'tree', *path): node for path, node in plan.items()}
    expected[()] = Node((), 'directory', 0, 0, 0o755, 0, (), None, None)
    if core_files is not None:
        require(core_files.keys() == set(core_apex.NAMES.values()), 'Expected exactly the three selected core APEX carrier files')
        for name, payload in core_files.items():
            path = (name.encode('ascii'),)
            expected[path] = Node(path, 'file', 0, 0, 0o444, payload['bytes'], (), None, payload)
    children = {path: set() for path, node in expected.items() if node.kind == 'directory'}
    for path in expected:
        if path:
            children[path[:-1]].add(path[-1])
    queue = [((), reader.root_nid, reader.root_nid, 2)]
    seen = set()
    files = []
    while queue:
        path, nid, parent, kind = queue.pop()
        try:
            node = expected[path]
            require(nid not in seen and FTYPE[kind] == node.kind, 'Unselected inode alias or directory entry type')
            seen.add(nid)
            found = reader.inode(nid)
            links = 2 + sum((path + (name,)) in children for name in children[path]) if kind == 2 else 1
            require((found.mode, found.uid, found.gid, found.links, found.attrs) ==
                    (KIND[node.kind] | node.mode, node.uid, node.gid, links, node.attrs),
                    'Stored inode type, mode, owner, links or raw xattrs differ')
            if kind == 2:
                entries = reader.directory(found, nid, parent, len(children[path]))
                require(entries.keys() == children[path], 'Raw directory namespace differs')
                queue.extend((path + (name,), child, nid, typ) for name, (child, typ) in reversed(entries.items()))
            else:
                require(found.size == node.size, 'Stored file or symlink size differs')
                if kind == 7:
                    require(b''.join(reader.chunks(found.spans)) == node.target, 'Stored raw symlink target differs')
                else:
                    files.append((path, found, node.payload['sha256']))
        except (ValueError, KeyError, struct.error) as exc:
            raise ValueError(f'{path!r} nid {nid}: {exc}') from exc
    require(len(seen) == len(expected) == reader.count, 'Incomplete reachable inode closure')
    reader.check_geometry()
    donor_files = 0
    donor_bytes = 0
    for path, found, expected_sha in files:
        digest = hashlib.sha256()
        for chunk in reader.chunks(found.spans):
            digest.update(chunk)
        require(digest.hexdigest() == expected_sha, f'Stored logical payload SHA-256 differs: {path!r}')
        if path[0] == b'tree':
            donor_files += 1
            donor_bytes += found.size
    return {'donorEntries': len(seen) - 1 - len(core_files or ()), 'regularFiles': donor_files,
            'logicalBytes': donor_bytes, 'layouts': dict(reader.layouts),
            'sharedXattrEntries': len(reader.xattr_cache), 'metadataReadBytes': reader.metadata_read}


def check_image(path, core_files=None):
    require(path.is_relative_to(ROOT / 'out'), 'Expected a repository out/ image')
    require(path.resolve(strict=True) == path and source.plain(path) == path, 'Noncanonical image path')
    named = path.lstat()
    require(stat.S_ISREG(named.st_mode) and not getattr(named, 'st_file_attributes', 0) & 0x400,
            'Expected a regular image with no reparse point')
    plan, _, _ = load_plan()
    manifest = source.read_small(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA)
    require(len(manifest) == MANIFEST_SIZE, 'Native manifest byte count differs')
    native.verify(manifest, plan)
    with path.open('rb') as stream:
        held = source.identity(os.fstat(stream.fileno()))
        require(held[:4] == source.identity(named)[:4], 'Opened and named image identity differ')
        reader = Erofs(stream, named.st_size, len(plan) + 1 + len(core_files or ()))
        result = verify_tree(reader, plan, core_files)
        require((result['donorEntries'], result['regularFiles'], result['logicalBytes']) ==
                (native.ROWS, native.FILES, native.LOGICAL_BYTES), 'Sealed whole-donor totals differ')
        digest = hashlib.sha256()
        for chunk in reader.chunks(((0, named.st_size),)):
            digest.update(chunk)
        require(source.identity(os.fstat(stream.fileno())) == held and source.identity(path.lstat()) == source.identity(named),
                'Held or named image changed during readback')
    return {'status': 'PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY', 'geometry': reader.geometry, 'readback': result,
            'image': {'path': path.relative_to(ROOT).as_posix(), 'bytes': named.st_size,
                      'sha256': digest.hexdigest(), 'identity': source.identity(named)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path, help='Regular raw image inside repository out/')
    parser.add_argument('--core-apex-carrier', action='store_true',
                        help='Require the three pinned top-level core APEX backing files')
    args = parser.parse_args()
    result = {'schema': 'oneos-guest-tree-erofs-image-readback/v1', 'status': 'HOLD',
              'toolSha256': source.sha(Path(__file__).read_bytes()), 'planSha256': PLAN_SHA,
              'nativeManifestSha256': MANIFEST_SHA, 'mountObserved': False,
              'writerExclusionEstablished': False, 'stageEligible': False}
    try:
        core_files = core_apex.backing_files() if args.core_apex_carrier else None
        if core_files is not None:
            result['carrierProfile'] = 'donor-tree-and-selected-core-apex'
            result['coreApexSourceCohortSha256'] = core_apex.COHORT_SHA
            result['expectedCoreApexFiles'] = {
                name: {'bytes': payload['bytes'], 'sha256': payload['sha256']}
                for name, payload in core_files.items()
            }
        else:
            result['carrierProfile'] = 'donor-tree-only'
        result.update(check_image(args.image.absolute(), core_files))
    except (OSError, ValueError, KeyError, struct.error) as exc:
        result['reason'] = str(exc)
    source.plain(OUT)
    OUT.mkdir(exist_ok=True)
    job = OUT / f'r-{uuid.uuid4().hex[:8]}'
    job.mkdir()
    receipt = job / 'receipt.json'
    with receipt.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(receipt)
    print(result['status'])
    return 1 if result['status'] == 'HOLD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
