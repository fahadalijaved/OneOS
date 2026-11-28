"""Read the exact unselected confirmation tester, profile, and publisher on the PC."""

from dataclasses import dataclass, field
from io import BytesIO
import json
import re
from pathlib import Path
from zipfile import ZipFile

from check_file_stage_device_preflight import require
from check_file_stage_local_cohort import (
    PAIR_STATUS, PROFILE_SLOT, V2_CONTROLLER_RECEIPT, pair_receipt_pin, require_static_exec,
    verify_local_cohort,
)
from run_guest_tree_install_transport import load_io, pinned, sha


RUN = 'out/file-stage-confirmation-rebuild/app/r-5cef399d'
PAIR_PIN = (RUN + '/pair-receipt.json', '196ddf261d05f8f5bfdaea4594dec821d6040ba1964e583a02bec51342f25f64')
BUILD_PIN = (RUN + '/receipt.json', '9963ce70b7699bbd40da09eab445e60fb22f742fbcb340aba7b6c91692633256')
CONFIRMATION_TESTER_BYTES = 53452
CONFIRMATION_TESTER_SHA256 = '0b8be31a2f0a84e5a8112c8074b0fdb9938c56878320da63967cad168fb23d15'
CONFIRMATION_PROFILE_SHA256 = 'b86263923519ef24ac1dc01e982a55f04946ac149a9f9d68cd46f476983239af'
CONFIRMATION_PUBLISHER_NAME = 'publisher-confirmation'
CONFIRMATION_PUBLISHER_BYTES = 580128
CONFIRMATION_PUBLISHER_SHA256 = '73e1cb3447e5f87d6b5d87f5e6eb96c0da7eaeb5a57950ac2f8829dc1e650540'
_SCHEMA = 'oneos-file-stage-confirmation-cohort/v1'
_PERMIT = 'Lcom/fahadali/oneos/core/root/RetainedRootHostServiceV2$PreparationPermit;'


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    size: int
    sha256: str
    data: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class ConfirmationCohort:
    tester_apk: Artifact
    tester_certificate: Artifact
    profile: Artifact
    publisher: Artifact
    tester_package: str
    tester_version_code: int
    tester_version_name: str
    host_package: str
    host_apk_sha256: str
    host_certificate_sha256: str
    controller_size: int
    controller_sha256: str
    may_execute: bool = field(default=False, init=False)


