"""Join held donor metadata and payload proofs without creating a guest tree."""

import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid


ROOT = Path(__file__).absolute().parents[1]
OUT = ROOT / 'out/guest-tree-materialization-plan'
CENSUS = 'out/guest-tree-ext4-census/r-55e26da9/receipt.json'
CENSUS_SHA = '1013a572c13ecf439b4fd2e5f1f5ab5e8d178de8304d329de511924b2571a81c'
NAMESPACE_SHA = '124ad42d7de69bdd5691ce189bd5a48eb7c5d2d05727ca748312c60fafe27919'
CONTENT = 'out/guest-tree-ext4-census/r-25def22b/receipt.json'
CONTENT_SHA = '82b3c23b3566b05a135bc0b0328306d0594455afff98f17d4cecbf44b305e233'
PAYLOAD_SHA = '86870dccde1cebd8620400200b018d0b0e6f2bc3fd8ee7cfc0e54aa30e708691'
POLICY = 'out/guest-tree-toolchain-admission/NORMALIZATION.json'
POLICY_SHA = 'bf7971bb7f25eebdc38bb798e7d40b53f708355ea7f58cef24ffdfe65169cd5b'
SOURCE_BYTES = 14669168640
FS_BYTES = 14554550272
IMAGE_SHA = '92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6'
BLOCK = 4096
EXPECTED_KINDS = {'directory': 3381, 'file': 11864, 'symlink': 329}
LINK_MODE_COUNTS = {0o644: 102, 0o750: 1, 0o755: 226}
SAMPLES = {
    'system/bin/app_process64': (51880, '78d3bf52333a151a6f4859f5144de5578adf009503b792a91db307435a0f21dc'),
    'system/bin/run-as': (51568, 'ce561d010bd4c75d2ef83906f8de3996f9beef841b3872cfc88a2e886c2eef90'),
    'system/etc/linker.config.pb': (1207, 'f9782b93cc1e7bd9989fd145380850ff2df5196cb1a314b6a8a41fe78eec076c'),
    'init.environ.rc.patch': (0, hashlib.sha256(b'').hexdigest()),
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path, raw):
    return {'path': os.path.relpath(path, ROOT).replace('\\', '/'), 'bytes': len(raw), 'sha256': sha(raw)}


def integer(value, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum, 'Out-of-range source integer')
    return value


def keys(value, names):
    require(isinstance(value, dict) and value.keys() == set(names.split()), 'Unexpected source fields')


def unique(items):
    obj = dict(items)
    require(len(obj) == len(items), 'Duplicate JSON key')
    return obj


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique)


