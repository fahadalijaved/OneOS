"""Narrow original Samsung UMS construction/registry owner audit; static only."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/samsung-user-registry-owner'
ARCHIVE = ROOT.parent / 'firmware/samsung/runtime-20261104/services.jar'
ARCHIVE_SHA = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
FRAMEWORK = ROOT.parent / 'firmware/samsung/framework.jar'
FRAMEWORK_SHA = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
READER_SHA = '0bbe5418e74bc928e770a634f7cfc7b734131afeb69a7aa0b26676b6ccaa1407'
JAVA_SHA = '9ee6f28750779f289bbb85049472d5261b7bacad5655faf01c8395f2f6d244cc'
BASE_PINS = {
    'inventory/authority-bootstrap-users.json': '3be21cf44efd85ccd56ba75d4ec7cfe95070f34cdfba00dc5bc0efa8dd5f8b91',
    'inventory/security-user-binding.json': 'acbc439cafd54927bca1440be576c06e9d72265625e3ab9cc5ac70d7dfc6e384',
    'inventory/user-registry-owner.json': '3bdb07acccede2f78c70e1c6d38b464ce3f7181a5ccab569490801e3e55b720e',
}
UMS = 'Lcom/android/server/pm/UserManagerService;'
FULL_CTOR = '<init>(Landroid/content/Context;Lcom/android/server/pm/PackageManagerService;Lcom/android/server/pm/UserDataPreparer;Lcom/android/server/pm/UserJourneyLogger;Ljava/lang/Object;Ljava/io/File;Landroid/util/SparseArray;Lcom/android/server/pm/PersonaManagerService;)V'
QUERY_NAMES = ['factory-reference', 'real-factory', 'ums-preload-leaves',
               'pms-injector-declarations', 'ums-declarations', 'factory-type-reference',
               'injector-get-ums', 'ums-pmi-restriction', 'visibility-ctor',
               'type-factory-selected', 'ums-clinit', 'user-manager-early-helpers',
               'user-stub-ctor', 'pms-factory-main', 'pms-declarations',
               'ums-restriction-core', 'user-manager-cache-invalidate',
               'pms-constructors', 'pms-injector-bootstrap', 'pms-installd-stage']
PEER_RECEIPT = 'out/tooling/20261106T014622068717Z-4d6fff9f4b65422a9b31f470fde97162/receipt.json'
PEER_RECEIPT_SHA = '966e0fb5d8a2c56c88dd118e2f4471149e2d42586a903ee0c0d0ac6a704522e4'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def inputs():
    for path, pin in BASE_PINS.items():
        need(sha(ROOT / path) == pin, path)
    need(sha(ROOT / 'tools/static_security_reader.py') == READER_SHA, 'Reader pin')
    need(sha(ROOT / 'tools/SecurityDexReader.java') == JAVA_SHA, 'Java reader pin')
    need(sha(ARCHIVE) == ARCHIVE_SHA and sha(FRAMEWORK) == FRAMEWORK_SHA, 'Archive pins')


def query(label, cls=None, methods=(), reference=None, framework=False):
    inputs()
    path = WORK / (label + '.json')
    if path.exists():
        return json.loads(path.read_text())
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    value = reader(FRAMEWORK if framework else ARCHIVE,
                   FRAMEWORK_SHA if framework else ARCHIVE_SHA,
                   class_name=cls, methods=methods, reference=reference,
                   stream='samsung-user-registry-owner')
    write(path, value)
    return value


def capture():
    query('factory-reference', reference=UMS + '->' + FULL_CTOR)
    query('real-factory', 'com.android.server.pm.PackageManagerService$$ExternalSyntheticLambda39',
          ['produce(Lcom/android/server/pm/PackageManagerServiceInjector;Lcom/android/server/pm/PackageManagerService;)Ljava/lang/Object;'])
    query('ums-preload-leaves', 'com.android.server.pm.UserManagerService',
          ['invalidateOwnerNameIfNecessary(Landroid/content/res/Resources;Z)V',
           'initDefaultGuestRestrictions()V'])
    query('pms-injector-declarations', 'com.android.server.pm.PackageManagerServiceInjector')
    query('ums-declarations', 'com.android.server.pm.UserManagerService')
    query('factory-type-reference', reference='Lcom/android/server/pm/PackageManagerService$$ExternalSyntheticLambda39;')
    query('injector-get-ums', 'com.android.server.pm.PackageManagerServiceInjector',
          ['getUserManagerService()Lcom/android/server/pm/UserManagerService;'])
    query('ums-pmi-restriction', 'com.android.server.pm.UserManagerService',
          ['getPackageManagerInternal()Landroid/content/pm/PackageManagerInternal;',
           'setUserRestriction(Ljava/lang/String;ZI)V'])
    query('visibility-ctor', 'com.android.server.pm.UserVisibilityMediator',
          ['<init>(ZZLandroid/os/Handler;)V'])
    query('type-factory-selected', 'com.android.server.pm.UserTypeFactory',
          ['getDefaultBuilders()Landroid/util/ArrayMap;',
           'customizeBuilders(Landroid/util/ArrayMap;Landroid/content/res/XmlResourceParser;)V'])
    query('ums-clinit', 'com.android.server.pm.UserManagerService', ['<clinit>()V'])
    query('user-manager-early-helpers', 'android.os.UserManager',
          ['invalidateIsUserUnlockedCache()V', 'isVisibleBackgroundUsersEnabled()Z',
           'isVisibleBackgroundUsersOnDefaultDisplayEnabled()Z'], framework=True)
    query('user-stub-ctor', 'android.os.IUserManager$Stub', ['<init>()V'], framework=True)
    query('pms-factory-main', 'com.android.server.pm.PackageManagerService',
          ['main(Landroid/content/Context;Lcom/android/server/pm/Installer;Lcom/android/server/pm/verify/domain/DomainVerificationService;Z)Lcom/android/server/pm/PackageManagerService;'])
    query('pms-declarations', 'com.android.server.pm.PackageManagerService')
    query('ums-restriction-core', 'com.android.server.pm.UserManagerService',
          ['updateUserRestrictionsInternalLR(ILandroid/os/Bundle;)V'])
    query('user-manager-cache-invalidate', 'android.os.UserManagerCache', ['invalidateUserUnlocked()V'], framework=True)
    query('pms-constructors', 'com.android.server.pm.PackageManagerService',
          ['<init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V',
           '<init>(Lcom/android/server/pm/PackageManagerServiceInjector;Lcom/android/server/pm/PackageManagerServiceTestParams;)V'])
    query('pms-injector-bootstrap', 'com.android.server.pm.PackageManagerServiceInjector',
          ['bootstrap(Lcom/android/server/pm/PackageManagerService;)V'])
    query('pms-installd-stage', 'com.samsung.android.server.pm.lifecycle.PmLifecycleImpl',
          ['onInstalldStarting()V'])


def report():
    """Recheck saved bodies/receipts and exact edges; no new reader or OEM call."""
    inputs()
    proofs, receipts, raw_pins, query_pins = {}, {}, {}, {}
    body_cache = {}
    reused = json.loads((ROOT / 'inventory/user-registry-owner.json').read_text())
    base = json.loads((ROOT / 'inventory/authority-bootstrap-users.json').read_text())
    names = {'<init>(Landroid/content/Context;)V', FULL_CTOR, '<clinit>()V',
             'readUserListLP()V', 'readUserLP(II)Lcom/android/server/pm/UserManagerService$UserData;',
             'readUserLP(ILjava/io/InputStream;I)Lcom/android/server/pm/UserManagerService$UserData;',
             'getInstance()Lcom/android/server/pm/UserManagerService;', 'fallbackToSingleUserLP()V',
             'upgradeIfNecessaryLP(II)V', 'scheduleWriteUser(I)V',
             'writeUserLP(Lcom/android/server/pm/UserManagerService$UserData;)V',
             'writeUserListLP()V', 'ensurePerfettoUserListExistsLP()V', 'setContainerInfo()V',
             'getProfileIds(Ljava/lang/String;IZZ)[I'}
    for key, value in reused['methodProofs'].items():
        owner, signature = key.split(':', 1)[1].split('->', 1)
        if ((owner == UMS and signature in names) or
            owner in ['Lcom/android/server/pm/ResilientAtomicFile;',
                      'Lcom/android/server/pm/UserManagerService$MainHandler;',
                      'Lcom/samsung/android/server/pm/lifecycle/PmCustomInjector$Singleton;',
                      'Lcom/samsung/android/server/pm/lifecycle/PmCustomInjector$$ExternalSyntheticLambda0;'] or
            (owner == 'Lcom/android/server/pm/PersonaManagerService;' and 'getWorkTabSupportLauncherUids' in signature)):
            proofs[key] = dict(value)
    for key, value in base['methodProofs'].items():
        if key == 'samsung-services:Lcom/android/server/pm/UserManagerService$LocalService;->getUserInfo(I)Landroid/content/pm/UserInfo;':
            proofs[key] = dict(value)
    for name in QUERY_NAMES:
        path = WORK / (name + '.json')
        result = json.loads(path.read_text())
        query_pins[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path)
        receipt_path = ROOT / result['receipt']
        receipt = json.loads(receipt_path.read_text())
        need(result['archiveSha256'] == receipt['archiveSha256'] and
             receipt['archiveSha256'] in (ARCHIVE_SHA, FRAMEWORK_SHA), 'Query archive pin')
        need(receipt['readerExitCode'] == 0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] and
             not receipt['oemCodeExecuted'] and not receipt['androidExecuted'], 'Static reader disposition')
        need(sha(ROOT / receipt['raw']) == receipt['rawSha256'] == result['rawSha256'], 'Query raw pin')
        receipts[result['receipt']] = sha(receipt_path)
        raw_pins[receipt['raw']] = receipt['rawSha256']
        side = 'samsung-services' if receipt['archiveSha256'] == ARCHIVE_SHA else 'samsung-framework'
        for proof in receipt['selectedMethodProofs']:
            key = side + ':' + proof['owner'] + '->' + proof['signature']
            previous = proofs.get(key)
            if previous:
                need(previous['bodySha256'] == proof['normalizedBodySha256'], 'Repeated body mismatch')
            proofs[key] = {'bodySha256': proof['normalizedBodySha256'], 'raw': receipt['raw'],
                           'rawSha256': receipt['rawSha256'], 'receipt': result['receipt'],
                           'physicalDex': proof['physicalDex'], 'logicalHeaderOffset': proof['logicalHeaderOffset']}
    need(sha(ROOT / PEER_RECEIPT) == PEER_RECEIPT_SHA, 'Peer lifecycle receipt pin')
    peer = json.loads((ROOT / PEER_RECEIPT).read_text())
    need(peer['archiveSha256'] == ARCHIVE_SHA and peer['readerExitCode'] == 0 and
         not peer['oemCodeExecuted'] and not peer['androidExecuted'], 'Peer static source profile')
    need(sha(ROOT / peer['raw']) == peer['rawSha256'], 'Peer raw pin')
    receipts[PEER_RECEIPT] = PEER_RECEIPT_SHA
    raw_pins[peer['raw']] = peer['rawSha256']
    for proof in peer['selectedMethodProofs']:
        if proof['owner'] == UMS and proof['signature'] in ('onBeforeUnlockUser(I)V', 'onBeforeStartUser(I)V'):
            proofs['samsung-services:' + UMS + '->' + proof['signature']] = {
                'bodySha256': proof['normalizedBodySha256'], 'raw': peer['raw'], 'rawSha256': peer['rawSha256'],
                'receipt': PEER_RECEIPT, 'physicalDex': proof['physicalDex'],
                'logicalHeaderOffset': proof['logicalHeaderOffset']}
    for value in proofs.values():
        need(sha(ROOT / value['raw']) == value['rawSha256'], 'Selected raw proof pin')
        raw_pins[value['raw']] = value['rawSha256']
        receipt = json.loads((ROOT / value['receipt']).read_text())
        need(receipt['archiveSha256'] in (ARCHIVE_SHA, FRAMEWORK_SHA) and receipt['readerExitCode'] == 0 and
             receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] and not receipt['oemCodeExecuted'] and
             not receipt['androidExecuted'], 'Selected receipt disposition')
        receipts[value['receipt']] = sha(ROOT / value['receipt'])

    def body(owner, signature, side='samsung-services'):
        proof = proofs[side + ':' + owner + '->' + signature]
        if proof['raw'] not in body_cache:
            body_cache[proof['raw']] = {row['body']['owner'] + '->' + row['body']['signature']: row['body']
                for row in map(json.loads, (ROOT / proof['raw']).read_text().splitlines()) if row.get('record') == 'method'}
        return body_cache[proof['raw']][owner + '->' + signature]

    def at(b, pc):
        return next(instruction for instruction in b['instructions'] if instruction['pc'] == pc)

    assertions = []
    def check(name, condition):
        need(condition, name)
        assertions.append(name)

    constructor = body(UMS, FULL_CTOR)
    short = body(UMS, '<init>(Landroid/content/Context;)V')
    check('context-only-cache-root-and-null-pms', 'getCacheDir()' in at(short, 12)['reference'] and
          at(short, 18)['registers'] == [2] and at(short, 18)['literal'] == 0 and
          at(short, 22)['reference'] == UMS + '->' + FULL_CTOR)
    factory_owner = 'Lcom/android/server/pm/PackageManagerService$$ExternalSyntheticLambda39;'
    factory = body(factory_owner, 'produce(Lcom/android/server/pm/PackageManagerServiceInjector;Lcom/android/server/pm/PackageManagerService;)Ljava/lang/Object;')
    check('factory-captured-context-installer-install-and-package-locks',
          [at(factory, pc)['reference'].split('->')[1] for pc in (0, 2, 4, 6)] ==
          ['f$0:Landroid/content/Context;', 'f$1:Lcom/android/server/pm/Installer;',
           'f$2:Lcom/android/server/pm/PackageManagerTracedLock;', 'f$3:Lcom/android/server/pm/PackageManagerTracedLock;'])
    check('factory-real-data-preparer-fields', all('UserDataPreparer;->' in at(factory, pc)['reference'] for pc in (18, 20, 22)))
    check('factory-original-data-directory', at(factory, 34)['reference'] == 'Landroid/os/Environment;->getDataDirectory()Ljava/io/File;')
    check('factory-real-pms-and-persona-provenance', at(factory, 27)['reference'].endswith('PackageManagerService;->sPersonaManager:Lcom/android/server/pm/PersonaManagerService;') and
          at(factory, 39)['registers'] == [2, 11] and at(factory, 40)['registerStart'] == 0 and
          at(factory, 40)['registerCount'] == 9 and at(factory, 40)['reference'] == UMS + '->' + FULL_CTOR)
    factory_refs = json.loads((WORK / 'factory-reference.json').read_text())
    refs = [r for r in map(json.loads, (ROOT / factory_refs['raw']).read_text().splitlines()) if r.get('record') == 'reference']
    check('only-two-direct-full-ctor-callers-in-captured-services', factory_refs['referenceMatchCount'] == 2 and
          {r['caller'] for r in refs} == {UMS + '-><init>(Landroid/content/Context;)V', factory_owner + '->' + factory['signature']})
    pms_owner = 'Lcom/android/server/pm/PackageManagerService;'
    pms = body(pms_owner, '<init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)V')
    for pc, target, label in [
            (323, 'PackageManagerServiceInjector;->bootstrap(', 'pms-bootstrap-before-ums'),
            (420, 'PersonaManagerService;-><init>(', 'pms-constructs-real-persona-before-ums'),
            (432, 'LocalServices;->addService(', 'pms-registers-real-pmi-before-ums'),
            (442, 'LocalManagerRegistry;->addManager(', 'pms-registers-package-local-before-ums'),
            (462, 'PackageManagerService;->mCustomInjector:', 'pms-stores-custom-injector-before-ums'),
            (471, 'PmLifecycleImpl;->onInstalldStarting()', 'pms-installd-stage-before-ums'),
            (476, 'LocalServices;->addService(', 'pms-publishes-actual-pms-before-ums'),
            (489, 'PackageManagerServiceInjector;->getUserManagerService()', 'pms-production-ums-call')]:
        check(label, target in at(pms, pc)['reference'])
    check('pms-pmi-class-and-real-implementation', at(pms, 425)['reference'] == 'Landroid/content/pm/PackageManagerInternal;' and
          at(pms, 427)['reference'].endswith('PackageManagerService$PackageManagerInternalImpl;'))
    bootstrap = body('Lcom/android/server/pm/PackageManagerServiceInjector;', 'bootstrap(Lcom/android/server/pm/PackageManagerService;)V')
    check('injector-bootstrap-is-actual-pms-field-assignment', at(bootstrap, 0)['reference'].endswith('->mPackageManager:Lcom/android/server/pm/PackageManagerService;'))
    installd = body('Lcom/samsung/android/server/pm/lifecycle/PmLifecycleImpl;', 'onInstalldStarting()V')
    check('installd-stage-real-config-and-worker', 'RestrictedReceiverFilter;->enableAndConfigure' in at(installd, 9)['reference'] and
          '->submit(' in at(installd, 42)['reference'] and 'Future;->get(' in at(installd, 50)['reference'] and
          'Future;->cancel(' in at(installd, 94)['reference'])
    check('ums-stores-real-owners', all(word in at(constructor, pc)['reference'] for pc, word in
          [(228, '->mContext:'), (230, '->mPm:'), (238, '->mPackagesLock:'), (399, '->mUserDataPreparer:')]))
    check('direct-concrete-pms-read-is-handler-frontier', [i['pc'] for i in constructor['instructions']
          if i['pc'] < 1010 and i.get('reference', '').startswith('Lcom/android/server/pm/PackageManagerService;->')] == [254])
    check('preload-allocates-own-localservice-before-publication', at(constructor, 123)['reference'].endswith('UserManagerService$LocalService;') and
          '->this$0:' in at(constructor, 128)['reference'] and '->mLocalService:' in at(constructor, 133)['reference'])
    check('original-early-unlocked-cache-invalidation', 'invalidateIsUserUnlockedCache' in at(constructor, 206)['reference'])
    check('preload-real-executor-and-visibility', 'ThreadPoolExecutor;-><init>' in at(constructor, 377)['reference'] and
          'UserVisibilityMediator;-><init>' in at(constructor, 392)['reference'])
    check('global-resource-user-type-xml-before-load', 'Resources;->getSystem' in at(constructor, 405)['reference'] and
          at(constructor, 409)['literal'] == 18284553 and 'UserTypeFactory;->customizeBuilders' in at(constructor, 416)['reference'])
    check('mkdir-permissions-and-restrictions-before-load', all(word in at(constructor, pc)['reference'] for pc, word in
          [(962, '->mkdirs()'), (974, '->mkdirs()'), (984, 'FileUtils;->setPermissions'), (1007, '->initDefaultGuestRestrictions()')]))
    check('registry-before-singleton-and-local-publication', '->readUserListLP()' in at(constructor, 1010)['reference'] and
          '->sInstance:' in at(constructor, 1013)['reference'] and 'LocalServices;->addService' in at(constructor, 1076)['reference'])
    check('later-systemconfig-and-initial-map-not-initial-completeness', 'SystemConfig;->getInstance' in at(constructor, 1057)['reference'] and
          'determineAllowlistedPackagesForUserTypes' in at(constructor, 1061)['reference'] and
          'SparseIntArray;->put' in at(constructor, 1094)['reference'] and 'invalidateIsUserUnlockedCache' in at(constructor, 1097)['reference'])
    pmi = body(UMS, 'getPackageManagerInternal()Landroid/content/pm/PackageManagerInternal;')
    check('pmi-is-lazy-original-localservices-cache', at(pmi, 4)['reference'] == 'Landroid/content/pm/PackageManagerInternal;' and
          'LocalServices;->getService' in at(pmi, 6)['reference'] and '->mPmInternal:' in at(pmi, 12)['reference'])
    load = body(UMS, 'readUserListLP()V')
    check('registry-load-recovery-and-upgrades', all(word in at(load, pc)['reference'] for pc, word in
          [(7, '->openRead()'), (22, '->fallbackToSingleUserLP()'), (319, '->upgradeIfNecessaryLP('),
           (337, '->writeUserLP('), (343, '->writeUserListLP()'), (386, '->failRead('), (389, '->readUserListLP()')]))
    upgrade = body(UMS, 'upgradeIfNecessaryLP(II)V')
    check('load-upgrade-reaches-real-restriction-setters', all('->setUserRestriction(' in at(upgrade, pc)['reference'] for pc in (308, 863, 871)))
    restrictions = body(UMS, 'setUserRestriction(Ljava/lang/String;ZI)V')
    check('restriction-setter-checks-and-real-policy-posts', 'checkManageUsersPermission' in at(restrictions, 3)['reference'] and
          'updateUserRestrictionsInternalLR' in at(restrictions, 52)['reference'] and
          'IRestrictionPolicy;->updateUserRestrictionsByKC' in at(restrictions, 78)['reference'] and
          'Handler;->post' in at(restrictions, 127)['reference'])
    restriction_core = body(UMS, 'updateUserRestrictionsInternalLR(ILandroid/os/Bundle;)V')
    check('restriction-core-schedules-persistence-and-original-children', 'scheduleWriteUser' in at(restriction_core, 59)['reference'] and
          'Handler;->post' in at(restriction_core, 96)['reference'] and 'Handler;->post' in at(restriction_core, 134)['reference'])
    profiles = body(UMS, 'getProfileIds(Ljava/lang/String;IZZ)[I')
    check('required-profile-query-real-persona-frontier', 'sPersonaManager:' in at(profiles, 24)['reference'] and
          'Object;->getClass()' in at(profiles, 26)['reference'] and 'workTabSupportLauncherUids' in at(profiles, 29)['reference'])
    unlocking = body(UMS, 'onBeforeUnlockUser(I)V')
    check('lifecycle-common-sms-path-is-not-dualdar-only', at(unlocking, 53)['targetPc'] == 132 and at(unlocking, 60)['targetPc'] == 132 and
          'UserDataPreparer;->prepareUserData' in at(unlocking, 43)['reference'])
    check('lifecycle-requires-concrete-sms-and-pmi', any('StorageManagerService$StorageManagerInternalImpl;' in i.get('reference', '')
          for i in unlocking['instructions'] if 132 <= i['pc'] <= 163) and
          any('mCeStoragePreparedUsers' in i.get('reference', '') for i in unlocking['instructions'] if 132 <= i['pc'] <= 163) and
          any('reconcileAppsData' in i.get('reference', '') for i in unlocking['instructions'] if 185 <= i['pc'] <= 189))
    value = {
        'schema': 'samsung-user-registry-owner/v1', 'status': 'NO_STANDALONE_COLD_CONSTRUCTION_CONTRACT',
        'selected': False, 'oemExecuted': False, 'androidExecuted': False, 'nativeExecuted': False,
        'privateRegistryRead': False, 'phoneActions': [], 'runtimeCodeAdded': False,
        'sourceArchive': {'path': str(ARCHIVE), 'sha256': ARCHIVE_SHA},
        'frameworkArchive': {'path': str(FRAMEWORK), 'sha256': FRAMEWORK_SHA},
        'reusedInventoryPins': BASE_PINS, 'queryPins': query_pins, 'receiptPins': receipts,
        'rawPins': raw_pins, 'methodProofs': proofs, 'selectedCodeBodies': len(proofs),
        'assertions': assertions, 'assertionCount': len(assertions),
        'factory': {'directFullConstructorCallers': 2, 'production': factory_owner + '->' + factory['signature'],
                    'productionArguments': ['actual Context', 'actual in-construction PMS',
                        'actual Installer/installLock/Context-backed UserDataPreparer', 'original UserJourneyLogger',
                        'actual packagesLock', 'Environment.getDataDirectory()', 'null sparse users argument', 'actual PMS.sPersonaManager'],
                    'contextOnlyIsProductionEquivalent': False},
        'firstUnmodifiedBlocker': 'Context-only null PMS dereference at full constructor254, before registry load1010; wrong cache-root argument also remains',
        'narrowHandlerRetargetIsExecutableOwnerClosure': False,
        'realPmsRouteBeforeUms': ['injector.bootstrap323', 'PersonaManagerService constructor420',
            'PackageManagerInternalImpl publication432', 'PackageManagerLocal442', 'PmCustomInjector459/462',
            'PmLifecycleImpl.onInstalldStarting471', 'PMS LocalServices476', 'getUserManagerService489'],
        'earliestPersistentRegistryAdmission': 'before mkdir962/974 and permissions984, not merely before readUserListLP1010 or publication',
        'loadDisposition': 'real recovery/fallback/upgrade/write, original queued restriction/persistence children; no readonly assumption',
        'retainedAlternative': {'owner': 'same original live system_server UMS/UMI/PMS/Persona/UserDataPreparer/SMS cohort',
            'capture': 'same-process source-owned actual UMS.getInstance, LocalServices UMI and PMS.mUserManager identity/lifetime; no Java-object transfer by name',
            'requires': ['six retained-authority topology gates', 'real live original registry/type/config/policy owner',
                         'required guest lifecycle beforeStart/beforeUnlock/CE behavior and original child/persistence/native drain'],
            'selected': False},
        'nextEngineeringAction': 'design one offline retained-original-owner capture/control cut before OneOS stop971; prove actual original UMS/UMI/PMS/Persona/SMS object and worker/view relationships, then root chooses topology; do not emit new cold handler/root patches',
        'limits': ['no complete transitive PMS/Persona/SystemConfig/Knox graph audit or blanket whole-SystemServer conclusion',
                   'current installed/live state and effective overlays unknown',
                   'query-only original registry retarget is not complete active-user lifecycle',
                   'class/descriptor/UID1000 and copied records do not establish authority',
                   'all18 end requirements remain'],
        'toolSha256': sha(Path(__file__)),
    }
    write(ROOT / 'inventory/samsung-user-registry-owner.json', value)
    write(WORK / 'audit-result.json', {'pass': True, 'status': value['status'],
          'assertions': len(assertions), 'selectedCodeBodies': len(proofs),
          'inventorySha256': sha(ROOT / 'inventory/samsung-user-registry-owner.json'),
          'oemOrRuntimeExecuted': False})
    print(json.dumps({'pass': True, 'status': value['status'], 'assertions': len(assertions),
                      'selectedCodeBodies': len(proofs)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--report', action='store_true')
    options = parser.parse_args()
    if options.capture:
        capture()
    if options.report:
        report()
    if not options.capture and not options.report:
        parser.error('Use --capture for selected static reads or --report for saved-proof validation')


if __name__ == '__main__':
    main()
