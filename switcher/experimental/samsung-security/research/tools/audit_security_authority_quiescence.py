"""Bounded old-Samsung-authority quiescence evidence; static source/API only.

Reads pinned existing receipts. Optional fixed missing-body reads use the same
static reader, never loading or executing an OEM class or contacting a phone.
"""
import argparse,hashlib,json,runpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'out/security-authority-quiescence'
LSS='Lcom/android/server/locksettings/LockSettingsService;';SPM='Lcom/android/server/locksettings/SyntheticPasswordManager;';STORE='Lcom/android/server/locksettings/LockSettingsStorage;'
SAM='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
FRAME='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
INVENTORIES=['credentials','construction-credentials','storage-keys','construction-storage-linkage','authority-bootstrap-storage','authority-bootstrap-biometrics']
EXTRA_RECEIPTS=['out/tooling/20261105T195249803276Z-67df37a32b2c498d991415ebb84bd02d/receipt.json']
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
def evidence():
 receipts={p:None for p in EXTRA_RECEIPTS};pins={}
 def walk(v):
  if isinstance(v,dict):
   path=v.get('receipt')
   if isinstance(path,str)and path.endswith('/receipt.json')and(ROOT/path).is_file():receipts.setdefault(path,v.get('receiptSha256'))
   for key,child in v.items():
    if isinstance(key,str)and key.endswith('/receipt.json')and(ROOT/key).is_file():receipts.setdefault(key,child if isinstance(child,str)else child.get('sha256'))
    walk(child)
  elif isinstance(v,list):
   for child in v:walk(child)
 for name in INVENTORIES:
  p=ROOT/('inventory/'+name+'.json');pins[p.relative_to(ROOT).as_posix()]=sha(p);walk(load(p))
 if(OUT/'reads.json').exists():
  for r in load(OUT/'reads.json'):receipts[r['receipt']]=None
 methods={};declarations={}
 for path,pin in receipts.items():
  p=ROOT/path
  if pin and sha(p)!=pin:raise ValueError('Inherited receipt drift '+path)
  r=load(p)
  if r.get('archiveSha256')not in [SAM,FRAME]:continue
  if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Raw drift')
  for line in(ROOT/r['raw']).read_text(encoding='utf8').splitlines():
   row=json.loads(line)
   if row['record']=='class':declarations[row['descriptor']]=(r,row)
   if row['record']=='method':
    b=row['body'];key=b['owner']+'->'+b['signature']
    if key in methods and methods[key][1]['normalizedBodySha256']!=row['normalizedBodySha256']:raise ValueError('Ambiguous source body')
    methods[key]=(r,row)
 return pins,methods,declarations
def collect():
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];path=OUT/'reads.json';ledger=load(path)if path.exists()else[]
 def query(owner,methods=()):
  key={'owner':owner,'methods':list(methods)};old=next((r for r in ledger if r['key']==key),None)
  if old:
   if sha(ROOT/old['raw'])!=old['rawSha256']:raise ValueError('Saved query drift')
   return old
  r=read(ROOT.parent/'firmware/samsung/runtime-20261104/services.jar',SAM,owner,methods,stream='security-authority-quiescence');r['key']=key;ledger.append(r);save(path,ledger);print('saved',owner,len(methods),flush=True);return r
 realm=load(ROOT/'inventory/security-code-realm.json')
 local=next(d for d in realm['privateCohortCandidates']if d['descriptor']==LSS[:-1]+'$LocalService;')
 query(LSS[:-1]+'$LocalService;',local['sourceMethodDescriptors'])
 query(LSS[:-1]+'$4;',['onFinished(ILandroid/os/Bundle;)V'])
 query(LSS[:-1]+'$3;',['onReceive(Landroid/content/Context;Landroid/content/Intent;)V'])
 query(LSS[:-1]+'$1;') # Maintenance-mode listener, not the broadcast receiver.
 for suffix in ['12','9']:
  query(LSS[:-1]+'$$ExternalSyntheticLambda'+suffix+';',['run()V'])
 bio='Lcom/android/server/locksettings/BiometricDeferredQueue;'
 declared=query(bio)['selectedClassDeclarations']
 if len(declared)!=1:raise ValueError('Unique deferred queue')
 selected=[m['signature']for m in declared[0]['methods']if any(x in m['signature'].lower()for x in ['reset','process','hat'])]
 if selected:query(bio,selected)
 for suffix in ['0','1']:
  query(bio[:-1]+'$$ExternalSyntheticLambda'+suffix+';',['run()V'])
 for name in ['StrongAuthTimeoutAlarmListener','NonStrongBiometricTimeoutAlarmListener','NonStrongBiometricIdleTimeoutAlarmListener']:
  query('Lcom/android/server/locksettings/LockSettingsStrongAuth$'+name+';',['onAlarm()V'])
