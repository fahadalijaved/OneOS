"""Stream a donor tree carrier with the three pinned core APEX backing files."""

import argparse
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import sys
import tarfile

import stream_guest_tree_erofs_tar as tar


tree = tar.tree
require = tar.require
COHORT = tar.ROOT / 'out/guest-tree-core-apex-cohort/source-cohort.json'
COHORT_SHA = '09c44b5f58795a8152bceb5053a25ea8ee747741d29382ca20351aeb67335ddd'
NAMES = {
    'com.android.art': 'art_payload.img',
    'com.android.i18n': 'i18n_payload.img',
    'com.android.runtime': 'runtime_payload.img',
}


def backing_files():
    cohort = tree.source.decode(tree.source.read_small(COHORT, 16384, COHORT_SHA))
    rows = cohort['sourceCohort']
    require(cohort['schema'] == 'oneos-guest-apex-core-source-cohort/v1'
            and cohort['runtimeAdmission'] is None and len(rows) == len(NAMES)
            and {row['name'] for row in rows} == NAMES.keys(), 'Wrong core APEX cohort')
    entries = {}
    for row in rows:
        payload = row['sources']['payload']
        path = PurePosixPath(payload['path'])
        require(path.parts[:4] == ('..', 'firmware', 'donor', 'apex') and len(path.parts) == 6
                and path.name == 'apex_payload.img' and '..' not in path.parts[1:]
                and re.fullmatch(r'[A-Za-z0-9_.-]+', path.parts[4])
                and type(payload['bytes']) is int and 0 < payload['bytes'] <= 64 * 1024 * 1024
                and payload['bytes'] % 4096 == 0
                and re.fullmatch(r'[a-f0-9]{64}', payload['sha256']), 'Invalid core APEX source')
        entries[NAMES[row['name']]] = payload
    return dict(sorted(entries.items()))


def copy_payload(payload, sink=None):
    path = tree.source.plain(tar.ROOT.parent.joinpath(*PurePosixPath(payload['path']).parts[1:]))
    size = payload['bytes']

    def named():
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_size == size, 'Invalid named core APEX payload')
        return tree.source.identity(info)

    before = named()
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    digest = hashlib.sha256()
    with os.fdopen(os.open(path, flags), 'rb', buffering=0) as stream:
        initial = os.fstat(stream.fileno())
        held = tree.source.identity(initial)
        require(stat.S_ISREG(initial.st_mode) and held[:4] == before[:4], 'Wrong held core APEX payload')
        for offset in range(0, size, tree.CHUNK):
            count = min(tree.CHUNK, size - offset)
            data = stream.read(count)
            require(len(data) == count, 'Short core APEX payload')
            digest.update(data)
            if sink is not None:
                tar.write_all(sink, data)
        require(digest.hexdigest() == payload['sha256'], 'Core APEX payload digest differs')
        require(tree.source.identity(os.fstat(stream.fileno())) == held and named() == before,
                'Core APEX source changed during read')


def append_payloads(entries, sink=None):
    for name, payload in entries.items():
        if sink is not None:
            tar.write_all(sink, tar.header(name, tarfile.REGTYPE, 0o444, 0, 0, payload['bytes']))
        copy_payload(payload, sink)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--stream', action='store_true')
    args = parser.parse_args()
    try:
        require(not args.stream or not sys.stdout.isatty(), 'Refusing binary output on a terminal')
        entries = backing_files()
        plan, image, _ = tree.load_plan()
        if args.dry_run:
            receipt = tar.dry_run(plan, image)
            append_payloads(entries)
            print(json.dumps(receipt | {
                'coreApexSourceCohortSha256': COHORT_SHA,
                'coreApexFiles': {name: {'bytes': row['bytes'], 'sha256': row['sha256']}
                                  for name, row in entries.items()},
                'carrierArchiveEntries': receipt['archiveEntries'] + len(entries),
                'projectedCarrierBytes': receipt['projectedTarBytes'] + sum(
                    tar.BLOCK + row['bytes'] for row in entries.values()),
            }, indent=2))
            return 0
        if os.name == 'nt':
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        sink = sys.stdout.buffer
        with tar.held_image(image) as read_at:
            require(tree.hash_stream(read_at, image['bytes']) == image['sha256'], 'Donor image digest differs')
            tar.write_entries(plan, read_at, sink)
        append_payloads(entries, sink)
        tar.write_all(sink, tar.END)
        sink.flush()
        return 0
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f'Core APEX EROFS carrier refused: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
