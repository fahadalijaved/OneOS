"""Emit and independently read back a standalone Settings preference-bind cut."""

import argparse
import hashlib
import json
import os
from uuid import uuid4
from zipfile import ZipFile

import build_guest_metrics_endpoint as runner
from build_coloros_settings_rpmb_leaf import SOURCE, SOURCE_SHA
from check_guest_fingerprint_preference_bind_retarget import validate
from prepare_guest_pin_final_callback_retarget import (
    ADAPTER_SOURCE, DEXLIB, DEXLIB_SHA, JDK, JDK_PINS, ROOT,
    bounded, digest, owned, record, require, restore_headers, sha,
)
from prepare_guest_pin_worker_return_retarget import held
from run_full_apk_build import dex_defined_classes


WORK = ROOT / 'out/guest-fingerprint-preference-bind-retarget'
RAW = ROOT / 'firmware/guest-fingerprint-preference-bind-retarget'
OWNER = b'Lcom/oplus/settings/feature/fingerprint/OplusFingerprintSettings$FingerprintSettingsFragment;'
CUT = OWNER + b'->onCreatePreferences(Landroid/os/Bundle;Ljava/lang/String;)V'
FRAME = (CUT, (3, 3, 3, 0, 67), (3, 3, 3, 0, 67))
SOURCE_DEX_SHA = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
WRITER = 'GuestFingerprintPreferenceBindRetarget'
JAVA_SOURCES = (WRITER + '.java', 'GuestPolicyInitRetarget.java',
                'Probe-SamsungDex041.java', 'SecurityDexReader.java')
HELPER_RECEIPT = ('out/fingerprint-enrollment-preference-bind-capture-build/r-cc879d09/receipt.json',
                  '110a9643e81b80016d220ec067dcbc411e571ef01e9fea320af9ded861cb8148')
HELPER_DEX = ('out/fingerprint-enrollment-preference-bind-capture-build/r-cc879d09/dex/classes.dex',
              '0ada17826b7090664972731fa75a6fd61e31a3a440f3f32ddcdb572e17c4b8b3')
BRIDGE_SOURCE = ('out/fingerprint-enrollment-preference-bind-capture-build/r-cc879d09/src/'
                 'FingerprintEnrollmentPreferenceBindCapture.java',
                 '15566fa9f1e124f0088d6cded0ac7f186fa4ff7ab06aadbf9143151fd1078969')
OWNER_BUILD = 'out/fingerprint-enrollment-preference-retirement-build/r-fc479fc4'
OWNER_RECEIPT = (OWNER_BUILD + '/receipt.json',
                 'fcf6ee4be75f58417a07643cd5a3e78e5e713e7b9611c1313cb6a4b29a797dea')
OWNER_DEX = (OWNER_BUILD + '/dex/classes.dex',
             '37facf79e09b94e23c996c4bdca16f52af524be4c70bcd037f890ad7ba1fcaf0')
OWNER_SOURCE = (OWNER_BUILD + '/src/FingerprintEnrollmentPreferenceBindCapture.java',
                'd717138163ca4afa7876fc9a6806e27cc9c01a078fb5a4f9d373a4a40a02d61b')
ACCESS_BUILD = 'out/fingerprint-enrollment-preference-feed-binding-build/r-16944ab9'
ACCESS_RECEIPT = (ACCESS_BUILD + '/receipt.json',
                  'c7130ca618de1ce0997e89381088318e237d2f0e0a30c48698532421f3135b40')
ACCESS_DEX = (ACCESS_BUILD + '/dex/classes.dex',
              'c99ab1eb24bb3abf4e93f7029ad726bf28202c5aa206df191001d52984b9bc19')
ACCESS_SOURCE = (ACCESS_BUILD + '/src/FingerprintEnrollmentPreferenceBindCapture.java',
                 '361d6898c875461736fe33e136a229e456fc15f186ff71b23745622cffcfdce7')


