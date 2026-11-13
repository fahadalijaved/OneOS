"""Read back the dormant Settings fingerprint preference-bind retarget from raw DEX039."""

import argparse
import json
from pathlib import Path
import re
import struct

from check_guest_pin_final_callback_retarget import declarations, try_identity, unique_code
from check_guest_pin_lifecycle_bridge_body import instructions, mapped_extent, member, pool_index, read_code
from check_guest_pin_lifecycle_pools import MAX_BYTES, bounded, digest, load_readers, need, symbolic
from prepare_guest_policy_init_retarget import clean_debug, code, expected_code, header


SOURCE_SHA = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
SOURCE_BYTES = 5_737_616
HELPER_SHA = '0ada17826b7090664972731fa75a6fd61e31a3a440f3f32ddcdb572e17c4b8b3'
HELPER_BYTES = 22_708
FRAGMENT_OWNED_HELPER_SHA = '37facf79e09b94e23c996c4bdca16f52af524be4c70bcd037f890ad7ba1fcaf0'
FRAGMENT_OWNED_HELPER_BYTES = 26_496
SOURCE_ACCESS_HELPER_SHA = 'c99ab1eb24bb3abf4e93f7029ad726bf28202c5aa206df191001d52984b9bc19'
SOURCE_ACCESS_HELPER_BYTES = 39_424
FRAGMENT = 'Lcom/oplus/settings/feature/fingerprint/OplusFingerprintSettings$FingerprintSettingsFragment;'
DASHBOARD = 'Lcom/android/settings/dashboard/DashboardFragment;'
CREATE_SIGNATURE = 'onCreatePreferences(Landroid/os/Bundle;Ljava/lang/String;)V'
CREATE = FRAGMENT + '->' + CREATE_SIGNATURE
ORIGINAL_CREATE = DASHBOARD + '->' + CREATE_SIGNATURE
CREATE_OFFSET = 1_609_820
CREATE_HEADER = (3, 3, 3, 0, 0, 67)
CREATE_WORDS = (0x306f, 0x0b8a, 0x0210)
FORWARD_CREATE = FRAGMENT + '->oneos$forwardCreatePreferences(Landroid/os/Bundle;Ljava/lang/String;)V'
PREFERENCE_FRAGMENT = 'Landroidx/preference/PreferenceFragmentCompat;'
SETTINGS_FRAGMENT = 'Lcom/android/settings/SettingsPreferenceFragment;'
SETTINGS_BASE = 'Lcom/oplus/settings/SettingsBaseFragment;'
SCREEN = 'Landroidx/preference/PreferenceScreen;'
ADAPTER = 'Landroidx/recyclerview/widget/RecyclerView$Adapter;'
BIND = 'bindPreferences()V'
CREATE_ADAPTER = 'onCreateAdapter(' + SCREEN + ')' + ADAPTER
UNBIND = 'onUnbindPreferences()V'
SET_SCREEN = 'setPreferenceScreen(' + SCREEN + ')V'
DESTROY_VIEW = 'onDestroyView()V'
STOCK_BIND = PREFERENCE_FRAGMENT + '->' + BIND
STOCK_ADAPTER = SETTINGS_FRAGMENT + '->' + CREATE_ADAPTER
STOCK_UNBIND = SETTINGS_FRAGMENT + '->' + UNBIND
STOCK_SET_SCREEN = SETTINGS_FRAGMENT + '->' + SET_SCREEN
STOCK_DESTROY_VIEW = SETTINGS_BASE + '->' + DESTROY_VIEW
ADDED_METHODS = {
    **{FRAGMENT + '->' + name: ('virtualMethods', 0x01, True)
       for name in (BIND, CREATE_ADAPTER, UNBIND, SET_SCREEN, DESTROY_VIEW)},
    FORWARD_CREATE: ('directMethods', 0x02, True),
}
STOCK_METHODS = (STOCK_BIND, STOCK_ADAPTER, STOCK_UNBIND, STOCK_SET_SCREEN, STOCK_DESTROY_VIEW, ORIGINAL_CREATE)
CAPTURE = 'Lcom/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceBindCapture;'
CAPTURE_CTOR = CAPTURE + '-><init>(' + PREFERENCE_FRAGMENT + ')V'
BIND_TOKEN = CAPTURE[:-1] + '$Bind;'
FIELD = FRAGMENT + '->oneos$preferenceBind:' + CAPTURE
SOURCE_ACCESSOR = FRAGMENT + '->oneos$getPreferenceBind()' + CAPTURE
SOURCE_ACCESSOR_DECLARATION = ('virtualMethods', 0x10, True)
SOURCE_ACCESSOR_HEADER = (2, 1, 0, 0, 0, 3)
BRIDGE_METHODS = tuple(CAPTURE + '->' + method for method in (
    'beginBind()' + BIND_TOKEN,
    'finishBind(' + BIND_TOKEN + ')V',
    'currentBind()' + BIND_TOKEN,
    'recordAdapter(' + BIND_TOKEN + SCREEN + ADAPTER + ')V',
    'retire()V',
    'retireIfScreenChanges(' + SCREEN + ')V',
    'abortBind(' + BIND_TOKEN + ')V',
))
HELPER_CLASSES = {
    ('Lcom/appleexploit/oneos/security/transport/' + name + ';').encode('ascii')
    for name in (
        'FingerprintEnrollmentPreferenceBindCapture', 'FingerprintEnrollmentPreferenceBindCapture$1',
        'FingerprintEnrollmentPreferenceBindCapture$Bind', 'FingerprintEnrollmentPreferenceBindCapture$BoundView',
        'FingerprintEnrollmentPreferenceSection', 'FingerprintEnrollmentPreferenceSection$State',
        'FingerprintEnrollmentPreferenceSession', 'FingerprintEnrollmentPreferenceSession$1',
        'FingerprintEnrollmentPreferenceSession$Refresh', 'FingerprintEnrollmentPreferenceViewBinding',
        'FingerprintEnrollmentPresentation', 'FingerprintEnrollmentPresentation$Status',
        'RetainedFingerprintEnrollmentReport', 'RetainedFingerprintEnrollmentReport$Row',
    )
}
FRAGMENT_OWNED_HELPER_CLASSES = HELPER_CLASSES | {
    ('Lcom/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceReportOwner' + suffix + ';').encode('ascii')
    for suffix in ('', '$1', '$SubjectSource')
}
SOURCE_ACCESS_HELPER_CLASSES = FRAGMENT_OWNED_HELPER_CLASSES | {
    ('Lcom/appleexploit/oneos/security/transport/FingerprintEnrollmentPreference' + name + ';').encode('ascii')
    for name in ('Feed', 'Feed$1', 'Feed$Listener', 'Feed$Request', 'Feed$ViewSource', 'FeedBinding',
                 'ReadySignal', 'ReadySignal$1', 'ReadySignal$Listener', 'ReadySignal$Pulse')
}


