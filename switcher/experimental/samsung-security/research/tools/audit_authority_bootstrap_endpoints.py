"""Replay finite endpoint/lifecycle source evidence; no patch or runtime API."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAM = 'authority-bootstrap-endpoints'
PINS = {
    "out/authority-bootstrap-endpoints/coloros-agent-early.json": "81ae4612bf00bdfec8d422718608e5979960cd6f3c5fb3e67a5be3b8d6fc7f77",
    "out/authority-bootstrap-endpoints/coloros-framework-lookup-xref.json": "9dfc615b2d1671635e130ff4c50f0a56796ea28225f4c3ee9dc9d36e90531a3a",
    "out/authority-bootstrap-endpoints/coloros-internal-declarations.json": "be6f368efac17d0873b48ecf1ae347ceac832daf9c9e32f84d8b0ca6b22695b7",
    "out/authority-bootstrap-endpoints/coloros-local-interface-xref.json": "014d29cd1ceefee974290ede3b06f4756b526402aca01ae17bd543c462eccd1d",
    "out/authority-bootstrap-endpoints/coloros-lpu-getter.json": "58af6f734f4a8c930ebccc3f0f17a0e92feb6c62dd7d492a4804e6a529dd7be6",
    "out/authority-bootstrap-endpoints/coloros-policy-early.json": "0310b06a077233174876b92f8a1915e0ae42b1727b9f19ceaad1243077cadfa7",
    "out/authority-bootstrap-endpoints/coloros-recovery-getter.json": "35e2b2e5cbc41096371a7b6cd0ad7d8be73cd061fb60934bfb86f035dd4b8a36",
    "out/authority-bootstrap-endpoints/coloros-recoverysystem-local.json": "e605356ea55092e75503fbbdcef2b32b06f1bc21ffa8d92980367c32f2b521e3",
    "out/authority-bootstrap-endpoints/coloros-recoverysystem-phase.json": "76eb26ee7e827f5648e0d55ae37223496975af27f5877d62c1f2ac43d0fa31b7",
    "out/authority-bootstrap-endpoints/coloros-securelock-local.json": "e1e95ee292b62f271cd27128c69a8832a12619e40e05dd030e4b70c1a018995b",
    "out/authority-bootstrap-endpoints/coloros-securelock-phase.json": "5dc0835018e67d2e484c9c6ee0ebfe40d85d29bec309aea3ee3a9239593f4ae6",
    "out/authority-bootstrap-endpoints/coloros-settings-lookup-xref.json": "116435eeb64d18bf60c534699cde04ce88a380282ffbb8bb5ebd1d73f6983f0c",
    "out/authority-bootstrap-endpoints/coloros-system-server-services-lookup-xref.json": "b40f06d8e178c6832b7dba3ec10973d1edd50da2ea51e308b6070db921df4287",
    "out/authority-bootstrap-endpoints/coloros-systemready-proxy.json": "be88d392b302299af4669a9dbbe978a561845b01c7e392ce3627c24d4e3520f6",
    "out/authority-bootstrap-endpoints/coloros-systemui-lookup-xref.json": "8af04ecf96a3e136627aa63f5e0763c9591bf55bf4c302cc01668e20fbd71a68",
    "out/authority-bootstrap-endpoints/coloros-trust-early.json": "9919809ec492655fa855650b052ca39e55bda0018fef5d6cf6f3a167d3ba08ff",
    "out/authority-bootstrap-endpoints/samsung-internal-declarations.json": "ec75bdce3ed4a3e7e0c3430213d6477eb8be7264d06f05ff81aa623bdf5a23f1",
    "out/authority-bootstrap-endpoints/samsung-locals.json": "065524643b910c2337883fbac4aad1ff3ab97910a6ed43112ef11c7fb71e7b92",
    "out/authority-bootstrap-endpoints/samsung-localservice-declarations.json": "2bae9667d5a57c69ef0f9839bc20af28a1401bd85fc0a5444a04f1ad680ecb28",
    "out/authority-bootstrap-endpoints/samsung-publication.json": "c21e6160b3653df13336c55294779ebd0f3a5f49d4db2e29b3a8fc15a527f3e6",
    "out/authority-bootstrap-endpoints/samsung-systemready-proxy.json": "ab41ecdc3cf25b1fe42b3257bd88420b40b23276bf6cec7b47b5a63cfe482b13",
    "out/authority-bootstrap-endpoints/samsung-write-admission.json": "5e2dabac8602cc64d9f65426338062d41cfcbe802d159fb7f29d5c9427ec41d2",
    "inventory/construction-startup.json": "998bd293e7cf598e76d4f60ec1b45a22e4417001aa38d4fe953f6b697a9706ef",
    "inventory/credentials.json": "333118f3876c61f641d9a8aae82bd11ed61d6366a28e916ddd58755c4a5ef3b8",
    "inventory/construction-credentials.json": "3d726dfce77e607c08272c9f61e36ea8e0f71092ab82eac5c8a1f75d1e6d6f9b",
    "inventory/construction-protocol.json": "aa2baaa0b449d5f93a4b796704176659ad54315a082547cb06c39f3acff13d18",
    "inventory/coloros-frontend.json": "24bdce6a4e213af97a2ce0bd05900c95945e6bdbbe1a3632fa6407591b6a68bc",
    "firmware/credentials/20261105T123453605431Z-ca414970bc0d4a81a8a808ca21b0cfb0.jsonl": "9cd220e79ca77e9f067888ed30f35d7de111f9be84f8d353ab411b1c9e66a7dc",
    "firmware/credentials/20261105T123454212027Z-7bee1deb9d7c403087492c4d788a2cd6.jsonl": "005f96ae16337e31ea8195cab9e98ffbc40da6d23c8f108745dd3448183d9377",
    "firmware/credentials/20261105T123705889135Z-94ca2a5cf4984aa38475568e752587d6.jsonl": "3d98459af85df8b6df4dd88a81bb62f0f5a32e7be98268f23c4c30a6f3ba062e"
}  # FROZEN_PINS
INTERNAL = 'Lcom/android/server/locksettings/LockSettingsInternal;'
LSS = 'Lcom/android/server/locksettings/LockSettingsService;'
LIFECYCLE = 'Lcom/android/server/locksettings/LockSettingsService$Lifecycle;'


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text())


def rows(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def main():
    if not PINS:
        raise ValueError('Unfrozen source evidence')
    for path, expected in PINS.items():
        if sha(ROOT / path) != expected:
            raise ValueError('Frozen evidence changed: ' + path)
    receipts, methods, proofs, declarations, references, archives = {}, {}, {}, {}, {}, {}
    for path in PINS:
        if not path.startswith('out/' + STREAM + '/'):
            continue
        r = load(path)
        if sha(ROOT / r['raw']) != r['rawSha256'] or r['readerExitCode']:
            raise ValueError('Raw/reader proof')
        label = Path(path).stem
        receipts[label] = r
        archives[r['archive']] = r['archiveSha256']
        declarations[label] = r['selectedClassDeclarations']
        for record in rows(r['raw']):
            if record['record'] == 'method':
                body = record['body']
                key = label + ':' + body['owner'] + '->' + body['signature']
                methods[key] = body
                proofs[key] = {'bodySha256': record['normalizedBodySha256'],
                               'raw': r['raw'], 'rawSha256': r['rawSha256'],
                               'archiveSha256': r['archiveSha256'],
                               'physicalDex': record['physicalDex'],
                               'logicalHeaderOffset': record['logicalHeaderOffset']}
            elif record['record'] == 'reference':
                references.setdefault(label, []).append({'caller': record['caller'],
                    'pc': record['instruction']['pc'], 'target': record['instruction']['reference']})
    for path, expected in archives.items():
        if sha(path) != expected:
            raise ValueError('Input archive changed')

    def inherit(label, raw, raw_sha, selected):
        if sha(ROOT / raw) != raw_sha:
            raise ValueError('Reused raw changed')
        seen = set()
        for record in rows(raw):
            if record['record'] != 'method':
                continue
            body = record['body']
            identity = body['owner'] + '->' + body['signature']
            if identity not in selected:
                continue
            if record['normalizedBodySha256'] != selected[identity]:
                raise ValueError('Reused method body changed')
            key = label + ':' + identity
            methods[key] = body
            proofs[key] = {'bodySha256': record['normalizedBodySha256'], 'raw': raw,
                           'rawSha256': raw_sha, 'reused': True,
                           'physicalDex': record['physicalDex'],
                           'logicalHeaderOffset': record['logicalHeaderOffset']}
            seen.add(identity)
        if seen != set(selected):
            raise ValueError('Reused method absent')

    startup = load('inventory/construction-startup.json')
    needed = {
        'com.android.server.SystemServer': ['startOtherServices('],
        'com.android.server.SystemServiceManager': ['startService(', 'startBootPhase('],
        'com.android.server.SystemService': ['publishBinderService(', 'publishLocalService('],
        'com.android.server.LocalServices': ['addService(', 'getService('],
        'com.android.server.locksettings.LockSettingsService$Lifecycle': [''],
        'com.android.server.locksettings.LockSettingsService': ['onBootPhase(', 'systemReady(', 'onThirdPartyAppsStarted('],
        'com.android.server.locksettings.LockSettingsService$LocalService': ['onThirdPartyAppsStarted(']}
    for evidence in startup['methodEvidence']:
        selected = {p['owner'] + '->' + p['signature']: p.get('normalizedBodySha256', p.get('bodySha256'))
                    for p in evidence['methodProofs'] if evidence['class'] in needed and
                    any(p['signature'].startswith(prefix) for prefix in needed[evidence['class']])}
        if selected:
            inherit('guest-startup', evidence['raw'], evidence['rawSha256'], selected)
    credentials = load('inventory/credentials.json')
    grouped = {}
    for key, p in credentials['methodProofs'].items():
        side, identity = key.split(':', 1)
        if ((identity.startswith(LIFECYCLE + '->') and side == 'samsung') or
                identity == LSS + '-><init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V'):
            grouped.setdefault((side, p['raw']), {})[identity] = p['bodySha256']
    for (side, raw), selected in grouped.items():
        inherit(side + '-credentials', raw, PINS[raw], selected)
    detail = load('inventory/construction-credentials.json')['methods'][LSS + '->systemReady()V']
    inherit('samsung-systemready', detail['raw'], detail['rawSha256'],
            {LSS + '->systemReady()V': detail['bodySha256']})
    frontend = load('inventory/coloros-frontend.json')
    for side in ['coloros', 'samsung']:
        proof = next(p for p in frontend['selectedRawProofs'][side] if any(
            m['owner'] == 'Lcom/android/internal/widget/ILockSettings$Stub;' and
            m['signature'].startswith('onTransact(') for m in p['selectedMethodProofs']))
        inherit(side + '-stub', proof['raw'], proof['rawSha256'], {
            m['owner'] + '->' + m['signature']: m['normalizedBodySha256']
            for m in proof['selectedMethodProofs']})

    assertions = []
    def at(key, pc, **expected):
        item = next(i for i in methods[key]['instructions'] if i['pc'] == pc)
        if any(item.get(k) != value for k, value in expected.items()):
            raise ValueError('Exact site changed: ' + key + ':' + str(pc))
        assertions.append({'proof': key, 'pc': pc, **expected})
    lpu = 'coloros-lpu-getter:Lcom/android/internal/widget/LockPatternUtils;->getLockSettings()Lcom/android/internal/widget/ILockSettings;'
    recovery = 'coloros-recovery-getter:Landroid/security/keystore/recovery/RecoveryController;->getInstance(Landroid/content/Context;)Landroid/security/keystore/recovery/RecoveryController;'
    ss = 'guest-startup:Lcom/android/server/SystemServer;->startOtherServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V'
    at(lpu, 5, reference='string=lock_settings')
    at(lpu, 15, opcode='IPUT_OBJECT')
    at(recovery, 1, reference='string=lock_settings')
    at(ss, 1712, reference=LIFECYCLE)
    at(ss, 1717, reference='string=lock_settings')
    at(ss, 5625, reference='Lcom/android/internal/widget/ILockSettings;->systemReady()V')
    at(ss, 6537, reference=INTERNAL + '->onThirdPartyAppsStarted()V')
    at('guest-startup:' + LIFECYCLE + '->onStart()V', 9,
       reference=LSS + '-><init>(Landroid/content/Context;)V')
    at('coloros-credentials:' + LSS + '-><init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V',
       287, reference='Lcom/android/server/LocalServices;->addService(Ljava/lang/Class;Ljava/lang/Object;)V')
    at('samsung-credentials:' + LSS + '-><init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V',
       1024, reference='Lcom/android/server/LocalServices;->addService(Ljava/lang/Class;Ljava/lang/Object;)V')
    at('samsung-write-admission:' + LSS + '->checkWritePermission()V', 2,
       reference='string=android.permission.ACCESS_KEYGUARD_SECURE_STORAGE')
    at('samsung-systemready:' + LSS + '->systemReady()V', 0, reference=LSS + '->checkWritePermission()V')
    for side, code in [('coloros', 26), ('samsung', 70)]:
        at(side + '-systemready-proxy:Lcom/android/internal/widget/ILockSettings$Stub$Proxy;->systemReady()V',
           22, literal=code)
        at(side + '-systemready-proxy:Lcom/android/internal/widget/ILockSettings$Stub$Proxy;->systemReady()V',
           24, literal=32)
    guest_methods = [m['signature'] for m in declarations['coloros-internal-declarations'][0]['methods']
                     if not m['signature'].startswith('<')]
    host_methods = [m['signature'] for m in declarations['samsung-internal-declarations'][0]['methods']
                    if not m['signature'].startswith('<')]
    comparison = []
    for signature in guest_methods:
        name = signature.split('(', 1)[0]
        alternatives = [m for m in host_methods if m.split('(', 1)[0] == name]
        comparison.append({'guestSignature': signature, 'samsungSameNameSignatures': alternatives,
                           'classification': 'exact declaration' if signature in host_methods else
                           'changed signature' if alternatives else 'absent from selected Samsung internal declaration',
                           'crossProcessImplementation': 'not implemented; declaration equality is not transport/semantic proof'})
    routes = load('inventory/construction-protocol.json')['operations']
    if any(op['name'] == 'systemReady' for op in routes) or len(routes) != 33:
        raise ValueError('Frozen transport baseline changed')
    count = {k: r['referenceMatchCount'] for k, r in receipts.items() if k.endswith('lookup-xref')}
    if sorted(count.values()) != [0, 0, 2, 2]:
        raise ValueError('Selected lookup closure changed')
    comparison_counts = {label: sum(item['classification'] == label for item in comparison)
                         for label in ['exact declaration', 'changed signature',
                                       'absent from selected Samsung internal declaration']}
    if list(comparison_counts.values()) != [8, 3, 7]:
        raise ValueError('Internal-interface declaration comparison changed')
    output = {
        'schema': 'authority-bootstrap-endpoints/v1', 'scope': 'Finite gate B: explicit endpoints and guest producer/local lifecycle replacement',
        'status': 'SOURCE_PROPOSAL_ONLY_MISSING_LIFECYCLE_AND_LOCAL_BRIDGE',
        'selected': False, 'patchBuilt': False, 'newRuntimeApiImplemented': False,
        'archives': archives, 'frozenEvidencePins': PINS, 'methodProofs': proofs,
        'sourceBodyCount': len(methods), 'selectedInstructionAssertions': assertions,
        'lookupCounts': count, 'lookupReferences': {k: v for k, v in references.items() if k.endswith('lookup-xref')},
        'proposedEndpoints': [
            {'name': 'lock_settings', 'status': 'canonical existing name; proposed Samsung-protocol guarded endpoint',
             'process': 'dedicated authority process', 'protocol': 'actual Samsung ILockSettings',
             'owner': 'same live/retirement owner as guest endpoint; raw originalStub must not bypass it',
             'registrationAndServiceManagerNamespaceVerifiedAtRuntime': False},
            {'name': 'oneos_coloros_lock_settings', 'status': 'PROPOSED alias; not published',
             'process': 'same dedicated authority process', 'protocol': 'selected original ColorOS ILockSettings mapped to actual Samsung',
             'owner': 'same live/retirement owner; original caller/user/operation validation before dispatch',
             'recoveryControllerCapabilitiesInCurrent33Routes': False},
            {'name': 'LockSettingsInternal', 'status': 'guest-local typed proxy REQUIRED, unimplemented',
             'process': 'guest system_server', 'publication': 'LocalServices keyed by actual guest Class object before replacement onStart returns',
             'remoteSamsungPublicationSatisfiesGuestLocalConsumer': False}],
        'requiredGuestLookupCuts': [
            {'proof': lpu, 'literalPc': 5, 'lookupPc': 7, 'cacheWritePc': 15,
             'change': 'retarget only guest lookup to proposed alias before any admitted instance caches canonical Binder'},
            {'proof': recovery, 'literalPc': 1, 'lookupPc': 4,
             'change': 'retarget guest recovery lookup too; recovery API requires separately reviewed support/unavailability, never canonical raw fallback'},
            {'proof': ss, 'literalPc': 1717, 'lookupPc': 1720,
             'change': 'retarget guest SystemServer retained ILockSettings lookup to alias; real systemReady remains required'}],
        'guestProducerReplacement': {'systemServerClassLiteralPc': 1712, 'startServicePc': 1714,
            'originalLifecycleConstructorOnlyCallsSystemServiceSuper': True,
            'originalOnStartCreatesGuestLssPc': 9, 'originalGuestLocalPublicationPc': 287,
            'originalBinderPublicationLiteralPc': 14, 'originalBinderPublicationPc': 19,
            'requiredCut': 'replace guest lifecycle producer before original onStart; never instantiate original guest LSS or rename its publication',
            'replacementOnStartRequirements': ['bind admitted live authority generation', 'publish real guest-local typed lifecycle/policy proxy before return',
                'make exact alias lookup available or stop unavailable before dependent constructors continue',
                'retain required original guest KeyStore provider setup without running old LSS constructor'],
            'allFiveLifecycleMethodsNeedReplacementOwnership': ['<init>(Context)', 'onStart()', 'onBootPhase(int)', 'onUserStarting(TargetUser)', 'onUserUnlocking(TargetUser)']},
        'systemReady': {'guestTransaction': 26, 'samsungTransaction': 70, 'flags': 32,
            'payloadAfterToken': [], 'reply': 'original exception/void completion',
            'systemServerInvokePc': 5625, 'beforePhase': 480,
            'originalSamsungAdmission': 'checkWritePermission at0 -> Context.enforceCallingOrSelfPermission ACCESS_KEYGUARD_SECURE_STORAGE',
            'inCurrent33Routes': False, 'proposedNewRouteOrControlledReplacementReviewed': False,
            'callReturnIsPolicyOrChildWorkReadiness': False},
        'localInterfaceComparison': comparison,
        'localInterfaceComparisonCounts': comparison_counts,
        'localDirectReferenceCount': receipts['coloros-local-interface-xref']['referenceMatchCount'],
        'localDirectReferences': references['coloros-local-interface-xref'],
        'earliestSelectedConsumers': [
            {'consumer': 'TrustManagerService constructor', 'systemServerStartPc': 3593, 'localCachePcs': [176, 184],
             'laterPhase': 500, 'conditionalListenerRegistrationPc': 47},
            {'consumer': 'AuthenticationPolicyService constructor', 'systemServerStartPc': 4516,
             'localLookupPc': 60, 'requireNonNullPc': 66, 'localCachePc': 72,
             'laterPhase': 500, 'listenerRegistrationPc': 4},
            {'consumer': 'SecureLockDeviceService', 'phase': 480, 'localCachePc': 32, 'strongAuthRegistrationPc': 68},
            {'consumer': 'RecoverySystemService', 'phase': 500, 'localListenerRegistrationPc': 16,
             'nullFallback': 'logs and skips listener, not recovery readiness'},
            {'consumer': 'SystemServer', 'after': 'AMS.systemReady', 'localLookupPc': 6528,
             'onThirdPartyAppsStartedPc': 6537, 'beforeStartSystemUiPc': 6550}],
        'minimumExecutableCutStillRequired': [
            'Reviewed original-protocol canonical guard and guest alias publication share one actual authority and retirement barrier; include private/local/lifecycle calls and old cached Binder references.',
            'Atomic three guest lookup retargets plus preconstruction lifecycle replacement; fresh guest instances only or prove old cached owners disconnected/drained.',
            'Implement and review original systemReady26->70 admission or exact controlled replacement of SystemServer call; current33route dispatch cannot handle bootstrap.',
            'Implement guest-local LockSettingsInternal owner and actual remote lifecycle/local callback channel before early consumers; all18 guest abstract methods require honest supported or unavailable behavior, not an empty proxy.',
            'Forward real boot phase/user identifiers to corresponding original Samsung lifecycle under current scope; preserve original systemReady-before480 and genuine phase520/550/1000 effects and posted work ownership.',
            'Provide exact user/profile/operation/caller ownership, same-source Samsung Context/registries/privateLPU, native/state one-writer lease and death/return drain from other bootstrap owners; service names/UID1000 are insufficient.'
        ],
        'limits': ['Source fact and proposed finite cut only; no lifecycle IPC/API, adapter publication, alias or source patch is implemented.',
            'Lookup closure covers exact literal sites in four supplied selected guest archives only; other selected JAR/APK/native/reflection/dynamic-name consumers require admission or exclusion.',
            'Current OneOS installed guest image and effective Binder/ServiceManager namespace, cache and access policy remain unverified.',
            'Exact local declaration match is not executable cross-process adaptation; changed returns/argument order and missing listeners/token/user methods must not be fabricated.',
            'Existing OneOS permissive SELinux/relaxed privileged permission limits are accepted disclosures, not a new global enforcing gate.'],
        'audit': {'pass': True, 'oemCodeExecuted': False, 'androidExecuted': False, 'phoneActions': []},
        'toolSha256': sha(__file__)}
    inventory = ROOT / 'inventory/authority-bootstrap-endpoints.json'
    inventory.write_text(json.dumps(output, indent=2) + '\n')
    result = {'pass': True, 'sourceBodies': len(methods), 'instructionAssertions': len(assertions),
              'lookupSites': sum(count.values()), 'localInterfaceMethods': len(comparison),
              'bootstrapImplemented': False, 'inventorySha256': sha(inventory), 'toolSha256': sha(__file__)}
    (ROOT / 'out' / STREAM / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
