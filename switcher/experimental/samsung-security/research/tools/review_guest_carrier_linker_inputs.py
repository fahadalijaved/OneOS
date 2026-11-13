"""Verify linkerconfig source paths in the held EROFS carrier without mounting it."""

from collections import defaultdict
from hashlib import sha256
import json
import os
import stat

from verify_guest_tree_erofs_image import Erofs, FTYPE, KIND, PLAN_SHA, ROOT, load_plan, require, source


READBACK = ('out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json',
            '92e2f8199da955cf4b8ddc15cf99b4ab978c133d3f9284535ad3c500fa0d5e6e')
LINKER = ('out/guest-tree-linker-inputs/receipt.json',
          '6a41ddb659835dc5580520de71bf24be4f812112a3a31cf911674ec1a01cb039')
ALIASES = {
    '/product': '/system/product',
    '/system_ext': '/system/system_ext',
    '/odm/etc': '/vendor/odm/etc',
    '/system/bin/linker64': '/apex/com.android.runtime/bin/linker64',
}
FILES = {
    '/system/etc/linker.config.pb': 'system/etc/linker.config.pb',
    '/system/etc/public.libraries.txt': 'system/etc/public.libraries.txt',
    '/system/etc/llndk.libraries.txt': 'system/etc/llndk.libraries.txt',
    '/system/etc/sanitizer.libraries.txt': 'system/etc/sanitizer.libraries.txt',
    '/product/etc/linker.config.pb': 'system/product/etc/linker.config.pb',
}
MISSING = {
    '/system_ext/etc/linker.config.pb': '/system/system_ext/etc/linker.config.pb',
    '/vendor/etc/linker.config.pb': '/vendor/etc/linker.config.pb',
    '/vendor/etc/public.libraries.txt': '/vendor/etc/public.libraries.txt',
    '/odm/etc/linker.config.pb': '/vendor/odm/etc/linker.config.pb',
    '/system/etc/ld.config.arm64.txt': '/system/etc/ld.config.arm64.txt',
    '/system/etc/ld.config.txt': '/system/etc/ld.config.txt',
    '/apex/apex-info-list.xml': '/apex/apex-info-list.xml',
    '/linkerconfig/ld.config.txt': '/linkerconfig/ld.config.txt',
    '/linkerconfig/apex.libraries.config.txt': '/linkerconfig/apex.libraries.config.txt',
}


class CarrierView:
    def __init__(self, reader, plan, backing):
        self.reader = reader
        self.plan = {(b'tree', *path): node for path, node in plan.items()}
        self.children = defaultdict(set)
        self.children[()] = {b'tree', *(name.encode('ascii') for name in backing)}
        for path in self.plan:
            self.children[path[:-1]].add(path[-1])
        nid = reader.root_nid
        node = reader.inode(nid)
        require(node.mode == stat.S_IFDIR | 0o755 and (node.uid, node.gid) == (0, 0), 'Unexpected carrier root')
        self.nodes = {(): (nid, node)}
        self.directories = {}
        self.nids = {nid}

    def entries(self, path):
        if path not in self.directories:
            nid, node = self.nodes[path]
            require(stat.S_ISDIR(node.mode), 'Cannot traverse a non-directory')
            parent = self.nodes[path[:-1]][0]
            expected = self.children[path]
            entries = self.reader.directory(node, nid, parent, len(expected))
            require(set(entries) == expected, 'Selected directory names differ from the sealed plan')
            self.directories[path] = entries
        return self.directories[path]

    def walk(self, physical):
        path = ()
        for part in (b'tree', *(p.encode('ascii') for p in physical[1:].split('/'))):
            match = self.entries(path).get(part)
            path += (part,)
            if match is None:
                return path, None
            if path not in self.nodes:
                nid, dtype = match
                expected = self.plan[path]
                require(nid not in self.nids and FTYPE[dtype] == expected.kind, 'Selected inode alias or type differs')
                node = self.reader.inode(nid)
                require((node.mode, node.uid, node.gid, node.attrs) ==
                        (KIND[expected.kind] | expected.mode, expected.uid, expected.gid, expected.attrs),
                        'Selected inode metadata differs')
                self.nodes[path] = (nid, node)
                self.nids.add(nid)
        return path, self.nodes[path]

    def file_bytes(self, physical, kind):
        path, result = self.walk(physical)
        require(result is not None and self.plan[path].kind == kind, 'Selected file or alias is absent')
        nid, node = result
        require(node.links == 1 and node.size == self.plan[path].size <= 8192, 'Unexpected selected file extent')
        raw = b''.join(self.reader.chunks(node.spans))
        require(len(raw) == node.size, 'Selected bytes differ from extent')
        return nid, raw


