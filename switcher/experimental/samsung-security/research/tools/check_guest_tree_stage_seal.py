#!/usr/bin/env python3
"""Independently recheck the selected donor tree in a private Linux materializer run."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from materialize_guest_tree import KIND, PLAN_SHA, load_plan, mount_id
from probe_guest_tree_pc_materializer import anchored_name, directory_at, named_identity, open_fd, read_attrs


ROOT = Path(__file__).absolute().parents[1]
ENTRY_COUNT = 15_574
FILE_COUNT = 11_864
LOGICAL_BYTES = 13_787_452_714
DATA_BYTES = 13_717_051_456
ZERO_BYTES = LOGICAL_BYTES - DATA_BYTES
CHUNK = 1024 * 1024
RECEIPT_LIMIT = 4096
RUN_LOCATOR = re.compile(r'out/guest-tree-materializer/(run-[0-9a-f]{12})')
RECEIPT_KEYS = {
    'status', 'planSha256', 'wholeImageHashVerified', 'linuxDestinationRoundtripVerified',
    'runtimeTreePublished', 'entries', 'dataBytes', 'zeroBytes', 'privateRun',
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique_keys(pairs):
    obj = dict(pairs)
    require(len(obj) == len(pairs), 'Duplicate materializer receipt key')
    return obj


def read_locator(data):
    require(0 < len(data) <= RECEIPT_LIMIT, 'Materializer receipt exceeds byte limit')
    obj = json.loads(data.decode('utf-8'), object_pairs_hook=unique_keys)
    require(isinstance(obj, dict) and obj.keys() == RECEIPT_KEYS, 'Unexpected materializer receipt fields')
    require(obj['status'] == 'PASS_PRIVATE_LINUX_TREE_READBACK_ONLY' and obj['planSha256'] == PLAN_SHA
            and obj['wholeImageHashVerified'] is True and obj['linuxDestinationRoundtripVerified'] is True
            and obj['runtimeTreePublished'] is False, 'Receipt is outside the selected materializer profile')
    for key, expected in (('entries', ENTRY_COUNT), ('dataBytes', DATA_BYTES), ('zeroBytes', ZERO_BYTES)):
        require(type(obj[key]) is int and obj[key] == expected, f'Materializer receipt {key} differs')
    run = obj['privateRun']
    match = RUN_LOCATOR.fullmatch(run) if isinstance(run, str) else None
    require(match is not None, 'Receipt is not a fixed repository materializer run locator')
    return match[1]


def hash_destination(node, read_at):
    """Read all admitted logical ranges. Holes can be physically allocated zeros."""
    digest = hashlib.sha256()
    cursor = 0
    for run in node.payload['ranges']:
        require(run['fileOffset'] == cursor, 'Unaccounted destination range')
        end = cursor + run['bytes']
        require(cursor < end <= node.size, 'Destination range exceeds logical file size')
        while cursor < end:
            count = min(CHUNK, end - cursor)
            data = read_at(cursor, count)
            require(len(data) == count, 'Short destination read')
            if run['kind'] != 'data':
                require(data.count(0) == count, 'Nonzero destination byte in a logical zero range')
            digest.update(data)
            cursor += count
    require(cursor == node.size and digest.hexdigest() == node.payload['sha256'],
            'Destination payload SHA-256 differs from admitted donor bytes')


class TreeReadback:
    def __init__(self, plan, root):
        self.plan = plan
        self.device = os.fstat(root).st_dev
        self.mount = mount_id(root)
        self.seen = set()
        self.children = {path: set() for path, node in plan.items() if node.kind == 'directory'}
        for path in plan:
            if path:
                self.children[path[:-1]].add(path[-1])
        self.files = 0
        self.logical_bytes = 0

    def observe(self, fd, node):
        found = os.fstat(fd)
        require(found.st_dev == self.device and found.st_ino > 0 and mount_id(fd) == self.mount,
                'Destination node crosses backing device or mount')
        require(found.st_ino not in self.seen, 'Destination has an unselected inode alias')
        self.seen.add(found.st_ino)
        actual = (stat.S_IFMT(found.st_mode), stat.S_IMODE(found.st_mode), found.st_uid, found.st_gid)
        require(actual == (KIND[node.kind], node.mode, node.uid, node.gid), 'Destination type, mode or owner differs')
        if node.kind == 'directory':
            links = 2 + sum(self.plan[node.path + (name,)].kind == 'directory'
                            for name in self.children[node.path])
            require(found.st_nlink == links, 'Destination directory link count differs')
        else:
            require(found.st_nlink == 1 and found.st_size == node.size, 'Destination size or link count differs')
        return named_identity(found)

    def names(self, fd, path):
        remaining = self.children[path].copy()
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME
        with open_fd(b'.', flags, parent=fd) as readable:
            require(named_identity(os.fstat(readable)) == named_identity(os.fstat(fd))
                    and mount_id(readable) == self.mount, 'Directory enumeration object differs')
            with os.scandir(readable) as directory:
                for entry in directory:
                    name = os.fsencode(entry.name)
                    require(name in remaining, 'Unexpected or repeated raw directory entry')
                    remaining.remove(name)
        require(not remaining, 'Missing raw directory entry')

    def directory(self, fd, path, node):
        before = self.observe(fd, node)
        require(read_attrs(fd) == node.attrs, 'Destination directory xattrs differ')
        self.names(fd, path)
        for name in sorted(self.children[path]):
            child = path + (name,)
            try:
                self.entry(fd, name, child, self.plan[child])
            except (OSError, ValueError) as exc:
                if isinstance(exc, EntryRefusal):
                    raise
                raise EntryRefusal(f'{child!r}: {exc}') from exc
        self.names(fd, path)
        require(named_identity(os.fstat(fd)) == before and mount_id(fd) == self.mount
                and read_attrs(fd) == node.attrs, 'Directory changed during independent readback')

    def entry(self, parent, name, path, node):
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        require(stat.S_IFMT(before.st_mode) == KIND[node.kind], 'Named entry has wrong type')
        if node.kind == 'directory':
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME
        elif node.kind == 'file':
            flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOATIME
        else:
            flags = os.O_PATH
        with open_fd(name, flags, parent=parent) as fd:
            expected = named_identity(before)
            require(named_identity(os.fstat(fd)) == expected, 'Named and held destination differ')
            if node.kind == 'directory':
                self.directory(fd, path, node)
            else:
                require(self.observe(fd, node) == expected, 'Destination identity changed before content read')
                if node.kind == 'symlink':
                    attrs = read_attrs(anchored_name(parent, name), nofollow=True)
                    require(os.readlink(name, dir_fd=parent) == node.target, 'Destination symlink target differs')
                else:
                    attrs = read_attrs(fd)
                    hash_destination(node, lambda offset, size: os.pread(fd, size, offset))
                    self.files += 1
                    self.logical_bytes += node.size
                require(attrs == node.attrs, 'Destination xattrs differ')
            require(named_identity(os.fstat(fd)) == expected and mount_id(fd) == self.mount
                    and named_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                    'Destination identity changed during independent readback')


class EntryRefusal(ValueError):
    pass


def check_private_run(run, plan):
    require(sys.platform.startswith('linux') and os.geteuid() == 0 and hasattr(os, 'O_NOATIME'),
            'Independent destination readback requires an admitted Linux root runtime')
    root_path = tuple(os.fsencode(part) for part in ROOT.parts[1:])
    directory = os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME
    with open_fd(b'/', directory) as slash, directory_at(slash, root_path) as repo:
        with directory_at(repo, (b'out', b'guest-tree-materializer')) as jobs:
            jobs_stat = os.fstat(jobs)
            require(jobs_stat.st_uid == 0 and not jobs_stat.st_mode & 0o022,
                    'Materializer parent is not root protected')
            run_name = run.encode('ascii')
            with open_fd(run_name, directory, parent=jobs) as run_fd:
                initial = os.fstat(run_fd)
                require(initial.st_uid == 0 and stat.S_IMODE(initial.st_mode) == 0o700
                        and mount_id(run_fd) == mount_id(jobs), 'Materializer run is not the expected private directory')
                with open_fd(b'tree', directory, parent=run_fd) as tree:
                    tree_before = named_identity(os.fstat(tree))
                    audit = TreeReadback(plan, tree)
                    require(audit.mount == mount_id(run_fd)
                            and named_identity(os.stat(b'tree', dir_fd=run_fd, follow_symlinks=False)) == tree_before,
                            'Tree is not the named directory on the run mount')
                    audit.directory(tree, (), plan[()])
                    require(len(audit.seen) == ENTRY_COUNT and audit.files == FILE_COUNT
                            and audit.logical_bytes == LOGICAL_BYTES, 'Independent destination closure differs')
                    require(named_identity(os.fstat(tree)) == tree_before
                            and named_identity(os.stat(b'tree', dir_fd=run_fd, follow_symlinks=False)) == tree_before,
                            'Named tree changed after independent readback')
                require(named_identity(os.fstat(run_fd)) == named_identity(initial)
                        and named_identity(os.stat(run_name, dir_fd=jobs, follow_symlinks=False)) == named_identity(initial),
                        'Named materializer run changed during readback')
    return {'entries': len(audit.seen), 'files': audit.files, 'logicalBytes': audit.logical_bytes,
            'destinationDev': audit.device, 'destinationIno': tree_before[1], 'destinationMountId': audit.mount}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-locator', action='store_true', help='Parse bounded materializer JSON on stdin')
    modes.add_argument('--verify-private-run', action='store_true', help='Read back the repo-private tree located by stdin JSON')
    args = parser.parse_args()
    result = {'schema': 'oneos-guest-tree-stage-readback/v1', 'status': 'HOLD', 'planSha256': PLAN_SHA,
              'destinationReadbackVerified': False, 'writerExclusionEstablished': False, 'stageEligible': False}
    try:
        raw = sys.stdin.buffer.read(RECEIPT_LIMIT + 1)
        run = read_locator(raw)
        result.update(run=run, locatorSha256=hashlib.sha256(raw).hexdigest())
        if args.verify_private_run:
            plan, _, _ = load_plan()
            result.update(check_private_run(run, plan), status='PASS_FRESH_PRIVATE_TREE_READBACK_ONLY',
                          destinationReadbackVerified=True)
        else:
            result['status'] = 'PASS_LOCATOR_SYNTAX_ONLY'
    except (OSError, ValueError, RecursionError) as exc:
        result['reason'] = str(exc)
    print(json.dumps(result, indent=2))
    return 1 if result['status'] == 'HOLD' else 0


if __name__ == '__main__':
    raise SystemExit(main())
