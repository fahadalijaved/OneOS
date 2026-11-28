"""Verify the dormant donor PIN final-callback edit from complete DEX039 bytes."""

import argparse
import json
from pathlib import Path
import struct

from audit_guest_metrics_parent_hook_contract import raw_tries
from check_guest_pin_lifecycle_bridge_body import (
    mapped_extent, member, pool_index, read_code, scan_slot_accesses,
)
from check_guest_pin_lifecycle_pools import (
    MAX_BYTES, SOURCE_SHA, bounded, digest, load_readers, need, source_input, symbolic,
)
from prepare_guest_policy_init_retarget import clean_debug, code, expected_code, header


SECURITY = 'Lcom/oplus/keyguard/security/'
TASK = SECURITY + 'OplusLockPatternChecker$oplusCheckCredential$task$1;'
CALLBACK = SECURITY + 'OplusLockPatternChecker$OplusOnCheckCallback;'
RESPONSE = 'Lcom/android/internal/widget/VerifyCredentialResponse;'
REQUEST = SECURITY + 'GuestPinCheckRequest;'
BRIDGE_OWNER = SECURITY + 'GuestPinFinalCallbackBridge;'
BRIDGE = (BRIDGE_OWNER + '->forwardOriginal(' + REQUEST + 'Landroid/os/AsyncTask;'
          + CALLBACK + RESPONSE + 'IZ)V')
TARGET = TASK + '->onPostExecute(Ljava/lang/Object;)V'
ORIGINAL = CALLBACK + '->onChecked(' + RESPONSE + 'IZ)V'
FORWARDER = TASK + '->oneos$forwardOriginalFinal(' + CALLBACK + RESPONSE + 'IZ)V'
FIELD = TASK + '->oneos$pinRequest:' + REQUEST
CUT_PC = 61
SOURCE_OFFSET = 4_303_184
SOURCE_CODE_SHA = '2ff3fc3cf5c763aa7bc34fd56000bd24aa33712d568bfa77f9d2df5dd1a8bc21'
SOURCE_HEADER = (8, 2, 4, 0, 0, 73)
TARGET_HEADER = (8, 2, 5, 0, 0, 73)
STOCK_WORDS = (0x4072, 0xadef, 0x2371)
HELPER_CLASSES = {
    (SECURITY + name + ';').encode('ascii')
    for name in (
        'GuestPinFinalCallbackBridge',
        'GuestPinCheckRequest', 'GuestPinCheckRequest$1', 'GuestPinCheckRequest$EntryState',
        'GuestPinCheckRequest$PostState', 'GuestPinCheckRequest$ProgressEntry',
        'GuestPinCheckRequest$ProgressPost', 'GuestPinCheckRequest$Slot',
        'GuestPinCheckRequest$TerminalDelivery', 'GuestPinCheckRequest$TerminalState',
        'GuestPinCheckRequest$WorkerExit', 'GuestPinCheckRequest$WorkerExitKind',
        'GuestPinSourceOccurrence', 'GuestPinSourceOccurrence$1', 'GuestPinSourceOccurrence$Owner',
        'GuestPinSourceOccurrence$Readback', 'GuestPinSourceOccurrence$Transition',
        'PinCheckCompletion', 'PinCheckCompletion$FinalKind', 'PinCheckCompletion$Retirement',
    )
}


def verify_pools(source, helper, target, readers):
    original, addition, actual = (symbolic(dex, readers) for dex in (source, helper, target))
    need(addition['classes'].keys() == HELPER_CLASSES, 'Unexpected final helper class set')
    need(not original['classes'].keys() & addition['classes'].keys(), 'Helper class collision')
    method = member(helper, BRIDGE, 'directMethods', 0x08)
    need(method['codeOffset'] > 0, 'Final bridge must have code')
    need(b'oneos$pinRequest' not in addition['strings'], 'Separate helper references the dormant field')

    expected = original
    task, request, bridge_owner = (descriptor.encode('ascii') for descriptor in (TASK, REQUEST, BRIDGE_OWNER))
    callback, response = CALLBACK.encode('ascii'), RESPONSE.encode('ascii')
    async_task = b'Landroid/os/AsyncTask;'
    field = task, b'oneos$pinRequest', request
    proto = b'V', (callback, response, b'I', b'Z')
    external_proto = b'V', (request, async_task, callback, response, b'I', b'Z')
    forwarder = task, b'oneos$forwardOriginalFinal', proto
    bridge = bridge_owner, b'forwardOriginal', external_proto
    need({task, async_task, callback, response, b'I', b'Z', b'V'} <= expected['types']
         and not {request, bridge_owner} & expected['types'], 'Unexpected original bridge types')
    need(field not in expected['fields'] and not {forwarder, bridge} & expected['methods'],
         'Added field or method reference collision')
    need(bridge in addition['methods'], 'Separate helper lacks the bridge reference')
    original_counts = {kind: len(rows) for kind, rows in original.items()}
    expected['strings'].update((request, bridge_owner, field[1], forwarder[1], bridge[1], b'VLLIZ', b'VLLLLIZ'))
    expected['types'].update((request, bridge_owner))
    expected['protos'].update((proto, external_proto))
    expected['fields'].add(field)
    expected['methods'].update((forwarder, bridge))
    for kind, rows in expected.items():
        need(rows == actual[kind], 'Unexpected symbolic pool delta: ' + kind)
    for kind in ('types', 'protos', 'fields', 'methods'):
        need(len(actual[kind]) <= 65536, '16-bit pool overflow: ' + kind)
    return {kind: len(actual[kind]) - original_counts[kind] for kind in actual}


