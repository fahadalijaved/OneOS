"""Closed ordinary039 DMS three-hook outs_size restoration; no semantic admission.

Input/output are static bytes. No OEM code, writer, native or device execution.
The original source, three changes and one new method are literal, not options.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
PARSER_PATH = ROOT / 'tools/preserve_dex_code_headers.py'
PARSER_SHA256 = '943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6'
SOURCE_ARCHIVE_SHA256 = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
SOURCE_SHA256 = 'c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f'
SOURCE_BYTES = 10042704
SOURCE_METHODS = 46864
SOURCE_CODED_METHODS = 45059
DMS = b'Lcom/android/server/display/DisplayManagerService;'
DISPATCH = DMS + b'->dispatchOneOsGuestMetricsFromParent(Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z'
HOOKS = {
    DMS + b'->onStart()V': ((4, 1, 4, 2, 57), (4, 1, 4, 3, 65)),
    DMS + b'->onBootPhase(I)V': ((12, 2, 3, 5, 277), (12, 2, 3, 6, 286)),
    b'Lcom/android/server/display/DisplayManagerService$BinderService;->onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z':
        ((7, 5, 5, 0, 27), (7, 5, 5, 0, 39)),
}
DISPATCH_HEADER = (6, 5, 6, 0, 11)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def _parser():
    need(digest(PARSER_PATH.read_bytes()) == PARSER_SHA256, 'Frozen parser/seal dependency pin')
    specification = importlib.util.spec_from_file_location('closed_parent_header_parser', PARSER_PATH)
    module = importlib.util.module_from_spec(specification)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        specification.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _debug_present(dex, row):
    return bool(row['codeOffset'] and dex.codes[row['codeOffset']]['debugOffset'])


def _plan(source, emitted):
    need(len(source.methods) == SOURCE_METHODS and
         sum(bool(m['codeOffset']) for m in source.methods.values()) == SOURCE_CODED_METHODS,
         'Literal original declared/coded method counts')
    need(DISPATCH not in source.methods and set(HOOKS) <= source.methods.keys(), 'Literal source method frontier')
    need(source.classes == emitted.classes, 'Class identity set changed')
    need(emitted.methods.keys() == source.methods.keys() | {DISPATCH}, 'Only literal new dispatch may be declared')
    need(sum(bool(m['codeOffset']) for m in emitted.methods.values()) == SOURCE_CODED_METHODS + 1,
         'Exact emitted coded method count')
    expected_rows = {}
    for identity, original in source.methods.items():
        actual = emitted.methods[identity]
        need((original['flags'], original['partition'], bool(original['codeOffset'])) ==
             (actual['flags'], actual['partition'], bool(actual['codeOffset'])),
             'Original flags/partition/code presence changed')
        need(_debug_present(source, original) == _debug_present(emitted, actual), 'Original debug presence changed')
        if original['header'] is None:
            continue
        expected = original['header']
        if identity in HOOKS:
            original_header, expected = HOOKS[identity]
            need(original['header'] == original_header, 'Literal source hook header')
        expected_rows[identity] = expected
    added = emitted.methods[DISPATCH]
    need(added['flags'] == 0 and added['partition'] == 'virtual' and bool(added['codeOffset']),
         'New dispatch flags/partition/code presence')
    need(not _debug_present(emitted, added), 'New dispatch debug must be zero')
    expected_rows[DISPATCH] = DISPATCH_HEADER
    groups = {}
    for identity, expected in expected_rows.items():
        actual = emitted.methods[identity]
        header = actual['header']
        need(header is not None and tuple(header[n] for n in (0, 1, 3, 4)) ==
             tuple(expected[n] for n in (0, 1, 3, 4)), 'Non-outs code header drift')
        word = actual['codeOffset'] + 4
        if word in groups:
            need(groups[word]['wanted'] == expected[2] and groups[word]['actual'] == header[2],
                 'Conflicting shared output code outs mapping')
        else:
            groups[word] = {'wanted': expected[2], 'actual': header[2], 'methods': []}
        groups[word]['methods'].append(identity)
    changes = {word: row for word, row in groups.items() if row['wanted'] != row['actual']}
    return changes, groups


def preserve_guest_metrics_parent_headers(source, emitted, *, emitted_sha256):
    """Return (repaired bytes, receipt); apply after EVERY emit against ORIGINAL.

    emitted_sha256 identifies caller input, never attests its producer/authority.
    This function performs no filesystem writes and never changes the inputs.
    """
    need(isinstance(source, bytes) and len(source) == SOURCE_BYTES and digest(source) == SOURCE_SHA256,
         'Literal original source pin')
    need(isinstance(emitted_sha256, str) and len(emitted_sha256) == 64 and
         all(c in '0123456789abcdef' for c in emitted_sha256), 'Explicit emitted input hash required')
    need(isinstance(emitted, bytes) and digest(emitted) == emitted_sha256, 'Emitted input pin')
    parser = _parser()
    original = parser.Dex039(source)
    candidate = parser.Dex039(emitted)
    changes, groups = _plan(original, candidate)  # Complete admission before mutation.
    output = bytearray(emitted)
    for word, row in changes.items():
        struct.pack_into('<H', output, word, row['wanted'])
    repaired = parser.seal(output)
    parser._assert_byte_whitelist(emitted, repaired, changes)
    checked = parser.Dex039(repaired)
    remaining, _ = _plan(original, checked)
    need(not remaining, 'Post-repair outs mismatch')
    need(len(repaired) == len(emitted) and candidate.methods.keys() == checked.methods.keys(),
         'Repair extent/identity drift')
    repairs = [{'offset': word, 'oldOuts': row['actual'], 'expectedOuts': row['wanted'],
                'methodIdentities': [x.decode('utf-8', 'backslashreplace') for x in row['methods']]}
               for word, row in sorted(changes.items())]
    return repaired, {
        'schema': 'guest-metrics-parent-header-preservation/v1',
        'sourceArchiveSha256': SOURCE_ARCHIVE_SHA256, 'sourceEntry': 'classes2.dex',
        'sourceSha256': SOURCE_SHA256, 'sourceBytes': SOURCE_BYTES,
        'inputSha256': emitted_sha256, 'repairedSha256': digest(repaired),
        'moduleSha256': digest(Path(__file__).read_bytes()), 'parserSha256': PARSER_SHA256,
        'sourceDeclaredMethods': len(original.methods), 'emittedDeclaredMethods': len(checked.methods),
        'sourceCodedMethods': SOURCE_CODED_METHODS, 'emittedCodedMethods': SOURCE_CODED_METHODS + 1,
        'sourceUniqueCodeItems': len(original.codes), 'emittedUniqueCodeItems': len(checked.codes),
        'repairedOutsWords': len(changes), 'repairs': repairs,
        'sharedOutputCodeGroups': sum(len(row['methods']) > 1 for row in groups.values()),
        'byteWhitelist': 'Only expected outs_size uint16 words and DEX integrity bytes8..31',
        'postRepairAllHeadersReparsed': True, 'fileSizeUnchanged': True,
        'applyAfterEveryEmitAndReemitAgainstOriginal': True,
        'instructionFieldDebugMetadataOrAuthorityAccepted': False,
        'callerEmittedPinVerified': True, 'callerEmitterProvenanceAdmittedByThisModule': False,
        'oemOrRuntimeExecuted': False,
    }


def self_test(source):
    """Decoded-record guard probes plus authored actual-byte parser/whitelist probes.

    No new OEM emission is made or accepted by these tests.
    """
    need(len(source) == SOURCE_BYTES and digest(source) == SOURCE_SHA256, 'Self-test original pin')
    parser = _parser()
    original = parser.Dex039(source)
    candidate = copy.copy(original)
    candidate.methods = copy.deepcopy(original.methods)
    candidate.codes = copy.deepcopy(original.codes)
    for identity, row in candidate.methods.items():
        if row['header'] is not None:
            expected = HOOKS[identity][1] if identity in HOOKS else row['header']
            row['header'] = (*expected[:2], 0, *expected[3:])
    artificial_offset = len(source) + 4
    candidate.methods[DISPATCH] = {'flags': 0, 'partition': 'virtual', 'codeOffset': artificial_offset,
                                   'header': (6, 5, 0, 0, 11), 'methodIndex': -1}
    candidate.codes[artificial_offset] = {'header': (6, 5, 0, 0, 11), 'debugOffset': 0}
    changes, _ = _plan(original, candidate)
    need(changes and artificial_offset + 4 in changes, 'Decoded-record positive dispatch repair')
    results = ['record-positive-exact-frontier']
    def reject(name, mutate):
        probe = copy.copy(candidate)
        probe.methods = copy.deepcopy(candidate.methods)
        probe.codes = copy.deepcopy(candidate.codes)
        probe.classes = set(candidate.classes)
        mutate(probe)
        try:
            _plan(original, probe)
        except ValueError:
            results.append('record-reject-' + name)
        else:
            raise ValueError('Negative accepted: ' + name)
    hook = DMS + b'->onStart()V'
    reject('missing-original', lambda x: x.methods.pop(hook))
    reject('unexpected-method', lambda x: x.methods.__setitem__(b'Lunexpected;->m()V', dict(x.methods[DISPATCH])))
    reject('new-flags', lambda x: x.methods[DISPATCH].__setitem__('flags', 1))
    reject('new-partition', lambda x: x.methods[DISPATCH].__setitem__('partition', 'direct'))
    reject('new-debug', lambda x: x.codes[artificial_offset].__setitem__('debugOffset', 1))
    reject('original-flags', lambda x: x.methods[hook].__setitem__('flags', x.methods[hook]['flags'] ^ 1))
    reject('original-code-presence', lambda x: x.methods[hook].__setitem__('codeOffset', 0))
    for index, name in [(0, 'registers'), (1, 'incoming'), (3, 'tries'), (4, 'units')]:
        def mutate(x, n=index):
            row = x.methods[hook]; header = list(row['header']); header[n] += 1; row['header'] = tuple(header)
        reject(name, mutate)
    reject('class-set', lambda x: x.classes.add(b'Lunexpected;'))
    pairs = {}
    alias_pair = None
    for identity, row in original.methods.items():
        if row['header'] is None or identity in HOOKS:
            continue
        key = tuple(row['header'][n] for n in (0, 1, 3, 4)) + (_debug_present(original, row),)
        if key in pairs and pairs[key][1] != row['header'][2]:
            alias_pair = (pairs[key][0], identity); break
        pairs[key] = (identity, row['header'][2])
    need(alias_pair is not None, 'Discriminating source alias pair')
    reject('conflicting-shared-word', lambda x: x.methods[alias_pair[1]].__setitem__(
        'codeOffset', x.methods[alias_pair[0]]['codeOffset']))
    present = next(k for k, v in original.methods.items() if _debug_present(original, v))
    reject('original-debug-presence', lambda x: x.codes[x.methods[present]['codeOffset']].__setitem__('debugOffset', 0))
    fixture = parser._fixture()
    parsed = parser.Dex039(fixture)
    offset = next(iter(parsed.codes))
    fixed = bytearray(fixture); struct.pack_into('<H', fixed, offset + 4, 0)
    fixed = parser.seal(fixed); parser.Dex039(fixed)
    parser._assert_byte_whitelist(fixture, fixed, [offset + 4])
    results.append('byte-positive-outs-only-reseal-reparse')
    bad = bytearray(fixed); bad[offset + 16] ^= 1
    try:
        parser._assert_byte_whitelist(fixture, parser.seal(bad), [offset + 4])
    except ValueError:
        results.append('byte-reject-non-outs-instruction-mutation')
    else:
        raise ValueError('Byte whitelist accepted instruction mutation')
    return {'pass': True, 'count': len(results), 'cases': results,
            'recordProbesAreDecodedRecordsNotMalformedDex': True,
            'byteProbesAreSmallAuthoredDexFixtures': True,
            'newOemEmissionOrRuntimeExecuted': False}


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--self-test', action='store_true')
    options = arguments.parse_args()
    if not options.self_test:
        arguments.error('Use fixed import API; CLI has no repair/write mode')
    archive = ROOT.parent / 'firmware/donor/extracted/system/framework/services.jar'
    archive_bytes = archive.read_bytes()
    need(digest(archive_bytes) == SOURCE_ARCHIVE_SHA256, 'Original archive pin')
    with zipfile.ZipFile(archive) as contents:
        source = contents.read('classes2.dex')
    print(json.dumps(self_test(source)))


if __name__ == '__main__':
    main()