def read_source(helper, helper_count=14):
    additions = dex_defined_classes(helper)
    require(len(additions) == helper_count, 'Unexpected helper definition count')
    expected = {'classes.dex', *(f'classes{index}.dex' for index in range(2, 15))}
    donors = set()
    source = None
    with SOURCE.open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == SOURCE_SHA, 'Held Settings APK differs')
        stream.seek(0)
        with ZipFile(stream) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)) == 10549, 'Held Settings APK member inventory differs')
            root_dexes = [name for name in names if '/' not in name and name.endswith('.dex')]
            require(set(root_dexes) == expected, 'Held Settings APK DEX members differ')
            for name in root_dexes:
                require(112 <= archive.getinfo(name).file_size <= 32 * 1024 * 1024, 'Settings DEX extent differs')
                raw = archive.read(name)
                classes = dex_defined_classes(raw)
                require(not classes & (donors | additions), 'Duplicate donor or helper class definition')
                donors.update(classes)
                if name == 'classes2.dex':
                    source = raw
    require(len(donors) == 78960 and source is not None and len(source) == 5737616
            and digest(source) == SOURCE_DEX_SHA, 'Exact donor Settings classes2 or definition count differs')
    return source, len(expected), len(donors)


def prepare(fragment_owned=False, *, source_access=False):
    require(not (fragment_owned and source_access), 'Expected exactly one optional retarget mode')
    if source_access:
        receipt_pin, dex_pin, source_pin = ACCESS_RECEIPT, ACCESS_DEX, ACCESS_SOURCE
        expected_status = 'PASS_UNSELECTED_FINGERPRINT_ENROLLMENT_PREFERENCE_FEED_BINDING_SDK37_D8_ONLY'
        output_status = 'PASS_UNSELECTED_DONOR_FINGERPRINT_PREFERENCE_SOURCE_ACCESS_DEX_ONLY'
        work_base = ROOT / 'out/guest-fingerprint-preference-source-access-retarget'
        raw_base = ROOT / 'firmware/guest-fingerprint-preference-source-access-retarget'
        helper_count = 27
        output_name = 'source-access-classes2.dex'
        mode = ['--source-access']
    elif fragment_owned:
        receipt_pin, dex_pin, source_pin = OWNER_RECEIPT, OWNER_DEX, OWNER_SOURCE
        expected_status = 'PASS_UNSELECTED_FINGERPRINT_ENROLLMENT_PREFERENCE_RETIREMENT_SDK37_D8_ONLY'
        output_status = 'PASS_UNSELECTED_DONOR_FINGERPRINT_PREFERENCE_OWNER_DEX_ONLY'
        work_base = ROOT / 'out/guest-fingerprint-preference-owner-retarget'
        raw_base = ROOT / 'firmware/guest-fingerprint-preference-owner-retarget'
        helper_count = 17
        output_name = 'fragment-owned-classes2.dex'
        mode = ['--fragment-owned']
    else:
        receipt_pin, dex_pin, source_pin = HELPER_RECEIPT, HELPER_DEX, BRIDGE_SOURCE
        expected_status = 'PASS_UNSELECTED_FINGERPRINT_ENROLLMENT_PREFERENCE_BIND_CAPTURE_SDK37_D8_ONLY'
        output_status = 'PASS_UNSELECTED_DONOR_FINGERPRINT_PREFERENCE_BIND_DEX_ONLY'
        work_base, raw_base = WORK, RAW
        helper_count = 14
        output_name = 'disabled-classes2.dex'
        mode = []
    _, raw_receipt = held(receipt_pin, 256 * 1024)
    helper_receipt = json.loads(raw_receipt)
    helper_path, helper = held(dex_pin, 64 * 1024)
    held(source_pin, 16 * 1024)
    require(helper_receipt['status'] == expected_status
            and helper_receipt['selected'] is False and helper_receipt['deviceEligible'] is False
            and helper_receipt['androidOrOemRuntimeExecuted'] is False
            and helper_receipt['dex']['path'] == dex_pin[0] and helper_receipt['dex']['sha256'] == dex_pin[1]
            and helper_receipt['dex']['bytes'] == len(helper), 'Held bind-capture helper proof differs')
    source, source_members, source_definitions = read_source(helper, helper_count)
    tools = {DEXLIB: DEXLIB_SHA, **{JDK / name: pin for name, pin in JDK_PINS.items()}}
    require(all(sha(path) == pin for path, pin in tools.items()), 'Pinned DEX toolchain differs')
    name = 'r-' + uuid4().hex[:8]
    work, raw = owned(work_base / name, work_base), owned(raw_base / name, raw_base)
    work.mkdir(parents=True)
    raw.mkdir(parents=True)
    for folder in ('classes', 'src', 'tmp', 'runtime-home'):
        (work / folder).mkdir()
    runner.WORK = work_base
    options = ['-Djava.io.tmpdir=' + str(work / 'tmp'), '-Duser.home=' + str(work / 'runtime-home')]
    adapter = work / 'src/SourcePreservingDexPool.java'
    adapter.write_text(ADAPTER_SOURCE, encoding='utf-8')
    original = raw / 'original-classes2.dex'
    emitted = raw / 'writer-classes2.dex'
    output = raw / output_name
    with original.open('xb') as stream:
        stream.write(source)
    source_paths = [ROOT / 'tools' / item for item in JAVA_SOURCES]
    source_pins = {path: sha(path) for path in source_paths}
    result = {'selected': False, 'deviceEligible': False, 'targetExecuted': False,
              'inputs': dict((receipt_pin, dex_pin, source_pin)), 'donorApkSha256': SOURCE_SHA,
              'donorDexSha256': SOURCE_DEX_SHA, 'donorDexMembers': source_members,
              'donorClassDefinitions': source_definitions,
              'writerSources': {path.name: pin for path, pin in source_pins.items()}}
    try:
        runner.run([JDK / 'javac.exe', *('-J' + option for option in options), '-proc:none',
                    '-implicit:none', '--release', '17', '-encoding', 'UTF-8',
                    '-cp', DEXLIB, '-d', work / 'classes', adapter, *source_paths], work, 'compile')
        execution = runner.run([JDK / 'java.exe', '-Xmx4g', *options, '-cp',
                                os.pathsep.join(map(str, (work / 'classes', DEXLIB))),
                                WRITER, original, helper_path, dex_pin[1], emitted, *mode], work, 'emit', timeout=180)
        summary = json.loads(execution['stdout'])
        candidate, headers = restore_headers(source, bounded(emitted), FRAME)
        require(sha(emitted) == summary['outputSha256'] and sha(original) == SOURCE_DEX_SHA
                and sha(helper_path) == dex_pin[1] and all(sha(path) == pin for path, pin in source_pins.items()),
                'Writer inputs or bytes changed')
        proof = validate(source, helper, candidate, fragment_owned=fragment_owned, source_access=source_access)
        with output.open('xb') as stream:
            stream.write(candidate)
        output_rel = output.relative_to(ROOT).as_posix()
        result.update(status=output_status, writer=summary,
                      output=output_rel, bytes=len(candidate), outputSha256=digest(candidate),
                      codeHeaders=headers, independentReadback=proof,
                      proposedDexPlacement={'classes2.dex': output_rel, 'classes15.dex': dex_pin[0]})
    except (OSError, ValueError, KeyError) as error:
        result.update(status='FAILED_STATIC_DONOR_FINGERPRINT_PREFERENCE_BIND', error=str(error))
        record(work / 'receipt.json', result)
        raise
    record(work / 'receipt.json', result)
    print(f"{result['status']} {work / 'receipt.json'}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--fragment-owned', action='store_true', help='Emit the standalone fragment-owned variant')
    modes.add_argument('--source-access', action='store_true', help='Emit the standalone source-access variant')
    args = parser.parse_args()
    prepare(args.fragment_owned, source_access=args.source_access)
