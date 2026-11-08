"""Emit an offline host-profile candidate for the exact signed file-backed tester."""

import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile


ROOT = Path(__file__).absolute().parents[3]
VERIFIED_RUN = 'out/file-stage-prepare-app-build-review/verify-dad1e3ec'
VERIFY_SHA = '0eee6a9848bd7e41bde446c5d4bb3b9114a72543d8a5f689d3bb82ab2e0a531e'
SIGN_RUN = 'out/file-stage-prepare-app-build-review/r-4935c4ad'
SIGN_SHA = '86fc952e336467b6f3aa00441fec094bdf41be03d9857be4cc88161dc08f2563'
SOURCE = 'out/file-stage-preparation-app/enabled/receipt.json'
SOURCE_SHA = '3ac2c90ccefb7c0db21984228e2451a520ae29918f896c4bc547f9ec9720dde2'
HOST_RUN = 'out/retained-view-ingress-host-package/r-698a94c6149a'
HOST_APK = {
    'path': f'{HOST_RUN}/OneOS-Retained-View-Ingress-Host-debug.apk',
    'sha256': '50413f663e7a87d1b561dc5aaefdc7c46561dc431fffe03d3bc4053be0a9e2c4',
    'bytes': 139689,
}
HOST_SOURCE = 'out/retained-view-ingress-build/r-2dc4e293/host-src'
HOST_PINS = {
    'HostRootLinkProfileV2.java': '020c0a2f91c8c62505851a2d091df1672b60cfd8d2ec012577077ca02fffdfec',
    'PreparedRetainedHostNativeBindingV2.java': '35ae3a2e3ed50017ac0528dff7a170a0cd84814bb3e2fdb400be7dd8b2b10d8d',
}
PACKAGE = 'com.fahadali.oneos.viewprep.filetree'
VERSION = '0.0.1-filetree'
SERVICE = 'com.fahadali.oneos.core.root.RetainedRootHostServiceV2'
DEVICE_SLOT = '/data/system/oneos_retained_root_link_v2'
APK = 'OneOS-File-View-Prep-debug.apk'
PAYLOADS = {'AndroidManifest.xml', 'resources.arsc', 'classes.dex'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(relative):
    path = ROOT / relative
    require(path.is_relative_to(ROOT / 'out') and '..' not in path.parts,
            'Expected a saved path under repository out')
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            pass
        else:
            require(not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
                    f'Reparse path refused: {part}')
        if part == ROOT:
            break
    return path


def candidate():
    inputs = {}

    def read(name, expected=None, size=None, limit=2 * 1024 * 1024):
        path = local(name)
        require(stat.S_ISREG(path.lstat().st_mode), f'Expected a regular saved input: {name}')
        with path.open('rb') as stream:
            data = stream.read(limit + 1)
        actual = digest(data)
        require(0 < len(data) <= limit and (expected is None or actual == expected)
                and (size is None or len(data) == size), f'Saved input differs: {name}')
        inputs[name] = {'sha256': actual, 'bytes': len(data)}
        return data

    receipt = json.loads(read(f'{VERIFIED_RUN}/receipt.json', VERIFY_SHA))
    require(receipt['schema'] == 'oneos-file-stage-preparation-app-build/v1'
            and receipt['status'] == 'PASS_PC_FILE_STAGE_PREPARATION_DEBUG_APK'
            and receipt['run'] == VERIFIED_RUN and receipt['deviceEligible'] is False,
            'Expected actual signed PC tester build')
    predecessor = f'{SIGN_RUN}/receipt.json'
    require(receipt['predecessor'] == {'path': predecessor, 'sha256': SIGN_SHA},
            'Expected the exact signing run before saved verification')
    read(predecessor, SIGN_SHA)
    require(receipt['sourceReceipt'] == {'path': SOURCE, 'sha256': SOURCE_SHA},
            'Expected enabled source receipt')
    source = json.loads(read(SOURCE, SOURCE_SHA))
    controller = receipt['controller']
    require(source['enabled'] is True and controller == source['controller']
            and 0 < controller['bytes'] <= 2097152, 'Selected controller differs')
    require(receipt['compiledConfig'] == {'RETAINED_VIEW_PREPARATION': True,
            'RETAINED_VIEW_CONTROLLER_SHA256': controller['sha256'],
            'RETAINED_VIEW_CONTROLLER_BYTES': controller['bytes']}, 'Actual compiled pins differ')
    read(controller['path'], controller['sha256'], controller['bytes'])
    require(receipt['unchangedHostApk'] == HOST_APK, 'Signed host identity differs')
    read(HOST_APK['path'], HOST_APK['sha256'], HOST_APK['bytes'])
    for name, expected in HOST_PINS.items():
        read(f'{HOST_SOURCE}/{name}', expected)

    app, cert = receipt['apk'], receipt['publicCertificate']
    require(app['path'] == f'{SIGN_RUN}/{APK}' and cert['path'] == f'{SIGN_RUN}/debug-certificate.der',
            'Expected the saved APK and public certificate from the signing run')
    apk = read(app['path'], app['sha256'], app['bytes'])
    signer = digest(read(cert['path'], cert['sha256'], cert['bytes'], 16384))
    with zipfile.ZipFile(io.BytesIO(apk)) as archive:
        require(len(archive.namelist()) == 3 and set(archive.namelist()) == PAYLOADS
                and all(entry.compress_type == zipfile.ZIP_STORED and 0 < entry.file_size <= len(apk)
                        for entry in archive.infolist())
                and set(receipt['payloadPins']) == PAYLOADS
                and all(digest(archive.read(name)) == receipt['payloadPins'][name] for name in PAYLOADS),
                'APK payload differs')

    profile = receipt['profile']
    require(profile['package'] == PACKAGE and profile['versionCode'] == 1
            and profile['versionName'] == VERSION and profile['minSdk'] == profile['targetSdk'] == 37
            and profile['service'] == SERVICE and profile['activity'] == f'{PACKAGE}.PrepareActivity',
            'Signed app identity differs')
    def transcript(label):
        command = receipt['commands'][label]
        require(command == json.loads(read(f'{VERIFIED_RUN}/{label}.result.json')) and command['exitCode'] == 0
                and Path(command['argv'][-1]) == local(app['path']), f'Wrong saved {label} invocation')
        output = command['stdout']
        require(output['path'] == f'{VERIFIED_RUN}/{label}.stdout', f'Wrong saved {label} transcript')
        return read(output['path'], output['sha256'], output['bytes']).decode('utf-8')

    verification = transcript('verify-signature')
    require(verification.replace('\r\n', '\n') == receipt['signatureVerification']
            and re.findall(r'certificate SHA-256 digest: ([a-f0-9]{64})', verification) == [signer]
            and 'Number of signers: 1' in verification.splitlines()
            and 'Verified using v3 scheme (APK Signature Scheme v3): true' in verification,
            'Official saved signature readback differs')
    badging = transcript('badging')
    require(f"package: name='{PACKAGE}' versionCode='1' versionName='{VERSION}'" in badging,
            'Official saved package readback differs')

    fields = {'version': '2', 'package': PACKAGE, 'signer': signer, 'apk': digest(apk), 'code': '1',
              'native': controller['sha256'], 'bytes': str(controller['bytes'])}
    data = ''.join(f'{key}={value}\n' for key, value in fields.items()).encode('ascii')
    require(0 < len(data) <= 2048 and data.count(b'\n') == 7, 'Profile format differs')
    return data, {
        'status': 'OFFLINE_HOST_PROFILE_CANDIDATE_ONLY', 'inputs': inputs, 'fields': fields,
        'targetSlot': {'path': DEVICE_SLOT, 'mode': '0440', 'uid': 0, 'gid': 1000, 'links': 1,
                       'kind': 'regular nonsymlink', 'oneReadPerProcess': True},
        'slotDisposition': 'UNKNOWN. No device inspection or write was performed. A separate approved admission '
                           'must prove the slot absent and publish without replacement. An exact existing match '
                           'needs no write. Unknown or different content refuses. No file edit re-arms a retained host.',
        'payload': {'sha256': digest(data), 'bytes': len(data)}, 'deviceEligible': False,
    }


def main():
    data, receipt = candidate()
    target = local('out/file-stage-preparation-app/protected-profile-candidate')
    target.mkdir()  # Never overwrite a previous PC candidate either.
    payload = target / 'candidate-profile.txt'
    with payload.open('xb') as stream:
        stream.write(data)
    require(payload.read_bytes() == data, 'Saved profile bytes differ')
    with (target / 'receipt.json').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    print((target / 'receipt.json').relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
