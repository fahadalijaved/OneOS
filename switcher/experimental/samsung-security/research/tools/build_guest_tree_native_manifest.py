#!/usr/bin/env python3
"""Build and independently decode the fixed donor tree's native metadata manifest."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import uuid

import check_guest_tree_materialization_plan as source
from materialize_guest_tree import PLAN_RUN, PLAN_SHA, RECEIPT_SHA, load_plan


ROOT = Path(__file__).absolute().parents[1]
OUT = ROOT / 'out/guest-tree-native-manifest'
PLAN = PLAN_RUN / 'plan.jsonl'
PLAN_BYTES = 8_490_653
MAGIC = b'OGTMF001'
HEADER = struct.Struct('<8sIIIIQ32s')
RECORD = struct.Struct('<HBBHHIIIQ')
ATTRIBUTE = struct.Struct('<HH')
KINDS = {'directory': 1, 'file': 2, 'symlink': 3}
ROWS, FILES, DIRECTORIES, SYMLINKS = 15_574, 11_864, 3_381, 329
LOGICAL_BYTES = 13_787_452_714
MAX_MANIFEST = 4 * 1024 * 1024
require = source.require


def encode():
    raw = source.read_small(PLAN, PLAN_BYTES, PLAN_SHA)
    require(len(raw) == PLAN_BYTES, 'Exact plan size differs')
    rows = [(b'/'.join(source.raw_path(row['pathB64'])), row) for row in source.json_lines(raw)]
    rows.sort(key=lambda pair: pair[0])
    output = bytearray(HEADER.pack(MAGIC, ROWS, FILES, DIRECTORIES, SYMLINKS,
                                   LOGICAL_BYTES, bytes.fromhex(PLAN_SHA)))
    for path, row in rows:
        kind = row['kind']
        size = row['size'] if kind != 'directory' else 0
        if kind == 'file':
            body = bytes.fromhex(row['fileSource']['sha256'])
        elif kind == 'symlink':
            body = source.encoded_bytes(row['symlinkTargetB64'], 4095)
        else:
            body = b''
        attrs = row['xattrs']
        output.extend(RECORD.pack(len(path), KINDS[kind], len(attrs), row['destinationMode'],
                                  len(body) if kind == 'symlink' else 0,
                                  row['uid'], row['gid'], row['nlink'], size))
        output.extend(path)
        output.extend(body)
        for attr in attrs:
            name = source.encoded_bytes(attr['nameB64'], 255)
            value = source.encoded_bytes(attr['valueB64'], 1024)
            output.extend(ATTRIBUTE.pack(len(name), len(value)))
            output.extend(name)
            output.extend(value)
        require(len(output) <= MAX_MANIFEST, 'Manifest exceeds native byte budget')
    return bytes(output)


class Reader:
    """Read fields sequentially without the encoder's struct definitions."""

    def __init__(self, data):
        require(64 <= len(data) <= MAX_MANIFEST, 'Invalid manifest byte length')
        self.data = data
        self.position = 0

    def take(self, length):
        end = self.position + length
        require(0 <= length and end <= len(self.data), 'Truncated manifest field')
        value = self.data[self.position:end]
        self.position = end
        return value

    def number(self, width):
        return int.from_bytes(self.take(width), 'little')


