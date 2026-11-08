"""Emit and read back the unselected split donor worker-return DEX."""

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

import build_guest_metrics_endpoint as runner
from check_guest_pin_worker_return_retarget import validate
from prepare_guest_pin_final_callback_retarget import (
    ADAPTER_SOURCE, DEXLIB, DEXLIB_SHA, JDK, JDK_PINS, ROOT, TASK,
    bounded, digest, owned, read_donor, record, require, restore_headers, sha,
)


WORK = ROOT / 'out/guest-pin-worker-return-retarget'
RAW = ROOT / 'firmware/guest-pin-worker-return-retarget'
WORKER = TASK + b'->doInBackground([Ljava/lang/Object;)Ljava/lang/Object;'
FRAME_CHANGE = (WORKER, (8, 2, 4, 1, 77), (8, 2, 4, 1, 85))
WRITER = 'GuestPinWorkerReturnRetarget'
JAVA_SOURCES = (WRITER + '.java', 'GuestPolicyInitRetarget.java',
                'Probe-SamsungDex041.java', 'SecurityDexReader.java')
BASE_RECEIPT = ('out/guest-pin-final-callback-retarget/r-a9085108/receipt.json',
                '4030536a675a6c31bda6a23f50f914aff55e0d65420db74ea68aa1a6741de239')
BASE_DEX = ('firmware/guest-pin-final-callback-retarget/r-a9085108/disabled-classes3.dex',
            '8235ff3c6dce66faf81a1761cbfda9843c40d2ab0ebdbfd9b8d7a9fc365b96e4')
HELPER_RECEIPT = ('out/guest-pin-final-callback-build/r-32a284d7/receipt.json',
                  'c0b1df054f8f9d36c621bc03220d21ef2789555eed9203162ae0d35291a8dd40')
HELPER_DEX = ('out/guest-pin-final-callback-build/r-32a284d7/dex/classes.dex',
              'fa8acc549e57ece7892073e60675d764df80d48bd02dbec5e165cf5bb29f2a98')
BRIDGE_SOURCE = ('compat/guest-pin-final-callback/com/oplus/keyguard/security/GuestPinWorkerReturnBridge.java',
                 'a16f47f0d37264f23fe6484bff19c7a4d45c808fba657e9440c8af8476ce394b')


def held(pin, limit):
    name, expected = pin
    path = owned(ROOT / name, ROOT / Path(name).parts[0])
    raw = bounded(path, limit)
    require(digest(raw) == expected, 'Pinned input differs: ' + name)
    return path, raw


def prepare():
    _, raw_base_receipt = held(BASE_RECEIPT, 256 * 1024)
    _, raw_helper_receipt = held(HELPER_RECEIPT, 256 * 1024)
    base_receipt, helper_receipt = json.loads(raw_base_receipt), json.loads(raw_helper_receipt)
    source_path, source = held(BASE_DEX, 16 * 1024 * 1024)
    helper_path, helper = held(HELPER_DEX, 64 * 1024)
    held(BRIDGE_SOURCE, 16 * 1024)
    require(base_receipt['status'] == 'PASS_UNSELECTED_DONOR_PIN_FINAL_CALLBACK_DEX_ONLY'
            and base_receipt['selected'] is False and base_receipt['deviceEligible'] is False
            and base_receipt['targetExecuted'] is False and base_receipt['bytes'] == len(source)
            and base_receipt['output'] == BASE_DEX[0] and base_receipt['outputSha256'] == BASE_DEX[1],
            'Unselected final callback predecessor differs')
    require(helper_receipt['status'] == 'PASS_UNSELECTED_PIN_FINAL_CALLBACK_WORKER_SDK37_D8_ONLY'
            and helper_receipt['selected'] is False and helper_receipt['deviceEligible'] is False
            and helper_receipt['androidOrOemExecuted'] is False and helper_receipt['dex']['bytes'] == len(helper)
            and helper_receipt['dex']['path'] == HELPER_DEX[0] and helper_receipt['dex']['sha256'] == HELPER_DEX[1],
            'Unselected worker helper cohort differs')
    _, checked_dex = read_donor(helper, definition_count=21)
    tools = {DEXLIB: DEXLIB_SHA, **{JDK / name: pin for name, pin in JDK_PINS.items()}}
    require(all(sha(path) == pin for path, pin in tools.items()), 'Pinned DEX toolchain differs')
    name = 'r-' + uuid4().hex[:8]
    work, raw = owned(WORK / name, WORK), owned(RAW / name, RAW)
    work.mkdir(parents=True)
    raw.mkdir(parents=True)
    for folder in ('classes', 'src', 'tmp', 'runtime-home'):
        (work / folder).mkdir()
    runner.WORK = WORK
    options = ['-Djava.io.tmpdir=' + str(work / 'tmp'), '-Duser.home=' + str(work / 'runtime-home')]
    adapter = work / 'src/SourcePreservingDexPool.java'
    adapter.write_text(ADAPTER_SOURCE, encoding='utf-8')
    emitted, output = raw / 'writer-classes3.dex', raw / 'disabled-classes3.dex'
    source_paths = [ROOT / 'tools' / item for item in JAVA_SOURCES]
    source_pins = {path: sha(path) for path in source_paths}
    result = {'selected': False, 'deviceEligible': False, 'targetExecuted': False,
              'inputs': dict((BASE_RECEIPT, BASE_DEX, HELPER_RECEIPT, HELPER_DEX, BRIDGE_SOURCE)),
              'writerSources': {path.name: pin for path, pin in source_pins.items()},
              'donorDexesCheckedForHelperNames': checked_dex}
    try:
        runner.run([JDK / 'javac.exe', *('-J' + option for option in options), '-proc:none',
                    '-implicit:none', '--release', '17', '-encoding', 'UTF-8',
                    '-cp', DEXLIB, '-d', work / 'classes', adapter, *source_paths], work, 'compile')
        execution = runner.run([JDK / 'java.exe', '-Xmx4g', *options, '-cp',
                                os.pathsep.join(map(str, (work / 'classes', DEXLIB))),
                                WRITER, source_path, helper_path, HELPER_DEX[1], emitted],
                               work, 'emit', timeout=180)
        summary = json.loads(execution['stdout'])
        candidate, headers = restore_headers(source, bounded(emitted), FRAME_CHANGE)
        require(sha(emitted) == summary['outputSha256'] and sha(source_path) == BASE_DEX[1]
                and sha(helper_path) == HELPER_DEX[1] and all(sha(path) == pin for path, pin in source_pins.items()),
                'Writer inputs or bytes changed')
        proof = validate(source, helper, candidate)
        with output.open('xb') as stream:
            stream.write(candidate)
        output_rel = output.relative_to(ROOT).as_posix()
        result.update(status='PASS_UNSELECTED_DONOR_PIN_WORKER_RETURN_DEX_ONLY', writer=summary,
                      output=output_rel, bytes=len(candidate), outputSha256=digest(candidate),
                      codeHeaders=headers, independentReadback=proof,
                      proposedDexPlacement={'classes3.dex': output_rel, 'classes10.dex': HELPER_DEX[0]})
    except (OSError, ValueError, KeyError) as error:
        result.update(status='FAILED_STATIC_DONOR_PIN_WORKER_RETURN', error=str(error))
        record(work / 'receipt.json', result)
        raise
    record(work / 'receipt.json', result)
    print(f"{result['status']} {work / 'receipt.json'}")


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
