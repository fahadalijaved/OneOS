#!/usr/bin/env python3
"""Assemble the held Activity lifecycle DEX into its unsigned tester APK."""

import hashlib
import io
import json
import uuid
import zipfile

from package_file_stage_early_exit_host import definition, require
from run_guest_tree_install_transport import ROOT, load_io, pinned, write_exclusive


BASE = ROOT / 'out/file-stage-activity-lifecycle-app-package'
PREVIOUS = ('out/file-stage-readiness-package/r-6c688c4ff1/receipt.json',
            '63892c552dee93bc017731ddd4aec8b0c51b7809bb472d54f6faaafc1bdecabb')
BUILD = ('out/file-stage-activity-lifecycle-build/r-ccef04ee/receipt.json',
         '55af5c0047cf3acf79ea3ff62433dbb91bb408b96f9fd714fc184592314b11d6')
ZIP_HELPER = ('tools/package_isolated_retained_view_app.py',
              '157cd576f4a2f6aeaf1e806e3c3bd8308c408c0a30a54bea6703a2124ae1f2c0')
DEX_HELPER = ('tools/check_guarded_stage_bundle.py',
              'c194b53cdf047c5fa8e03b78b1d17da3172fd843962e0a8f8954367022276da9')
PAYLOADS = ('AndroidManifest.xml', 'resources.arsc', 'classes.dex')
OFFSETS = (56, 2392, 2480)
APK_MAX = 256 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_payloads(blob):
    require(len(blob) <= APK_MAX, 'APK exceeds the tester archive bound')
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        entries = archive.infolist()
        require(tuple(entry.filename for entry in entries) == PAYLOADS,
                'Expected the exact three tester payloads in order')
        require(all(entry.compress_type == zipfile.ZIP_STORED and entry.flag_bits == 0
                    and entry.file_size == entry.compress_size <= APK_MAX for entry in entries)
                and sum(entry.file_size for entry in entries) <= APK_MAX,
                'Tester payloads must be bounded, stored and unflagged')
        return {entry.filename: archive.read(entry) for entry in entries}


def package():
    checked = load_io()

    def read_receipt(pin):
        return json.loads(pinned(checked, *pin, 128 * 1024),
                          object_pairs_hook=checked['unique_object'])

    def read_artifact(row):
        require(0 < row['bytes'] <= APK_MAX, 'Artifact size exceeds bound')
        data = pinned(checked, row['path'], row['sha256'], row['bytes'])
        require(len(data) == row['bytes'], 'Artifact size differs from receipt')
        return data

    previous = read_receipt(PREVIOUS)
    build = read_receipt(BUILD)
    require(previous['status'] == 'PASS_PC_MATCHED_READINESS_APKS_AND_PROFILE_ONLY'
            and build['status'] == 'PASS_UNSELECTED_FILE_STAGE_ACTIVITY_LIFECYCLE_APP_SDK37_DEX_ONLY'
            and build['predecessorReceipt'] == previous['buildReceipt']
            and all(build[field] is False for field in
                    ('selected', 'deviceEligible', 'signed', 'androidOrOemExecuted')),
            'Lifecycle build provenance differs')
    app = previous['packages']['app']
    old_apk = read_artifact(app['unsignedApk'])
    new_dex = read_artifact(build['dex'])
    original = read_payloads(old_apk)
    require({name: digest(data) for name, data in original.items()} == app['payloadPins'],
            'Predecessor payload pins differ')
    old_dex = original['classes.dex']
    require(digest(old_dex) == app['dex']['sha256'] and new_dex != old_dex,
            'Unexpected old or unchanged DEX')

    zip_source = pinned(checked, *ZIP_HELPER, 64 * 1024)
    write_zip = definition(zip_source, ZIP_HELPER[0], 'aligned_zip')
    read_zip = definition(zip_source, ZIP_HELPER[0], 'stored_zip')
    read_dex = definition(pinned(checked, *DEX_HELPER, 64 * 1024), DEX_HELPER[0], 'Dex')
    before, _ = read_zip(old_apk, original)
    require(write_zip(original) == old_apk, 'Predecessor canonical layout differs')
    old_defs = sorted(name.decode('ascii') for name in read_dex(old_dex).classes)
    new_defs = sorted(name.decode('ascii') for name in read_dex(new_dex).classes)
    require(len(new_defs) == 30 and new_defs == old_defs
            and old_defs == sorted(app['dex']['definitions'])
            and new_defs == sorted(build['dex']['definitions']), 'Tester DEX definitions differ')

    replacement = {**original, 'classes.dex': new_dex}
    apk = write_zip(replacement)
    observed = read_payloads(apk)
    require(observed == replacement, 'Packed bytes differ from the held payloads')
    rows, central = read_zip(apk, replacement)
    require(tuple(row['data'] for row in before) == tuple(row['data'] for row in rows) == OFFSETS
            and [row['extra'] for row in rows] == [row['extra'] for row in before]
            and central == OFFSETS[-1] + len(new_dex) and len(apk) - central == 204,
            'Unsigned tester layout differs')
    require(write_zip({**observed, 'classes.dex': old_dex}) == old_apk,
            'Exact predecessor inverse failed')

    checked['checked_path'](BASE.parent, directory=True)
    BASE.mkdir(exist_ok=True)
    checked['checked_path'](BASE, directory=True)
    run = BASE / f'r-{uuid.uuid4().hex[:8]}'
    run.mkdir()
    apk_path = run / 'OneOS-File-View-Prep-Activity-Lifecycle-unsigned.apk'
    write_exclusive(apk_path, apk)
    with checked['checked_input'](apk_path, size=len(apk)) as stream:
        require(stream.read(len(apk) + 1) == apk, 'Saved APK readback differs')

    receipt = {
        'schema': 'oneos-file-stage-activity-lifecycle-app-package/v1',
        'status': 'PASS_UNSELECTED_ACTIVITY_LIFECYCLE_UNSIGNED_TESTER_APK',
        'selected': False,
        'deviceEligible': False,
        'signed': False,
        'androidOrOemExecuted': False,
        'deviceAction': False,
        'identityFromPreservedManifest': {key: app[key] for key in
                                          ('package', 'versionCode', 'versionName', 'minSdk', 'targetSdk')},
        'predecessorReceipt': dict(zip(('path', 'sha256'), PREVIOUS)),
        'predecessorUnsignedApk': app['unsignedApk'],
        'buildReceipt': dict(zip(('path', 'sha256'), BUILD)),
        'dex': build['dex'],
        'helpers': dict((ZIP_HELPER, DEX_HELPER)),
        'unsignedApk': {'path': apk_path.relative_to(ROOT).as_posix(), 'bytes': len(apk), 'sha256': digest(apk)},
        'layout': {
            'payloadPins': {name: digest(data) for name, data in observed.items()},
            'dataOffsets': {row['name']: row['data'] for row in rows},
            'centralDirectoryOffset': central,
            'predecessorInverseExact': True,
            'signatureGapAbsent': True,
            'definitionCount': len(new_defs),
        },
        'historicalProtectedProfile': previous['profile']['payload'],
        'protectedProfileCarriesForward': False,
        'matchedProfileOrPublisherCreated': False,
    }
    path = run / 'receipt.json'
    write_exclusive(path, (json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    print(path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    package()
