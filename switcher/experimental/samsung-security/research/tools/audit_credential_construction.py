"""Bounded source-only LockSettings construction frontier; no OEM execution."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'out/construction-credentials'
BASE = 'com.android.server.locksettings.'
SELECT = {
    BASE + 'LockSettingsService': ['<clinit>', 'systemReady'],
    BASE + 'SyntheticPasswordManager': ['<clinit>'],
    BASE + 'LockSettingsService$DeviceProvisionedObserver': ['<init>', 'isProvisioned', 'onChange', 'updateRegistration'],
    BASE + 'RebootEscrowManager': ['<init>'],
    BASE + 'recoverablekeystore.PlatformKeyManager': ['<clinit>', '<init>', 'getInstance'],
    BASE + 'recoverablekeystore.storage.ApplicationKeyStorage': ['<init>', 'getInstance', 'deleteEntry'],
    BASE + 'recoverablekeystore.storage.CleanupManager': ['<init>', 'verifyKnownUsers', 'removeDataForUser', 'storeUserSerialNumber'],
    BASE + 'recoverablekeystore.KeyStoreProxyImpl': ['<init>', 'deleteEntry'],
    BASE + 'recoverablekeystore.RecoverableKeyStoreManager': ['<init>'],
    'com.android.server.biometrics.BiometricHandlerProvider': ['<clinit>', 'getBiometricCallbackHandler', 'getNewHandler'],
}
FRAMEWORK_SELECT = {
    'com.samsung.android.knox.dar.ddar.DualDarAuthUtils': ['<init>'],
    'com.samsung.android.knox.dar.VirtualLockUtils': ['<init>'],
    'com.samsung.android.feature.SemFloatingFeature': ['<clinit>', '<init>', 'getInstance', 'getBoolean', 'loadFeatureFile'],
}

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def collect():
    previous = json.loads((ROOT / 'inventory/credentials.json').read_text(encoding='utf-8'))
    info = previous['inputs']['samsung']
    archive, index = ROOT.parent / info['archive'], ROOT.parent / info['declarations']
    if digest(archive) != info['archiveSha256'] or digest(index) != info['declarationsSha256']:
        raise ValueError('Immutable archive/index drift')
    selected = {}
    with gzip.open(index, 'rt', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            name = row.get('descriptor', '')[1:-1].replace('/', '.')
            if name in SELECT:
                methods = [m['name'] + m['descriptor'] for m in row['methods'] if m['name'] in SELECT[name]]
                if name in selected or not methods:
                    raise ValueError('Missing/ambiguous selector ' + name)
                selected[name] = methods
    if set(selected) != set(SELECT):
        raise ValueError('Missing selected owner')
    inputs = {'services': info}
    all_selected = [(info, name, methods) for name, methods in selected.items()]
    ledger = {r['id']: r for r in json.loads((ROOT / 'inventory/inputs.json').read_text(encoding='utf-8'))['files']}
    a, d = ledger['samsung-framework'], ledger['samsung-framework-declarations']
    framework = {'archive': a['path'], 'archiveSha256': a['sha256'], 'declarations': d['path'], 'declarationsSha256': d['sha256']}
    inputs['framework'] = framework
    if digest(ROOT.parent / a['path']) != a['sha256'] or digest(ROOT.parent / d['path']) != d['sha256']:
        raise ValueError('Framework archive/index drift')
    found = set()
    with gzip.open(ROOT.parent / d['path'], 'rt', encoding='utf-8') as f:
        for line in f:
            row = json.loads(line)
            name = row.get('descriptor', '')[1:-1].replace('/', '.')
            if name in FRAMEWORK_SELECT:
                if name in found:
                    raise ValueError('Ambiguous framework owner')
                found.add(name)
                all_selected.append((framework, name, [m['name'] + m['descriptor'] for m in row['methods'] if m['name'] in FRAMEWORK_SELECT[name]]))
    if found != set(FRAMEWORK_SELECT):
        raise ValueError('Missing framework owner')
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    rows = []
    for info, name, methods in all_selected:
        archive = ROOT.parent / info['archive']
        old = None
        for p in (ROOT / 'out/tooling').glob('*/receipt.json'):
            r = json.loads(p.read_text(encoding='utf-8'))
            if (r['archiveSha256'] == info['archiveSha256']
                    and r['raw'].startswith('firmware/construction-credentials/')
                    and r['query']['class'] == 'L' + name.replace('.', '/') + ';'
                    and set(r['query']['exactMethods']) == set(methods)
                    and r['readerExitCode'] == 0 and digest(ROOT / r['raw']) == r['rawSha256']):
                old = {**r, 'receipt': p.relative_to(ROOT).as_posix()}
                break
        r = old or read(archive, info['archiveSha256'], class_name=name, methods=methods, stream='construction-credentials')
        rows.append({'class': name, 'archiveSha256': info['archiveSha256'], 'receipt': r['receipt'], 'raw': r['raw'], 'rawSha256': r['rawSha256']})
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / 'receipts.json').write_text(json.dumps({'inputs': inputs, 'queries': rows}, indent=2) + '\n', encoding='utf-8')
        print(name, len(methods), flush=True)

def report():
    collection = json.loads((WORK / 'receipts.json').read_text(encoding='utf-8'))
    for info in collection['inputs'].values():
        if (digest(ROOT.parent / info['archive']) != info['archiveSha256']
                or digest(ROOT.parent / info['declarations']) != info['declarationsSha256']):
            raise ValueError('Construction archive/index drift')
    previous_path = ROOT / 'inventory/credentials.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    methods, bodies, receipts = {}, {}, {}
    def load(q, chosen=None, reused=False):
        path = ROOT / q['receipt']
        r = json.loads(path.read_text(encoding='utf-8'))
        if (r['readerExitCode'] or not r['archiveAndToolPinsVerifiedBeforeAndAfter']
                or r['raw'] != q['raw'] or digest(ROOT / r['raw']) != r['rawSha256']):
            raise ValueError('Receipt/raw verification failed')
        if (r['archiveSha256'] not in {i['archiveSha256'] for i in collection['inputs'].values()}
                or ('archiveSha256' in q and q['archiveSha256'] != r['archiveSha256'])):
            raise ValueError('Receipt archive identity mismatch')
        receipts[q['receipt']] = digest(path)
        for line in (ROOT / r['raw']).read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['record'] != 'method':
                continue
            b = row['body']
            key = b['owner'] + '->' + b['signature']
            if chosen is not None and key not in chosen:
                continue
            bodies[key] = b
            methods[key] = {'bodySha256': row['normalizedBodySha256'], 'archiveSha256': r['archiveSha256'],
                            'physicalDex': row['physicalDex'], 'logicalHeaderOffset': row['logicalHeaderOffset'],
                            'hasCode': b['hasCode'], 'reused': reused, 'raw': r['raw'], 'rawSha256': r['rawSha256'],
                            'receipt': q['receipt'], 'calls': [{'pcHex': hex(i['pc']), 'target': i['reference']}
                            for i in b['instructions'] if i['opcode'].startswith('INVOKE')]}
    for q in collection['queries']:
        load(q)
    grouped = {}
    for key, p in previous['methodProofs'].items():
        if not key.startswith('samsung:'):
            continue
        owner_method = key.split(':', 1)[1]
        if (('LockSettingsService$Lifecycle;' in key or 'LockSettingsService$Injector;' in key)
                or ('LockSettingsService;-><init>' in key)
                or ('LockSettingsStrongAuth;-><init>' in key)
                or ('LockSettingsStrongAuth$Injector;' in key)
                or ('LockSettingsStorage$DatabaseHelper;-><init>' in key)):
            g = grouped.setdefault(p['receipt'], {'receipt': p['receipt'], 'raw': p['raw'], 'selected': set()})
            g['selected'].add(owner_method)
    for q in grouped.values():
        load(q, q['selected'], reused=True)
    facts = {}
    def fact(label, owner, prefix, checks, meaning):
        matches = [k for k in bodies if k.startswith('L' + owner.replace('.', '/') + ';->' + prefix)]
        if len(matches) != 1:
            raise ValueError('Exact unique body required: ' + label)
        key = matches[0]
        ins = {i['pc']: i for i in bodies[key]['instructions']}
        checked = []
        for pc, field, expected in checks:
            actual = ins[pc][field]
            if actual != expected:
                raise ValueError('Source assertion drift: ' + label + '@' + hex(pc))
            checked.append({'pcHex': hex(pc), field: actual})
        facts[label] = {'classification': 'observed-source', 'method': key, 'meaning': meaning, 'checked': checked}
    c = BASE + 'recoverablekeystore.storage.CleanupManager'
    fact('coldSingletonGuard', BASE + 'LockSettingsService', '<init>(', [(0xbf, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/RecoverableKeyStoreManager;->mInstance:Lcom/android/server/locksettings/recoverablekeystore/RecoverableKeyStoreManager;'), (0xc1, 'opcode', 'IF_NEZ'), (0xc1, 'targetPc', 0x17b)], 'Existing singleton skips cold creation; its state provenance is separately required')
    fact('synchronousRecoverableCleanup', BASE + 'recoverablekeystore.RecoverableKeyStoreManager', '<init>(', [(0x1a, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;->verifyKnownUsers()V')], 'Cold manager construction performs user reconciliation synchronously')
    fact('cleanupUserSerialDecisions', c, 'verifyKnownUsers(', [(0x32, 'literal', -1), (0x47, 'reference', 'Landroid/os/UserManager;->getSerialNumberForUser(Landroid/os/UserHandle;)J'), (0x4b, 'registers', [8, 6, 4]), (0x4d, 'opcode', 'IF_NEZ'), (0x4d, 'targetPc', 0x5a), (0x56, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;->removeDataForUser(I)V'), (0x60, 'opcode', 'IF_NEZ'), (0x60, 'targetPc', 0x6a), (0x66, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;->storeUserSerialNumber(IJ)V'), (0x6e, 'registers', [2, 4, 6]), (0x70, 'opcode', 'IF_EQZ'), (0x70, 'targetPc', 0x1a), (0x79, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;->removeDataForUser(I)V'), (0x80, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;->storeUserSerialNumber(IJ)V')], 'Missing live user (-1) or changed known serial can remove recoverable state; unknown recorded serial is initialized')
    fact('cleanupActualDeletes', c, 'removeDataForUser(', [(0x31, 'reference', 'Ljava/io/File;->delete()Z'), (0x5b, 'reference', 'Lcom/android/server/locksettings/recoverablekeystore/storage/ApplicationKeyStorage;->deleteEntry(IILjava/lang/String;)V'), *[(pc, 'reference', 'Landroid/database/sqlite/SQLiteDatabase;->delete(Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;)I') for pc in (0x95, 0xa7, 0xb9, 0xcb)]], 'Deletes snapshots, recoverable app-key entries and user rows in four tables')
    fact('cleanupActualKeyDelete', BASE + 'recoverablekeystore.storage.ApplicationKeyStorage', 'deleteEntry(', [(0x1a, 'reference', 'Ljava/security/KeyStore;->deleteEntry(Ljava/lang/String;)V')], 'Actual KeyStore deletion, not metadata-only cleanup')
    fact('cleanupSerialWrite', c, 'storeUserSerialNumber(', [(0x49, 'reference', 'Landroid/database/sqlite/SQLiteDatabase;->update(Ljava/lang/String;Landroid/content/ContentValues;Ljava/lang/String;[Ljava/lang/String;)I')], 'Reconciliation also writes authoritative serial metadata')
    fact('coldBiometricHandlerStartsThread', 'com.android.server.biometrics.BiometricHandlerProvider', 'getNewHandler(', [(5, 'reference', 'Landroid/os/HandlerThread;->start()V')], 'Cold callback handler creation owns a started thread')
    for label, owner, pc in [('platformKeyStoreEagerLoad', BASE + 'recoverablekeystore.PlatformKeyManager', 0xf), ('applicationKeyStoreEagerLoad', BASE + 'recoverablekeystore.storage.ApplicationKeyStorage', 0xb)]:
        fact(label, owner, 'getInstance(', [(pc, 'reference', 'Ljava/security/KeyStore;->load(Ljava/security/KeyStore$LoadStoreParameter;)V')], 'Loads a separate AndroidKeyStore using null load parameters in this body')
    fact('spmEagerSamsungFeature', BASE + 'SyntheticPasswordManager', '<clinit>(', [(0x16, 'reference', 'string=SEC_FLOATING_FEATURE_COMMON_SUPPORT_UNPACK'), (0x19, 'reference', 'Lcom/samsung/android/feature/SemFloatingFeature;->getBoolean(Ljava/lang/String;)Z')], 'Class initialization consumes real Samsung feature policy')
    fact('floatingFeatureEagerFile', 'com.samsung.android.feature.SemFloatingFeature', 'loadFeatureFile(', [(8, 'reference', 'string=/system/etc/floating_feature.xml'), (0x2d, 'reference', 'Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V')], 'Cold singleton parses an absolute configuration path')
    fact('provisionedCallbackMutation', BASE + 'LockSettingsService$DeviceProvisionedObserver', 'onChange(', [(0x22, 'reference', 'Landroid/service/gatekeeper/IGateKeeperService;->reportDeviceSetupComplete()V'), (0x6f, 'reference', 'Lcom/android/server/locksettings/LockSettingsStorage;->writePersistentDataBlock(III[B)V')], 'Deferred real settings callback can report setup and conditionally clear FRP data')
    fact('systemReadyIsActive', BASE + 'LockSettingsService', 'systemReady(', [(0x2f, 'reference', 'Lcom/android/server/locksettings/LockSettingsService;->migrateLockSettingsDB()V'), (0x32, 'reference', 'Lcom/android/server/locksettings/LockSettingsService;->migrateSpblob()V'), (0xaa, 'reference', 'Lcom/android/server/locksettings/SyntheticPasswordManager;->migrateKeyNamespace()Z'), (0x12b, 'reference', 'Landroid/os/ServiceManager;->waitForDeclaredService(Ljava/lang/String;)Landroid/os/IBinder;')], 'systemReady is a separate active stage, not a readiness getter')
    frontier = [
        {'stage': 'before-first-LSS-construction', 'binding': 'same-authority UserManager serials, recoverable DB/snapshots, default AndroidKeyStore backend and namespace', 'reason': 'synchronousRecoverableCleanup', 'status': 'actual-runtime-owner-unselected'},
        {'stage': 'before-SPM-class-initialization', 'binding': 'Samsung floating feature input and canonical feature singleton provenance', 'reason': 'spmEagerSamsungFeature', 'status': 'source-path-known-runtime-policy-unproven'},
        {'stage': 'before-LSS-construction', 'binding': 'Context/resources, application Context, main Looper, NotificationManager, ActivityManager, UserManager, mount IStorageManager, concrete storage local service, supervision local service', 'reason': 'reused constructor/StrongAuth bodies', 'status': 'actual-runtime-objects-unselected'},
        {'stage': 'before-publication', 'binding': 'one canonical LocalServices registry and free LockSettingsInternal key; compatible lock_settings Binder publication', 'reason': 'reused constructor/lifecycle bodies', 'status': 'handoff-and-registration-not-implemented'},
        {'stage': 'before-systemReady-and-boot-phases', 'binding': 'authoritative paths/users, FRP, Gatekeeper/Weaver/AuthSecret, KeyStore/native registrations, DAR and actual biometric services', 'reason': 'systemReadyIsActive and reused phase bodies', 'status': 'transitive-native-state-and-policy-bindings-open'},
        {'stage': 'before-any-activation', 'binding': 'retained thread/receiver/handler/executor/observer ownership and failed-partial-construction recovery', 'reason': 'constructor publishes local service only after earlier external effects', 'status': 'no-stop-or-rollback-protocol-demonstrated'},
    ]
    result = {'schema': 'credential-construction-frontier/v1', 'sourceAssertionsPass': True,
              'inputs': collection['inputs'], 'reusedInventory': {'path': 'inventory/credentials.json', 'sha256': digest(previous_path)},
              'newCodeBodies': sum(not p['reused'] for p in methods.values()), 'reusedCodeBodies': sum(p['reused'] for p in methods.values()),
              'methods': methods, 'readerReceipts': receipts, 'sourceFacts': facts, 'requiredBindings': frontier,
              'closureStatus': 'bounded newly inspected source frontier; actual owner/native/state closure remains open',
              'ownerAlternatives': [
                  {'candidate': 'original Samsung LSS construction path', 'status': 'observed constructor requires its eager dependencies and mutation ownership; full system_server necessity not established'},
                  {'candidate': 'smaller coherent Samsung owner behind adapted ColorOS clients', 'status': 'permitted design alternative; must prove real SP/credential/policy/native/key ownership and source-preserving replacement of reached construction obligations; not implemented'},
                  {'candidate': 'remove optional unsupported OPPO features and background work', 'status': 'permitted only with real core-path, policy, caller and teardown evidence; optional donor features do not become Samsung constructor requirements'}],
              'runtimeVerified': False, 'oemExecuted': False, 'phoneActions': False,
              'limits': ['Selected exact methods only, not complete transitive closure', 'Native declarations/initialization and effective resources/configuration need independent owner evidence', 'A cast or stored null does not alone establish successful or impossible construction', 'Cold and warm singleton paths require separate state provenance; never reset the singleton as a workaround']}
    p = ROOT / 'inventory/construction-credentials.json'
    p.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'newBodies': result['newCodeBodies'], 'reusedBodies': result['reusedCodeBodies'], 'facts': len(facts), 'sha256': digest(p)}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.collect:
        collect()
    if args.report:
        report()
