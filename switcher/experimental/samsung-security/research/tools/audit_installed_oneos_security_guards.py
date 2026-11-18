"""Recheck bounded, saved staged-DEX guard evidence; never invoke a DEX reader or OEM.

The collection manifests are immutable inputs from completed static-reader jobs.
This tool hashes archives and parses their saved JSON records only. It does not
execute the upstream patch producers, rebuild JARs, or inspect a device.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / 'out/installed-oneos-security-guards'
COLLECTIONS = {
    'body-collection.json': 'ac3ffbaa2c272c63c7280503308f67c0b284a5ac7ccdde5d98a58fd00d0f736c',
    'frontdoor-collection.json': '47ca1f8308c5eb25ee7af84bf7edaff70ff4534d0309927aea2929349d0431fa',
    'oplus-body-collection.json': '4b8a82f23e263c036464febcda09a6c6d3aa97033ba6aa95a4c6d6a6be8f90ea',
    'oplus-reference-collection.json': 'b4ff117bc4a4574b8fa8d0144b5402a06d191a15c5729b9cb00bc3bf46073950',
    'reference-collection.json': '02cedcdbdaad42654347f74678d7371deea983cdf07bca8d064d0d9c7e46efb8',
    'startup-collection.json': '36554401c60e0b3bb210fe2ae66211960489a5f9596026ce8478997bd688eb3a',
    'vold-reference-collection.json': '8d264a44549100b3d3a86d97259b118400bb7ca82303a1823db934b7002e8796',
}
ACQUISITION = 'out/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/acquisition.json'
ACQUISITION_SHA = 'ad6b1d7aaa79a17f2745c52a347a660b1d70bef7956a4354f6feb997417e0d23'
STAGED_DIR = 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/'
ARCHIVES = {
    'original-services': ('../firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
    'original-framework': ('../firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'original-oplus': ('../firmware/donor/extracted/system/framework/oplus-services.jar', 'cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39'),
    'staged-services': (STAGED_DIR + 'services_patched.jar', 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'),
    'staged-framework': (STAGED_DIR + 'framework_patched.jar', '5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246'),
    'staged-oplus': (STAGED_DIR + 'oplus-services_patched.jar', 'a854468fec404a8950f8f3c651f869f19ded098bb244fbef26880c2ece141fa8'),
}
PATCH_DIR = 'firmware/method-review-upstream/1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe/switcher/patches/'
PATCHES = {
    'guest_no_gatekeeper.py': '7c1e54b5d4f667b3f102a629a99b030130cb3320c03a2c3a712af3538a3f1dc9',
    'guest_no_weaver.py': 'd07c2a7c550eef87c9c43a1864987c1dc776f192880ed68b6c310e06e4da2439',
    'guest_no_vold_keys.py': '442027bf3f5b80ba0086460f84dd54cae9040872fa935452b80eccf4e3b01658',
    'guest_no_biometric_cleanup.py': '2ee50961b2855cecda4fbc7f1261194204c5b3a39bf1488429db939d286f6de9',
}
LSS = 'Lcom/android/server/locksettings/LockSettingsService;'
SPM = 'Lcom/android/server/locksettings/SyntheticPasswordManager;'
SMS = 'Lcom/android/server/StorageManagerService;'
INTERNAL = 'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;'
GK = 'Landroid/service/gatekeeper/IGateKeeperService;'
VOLD = 'Landroid/os/IVold;'
KEY_OPS = {'createUserStorageKeys', 'destroyUserStorageKeys', 'setCeStorageProtection', 'unlockCeStorage', 'lockCeStorage'}


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def pin(relative, expected=None):
    path = ROOT / relative
    value = digest(path)
    if expected is not None:
        assert value == expected, (relative, value, expected)
    return {'path': relative, 'sha256': value, 'size': path.stat().st_size}


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def main():
    pins = {ACQUISITION: pin(ACQUISITION, ACQUISITION_SHA)}
    archives = {name: pin(path, sha) for name, (path, sha) in ARCHIVES.items()}
    assert [archives[n]['size'] for n in ('staged-services', 'staged-framework', 'staged-oplus')] == [44699364, 52377761, 30364137]
    for name, sha in PATCHES.items():
        path = PATCH_DIR + name
        pins[path] = pin(path, sha)
    collections = {}
    for name, sha in COLLECTIONS.items():
        path = 'out/installed-oneos-security-guards/' + name
        pins[path] = pin(path, sha)
        collections[name] = load(path)
    raw_cache = {}
    proofs = []
    methods = {}

    def evidence(item):
        raw = item['raw']
        pins[raw] = pin(raw, item['rawSha256'])
        receipt = item['receipt']
        pins[receipt] = pin(receipt)
        r = load(receipt)
        assert (r['raw'], r['rawSha256']) == (raw, item['rawSha256'])
        assert r['archiveSha256'] in {v[1] for v in ARCHIVES.values()}
        if 'archiveSha256' in item:
            assert r['archiveSha256'] == item['archiveSha256']
        if raw not in raw_cache:
            raw_cache[raw] = [json.loads(line) for line in (ROOT / raw).read_text(encoding='utf-8').splitlines()]
        return raw_cache[raw]

    def add(item, metadata):
        rows = evidence(item)
        hits = [r for r in rows if r['record'] == 'method' and r['body']['owner'] == metadata['owner'] and r['body']['signature'] == metadata['signature']]
        assert len(hits) == 1
        row = hits[0]
        assert row['normalizedBodySha256'] == metadata['normalizedBodySha256']
        assert row['body']['hasCode']
        key = (item['profile'], metadata['owner'], metadata['signature'])
        assert key not in methods
        methods[key] = row['body']
        proofs.append({
            'profile': item['profile'], 'owner': metadata['owner'], 'signature': metadata['signature'],
            'accessFlags': row['body']['accessFlags'], 'registerCount': row['body']['registerCount'],
            'physicalDex': row['physicalDex'], 'logicalHeaderOffset': row['logicalHeaderOffset'],
            'instructionCount': len(row['body']['instructions']), 'tryHandlerCount': len(row['body']['catches']),
            'normalizedBodySha256': row['normalizedBodySha256'],
            'receipt': item['receipt'], 'raw': item['raw'], 'rawSha256': item['rawSha256'],
        })

    for item in collections['body-collection.json']['bodies']:
        add(item, item)
    for name in ('frontdoor-collection.json', 'oplus-body-collection.json'):
        for item in collections[name]:
            add(item, item['method'])
    for item in collections['startup-collection.json']:
        for metadata in item['methods']:
            add(item, metadata)
    assert len(proofs) == 50

    def body(profile, owner, prefix):
        hits = [v for (p, o, sig), v in methods.items() if p == profile and o == owner and sig.startswith(prefix)]
        assert len(hits) == 1, (profile, owner, prefix, len(hits))
        return hits[0]

    def at(b, pc, opcode=None, suffix=None, literal=None):
        hits = [i for i in b['instructions'] if i['pc'] == pc]
        assert len(hits) == 1, (b['signature'], pc)
        ins = hits[0]
        if opcode:
            assert ins['opcode'] == opcode, (b['signature'], pc, ins)
        if suffix:
            assert ins.get('reference', '').endswith(suffix), (b['signature'], pc, ins)
        if literal is not None:
            assert ins['literal'] == literal
        return ins

    facts = []
    def fact(name, **data):
        facts.append({'name': name, **data})

    for prefix in ('setLockCredentialInternal(', 'setLockCredentialWithTokenInternalLocked('):
        b = body('staged', LSS, prefix)
        assert [i['opcode'] for i in b['instructions'][:5]] == ['CONST_STRING', 'CONST_STRING', 'INVOKE_STATIC', 'CONST_4', 'RETURN']
        at(b, 4, suffix='Slog;->w(Ljava/lang/String;Ljava/lang/String;)I')
        zero = at(b, 7, 'CONST_4', literal=0)
        assert at(b, 8, 'RETURN')['registers'] == zero['registers']
        assert b['instructions'][5]['pc'] == 9
        assert all(c['startPc'] >= 9 for c in b['catches'])
        fact('setter-entry-false', method=b['signature'], returnPc=8, originalTailStartPc=9, scope='normal prefix completion; logging exceptions are not success')
    b = body('staged', SPM, 'getWeaverServiceLocked(')
    assert [i['opcode'] for i in b['instructions'][:5]] == ['CONST_STRING', 'CONST_STRING', 'INVOKE_STATIC', 'CONST_4', 'RETURN_OBJECT']
    at(b, 7, 'CONST_4', literal=0)
    at(b, 8, 'RETURN_OBJECT')
    assert all(c['startPc'] >= 9 for c in b['catches'])
    fact('weaver-getter-null', returnPc=8, originalTailStartPc=9, scope='this getter only; not all Weaver owners')

    reference_sets = {}
    excluded = []
    for name in ('reference-collection.json', 'vold-reference-collection.json', 'oplus-reference-collection.json'):
        for item in collections[name]:
            if name == 'reference-collection.json' and item['kind'] == 'vold':
                evidence(item)
                excluded.append({'receipt': item['receipt'], 'reason': 'invalid prefix selector IVold;-> is an exact-member query, not an owner query; zero is not absence evidence'})
                continue
            rows = evidence(item)
            invokes = [r for r in rows if r['record'] == 'reference' and r['instruction']['opcode'].startswith('INVOKE') and r['instruction'].get('referenceKind') == 'method']
            kind = ('vold' if item.get('kind', '').startswith('vold') else item.get('kind')) or {
                GK: 'gatekeeper', VOLD: 'vold', 'Landroid/hardware/weaver/IWeaver;': 'weaver',
            }[item['owner']]
            reference_sets[(item['profile'], kind)] = invokes
    assert len(excluded) == 2
    gko = reference_sets[('original', 'gatekeeper')]
    gks = reference_sets[('staged', 'gatekeeper')]
    assert (len(gko), len(gks)) == (17, 9)
    def opname(row):
        return row['instruction']['reference'].split('->')[1].split('(')[0]
    removed_counts = Counter(opname(r) for r in gko) - Counter(opname(r) for r in gks)
    assert dict(removed_counts) == {'clearSecureUserId': 3, 'reportDeviceSetupComplete': 1, 'enroll': 4}
    assert Counter(opname(r) for r in gks)['verifyChallenge'] == 3
    fact('gatekeeper-frontier', originalInvokeCount=17, stagedInvokeCount=9, removed=dict(removed_counts), remainingVerifyChallenge=3,
         remaining=[{'caller': r['caller'], 'pc': r['instruction']['pc'], 'reference': r['instruction']['reference']} for r in gks],
         scope='archive direct invokes; verification is not classified read-only')
    for prefix, original_pc, staged_pc in [
        ('createLskfBasedProtector(', 215, 213), ('newSidForUser(', 5, 5),
        ('unlockLskfBasedProtector(', 435, 435), ('verifyChallengeInternal(', 49, 49),
    ]:
        original = body('original', SPM, prefix)
        staged = body('staged', SPM, prefix)
        call = at(original, original_pc, 'INVOKE_INTERFACE', 'IGateKeeperService;->enroll(I[B[B[B)Landroid/service/gatekeeper/GateKeeperResponse;')
        original_result = at(original, original_pc + call['codeUnits'], 'MOVE_RESULT_OBJECT')
        at(staged, staged_pc, 'NOP')
        replacement = at(staged, staged_pc + 1, 'CONST_4', literal=0)
        assert replacement['registers'] == original_result['registers']
        fact('enroll-null-response-replacement', method=staged['signature'], originalInvokePc=original_pc,
             stagedNopPc=staged_pc, stagedNullPc=staged_pc + 1, responseRegisters=replacement['registers'])
    for owner, prefix, pc in [
        (LSS, 'gateKeeperClearSecureUserId(', 4),
        ('Lcom/android/server/locksettings/LockSettingsService$DeviceProvisionedObserver;', 'reportDeviceSetupComplete(', 6),
        (SPM, 'createLskfBasedProtector(', 183), (SPM, 'removeUser(', 43),
    ]:
        at(body('staged', owner, prefix), pc, 'NOP')
        fact('gatekeeper-void-call-nop', owner=owner, method=body('staged', owner, prefix)['signature'], pc=pc)
    vo = reference_sets[('original', 'vold')]
    vs = reference_sets[('staged', 'vold')]
    assert (len(vo), len(vs)) == (78, 61)
    assert sum(opname(r) in KEY_OPS for r in vo) == 5
    assert not any(opname(r) in KEY_OPS for r in vs)
    old_sites = {(r['caller'], r['instruction']['reference']) for r in vo}
    new_sites = {(r['caller'], r['instruction']['reference']) for r in vs}
    assert not new_sites - old_sites
    fact('vold-frontier', originalOwnerReferenceCount=80, stagedOwnerReferenceCount=63,
         typeReferencesEach=2, originalInvokeCount=78, stagedInvokeCount=61, removedSites=[{'caller': a, 'reference': b} for a, b in sorted(old_sites - new_sites)],
         removedKeyOperations=sorted(KEY_OPS), additionalRemovedInvokeSites=12)

    # Assert the exact observed post-guard Java state/return sites, not native completion.
    sites = [
        (INTERNAL, 'createUserStorageKeys(', 17, 'INVOKE_VIRTUAL', 'WatchedUnlockedUsers;->append(I)V'),
        (INTERNAL, 'destroyUserStorageKeys(', 17, 'INVOKE_VIRTUAL', 'WatchedUnlockedUsers;->remove(I)V'),
        (INTERNAL, 'setCeStorageProtection(', 6, 'GOTO', None),
        (INTERNAL, 'unlockCeStorage(', 12, 'GOTO', None),
        (INTERNAL, 'unlockCeStorage(', 28, 'INVOKE_VIRTUAL', 'WatchedUnlockedUsers;->append(I)V'),
        (SMS, 'lockCeStorage(', 59, 'NOP', None),
        (SMS, 'lockCeStorage(', 65, 'INVOKE_VIRTUAL', 'WatchedUnlockedUsers;->remove(I)V'),
        (LSS, 'lockUser(', 30, 'INVOKE_INTERFACE', 'IStorageManager;->lockCeStorage(I)V'),
        (LSS, 'lockUser(', 40, 'INVOKE_DIRECT', 'LockSettingsService;->lockKeystore(I)V'),
        (LSS, 'lockKeystore(', 2, 'INVOKE_VIRTUAL', 'KeyStoreAuthorization;->onUserStorageLocked(I)I'),
    ]
    for owner, prefix, pc, opcode, suffix in sites:
        b = body('staged', owner, prefix)
        at(b, pc, opcode, suffix)
        fact('observed-site', owner=owner, method=b['signature'], pc=pc, opcode=opcode, referenceSuffix=suffix)
    assert body('original', LSS, 'lockUser(') == body('staged', LSS, 'lockUser(')
    same_methods = [
        (LSS, 'setLockCredential('),
        ('Lcom/android/server/locksettings/LockSettingsService$LocalService;', 'lockUser('),
        ('Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;', 'onStart('),
        ('Lcom/android/server/biometrics/sensors/fingerprint/aidl/FingerprintProvider;', 'getHalInstance('),
        ('Lcom/android/internal/widget/ILockSettings$Stub;', 'onTransact('),
    ]
    for owner, prefix in same_methods:
        assert body('original', owner, prefix) == body('staged', owner, prefix)
        fact('selected-body-identical', owner=owner, method=body('staged', owner, prefix)['signature'])
    clean = body('staged', 'Lcom/android/server/biometrics/sensors/InternalCleanupClient;', 'startCleanup')
    at(clean, 2, 'INVOKE_VIRTUAL', 'ArrayList;->clear()V')
    at(clean, 14, 'CONST_4', literal=1)
    at(clean, 15, 'INVOKE_INTERFACE', 'ClientMonitorCallback;->onClientFinished(Lcom/android/server/biometrics/sensors/BaseClientMonitor;Z)V')
    at(clean, 18, 'RETURN_VOID')
    assert all(c['startPc'] >= 19 for c in clean['catches'])
    fact('cleanup-skips-and-reports-success', clearPc=2, callbackPc=15, returnPc=18, originalTailStartPc=19, nativeReconciliation=False)
    fp = body('staged', 'Lcom/android/server/biometrics/sensors/fingerprint/aidl/FingerprintProvider;', 'getHalInstance(')
    at(fp, 257, 'INVOKE_VIRTUAL', 'FingerprintProvider;->scheduleInternalCleanup(IILcom/android/server/biometrics/sensors/ClientMonitorCallback;)V')
    fact('fingerprint-provider-still-schedules-cleanup', pc=257, scope='conditional source call; no HAL getter or service was executed')
    ss = body('staged', 'Lcom/android/server/SystemServer;', 'startOtherServices(')
    for pc in (1714, 4399, 4417, 4432):
        at(ss, pc, 'INVOKE_VIRTUAL', 'SystemServiceManager;->startService(Ljava/lang/Class;)Lcom/android/server/SystemService;')
    at(ss, 4403, 'CHECK_CAST', 'Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;')
    at(ss, 1724, 'INVOKE_STATIC', 'ILockSettings$Stub;->asInterface(Landroid/os/IBinder;)Lcom/android/internal/widget/ILockSettings;')
    at(ss, 6537, 'INVOKE_VIRTUAL', 'LockSettingsInternal;->onThirdPartyAppsStarted()V')
    lifecycle = body('staged', 'Lcom/android/server/locksettings/LockSettingsService$Lifecycle;', 'onStart(')
    at(lifecycle, 9, 'INVOKE_DIRECT', 'LockSettingsService;-><init>(Landroid/content/Context;)V')
    at(lifecycle, 19, 'INVOKE_VIRTUAL', 'LockSettingsService$Lifecycle;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    fact('guest-startup-remains', lockSettingsStartPc=1714, fingerprintStartPc=4399, fingerprintResultCastPc=4403,
         biometricStartPc=4417, authStartPc=4432, localLateConsumerPc=6537, lifecycleConstructorPc=9, lifecyclePublicationPc=19,
         scope='conditional sites in actual staged bodies; runtime gate values and loaded classes unobserved')
    ext_owner = 'Lcom/android/server/locksettings/SyntheticPasswordManagerExtImpl;'
    assert body('original-oplus', ext_owner, 'triggerChannelOpen(') == body('staged-oplus', ext_owner, 'triggerChannelOpen(')
    ext = body('staged-oplus', ext_owner, 'triggerChannelOpen(')
    at(ext, 6, 'INVOKE_INTERFACE', 'ISyntheticPasswordManagerWrapper;->getWeaver()Landroid/hardware/weaver/IWeaver;')
    assert at(ext, 12, 'IF_NEZ')['targetPc'] == 21
    at(ext, 21, 'INVOKE_INTERFACE', 'IWeaver;->getConfig()Landroid/hardware/weaver/WeaverConfig;')
    oplus_counts = {k: len(v) for (p, k), v in reference_sets.items() if p == 'staged-oplus'}
    assert oplus_counts == {'gatekeeper': 0, 'weaver': 1, 'vold': 18}, oplus_counts
    assert not any(opname(r) in KEY_OPS for r in reference_sets[('staged-oplus', 'vold')])
    fact('oplus-conditional-frontier', invokeCounts=oplus_counts, wrapperGetPc=6, nonnullBranchPc=12, weaverGetConfigPc=21,
         scope='wrapper supplier/lifetime remains open; this is not a demonstrated getter bypass or global hardware isolation')
    result = {
        'schema': 'installed-oneos-security-guards/1', 'status': 'PASS-bounded-static-assertions',
        'selected': False, 'loadedGuestProved': False, 'securityAcceptance': False,
        'producerExecuted': False, 'oemExecuted': False, 'deviceAccess': False,
        'profile': {'version': 'OneOS 0.4.57', 'versionCode': 74, 'set': 'x9u-in-sultra', 'image': 'coloros17-findx9u-in', 'sourceCommit': '1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe'},
        'tool': pin('tools/audit_installed_oneos_security_guards.py'),
        'archives': archives, 'inputs': sorted(pins.values(), key=lambda x: x['path']),
        'methodEvidence': proofs, 'assertions': facts, 'excludedQueries': excluded,
        'limits': [
            'Staged JAR acquisition is not proof of loaded guest implementation or runtime feature gates.',
            'Direct owner-reference scans do not cover reflection, JNI, other protocols, or every native writer.',
            'Verification may mutate policy/state; retained verifyChallenge is not a read-only guarantee.',
            'Void returns, Java CE cache updates and cleanup success callbacks do not establish native work or drain.',
            'Selected Stub onTransact equality is not all-33-backend-method, Proxy, or installed-adapter equality.',
            'Private Oplus Weaver wrapper binding and all optional extension lifetimes remain open.',
            'Guard removal, source selection, guest lifecycle replacement, native admission and runtime testing remain unimplemented.',
        ],
    }
    target = ROOT / 'inventory/installed-oneos-security-guards.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = SCOPE / stamp
    run.mkdir(parents=True, exist_ok=False)
    receipt = {'status': result['status'], 'assertionCount': len(facts), 'methodCount': len(proofs), 'rawProofCount': len(raw_cache),
               'inventory': pin('inventory/installed-oneos-security-guards.json'), 'tool': result['tool'],
               'execution': 'authored Python: hashes and saved JSON parsing only; no imports of project code, producer, reader, OEM or Android execution'}
    (run / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'receipt': str((run / 'receipt.json').relative_to(ROOT)), **receipt}, indent=2))


if __name__ == '__main__':
    main()