def declarations(dex):
    result = {row['descriptor']: (row['partition'], row['accessFlags'], bool(row['codeOffset']))
              for row in dex.members}
    need(len(result) == len(dex.members), 'Duplicate encoded member declaration')
    return result


def verify_declarations(source, target):
    expected = declarations(source)
    need(FORWARDER not in expected and FIELD not in expected, 'Added declaration collision')
    expected[FORWARDER] = ('directMethods', 0x02, True)
    expected[FIELD] = ('instanceFields', 0x1042, False)
    need(declarations(target) == expected, 'Unexpected encoded member delta')


def unique_code(dex, row):
    extent = mapped_extent(dex, 0x2001)
    offset = row['codeOffset']
    need(extent is not None and extent[1] <= offset < extent[2]
         and sum(other['codeOffset'] == offset for other in dex.codes) == 1,
         'Missing or aliased selected code item: ' + row['descriptor'])
    return read_code(dex, offset, extent[2])


def verify_cut(source, target):
    old = member(source, TARGET, 'virtualMethods', 0x11)
    new = member(target, TARGET, 'virtualMethods', 0x11)
    forwarder = member(target, FORWARDER, 'directMethods', 0x02)
    field = member(target, FIELD, 'instanceFields', 0x1042)
    forwarder_id = pool_index(target.methods, FORWARDER)
    field_id = pool_index(target.fields, FIELD)
    bridge_id = pool_index(target.methods, BRIDGE)
    stock_id = pool_index(target.methods, ORIGINAL)
    need(field_id == field['memberIndex'], 'Unexpected task field ID')

    old_header, old_words = unique_code(source, old)
    new_header, new_words = unique_code(target, new)
    new_invoke = (0x5270, forwarder_id, 0x3716)
    need(old['codeOffset'] == SOURCE_OFFSET and old_header == SOURCE_HEADER
         and digest(code(source, old)) == SOURCE_CODE_SHA
         and pool_index(source.methods, ORIGINAL) == STOCK_WORDS[1]
         and old_words[CUT_PC:CUT_PC + 3] == STOCK_WORDS, 'Original final callback code drift')
    need(new_header == TARGET_HEADER and new_words[CUT_PC:CUT_PC + 3] == new_invoke,
         'Unexpected final callback header or exact five-register invoke')

    words = (
        0x1054, field_id,          # PC 0: v0 = this(v1).oneos$pinRequest
        0x0038, 6,                 # PC 2: null branches to the original callback
        0x0677, bridge_id, 0,      # PC 4: invoke-static/range v0..v5
        0x000e,                    # PC 7: return after bridge
        0x4072, stock_id, 0x5432,  # PC 8: callback(v2).onChecked(v3, v4, v5)
        0x000e,                    # PC 11: return after original callback
    )
    need(unique_code(target, forwarder) == ((6, 5, 6, 0, 0, len(words)), words),
         'Unexpected final callback forwarder body')
    scan_count = scan_slot_accesses(target, field_id, forwarder['codeOffset'])
    return new_invoke, {
        'method': TARGET, 'oldCodeOffset': old['codeOffset'], 'newCodeOffset': new['codeOffset'],
        'cutPc': CUT_PC, 'oldHeader': old_header, 'newHeader': new_header,
        'oldInvokeWords': STOCK_WORDS, 'newInvokeWords': new_invoke, 'resumeOriginalAtPc': 64,
        'forwarder': FORWARDER, 'forwarderCodeOffset': forwarder['codeOffset'],
        'stockFallbackPc': 8, 'bridge': BRIDGE, 'field': FIELD, 'fieldId': field_id,
        'fieldReads': 1, 'fieldWrites': 0, 'fieldHandles': 0, 'scannedCodeItems': scan_count,
    }


