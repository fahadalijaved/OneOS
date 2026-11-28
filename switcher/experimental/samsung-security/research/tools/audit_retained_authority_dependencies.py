"""Recheck a bounded retained-owner proposal using frozen static evidence only."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PINS = {
    'construction-credentials': '3d726dfce77e607c08272c9f61e36ea8e0f71092ab82eac5c8a1f75d1e6d6f9b',
    'authority-bootstrap-users': '3be21cf44efd85ccd56ba75d4ec7cfe95070f34cdfba00dc5bc0efa8dd5f8b91',
    'authority-bootstrap-policy': 'df78da9e85e05dd1528d69f6a7a51742be94e6fdc886cbe0d717c12c3baff640',
    'authority-bootstrap-biometrics': 'b48f5fc8befb334ee41396fa356c29981e55dc560d8ad63eae2605af193f3d8a',
    'construction-storage-linkage': 'df20e5c08427b2e6abf5e08691fb6e5efcb3da178b734dd3e58e631b7ad361a6',
    'security-authority-quiescence': '352d9b2ddd3f003f49b6027e2f9bb13dbad57f09a0e8208c562e220847ff43bd',
    'authority-bootstrap-storage': '99fe38dc1c917aadf8e86bdd2591e421b6735b6dff84bd216813f868fb882cc1',
    'security-native-linkage': '72e89204fa34586219db73d18a876d24129f1be09070b19db2b7a0c087d4c7d7',
    'security-code-realm': '63ba98318e9c7c9b528c07208400e833e615a05091313f0779e3b8fe88063346',
    'construction-state': 'db1cf18b25eac47666ade696f0f539fdb5d2b771144e5aa891fd1591c1cca1dd',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    control_report = ROOT / 'docs/retained-authority-control.md'
    control_pin = '1d3cc146e87f1c709dedbfddca7fed539eec43e101785108ce548e2d7a691d97'
    if digest(control_report) != control_pin:
        raise ValueError('Reviewed peer control report changed')
    inherited = {}
    inputs = []
    for name, pin in PINS.items():
        path = ROOT / 'inventory' / (name + '.json')
        if digest(path) != pin:
            raise ValueError('Frozen inventory changed: ' + name)
        inherited[name] = json.loads(path.read_text())
        inputs.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': pin})
    bio_path = ROOT / inherited['authority-bootstrap-biometrics']['evidence']['methodReport']
    if digest(bio_path) != inherited['authority-bootstrap-biometrics']['evidence']['methodReportSha256']:
        raise ValueError('Biometrics method ledger changed')
    bio = json.loads(bio_path.read_text())['proofs']
    selected, bodies = [], {}
    cache = {}

    def collect(key, item):
        raw = item['raw']
        if raw not in cache:
            path = ROOT / raw
            if digest(path) != item['rawSha256']:
                raise ValueError('Frozen raw changed: ' + raw)
            lines = path.read_text().splitlines()
            if lines[0].startswith('META '):
                meta = json.loads(lines[0][5:])
                rows = []
                for line in lines:
                    if line.startswith('METHOD '):
                        signature, flags = line[7:].split(' FLAGS ')
                        body = {'owner': meta['descriptor'], 'signature': signature,
                                'accessFlags': int(flags), 'instructions': []}
                        rows.append({'record': 'method', 'body': body})
                    elif re.match(r'^[0-9a-f]{4} ', line):
                        pc, opcode, *tail = line.split(' ', 2)
                        reference = re.search(r'(L[^ ]+;->[^ ]+)', tail[0] if tail else '')
                        body['instructions'].append({'pc': int(pc, 16), 'opcode': opcode,
                                                     'reference': reference[1] if reference else ''})
                cache[raw] = rows
            else:
                cache[raw] = [json.loads(line) for line in lines]
        if digest(ROOT / raw) != item['rawSha256']:
            raise ValueError('Raw hash mismatch')
        descriptor = key.split(':L')[-1]
        if not descriptor.startswith('L'):
            descriptor = 'L' + descriptor
        owner, signature = descriptor.split('->', 1)
        matches = [(line, row['body']) for line, row in enumerate(cache[raw], 1)
                   if row.get('record') == 'method' and row['body']['owner'] == owner
                   and row['body']['signature'] == signature]
        if len(matches) != 1:
            raise ValueError('Exact body missing/duplicated: ' + key)
        line, body = matches[0]
        bodies[key] = body
        receipt_path = item.get('receipt')
        if receipt_path is None and raw.endswith('.jsonl'):
            candidate = ROOT / 'out/tooling' / Path(raw).stem / 'receipt.json'
            if candidate.exists():
                receipt_path = candidate.relative_to(ROOT).as_posix()
        proof = item
        if receipt_path:
            receipt = json.loads((ROOT / receipt_path).read_text())
            if receipt['rawSha256'] != item['rawSha256']:
                raise ValueError('Receipt/raw mismatch')
            proof, = [p for p in receipt['selectedMethodProofs'] if p['owner'] == owner and p['signature'] == signature]
        selected.append({'key': key, 'raw': raw, 'rawSha256': item['rawSha256'],
                         'selectionOrdinal': line, 'bodySha256': proof.get('normalizedBodySha256', proof.get('bodySha256')),
                         'physicalDex': proof.get('physicalDex'), 'logicalHeaderOffset': proof.get('logicalHeaderOffset'),
                         'receipt': receipt_path, 'receiptSha256': digest(ROOT / receipt_path) if receipt_path else None,
                         'accessFlags': body['accessFlags']})

    q = inherited['security-authority-quiescence']['methodProofs']
    qkeys = [
        'Lcom/android/server/locksettings/LockSettingsService;-><init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V',
        'Lcom/android/server/locksettings/LockSettingsService;->unlockUser(I)V',
        'Lcom/android/server/locksettings/LockSettingsStrongAuth;-><init>(Landroid/content/Context;Lcom/android/server/locksettings/LockSettingsStrongAuth$Injector;)V',
        'Lcom/android/server/locksettings/LockSettingsStrongAuth$StrongAuthTimeoutAlarmListener;->onAlarm()V',
        'Lcom/android/server/locksettings/SyntheticPasswordManager;->unlockLskfBasedProtector(Landroid/service/gatekeeper/IGateKeeperService;JLcom/android/internal/widget/LockscreenCredential;ILcom/android/internal/widget/ICheckCredentialProgressCallback;)Lcom/android/server/locksettings/SyntheticPasswordManager$AuthenticationResult;',
    ]
    for key in qkeys:
        item, = [item for item in q if item['method'] == key]
        collect(key, item)
    # These two already exist in the same pinned complete LSS receipt; no new DEX query.
    lss_raw = next(item for item in q if item['method'] == qkeys[0])
    for signature in ['checkWritePermission()V', 'getGateKeeperService()Landroid/service/gatekeeper/IGateKeeperService;']:
        collect('Lcom/android/server/locksettings/LockSettingsService;->' + signature, lss_raw)
    u = inherited['authority-bootstrap-users']['methodProofs']
    user_keys = [
        'samsung-services:Lcom/android/server/pm/UserManagerService$LocalService;->setUserState(II)V',
        'samsung-services:Lcom/android/server/pm/UserManagerService$LocalService;->removeUserState(I)V',
        'samsung-services:Lcom/android/server/am/UserController;->finishUserBoot(Lcom/android/server/am/UserState;Lcom/android/server/am/ActivityManagerService$10;)V',
        'samsung-services:Lcom/android/server/am/UserController;->finishUserStopped(Lcom/android/server/am/UserState;Z)V',
        'samsung-services:Lcom/android/server/supervision/SupervisionService;-><init>(Lcom/android/server/supervision/SupervisionService$Injector;)V',
    ]
    for key in user_keys:
        collect(key, u[key])
    bio_keys = [
        'Lcom/android/server/biometrics/log/BiometricContextProvider;-><init>(Landroid/content/Context;Landroid/view/WindowManager;Lcom/android/internal/statusbar/IStatusBarService;Landroid/os/Handler;Lcom/android/server/biometrics/sensors/AuthSessionCoordinator;)V',
        'Lcom/android/server/biometrics/sensors/SensorList;->addSensor(ILjava/lang/Object;ILandroid/app/SynchronousUserSwitchObserver;)V',
        'samsung:com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider->getHalInstance()Landroid/hardware/biometrics/fingerprint/IFingerprint;',
        'Lcom/android/server/biometrics/SemBiometricSysUiManager;->bind()V',
    ]
    for key in bio_keys:
        item, = [item for item in bio if item['key'] == key]
        canonical = key if key.startswith('L') else 'L' + key.split(':', 1)[1].replace('->', ';->', 1).replace('.', '/')
        collect(canonical, item)
    s = inherited['construction-storage-linkage']['evidence']
    store, = [item for item in s if item.get('input') == 'samsung-services' and item.get('class') == 'com.android.server.StorageManagerService' and any(p.get('signature') == 'connectVold$1()V' for p in item.get('methodProofs', []))]
    collect('Lcom/android/server/StorageManagerService;->connectVold$1()V', store)
    assertions = []

    def edge(key, pc, suffix):
        instruction, = [instruction for instruction in bodies[key]['instructions'] if instruction['pc'] == pc]
        if not instruction.get('reference', '').endswith(suffix):
            raise ValueError((key, pc, suffix))
        assertions.append({'method': key, 'pcDecimal': pc, 'referenceSuffix': suffix})

    for pc, suffix in [(424, '->mHandler:Landroid/os/Handler;'), (438, '->mStrongAuth:Lcom/android/server/locksettings/LockSettingsStrongAuth;'), (444, '->mActivityManager:Landroid/app/IActivityManager;'), (597, '->mStorage:Lcom/android/server/locksettings/LockSettingsStorage;'), (610, '->mNotificationManager:Landroid/app/NotificationManager;'), (623, '->mUserManager:Landroid/os/UserManager;'), (641, '->mStorageManager:Landroid/os/storage/IStorageManager;'), (651, '->mStorageManagerInternal:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;'), (661, '->mSupervisionManagerInternal:Landroid/app/supervision/SupervisionManagerInternal;'), (755, '->mSpManager:Lcom/android/server/locksettings/SyntheticPasswordManager;')]:
        edge(qkeys[0], pc, suffix)
    edge('Lcom/android/server/locksettings/LockSettingsService;->checkWritePermission()V', 8, '->enforceCallingOrSelfPermission(Ljava/lang/String;Ljava/lang/String;)V')
    edge('Lcom/android/server/locksettings/LockSettingsService;->getGateKeeperService()Landroid/service/gatekeeper/IGateKeeperService;', 1, '->mGateKeeperService:Landroid/service/gatekeeper/IGateKeeperService;')
    edge('Lcom/android/server/locksettings/LockSettingsService;->getGateKeeperService()Landroid/service/gatekeeper/IGateKeeperService;', 10, '->waitForService(Ljava/lang/String;)Landroid/os/IBinder;')
    edge('Lcom/android/server/locksettings/LockSettingsService;->getGateKeeperService()Landroid/service/gatekeeper/IGateKeeperService;', 28, '->linkToDeath(Landroid/os/IBinder$DeathRecipient;I)V')
    edge('Lcom/android/server/locksettings/LockSettingsService;->getGateKeeperService()Landroid/service/gatekeeper/IGateKeeperService;', 47, '->mGateKeeperService:Landroid/service/gatekeeper/IGateKeeperService;')
    edge(qkeys[1], 42, '->unlockUser2(ILandroid/os/IProgressListener;)Z')
    edge(user_keys[2], 75, '->setUserState(II)V')
    edge(user_keys[3], 194, '->removeUserState(I)V')
    # Preserve exact selected method references for reconnect/callback/physical UI review.
    relevant = ['getService(', 'waitForService(', 'linkToDeath(', 'registerUserSwitchObserver(', 'registerSessionListener(', 'registerBiometricContextListener(', 'bindService(', 'mVold:', 'mDaemon:', 'getAliveUsers(', 'scheduleInternalCleanup(', 'scheduleLoadAuthenticatorIds(']
    boundary_sites = []
    for key, body in bodies.items():
        for instruction in body['instructions']:
            ref = instruction.get('reference', '')
            if any(term in ref for term in relevant):
                boundary_sites.append({'method': key, 'pcDecimal': instruction['pc'], 'reference': ref})
    result = {'schema': 'retained-authority-dependencies/v1', 'status': 'SOURCE_PROPOSAL_ONLY_NO_ARCHITECTURE_PIVOT', 'inheritedInventories': inputs,
              'peerControlReport': {'path': control_report.relative_to(ROOT).as_posix(), 'sha256': control_pin, 'jointCritique': 'control source reviewed; preserved parent-death uncertainty, original whole-thread view and Binder namespace/driver distinction; no reciprocal inventory pin'},
              'selectedReusedBodies': selected, 'selectedBodyCount': len(selected), 'newBodies': 0, 'assertions': assertions, 'assertionCount': len(assertions), 'boundarySites': boundary_sites,
              'observedRuntimeInstances': False, 'sourceInterpretation': 'These bodies identify original owner relationships, not proof that any live current instance was retained.',
              'minimumProposedTopology': ['Keep original initialized Samsung system_server and required live policy/user/storage/biometric/native graph; no second security constructor/writer', 'Preserve whole-thread original state/code/mount/property/endpoint view before switch preparation; retaining PID or copied caches is insufficient', 'Guest-protocol frontend in that same original process calls the actual original Samsung Stub/backend directly; preserve native Binder caller and original permission checks', 'Separate guest framework service publications/routes from host canonical internal endpoints; admit real user/package/UID/policy mapping and required guest local proxies', 'One physical/native/CE/enrollment writer and genuine crossOS active lifecycle/events; exact hostUI/display/power producer cuts, watchdog/zygote/return control and native completion remain open'],
              'advantagesOverCold': ['No rerun of original eager credential/serial cleanup, UMS/DPMS policy load/migration or biometric provider metadata construction', 'Already selected canonical class/local-service/JNI/resource owners are retained rather than reconstructed, if whole runtime view survives', 'Existing in-flight native/deferred work stays with original owner rather than assumed transferred'],
              'disqualifiers': ['Cannot retain parent/zygote/watchdog/service lifetime without restarting original authority', 'Cannot preserve original physical state/code/native/property view while guest mounts/properties change', 'Cannot preserve genuine policy/user/packageUID mapping or separate conflicting namespace/physicalUI/native owners', 'Required live producers cannot remain or be source-preservingly transferred with exclusive writer and real completion', 'Return/reboot/native uncertainty cannot be owned without competing writer or default/fake policy'],
              'runtimeImplemented': False, 'endpointPublished': False, 'oemExecuted': False, 'phoneChanged': False, 'toolSha256': digest(__file__)}
    out = ROOT / 'out/retained-authority-dependencies'
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / 'inventory/retained-authority-dependencies.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'reusedBodies': len(selected), 'assertions': len(assertions), 'newBodies': 0, 'runtimeVerified': False}))


if __name__ == '__main__':
    main()
