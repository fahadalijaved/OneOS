"""Extend the frozen, unsigned Settings code archive with the progress log cut."""

import argparse
import copy
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

from compose_coloros_settings_fingerprint_name_log import (
    COMPOSER, COMPOSER_SHA, MAX_DEX_BYTES, MAX_ENTRY_BYTES, ROOT, RPMB, SOURCE, SOURCE_SHA,
    combine_dex, digest, historical_leaf, load_archive, load_io, out_pin,
    pinned, read_receipt, require, sha, utility, write_exclusive,
)


PREVIOUS = (
    'out/settings-fingerprint-name-log-composition/r-9db92f49/receipt.json',
    '5e054c7776c68a21a367d8331dbd5e8aafb981c46ff1c81fa2794e3a7e159db9',
)
ENTRY = 'classes13.dex'
SOURCE_DEX_SHA = 'a706e235bfe59e04b5febe2dc96a1aae2a8e8eac517c7585cdd22ae8b180e6ac'
PROGRESS_DEX_SHA = 'f4217ab60578cbba4bc395da92af3b24c83b3d0bed655515d3821044727b9047'
COMBINED_DEX_SHA = 'bf20adf0ae4538d6e6e19008b5307115fb1abc1d222cdb5510c318940b30c5ec'
PROGRESS_METHOD_ID = 26464
PROGRESS_SPANS = ((3126804, 3126840), (3126844, 3126850))
ARTIFACT_DIR = ROOT / 'firmware/settings-fingerprint-progress-log-composition'
RECEIPT_DIR = ROOT / 'out/settings-fingerprint-progress-log-composition'


