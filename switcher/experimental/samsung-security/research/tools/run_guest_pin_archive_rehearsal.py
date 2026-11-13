"""Rehearse the verified dormant split in memory and save only its evidence."""

import argparse
import io
import json
from uuid import uuid4
import zipfile

from check_guest_pin_rehearsal_zip import verify
from check_guest_pin_split_archive import (
    ADDITION, APK, APK_SHA, APK_SIZE, REPLACEMENT, ROOT, digest, held, owned, require,
    root_dex_entries, stored_dex_offset, stored_payload_offset,
)
from compose_guest_pin_rehearsal_zip import compose


PREFLIGHT = ('out/guest-pin-split-archive/r-3902f737/receipt.json',
             '9841cc147b93271d362f13d70a739a549b34623d1fc8324a1acf729d4e51e75d')
SIGNATURE = ('out/guest-pin-donor-signature/r-946d4d85/receipt.json',
             '243298d66f8111930007d96d1c2ee9c81f867b7dc435c12d4d3e384a9f118432')
TOOLS = ('run_guest_pin_archive_rehearsal.py', 'read_guest_pin_rehearsal_zip.py',
         'compose_guest_pin_rehearsal_zip.py', 'check_guest_pin_rehearsal_zip.py',
         'check_guest_pin_split_archive.py')


def expanded_readback(candidate, preflight, replacement, addition):
    with zipfile.ZipFile(io.BytesIO(candidate)) as archive:
        require(len(archive.infolist()) == preflight['donor']['zipEntries'] + 1,
                'Candidate entry count differs')
        dex_members = root_dex_entries(archive, 10)
        offsets = {entry.filename: stored_dex_offset(archive, entry) for entry in dex_members}
        require(archive.read('classes3.dex') == replacement and archive.read('classes10.dex') == addition,
                'Expanded split payload differs')
        for row in preflight['donor']['dexMembers']:
            name = row['member']
            if name != 'classes3.dex':
                require(digest(archive.read(name)) == row['sha256'], 'Unexpected donor DEX change: ' + name)
        for name, row in preflight['donor']['namedPayloads'].items():
            require(digest(archive.read(name)) == row['sha256'], 'Unexpected donor payload change: ' + name)
        resources_offset = stored_payload_offset(archive, archive.getinfo('resources.arsc'), 4)
        native_offsets = {
            entry.filename: stored_payload_offset(archive, entry, 16 * 1024)
            for entry in archive.infolist()
            if entry.filename.startswith('lib/arm64-v8a/') and entry.filename.endswith('.so')
        }
        require(len(native_offsets) == preflight['donor']['storedArm64Libraries'], 'Native inventory differs')
        require(archive.testzip() is None, 'Expanded candidate ZIP integrity differs')
    return {'dexDataOffsets': offsets, 'resourcesDataOffset': resources_offset,
            'arm64DataOffsets': native_offsets, 'allExpandedMemberCrcsPassed': True}


def rehearse():
    source_pins = {name: digest((ROOT / 'tools' / name).read_bytes()) for name in TOOLS}
    preflight = json.loads(held(PREFLIGHT, 256 * 1024))
    signature = json.loads(held(SIGNATURE, 256 * 1024))
    require(preflight['status'] == 'PASS_PLANNED_SPLIT_ARCHIVE_LAYOUT_ONLY'
            and preflight['selected'] is False and preflight['deviceEligible'] is False
            and preflight['donor']['bytes'] == APK_SIZE and preflight['donor']['sha256'] == APK_SHA
            and preflight['proposed']['replace']['sha256'] == REPLACEMENT[1]
            and preflight['proposed']['add']['sha256'] == ADDITION[1], 'Held archive preflight differs')
    signer = signature['embeddedCertificateSha256']
    require(signature['status'] == 'PASS_EXACT_HELD_DONOR_SYSTEMUI_V2_V3_SIGNATURE'
            and signature['verificationOnly'] is True and signature['signedByAudit'] is False
            and signature['inputs'][str(APK)]['sha256'] == APK_SHA
            and all(signature['commands'][scheme]['verified'] is True
                    and signature['commands'][scheme]['verifiedCertificateSha256'] == signer
                    for scheme in ('v2', 'v3')), 'Held donor signature proof differs')
    with APK.open('rb') as stream:
        donor = stream.read(APK_SIZE + 1)
    require(len(donor) == APK_SIZE and digest(donor) == APK_SHA, 'Held donor APK differs')
    replacement = held(REPLACEMENT, 16 * 1024 * 1024)
    addition = held(ADDITION, 64 * 1024)
    candidate = compose(donor, replacement, addition)
    raw_proof = verify(donor, candidate, replacement, addition)
    expanded = expanded_readback(candidate, preflight, replacement, addition)
    require(all(digest((ROOT / 'tools' / name).read_bytes()) == pin for name, pin in source_pins.items()),
            'Rehearsal tooling changed during readback')
    return {'schema': 'oneos-guest-pin-archive-rehearsal/v1',
            'status': 'PASS_IN_MEMORY_UNSIGNED_SPLIT_ZIP_ONLY',
            'inputs': dict((PREFLIGHT, SIGNATURE, REPLACEMENT, ADDITION)),
            'toolSha256': source_pins,
            'donorSha256': APK_SHA, 'verifiedDonorCertificateSha256': signer,
            'rehearsedZipBytes': len(candidate), 'rehearsedZipSha256': digest(candidate),
            'plannedDefinitions': preflight['proposed']['definitions'],
            'rawReadback': raw_proof, 'expandedReadback': expanded,
            'archivePersisted': False, 'signed': False, 'selected': False,
            'loaded': False, 'deviceEligible': False, 'targetExecuted': False}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = rehearse()
    base = ROOT / 'out/guest-pin-archive-rehearsal'
    run = owned(base / ('r-' + uuid4().hex[:8]), base)
    run.mkdir(parents=True)
    receipt = run / 'receipt.json'
    with receipt.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(f"{result['status']} {receipt}")


if __name__ == '__main__':
    main()
