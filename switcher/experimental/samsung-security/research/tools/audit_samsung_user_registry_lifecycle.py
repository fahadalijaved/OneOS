"""Bounded static lifecycle/CE evidence; never initializes OEM classes or users."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/samsung-user-registry-lifecycle'
ARCHIVES = {
    'samsung-services': ('firmware/samsung/runtime-20261104/services.jar', 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
    'coloros-services': ('firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
    'samsung-framework': ('firmware/samsung/framework.jar', '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def capture():
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'queries.json'
    queries = json.loads(path.read_text()) if path.exists() else []
    selectors = [
        ('coloros-services', 'com.android.server.am.UserController', [
            'finishUserUnlocking(Lcom/android/server/am/UserState;)Z',
            'finishUserUnlocked(Lcom/android/server/am/UserState;)V',
            'lambda$finishUserUnlocking$1(ILcom/android/server/am/UserState;)V',
            'lambda$finishUserUnlocked$2(Lcom/android/server/am/UserState;)V',
            'dispatchUserLocking(ILjava/util/List;)V',
            'finishUserStopping(ILcom/android/server/am/UserState;Z)V'], 'guest-unlock-stop'),
        ('coloros-services', 'com.android.server.am.UserController', [
            'lambda$dispatchUserLocking$14(ILjava/util/List;)V'], 'guest-lock-worker'),
        ('coloros-services', 'com.android.server.am.UserController', [
            'continueStartUserInternal(Landroid/content/pm/UserInfo;IIILcom/android/server/am/UserState;ZII)V',
            'startUserInternal(IIIILandroid/os/IProgressListener;Lcom/android/server/utils/TimingsTraceAndSlog;)Z',
            'stopSingleUserLU(IZLandroid/app/IStopUserCallback;Lcom/android/server/am/UserState$KeyEvictedCallback;)V'], 'guest-remaining-state-writers'),
        ('coloros-services', 'com.android.server.am.UserController$Injector', [
            'getUserManagerInternal()Lcom/android/server/pm/UserManagerInternal;',
            'getUserManager()Lcom/android/server/pm/UserManagerService;',
            'isCeStorageUnlocked(I)Z'], 'guest-actual-user-owner-v2'),
        ('samsung-services', 'com.android.server.pm.UserManagerService', [
            'onBeforeStartUser(I)V', 'onBeforeUnlockUser(I)V'], 'samsung-before-storage'),
        ('samsung-services', 'com.android.server.pm.UserManagerService$LifeCycle', [
            'onUserUnlocking(Lcom/android/server/SystemService$TargetUser;)V',
            'onUserStopping(Lcom/android/server/SystemService$TargetUser;)V'], 'samsung-lifecycle-tail'),
        ('samsung-framework', 'android.os.storage.StorageManager', [
            'isCeStorageUnlocked(I)Z'], 'samsung-actual-ce-query'),
    ]
    for side, cls, methods, label in selectors:
        if any(q['label'] == label for q in queries):
            continue
        archive, pin = ARCHIVES[side]
        result = read(ROOT.parent / archive, pin, class_name=cls, methods=methods,
                      stream='samsung-user-registry-lifecycle')
        queries.append({'side': side, 'class': cls, 'label': label, 'receipt': result['receipt']})
        path.write_text(json.dumps(queries, indent=2) + '\n')
        print(label, result['receipt'], flush=True)
    if not any(q['label'] == 'guest-state-writers' for q in queries):
        archive, pin = ARCHIVES['coloros-services']
        result = read(ROOT.parent / archive, pin,
                      reference='Lcom/android/server/pm/UserManagerInternal;->setUserState(II)V',
                      stream='samsung-user-registry-lifecycle')
        queries.append({'side': 'coloros-services', 'label': 'guest-state-writers', 'receipt': result['receipt']})
        path.write_text(json.dumps(queries, indent=2) + '\n')
        print('guest-state-writers', result['receipt'], flush=True)


def evidence():
    proofs = {}
    for name in ['security-user-binding', 'authority-bootstrap-users']:
        values = json.loads((ROOT / ('inventory/' + name + '.json')).read_text())
        for key, proof in values['methodProofs'].items():
            if key.startswith(('samsung-services:Lcom/android/server/pm/UserManagerService',
                               'samsung-services:Lcom/android/server/am/UserController',
                               'coloros-services:Lcom/android/server/am/UserController')):
                proofs[key] = dict(proof)
    registry = json.loads((ROOT / 'inventory/user-registry-owner.json').read_text())
    for key, proof in registry['methodProofs'].items():
        if any(part in key for part in ['->scheduleWriteUser(I)V', '$MainHandler;->handleMessage(',
                                       '-><init>(Landroid/content/Context;Lcom/android/server/pm/PackageManagerService;']):
            proofs[key] = dict(proof)
    local = json.loads((ROOT / 'inventory/local-locksettings-contract.json').read_text())
    for key, proof in local['methodProofs'].items():
        if key == 'samsung-user-lock-backing:Lcom/android/server/am/UserController$$ExternalSyntheticLambda3;->run()V':
            proofs[key] = dict(proof)
    for q in json.loads((WORK / 'queries.json').read_text()):
        rec = json.loads((ROOT / q['receipt']).read_text())
        assert rec['readerExitCode'] == 0 and rec['archiveAndToolPinsVerifiedBeforeAndAfter']
        assert rec['archiveSha256'] == ARCHIVES[q['side']][1]
        assert not rec['oemCodeExecuted'] and not rec['androidExecuted']
        for p in rec['selectedMethodProofs']:
            proofs[q['side'] + ':' + p['owner'] + '->' + p['signature']] = {
                'bodySha256': p['normalizedBodySha256'], 'raw': rec['raw'], 'rawSha256': rec['rawSha256'],
                'receipt': q['receipt'], 'physicalDex': p['physicalDex'],
                'logicalHeaderOffset': p['logicalHeaderOffset']}
    keep = ('->onBefore', '->finishUser', '->lambda$finishUser', '->lambda$dispatchUserLocking',
            '->dispatchUserLocking', '->continueStartUserInternal', '->startUserInternal',
            '->stopSingleUserLU', '->getUserManager()', '->getUserManagerInternal()',
            '->isCeStorageUnlocked', '->onUser', '->isUserUnlockingOrUnlocked', '->setUserState',
            '->removeUserState', '->scheduleWriteUser', '$MainHandler;->handleMessage',
            '-><init>(Landroid/content/Context;Lcom/android/server/pm/PackageManagerService;',
            'UserController$$ExternalSyntheticLambda3;->run()')
    return {key: proof for key, proof in proofs.items() if any(part in key for part in keep)}


def selected_bodies(proofs):
    result = {}
    cache = {}
    for key, p in proofs.items():
        assert sha(ROOT / p['raw']) == p['rawSha256']
        if p['raw'] not in cache:
            cache[p['raw']] = [json.loads(line) for line in (ROOT / p['raw']).read_text().splitlines()]
        row = next(row for row in cache[p['raw']] if row.get('record') == 'method' and
                   row['body']['owner'] + '->' + row['body']['signature'] == key.split(':', 1)[1])
        assert row['normalizedBodySha256'] == p['bodySha256']
        result[key] = row['body']
    return result


def report():
    proofs = evidence()
    bodies = selected_bodies(proofs)
    assertions = []
    def select(part):
        keys = [key for key in bodies if part in key]
        assert len(keys) == 1, (part, keys)
        return keys[0]
    def check(label, part, pc, **expected):
        key = select(part)
        ins = next(i for i in bodies[key]['instructions'] if i['pc'] == pc)
        for field, value in expected.items():
            assert (value in ins[field]) if field == 'reference' else (ins[field] == value), (label, ins)
        assertions.append({'id': label, 'method': key, 'pc': pc, 'observed': {k: ins[k] for k in expected}})
    c = 'coloros-services:Lcom/android/server/am/UserController;->'
    s = 'samsung-services:Lcom/android/server/pm/UserManagerService;->'
    injector = 'coloros-services:Lcom/android/server/am/UserController$Injector;->'
    check('guestUMS requires concrete local class', injector + 'getUserManager()', 15, opcode='CHECK_CAST', reference='UserManagerService;')
    check('guestUMS actual object is cached', injector + 'getUserManager()', 17, opcode='IPUT_OBJECT', reference='mUserManager:')
    check('guestUMI Class-keyed LocalServices acquisition', injector + 'getUserManagerInternal()', 6, reference='LocalServices;->getService')
    check('guestUMI actual object is cached', injector + 'getUserManagerInternal()', 12, opcode='IPUT_OBJECT', reference='mUserManagerInternal:')
    check('before-start direct concreteUMS call', c + 'continueStartUserInternal(', 281, reference='UserManagerService;->onBeforeStartUser(I)V')
    check('unlock initial realCE test', c + 'finishUserUnlocking(', 24, reference='isCeStorageUnlocked(I)Z')
    check('unlock current UserState identity guard', c + 'finishUserUnlocking(', 41, opcode='IF_NE', targetPc=91)
    check('unlock queues work then immediately returns true', c + 'finishUserUnlocking(', 87, reference='Handler;->post')
    check('unlock true is not callback acknowledgement', c + 'finishUserUnlocking(', 90, opcode='RETURN', registers=[3])
    check('unlock worker retestsCE', c + 'lambda$finishUserUnlocking$1(', 2, reference='isCeStorageUnlocked(I)Z')
    check('unlock before-state concreteUMS call', c + 'lambda$finishUserUnlocking$1(', 49, reference='UserManagerService;->onBeforeUnlockUser(I)V')
    check('unlock worker commits realstate toUMI', c + 'lambda$finishUserUnlocking$1(', 77, reference='UserManagerInternal;->setUserState(II)V')
    check('unlock worker posts continuation', c + 'lambda$finishUserUnlocking$1(', 114, reference='Message;->sendToTarget()V')
    check('unlocked retestsCE', c + 'finishUserUnlocked(', 17, reference='isCeStorageUnlocked(I)Z')
    check('unlocked state commit before progress finish', c + 'finishUserUnlocked(', 62, reference='UserManagerInternal;->setUserState(II)V')
    check('unlocked actual progress finish', c + 'finishUserUnlocked(', 67, reference='ProgressReporter;->finish()V')
    check('stop state removal precedes later locking', c + 'finishUserStopped(', 229, reference='UserManagerInternal;->removeUserState(I)V')
    check('stop schedules later locking', c + 'finishUserStopped(', 484, reference='UserController;->dispatchUserLocking')
    check('lock dispatch queues actual worker', c + 'dispatchUserLocking(', 15, reference='Handler;->post')
    check('lock worker rechecks actual restarted user', c + 'lambda$dispatchUserLocking$14(', 0, reference='hasStartedUserState(I)Z')
    check('lock worker invokes genuine LSI operation', c + 'lambda$dispatchUserLocking$14(', 20, reference='LockSettingsInternal;->lockUser(I)V')
    check('lock callback follows actual operation', c + 'lambda$dispatchUserLocking$14(', 39, reference='KeyEvictedCallback;->keyEvicted(I)V')
    check('beforeStart real DE flag', s + 'onBeforeStartUser(', 38, literal=1)
    check('beforeStart real user data preparation', s + 'onBeforeStartUser(', 48, reference='UserDataPreparer;->prepareUserData')
    check('beforeStart real package data reconciliation', s + 'onBeforeStartUser(', 64, reference='PackageManagerInternal;->reconcileAppsData')
    check('beforeStart user0 skips extra restrictions branch', s + 'onBeforeStartUser(', 70, opcode='IF_EQZ', targetPc=96)
    check('beforeStart schedules user persistence', s + 'onBeforeStartUser(', 85, reference='scheduleWriteUser(I)V')
    check('beforeUnlock genuine missingUser returns', s + 'onBeforeUnlockUser(', 6, opcode='RETURN_VOID')
    check('beforeUnlock real CE flag', s + 'onBeforeUnlockUser(', 42, literal=2)
    check('beforeUnlock real user data preparation', s + 'onBeforeUnlockUser(', 43, reference='UserDataPreparer;->prepareUserData')
    check('ordinary nonmanaged user joins concreteSMS path', s + 'onBeforeUnlockUser(', 53, opcode='IF_EQZ', targetPc=132)
    check('noDualDARflag also joins concreteSMS path', s + 'onBeforeUnlockUser(', 60, opcode='IF_LEZ', targetPc=132)
    check('DualDAR success joins same concreteSMS path', s + 'onBeforeUnlockUser(', 80, opcode='IF_NEZ', targetPc=132)
    check('concreteSMS Class-keyed owner', s + 'onBeforeUnlockUser(', 136, opcode='CONST_CLASS', reference='StorageManagerService$StorageManagerInternalImpl;')
    check('concreteSMS parent dereference', s + 'onBeforeUnlockUser(', 148, reference='StorageManagerInternalImpl;->this$0:')
    check('concreteSMS original lock', s + 'onBeforeUnlockUser(', 150, reference='StorageManagerService;->mLock:')
    check('concreteSMS original prepared-user cache', s + 'onBeforeUnlockUser(', 155, reference='mCeStoragePreparedUsers:')
    check('concreteSMS prepared-user cache updated', s + 'onBeforeUnlockUser(', 163, reference='ArraySet;->add')
    check('beforeUnlock actual package data reconciliation', s + 'onBeforeUnlockUser(', 189, reference='PackageManagerInternal;->reconcileAppsData')
    check('user writes have delayed handler ownership', s + 'scheduleWriteUser(', 25, literal=2000)
    check('user writes queued rather than completed', s + 'scheduleWriteUser(', 27, reference='Handler;->sendMessageDelayed')
    check('actual handler performs user write', '$MainHandler;->handleMessage(', 55, reference='UserManagerService;->writeUserLP')
    ce = 'samsung-framework:Landroid/os/storage/StorageManager;->isCeStorageUnlocked('
    check('Samsung CE cache resolves actual global Binder', ce, 7, reference='ServiceManager;->getService')
    check('Samsung CE query identity behavior preserved', ce, 30, reference='Binder;->clearCallingIdentity()J')
    check('Samsung CE query actual remote endpoint', ce, 36, reference='IStorageManager;->isCeStorageUnlocked(I)Z')
    local = 'samsung-services:Lcom/android/server/pm/UserManagerService$LocalService;->'
    check('UMI state write invalidates original cache', local + 'setUserState(', 14, reference='invalidateIsUserUnlockedCache()V')
    check('UMI state deletion invalidates original cache', local + 'removeUserState(', 14, reference='invalidateIsUserUnlockedCache()V')
    check('UMI stopping states recheck actualCE', local + 'isUserUnlockingOrUnlocked(', 32, reference='StorageManager;->isCeStorageUnlocked(I)Z')
    check('Samsung original physical locking', 'samsung-user-lock-backing:', 373, reference='IStorageManager;->lockCeStorage')
    check('Samsung lock genuine Keystore notification', 'samsung-user-lock-backing:', 378, reference='KeyStoreAuthorization;->onUserStorageLocked')
    check('Samsung lock genuine StrongAuth', 'samsung-user-lock-backing:', 387, reference='requireStrongAuth')
    queries = json.loads((WORK / 'queries.json').read_text())
    reference = next(q for q in queries if q['label'] == 'guest-state-writers')
    rec = json.loads((ROOT / reference['receipt']).read_text())
    assert rec['referenceMatchCount'] == 8 and sha(ROOT / rec['raw']) == rec['rawSha256']
    writers = [row for row in map(json.loads, (ROOT / rec['raw']).read_text().splitlines()) if row.get('record') == 'reference']
    assert len({row['caller'] for row in writers}) == 7
    for row in writers:
        key = 'coloros-services:' + row['caller']
        assert key in bodies and next(i for i in bodies[key]['instructions'] if i['pc'] == row['instruction']['pc'])['reference'].endswith('->setUserState(II)V')
    receipts = {q['receipt']: sha(ROOT / q['receipt']) for q in queries}
    for p in proofs.values():
        if 'receipt' in p:
            receipts[p['receipt']] = sha(ROOT / p['receipt'])
    inputs = ['docs/authority-owner-assembly.md', 'inventory/authority-owner-assembly.json',
              'docs/authority-bootstrap-users.md', 'inventory/authority-bootstrap-users.json',
              'docs/user-registry-owner.md', 'inventory/user-registry-owner.json',
              'docs/local-locksettings-contract.md', 'inventory/local-locksettings-contract.json',
              'docs/security-authority-quiescence.md', 'inventory/security-authority-quiescence.json',
              'docs/retained-authority-dependencies.md', 'docs/retained-authority-control.md',
              'tools/static_security_reader.py', 'tools/SecurityDexReader.java']
    value = {'schema': 'samsung-user-registry-lifecycle/v1',
             'status': 'SOURCE_CLOSED_LIFECYCLE_FRONTIER_REAL_OWNER_UNASSEMBLED',
             'evidenceKind': 'bounded static captured method-body/branch/reference proofs',
             'assertions': assertions, 'assertionCount': len(assertions), 'methodProofs': proofs,
             'queries': queries, 'receiptPins': receipts,
             'archivePins': {side: {'path': str((ROOT.parent / path).resolve()), 'sha256': pin}
                             for side, (path, pin) in ARCHIVES.items()},
             'rawPins': {p['raw']: p['rawSha256'] for p in proofs.values()} | {rec['raw']: rec['rawSha256']},
             'guestStateWriterSites': [{'caller': x['caller'], 'pc': x['instruction']['pc']} for x in writers],
             'inputPins': {p: sha(ROOT / p) for p in inputs}, 'toolSha256': sha(__file__),
             'requiredOwners': ['one genuine Samsung user/serial/profile/type-policy registry before any state read/recovery',
                                'one active guest lifecycle producer with original UserState/CE/order and cache-binding',
                                'actual UserDataPreparer/Installer/installLock and package-data policy owner',
                                'same Samsung concrete storage prepared-user cache/lock or separately proved source-equivalent adaptation',
                                'original handlers/persistence/restriction/profile callbacks and physical lock acknowledgement'],
             'priorAssemblyCorrection': 'UMI set/remove transport is necessary but does not cover concrete guest UMS calls, data preparation, Samsung SMS prepared-user state or asynchronous CE lock/drain.',
             'minimumPmsOrAmImportProved': False, 'lifecycleOrRetainerImplemented': False,
             'oemExecuted': False, 'androidExecuted': False, 'privateUserStateRead': False,
             'phoneActions': False, 'architectureSelected': False,
             'nextEngineeringAction': 'Review a retention-specific active-user lifecycle routing cut across actual guest concrete UMS calls and retained Samsung UMS/PMI/SMS, including separate package-data realms, host producer exclusion, initial complete state and original lock/child acknowledgements; no new cold leaf.',
             'limits': ['Captured source is not actual initialized owner/runtime/installed image evidence',
                        'Source bodies do not prove caller/user/serial/protocol/currentness or completion',
                        'No full PMS/AM/SMS necessity or free dual-SystemServer coexistence conclusion',
                        'Method returns/state-map deletion/Handler markers do not establish native/durable/global drain']}
    path = ROOT / 'inventory/samsung-user-registry-lifecycle.json'
    path.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'status': value['status'], 'assertions': len(assertions), 'methods': len(proofs),
                      'guestWriterSites': len(writers), 'inventorySha256': sha(path)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.capture:
        capture()
    if args.report:
        report()
