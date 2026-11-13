"""Assemble an unselected Settings code ZIP with the passive display split."""

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
    DEX_NAMES, MAX_DEX_BYTES, MAX_ENTRY_BYTES, ROOT, SOURCE, SOURCE_SHA, digest,
    load_archive, load_io, out_pin, pinned, read_receipt, require, sha, write_exclusive,
)
from compose_coloros_settings_fingerprint_source_access import compose_dex
from run_full_apk_build import dex_defined_classes


SPLIT_RECEIPT = (
    'out/guest-fingerprint-preference-source-access-retarget/r-951960aa/receipt.json',
    'b3740d1e6311a93783ebf14972810d3894f62893fc041a192bc7705695f892bc',
)
COMPOSER = ROOT / 'tools/compose_coloros_settings_fingerprint_source_access.py'
COMPOSER_SHA = '04675a5417606f7a687de2d64e05bcbf6c939f4266cdc491baa1628495678b28'
PREVIOUS_ZIP_SHA = '6cc86084ae39377d827df50f840fa1e70bd634725a2c1589f2ce3ada5772f386'
COMBINED_CLASSES2_SHA = 'cac2701ec069bb0a8436f8e8c4d68c07d075825ea1e73e6b51de29b223b0c948'
ORIGINAL_HELPER = (
    'out/fingerprint-enrollment-preference-feed-binding-build/r-16944ab9/dex/classes.dex',
    'c99ab1eb24bb3abf4e93f7029ad726bf28202c5aa206df191001d52984b9bc19',
)
RECOVERY_HELPER_SHA = '6642aa6e875d5bc0f989066a8e6f4aa2ee0a8b16434d405b60e0d1ce1697113e'
ARTIFACT_DIR = ROOT / 'firmware/settings-fingerprint-display-composition'
RECEIPT_DIR = ROOT / 'out/settings-fingerprint-display-composition'


