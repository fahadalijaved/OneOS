"""Verify a matched Stop status APK, profile and publisher cohort offline."""

import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import struct
from zipfile import BadZipFile, ZipFile

from check_file_stage_device_preflight import require
from check_file_stage_local_cohort import PROFILE_SLOT, require_static_exec
from check_guarded_stage_bundle import Dex
from check_retained_view_host_pair import signature_v3
from file_stage_integrated_cohort import HOST_SIGNING_PIN, PAIR_PIN as PREDECESSOR_PIN
from package_isolated_retained_view_app import stored_zip as tester_zip
from package_retained_view_ingress_host import stored_zip as host_zip
from run_guest_tree_install_transport import load_io, pinned, sha


COMPILE_PIN = ('out/file-stage-stop-status-build/r-c032e8ba/receipt.json',
               'fdb366c5f8d089bfa788f1fc828efe269f1f7643df6fdbd35d8f9a1f74e50be4')
CONTROLLER_PIN = ('out/file-stage-controller-successor-build/r-22e19452/receipt.json',
                  '6a5f79ba5ae2a65dabe54e544ef7a103f9094055226a794802eaec6bc7d345e8')
_HEX64 = re.compile(r'[0-9a-f]{64}')
_PATH = re.compile(r'out(?:/[A-Za-z0-9_.-]+)+')
_APK_MAX = 256 * 1024
_EXEC_MAX = 2 * 1024 * 1024
_ARTIFACT = {'path', 'bytes', 'sha256'}
_CONTROLLER_ARTIFACT = _ARTIFACT | {'imageBytes', 'imageSha256', 'fsVerityDigest'}
_PACKAGE = {'package', 'versionCode', 'versionName', 'minSdk', 'targetSdk', 'apk', 'unsignedApk',
            'publicCertificate', 'dex', 'payloadPins'}
_HOST_METADATA = {
    'META-INF/xposed/module.prop': b'minApiVersion=102\ntargetApiVersion=102\nstaticScope=true\nautoHotReload=false\n',
    'META-INF/xposed/scope.list': b'android\n',
    'META-INF/xposed/java_init.list': b'com.appleexploit.oneos.security.authority.RetainedPinHostModule\n',
}
_PAYLOADS = ('AndroidManifest.xml', 'resources.arsc', 'classes.dex')
_STATUS_CLASS = b'Lcom/fahadali/oneos/core/root/RetainedStopStatus;'
_APP_JAVAC_WARNINGS = (
    b'warning: [options] source value 8 is obsolete and will be removed in a future release\r\n'
    b'warning: [options] target value 8 is obsolete and will be removed in a future release\r\n'
    b'warning: [options] To suppress warnings about obsolete options, use -Xlint:-options.\r\n3 warnings\r\n'
)


def _path(value):
    require(type(value) is str and len(value) <= 512 and _PATH.fullmatch(value) is not None
            and not {'.', '..'}.intersection(value.split('/')), 'Expected a canonical repository output path')
    return value


def _digest(value):
    require(type(value) is str and _HEX64.fullmatch(value) is not None, 'Expected an exact lowercase SHA-256')
    return value


def _pin(io, path, digest, maximum):
    return pinned(io, _path(path), _digest(digest), maximum)


def _proof(pin):
    return dict(zip(('path', 'sha256'), pin))


def _matches_proof(row, pin):
    expected = _proof(pin)
    return type(row) is dict and (row == expected or row.keys() == _ARTIFACT
                                  and type(row['bytes']) is int and 0 < row['bytes'] <= 256 * 1024
                                  and all(row[key] == value for key, value in expected.items()))


def _record(io, pin):
    require(type(pin) in (tuple, list) and len(pin) == 2, 'Expected a pinned local receipt')
    require(_path(pin[0]).endswith('/receipt.json') or pin[0] == PREDECESSOR_PIN[0], 'Unexpected receipt filename')
    data = _pin(io, *pin, 256 * 1024)
    row = json.loads(data.decode('ascii'), object_pairs_hook=io['unique_object'])
    require(type(row) is dict, 'Expected one receipt object')
    return row


