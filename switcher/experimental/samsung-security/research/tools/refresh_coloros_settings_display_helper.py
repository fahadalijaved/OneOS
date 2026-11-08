"""Replace the exact passive helper in the held Settings code ZIP and align it."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
import zipfile

sys.dont_write_bytecode = True

from compose_coloros_settings_fingerprint_name_log import (
    MAX_DEX_BYTES, ROOT, digest, load_io, out_pin, pinned, read_receipt, require, write_exclusive,
)
from run_full_apk_build import dex_defined_classes
from verify_guest_settings_apk import (
    MANIFEST_SHA, MAX_ARCHIVE, ZIPALIGN, archive_info, check_zip_end, run_checked, stream_sha, verify_tools,
)


BASE = ROOT / 'firmware/settings-fingerprint-display-composition/r-7edf896b/Settings.unselected-code.zip'
BASE_SHA = 'a4e630f5a8269822ce9b4330f0a8b621755e10a845c963f3683885441a5de3ec'
PREDECESSOR_BUILD = {
    'path': 'out/fingerprint-enrollment-preference-feed-binding-recovery-build/r-2be64797/receipt.json',
    'sha256': '9f90a31a10f8512494d6c471d0533d6386361f06d2d9fa5535fb0da35d6deb02',
}
BASE_HELPER_SHA = '6642aa6e875d5bc0f989066a8e6f4aa2ee0a8b16434d405b60e0d1ce1697113e'
HELPER_SHA = 'eac50f52c5d2d252dda4b3cf2f9dfe07a0b7a5a25b404f7639c48aab42bf2c7c'
ENTRY = 'classes15.dex'
COUNT = 10_550
CHUNK = 1024 * 1024
ARTIFACTS = ROOT / 'firmware/settings-fingerprint-display-retirement'
EVIDENCE = ROOT / 'out/settings-fingerprint-display-retirement'


def verify_replacement(original, rows, result, helper_bytes):
    check_zip_end(result, COUNT)
    result.seek(-6, os.SEEK_END)
    central = int.from_bytes(result.read(4), 'little')
    require(central >= 16, 'Invalid central-directory location')
    result.seek(central - 16)
    require(result.read(16) != b'APK Sig Block 42', 'Unsigned archive carries an APK signing block')
    with zipfile.ZipFile(result) as output:
        actual = archive_info(output, COUNT)
        require([info.filename for info in actual] == [info.filename for info in rows],
                'Aligned entry names or order differ')
        for old, new in zip(rows, actual):
            require(old.compress_type == new.compress_type, 'Compression method differs')
            if new.filename == ENTRY:
                require(new.file_size == len(helper_bytes) and output.read(new) == helper_bytes,
                        'Final helper DEX differs')
                continue
            require(old.file_size == new.file_size and old.CRC == new.CRC,
                    f'Unexpected member extent or CRC: {old.filename}')
            with original.open(old) as left, output.open(new) as right:
                while True:
                    block = left.read(CHUNK)
                    require(right.read(CHUNK) == block, f'Unexpected member payload: {old.filename}')
                    if not block:
                        break
        require(hashlib.sha256(output.read('AndroidManifest.xml')).hexdigest() == MANIFEST_SHA,
                'Unexpected Settings manifest')


def publish(helper_receipt_pin):
    producer = Path(__file__)
    producer_sha = digest(producer)
    io = load_io()
    checked = io['checked_input']
    helper_receipt = read_receipt(io, out_pin(helper_receipt_pin))
    require(helper_receipt['schema'] == 'oneos-fingerprint-enrollment-preference-section-sdk-build/v1'
            and helper_receipt['status'] ==
            'PASS_UNSELECTED_FINGERPRINT_ENROLLMENT_PREFERENCE_SECTION_SDK37_D8_ONLY'
            and helper_receipt['predecessorReceipt'] == PREDECESSOR_BUILD
            and helper_receipt['sectionPublicProtectedClassApiUnchanged'] is True
            and len(helper_receipt['capturePublicProtectedDexMethodsUnchanged']) == 10
            and all(helper_receipt[key] is False for key in (
                'selected', 'deviceEligible', 'androidOrOemRuntimeExecuted')),
            'Expected the reviewed offline passive Section build')
    helper = helper_receipt['dex']
    helper_bytes = pinned(io, *out_pin((helper['path'], helper['sha256'])), MAX_DEX_BYTES)
    require(len(helper_bytes) == helper['bytes'] and helper['sha256'] == HELPER_SHA,
            'Exact verified retirement helper required')
    helper_classes = dex_defined_classes(helper_bytes)

    run_id = 'r-' + uuid.uuid4().hex[:8]
    for base in (ARTIFACTS, EVIDENCE):
        io['checked_path'](base.parent, directory=True)
        base.mkdir(exist_ok=True)
        io['checked_path'](base, directory=True)
        (base / run_id).mkdir()
    work = EVIDENCE / run_id
    aligned = ARTIFACTS / run_id / 'Settings.aligned-unsigned.zip'
    verify_tools(checked)
    with tempfile.TemporaryDirectory(dir=ARTIFACTS / run_id) as temp:
        workspace = Path(temp)
        io['checked_path'](workspace, directory=True)
        unaligned = workspace / 'Settings.unsigned.zip'
        with checked(BASE, max_size=MAX_ARCHIVE) as held:
            require(stream_sha(held) == BASE_SHA, 'Held Settings archive differs')
            check_zip_end(held, COUNT)
            with zipfile.ZipFile(held) as original:
                rows = archive_info(original, COUNT)
                old_helper = original.read(ENTRY)
                require(hashlib.sha256(old_helper).hexdigest() == BASE_HELPER_SHA
                        and len(helper_classes) == 27 and helper_classes == dex_defined_classes(old_helper),
                        'Passive helper class inventory differs')
                with zipfile.ZipFile(unaligned, 'x') as output:
                    for info in rows:
                        with output.open(copy.copy(info), 'w') as writer:
                            if info.filename == ENTRY:
                                require(writer.write(helper_bytes) == len(helper_bytes), 'Short helper write')
                            else:
                                with original.open(info) as reader:
                                    shutil.copyfileobj(reader, writer, length=CHUNK)
                run_checked([ZIPALIGN, '-P', '16', '4', unaligned, aligned], work)
                run_checked([ZIPALIGN, '-c', '-P', '16', '4', aligned], work)
                with checked(aligned, max_size=MAX_ARCHIVE) as result:
                    verify_replacement(original, rows, result, helper_bytes)
                    aligned_sha = stream_sha(result)

    verify_tools(checked)
    require(digest(BASE) == BASE_SHA and digest(producer) == producer_sha
            and digest(ROOT / helper_receipt_pin[0]) == helper_receipt_pin[1]
            and digest(ROOT / helper['path']) == helper['sha256'], 'Input changed during publication')
    receipt = work / 'receipt.json'
    record = {
        'schema': 'oneos-coloros-settings-display-retirement-archive/v1',
        'status': 'PASS_UNSELECTED_ALIGNED_UNSIGNED_SETTINGS_ONLY',
        'producerSha256': producer_sha, 'predecessorArchiveSha256': BASE_SHA,
        'predecessorHelperBuild': PREDECESSOR_BUILD,
        'helperBuild': dict(zip(('path', 'sha256'), helper_receipt_pin)),
        'helperSha256': helper['sha256'], 'changedMembers': [ENTRY], 'entryCount': COUNT,
        'helperDefinitions': len(helper_classes), 'manifestSha256': MANIFEST_SHA,
        'unchangedExpandedPayloadsVerified': COUNT - 1,
        'archive': {'path': aligned.relative_to(ROOT).as_posix(), 'sha256': aligned_sha,
                    'bytes': aligned.stat().st_size},
        'zipalign16KiB': True, 'coldStartOnly': True, 'selected': False,
        'deviceEligible': False, 'signed': False, 'installed': False, 'deviceAction': False,
    }
    write_exclusive(receipt, (json.dumps(record, indent=2) + '\n').encode())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper-receipt', required=True)
    parser.add_argument('--helper-receipt-sha256', required=True)
    args = parser.parse_args()
    output = publish((args.helper_receipt, args.helper_receipt_sha256))
    print(output.relative_to(ROOT).as_posix(), digest(output))
