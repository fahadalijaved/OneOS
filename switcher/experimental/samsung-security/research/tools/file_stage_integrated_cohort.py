"""Verify the exact saved integrated tester and host for offline review."""

from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile

from check_file_stage_device_preflight import require
from check_file_stage_local_cohort import PROFILE_SLOT, V2_CONTROLLER_RECEIPT, require_static_exec, verify_local_cohort
from check_guarded_stage_bundle import Dex
from confirmation_tester_cohort import PAIR_PIN as PREDECESSOR_PIN
from run_guest_tree_install_transport import load_io, pinned, sha


RUN = 'out/file-stage-integrated-runtime/app/r-8bd93a75'
BUILD_PIN = (RUN + '/receipt.json', 'b451c8b33c64de07e8b36a006e2535032e7fb6e665ce7f336a98e8fc9cfbc6a7')
PAIR_PIN = (RUN + '/pair-receipt.json', '8e6c234d7785cbb0aa9232f75041f3c6b62baff063f7335a83b49f98696d51ba')
COMPILE_PIN = ('out/file-stage-confirmation-lifecycle-build/r-ff4de804/receipt.json',
               '811bca567e5c606da09247ab0a9362c215ab1b9234080a5a04993d2fd3e70106')
HOST_SIGNING_PIN = ('out/file-stage-early-exit-host-signing/r-70eb7bd5/receipt.json',
                    '553fb421f484cd8055d356056690f5b5a3f652a0de3b1c414b31c6651128ed1d')


