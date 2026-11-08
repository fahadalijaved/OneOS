"""Reproduce bounded trust-policy metadata from exact supplied offline inputs.

No OEM code executes. Raw selected DEX methods stay in ignored firmware/trust-policy.
"""
import gzip, hashlib, json, sys
sys.dont_write_bytecode=True
from pathlib import Path
from static_security_reader import read_archive

ROOT=Path(__file__).resolve().parent.parent
PARENT=ROOT.parent
SAMSUNG_SERVICES='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
SAMSUNG_FRAMEWORK='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
COLOROS_SERVICES='66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
COLOROS_FRAMEWORK='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
ARCHIVES={
 'samsung-services':('firmware/samsung/runtime-20261104/services.jar',SAMSUNG_SERVICES),
 'samsung-framework':('firmware/samsung/framework.jar',SAMSUNG_FRAMEWORK),
 'coloros-services':('firmware/donor/extracted/system/framework/services.jar',COLOROS_SERVICES),
 'coloros-framework':('firmware/donor/extracted/system/framework/framework.jar',COLOROS_FRAMEWORK)}
LOCK='Lcom/android/server/locksettings/LockSettingsService;'
AUTH='Lcom/android/server/biometrics/AuthService;'
FP='Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;'
CREDENTIAL='Lcom/android/internal/widget/LockscreenCredential;'
RESPONSE='Lcom/android/internal/widget/VerifyCredentialResponse;'
AUTHENTICATE='authenticate(Landroid/os/IBinder;JILandroid/hardware/biometrics/IBiometricServiceReceiver;Ljava/lang/String;Landroid/hardware/biometrics/PromptInfo;)J'
QUERIES=[
 ('samsung-services',LOCK,[f'checkCredential({CREDENTIAL}ILcom/android/internal/widget/ICheckCredentialProgressCallback;){RESPONSE}',f'verifyCredential({CREDENTIAL}II){RESPONSE}',f'verifyGatekeeperPasswordHandle(JJI){RESPONSE}','checkReadPermission()V','checkWritePermission()V',f'doVerifyCredential({CREDENTIAL}ILcom/android/internal/widget/ICheckCredentialProgressCallback;I){RESPONSE}','onCredentialVerified(Lcom/android/server/locksettings/SyntheticPasswordManager$SyntheticPassword;Landroid/app/admin/PasswordMetrics;I)V',f'setLockCredentialWithIgnoreNotifyIfNeeded({CREDENTIAL}{CREDENTIAL}IZ)Z']),
 ('coloros-services',LOCK,['checkReadPermission()V','checkWritePermission()V','checkAccessSecureStoragePermission(Ljava/lang/String;)V',f'verifyCredential({CREDENTIAL}II){RESPONSE}',f'verifyGatekeeperPasswordHandle(JJI){RESPONSE}',f'setLockCredential({CREDENTIAL}{CREDENTIAL}I)Z']),
 ('samsung-services',AUTH,['-$$Nest$mcheckInternalPermission(Lcom/android/server/biometrics/AuthService;)V','-$$Nest$mcheckPermission(Lcom/android/server/biometrics/AuthService;)V']),
 ('samsung-services','Lcom/android/server/biometrics/AuthService$AuthServiceImpl;',[AUTHENTICATE]),
 ('samsung-services','Lcom/android/server/biometrics/BiometricService$BiometricServiceWrapper;',[AUTHENTICATE]),
 ('samsung-services',FP,['-$$Nest$mcanUseFingerprint(Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;Ljava/lang/String;Ljava/lang/String;ZIII)Z']),
 ('samsung-services',FP[:-1]+'$1;',['authenticate(Landroid/os/IBinder;JLandroid/hardware/fingerprint/IFingerprintServiceReceiver;Landroid/hardware/fingerprint/FingerprintAuthenticateOptions;)J','semAuthenticate(Landroid/os/IBinder;JLandroid/hardware/fingerprint/IFingerprintServiceReceiver;Landroid/hardware/fingerprint/FingerprintAuthenticateOptions;Landroid/os/Bundle;)J']),
 ('samsung-services','Lcom/android/server/biometrics/SemUtils;',['isKeyguard(Landroid/content/Context;Ljava/lang/String;)Z','isCurrentUserOrProfile(Landroid/content/Context;I)Z','checkPermission(Landroid/content/Context;Ljava/lang/String;)V']),
]
BINDERS=['Lcom/android/internal/widget/ILockSettings;','Landroid/hardware/fingerprint/IFingerprintService;','Landroid/hardware/biometrics/IAuthService;','Landroid/hardware/biometrics/IBiometricService;']
for variant in ['samsung-framework','coloros-framework']:
 for binder in BINDERS: QUERIES.append((variant,binder[:-1]+'$Stub;',['getDefaultTransactionName(I)Ljava/lang/String;']))
