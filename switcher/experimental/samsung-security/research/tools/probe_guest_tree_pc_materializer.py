"""Validate or round-trip a bounded synthetic guest-tree fixture on a PC."""

import argparse
import base64
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid


ROOT = Path(__file__).absolute().parents[1]
BASE = ROOT / 'out/guest-tree-pc-materializer'
SCHEMA = 'oneos-pc-guest-tree-fixture/v1'
LINK_MODES = {0o644, 0o750, 0o755, 0o777}
KINDS = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'symlink': stat.S_IFLNK}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def integer(value, minimum, maximum):
    require(type(value) is int and minimum <= value <= maximum, 'Out-of-range fixture integer')
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unb64(value, maximum):
    require(isinstance(value, str) and len(value) <= 4 * ((maximum + 2) // 3), 'Oversized base64 field')
    raw = base64.b64decode(value, validate=True)
    require(len(raw) <= maximum and base64.b64encode(raw).decode('ascii') == value, 'Noncanonical base64 field')
    return raw


def safe_component(value):
    raw = unb64(value, 255)
    require(raw not in (b'', b'.', b'..') and b'/' not in raw and b'\0' not in raw, 'Unsafe path component')
    return raw


def object_pairs(items):
    obj = dict(items)
    require(len(obj) == len(items), 'Duplicate JSON key')
    return obj


@dataclass(frozen=True)
class Entry:
    path: tuple
    kind: str
    inode: int
    uid: int
    gid: int
    mode: int
    nlink: int
    group: int | None
    attrs: tuple
    body: bytes

    @property
    def expected_mode(self):
        return 0o777 if self.kind == 'symlink' else self.mode


def attributes(rows, kind):
    require(isinstance(rows, list) and len(rows) <= 8, 'Invalid xattr list')
    result = []
    for row in rows:
        require(isinstance(row, dict) and row.keys() == {'nameB64', 'valueB64'}, 'Invalid xattr row')
        name, value = unb64(row['nameB64'], 255), unb64(row['valueB64'], 1024)
        allowed = (b'user.oneos.fixture', b'trusted.oneos.fixture', b'security.selinux', b'security.capability')
        require(name in allowed, 'Outside synthetic xattr profile')
        require(name != b'security.capability' or kind == 'file', 'Capability xattr requires a regular file')
        require(kind != 'symlink' or name == b'security.selinux', 'Outside synthetic symlink xattr profile')
        require(not result or result[-1][0] < name, 'Xattr names must be unique and byte-sorted')
        result.append((name, value))
    return tuple(result)


def entry(row, read_blob):
    require(isinstance(row, dict) and isinstance(row.get('kind'), str) and row['kind'] in KINDS,
            'Unexpected fixture entry kind')
    kind = row['kind']
    keys = set('pathB64 kind inode uid gid mode size nlink hardlinkGroup xattrs'.split())
    keys |= {'sha256'} if kind == 'file' else {'symlinkTargetB64'} if kind == 'symlink' else set()
    require(row.keys() == keys, 'Unexpected fixture entry fields')
    require(isinstance(row['pathB64'], list) and len(row['pathB64']) <= 12, 'Invalid fixture path depth')
    path = tuple(safe_component(component) for component in row['pathB64'])
    inode = integer(row['inode'], 1, 2**63 - 1)
    uid, gid = (integer(row[key], 0, 65535) for key in ('uid', 'gid'))
    mode = integer(row['mode'], 0, 0o7777)
    nlink = integer(row['nlink'], 1, 64)
    size = integer(row['size'], 0, 65536)
    group = row['hardlinkGroup']
    if kind == 'directory' or nlink == 1:
        require(group is None, 'Unexpected hardlink group')
    else:
        require(integer(group, 1, 2**63 - 1) == inode, 'Hardlink group must equal source inode')
    body = b''
    if kind == 'file':
        require(not mode & 0o7111, 'Synthetic regular files must be inert data')
        pin = row['sha256']
        require(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin), 'Invalid blob digest')
        body = read_blob(pin)
        require(len(body) == size and sha(body) == pin, 'Blob bytes differ from manifest')
    if kind == 'symlink':
        body = unb64(row['symlinkTargetB64'], 4095)
        require(body and b'\0' not in body and len(body) == size and mode in LINK_MODES, 'Unsupported symlink payload or mode')
    return Entry(path, kind, inode, uid, gid, mode, nlink, group, attributes(row['xattrs'], kind), body)


def load_plan(raw, read_blob):
    obj = json.loads(raw, object_pairs_hook=object_pairs)
    require(isinstance(obj, dict) and obj.keys() == {'schema', 'entries'} and obj['schema'] == SCHEMA,
            'Only synthetic guest-tree manifests are admitted')
    rows = obj['entries']
    require(isinstance(rows, list) and 1 <= len(rows) <= 64, 'Invalid fixture entry count')
    plan, inodes = {}, {}
    for row in rows:
        item = entry(row, read_blob)
        require(item.path not in plan, 'Duplicate raw fixture path')
        plan[item.path] = item
        inodes.setdefault(item.inode, []).append(item)
    require(() in plan and plan[()].kind == 'directory', 'Missing root directory entry')
    for path in plan:
        require(not path or path[:-1] in plan and plan[path[:-1]].kind == 'directory', 'Missing ordinary fixture parent')
    for family in inodes.values():
        first = family[0]
        if len(family) == 1 and first.group is None:
            continue
        require(first.group is not None and len(family) == first.nlink, 'Incomplete hardlink family')
        require(all((r.kind, r.uid, r.gid, r.mode, r.nlink, r.group, r.attrs, r.body) ==
                    (first.kind, first.uid, first.gid, first.mode, first.nlink, first.group, first.attrs, first.body)
                    for r in family), 'Conflicting shared-inode metadata')
    require(sum(len(item.body) for item in plan.values()) <= 256 * 1024, 'Fixture payload exceeds total bound')
    return dict(sorted(plan.items(), key=lambda kv: (len(kv[0]), kv[0])))


def contained(path):
    require(path.is_relative_to(BASE), 'Expected probe-owned fixture path')
    for current in (path, *path.parents):
        if current == ROOT:
            break
        require(not current.is_symlink() and not getattr(current, 'is_junction', lambda: False)(),
                'Fixture reparse/symlink path refused')
    return path


def read_small(path, limit):
    require(contained(path).is_file(), 'Expected an ordinary fixture input file')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Fixture input exceeds byte bound')
    return raw


@contextmanager
def open_fd(name, flags, *, parent=None, mode=0o600):
    fd = os.open(name, flags | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=parent)
    try:
        yield fd
    finally:
        os.close(fd)


@contextmanager
def directory_at(root_fd, path):
    current = os.dup(root_fd)
    try:
        for component in path:
            new = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            old, current = current, new
            os.close(old)
        yield current
    finally:
        os.close(current)


def anchored_name(parent_fd, name):
    # The proc intermediate component resolves the held parent FD. l* xattr
    # behavior on the last component preserves the link rather than its target.
    return f'/proc/self/fd/{parent_fd}/'.encode('ascii') + name


def set_metadata(item, fd):
    os.fchown(fd, item.uid, item.gid)
    os.fchmod(fd, item.expected_mode)
    for name, value in item.attrs:
        os.setxattr(fd, name, value)


def build_tree(tree_fd, plan):
    first_paths = {}
    for path, item in plan.items():
        if not path:
            continue
        with directory_at(tree_fd, path[:-1]) as parent:
            name = path[-1]
            if item.kind == 'directory':
                os.mkdir(name, 0o700, dir_fd=parent)
            elif item.group is not None and item.group in first_paths:
                original = first_paths[item.group]
                with directory_at(tree_fd, original[:-1]) as source:
                    os.link(original[-1], name, src_dir_fd=source, dst_dir_fd=parent, follow_symlinks=False)
            elif item.kind == 'symlink':
                os.symlink(item.body, name, dir_fd=parent)
                os.chown(name, item.uid, item.gid, dir_fd=parent, follow_symlinks=False)
                for key, value in item.attrs:
                    os.setxattr(anchored_name(parent, name), key, value, follow_symlinks=False)
            else:
                with open_fd(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, parent=parent) as fd:
                    data = memoryview(item.body)
                    while data:
                        count = os.write(fd, data)
                        require(count > 0, 'Zero-progress fixture write')
                        data = data[count:]
                    set_metadata(item, fd)
            if item.group is not None:
                first_paths.setdefault(item.group, path)
    for path, item in reversed(list(plan.items())):
        if item.kind == 'directory':
            with directory_at(tree_fd, path) as fd:
                set_metadata(item, fd)


def read_attrs(target, nofollow=False):
    keys = [os.fsencode(key) for key in os.listxattr(target, follow_symlinks=not nofollow)]
    require(len(keys) <= 8, 'Unexpected actual xattr count')
    result = []
    for key in sorted(keys):
        value = os.getxattr(target, key, follow_symlinks=not nofollow)
        require(len(value) <= 1024, 'Actual xattr exceeds bound')
        result.append((key, value))
    return tuple(result)


def actual_row(s, attrs, body):
    return {'kind': stat.S_IFMT(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid, 'mode': stat.S_IMODE(s.st_mode),
            'identity': (s.st_dev, s.st_ino), 'nlink': s.st_nlink, 'attrs': attrs, 'body': body}


def named_identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink, s.st_size, s.st_ctime_ns, s.st_mtime_ns)


def read_tree(tree_fd, plan):
    root_dev = os.fstat(tree_fd).st_dev
    observed = {}
    children = {path: set() for path, item in plan.items() if item.kind == 'directory'}
    for path in plan:
        if path:
            children[path[:-1]].add(path[-1])
    for path, item in plan.items():
        if item.kind == 'directory':
            with directory_at(tree_fd, path) as fd:
                initial = os.fstat(fd)
                require({os.fsencode(name) for name in os.listdir(fd)} == children[path], 'Directory name census differs')
                row = actual_row(initial, read_attrs(fd), b'')
                require(named_identity(initial) == named_identity(os.fstat(fd)), 'Directory changed during readback')
        else:
            with directory_at(tree_fd, path[:-1]) as parent:
                name = path[-1]
                initial = os.stat(name, dir_fd=parent, follow_symlinks=False)
                require(stat.S_IFMT(initial.st_mode) == KINDS[item.kind], 'Actual entry type differs')
                if item.kind == 'symlink':
                    row = actual_row(initial, read_attrs(anchored_name(parent, name), nofollow=True),
                                     os.readlink(name, dir_fd=parent))
                else:
                    with open_fd(name, os.O_RDONLY | os.O_NONBLOCK, parent=parent) as fd:
                        require(named_identity(os.fstat(fd)) == named_identity(initial), 'Named and opened file differ')
                        with os.fdopen(os.dup(fd), 'rb') as file:
                            body = file.read(len(item.body) + 1)
                        row = actual_row(initial, read_attrs(fd), body)
                        require(named_identity(initial) == named_identity(os.fstat(fd)), 'Opened file changed')
                require(named_identity(initial) == named_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)),
                        'Named entry changed during readback')
        require(row['identity'][0] == root_dev, 'Unexpected filesystem crossing in fixture output')
        observed[path] = row
    return observed


