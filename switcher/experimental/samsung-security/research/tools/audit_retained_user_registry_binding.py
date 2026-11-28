"""Static source-owned retained user cohort capture contract; no OEM execution."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/retained-user-registry-binding'
ARCHIVE = ROOT.parent / 'firmware/samsung/runtime-20261104/services.jar'
ARCHIVE_SHA = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
FRAMEWORK = ROOT.parent / 'firmware/samsung/framework.jar'
FRAMEWORK_SHA = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
READER_SHA = '0bbe5418e74bc928e770a634f7cfc7b734131afeb69a7aa0b26676b6ccaa1407'
JAVA_SHA = '9ee6f28750779f289bbb85049472d5261b7bacad5655faf01c8395f2f6d244cc'
LABELS = ['system-server-declaration', 'ams-declaration', 'ams-local-declaration',
          'user-controller-declaration', 'user-injector-declaration', 'pmi-declaration',
          'sms-declaration', 'smi-declaration', 'controller-current-reads',
          'injector-owner-reads', 'sms-ce-read', 'watched-ce-declaration', 'user-state-declaration',
          'user-state-names', 'ums-lifecycle-publication', 'boot-completed-predicate',
          'ams-lifecycle-publication', 'data-preparer-declaration', 'umi-declaration',
          'zygote-init-declaration', 'zygote-system-server-loader',
          'pmi-parent-constructor', 'ami-parent-constructor', 'ams-internal-reference', 'ams-local-producer']
BASE_PINS = {
    'inventory/samsung-user-registry-owner.json': 'd9470806703b02ddaf2a18b580b244061565a6c96a501292c0e3d353b8261f9e',
    'inventory/authority-boot-framework.json': '8a7b144c1c9024ffbff548568439b2e81a9c072ecd05683469a7fbc33f31f96a',
    'inventory/authority-bootstrap-endpoints.json': '2e99d62f8287b9fcf16a4cd32439ce1e91d2a83ad2f4fb95006a36b6411284b0',
    'inventory/construction-storage-linkage.json': 'df20e5c08427b2e6abf5e08691fb6e5efcb3da178b734dd3e58e631b7ad361a6',
    'inventory/retained-guest-user-lifecycle.json': '731ac8031bf051c283d1cbb7ec23425d69d90c7a12b1895a547e9a64a5421040',
    'inventory/installed-oneos-code-profile.json': 'e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a',
    'out/retention-native-view-observation/20261106T022427951464Z-d70f0ad08106435bb3bcac4bf737f458/observation.json':
        '2d55a1ae77a5886787926b307aaad1d2e76c33c2d167a7a1e72e6738bdec0f04',
}
FIELD_NAMES = {
    'Lcom/android/server/pm/UserManagerService;': ['mLocalService', 'mPm', 'mPmInternal', 'mUserDataPreparer', 'sPersonaManager', 'mPackagesLock', 'mContext'],
    'Lcom/android/server/pm/PackageManagerService;': ['mUserManager', 'mInstaller', 'mInstallLock', 'mLock', 'sPersonaManager'],
    'Lcom/android/server/pm/UserManagerService$LocalService;': ['this$0'],
    'Lcom/android/server/pm/PackageManagerService$PackageManagerInternalImpl;': ['this$0'],
    'Lcom/android/server/StorageManagerService;': ['mStorageManagerInternal', 'mVold'],
    'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;': ['this$0'],
    'Lcom/android/server/am/ActivityManagerService;': ['mInternal', 'mSystemServiceManager', 'mUserController'],
    'Lcom/android/server/am/ActivityManagerService$LocalService;': ['this$0'],
    'Lcom/android/server/am/UserController;': ['mInjector'],
    'Lcom/android/server/am/UserController$Injector;': ['mService', 'mUserManager', 'mUserManagerInternal'],
    'Lcom/android/server/pm/UserDataPreparer;': ['mContext', 'mInstaller', 'mInstallLock'],
    'Lcom/android/internal/os/ZygoteInit;': ['sCachedSystemServerClassLoader'],
}


def sha(path):
    with Path(path).open('rb') as value:
        return hashlib.file_digest(value, 'sha256').hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def query(label, cls=None, methods=(), framework=False, reference=None):
    need(sha(ROOT / 'tools/static_security_reader.py') == READER_SHA and
         sha(ROOT / 'tools/SecurityDexReader.java') == JAVA_SHA, 'Reader pins')
    archive, archive_sha = (FRAMEWORK, FRAMEWORK_SHA) if framework else (ARCHIVE, ARCHIVE_SHA)
    need(sha(archive) == archive_sha, 'Archive pin')
    path = WORK / (label + '.json')
    if path.exists():
        return json.loads(path.read_text())
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    result = reader(archive, archive_sha, class_name=cls, methods=methods, reference=reference,
                    stream='retained-user-registry-binding')
    WORK.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def capture():
    for label, cls in [
        ('system-server-declaration', 'com.android.server.SystemServer'),
        ('ams-declaration', 'com.android.server.am.ActivityManagerService'),
        ('ams-local-declaration', 'com.android.server.am.ActivityManagerService$LocalService'),
        ('user-controller-declaration', 'com.android.server.am.UserController'),
        ('user-injector-declaration', 'com.android.server.am.UserController$Injector'),
        ('pmi-declaration', 'com.android.server.pm.PackageManagerService$PackageManagerInternalImpl'),
        ('sms-declaration', 'com.android.server.StorageManagerService'),
        ('smi-declaration', 'com.android.server.StorageManagerService$StorageManagerInternalImpl')]:
        query(label, cls)
    query('controller-current-reads', 'com.android.server.am.UserController',
          ['getCurrentUserId()I', 'getStartedUserState(I)Lcom/android/server/am/UserState;'])
    query('injector-owner-reads', 'com.android.server.am.UserController$Injector',
          ['getUserManager()Lcom/android/server/pm/UserManagerService;',
           'getUserManagerInternal()Lcom/android/server/pm/UserManagerInternal;'])
    query('sms-ce-read', 'com.android.server.StorageManagerService', ['isCeStorageUnlocked(I)Z'])
    query('watched-ce-declaration', 'com.android.server.StorageManagerService$WatchedUnlockedUsers')
    query('user-state-declaration', 'com.android.server.am.UserState')
    query('user-state-names', 'com.android.server.am.UserState', ['stateToString(I)Ljava/lang/String;'])
    query('ums-lifecycle-publication', 'com.android.server.pm.UserManagerService$LifeCycle', ['onStart()V'])
    query('boot-completed-predicate', 'com.android.server.SystemServiceManager', ['isBootCompleted()Z'])
    query('ams-lifecycle-publication', 'com.android.server.am.ActivityManagerService$Lifecycle', ['onStart()V'])
    query('data-preparer-declaration', 'com.android.server.pm.UserDataPreparer')
    query('umi-declaration', 'com.android.server.pm.UserManagerService$LocalService')
    query('zygote-init-declaration', 'com.android.internal.os.ZygoteInit', framework=True)
    query('zygote-system-server-loader', 'com.android.internal.os.ZygoteInit',
          ['handleSystemServerProcess(Lcom/android/internal/os/ZygoteArguments;)Ljava/lang/Runnable;',
           'getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;'], framework=True)
    query('pmi-parent-constructor', 'com.android.server.pm.PackageManagerService$PackageManagerInternalImpl',
          ['<init>(Lcom/android/server/pm/PackageManagerService;)V'])
    query('ami-parent-constructor', 'com.android.server.am.ActivityManagerService$LocalService',
          ['<init>(Lcom/android/server/am/ActivityManagerService;)V'])
    query('ams-internal-reference', reference='Lcom/android/server/am/ActivityManagerService;->mInternal:Landroid/app/ActivityManagerInternal;')
    query('ams-local-producer', 'com.android.server.am.ActivityManagerService',
          ['<init>(Landroid/content/Context;Lcom/android/server/wm/ActivityTaskManagerService;)V'])


def report():
    for path, pin in BASE_PINS.items():
        need(sha(ROOT / path) == pin, 'Frozen dependency: ' + path)
    declarations, proofs, raw_pins, receipt_pins, query_pins = {}, {}, {}, {}, {}
    def consume(result):
        receipt = json.loads((ROOT / result['receipt']).read_text())
        need(receipt['archiveSha256'] in (ARCHIVE_SHA, FRAMEWORK_SHA) and receipt['readerExitCode'] == 0 and
             receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] and not receipt['oemCodeExecuted'] and
             not receipt['androidExecuted'], 'Static reader profile')
        need(sha(ROOT / receipt['raw']) == receipt['rawSha256'], 'Raw source pin')
        receipt_pins[result['receipt']] = sha(ROOT / result['receipt'])
        raw_pins[receipt['raw']] = receipt['rawSha256']
        for declaration in receipt['selectedClassDeclarations']:
            declarations[declaration['descriptor']] = dict(declaration, archiveSha256=receipt['archiveSha256'])
        for proof in receipt['selectedMethodProofs']:
            proofs[proof['owner'] + '->' + proof['signature']] = dict(proof, raw=receipt['raw'],
                rawSha256=receipt['rawSha256'], receipt=result['receipt'], archiveSha256=receipt['archiveSha256'])
    for label in LABELS:
        path = WORK / (label + '.json')
        query_pins[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path)
        consume(json.loads(path.read_text()))
    older = json.loads((ROOT / 'inventory/samsung-user-registry-owner.json').read_text())
    for label in ['ums-declarations', 'pms-declarations']:
        path = 'out/samsung-user-registry-owner/' + label + '.json'
        need(sha(ROOT / path) == older['queryPins'][path], 'Older declaration pin')
        consume(json.loads((ROOT / path).read_text()))
    original_ums_signature = '<init>(Landroid/content/Context;Lcom/android/server/pm/PackageManagerService;Lcom/android/server/pm/UserDataPreparer;Lcom/android/server/pm/UserJourneyLogger;Ljava/lang/Object;Ljava/io/File;Landroid/util/SparseArray;Lcom/android/server/pm/PersonaManagerService;)V'
    ums_proof = older['methodProofs']['samsung-services:Lcom/android/server/pm/UserManagerService;->' + original_ums_signature]
    need(sha(ROOT / ums_proof['raw']) == ums_proof['rawSha256'], 'Original UMS constructor raw')
    ums_constructor_receipt = ums_proof['receipt']
    consume(dict(json.loads((ROOT / ums_constructor_receipt).read_text()), receipt=ums_constructor_receipt))
    path = 'out/samsung-user-registry-owner/pms-constructors.json'
    need(sha(ROOT / path) == older['queryPins'][path], 'Original PMS constructor snapshot')
    pms_constructor_result = json.loads((ROOT / path).read_text())
    pms_constructor_receipt = pms_constructor_result['receipt']
    consume(pms_constructor_result)
    bootstrap = 'out/tooling/20261105T123938572593Z-7fa57b74656d4701b1ebb25c779e8222/receipt.json'
    need(sha(ROOT / bootstrap) == '738b76fd3896b91d745b6de18fb73f592935e8a011768382e7b876220a6db2c4', 'Original bootstrap receipt')
    consume(dict(json.loads((ROOT / bootstrap).read_text()), receipt=bootstrap))
    sms_start = 'out/tooling/20261105T143846536698Z-46067db869724005abe8cacfda8fd036/receipt.json'
    storage = json.loads((ROOT / 'inventory/construction-storage-linkage.json').read_text())
    expected = next(e['receiptSha256'] for e in storage['evidence'] if e.get('receipt') == sms_start)
    need(sha(ROOT / sms_start) == expected, 'Original SMS publication receipt')
    consume(dict(json.loads((ROOT / sms_start).read_text()), receipt=sms_start))
    needed = ['Lcom/android/server/SystemServer;->main([Ljava/lang/String;)V',
              'Lcom/android/server/SystemServer;->startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V',
              'Lcom/android/server/StorageManagerService$Lifecycle;->onStart()V']
    proofs = {key: value for key, value in proofs.items()
              if value['receipt'] not in (bootstrap, sms_start) or key in needed}
    proofs = {key: value for key, value in proofs.items()
              if (value['receipt'] != ums_constructor_receipt or key == 'Lcom/android/server/pm/UserManagerService;->' + original_ums_signature)
              and (value['receipt'] != pms_constructor_receipt or key == 'Lcom/android/server/pm/PackageManagerService;-><init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V')}
    fields = []
    for owner, names in FIELD_NAMES.items():
        declaration = declarations[owner]
        for name in names:
            field = next(f for f in declaration['fields'] if f['name'] == name)
            fields.append(dict(field, owner=owner, declaringClassAccessFlags=declaration['accessFlags'],
                archiveSha256=declaration['archiveSha256'], physicalDex=declaration['physicalDex'],
                logicalHeaderOffset=declaration['logicalHeaderOffset'],
                requiredDefiningLoader='framework/Binder loader' if owner.startswith('Lcom/android/internal/os/') else 'cached original SystemServer loader C'))
    body_cache = {}
    def body(owner, signature):
        proof = proofs[owner + '->' + signature]
        if proof['raw'] not in body_cache:
            body_cache[proof['raw']] = {r['body']['owner'] + '->' + r['body']['signature']: r['body']
                for r in map(json.loads, (ROOT / proof['raw']).read_text().splitlines()) if r.get('record') == 'method'}
        return body_cache[proof['raw']][owner + '->' + signature]
    def at(value, pc):
        return next(i for i in value['instructions'] if i['pc'] == pc)
    assertions = []
    def check(name, condition):
        need(condition, name)
        assertions.append(name)
    zygote = body('Lcom/android/internal/os/ZygoteInit;', 'handleSystemServerProcess(Lcom/android/internal/os/ZygoteArguments;)Ljava/lang/Runnable;')
    check('actual-zygote-loader-to-main-context-loader', 'getOrCreateSystemServerClassLoader' in at(zygote, 160)['reference'] and
          'Thread;->setContextClassLoader' in at(zygote, 170)['reference'] and '->zygoteInit(' in at(zygote, 181)['reference'])
    cache = body('Lcom/android/internal/os/ZygoteInit;', 'getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;')
    check('cached-loader-read-and-cold-factory-distinct', 'sCachedSystemServerClassLoader' in at(cache, 0)['reference'] and
          'createPathClassLoader' in at(cache, 14)['reference'] and at(cache, 18)['opcode'] == 'SPUT_OBJECT')
    boot = json.loads((ROOT / 'inventory/authority-boot-framework.json').read_text())
    check('actual-framework-boot-cohort', boot['frameworkBootEntryIndex'] == 5 and
          boot['bootClassPath'][5] == '/system/framework/framework.jar' and '/system/framework/services.jar' in boot['systemServerClassPath'])
    locals_proof = json.loads((ROOT / 'inventory/authority-bootstrap-endpoints.json').read_text())['methodProofs'][
        'samsung-locals:Lcom/android/server/LocalServices;->getService(Ljava/lang/Class;)Ljava/lang/Object;']
    check('actual-localservices-in-framework-not-package-inference', locals_proof['archiveSha256'] == FRAMEWORK_SHA and
          locals_proof['physicalDex'] == 'classes6.dex' and sha(ROOT / locals_proof['raw']) == locals_proof['rawSha256'])
    main = body('Lcom/android/server/SystemServer;', 'main([Ljava/lang/String;)V')
    check('actual-system-server-main-looper', 'Looper;->prepareMainLooper()' in at(main, 368)['reference'] and
          'Looper;->loop()' in at(main, 910)['reference'])
    phase = body('Lcom/android/server/SystemServiceManager;', 'isBootCompleted()Z')
    check('boot-predicate-is-only-phase-at-least1000', '->mCurrentPhase:I' in at(phase, 0)['reference'] and
          at(phase, 2)['literal'] == 1000 and at(phase, 4)['opcode'] == 'IF_LT')
    check('pmi-declaring-class-is-package-private', declarations['Lcom/android/server/pm/PackageManagerService$PackageManagerInternalImpl;']['accessFlags'] == 0)
    check('injector-declaring-class-is-package-private', declarations['Lcom/android/server/am/UserController$Injector;']['accessFlags'] == 0)
    check('zygote-cache-field-is-private-static', next(f for f in fields if f['name'] == 'sCachedSystemServerClassLoader')['accessFlags'] == 10)
    check('all-relationship-fields-source-public', all(f['accessFlags'] & 1 for f in fields if f['name'] != 'sCachedSystemServerClassLoader'))
    local_pub = body('Lcom/android/server/am/ActivityManagerService$Lifecycle;', 'onStart()V')
    check('actual-ami-publication', at(local_pub, 166)['reference'] == 'Landroid/app/ActivityManagerInternal;' and
          '->mInternal:' in at(local_pub, 168)['reference'] and 'LocalServices;->addService' in at(local_pub, 170)['reference'])
    umi_pub = body('Lcom/android/server/pm/UserManagerService$LifeCycle;', 'onStart()V')
    check('actual-ums-singleton-publication', '->getInstance()' in at(umi_pub, 0)['reference'] and '->publishBinderService(' in at(umi_pub, 9)['reference'])
    sms_pub = body('Lcom/android/server/StorageManagerService$Lifecycle;', 'onStart()V')
    check('actual-smi-is-concrete-object-only', declarations['Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;']['superclass'] == 'Ljava/lang/Object;' and
          declarations['Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;']['interfaces'] == [])
    root_publications = [
        {'role': 'SMI', 'key': 'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;',
         'owner': 'Lcom/android/server/StorageManagerService$Lifecycle;', 'method': 'onStart()V',
         'keyPc': 533, 'valuePc': 535, 'publishPc': 537,
         'valueReference': 'Lcom/android/server/StorageManagerService;->mStorageManagerInternal:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;', 'arguments': [1, 2]},
        {'role': 'UMI', 'key': 'Lcom/android/server/pm/UserManagerInternal;',
         'owner': 'Lcom/android/server/pm/UserManagerService;', 'method': original_ums_signature,
         'keyPc': 1072, 'valuePc': 1074, 'publishPc': 1076,
         'valueReference': 'Lcom/android/server/pm/UserManagerService;->mLocalService:Lcom/android/server/pm/UserManagerService$LocalService;', 'arguments': [0, 2]},
        {'role': 'AMI', 'key': 'Landroid/app/ActivityManagerInternal;',
         'owner': 'Lcom/android/server/am/ActivityManagerService$Lifecycle;', 'method': 'onStart()V',
         'keyPc': 166, 'valuePc': 168, 'publishPc': 170,
         'valueReference': 'Lcom/android/server/am/ActivityManagerService;->mInternal:Landroid/app/ActivityManagerInternal;', 'arguments': [0, 1]},
        {'role': 'SSM', 'key': 'Lcom/android/server/SystemServiceManager;',
         'owner': 'Lcom/android/server/SystemServer;', 'method': 'main([Ljava/lang/String;)V',
         'keyPc': 527, 'valuePc': 529, 'publishPc': 531,
         'valueReference': 'Lcom/android/server/SystemServer;->mSystemServiceManager:Lcom/android/server/SystemServiceManager;', 'arguments': [2, 4]},
        {'role': 'PMI', 'key': 'Landroid/content/pm/PackageManagerInternal;',
         'owner': 'Lcom/android/server/pm/PackageManagerService;', 'method': '<init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V',
         'keyPc': 425, 'valuePc': 427, 'publishPc': 432,
         'valueReference': 'Lcom/android/server/pm/PackageManagerService$PackageManagerInternalImpl;', 'arguments': [0, 2]},
        {'role': 'PMS', 'key': 'Lcom/android/server/pm/PackageManagerService;',
         'owner': 'Lcom/android/server/pm/PackageManagerService;', 'method': '<init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V',
         'keyPc': 474, 'valuePc': 0, 'publishPc': 476,
         'valueReference': None, 'arguments': [3, 1]},
    ]
    for row in root_publications:
        source = body(row['owner'], row['method'])
        check('literal-' + row['role'] + '-publication-key', at(source, row['keyPc'])['opcode'] == 'CONST_CLASS' and
              at(source, row['keyPc'])['reference'] == row['key'] and at(source, row['keyPc'])['registers'] == [row['arguments'][0]])
        if row['valueReference'] is not None:
            check('literal-' + row['role'] + '-publication-value', at(source, row['valuePc'])['reference'] == row['valueReference'] and
                  at(source, row['valuePc'])['registers'][0] == row['arguments'][1])
        else:
            check('literal-PMS-publication-this', at(source, 0)['opcode'] == 'MOVE_OBJECT_FROM16' and at(source, 0)['registers'] == [1, 27])
        check('literal-' + row['role'] + '-publication-call', at(source, row['publishPc'])['reference'] ==
              'Lcom/android/server/LocalServices;->addService(Ljava/lang/Class;Ljava/lang/Object;)V' and
              at(source, row['publishPc'])['registers'] == row['arguments'])
    pmi_ctor = body('Lcom/android/server/pm/PackageManagerService$PackageManagerInternalImpl;', '<init>(Lcom/android/server/pm/PackageManagerService;)V')
    ami_ctor = body('Lcom/android/server/am/ActivityManagerService$LocalService;', '<init>(Lcom/android/server/am/ActivityManagerService;)V')
    check('actual-pmi-parent-write', at(pmi_ctor, 3)['registers'] == [1, 0] and '->this$0:' in at(pmi_ctor, 3)['reference'])
    check('actual-ami-parent-write', at(ami_ctor, 0)['registers'] == [1, 0] and '->this$0:' in at(ami_ctor, 0)['reference'])
    ams_ctor = body('Lcom/android/server/am/ActivityManagerService;', '<init>(Landroid/content/Context;Lcom/android/server/wm/ActivityTaskManagerService;)V')
    check('actual-ams-internal-value-producer', at(ams_ctor, 2025)['reference'] == 'Lcom/android/server/am/ActivityManagerService$LocalService;' and
          at(ams_ctor, 2027)['registers'] == [0, 1] and at(ams_ctor, 2030)['registers'] == [0, 1] and '->mInternal:' in at(ams_ctor, 2030)['reference'])
    injector = body('Lcom/android/server/am/UserController$Injector;', 'getUserManager()Lcom/android/server/pm/UserManagerService;')
    check('injector-getter-is-lazy-and-forbidden-to-capture', 'ServiceManager;->getService' in at(injector, 7)['reference'] and
          at(injector, 17)['opcode'] == 'IPUT_OBJECT')
    ce = body('Lcom/android/server/StorageManagerService;', 'isCeStorageUnlocked(I)Z')
    check('original-ce-is-locked-cache-not-native-probe', at(ce, 2)['opcode'] == 'MONITOR_ENTER' and
          'WatchedUnlockedUsers;->users:[I' in at(ce, 5)['reference'] and 'ArrayUtils;->contains' in at(ce, 7)['reference'])
    names = body('Lcom/android/server/am/UserState;', 'stateToString(I)Ljava/lang/String;')
    check('state3-is-running-unlocked-not-keyguard', at(names, 8)['literal'] == 3 and at(names, 30)['reference'] == 'string=RUNNING_UNLOCKED')
    value = {'schema': 'retained-user-registry-binding/v1', 'status': 'SOURCE_CLOSED_CAPTURE_ONLY_CONTRACT_LIFECYCLE_OPEN',
        'selected': False, 'api': ['PreparedRetainedUserRegistryCapture.captureExisting()', 'checkStillBound()'],
        'mainThreadOnly': True, 'cachedOriginalZygoteLoaderOnly': True, 'providerRealizationPermitted': False,
        'noUniversalNoClassInitializationClaim': True, 'inputPins': BASE_PINS, 'queryPins': query_pins,
        'receiptPins': receipt_pins, 'rawPins': raw_pins, 'methodProofs': proofs,
        'captureFields': fields, 'assertions': assertions, 'assertionCount': len(assertions),
        'bootLocalServicesProof': locals_proof, 'literalRootPublications': root_publications,
        'supersededUnbuiltRootKey': 'android.os.storage.StorageManagerInternal; wrong abstraction, never actual Samsung publication; history under out/retained-user-registry-capture/history/unbuilt-abstract-smi/',
        'explicitReflectiveReadAccess': [
            'ZygoteInit.sCachedSystemServerClassLoader:Ljava/lang/ClassLoader; private-static10',
            'PMS$PackageManagerInternalImpl.this$0:Lcom/android/server/pm/PackageManagerService; public-final-synthetic4113 on declaring class0',
            'UserController$Injector.mService:Lcom/android/server/am/ActivityManagerService; public1 on declaring class0',
            'UserController$Injector.mUserManager:Lcom/android/server/pm/UserManagerService; public1 on declaring class0',
            'UserController$Injector.mUserManagerInternal:Lcom/android/server/pm/UserManagerInternal; public1 on declaring class0'],
        'initialAccessClaimHistory': 'out/retained-user-registry-binding/history/initial-contract/; superseded erroneous public Injector claim only',
        'notCapturedOrGranted': ['current user/serial/profile/policy snapshot', 'native generation or hardware truth',
            'actual code/process/loader attestation', 'authentication/readiness', 'mount/path custody', 'guest lifecycle or drain'],
        'integrationFrontier': ['actual retained source/native path view before init-view app-data redirection',
            'genuine guest keyguard view into Samsung Trust/StrongAuth/Keystore policy',
            'distinct guest runtime retirement versus actual physical key eviction'],
        'failedExactSelectorHistory': 'out/tooling/20261106T022027202310Z-ee559d5cc551436fb9f0a7ad394cc5a0/stderr.txt: AMS.start absent; actual lifecycle body selected instead',
        'sourceContractSha256': sha(ROOT / 'docs/retained-user-registry-binding.md'),
        'toolSha256': sha(Path(__file__)), 'runtimeComponentImplementedByThisContract': False,
        'oemOrNativeOrAndroidExecutedByThisWorker': False, 'phoneActionsByThisWorker': []}
    path = ROOT / 'inventory/retained-user-registry-binding.json'
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    result = {'pass': True, 'assertions': len(assertions), 'captureFields': len(fields),
              'hostBodyProofs': len(proofs), 'inventorySha256': sha(path), 'oemOrRuntimeExecuted': False}
    (WORK / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--capture', action='store_true')
    arguments.add_argument('--report', action='store_true')
    options = arguments.parse_args()
    if options.capture:
        capture()
    if options.report:
        report()
    if not options.capture and not options.report:
        arguments.error('Use --capture for exact static reads or --report for saved-proof validation')


if __name__ == '__main__':
    main()