def symbolic_method(reference):
    owner, member_signature = reference.encode('ascii').split(b'->', 1)
    name, prototype = member_signature.split(b'(', 1)
    parameters, result = prototype.split(b')', 1)
    arguments = tuple(re.findall(rb'\[*(?:[ZBSCIJFD]|L[^;]+;)', parameters))
    need(b''.join(arguments) == parameters, 'Invalid planned method parameter descriptors')
    return owner, name, (result, arguments)


def add_method_reference(pools, reference):
    owner, name, prototype = symbolic_method(reference)
    result, parameters = prototype
    types = (result, *parameters)
    shorty = b''.join(b'L' if value.startswith((b'L', b'[')) else value for value in types)
    pools['strings'].update((owner, name, shorty, *types))
    pools['types'].update((owner, *types))
    pools['protos'].add(prototype)
    pools['methods'].add((owner, name, prototype))


def add_field_reference(pools, reference):
    owner, name_and_type = reference.encode('ascii').split(b'->', 1)
    name, value = name_and_type.split(b':', 1)
    pools['strings'].update((owner, name, value))
    pools['types'].update((owner, value))
    pools['fields'].add((owner, name, value))


def verify_pools(source, helper, target, readers, *, fragment_owned=False, source_access=False):
    expected, addition, actual = (symbolic(dex, readers) for dex in (source, helper, target))
    if source_access:
        helper_classes = SOURCE_ACCESS_HELPER_CLASSES
    else:
        helper_classes = FRAGMENT_OWNED_HELPER_CLASSES if fragment_owned else HELPER_CLASSES
    need(addition['classes'].keys() == helper_classes
         and all(addition['classes'][name.encode('ascii')][0] & 0x01 for name in (CAPTURE, BIND_TOKEN)),
         'Unexpected exact public preference-bind helper definitions')
    need(not expected['classes'].keys() & addition['classes'].keys()
         and b'oneos$preferenceBind' not in addition['strings'],
         'Separate helper collides or references the dormant field')
    helper_methods = declarations(helper)
    for reference in BRIDGE_METHODS:
        part, flags, has_code = helper_methods.get(reference, (None, 0, False))
        need(part == 'virtualMethods' and flags & 0x09 == 0x01 and has_code,
             'Missing public instance capture method: ' + reference)
    added_bridge_methods = BRIDGE_METHODS
    if fragment_owned:
        need(helper_methods.get(CAPTURE_CTOR) == ('directMethods', 0x10001, True),
             'Missing exact public capture constructor')
        added_bridge_methods = (*BRIDGE_METHODS, CAPTURE_CTOR)

    added_methods = (*ADDED_METHODS, SOURCE_ACCESSOR) if source_access else tuple(ADDED_METHODS)
    before = {kind: len(rows) for kind, rows in expected.items()}
    need(not {symbolic_method(name) for name in (*added_methods, *added_bridge_methods)} & expected['methods'],
         'Added method reference collides with source')
    need(b'oneos$preferenceBind' not in expected['strings'], 'Added field name collides with source')
    for reference in (*added_methods, *added_bridge_methods, *STOCK_METHODS):
        add_method_reference(expected, reference)
    add_field_reference(expected, FIELD)
    for kind, rows in expected.items():
        need(rows == actual[kind], 'Unexpected symbolic pool delta: ' + kind)
    for kind in ('types', 'protos', 'fields', 'methods'):
        need(len(actual[kind]) <= 65536, '16-bit pool overflow: ' + kind)
    return {kind: len(actual[kind]) - before[kind] for kind in actual}


