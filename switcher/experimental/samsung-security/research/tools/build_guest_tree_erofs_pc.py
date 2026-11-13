"""Build the sealed guest tree and core APEX carrier as a raw EROFS image."""

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
import os
import shutil
import struct
import sys
import uuid

import guest_tree_erofs_metadata as metadata
import stream_guest_tree_core_apex_tar as core_apex
import stream_guest_tree_erofs_tar as tar


tree = tar.tree
require = tree.require
OUT = tar.ROOT / 'out/guest-tree-erofs-pc'
BLOCK = 4096
SLOT = 32
EXTENDED_INODE = 64
SUPER_OFFSET = 1024
META_BLOCK = 1
NULL_BLOCK = 0xffffffff
MAX_BYTES = 16 * 1024**3
FTYPE = {'file': 1, 'directory': 2, 'symlink': 7}


@dataclass(frozen=True)
class InodeSlot:
    node: tree.Node
    nid: int
    attrs: bytes


@dataclass(frozen=True)
class Payload:
    path: tuple
    node: tree.Node
    inline_source: bytes | None


def aligned(size, unit):
    return size + (-size) % unit


def slots_and_children(plan, core_files):
    nodes = {(): tree.Node((), 'directory', 0, 0, 0o755, 0, (), None, None)}
    nodes.update({(b'tree', *path): node for path, node in plan.items()})
    for name, source in core_files.items():
        path = (name.encode('ascii'),)
        require(path not in nodes, 'Duplicate carrier root entry')
        nodes[path] = tree.Node(path, 'file', 0, 0, 0o444, source['bytes'], (), None, source)

    slots = {}
    cursor = SLOT
    for path, node in nodes.items():
        attrs = metadata.inline_xattrs(node.attrs)
        width = aligned(EXTENDED_INODE + len(attrs), SLOT)
        if cursor % BLOCK + width > BLOCK:
            cursor = aligned(cursor, BLOCK)
        slots[path] = InodeSlot(node, cursor // SLOT, attrs)
        cursor += width

    children = {path: [] for path, slot in slots.items() if slot.node.kind == 'directory'}
    for path, slot in slots.items():
        if path:
            children[path[:-1]].append((path[-1], slot.nid, FTYPE[slot.node.kind]))
    return slots, children, aligned(cursor, BLOCK)


def superblock(root_nid, inode_count, blocks, identifier):
    require(0 < root_nid < 2**16 and 1 < blocks < NULL_BLOCK and len(identifier) == 16,
            'Unrepresentable EROFS geometry')
    first = bytearray(BLOCK)
    struct.pack_into('<IIIBBHQ', first, SUPER_OFFSET, 0xe0f5e1e2, 0, 1, 12, 0, root_nid, inode_count)
    struct.pack_into('<III', first, SUPER_OFFSET + 36, blocks, META_BLOCK, 0)
    first[SUPER_OFFSET + 48:SUPER_OFFSET + 64] = identifier
    # EROFS CRC32C uses an all-ones initial register and stores it without XOR.
    remainder = 0xffffffff
    for byte in first[SUPER_OFFSET:]:
        remainder ^= byte
        for _ in range(8):
            remainder = (remainder >> 1) ^ (0x82f63b78 if remainder & 1 else 0)
    struct.pack_into('<I', first, SUPER_OFFSET + 4, remainder)
    return first


def layout(plan, core_files, identifier):
    slots, children, inode_bytes = slots_and_children(plan, core_files)
    inodes = bytearray(inode_bytes)
    payloads = []
    next_block = META_BLOCK + inode_bytes // BLOCK
    for path, slot in slots.items():
        node, nid, attrs = slot.node, slot.nid, slot.attrs
        links = 1
        data = None
        if node.kind == 'directory':
            entries = children[path]
            parent = slots[path[:-1]].nid
            data = metadata.directory_bytes(nid, parent, entries)
            node = replace(node, size=len(data))
            links = 2 + sum(kind == FTYPE['directory'] for _, _, kind in entries)
        elif node.kind == 'symlink':
            data = node.target
            require(data and len(data) == node.size and b'\0' not in data, 'Invalid source symlink')

        address = next_block if node.size else NULL_BLOCK
        encoded = metadata.extended_inode(node, links, address, attrs)
        require(len(encoded) == EXTENDED_INODE, 'Invalid encoded inode width')
        offset = nid * SLOT
        inodes[offset:offset + len(encoded) + len(attrs)] = encoded + attrs
        if node.size:
            payloads.append(Payload(path, node, data))
            next_block += aligned(node.size, BLOCK) // BLOCK
        else:
            require(node.kind == 'file' and node.payload['sha256'] == hashlib.sha256(b'').hexdigest(),
                    'Unselected empty payload')

    size = next_block * BLOCK
    require(size <= MAX_BYTES, 'Image exceeds the fixed single-device bound')
    first = superblock(slots[()].nid, len(slots), next_block, identifier)
    return first, inodes, payloads, size, len(slots)


def emit_donor_payload(sink, node, read_at):
    cursor = 0

    def emit(offset, data):
        nonlocal cursor
        require(cursor <= offset and offset + len(data) <= node.size, 'Invalid donor payload offset')
        tar.write_zeros(sink, offset - cursor)
        tar.write_all(sink, data)
        cursor = offset + len(data)

    tree.emit_payload(node.payload, read_at, emit)
    tar.write_zeros(sink, node.size - cursor)


def write_image(sink, geometry, read_at):
    first, inodes, payloads, size, _ = geometry
    tar.write_all(sink, first)
    tar.write_all(sink, inodes)
    for payload in payloads:
        if payload.inline_source is not None:
            tar.write_all(sink, payload.inline_source)
        elif payload.path[0] == b'tree':
            emit_donor_payload(sink, payload.node, read_at)
        else:
            core_apex.copy_payload(payload.node.payload, sink)
        tar.write_zeros(sink, (-payload.node.size) % BLOCK)
    require(sink.tell() == size, 'Written image length differs from allocated blocks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--build', action='store_true')
    args = parser.parse_args()
    try:
        plan, image, _ = tree.load_plan()
        core_files = core_apex.backing_files()
        identifier = uuid.uuid5(uuid.NAMESPACE_URL, f'oneos-erofs:{tree.PLAN_SHA}:{core_apex.COHORT_SHA}')
        geometry = layout(plan, core_files, identifier.bytes)
        first, inodes, _, size, count = geometry
        result = {
            'schema': 'oneos-guest-tree-erofs-pc-build/v1', 'status': 'PLANNED_GEOMETRY_ONLY',
            'planSha256': tree.PLAN_SHA, 'coreApexSourceCohortSha256': core_apex.COHORT_SHA,
            'bytes': size, 'inodeCount': count, 'inodeRegionBytes': len(inodes),
            'firstBlockSha256': hashlib.sha256(first).hexdigest(), 'uuid': str(identifier),
            'independentReadback': False, 'stageEligible': False,
        }
        if args.build:
            tree.source.plain(OUT)
            require(shutil.disk_usage(OUT.parent).free >= size, 'Insufficient space for a single raw image')
            OUT.mkdir(exist_ok=True)
            job = OUT / f'r-{uuid.uuid4().hex[:8]}'
            job.mkdir()
            partial = job / 'guest.erofs.partial'
            complete = job / 'guest.erofs'
            print(f'Building {job.relative_to(tar.ROOT)}', file=sys.stderr, flush=True)
            with tar.held_image(image) as read_at:
                require(tree.hash_stream(read_at, image['bytes']) == image['sha256'], 'Whole donor image digest differs')
                with partial.open('xb') as sink:
                    write_image(sink, geometry, read_at)
                    sink.flush()
                    os.fsync(sink.fileno())
            partial.rename(complete)
            result.update(status='BUILT_PENDING_INDEPENDENT_READBACK', image=complete.relative_to(tar.ROOT).as_posix(),
                          sourceImageSha256=image['sha256'])
            with (job / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(result, stream, indent=2)
                stream.write('\n')
        print(json.dumps(result, indent=2))
        return 0
    except (KeyError, OSError, ValueError) as exc:
        print(f'Raw EROFS build refused: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
