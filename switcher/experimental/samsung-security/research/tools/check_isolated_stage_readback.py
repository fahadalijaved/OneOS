"""Check saved read-only observations for the fixed isolated VIEW stage."""

import argparse
import base64
import hashlib
import json
import re
import stat
from pathlib import Path


ROOT = Path(__file__).absolute().parents[1]
STAGE = '/data/local/tmp/oneos-viewprep'
DATA = STAGE + '/data'
IMAGE = STAGE + '/system.raw'
IMAGE_ID = IMAGE + '.id'
BIN = STAGE + '/bin'
CONTROLLER = BIN + '/oneos_retained_root_handoff'
GUARD = '/dev/oneos-retained-viewprep'
LEASE = GUARD + '/lease'
MARKERS = ('writer-blocked', 'legacy-blocked', 'view-blocked')
DIRECTORIES = ('/', '/data', '/data/local', '/data/local/tmp', '/data_mirror', '/dev', '/mnt',
               STAGE, DATA, DATA + '/user', DATA + '/user/0', DATA + '/data', BIN, GUARD)
FILES = (IMAGE, IMAGE_ID, CONTROLLER, LEASE)
DIR_OPEN = 'openat-componentwise-O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC'
FILE_OPEN = 'openat-O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC'
NAMED_STAT = 'fstatat-AT_SYMLINK_NOFOLLOW'
CAPTURE_SCHEMA = 'oneos-isolated-stage-readback/v1'
IMAGE_BYTES = 14669168640
CACHED_DIGEST = '92c7cd8485dd6ef80d1f5c734ea13a8744510c15b77a18471eb11078df84ddb6'
CONTROLLER_BYTES = 663592
ARTIFACTS = {
    'app': ('out/isolated-retained-view-app-package/r-e2590d4cf9ba/OneOS-Isolated-View-Prep-debug.apk',
            'ced1d702d5704ebdc087c1d5d4ab4e7f3d30245ab08edf085043349a94c63b39'),
    'host': ('out/retained-view-ingress-host-package/r-698a94c6149a/OneOS-Retained-View-Ingress-Host-debug.apk',
             '50413f663e7a87d1b561dc5aaefdc7c46561dc431fffe03d3bc4053be0a9e2c4'),
    'controller': ('out/isolated-retained-view-controller/r-c88346bc/oneos_retained_root_view_isolated',
                   '1f47c5edb783c4a5b691326f8c2d94665bb9b1e963b8fcffcdbfe6d51c730180'),
    'pcPair': ('out/isolated-retained-view-pair/r-bbb18fa1/receipt.json',
               'bf77aa07a33689b44d2ac02eee3f39131803576967a48ff2a44a290785a212b4'),
    'nativeBuild': ('out/isolated-retained-view-controller/r-c88346bc/receipt.json',
                    'ece49e0dd778ecd20f1c06a1cb54dc4ff94ca233e12823a8e583c485ad0e8e49'),
    'gviSource': ('out/isolated-retained-view-controller/r-c88346bc/native-src/guest_private_view_inputs.c',
                  'c76ad84ef6ee79f9ab254888df868f21c1800ed1def05bb3e18ca253235ad50d'),
    'gvoSource': ('out/isolated-retained-view-controller/r-c88346bc/native-src/guest_private_view_owner.c',
                  '30d7dc8ddcf372f76c3384e43dc6ed806989edfd0fb72efc2f0886bab8c0b063'),
    'mountParserSource': ('out/isolated-retained-view-controller/r-c88346bc/native-src/guest_private_view_mountinfo.c',
                          '7cf383c26bc677cef661a820dbfb3fc414eda076566b147d4b29741ccf077cca'),
    'launcherSource': ('out/retained-view-isolated-ui/relay/successor/RetainedRootOfferCommand.java',
                       '6d27d407c7fc958e75351a8ce521286d937853cd1a0559971dce563efd30c2e0'),
    'inputPlan': ('out/isolated-view-inputs/r-b85ca77d/manifest.json',
                  '441d314626cefb0b5386ae189871c0363867cfe56864672f0f20ae7e6525f97d'),
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def fields(value, names, where):
    require(isinstance(value, dict) and value.keys() == set(names.split()), f'Unexpected fields: {where}')


def number(value, where, minimum=0, maximum=(1 << 64) - 1):
    require(type(value) is int and minimum <= value <= maximum, f'Invalid integer: {where}')
    return value


def ascii_text(value, limit, where):
    require(isinstance(value, str) and 0 < len(value) < limit and value.isascii() and '\0' not in value,
            f'Invalid bounded text: {where}')
    return value


def decimal(value, where, minimum=0, maximum=(1 << 64) - 1):
    require(re.fullmatch(r'[0-9]{1,20}', value), f'Invalid decimal: {where}')
    return number(int(value), where, minimum, maximum)


def device_parts(dev):
    # Linux userspace dev_t encoding, independent of the offline PC's platform.
    return ((dev >> 8) & 0xfff) | ((dev >> 32) & 0xfffff000), (dev & 0xff) | ((dev >> 12) & 0xffffff00)


def below(path, parent):
    return parent == '/' or path == parent or path.startswith(parent + '/')


def mount_path(value):
    escapes = {'040': ' ', '011': '\t', '012': '\n', '134': '\\'}
    require(re.fullmatch(r'/(?:[^\\]|\\(?:040|011|012|134))*', value), 'Invalid mountinfo path escape')
    path = re.sub(r'\\([0-7]{3})', lambda m: escapes[m[1]], value)
    require(len(path) < 1024 and (path == '/' or all(p not in ('', '.', '..') for p in path[1:].split('/'))),
            'Noncanonical mountinfo path')
    return path


def mount_options(value):
    require(0 < len(value) <= 512 and re.fullmatch(r'(?:[^\\]|\\(?:040|011|012|134|043|054))+', value),
            'Invalid mount options')
    keys = [part.partition('=')[0] for part in value.split(',')]
    require(all(keys) and len(set(keys)) == len(keys) and not {'ro', 'rw'} <= set(keys),
            'Ambiguous mount options')


def mount_table(raw):
    text = ascii_text(raw, 2 * 1024 * 1024, 'mountinfo')
    require(text.endswith('\n') and 0 < text.count('\n') <= 4096, 'Incomplete mountinfo')
    rows = {}
    for line in text[:-1].split('\n'):
        require(0 < len(line) <= 8192 and all(32 <= ord(c) < 127 for c in line), 'Invalid mountinfo row')
        left, sep, right = line.partition(' - ')
        a, b = left.split(' '), right.split(' ')
        require(sep and len(a) >= 6 and len(b) == 3 and all(a + b), 'Invalid mountinfo framing')
        mount_id = decimal(a[0], 'mount ID', 1)
        decimal(a[1], 'parent ID', 1)
        require(mount_id not in rows, 'Duplicate mount ID')
        parts = a[2].split(':')
        require(len(parts) == 2, 'Invalid mountinfo device')
        dev = tuple(decimal(x, 'mount device', maximum=(1 << 32) - 1) for x in parts)
        mount_path(a[3])
        mount_options(a[5])
        mount_options(b[2])
        tags = set()
        for tag in a[6:]:
            name, delim, value = tag.partition(':')
            if tag != 'unbindable':
                require(delim and name in ('shared', 'master', 'propagate_from'), 'Unknown mount propagation field')
                decimal(value, name, 1)
            require(name not in tags, 'Duplicate mount propagation field')
            tags.add(name)
        require(('propagate_from' not in tags or 'master' in tags) and ('unbindable' not in tags or len(tags) == 1),
                'Invalid mount propagation fields')
        for value, cap in ((b[0], 64), (b[1], 1024)):
            require(len(value) < cap and re.fullmatch(r'(?:[^\\]|\\(?:040|011|012|134|043))+', value),
                    'Invalid mount filesystem or source')
        rows[mount_id] = {'device': dev, 'point': mount_path(a[4])}
    return rows


def fd_mount_id(raw):
    text = ascii_text(raw, 8192, 'fdinfo')
    require(text.endswith('\n'), 'Incomplete fdinfo')
    values = []
    for line in text[:-1].split('\n'):
        name, sep, value = line.partition(':')
        require(sep and name and all(32 < ord(c) < 127 for c in name)
                and all(c == '\t' or 32 <= ord(c) < 127 for c in value), 'Invalid fdinfo field')
        if name == 'mnt_id':
            require(value and value[0] in ' \t', 'Missing fdinfo mnt_id delimiter')
            values.append(decimal(value.lstrip(' \t'), 'fdinfo mnt_id', 1))
    require(len(values) == 1, 'Expected one fdinfo mnt_id')
    return values[0]


def environment(value):
    fields(value, 'bootId mountNamespace pid startTimeTicks uid euid', 'environment')
    require(isinstance(value['bootId'], str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',
                                                            value['bootId'])
            and value['bootId'] != '00000000-0000-0000-0000-000000000000', 'Invalid boot ID')
    fields(value['mountNamespace'], 'dev ino', 'mount namespace')
    for key in ('dev', 'ino'):
        number(value['mountNamespace'][key], f'mount namespace {key}', 1)
    number(value['pid'], 'pid', 1, (1 << 31) - 1)
    number(value['startTimeTicks'], 'start time ticks', 1)
    for key in ('uid', 'euid'):
        number(value[key], key, 0, 0)
    return value


def stat_tuple(value, path):
    fields(value, 'dev ino mode uid gid nlink size mtimeSec mtimeNsec ctimeSec ctimeNsec', path)
    for key in ('dev', 'ino', 'mode', 'uid', 'gid', 'nlink', 'size', 'mtimeSec', 'mtimeNsec', 'ctimeSec', 'ctimeNsec'):
        minimum = 1 if key in ('ino', 'nlink') else -(1 << 63) if key in ('mtimeSec', 'ctimeSec') else 0
        maximum = (999999999 if key.endswith('Nsec') else 0xffff if key == 'mode' else
                   (1 << 32) - 1 if key in ('uid', 'gid') else (1 << 63) - 1 if key.endswith('Sec') or key == 'size'
                   else (1 << 64) - 1)
        number(value[key], f'{path} {key}', minimum, maximum)
    return value


def object_stat(path, record, rows):
    fields(record, 'openMethod namedMethod heldBefore heldAfter namedBefore namedAfter fdinfoBefore fdinfoAfter', path)
    directory = path in DIRECTORIES
    require(record['openMethod'] == (DIR_OPEN if directory else FILE_OPEN) and record['namedMethod'] == NAMED_STAT,
            f'Missing fixed no-follow acquisition evidence: {path}')
    s = stat_tuple(record['heldBefore'], path)
    for key in ('heldAfter', 'namedBefore', 'namedAfter'):
        require(stat_tuple(record[key], path) == s, f'Named/held identity drift: {path} ({key})')
    require(stat.S_ISDIR(s['mode']) if directory else stat.S_ISREG(s['mode']), f'Unexpected object type: {path}')
    mount_id = fd_mount_id(record['fdinfoBefore'])
    require(fd_mount_id(record['fdinfoAfter']) == mount_id and mount_id in rows, f'FD mount identity drift: {path}')
    row = rows[mount_id]
    require(device_parts(s['dev']) == row['device'] and below(path, row['point']), f'FD/mountinfo mismatch: {path}')
    return s, mount_id


def image_id(capture, s, sidecar_size):
    fields(capture, 'method beforeBase64 afterBase64', 'image ID')
    require(capture['method'] == 'pread-held-system.raw.id', 'ID must be read through the held sidecar FD')
    before = ascii_text(capture['beforeBase64'], 1366, 'image ID base64')
    require(before == capture['afterBase64'], 'Held image ID changed')
    raw = base64.b64decode(before, validate=True)
    require(0 < len(raw) == sidecar_size < 1024 and base64.b64encode(raw).decode('ascii') == before,
            'Invalid image ID byte count or base64')
    tokens = re.split(rb'[ \t\r\n]+', raw.strip(b' \t\r\n'))
    require(len(tokens) == 3, 'Image ID must have exactly three fields')
    size, cached_hash, rendered = tokens
    require(decimal(size.decode('ascii'), 'image ID size', 1) == s['size'] == IMAGE_BYTES, 'Image ID size mismatch')
    require(cached_hash == CACHED_DIGEST.encode('ascii'), 'Image ID does not name the selected cached digest')
    expected = f"{s['dev']}:{s['ino']}:{s['size']}:{s['mtimeSec']}".encode('ascii')
    require(s['mtimeSec'] >= 0 and rendered == expected, 'Image ID does not match held image stat')


def check_capture(value, expected_cohort):
    fields(value, 'schema captureKind cohort envBefore envAfter mountinfoBefore mountinfoAfter objects markers imageId '
                  'controllerDigest', 'capture')
    require(value['schema'] == CAPTURE_SCHEMA and value['cohort'] == expected_cohort, 'Wrong capture profile or cohort')
    require(value['captureKind'] in ('device-readback', 'synthetic-fixture'), 'Unknown capture kind')
    env = environment(value['envBefore'])
    require(environment(value['envAfter']) == env, 'Capture process, boot or mount namespace changed')
    require(value['mountinfoBefore'] == value['mountinfoAfter'], 'Mountinfo changed during capture')
    rows = mount_table(value['mountinfoBefore'])
    objects = value['objects']
    require(isinstance(objects, dict) and objects.keys() == set(DIRECTORIES + FILES), 'Incomplete fixed sibling objects')
    seen = {path: object_stat(path, record, rows) for path, record in objects.items()}
    stats = {path: sample[0] for path, sample in seen.items()}
    for path in (STAGE, BIN, CONTROLLER):
        s = stats[path]
        require(s['uid'] == 0 and re.fullmatch(r'[57][0145][0145]', f"{stat.S_IMODE(s['mode']):o}"),
                f'Launcher ownership/mode mismatch: {path}')
    for path in (IMAGE, IMAGE_ID, '/dev'):
        require(stats[path]['uid'] == 0 and not stats[path]['mode'] & 0o022, f'Unprotected root object: {path}')
    # Additional sibling-stage containment: refuse mounted replacement trees and hard-linked program/image inputs.
    require(not any(below(row['point'], STAGE) or below(row['point'], GUARD) for row in rows.values()),
            'Mount at or below sibling stage or guard')
    require(all(stats[path]['nlink'] == 1 for path in (IMAGE, IMAGE_ID, CONTROLLER)), 'Shared hard-linked stage input')
    require(all(mid == seen[STAGE][1] for path, (_, mid) in seen.items() if below(path, STAGE)),
            'Sibling stage file mount identities differ')
    d, host = stats[DATA], stats['/data']
    require((d['uid'], d['gid'], stat.S_IMODE(d['mode'])) == (1000, 1000, 0o771), 'Staged data profile differs')
    require((d['dev'], d['ino']) != (host['dev'], host['ino']), 'Staged data aliases host /data')
    for path, mode in ((GUARD, 0o700), (LEASE, 0o600)):
        s = stats[path]
        require((s['uid'], s['gid'], stat.S_IMODE(s['mode'])) == (0, 0, mode), f'Guard profile differs: {path}')
    require((stats[LEASE]['size'], stats[LEASE]['nlink']) == (0, 1) and seen['/dev'][1] == seen[GUARD][1] == seen[LEASE][1],
            'Lease is not the empty single-link file on the guard mount')
    markers = value['markers']
    require(isinstance(markers, dict) and markers.keys() == set(MARKERS), 'Incomplete negative reservation observations')
    expected_marker = {'method': NAMED_STAT, 'before': 'ENOENT', 'after': 'ENOENT'}
    require(all(record == expected_marker for record in markers.values()), 'Reservation is present or uncertain')
    image_id(value['imageId'], stats[IMAGE], stats[IMAGE_ID]['size'])
    digest = value['controllerDigest']
    require(digest == {'method': 'sha256-held-fd', 'sha256': expected_cohort['controller'], 'bytes': CONTROLLER_BYTES}
            and stats[CONTROLLER]['size'] == CONTROLLER_BYTES, 'Held controller differs from selected artifact')
    return {'captureKind': value['captureKind'], 'environment': env,
            'mountinfoSha256': hashlib.sha256(value['mountinfoBefore'].encode('ascii')).hexdigest(),
            'objects': {path: {'stat': s, 'mountId': mid} for path, (s, mid) in seen.items()},
            'cachedImageDigest': CACHED_DIGEST, 'cachedImageStatMatches': True, 'imageContentHashVerified': False,
            'liveLeaseAcquired': False, 'reservationCreated': False, 'runtimeAdmissionProved': False}


def read_repo(relative, limit):
    rel = Path(relative)
    require(not rel.is_absolute() and rel.parts and rel.parts[0] == 'out' and '..' not in rel.parts,
            'Use a repository-relative path in out/')
    path = ROOT / rel
    for part in (path, *path.parents):
        if part == ROOT:
            break
        require(not part.is_symlink() and not getattr(part, 'is_junction', lambda: False)(), 'Reparse input refused')
    require(path.is_file(), 'Expected a regular saved input')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, 'Saved input outside byte bound')
    return raw


