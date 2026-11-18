#!/usr/bin/env python3
"""Assemble the reviewed early-exit host DEX into its unsigned APK template."""

import ast
import hashlib
import io
import json
import stat
import struct
import uuid
import zipfile
import zlib

from run_guest_tree_install_transport import ROOT, load_io, pinned, write_exclusive


PREVIOUS = ('out/file-stage-readiness-package/r-6c688c4ff1/receipt.json',
            '63892c552dee93bc017731ddd4aec8b0c51b7809bb472d54f6faaafc1bdecabb')
BUILD = ('out/file-stage-early-exit-host-dex/r-cbc36dc3/receipt.json',
         'df536331acbc472ec8159b588457777a81b0b739d7c513eaffcdd819933ecee0')
CHECK = ('out/file-stage-early-exit-host-dex/r-cbc36dc3/saved-output-check.json',
         'db50b0b978886c98264b7e02022ef026ef3a14f78a949d5043a08166074684c1')
WRITER = ('tools/package_isolated_retained_view_app.py',
          '157cd576f4a2f6aeaf1e806e3c3bd8308c408c0a30a54bea6703a2124ae1f2c0')
READER = ('tools/package_retained_view_ingress_host.py',
          '93c5d35c28a29ee9bcd09d6bafba1dd1cc84468ec76be2074d5f9568f3a0d4f1')
DEX_READER = ('tools/check_guarded_stage_bundle.py',
              'c194b53cdf047c5fa8e03b78b1d17da3172fd843962e0a8f8954367022276da9')
DEX_SHA = 'f4f378a8017aabfee9fdc09410439e4dcec6bcb7bc8eaf8d742dc2bc0bf1b36f'
DEX_SIZE = 133004
PAYLOADS = ('AndroidManifest.xml', 'resources.arsc', 'classes.dex',
            'META-INF/xposed/module.prop', 'META-INF/xposed/scope.list',
            'META-INF/xposed/java_init.list')
APK_MAX = 256 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def definition(raw, filename, name):
    tree = ast.parse(raw, filename=filename)
    nodes = [node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name]
    require(len(nodes) == 1, f'Expected one pinned definition: {name}')
    scope = {'require': require, 'struct': struct, 'stat': stat,
             'zipfile': zipfile, 'zlib': zlib, 'hashlib': hashlib}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, 'exec'), scope)
    return scope[name]


def read_payloads(blob):
    require(len(blob) <= APK_MAX, 'APK exceeds the host archive bound')
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            entries = archive.infolist()
            require(tuple(entry.filename for entry in entries) == PAYLOADS,
                    'Host APK must contain the six reviewed payloads in order')
            require(all(entry.compress_type == zipfile.ZIP_STORED and entry.flag_bits == 0
                        and entry.file_size == entry.compress_size <= APK_MAX for entry in entries)
                    and sum(entry.file_size for entry in entries) <= APK_MAX,
                    'Host payloads must be bounded, stored and unflagged')
            return {entry.filename: archive.read(entry) for entry in entries}
    except zipfile.BadZipFile as error:
        raise ValueError('Invalid host ZIP records') from error


def compose_host_apk(predecessor, successor_dex, payload_pins):
    require(len(successor_dex) == DEX_SIZE and sha(successor_dex) == DEX_SHA,
            'Expected the reviewed full successor host DEX')
    original = read_payloads(predecessor)
    require({name: sha(data) for name, data in original.items()} == payload_pins,
            'Predecessor payload pins differ')

    checked = load_io()
    writer_source = pinned(checked, *WRITER, 64 * 1024)
    # Same cardinality adjustment as the reviewed six-entry readiness recipe.
    old_counts = b'0, 0, 3, 3, len(directory)'
    require(writer_source.count(old_counts) == 1, 'Expected literal EOCD entry counts')
    writer_source = writer_source.replace(old_counts, b'0, 0, len(payloads), len(payloads), len(directory)', 1)
    write_zip = definition(writer_source, WRITER[0], 'aligned_zip')
    read_zip = definition(pinned(checked, *READER, 64 * 1024), READER[0], 'stored_zip')
    read_dex = definition(pinned(checked, *DEX_READER, 64 * 1024), DEX_READER[0], 'Dex')
    read_zip(predecessor, original)
    require(write_zip(original) == predecessor, 'Predecessor is not the exact canonical unsigned layout')
    old_dex = original['classes.dex']
    definitions = read_dex(successor_dex).classes
    require(len(definitions) == 48 and definitions.keys() == read_dex(old_dex).classes.keys(),
            'Host DEX definitions differ')

    replacement = dict(original)
    replacement['classes.dex'] = successor_dex
    apk = write_zip(replacement)
    observed = read_payloads(apk)
    rows, central = read_zip(apk, observed)
    require(observed == replacement and all(row['data'] % 4 == 0 for row in rows),
            'Packed bytes or alignment differ')
    observed['classes.dex'] = old_dex
    require(write_zip(observed) == predecessor, 'Exact predecessor inverse failed')
    return apk, {
        'payloadPins': {name: sha(data) for name, data in replacement.items()},
        'dataOffsets': {row['name']: row['data'] for row in rows},
        'centralDirectoryOffset': central,
        'predecessorDexSha256': sha(old_dex),
        'dexDefinitions': len(definitions),
    }