QUERIES.append(('samsung-framework','Landroid/hardware/biometrics/IBiometricService$Stub;',['authenticate_enforcePermission()V']))
QUERIES.extend([
 ('samsung-services','Lcom/android/server/biometrics/BiometricService;',['handleAuthenticationSucceeded(JI[BLandroid/os/Bundle;)V','handleOnDismissed(I[BJ)V']),
 ('samsung-services','Lcom/android/server/locksettings/SyntheticPasswordManager;',[f'verifyChallengeInternal(IJLandroid/service/gatekeeper/IGateKeeperService;[B){RESPONSE}']),
 ('samsung-services','Lcom/android/server/wm/Task$$ExternalSyntheticBUOutline0;',['m(Ljava/lang/String;)V']),
])
for variant in ['samsung-framework','coloros-framework']:
 QUERIES.append((variant,'Lcom/android/internal/widget/ILockSettings$Stub;',['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']))
 QUERIES.append((variant,'Lcom/android/internal/widget/ILockSettings$Stub$Proxy;',[f'checkCredential({CREDENTIAL}ILcom/android/internal/widget/ICheckCredentialProgressCallback;){RESPONSE}',f'verifyCredential({CREDENTIAL}II){RESPONSE}',f'verifyGatekeeperPasswordHandle(JJI){RESPONSE}']))


def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def transaction_map(body):
 ins=body['instructions'];by_pc={i['pc']:i for i in ins}
 switches=[i for i in ins if i['opcode'] in ['PACKED_SWITCH','SPARSE_SWITCH']]
 if len(switches)!=1:raise ValueError('Expected one transaction-name switch')
 switch=switches[0];payload=by_pc[switch['targetPc']];result={}
 for edge in payload['switchElements']:
  pc=switch['pc']+edge['offsetFromReferringSwitchPc'];value=None;seen=set()
  for _ in range(12):
   if pc in seen:raise ValueError('Transaction-name branch cycle')
   seen.add(pc);i=by_pc[pc]
   if i['opcode'] in ['CONST_STRING','CONST_STRING_JUMBO']:
    if value is not None:raise ValueError('Ambiguous transaction name')
    value=i['reference'].removeprefix('string=')
   elif i['opcode']=='RETURN_OBJECT':break
   elif i['opcode'].startswith('GOTO'):
    pc=i['targetPc'];continue
   elif i['opcode'] not in ['NOP']:raise ValueError('Unexpected transaction-name opcode '+i['opcode'])
   pc+=i['codeUnits']
  else:raise ValueError('Transaction-name branch bound')
  if value is None:raise ValueError('Transaction name missing')
  result[str(edge['key'])]=value
 return result

