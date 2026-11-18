"""Collect bounded original strong-auth/factor gating evidence, offline only."""
import argparse
import gzip
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
INDEX = PARENT / 'out/os-comparison-resumed/archive-index/comparisons'
UI = 'com.android.systemui.'
KG = 'com.android.keyguard.'
SELECT = {
    ('systemui', 'coloros'): {
        KG + 'KeyguardSecurityContainerController': ['showNextSecurityScreenOrFinish'],
        KG + 'KeyguardSecurityContainerController$3': ['dismiss'],
        KG + 'KeyguardSecurityModel': ['<init>', 'getSecurityMode'],
        KG + 'KeyguardSecurityModel$$ExternalSyntheticLambda0': ['accept'],
        KG + 'KeyguardSecurityViewFlipperController': ['getSecurityView'],
        KG + 'KeyguardInputViewController$Factory': ['create'],
        KG + 'KeyguardSecureLockDeviceBiometricAuthViewController': ['onInit'],
        UI + 'securelockdevice.data.repository.SecureLockDeviceRepositoryImpl$isSecureLockDeviceEnabled$1': ['invokeSuspend'],
        UI + 'securelockdevice.data.repository.SecureLockDeviceRepositoryImpl$isSecureLockDeviceEnabled$1$listener$1': ['onSecureLockDeviceEnabledStatusChanged'],
        UI + 'securelockdevice.domain.interactor.SecureLockDeviceInteractor': ['<init>', 'onBiometricAuthRequested', 'onBiometricAuthUiHidden', 'onBiometricAuthenticatedStateUpdated', 'onReadyToDismissBiometricAuth', 'onGoneTransitionFinished'],
        UI + 'securelockdevice.domain.interactor.SecureLockDeviceInteractor$isAuthenticatedButPendingDismissal$1': ['invokeSuspend'],
        UI + 'keyguard.shared.model.AuthenticationFlags': ['<init>'],
        UI + 'keyguard.data.repository.BiometricSettingsRepositoryImpl$special$$inlined$map$3$2': ['emit'],
        UI + 'securelockdevice.ui.viewmodel.SecureLockDeviceBiometricAuthContentViewModel$confirmAuthenticated$2': ['invokeSuspend'],
    },
}
for side in ['samsung', 'coloros']:
    SELECT[('framework', side)] = {
        'android.security.authenticationpolicy.AuthenticationPolicyManager': ['registerSecureLockDeviceStatusListener', 'isSecureLockDeviceEnabled', 'disableSecureLockDevice'],
        'android.security.authenticationpolicy.AuthenticationPolicyManager$1': ['onSecureLockDeviceEnabledStatusChanged'],
    }
    SELECT[('system-server-services', side)] = {
        'com.android.server.security.authenticationpolicy.SecureLockDeviceService': ['registerSecureLockDeviceStatusListener', 'isSecureLockDeviceEnabled', 'disableSecureLockDevice'],
    }


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declarations(role, side):
    meta = json.loads((INDEX / role / 'summary.json').read_text())[side]
    path = PARENT / meta['declarations']
    if digest(path) != meta['declarationsSha256'] or digest(PARENT / meta['archive']) != meta['archiveSha256']:
        raise ValueError('Pinned archive/index drift')
    names = {'L' + n.replace('.', '/') + ';' for n in SELECT[(role, side)]}
    rows = {}
    for line in gzip.open(path, 'rt', encoding='utf-8'):
        row = json.loads(line)
        if row.get('record') == 'class' and row['descriptor'] in names:
            if row['descriptor'] in rows:
                raise ValueError('Ambiguous selected original class')
            rows[row['descriptor']] = row
    if set(rows) != names:
        raise ValueError('Missing original types: ' + str(names - set(rows)))
    return meta, rows


def read_bodies(receipt):
    raw = ROOT / receipt['raw']
    if digest(raw) != receipt['rawSha256']:
        raise ValueError('Selected raw body drift')
    return [r for line in raw.read_text(encoding='utf-8').splitlines() if (r := json.loads(line))['record'] == 'method']


