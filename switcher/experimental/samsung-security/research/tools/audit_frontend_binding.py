"""Exact offline native ColorOS entrypoint/consumer inspection, no OEM execution."""
import argparse
import hashlib
import json
import runpy
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
WORK = ROOT / 'out/construction-frontend'
RAW = ROOT / 'firmware/construction-frontend'
SETTINGS = PARENT / 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk'
SETTINGS_SHA = '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
READ = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
S = 'com.oplus.settings.feature.'
V = 'com.oplus.keyguard.security.verify.'
DECL = [S+'password.LockSaveAndFinishWorker', S+'password.ChooseLockPasswordFragment', S+'password.OplusScreenLockSettings$ScreenLockSettingsFragment', S+'password.ConfirmLockPasswordFragment', S+'fingerprint.FingerprintEnrollProcessor', S+'fingerprint.OplusFingerprintSettings$FingerprintSettingsFragment', S+'fingerprint.NewFingerEnrollActivity', 'com.android.settings.password.ChooseLockSettingsHelper']
BODIES = {'settings': {
    S+'password.LockSaveAndFinishWorker': ['saveAndVerifyInBackground', 'saveScreenLockInRpmb', 'storeOldPasswordOnModify', 'recordScreenLockPassword'],
    S+'password.ChooseLockPasswordFragment': ['startSaveAndFinish', 'onChosenLockSaveFinished'],
    S+'password.OplusScreenLockSettings$ScreenLockSettingsFragment': ['updateUnlockMethodAndFinish', 'launchChooseOrConfirmLock', 'deleteAllFingerprint'],
    S+'password.ConfirmLockPasswordFragment': ['startCheckPassword', 'startVerifyPassword', 'lambda$startVerifyPassword$6', 'onPasswordChecked'],
    S+'fingerprint.FingerprintEnrollProcessor': ['<init>', 'startEnrollment', 'cancelEnrollment'],
    S+'fingerprint.OplusFingerprintSettings$FingerprintSettingsFragment': ['getEnrollingIntent', 'generateChallengeAndStartEnroll', 'lambda$generateChallengeAndStartEnroll$11', 'launchChooseOrConfirmLock', 'onActivityResult', 'lambda$showDeleteFingerConfirmDialog$6', 'lambda$showEditFingerprintDialog$3', 'initFingerprintData'],
    'com.android.settings.biometrics.BiometricUtils': ['requestGatekeeperHat'],
    S+'fingerprint.utils.FingprintSwitchHelper': ['deleteAllFingerprints', 'deleteAllComplete'],
}, 'systemui': {
    V+'RpmbCheckTask$$ExternalSyntheticLambda0': ['onChecked'],
    V+'RpmbCheckTask$$ExternalSyntheticLambda1': ['onChecked'],
    V+'RpmbChannel': ['processCmdV2'],
    V+'OplusPasswordChangedCallbackImpl': ['onPasswordChanged'],
    V+'OplusKeyguardVerifyManagerExImpl': ['handleSystemRebooted', 'checkLockPatternSuccess', 'checkRpmbWhenReboot', 'checkRpmbWhenRebootWithSP', 'init', 'postRpmbCheckTask'],
    V+'OplusKeyguardVerifyManagerExImpl$checkFormSyntheticPasswordManager$3': ['run'],
    'com.oplusos.systemui.common.feature.KeyguardFeatureOption': ['isSupportOplusRoR', 'isOplusRoR', '$r8$lambda$Pd2QiML-oi8HzlCTayMwwltv5_o'],
    'com.oplusos.systemui.common.feature.KeyguardFeatureOption$$ExternalSyntheticLambda0': ['invoke'],
}, 'oplus-framework': {
    'com.oplus.os.OplusSyntheticPasswordManager': ['registerPasswordChangedCallback', 'unlockCeStorageWithSyntheticPassword'],
}}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def archive(role):
    if role == 'settings':
        return SETTINGS, SETTINGS_SHA
    if role == 'oplus-framework':
        return PARENT/'firmware/donor/extracted/system/framework/oplus-framework.jar', 'e53b28b80c5481364a7046a049d4bd4efa7f768262887961c1fc02d18c13f8fe'
    meta = json.loads((PARENT/'out/os-comparison-resumed/archive-index/comparisons'/role/'summary.json').read_text())['coloros']
    return PARENT/meta['archive'], meta['archiveSha256']


def load_ledger():
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK/'ledger.json'
    return json.loads(path.read_text()) if path.exists() else []


