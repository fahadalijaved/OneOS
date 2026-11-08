"""Join the sealed carrier to the startup readers' static path requirements."""

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import PurePosixPath
import stat

from review_guest_carrier_linker_inputs import (
    CarrierView, Erofs, PLAN_SHA, READBACK, ROOT, load_plan, require, source,
)


DEMAND = ('out/guest-exec-mount-demand-ce69fa4f/receipt.json',
          'ce69fa4f536ef35f920265970f06578a25eab9d0e14d51014617146f90a39b7d')
PROFILE = ('out/guest-native-exec-placement-profile/r-078191c7/receipt.json',
           '94c2e0001d8c9525668a283257f918a32ffbf2324d3389447a8da5f6cde59f1d')
GRAPH = ('out/guest-app-process-dependency-graph/r-edbed514/receipt.json',
         '689cff7eeccd603a7c1930589aa40a2e1b20fcb4703d56bc83ead3b50645c985')
READER = ('compat/native/guest_linkerconfig_app_process.c',
          '87ce761dac5dd0295e82c77e0de76d5f2d260f7c19fbb57091eeb7a8616fd28d')
APP = '/system/bin/app_process64'
LINK = '/system/bin/linker64'
APP_METADATA = {
    '/': (stat.S_IFDIR | 0o755, 0, 0),
    '/system': (stat.S_IFDIR | 0o755, 0, 0),
    '/system/bin': (stat.S_IFDIR | 0o751, 0, 2000),
    '/system/etc': (stat.S_IFDIR | 0o755, 0, 0),
    APP: (stat.S_IFREG | 0o755, 0, 2000),
    LINK: (stat.S_IFLNK | 0o777, 0, 2000),
}


def record(nid, node):
    return {'nid': nid, 'mode': f'{node.mode:06o}', 'uid': node.uid, 'gid': node.gid,
            'nlink': node.links, 'bytes': node.size,
            'xattrsHex': {key.decode('ascii'): value.hex() for key, value in node.attrs}}