def verify_declarations(source, target, *, source_access=False):
    expected = declarations(source)
    added = {**ADDED_METHODS, SOURCE_ACCESSOR: SOURCE_ACCESSOR_DECLARATION} if source_access else ADDED_METHODS
    need(not expected.keys() & (added.keys() | {FIELD}), 'Added declarations collide with source')
    expected.update(added)
    expected[FIELD] = ('instanceFields', 0x02, False)
    need(declarations(target) == expected, 'Unexpected encoded member delta')


def scan_field(dex, field_id, expected_reads, expected_writes=()):
    extent = mapped_extent(dex, 0x2001)
    need(extent is not None, 'Missing code map')
    count, start, limit = extent
    offsets = sorted({row['codeOffset'] for row in dex.codes})
    need(offsets and len(offsets) == count and offsets[0] == start and offsets[-1] < limit,
         'Unexpected code item coverage')
    reads, writes = [], []
    for offset, following in zip(offsets, offsets[1:] + [limit]):
        _, words = read_code(dex, offset, following)
        for pc, opcode in instructions(words):
            if 0x52 <= opcode <= 0x6d and words[pc + 1] == field_id:
                if opcode == 0x54:
                    reads.append((offset, pc))
                elif opcode == 0x5b and expected_writes:
                    writes.append((offset, pc))
                else:
                    need(False, 'Unexpected preference-bind field opcode, including any write')
    need(reads == sorted(expected_reads), 'Unexpected preference-bind field reads')
    need(writes == sorted(expected_writes), 'Unexpected preference-bind field writes')
    need(mapped_extent(dex, 0x0008) is None, 'Unexpected method handle section')
    return count


