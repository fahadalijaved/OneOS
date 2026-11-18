"""Verify the dormant donor PIN worker-return edits from complete split DEX039 bytes."""

import argparse
import json
from pathlib import Path
import struct

from check_guest_pin_final_callback_retarget import (
    BRIDGE, FIELD, FORWARDER, HELPER_CLASSES, REQUEST, RESPONSE, SECURITY, TASK,
    declarations, try_identity, unique_code,
)
from check_guest_pin_lifecycle_bridge_body import instructions, mapped_extent, member, pool_index, read_code
from check_guest_pin_lifecycle_pools import MAX_BYTES, bounded, digest, load_readers, need, symbolic
from prepare_guest_policy_init_retarget import clean_debug, code, expected_code, header


BASE_SHA = '8235ff3c6dce66faf81a1761cbfda9843c40d2ab0ebdbfd9b8d7a9fc365b96e4'
BASE_BYTES = 10_183_800
WORKER = TASK + '->doInBackground([Ljava/lang/Object;)Ljava/lang/Object;'
WORKER_SOURCE_OFFSET = 7_794_500
WORKER_SOURCE_HEADER = (8, 2, 4, 1, 0, 77)
WORKER_TARGET_HEADER = (8, 2, 4, 1, 0, 85)
REMOTE_FAILURE = 'Landroid/os/RemoteException;'
ASYNC_TASK = 'Landroid/os/AsyncTask;'
LOGGER = ('Lcom/oplusos/keyguard/utils/KgdLogUtil;'
          '->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)V')
WORKER_BRIDGE = SECURITY + 'GuestPinWorkerReturnBridge;'
WORKER_HELPER_CLASSES = HELPER_CLASSES | {WORKER_BRIDGE.encode('ascii')}
NORMAL_NAME = 'oneos$observeNormalWorkerReturn'
CAUGHT_NAME = 'oneos$observeCaughtWorkerReturn'
NORMAL_BRIDGE_NAME = 'observeNormalWorkerReturn'
CAUGHT_BRIDGE_NAME = 'observeCaughtWorkerReturn'
NORMAL = TASK + '->' + NORMAL_NAME + '(' + RESPONSE + ')V'
CAUGHT = TASK + '->' + CAUGHT_NAME + '(' + RESPONSE + REMOTE_FAILURE + ')V'
NORMAL_BRIDGE = WORKER_BRIDGE + '->' + NORMAL_BRIDGE_NAME + '(' + REQUEST + ASYNC_TASK + RESPONSE + ')V'
CAUGHT_BRIDGE = (WORKER_BRIDGE + '->' + CAUGHT_BRIDGE_NAME + '(' + REQUEST + ASYNC_TASK
                 + RESPONSE + REMOTE_FAILURE + ')V')
ORIGINAL_TRY = [(27, 40, [(REMOTE_FAILURE, 68)])]


def verify_pools(source, helper, target, readers):
    expected, addition, actual = (symbolic(dex, readers) for dex in (source, helper, target))
    need(addition['classes'].keys() == WORKER_HELPER_CLASSES, 'Unexpected worker helper class set')
    need(not expected['classes'].keys() & addition['classes'].keys(), 'Helper class collision')
    need(b'oneos$pinRequest' not in addition['strings'], 'Separate helper references the dormant field')
    for reference in (BRIDGE, NORMAL_BRIDGE, CAUGHT_BRIDGE):
        need(member(helper, reference, 'directMethods', 0x08)['codeOffset'] > 0,
             'Separate bridge must have code: ' + reference)

    task, request, response, remote, async_task, bridge_owner = (
        value.encode('ascii') for value in (TASK, REQUEST, RESPONSE, REMOTE_FAILURE, ASYNC_TASK, WORKER_BRIDGE)
    )
    names = tuple(value.encode('ascii') for value in (NORMAL_NAME, CAUGHT_NAME, NORMAL_BRIDGE_NAME, CAUGHT_BRIDGE_NAME))
    protos = (
        (b'V', (response,)), (b'V', (response, remote)),
        (b'V', (request, async_task, response)), (b'V', (request, async_task, response, remote)),
    )
    methods = set(zip((task, task, bridge_owner, bridge_owner), names, protos))
    need({task, request, response, remote, async_task, b'V'} <= expected['types']
         and bridge_owner not in expected['types'], 'Unexpected worker bridge type delta')
    need(not methods & expected['methods'] and all(name not in expected['strings'] for name in names),
         'Worker bridge member collision')
    need({method for method in methods if method[0] == bridge_owner} <= addition['methods'],
         'Separate helper lacks worker bridge IDs')
    before = {kind: len(rows) for kind, rows in expected.items()}
    expected['strings'].update((*names, bridge_owner, b'VL', b'VLL', b'VLLL', b'VLLLL'))
    expected['types'].add(bridge_owner)
    expected['protos'].update(protos)
    expected['methods'].update(methods)
    for kind, rows in expected.items():
        need(rows == actual[kind], 'Unexpected symbolic pool delta: ' + kind)
    for kind in ('types', 'protos', 'fields', 'methods'):
        need(len(actual[kind]) <= 65536, '16-bit pool overflow: ' + kind)
    return {kind: len(actual[kind]) - before[kind] for kind in actual}