def derive():
    prior, linker = (json.loads(source.read_small(ROOT / path, 32768, digest)) for path, digest in (READBACK, LINKER))
    require(prior['status'] == 'PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY'
            and prior['planSha256'] == PLAN_SHA and prior['mountObserved'] is False
            and linker['generatedConfig'] is None and linker['entryAdmission'] is None, 'Unexpected predecessor evidence')
    plan, _, _ = load_plan()
    image = prior['image']
    path = ROOT / image['path']
    require(path.is_relative_to(ROOT / 'out') and source.plain(path) == path, 'Image path escaped repository output')
    named = source.identity(path.lstat())
    require(list(named) == image['identity'], 'Held carrier identity differs from whole-image readback')
    with path.open('rb') as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        require(opened[:4] == named[:4], 'Opened carrier differs')
        backing = prior['expectedCoreApexFiles']
        reader = Erofs(stream, image['bytes'], len(plan) + len(backing) + 1)
        require(reader.geometry == prior['geometry'], 'Held carrier geometry differs')
        view = CarrierView(reader, plan, backing)
        for link, target in ALIASES.items():
            _, raw = view.file_bytes(link, 'symlink')
            require(raw == target.encode('ascii'), 'Guest-root alias target differs')

        files = {}
        for logical, relative in FILES.items():
            nid, raw = view.file_bytes('/' + relative, 'file')
            pin = linker['verifiedPartitionSourceBytes'][relative]
            digest = sha256(raw).hexdigest()
            require((len(raw), digest) == (pin['bytes'], pin['sha256']), 'Packaged linker input bytes differ')
            files[logical] = {'physicalPath': '/' + relative, 'nid': nid, 'bytes': len(raw), 'sha256': digest}

        absent = {}
        for logical, physical in MISSING.items():
            walked, result = view.walk(physical)
            require(result is None, 'Unexpected linker input exists in the carrier')
            absent[logical] = {'physicalPath': physical, 'firstMissing': '/' + '/'.join(p.decode('ascii') for p in walked[1:])}
        for directory in ('/apex', '/linkerconfig', '/vendor'):
            walked, result = view.walk(directory)
            require(result is not None and not view.entries(walked), 'Expected empty original mountpoint')
        reader.check_geometry()
        require(source.identity(os.fstat(stream.fileno())) == opened and source.identity(path.lstat()) == named,
                'Held or named carrier changed during readback')
    return {'schema': 'oneos-guest-carrier-linker-inputs/v1', 'status': 'VERIFIED_HELD_CARRIER_SLOTS_ONLY',
            'inputs': [dict(zip(('path', 'sha256'), pin)) for pin in (READBACK, LINKER)], 'carrier': image,
            'wholeImageRehashed': False, 'metadataReadBytes': reader.metadata_read, 'aliases': ALIASES,
            'files': files, 'missing': absent, 'emptyDirectories': ['/apex', '/linkerconfig', '/vendor'],
            'effectiveMountedViewVerified': False, 'generatedConfig': None, 'entryAdmission': None,
            'targetExecuted': False}


if __name__ == '__main__':
    print(json.dumps(derive(), indent=2))