def verify_bodies(source, target, *, fragment_owned=False, source_access=False):
    old = member(source, CREATE, 'virtualMethods', 0x01)
    new = member(target, CREATE, 'virtualMethods', 0x01)
    old_header, old_words = unique_code(source, old)
    new_header, new_words = unique_code(target, new)
    method_id = lambda ref: pool_index(target.methods, ref)
    new_invoke = (0x3070, method_id(FORWARD_CREATE), 0x0210)
    need(old['codeOffset'] == CREATE_OFFSET and old_header == CREATE_HEADER
         and old_words[:3] == CREATE_WORDS
         and source.methods[CREATE_WORDS[1]] == ORIGINAL_CREATE,
         'Original onCreatePreferences frame or exact super call differs')
    need(new_header == CREATE_HEADER and new_words[:3] == new_invoke,
         'Unexpected onCreatePreferences header or exact three-register invoke')
    need(old_words[-1] == new_words[-1] == 0x000e, 'Original onCreatePreferences return changed')

    capture = member(target, FIELD, 'instanceFields', 0x02)
    field_id = pool_index(target.fields, FIELD)
    need(capture['memberIndex'] == field_id, 'Unexpected preference-bind field ID')
    begin, finish, current, record, retire, retire_changed, abort = map(method_id, BRIDGE_METHODS)
    bind_words = (
        0x3054, field_id, 0x0112, 0x0038, 6,
        0x106e, begin, 0, 0x010c,
        0x106f, method_id(STOCK_BIND), 3,
        0x0138, 5, 0x206e, finish, 0x0010, 0x000e,
        0x020d, 0x0138, 5, 0x206e, abort, 0x0010, 0x0227,
    )
    adapter_words = (
        0x3054, field_id, 0x0112, 0x0038, 6,
        0x106e, current, 0, 0x010c,
        0x206f, method_id(STOCK_ADAPTER), 0x0043, 0x020c,
        0x0138, 5, 0x406e, record, 0x2410, 0x0211,
    )
    unbind_words = (
        0x1054, field_id, 0x0038, 5, 0x106e, retire, 0,
        0x106f, method_id(STOCK_UNBIND), 1, 0x000e,
    )
    destroy_words = (
        0x1054, field_id, 0x0038, 5, 0x106e, retire, 0,
        0x106f, method_id(STOCK_DESTROY_VIEW), 1, 0x000e,
    )
    set_screen_words = (
        0x1054, field_id, 0x0038, 5, 0x206e, retire_changed, 0x0020,
        0x206f, method_id(STOCK_SET_SCREEN), 0x0021, 0x000e,
    )
    if fragment_owned:
        capture_type = pool_index(target.types, CAPTURE)
        forward_create = ((4, 3, 3, 1, 0, 21), (
            0x1054, field_id, 0x0039, 10,
            0x0022, capture_type, 0x2070, method_id(CAPTURE_CTOR), 0x0010,
            0x105b, field_id, 0x0428, 0x106e, retire, 0,
            0x306f, method_id(ORIGINAL_CREATE), 0x0321, 0x000e, 0x000d, 0xfb28,
        ))
    else:
        forward_create = ((4, 3, 3, 0, 0, 11), (
            0x1054, field_id, 0x0038, 5, 0x106e, retire, 0,
            0x306f, method_id(ORIGINAL_CREATE), 0x0321, 0x000e,
        ))
    expected = {
        FRAGMENT + '->' + BIND: ((4, 1, 2, 1, 0, 25), bind_words),
        FRAGMENT + '->' + CREATE_ADAPTER: ((5, 2, 4, 0, 0, 19), adapter_words),
        FRAGMENT + '->' + UNBIND: ((2, 1, 1, 0, 0, 11), unbind_words),
        FRAGMENT + '->' + SET_SCREEN: ((3, 2, 2, 0, 0, 11), set_screen_words),
        FRAGMENT + '->' + DESTROY_VIEW: ((2, 1, 1, 0, 0, 11), destroy_words),
        FORWARD_CREATE: forward_create,
    }
    locations = {}
    for name, body in expected.items():
        row = member(target, name, *ADDED_METHODS[name][:2])
        need(unique_code(target, row) == body, 'Unexpected exact preference-bind wrapper: ' + name)
        catches = [(9, 3, [(None, 18)])] if name == FRAGMENT + '->' + BIND else []
        if fragment_owned and name == FORWARD_CREATE:
            catches = [(0, 15, [(None, 19)])]
        need(try_identity(target, row, header(target, row)) == catches, 'Unexpected wrapper catch range: ' + name)
        locations[name] = row['codeOffset']
    writes = [(locations[FORWARD_CREATE], 9)] if fragment_owned else []
    reads = [(offset, 0) for offset in locations.values()]
    accessor = {}
    if source_access:
        row = member(target, SOURCE_ACCESSOR, *SOURCE_ACCESSOR_DECLARATION[:2])
        need(unique_code(target, row) == (SOURCE_ACCESSOR_HEADER, (0x1054, field_id, 0x0011)),
             'Unexpected exact package-private source accessor')
        reads.append((row['codeOffset'], 0))
        accessor = {'sourceAccessor': {'method': SOURCE_ACCESSOR, 'codeOffset': row['codeOffset'],
                                      'accessFlags': 0x10, 'header': SOURCE_ACCESSOR_HEADER, 'fieldReadPc': 0}}
    scanned = scan_field(target, field_id, reads, writes)
    return new_invoke, {
        'method': CREATE, 'oldCodeOffset': old['codeOffset'], 'newCodeOffset': new['codeOffset'],
        'header': CREATE_HEADER, 'cutPc': 0, 'oldInvokeWords': CREATE_WORDS, 'newInvokeWords': new_invoke,
        'stockCalls': STOCK_METHODS, 'wrapperCodeOffsets': locations, 'field': FIELD, 'fieldId': field_id,
        'bindStockTry': [9, 12], 'bindCatchAllPc': 18,
        'fieldReads': len(reads), 'fieldWrites': len(writes), 'fieldHandles': 0, 'scannedCodeItems': scanned,
        **({'forwardCreateTry': [0, 15], 'forwardCreateCatchAllPc': 19, 'fieldWritePc': 9}
           if fragment_owned else {}),
        **accessor,
    }