def encoded_bytes(text, maximum):
    require(isinstance(text, str) and len(text) <= 4 * ((maximum + 2) // 3), 'Oversized base64')
    raw = base64.b64decode(text, validate=True)
    require(len(raw) <= maximum and base64.b64encode(raw).decode('ascii') == text, 'Noncanonical base64')
    return raw


def raw_path(parts):
    require(isinstance(parts, list) and len(parts) <= 128, 'Invalid path depth')
    raw = tuple(encoded_bytes(part, 255) for part in parts)
    require(all(p not in (b'', b'.', b'..') and b'/' not in p and b'\0' not in p for p in raw), 'Unsafe raw path')
    return raw


def plain(path):
    for part in (path, *path.parents):
        if part == ROOT.parent:
            break
        require(not part.is_symlink() and not getattr(part, 'is_junction', lambda: False)(), 'Reparse path refused')
    return path


def read_small(path, limit, expected=None):
    path = plain(path)
    require(stat.S_ISREG(path.lstat().st_mode), 'Expected ordinary saved input')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit and (expected is None or sha(raw) == expected), f'Input length or SHA mismatch: {path}')
    return raw


def json_lines(raw):
    require(raw.endswith(b'\n') and b'\r' not in raw, 'Expected exact LF-delimited source rows')
    return (decode(line) for line in raw[:-1].split(b'\n'))


def metadata(raw):
    rows, inodes, modes, kinds, attributes = {}, set(), Counter(), Counter(), Counter()
    for row in json_lines(raw):
        keys(row, 'pathB64 inode kind uid gid mode size nlink hardlinkGroup xattrs symlinkTargetB64')
        path = raw_path(row['pathB64'])
        inode = integer(row['inode'], 1, 2**32 - 1)
        require(path not in rows and inode not in inodes and row['hardlinkGroup'] is None,
                'Unexpected duplicate path or shared inode in selected donor')
        kind = row['kind']
        require(kind in EXPECTED_KINDS, 'Unexpected donor object type')
        for key in ('uid', 'gid'):
            integer(row[key], 0, 2**32 - 1)
        mode = integer(row['mode'], 0, 0o7777)
        size = integer(row['size'], 0, FS_BYTES)
        links = integer(row['nlink'], 1, 65535)
        require(kind == 'directory' or links == 1, 'Non-directory link count differs from census')
        if kind == 'symlink':
            link = encoded_bytes(row['symlinkTargetB64'], 4095)
            require(link and b'\0' not in link and len(link) == size and mode in LINK_MODE_COUNTS, 'Symlink profile differs')
            modes[mode] += 1
        else:
            require(row['symlinkTargetB64'] is None, 'Nonlink has a link payload')
        require(isinstance(row['xattrs'], list) and 1 <= len(row['xattrs']) <= 2, 'Unexpected donor xattr cardinality')
        names = []
        for pair in row['xattrs']:
            keys(pair, 'nameB64 valueB64')
            name = encoded_bytes(pair['nameB64'], 255)
            require(name == b'security.selinux' or (name == b'security.capability' and kind == 'file'), 'Unexpected xattr')
            require(encoded_bytes(pair['valueB64'], 65536), 'Missing xattr bytes')
            names.append(name)
            attributes[name] += 1
        require(names == sorted(set(names)) and b'security.selinux' in names, 'Missing SELinux attr or ambiguous xattrs')
        kinds[kind] += 1
        inodes.add(inode)
        rows[path] = row
    require(kinds == EXPECTED_KINDS and modes == LINK_MODE_COUNTS
            and attributes == {b'security.selinux': 15574, b'security.capability': 2}, 'Exact census totals differ')
    require(rows[()]['kind'] == 'directory' and all(not p or p[:-1] in rows and rows[p[:-1]]['kind'] == 'directory'
                                                    for p in rows), 'Invalid directory ancestry')
    return rows


def runs_for(extents, size):
    """Convert ext4 extents to bounded logical reads and zero fills."""
    require(isinstance(extents, list), 'Missing ext4 extent list')
    output = []
    last_block = 0
    cursor = 0

    def add(kind, end, image_offset=None):
        nonlocal cursor
        if end > cursor:
            row = {'kind': kind, 'fileOffset': cursor, 'bytes': end - cursor}
            if image_offset is not None:
                row['imageOffset'] = image_offset
            output.append(row)
            cursor = end

    for extent in extents:
        require(isinstance(extent, list) and len(extent) == 4, 'Invalid extent tuple')
        logical, physical, blocks, initialized = extent
        integer(logical, last_block, 2**32 - 1)
        integer(physical, 1, FS_BYTES // BLOCK - 1)
        integer(blocks, 1, 32768)
        require(type(initialized) is bool and physical + blocks <= FS_BYTES // BLOCK and logical + blocks <= 2**32
                and (initialized or blocks < 32768), 'Extent outside admitted bounds')
        last_block = logical + blocks
        add('hole', min(logical * BLOCK, size))
        add('data' if initialized else 'unwritten', min(last_block * BLOCK, size), physical * BLOCK if initialized else None)
    add('hole', size)
    return output


def join(namespace, raw):
    files = {path: row for path, row in namespace.items() if row['kind'] == 'file'}
    mappings, physical_reads = {}, []
    totals = Counter()
    for row in json_lines(raw):
        keys(row, 'pathB64 inode size sha256 dataBytes zeroBytes extents')
        path = raw_path(row['pathB64'])
        require(path in files and path not in mappings, 'Payload row missing census path or duplicated')
        source = files[path]
        size = integer(row['size'], 0, FS_BYTES)
        require(size == source['size'] and integer(row['inode'], 1, 2**32 - 1) == source['inode'],
                'Payload inode or size differs from census')
        require(isinstance(row['sha256'], str) and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Invalid payload SHA')
        if size == 0:
            require(row['sha256'] == sha(b''), 'Empty-file payload SHA differs')
        runs = runs_for(row['extents'], size)
        data = sum(run['bytes'] for run in runs if run['kind'] == 'data')
        zero = sum(run['bytes'] for run in runs if run['kind'] != 'data')
        require(data == integer(row['dataBytes'], 0, size) and zero == integer(row['zeroBytes'], 0, size)
                and data + zero == size, 'Payload range accounting differs')
        physical_reads.extend((run['imageOffset'], run['imageOffset'] + run['bytes']) for run in runs if run['kind'] == 'data')
        mappings[path] = {'sha256': row['sha256'], 'ranges': runs}
        totals.update(files=1, logicalBytes=size, dataBytes=data, zeroBytes=zero, emptyFiles=int(size == 0),
                      holeBytes=sum(r['bytes'] for r in runs if r['kind'] == 'hole'),
                      unwrittenBytes=sum(r['bytes'] for r in runs if r['kind'] == 'unwritten'))
    require(list(mappings) == list(files), 'Incomplete or reordered regular-file payload closure')
    last = 0
    for start, end in sorted(physical_reads):
        require(last <= start < end <= FS_BYTES, 'Overlapping or out-of-bounds donor data ranges')
        last = end
    return mappings, dict(totals)


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def compare_samples(image, named_pin, payloads):
    samples = []
    named = identity(plain(image).lstat())
    require(list(named) == named_pin and stat.S_ISREG(image.lstat().st_mode), 'Donor named identity differs')
    with image.open('rb', buffering=0) as stream:
        held = identity(os.fstat(stream.fileno()))
        require(held[:4] == named[:4], 'Named/held donor identity differs')
        for name, (size, expected) in SAMPLES.items():
            extracted = ROOT.parent / 'firmware/donor/extracted' / name
            raw = read_small(extracted, size, expected)
            require(len(raw) == size, 'Independent extraction length differs')
            mapped = payloads[tuple(name.encode('ascii').split(b'/'))]
            found = bytearray()
            for row in mapped['ranges']:
                count = row['bytes']
                require(len(found) + count <= size, 'Sample exceeds its bound')
                if row['kind'] == 'data':
                    stream.seek(row['imageOffset'])
                    chunk = stream.read(count)
                    require(len(chunk) == count, 'Short sampled image read')
                else:
                    chunk = bytes(count)
                found.extend(chunk)
            require(found == raw and mapped['sha256'] == expected, f'Independent payload sample differs: {name}')
            samples.append(pin(extracted, raw) | {'imageRanges': mapped['ranges']})
        require(identity(os.fstat(stream.fileno())) == held, 'Donor held identity changed during sampling')
    require(identity(image.lstat()) == named, 'Donor named identity changed during sampling')
    return samples


def encode_lines(rows):
    return b''.join(json.dumps(row, separators=(',', ':'), ensure_ascii=True).encode('ascii') + b'\n' for row in rows)


def prepare():
    census_path, content_path, policy_path = (ROOT / p for p in (CENSUS, CONTENT, POLICY))
    census_raw = read_small(census_path, 16384, CENSUS_SHA)
    content_raw = read_small(content_path, 16384, CONTENT_SHA)
    policy_raw = read_small(policy_path, 16384, POLICY_SHA)
    census, content = decode(census_raw), decode(content_raw)
    require(census['schema'] == 'guest-tree-ext4-census/v1' and census['status'] == 'PASS_ROOT_REACHABLE_EXT4_METADATA_CENSUS'
            and content['schema'] == 'guest-tree-ext4-payload-hashes/v1'
            and content['status'] == 'PASS_ALL_ROOT_REACHABLE_REGULAR_PAYLOAD_HASHES'
            and census['imageIdentityStable'] is True and content['imageIdentityStable'] is True
            and census['filesystemBytes'] == content['filesystemBytes'] == FS_BYTES
            and census['sourcePins'] == content['sourcePins'] and census['image'] == content['image'], 'Source receipts disagree')
    image = census['image']
    require(image['path'] == '../firmware/donor/OneOS_ColorOS17_FindX9Ultra_IN_Full.img'
            and image['sha256'] == IMAGE_SHA and image['bytes'] == SOURCE_BYTES
            and image['wholeHashRecomputed'] is False, 'Donor image profile differs')
    census_map, payload_map = census['namespace'], content['payloads']
    require(census_map['path'] == 'namespace.jsonl' and census_map['sha256'] == NAMESPACE_SHA
            and census_map['bytes'] == 5132484 and census_map['kinds'] == EXPECTED_KINDS
            and census_map['paths'] == census_map['uniqueInodes'] == 15574 and census_map['hardlinkGroups'] == 0,
            'Census namespace profile differs')
    require(payload_map['path'] == 'payloads.jsonl' and payload_map['sha256'] == PAYLOAD_SHA
            and payload_map['bytes'] == 3458110 and payload_map['extentBlockBytes'] == BLOCK
            and payload_map['extentFields'] == ['logicalBlock', 'physicalBlock', 'blocks', 'initialized'],
            'Payload map profile differs')
    namespace_path = census_path.with_name('namespace.jsonl')
    payload_path = content_path.with_name('payloads.jsonl')
    expected_namespace = {'receiptPath': CENSUS, 'receiptSha256': CENSUS_SHA,
                          'path': namespace_path.relative_to(ROOT).as_posix(), 'sha256': NAMESPACE_SHA,
                          'bytes': census_map['bytes']}
    require(content['namespaceSource'] == expected_namespace, 'Payload result does not bind this census')
    namespace_raw = read_small(namespace_path, census_map['bytes'], NAMESPACE_SHA)
    payload_raw = read_small(payload_path, payload_map['bytes'], PAYLOAD_SHA)
    namespace = metadata(namespace_raw)
    mappings, totals = join(namespace, payload_raw)
    require(all(totals[key] == payload_map[key] for key in totals), 'Joined accounting differs from payload receipt')
    samples = compare_samples(ROOT / image['path'], image['namedFileIdentity'], mappings)
    output = encode_lines(row | {'destinationMode': 0o777 if row['kind'] == 'symlink' else row['mode'],
                                 'fileSource': mappings.get(path)} for path, row in namespace.items())
    pins = [(census_path, census_raw), (content_path, content_raw), (namespace_path, namespace_raw),
            (payload_path, payload_raw), (policy_path, policy_raw)]
    require(all(read_small(path, len(raw), sha(raw)) == raw for path, raw in pins), 'Saved source changed during join')
    receipt = {
        'schema': 'oneos-guest-tree-materialization-plan/v1',
        'status': 'PASS_SOURCE_MAPPING_ONLY_DESTINATION_UNVERIFIED',
        'inputs': [pin(path, raw) for path, raw in pins],
        'sourceImage': image,
        'sourceTotals': totals | {'kinds': EXPECTED_KINDS},
        'independentExtractionComparisons': samples,
        'independentImageDataBytesRead': sum(r['bytes'] for s in samples for r in s['imageRanges'] if r['kind'] == 'data'),
        'destinationPolicy': {
            'candidateRoot': '/data/local/tmp/oneos-viewprep/tree',
            'scope': 'Directory, file and symlink rows only. Runtime-owned receivers and mount overlays are separate.',
            'ordinarySymlinkPermissionNormalization': {'0644': '0777', '0750': '0777', '0755': '0777'},
            'requiredExact': ['raw path and type', 'UID and GID', 'mode except enumerated symlink permissions',
                              'regular logical content SHA-256', 'raw symlink payload', 'xattr names and values',
                              'non-directory link identity and count'],
            'dirSizeAndLinkCountAreSourceMetadata': True,
            'unsupported': ['unselected object kinds', 'unvalidated xattr application or effective security policy',
                            'timestamp and physical allocation equivalence'],
        },
        'treeCreated': False,
        'blobsCreated': False,
        'fullContentHashesRecomputed': False,
        'linuxDestinationRoundtripVerified': False,
        'destinationEligible': False,
    }
    return output, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emit-plan', action='store_true', required=True)
    parser.parse_args()
    plan, receipt = prepare()
    plain(OUT).mkdir(exist_ok=True)
    run = plain(OUT / ('r-' + uuid.uuid4().hex[:8]))
    run.mkdir()
    output = run / 'plan.jsonl'
    with output.open('xb') as stream:
        require(stream.write(plan) == len(plan), 'Short plan write')
    require(read_small(output, len(plan), sha(plan)) == plan, 'Plan readback differs')
    receipt['plan'] = pin(output, plan)
    receipt['producer'] = pin(Path(__file__).absolute(), Path(__file__).read_bytes())
    evidence = run / 'receipt.json'
    with evidence.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(pin(evidence, evidence.read_bytes())))


if __name__ == '__main__':
    main()
