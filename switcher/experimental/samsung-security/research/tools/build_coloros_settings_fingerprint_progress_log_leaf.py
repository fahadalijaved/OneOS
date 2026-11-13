"""Derive an unselected Settings DEX with one enrollment-progress log removed."""

from hashlib import sha256
import json
import struct
from uuid import uuid4
from zipfile import ZipFile

from build_coloros_settings_rpmb_leaf import ROOT, SOURCE, SOURCE_SHA, digest, header, seal
from check_guest_pin_lifecycle_bridge_body import instructions
from compose_coloros_ui_removals import instruction_owner
from preserve_dex_code_headers import Dex039, need


OWNER = 'Lcom/oplus/settings/feature/fingerprint/FingerprintEnrollProcessor;'
METHOD = 'onEnrollProgress(I)V'
ENTRY = 'classes13.dex'
DEX_BYTES = 11_447_552
SOURCE_DEX_SHA = 'a706e235bfe59e04b5febe2dc96a1aae2a8e8eac517c7585cdd22ae8b180e6ac'
SOURCE_BODY_SHA = 'fe040164a60e46e6390cf596fe12316896582c71ad2db274022089779a97a0de'
OUTPUT_DEX_SHA = 'f4217ab60578cbba4bc395da92af3b24c83b3d0bed655515d3821044727b9047'
METHOD_ID = 26_464
CODE_OFFSET = 3_126_788
CODE_HEADER = (4, 2, 3, 0, 64)
SPANS = (
    (0, 18, 'd9d812dec4ebd6ee4b4a09d9fc879b329b3c4221d8f5317920ccb004266d2ec6'),
    (20, 23, 'd4bb49c231fcae1edbe571af60e425ac3597232d11c6e60fb679aa91db71517e'),
)


def branch_edges(words, decoded):
    edges = []
    for pc, opcode in decoded.items():
        if opcode == 0x28:  # goto
            delta = (words[pc] >> 8 ^ 0x80) - 0x80
        elif 0x32 <= opcode <= 0x3d:  # if and if-z
            delta = (words[pc + 1] ^ 0x8000) - 0x8000
        else:
            need(opcode not in (0x26, 0x29, 0x2a, 0x2b, 0x2c),
                 'Unexpected branch or payload in the selected method')
            continue
        edges.append((pc, pc + delta))
    return edges