def validate_dispatch(out):
 """Cross-check name tables against actual Stub dispatch and selected Proxy literals."""
 results=[]
 for q in out['methodQueries']:
  cls=q['class']
  if not cls.startswith('Lcom/android/internal/widget/ILockSettings$Stub'):continue
  names=out['binderContracts']['Lcom/android/internal/widget/ILockSettings;'][q['variant'].split('-')[0]+'Transactions']
  for line in (ROOT/q['raw']).read_text(encoding='utf8').splitlines():
   row=json.loads(line)
   if row['record']!='method':continue
   body=row['body'];ins=body['instructions'];by={i['pc']:i for i in ins}
   if body['signature'].startswith('onTransact('):
    switches=[i for i in ins if i['opcode'] in ['PACKED_SWITCH','SPARSE_SWITCH']]
    if len(switches)!=1:raise ValueError('Unexpected Stub switch count')
    switch=switches[0];elements=by[switch['targetPc']]['switchElements']
    targets={e['key']:switch['pc']+e['offsetFromReferringSwitchPc'] for e in elements}
    if set(map(str,targets))!=set(names):raise ValueError('Name/dispatch code set differs')
    for code,start in targets.items():
     end=min((v for v in targets.values() if v>start),default=max(by)+1)
     calls=[i for i in ins if start<=i['pc']<end and i.get('referenceKind')=='method' and i['reference'].startswith(cls+'->')]
     matching=[i for i in calls if i['reference'].split('->')[1].split('(')[0]==names[str(code)]]
     if len(matching)!=1:raise ValueError('Name/actual Stub target differs at '+str(code))
     results.append({'variant':q['variant'],'code':code,'name':names[str(code)],'dispatchPc':matching[0]['pc'],'bodySha256':row['normalizedBodySha256']})
   elif '$Proxy;' in cls:
    calls=[i for i in ins if i.get('reference')=='Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']
    if len(calls)!=1:raise ValueError('Expected one exact Proxy transaction')
    call=calls[0];reg=call['registers'][1]
    candidates=[i for i in ins if i['pc']<call['pc'] and (i.get('registers') or [None])[0]==reg and i['opcode'].startswith('CONST') and 'literal' in i]
    if not candidates:raise ValueError('Proxy transaction literal missing')
    literal=candidates[-1];between=[i for i in ins if literal['pc']<i['pc']<call['pc'] and (i.get('registers') or [None])[0]==reg and not i['opcode'].startswith(('INVOKE','IF_','RETURN','IPUT','SPUT'))]
    if between:raise ValueError('Proxy transaction register overwritten')
    code=literal['literal'];name=body['signature'].split('(')[0]
    if names.get(str(code))!=name:raise ValueError('Proxy/name map differs')
    results.append({'variant':q['variant'],'proxyMethod':name,'code':code,'transactPc':call['pc'],'bodySha256':row['normalizedBodySha256']})
 if len(results)!=172:raise ValueError('Expected104Samsung+62ColorOS dispatches and6Proxy proofs')
 return results

def declarations(sha):
 p=PARENT/'out/os-comparison-resumed/archive-index/indexes'/sha/'declarations.jsonl.gz'
 data={}
 for line in gzip.open(p,'rt',encoding='utf8'):
  row=json.loads(line)
  if row.get('descriptor') in BINDERS:data[row['descriptor']]=row
 if set(data)!=set(BINDERS):raise ValueError('Binder declaration missing')
 return data,{'path':p.relative_to(PARENT).as_posix(),'sha256':digest(p)}