def compose(previous_receipt_pin, helper_receipt_pin):
    require(digest(COMPOSER) == COMPOSER_SHA, 'Frozen source-access composer differs')
    producer = Path(__file__)
    producer_sha = digest(producer)
    io = load_io()
    previous_receipt = read_receipt(io, out_pin(previous_receipt_pin))
    helper_receipt = read_receipt(io, out_pin(helper_receipt_pin))
    require(previous_receipt['schema'] == 'oneos-coloros-settings-fingerprint-progress-log-composition/v1'
            and previous_receipt['archive']['sha256'] == PREVIOUS_ZIP_SHA
            and all(previous_receipt[key] is False for key in ('selected', 'signed', 'installed', 'androidExecuted')),
            'Expected frozen unsigned Settings code archive')
    require(helper_receipt['schema'] == 'oneos-fingerprint-enrollment-preference-feed-binding-recovery-sdk-build/v1'
            and helper_receipt['status'] ==
            'PASS_UNSELECTED_FINGERPRINT_ENROLLMENT_PREFERENCE_FEED_BINDING_RECOVERY_SDK37_D8_ONLY'
            and all(helper_receipt[key] is False for key in (
                'selected', 'deviceEligible', 'androidOrOemRuntimeExecuted'))
            and helper_receipt['feedBindingPublicProtectedClassApiUnchanged'] is True
            and len(helper_receipt['capturePublicProtectedDexMethodsUnchanged']) == 10,
            'Expected SDK-verified passive recovery helper with preserved ABI')
    helper = helper_receipt['dex']
    require(helper['sha256'] == RECOVERY_HELPER_SHA, 'Exact reviewed recovery helper required')
    helper_bytes = pinned(io, *out_pin((helper['path'], helper['sha256'])), MAX_DEX_BYTES)
    original_helper = pinned(io, *ORIGINAL_HELPER, MAX_DEX_BYTES)
    helper_defs = dex_defined_classes(helper_bytes)
    require(len(helper_bytes) == helper['bytes'] and len(helper_defs) == 27
            and helper_defs == dex_defined_classes(original_helper),
            'Passive helper extent or exact class set differs')

    split = read_receipt(io, SPLIT_RECEIPT)
    structural = pinned(io, split['output'], split['outputSha256'], MAX_DEX_BYTES)
    require(digest(SOURCE) == SOURCE_SHA, 'Original donor Settings differs')
    with zipfile.ZipFile(SOURCE) as donor:
        info = donor.getinfo('classes2.dex')
        require(info.file_size == 5_737_616, 'Original classes2 extent differs')
        original = donor.read(info)
    previous = previous_receipt['archive']
    previous_path = ROOT / previous['path']
    io['checked_path'](previous_path, directory=False)
    require(previous_path.stat().st_size == previous['bytes']
            and digest(previous_path) == PREVIOUS_ZIP_SHA, 'Frozen Settings ZIP differs')
    infos, members = load_archive(previous_path, MAX_ENTRY_BYTES)
    require(len(infos) == 10_549
            and {name for name in members if re.fullmatch(r'classes(?:\d+)?\.dex', name)} == DEX_NAMES,
            'Previous archive DEX inventory differs')
    classes2, proof = compose_dex(original, structural, members['classes2.dex'])
    require(sha(classes2) == COMBINED_CLASSES2_SHA, 'Combined classes2 output differs')
    output = members | {'classes2.dex': classes2, 'classes15.dex': helper_bytes}
    classes = set()
    for name in sorted(DEX_NAMES):
        definitions = dex_defined_classes(output[name])
        require(not classes & definitions, 'Duplicate definition across donor members')
        classes.update(definitions)
    require(len(classes) == 78_960 and not classes & helper_defs
            and dex_defined_classes(original) == dex_defined_classes(classes2),
            'Donor or helper class identities differ')

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
        archive.writestr('classes15.dex', helper_bytes)
    observed_infos, observed = load_archive(wrapper, MAX_ENTRY_BYTES)
    require([info.filename for info in observed_infos] == [info.filename for info in infos] + ['classes15.dex']
            and observed == output, 'Saved Settings code ZIP differs')
    require(digest(SOURCE) == SOURCE_SHA and digest(previous_path) == PREVIOUS_ZIP_SHA
            and digest(COMPOSER) == COMPOSER_SHA and digest(producer) == producer_sha
            and digest(ROOT / helper['path']) == helper['sha256']
            and digest(ROOT / helper_receipt_pin[0]) == helper_receipt_pin[1]
            and digest(ROOT / previous_receipt_pin[0]) == previous_receipt_pin[1],
            'Selected input changed while composing')
    receipt = RECEIPT_DIR / run_id / 'receipt.json'
    report = {
        'schema': 'oneos-coloros-settings-fingerprint-display-composition/v1',
        'producerSha256': producer_sha,
        'previousReceipt': dict(zip(('path', 'sha256'), previous_receipt_pin)),
        'sourceAccessReceipt': dict(zip(('path', 'sha256'), SPLIT_RECEIPT)),
        'helperReceipt': dict(zip(('path', 'sha256'), helper_receipt_pin)),
        'archive': {'path': wrapper.relative_to(ROOT).as_posix(), 'sha256': digest(wrapper),
                    'bytes': wrapper.stat().st_size},
        'entryCount': len(observed_infos), 'changedPredecessorMembers': ['classes2.dex'],
        'addedMember': 'classes15.dex', 'classes2Proof': proof,
        'donorDefinitions': len(classes), 'helperDefinitions': len(helper_defs),
        'requiredSelectionConditions': previous_receipt['requiredSelectionConditions'] + [
            'Require compatible Settings package and shared UID signing, loading and fresh-process evidence',
            'Bind a genuine same-runtime-package caller, current view and admitted report source before presentation',
        ],
        'selected': False, 'signed': False, 'installed': False, 'androidExecuted': False,
        'coldStartOnly': True, 'deviceAction': False,
    }
    write_exclusive(receipt, (json.dumps(report, indent=2) + '\n').encode())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-receipt', required=True)
    parser.add_argument('--previous-receipt-sha256', required=True)
    parser.add_argument('--helper-receipt', required=True)
    parser.add_argument('--helper-receipt-sha256', required=True)
    args = parser.parse_args()
    result = compose((args.previous_receipt, args.previous_receipt_sha256),
                     (args.helper_receipt, args.helper_receipt_sha256))
    print(result.relative_to(ROOT).as_posix(), digest(result))
