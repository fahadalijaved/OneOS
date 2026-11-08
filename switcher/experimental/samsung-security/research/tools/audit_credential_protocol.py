"""Bounded, offline credential transport construction audit; never executes OEM code.

Default reuses pinned ignored receipts. --collect regenerates this stream's fixed
queries with the shared DEX041 reader. Inputs/receipts are validated before report.
"""
import argparse,gzip,hashlib,json,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent
PARENT=ROOT.parent
WORK=ROOT/'out/construction-protocol'
ILS='Lcom/android/internal/widget/ILockSettings;'
LPU='Lcom/android/internal/widget/LockPatternUtils;'
LSS='Lcom/android/server/locksettings/LockSettingsService;'
PROXY=ILS[:-1]+'$Stub$Proxy;'
CORE=set('getBoolean setBoolean getLong setLong getString setString getCredentialType hasSecureLockScreen getPinLength refreshStoredPinLength prepareToVerifyCredential checkCredential verifyCredential verifyTiedProfileChallenge verifyGatekeeperPasswordHandle removeGatekeeperPasswordHandle setLockCredential getLockoutEndTime getStrongAuthForUser registerStrongAuthTracker unregisterStrongAuthTracker requireStrongAuth userPresent reportSuccessfulBiometricUnlock scheduleNonStrongBiometricIdleTimeout setSeparateProfileChallengeEnabled isUseOneLockSettingEnabled removeCachedUnifiedChallenge tryUnlockWithCachedUnifiedChallenge getHashFactor hasPendingEscrowToken unlockUserKeyIfUnsecured resetKeyStore'.split())
ARCHIVES={
 'coloros-framework':('firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
 'samsung-framework':('firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
 'coloros-services':('firmware/donor/extracted/system/framework/services.jar','66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
 'samsung-services':('firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
 'coloros-settings':('firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk','33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'),
 'coloros-systemui':('firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk','0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'),
 'coloros-oplusservices':('firmware/donor/extracted/system/framework/oplus-services.jar','cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39')}
SEMANTICS={
 'getCredentialType':'Return real selected-user credential type; NONE(-1) is a real state, never unavailable. Guest type cache and multi-app remapping require readiness control.',
 'hasSecureLockScreen':'Service secure-lockscreen capability, not user credential presence or backend readiness.',
 'getPinLength':'Actual PasswordMetrics/PIN metadata; unknown(-1) remains unknown, never guessed four/six digits.',
 'refreshStoredPinLength':'Refresh/sync actual protector PIN metadata under original auto-confirm policy; this is a write-capable operation.',
 'prepareToVerifyCredential':'Original preparation hook, not successful verification or readiness acknowledgment.',
 'checkCredential':'Credential,user,progress callback -> full VerifyCredentialResponse; authenticated progress precedes final reply and must retain operation/user/generation ownership.',
 'verifyCredential':'Credential,user,flags -> full response; flags1 obtains a real temporary GK-password handle; no fabricated flag/result or general repair-mode admission.',
 'verifyTiedProfileChallenge':'Original parent/profile credential verification; require real tied-profile relationship and original user semantics.',
 'verifyGatekeeperPasswordHandle':'Handle,actual consuming challenge,user -> genuine challenge-bound HAT; handle belongs to same live Samsung authority and operation.',
 'removeGatekeeperPasswordHandle':'Release only an owned temporary handle, without affecting another generation.',
 'setLockCredential':'New credential,previous credential,user -> actual commit Boolean; NONE new/old governs removal/creation with genuine policy. Lost/postcommit failures require readback/reconciliation before retry.',
 'getLockoutEndTime':'ParcelDuration representing actual elapsed-realtime deadline, not remaining timeout. Query may perform original Samsung DB deadline reconciliation.',
 'getStrongAuthForUser':'Return actual flags; preserve first-unlock,lockout,lockdown,enterprise and extra-factor state.',
 'registerStrongAuthTracker':'Register exact live Binder tracker with owned callbacks; no optimistic default before original initial state is applied.',
 'unregisterStrongAuthTracker':'Unregister same Binder owner; drain queued callbacks/generation before releasing consumer.',
 'requireStrongAuth':'Original privileged flag/user policy mutation; not frontend authority to clear requirements.',
 'userPresent':'Privileged Samsung user-present policy effects; call only after real final unlock policy, not cosmetic dismissal.',
 'reportSuccessfulBiometricUnlock':'Real strong/non-strong result and user to original StrongAuth policy; never caller-invented success.',
 'scheduleNonStrongBiometricIdleTimeout':'Original MANAGE_BIOMETRIC operation; owned policy session only.',
 'setSeparateProfileChallengeEnabled':'Original enabled flag,profile,old credential; preserve tied-profile credential/storage/key mutation semantics.',
 'isUseOneLockSettingEnabled':'Authoritative profilechallenge setting/read policy, not guessed numeric-user equivalence.',
 'removeCachedUnifiedChallenge':'Privileged actual cache mutation; require owned profile/context.',
 'tryUnlockWithCachedUnifiedChallenge':'Real authorized profile cached credential path; never accept guest unlocked cache as proof.',
 'getHashFactor':'Credential/user -> original secret history factor consumed only on device by policy; never diagnostics/export or credential replication.',
 'hasPendingEscrowToken':'Original owned-user escrow state; preserve lifecycle policy, not an activation grant.',
 'unlockUserKeyIfUnsecured':'Actual unsecured-user storage unlock with original secure-state and lifecycle checks; no bypass for secure users.',
 'resetKeyStore':'Destructive original key-reset operation, separately admitted only for a genuine required workflow; never generic maintenance.',
 'getBoolean':'Key,default,user -> real value; restrict reached key/purpose,never substitute default for unavailable authority.',
 'getLong':'Key,default,user -> real value; distinguish policy,lockout and optional OEM metadata keys.',
 'getString':'Key,default,user -> actual value; protected values remain on device and out of diagnostics.',
 'setBoolean':'Key,value,user -> original permission-checked write; restrict reached key and preserve source-specific effects.',
 'setLong':'Key,value,user -> actual original write; OEM hooks differ, so matching wire shape does not establish all per-key semantic parity.',
 'setString':'Key,value,user -> actual original write; no broad guest access to Samsung database or secret keys.'}

def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def declarations(variant,owner):
 h=ARCHIVES[variant][1];p=PARENT/'out/os-comparison-resumed/archive-index/indexes'/h/'declarations.jsonl.gz'
 for line in gzip.open(p,'rt',encoding='utf8'):
  d=json.loads(line)
  if d.get('descriptor')==owner:return d
 raise ValueError('Missing exact declared class '+owner)
def rows(receipt):
 raw=ROOT/receipt['raw']
 if digest(raw)!=receipt['rawSha256']:raise ValueError('Raw proof changed '+str(raw))
 return [json.loads(l) for l in raw.read_text(encoding='utf8').splitlines()]
def compact_receipt(r):
 return {k:r[k] for k in ['archiveSha256','query','raw','rawSha256','selectedMethodProofs','tools','physicalLogicalDex','readerExitCode','archiveAndToolPinsVerifiedBeforeAndAfter']}
def parameters(sig):
 s=sig.split('(',1)[1].split(')',1)[0];out=[];i=0
 while i<len(s):
  a=i
  while s[i]=='[':i+=1
  if s[i]=='L':i=s.index(';',i)+1
  else:i+=1
  out.append(s[a:i])
 return out

def symbolic_proxy(body):
 """Trace incoming argument provenance through straight-line generated Proxy IO.

Only symbolic labels enter metadata; no input values exist or OEM code executes.
Unsupported writes fail instead of silently treating arguments as equivalent.
"""
 ps=parameters(body['signature']);width=sum(2 if p in ['J','D'] else 1 for p in ps)
 reg={body['registerCount']-width-1:'this'};n=body['registerCount']-width
 for ix,p in enumerate(ps):
  reg[n]='argument:'+str(ix)
  if p in ['J','D']:reg[n+1]='argument:'+str(ix)+':wideHi';n+=1
  n+=1
 pending=None;io=[];transacts=[];parcels=0
 for ins in body['instructions']:
  op=ins['opcode'];rs=ins.get('registers',list(range(ins.get('registerStart',0),ins.get('registerStart',0)+ins.get('registerCount',0))))
  if op.startswith('CONST_STRING'):reg[rs[0]]=ins['reference']
  elif op.startswith('CONST') and 'literal'in ins:reg[rs[0]]='literal:'+str(ins['literal'])
  elif op.startswith('MOVE_RESULT'):
   reg[rs[0]]=pending
   if 'WIDE'in op:reg[rs[0]+1]=str(pending)+':wideHi'
  elif op.startswith('MOVE') and op!='MOVE_EXCEPTION':
   reg[rs[0]]=reg.get(rs[1],'unproved')
   if 'WIDE'in op:reg[rs[0]+1]=reg.get(rs[1]+1,'unproved')
  elif op.startswith(('IGET','SGET')):reg[rs[0]]='field:'+ins['reference']
  elif op.startswith('INVOKE'):
   ref=ins['reference'];args=[reg.get(r,'unproved') for r in rs]
   if ref.startswith('Landroid/os/Parcel;->obtain('):pending='parcel:'+str(parcels);parcels+=1
   elif ref.startswith('Landroid/os/Parcel;->') and not any(x in ref for x in ['recycle(','obtain(']):
    if any(v is None or v=='unproved' for v in args):raise ValueError('Unproved Proxy argument '+body['signature'])
    io.append({'method':ref.split('->',1)[1],'arguments':args[1:]});pending='result:'+ref
   elif ref=='Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z':transacts.append({'pc':ins['pc'],'arguments':args[1:]});pending='transactResult'
   else:pending='result:'+ref
  elif op=='CHECK_CAST':pass
 if len(transacts)!=1:raise ValueError('Expected one exact transaction')
 return {'parcelIO':io,'transact':transacts[0]}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--collect',action='store_true');args=ap.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 trust=load(ROOT/'inventory/trust-policy.json');creds=load(ROOT/'inventory/credentials.json');frontend=load(ROOT/'inventory/coloros-frontend.json')
 for variant,(p,h) in ARCHIVES.items():
  if digest(PARENT/p)!=h:raise ValueError('Archive identity drift '+variant)
 old_receipts={q['receipt'] for q in trust['methodQueries']}|{p['receipt'] for p in creds['methodProofs'].values()}
 refs=[('framework-locksettings-refs','coloros-framework',ILS),('settings-lockpattern-refs','coloros-settings',LPU),('settings-locksettings-refs','coloros-settings',ILS),('systemui-lockpattern-refs','coloros-systemui',LPU),('systemui-locksettings-refs','coloros-systemui',ILS),('framework-passwordtype-refs','coloros-framework','string=lockscreen.password.type'),('oplusservices-passwordtype-refs','coloros-oplusservices','string=lockscreen.password.type')]
 if args.collect:
  from static_security_reader import read_archive
  for name,variant,reference in refs:
   p,h=ARCHIVES[variant];r=read_archive(PARENT/p,h,reference=reference,stream='construction-protocol');(WORK/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
  # Existing fixed body query receipts are part of this reproducible selection.
  # Re-run their exact selectors rather than infer a constructor or add classes.
  for cache in sorted(WORK.glob('*.json')):
   if cache.stem in {n for n,_,_ in refs}:continue
   r=load(cache)
   if r.get('schema')!='static-security-reader/v1' or r['query']['reference'] or r['query']['listClasses']:continue
   variant=next((v for v,x in ARCHIVES.items() if x[1]==r['archiveSha256']),None)
   if variant is None:raise ValueError('Unknown receipt archive')
   p,h=ARCHIVES[variant];q=r['query'];new=read_archive(PARENT/p,h,q['class'],q['exactMethods'],stream='construction-protocol',all_methods=q['allMethods']);cache.write_text(json.dumps(new,indent=2)+'\n')
 receipts={p:load(ROOT/p) for p in sorted(old_receipts)}
 for p in WORK.glob('*.json'):
  r=load(p)
  if r.get('schema')=='static-security-reader/v1':receipts[p.relative_to(ROOT).as_posix()]=r
 pool={};proofs={};reference_rows={};receipt_metadata=[]
 for path,r in receipts.items():
  if not r['archiveAndToolPinsVerifiedBeforeAndAfter'] or r['readerExitCode']!=0:raise ValueError('Unaccepted static receipt')
  if r['archiveSha256'] not in {a[1] for a in ARCHIVES.values()}:continue
  allrows=rows(r);receipt_metadata.append({'receipt':path,**compact_receipt(r)})
  if path.startswith('out/construction-protocol/') and r['query']['reference']:
   reference_rows[Path(path).stem]=[x for x in allrows if x['record']=='reference']
  for row in allrows:
   if row['record']!='method':continue
   b=row['body'];key=(r['archiveSha256'],b['owner'],b['signature'])
   if key in pool and pool[key]['normalizedBodySha256']!=row['normalizedBodySha256']:raise ValueError('Conflicting pinned body')
   pool[key]=row;proofs[key]={'archiveSha256':r['archiveSha256'],'owner':b['owner'],'signature':b['signature'],'bodySha256':row['normalizedBodySha256'],'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':path,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset']}
 def body(variant,owner,sig):return pool[(ARCHIVES[variant][1],owner,sig)]['body']
 def proof(variant,owner,sig):return proofs[(ARCHIVES[variant][1],owner,sig)]
 names=trust['binderContracts'][ILS];guest={m['name']:m['name']+m['descriptor'] for m in declarations('coloros-framework',ILS)['methods']};host={m['name']:m['name']+m['descriptor'] for m in declarations('samsung-framework',ILS)['methods']}
 protocols=[];wire_checks=0
 for name in sorted(CORE):
  if guest[name]!=host[name]:raise ValueError('Core signature mismatch '+name)
  sig=guest[name];a=symbolic_proxy(body('coloros-framework',PROXY,sig));b=symbolic_proxy(body('samsung-framework',PROXY,sig))
  if a['parcelIO']!=b['parcelIO']:raise ValueError('Proxy payload provenance differs '+sig)
  tx={s:int(next(k for k,v in names[s+'Transactions'].items() if v==name)) for s in ['coloros','samsung']}
  for side,view in [('coloros',a),('samsung',b)]:
   if view['transact']['arguments'][0]!='literal:'+str(tx[side]):raise ValueError('Transaction literal mismatch')
  if a['transact']['arguments'][1:]!=b['transact']['arguments'][1:]:raise ValueError('Transact owner/flags differ')
  wire_checks+=1;entries={}
  for side in ['coloros','samsung']:
   variant=side+'-services';sbody=body(variant,LSS,sig);edges=[{'pc':i['pc'],'target':i['reference']} for i in sbody['instructions'] if i.get('referenceKind')=='method' and any(x in i['reference'] for x in ['Permission','hasPermission','clearCallingIdentity','restoreCallingIdentity','getCallingUid','getCallingPid','getCallingUserId','StrongAuth','setLockCredential'])]
   entries[side]={'transaction':tx[side],'proxy':proof(side+'-framework',PROXY,sig),'service':proof(variant,LSS,sig),'callerPolicyAndIdentityEdges':edges,'originalGate':('MANAGE_BIOMETRIC' if name in ['reportSuccessfulBiometricUnlock','scheduleNonStrongBiometricIdleTimeout'] else 'None in original capability getter' if name=='hasSecureLockScreen' else 'ACCESS_KEYGUARD_SECURE_STORAGE or SET_AND_VERIFY_LOCKSCREEN_CREDENTIALS or SET_INITIAL_LOCK with oldNONE' if name=='setLockCredential' else 'ACCESS_KEYGUARD_SECURE_STORAGE or SET_AND_VERIFY_LOCKSCREEN_CREDENTIALS' if name=='verifyCredential' else 'ACCESS_KEYGUARD_SECURE_STORAGE')}
  protocols.append({'name':name,'exactSignature':sig,'parameterTypes':parameters(sig),'resultType':sig.split(')',1)[1],'semantics':SEMANTICS[name],'wirePayloadArgumentProvenanceEqual':True,'wire':a['parcelIO'],'transactFlagsSymbol':a['transact']['arguments'][-1],**entries})
 # A selected real mutation of argument provenance must discriminate this check.
 setter=next(p for p in protocols if p['name']=='setLockCredential');negative=json.loads(json.dumps(setter['wire']));writes=[x for x in negative if x['method'].startswith('writeTypedObject')]
 if len(writes)!=2:raise ValueError('Expected two real credential arguments')
 writes[0]['arguments'][0],writes[1]['arguments'][0]=writes[1]['arguments'][0],writes[0]['arguments'][0]
 if negative==setter['wire']:raise ValueError('Swapped-old/new credential negative did not discriminate')
 actual_edges=[]
 for source,_,_ in refs:
  for r in reference_rows.get(source,[]):
   if r['instruction'].get('referenceKind')=='method':actual_edges.append({'source':source,'caller':r['caller'],'pc':r['instruction']['pc'],'callee':r['instruction']['reference']})
 lpu=body('coloros-framework',LPU,'setLockCredential(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;I)Z');calls=[i for i in lpu['instructions'] if i.get('referenceKind')=='method'];commit=next(i['pc'] for i in calls if 'ILockSettings;->setLockCredential('in i['reference']);optional=next(i['pc'] for i in calls if 'setLockscreenPasswordType('in i['reference'])
 if not commit<optional:raise ValueError('Postcommit order changed')
 typecache=body('coloros-framework','Lcom/android/internal/widget/LockPatternUtils$1;','apply(Ljava/lang/Integer;)Ljava/lang/Integer;');lockcache=body('coloros-framework','Lcom/android/internal/widget/LockPatternUtils$2;','apply(Ljava/lang/Integer;)Ljava/time/Duration;')
 if not any(c['exceptionType']=='Landroid/os/RemoteException;' for c in typecache['catches']) or not any(c['exceptionType']=='Landroid/os/RemoteException;' for c in lockcache['catches']):raise ValueError('Expected actual RemoteException handlers')
 if not any(i.get('literal')==-1 and i['pc']==27 for i in typecache['instructions']):raise ValueError('Type fallback source changed')
 if not any(i.get('reference')=='Ljava/time/Duration;->ZERO:Ljava/time/Duration;' and i['pc']==27 for i in lockcache['instructions']):raise ValueError('Lockout fallback source changed')
 selected=sorted({(ARCHIVES[s+'-services'][1],LSS,p['exactSignature']) for p in protocols for s in ['coloros','samsung']}|{(ARCHIVES['coloros-framework'][1],LPU,lpu['signature']),(ARCHIVES['coloros-framework'][1],'Lcom/android/internal/widget/LockPatternUtils$1;',typecache['signature']),(ARCHIVES['coloros-framework'][1],'Lcom/android/internal/widget/LockPatternUtils$2;',lockcache['signature'])})
 out={'schema':'credential-construction-protocol/v1','scope':'Pinned bounded PIN/readiness/policy protocol; static evidence and patch requirements, not an implemented adapter','goalSha256':digest(ROOT/'GOAL.md'),'inputs':{v:{'path':p,'sha256':h} for v,(p,h)in ARCHIVES.items()},'inheritedInventories':{p:digest(ROOT/p) for p in ['inventory/trust-policy.json','inventory/credentials.json','inventory/coloros-frontend.json']},'operations':protocols,'operationCount':len(protocols),'selectedMethodProofs':[proofs[k] for k in selected],'receiptMetadata':receipt_metadata,'actualReachedEdges':actual_edges,'referenceScanCounts':{n:len(reference_rows.get(n,[])) for n,_,_ in refs},'guestOnlyMethods':names['colorosOnly'],'patchRequirements':{'postcommitOptionalMetadata':{'commonSetterPc':commit,'optionalHelperPc':optional,'requiredChange':'Remove exact optional postcommit OEM producer and its bounded metadata logging consumer for selected profile; preserve actual Samsung commit/result and required policy/quality/metadata. Do not import OPPO service solely for this helper or acknowledge an unperformed auth operation.'},'typeCacheUnavailable':{'fallbackPc':27,'fallbackValue':-1,'requiredChange':'Authority validity/generation/user admission before any cached type or mode projection; never translate unavailable/RemoteException to NONE/swipe. Invalidate caches on authority/user changes and close ingress until fresh authoritative state is applied.'},'lockoutCacheUnavailable':{'fallbackPc':27,'fallbackValue':'Duration.ZERO','requiredChange':'Missing lockout authority is unknown/locked, not no lockout. Preserve actual elapsed-time deadline, source-specific original policy and freshness.'}},'checks':{'equalSymbolicProxyPayloads':wire_checks,'swappedNewOldCredentialNegativeRejected':True,'transactionLiteralsPinned':2*wire_checks,'reusedActualStubDispatchProofs':trust['dispatchCrosschecks'],'postcommitOrderingPinned':True,'noneAndZeroErrorFallbacksPinned':True},'limitations':['Direct invocation evidence is a statically reached lower bound, not runtime path coverage or reflection/JNI closure','Core profile/tied/escrow/key-reset rows are explicit conditional ownership obligations, not generic frontend capabilities','No Android/service/native/cryptographic acceptance or installed OneOS patch identity','Platform SELinuxPermissive/relaxedprivapp limitations are disclosed as accepted GOAL scope; no new global Enforcing prerequisite','No credential/token/enrollment values exist in this audit; raw OEM instructions remain ignored firmware'],'oemCodeExecuted':False,'phoneActions':False,'toolSha256':digest(Path(__file__))}
 (ROOT/'inventory/construction-protocol.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf8');print('PASS',len(protocols),'typed operations;',wire_checks,'payload provenance comparisons; negative swap rejected')
if __name__=='__main__':main()
