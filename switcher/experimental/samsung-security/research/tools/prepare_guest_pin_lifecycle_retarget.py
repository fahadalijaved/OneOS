"""Emit and check one disabled, unselected ColorOS lifecycle DEX on the PC."""

import argparse
import json
import os
from pathlib import Path
import struct
from uuid import uuid4

import build_guest_metrics_endpoint as runner
from check_guest_pin_lifecycle_bridge_body import verify_bridge
from check_guest_pin_lifecycle_call_sites import check
from check_guest_pin_lifecycle_pools import bounded, source_input, validate
from prepare_guest_policy_init_retarget import DEXLIB, DEXLIB_SHA, JDK, JDK_PINS, owned, sha
from preserve_dex_code_headers import Dex039, _assert_byte_whitelist, digest, seal
from probe_samsung_framework_dex import ADAPTER_SOURCE


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'out/guest-pin-lifecycle-retarget'
RAW = ROOT / 'firmware/guest-pin-lifecycle-retarget'
APK = ROOT.parent / 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk'
HELPER = ROOT / 'out/guest-pin-systemui-lifecycle-relocated-build/r-c89ebd7b/dex/classes.dex'
HELPER_SHA = '2a22b567f46f7b6d3beee281f0c99f52de4359e1debd23773f5cf89752a81e4f'
JAVA_SOURCES = (
    'GuestPinLifecycleRetarget.java', 'GuestPolicyInitRetarget.java',
    'Probe-SamsungDex041.java', 'SecurityDexReader.java',
)
CONTROLLER = b'Lcom/oplus/keyguard/security/view/OplusKeyguardAbsKeyInputViewController;'
CUTS = {CONTROLLER + b'->onPause()V', CONTROLLER + b'->verifyPasswordAndUnlock()V'}


def restore_outgoing_words(source, helper, emitted):
    """Retain original code headers after dexlib recalculates outgoing words."""
    original, addition, candidate = (Dex039(raw) for raw in (source, helper, emitted))
    originals = original.methods | addition.methods
    if len(originals) != len(original.methods) + len(addition.methods) or not CUTS <= originals.keys():
        raise ValueError('Unexpected original or helper method identities')
    wanted = {}
    for name, old in originals.items():
        new = candidate.methods[name]
        if old['header'] is None:
            if new['header'] is not None:
                raise ValueError('Unexpected added code on a held method')
            continue
        expected = list(old['header'])
        if name in CUTS:
            expected[-1] += 3
        actual = new['header']
        if actual is None or actual[:2] != tuple(expected[:2]) or actual[3:] != tuple(expected[3:]):
            raise ValueError('Unexpected non-outgoing code header difference')
        offset = new['codeOffset'] + 4
        previous = wanted.setdefault(offset, (actual[2], expected[2]))
        if previous != (actual[2], expected[2]):
            raise ValueError('Shared code has conflicting original outgoing words')
    changes = {offset: target for offset, (actual, target) in wanted.items() if actual != target}
    revised = bytearray(emitted)
    for offset, value in changes.items():
        struct.pack_into('<H', revised, offset, value)
    output = seal(revised)
    _assert_byte_whitelist(emitted, output, changes)
    restored = Dex039(output)
    if any(restored.u16(offset) != target for offset, (_, target) in wanted.items()):
        raise ValueError('Restored outgoing words differ from original frames')
    return output, {'checkedCodeItems': len(wanted), 'restoredOutgoingWords': len(changes)}


def record(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def prepare():
    source = source_input(APK)
    if HELPER.stat().st_size != 12444 or sha(HELPER) != HELPER_SHA:
        raise ValueError('Exact checked relocated helper is required')
    tools = {DEXLIB: DEXLIB_SHA, **{JDK / name: pin for name, pin in JDK_PINS.items()}}
    if any(sha(path) != pin for path, pin in tools.items()):
        raise ValueError('Pinned existing DEX toolchain differs')
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
    original.write_bytes(source)
    emitted = raw / 'writer-classes3.dex'
    output = raw / 'disabled-classes3.dex'
    source_paths = [ROOT / 'tools' / name for name in JAVA_SOURCES]
    source_pins = {path: sha(path) for path in source_paths}
    result = {'selected': False, 'deviceEligible': False, 'targetExecuted': False,
              'inputs': {'originalSha256': sha(original), 'helperSha256': HELPER_SHA},
              'writerSources': {path.name: pin for path, pin in source_pins.items()}}
    try:
        runner.run([JDK / 'javac.exe', *('-J' + option for option in options), '-proc:none',
                    '-implicit:none', '--release', '17', '-encoding', 'UTF-8',
                    '-cp', DEXLIB, '-d', work / 'classes', adapter, *source_paths], work, 'compile')
        execution = runner.run([JDK / 'java.exe', '-Xmx4g', *options, '-cp',
                                os.pathsep.join(map(str, (work / 'classes', DEXLIB))),
                                'GuestPinLifecycleRetarget', original, HELPER, emitted], work, 'emit', timeout=180)
        summary = json.loads(execution['stdout'])
        if sha(emitted) != summary['outputSha256'] or any(sha(path) != pin for path, pin in source_pins.items()):
            raise ValueError('Output or authored compiler inputs differ')
        helper = bounded(HELPER, limit=12444)
        candidate, headers = restore_outgoing_words(source, helper, bounded(emitted))
        result.update(status='PASS_DISABLED_DONOR_PIN_LIFECYCLE_DEX_ONLY',
                      output=output.relative_to(ROOT).as_posix(), bytes=len(candidate), writer=summary,
                      outputSha256=digest(candidate), codeHeaders=headers,
                      callSites=check(source, candidate), bridge=verify_bridge(candidate),
                      pools=validate(source, helper, candidate))
        with output.open('xb') as stream:
            stream.write(candidate)
    except (OSError, ValueError) as error:
        result.update(status='FAILED_STATIC_DONOR_PIN_LIFECYCLE', error=str(error))
        record(work / 'receipt.json', result)
        raise
    record(work / 'receipt.json', result)
    print(f"{result['status']} {work / 'receipt.json'}")


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
