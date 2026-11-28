"""Static retained-user/guest-package lifecycle cut; no OEM or phone execution."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/retained-guest-user-lifecycle'
ARCHIVES = {
    'guest': ('firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
    'samsung': ('firmware/samsung/runtime-20261104/services.jar', 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
    'stage': (ROOT / 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/services_patched.jar',
              'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'),
    'guest-framework': ('firmware/donor/extracted/system/framework/framework.jar',
                        'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'stage-framework': (ROOT / 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/framework_patched.jar',
                        '5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def query(side, cls, methods, label):
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'queries.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    old = next((row for row in rows if row['label'] == label), None)
    if old:
        assert old['side'] == side and old['class'] == cls and set(old['methods']) == set(methods), 'Saved selector changed'
        return json.loads((ROOT / old['receipt']).read_text())
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    archive, pin = ARCHIVES[side]
    result = read(ROOT.parent / archive, pin, class_name=cls, methods=methods,
                  stream='retained-guest-user-lifecycle')
    rows.append({'side': side, 'class': cls, 'methods': methods, 'label': label, 'receipt': result['receipt']})
    path.write_text(json.dumps(rows, indent=2) + '\n')
    print(label, result['receipt'], flush=True)
    return result


def capture():
    query('guest', 'com.android.server.pm.UserManagerService',
          ['onBeforeStartUser(I)V', 'onBeforeUnlockUser(I)V'], 'guest-before-user')
    query('samsung', 'com.android.server.trust.TrustManagerService',
          ['refreshDeviceLockedForUser(II)V', 'setDeviceLockedForUser(IZ)V'], 'samsung-keyguard-owner')
    query('guest', 'com.android.server.pm.UserDataPreparer',
          ['prepareUserDataLI(Ljava/lang/String;Landroid/content/pm/UserInfo;IZ)V'], 'guest-data-prepare-inner')
    query('guest', 'com.android.server.pm.PackageManagerInternalBase',
          ['reconcileAppsData(IIZ)V'], 'guest-package-base')
    query('guest', 'com.android.server.pm.AppDataHelper',
          ['reconcileAppsData(IIZ)V'], 'guest-appdata')
    query('guest', 'com.android.server.StorageManagerService',
          ['prepareUserStorageInternal(Ljava/lang/String;II)V'], 'guest-storage-prepare')
    query('guest', 'com.android.server.pm.AppDataHelper',
          ['reconcileAppsDataLI(Ljava/lang/String;IIZ)V'], 'guest-appdata-inner')
    query('guest', 'com.android.server.pm.UserDataPreparer', [
          'getDataUserDeDirectory(Ljava/lang/String;I)Ljava/io/File;',
          'getDataUserCeDirectory(Ljava/lang/String;I)Ljava/io/File;',
          'getDataSystemDeDirectory(I)Ljava/io/File;',
          'getDataSystemCeDirectory(I)Ljava/io/File;'], 'guest-data-paths')
    for cls, prefixes, label in [
        ('com.android.server.pm.UserDataPreparer', ('prepareUserData(',), 'guest-data-prepare'),
        ('com.android.server.pm.PackageManagerService$PackageManagerInternalImpl', ('reconcileAppsData(',), 'guest-package-prepare'),
        ('com.android.server.trust.TrustManagerService', ('setDeviceLockedForUser(', 'refreshDeviceLockedForUser(', 'notifyKeystoreOfDeviceLockState('), 'guest-screen-lock'),
    ]:
        declaration = query('guest', cls, [], label + '-declaration')
        assert len(declaration['selectedClassDeclarations']) == 1
        methods = [method['signature'] for method in declaration['selectedClassDeclarations'][0]['methods']
                   if method['signature'].startswith(prefixes)]
        assert len(methods) <= 8
        if methods:
            query('guest', cls, methods, label)


def capture_stage():
    acquisition = ROOT / 'out/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/acquisition.json'
    assert sha(acquisition) == 'ad6b1d7aaa79a17f2745c52a347a660b1d70bef7956a4354f6feb997417e0d23'
    assert sha(ROOT / 'inventory/samsung-user-registry-lifecycle.json') == 'f63158e824cc30ee2797c9a9e588728d247a94ab533cd1e4d005194144b0946b'
    proofs, _, _ = evidence()
    groups = {}
    for key in proofs:
        side, name = key.split(':', 1)
        if side not in ('guest', 'coloros-services'):
            continue
        owner, signature = name.split('->', 1)
        groups.setdefault(owner, set()).add(signature)
    for owner, methods in groups.items():
        ledger = json.loads((WORK / 'queries.json').read_text())
        def descriptor(name):
            return name if name.startswith('L') and name.endswith(';') else 'L' + name.replace('.', '/') + ';'
        covered = {m for q in ledger if q['side'] == 'stage' and descriptor(q['class']) == owner for m in q['methods']}
        missing = sorted(methods - covered)
        if missing:
            stamp = hashlib.sha256(json.dumps(missing).encode()).hexdigest()[:8]
            query('stage', owner, missing, 'stage-add-' + owner.split('/')[-1].rstrip(';') + '-' + stamp)
    for side in ['guest', 'stage']:
        cls = 'com.android.server.pm.Installer'
        declaration = query(side, cls, [], side + '-installer-declaration')
        methods = [m['signature'] for m in declaration['selectedClassDeclarations'][0]['methods']
                   if m['signature'].startswith(('createUserData(', 'destroyUserData('))]
        assert 1 <= len(methods) <= 4
        query(side, cls, methods, side + '-installer-user-data')
        query(side, cls, ['checkBeforeRemote()Z', 'connect()V'], side + '-installer-routing')
        query(side, 'com.android.server.pm.UserDataPreparer', [
              'enforceSerialNumber(Ljava/io/File;I)V',
              'destroyUserDataLI(Ljava/lang/String;II)V'], side + '-data-serial-cleanup')
        query(side, 'com.android.server.StorageManagerService', ['isCeStorageUnlocked(I)Z'], side + '-ce-storage-status')
        query(side, 'com.android.server.StorageManagerService$StorageManagerInternalImpl',
              ['isCeStoragePrepared(I)Z'], side + '-ce-prepared-status')
    for side in ['guest-framework', 'stage-framework']:
        query(side, 'android.os.storage.StorageManager', ['isCeStorageUnlocked(I)Z'], side + '-ce-query')
        query(side, 'android.security.KeyStoreAuthorization', [
              'onDeviceLocked(I[JZ)I', 'onDeviceUnlocked(I[B)I'], side + '-keyguard-keystore')
    bridge = query('stage', 'com.android.server.pm.OneOSInstalldProxy', [], 'stage-installd-proxy-declaration')
    methods = [m['signature'] for m in bridge['selectedClassDeclarations'][0]['methods']
               if m['signature'].startswith(('asInterface(', 'createUserData(', 'invoke('))]
    assert 1 <= len(methods) <= 4
    query('stage', 'com.android.server.pm.OneOSInstalldProxy', methods, 'stage-installd-proxy')
    query('stage', 'com.android.server.pm.OneOSInstalldProxy',
          ['<init>(Landroid/os/IBinder;)V', 'asBinder()Landroid/os/IBinder;'], 'stage-installd-proxy-owner')


def evidence():
    proofs = {}
    queries = json.loads((WORK / 'queries.json').read_text())
    receipts = {}
    for item in queries:
        r = json.loads((ROOT / item['receipt']).read_text())
        assert r['archiveSha256'] == ARCHIVES[item['side']][1]
        assert r['readerExitCode'] == 0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
        assert not r['oemCodeExecuted'] and not r['androidExecuted']
        assert sha(ROOT / r['raw']) == r['rawSha256']
        receipts[item['receipt']] = sha(ROOT / item['receipt'])
        for p in r['selectedMethodProofs']:
            proofs[item['side'] + ':' + p['owner'] + '->' + p['signature']] = {
                'bodySha256': p['normalizedBodySha256'], 'raw': r['raw'], 'rawSha256': r['rawSha256'],
                'receipt': item['receipt'], 'physicalDex': p['physicalDex'], 'logicalHeaderOffset': p['logicalHeaderOffset']}
    previous = json.loads((ROOT / 'inventory/samsung-user-registry-lifecycle.json').read_text())
    for key, proof in previous['methodProofs'].items():
        if key.startswith('coloros-services:Lcom/android/server/am/UserController;') and any(x in key for x in [
                '->finishUserUnlocking(', '->lambda$finishUserUnlocking$1(', '->finishUserUnlocked(',
                '->finishUserStopped(', '->lambda$dispatchUserLocking$14(', '->dispatchUserLocking(',
                '->continueStartUserInternal(']):
            proofs[key] = proof
        if key.startswith('coloros-services:Lcom/android/server/am/UserController$Injector;'):
            proofs[key] = proof
    trust = json.loads((ROOT / 'inventory/strongauth-callback-adapter.json').read_text())
    for key, proof in trust['methodProofs'].items():
        if 'TrustManagerService;->notifyKeystoreOfDeviceLockState(IZ)V' in key:
            proofs['samsung:' + key.split(':', 1)[1]] = proof
    for receipt_path, wanted in [
        ('out/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0/receipt.json', ['unlockCeStorage(']),
        ('out/tooling/20261105T143847134808Z-6847f9efcbf341b98c8961485613a152/receipt.json', ['prepareUserStorage(', 'markCeStoragePrepared(']),
    ]:
        r = json.loads((ROOT / receipt_path).read_text())
        assert r['readerExitCode'] == 0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
        side = 'samsung' if r['archiveSha256'] == ARCHIVES['samsung'][1] else 'guest'
        assert r['archiveSha256'] == ARCHIVES[side][1]
        receipts[receipt_path] = sha(ROOT / receipt_path)
        for p in r['selectedMethodProofs']:
            if not p['signature'].startswith(tuple(wanted)):
                continue
            proofs[side + ':' + p['owner'] + '->' + p['signature']] = {
                'bodySha256': p['normalizedBodySha256'], 'raw': r['raw'], 'rawSha256': r['rawSha256'],
                'receipt': receipt_path, 'physicalDex': p['physicalDex'], 'logicalHeaderOffset': p['logicalHeaderOffset']}
    peer_guards = [
        ('out/tooling/20261106T022314441351Z-578d199db5a94df491e5fcaf1d2215ab/receipt.json',
         'Lcom/android/server/locksettings/LockSettingsService;', 'lockUser(I)V'),
        ('out/tooling/20261106T022315525769Z-1760c7624e1c44138846c43ca7d7464b/receipt.json',
         'Lcom/android/server/locksettings/LockSettingsService$LocalService;', 'lockUser(I)V'),
        ('out/tooling/20261106T022322469704Z-91ab83e71fcd4c36ba70f0813489e050/receipt.json',
         'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;', 'unlockCeStorage(I[B)V'),
        ('out/tooling/20261106T022323677638Z-d2e1ff3050ed44de89c6eb813247664a/receipt.json',
         'Lcom/android/server/StorageManagerService;', 'lockCeStorage(I)V'),
    ]
    for receipt_path, owner, method in peer_guards:
        r = json.loads((ROOT / receipt_path).read_text())
        assert r['archiveSha256'] == ARCHIVES['stage'][1] and r['readerExitCode'] == 0
        assert r['archiveAndToolPinsVerifiedBeforeAndAfter'] and not r['oemCodeExecuted']
        p = next(p for p in r['selectedMethodProofs'] if p['owner'] == owner and p['signature'] == method)
        proofs['stage:' + owner + '->' + method] = {
            'bodySha256': p['normalizedBodySha256'], 'raw': r['raw'], 'rawSha256': r['rawSha256'],
            'receipt': receipt_path, 'physicalDex': p['physicalDex'], 'logicalHeaderOffset': p['logicalHeaderOffset'],
            'reusedPeerGuardRead': True}
    bodies = {}
    cache = {}
    for key, proof in proofs.items():
        assert sha(ROOT / proof['raw']) == proof['rawSha256']
        if proof['raw'] not in cache:
            cache[proof['raw']] = [json.loads(line) for line in (ROOT / proof['raw']).read_text().splitlines()]
        row = next(row for row in cache[proof['raw']] if row.get('record') == 'method' and
                   row['body']['owner'] + '->' + row['body']['signature'] == key.split(':', 1)[1])
        assert row['normalizedBodySha256'] == proof['bodySha256']
        bodies[key] = row['body']
        if 'receipt' in proof:
            receipts[proof['receipt']] = sha(ROOT / proof['receipt'])
    return proofs, bodies, receipts


def report():
    proofs, bodies, receipts = evidence()
    checks = []
    def check(label, part, pc, **wanted):
        keys = [key for key in bodies if part in key]
        assert len(keys) == 1, (part, keys)
        key = keys[0]
        ins = next(i for i in bodies[key]['instructions'] if i['pc'] == pc)
        for field, value in wanted.items():
            assert value in ins[field] if field == 'reference' else ins[field] == value, (label, ins)
        checks.append({'id': label, 'method': key, 'pc': pc, 'observed': {k: ins[k] for k in wanted}})
    u = 'guest:Lcom/android/server/pm/UserManagerService;->'
    p = 'guest:Lcom/android/server/pm/UserDataPreparer;->'
    g = 'guest:Lcom/android/server/trust/TrustManagerService;->'
    h = 'samsung:Lcom/android/server/trust/TrustManagerService;->'
    c = 'coloros-services:Lcom/android/server/am/UserController;->'
    check('guestBeforeStart own app-data preparation', u + 'onBeforeStartUser(', 63, reference='UserDataPreparer;->prepareUserData')
    check('guestBeforeStart own package reconciliation', u + 'onBeforeStartUser(', 85, reference='reconcileAppsData(IIZ)V')
    check('guestBeforeUnlock original vendor storage preparation', u + 'onBeforeUnlockUser(', 13, reference='normalizeExternalStorageData(I)V')
    check('guestBeforeUnlock data preparation', u + 'onBeforeUnlockUser(', 57, reference='UserDataPreparer;->prepareUserData')
    check('guestBeforeUnlock own prepared cache', u + 'onBeforeUnlockUser(', 67, reference='markCeStoragePrepared(I)V')
    check('guestBeforeUnlock own package reconciliation', u + 'onBeforeUnlockUser(', 97, reference='reconcileAppsData(IIZ)V')
    check('actual user ID used', p + 'prepareUserDataLI(', 0, reference='UserInfo;->id:I')
    check('actual serial used', p + 'prepareUserDataLI(', 2, reference='UserInfo;->serialNumber:I')
    check('new-user recovery guard actual metadata', p + 'prepareUserDataLI(', 4, reference='UserInfo;->lastLoggedInTime:J')
    check('actual guest storage preparation', p + 'prepareUserDataLI(', 44, reference='StorageManagerInternal;->prepareUserStorage')
    for pc in [55, 70, 81, 96]:
        check('actual serial enforcement ' + str(pc), p + 'prepareUserDataLI(', pc, reference='enforceSerialNumber')
    check('actual Installer user-data creation', p + 'prepareUserDataLI(', 101, reference='Installer;->createUserData')
    check('global CE available property write', p + 'prepareUserDataLI(', 167, reference='SystemProperties;->set')
    check('only new-user recovery destroys', p + 'prepareUserDataLI(', 176, opcode='IF_EQZ', targetPc=222)
    check('new-user recovery real destroy', p + 'prepareUserDataLI(', 218, reference='destroyUserDataLI')
    check('one allowed retry guard', p + 'prepareUserDataLI(', 262, opcode='IF_EQZ', targetPc=270)
    check('retry real data preparation', p + 'prepareUserDataLI(', 266, reference='prepareUserDataLI')
    check('terminal wipe new-user guard', p + 'prepareUserDataLI(', 293, opcode='IF_EQZ', targetPc=306)
    check('terminal wipe system-user guard', p + 'prepareUserDataLI(', 295, opcode='IF_NEZ', targetPc=306)
    check('terminal wipe internal-volume guard', p + 'prepareUserDataLI(', 297, opcode='IF_NEZ', targetPc=306)
    check('source terminal recovery wipe call never executed here', p + 'prepareUserDataLI(', 303, reference='rebootPromptAndWipeUserData')
    for method, target in [('getDataUserDeDirectory(', 'getDataUserDeDirectory'),
                           ('getDataUserCeDirectory(', 'getDataUserCeDirectory'),
                           ('getDataSystemDeDirectory(', 'getDataSystemDeDirectory'),
                           ('getDataSystemCeDirectory(', 'getDataSystemCeDirectory')]:
        check('real Environment path ' + target, p + method, 0, reference='Environment;->' + target)
    check('guestSMS actual vold call has no prior already-unlocked guard', 'guest:Lcom/android/server/StorageManagerService;->prepareUserStorageInternal(', 2, reference='IVold;->prepareUserStorage')
    check('guestSMS swallowed error uses actual UMI policy', 'guest:Lcom/android/server/StorageManagerService;->prepareUserStorageInternal(', 70, reference='shouldIgnorePrepareStorageErrors')
    check('guestSMS can return after logged ignored error', 'guest:Lcom/android/server/StorageManagerService;->prepareUserStorageInternal(', 105, opcode='RETURN_VOID')
    check('real PMInternal package helper', 'guest:Lcom/android/server/pm/PackageManagerInternalBase;->reconcileAppsData(', 4, reference='AppDataHelper;->reconcileAppsData')
    check('real guest PMS install lock', 'guest:Lcom/android/server/pm/AppDataHelper;->reconcileAppsData(', 48, reference='PackageManagerService;->mInstallLock:')
    check('real per-volume package preparation', 'guest:Lcom/android/server/pm/AppDataHelper;->reconcileAppsData(', 54, reference='reconcileAppsDataLI')
    check('package inner selected next original method', 'guest:Lcom/android/server/pm/AppDataHelper;->reconcileAppsDataLI(', 6, reference='reconcileAppsDataLI(Ljava/lang/String;IIZZ)Ljava/util/List;')
    check('guest keyguard truth from real WM', g + 'refreshDeviceLockedForUser(II)', 192, reference='IWindowManager;->isKeyguardLocked()Z')
    check('guest screen lock state is separate map', g + 'setDeviceLockedForUser(', 15, reference='SparseBooleanArray;->put')
    check('guest keyguard notifies Keystore', g + 'setDeviceLockedForUser(', 24, reference='notifyKeystoreOfDeviceLockState')
    check('guest locked keys policy', g + 'notifyKeystoreOfDeviceLockState(', 26, reference='KeyStoreAuthorization;->onDeviceLocked')
    check('guest unlock notification distinct from CE', g + 'notifyKeystoreOfDeviceLockState(', 33, reference='KeyStoreAuthorization;->onDeviceUnlocked')
    check('host keyguard truth must be admitted WM view', h + 'refreshDeviceLockedForUser(II)', 150, reference='IWindowManager;->isKeyguardLocked()Z')
    check('host actual DualDAR policy retained', h + 'setDeviceLockedForUser(', 71, reference='handleDualDARDeviceLockedChangedForUser')
    check('host actual Keystore state notification retained', h + 'setDeviceLockedForUser(', 141, reference='notifyKeystoreOfDeviceLockState')
    check('host locked-key policy retained', h + 'notifyKeystoreOfDeviceLockState(', 190, reference='KeyStoreAuthorization;->onDeviceLocked')
    check('host source unlocked-key notification retained', h + 'notifyKeystoreOfDeviceLockState(', 196, reference='KeyStoreAuthorization;->onDeviceUnlocked')
    lss = 'samsung:Lcom/android/server/locksettings/LockSettingsService;->unlockCeStorage('
    check('genuine already-unlocked CE query', lss, 7, reference='isCeStorageUnlocked(I)Z')
    check('only actual locked branch continues', lss, 14, opcode='IF_EQZ', targetPc=30)
    check('genuine already-done CE return', lss, 29, opcode='RETURN_VOID')
    check('guest state2 only after beforeUnlock', c + 'lambda$finishUserUnlocking$1(', 77, reference='UserManagerInternal;->setUserState')
    check('guest unlock worker continuation', c + 'lambda$finishUserUnlocking$1(', 114, reference='Message;->sendToTarget')
    check('guest actual physical key lock precedes callback', c + 'lambda$dispatchUserLocking$14(', 20, reference='LockSettingsInternal;->lockUser(I)V')
    check('guest keyEvicted callback is physical operation outcome', c + 'lambda$dispatchUserLocking$14(', 39, reference='KeyEvictedCallback;->keyEvicted(I)V')
    # Effective acquired code: its compatibility guards must not become authority.
    stage_sms = 'stage:Lcom/android/server/StorageManagerService;->'
    stage_prep = 'stage:Lcom/android/server/pm/UserDataPreparer;->'
    stage_installer = 'stage:Lcom/android/server/pm/Installer;->'
    bridge = 'stage:Lcom/android/server/pm/OneOSInstalldProxy;->'
    check('staged CE getter forces true at entry', stage_sms + 'isCeStorageUnlocked(', 0, opcode='CONST_4', literal=1)
    check('staged CE getter returns before old cache', stage_sms + 'isCeStorageUnlocked(', 1, opcode='RETURN')
    check('staged userdata destroy returns before old cleanup', stage_prep + 'destroyUserDataLI(', 0, opcode='RETURN_VOID')
    check('staged terminal recovery now OneOS log', stage_prep + 'prepareUserDataLI(', 303, reference='string=OneOS')
    check('staged terminal recovery logger', stage_prep + 'prepareUserDataLI(', 305, reference='Slog;->w')
    check('staged serial check still sets missing serial', stage_prep + 'enforceSerialNumber(', 69, reference='setSerialNumber')
    check('staged real serial mismatch still throws', stage_prep + 'enforceSerialNumber(', 134, opcode='THROW')
    check('staged createUserData retains actual remote call', stage_installer + 'createUserData(', 9, reference='IInstalld;->createUserData')
    check('staged Installer connects canonical installd', stage_installer + 'connect(', 0, reference='string=installd')
    check('staged Installer uses existing OneOS protocol bridge', stage_installer + 'connect(', 23, reference='OneOSInstalldProxy;->asInterface')
    check('staged Installer caches bridge then latch', stage_installer + 'connect(', 27, reference='mInstalld:')
    check('staged Installer ready latch not native completion', stage_installer + 'connect(', 31, reference='CountDownLatch;->countDown')
    check('Installer isolated branch false skip', stage_installer + 'checkBeforeRemote(', 78, literal=0)
    check('Installer real wait deadline', stage_installer + 'checkBeforeRemote(', 84, literal=10000)
    check('Installer timeout throws', stage_installer + 'checkBeforeRemote(', 101, opcode='THROW')
    check('Installer interrupted branch can continue true', stage_installer + 'checkBeforeRemote(', 103, literal=1)
    check('existing OneOS proxy retains actual supplied Binder', bridge + '<init>(', 3, reference='mRemote:')
    check('existing OneOS proxy actual token', bridge + 'createUserData(', 12, reference='string=android.os.IInstalld')
    check('existing OneOS proxy code1', bridge + 'createUserData(', 31, literal=1)
    check('existing OneOS proxy synchronous flags0', bridge + 'createUserData(', 32, literal=0)
    check('existing OneOS proxy native Binder transact', bridge + 'createUserData(', 33, reference='IBinder;->transact')
    check('existing OneOS proxy real exception reply', bridge + 'createUserData(', 37, reference='Parcel;->readException')
    check('staged locking no native call at old dispatch site', stage_sms + 'lockCeStorage(', 59, opcode='NOP')
    check('staged locking still mutates guest unlocked cache', stage_sms + 'lockCeStorage(', 65, reference='WatchedUnlockedUsers;->remove')
    check('staged unlocking skips actual native call', 'stage:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;->unlockCeStorage(', 12, opcode='GOTO', targetPc=17)
    check('staged unlocking still appends guest unlocked cache', 'stage:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;->unlockCeStorage(', 28, reference='WatchedUnlockedUsers;->append')
    check('staged local lock still invokes IStorageManager', 'stage:Lcom/android/server/locksettings/LockSettingsService;->lockUser(', 30, reference='IStorageManager;->lockCeStorage')
    check('staged local lock retains conditional Keystore path', 'stage:Lcom/android/server/locksettings/LockSettingsService;->lockUser(', 40, reference='LockSettingsService;->lockKeystore')
    check('staged local lock retains StrongAuth path', 'stage:Lcom/android/server/locksettings/LockSettingsService;->lockUser(', 49, reference='requireStrongAuth')
    for method in ['onDeviceLocked(', 'onDeviceUnlocked(']:
        part = 'stage-framework:Landroid/security/KeyStoreAuthorization;->' + method
        check('staged keyguard wrapper attempts real interface ' + method, part, 7, reference='IKeystoreAuthorization;->' + method)
        check('staged keyguard wrapper connection failure status ' + method, part, 24, literal=4)
    for part, absent in [(stage_sms + 'prepareUserStorageInternal(', 'IVold;->prepareUserStorage'),
                         (stage_installer + 'destroyUserData(', 'IInstalld;->destroyUserData'),
                         (stage_sms + 'lockCeStorage(', 'IVold;->lockCeStorage'),
                         ('stage:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;->unlockCeStorage(', 'IVold;->unlockCeStorage')]:
        key = next(k for k in bodies if part in k)
        assert not any(absent in i.get('reference', '') for i in bodies[key]['instructions'])
        checks.append({'id': 'effective preservation guard removes ' + absent, 'method': key, 'referenceAbsent': absent})
    comparisons, added, peer_only = [], [], []
    for key, proof in proofs.items():
        if not key.startswith(('stage:', 'stage-framework:')):
            continue
        side, name = key.split(':', 1)
        before = ('guest-framework:' if side == 'stage-framework' else 'guest:') + name
        if before not in proofs:
            before = 'coloros-services:' + name
        if before not in proofs:
            (peer_only if proof.get('reusedPeerGuardRead') else added).append(key)
            continue
        comparisons.append({'method': name, 'originalProof': before, 'stageProof': key,
                            'originalBodySha256': proofs[before]['bodySha256'], 'stageBodySha256': proof['bodySha256'],
                            'normalizedBodyIdentical': proofs[before]['bodySha256'] == proof['bodySha256']})
    assert len(comparisons) == 39 and sum(x['normalizedBodyIdentical'] for x in comparisons) == 33
    assert len(added) == 4 and all('OneOSInstalldProxy;' in key for key in added)
    assert len(peer_only) == 4
    fixed_inputs = {
        'out/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/acquisition.json': 'ad6b1d7aaa79a17f2745c52a347a660b1d70bef7956a4354f6feb997417e0d23',
        'out/installed-oneos-code-profile/static/appdata-bridge-source.json': '07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
        'docs/installed-oneos-code-profile.md': '6898a3096493f88648f85bd6009c9544a1de92d44b25f3bd9820bc013290425d',
        'out/retention-native-view-observation/20261106T022427951464Z-d70f0ad08106435bb3bcac4bf737f458/observation.json': '2d55a1ae77a5886787926b307aaad1d2e76c33c2d167a7a1e72e6738bdec0f04',
    }
    for path, pin in fixed_inputs.items():
        assert sha(ROOT / path) == pin
    input_paths = ['inventory/samsung-user-registry-lifecycle.json', 'docs/samsung-user-registry-lifecycle.md',
                   'inventory/strongauth-callback-adapter.json', 'inventory/construction-storage-linkage.json',
                   'docs/local-locksettings-contract.md', 'docs/security-authority-quiescence.md',
                   'tools/static_security_reader.py', 'tools/SecurityDexReader.java']
    value = {'schema': 'retained-guest-user-lifecycle/v1',
             'status': 'ACTUAL_STAGED_PROFILE_PINNED_REAL_DATA_AND_POLICY_BINDING_UNASSEMBLED',
             'assertions': checks, 'assertionCount': len(checks), 'methodProofs': proofs,
             'receiptPins': receipts, 'rawPins': {p['raw']: p['rawSha256'] for p in proofs.values()},
             'archivePins': {side: {'path': str((ROOT.parent / path).resolve()), 'sha256': pin}
                             for side, (path, pin) in ARCHIVES.items()},
             'queries': json.loads((WORK / 'queries.json').read_text()),
             'inputPins': {p: sha(ROOT / p) for p in input_paths} | fixed_inputs, 'toolSha256': sha(__file__),
             'guestEvidenceIsOriginalDonorOnly': False, 'selectedStagedMethodProfileCaptured': True,
             'runtimeProfileOrLoadedIdentityAdmitted': False, 'methodComparisons': comparisons,
             'comparisonCounts': {'pairedMethods': 39, 'identicalBodies': 33, 'changedBodies': 6,
                                  'unpairedOneOsProxyMethods': 4, 'reusedStagedGuardMethods': 4},
             'oneOsUnpairedProxyMethods': added, 'reusedStagedGuardMethods': peer_only,
             'acquiredStagedServices': {
                 'sha256': 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671',
                 'evidenceKind': 'root read-only init-view artifact acquisition with before/after manifests/remote identity and local hashes; exact bodies statically compared here, no execution'},
             'conclusions': {
                 'ordinaryScreenLockIsNotUserStop': 'separate observed source mechanisms; retain actual Samsung Trust/StrongAuth/profile/Keystore policy, not an unconditional all-profile CE claim',
                 'hostPhysicalUserCanRemainGenuinelyRunning': 'conditional retained design: no synthetic host boot/state replay, real same-user CE/currentness and actual guest keyguard view required',
                 'oneOsExistingAppDataMechanism': 'canonical installd through existing OneOSInstalldProxy plus init-view fourteen-tree data redirection and guest scaffold; source ACKs do not establish native identity or completion',
                 'guestDataPreparationIsNotAlreadyDoneFromHostCeUnlocked': 'actual guest serial/Environment/Installer/PM package work continues; native prepare/destroy guards and forced-true CE status are compatibility behavior, not physical truth',
                 'guestVmDetachIsNotPhysicalKeyEviction': 'staged keyEvicted can follow no-native SMS lock/cache mutation; genuine retained-key eviction needs real authority outcome, or separately defined guest-runtime retirement with no false physical acknowledgement',
                 'onlyProvenAlreadyDoneBranch': 'original Samsung LSS actual isCeStorageUnlocked result chooses return29; no forced result/no generic UMS beforeUnlock no-op'},
             'earliestMissingOwner': 'real guest appdata backend/view and retained-host future path/native-writer separation before the packaged init-view appdata overmounts and guest Installer requests; retained Trust also needs actual guest keyguard input rather than its own old WM view',
             'runtimeCodeOrControlAdded': False, 'oemExecuted': False, 'androidExecuted': False,
             'phoneActions': False, 'privateUserStateRead': False, 'architectureSelected': False,
             'limits': ['Exact acquired staged bytes are not loaded guest/process/native/Android execution proof',
                        'Ordinary-OneUI main process namespace observation is not a future OneOS propagation/whole-thread retention proof',
                        'No fake Samsung user state, copied registry, default user0, duplicate both data preparations or foreign object call is selected',
                        'Original caught/void returns and callbacks do not prove native persistence or global drain',
                        'Next package helper overload, vendor extensions and effective guard behavior are explicit frontiers, not assumed no-ops']}
    path = ROOT / 'inventory/retained-guest-user-lifecycle.json'
    path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'status': value['status'], 'assertions': len(checks), 'methods': len(proofs),
                      'inventorySha256': sha(path)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--report', action='store_true')
    p.add_argument('--capture-stage', action='store_true')
    args = p.parse_args()
    if args.capture:
        capture()
    if args.report:
        report()
    if args.capture_stage:
        capture_stage()