def query(ledger, role, owner=None, methods=(), reference=None):
    key = {'role': role, 'owner': owner, 'methods': list(methods), 'reference': reference}
    old = next((r for r in ledger if r['key'] == key), None)
    if old:
        if sha(ROOT/old['raw']) != old['rawSha256']:
            raise ValueError('Cached exact raw proof drift')
        return old
    path, pin = archive(role)
    result = READ(path, pin, owner, methods, reference, stream='construction-frontend')
    old = {**result, 'key': key}
    ledger.append(old)
    (WORK/'ledger.json').write_text(json.dumps(ledger, indent=2)+'\n')
    return old


def named(ledger, role, owner, names):
    declared = query(ledger, role, owner)['selectedClassDeclarations']
    if len(declared) != 1:
        raise ValueError('Unique original declaration required')
    available = declared[0]['methods']
    exact = [m.get('signature', m.get('name', '')+m.get('descriptor', '')) for m in available]
    exact = [m for m in exact if m.split('(')[0] in names]
    if {m.split('(')[0] for m in exact} != set(names):
        raise ValueError('Missing named method in '+owner+' '+str(names))
    return query(ledger, role, owner, exact)


def bodies(ledger):
    result = {}
    for row in ledger:
        if sha(ROOT/row['raw']) != row['rawSha256']:
            raise ValueError('Selected proof changed')
        for line in (ROOT/row['raw']).read_text(encoding='utf-8').splitlines():
            value = json.loads(line)
            if value['record'] == 'method':
                body = value['body']
                result[(row['key']['role'], body['owner'], body['signature'])] = value
    return result


