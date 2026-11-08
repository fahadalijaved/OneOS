"""Compose the three reviewed Settings leaves into an unselected PC code ZIP."""

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
import re
import sys
import uuid
import zipfile

sys.dont_write_bytecode = True

from compose_coloros_ui_removals import UTILITY, UTILITY_SHA, admitted_component_conditions, combine_dex, digest, load_archive, utility
from run_guest_tree_install_transport import ROOT, load_io, pinned, sha, write_exclusive


SOURCE_NAME = 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk'
SOURCE = ROOT.parent / SOURCE_NAME
SOURCE_SHA = '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
SOURCE_BYTES = 280336937
COMPOSER = ROOT / 'tools/compose_coloros_ui_removals.py'
COMPOSER_SHA = 'ad2ff2001622be96f85502f6c6c8200f9af1e0fe3ff20683fb70b4c5e335c68c'
RPMB = ('inventory/coloros-settings-rpmb-leaf.json', '8d5e0dba53221b6c5720a4bac7e3c7f062ba8a0a148d3835176ffcfc84f9375e')
RETRIEVAL = ('inventory/coloros-retrieval-capability-leaf.json', '749bb14c7a863df6d79bc830a44cb48dba3ceead6811a8abe8ce51c0ab68006b')
NAME_LOG_SHA = 'bea7993c428bb828a75882b525e744cf6f22a51cf1ca41ad6d8c89919ac5207b'
NAME_LOG_ENTRY = 'classes2.dex'
NAME_LOG_ORIGINAL_SHA = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
NAME_LOG_METHOD_ID = 14225
NAME_LOG_FIRST_BYTE = 1604220
NAME_LOG_END_BYTE = 1604268
NAME_LOG_SLICE_SHA = 'ac8ce72525f41e208a514a3a519b833d01bdf23e5ced0bee5b0fe2b310c17cd2'
MAX_ENTRY_BYTES = 128 * 1024 * 1024
MAX_DEX_BYTES = 32 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024
DEX_NAMES = {'classes.dex', *(f'classes{i}.dex' for i in range(2, 15))}
OUT = ROOT / 'out/settings-fingerprint-name-log-composition'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def out_pin(pin):
    require(type(pin) is tuple and len(pin) == 2 and all(type(value) is str for value in pin), 'Expected a path/hash pin')
    name, expected = pin
    path = PurePosixPath(name)
    require(len(name) <= 512 and re.fullmatch(r'[A-Za-z0-9_./-]+', name) is not None
            and path.as_posix() == name and path.is_relative_to('out') and len(path.parts) > 1
            and '..' not in path.parts and re.fullmatch(r'[0-9a-f]{64}', expected) is not None,
            'Expected an exact repository output pin')
    return pin


def pin_row(pin):
    return dict(zip(('path', 'sha256'), pin))


def read_receipt(io, pin):
    return json.loads(pinned(io, *pin, MAX_RECEIPT_BYTES), object_pairs_hook=io['unique_object'])


def historical_leaf(io, receipt_pin, entry):
    receipt = read_receipt(io, receipt_pin)
    conditions = admitted_component_conditions(*receipt_pin, receipt, SOURCE_SHA)
    require(receipt['physicalDex'] == entry and receipt['phoneActions'] is False, 'Historical DEX scope differs')
    artifact_pin = out_pin((receipt['patchedDex'], receipt['patchedDexSha256']))
    data = pinned(io, *artifact_pin, MAX_DEX_BYTES)
    return data, conditions, {'receipt': pin_row(receipt_pin), 'dex': pin_row(artifact_pin), 'entry': entry,
                              'sourceDexSha256': receipt['sourceDexSha256']}