def load_confirmation_cohort() -> ConfirmationCohort:
    """Return immutable bytes and identities after checking the saved build evidence."""
    io = load_io()

    def record(pin, limit):
        return json.loads(pinned(io, *pin, limit), object_pairs_hook=io['unique_object'])

    def artifact(row, limit):
        path, size, digest = row['path'], row['bytes'], row['sha256']
        require(type(size) is int and 0 <= size <= limit, 'Confirmation artifact exceeds its bound')
        data = pinned(io, path, digest, size)
        require(len(data) == size, 'Incomplete confirmation artifact')
        return Artifact(path, size, digest, data)

    def stdout(receipt, label, limit, apk=None):
        command = receipt['commands'][label]
        require(type(command['exitCode']) is int and command['exitCode'] == 0
                and command['ownedProcessReaped'] is True and command['boundedFailure'] is None,
                'Unconfirmed saved confirmation tool terminal')
        if apk is not None:
            require(Path(command['argv'][-1]) == io['ROOT'] / apk.path, 'Saved verifier inspected another APK')
        require(artifact(command['stderr'], 0).data == b'', 'Unexpected saved confirmation diagnostics')
        return artifact(command['stdout'], limit)

    def package(receipt, label, row, launcher=False):
        apk = artifact(row['apk'], 256 * 1024)
        cert = artifact(row['publicCertificate'], 16 * 1024)
        with ZipFile(BytesIO(apk.data)) as archive:
            entries = archive.infolist()
            require(len(entries) == len(row['payloadPins'])
                    and {entry.filename for entry in entries} == row['payloadPins'].keys()
                    and all(0 < entry.file_size <= 256 * 1024 for entry in entries),
                    'Signed APK payload inventory differs')
            require(all(sha(archive.read(entry)) == row['payloadPins'][entry.filename] for entry in entries),
                    'Signed APK payload differs from saved manifest or DEX pins')
        verify = stdout(receipt, label + '-verify', 4096, apk).data.decode('ascii')
        require(verify.splitlines()[0] == 'Verifies'
                and 'Number of signers: 1' in verify.splitlines()
                and 'Verified using v3 scheme (APK Signature Scheme v3): true' in verify.splitlines()
                and re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})', verify) == [cert.sha256],
                'Saved APK signature proof differs')
        badging = stdout(receipt, label + '-badging', 4096, apk).data.decode('ascii')
        identity = (f"package: name='{row['package']}' versionCode='{row['versionCode']}' "
                    f"versionName='{row['versionName']}' ")
        require(badging.startswith(identity) and "minSdkVersion:'37'" in badging.splitlines()
                and "targetSdkVersion:'37'" in badging.splitlines()
                and (row['minSdk'], row['targetSdk']) == (37, 37)
                and (not launcher or f"launchable-activity: name='{row['package']}.PrepareActivity'" in badging),
                'Saved APK manifest badging differs')
        return apk, cert

    pair = record(PAIR_PIN, 64 * 1024)
    build = record(BUILD_PIN, 96 * 1024)
    require(pair['status'] == PAIR_STATUS
            and build['status'] == 'PASS_PC_MATCHED_READINESS_STATIC_EXEC_PUBLISHER_ONLY'
            and all(row['schema'] == _SCHEMA and row['selected'] is False and row['deviceEligible'] is False
                    and row['targetExecuted'] is False and row['hostReusedByteForByte'] is True
                    and row['testerSignerMatchesPredecessor'] is False for row in (pair, build))
            and all(build[key] == value for key, value in pair.items() if key not in ('status', 'commands'))
            and all(build['commands'][key] == value for key, value in pair['commands'].items()),
            'Confirmation pair and publisher receipts disagree')

    stage = verify_local_cohort(carrier_protocol='v2')
    old_path, old_sha = pair_receipt_pin('v2')
    require(stage['status'] == 'MATCHED_LOCAL_COHORT_VERIFIED' and stage['mayExecute'] is False
            and stage['installerProtocol'] == 'v2' and stage['pairReceiptSha256'] == old_sha
            and pair['predecessorPair'] == {'path': old_path, 'sha256': old_sha},
            'Confirmation pair does not derive from the staged cohort')
    old = record((old_path, old_sha), 64 * 1024)
    controller = pair['controller']
    controller_path, controller_sha = V2_CONTROLLER_RECEIPT
    require(pair['controllerProof'] == {'path': controller_path, 'sha256': controller_sha}
            and record(V2_CONTROLLER_RECEIPT, 64 * 1024)['executable'] == old['controller'] == controller
            and controller['sha256'] == stage['controllerSha256']
            and all(controller[key] == value for key, value in stage['carrier'].items()),
            'Confirmation controller or carrier differs from the staged cohort')

    tester, host = (pair['packages'][role] for role in ('app', 'host'))
    old_tester = old['packages']['app']
    require(host == old['packages']['host']
            and all(tester[key] == old_tester[key] for key in ('package', 'versionCode', 'versionName', 'minSdk', 'targetSdk'))
            and all(tester['payloadPins'][key] == old_tester['payloadPins'][key]
                    for key in ('AndroidManifest.xml', 'resources.arsc'))
            and tester['publicCertificate']['sha256'] != old_tester['publicCertificate']['sha256']
            and tester['dex'] == pair['testerDex'] and tester['payloadPins']['classes.dex'] == tester['dex']['sha256']
            and pair['dexDefinitionDelta'] == {'added': [_PERMIT], 'removed': []}
            and len(tester['dex']['definitions']) == 31
            and set(tester['dex']['definitions']) == set(old_tester['dex']['definitions']) | {_PERMIT},
            'Unexpected confirmation APK or definition delta')
    tester_apk, tester_cert = package(build, 'app', tester, launcher=True)
    require((tester_apk.size, tester_apk.sha256) == (CONFIRMATION_TESTER_BYTES, CONFIRMATION_TESTER_SHA256),
            'Saved tester APK differs from the confirmation pin')
    historical_host = record(('out/file-stage-readiness-package/r-6c688c4ff1/receipt.json',
                              '63892c552dee93bc017731ddd4aec8b0c51b7809bb472d54f6faaafc1bdecabb'), 64 * 1024)
    require(historical_host['packages']['host'] == host, 'Saved host signature proof belongs to another package')
    host_apk, host_cert = package(historical_host, 'host', host)

    profile = artifact(pair['profile']['payload'], 288)
    fields = {'version': '2', 'package': tester['package'], 'signer': tester_cert.sha256,
              'apk': tester_apk.sha256, 'code': str(tester['versionCode']),
              'native': controller['sha256'], 'bytes': str(controller['bytes'])}
    expected = ''.join(f'{key}={value}\n' for key, value in fields.items()).encode('ascii')
    require(profile.size == 288 and profile.sha256 == CONFIRMATION_PROFILE_SHA256
            and profile.data == expected and pair['profile']['fields'] == fields
            and pair['profile']['targetSlot'] == PROFILE_SLOT and pair['profile']['protectedLoadInvoked'] is False
            and pair['profile']['publisherSelected'] is False
            and stdout(build, 'profile-parser', 4096).data.strip() == b'PASS exact V2 profile roundtrip and six format refusals',
            'Confirmation profile does not bind the exact tester and staged controller')
    publisher = artifact(build['artifact'], 2 * 1024**2)
    require((publisher.size, publisher.sha256) == (CONFIRMATION_PUBLISHER_BYTES, CONFIRMATION_PUBLISHER_SHA256),
            'Saved publisher differs from the confirmation pin')
    require_static_exec(publisher.data)
    embedded = build['embeddedProfile']
    offset = embedded['offset']
    require(stdout(build, 'publisher-link', 2 * 1024**2) == publisher
            and embedded['symbol'] == 'oneos_verified_host_profile' and embedded['sha256'] == profile.sha256
            and embedded['bytes'] == profile.size and type(offset) is int and offset >= 0
            and publisher.data[offset:offset + profile.size] == profile.data and publisher.data.count(profile.data) == 1,
            'Static publisher does not contain the exact confirmation profile')
    return ConfirmationCohort(tester_apk, tester_cert, profile, publisher, tester['package'], tester['versionCode'],
                              tester['versionName'], host['package'], host_apk.sha256, host_cert.sha256,
                              controller['bytes'], controller['sha256'])