def compare(plan, observed):
    require(plan.keys() == observed.keys(), 'Readback path census differs')
    inode_ids, actual_ids = {}, {}
    for path, item in plan.items():
        row = observed[path]
        require((row['kind'], row['uid'], row['gid'], row['mode'], row['attrs'], row['body']) ==
                (KINDS[item.kind], item.uid, item.gid, item.expected_mode, item.attrs, item.body),
                f'Metadata, xattrs or bytes differ at {path!r}')
        if item.kind != 'directory':
            require(row['nlink'] == item.nlink, 'Actual hardlink count differs')
        require(inode_ids.setdefault(item.inode, row['identity']) == row['identity'] and
                actual_ids.setdefault(row['identity'], item.inode) == item.inode, 'Actual hardlink equivalence differs')


def roundtrip(plan, result):
    require(sys.platform.startswith('linux') and os.geteuid() == 0, 'Linux root fixture runtime required')
    name = 'run-' + uuid.uuid4().hex[:12]
    with open_fd(ROOT, os.O_RDONLY | os.O_DIRECTORY) as repo:
        with directory_at(repo, (b'out', b'guest-tree-pc-materializer')) as parent:
            os.mkdir(name, 0o700, dir_fd=parent)
            result['privateOutput'] = (BASE / name).relative_to(ROOT).as_posix()
            with open_fd(name, os.O_RDONLY | os.O_DIRECTORY, parent=parent) as run:
                os.mkdir('tree', 0o700, dir_fd=run)
                with open_fd('tree', os.O_RDONLY | os.O_DIRECTORY, parent=run) as tree:
                    build_tree(tree, plan)
                    compare(plan, read_tree(tree, plan))
    result['roundtripVerified'] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', help='single filename in out/guest-tree-pc-materializer')
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--roundtrip', action='store_true', help='create and verify one private synthetic Linux tree')
    args = parser.parse_args()
    result = {'status': 'HOLD_FIXTURE', 'roundtripVerified': False, 'donorUsed': False, 'deviceAccessed': False}
    try:
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,64}\.json', args.fixture), 'Expected simple fixture filename')
        raw = read_small(BASE / args.fixture, 512 * 1024)
        require(sha(raw) == args.sha256, 'Fixture hash differs')
        plan = load_plan(raw, lambda pin: read_small(BASE / 'fixture-blobs' / pin, 65536))
        result.update(manifestSha256=sha(raw), entries=dict(Counter(item.kind for item in plan.values())),
                      privilegedXattrsRequested=sorted({key.decode('ascii') for item in plan.values() for key, _ in item.attrs
                                                       if key.startswith((b'security.', b'trusted.'))}))
        if args.roundtrip:
            roundtrip(plan, result)
        result['status'] = 'PASS_SYNTHETIC_LINUX_TREE_ONLY' if args.roundtrip else 'PASS_FIXTURE_INPUTS_ONLY'
    except (OSError, ValueError, RecursionError) as exc:
        result['reason'] = str(exc)
    print(json.dumps(result, indent=2))
    return 1 if result['status'] == 'HOLD_FIXTURE' else 0


if __name__ == '__main__':
    raise SystemExit(main())