def compose(receipt_pin):
    producer = Path(__file__)
    producer_sha = digest(producer)
    require(digest(COMPOSER) == COMPOSER_SHA, 'Frozen DEX composer differs')
    io = load_io()
    dex = utility()
    predecessor = read_receipt(io, PREVIOUS)
    leaf = read_receipt(io, out_pin(receipt_pin))
    require(leaf['schema'] == 'oneos-coloros-settings-fingerprint-progress-log-leaf/v1'
            and leaf['status'] == 'PASS_EXACT_UNSELECTED_SETTINGS_FINGERPRINT_PROGRESS_LOG_LEAF'
            and all(leaf[key] is False for key in ('selected', 'deviceAction', 'targetExecuted'))
            and leaf['method']['inverseExact'] is True and leaf['method']['roundtripExact'] is True,
            'Expected an unselected, inverse-checked progress diagnostic leaf')
    emitted = leaf['outputDex']
    require(leaf['sourceArchive'] == predecessor['sourceArchive']
            and leaf['sourceDex'] == {'entry': ENTRY, 'bytes': 11_447_552, 'sha256': SOURCE_DEX_SHA}
            and emitted['sha256'] == PROGRESS_DEX_SHA
            and re.fullmatch(r'firmware/settings-fingerprint-progress-log-leaf/r-[0-9a-f]{8}/classes13\.dex',
                             emitted['path']) is not None,
            'Progress leaf does not match the original Settings and exact reviewed output')
    progress = pinned(io, emitted['path'], PROGRESS_DEX_SHA, MAX_DEX_BYTES)
    require(len(progress) == emitted['bytes'], 'Progress output extent differs')
    rpmb, _, rpmb_pin = historical_leaf(io, RPMB, ENTRY)
    previous_archive = predecessor['archive']
    previous_path = ROOT / previous_archive['path']
    io['checked_path'](previous_path, directory=False)
    require(previous_path.stat().st_size == previous_archive['bytes']
            and digest(previous_path) == previous_archive['sha256'], 'Frozen Settings ZIP differs')
    require(SOURCE.resolve(strict=True) == SOURCE and digest(SOURCE) == SOURCE_SHA,
            'Immutable donor Settings differs')
    with zipfile.ZipFile(SOURCE) as donor:
        member = donor.getinfo(ENTRY)
        require(member.file_size == leaf['sourceDex']['bytes'], 'Original DEX extent differs')
        original = donor.read(member)
    require(sha(original) == SOURCE_DEX_SHA, 'Original classes13 digest differs')
    infos, previous = load_archive(previous_path, MAX_ENTRY_BYTES)
    require(len(infos) == predecessor['entryCount'] and previous[ENTRY] == rpmb,
            'Previous archive does not contain the exact RPMB member')
    combined, edits = combine_dex(original, [('rpmb', rpmb), ('progressLog', progress)], dex)
    require(sha(combined) == COMBINED_DEX_SHA, 'Combined classes13 differs from independent replay')
    progress_edits = [edit for edit in edits if edit['component'] == 'progressLog']
    require(progress_edits and all(
        edit['methodId'] == PROGRESS_METHOD_ID and any(
            first <= edit['firstByte'] < edit['endExclusiveByte'] <= end
            for first, end in PROGRESS_SPANS)
        for edit in progress_edits), 'Progress edit leaves its reviewed instruction spans')
    require(all(combined[first:end] == bytes(end - first) for first, end in PROGRESS_SPANS),
            'Combined DEX does not retain the complete progress cut')
    output = previous | {ENTRY: combined}
    require(combined != previous[ENTRY], 'Successor must change classes13')

    run_id = 'r-' + uuid.uuid4().hex[:8]
    for base in (ARTIFACT_DIR, RECEIPT_DIR):
        io['checked_path'](base.parent, directory=True)
        base.mkdir(exist_ok=True)
        io['checked_path'](base, directory=True)
        (base / run_id).mkdir()
    wrapper = ARTIFACT_DIR / run_id / 'Settings.unselected-code.zip'
    with zipfile.ZipFile(wrapper, 'x') as archive:
        for info in infos:
            archive.writestr(copy.copy(info), output[info.filename])
    observed_infos, observed = load_archive(wrapper, MAX_ENTRY_BYTES)
    require([info.filename for info in observed_infos] == [info.filename for info in infos]
            and observed == output, 'Successor ZIP payloads or order differ')
    require(digest(SOURCE) == SOURCE_SHA and digest(previous_path) == previous_archive['sha256']
            and digest(producer) == producer_sha and digest(COMPOSER) == COMPOSER_SHA
            and digest(ROOT / receipt_pin[0]) == receipt_pin[1]
            and digest(ROOT / emitted['path']) == PROGRESS_DEX_SHA
            and digest(ROOT / rpmb_pin['dex']['path']) == rpmb_pin['dex']['sha256'],
            'Selected input changed during composition')
    receipt = RECEIPT_DIR / run_id / 'receipt.json'
    report = {
        'schema': 'oneos-coloros-settings-fingerprint-progress-log-composition/v1',
        'producerSha256': producer_sha,
        'predecessorReceipt': dict(zip(('path', 'sha256'), PREVIOUS)),
        'progressLeafReceipt': dict(zip(('path', 'sha256'), receipt_pin)),
        'archive': {'path': wrapper.relative_to(ROOT).as_posix(), 'sha256': digest(wrapper),
                    'bytes': wrapper.stat().st_size},
        'entryCount': len(infos), 'unchangedExpandedPayloadsFromPredecessor': len(infos) - 1,
        'classes13': {'sourceSha256': SOURCE_DEX_SHA, 'combinedSha256': sha(combined),
                      'bytes': len(combined), 'sameBaseInverseAndRoundtrip': True, 'edits': edits},
        'requiredSelectionConditions': predecessor['requiredSelectionConditions'],
        'selected': False, 'signed': False, 'installed': False, 'androidExecuted': False,
        'coldStartOnly': True, 'deviceAction': False,
    }
    write_exclusive(receipt, (json.dumps(report, indent=2) + '\n').encode())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--progress-receipt', required=True)
    parser.add_argument('--progress-receipt-sha256', required=True)
    args = parser.parse_args()
    result = compose((args.progress_receipt, args.progress_receipt_sha256))
    print(result.relative_to(ROOT).as_posix(), digest(result))