def derive():
    inputs = (READBACK, DEMAND, PROFILE, GRAPH, READER)
    prior, demand, profile, graph = (
        json.loads(source.read_small(ROOT / path, 1024**2, digest)) for path, digest in inputs[:4]
    )
    source.read_small(ROOT / READER[0], 32 * 1024, READER[1])
    image = prior['image']
    require(prior['status'] == 'PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY'
            and prior['planSha256'] == graph['inputs']['materializationPlanSha256'] == PLAN_SHA
            and image['sha256'] == graph['inputs']['carrierSha256']
            and profile['demandSha256'] == DEMAND[1], 'Startup source cohorts differ')

    app = graph['expanded']['objects']
    app_carrier = {path: row for path, row in app.items() if row['source']['kind'] == 'sealedCarrier'}
    require((app_carrier[APP]['bytes'], app_carrier[APP]['sha256']) ==
            (51880, '78d3bf52333a151a6f4859f5144de5578adf009503b792a91db307435a0f21dc'),
            'App reader content pin differs from the candidate graph')
    phase_counts = {}
    early_carrier = {}
    for phase, ordered in profile['orderedPaths'].items():
        declared = demand['phases'][phase]
        require(ordered == [declared['entry'], declared['interpreter'], *declared['libraries']],
                f'Early placement order differs for {phase}')
        files = {path: demand['objects'][path] for path in ordered}
        phase_counts[phase] = dict(sorted(Counter(row['mountRole'] for row in files.values()).items()))
        require(phase_counts[phase] == declared['executableFilesByMountRole'], f'Early placement role differs for {phase}')
        early_carrier.update((path, row) for path, row in files.items() if row['mountRole'] == 'carrierSystem')

    plan, _, _ = load_plan()
    image_path = ROOT / image['path']
    require(image_path.is_relative_to(ROOT / 'out') and source.plain(image_path) == image_path,
            'Image path escaped repository output')
    named = source.identity(image_path.lstat())
    require(list(named) == image['identity'], 'Named image identity differs from whole-image readback')
    backing = prior['expectedCoreApexFiles']
    with image_path.open('rb') as stream:
        opened = source.identity(os.fstat(stream.fileno()))
        require(opened[:4] == named[:4], 'Opened image differs from held input')
        reader = Erofs(stream, image['bytes'], len(plan) + len(backing) + 1)
        require(reader.geometry == prior['geometry'], 'Carrier geometry differs')
        view = CarrierView(reader, plan, backing)
        files = {}
        for path in sorted(early_carrier.keys() | app_carrier.keys()):
            key, found = view.walk(path)
            require(found is not None and view.plan[key].kind == 'file', f'Missing carrier object {path}')
            nid, node = found
            pin = view.plan[key].payload['sha256']
            for rows in (early_carrier, app_carrier):
                if path in rows:
                    require((node.size, pin) == (rows[path]['bytes'], rows[path]['sha256']),
                            f'Carrier cohort disagrees at {path}')
            if path in app_carrier:
                require(nid == app_carrier[path]['source']['inode'], f'Carrier inode disagrees at {path}')
            if path in early_carrier:
                digest = sha256()
                for chunk in reader.chunks(node.spans):
                    digest.update(chunk)
                require(digest.hexdigest() == pin, f'Early carrier bytes disagree at {path}')
            require(node.links == 1, f'Carrier file link count differs at {path}')
            files[path] = {**record(nid, node), 'sha256': pin, 'earlyBytesRehashed': path in early_carrier}

        app_paths = {}
        for path, expected in APP_METADATA.items():
            found = view.nodes[(b'tree',)] if path == '/' else view.walk(path)[1]
            require(found is not None, f'Missing app reader path {path}')
            nid, node = found
            require((node.mode, node.uid, node.gid) == expected, f'App reader metadata differs at {path}')
            app_paths[path] = record(nid, node)
        aliases = graph['observedAliases']
        require(aliases[LINK] == '/apex/com.android.runtime/bin/linker64', 'App reader link target differs')
        for path, target in aliases.items():
            _, raw = view.file_bytes(path, 'symlink')
            require(raw == target.encode('ascii'), f'Carrier alias differs at {path}')
        empty = ['/apex', '/linkerconfig', '/vendor']
        for path in empty:
            key, found = view.walk(path)
            require(found is not None and not view.entries(key), f'Expected empty carrier directory at {path}')
        require(view.walk('/system/etc/ld.config.arm64.txt')[1] is None, 'Arch config shadows the expected branch')
        reader.check_geometry()
        require(source.identity(os.fstat(stream.fileno())) == opened
                and source.identity(image_path.lstat()) == named, 'Carrier changed during topology readback')

    return {
        'schema': 'oneos-guest-carrier-startup-topology/v1',
        'status': 'VERIFIED_SEALED_CARRIER_STARTUP_METADATA_ONLY',
        'inputs': [dict(zip(('path', 'sha256'), pin)) for pin in inputs],
        'carrierSha256': image['sha256'], 'guestProjection': '/tree',
        'earlyExecutableCounts': phase_counts, 'earlyCarrierObjectsRehashed': len(early_carrier),
        'appProcessCandidateCounts': dict(sorted(Counter(row['source']['kind'] for row in app.values()).items())),
        'carrierFilesByDirectory': dict(sorted(Counter(str(PurePosixPath(path).parent) for path in files).items())),
        'carrierFiles': files, 'appReaderMetadata': app_paths, 'carrierAliases': aliases,
        'emptyRawDirectories': empty, 'archConfigShadowAbsent': True, 'carrierMetadataReadBytes': reader.metadata_read,
        'wholeImageRehashed': False, 'effectiveMountsObserved': False, 'effectiveLabelsObserved': False,
        'effectiveNamespaceVerified': False, 'targetExecuted': False, 'deviceAction': False,
    }


if __name__ == '__main__':
    print(json.dumps(derive(), indent=2))
