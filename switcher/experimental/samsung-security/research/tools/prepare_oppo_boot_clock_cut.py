"""Fixed actual-a854 optional OPPO ingress cut; --plan never creates a candidate.

--emit requires a separately reviewed frozen source and a root-authorized run.
Only static bytes are handled. No OEM implementation, VM, script or phone runs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
import uuid
import zlib

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/oppo-boot-clock-cut'
RAW = ROOT / 'firmware/oppo-boot-clock-cut'
SOURCE = ROOT / 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/oplus-services_patched.jar'
SOURCE_SHA = 'a854468fec404a8950f8f3c651f869f19ded098bb244fbef26880c2ece141fa8'
SOURCE_SIZE = 30364137
DEX_SHA = 'e906dc79d971e37f958f675efd1e54cbb7f06742087254b5036944b9b758189b'
DEX_SIZE = 11942320
TARGET = b'Lcom/android/server/NetworkTimeUpdateServiceExtImpl;->checkSystemTime()V'
GETTER = b'Lcom/android/server/NetworkTimeUpdateServiceExtImpl;->getOplusNewNetworkTimeUpdateServiceFeature()Lcom/android/server/IOplusNewNetworkTimeUpdateServiceFeature;'
CALLEE = b'Lcom/android/server/IOplusNewNetworkTimeUpdateServiceFeature;->checkSystemTime()V'
CODE = 6464348
DEBUG = 5213031
BEFORE = bytes.fromhex('7010851101000c007210d81000000e00')
AFTER = b'\x0e\x00' + b'\0\0' * 6 + b'\x0e\x00'
DEPENDENCIES = {
    'tools/build_guest_metrics_services_bundle.py': '7b98178922b6bb9820687885f768581b220d391a3f6a3c2f4c1af4dfc55035b1',
    'tools/preserve_dex_code_headers.py': '943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6',
    'tools/audit_guest_metrics_parent_hook_contract.py': '8ce619e2a3801571eadbc190227219f2d80976abf1289ae0dc474c3e9247b139',
}


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def modules():
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        loaded = {}
        for path, pin in DEPENDENCIES.items():
            need(sha(ROOT / path) == pin, 'Frozen static helper changed: ' + path)
            loaded[path] = runpy.run_path(str(ROOT / path))
        return (loaded['tools/build_guest_metrics_services_bundle.py']['inspect_zip'],
                loaded['tools/preserve_dex_code_headers.py']['Dex039'],
                loaded['tools/preserve_dex_code_headers.py']['seal'],
                loaded['tools/audit_guest_metrics_parent_hook_contract.py']['debug'])
    finally:
        sys.dont_write_bytecode = previous


def source_bytes():
    need(SOURCE.stat().st_size == SOURCE_SIZE, 'Literal archive size')
    with SOURCE.open('rb') as stream:
        data = stream.read(SOURCE_SIZE + 1)
    need(len(data) == SOURCE_SIZE and digest(data) == SOURCE_SHA, 'Literal actual staged archive bytes')
    return data


def profile(source):
    """Validate source only. Never calls forward/inverse or constructs AFTER bytes."""
    need(len(source) == SOURCE_SIZE and digest(source) == SOURCE_SHA, 'Source archive profile')
    inspect_zip, Dex, _, debug = modules()
    rows, end = inspect_zip(source)
    need([r['name'] for r in rows] == ['classes.dex', 'classes2.dex', 'classes3.dex', 'META-INF/MANIFEST.MF',
         'com/android/server/display/feature/wifidisplay/OplusRemoteDisplay.uau'], 'Exact original ZIP entry order')
    row = rows[0]
    need((row['offset'], row['dataStart'], row['method'], row['flags'], row['size'], row['packed']) ==
         (0, 69, 0, 0, DEX_SIZE, DEX_SIZE), 'Exact stored target ZIP profile; no recompression fallback')
    dex = row['bytes']
    need(digest(dex) == DEX_SHA, 'Literal original primary DEX')
    parsed = Dex(dex)
    method = parsed.methods[TARGET]
    need(method == {'flags': 1, 'partition': 'virtual', 'codeOffset': CODE, 'header': (2, 1, 1, 0, 8), 'methodIndex': 4483},
         'Exact target code header/member profile')
    item = parsed.codes[CODE]
    need(item['debugOffset'] == DEBUG and item['end'] == CODE + 32, 'No handlers/padding/payload or code extent drift')
    need([key for key, value in parsed.methods.items() if value['codeOffset'] == CODE] == [TARGET], 'Target code item must have one owner')
    need(dex[CODE + 16:CODE + 32] == BEFORE, 'Exact four source instructions and boundaries')
    words = struct.unpack('<8H', BEFORE)
    need(words[0] == 0x1070 and words[2:5] == (1, 0x000c, 0x1072) and words[6:] == (0, 0x000e),
         'Exact invoke35c/move-result/return forms; no branches or payload')
    need(parsed.methods[GETTER]['methodIndex'] == words[1] and parsed.methods[CALLEE]['methodIndex'] == words[5],
         'Exact getter/interface method identity operands')
    info = debug(dex, DEBUG, 8)
    need(info['bytes'] == 5 and info['sha256'] == '7b415843d10e5741b4f01d70c0dd328f9b69419948c1739c7b3eda5c9b300bb1' and
         info['lineStart'] == 72 and info['parameterNameIndices'] == [] and
         [(x['kind'], x['pc'], x['line']) for x in info['events']] == [('LINE', 0, 72), ('LINE', 7, 73), ('END_SEQUENCE', 7, 73)],
         'Exact original raw debug sequence')
    central = struct.unpack_from('<I', end, 16)[0]
    need(source[central:central + len(row['central'])] == row['central'], 'First central record exact placement')
    return {'rows': rows, 'end': end, 'sourceDex': dex, 'dexObject': parsed,
            'debug': info, 'dexBase': 69, 'localCrcOffset': 14, 'centralCrcOffset': central + 16}


def forward_dex(source_dex):
    need(len(source_dex) == DEX_SIZE and digest(source_dex) == DEX_SHA, 'Literal DEX required before forward')
    need(source_dex[CODE + 16:CODE + 32] == BEFORE, 'Literal forward instruction extent')
    _, Dex, seal, _ = modules()
    result = bytearray(source_dex)
    result[CODE + 16:CODE + 32] = AFTER
    candidate = seal(result)
    allowed = set(range(8, 32)) | set(range(CODE + 16, CODE + 30))
    need(len(candidate) == len(source_dex) and all(i in allowed for i, (a, b) in enumerate(zip(source_dex, candidate)) if a != b),
         'DEX byte whitelist')
    parsed = Dex(candidate)
    need(parsed.methods[TARGET]['header'] == (2, 1, 1, 0, 8) and parsed.codes[CODE]['debugOffset'] == DEBUG,
         'Candidate header/debug identity')
    need(candidate[CODE + 30:CODE + 32] == b'\x0e\x00' and candidate[CODE + 16:CODE + 32] == AFTER,
         'Early void return plus six NOPs and retained source return')
    return candidate


def inverse_dex(source_dex, candidate):
    expected = forward_dex(source_dex)
    need(candidate == expected, 'Inverse DEX rejects ANY unapproved candidate byte before restoration')
    _, Dex, seal, _ = modules()
    restored = bytearray(candidate)
    restored[CODE + 16:CODE + 32] = BEFORE
    restored = seal(restored)
    Dex(restored)
    need(restored == source_dex, 'Inverse DEX must reconstruct exact source bytes')
    return restored


def forward_jar(source):
    original = profile(source)
    changed = forward_dex(original['sourceDex'])
    result = bytearray(source)
    base = original['dexBase']
    result[base:base + len(changed)] = changed
    crc = zlib.crc32(changed) & 0xffffffff
    for offset in (original['localCrcOffset'], original['centralCrcOffset']):
        struct.pack_into('<I', result, offset, crc)
    result = bytes(result)
    verify_jar(source, result, original, changed)
    return result, changed


def verify_jar(source, candidate, original, changed):
    inspect_zip, _, _, _ = modules()
    current, end = inspect_zip(candidate)
    need(len(candidate) == len(source) and len(current) == len(original['rows']) and end == original['end'], 'Exact archive size/entry count/end record')
    allowed = {original['dexBase'] + i for i in set(range(8, 32)) | set(range(CODE + 16, CODE + 30))}
    for p in (original['localCrcOffset'], original['centralCrcOffset']):
        allowed.update(range(p, p + 4))
    need(all(i in allowed for i, (a, b) in enumerate(zip(source, candidate)) if a != b), 'JAR absolute byte whitelist')
    for index, (before, after) in enumerate(zip(original['rows'], current)):
        need(before['name'] == after['name'], 'ZIP name/order unchanged')
        if index:
            need(before['local'] == after['local'] and before['central'] == after['central'] and before['bytes'] == after['bytes'],
                 'Non-target ZIP local/compressed stream/central/plain bytes unchanged')
        else:
            need(after['bytes'] == changed and after['offset'] == before['offset'] and after['dataStart'] == before['dataStart'], 'Target exact DEX and placement')
            for a, b, offset in [(before['local'][:69], after['local'][:69], 14), (before['central'], after['central'], 16)]:
                x, y = bytearray(a), bytearray(b)
                x[offset:offset + 4] = y[offset:offset + 4] = b'\0' * 4
                need(x == y, 'Target ZIP metadata changed outside CRC')


def inverse_jar(source, candidate):
    expected, _ = forward_jar(source)
    need(candidate == expected, 'Inverse JAR rejects ANY unapproved candidate byte before restoration')
    original = profile(source)
    inspect_zip, _, _, _ = modules()
    current, _ = inspect_zip(candidate)
    restored_dex = inverse_dex(original['sourceDex'], current[0]['bytes'])
    restored = bytearray(candidate)
    restored[69:69 + DEX_SIZE] = restored_dex
    crc = zlib.crc32(restored_dex) & 0xffffffff
    for offset in (original['localCrcOffset'], original['centralCrcOffset']):
        struct.pack_into('<I', restored, offset, crc)
    restored = bytes(restored)
    need(restored == source, 'Template-derived inverse JAR did not reconstruct exact source')
    return restored


def plan():
    source = source_bytes()
    item = profile(source)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex
    work, raw = WORK / stamp, RAW / stamp
    work.mkdir(parents=True, exist_ok=False)
    raw.mkdir(parents=True, exist_ok=False)
    debug = item['debug']
    raw_file = raw / 'source-profile.json'
    raw_file.write_text(json.dumps({'codeHeaderHex': source[69 + CODE:69 + CODE + 16].hex(),
                                    'instructionHex': BEFORE.hex(), 'debug': debug,
                                    'debugHex': source[69 + DEBUG:69 + DEBUG + debug['bytes']].hex()}, indent=2) + '\n')
    result = {'schema': 'oppo-boot-clock-cut-plan/v1', 'status': 'PREPARED_SOURCE_ONLY_NO_CANDIDATE',
              'source': {'path': str(SOURCE), 'sha256': SOURCE_SHA, 'bytes': SOURCE_SIZE},
              'primaryDex': {'name': 'classes.dex', 'sha256': DEX_SHA, 'bytes': DEX_SIZE},
              'method': TARGET.decode(), 'normalizedSourceBodySha256': 'fee9acf2def335b4f44020e5228547dd5145f6a6b7b591bdecf1eb4355ab163b',
              'codeOffset': CODE, 'header': [2, 1, 1, 0, DEBUG, 8], 'uniqueCodeOwner': True,
              'instructionBoundariesBefore': [0, 3, 4, 7, 8], 'instructionBoundariesAfterPlanned': list(range(9)),
              'pcMap': {str(i): i for i in range(9)}, 'tryMaps': [],
              'debug': {k: v for k, v in debug.items() if k != 'events'},
              'dexBase': 69, 'localCrcOffset': 14, 'centralCrcOffset': item['centralCrcOffset'],
              'entryCount': len(item['rows']), 'dependencyPins': DEPENDENCIES,
              'raw': {'path': str(raw_file.relative_to(ROOT)), 'sha256': sha(raw_file)},
              'candidateComputed': False, 'candidateEmitted': False, 'oemExecuted': False, 'phoneActions': [],
              'toolSha256': sha(Path(__file__))}
    need(sha(SOURCE) == SOURCE_SHA, 'Source drift after plan')
    for path, pin in DEPENDENCIES.items():
        need(sha(ROOT / path) == pin, 'Frozen helper drift after plan: ' + path)
    (work / 'plan.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'plan': str((work / 'plan.json').relative_to(ROOT)), 'raw': str(raw_file.relative_to(ROOT)), 'candidateComputed': False}))


def emit(freeze):
    freeze = freeze.resolve()
    need(freeze.is_relative_to(WORK.resolve()), 'Own explicit source-review freeze required')
    need(freeze.stat().st_size <= 65536, 'Source-review freeze size bound')
    freeze_pin = sha(freeze)
    gate = json.loads(freeze.read_text())
    need(gate.get('schema') == 'oppo-boot-clock-cut-source/v1' and gate.get('frozen') is True and
         gate.get('toolSha256') == sha(Path(__file__)) and isinstance(gate.get('review'), str) and
         1 <= len(gate['review']) <= 2000 and not gate['review'].startswith('PENDING'), 'Frozen reviewed producer required')
    source = source_bytes()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex
    work = WORK / stamp
    work.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'runHandle': str(work.relative_to(ROOT)), 'staticOnly': True}), flush=True)
    jar, dex = forward_jar(source)
    need(inverse_dex(profile(source)['sourceDex'], dex) == profile(source)['sourceDex'], 'Actual DEX inverse proof')
    need(inverse_jar(source, jar) == source, 'Actual template-derived JAR inverse proof')
    # Meaningful refusal checks use changed copies only after the authorized forward.
    inspect_zip, _, seal, _ = modules()
    bad = bytearray(dex); bad[-1] ^= 1
    bad = seal(bad)  # valid integrity words do not authorize an unrelated change
    try:
        inverse_dex(profile(source)['sourceDex'], bad)
    except ValueError:
        pass
    else:
        raise ValueError('Off-target DEX byte accepted by inverse')
    original = profile(source)
    central_start = original['centralCrcOffset'] - 16
    # Change one non-target central external-attribute low bit, keeping ZIP valid.
    bad = bytearray(jar)
    bad[central_start + len(original['rows'][0]['central']) + 38] ^= 1
    inspect_zip(bytes(bad))
    try:
        inverse_jar(source, bytes(bad))
    except ValueError:
        pass
    else:
        raise ValueError('Off-target JAR byte accepted by inverse')
    paths = []
    for name, data in [('oplus-services-boot-clock-cut.jar', jar), ('classes-boot-clock-cut.dex', dex)]:
        path = work / name
        with path.open('xb') as stream:
            stream.write(data)
        need(path.read_bytes() == data, 'Saved candidate bytes differ')
        paths.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(data), 'bytes': len(data)})
    need(sha(SOURCE) == SOURCE_SHA and gate['toolSha256'] == sha(Path(__file__)) and sha(freeze) == freeze_pin, 'Source/tool/review drift after emission')
    for path, pin in DEPENDENCIES.items():
        need(sha(ROOT / path) == pin, 'Frozen helper drift after emission: ' + path)
    result = {'schema': 'oppo-boot-clock-cut-emission/v1', 'status': 'PASS_UNSELECTED_STATIC_OPTIONAL_INGRESS_CUT',
              'inputs': {'archiveSha256': SOURCE_SHA, 'dexSha256': DEX_SHA, 'toolSha256': sha(Path(__file__)), 'dependencyPins': DEPENDENCIES},
              'sourceReviewFreeze': {'path': str(freeze.relative_to(ROOT)), 'sha256': freeze_pin},
              'dependencyPinsVerifiedBeforeAfter': True,
              'artifacts': paths, 'exactDexInverse': True, 'exactTemplateDerivedJarInverse': True,
              'offTargetInverseRefusals': 2, 'refusalKinds': ['resealed unrelated DEX change', 'well-formed ZIP non-target attribute change'],
              'allOtherArchiveAndDexBytesPreserved': True,
              'allClockWritersClosed': False, 'firstBootGlobalOverrideChanged': False,
              'oemExecuted': False, 'phoneActions': [], 'runtimeSelected': False,
              'signatureOrOemAuthenticityVerified': False,
              'limits': 'One void wrapper ingress only; no OneOS selection/guard composition, ART, loader, time owner or phone acceptance.'}
    (work / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'receipt': str((work / 'receipt.json').relative_to(ROOT)), 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--plan', action='store_true')
    group.add_argument('--emit', type=Path, metavar='REVIEWED_SOURCE_FREEZE')
    args = parser.parse_args()
    if args.plan:
        plan()
    else:
        emit(args.emit)
