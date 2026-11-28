"""Bounded saved-source reader for the Samsung-authority/ColorOS-UI proposal.

No OEM execution, Binder publication, service binding or phone operation.
--collect requests only the named methods; default rechecks saved receipts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
OUT=ROOT/'out/biometric-ui-authority'
LEDGER=OUT/'ledger.json'
INPUTS={
 'services':('firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
 'framework':('firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
 'systemui':('firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk','0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'),
 'guest-framework':('firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
 'guest-services':('firmware/donor/extracted/system/framework/services.jar','66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
}
QUERIES=[
 ('services','com.android.server.biometrics.SemBiometricSysUiWrapper',['showAuthenticationDialog','hideAuthenticationDialog','onBiometricError']),
 ('services','com.android.server.biometrics.sensors.fingerprint.SemFpSysUiImpl',['<init>','start','stop','onDismissed','setAttribute','handleOnError']),
 ('services','com.android.server.biometrics.sensors.fingerprint.SemUdfpsSysUiImpl',['<init>','stop','handleOnError']),
 ('services','com.android.server.biometrics.sensors.fingerprint.aidl.SemFingerprintEnrollClient',['createSysUiImpl','startHalOperation','stopHalOperation']),
 ('systemui','com.android.systemui.biometrics.AuthController',['showAuthenticationDialog','hideAuthenticationDialog','onBiometricAuthenticated','onBiometricHelp','onBiometricError','onDismissed']),
 ('systemui','com.android.systemui.biometrics.AuthContainerView',['onDialogAnimatedIn','removeWindowIfAttached','animateAway','onCredentialMatched','sendEarlyUserCanceled','dismissWithoutCallback']),
 ('services','com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda8',['run']),
 ('services','com.android.server.biometrics.sensors.fingerprint.aidl.SemFingerprintEnrollClient',['start']),
 ('services','com.android.server.biometrics.BiometricService$2',['onDialogAnimatedIn','onDialogDismissed','onPauseAuthentication','onResumeAuthentication','onSysUiError','onSystemEvent']),
 ('services','com.android.server.biometrics.AuthSession',['<init>','hasAuthenticatedAndConfirmed','isConfirmationRequired','onCancelAuthSession']),
 ('systemui','com.android.systemui.biometrics.AuthContainerView$BiometricCallback',['onAuthenticated','onAuthenticatedAndConfirmed','onButtonNegative','onButtonTryAgain','onStartDelayedFingerprintSensor','onUseDeviceCredential','onUserCanceled']),
 ('systemui','com.android.systemui.biometrics.AuthController',['getCurrentReceiver','showDialog']),
 ('services','com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda15',['run']),
 ('services','com.android.server.biometrics.SemBiometricSysUiReceiver$1',['onDismissed','onError','onEvent']),
 ('services','com.android.server.biometrics.BiometricService$1$$ExternalSyntheticLambda0',['run']),
 ('services','com.android.server.biometrics.BiometricService$2$$ExternalSyntheticLambda3',['run']),
 ('services','com.android.server.biometrics.BiometricService$2$$ExternalSyntheticLambda8',['run']),
 ('services','com.android.server.biometrics.BiometricService$2$$ExternalSyntheticLambda6',['run']),
 ('services','com.android.server.biometrics.sensors.SensorOverlays',['show','hide']),
 ('services','com.android.server.biometrics.BiometricService$2',['onTryAgainPressed','onDeviceCredentialPressed','onStartFingerprintNow','asBinder']),
 ('services','com.android.server.biometrics.BiometricService',['handleOnDismissed','handleAuthenticationSucceeded']),
 ('systemui','com.android.systemui.biometrics.AuthContainerView',['addCredentialView']),
 ('guest-services','com.android.server.statusbar.StatusBarManagerService',['showAuthenticationDialog','hideAuthenticationDialog']),
 ('systemui','com.android.systemui.statusbar.CommandQueue',['showAuthenticationDialog','hideAuthenticationDialog']),
]


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def collect():
    from static_security_reader import read_archive
    ledger=json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    for role,owner,names in QUERIES:
        key={'role':role,'owner':owner,'names':names}
        old=next((r for r in ledger if r['key']==key),None)
        if old:
            if digest(ROOT/old['raw'])!=old['rawSha256']:raise ValueError('Saved raw changed')
            continue
        path,pin=INPUTS[role]
        declaration=read_archive(PARENT/path,pin,class_name=owner,stream='biometric-ui-authority')
        classes=declaration['selectedClassDeclarations']
        if len(classes)!=1:raise ValueError('Exact class unavailable '+owner)
        methods=[m['signature'] for m in classes[0]['methods'] if m['signature'].split('(',1)[0] in names]
        if {m.split('(',1)[0] for m in methods}!=set(names):
            raise ValueError('Selected method absent '+owner+': '+str(set(names)-{m.split('(',1)[0] for m in methods}))
        result=read_archive(PARENT/path,pin,class_name=owner,methods=methods,stream='biometric-ui-authority')
        ledger.append({'key':key,'declaration':declaration,**result})
        LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')


def saved():
    ledger=json.loads(LEDGER.read_text());bodies={};proofs=[]
    expected={(r,o,tuple(n)) for r,o,n in QUERIES}
    actual={(p['key']['role'],p['key']['owner'],tuple(p['key']['names'])) for p in ledger}
    if len(ledger)!=len(expected) or actual!=expected:raise ValueError('Bounded query set changed')
    for p in ledger:
        if digest(ROOT/p['raw'])!=p['rawSha256'] or p['archiveSha256']!=INPUTS[p['key']['role']][1] or p['readerExitCode']!=0:
            raise ValueError('Saved exact source receipt drift')
        for line in (ROOT/p['raw']).read_text().splitlines():
            row=json.loads(line)
            if row['record']!='method':continue
            b=row['body'];key=p['key']['role']+':'+b['owner']+'->'+b['signature']
            if key in bodies:raise ValueError('Duplicate selected method')
            bodies[key]=b
            proofs.append({'key':key,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'normalizedBodySha256':row['normalizedBodySha256'],'raw':p['raw'],'rawSha256':p['rawSha256'],'receipt':p['receipt']})
    return ledger,bodies,proofs


def assertions(bodies):
    """Pin source edges, not authenticity of an assembled adapter or runtime."""
    rows=[]
    def check(label,selector,pc,opcode,reference=None,**fields):
        matches=[(k,b) for k,b in bodies.items() if selector in k]
        if len(matches)!=1:raise ValueError('Ambiguous source assertion '+label)
        key,body=matches[0]
        ins=next((i for i in body['instructions'] if i['pc']==pc),None)
        if ins is None or ins['opcode']!=opcode or (reference is not None and reference not in ins.get('reference','')) or any(ins.get(k)!=v for k,v in fields.items()):
            raise ValueError('Source edge drift '+label)
        rows.append({'id':label,'method':key,'pc':pc,'instruction':ins})
    check('outer-auth-session-op-id','AuthSession;-><init>',68,'IPUT_WIDE','->mOperationId:J')
    check('outer-auth-session-opens-companion','AuthSession;-><init>',241,'INVOKE_VIRTUAL','SysUiManager;->openSession(')
    check('provider-bp-skips-sensor-ui-session','FingerprintProvider$$ExternalSyntheticLambda8;->run',374,'IF_NEZ',targetPc=442)
    check('sensor-bp-skips-show','SemFpSysUiImpl;->start',2,'IF_NEZ',targetPc=42)
    check('enroll-opens-sensor-ui-session','Lambda15;->run',264,'INVOKE_VIRTUAL','SysUiManager;->openSession(')
    check('enroll-starts-real-helper','SemFingerprintEnrollClient;->startHalOperation',4,'INVOKE_VIRTUAL','SemFpSysUiImpl;->start()V')
    check('enroll-udfps-native-touch','SemFingerprintEnrollClient;->startHalOperation',21,'INVOKE_VIRTUAL','SemUdfpsTspManager;->enable(I)V')
    check('enroll-real-overlay','SemFingerprintEnrollClient;->startHalOperation',76,'INVOKE_VIRTUAL','SensorOverlays;->show(')
    check('guest-controller-main-thread','AuthController;->showDialog',9,'INVOKE_VIRTUAL','->assertIsMainThread()V')
    check('guest-original-confirm-policy','AuthController;->showDialog',79,'IPUT_BOOLEAN','->mRequireConfirmation:Z')
    check('guest-original-op-id','AuthController;->showDialog',89,'IPUT_WIDE','->mOperationId:J')
    check('guest-prompt-shown-is-early','AuthController;->showDialog',179,'INVOKE_INTERFACE','->onBiometricPromptShown(')
    check('guest-actual-window-show','AuthController;->showDialog',316,'INVOKE_VIRTUAL','AuthContainerView;->show(')
    check('guest-real-ready-request','AuthContainerView;->onDialogAnimatedIn',65,'INVOKE_VIRTUAL','->getCurrentReceiver(J)')
    check('guest-real-ready-inverts-delay','AuthContainerView;->onDialogAnimatedIn',64,'XOR_INT_2ADDR',registers=[0,1])
    check('guest-real-ready-callback','AuthContainerView;->onDialogAnimatedIn',79,'INVOKE_INTERFACE','->onDialogAnimatedIn(Z)V')
    check('source-ready-removes-watchdog','BiometricService$2;->onDialogAnimatedIn',14,'INVOKE_VIRTUAL','->removeCallbacks(')
    check('source-ready-current-request','BiometricService$2$$ExternalSyntheticLambda3;->run',16,'INVOKE_VIRTUAL','->getAuthSessionIfCurrent(J)')
    check('source-ready-false-delays','BiometricService$2$$ExternalSyntheticLambda3;->run',71,'IF_EQZ',targetPc=82)
    check('source-ready-true-starts-prepared','BiometricService$2$$ExternalSyntheticLambda3;->run',78,'INVOKE_VIRTUAL','->startAllPreparedSensors(')
    check('source-callback-has-no-binder','BiometricService$2;->asBinder',0,'CONST_4',literal=0)
    check('guest-retry-exact-action','BiometricCallback;->onButtonTryAgain',29,'INVOKE_INTERFACE','->onTryAgainPressed()V')
    check('guest-delayed-fp-exact-action','BiometricCallback;->onStartDelayedFingerprintSensor',24,'INVOKE_INTERFACE','->onStartFingerprintNow()V')
    check('guest-credential-exact-action','BiometricCallback;->onUseDeviceCredential',24,'INVOKE_INTERFACE','->onDeviceCredentialPressed()V')
    check('guest-credential-actual-terminal-branch','AuthContainerView;->onCredentialMatched',2,'IF_EQZ',targetPc=10)
    check('guest-credential-resume','AuthContainerView;->onCredentialMatched',45,'INVOKE_INTERFACE','->onResumeAuthentication()V')
    check('source-hardware-match-current-request','BiometricService;->handleAuthenticationSucceeded',8,'INVOKE_VIRTUAL','->getAuthSessionIfCurrent(J)')
    check('source-hardware-token-escrow','BiometricService;->handleAuthenticationSucceeded',81,'IPUT_OBJECT','->mTokenEscrow:[B')
    check('source-hardware-confirmation-policy','BiometricService;->handleAuthenticationSucceeded',217,'INVOKE_VIRTUAL','->isConfirmationRequired(')
    check('source-dismiss-current-request','BiometricService;->handleOnDismissed',8,'INVOKE_VIRTUAL','->getAuthSessionIfCurrent(J)')
    check('source-credential-native-token','BiometricService;->handleOnDismissed',248,'INVOKE_VIRTUAL','KeyStoreAuthorization;->addAuthToken([B)I')
    check('source-biometric-native-token','BiometricService;->handleOnDismissed',299,'INVOKE_VIRTUAL','KeyStoreAuthorization;->addAuthToken([B)I')
    check('source-app-result-separate-from-token','BiometricService;->handleOnDismissed',372,'INVOKE_INTERFACE','->onAuthenticationSucceeded(I)V')
    check('guest-statusbar-permission','StatusBarManagerService;->showAuthenticationDialog',0,'INVOKE_DIRECT','->enforceBiometricDialog()V')
    check('guest-statusbar-user-policy','StatusBarManagerService;->showAuthenticationDialog',3,'INVOKE_DIRECT','->enforceValidCallingUser()V')
    check('guest-command-message','CommandQueue;->showAuthenticationDialog',35,'CONST_HIGH16',literal=2555904)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.collect:collect()
    for path,pin in INPUTS.values():
        if digest(PARENT/path)!=pin:raise ValueError('Original archive identity changed')
    ledger,bodies,proofs=saved()
    checks=assertions(bodies)
    report={'schema':'biometric-ui-authority-methods/v1','scope':'Selected static source methods only; no adapter/runtime acceptance','inputs':INPUTS,'proofs':proofs,'assertions':checks,'toolSha256':digest(__file__),'oemExecuted':False,'androidExecuted':False,'phoneActions':False}
    (OUT/'method-proofs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selectedQueries':len(ledger),'selectedMethods':len(bodies),'sourceAssertions':len(checks),'report':'out/biometric-ui-authority/method-proofs.json'}))


if __name__=='__main__':main()