def main():
 pins,methods,declarations=evidence()
 def b(owner,name):
  rows=[r for key,(_,r)in methods.items()if key.startswith(owner+'->'+name+'(')]
  if len(rows)!=1:raise ValueError('Exact unique source method '+owner+' '+name)
  return rows[0]['body']
 def at(body,pc,target):
  i=next(i for i in body['instructions']if i['pc']==pc)
  assert i.get('reference')==target
  return i
 def ignored(body,pc):
  ins=body['instructions'];n=next(n for n,i in enumerate(ins)if i['pc']==pc)
  assert not ins[n+1]['opcode'].startswith('MOVE_RESULT')
 unlock=b(LSS,'unlockUser')
 at(unlock,42,'Landroid/app/IActivityManager;->unlockUser2(ILandroid/os/IProgressListener;)Z')
 at(unlock,49,'Ljava/util/concurrent/CountDownLatch;->await(JLjava/util/concurrent/TimeUnit;)Z');ignored(unlock,49)
 assert next(i for i in unlock['instructions']if i['pc']==47)['literal']==15
 at(b(LSS[:-1]+'$4;','onFinished'),11,'Ljava/util/concurrent/CountDownLatch;->countDown()V')
 verify=b(SPM,'unlockLskfBasedProtector')
 at(verify,435,'Landroid/service/gatekeeper/IGateKeeperService;->verifyChallenge(IJ[B[B)Landroid/service/gatekeeper/GateKeeperResponse;')
 at(verify,461,'Landroid/service/gatekeeper/IGateKeeperService;->enroll(I[B[B[B)Landroid/service/gatekeeper/GateKeeperResponse;')
 at(verify,518,SPM+'->syncState(I)V');at(verify,834,'Lcom/android/internal/widget/ICheckCredentialProgressCallback;->onCredentialVerified()V');at(verify,898,SPM+'->verifyChallenge(Landroid/service/gatekeeper/IGateKeeperService;Lcom/android/server/locksettings/SyntheticPasswordManager$SyntheticPassword;I)Lcom/android/internal/widget/VerifyCredentialResponse;')
 assert not any(i['opcode'].startswith('MONITOR_')for i in verify['instructions'])and not(verify['accessFlags']&0x20020)
 doverify=b(LSS,'doVerifyCredential')
 at(doverify,567,'Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z');at(doverify,622,'Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z')
 setsp=b(LSS,'setLockCredentialWithSpLocked');at(setsp,334,'Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z')
 remove=b(LSS[:-1]+'$$ExternalSyntheticLambda9;','run')
 at(remove,82,'Landroid/hardware/fingerprint/FingerprintManager;->removeAll(ILandroid/hardware/fingerprint/FingerprintManager$RemovalCallback;)V')
 at(remove,149,'Landroid/hardware/face/FaceManager;->removeAll(ILandroid/hardware/face/FaceManager$RemovalCallback;)V')
 for pc in [85,152]:at(remove,pc,'Ljava/util/concurrent/CountDownLatch;->await(JLjava/util/concurrent/TimeUnit;)Z');ignored(remove,pc)
 bio=b('Lcom/android/server/locksettings/BiometricDeferredQueue$$ExternalSyntheticLambda1;','run')
 for pc in [243,396,464]:at(bio,pc,'Ljava/util/ArrayList;->clear()V')
 at(bio,168,'Landroid/hardware/face/FaceManager;->generateChallenge(IILandroid/hardware/face/FaceManager$GenerateChallengeCallback;)V')
 at(bio,376,'Landroid/hardware/fingerprint/FingerprintManager;->resetLockout(II[B)V')
 write=methods[(STORE+'->writeFile(Ljava/io/File;[BZ)V')][1]['body']
 at(write,7,STORE+'->mFileWriteLock:Ljava/lang/Object;');assert next(i for i in write['instructions']if i['pc']==9)['opcode']=='MONITOR_ENTER'
 assert any(c['exceptionType']=='Ljava/io/IOException;'for c in write['catches'])
 metrics=b(LSS,'notifyPasswordMetricsChanged')
 for pc in [34,59]:at(metrics,pc,'Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z')
 at(b(LSS[:-1]+'$$ExternalSyntheticLambda3;','run'),17,'Landroid/app/admin/DevicePolicyManager;->reportPasswordChanged(Landroid/app/admin/PasswordMetrics;I)V')
 api=[]
 for owner in [LSS,SPM,STORE,'Lcom/android/server/locksettings/LockSettingsStrongAuth;','Lcom/android/server/locksettings/BiometricDeferredQueue;']:
  r=declarations[owner][1];found=[m['signature']for m in r['methods']if any(t in m['signature'].lower()for t in ['quies','shutdown','drain','pause','stop','close'])];api.append({'owner':owner,'matchingDeclaredNames':found})
 assert api[0]['matchingDeclaredNames']==['closeSession(Ljava/lang/String;)V']
 assert api[1]['matchingDeclaredNames']==[]and api[3]['matchingDeclaredNames']==[]and api[4]['matchingDeclaredNames']==[]
 focus_lss={'<init>','checkCredential','verifyCredential','doVerifyCredential','setLockCredential','setLockCredentialInternal','setLockCredentialWithIgnoreNotifyIfNeeded','setLockCredentialWithSpLocked','onCredentialVerified','unlockUser','unlockKeystore','unlockCeStorage','notifyPasswordMetricsChanged','onPostLockCredentialChanged','activateEscrowTokens','systemReady','migrateOldDataAfterSystemReady','setString','setLong','setBoolean','removeUserState','closeSession'}
 focus_spm={'unlockLskfBasedProtector','createLskfBasedProtector','verifyChallenge','verifyChallengeInternal','syncState','saveState','destroyLskfBasedProtector','destroyState','writeRepairModeCredentialLocked'}
 focus_store={'writeFile','deleteFile','writeKeyValue','removeUser','removeKey','setString','writePersistentDataBlock','fsyncDirectory','closeDatabase'}
 source=[]
 for key,(receipt,r)in methods.items():
  if not key.startswith('Lcom/android/server/locksettings/'):continue
  owner=r['body']['owner'];name=r['body']['signature'].split('(')[0]
  if owner==LSS and name not in focus_lss:continue
  if owner==SPM and name not in focus_spm:continue
  if owner==STORE and name not in focus_store:continue
  if owner not in [LSS,SPM,STORE]and not any(x in owner for x in ['LockSettingsService$LocalService;','LockSettingsService$Lifecycle;','LockSettingsService$DeviceProvisionedObserver;','LockSettingsService$4;','LockSettingsService$3;','LockSettingsService$$ExternalSyntheticLambda12;','LockSettingsService$$ExternalSyntheticLambda9;','LockSettingsService$$ExternalSyntheticLambda3;','BiometricDeferredQueue','LockSettingsStrongAuth']):continue
  b=r['body'];source.append({'method':key,'physicalDex':r['physicalDex'],'logicalHeaderOffset':r['logicalHeaderOffset'],'normalizedBodySha256':r['normalizedBodySha256'],'raw':receipt['raw'],'rawSha256':receipt['rawSha256'],'accessFlags':b['accessFlags'],'monitors':[{'pc':i['pc'],'opcode':i['opcode'],'registers':i.get('registers',[])}for i in b['instructions']if i['opcode'].startswith('MONITOR_')],'sites':[{'pc':i['pc'],'opcode':i['opcode'],'reference':i['reference']}for i in b['instructions']if i.get('referenceKind')in ['method','field','type']],'catches':b['catches']})
 gpath=ROOT/'inventory/authority-bootstrap-handoff.json';g=load(gpath);pins[gpath.relative_to(ROOT).as_posix()]=sha(gpath)
 selected_ids={'stop-stock-java','stock-keeper','return-force-kills','return-namespace-kills','return-stock-reconstruct'}
 windows=[x for x in g['sourceFacts']if x['id']in selected_ids]
 for inp in g['inputs']:
  if inp['sourceRelativePath']in {w['sourceRelativePath']for w in windows}and sha(ROOT/inp['path'])!=inp['sha256']:raise ValueError('OneOS boundary source drift')
 cards=[
  {'id':'ordinary-verification-mutates','source':'SPM.unlockLskfBasedProtector','sites':{'nativeVerify':435,'conditionalReenroll':461,'syncState':518,'earlyProgress':834,'laterVerifyChallenge':898,'laterSync':985},'result':'Verification is write-capable; early callback is not completion. These calls cannot be admitted as harmless reads during retirement.'},
  {'id':'separate-synchronous-locks','source':'LSS.doVerifyCredential / SPM.unlockLskfBasedProtector / Storage.writeFile','sites':{'lssSpManagerMonitorEnter':323,'storageFileLockEnter':9},'result':'SPM monitor regions do not encompass handler/alarm/AM/native tails; SPM unlock has no own synchronized flag/monitor, and storage file/SQL locks are separate. No single acquired lock proves global quiescence.'},
  {'id':'am-unlock-external-tail','source':'LSS.unlockUser / LSS$4.onFinished','sites':{'unlockUser2':42,'fifteenSecondAwaitIgnored':49,'actualCallbackCountDown':11},'result':'Timed wait Boolean is ignored; method/Binder return may precede original AM onFinished. Actual listener and external operation ownership must survive timeout.'},
  {'id':'deferred-verify-policy','source':'LSS.doVerifyCredential / onCredentialVerified','sites':{'enqueueUserAuthInfo':567,'enqueueIntegrityWork':622},'result':'Real derived GK authentication input and SI work are posted after verification; capture original queued objects and completion, not only Binder frames.'},
  {'id':'biometric-reset-not-empty-list','source':'BiometricDeferredQueue Lambda0/Lambda1 / requestHatFromGatekeeperPassword','sites':{'faceChallengeRequest':168,'fingerprintResetRequest':376,'clearLists':[243,396,464]},'result':'Queue worker can issue more GK verify/HAT calls and challenge/reset RPCs then clear its lists; list empty or Handler return is not hardware/session completion. Challenge callback/provider/native/durable-state disposition remains unclosed.'},
  {'id':'credential-removal-async','source':'LSS.setLockCredentialWithSpLocked / Lambda9.run','sites':{'postRemovalWork':334,'fingerprintRemoveAll':82,'ignoredFingerprintTimedAwait':85,'faceRemoveAll':149,'ignoredFaceTimedAwait':152},'result':'Original posted biometric deletion work can outlive setLockCredential and its own timed wait. Removal callback/native persistence ownership is not established by these returns.'},
  {'id':'policy-notifications-alarms','source':'LSS.notifyPasswordMetricsChanged / Lambda3 / StrongAuth Handler+alarm listeners','sites':{'postMetricsWork':[34,59],'dpmReportPasswordChanged':[17,33],'wmReportPasswordChanged':44},'result':'Actual DPM/WM calls and main-Looper StrongAuth messages/alarms must be acknowledged or transferred with real deadlines/state. Do not drop callbacks or clear policy to make queues empty.'},
  {'id':'local-and-lifecycle-ingress','source':'LSS$LocalService12 / Lifecycle / DeviceProvisionedObserver / Receiver$3','result':'Local token/user/escrow/provisioning/boot/receiver paths bypass a new Binder router. createNewUser initializes SP/native key state; token unlock enters onCredentialVerified; user removal reaches storage. Known maintenance registration/other feature tails still need closure.'},
  {'id':'native-and-durability-uncertainty','source':'existing authority-bootstrap-storage + original Storage.writeFile/fsyncDirectory','result':'Real Gatekeeper/Weaver, keystore, vold and file/DB operations have distinct acknowledgements. Original void/logging/caught-error paths and lost replies can follow mutations. No scalar getter, PID, sync shell command or database close settles all outcomes.'}]
 report={'schema':'security-authority-quiescence-source/v1','status':'SOURCE_CARD_ONLY; no observed existing comprehensive retirement/drain control or implemented root hook','sourceServicesSha256':SAM,'inheritedInventories':pins,'peerLambda3Receipt':{'path':EXTRA_RECEIPTS[0],'sha256':sha(ROOT/EXTRA_RECEIPTS[0])},'methodProofs':source,'methodCount':len(source),'cards':cards,'declaredControlNameCheck':api,'oneosBoundaryFacts':windows,'minimalProposedHookBoundaries':[
  'Before switch971: actual old-system_server authority admission must close at real original Binder method ingress AND direct LocalService/lifecycle/observer/receiver roots; stale/cached Binder refs remain covered. No current hook implemented.',
  'Retain each admitted real operation and actual child Runnable/message/listener/native operation through terminal result or owned reconciliation; shared counters are meaningful only after complete producer/child enrollment, not router call count.',
  'Stop or generation-fence new registered event/alarm/job production without fabricating deadlines or dropping required policy. A Handler marker only proves its own execution; nested posts/delayed jobs/external callbacks require own acknowledgement.',
  'A coordinator outside the queues/monitors it awaits must join actual service Handler, StrongAuth main work, biometric queue/callbacks, DPM/user/unlock/native/storage tails. Do not wait for a queue from that same queue or call completion from a synthetic listener.',
  'Track real native/storage issue and outcome inside original caught/void paths; retain unresolved commit ownership, never blind retry/read-only hardware probe. No complete native/drain/reconciliation API found here.',
  'Only after old-generation terminal acknowledgement may OneOS stop zygote/kill it and construct the next writer. Apply the same cut before dedicated-authority return teardown/stock reconstruction; code/name changes alone do not transfer state.'], 'alternatives':[
  {'choice':'Instrument genuine old authority with reviewed root/bootstrap hooks','sourceSupport':'Concrete method/worker/listener boundaries identified','missing':'Hook installation/admission, complete producer closure, native result/durability ownership, protected UI and real completion API are unimplemented; no module activation authorized'},
  {'choice':'Retain actual initialized old Samsung authority','sourceSupport':'Avoids transferring an unfinished old operation to a new credential writer','missing':'Current OneOS stops/kills its system_server; retaining security/local dependencies and preventing two framework producers requires a different admitted topology'},
  {'choice':'Treat kill/normal crash recovery as handoff','sourceSupport':'Original startup has migration/reconciliation code','missing':'No proof of atomic recovery across all outstanding SP/Gatekeeper/Weaver/vold/keystore/FP operations; process death is not completion and does not meet the requested no-reboot owned return'}], 'fullProducerClosure':False,'rootHookImplemented':False,'originalWorkerDrainImplemented':False,'nativeCompletionProved':False,'oemExecuted':False,'phoneActions':0,'adbCalls':0,'runtimeAccepted':False,'toolSha256':sha(__file__)}
 save(OUT/'collected.json',{'inheritedInventories':pins,'methods':source});save(ROOT/'inventory/security-authority-quiescence.json',report);print('verified',len(source),'focused method proofs;',len(cards),'source cards; no admission/drain implementation')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');a=p.parse_args()
 if a.collect:collect()
 main()
