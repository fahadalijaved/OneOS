"""Materialize the selected donor plan into a fresh private Linux repo directory."""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

import check_guest_tree_materialization_plan as source
from probe_guest_tree_pc_materializer import anchored_name, directory_at, named_identity, open_fd, read_attrs


ROOT = Path(__file__).absolute().parents[1]
OUT = ROOT / 'out/guest-tree-materializer'
PLAN_RUN = ROOT / 'out/guest-tree-materialization-plan/r-b4e075c2'
RECEIPT_SHA = '1e00a9deff87625902fadd54d955a3cce52a3617f9703974956cdada531bac95'
PLAN_SHA = '0786e4682f7ac2f7b20e99154baa72baa289a03b8cafe22c6a0db37c36b3b259'
IMAGE_NAME = b'OneOS_ColorOS17_FindX9Ultra_IN_Full.img'
CHUNK = 1024 * 1024
ZERO = bytes(CHUNK)
DIR = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
KIND = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'symlink': stat.S_IFLNK}
require = source.require


@dataclass(frozen=True)
class Node:
    path: tuple
    kind: str
    uid: int
    gid: int
    mode: int
    size: int
    attrs: tuple
    target: bytes | None
    payload: dict | None


def payload_profile(payload, size, limit):
    source.keys(payload, 'sha256 ranges')
    digest, ranges = payload['sha256'], payload['ranges']
    require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid payload digest')
    require(isinstance(ranges, list) and len(ranges) <= 65536, 'Invalid payload range count')
    cursor, counts = 0, Counter(data=0, hole=0, unwritten=0)
    for row in ranges:
        require(isinstance(row, dict) and row.get('kind') in ('data', 'hole', 'unwritten'), 'Invalid payload range kind')
        kind = row['kind']
        source.keys(row, 'kind fileOffset bytes imageOffset' if kind == 'data' else 'kind fileOffset bytes')
        require(source.integer(row['fileOffset'], 0, size) == cursor, 'Payload ranges are not contiguous')
        count = source.integer(row['bytes'], 1, size - cursor)
        if kind == 'data':
            offset = source.integer(row['imageOffset'], 0, limit - count)
            require(offset % source.BLOCK == 0, 'Data range does not start at an ext4 block')
        counts[kind] += count
        cursor += count
    require(cursor == size and (size != 0 or digest == source.sha(b'')), 'Incomplete logical payload')
    return counts


def load_plan():
    receipt = source.decode(source.read_small(PLAN_RUN / 'receipt.json', 5951, RECEIPT_SHA))
    require(receipt['schema'] == 'oneos-guest-tree-materialization-plan/v1' and receipt['destinationEligible'] is False,
            'Unexpected source plan status')
    require(receipt['plan']['path'] == (PLAN_RUN / 'plan.jsonl').relative_to(ROOT).as_posix()
            and receipt['plan']['sha256'] == PLAN_SHA and receipt['plan']['bytes'] == 8490653, 'Unexpected plan identity')
    img = receipt['sourceImage']
    require(img['path'] == '../firmware/donor/' + IMAGE_NAME.decode('ascii')
            and img['bytes'] == source.SOURCE_BYTES and img['sha256'] == source.IMAGE_SHA, 'Unexpected image identity')
    raw = source.read_small(PLAN_RUN / 'plan.jsonl', receipt['plan']['bytes'], PLAN_SHA)
    metadata, extras = [], {}
    for row in source.json_lines(raw):
        mode, payload = row.pop('destinationMode'), row.pop('fileSource')
        path = source.raw_path(row['pathB64'])
        require(path not in extras, 'Duplicate raw plan path')
        metadata.append(row)
        extras[path] = (mode, payload)
    census = source.metadata(source.encode_lines(metadata))
    plan, counts = {}, Counter()
    for path, row in census.items():
        mode, payload = extras[path]
        kind = row['kind']
        require(type(mode) is int and mode == (0o777 if kind == 'symlink' else row['mode']), 'Unselected mode change')
        if kind == 'file':
            counts.update(payload_profile(payload, row['size'], source.FS_BYTES))
        else:
            require(payload is None, 'Non-file entry contains data ranges')
        attrs = tuple((source.encoded_bytes(p['nameB64'], 255), source.encoded_bytes(p['valueB64'], 1024))
                      for p in row['xattrs'])
        target = source.encoded_bytes(row['symlinkTargetB64'], 4095) if kind == 'symlink' else None
        plan[path] = Node(path, kind, row['uid'], row['gid'], mode, row['size'], attrs, target, payload)
    require(counts == {'data': receipt['sourceTotals']['dataBytes'], 'hole': receipt['sourceTotals']['holeBytes'],
                       'unwritten': receipt['sourceTotals']['unwrittenBytes']}, 'Payload accounting differs from receipt')
    return dict(sorted(plan.items(), key=lambda item: (len(item[0]), item[0]))), img, counts


