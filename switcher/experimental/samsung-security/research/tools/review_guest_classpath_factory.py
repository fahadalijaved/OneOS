"""Project the fixed classpath scan over the supplied donor's factory payloads."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
import re
import stat
import struct
import sys
from zipfile import ZipFile

from audit_guest_linkerconfig_apex_inputs import fields
from audit_guest_runtime_apex import SelectedExt4
from audit_samsung_boot_classpath_cohort import fragment
from check_guest_classpath_selection import ENUM, PATTERNS, ROOT, read_held, require
from review_guest_classpath_frontier import BASE, FRONTIER, artifact, expected_exports, pinned, scenarios
from verify_guest_tree_erofs_image import crc32c, directory_block


DONOR = ROOT.parent / 'firmware/donor'
ARCHIVE_LIMIT = 160 * 1024 * 1024
CATALOG = ('../firmware/donor/filesystem-catalog.json', 9237704,
           '00dfb30a2723d8770d55d9242796dc03c9821202e01899eb0616a603d8106de4')
INVENTORY = ('../inventory/apex.json', 46030,
             '06c05f2009d8ff3ef54339ffc73fdfe0b854a6295769c5a4976517b25f54cc1b')
FRAGMENTS = {suffix[1:]: keys for keys, _, suffix in PATTERNS}
JAR = re.compile(r'/(?:[A-Za-z0-9._+-]+/)+[A-Za-z0-9._+-]+\.jar')


class InlineErofs:
    """Read only compact inline metadata reached by the fixed directory walk."""

    def __init__(self, image):
        self.image = image
        superblock = image[1024:4096]
        magic, checksum, compat, bits, slots, self.root, count = struct.unpack_from('<IIIBBHQ', superblock)
        blocks, meta, shared = struct.unpack_from('<III', superblock, 36)
        incompatible, _, devices, device_table, directory_bits = struct.unpack_from('<IHHHB', superblock, 80)
        self.end = blocks * 4096
        require((magic, compat, bits, slots) == (0xe0f5e1e2, 7, 12, 0) and incompatible in (1, 3)
                and not (meta or shared or devices or device_table or directory_bits)
                and 0 < count < 1000 and 4096 <= self.end <= len(image), 'Held nested EROFS profile')
        require(crc32c(superblock[:4] + bytes(4) + superblock[8:]) == checksum, 'EROFS superblock checksum')

    def inode(self, number, kind, limit):
        offset = number * 32
        require(1152 <= offset <= self.end - 32, 'EROFS inode extent')
        form, xcount, mode, _, size = struct.unpack_from('<HHHHI', self.image, offset)
        xattrs = 12 + 4 * (xcount - 1) if xcount else 0
        start = offset + 32 + xattrs
        require(form == 4 and stat.S_IFMT(mode) == kind and 0 < size <= limit
                and start + size <= self.end and offset // 4096 == (start + size - 1) // 4096,
                'Bounded EROFS compact inline inode')
        return self.image[start:start + size]

    def directory(self, number, parent):
        entries = list(directory_block(self.inode(number, stat.S_IFDIR, 4096)))
        names = {name.decode('ascii'): (node, kind) for name, node, kind in entries}
        require(len(names) == len(entries) and names.get('.') == (number, 2) and names.get('..') == (parent, 2),
                'Exact EROFS directory ancestry')
        return names


def file_row(path, raw):
    return {'path': path, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def member(archive, name, limit):
    matches = [info for info in archive.infolist() if info.filename == name]
    require(len(matches) == 1 and not matches[0].is_dir() and 0 < matches[0].file_size <= limit,
            f'Unique bounded ZIP member: {name}')
    data = archive.read(matches[0])
    require(len(data) == matches[0].file_size, f'Exact ZIP member extent: {name}')
    return data


def module_id(manifest):
    decoded = fields(manifest)
    name, = decoded[1]
    version, = decoded[2]
    require(isinstance(name, bytes) and re.fullmatch(rb'[a-zA-Z0-9_.-]+', name)
            and b'.' in name and not name.startswith(b'.') and type(version) is int and version > 0,
            'Exact APEX manifest identity')
    return name.decode('ascii'), version


def raw_payload(path, folder, source, size):
    require(0 < size <= ARCHIVE_LIMIT, 'Bounded factory container')
    outer_data = read_held(path, size)
    require(len(outer_data) == size, 'Factory container extent')
    with ZipFile(BytesIO(outer_data)) as outer:
        wrapped = 'original_apex' in outer.namelist()
        require(wrapped == source.get('compressedWrapper', False), 'Factory wrapper profile')
        outer_id = module_id(member(outer, 'apex_manifest.pb', 4096))
        inner_data = member(outer, 'original_apex', ARCHIVE_LIMIT) if wrapped else outer_data
    if wrapped:
        require(read_held(folder / 'original.apex', len(inner_data)) == inner_data, 'Held inner APEX differs')
    with ZipFile(BytesIO(inner_data)) as inner:
        manifest = member(inner, 'apex_manifest.pb', 4096)
        require(module_id(manifest) == outer_id, 'Outer and inner APEX identities differ')
        payload = member(inner, 'apex_payload.img', ARCHIVE_LIMIT)
    require(read_held(folder / 'apex_payload.img', len(payload)) == payload, 'Held payload differs from factory APEX')
    return outer_data, payload, manifest, outer_id


def read_fragments(directory, read_small, root):
    rows = []
    for relative, keys in FRAGMENTS.items():
        name = relative.rsplit('/', 1)[1]
        if name not in directory:
            continue
        inode, kind = directory[name]
        require(kind == 1, f'Nonregular classpath fragment: {root}/{relative}')
        raw = read_small(inode, 8192)
        groups = {key: [] for key in keys}
        entries = fragment(raw)
        require(0 < len(entries) <= 64, 'Bounded nonempty classpath fragment')
        for entry in entries:
            key = next((key for key in keys if ENUM[key] == entry['classpathRaw']), None)
            jar = entry['path']
            require(key is not None and JAR.fullmatch(jar) and not {'.', '..'}.intersection(jar.split('/')),
                    'Exact classpath category and JAR name')
            groups[key].append(entry)
        rows.append({**file_row(root + '/' + relative, raw), 'orderedGroups': groups})
    return rows


def ext4_view(image):
    sb = image[1024:2048]
    blocks, = struct.unpack_from('<I', sb, 4)
    inodes_per_group, = struct.unpack_from('<I', sb, 40)
    return SelectedExt4(BytesIO(image), len(image), '7d1522e19dfa5edba43e98e3a4d20250', 0x42,
                        inodes_per_group, blocks * 4096)


def candidate_fragments(image, kind, root, manifest):
    if kind == 'Ext':
        view = ext4_view(image)

        def directory(number, parent):
            names = view.directory(number)[0]
            require(names.get('.') == (number, 2) and names.get('..') == (parent, 2), 'Exact Ext directory ancestry')
            return names

        def read_small(number, limit):
            raw, row = view.inode(number, limit)
            require(stat.S_ISREG(int(row['mode'], 8)), 'Ext regular file')
            return raw

        root_inode = 2
    else:
        require(kind == 'EROFS', 'Known nested payload filesystem')
        erofs = InlineErofs(image)
        root_inode = erofs.root
        directory = erofs.directory

        def read_small(number, limit):
            return erofs.inode(number, stat.S_IFREG, limit)

    root_names = directory(root_inode, root_inode)
    manifest_inode, manifest_kind = root_names['apex_manifest.pb']
    require(manifest_kind == 1 and read_small(manifest_inode, 4096) == manifest, 'Raw payload manifest identity')
    names, parent, node = root_names, root_inode, root_inode
    for segment in ('etc', 'classpaths'):
        if segment not in names:
            return []
        parent, (node, entry_type) = node, names[segment]
        require(entry_type == 2, 'Classpath ancestor must be a directory')
        names = directory(node, parent)
    return read_fragments(names, read_small, root)


def derive():
    catalog = json.loads(pinned(*CATALOG))
    inventory = json.loads(pinned(*INVENTORY))
    base = json.loads(pinned(*BASE))
    extended = json.loads(pinned(*FRONTIER))
    archives = inventory['archives']
    containers = {row['Path'].replace('\\', '/'): int(row['Size']) for row in catalog['files']
                  if row['Path'].endswith(('.apex', '.capex'))}
    require(len(archives) == len(containers) == 43 and not inventory['failures']
            and set(containers) == {row['containerPath'] for row in archives}, 'Exact supplied factory container inventory')
    fragments = []
    jars = {}
    erofs_jars = {row['entry']['path']: row['jar'] for module in extended['candidates'].values()
                  for row in module['classpathFragments']}
    for row in base['fragments']:
        if not row['path'].startswith('/system/'):
            continue
        raw = read_held(DONOR / 'extracted' / row['path'].lstrip('/'), row['bytes'])
        require(len(raw) == row['bytes'] and sha256(raw).hexdigest() == row['sha256'],
                'Held system fragment differs')
        fragments.append(row)
        for group in row['orderedGroups'].values():
            for entry in group:
                jar = entry['path']
                jars[jar] = base['heldJarObjects'][jar]
                artifact(jars[jar], 64 * 1024 * 1024)

    modules = {}
    for index, source in enumerate(archives):
        container = source['containerPath']
        outer = DONOR / 'extracted' / container
        folder = DONOR / 'apex' / f'{index:03d}-{outer.stem}'
        outer_data, image, manifest, (name, version) = raw_payload(outer, folder, source, containers[container])
        require(name not in modules, 'Duplicate factory APEX name')
        root = '/apex/' + name
        kind = source['payloadType']
        rows = candidate_fragments(image, kind, root, manifest)
        for row in rows:
            for group in row['orderedGroups'].values():
                for entry in group:
                    jar = entry['path']
                    require(jar.startswith(root + '/javalib/'), 'Factory fragment references a foreign JAR')
                    if jar in jars:
                        continue
                    relative = jar.removeprefix(root + '/')
                    if kind == 'EROFS':
                        proof = erofs_jars[jar]
                        require((ROOT / proof['path']).resolve() == (folder / 'files' / relative).resolve(),
                                'EROFS JAR extraction provenance')
                        artifact(proof, 16 * 1024 * 1024)
                        jars[jar] = proof
                    else:
                        _, metadata = ext4_view(image).lookup(relative, 1, 6 * 1024 * 1024)
                        prior = base['heldJarObjects'].get(jar)
                        require(prior is None or prior['sha256'] == metadata['sha256'], 'Prior JAR differs from raw payload')
                        jars[jar] = {**metadata, 'sourceKind': 'raw Ext inode', 'payloadMember': relative, 'module': name}
        fragments.extend(rows)
        modules[name] = {'version': version, 'filesystem': kind, 'container': file_row(container, outer_data),
                         'payload': file_row(folder.name + '/apex_payload.img', image),
                         'manifestSha256': sha256(manifest).hexdigest(),
                         'fragments': [row['path'] for row in rows]}

    releases = {str(sdk): scenarios(fragments, jars, sdk) for sdk in (36, 37)}
    return {'status': 'FACTORY_DONOR_CLASSPATH_SCENARIO_ONLY',
            'inputs': [{'path': path, 'bytes': size, 'sha256': digest}
                       for path, size, digest in (CATALOG, INVENTORY, BASE, FRONTIER)],
            'modules': modules, 'fragments': fragments,
            'jars': jars, 'releaseScenarios': releases,
            'exportFixtures': {sdk: file_row(f'modeled-sdk-{sdk}', expected_exports(result))
                               for sdk, result in releases.items()},
            'activeAliasesVerified': False, 'runtimeAdmitted': False, 'deviceAction': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emit-exports', choices=('36', '37'), help='Write the selected modeled export as exact bytes')
    args = parser.parse_args()
    report = derive()
    if args.emit_exports:
        sys.stdout.buffer.write(expected_exports(report['releaseScenarios'][args.emit_exports]))
    else:
        print(json.dumps(report, indent=2))