def package():
    checked = load_io()

    def read_receipt(pin):
        return json.loads(pinned(checked, *pin, 128 * 1024),
                          object_pairs_hook=checked['unique_object'])

    def artifact_bytes(record, maximum):
        require(0 < record['bytes'] <= maximum, 'Artifact size exceeds bound')
        data = pinned(checked, record['path'], record['sha256'], record['bytes'])
        require(len(data) == record['bytes'], 'Artifact size differs from receipt')
        return data

    previous, build, check = (read_receipt(pin) for pin in (PREVIOUS, BUILD, CHECK))
    require(build['status'] == 'PASS_UNSELECTED_EARLY_EXIT_FULL_HOST_DEX'
            and all(build[field] is False for field in ('selected', 'deviceEligible', 'signed', 'apkBuilt',
                                                        'androidOrOemCodeExecuted', 'deviceAction'))
            and build['readinessReceiptSha256'] == previous['buildReceipt']['sha256'],
            'Full host build provenance differs')
    require(check['status'] == 'PASS_SAVED_HOST_DEX_DEFINITION_AND_MEMBER_UNION'
            and (check['receiptSha256'], check['dexSha256']) == (BUILD[1], DEX_SHA)
            and (check['definitions'], check['members'], check['compilerAbiDefinitions']) == (48, 962, 0),
            'Independent full host DEX readback differs')
    host = previous['packages']['host']
    old_apk = artifact_bytes(host['unsignedApk'], APK_MAX)
    new_dex = artifact_bytes(build['dex'], APK_MAX)
    apk, layout = compose_host_apk(old_apk, new_dex, host['payloadPins'])
    require(layout['predecessorDexSha256'] == host['dex']['sha256'],
            'Unsigned template DEX differs from the common build')

    same_inputs = {
        'testerApk': previous['packages']['app']['apk'],
        'controller': previous['controller'],
        'protectedProfile': previous['profile']['payload'],
    }
    artifact_bytes(same_inputs['testerApk'], APK_MAX)
    artifact_bytes(same_inputs['controller'], 1024 * 1024)
    artifact_bytes(same_inputs['protectedProfile'], 4096)

    out = ROOT / 'out'
    checked['checked_path'](out, directory=True)
    base = out / 'file-stage-early-exit-host-package'
    base.mkdir(exist_ok=True)
    checked['checked_path'](base, directory=True)
    run = base / f'r-{uuid.uuid4().hex[:8]}'
    run.mkdir()
    apk_path = run / 'OneOS-File-View-Host-Early-Exit-unsigned.apk'
    write_exclusive(apk_path, apk)
    with checked['checked_input'](apk_path, size=len(apk)) as stream:
        require(stream.read(len(apk) + 1) == apk, 'Saved APK readback differs')

    receipt = {
        'schema': 'file-stage-early-exit-host-package/v1',
        'status': 'PASS_UNSELECTED_EARLY_EXIT_UNSIGNED_HOST_APK',
        'selected': False,
        'deviceEligible': False,
        'signed': False,
        'androidOrOemCodeExecuted': False,
        'deviceAction': False,
        'hostIdentityFromPreservedManifest': {key: host[key] for key in
                                              ('package', 'versionCode', 'versionName', 'minSdk', 'targetSdk')},
        'predecessorReceiptSha256': PREVIOUS[1],
        'predecessorUnsignedApk': host['unsignedApk'],
        'fullDexReceiptSha256': BUILD[1],
        'fullDexReadbackSha256': CHECK[1],
        'dexSha256': DEX_SHA,
        'unsignedApk': {'path': apk_path.relative_to(ROOT).as_posix(), 'bytes': len(apk), 'sha256': sha(apk)},
        'layout': layout,
        'unchangedHistoricalInputs': same_inputs,
    }
    path = run / 'receipt.json'
    write_exclusive(path, (json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    print(path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    package()
