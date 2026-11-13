"""Read the held apexd ELF dependency candidates directly from the EROFS carrier."""

from collections import deque
import json
import os
import re

from check_guest_tree_runtime_apex import held_reader
from review_guest_carrier_linker_inputs import CarrierView, Erofs, PLAN_SHA, READBACK, ROOT, load_plan, require, source


ELF_READER = ('tools/audit_guest_runtime_apex.py',
              'c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de')
PRODUCER = ('out/guest-carrier-apexd-producer-09add2c7/receipt.json',
            'b750922f74b209284c2551ca40f9288cd3c113bf882dd08562f55535a40d4f51')
APEXD = '/system/bin/apexd'
INTERPRETER = '/system/bin/bootstrap/linker64'
INTERPRETER_SHA = '150ccf670e2eba545cf559d79c32996871526c7cfd4b8404e429975d2be09fd7'
CANDIDATE_DIRS = ('/system/lib64/bootstrap', '/system/lib64')


def dependency_candidates(needed, read_candidate):
    pending = deque(needed)
    libraries = {}
    while pending:
        name = pending.popleft()
        if name in libraries:
            continue
        require(len(libraries) < 128 and re.fullmatch(r'[A-Za-z0-9_.+-]{1,192}\.so', name),
                'Unexpected dependency name or graph size')
        candidates = []
        for directory in CANDIDATE_DIRS:
            obj = read_candidate(f'{directory}/{name}')
            if obj is None:
                continue
            require(obj['soname'] == name and obj['interpreter'] is None and not obj['searchOverrides'],
                    f'Unexpected SONAME, interpreter or search override: {obj["path"]}')
            candidates.append(obj)
            pending.extend(obj['needed'])
        require(candidates, f'No library candidate in the two held directories: {name}')
        libraries[name] = candidates
    return libraries


def derive():
    prior, producer = (json.loads(source.read_small(ROOT / name, 32768, digest))
                       for name, digest in (READBACK, PRODUCER))
    _, parse_elf = held_reader(source.read_small(ROOT / ELF_READER[0], 32768, ELF_READER[1]))
    image = prior['image']
    require(prior['status'] == 'PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY'
            and prior['planSha256'] == PLAN_SHA and image['sha256'] == producer['imageSha256'],
            'Unexpected predecessor evidence')
    plan, _, _ = load_plan()
    path = ROOT / image['path']
    require(path.is_relative_to(ROOT / 'out') and source.plain(path) == path, 'Carrier path escaped repository output')
    named = source.identity(path.lstat())
    require(list(named) == image['identity'], 'Held carrier identity differs from whole-image readback')
    selected_bytes = 0
    excluded_symlinks = {}
    with path.open('rb') as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        require(opened[:4] == named[:4], 'Opened carrier differs')
        backing = prior['expectedCoreApexFiles']
        reader = Erofs(stream, image['bytes'], len(plan) + len(backing) + 1)
        require(reader.geometry == prior['geometry'], 'Held carrier geometry differs')
        view = CarrierView(reader, plan, backing)

        def read_elf(physical):
            nonlocal selected_bytes
            key, found = view.walk(physical)
            if found is None:
                return None
            nid, inode = found
            expected = view.plan[key]
            if expected.kind == 'symlink':
                _, raw = view.file_bytes(physical, 'symlink')
                require(raw == expected.target, f'Alias target differs from sealed plan: {physical}')
                excluded_symlinks[physical] = {'nid': nid, 'target': raw.decode('ascii')}
                return None
            require(expected.kind == 'file' and inode.links == 1 and 64 <= inode.size == expected.size <= 8 * 1024**2,
                    f'Unexpected regular ELF extent: {physical}')
            selected_bytes += inode.size
            require(selected_bytes <= 64 * 1024**2, 'Selected ELF bytes exceeded bound')
            obj = parse_elf(b''.join(reader.chunks(inode.spans)))
            require(obj['bytes'] == inode.size and obj['sha256'] == expected.payload['sha256'],
                    f'ELF bytes differ from sealed plan: {physical}')
            return {'path': physical, 'nid': nid, **obj}

        entry = read_elf(APEXD)
        interpreter = read_elf(INTERPRETER)
        require(entry is not None and entry['sha256'] == producer['files'][APEXD]['sha256']
                and entry['interpreter'] == INTERPRETER and not entry['searchOverrides'], 'Donor apexd ELF differs')
        require(interpreter is not None and interpreter['sha256'] == INTERPRETER_SHA
                and interpreter['soname'] == 'ld-android.so' and interpreter['interpreter'] is None
                and not interpreter['needed'] and not interpreter['searchOverrides'], 'Bootstrap interpreter differs')
        libraries = dependency_candidates(entry['needed'], read_elf)
        reader.check_geometry()
        require(source.identity(os.fstat(stream.fileno())) == opened and source.identity(path.lstat()) == named,
                'Held or named carrier changed during readback')

    return {'schema': 'oneos-guest-apexd-bootstrap-inputs/v1', 'status': 'VERIFIED_HELD_ELF_CANDIDATES_ONLY',
            'inputs': [dict(zip(('path', 'sha256'), pin)) for pin in (READBACK, PRODUCER, ELF_READER)],
            'carrierSha256': image['sha256'], 'wholeImageRehashed': False, 'selectedBytes': selected_bytes,
            'metadataReadBytes': reader.metadata_read, 'candidateDirectories': CANDIDATE_DIRS,
            'entry': entry, 'interpreter': interpreter, 'libraries': libraries, 'excludedSymlinks': excluded_symlinks,
            'effectiveLoaderSelectionVerified': False, 'targetExecuted': False, 'deviceAction': False}


if __name__ == '__main__':
    print(json.dumps(derive(), indent=2))