def verify(data, plan):
    reader = Reader(data)
    require(reader.take(8) == b'OGTMF001', 'Unexpected manifest magic')
    require(tuple(reader.number(4) for _ in range(4)) == (ROWS, FILES, DIRECTORIES, SYMLINKS)
            and reader.number(8) == LOGICAL_BYTES
            and reader.take(32).hex() == PLAN_SHA, 'Unexpected manifest header counts or plan pin')
    directories = {node.path: 2 for node in plan.values() if node.kind == 'directory'}
    for path in directories:
        if path:
            directories[path[:-1]] += 1
    expected = {b'/'.join(node.path): node for node in plan.values()}
    require(len(expected) == ROWS == len(plan), 'Plan paths do not produce a unique native namespace')
    logical_bytes = 0
    counts = [0, 0, 0]
    path_bytes = component_bytes = depth = link_bytes = 0
    xattr_name_bytes = xattr_value_bytes = max_record_bytes = 0
    previous = None
    for _ in range(ROWS):
        start = reader.position
        length = reader.number(2)
        kind, attr_count = reader.number(1), reader.number(1)
        mode, target_length = reader.number(2), reader.number(2)
        uid, gid, links = reader.number(4), reader.number(4), reader.number(4)
        size = reader.number(8)
        require(length <= 4095 and kind in (1, 2, 3) and 1 <= attr_count <= 2 and mode <= 0o7777,
                'Outside native record limits')
        path = reader.take(length)
        parts = path.split(b'/') if path else []
        require(len(parts) <= 128 and all(1 <= len(part) <= 255 and part not in (b'.', b'..')
                                         and b'\0' not in part for part in parts), 'Noncanonical raw path')
        require((previous is None and path == b'') or (previous is not None and previous < path),
                'Missing root, duplicate path or out-of-order records')
        previous = path
        node = expected.pop(path, None)
        require(node is not None and node.kind == ('directory', 'file', 'symlink')[kind - 1],
                'Unexpected raw path or object type')
        require((uid, gid, mode) == (node.uid, node.gid, node.mode)
                and links == (directories[node.path] if kind == 1 else 1), 'Native metadata differs from plan')
        require(size == (0 if kind == 1 else node.size), 'Unexpected native logical length')
        require(target_length == (node.size if kind == 3 else 0) and target_length <= 4095,
                'Unexpected native symlink length')
        if kind == 2:
            require(reader.take(32).hex() == node.payload['sha256'], 'Native content digest differs')
            logical_bytes += size
        elif kind == 3:
            require(reader.take(target_length) == node.target, 'Native symlink payload differs')
        attrs = []
        for _ in range(attr_count):
            name_len, value_len = reader.number(2), reader.number(2)
            require(1 <= name_len <= 255 and 1 <= value_len <= 1024, 'Outside native xattr byte limits')
            name, value = reader.take(name_len), reader.take(value_len)
            require(not attrs or attrs[-1][0] < name, 'Duplicate or unsorted xattr name')
            attrs.append((name, value))
            xattr_name_bytes = max(xattr_name_bytes, name_len)
            xattr_value_bytes = max(xattr_value_bytes, value_len)
        require(tuple(attrs) == node.attrs, 'Native xattrs differ from plan')
        counts[kind - 1] += 1
        path_bytes = max(path_bytes, length)
        component_bytes = max(component_bytes, *(len(part) for part in parts), 0)
        depth = max(depth, len(parts))
        link_bytes = max(link_bytes, target_length)
        max_record_bytes = max(max_record_bytes, reader.position - start)
    require(not expected and reader.position == len(data) and logical_bytes == LOGICAL_BYTES
            and counts == [DIRECTORIES, FILES, SYMLINKS], 'Incomplete native coverage or trailing bytes')
    return {'rows': ROWS, 'directories': counts[0], 'files': counts[1], 'symlinks': counts[2],
            'logicalBytes': logical_bytes, 'maxRecordBytes': max_record_bytes, 'maxPathBytes': path_bytes,
            'maxComponentBytes': component_bytes, 'maxDepth': depth,
            'maxLinkBytes': link_bytes, 'maxXattrNameBytes': xattr_name_bytes,
            'maxXattrValueBytes': xattr_value_bytes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-run', help='Read back an existing run r-<8 lowercase hex digits>')
    args = parser.parse_args()
    plan, _, _ = load_plan()
    if args.verify_run is not None:
        require(re.fullmatch(r'r-[0-9a-f]{8}', args.verify_run), 'Invalid run locator')
        data = source.read_small(OUT / args.verify_run / 'manifest.bin', MAX_MANIFEST)
        print(json.dumps(verify(data, plan), sort_keys=True))
        return
    data = encode()
    stats = verify(data, plan)
    source.plain(OUT)
    OUT.mkdir(exist_ok=True)
    job = OUT / f'r-{uuid.uuid4().hex[:8]}'
    job.mkdir()
    manifest = job / 'manifest.bin'
    with manifest.open('xb') as output:
        require(output.write(data) == len(data), 'Short native manifest write')
    saved = source.read_small(manifest, MAX_MANIFEST, hashlib.sha256(data).hexdigest())
    require(saved == data, 'Native manifest readback differs')
    receipt = {
        'schema': 'oneos-guest-tree-native-manifest/v1',
        'status': 'PASS_SELECTED_PLAN_NATIVE_MANIFEST_ONLY',
        'toolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'plan': {'path': PLAN.relative_to(ROOT).as_posix(), 'bytes': PLAN_BYTES, 'sha256': PLAN_SHA,
                 'receiptSha256': RECEIPT_SHA},
        'manifest': {'path': 'manifest.bin', 'bytes': len(saved), 'sha256': hashlib.sha256(saved).hexdigest(), **stats},
        'writerExclusionEstablished': False, 'destinationReadbackVerified': False, 'stageEligible': False,
    }
    with (job / 'receipt.json').open('x', encoding='utf-8', newline='\n') as output:
        output.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(job / 'receipt.json')


if __name__ == '__main__':
    main()