def hash_stream(read_at, size):
    digest = hashlib.sha256()
    for offset in range(0, size, CHUNK):
        count = min(CHUNK, size - offset)
        chunk = read_at(offset, count)
        require(len(chunk) == count, 'Short stream read')
        digest.update(chunk)
    return digest.hexdigest()


def emit_payload(payload, read_at, write_at):
    digest = hashlib.sha256()
    for row in payload['ranges']:
        is_data = row['kind'] == 'data'
        for relative in range(0, row['bytes'], CHUNK):
            count = min(CHUNK, row['bytes'] - relative)
            if is_data:
                chunk = read_at(row['imageOffset'] + relative, count)
                require(len(chunk) == count, 'Short image range read')
                write_at(row['fileOffset'] + relative, chunk)
            else:
                chunk = ZERO[:count]
            digest.update(chunk)
    require(digest.hexdigest() == payload['sha256'], 'Logical source file digest differs')


def write_at(fd, offset, raw):
    remaining = memoryview(raw)
    while remaining:
        written = os.pwrite(fd, remaining, offset)
        require(written > 0, 'Zero-progress write')
        offset += written
        remaining = remaining[written:]


def finalize_metadata(fd, node):
    os.fchown(fd, node.uid, node.gid)
    os.fchmod(fd, node.mode)
    # Preserve capability bytes after content, ownership, mode and other xattrs.
    for key, value in sorted(node.attrs, key=lambda attr: attr[0] == b'security.capability'):
        os.setxattr(fd, key, value)
    os.fsync(fd)


def build_tree(tree, plan, read_image, root_mount):
    for path, node in plan.items():
        if not path:
            continue
        with directory_at(tree, path[:-1]) as parent:
            require(mount_id(parent) == root_mount, 'Destination parent mount crossing before write')
            name = path[-1]
            if node.kind == 'directory':
                os.mkdir(name, 0o700, dir_fd=parent)
            elif node.kind == 'symlink':
                os.symlink(node.target, name, dir_fd=parent)
                os.chown(name, node.uid, node.gid, dir_fd=parent, follow_symlinks=False)
                for key, value in node.attrs:
                    os.setxattr(anchored_name(parent, name), key, value, follow_symlinks=False)
            else:
                with open_fd(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, parent=parent) as fd:
                    require(mount_id(fd) == root_mount, 'Destination file mount crossing before write')
                    emit_payload(node.payload, read_image, lambda offset, chunk: write_at(fd, offset, chunk))
                    os.ftruncate(fd, node.size)
                    finalize_metadata(fd, node)
    for path, node in reversed(list(plan.items())):
        if node.kind == 'directory':
            with directory_at(tree, path) as fd:
                require(mount_id(fd) == root_mount, 'Destination directory mount crossing before metadata')
                finalize_metadata(fd, node)


def mount_id(fd):
    with open(f'/proc/self/fdinfo/{fd}', 'rb') as stream:
        raw = stream.read(8193)
    require(raw.endswith(b'\n') and len(raw) <= 8192, 'Invalid fdinfo read')
    ids = re.findall(rb'^mnt_id:[ \t]+([0-9]{1,20})$', raw, re.MULTILINE)
    require(len(ids) == 1 and int(ids[0]) > 0, 'Missing exact held mount identity')
    return int(ids[0])


def verify_metadata(node, s, attrs):
    require((stat.S_IFMT(s.st_mode), stat.S_IMODE(s.st_mode), s.st_uid, s.st_gid, attrs) ==
            (KIND[node.kind], node.mode, node.uid, node.gid, node.attrs), f'Destination metadata differs: {node.path!r}')
    if node.kind != 'directory':
        require(s.st_nlink == 1 and s.st_size == node.size, f'Destination link count or size differs: {node.path!r}')


def verify_tree(tree, plan, root_mount):
    device = os.fstat(tree).st_dev
    children = {path: set() for path, node in plan.items() if node.kind == 'directory'}
    seen = set()
    for path in plan:
        if path:
            children[path[:-1]].add(path[-1])
    for path, node in plan.items():
        if node.kind == 'directory':
            with directory_at(tree, path) as fd:
                observed = os.fstat(fd)
                require(mount_id(fd) == root_mount, 'Directory mount crossing')
                require({os.fsencode(name) for name in os.listdir(fd)} == children[path], 'Directory raw-name census differs')
                verify_metadata(node, observed, read_attrs(fd))
                require(named_identity(os.fstat(fd)) == named_identity(observed), 'Directory changed during readback')
        else:
            with directory_at(tree, path[:-1]) as parent:
                name = path[-1]
                observed = os.stat(name, dir_fd=parent, follow_symlinks=False)
                require(stat.S_IFMT(observed.st_mode) == KIND[node.kind], 'Destination named type differs')
                flags = os.O_PATH if node.kind == 'symlink' else os.O_RDONLY | os.O_NONBLOCK
                with open_fd(name, flags, parent=parent) as fd:
                    expected = named_identity(observed)
                    require(named_identity(os.fstat(fd)) == expected and mount_id(fd) == root_mount,
                            'Named and held destination differ')
                    if node.kind == 'symlink':
                        attrs = read_attrs(anchored_name(parent, name), nofollow=True)
                        require(os.readlink(name, dir_fd=parent) == node.target, 'Destination symlink bytes differ')
                    else:
                        attrs = read_attrs(fd)
                        require(hash_stream(lambda offset, count: os.pread(fd, count, offset), node.size) == node.payload['sha256'],
                                f'Destination content digest differs: {path!r}')
                    verify_metadata(node, observed, attrs)
                    require(named_identity(os.fstat(fd)) == expected and
                            named_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                            'Destination identity changed during readback')
        require(observed.st_dev == device and observed.st_ino not in seen, 'Unexpected device or inode alias')
        seen.add(observed.st_ino)


