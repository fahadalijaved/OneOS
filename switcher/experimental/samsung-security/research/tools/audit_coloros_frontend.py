"""Bounded offline ColorOS presentation contract evidence; no OEM execution."""
import gzip
import hashlib
import json
import argparse
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
INDEX = PARENT / 'out/os-comparison-resumed/archive-index'
SRC = 'firmware/donor/decompiled/SystemUI/sources/'
TARGETS = {
    'com/android/internal/widget/ILockSettings': ['checkCredential', 'verifyCredential', 'getCredentialType', 'getPinLength', 'getLockoutEndTime', 'getStrongAuthForUser', 'registerStrongAuthTracker', 'unregisterStrongAuthTracker', 'requireStrongAuth', 'userPresent', 'reportSuccessfulBiometricUnlock', 'setLockCredential'],
    'com/android/internal/widget/ILockSettings$Stub': ['asInterface', 'getDefaultTransactionName'],
    'com/android/internal/widget/VerifyCredentialResponse': ['isMatched', 'hasTimeout', 'getTimeout', 'isCredAlreadyTried', 'getGatekeeperHAT', 'getGatekeeperPasswordHandle', 'writeToParcel'],
    'com/android/internal/widget/LockscreenCredential': ['createPinOrNone', 'createPasswordOrNone', 'writeToParcel', 'zeroize'],
    'com/android/internal/widget/ICheckCredentialProgressCallback': ['onCredentialVerified'],
    'android/hardware/fingerprint/IFingerprintService': ['authenticate', 'detectFingerprint', 'cancelAuthentication', 'getSensorPropertiesInternal', 'getEnrolledFingerprints', 'getAuthenticatorId', 'getLockoutModeForUser', 'addLockoutResetCallback'],
    'android/hardware/fingerprint/IFingerprintServiceReceiver': ['onAuthenticationSucceeded', 'onAuthenticationFailed', 'onError', 'onAcquired', 'onFingerprintDetected'],
    'android/hardware/fingerprint/FingerprintAuthenticateOptions': ['writeToParcel', 'getUserId', 'getSensorId', 'getOpPackageName', 'getAttributionTag'],
}
SOURCES = {
    'com/oplus/keyguard/security/view/OplusKeyguardPinViewController.java': ['getEnteredCredential', 'LockscreenCredential.createPinOrNone'],
    'com/oplus/keyguard/security/view/OplusKeyguardPasswordViewController.java': ['getEnteredCredential', 'LockscreenCredential.createPasswordOrNone'],
    'com/oplus/keyguard/security/view/OplusKeyguardAbsKeyInputViewController.java': ['onPasswordChecked', 'getLockoutEndTime', 'getKeyguardSecurityCallback().dismiss', 'getChecker().checkPassword'],
    'com/oplus/keyguard/security/OplusLockPatternChecker.java': ['public final void onChecked', 'public final void onEarlyMatched', 'getLockSettings().checkCredential', 'verifyCredentialResponse.isMatched()', 'verifyCredentialResponse.isCredAlreadyTried()', 'getMultiSystemUserId', 'setTargetUerIdByPw', 'this.cannotCancel', 'getTimeout().toMillis()'],
    'com/oplus/keyguard/security/verify/RpmbCheckTask.java': ['getGatekeeperHAT()', 'RpmbChecker.checkPassword'],
    'com/oplus/keyguard/security/verify/RpmbChecker.java': ['CE_CMD_PMS_VERIFY', 'RpmbChannel.processCmdV2'],
    'com/oplus/keyguard/security/verify/OplusKeyguardVerifyManagerExImpl.java': ['public final void postRpmbCheckTask', 'rpmbCheckTask.mUserId != 0', 'submitOnThreadExecutor(rpmbCheckTask)'],
    'com/oplus/keyguard/utils/KeyguardPasswordUtils.java': ['public static final int getNumericPwdLength', 'OplusSyntheticPasswordManager.triggerChannelOpen'],
    'com/oplus/keyguard/security/OplusKeyguardSecurityModel.java': ['getActivePasswordQuality(currentUser)', 'KeyguardPasswordUtils.getNumericPwdLength', 'public final KeyguardSecurityModel.SecurityMode getSecurityMode'],
    'com/oplus/systemui/keyguard/OplusKeyguardBouncerExImpl.java': ['OplusKeyguardSecurityModel.INSTANCE.getSecurityMode'],
    'com/android/keyguard/KeyguardSecurityContainerController.java': ['reportSuccessfulPasswordAttempt', 'reportFailedPasswordAttempt', 'getMaximumFailedPasswordsForWipe', 'reportPasswordLockout', 'showNextSecurityScreenOrFinish'],
    'com/android/keyguard/KeyguardUpdateMonitor.java': ['public final void handleFingerprintAuthenticated', 'public void onFingerprintAuthenticated', 'public final void startListeningForFingerprint', 'public final void stopListeningForFingerprint', 'isBiometricAllowedForUser', 'requireStrongAuth(8', 'unlockedByBiometricForUser', 'mBoundSessionId == keyguardUpdateMonitor.mCurrentFingerprintSessionId', 'fingerprintManager.authenticate', 'new FingerprintAuthenticateOptions.Builder().setUserId'],
    'com/android/keyguard/KeyguardUpdateMonitor$$ExternalSyntheticLambda8.java': ['reportSuccessfulBiometricUnlock'],
    'com/android/systemui/keyguard/KeyguardViewMediator.java': ['mLockPatternUtils.userPresent'],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_contracts(report):
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    queries = {
        'com.android.internal.widget.ILockSettings$Stub$Proxy': ['checkCredential(Lcom/android/internal/widget/LockscreenCredential;ILcom/android/internal/widget/ICheckCredentialProgressCallback;)Lcom/android/internal/widget/VerifyCredentialResponse;'],
        'com.android.internal.widget.ILockSettings$Stub': ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'],
        'com.android.internal.widget.VerifyCredentialResponse': ['writeToParcel(Landroid/os/Parcel;I)V', 'isMatched()Z', 'isCredAlreadyTried()Z', 'hasTimeout()Z'],
        'com.android.internal.widget.VerifyCredentialResponse$1': ['createFromParcel(Landroid/os/Parcel;)Lcom/android/internal/widget/VerifyCredentialResponse;'],
        'com.android.internal.widget.LockscreenCredential': ['writeToParcel(Landroid/os/Parcel;I)V'],
        'com.android.internal.widget.LockscreenCredential$1': ['createFromParcel(Landroid/os/Parcel;)Lcom/android/internal/widget/LockscreenCredential;'],
        'com.android.internal.widget.ICheckCredentialProgressCallback$Stub$Proxy': ['onCredentialVerified()V'],
    }
    receipts = {}
    for side, metadata in report['sides'].items():
        receipts[side] = []
        for owner, methods in queries.items():
            result = reader(PARENT / metadata['archive'], metadata['archiveSha256'], owner, methods, stream='coloros-frontend')
            receipts[side].append({key: result[key] for key in ['receipt', 'raw', 'rawSha256', 'selectedMethodProofs', 'archiveAndToolPinsVerifiedBeforeAndAfter', 'readerExitCode']})
    report['selectedRawProofs'] = receipts
    systemui = json.loads((INDEX / 'comparisons/systemui/summary.json').read_text())['coloros']
    ui_queries = {
        'com.oplus.keyguard.security.OplusLockPatternChecker$oplusCheckCredential$task$1': ['doInBackground([Ljava/lang/Object;)Ljava/lang/Object;', 'onPostExecute(Ljava/lang/Object;)V'],
        'com.oplus.keyguard.security.OplusLockPatternChecker$checkCredential$1': ['onEarlyMatched()V', 'onChecked(Lcom/android/internal/widget/VerifyCredentialResponse;IZ)V'],
        'com.oplus.keyguard.security.verify.RpmbCheckTask': ['run()V'],
        'com.oplus.keyguard.security.OplusKeyguardSecurityModel': ['getDeviceSecurityMode(Landroid/content/Context;Lcom/android/internal/widget/LockPatternUtils;)Lcom/android/keyguard/KeyguardSecurityModel$SecurityMode;'],
    }
    report['selectedUiProofs'] = []
    for owner, methods in ui_queries.items():
        result = reader(PARENT / systemui['archive'], systemui['archiveSha256'], owner, methods, stream='coloros-frontend')
        report['selectedUiProofs'].append({key: result[key] for key in ['receipt', 'raw', 'rawSha256', 'archiveSha256', 'selectedMethodProofs', 'archiveAndToolPinsVerifiedBeforeAndAfter', 'readerExitCode']})


def derive_contracts(report):
    methods = {}
    for side, receipts in report['selectedRawProofs'].items():
        methods[side] = {}
        for receipt in receipts:
            raw = ROOT / receipt['raw']
            if sha(raw) != receipt['rawSha256']:
                raise ValueError('Selected raw proof changed')
            for line in raw.read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                if row['record'] == 'method':
                    body = row['body']
                    methods[side][(body['owner'], body['signature'])] = body
    proxy_owner = 'Lcom/android/internal/widget/ILockSettings$Stub$Proxy;'
    signature = 'checkCredential(Lcom/android/internal/widget/LockscreenCredential;ILcom/android/internal/widget/ICheckCredentialProgressCallback;)Lcom/android/internal/widget/VerifyCredentialResponse;'
    numbers = {}
    for side, bodies in methods.items():
        registers = {}
        for ins in bodies[(proxy_owner, signature)]['instructions']:
            if ins['opcode'].startswith('CONST') and 'literal' in ins:
                registers[ins['registers'][0]] = ins['literal']
            if '->transact(' in ins.get('reference', ''):
                numbers[side] = {'transaction': registers[ins['registers'][1]], 'flags': registers[ins['registers'][4]], 'invokePc': ins['pc']}
        if numbers[side]['transaction'] != {'samsung': 54, 'coloros': 10}[side]:
            raise ValueError('Reviewed transaction changed')
    def refs(side, owner, signature):
        return [i['reference'] for i in methods[side][('Lcom/android/internal/widget/' + owner + ';', signature)]['instructions'] if 'reference' in i]
    comparisons = {}
    for owner, signature in [('VerifyCredentialResponse', 'writeToParcel(Landroid/os/Parcel;I)V'), ('VerifyCredentialResponse$1', 'createFromParcel(Landroid/os/Parcel;)Lcom/android/internal/widget/VerifyCredentialResponse;'), ('LockscreenCredential', 'writeToParcel(Landroid/os/Parcel;I)V'), ('LockscreenCredential$1', 'createFromParcel(Landroid/os/Parcel;)Lcom/android/internal/widget/LockscreenCredential;')]:
        equal = refs('samsung', owner, signature) == refs('coloros', owner, signature)
        if not equal:
            raise ValueError('Reviewed parcel reference sequence changed')
        comparisons[owner + '->' + signature] = {'referenceSequenceEqual': True, 'note': 'Inspected register/control flow also; equality alone is not cryptographic or runtime proof'}
    stub = methods['samsung'][('Lcom/android/internal/widget/ILockSettings$Stub;', 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')]['instructions']
    dispatch = next(i for i in stub if i['opcode'] == 'PACKED_SWITCH')
    payload = next(i for i in stub if i['pc'] == dispatch['targetPc'])
    branch10 = dispatch['pc'] + next(e for e in payload['switchElements'] if e['key'] == 10)['offsetFromReferringSwitchPc']
    call = next(i for i in stub if i['pc'] >= branch10 and 'Lcom/android/internal/widget/ILockSettings$Stub;->' in i.get('reference', ''))
    if not call['reference'].endswith('->setCarrierLockEnabled(I)V'):
        raise ValueError('Reviewed Samsung transaction10 changed')
    report['derivedRawContracts'] = {'checkCredential': numbers, 'sameDescriptor': 'com.android.internal.widget.ILockSettings', 'rawBinderForwardingCompatible': False, 'samsungTransaction10Dispatch': {'method': 'setCarrierLockEnabled(I)V', 'branchPc': branch10, 'invokePc': call['pc']}, 'parcelComparisons': comparisons, 'responseWireOrder': ['responseCode:int', 'timeoutSeconds:long', 'timeoutNanos:int', 'gatekeeperHAT:byte[]', 'gatekeeperPasswordHandle:long'], 'credentialWireOrder': ['type:int', 'credential:byte[]', 'hasInvalidChars:boolean', 'isUnifiedProfilePassword:boolean'], 'observedPredicates': {'matchedCode': 0, 'duplicateCode': 3}, 'progressCallback': {'descriptor': 'com.android.internal.widget.ICheckCredentialProgressCallback', 'transaction': 1, 'oneway': True, 'args': []}, 'runtimeAccepted': False}
    ui_edges = []
    terms = ['->checkCredential(', '->onPasswordChecked(', '->getGatekeeperHAT(', 'RpmbChecker;->checkPassword(', '->getActivePasswordQuality(', '->getNumericPwdLength(', 'RpmbCheckTask;-><init>', '->postRpmbCheckTask(', '->sendUnlockBroadcast(', '->setTargetUerIdByPw(']
    for receipt in report.get('selectedUiProofs', []):
        raw = ROOT / receipt['raw']
        if sha(raw) != receipt['rawSha256']:
            raise ValueError('Selected UI raw proof changed')
        for line in raw.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row['record'] != 'method':
                continue
            body = row['body']
            for ins in body['instructions']:
                if any(term in ins.get('reference', '') for term in terms):
                    ui_edges.append({'caller': body['owner'] + '->' + body['signature'], 'pc': ins['pc'], 'callee': ins['reference'], 'proofBodySha256': row['normalizedBodySha256']})
    if report.get('selectedUiProofs') and len(ui_edges) != 11:
        raise ValueError('Reviewed original UI edge closure changed')
    report['derivedRawContracts']['uiObservedEdges'] = ui_edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-contracts', action='store_true')
    args = parser.parse_args()
    summary_path = INDEX / 'comparisons/framework/summary.json'
    summary = json.loads(summary_path.read_text())
    report = {'schema': 'coloros-frontend-contracts/v1', 'scope': 'Offline original source/declaration evidence only; no installed-image or runtime acceptance', 'declarationSummary': {'path': summary_path.relative_to(PARENT).as_posix(), 'sha256': sha(summary_path)}, 'sides': {}, 'sourceEvidence': []}
    for side in ['samsung', 'coloros']:
        meta = summary[side]
        declarations = PARENT / meta['declarations']
        if sha(declarations) != meta['declarationsSha256']:
            raise ValueError('Immutable declaration index changed')
        archive = PARENT / meta['archive']
        if sha(archive) != meta['archiveSha256']:
            raise ValueError('Indexed framework archive changed')
        wanted = {'L' + name + ';': methods for name, methods in TARGETS.items()}
        rows = {}
        with gzip.open(declarations, 'rt', encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                desc = row.get('descriptor')
                if desc not in wanted:
                    continue
                if desc in rows:
                    raise ValueError('Ambiguous definition: ' + desc)
                rows[desc] = {'physicalDex': row['physicalDex'], 'logicalHeaderOffset': row['logicalHeaderOffset'], 'methods': [m for m in row['methods'] if m['name'] in wanted[desc]], 'fields': [f for f in row['fields'] if f['name'].startswith(('TRANSACTION_', 'DESCRIPTOR')) or desc.endswith('VerifyCredentialResponse;')]}
        if set(rows) != set(wanted):
            raise ValueError('Required declaration absent: ' + str(set(wanted) - set(rows)))
        report['sides'][side] = {'archive': meta['archive'], 'archiveSha256': meta['archiveSha256'], 'index': meta['declarations'], 'indexSha256': meta['declarationsSha256'], 'classes': rows}
    for relative, terms in SOURCES.items():
        path = PARENT / SRC / relative
        lines = path.read_text(encoding='utf-8').splitlines()
        evidence = []
        for term in terms:
            found = [i for i, line in enumerate(lines, 1) if term in line]
            if not found:
                raise ValueError('Source anchor absent: ' + relative + ' ' + term)
            # Authored anchor labels + line positions, never proprietary method bodies.
            evidence.append({'anchor': term, 'lines': found})
        report['sourceEvidence'].append({'path': path.relative_to(PARENT).as_posix(), 'sha256': sha(path), 'anchors': evidence})
    report['unproved'] = ['Full remaining policy-interface transaction/parcel compatibility', 'Installed OneOS effective patch/image identity', 'Samsung authority startup/import/retention and caller permissions', 'Cross-runtime user serial/SID/protector/template/StrongAuth/Trust/keystore identity', 'Authenticated hardware HAT acceptance and real host/guest unlock', 'ColorOS RPMB consumer compatibility', 'Cancellation/drain/recovery and return/reboot preservation']
    output = ROOT / 'inventory/coloros-frontend.json'
    if args.raw_contracts:
        raw_contracts(report)
    elif output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        if previous['sides'] == report['sides'] and 'selectedRawProofs' in previous:
            report['selectedRawProofs'] = previous['selectedRawProofs']
            if 'selectedUiProofs' in previous:
                report['selectedUiProofs'] = previous['selectedUiProofs']
    if 'selectedRawProofs' in report:
        derive_contracts(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(output), 'classesPerSide': len(TARGETS), 'sourceFiles': len(SOURCES), 'runtimeVerified': False}))


if __name__ == '__main__':
    main()