def name_log_leaf(io, receipt_pin, artifact_pin):
    receipt = read_receipt(io, receipt_pin)
    require(receipt['schema'] == 'oneos-coloros-settings-fingerprint-name-log-leaf/v1'
            and receipt['status'] == 'PASS_EXACT_UNSELECTED_SETTINGS_FINGERPRINT_NAME_LOG_LEAF'
            and all(receipt[key] is False for key in ('selected', 'deviceAction', 'targetExecuted')),
            'Expected exact unselected name-log leaf')
    donor = receipt['sourceArchive']
    original = receipt['sourceDex']
    emitted = receipt['outputDex']
    require(donor == {'path': SOURCE_NAME, 'bytes': SOURCE_BYTES, 'sha256': SOURCE_SHA}
            and (original['entry'], original['sha256']) == (NAME_LOG_ENTRY, NAME_LOG_ORIGINAL_SHA)
            and (emitted['path'], emitted['sha256']) == artifact_pin and emitted['sha256'] == NAME_LOG_SHA,
            'Name-log receipt does not join the exact Settings donor and DEX')
    data = pinned(io, *artifact_pin, MAX_DEX_BYTES)
    require(type(emitted['bytes']) is int and type(original['bytes']) is int
            and len(data) == emitted['bytes'] == original['bytes'], 'Name-log DEX extent differs')
    method = receipt['method']
    require((method['firstPc'], method['endExclusivePc'], method['firstByte'], method['endExclusiveByte'],
             method['sourceSliceSha256'], method['location']['methodId']) ==
            (86, 110, NAME_LOG_FIRST_BYTE, NAME_LOG_END_BYTE, NAME_LOG_SLICE_SHA, NAME_LOG_METHOD_ID)
            and method['inverseExact'] is True and method['roundtripExact'] is True
            and data[NAME_LOG_FIRST_BYTE:NAME_LOG_END_BYTE] == bytes(NAME_LOG_END_BYTE - NAME_LOG_FIRST_BYTE),
            'Name-log method scope or emitted instruction bytes differ')
    return data, {'receipt': pin_row(receipt_pin), 'dex': pin_row(artifact_pin), 'entry': NAME_LOG_ENTRY,
                  'sourceDexSha256': NAME_LOG_ORIGINAL_SHA, 'method': method}


def verify_leaf(original, label, data, dex):
    recomposed, edits = combine_dex(original, [(label, data)], dex)
    require(recomposed == data and len({edit['methodId'] for edit in edits}) == 1,
            'Expected exact one-method leaf over the original DEX: ' + label)
    return edits