def verify_preservation(source, target, readers, new_invoke):
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
        shape = header(source, row)
        wanted = expected_code(source, target, row, False, index_maps)
        if name == CREATE:
            wanted = struct.pack('<3H', *new_invoke) + wanted[6:]
        need(header(target, emitted) == shape, 'Unexpected preserved code header: ' + name)
        need(code(target, emitted) == wanted, 'Unexpected raw instruction delta: ' + name)
        need(try_identity(source, row, shape) == try_identity(target, emitted, shape),
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


def validate(source, helper, candidate, *, fragment_owned=False, source_access=False):
    """Compare the exact donor and separate helper to the independently emitted retarget."""
    for raw in (source, helper, candidate):
        need(type(raw) is bytes and 112 <= len(raw) <= MAX_BYTES, 'Ordinary DEX input byte bound')
    need(len(source) == SOURCE_BYTES and digest(source) == SOURCE_SHA, 'Held donor Settings DEX differs')
    fragment_owned = fragment_owned or source_access
    if source_access:
        helper_bytes, helper_sha = SOURCE_ACCESS_HELPER_BYTES, SOURCE_ACCESS_HELPER_SHA
        helper_classes = SOURCE_ACCESS_HELPER_CLASSES
    elif fragment_owned:
        helper_bytes, helper_sha = FRAGMENT_OWNED_HELPER_BYTES, FRAGMENT_OWNED_HELPER_SHA
        helper_classes = FRAGMENT_OWNED_HELPER_CLASSES
    else:
        helper_bytes, helper_sha = HELPER_BYTES, HELPER_SHA
        helper_classes = HELPER_CLASSES
    need(len(helper) == helper_bytes and digest(helper) == helper_sha, 'Held separate preference-bind helper differs')
    readers = load_readers()
    original, addition, result = (readers['Dex'](raw) for raw in (source, helper, candidate))
    added_pools = verify_pools(original, addition, result, readers, fragment_owned=fragment_owned,
                              source_access=source_access)
    verify_declarations(original, result, source_access=source_access)
    new_invoke, cut = verify_bodies(original, result, fragment_owned=fragment_owned, source_access=source_access)
    source_sections, result_sections = ({row['type'] for row in dex.map} for dex in (original, result))
    need(result_sections == source_sections and 0xf000 not in result_sections,
         'Unexpected map section or hidden API data')
    map_proof = readers['raw_map'](result, {'Debug': readers['RawDebug']})
    return {
        'status': 'PASS_STATIC_DISABLED_SPLIT_FINGERPRINT_PREFERENCE_BIND_RETARGET',
        'sourceSha256': SOURCE_SHA, 'helperSha256': helper_sha,
        'helperDefinitions': len(helper_classes),
        'helperMerged': False,
        'candidateSha256': digest(candidate), 'candidateBytes': len(candidate),
        'poolCounts': result.counts, 'addedPoolCountsOverDonor': added_pools,
        'callSite': cut, 'preservation': verify_preservation(original, result, readers, new_invoke),
        'map': map_proof, 'selected': False, 'deviceEligible': False, 'targetExecuted': False,
        **({'fragmentOwned': True} if fragment_owned else {}),
        **({'sourceAccess': True} if source_access else {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Held donor Settings classes2.dex')
    parser.add_argument('helper', type=Path, help='Held separate preference-bind helper DEX')
    parser.add_argument('candidate', type=Path, help='Standalone emitted classes2.dex')
    parser.add_argument('--fragment-owned', action='store_true', help='Check the fragment-owned capture variant')
    parser.add_argument('--source-access', action='store_true', help='Check the fragment-owned source accessor variant')
    args = parser.parse_args()
    print(json.dumps(validate(bounded(args.source), bounded(args.helper), bounded(args.candidate),
                              fragment_owned=args.fragment_owned, source_access=args.source_access), indent=2))


if __name__ == '__main__':
    main()