def _artifact(io, row, maximum, *, minimum=1, suffix=None):
    require(type(row) is dict and _ARTIFACT <= row.keys() and type(row['bytes']) is int
            and minimum <= row['bytes'] <= maximum and (suffix is None or _path(row['path']).endswith(suffix)),
            'Unexpected pinned artifact extent or type')
    raw = _pin(io, row['path'], row['sha256'], row['bytes'])
    require(len(raw) == row['bytes'], 'Pinned artifact length differs')
    return raw


def _tool_output(io, receipt, label, limit, *, inspected=None, expected_stderr=b''):
    command = receipt['commands'][label]
    require(type(command['exitCode']) is int and command['exitCode'] == 0
            and command['ownedProcessReaped'] is True and command['boundedFailure'] is None
            and _artifact(io, command['stderr'], len(expected_stderr), minimum=0) == expected_stderr,
            f'Saved {label} terminal differs')
    if inspected is not None:
        require(Path(command['argv'][-1]) == io['ROOT'] / inspected['path'],
                f'Saved {label} inspected another artifact')
    return _artifact(io, command['stdout'], limit, minimum=0)


def _offline(row):
    return all(row.get(key) is False for key in ('selected', 'deviceEligible', 'deviceAction'))


def _package_receipt(receipt, role):
    require(receipt.get('schema') == f'oneos-file-stage-stop-status-{role}-package/v1'
            and receipt.get('status') == f'PASS_SIGNED_PC_ONLY_STOP_STATUS_{role.upper()}_APK'
            and _offline(receipt), 'Unexpected unselected Stop status APK receipt')