def check_plan(raw, objects):
    plan = json.loads(raw, object_pairs_hook=unique_object)
    require(plan['schema'] == 'oneos-isolated-view-input-plan/v1', 'Unexpected sibling input plan')
    for row in plan['targetObjects']:
        path = row['path']
        s = objects[path]['stat']
        if 'mode' in row:
            require((s['uid'], s['gid'], stat.S_IMODE(s['mode'])) == (row['uid'], row['gid'], int(row['mode'], 8)),
                    f'Selected sibling input plan differs: {path}')


def unique_object(items):
    obj = dict(items)
    require(len(obj) == len(items), 'Duplicate JSON key')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', help='saved JSON capture in out/ (repo-relative)')
    parser.add_argument('--sha256', required=True, help='expected SHA-256 of exact capture bytes')
    args = parser.parse_args()
    receipt = {'status': 'HOLD_SAVED_STAGE_READBACK', 'liveLeaseAcquired': False,
               'reservationCreated': False, 'runtimeAdmissionProved': False}
    try:
        raw = read_repo(args.capture, 8 * 1024 * 1024)
        actual = hashlib.sha256(raw).hexdigest()
        receipt['capture'] = {'path': Path(args.capture).as_posix(), 'sha256': actual, 'bytes': len(raw)}
        require(actual == args.sha256, 'Capture SHA-256 mismatch')
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
        cohort = {role: ARTIFACTS[role][1] for role in ('app', 'host', 'controller')}
        checks = check_capture(value, cohort)
        for role, (path, expected) in ARTIFACTS.items():
            artifact = read_repo(path, 2 * 1024 * 1024)
            require(hashlib.sha256(artifact).hexdigest() == expected, f'PC artifact pin differs: {role}')
            if role == 'inputPlan':
                check_plan(artifact, checks['objects'])
        status = ('MATCH_SAVED_SIBLING_STAGE_METADATA_ONLY' if checks['captureKind'] == 'device-readback'
                  else 'MATCH_SYNTHETIC_FIXTURE_ONLY')
        receipt.update(checks, status=status,
                       artifactPins={role: {'path': path, 'sha256': digest} for role, (path, digest) in ARTIFACTS.items()})
    except (OSError, ValueError, RecursionError) as exc:
        receipt['reason'] = str(exc)
    print(json.dumps(receipt, indent=2))
    return 1 if receipt['status'] == 'HOLD_SAVED_STAGE_READBACK' else 0


if __name__ == '__main__':
    raise SystemExit(main())
