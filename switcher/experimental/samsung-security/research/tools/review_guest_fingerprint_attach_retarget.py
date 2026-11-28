"""Independently review the closed AMS fingerprint attach observation DEX."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
from zipfile import ZipFile

from audit_coloros_raw_debug_baseline import RawDebug
from audit_guest_metrics_parent_hook_contract import raw_tries
from preflight_guest_metrics_parent_payload import Dex
from prepare_guest_locksettings_proxy_retarget import raw_ids
from prepare_guest_system_server_fork_retarget import (
    clean_debug, code, expected_code, header, ordered_ids, raw_identity,
)
from preserve_dex_code_headers import Dex039, need


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/services_patched.jar'
ARCHIVE_SHA = 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'
DEX_SHA = 'bcc9cb821ffc6a37b3838ca2391253652a0d40245a4b75b8b35eccd17779ca20'
DEX_BYTES = 12_186_672
EVIDENCE = 'firmware/retained-fingerprint-caller-ingress/20261107T034034832840Z-d21c46039fdf42f2a76654312153b21f.jsonl'
EVIDENCE_SHA = 'b3bd642563a9b096a8cf392277737dea6f652f1a119a81f160817701add47958'

AMS = 'Lcom/android/server/am/ActivityManagerService;'
INNER = AMS + '->finishAttachApplicationInner(JII)V'
OUTER = AMS + '->finishAttachApplication(JJ)V'
NO_WAIT = AMS + '->attachApplicationLocked(Landroid/app/IApplicationThread;IIJ)V'
RECORD = 'Lcom/android/server/am/ProcessRecord;'
THREAD_FIELD = RECORD + '->mThread:Lcom/android/server/am/ApplicationThreadDeferred;'
HELPER = 'Lcom/android/server/am/PreparedGuestFingerprintAttach;'
OBSERVATION = HELPER[:-1] + '$Observation;'
CLONE_NAME = 'finishAttachApplicationForFingerprintObservation'
CLONE_PROTO = '(JII)' + OBSERVATION
CLONE = AMS + '->' + CLONE_NAME + CLONE_PROTO
SNAPSHOT_PROTO = '(' + RECORD + 'Landroid/app/IApplicationThread;JII)' + OBSERVATION
SNAPSHOT = HELPER + '->snapshot' + SNAPSHOT_PROTO
ORIGINAL_COUNTS = dict(strings=108089, types=10154, protos=15929, fields=39251, methods=65533, classes=6789)
SOURCE_HEADERS = {
    INNER: ([43, 5, 19, 30, 977], 6336228, 9148660),
    OUTER: ([15, 5, 6, 1, 101], 6352452, 9200620),
    NO_WAIT: ([70, 6, 34, 75, 2359], 6317767, 9113140),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pinned_path(relative, pin, limit, roots):
    need(type(relative) is str and type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin),
         'Expected a relative path and literal SHA-256')
    pure = PurePosixPath(relative)
    need(pure.as_posix() == relative and pure.parts and pure.parts[0] in roots
         and all(part not in ('.', '..') and ':' not in part and '\\' not in part for part in pure.parts),
         'Expected a canonical path in the evidence roots')
    path = ROOT.joinpath(*pure.parts)
    need(path.resolve(strict=True) == path and path.is_file() and 0 < path.stat().st_size <= limit
         and digest_file(path) == pin, 'Artifact path, extent or SHA-256 differs: ' + relative)
    return path


def source_bytes():
    path = pinned_path(ARCHIVE, ARCHIVE_SHA, 96 * 1024 * 1024, {'firmware'})
    with ZipFile(path) as archive:
        names = archive.namelist()
        need(len(names) == 83 and len(set(names)) == len(names)
             and [n for n in names if re.fullmatch(r'classes(?:[0-9]+)?\.dex', n)]
             == ['classes.dex', 'classes2.dex', 'classes3.dex', 'classes4.dex'],
             'Staged archive inventory differs')
        data = archive.read('classes.dex')
    need(len(data) == DEX_BYTES and sha(data) == DEX_SHA and digest_file(path) == ARCHIVE_SHA,
         'Pinned complete staged source DEX differs')
    return data


def original_bodies():
    path = pinned_path(EVIDENCE, EVIDENCE_SHA, 512 * 1024, {'firmware'})
    selected = {}
    for line in path.read_bytes().splitlines():
        row = json.loads(line)
        if row['record'] != 'method':
            continue
        body = row['body']
        name = body['owner'] + '->' + body['signature']
        if name in (INNER, OUTER):
            need(name not in selected and row['physicalDex'] == 'classes.dex'
                 and row['logicalHeaderOffset'] == 0, 'Original selected evidence location')
            selected[name] = body['instructions']
    need(set(selected) == {INNER, OUTER}, 'Original selected instruction evidence missing')
    return selected


def _remove_exact(values, additions, label):
    result = list(values)
    for row in additions:
        need(result.count(row) == 1, 'Missing or duplicate added ' + label)
        result.remove(row)
    return result


def verify_inventory(source, output, physical_source, physical_output):
    tools = {'raw_ids': raw_ids}
    for dex in (source, output):
        ordered_ids(dex, tools)
    left, right = raw_identity(source, tools), raw_identity(output, tools)
    for kind in ('classes', 'classRootPresence', 'fields'):
        need(left[kind] == right[kind], 'Original ordered inventory differs: ' + kind)
    additions = {
        'strings': [[len(value), value.encode().hex()] for value in (HELPER, OBSERVATION, CLONE_NAME)],
        'types': [value.encode().hex() for value in (HELPER, OBSERVATION)],
        'protos': [
            [b'LJII'.hex(), OBSERVATION, [True, ['J', 'I', 'I']]],
            [b'LLLJII'.hex(), OBSERVATION, [True, [RECORD, 'Landroid/app/IApplicationThread;', 'J', 'I', 'I']]],
        ],
        'methods': [[AMS, CLONE_PROTO, CLONE_NAME.encode().hex()],
                    [HELPER, SNAPSHOT_PROTO, b'snapshot'.hex()]],
    }
    for kind, added in additions.items():
        need(all(value not in left[kind] for value in added)
             and _remove_exact(right[kind], added, kind) == left[kind],
             'Unexpected original ordered raw ID change: ' + kind)
    need(_remove_exact(right['members'], [(CLONE, 'directMethods', 2, True)], 'clone member')
         == left['members'], 'Original encoded member inventory differs')
    need(source.counts == ORIGINAL_COUNTS
         and output.counts == {kind: n + len(additions.get(kind, ())) for kind, n in ORIGINAL_COUNTS.items()}
         and set(physical_source.maps) == set(physical_output.maps)
         and not ({7, 8, 0xf000} & set(physical_output.maps)), 'Unexpected physical DEX inventory')


def _tries(dex, member):
    h = header(dex, member)
    return [(row['startPc'], row['startPc'] + row['codeUnits'],
             [(item['exceptionType'], item['handlerPc']) for item in row['handlers']])
            for row in raw_tries(dex, member, {'tries': h[3], 'units': h[4]})]


def _debug(dex):
    return RawDebug(dex.d, dex.strings, [value.encode() for value in dex.types])


def _debug_at(dex, member, reader, cache):
    offset = dex.u32(member['codeOffset'] + 8)
    if offset and offset not in cache:
        cache[offset] = clean_debug(reader.read(offset))
    return cache.get(offset)


def verify_unchanged(source, output, old, new, maps):
    before, after = _debug(source), _debug(output)
    cache_a, cache_b = {}, {}
    count = 0
    for name, member in old.items():
        if not member['codeOffset'] or name == OUTER:
            continue
        actual = new[name]
        need(header(source, member) == header(output, actual), 'Original code header differs: ' + name)
        need(expected_code(source, output, member, False, maps) == code(output, actual),
             'Original instruction or operand differs: ' + name)
        need(_tries(source, member) == _tries(output, actual), 'Original try contour differs: ' + name)
        need(_debug_at(source, member, before, cache_a) == _debug_at(output, actual, after, cache_b),
             'Original debug contour differs: ' + name)
        count += 1
    need(count == 49118, 'Complete non-target coded method comparison required')
    return count


def _word_sequence(*words):
    return struct.pack('<' + 'H' * len(words), *words)


def _relocated_code(source, output, member, maps, instructions, before, replace):
    original = expected_code(source, output, member, False, maps)
    result = bytearray()
    translated = {}
    for item in instructions:
        pc, width = item['pc'], item['codeUnits']
        result.extend(before.get(pc, b''))
        translated[pc] = len(result) // 2
        result.extend(replace.get(pc, original[pc * 2:(pc + width) * 2]))
    translated[len(original) // 2] = len(result) // 2
    for item in instructions:
        if 'targetPc' not in item:
            continue
        at = translated[item['pc']]
        delta = translated[item['targetPc']] - at
        opcode = item['opcode']
        if opcode == 'GOTO':
            need(-128 <= delta <= 127, 'Unexpected branch widening')
            struct.pack_into('<b', result, 2 * at + 1, delta)
        elif opcode == 'GOTO_16' or opcode.startswith('IF_'):
            need(-32768 <= delta <= 32767, 'Unexpected branch widening')
            struct.pack_into('<h', result, 2 * at + 2, delta)
        elif opcode == 'GOTO_32':
            struct.pack_into('<i', result, 2 * at + 2, delta)
        else:
            raise ValueError('Unexpected selected offset or payload: ' + opcode)
    return bytes(result), translated


def _debug_relocated(value, translated):
    return {**value,
            'events': [[kind, translated[pc], *rest] for kind, pc, *rest in value['events']],
            'terminalCursor': [translated[value['terminalCursor'][0]], value['terminalCursor'][1]]}


def _expect_changed(source, output, member, actual, maps, instructions, before, replace,
                    try_end_override=None):
    expected, translated = _relocated_code(source, output, member, maps, instructions, before, replace)
    original = header(source, member)
    need(header(output, actual) == [*original[:4], len(expected) // 2],
         'Edited header differs: ' + actual['descriptor'])
    need(code(output, actual) == expected, 'Edited instruction layout differs: ' + actual['descriptor'])
    end_override = try_end_override or {}
    relocated = [(translated[start], end_override.get(end, translated[end]),
                  [(exception, translated[handler]) for exception, handler in handlers])
                 for start, end, handlers in _tries(source, member)]
    need(_tries(output, actual) == relocated, 'Edited try contour differs: ' + actual['descriptor'])
    debug_before = _debug_at(source, member, _debug(source), {})
    debug_after = _debug_at(output, actual, _debug(output), {})
    need(debug_before is not None and debug_after == _debug_relocated(debug_before, translated),
         'Edited debug contour differs: ' + actual['descriptor'])
    return translated


def _source_headers(source, old):
    for name, (size, debug, offset) in SOURCE_HEADERS.items():
        member = old[name]
        need(member['codeOffset'] == offset and header(source, member) == size
             and source.u32(offset + 8) == debug, 'Original AMS code shape differs: ' + name)


def _selected(source, output, old, new, maps):
    evidence = original_bodies()
    outer_orig = expected_code(source, output, old[OUTER], False, maps)
    invoke, previous, registers = struct.unpack_from('<3H', outer_orig, 2 * 67)
    need(invoke == 0x5170 and previous == maps['methods'][INNER] and registers == 0x7cba,
         'Original five-word private attach call differs')
    outer = _expect_changed(
        source, output, old[OUTER], new[OUTER], maps, evidence[OUTER],
        {70: _word_sequence(0x000c)},
        {67: _word_sequence(invoke, maps['methods'][CLONE], registers)},
        try_end_override={70: 70},
    )

    # v2 remains the validated ProcessRecord. Hold its deferred thread in v6
    # before the original monitor exit. The exact post-trace range is six words.
    capture_thread = _word_sequence(0x2654, maps['fields'][THREAD_FIELD])
    build_snapshot = _word_sequence(
        0x2807, 0x6907, 0x0a05, 39, 0x0c02, 41, 0x0d02, 42,
        0x0677, maps['methods'][SNAPSHOT], 8, 0x060c, 0x0611,
    )
    clone = _expect_changed(
        source, output, old[INNER], new[CLONE], maps, evidence[INNER],
        {793: capture_thread},
        {461: _word_sequence(0x0411), 800: build_snapshot, 959: _word_sequence(0x0411)},
    )
    return {
        'oldInnerVoidPreserved': True, 'oldNoWaitCallerPreserved': True,
        'typedClone': CLONE, 'snapshotFactory': SNAPSHOT,
        'cloneThreadReadPc': clone[793] - 2, 'cloneOriginalMonitorExitPc': clone[793],
        'cloneOriginalTracePc': clone[797], 'cloneSnapshotInvokePc': clone[800] + 8,
        'cloneNullReturnPcs': [clone[461], clone[959]],
        'outerCloneInvokePc': outer[67], 'outerMoveResultPc': outer[70] - 1,
        'outerNormalRestorePc': outer[70], 'outerExceptionalRestorePc': outer[97],
        'outerSnapshotRegister': 0, 'outerSnapshotOverwrittenAtPc': outer[76],
    }


def review(dex_path, dex_pin):
    need(type(dex_path) is str and re.fullmatch(
        r'firmware/guest-fingerprint-attach-retarget/r-[0-9a-f]{8}/[a-z0-9][a-z0-9._-]{0,63}\.dex', dex_path
    ), 'Expected a saved DEX in the dedicated attach-retarget run directory')
    path = pinned_path(dex_path, dex_pin, 24 * 1024 * 1024, {'firmware'})
    source_raw = source_bytes()
    output_raw = path.read_bytes()
    need(sha(output_raw) == dex_pin and source_raw != output_raw, 'Independent DEX readback differs')
    physical_source, physical_output = Dex039(source_raw), Dex039(output_raw)
    source, output = Dex(source_raw), Dex(output_raw)
    verify_inventory(source, output, physical_source, physical_output)
    need(len(physical_source.codes) == len(source.codes) == 49119
         and len(physical_output.codes) == len(output.codes) == 49120
         and len(source.members) == 89588 and len(output.members) == 89589,
         'Unique physical/encoded member totals differ')
    old = {row['descriptor']: row for row in source.members}
    new = {row['descriptor']: row for row in output.members}
    _source_headers(source, old)
    maps = {kind: {value: index for index, value in enumerate(getattr(output, kind))}
            for kind in ('strings', 'types', 'protos', 'fields', 'methods')}
    selected = _selected(source, output, old, new, maps)
    unchanged = verify_unchanged(source, output, old, new, maps)
    need(digest_file(path) == dex_pin, 'Saved output changed during independent review')
    return {
        'schema': 'oneos-guest-fingerprint-attach-retarget-independent-review/v1',
        'status': 'PASS_STATIC_CLOSED_GUEST_ATTACH_RETARGET',
        'sourceArchive': {'path': ARCHIVE, 'sha256': ARCHIVE_SHA},
        'sourceDex': {'member': 'classes.dex', 'bytes': DEX_BYTES, 'sha256': DEX_SHA, 'ids': source.counts},
        'outputDex': {'path': dex_path, 'bytes': len(output_raw), 'sha256': dex_pin, 'ids': output.counts},
        'sourceInstructionEvidence': {'path': EVIDENCE, 'sha256': EVIDENCE_SHA},
        'reviewToolSha256': digest_file(Path(__file__)),
        'originalUnchangedCodedMethods': unchanged, 'originalEncodedMembers': len(source.members),
        'originalClassDefinitions': source.counts['classes'], 'code': selected,
        'selected': False, 'deviceAction': False, 'targetExecuted': False,
        'matchesAfterRestoreIntegrated': False, 'operationAuthorityIssued': False,
    }


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('dex_path', help='Repository-relative saved attach-retarget DEX path')
    args.add_argument('dex_sha256', help='Expected literal SHA-256 of the complete output DEX')
    options = args.parse_args()
    print(json.dumps(review(options.dex_path, options.dex_sha256), indent=2))


if __name__ == '__main__':
    main()