def derived(ledger):
    methods = bodies(ledger)
    def selected(role, owner, prefix):
        found = [value for (r, name, sig), value in methods.items() if r == role and name == 'L'+owner.replace('.', '/')+';' and sig.startswith(prefix+'(')]
        if len(found) != 1:
            raise ValueError('Exact reviewed body missing or ambiguous: '+owner+' '+prefix)
        return found[0]
    assertions = [
        ('settings', S+'password.LockSaveAndFinishWorker', 'saveAndVerifyInBackground', 'LockPatternUtils;->setLockCredential(', 60),
        ('settings', S+'password.LockSaveAndFinishWorker', 'saveAndVerifyInBackground', 'LockPatternUtils;->verifyCredential(', 118),
        ('settings', S+'password.OplusScreenLockSettings$ScreenLockSettingsFragment', 'updateUnlockMethodAndFinish', 'LockPatternUtils;->setLockCredential(', 262),
        ('settings', S+'fingerprint.FingerprintEnrollProcessor', 'startEnrollment', 'FingerprintManager;->enroll(', 97),
        ('systemui', V+'OplusKeyguardVerifyManagerExImpl', 'init', 'OplusSyntheticPasswordManager;->registerPasswordChangedCallback(', 60),
        ('systemui', V+'OplusKeyguardVerifyManagerExImpl', 'handleSystemRebooted', '->checkRpmbWhenRebootWithSP(', 333),
        ('systemui', V+'OplusKeyguardVerifyManagerExImpl', 'handleSystemRebooted', '->checkRpmbWhenReboot(', 337),
    ]
    facts = []
    for role, owner, name, target, expected in assertions:
        row = selected(role, owner, name)
        matches = [i for i in row['body']['instructions'] if target in i.get('reference', '')]
        if len(matches) != 1 or matches[0]['pc'] != expected:
            raise ValueError('Reviewed native callsite drift: '+target)
        facts.append({'role': role, 'caller': row['body']['owner']+'->'+row['body']['signature'], 'pc': expected, 'callee': matches[0]['reference'], 'bodySha256': row['normalizedBodySha256']})
    removal = [
        {'id': 'SUI-ROR-REGISTER', 'target': V+'OplusKeyguardVerifyManagerExImpl.init', 'edit': 'Remove only optional password-changed callback registration edge at PC60 before SP material can cross into UI', 'preserve': ['original KeyguardUpdateMonitor registration and mandatory security readiness'], 'evidence': selected('systemui', V+'OplusKeyguardVerifyManagerExImpl', 'init')['normalizedBodySha256']},
        {'id': 'SUI-ROR-REBOOT', 'target': V+'OplusKeyguardVerifyManagerExImpl.handleSystemRebooted', 'edit': 'Remove optional recovery enqueue edges PC333/337 for unsupported profile; do not mark reboot verified or call checkLockPatternSuccess', 'preserve': ['Samsung real first-unlock/StrongAuth state', 'native mandatory monitor callbacks and locked UI'], 'evidence': selected('systemui', V+'OplusKeyguardVerifyManagerExImpl', 'handleSystemRebooted')['normalizedBodySha256']},
        {'id': 'SETTINGS-RPMB-WRITE', 'target': S+'password.LockSaveAndFinishWorker.saveScreenLockInRpmb', 'edit': 'Skip this optional side-operation before extra HAL challenge/HAT acquisition; do not fake a TEE success callback', 'preserve': ['actual setLockCredential and verifyCredential', 'real GK handle returned to native enrollment', 'separate metadata/record update and cleanup'], 'evidence': selected('settings', S+'password.LockSaveAndFinishWorker', 'saveScreenLockInRpmb')['normalizedBodySha256']},
        {'id': 'SETTINGS-OLD-RETRIEVAL', 'target': 'com.oplus.settings.utils.SysFeatureUtils.isSupportPasswordRetrieve', 'edit': 'Expose capability unavailable on selected Samsung profile; remove paired old-password recovery UI/controller/background TEE consumers', 'preserve': ['Samsung legitimate previous-credential recovery only through separately mapped dedicated flow', 'ordinary old-PIN rejection', 'native current-credential confirmation'], 'evidence': selected('settings', 'com.oplus.settings.utils.SysFeatureUtils', 'isSupportPasswordRetrieve')['normalizedBodySha256']},
        {'id': 'SUI-INPUT-RPMB', 'target': 'Original OplusLockPatternChecker.onChecked success allocation plus PIN/password/fixed-PIN/pattern setEntry callers', 'edit': 'Remove before RpmbCheckTask allocation and extra immutable credential-string retention; a no-op post alone is insufficient', 'preserve': ['real primary result', 'original credential zeroization', 'current user/generation and finish/extra-factor guards'], 'evidence': 'Reused inventory/coloros-frontend.json selectedUiProofs; native PIN/password copies pinned in this ledger'},
    ]
    return {'checkedCallsites': facts, 'sourcePatchPlan': removal, 'patchPlanApplied': False, 'binaryProducerImplemented': False, 'producerBlocker': 'Method-level source decisions are reviewable; complete reachable optional UI/background/late callback removal and resource/cache adaptation still need coordinated integration before producing an executable candidate', 'unresolvedRequired': ['Native Settings save/verify/remove calls require actual Samsung typed authority and commit/readback/recovery', 'Enrollment vendor getEnrollmentTotalTimes progress semantics need genuine Samsung adaptation or indeterminate native progress', 'Native activity/adaptor feature enable and installed patched byte identity not live-verified', 'Full password/pattern/recovery/profile/admin exposed path mapping remains incomplete', 'Gatekeeper handle/HAT lifetime and challenge revocation must follow real native ownership', 'Mandatory credential/PIN-length/cache/StrongAuth readiness must not use guest fail-soft defaults', 'Pattern/fixed-PIN and all late optional retry/entry callbacks need paired removal coverage before payload production']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['declarations', 'bodies', 'manifest', 'report'], default='report')
    p.add_argument('--role', choices=['settings', 'systemui', 'oplus-framework'])
    p.add_argument('--owner')
    p.add_argument('--name', action='append', default=[])
    p.add_argument('--reference')
    a = p.parse_args()
    ledger = load_ledger()
    if a.role:
        result = named(ledger, a.role, a.owner, a.name) if a.name else query(ledger, a.role, a.owner, reference=a.reference)
        print(json.dumps({'receipt': result['receipt'], 'raw': result['raw'], 'methods': result['selectedClassDeclarations'][0]['methods'] if a.owner and not a.name else result['selectedMethodProofs'], 'referenceMatches': result['referenceMatchCount']}))
        return
    if a.stage == 'declarations':
        for owner in DECL:
            result = query(ledger, 'settings', owner)
            print(json.dumps({'owner': owner, 'methods': result['selectedClassDeclarations'][0]['methods']}))
    elif a.stage == 'bodies':
        for role, classes in BODIES.items():
            for owner, names in classes.items():
                named(ledger, role, owner, names)
    elif a.stage == 'manifest':
        path, pin = archive('settings')
        if sha(path) != pin:
            raise ValueError('Settings archive changed')
        aapt = PARENT/'out/toolchain/android-sdk/build-tools/37.0.0/aapt2.exe'
        aapt_sha = sha(aapt)
        result = subprocess.run([str(aapt), 'dump', 'xmltree', str(path), '--file', 'AndroidManifest.xml'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode or len(result.stdout)>16*1024*1024:
            raise ValueError('Bounded static manifest dump refused')
        RAW.mkdir(parents=True, exist_ok=True)
        dest = RAW/'settings-manifest.txt'
        dest.write_bytes(result.stdout)
        if sha(path)!=pin or sha(aapt)!=aapt_sha:
            raise ValueError('Manifest input/tool changed')
        (WORK/'manifest-receipt.json').write_text(json.dumps({'archiveSha256': pin, 'aapt2Sha256': aapt_sha, 'raw': dest.relative_to(ROOT).as_posix(), 'rawSha256': sha(dest), 'oemCodeExecuted': False}, indent=2)+'\n')
        print('Pinned static Settings manifest dumped')
    else:
        for role in {r['key']['role'] for r in ledger}:
            path, pin = archive(role)
            if sha(path) != pin:
                raise ValueError('Selected archive changed before report')
        report = {'schema': 'construction-frontend/v1', 'scope': 'Offline native frontend callsite/consumer construction obligations; no phone/runtime acceptance', 'settings': {'archive': SETTINGS.relative_to(PARENT).as_posix(), 'sha256': SETTINGS_SHA}, 'proofs': [], 'reusedReports': [], 'runtimeAccepted': False, 'oemCodeExecuted': False}
        for row in ledger:
            if sha(ROOT/row['raw']) != row['rawSha256']:
                raise ValueError('Raw proof drift')
            report['proofs'].append({k: row[k] for k in ['key', 'receipt', 'raw', 'rawSha256', 'archiveSha256', 'selectedMethodProofs', 'referenceMatchCount']})
        report['referenceFacts'] = []
        for row in ledger:
            if row['key']['reference'] is None:
                continue
            refs = []
            for line in (ROOT/row['raw']).read_text(encoding='utf-8').splitlines():
                item = json.loads(line)
                if item['record'] == 'reference':
                    refs.append({'caller': item['caller'], 'pc': item['instruction']['pc'], 'reference': item['instruction']['reference']})
            report['referenceFacts'].append({'query': row['key'], 'count': len(refs), 'callsites': refs})
        for path in ['inventory/coloros-frontend.json', 'inventory/strong-auth-gating.json']:
            report['reusedReports'].append({'path': path, 'sha256': sha(ROOT/path)})
        report['discoveryReceipts'] = []
        for stamp in ['20261105T143456296793Z-318b5ac2734144cfb3b5d7f22e7de23f', '20261105T143553548650Z-873b7465e0c34e199d3dd4ef10c4f65b', '20261105T143608876185Z-6328bfbfffc042e29a3af80f71ace396', '20261105T143646397049Z-6da36af8ade04e58b61626c7046f24a4']:
            receipt_path = ROOT/'out/tooling'/stamp/'receipt.json'
            receipt = json.loads(receipt_path.read_text())
            if sha(ROOT/receipt['raw']) != receipt['rawSha256']:
                raise ValueError('Original discovery proof drift')
            report['discoveryReceipts'].append({'receipt': receipt_path.relative_to(ROOT).as_posix(), 'receiptSha256': sha(receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'query': receipt['query'], 'referenceMatchCount': receipt['referenceMatchCount'], 'summary': receipt['summary']})
        manifest_path = WORK/'manifest-receipt.json'
        report['manifest'] = json.loads(manifest_path.read_text())
        if sha(ROOT/report['manifest']['raw']) != report['manifest']['rawSha256']:
            raise ValueError('Static manifest proof drift')
        report['constructionContracts'] = derived(ledger)
        report['constructionContracts']['additionalCacheConsumer'] = {'caller': 'LockSaveAndFinishWorker.saveAndVerifyInBackground', 'pc': 101, 'callee': 'com.oplus.settings.utils.LockSettingsHelper.savePassword(LockscreenCredential,int)', 'effect': 'Static per-user SparseArray retains same credential object for repeated-password UI hint; not credential authority', 'removalObligation': 'Paired UI hint/cache/lifetime adaptation and real Samsung password-history policy, no assumed credential rollback or authorization from cache'}
        output = ROOT/'inventory/construction-frontend.json'
        output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'report': str(output), 'queries': len(ledger)}))


if __name__ == '__main__':
    main()