def integrated_cohort() -> dict:
    """Return authenticated public metadata for the transcript reviewer."""
    io = load_io()

    def record(pin):
        return json.loads(pinned(io, *pin, 64 * 1024), object_pairs_hook=io['unique_object'])

    def artifact(row, limit):
        size = row['bytes']
        require(type(size) is int and 0 <= size <= limit, 'Integrated artifact exceeds its bound')
        raw = pinned(io, row['path'], row['sha256'], size)
        require(len(raw) == size, 'Integrated artifact length differs')
        return raw

    def stdout(receipt, label, limit, apk=None):
        command = receipt['commands'][label]
        require(type(command['exitCode']) is int and command['exitCode'] == 0
                and command.get('ownedProcessReaped', True) is True and command.get('boundedFailure') is None
                and artifact(command['stderr'], 0) == b'', 'Saved integrated tool terminal differs')
        if apk is not None:
            require(Path(command['argv'][-1]) == io['ROOT'] / apk['path'], 'Saved tool inspected a different APK')
        return artifact(command['stdout'], limit)

    def package(row, proof, label):
        apk = artifact(row['apk'], 256 * 1024)
        cert = artifact(row['publicCertificate'], 16 * 1024)
        with ZipFile(BytesIO(apk)) as archive:
            entries = archive.infolist()
            require(len(entries) == len(row['payloadPins'])
                    and {entry.filename for entry in entries} == row['payloadPins'].keys()
                    and all(0 < entry.file_size <= 256 * 1024 for entry in entries), 'Integrated APK inventory differs')
            payloads = {entry.filename: archive.read(entry) for entry in entries}
        require({name: sha(raw) for name, raw in payloads.items()} == row['payloadPins'],
                'Integrated APK payload hashes differ')
        unsigned = artifact(row['unsignedApk'], 256 * 1024)
        with ZipFile(BytesIO(unsigned)) as archive:
            require(len(archive.infolist()) == len(payloads) and set(archive.namelist()) == payloads.keys()
                    and all(entry.file_size == len(payloads[entry.filename]) and archive.read(entry) == payloads[entry.filename]
                            for entry in archive.infolist()), 'Signed APK payload differs from the unsigned assembly')
        signer = sha(cert)
        verification = stdout(proof, label + '-verify', 4096, row['apk']).decode('ascii')
        require(verification.startswith('Verifies') and 'Number of signers: 1' in verification.splitlines()
                and 'Verified using v3 scheme (APK Signature Scheme v3): true' in verification.splitlines()
                and re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', verification) == [signer],
                'Saved integrated APK signer proof differs')
        badging = stdout(proof, label + '-badging', 4096, row['apk']).decode('ascii')
        identity = (f"package: name='{row['package']}' versionCode='{row['versionCode']}' "
                    f"versionName='{row['versionName']}' ")
        require(badging.startswith(identity) and row['versionCode'] == 1 and (row['minSdk'], row['targetSdk']) == (37, 37)
                and {"minSdkVersion:'37'", "targetSdkVersion:'37'"} <= set(badging.splitlines())
                and (label != 'app' or f"launchable-activity: name='{row['package']}.PrepareActivity'" in badging),
                'Saved integrated APK manifest proof differs')
        return {'package': row['package'], 'apkSha256': sha(apk), 'certificateSha256': signer}, payloads

    pair, build = record(PAIR_PIN), record(BUILD_PIN)
    require(pair['status'] == 'PASS_PC_MATCHED_READINESS_APKS_AND_PROFILE_ONLY'
            and build['status'] == 'PASS_PC_MATCHED_READINESS_STATIC_EXEC_PUBLISHER_ONLY'
            and all(row['schema'] == 'oneos-file-stage-integrated-tester-cohort/v1' and row['selected'] is False
                    and row['deviceEligible'] is False and row['targetExecuted'] is False for row in (pair, build))
            and all(build[key] == value for key, value in pair.items() if key not in ('status', 'commands'))
            and all(build['commands'][key] == value for key, value in pair['commands'].items()),
            'Saved integrated pair and publisher receipts disagree')
    require(pair['predecessorPair'] == dict(zip(('path', 'sha256'), PREDECESSOR_PIN))
            and pair['compileProof'] == dict(zip(('path', 'sha256'), COMPILE_PIN))
            and pair['controllerProof'] == dict(zip(('path', 'sha256'), V2_CONTROLLER_RECEIPT)),
            'Integrated provenance pins differ')
    predecessor, compiled, controller_proof = map(record, (PREDECESSOR_PIN, COMPILE_PIN, V2_CONTROLLER_RECEIPT))
    controller = pair['controller']
    stage = verify_local_cohort(carrier_protocol='v2')
    require(stage['status'] == 'MATCHED_LOCAL_COHORT_VERIFIED' and stage['mayExecute'] is False
            and stage['controllerSha256'] == controller['sha256']
            and all(controller[key] == value for key, value in stage['carrier'].items())
            and controller == controller_proof['executable'] == compiled['controller'] == predecessor['controller'],
            'Integrated controller differs from the staged controller')
    require_static_exec(artifact(controller, 1024**2))

    app, host = pair['packages']['app'], pair['packages']['host']
    previous_app, previous_host = predecessor['packages']['app'], predecessor['packages']['host']
    require(compiled['status'] == 'PASS_CONFIRMATION_LIFECYCLE_SDK37_D8_ONLY'
            and compiled['selected'] is False and compiled['signed'] is False and compiled['targetExecuted'] is False
            and len(compiled['javacClassPins']) == len(compiled['testerDex']['definitions']) == 31
            and compiled['testerDex']['definitions'] == previous_app['dex']['definitions']
            and app['dex'] == pair['testerDex']
            and all(app['dex'][key] == compiled['testerDex'][key] for key in ('bytes', 'sha256', 'definitions')),
            'Saved integrated compiler proof or 31-definition closure differs')
    require(all(compiled['commands'][label]['exitCode'] == 0
                and compiled['commands'][label]['ownedProcessReaped'] is True for label in ('app-javac', 'app-d8')),
            'Integrated compile terminal differs')
    host_proof = record(HOST_SIGNING_PIN)
    require(host['signingProof'] == dict(zip(('path', 'sha256'), HOST_SIGNING_PIN))
            and host_proof['status'] == 'PASS_SIGNED_PC_ONLY_EARLY_EXIT_HOST_APK'
            and host_proof['selected'] is False and host_proof['deviceEligible'] is False and host_proof['deviceAction'] is False
            and host_proof['signedApk'] == host['apk'] and host_proof['signedPackage'] == host['package']
            and all(host_proof[key] == host[key] for key in
                    ('publicCertificate', 'unsignedApk', 'payloadPins', 'versionCode', 'versionName', 'minSdk', 'targetSdk'))
            and host_proof['verifiedV3SignerCount'] == 1 and host_proof['unsignedToSignedPayloadChanged'] == []
            and host_proof['predecessorToSuccessorPayloadChanged'] == ['classes.dex'], 'Signed host receipt differs')
    for row, old in ((app, previous_app), (host, previous_host)):
        require(row['package'] == old['package'] and row['publicCertificate']['sha256'] != old['publicCertificate']['sha256']
                and row['payloadPins'].keys() == old['payloadPins'].keys()
                and {key for key in row['payloadPins'] if row['payloadPins'][key] != old['payloadPins'][key]} == {'classes.dex'},
                'Integrated APK package, signer transition or payload scope differs')
    tester, tester_payloads = package(app, build, 'app')
    host_identity, _ = package(host, host_proof, 'host')
    dex = tester_payloads['classes.dex']
    require(dex == artifact(compiled['testerDex'], 256 * 1024) == artifact(app['dex'], 256 * 1024)
            and sorted(name.decode('ascii') for name in Dex(dex).classes) == compiled['testerDex']['definitions'],
            'Packaged tester DEX differs from the exact compiled 31 definitions')

    profile = pair['profile']
    profile_bytes = artifact(profile['payload'], 288)
    fields = {'version': '2', 'package': tester['package'], 'signer': tester['certificateSha256'],
              'apk': tester['apkSha256'], 'code': str(app['versionCode']), 'native': controller['sha256'],
              'bytes': str(controller['bytes'])}
    require(len(profile_bytes) == 288 and profile['fields'] == fields and profile['targetSlot'] == PROFILE_SLOT
            and profile_bytes == ''.join(f'{key}={value}\n' for key, value in fields.items()).encode('ascii')
            and profile['protectedLoadInvoked'] is False and profile['publisherSelected'] is False
            and stdout(build, 'profile-parser', 4096).strip() == b'PASS exact V2 profile roundtrip and six format refusals',
            'Integrated protected profile binding differs')
    publisher = artifact(build['artifact'], 2 * 1024**2)
    require_static_exec(publisher)
    embedded = build['embeddedProfile']
    offset = embedded['offset']
    require(stdout(build, 'publisher-link', 2 * 1024**2) == publisher
            and embedded['symbol'] == 'oneos_verified_host_profile' and embedded['bytes'] == 288
            and embedded['sha256'] == sha(profile_bytes) and type(offset) is int and offset >= 0
            and publisher[offset:offset + 288] == profile_bytes and publisher.count(profile_bytes) == 1,
            'Integrated static publisher contains different profile bytes')
    return {'status': 'MATCHED_LOCAL_COHORT_VERIFIED', 'mayExecute': False,
            'pairReceiptSha256': PAIR_PIN[1], 'profileSha256': sha(profile_bytes), 'controllerSha256': controller['sha256'],
            'packages': {'tester': tester, 'host': host_identity}}