def _zip(raw, names, *, signed, is_host):
    with ZipFile(BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(tuple(entry.filename for entry in entries) == names and all(
            entry.compress_type == 0 and entry.flag_bits == 0 and 0 < entry.file_size <= _APK_MAX
            and entry.compress_size == entry.file_size for entry in entries), 'Unexpected exact APK member inventory')
        payloads = {entry.filename: archive.read(entry) for entry in entries}
    read = host_zip if is_host else tester_zip
    entries, _ = read(raw, payloads, signed=signed)
    require(all(entry['data'] % 4 == 0 for entry in entries), 'APK stored member is misaligned')
    return payloads, {entry['name']: entry['data'] for entry in entries}


def _signature_log(raw, scheme, signature):
    lines = raw.decode('ascii').splitlines()
    require(lines and lines[0] == 'Verifies' and 'Number of signers: 1' in lines
            and f'Verified using v{scheme} scheme (APK Signature Scheme v{scheme}): true' in lines
            and re.findall(rb'certificate SHA-256 digest: ([0-9a-f]{64})', raw)
            == [signature['certificateSha256'].encode('ascii')]
            and re.findall(rb'public key SHA-256 digest: ([0-9a-f]{64})', raw)
            == [signature['publicKeySha256'].encode('ascii')], 'Saved APK signer verification differs')


def _package(io, receipt, predecessor, compiled, role, controller):
    is_host = role == 'host'
    row = receipt['package']
    fields = _PACKAGE if is_host else _PACKAGE | {'signedDataOffsets'}
    require(type(row) is dict and row.keys() == fields and all(row[key] == predecessor[key] for key in
            ('package', 'versionCode', 'versionName', 'minSdk', 'targetSdk'))
            and all(type(row[key]) is int for key in ('versionCode', 'minSdk', 'targetSdk')),
            'APK package identity differs from its predecessor')
    require(row['dex'] == compiled['dex'], 'Packaged DEX receipt differs from the exact SDK37 build')
    names = _PAYLOADS + tuple(_HOST_METADATA) if is_host else _PAYLOADS
    old_apk = _artifact(io, predecessor['apk'], _APK_MAX, suffix='.apk')
    apk = _artifact(io, row['apk'], _APK_MAX, suffix='.apk')
    unsigned = _artifact(io, row['unsignedApk'], _APK_MAX, suffix='.apk')
    certificate = _artifact(io, row['publicCertificate'], 16 * 1024, suffix='.der')
    old_payloads, _ = _zip(old_apk, names, signed=True, is_host=is_host)
    payloads, offsets = _zip(apk, names, signed=True, is_host=is_host)
    expected_offsets = receipt['signedDataOffsets'] if is_host else row['signedDataOffsets']
    require(payloads == _zip(unsigned, names, signed=False, is_host=is_host)[0] and offsets == expected_offsets
            and {key: sha(value) for key, value in payloads.items()} == row['payloadPins']
            and {key for key in names if payloads[key] != old_payloads[key]} == {'classes.dex'},
            'Signed/unsigned APK payloads or predecessor delta differ')
    if is_host:
        require(all(payloads[key] == value for key, value in _HOST_METADATA.items()), 'Host scope or module entry differs')

    code = payloads['classes.dex']
    require(code == _artifact(io, compiled['dex'], _APK_MAX, suffix='/classes.dex'), 'Packaged DEX bytes differ')
    dex = Dex(code)
    definitions = sorted(name.decode('ascii') for name in dex.classes)
    require(definitions == compiled['dex']['definitions'] and len(definitions) == (53 if is_host else 34)
            and set(definitions) == {f'L{name.removesuffix(".class")};' for name in compiled['classPins']},
            'Exact Stop status DEX definition closure differs')
    dex.constants(_STATUS_CLASS, {'TRANSACTION': 6, 'VERSION': 1})
    if is_host:
        require(code.count(controller['sha256'].encode('ascii') + b'\0') == 1,
                'Host DEX is missing its exact successor controller digest')
    else:
        dex.constants(b'Lcom/fahadali/oneos/BuildConfig;', {
            'RETAINED_VIEW_PREPARATION': True, 'RETAINED_VIEW_CONTROLLER_SHA256': controller['sha256'],
            'RETAINED_VIEW_CONTROLLER_BYTES': controller['bytes'],
        })

    signature, old_signature = signature_v3(apk), signature_v3(old_apk)
    require(signature['certificateSha256'] == sha(certificate), 'Public certificate is not the APK signing leaf')
    labels = ('host-verify-v2', 'host-verify-v3', 'host-badging') if is_host else ('verifyV2', 'verify', 'badging')
    if is_host:
        readback = receipt['signatureReadback']
        require(readback['v2Verified'] is True and readback['v3Verified'] is True
                and type(readback['numberOfSigners']) is int and readback['numberOfSigners'] == 1
                and readback['v2SdkRange'] == [24, 27] and readback['v3ManifestMinSdk'] == 37
                and readback['v2'] == receipt['commands'][labels[0]]['stdout']
                and readback['v3'] == receipt['commands'][labels[1]]['stdout']
                and readback['certificateSha256'] == signature['certificateSha256'], 'Saved host signing proof differs')
    else:
        require(all(type(receipt[key]) is int and receipt[key] == 1
                    for key in ('verifiedV2SignerCount', 'verifiedV3SignerCount'))
                and receipt['targetExecuted'] is False, 'Saved tester signing proof differs')
    for scheme, label in enumerate(labels[:2], 2):
        flags = ['verify', '--verbose', '--print-certs']
        if scheme == 2:
            flags += ['--min-sdk-version', '24', '--max-sdk-version', '27']
        require(receipt['commands'][label]['argv'][-len(flags) - 1:-1] == flags,
                'Saved APK signature verification SDK range differs')
        _signature_log(_tool_output(io, receipt, label, 8192, inspected=row['apk']), scheme, signature)
    badging = _tool_output(io, receipt, labels[2], 8192, inspected=row['apk']).decode('ascii').splitlines()
    identity = (f"package: name='{row['package']}' versionCode='{row['versionCode']}' "
                f"versionName='{row['versionName']}' ")
    launcher = f"launchable-activity: name='{row['package']}.PrepareActivity'"
    launches = [line for line in badging if line.startswith('launchable-activity:')]
    require(badging and badging[0].startswith(identity)
            and {"minSdkVersion:'37'", "targetSdkVersion:'37'"} <= set(badging)
            and (not launches if is_host else len(launches) == 1 and launches[0].startswith(launcher)),
            'Saved APK manifest badging differs')
    return {'package': row['package'], 'apkSha256': row['apk']['sha256'],
            'certificateSha256': signature['certificateSha256'], 'publicKeySha256': signature['publicKeySha256'],
            'apk': row['apk'], 'dex': row['dex'], 'payloadPins': row['payloadPins']}, old_signature


def _controller(io, compiled, predecessor):
    receipt = _record(io, CONTROLLER_PIN)
    require(receipt['schema'] == 'oneos-file-stage-controller-successor-static-build/v1'
            and receipt['status'] == 'PASS_FILE_BACKED_CONTROLLER_SUCCESSOR_STATIC_EXEC_LINK_ONLY'
            and all(receipt[key] is False for key in ('selected', 'deviceEligible', 'targetExecuted'))
            and receipt['predecessor'] == predecessor['controller'], 'Unexpected controller successor proof')
    controller = receipt['executable']
    require(controller.keys() == _CONTROLLER_ARTIFACT and controller == compiled['controller']
            and all(controller[key] == predecessor['controller'][key]
                    for key in ('imageBytes', 'imageSha256', 'fsVerityDigest')),
            'Compiled controller or carrier identity differs')
    raw = _artifact(io, controller, _EXEC_MAX, suffix='/oneos_retained_tree_preparation')
    require_static_exec(raw)
    carrier_pin = controller['imageBytes'].to_bytes(8, 'little') + bytes.fromhex(controller['fsVerityDigest'])
    require(raw.count(carrier_pin) == 1 and raw.count(b'--host-control-v2\0') == 1,
            'Controller does not embed the expected carrier and entry profile')
    return controller


def _publisher(io, receipt, tester_receipt, tester_pin, controller, compiled):
    require(receipt['schema'] == 'oneos-file-stage-stop-status-profile-publisher/v1'
            and receipt['status'] == 'PASS_STOP_STATUS_PROFILE_AND_STATIC_EXEC_PUBLISHER_ONLY'
            and _offline(receipt) and receipt['targetExecuted'] is False
            and _matches_proof(receipt['testerProof'], tester_pin)
            and _matches_proof(receipt['compileProof'], COMPILE_PIN)
            and _matches_proof(receipt['controllerProof'], CONTROLLER_PIN), 'Publisher provenance differs')
    tester = tester_receipt['package']
    require(receipt['testerApk'] == tester['apk'] and receipt['testerCertificate'] == tester['publicCertificate']
            and all(receipt['controller'][key] == controller[key] for key in _ARTIFACT),
            'Publisher receipt differs from the actual tester or controller')
    profile = receipt['profile']
    fields = {'version': '2', 'package': tester['package'], 'signer': tester['publicCertificate']['sha256'],
              'apk': tester['apk']['sha256'], 'code': str(tester['versionCode']),
              'native': controller['sha256'], 'bytes': str(controller['bytes'])}
    raw = _artifact(io, profile['payload'], 288, suffix='.txt')
    parser = {name: digest for name, digest in compiled['cohorts']['host']['classPins'].items()
              if name.startswith('com/appleexploit/oneos/security/authority/HostRootLinkProfileV2')}
    require(len(raw) == 288 and raw == ''.join(f'{key}={value}\n' for key, value in fields.items()).encode('ascii')
            and profile['fields'] == fields and profile['targetSlot'] == PROFILE_SLOT
            and profile['parserClassPins'] == parser and len(parser) == 3 and profile['formatRefusals'] == 6
            and profile['protectedLoadInvoked'] is False and profile['publisherSelected'] is False
            and _tool_output(io, receipt, 'profile-parser', 4096).strip()
            == b'PASS exact V2 profile roundtrip and six format refusals', 'Protected profile binding differs')
    publisher = _artifact(io, receipt['artifact'], _EXEC_MAX, suffix='/oneos_publish_verified_host_profile')
    require_static_exec(publisher)
    embedded = receipt['embeddedProfile']
    offset = embedded['offset']
    inspected = _tool_output(io, receipt, 'publisher-inspect', 512 * 1024, inspected=receipt['artifact'])
    require(_tool_output(io, receipt, 'publisher-link', _EXEC_MAX) == publisher
            and embedded['symbol'] == 'oneos_verified_host_profile' and embedded['bytes'] == len(raw)
            and embedded['sha256'] == sha(raw) and type(offset) is int and offset >= 0
            and publisher[offset:offset + len(raw)] == raw and publisher.count(raw) == 1
            and embedded['elfEntry'] == struct.unpack_from('<Q', publisher, 24)[0]
            and b'There are no relocations in this file.' in inspected.splitlines()
            and len(re.findall(rb'(?m)^\s*\d+: [0-9a-fA-F]+\s+288 OBJECT\s+GLOBAL\s+DEFAULT\s+\d+ '
                               rb'oneos_verified_host_profile\r?$', inspected)) == 1
            and all(embedded[key] is False for key in ('ptInterp', 'dtNeeded', 'pendingRelocations')),
            'Publisher does not embed the exact protected profile once')
    return profile['payload'], receipt['artifact']


def stop_status_cohort(tester_pin, host_pin, publisher_pin) -> dict:
    """Return matched public artifact metadata without selecting device actions."""
    io = load_io()
    tester_receipt, host_receipt, publisher_receipt = (_record(io, pin) for pin in (tester_pin, host_pin, publisher_pin))
    _package_receipt(tester_receipt, 'tester')
    _package_receipt(host_receipt, 'host')
    compiled, predecessor = (_record(io, pin) for pin in (COMPILE_PIN, PREDECESSOR_PIN))
    require(compiled['schema'] == 'oneos-file-stage-stop-status-sdk37-d8/v1'
            and compiled['status'] == 'PASS_MATCHED_STOP_STATUS_SDK37_D8_ONLY'
            and all(compiled[key] is False for key in ('selected', 'deviceEligible', 'signed', 'targetExecuted')),
            'Unexpected exact Stop status SDK37/D8 build')
    _tool_output(io, compiled, 'app-javac', 8192, expected_stderr=_APP_JAVAC_WARNINGS)
    for label in ('app-d8', 'host-javac', 'host-d8'):
        _tool_output(io, compiled, label, 8192)
    old = predecessor['packages']
    prior_host = _record(io, HOST_SIGNING_PIN)
    require(_matches_proof(tester_receipt['compileProof'], COMPILE_PIN)
            and _matches_proof(tester_receipt['predecessorPair'], PREDECESSOR_PIN)
            and tester_receipt['predecessorSignedApk'] == old['app']['apk']
            and _matches_proof(host_receipt['buildReceipt'], COMPILE_PIN)
            and _matches_proof(host_receipt['predecessorReceipt'], HOST_SIGNING_PIN)
            and host_receipt['predecessorApk'] == prior_host['signedApk'] == old['host']['apk']
            and host_receipt['predecessorCertificate'] == prior_host['publicCertificate'] == old['host']['publicCertificate'],
            'APK cohort proof differs')
    controller = _controller(io, compiled, predecessor)
    tester, old_tester = _package(io, tester_receipt, old['app'], compiled['cohorts']['app'], 'tester', controller)
    host, old_host = _package(io, host_receipt, old['host'], compiled['cohorts']['host'], 'host', controller)
    for key in ('certificateSha256', 'publicKeySha256'):
        require(len({tester[key], host[key], old_tester[key], old_host[key]}) == 4,
                'Stop status packages did not receive distinct fresh signing identities')
    profile, publisher = _publisher(io, publisher_receipt, tester_receipt, tester_pin, controller, compiled)
    return {'status': 'MATCHED_STOP_STATUS_PACKAGE_VERIFIED', 'mayExecute': False, 'deviceAcceptance': False,
            'controller': controller, 'profile': profile, 'publisher': publisher,
            'packages': {'tester': tester, 'host': host},
            'proofs': {'compile': _proof(COMPILE_PIN), 'controller': _proof(CONTROLLER_PIN),
                       'predecessor': _proof(PREDECESSOR_PIN), 'tester': _proof(tester_pin), 'host': _proof(host_pin),
                       'publisher': _proof(publisher_pin)}}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    for role in ('tester', 'host', 'publisher'):
        cli.add_argument(f'--{role}', metavar=('RECEIPT', 'SHA256'), nargs=2, required=True)
    args = cli.parse_args(argv)
    try:
        result = stop_status_cohort(args.tester, args.host, args.publisher)
    except (BadZipFile, IndexError, KeyError, OSError, OverflowError, RecursionError, TypeError, ValueError, struct.error) as error:
        cli.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