def check_linux_runtime():
    require(sys.platform.startswith('linux') and os.geteuid() == 0 and hasattr(os, 'O_PATH'), 'Linux root runtime required')


def materialize(plan, image, counts, result):
    check_linux_runtime()
    # Resolve each known repository component from an actual held filesystem root.
    workspace = tuple(os.fsencode(p) for p in ROOT.parent.parts[1:])
    repo_name = os.fsencode(ROOT.name)
    with open_fd(b'/', DIR) as slash, directory_at(slash, workspace) as work:
        with directory_at(work, (b'firmware', b'donor')) as image_parent:
            with open_fd(IMAGE_NAME, os.O_RDONLY | os.O_NONBLOCK, parent=image_parent) as fd:
                def held_image():
                    held = os.fstat(fd)
                    named = os.stat(IMAGE_NAME, dir_fd=image_parent, follow_symlinks=False)
                    require(stat.S_ISREG(held.st_mode) and held.st_size == image['bytes']
                            and named_identity(held) == named_identity(named), 'Held donor image differs from fixed name')
                    return named_identity(held)

                original = held_image()
                read_image = lambda offset, count: os.pread(fd, count, offset)
                require(hash_stream(read_image, image['bytes']) == image['sha256'] and held_image() == original,
                        'Fresh whole donor digest or identity differs')
                result['wholeImageHashVerified'] = True
                with directory_at(work, (repo_name, b'out')) as out_fd:
                    try:
                        os.mkdir(OUT.name, 0o700, dir_fd=out_fd)
                    except FileExistsError:
                        pass
                    with open_fd(OUT.name, DIR, parent=out_fd) as jobs:
                        own = os.fstat(jobs)
                        require(own.st_uid == 0 and not own.st_mode & 0o022, 'Output parent is not root-protected')
                        volume = os.fstatvfs(jobs)
                        require(volume.f_bavail * volume.f_frsize >= counts['data'], 'Insufficient destination capacity for file data')
                        name = 'run-' + uuid.uuid4().hex[:12]
                        os.mkdir(name, 0o700, dir_fd=jobs)
                        result['privateRun'] = (OUT / name).relative_to(ROOT).as_posix()
                        with open_fd(name, DIR, parent=jobs) as run:
                            private = os.fstat(run)
                            require(private.st_uid == 0 and stat.S_IMODE(private.st_mode) == 0o700 and
                                    mount_id(run) == mount_id(jobs), 'New run is not an owned private directory')
                            os.mkdir('tree', 0o700, dir_fd=run)
                            with open_fd('tree', DIR, parent=run) as tree:
                                root_mount = mount_id(tree)
                                require(root_mount == mount_id(run), 'Tree mount differs from private run')
                                build_tree(tree, plan, read_image, root_mount)
                                verify_tree(tree, plan, root_mount)
                                require(held_image() == original, 'Donor changed during tree creation')
                                require(named_identity(os.fstat(tree)) ==
                                        named_identity(os.stat('tree', dir_fd=run, follow_symlinks=False)),
                                        'Named tree differs from held tree')
                            os.fsync(run)
                        os.fsync(jobs)
    result['linuxDestinationRoundtripVerified'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-plan', action='store_true')
    modes.add_argument('--materialize', action='store_true')
    args = parser.parse_args()
    result = {'status': 'HOLD', 'planSha256': PLAN_SHA, 'wholeImageHashVerified': False,
              'linuxDestinationRoundtripVerified': False, 'runtimeTreePublished': False}
    try:
        if args.materialize:
            check_linux_runtime()
        plan, image, counts = load_plan()
        result.update(entries=len(plan), dataBytes=counts['data'], zeroBytes=counts['hole'] + counts['unwritten'])
        if args.materialize:
            materialize(plan, image, counts, result)
        result['status'] = 'PASS_PRIVATE_LINUX_TREE_READBACK_ONLY' if args.materialize else 'PASS_SELECTED_PLAN_ONLY'
    except (OSError, ValueError, RecursionError) as exc:
        result['reason'] = str(exc)
    print(json.dumps(result, indent=2))
    return 1 if result['status'] == 'HOLD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