def verify_declarations(source, target):
    expected = declarations(source)
    need(NORMAL not in expected and CAUGHT not in expected, 'Added worker wrapper declaration collision')
    expected[NORMAL] = expected[CAUGHT] = ('directMethods', 0x02, True)
    need(declarations(target) == expected, 'Unexpected encoded member delta')


def scan_request_field(dex, field_id, expected_offsets):
    extent = mapped_extent(dex, 0x2001)
    need(extent is not None, 'Missing code map')
    count, start, limit = extent
    offsets = sorted({row['codeOffset'] for row in dex.codes})
    need(offsets and len(offsets) == count and offsets[0] == start and offsets[-1] < limit,
         'Unexpected code item coverage')
    reads = []
    for offset, following in zip(offsets, offsets[1:] + [limit]):
        _, words = read_code(dex, offset, following)
        for pc, opcode in instructions(words):
            if 0x52 <= opcode <= 0x6d and words[pc + 1] == field_id:
                need(opcode == 0x54, 'Unexpected task request field opcode, including any write')
                reads.append((offset, pc))
    need(reads == [(offset, 0) for offset in sorted(expected_offsets)], 'Unexpected exact task request field reads')
    need(mapped_extent(dex, 0x0008) is None, 'Unexpected method handle section')
    return count


def verify_cuts(source, target):
    old = member(source, WORKER, 'virtualMethods', 0x11)
    new = member(target, WORKER, 'virtualMethods', 0x11)
    old_header, old_words = unique_code(source, old)
    new_header, new_words = unique_code(target, new)
    need(old['codeOffset'] == WORKER_SOURCE_OFFSET and old_header == WORKER_SOURCE_HEADER
         and new_header == WORKER_TARGET_HEADER, 'Unexpected exact worker frame')
    need(try_identity(source, old, header(source, old)) == ORIGINAL_TRY
         and try_identity(target, new, header(target, new)) == ORIGINAL_TRY,
         'Unexpected exact worker RemoteException range or target')
    old_log = (0x3071, pool_index(source.methods, LOGGER), 0x0670)
    new_log = (0x3071, pool_index(target.methods, LOGGER), 0x0570)
    need(all(old_words[pc] == 0x0111 for pc in (67, 70, 76)) and old_words[68] == 0x060d
         and old_words[73:76] == old_log, 'Unexpected original worker exits or logger')

    field = member(target, FIELD, 'instanceFields', 0x1042)
    field_id = pool_index(target.fields, FIELD)
    need(field['memberIndex'] == field_id, 'Unexpected task field ID')
    wrapper_offsets = []
    for name, reference, incoming in ((NORMAL, NORMAL_BRIDGE, 2), (CAUGHT, CAUGHT_BRIDGE, 3)):
        wrapper = member(target, name, 'directMethods', 0x02)
        bridge_id = pool_index(target.methods, reference)
        count = incoming + 1
        words = (0x1054, field_id, 0x0038, 5, (count << 8) | 0x77, bridge_id, 0, 0x000e)
        need(unique_code(target, wrapper) == ((count, incoming, count, 0, 0, 8), words),
             'Unexpected worker wrapper body: ' + name)
        wrapper_offsets.append(wrapper['codeOffset'])

    replacements = {67: 0x0a28, 68: 0x050d, 70: 0x0728, 75: new_log[2], 76: 0x0528}
    tail = (0x2070, pool_index(target.methods, NORMAL), 0x0016, 0x0111,
            0x3070, pool_index(target.methods, CAUGHT), 0x0516, 0x0111)
    need(all(new_words[pc] == word for pc, word in replacements.items())
         and new_words[73:76] == new_log and new_words[77:] == tail,
         'Unexpected exact worker branches, exception register, logger or return blocks')
    forwarder = member(target, FORWARDER, 'directMethods', 0x02)
    read_offsets = [forwarder['codeOffset'], *wrapper_offsets]
    scan_count = scan_request_field(target, field_id, read_offsets)
    return replacements, tail, {
        'method': WORKER, 'oldCodeOffset': old['codeOffset'], 'newCodeOffset': new['codeOffset'],
        'oldHeader': old_header, 'newHeader': new_header, 'tryRange': [27, 67],
        'catchType': REMOTE_FAILURE, 'handlerPc': 68, 'caughtRegister': 5,
        'normalReturnCuts': [67, 70], 'caughtReturnCut': 76, 'appendedBlocks': [77, 81],
        'wrapperCodeOffsets': dict(zip((NORMAL, CAUGHT), wrapper_offsets)),
        'field': FIELD, 'fieldId': field_id, 'fieldReads': 3, 'fieldWrites': 0, 'fieldHandles': 0,
        'scannedCodeItems': scan_count,
    }