def main():
 out={'schema':'oneos-trust-policy/v1','scope':'Offline source and exact DEX body evidence; no runtime/cryptographic acceptance','oneosBaseline':'2a5f41043b4a69399cae058bad213cdef7408e88','olderSourceOnly':'9a39df159b2086a46f4ec4a848c3cf9bb471369c','archives':{},'sourceEvidence':[],'methodQueries':[],'binderContracts':{},'oemCodeExecuted':False,'androidExecuted':False,'phoneAction':False}
 baseline=PARENT/'firmware/reference/OneOS'/out['oneosBaseline']
 source_files={
  'switcher/assets/oneos_switch.sh':[(614,624,'Global setenforce0'),(750,751,'Privapp allowlist log mode'),(987,1000,'Host system_server killed')],
  'switcher/assets/guest_prepare.sh':[(109,138,'appid15000 declaration/check conditional on GMS'),(301,312,'Shared dev/binderfs mounts'),(417,430,'IMS scoped shared-UID carveout')],
  'switcher/assets/guest_start.sh':[(647,655,'Shared servicemanager vold namespace')],
  'switcher/assets/return_to_oneui.sh':[(749,751,'Restore recorded SELinux state or failsafe')],
  'scripts/make-overlays.sh':[(205,224,'Storage and authentication preservation patch producer calls'),(239,244,'IMS signature carveout producer call'),(810,810,'Guard marker producer')],
  'switcher/patches/guest_no_gatekeeper.py':[(15,39,'Block guest credential mutation; leave verifyChallenge/read SID call sites')],
  'switcher/patches/guest_no_biometric_cleanup.py':[(14,17,'Prevent unknown-template removal')],
  'docs/samsung-ims-in-guest.md':[(74,87,'Documented scoped signature carveout intent')],
 }
 for rel,ranges in source_files.items():
  path=baseline/rel;lines=path.read_text(encoding='utf8').splitlines();out['sourceEvidence'].append({'path':path.relative_to(PARENT).as_posix(),'sha256':digest(path),'lineCount':len(lines),'ranges':[{'first':a,'last':b,'purpose':label} for a,b,label in ranges]})
 older=PARENT/'firmware/reference/OneOS'/out['olderSourceOnly']
 for rel in ['switcher/patches/guest_app_id_offset.py','switcher/patches/guest_sec_ims_signature.py']:
  path=older/rel;out['sourceEvidence'].append({'path':path.relative_to(PARENT).as_posix(),'sha256':digest(path),'status':'Older039 implementation; selected055 producer invokes named patch, current body not supplied'})
 transactions={};raw_bodies=[]
 for variant,cls,methods in QUERIES:
  rel,sha=ARCHIVES[variant];print(variant,cls,flush=True)
  out['archives'][variant]={'path':rel,'sha256':sha}
  receipt=read_archive(PARENT/rel,sha,cls,methods,stream='trust-policy')
  methods_raw=[json.loads(line) for line in (ROOT/receipt['raw']).read_text(encoding='utf8').splitlines() if json.loads(line)['record']=='method']
  record={'variant':variant,'class':cls,'receipt':receipt['receipt'],'raw':receipt['raw'],'rawSha256':receipt['rawSha256'],'proofs':receipt['selectedMethodProofs'],'pinsVerifiedBeforeAndAfter':receipt['archiveAndToolPinsVerifiedBeforeAndAfter'],'readerTools':receipt['tools'],'physicalLogicalDex':receipt['physicalLogicalDex'],'readerExitCode':receipt['readerExitCode']}
  out['methodQueries'].append(record)
  raw_bodies.extend({'variant':variant,**row} for row in methods_raw)
  for row in methods_raw:
   if row['body']['signature'].startswith('getDefaultTransactionName('):transactions[(variant,cls)]=transaction_map(row['body'])
 left,lproof=declarations(SAMSUNG_FRAMEWORK);right,rproof=declarations(COLOROS_FRAMEWORK)
 out['declarationIndexes']={'samsung':lproof,'coloros':rproof}
 for cls in BINDERS:
  a={m['name']+m['descriptor'] for m in left[cls]['methods']};b={m['name']+m['descriptor'] for m in right[cls]['methods']}
  ac=transactions['samsung-framework',cls[:-1]+'$Stub;'];bc=transactions['coloros-framework',cls[:-1]+'$Stub;']
  same=[{'code':int(k),'method':v} for k,v in ac.items() if bc.get(k)==v]
  drift=[{'code':int(k),'samsung':ac.get(k),'coloros':bc.get(k)} for k in sorted(ac.keys()|bc.keys(),key=int) if ac.get(k)!=bc.get(k)]
  out['binderContracts'][cls]={'samsungDeclaredMethods':len(a),'colorosDeclaredMethods':len(b),'commonExactDescriptors':len(a&b),'samsungOnly':sorted(a-b),'colorosOnly':sorted(b-a),'samsungTransactions':ac,'colorosTransactions':bc,'sameCodeAndNameCount':len(same),'differentCodeName':drift,'limit':'Matching transaction names do not prove same parcel layout, permission/semantic policy, runtime reachability or key authorization'}
 out['dispatchCrosschecks']=validate_dispatch(out)
 out['selectedBodyEvidence']=[{'variant':r['variant'],'owner':r['body']['owner'],'method':r['body']['signature'],'normalizedBodySha256':r['normalizedBodySha256'],'edges':[{'pc':i['pc'],'target':i['reference']} for i in r['body']['instructions'] if i.get('referenceKind')=='method' and any(x in i['reference'] for x in ['enforceCalling','clearCallingIdentity','restoreCallingIdentity','verifyChallenge','checkReadPermission','checkWritePermission','hasPermission','addAuthToken','onCredentialVerified','requireStrongAuth','getCallingUid','getCallingPid','getCallingUserId','noteOp','isForeground','isKeyguard','getStrongAuth','unlockKeystore','unlockCeStorage'])]} for r in raw_bodies if not r['body']['signature'].startswith(('getDefaultTransactionName','onTransact'))]
 out['limits']=['Parent mounted Samsung capture is not certified stock partition image','Selected055 baseline is20-file subset; older039 patch bodies cannot certify current producer output or installed files','Raw DEX bodies are exact selected source evidence; no startup/native/Android/hardware acceptance','Guest Context/UID1000, resource IDs, permission manager, user manager, local service graph and data owners require independent attestation','No signature bypass, fake HAT, UI dismissal or altered security policy is proposed as success']
 out['auditToolSha256']=digest(Path(__file__))
 (ROOT/'inventory/trust-policy.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
 print('wrote inventory/trust-policy.json',flush=True)
if __name__=='__main__':main()
