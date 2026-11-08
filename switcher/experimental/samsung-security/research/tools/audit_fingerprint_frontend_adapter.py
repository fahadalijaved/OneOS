"""Bounded fingerprint presentation contract receipts; no OEM/runtime execution.

Default validates saved exact bodies only. --collect reads the selected missing
classes/methods through the existing static reader. No whole-archive xref scan.
Raw OEM output remains in ignored firmware/fingerprint-frontend-adapter/.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
OUT = ROOT/'out/fingerprint-frontend-adapter'
LEDGER = OUT/'ledger.json'
INPUTS = {
    'framework-samsung': ('firmware/samsung/framework.jar', '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
    'framework': ('firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'settings': ('firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk', '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'),
    'systemui': ('firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk', '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'),
}
QUERIES = [
 ('framework-samsung','android.hardware.fingerprint.IFingerprintServiceReceiver$Stub$Proxy', ['onEnrollResult','onChallengeGenerated']),
 ('framework','android.hardware.fingerprint.IFingerprintServiceReceiver$Stub$Proxy', ['onEnrollResult','onChallengeGenerated']),
 ('framework','android.hardware.fingerprint.FingerprintCallback', ['sendAuthenticatedSucceeded','sendEnrollResult','sendChallengeGenerated','sendRemovedResult']),
 ('framework','android.hardware.fingerprint.FingerprintManager$FingerprintServiceReceiver', ['onAuthenticationSucceeded','onEnrollResult','onChallengeGenerated','lambda$onAuthenticationSucceeded$2','lambda$onEnrollResult$0','lambda$onChallengeGenerated$6']),
 ('settings','com.oplus.settings.feature.fingerprint.FingerprintEnrollProcessor', ['onEnrollProgress','isAvailableProgress','isDone','getEnrollmentSteps']),
 ('settings','com.oplus.settings.feature.fingerprint.FingerprintEnrollProcessor$FingerEnrollmentCallback', ['onEnrollmentProgress','onEnrollmentHelp','onEnrollmentError']),
 ('settings','com.oplus.settings.feature.fingerprint.utils.FingerprintUtils', ['getFingerListFromUser','getSystemCloneBiometricId']),
 ('settings','com.oplus.settings.feature.fingerprint.utils.FingerprintUtils', ['isSystemCloneFingerprint']),
 ('systemui','com.oplus.keyguard.utils.OplusSwitchUserUtil', ['isSubUserFingerprint$vendor__oplus__packages__apps__systemui__oplus_systemui__android_common__Oplus_SystemUI_application_export','numOfMainUserFingerprints','numOfSubUserFingerprints','switchToUserByFp','setFingerprintLists']),
 ('systemui','com.oplus.keyguard.OplusKeyguardUpdateMonitorExImpl', ['onFpAuthenticationSucceeded','isMultiSystemFpAuth']),
 ('systemui','com.android.keyguard.KeyguardUpdateMonitor$SafeFingerprintAuthCallback', ['validateAndDelegate']),
]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def collect():
    from static_security_reader import read_archive
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    for role,owner,names in QUERIES:
        key={'role':role,'owner':owner,'names':names}
        old=next((r for r in ledger if r['key']==key),None)
        if old:
            if digest(ROOT/old['raw'])!=old['rawSha256']: raise ValueError('Saved raw drift')
            continue
        path,pin=INPUTS[role]
        declaration=read_archive(PARENT/path,pin,class_name=owner,stream='fingerprint-frontend-adapter')
        declared=declaration['selectedClassDeclarations']
        if len(declared)!=1: raise ValueError('Missing/ambiguous selected class '+owner)
        methods=[m['signature'] for m in declared[0]['methods'] if m['signature'].split('(',1)[0] in names]
        if {m.split('(',1)[0] for m in methods}!=set(names): raise ValueError('Missing exact selected method in '+owner)
        proof=read_archive(PARENT/path,pin,class_name=owner,methods=methods,stream='fingerprint-frontend-adapter')
        ledger.append({'key':key,'declaration':declaration,**proof})
        LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')


def inspect_saved():
    ledger=json.loads(LEDGER.read_text());proofs=[];bodies={}
    expected={json.dumps({'role':role,'owner':owner,'names':names},sort_keys=True) for role,owner,names in QUERIES}
    if len(ledger)!=len(QUERIES) or {json.dumps(r['key'],sort_keys=True) for r in ledger}!=expected:
        raise ValueError('Incomplete or altered bounded frontier')
    for p in ledger:
        if digest(ROOT/p['raw'])!=p['rawSha256']: raise ValueError('Saved source proof changed')
        if p['archiveSha256']!=INPUTS[p['key']['role']][1] or p['readerExitCode']!=0:
            raise ValueError('Wrong source identity or incomplete read')
        for line in (ROOT/p['raw']).read_text(encoding='utf8').splitlines():
            r=json.loads(line)
            if r['record']!='method': continue
            b=r['body'];key=p['key']['role']+':'+b['owner']+'->'+b['signature'];bodies[key]=b
            proofs.append({'key':key,'physicalDex':r['physicalDex'],'logicalHeaderOffset':r['logicalHeaderOffset'],'normalizedBodySha256':r['normalizedBodySha256'],'raw':p['raw'],'rawSha256':p['rawSha256'],'receipt':p['receipt'],'instructionCount':len(b['instructions'])})
    return ledger,proofs,bodies


def contracts(bodies):
    checks=[]
    def find(role,owner,signature):
        return bodies[role+':L'+owner.replace('.','/')+';->'+signature]
    def at(body,pc):
        return next(i for i in body['instructions'] if i['pc']==pc)
    def call(body,pc,fragment,label):
        if fragment not in at(body,pc).get('reference',''): raise ValueError('Source contract changed: '+label)
        checks.append({'claim':label,'owner':body['owner'],'method':body['signature'],'pc':pc})
    proxy='android.hardware.fingerprint.IFingerprintServiceReceiver$Stub$Proxy'
    for role in ['framework-samsung','framework']:
        body=find(role,proxy,'onEnrollResult(Landroid/hardware/fingerprint/Fingerprint;I)V')
        call(body,14,'->writeTypedObject','Enrollment callback writes typed template before remaining')
        call(body,17,'->writeInt','Enrollment callback preserves remaining int')
        if at(body,23).get('literal')!=1: raise ValueError('Enrollment transaction/oneway constant changed')
        body=find(role,proxy,'onChallengeGenerated(IIJ)V')
        for pc,fragment in [(13,'->writeInt'),(16,'->writeInt'),(19,'->writeLong')]:
            call(body,pc,fragment,'Challenge sender preserves sensor/user/long challenge ordering')
        if at(body,25).get('literal')!=1 or at(body,26).get('literal')!=8:
            raise ValueError('Challenge transaction/oneway constants changed')
    owner='android.hardware.fingerprint.FingerprintCallback'
    body=find('framework',owner,'sendAuthenticatedSucceeded(Landroid/hardware/fingerprint/Fingerprint;IZ)V')
    call(body,21,'AuthenticationResult;-><init>','AuthenticationResult uses retained CryptoObject plus actual template/user/strength')
    call(body,26,'AuthenticationCallback;->onAuthenticationSucceeded','Original authentication callback receives the real result object')
    call(find('framework',owner,'sendEnrollResult(I)V'),34,'EnrollmentCallback;->onEnrollmentProgress','Enrollment callback consumes real remaining count')
    call(find('framework',owner,'sendChallengeGenerated(JII)V'),14,'->onChallengeGenerated(IIJ)V','Challenge callback preserves sensor/user/challenge argument roles')
    receiver='android.hardware.fingerprint.FingerprintManager$FingerprintServiceReceiver'
    body=find('framework',receiver,'onAuthenticationSucceeded(Landroid/hardware/fingerprint/Fingerprint;IZ)V')
    if at(body,60).get('reference')!='string=com.android.systemui': raise ValueError('Original inline package gate changed')
    call(body,70,'->sendAuthenticatedSucceeded','SystemUI package success path is direct')
    call(body,85,'HandlerExecutor;->execute','Other package success path uses original executor')
    call(find('framework',receiver,'onEnrollResult(Landroid/hardware/fingerprint/Fingerprint;I)V'),8,'FingerprintServiceReceiver;I)V','Enrollment receiver posts remaining only, not template fields')
    proc='com.oplus.settings.feature.fingerprint.FingerprintEnrollProcessor'
    body=find('settings',proc,'onEnrollProgress(I)V')
    call(body,23,'->isAvailableProgress','Optional animation filter precedes completion state update')
    if at(body,47).get('opcode')!='IF_NEZ' or at(body,52).get('reference','').endswith('mDone:Z') is False:
        raise ValueError('Original remaining-zero completion contract changed')
    call(body,60,'->onEnrollmentProgressChange(II)V','Original listener receives steps and actual remaining')
    util='com.oplus.settings.feature.fingerprint.utils.FingerprintUtils'
    body=find('settings',util,'getFingerListFromUser()Ljava/util/List;')
    call(body,34,'OplusMultiUserFingerprintManager;->getEnrolledFingerprints','Settings currently depends on OEM list provider even for main user')
    for pc in [137,164,193]: call(body,pc,'Fingerprint;-><init>(Ljava/lang/CharSequence;IIJ)V','Original Settings already reconstructs common tuple without copying OEM flags')
    body=find('settings',util,'isSystemCloneFingerprint(Landroid/hardware/fingerprint/OplusFingerprint;)Z')
    if at(body,4).get('literal')!=0x10000000: raise ValueError('Clone classification bit changed')
    call(body,0,'->getFingerFlags','OPPO flags classify system-clone templates')
    switch='com.oplus.keyguard.utils.OplusSwitchUserUtil'
    body=find('systemui',switch,'switchToUserByFp(Landroid/content/Context;I)Z')
    call(body,2,'->isSubUserFingerprint','Fingerprint ID plus OEM list classification controls user-switch target')
    call(body,11,'->getMultiSystemUserId','Clone target comes from OEM multiuser manager')
    if at(body,6).get('literal')!=0 or at(body,16).get('registers')!=[5,0]:
        raise ValueError('Original main-user fallback changed')
    ex='com.oplus.keyguard.OplusKeyguardUpdateMonitorExImpl'
    call(find('systemui',ex,'onFpAuthenticationSucceeded(Landroid/hardware/fingerprint/FingerprintManager$AuthenticationResult;ZLandroid/hardware/fingerprint/FingerprintManager$AuthenticationCallback;)Z'),401,'->switchToUserByFp','Original successful-auth OEM hook actually reaches flag-dependent user switching')
    safe=find('systemui','com.android.keyguard.KeyguardUpdateMonitor$SafeFingerprintAuthCallback','validateAndDelegate(Ljava/lang/String;Ljava/lang/Runnable;)V')
    call(safe,59,'Runnable;->run','Original safe auth callback runs only after monitor/session comparison')
    return checks


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.collect: collect()
    ledger,proofs,bodies=inspect_saved()
    # Curated body identities only. OEM instructions and strings stay in raw.
    report={'schema':'fingerprint-frontend-adapter-methods/v1','scope':'Selected consumer method bodies only; no converter, source authenticity or runtime acceptance','inputs':INPUTS,'proofs':proofs,'sourceAssertions':contracts(bodies),'toolSha256':digest(__file__),'oemExecuted':False,'androidExecuted':False,'phoneActions':False}
    (OUT/'method-proofs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selectedClasses':len({(r['key']['role'],r['key']['owner']) for r in ledger}),'selectedMethods':len(proofs),'report':'out/fingerprint-frontend-adapter/method-proofs.json','oemExecuted':False}))


if __name__=='__main__': main()
