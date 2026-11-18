"""Recheck the exact PC artifacts referenced by the fresh-stage review."""

import argparse
import json
import os
import struct

from check_file_stage_device_preflight import PROFILE, drop_artifacts, readiness_artifacts, require
from guest_tree_protected_drop_transfer import publisher_pin
from run_guest_tree_install_transport import (
    FEED, FEED_SHA, carrier_installer_pin, installer_build_status, load_io, pinned, selected_source_receipt,
)
import stream_guest_tree_install_feed as feed


CONTROLLER_RECEIPT = ('out/tree-retained-controller/r-b40000a8/receipt.json',
                      '22865cbd53a654d217e93db31eff650e0bacc1a94f8681ceee817e1c3ee05e2d')
V2_CONTROLLER_RECEIPT = ('out/tree-retained-controller-static-exec/r-20b2ea21/readback-receipt.json',
                         '0b5fd9f057020f14309b4e10013f4ef6109ac737d634a040517025d1df68697a')
V1_PAIR_RECEIPT = ('out/file-stage-readiness-package/r-6c688c4ff1/receipt.json',
                   '63892c552dee93bc017731ddd4aec8b0c51b7809bb472d54f6faaafc1bdecabb')
V2_PAIR_RECEIPT = ('out/file-stage-static-exec-repair/app/r-f6d89caa/pair-receipt.json',
                   '620c2acc1f9a1c8e1f75988d9b45f51ae13b79ce19863d597f960bec768a2b2d')
PAIR_STATUS = 'PASS_PC_MATCHED_READINESS_APKS_AND_PROFILE_ONLY'
PROFILE_SLOT = {'path': PROFILE, 'mode': '0440', 'uid': 0, 'gid': 1000, 'links': 1}


def pair_receipt_pin(carrier_protocol='v1'):
    carrier_installer_pin(carrier_protocol)
    return V2_PAIR_RECEIPT if carrier_protocol == 'v2' else V1_PAIR_RECEIPT


def require_static_exec(data):
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    require(header[0][:7] == b'\x7fELF\x02\x01\x01' and header[1:3] == (2, 183)
            and header[9] == 56 and 0 < header[10] <= 64
            and header[11] == 64 and 0 < header[12] <= 256,
            'Expected an AArch64 ELF64 executable')
    segments = [struct.unpack_from('<IIQQQQQQ', data, header[5] + i * header[9])
                for i in range(header[10])]
    require(all(seg[0] not in (2, 3) for seg in segments)
            and any(seg[0] == 1 and seg[1] & 1 and seg[3] <= header[4] < seg[3] + seg[5]
                    for seg in segments)
            and all(struct.unpack_from('<I', data, header[6] + i * header[11] + 4)[0]
                    not in (4, 6, 9, 19) for i in range(header[12])),
            'Unexpected interpreter, dynamic metadata, relocation or entry point')