def try_identity(dex, row, shape):
    return [
        (block['startPc'], block['codeUnits'],
         [(handler['exceptionType'], handler['handlerPc']) for handler in block['handlers']])
        for block in raw_tries(dex, row, {'tries': shape[3], 'units': shape[4]})
    ]


def verify_preservation(source, target, readers, new_invoke):
    target_members = {row['descriptor']: row for row in target.codes}
    index_maps = {kind: {value: index for index, value in enumerate(getattr(target, kind))}
                  for kind in ('strings', 'types', 'protos', 'fields', 'methods')}
    result_debug = readers['RawDebug'](target.d, target.strings, [kind.encode() for kind in target.types])
    target_debug_cache = {}
    source_debug = readers['RawDebug'](source.d, source.strings, [kind.encode() for kind in source.types])
    source_debug_cache = {}
    owners = {}
    for row in source.codes:
        name = row['descriptor']
        emitted = target_members[name]
        shape = header(source, row)
        wanted = expected_code(source, target, row, False, index_maps)
        if name == TARGET:
            shape[2] = 5
            start = CUT_PC * 2
            wanted = wanted[:start] + struct.pack('<3H', *new_invoke) + wanted[start + 6:]
        need(header(target, emitted) == shape, 'Unexpected preserved code header: ' + name)
        need(code(target, emitted) == wanted, 'Unexpected raw instruction delta: ' + name)
        need(try_identity(source, row, shape) == try_identity(target, emitted, shape),
             'Unexpected try/catch delta: ' + name)
        old_debug = source.u32(row['codeOffset'] + 8)
        new_debug = target.u32(emitted['codeOffset'] + 8)
        need(bool(old_debug) == bool(new_debug), 'Unexpected debug presence: ' + name)
        if old_debug:
            if old_debug not in source_debug_cache:
                source_debug_cache[old_debug] = clean_debug(source_debug.read(old_debug))
            if new_debug not in target_debug_cache:
                target_debug_cache[new_debug] = clean_debug(result_debug.read(new_debug))
            need(source_debug_cache[old_debug] == target_debug_cache[new_debug],
                 'Unexpected debug event delta: ' + name)
        old_offset = row['codeOffset']
        need(owners.setdefault(emitted['codeOffset'], old_offset) == old_offset,
             'Distinct preserved code items were aliased: ' + name)
    return {'originalCodedMethods': len(source.codes),
            'symbolicRawWordsExact': True, 'codeHeadersTriesAndDebugExact': True}


def validate(source, helper, candidate):
    """Read back the pinned donor and caller-verified helper cohort without execution."""
    for raw in (source, helper, candidate):
        need(type(raw) is bytes and 112 <= len(raw) <= MAX_BYTES, 'Ordinary DEX input byte bound')
    need(len(source) == 10_177_500 and digest(source) == SOURCE_SHA, 'Held donor DEX differs')
    readers = load_readers()
    original, addition, result = (readers['Dex'](raw) for raw in (source, helper, candidate))
    added_pools = verify_pools(original, addition, result, readers)
    verify_declarations(original, result)
    new_invoke, cut = verify_cut(original, result)
    donor_sections, candidate_sections = (
        {row['type'] for row in dex.map} for dex in (original, result)
    )
    need(candidate_sections == donor_sections and 0xf000 not in candidate_sections,
         'Unexpected map section or hidden API data')
    map_proof = readers['raw_map'](result, {'Debug': readers['RawDebug']})
    preservation = verify_preservation(original, result, readers, new_invoke)
    return {
        'status': 'PASS_STATIC_DISABLED_SPLIT_PIN_FINAL_CALLBACK_RETARGET',
        'sourceSha256': SOURCE_SHA, 'helperSha256': digest(helper),
        'helperDefinitions': len(HELPER_CLASSES), 'helperMerged': False,
        'candidateSha256': digest(candidate), 'candidateBytes': len(candidate),
        'poolCounts': result.counts, 'addedPoolCountsOverDonor': added_pools,
        'callSite': cut, 'preservation': preservation, 'map': map_proof,
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Held classes3.dex or exact donor SystemUI APK')
    parser.add_argument('helper', type=Path, help='Caller-verified final callback helper DEX')
    parser.add_argument('candidate', type=Path, help='Standalone emitted DEX039')
    args = parser.parse_args()
    print(json.dumps(validate(source_input(args.source), bounded(args.helper), bounded(args.candidate)), indent=2))


if __name__ == '__main__':
    main()