def derive(report):
    selected = {(p['side'], r['body']['owner'], r['body']['signature']): r for p in report['selectedProofs'] for r in read_bodies(p)}
    reused = {(p['side'], r['body']['owner'], r['body']['signature']): r for p in report['reusedCredentialProofs'] for r in read_bodies(p)}
    guard = next(r for (side, owner, sig), r in selected.items() if side == 'coloros' and owner == 'Lcom/android/keyguard/KeyguardSecurityContainerController;' and sig.startswith('showNextSecurityScreenOrFinish('))
    instructions = guard['body']['instructions']
    def pc(rows, term):
        values = [i['pc'] for i in rows if term in i.get('reference', '')]
        if len(values) != 1:
            raise ValueError('Expected unique actual reference: ' + term)
        return values[0]
    positions = {'enabledReadPc': pc(instructions, '->isSecureLockDeviceEnabled('), 'pendingReadPc': pc(instructions, '->isAuthenticatedButPendingDismissal('), 'finishInvokePc': pc(instructions, '->finish('), 'blockedReturnPc': 434}
    if not (positions['enabledReadPc'] == 391 < positions['pendingReadPc'] == 413 < positions['blockedReturnPc'] < positions['finishInvokePc'] == 602):
        raise ValueError('Reviewed finish gate body drift')
    if next(i for i in instructions if i['pc'] == 434)['opcode'] != 'RETURN':
        raise ValueError('Original blocked path no longer returns')
    timing = {}
    for side in ['samsung', 'coloros']:
        original = next(r for (s, owner, sig), r in reused.items() if s == side and owner == 'Lcom/android/server/locksettings/SyntheticPasswordManager;' and sig.startswith('unlockLskfBasedProtector('))
        body = original['body']['instructions']
        timing[side] = {'progressInvokePc': pc(body, 'ICheckCredentialProgressCallback;->onCredentialVerified()'), 'blobUnwrapPc': pc(body, '->unwrapSyntheticPasswordBlob('), 'postUnwrapChallengePc': pc(body, 'SyntheticPasswordManager;->verifyChallenge('), 'proofBodySha256': original['normalizedBodySha256']}
        if not timing[side]['progressInvokePc'] < timing[side]['blobUnwrapPc'] < timing[side]['postUnwrapChallengePc']:
            raise ValueError('Reviewed provisional progress ordering changed')
    report['actualTimingFacts'] = {'colorosFinishGuard': {'positions': positions, 'bodySha256': guard['normalizedBodySha256'], 'condition': 'candidateFinish && enabled && !pending -> return false before finish'}, 'protectorEarlyProgressOrder': timing, 'note': 'PC order plus inspected original control flow; one-way/handler callback delivery scheduling is not runtime-tested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'inventory/strong-auth-gating.json'
    report = {'schema': 'strong-auth-gating/v1', 'scope': 'Original source/body facts only; no OEM execution or runtime acceptance', 'selectedProofs': [], 'archivePins': [], 'reusedCredentialProofs': [], 'frozenFrontendPins': []}
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    old = json.loads(output.read_text()) if output.exists() else None
    for (role, side), queries in SELECT.items():
        meta, rows = declarations(role, side)
        report['archivePins'].append({'role': role, 'side': side, 'archive': meta['archive'], 'sha256': meta['archiveSha256'], 'declarations': meta['declarations'], 'declarationsSha256': meta['declarationsSha256']})
        for name, methods in queries.items():
            row = rows['L' + name.replace('.', '/') + ';']
            exact = [m['name'] + m['descriptor'] for m in row['methods'] if m['name'] in methods]
            if set(m.split('(')[0] for m in exact) != set(methods):
                raise ValueError('Missing selected exact method ' + name)
            if args.collect:
                proof = read(PARENT / meta['archive'], meta['archiveSha256'], name, exact, stream='strong-auth-gating')
                proof = {k: proof[k] for k in ['receipt', 'raw', 'rawSha256', 'selectedMethodProofs', 'archiveAndToolPinsVerifiedBeforeAndAfter', 'readerExitCode']}
                proof.update({'role': role, 'side': side, 'class': name})
            else:
                if old is None:
                    raise ValueError('Use --collect for initial selected raw evidence')
                proof = next(p for p in old['selectedProofs'] if p['role'] == role and p['side'] == side and p['class'] == name)
                if {m['signature'] for m in proof['selectedMethodProofs']} != set(exact):
                    raise ValueError('Selected exact methods changed')
            read_bodies(proof)
            report['selectedProofs'].append(proof)
    shared_path = ROOT / 'out/credentials/shared-body-receipts.json'
    shared = json.loads(shared_path.read_text())
    report['credentialReceiptList'] = {'path': shared_path.relative_to(ROOT).as_posix(), 'sha256': digest(shared_path)}
    for side in ['samsung', 'coloros']:
        for name, starts in [('com.android.server.locksettings.LockSettingsService', ['doVerifyCredential(', 'onCredentialVerified(']), ('com.android.server.locksettings.SyntheticPasswordManager', ['unlockLskfBasedProtector('])]:
            proof = next(r for r in shared['receipts'] if r.get('side') == side and r.get('class') == name)
            selected = [r for r in read_bodies(proof) if r['body']['signature'].startswith(tuple(starts))]
            if len(selected) != len(starts):
                raise ValueError('Reused actual method missing')
            report['reusedCredentialProofs'].append({**proof, 'selectedBodies': [{'owner': r['body']['owner'], 'signature': r['body']['signature'], 'bodySha256': r['normalizedBodySha256'], 'physicalDex': r['physicalDex'], 'logicalHeaderOffset': r['logicalHeaderOffset']} for r in selected]})
    for name in ['docs/coloros-frontend.md', 'inventory/coloros-frontend.json', 'tools/audit_coloros_frontend.py']:
        report['frozenFrontendPins'].append({'path': name, 'sha256': digest(ROOT / name)})
    report['sourceEvidence'] = []
    sources = [KG + 'KeyguardSecurityContainerController', KG + 'KeyguardSecurityModel', KG + 'KeyguardSecurityViewFlipperController', KG + 'KeyguardInputViewController', KG + 'KeyguardSecureLockDeviceBiometricAuthViewController', UI + 'securelockdevice.data.repository.SecureLockDeviceRepositoryImpl', UI + 'securelockdevice.domain.interactor.SecureLockDeviceInteractor', UI + 'keyguard.shared.model.AuthenticationFlags', UI + 'securelockdevice.ui.viewmodel.SecureLockDeviceBiometricAuthContentViewModel', UI + 'keyguard.data.repository.BiometricSettingsRepositoryImpl']
    for name in sources:
        path = PARENT / 'firmware/donor/decompiled/SystemUI/sources' / (name.replace('.', '/') + '.java')
        report['sourceEvidence'].append({'path': path.relative_to(PARENT).as_posix(), 'sha256': digest(path)})
    report['runtimeVerified'] = False
    report['oemCodeExecuted'] = False
    report['phoneActions'] = False
    report['conclusions'] = {
        'colorosOriginalExtraFactorSupportExists': True,
        'directEarlyProgressForwardingProvedSafeForAllHostStates': False,
        'sourceSupportedFinishGuard': 'If candidate finish and secure-lock enabled and not authenticated-pending-dismissal, return false before finish',
        'stateNamespaceObligation': 'AuthenticationPolicyManager enabled listener, StrongAuth selected-user flags, biometric authenticated/confirmation and original finish flows must come from one genuine authority and live request generation',
        'unsupportedUntilProved': ['Uninitialized/missing/wrong-authority policy or tracker', 'secure mode without genuine same-authority factor/confirmation/finish closure', 'foreign or replaced user/operation', 'provisional progress followed by final failure/death', 'unmapped Knox/profile/remote/secondary policy'],
        'sourceCaveat': 'Both original Samsung and ColorOS SPMs emit early progress before blob unwrap and final synthetic-password challenge; this is not a proven cross-OEM timing discrepancy or OEM runtime vulnerability',
    }
    derive(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(output), 'queries': len(report['selectedProofs']), 'selectedMethods': sum(len(p['selectedMethodProofs']) for p in report['selectedProofs']), 'reusedCredentialBodies': sum(len(p['selectedBodies']) for p in report['reusedCredentialProofs']), 'runtimeVerified': False}))


if __name__ == '__main__':
    main()