def verify_local_cohort(*, carrier_protocol='v1'):
    installer_pin = carrier_installer_pin(carrier_protocol)
    v2 = carrier_protocol == 'v2'
    package_pins, readiness_pins = readiness_artifacts(carrier_protocol)
    drop_pins = drop_artifacts(carrier_protocol)
    publisher_path, publisher_receipt, publisher_sha, publisher_status = publisher_pin(carrier_protocol)
    io = load_io()

    def record(path, digest, status, *, maximum=64 * 1024):
        raw = pinned(io, path, digest, maximum)
        result = json.loads(raw.decode('ascii'), object_pairs_hook=io['unique_object'])
        require(result['status'] == status and result['deviceEligible'] is False,
                'Unexpected saved cohort receipt')
        return result

    def artifact(pin, maximum, expected_size=None, expected_sha=None):
        size, digest = pin['bytes'], pin['sha256']
        require(type(size) is int and 0 < size <= maximum and (expected_size is None or size == expected_size)
                and (expected_sha is None or digest == expected_sha), 'Unexpected local cohort artifact')
        data = pinned(io, pin['path'], digest, size)
        require(len(data) == size, 'Incomplete local cohort artifact')
        return data

    def executable(receipt, path, size, digest):
        pin = receipt['artifact']
        require(pin['path'] == path and receipt['targetExecuted'] is False, 'Unexpected executable receipt')
        return artifact(pin, 2 * 1024**2, size, digest)

    installer = record(installer_pin.receipt_path, installer_pin.receipt_sha256,
                       installer_build_status(carrier_protocol))
    publisher = record(publisher_receipt, publisher_sha, publisher_status,
                       maximum=(72 if v2 else 64) * 1024)
    pair_path, pair_sha = pair_receipt_pin(carrier_protocol)
    if v2:
        controller_path, controller_sha = V2_CONTROLLER_RECEIPT
        controller_proof = record(controller_path, controller_sha,
                                  'PASS_FILE_BACKED_PREPARE_STOP_STATIC_EXEC_LINK_ONLY')
    else:
        require(publisher['pairReceipt'] == {'path': pair_path, 'sha256': pair_sha},
                'Publisher pair receipt differs')
        controller_proof = record(*CONTROLLER_RECEIPT, 'PASS_FILE_BACKED_PREPARE_STOP_STATIC_LINK_ONLY')
    pair = record(pair_path, pair_sha, PAIR_STATUS)
    controller = controller_proof['executable']
    require(pair['controller'] == controller and installer['controller'] == {
        key: controller[key] for key in ('bytes', 'sha256')}, 'Controller pins disagree')
    controller_bytes = artifact(controller, 1024**2, 724152 if v2 else 746760)
    installer_bytes = executable(installer, installer_pin.artifact_path,
                                 installer_pin.artifact_bytes, installer_pin.artifact_sha256)
    require(installer_bytes.count(controller_bytes) == 1, 'Installer does not embed this controller exactly once')
    if v2:
        require(all(item['selected'] is False and item['targetExecuted'] is False
                    for item in (pair, publisher, installer, controller_proof))
                and pair['hostReusedByteForByte'] is True
                and publisher['hostReusedByteForByte'] is True
                and publisher['controllerProof'] == pair['controllerProof']
                == {'path': controller_path, 'sha256': controller_sha}
                and publisher['controller'] == controller and publisher['packages'] == pair['packages']
                and drop_pins['deploy_installer'][1:] == (installer_pin.artifact_bytes,
                                                          installer_pin.artifact_sha256),
                'V2 build receipts or installer transfer pin disagree')
        require_static_exec(controller_bytes)
        require_static_exec(installer_bytes)

    packages = {}
    for side, role in (('app', 'tester'), ('host', 'host')):
        package = pair['packages'][side]
        name, size, _ = package_pins[role]
        require(package['package'] == name and type(package['versionCode']) is int and package['versionCode'] == 1,
                'Unexpected local package identity')
        artifact(package['apk'], 256 * 1024, size, readiness_pins[role])
        artifact(package['publicCertificate'], 16384)
        packages[role] = {'package': name, 'apkSha256': package['apk']['sha256'],
                          'certificateSha256': package['publicCertificate']['sha256']}

    profile = pair['profile']
    if v2:
        require(profile == publisher['profile'] and profile['targetSlot'] == PROFILE_SLOT,
                'V2 profile publisher and package pins disagree')
    else:
        require(profile['payload'] == publisher['profile'] and profile['targetSlot'] == publisher['profileTarget']
                == PROFILE_SLOT, 'Profile publisher and package pins disagree')
    profile_bytes = artifact(profile['payload'], 288, 288, readiness_pins['profile'])
    tester = pair['packages']['app']
    fields = {'version': '2', 'package': tester['package'], 'signer': tester['publicCertificate']['sha256'],
              'apk': tester['apk']['sha256'], 'code': str(tester['versionCode']),
              'native': controller['sha256'], 'bytes': str(controller['bytes'])}
    expected_profile = ''.join(f'{name}={value}\n' for name, value in fields.items()).encode('ascii')
    publisher_bytes = executable(publisher, publisher_path, *drop_pins['deploy_publisher'][1:])
    require(profile['fields'] == fields and profile_bytes == expected_profile
            and publisher_bytes.count(profile_bytes) == 1, 'Profile bytes do not bind the exact tester and controller')
    if v2:
        require_static_exec(publisher_bytes)
        embedded = publisher['embeddedProfile']
        offset = embedded['offset']
        require(embedded['sha256'] == profile['payload']['sha256'] and embedded['bytes'] == len(profile_bytes)
                and type(offset) is int and offset >= 0
                and publisher_bytes[offset:offset + len(profile_bytes)] == profile_bytes,
                'V2 publisher profile readback differs')

    pinned(io, FEED, FEED_SHA, 64 * 1024)
    source = json.loads(selected_source_receipt())
    expected_carrier = {'imageBytes': source['imageBytes'], 'imageSha256': source['imageSha256'],
                        'fsVerityDigest': source['fsVerityDigest']}
    require(installer['carrier'] == expected_carrier and all(controller[k] == v for k, v in expected_carrier.items()),
            'Carrier and descriptor pins disagree')
    if v2:
        carrier_pin = (expected_carrier['imageBytes'].to_bytes(8, 'little')
                       + bytes.fromhex(expected_carrier['imageSha256'] + expected_carrier['fsVerityDigest']))
        controller_pin = (expected_carrier['imageBytes'].to_bytes(8, 'little')
                          + bytes.fromhex(expected_carrier['fsVerityDigest']))
        require(installer['commands']['link']['stdoutSha256'] == installer_pin.artifact_sha256
                and installer_bytes.count(carrier_pin) == 1
                and controller_bytes.count(controller_pin) == 1
                and all(installer_bytes.count(marker + b'\0') == 1 for marker in (
                    b'--bootstrap-empty-stage-with-witness', b'ONEOS_STAGE_V2',
                    b'--install-preparation-controller-with-bound-stage',
                    b'--install-verified-carrier-with-witness', b'--observe-published-carrier',
                    b'ONEOS_CARRIER_V2', b'ONEOS_CARRIER_READBACK_V1')),
                'V2 linked installer profile differs')
    image_path, identity = feed.authenticate_profile(io)
    require(image_path == io['ROOT'] / source['image'], 'Carrier path differs')
    with io['checked_input'](image_path, size=source['imageBytes']) as stream:
        require(feed.identity(io['checked_path'](image_path)) == identity
                and feed.identity(os.fstat(stream.fileno()))[:4] == identity[:4],
                'Carrier identity differs from its raw readback')

    result = {'status': 'MATCHED_LOCAL_COHORT_VERIFIED', 'mayExecute': False,
            'pairReceiptSha256': pair_sha, 'profileSha256': readiness_pins['profile'],
            'installerSha256': installer_pin.artifact_sha256, 'publisherSha256': drop_pins['deploy_publisher'][2],
            'controllerSha256': controller['sha256'], 'carrier': expected_carrier, 'packages': packages,
            'carrierWholeFileRehashRequiredDuringTransfer': True}
    if v2:
        result['installerProtocol'] = carrier_protocol
        result['installerBuildReceiptSha256'] = installer_pin.receipt_sha256
        result['installerPath'] = installer_pin.artifact_path
        result['installerBytes'] = installer_pin.artifact_bytes
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--carrier-protocol', choices=('v1', 'v2'), default='v1')
    args = parser.parse_args()
    print(json.dumps(verify_local_cohort(carrier_protocol=args.carrier_protocol), indent=2))