def patch_dex(original: bytes) -> tuple[bytes, dict]:
    need(type(original) is bytes and len(original) == DEX_BYTES
         and sha256(original).hexdigest() == SOURCE_DEX_SHA,
         'Expected the exact donor Settings classes13.dex')
    dex = Dex039(original)
    method = dex.methods.get(f'{OWNER}->{METHOD}'.encode('ascii'))
    need(method is not None and method['flags'] == 2 and method['partition'] == 'direct'
         and method['methodIndex'] == METHOD_ID and method['codeOffset'] == CODE_OFFSET
         and method['header'] == CODE_HEADER, 'Exact private progress method differs')
    code = dex.codes[CODE_OFFSET]
    registers, incoming, outgoing, tries, units = CODE_HEADER
    start = CODE_OFFSET + 16
    need(code['debugOffset'] == 0 and code['end'] == start + units * 2,
         'Progress method extent or debug info differs')
    words = struct.unpack_from(f'<{units}H', original, start)
    decoded = dict(instructions(words))
    edges = branch_edges(words, decoded)
    need(edges == [(27, 36), (39, 45), (47, 51), (50, 52), (56, 63)]
         and all(target in decoded for _, target in edges), 'Progress branch edges differ')

    ranges = [(row['methodIndex'], row['codeOffset'], dex.codes[row['codeOffset']]['end'])
              for row in dex.methods.values() if row['codeOffset']]
    need(len(ranges) == len(dex.codes), 'An encoded method aliases a code item')
    spans = []
    patched = bytearray(original)
    for first, end, pin in SPANS:
        first_byte, end_byte = start + first * 2, start + end * 2
        need(first in decoded and end in decoded
             and all(not first <= target < end for _, target in edges),
             'Diagnostic span has an unaligned boundary or incoming branch')
        need(sha256(original[first_byte:end_byte]).hexdigest() == pin
             and instruction_owner(ranges, first_byte, end_byte) == METHOD_ID,
             'Diagnostic bytes or their method ownership differ')
        patched[first_byte:end_byte] = bytes(end_byte - first_byte)
        spans.append({'firstPc': first, 'endExclusivePc': end, 'firstByte': first_byte,
                      'endExclusiveByte': end_byte, 'sourceSliceSha256': pin})

    result = seal(patched)
    header(result)
    need(sha256(result).hexdigest() == OUTPUT_DEX_SHA, 'Unexpected progress-log DEX hash')
    restored = bytearray(result)
    for span in spans:
        first, end = span['firstByte'], span['endExclusiveByte']
        need(result[first:end] == bytes(end - first), 'Diagnostic span is not all NOPs')
        restored[first:end] = original[first:end]
    need(seal(restored) == original, 'Inverse does not recover all original bytes')
    for span in spans:
        first, end = span['firstByte'], span['endExclusiveByte']
        restored[first:end] = bytes(end - first)
    need(seal(restored) == result, 'Forward roundtrip differs')
    return result, {
        'owner': OWNER, 'signature': METHOD, 'sourceNormalizedBodySha256': SOURCE_BODY_SHA,
        'methodId': METHOD_ID, 'codeOffset': CODE_OFFSET, 'instructionsOffset': start,
        'registers': registers, 'incomingWords': incoming, 'outgoingWords': outgoing,
        'tryItems': tries, 'debugInfoOffset': code['debugOffset'], 'instructionUnits': units,
        'spans': spans, 'branchEdges': edges, 'preservedTagPc': 18, 'preservedWarningPc': 32,
        'encodedMethods': len(dex.methods), 'uniqueCodeItems': len(dex.codes),
        'inverseExact': True, 'roundtripExact': True,
    }


def build():
    need(digest(SOURCE) == SOURCE_SHA, 'Expected the exact donor Settings APK')
    with ZipFile(SOURCE) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)) == 10_549 and archive.getinfo(ENTRY).file_size == DEX_BYTES,
             'Donor Settings archive shape differs')
        original = archive.read(ENTRY)
    patched, method = patch_dex(original)
    need(digest(SOURCE) == SOURCE_SHA, 'Donor Settings APK changed while reading')

    run_name = 'r-' + uuid4().hex[:8]
    runs = [ROOT / area / 'settings-fingerprint-progress-log-leaf' / run_name
            for area in ('firmware', 'out')]
    for run in runs:
        need(run.resolve() == run, 'Output escapes the expected repository path')
        run.mkdir(parents=True)
    raw_run, receipt_run = runs
    dex = raw_run / ENTRY
    with dex.open('xb') as stream:
        stream.write(patched)
    need(dex.stat().st_size == DEX_BYTES and digest(dex) == OUTPUT_DEX_SHA,
         'Progress-log DEX readback differs')
    receipt = {
        'schema': 'oneos-coloros-settings-fingerprint-progress-log-leaf/v1',
        'status': 'PASS_EXACT_UNSELECTED_SETTINGS_FINGERPRINT_PROGRESS_LOG_LEAF',
        'sourceArchive': {'path': SOURCE.relative_to(ROOT.parent).as_posix(),
                          'bytes': SOURCE.stat().st_size, 'sha256': SOURCE_SHA},
        'sourceDex': {'entry': ENTRY, 'bytes': DEX_BYTES, 'sha256': SOURCE_DEX_SHA},
        'outputDex': {'path': dex.relative_to(ROOT).as_posix(), 'bytes': DEX_BYTES, 'sha256': OUTPUT_DEX_SHA},
        'method': method,
        'selected': False, 'deviceAction': False, 'targetExecuted': False,
    }
    path = receipt_run / 'receipt.json'
    with path.open('x', encoding='ascii', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    return path


if __name__ == '__main__':
    output = build()
    print(output.relative_to(ROOT).as_posix(), digest(output))
