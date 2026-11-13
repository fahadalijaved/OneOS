"""Read back the exact isolated VIEW cohort and describe its unresolved teardown gates."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).absolute().parents[1]
OUT = ROOT / 'out/isolated-view-smoke-cohort'
APP_SDK = 'out/isolated-retained-view-app-build/r-acfd6f87'
HOST_SDK = 'out/retained-view-ingress-build/r-2dc4e293'
NATIVE = 'out/isolated-retained-view-controller/r-c88346bc'
RECEIPTS = {
    'app': ('out/isolated-retained-view-app-package/r-e2590d4cf9ba/receipt.json',
            'e37885f7a61e3adcfba7f079a340a4482f1b5519a08016f59fd0bbec2fb2532c'),
    'host': ('out/retained-view-ingress-host-package/r-698a94c6149a/receipt.json',
             'dd37ed39f6e5df34a505bbd6e6fcd9bcdb8201f912275eaae068a78d62ab4711'),
    'native': (NATIVE + '/receipt.json', 'ece49e0dd778ecd20f1c06a1cb54dc4ff94ca233e12823a8e583c485ad0e8e49'),
    'appSdk': (APP_SDK + '/receipt.json', 'd9a3bced953b300800a7573168211894feaf290f72f8bc4ed985dcd27a1f6441'),
    'hostSdk': (HOST_SDK + '/receipt.json', '621a3f712028582463e5cbd3500bfd49cf87c53910689b72d6596df49dd60f44'),
    'pairReadback': ('out/isolated-retained-view-pair/r-bbb18fa1/receipt.json',
                     'bf77aa07a33689b44d2ac02eee3f39131803576967a48ff2a44a290785a212b4'),
    'loopRelease': ('out/retained-view-loop-release/SOURCE-PROOF.json',
                    '4848b5400a3ceb91d2492ba74b2ad1839b72b9a9e80698be4247376c106cdd29'),
}
PACKAGE = 'com.fahadali.oneos.viewprep'
STAGE = '/data/local/tmp/oneos-viewprep'
LEASE_DIR = '/dev/oneos-retained-viewprep'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Repository-relative path required')
    path = ROOT / relative
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            pass
        else:
            require(not part.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Reparse path refused')
        if part == ROOT:
            break
    require(path.resolve().is_relative_to(ROOT.resolve()), 'Path outside repository')
    return path


def check():
    evidence = {}

    def retain(name, expected, size=None):
        path = local(name)
        require(path.is_file() and 0 < path.stat().st_size <= 2 * 1024 * 1024, 'Bounded saved input required')
        data = path.read_bytes()
        require(len(data) <= 2 * 1024 * 1024 and digest(data) == expected
                and (size is None or size == len(data)), 'Exact input pin differs: ' + name)
        evidence[name] = {'bytes': len(data), 'sha256': expected}
        return data

    receipts = {kind: json.loads(retain(*pin)) for kind, pin in RECEIPTS.items()}
    app, host, native = (receipts[key] for key in ('app', 'host', 'native'))
    pair = receipts['pairReadback']
    require(app['status'] == 'PASS_PC_ISOLATED_RETAINED_VIEW_APP_DEBUG_APK_ONLY'
            and host['status'] == 'PASS_PC_RETAINED_VIEW_INGRESS_HOST_DEBUG_APK_ONLY'
            and native['status'] == 'PASS_PC_ISOLATED_STAGE_CONTROLLER_STATIC_ONLY'
            and pair['status'] == 'PASS_PC_SIBLING_APP_HOST_CONTROLLER_COHORT_ONLY'
            and pair['candidateProfileSyntaxVerified'] and pair['actualCallbackConstantsMatch'],
            'Exact prior compatibility proof required')
    dexes = {}
    for kind, receipt, count in (('app', app, 30), ('host', host, 47)):
        spec = receipt['apk']
        retain(spec['path'], spec['sha256'], spec['bytes'])
        cert = receipt['freshDebugCertificate']
        retain(cert['path'], cert['sha256'], cert['bytes'])
        require('Verified using v3 scheme (APK Signature Scheme v3): true' in receipt['signatureVerification'],
                'Saved APK signer verification required')
        with zipfile.ZipFile(local(spec['path'])) as archive:
            require(archive.namelist() == list(receipt['payloadPins']) and archive.testzip() is None
                    and all(digest(archive.read(n)) == expected for n, expected in receipt['payloadPins'].items()),
                    'APK entry closure differs')
            dexes[kind] = archive.read('classes.dex')
        require(len(receipt['dex']['definitions']) == count and digest(dexes[kind]) == receipt['dex']['sha256'],
                'Exact saved DEX differs')
    require(set(app['payloadPins']) == {'AndroidManifest.xml', 'resources.arsc', 'classes.dex'}
            and app['freshDebugCertificate']['sha256'] != host['freshDebugCertificate']['sha256'],
            'Isolated app content or independent identity differs')
    controller = native['artifact']
    elf = retain(controller['path'], controller['sha256'], controller['bytes'])
    require(elf[:4] == b'\x7fELF' and not native['outputExecuted'] and not native['phoneActions']
            and pair['apk']['sha256'] == app['apk']['sha256']
            and pair['apk']['signerCertificateSha256'] == app['freshDebugCertificate']['sha256']
            and pair['hostApkSha256'] == host['apk']['sha256']
            and pair['isolatedControllerSha256'] == controller['sha256']
            and pair['distinctPackage'] == PACKAGE and pair['versionCode'] == 1, 'Pair and native pins differ')
    require(STAGE.encode() in dexes['app'] and STAGE.encode() in elf and LEASE_DIR.encode() in elf
            and b'cgroup.procs\0' in elf
            and all(token not in dexes['app'] for token in (b'/data/local/tmp/oneos/',
                    b'RetainedHandoffControllerSetup', b'ensureInstalled'))
            and all(token not in elf for token in (b'/data/local/tmp/oneos/', b'/dev/oneos-retained-view\0')),
            'Exact sibling selector or excluded legacy names differ')

    app_sdk = receipts['appSdk']
    host_sdk = receipts['hostSdk']
    anchors = {}

    def source(directory, name, expected, needles):
        path = directory + '/' + name
        lines = retain(path, expected).decode('utf-8').splitlines()
        result = {needle: [n for n, line in enumerate(lines, 1) if needle in line] for needle in needles}
        require(all(result.values()), 'Selected source anchor missing: ' + path)
        anchors[path] = result
        return '\n'.join(lines)

    for name, needles in {
        'HostBootstrapPermit.java': ('system/oneos-samsung-pin-host-bootstrap', '"request-v1"', '0750', '0440', 'CAPTURE_PIN_HOST_BOOTSTRAP_V1'),
        'HostRootLinkProfileV2.java': ('/data/system/oneos_retained_root_link_v2', '0440', '2097152L', 'key.equals("signer")'),
        'RetainedPinHostModule.java': ('param.isSystemServer()', 'chain.proceed()', 'HostBootstrapPermit.present()', '!= 1000',
                                     'HostRootLinkProfileV2.load()', 'rootLink.start()', 'onHotReloading'),
        'PreparedRetainedHostNativeBindingV2.java': ('getApkContentsSigners', 'getLongVersionCode', 'splitSourceDirs',
                                                  'RetainedHostControlProtocol.BEGIN', 'appTransportLost = true',
                                                  'appViewStatus', 'ACTION_PACKAGE_REMOVED'),
        'RetainedHostNativeControlV2.java': ('int appViewStatus()', 'boolean cleanupComplete()', 'STATUS_LOCAL_CLEANUP_OBSERVED'),
    }.items():
        source(HOST_SDK + '/host-src', name, host_sdk['cohorts']['host']['sources'][name], needles)
    service = source(APP_SDK + '/src', 'RetainedRootHostServiceV2.java',
                     app_sdk['stagedPins'][APP_SDK + '/src/RetainedRootHostServiceV2.java'],
                     ('Binder.getCallingUid()', 'Binder.getCallingPid()', 'startup = created', 'actual.start()',
                      'void retireDelivery()', '!viewPrepareIssued || viewStopIssued'))
    command = source(APP_SDK + '/src', 'RetainedRootOfferCommand.java',
                     app_sdk['stagedPins'][APP_SDK + '/src/RetainedRootOfferCommand.java'],
                     (STAGE, 'sha256sum', 'exec 3<', ' --host-control-v2'))
    require('ensureInstalled' not in service and '/data/local/tmp/oneos/' not in command, 'Unexpected installer or stock path')
    for name, needles in {
        'retained_root_handoff.c': ('place_self_root_cgroup(&owner,deadline)', '"cgroup.procs"', '"0\\n"',
                                    'pipe_read_frame(&owner', 'wait_request(int fd)', 'address.sun_path+1',
                                    'GVI_LOCAL_RELEASED_KERNEL_UNCONFIRMED) result=3'),
        'guest_private_view_inputs.c': (LEASE_DIR, 'mkdirat(p->guard_parent,"view-blocked"', 'rmdir(GVI_GUARD "/view-blocked")',
                                       'guard_zero_effect', 'return GVI_HOLD'),
        'guest_private_view_owner.c': ('"loop-control",O_RDWR', 'LOOP_CTL_GET_FREE', 'LOOP_CONFIGURE',
                                       'LO_FLAGS_READ_ONLY|LO_FLAGS_AUTOCLEAR', 'unshare(CLONE_NEWNS)',
                                       'GVO_LOCAL_RELEASED_KERNEL_UNCONFIRMED'),
    }.items():
        source(NATIVE + '/native-src', name, native['compiledSourcePins'][name], needles)

    marker = b'CAPTURE_PIN_HOST_BOOTSTRAP_V1\n'
    fields = {'version': '2', 'package': PACKAGE, 'signer': app['freshDebugCertificate']['sha256'],
              'apk': app['apk']['sha256'], 'code': '1', 'native': controller['sha256'],
              'bytes': str(controller['bytes'])}
    return {
        'schema': 'isolated-view-smoke-admission-readback/v1',
        'status': 'PC_COMPATIBILITY_BOUND_DEVICE_SMOKE_HELD',
        'scope': 'Non-loadable metadata only. No deployment, enablement, restart, launch or deletion authorization.',
        'artifacts': {'app': app['apk'], 'host': host['apk'], 'controller': controller},
        'bootPermit': {'directory': '/data/system/oneos-samsung-pin-host-bootstrap',
                       'directoryProfile': 'directory 0:1000 exact 0750',
                       'leaf': 'request-v1', 'leafProfile': 'regular nonsymlink 0:1000 exact 0440 nlink1',
                       'markerBytes': len(marker), 'markerSha256': digest(marker)},
        'protectedProfile': {'path': '/data/system/oneos_retained_root_link_v2',
                             'leafProfile': 'regular nonsymlink 0:1000 exact 0440 nlink1, 1..2048 bytes',
                             'admissionFieldsOnly': fields,
                             'parentReadback': 'Named /, /data and /data/system and held /data/system directory identities remain equal.'},
        'existingStageEvidenceOwner': 'Separate stage-stat and identity schema remains with build verification.',
        'separateStage': STAGE, 'separateLeaseDirectory': LEASE_DIR,
        'deploymentGates': [
            'Admit the exact single installed sibling APK as user 0 with the captured signer, version and whole-APK hash. The nonexported same-process V2 service must resolve to its UID.',
            'Exactly one reviewed host bootstrap module may be active in the Android/SystemServer scope. The new host shares the older guard package and has a distinct signer. An in-place update is unproved; overlapping bootstrap modules or automatic removal of any installed module are excluded.',
            'The fixed permit and profile slots are global. Absent or independently owned prior state must be established before any future approved change. Removing either file cannot retire the current process-lifetime hook or captured owner.',
            'Use the actual matching Samsung/SDK37/API102 source and genuine phase-1000 occurrence. The existing hook preserves original dispatch. File format, static ELF and PC signing do not prove Android visibility, execution, kernel policy, or authority.',
        ],
        'beginBeforeUi': [
            'Protected profile load starts the retained host binding once after the actual capture. After unlock it hashes and binds the sibling APK, then sends synchronous BEGIN.',
            'The genuine UID1000/positive PID BEGIN retains Startup before the app invokes su. The command checks the preprovisioned sibling stage/bin/executable, hashes the opened executable and execs that FD. No stock installer, asset copy or protected-file writer exists in this route.',
            'Before INIT or OFFER, the alternate controller sets up its own signals/session and parent-death policy and writes 0 newline to the verified root cgroup.procs for its own membership. Host cgroup policy and su authorization are outside the sibling stage.',
            'A random abstract Unix socket and native process/pidfd are acquired before UI preparation. Authenticated COMMIT retains direct SystemServer custody. App-side teardown and transport loss do not retire that native owner.',
        ],
        'teardownGates': [
            'Boot-only COMMIT may idle indefinitely. APP_VIEW_STOP requires a real app PREPARE occurrence. Status 8 can prove no selected VIEW dispatch while the earlier native control remains active. No normal app command retires this boot-only controller.',
            'Once PREPARE may have dispatched, only the same owner can drive STOP/drain. A queue reply is not cleanup. Exact status 7 is local cleanup after native state 6; it does not retire the boot hook or certify stock/global kernel return.',
            'PREPARE acquires a sibling reservation and uses host-global loop-control/LOOP_CTL_GET_FREE and a possible read-only AUTOCLEAR LOOP_CONFIGURE. Child mount work starts in a new private mount namespace; namespace isolation does not isolate kernel loop attachments.',
            'HOLD, loss, or actual local terminal 3 / VIEW 5 leaves kernel release unconfirmed. The original owner retains view-blocked on that path. No raw FD, loop reset, force-kill, marker removal, app uninstall or stock operation can substitute for owner evidence.',
            'Require a separately selected normal owner retirement path before arming even a boot-only smoke. Require an accepted disposition for potential loop/HOLD and concurrent stock-switch exclusion before any positive preparation smoke. Removing the permit/profile or disabling a module only changes future admission.',
        ],
        'admission': {'device': False, 'bootOnlyRollbackClosed': False, 'positiveViewRollbackClosed': False,
                      'singleActiveHostObserved': False, 'kernelReleaseProved': False},
        'sourceAnchors': anchors, 'inputPins': evidence,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='write the one non-loadable JSON manifest')
    args = parser.parse_args()
    result = check()
    if args.write:
        local(OUT.relative_to(ROOT)).mkdir(exist_ok=True)
        output = local((OUT / 'ADMISSION-AND-TEARDOWN.json').relative_to(ROOT))
        with output.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
        print(output.relative_to(ROOT).as_posix())
    else:
        print(json.dumps(result, indent=2))
