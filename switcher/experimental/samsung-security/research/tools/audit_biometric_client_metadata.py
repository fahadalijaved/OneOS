"""Bounded original client Context/authenticate/cancel metadata source audit.

Static reader only. No client helper, converter, protocol, Binder publication,
Android/OEM code, hardware operation or phone action is implemented/executed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
OUT=ROOT/'out/biometric-client-metadata'
LEDGER=OUT/'ledger.json'
PROMPT_INVENTORY='inventory/prompt-wire-contract.json'
PROMPT_SHA='834670bcd74636b9171a06fd50066d40cdc71a88c74c3a833bcf59f32649a4bf'
INPUTS={
 'guest':('firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
 'samsung':('firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
 'samsung-services':('firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
}
QUERIES=[
 ('guest','android.hardware.biometrics.BiometricPrompt',['<init>','authenticate']),
 ('guest','android.hardware.biometrics.BiometricPrompt$OnAuthenticationCancelListener',['<init>','onCancel']),
 ('guest','android.hardware.biometrics.BiometricPrompt',['authenticateInternal(Landroid/hardware/biometrics/BiometricPrompt$CryptoObject;Landroid/os/CancellationSignal;Ljava/util/concurrent/Executor;Landroid/hardware/biometrics/BiometricPrompt$AuthenticationCallback;I)V']),
 ('guest','android.os.CancellationSignal',['cancel','setOnCancelListener']),
 ('samsung-services','com.android.server.biometrics.AuthService$AuthServiceImpl',['cancelAuthentication']),
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
        declaration=read_archive(PARENT/path,pin,class_name=owner,stream='biometric-client-metadata')
        classes=declaration['selectedClassDeclarations']
        if len(classes)!=1:raise ValueError('Exact class unavailable '+owner)
        exact=all('(' in name for name in names)
        methods=[m['signature'] for m in classes[0]['methods'] if (m['signature'] in names if exact else m['signature'].split('(',1)[0] in names)]
        if (set(methods) if exact else {m.split('(',1)[0] for m in methods})!=set(names):raise ValueError('Selected method absent '+owner)
        result=read_archive(PARENT/path,pin,class_name=owner,methods=methods,stream='biometric-client-metadata')
        ledger.append({'key':key,'declaration':declaration,**result})
        LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')


def reused():
    if digest(ROOT/PROMPT_INVENTORY)!=PROMPT_SHA:raise ValueError('Reviewed conditional prompt inventory changed')
    inv=json.loads((ROOT/PROMPT_INVENTORY).read_text());selected=[];bodies={};proofs=[]
    for p in inv['selectedMethodProofs']:
        role=next((r for r,(_,h) in INPUTS.items() if h==p['archiveSha256']),None)
        name=p['signature'].split('(',1)[0];owner=p['owner']
        take=(role in ('guest','samsung') and owner=='Landroid/hardware/biometrics/BiometricPrompt;' and name in ('authenticateInternal','cancelAuthentication')) or (role=='samsung' and owner=='Landroid/hardware/biometrics/BiometricPrompt;' and name=='semSetExtraInfo') or (role=='guest' and owner=='Landroid/hardware/biometrics/BiometricPrompt$Builder;' and name in ('<init>','build')) or (role=='samsung-services' and owner=='Lcom/android/server/biometrics/AuthService$AuthServiceImpl;' and name=='authenticate')
        if take:selected.append((role,p))
    if len(selected)!=8:raise ValueError('Exact reused source subset drift')
    for role,p in selected:
        source=next(s for s in inv['sources'] if s['raw']==p['raw'] and s['archiveSha256']==p['archiveSha256'])
        if digest(ROOT/source['raw'])!=source['rawSha256'] or digest(ROOT/source['receipt'])!=source['receiptSha256']:raise ValueError('Reused raw/receipt changed')
        rows=[json.loads(line) for line in (ROOT/source['raw']).read_text().splitlines()]
        row=next(r for r in rows if r['record']=='method' and r['body']['owner']==p['owner'] and r['body']['signature']==p['signature'])
        if row['normalizedBodySha256']!=p['bodySha256']:raise ValueError('Reused selected body drift')
        key=role+':'+p['owner']+'->'+p['signature'];bodies[key]=row['body']
        proofs.append({'key':key,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'normalizedBodySha256':row['normalizedBodySha256'],'raw':source['raw'],'rawSha256':source['rawSha256'],'receipt':source['receipt'],'receiptSha256':source['receiptSha256'],'reusedFrom':PROMPT_INVENTORY})
    return bodies,proofs


def saved():
    ledger=json.loads(LEDGER.read_text());bodies,proofs=reused()
    expected={(r,o,tuple(n)) for r,o,n in QUERIES}
    actual={(p['key']['role'],p['key']['owner'],tuple(p['key']['names'])) for p in ledger}
    if len(ledger)!=len(expected) or actual!=expected:raise ValueError('Bounded query set changed')
    for p in ledger:
        if digest(ROOT/p['raw'])!=p['rawSha256'] or p['archiveSha256']!=INPUTS[p['key']['role']][1] or p['readerExitCode']!=0:raise ValueError('Saved source proof drift')
        for line in (ROOT/p['raw']).read_text().splitlines():
            row=json.loads(line)
            if row['record']!='method':continue
            b=row['body'];key=p['key']['role']+':'+b['owner']+'->'+b['signature']
            if key in bodies:raise ValueError('Duplicate selected method')
            bodies[key]=b
            proofs.append({'key':key,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'normalizedBodySha256':row['normalizedBodySha256'],'raw':p['raw'],'rawSha256':p['rawSha256'],'receipt':p['receipt']})
    return ledger,bodies,proofs


def assertions(bodies):
    rows=[]
    def check(label,selector,pc,opcode,reference=None,**fields):
        matches=[(k,v) for k,v in bodies.items() if selector in k]
        if len(matches)!=1:raise ValueError('Ambiguous selected method '+label)
        key,b=matches[0];ins=next((i for i in b['instructions'] if i['pc']==pc),None)
        if ins is None or ins['opcode']!=opcode or (reference is not None and reference not in ins.get('reference','')) or any(ins.get(k)!=v for k,v in fields.items()):raise ValueError('Source edge drift '+label)
        rows.append({'id':label,'method':key,'pc':pc,'instruction':ins})
    guest='guest:Landroid/hardware/biometrics/BiometricPrompt;->'
    internal=guest+'authenticateInternal(J'
    ctor=guest+'<init>(Landroid/content/Context;Landroid/hardware/biometrics/PromptInfo;Landroid/hardware/biometrics/BiometricPrompt$ButtonInfo;Landroid/hardware/biometrics/BiometricPrompt$ButtonInfo;[Landroid/hardware/biometrics/BiometricPrompt$ButtonInfo;Landroid/hardware/biometrics/IAuthService;)V'
    check('builder-retains-real-context','guest:Landroid/hardware/biometrics/BiometricPrompt$Builder;-><init>',18,'IPUT_OBJECT','->mContext:')
    check('builder-context-display','guest:Landroid/hardware/biometrics/BiometricPrompt$Builder;-><init>',24,'INVOKE_VIRTUAL','Context;->getDisplayId()I')
    check('builder-global-auth-lookup','guest:Landroid/hardware/biometrics/BiometricPrompt$Builder;->build(',33,'CONST_STRING','string=auth')
    check('builder-passes-context-to-prompt','guest:Landroid/hardware/biometrics/BiometricPrompt$Builder;->build(',50,'IGET_OBJECT','->mContext:')
    check('prompt-original-token',ctor,8,'IPUT_OBJECT','->mToken:')
    check('prompt-original-receiver',ctor,15,'IPUT_OBJECT','->mBiometricServiceReceiver:')
    check('prompt-real-context-no-substitution',ctor,17,'IPUT_OBJECT','->mContext:',registers=[2,1])
    check('prompt-service-owner',ctor,27,'IPUT_OBJECT','->mService:')
    crypto=guest+'authenticateInternal(Landroid/hardware/biometrics/BiometricPrompt$CryptoObject;'
    check('original-crypto-retained',crypto,0,'IPUT_OBJECT','->mCryptoObject:')
    check('original-native-operation',crypto,4,'INVOKE_VIRTUAL','CryptoObject;->getOpId()J')
    check('original-native-operation-delegated',crypto,17,'INVOKE_DIRECT_RANGE','->authenticateInternal(J')
    check('operation-id-comparison',internal,16,'CMP_LONG',registers=[0,4,17])
    check('cancellation-checked-before-auth',internal,30,'INVOKE_VIRTUAL_RANGE','CancellationSignal;->isCanceled()Z')
    check('effective-prompt-original-clone',internal,93,'INVOKE_DIRECT','PromptInfo;-><init>(Landroid/os/Parcel;)V')
    check('original-crypto-default-normalization',internal,104,'INVOKE_VIRTUAL','PromptInfo;->setAuthenticators(I)V')
    check('actual-context-at-client-call',internal,119,'IGET_OBJECT','->mContext:',registers=[0,1])
    check('actual-package-at-client-call',internal,121,'INVOKE_VIRTUAL','Context;->getPackageName()')
    check('actual-direct-iauth-call',internal,129,'INVOKE_INTERFACE_RANGE','IAuthService;->authenticate(',registerStart=8,registerCount=8)
    check('actual-request-id-to-listener',internal,135,'INVOKE_DIRECT','OnAuthenticationCancelListener;-><init>(',registers=[0,1,7,8])
    check('postreply-listener-install',internal,140,'INVOKE_VIRTUAL','CancellationSignal;->setOnCancelListener(')
    check('postinstall-showing-state',internal,144,'IPUT_BOOLEAN','->mIsPromptShowing:Z')
    listener='guest:Landroid/hardware/biometrics/BiometricPrompt$OnAuthenticationCancelListener;->'
    check('listener-stores-real-request',listener+'<init>',5,'IPUT_WIDE','->mAuthRequestId:J',registers=[2,0])
    check('listener-reads-showing-state',listener+'onCancel(',2,'INVOKE_STATIC','->-$$Nest$fgetmIsPromptShowing(')
    check('listener-skips-unshown-request',listener+'onCancel(',8,'IF_NEZ',targetPc=16)
    check('listener-real-request-cancel',listener+'onCancel(',44,'INVOKE_STATIC','->-$$Nest$mcancelAuthentication(')
    check('client-original-cancel-call',guest+'cancelAuthentication(',14,'INVOKE_INTERFACE','IAuthService;->cancelAuthentication(')
    check('cancellation-sets-canceled','guest:Landroid/os/CancellationSignal;->cancel(',8,'IPUT_BOOLEAN','->mIsCanceled:Z')
    check('late-listener-checks-canceled','guest:Landroid/os/CancellationSignal;->setOnCancelListener(',14,'IF_EQZ',targetPc=24)
    check('late-listener-synchronous-callback','guest:Landroid/os/CancellationSignal;->setOnCancelListener(',20,'INVOKE_INTERFACE','OnCancelListener;->onCancel()V')
    extra='samsung:Landroid/hardware/biometrics/BiometricPrompt;->semSetExtraInfo('
    check('source-display-producer',extra,6,'INVOKE_VIRTUAL','Context;->getDisplayId()I')
    check('source-display-exception-fallback',extra,31,'CONST_4',literal=0)
    check('source-display-set',extra,32,'INVOKE_VIRTUAL','->semSetDisplayId(I)V')
    check('source-task-only-actual-activity',extra,37,'INSTANCE_OF','Landroid/app/Activity;')
    check('source-nonactivity-no-task-write',extra,39,'IF_EQZ',targetPc=71)
    check('source-task-producer',extra,43,'INVOKE_VIRTUAL','Activity;->getTaskId()I')
    check('source-task-set',extra,47,'INVOKE_VIRTUAL','->semSetTaskId(I)V')
    auth='samsung-services:Lcom/android/server/biometrics/AuthService$AuthServiceImpl;->authenticate('
    for label,pc,ref in [('source-native-calling-user',62,'UserHandle;->getCallingUserId()I'),('source-native-calling-uid',66,'Binder;->getCallingUid()I'),('source-native-calling-pid',70,'Binder;->getCallingPid()I')]:check(label,auth,pc,'INVOKE_STATIC',ref)
    check('source-appops',auth,113,'INVOKE_VIRTUAL_RANGE','AppOpsManager;->noteOp(')
    check('source-foreground-policy',auth,135,'INVOKE_VIRTUAL','->isForeground(II)Z')
    check('source-sem-privilege-input',auth,209,'INVOKE_VIRTUAL_RANGE','->semGetPrivilegedFlag()I')
    check('source-sem-type-input',auth,215,'INVOKE_VIRTUAL_RANGE','->semGetBiometricType()I')
    check('source-sem-privilege-enforcement',auth,233,'INVOKE_VIRTUAL','->enforceCallingOrSelfPermission(')
    check('source-only-clear-after-admission',auth,236,'INVOKE_STATIC','Binder;->clearCallingIdentity()J')
    check('source-real-biometric-service',auth,259,'INVOKE_INTERFACE_RANGE','IBiometricService;->authenticate(')
    cancel='samsung-services:Lcom/android/server/biometrics/AuthService$AuthServiceImpl;->cancelAuthentication('
    check('source-cancel-original-permission',cancel,37,'INVOKE_STATIC','->-$$Nest$mcheckPermission(')
    check('source-cancel-original-clear',cancel,45,'INVOKE_STATIC','Binder;->clearCallingIdentity()J')
    check('source-cancel-original-backend',cancel,53,'INVOKE_INTERFACE','IBiometricService;->cancelAuthentication(')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.collect:collect()
    for path,pin in INPUTS.values():
        if digest(PARENT/path)!=pin:raise ValueError('Original archive identity changed')
    ledger,bodies,proofs=saved()
    checks=assertions(bodies)
    report={'schema':'biometric-client-metadata-methods/v1','scope':'Source/API proposal only, no helper/adapter/runtime acceptance','inputs':INPUTS,'proofs':proofs,'sourceAssertions':checks,'toolSha256':digest(__file__),'oemExecuted':False,'androidExecuted':False,'phoneActions':False}
    (OUT/'method-proofs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'newQueries':len(ledger),'selectedMethods':len(bodies),'reusedMethods':8,'sourceAssertions':len(checks),'report':'out/biometric-client-metadata/method-proofs.json'}))


if __name__=='__main__':main()