def verify_preservation(source, target, readers, replacements, tail):
    target_members = {row['descriptor']: row for row in target.codes}
    index_maps = {kind: {value: index for index, value in enumerate(getattr(target, kind))}
                  for kind in ('strings', 'types', 'protos', 'fields', 'methods')}
    debug_readers = [readers['RawDebug'](dex.d, dex.strings, [kind.encode() for kind in dex.types])
                     for dex in (source, target)]
    debug_caches = [{}, {}]
    owners = {}
    for row in source.codes:
        name = row['descriptor']
        emitted = target_members[name]
        old_shape = header(source, row)
        new_shape = header(target, emitted)
        wanted = expected_code(source, target, row, False, index_maps)
        if name == WORKER:
            adjusted = bytearray(wanted)
            for pc, word in replacements.items():
                struct.pack_into('<H', adjusted, pc * 2, word)
            wanted = bytes(adjusted) + struct.pack('<8H', *tail)
            need(new_shape == old_shape[:4] + [85], 'Unexpected worker header delta')
        else:
            need(new_shape == old_shape, 'Unexpected preserved code header: ' + name)
        need(code(target, emitted) == wanted, 'Unexpected raw instruction delta: ' + name)
        need(try_identity(source, row, old_shape) == try_identity(target, emitted, new_shape),
             'Unexpected try/catch delta: ' + name)
        offsets = (source.u32(row['codeOffset'] + 8), target.u32(emitted['codeOffset'] + 8))
        need(bool(offsets[0]) == bool(offsets[1]), 'Unexpected debug presence: ' + name)
        if offsets[0]:
            for at, debug, cache in zip(offsets, debug_readers, debug_caches):
                if at not in cache:
                    cache[at] = clean_debug(debug.read(at))
            need(debug_caches[0][offsets[0]] == debug_caches[1][offsets[1]],
                 'Unexpected debug event delta: ' + name)
        old_offset = row['codeOffset']
        need(owners.setdefault(emitted['codeOffset'], old_offset) == old_offset,
             'Distinct preserved code items were aliased: ' + name)
    return {'sourceCodedMethods': len(source.codes), 'symbolicRawWordsExact': True,
            'codeHeadersTriesAndDebugExact': True}


def validate(source, helper, candidate):
    """Read back the pinned split predecessor and separately verified helper without execution."""
    for raw in (source, helper, candidate):
        need(type(raw) is bytes and 112 <= len(raw) <= MAX_BYTES, 'Ordinary DEX input byte bound')
    need(len(source) == BASE_BYTES and digest(source) == BASE_SHA, 'Held final-callback predecessor differs')
    readers = load_readers()
    original, addition, result = (readers['Dex'](raw) for raw in (source, helper, candidate))
    added_pools = verify_pools(original, addition, result, readers)
    verify_declarations(original, result)
    replacements, tail, cuts = verify_cuts(original, result)
    source_sections, result_sections = ({row['type'] for row in dex.map} for dex in (original, result))
    need(result_sections == source_sections and 0xf000 not in result_sections, 'Unexpected map section or hidden API data')
    map_proof = readers['raw_map'](result, {'Debug': readers['RawDebug']})
    return {
        'status': 'PASS_STATIC_DISABLED_SPLIT_PIN_WORKER_RETURN_RETARGET',
        'sourceSha256': BASE_SHA, 'helperSha256': digest(helper),
        'helperDefinitions': len(WORKER_HELPER_CLASSES), 'helperMerged': False,
        'candidateSha256': digest(candidate), 'candidateBytes': len(candidate),
        'poolCounts': result.counts, 'addedPoolCountsOverPredecessor': added_pools,
        'worker': cuts, 'preservation': verify_preservation(original, result, readers, replacements, tail),
        'map': map_proof, 'selected': False, 'deviceEligible': False, 'targetExecuted': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Held split final-callback classes3.dex')
    parser.add_argument('helper', type=Path, help='Verified split worker-return helper DEX')
    parser.add_argument('candidate', type=Path, help='Standalone emitted classes3.dex')
    args = parser.parse_args()
    print(json.dumps(validate(bounded(args.source), bounded(args.helper), bounded(args.candidate)), indent=2))


if __name__ == '__main__':
    main()
