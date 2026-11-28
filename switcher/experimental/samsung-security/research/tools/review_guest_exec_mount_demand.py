"""Inspect file-backed executable segments in the pinned donor startup candidates."""

from collections import Counter, deque
from io import BytesIO
import json
import struct

from check_guest_tree_materialization_plan import ROOT, read_small, require
from check_guest_tree_runtime_apex import held_reader


BOOTSTRAP = ('out/guest-apexd-bootstrap-inputs-d948fb34/receipt.json',
             'd948fb34c568e6ccbd0d47f7ef66cdf19fb0ef789f01a68c1b3de9ab6eb2b703')
FRONTIER = ('out/guest-entry-library-frontier/r-7288af31/receipt.json',
            '2ab3319a16676bbbf75f2327d46f095b078d186b7f8d8b560398a00da10db4c7')
ELF_READER = ('tools/audit_guest_runtime_apex.py',
              'c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de')
DONOR = ROOT.parent / 'firmware/donor'
RUNTIME = '/apex/com.android.runtime/'
ART = '/apex/com.android.art/'


def executable_segments(raw):
    # The caller has already validated the exact ELF program table.
    offset, = struct.unpack_from('<Q', raw, 32)
    width, count = struct.unpack_from('<HH', raw, 54)
    segments = []
    for index in range(count):
        kind, flags, start, va, _, file_size, memory_size, align = struct.unpack_from(
            '<IIQQQQQQ', raw, offset + index * width)
        if kind != 1:
            continue
        require(file_size <= memory_size and align and (start - va) % align == 0,
                'Unexpected PT_LOAD extent or alignment')
        if flags & 1 and file_size:
            segments.append({'programIndex': index, 'flags': flags, 'fileOffset': start,
                             'fileBytes': file_size, 'virtualAddress': va, 'memoryBytes': memory_size, 'alignment': align})
    return segments


def library_closure(initial, dependencies):
    pending = deque(initial)
    reached = set()
    while pending:
        name = pending.popleft()
        if name in reached:
            continue
        require(name in dependencies, f'Unbound provisional provider: {name}')
        reached.add(name)
        pending.extend(dependencies[name])
    return reached


def derive():
    bootstrap, frontier = (json.loads(read_small(ROOT / path, 65536, pin)) for path, pin in (BOOTSTRAP, FRONTIER))
    ext4, elf = held_reader(read_small(ROOT / ELF_READER[0], 32768, ELF_READER[1]))
    art_payload = frontier['selectedArtPayload']
    art_raw = read_small(DONOR / 'apex/016-com.google.android.art_compressed/apex_payload.img',
                         32 * 1024**2, art_payload['sha256'])
    art = ext4(BytesIO(art_raw), len(art_raw), '7d1522e19dfa5edba43e98e3a4d20250', 0x42, 96, 7660 * 4096)
    objects = {}

    def inspect(path, expected):
        require('..' not in path.split('/') and 0 < expected['bytes'] <= 16 * 1024**2, 'Unexpected object path or extent')
        if path in objects:
            require(expected['sha256'] == objects[path]['sha256'], f'Conflicting pinned object: {path}')
            return path
        if path.startswith('/system/'):
            mount = 'carrierSystem'
            raw = read_small(DONOR / 'extracted' / path[1:], expected['bytes'], expected['sha256'])
        elif path.startswith(RUNTIME):
            mount = 'runtimeApex'
            raw = read_small(DONOR / 'apex/005-com.android.runtime/files' / path[len(RUNTIME):],
                             expected['bytes'], expected['sha256'])
        else:
            require(path.startswith(ART + 'lib64/'), f'Unknown mount role: {path}')
            mount = 'artApex'
            raw, _ = art.lookup(path[len(ART):], 1, 262144)
        actual = elf(raw)
        require(all(actual[key] == expected[key] for key in ('bytes', 'sha256', 'needed', 'soname', 'interpreter')),
                f'ELF profile changed: {path}')
        segments = executable_segments(raw)
        require(segments, f'No file-backed executable PT_LOAD: {path}')
        objects[path] = {'mountRole': mount, 'bytes': actual['bytes'], 'sha256': actual['sha256'],
                         'executableLoads': segments}
        return path

    def phase(entry, interpreter, libraries, scope):
        paths = {entry, interpreter, *libraries}
        counts = Counter(objects[path]['mountRole'] for path in paths)
        return {'scope': scope, 'entry': entry, 'interpreter': interpreter, 'libraries': sorted(libraries),
                'executableFilesByMountRole': dict(sorted(counts.items()))}

    boot_entry = inspect(bootstrap['entry']['path'], bootstrap['entry'])
    boot_linker = inspect(bootstrap['interpreter']['path'], bootstrap['interpreter'])
    boot_candidates = {name: row for name, (row,) in bootstrap['libraries'].items()}
    require(library_closure(bootstrap['entry']['needed'], {name: row['needed'] for name, row in boot_candidates.items()})
            == boot_candidates.keys(), 'Bootstrap candidate graph differs')
    stub = boot_candidates.pop('ld-android.so')
    stub_path = inspect(stub['path'], stub)
    boot_libraries = [inspect(row['path'], row) for row in boot_candidates.values()]

    runtime_linker = inspect(RUNTIME + 'bin/linker64', frontier['interpreter'])
    generator = inspect(RUNTIME + 'bin/linkerconfig', frontier['linkerconfig'])
    app = inspect('/system/bin/app_process64', frontier['appProcess64'])
    direct = frontier['directLibraryCandidates']
    config_graph = frontier['linkerconfigProvisionalGraph']
    config_needed = library_closure(frontier['linkerconfig']['needed'], config_graph['providerNeeded'])
    require(config_needed == config_graph['providerNeeded'].keys()
            and config_graph['entryNeeded'] == frontier['linkerconfig']['needed'], 'Linkerconfig graph differs')
    config_needed.remove('ld-android.so')
    config_libraries = [inspect(direct[name]['candidate'], direct[name]) for name in config_needed]
    app_libraries = [inspect(direct[name]['candidate'], direct[name]) for name in frontier['appProcess64']['needed']]

    return {'schema': 'oneos-guest-exec-mount-demand/v1', 'status': 'VERIFIED_STATIC_FILE_BACKED_EXECUTABLE_SEGMENTS',
            'inputs': [dict(zip(('path', 'sha256'), pin)) for pin in (BOOTSTRAP, FRONTIER, ELF_READER)],
            'phases': {
                'apexdBootstrap': phase(boot_entry, boot_linker, boot_libraries, 'Held bootstrap dependency picks'),
                'linkerconfig': phase(generator, runtime_linker, config_libraries, 'Held provisional transitive picks'),
                'appProcess64': phase(app, runtime_linker, app_libraries, 'Held provisional direct picks only'),
            },
            'excludedSystemStub': {'path': stub_path, 'reason': 'These branches model the interpreter as preloaded ld-android.so'},
            'objects': dict(sorted(objects.items())), 'effectiveMountsObserved': False,
            'effectiveNamespaceVerified': False, 'appProcessTransitiveClosureVerified': False,
            'targetExecuted': False, 'deviceAction': False}


if __name__ == '__main__':
    print(json.dumps(derive(), indent=2))