def compose(name_log_dex_pin, *, name_log_receipt_pin):
    """Read exact pins and return the fresh, offline-only composition receipt path."""
    require(digest(COMPOSER) == COMPOSER_SHA, 'Reviewed composition helper differs')
    producer_sha = digest(Path(__file__))
    io = load_io()
    dex = utility()
    name_log_dex_pin = out_pin(name_log_dex_pin)
    name_log_receipt_pin = out_pin(name_log_receipt_pin)
    rpmb, rpmb_conditions, rpmb_pin = historical_leaf(io, RPMB, 'classes13.dex')
    retrieval, retrieval_conditions, retrieval_pin = historical_leaf(io, RETRIEVAL, 'classes2.dex')
    name_log, name_pin = name_log_leaf(io, name_log_receipt_pin, name_log_dex_pin)
    require(SOURCE.resolve(strict=True) == SOURCE and SOURCE.stat().st_size == SOURCE_BYTES
            and digest(SOURCE) == SOURCE_SHA, 'Exact original Settings donor differs')
    infos, original = load_archive(SOURCE, MAX_ENTRY_BYTES)
    require(len(infos) == 10549 and {name for name in original if re.fullmatch(r'classes(?:\d+)?\.dex', name)} == DEX_NAMES,
            'Original Settings entry scope differs')
    count = sum(dex.header(original[entry])['classes'] for entry in DEX_NAMES)
    require(count == 78960, 'Original Settings class count differs')
    components = {'rpmb': (rpmb, rpmb_pin), 'retrieval': (retrieval, retrieval_pin), 'nameLog': (name_log, name_pin)}
    proofs = {}
    for label, (data, pin) in components.items():
        member = original[pin['entry']]
        require(sha(member) == pin['sourceDexSha256'], 'Original member differs: ' + label)
        proofs[label] = verify_leaf(member, label, data, dex)
    require(sha(original[NAME_LOG_ENTRY][NAME_LOG_FIRST_BYTE:NAME_LOG_END_BYTE]) == NAME_LOG_SLICE_SHA
            and all(edit['methodId'] == NAME_LOG_METHOD_ID
                    and NAME_LOG_FIRST_BYTE <= edit['firstByte'] < edit['endExclusiveByte'] <= NAME_LOG_END_BYTE
                    for edit in proofs['nameLog']), 'Name-log bytes leave their exact original interval')

    combined_two, shared_edits = combine_dex(original['classes2.dex'], [('retrieval', retrieval), ('nameLog', name_log)], dex)
    require(shared_edits == proofs['retrieval'] + proofs['nameLog'], 'Combined classes2 edits differ from the verified leaves')
    output = original | {'classes2.dex': combined_two, 'classes13.dex': rpmb}
    changed = {entry for entry, data in output.items() if data != original[entry]}
    require(changed == {'classes2.dex', 'classes13.dex'}
            and all(dex.header(output[entry])['classes'] == dex.header(original[entry])['classes'] for entry in changed),
            'Unexpected changed payload or definition count')

    io['checked_path'](OUT.parent, directory=True)
    OUT.mkdir(exist_ok=True)
    io['checked_path'](OUT, directory=True)
    run = OUT / ('r-' + uuid.uuid4().hex[:8])
    run.mkdir()
    wrapper = run / 'Settings.unselected-code.zip'
    with zipfile.ZipFile(wrapper, 'x') as archive:
        for info in infos:
            archive.writestr(copy.copy(info), output[info.filename])
    observed_infos, observed = load_archive(wrapper, MAX_ENTRY_BYTES)
    require([row.filename for row in observed_infos] == [row.filename for row in infos] and observed == output,
            'Final ZIP payloads or ordering differ')
    require(digest(SOURCE) == SOURCE_SHA and digest(COMPOSER) == COMPOSER_SHA and digest(UTILITY) == UTILITY_SHA
            and digest(Path(__file__)) == producer_sha, 'Donor or composition tool changed')
    for _, (_, pin) in components.items():
        for role in ('receipt', 'dex'):
            row = pin[role]
            require(digest(ROOT / row['path']) == row['sha256'], 'Input changed during composition')

    changes = {entry: {'sourceSha256': sha(original[entry]), 'outputSha256': sha(output[entry]), 'bytes': len(output[entry])}
               for entry in sorted(changed)}
    report = {
        'schema': 'oneos-coloros-settings-fingerprint-name-log-composition/v1',
        'status': 'UNSELECTED_PC_ONLY_COLD_SETTINGS_CODE_COMPOSITION',
        'sourceArchive': {'path': SOURCE_NAME, 'bytes': SOURCE_BYTES, 'sha256': SOURCE_SHA},
        'components': {label: pin for label, (_, pin) in components.items()},
        'archive': {'path': wrapper.relative_to(ROOT).as_posix(), 'bytes': wrapper.stat().st_size, 'sha256': digest(wrapper)},
        'originalClasses': count, 'entryCount': len(infos), 'unchangedExpandedPayloads': len(infos) - len(changed),
        'changedMembers': changes, 'changedInstructionByteSpans': proofs,
        'sameBaseInverseAndRoundtrip': True, 'expandedPayloadsAndOrderVerified': True,
        'requiredSelectionConditions': sorted(set(rpmb_conditions + retrieval_conditions + [
            'Apply only in a fresh Settings process before affected callbacks, jobs or credential owners exist',
            'Require the independent name-log method proof and actual Settings enrollment authority admission',
        ])),
        'coldStartOnly': True, 'selected': False, 'signed': False, 'installed': False,
        'androidExecuted': False, 'deviceAction': False,
        'limits': ['Expanded entry payloads are verified. Physical ZIP encoding and APK signatures are not preserved.'],
        'composerSha256': COMPOSER_SHA, 'utilitySha256': UTILITY_SHA, 'producerSha256': producer_sha,
    }
    receipt = run / 'receipt.json'
    write_exclusive(receipt, (json.dumps(report, indent=2) + '\n').encode('utf-8'))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name-log-dex', required=True)
    parser.add_argument('--name-log-sha256', required=True)
    parser.add_argument('--name-log-receipt', required=True)
    parser.add_argument('--name-log-receipt-sha256', required=True)
    args = parser.parse_args()
    receipt = compose((args.name_log_dex, args.name_log_sha256),
                      name_log_receipt_pin=(args.name_log_receipt, args.name_log_receipt_sha256))
    print(json.dumps({'receipt': receipt.relative_to(ROOT).as_posix(), 'sha256': digest(receipt)}))


if __name__ == '__main__':
    main()
