"""Build and independently read back the unselected donor final-callback DEX."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
from uuid import uuid4
import zipfile

import build_guest_metrics_endpoint as runner
from check_guest_pin_final_callback_retarget import validate
from check_guest_pin_lifecycle_pools import SOURCE_APK_SHA, SOURCE_SHA, bounded, load_readers, symbolic
from prepare_guest_policy_init_retarget import DEXLIB, DEXLIB_SHA, JDK, JDK_PINS, owned, sha
from preserve_dex_code_headers import Dex039, _assert_byte_whitelist, digest, seal
from probe_samsung_framework_dex import ADAPTER_SOURCE


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'out/guest-pin-final-callback-retarget'
RAW = ROOT / 'firmware/guest-pin-final-callback-retarget'
APK = ROOT.parent / 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk'
JAVA_SOURCES = ('GuestPinFinalCallbackRetarget.java', 'GuestPolicyInitRetarget.java',
                'Probe-SamsungDex041.java', 'SecurityDexReader.java')
TASK = b'Lcom/oplus/keyguard/security/OplusLockPatternChecker$oplusCheckCredential$task$1;'
CUT = TASK + b'->onPostExecute(Ljava/lang/Object;)V'
BRIDGE_SOURCE = ('compat/guest-pin-final-callback/com/oplus/keyguard/security/GuestPinFinalCallbackBridge.java',
                 'a69df7691db8dcb61732fe6bbcd8aadb1251627b784b57f05e1e7ea669a39f3e')
HELPER_RECEIPT = ('out/guest-pin-final-callback-build/r-2fc9e372/receipt.json',
                  'df99ce1a80e32d7b245d9c26ff42ee5f54d6c075f61f5384381478bd39262b6f')
HELPER_DEX = ('out/guest-pin-final-callback-build/r-2fc9e372/dex/classes.dex',
              '892814d73cc9aeaf83cf368098cdd1f7a23c6235ca2c566ab7deee251c1f2ee7')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_donor(helper, definition_count=20):
    readers = load_readers()
    definitions = symbolic(readers['Dex'](helper), readers)['classes']
    require(len(definitions) == definition_count, 'Unexpected helper definition count')
    names = ['classes.dex', *(f'classes{index}.dex' for index in range(2, 10))]
    with APK.open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == SOURCE_APK_SHA, 'Donor APK differs')
        stream.seek(0)
        with zipfile.ZipFile(stream) as apk:
            entries = [entry for entry in apk.infolist() if '/' not in entry.filename
                       and entry.filename.startswith('classes') and entry.filename.endswith('.dex')]
            require(sorted(row.filename for row in entries) == sorted(names), 'Donor DEX members differ')
            source = None
            for entry in entries:
                require(112 <= entry.file_size <= 32 * 1024 * 1024, 'Donor DEX member size')
                raw = apk.read(entry)
                require(all(name + b'\0' not in raw for name in definitions), 'Helper name occurs in donor DEX')
                if entry.filename == 'classes3.dex':
                    source = raw
    require(source is not None and digest(source) == SOURCE_SHA, 'Donor classes3 differs')
    return source, len(names)


def restore_headers(source, emitted, frame_change=(CUT, (8, 2, 4, 0, 73), (8, 2, 5, 0, 73))):
    original, candidate = (Dex039(raw) for raw in (source, emitted))
    changed, original_frame, edited_frame = frame_change
    require(changed in original.methods, 'Original edited method is absent')
    wanted = {}
    for name, old in original.methods.items():
        actual = candidate.methods[name]
        if old['header'] is None:
            require(actual['header'] is None, 'Unexpected added original method body')
            continue
        expected = old['header']
        if name == changed:
            require(expected == original_frame, 'Original edited frame differs')
            expected = edited_frame
        header = actual['header']
        require(header is not None and header[:2] == expected[:2] and header[3:] == expected[3:],
                'Unexpected register, input, try or size difference')
        if name == changed:
            require(header[2] == edited_frame[2], 'Edited caller outgoing register count differs')
        offset = actual['codeOffset'] + 4
        prior = wanted.setdefault(offset, (header[2], expected[2]))
        require(prior == (header[2], expected[2]), 'Conflicting shared code header')
    changes = {offset: target for offset, (actual, target) in wanted.items() if actual != target}
    fixed = bytearray(emitted)
    for offset, value in changes.items():
        struct.pack_into('<H', fixed, offset, value)
    output = seal(fixed)
    _assert_byte_whitelist(emitted, output, changes)
    restored = Dex039(output)
    require(all(restored.u16(offset) == target for offset, (_, target) in wanted.items()),
            'Original outgoing register restoration differs')
    return output, {'checkedCodeItems': len(wanted), 'restoredOutgoingWords': len(changes),
                    'editedCallerOutgoingWords': edited_frame[2]}


def record(path, result):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


def prepare():
    receipt_raw = bounded(owned(ROOT / HELPER_RECEIPT[0], ROOT / 'out'), 256 * 1024)
    require(digest(receipt_raw) == HELPER_RECEIPT[1], 'Held final callback build receipt differs')
    helper_receipt = json.loads(receipt_raw)
    helper_path = owned(ROOT / HELPER_DEX[0], ROOT / 'out')
    helper_sha = HELPER_DEX[1]
    helper = bounded(helper_path, 64 * 1024)
    require(helper_receipt['status'] == 'PASS_UNSELECTED_PIN_FINAL_CALLBACK_SDK37_D8_ONLY'
            and helper_receipt['selected'] is False and helper_receipt['deviceEligible'] is False
            and helper_receipt['androidOrOemExecuted'] is False
            and helper_receipt['dex']['path'] == HELPER_DEX[0] and helper_receipt['dex']['sha256'] == helper_sha
            and helper_receipt['dex']['bytes'] == len(helper) and digest(helper) == helper_sha
            and sha(ROOT / BRIDGE_SOURCE[0]) == BRIDGE_SOURCE[1],
            'Pinned final-forwarder inputs differ')
    source, checked_dex = read_donor(helper)
    tools = {DEXLIB: DEXLIB_SHA, **{JDK / name: pin for name, pin in JDK_PINS.items()}}
    require(all(sha(path) == pin for path, pin in tools.items()), 'Pinned DEX toolchain differs')
    name = 'r-' + uuid4().hex[:8]
    work = owned(WORK / name, WORK)
    raw = owned(RAW / name, RAW)
    work.mkdir(parents=True)
    raw.mkdir(parents=True)
    for folder in ('classes', 'src', 'tmp', 'runtime-home'):
        (work / folder).mkdir()
    runner.WORK = WORK
    options = ['-Djava.io.tmpdir=' + str(work / 'tmp'), '-Duser.home=' + str(work / 'runtime-home')]
    adapter = work / 'src/SourcePreservingDexPool.java'
    adapter.write_text(ADAPTER_SOURCE, encoding='utf-8')
    original = raw / 'original-classes3.dex'
    emitted = raw / 'writer-classes3.dex'
    candidate_path = raw / 'disabled-classes3.dex'
    with original.open('xb') as stream:
        stream.write(source)
    source_paths = [ROOT / 'tools' / name for name in JAVA_SOURCES]
    source_pins = {path: sha(path) for path in source_paths}
    result = {'selected': False, 'deviceEligible': False, 'targetExecuted': False,
              'inputs': {'donorDexSha256': SOURCE_SHA, 'helperSha256': helper_sha,
                         'helper': HELPER_DEX[0], 'helperReceipt': HELPER_RECEIPT[0],
                         'helperReceiptSha256': HELPER_RECEIPT[1]},
              'writerSources': {path.name: pin for path, pin in source_pins.items()},
              'donorDexesCheckedForHelperNames': checked_dex}
    try:
        runner.run([JDK / 'javac.exe', *('-J' + option for option in options), '-proc:none',
                    '-implicit:none', '--release', '17', '-encoding', 'UTF-8',
                    '-cp', DEXLIB, '-d', work / 'classes', adapter, *source_paths], work, 'compile')
        execution = runner.run([JDK / 'java.exe', '-Xmx4g', *options, '-cp',
                                os.pathsep.join(map(str, (work / 'classes', DEXLIB))),
                                'GuestPinFinalCallbackRetarget', original, helper_path, helper_sha, emitted],
                               work, 'emit', timeout=180)
        summary = json.loads(execution['stdout'])
        candidate, headers = restore_headers(source, bounded(emitted))
        require(sha(emitted) == summary['outputSha256'] and sha(helper_path) == helper_sha
                and all(sha(path) == pin for path, pin in source_pins.items()), 'Writer inputs or bytes changed')
        proof = validate(source, helper, candidate)
        with candidate_path.open('xb') as stream:
            stream.write(candidate)
        result.update(status='PASS_UNSELECTED_DONOR_PIN_FINAL_CALLBACK_DEX_ONLY', writer=summary,
                      output=candidate_path.relative_to(ROOT).as_posix(), bytes=len(candidate),
                      outputSha256=digest(candidate), codeHeaders=headers, independentReadback=proof,
                      proposedDexPlacement={'classes3.dex': candidate_path.relative_to(ROOT).as_posix(),
                                            'classes10.dex': HELPER_DEX[0]})
    except (OSError, ValueError, KeyError) as error:
        result.update(status='FAILED_STATIC_DONOR_PIN_FINAL_CALLBACK', error=str(error))
        record(work / 'receipt.json', result)
        raise
    record(work / 'receipt.json', result)
    print(f"{result['status']} {work / 'receipt.json'}")


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
