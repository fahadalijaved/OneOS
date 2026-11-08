"""Offline user-identity dependency and typed-protocol audit; no device/state access."""
import argparse,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'out/security-user-binding'
ARCHIVES={
 'samsung-services':('../firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
 'samsung-framework':('../firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
 'coloros-services':('../firmware/donor/extracted/system/framework/services.jar','66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
 'coloros-framework':('../firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2')}
TARGETS=('Landroid/os/UserManager;','Lcom/android/server/pm/UserManagerInternal;','Landroid/app/supervision/SupervisionManagerInternal;','Landroid/content/pm/UserInfo;','Landroid/content/pm/UserProperties;')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def rows(r):
 if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Raw evidence drift')
 return [json.loads(x) for x in (ROOT/r['raw']).read_text().splitlines()]
def proxy_protocol(b):
 """Resolve each transact register's last writer; refuse unknown assignments."""
 code=b['instructions'];calls=[]
 def regs(i):return i.get('registers',list(range(i.get('registerStart',0),i.get('registerStart',0)+i.get('registerCount',0))))
 def constant(before,wanted,depth=0):
  if depth>32:raise ValueError('Register copy chain exceeds bound')
  nonwriters=('INVOKE','IF_','RETURN','GOTO','PACKED_SWITCH','SPARSE_SWITCH','THROW','MONITOR','IPUT','SPUT','APUT','FILL_ARRAY_DATA','NOP')
  for n in range(before-1,-1,-1):
   i=code[n];rr=regs(i);op=i['opcode']
   if not rr or rr[0]!=wanted or op.startswith(nonwriters):continue
   if op.startswith('CONST') and 'literal' in i:return i['literal'],i['pc']
   if op.startswith('MOVE') and len(rr)==2:return constant(n,rr[1],depth+1)
   raise ValueError('Transact register last writer is not a literal/copy')
  raise ValueError('Transact register has no established constant')
 for n,i in enumerate(code):
  if i.get('reference','')!='Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z':continue
  rr=regs(i)
  if len(rr)!=5:raise ValueError('Unexpected transact register shape')
  value,pc=constant(n,rr[1]);flags,flagpc=constant(n,rr[4])
  calls.append({'code':value,'flags':flags,'pc':i['pc'],'codeConstantPc':pc,'flagsConstantPc':flagpc})
 if len(calls)!=1:raise ValueError('Require one exact transact')
 parcel=[i['reference'].split('->')[1] for i in code if i.get('reference','').startswith('Landroid/os/Parcel;->')]
 return {**calls[0],'request':[s for s in parcel if s.startswith('write') and not s.startswith('writeInterfaceToken')],'result':[s for s in parcel if s.startswith(('read','create')) and not s.startswith('readException')]}
def report(receipts,surface):
 bodies={};proofs={}
 for key,r in receipts.items():
  archive=next((a for a in ARCHIVES if key.startswith(a+':')),None)
  if archive is None:continue
  for row in rows(r):
   if row['record']!='method':continue
   b=row['body'];name=archive+':'+b['owner']+'->'+b['signature']
   if name in bodies and bodies[name]['normalizedBodySha256']!=row['normalizedBodySha256']:raise ValueError('Conflicting method source')
   bodies[name]=row
   proofs[name]={'bodySha256':row['normalizedBodySha256'],'hasCode':b['hasCode'],'instructionCount':len(b['instructions']),'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':r['receipt']}
 reused=json.loads((ROOT/'inventory/construction-credentials.json').read_text())['methods']
 for key,p in reused.items():
  if not (key.startswith('Lcom/android/server/locksettings/LockSettingsService;-><init>') or key.endswith('CleanupManager;->verifyKnownUsers()V')):continue
  row=next(x for x in rows({'raw':p['raw'],'rawSha256':p['rawSha256']}) if x['record']=='method' and x['body']['owner']+'->'+x['body']['signature']==key)
  name='samsung-services:'+key;bodies[name]=row
  proofs[name]={'bodySha256':row['normalizedBodySha256'],'hasCode':row['body']['hasCode'],'instructionCount':len(row['body']['instructions']),'raw':p['raw'],'rawSha256':p['rawSha256'],'receipt':p['receipt'],'reused':True}
 def body(archive,owner,method):return bodies[archive+':'+owner+'->'+method]['body']
 def protocol(archive,method):
  b=body(archive,'Landroid/os/IUserManager$Stub$Proxy;',method)
  return {**proxy_protocol(b),'bodySha256':bodies[archive+':'+b['owner']+'->'+method]['normalizedBodySha256']}
 methods=sorted({v['body']['signature'] for k,v in bodies.items() if k.startswith('samsung-framework:Landroid/os/IUserManager$Stub$Proxy;->')})
 wire=[]
 for method in methods:
  host=protocol('samsung-framework',method);guest=protocol('coloros-framework',method)
  wire.append({'method':method,'role':'candidate-only internal-property projection' if method.startswith('getUserPropertiesCopy') else 'required UserManager remote projection','samsung':host,'coloros':guest,'sameSelectedRequestAndResultOperations':host['request']==guest['request'] and host['result']==guest['result'],'sameTransactionCode':host['code']==guest['code']})
 def parcel_fields(archive,method):
  b=body(archive,'Landroid/content/pm/UserInfo;',method)
  return [i['reference'].split('->')[1] for i in b['instructions'] if i['opcode'].startswith(('IGET','IPUT')) and i.get('reference','').startswith('Landroid/content/pm/UserInfo;->')]
 schema={a:{'readFields':parcel_fields(a,'<init>(Landroid/os/Parcel;)V'),'writeFields':parcel_fields(a,'writeToParcel(Landroid/os/Parcel;I)V')} for a in ('samsung-framework','coloros-framework')}
 if any(v['readFields']!=v['writeFields'] for v in schema.values()):raise ValueError('UserInfo own read/write order differs')
 checks=[]
 def check(fid,archive,owner,method,need):
  b=body(archive,owner,method);pc=[]
  for fragment in need:
   found=[i['pc'] for i in b['instructions'] if fragment in i.get('reference','')]
   if not found:raise ValueError('Source assertion missing: '+fid+' '+fragment)
   pc.extend(found)
  key=archive+':'+owner+'->'+method
  checks.append({'id':fid,'classification':'observed-source','methodProof':key,'pcsDecimal':sorted(set(pc))})
 check('client-only-user-owner','samsung-framework','Landroid/os/UserManager;','<init>(Landroid/content/Context;Landroid/os/IUserManager;)V',('->mService:','->getApplicationContext()','->getUserId()'))
 check('client-cache-construction','samsung-framework','Landroid/os/UserManagerCache;','<init>()V',('Object;-><init>()','->mQuietModeEnabledLock:','->mUserSerialNumberLock:'))
 check('context-lookup-user-client','samsung-framework','Landroid/os/UserManager;','get(Landroid/content/Context;)Landroid/os/UserManager;',('string=user','->getSystemService('))
 check('application-context-escapes-to-application','samsung-framework','Landroid/app/ContextImpl;','getApplicationContext()Landroid/content/Context;',('LoadedApk;->getApplication()','ActivityThread;->getApplication()'))
 check('context-global-registry','samsung-framework','Landroid/app/ContextImpl;','getSystemService(Ljava/lang/String;)Ljava/lang/Object;',('SystemServiceRegistry;->getSystemService(',))
 check('client-global-headless-query','samsung-framework','Landroid/os/UserManager;','isHeadlessSystemUserMode()Z',('string=user','ServiceManager;->getService(','IUserManager;->isHeadlessSystemUserMode()','->sIsHeadlessSystemUser:'))
 check('serial-wrapper-identifies-real-user','samsung-framework','Landroid/os/UserManager;','getSerialNumberForUser(Landroid/os/UserHandle;)J',('UserHandle;->getIdentifier()','->getUserSerialNumber('))
 check('serial-server-original-user-record','samsung-services','Lcom/android/server/pm/UserManagerService;','getUserSerialNumber(I)I',('->mUsersLock:','->getUserInfoLU(','UserInfo;->serialNumber:I'))
 ctor=next(v['body']['signature'] for k,v in bodies.items() if k.startswith('samsung-services:Lcom/android/server/locksettings/LockSettingsService;-><init>'))
 check('early-cleanup-application-context-route','samsung-services','Lcom/android/server/locksettings/LockSettingsService;',ctor,('Context;->getApplicationContext()','UserManager;->get(','CleanupManager;-><init>','->mUserManager:'))
 check('cleanup-compares-and-mutates-user-serial-state','samsung-services','Lcom/android/server/locksettings/recoverablekeystore/storage/CleanupManager;','verifyKnownUsers()V',('->getUserSerialNumbers()','UserManager;->getSerialNumberForUser(','->removeDataForUser(','->storeUserSerialNumber('))
 check('actual-client-factory-uses-user-binder','samsung-framework','Landroid/app/SystemServiceRegistry$82;','createService(Landroid/app/ContextImpl;)Landroid/os/UserManager;',('string=user','ServiceManager;->getServiceOrThrow(','IUserManager$Stub;->asInterface(','UserManager;-><init>'))
 check('actual-production-registry-root','samsung-services','Lcom/android/server/pm/PackageManagerService$$ExternalSyntheticLambda39;','produce(Lcom/android/server/pm/PackageManagerServiceInjector;Lcom/android/server/pm/PackageManagerService;)Ljava/lang/Object;',('Environment;->getDataDirectory()','UserManagerService;-><init>'))
 check('missing-userlist-can-create-new-user','samsung-services','Lcom/android/server/pm/UserManagerService;','readUserListLP()V',('string=userlist.xml not found, fallback to single user','->fallbackToSingleUserLP()'))
 check('fallback-persists-fresh-user','samsung-services','Lcom/android/server/pm/UserManagerService;','fallbackToSingleUserLP()V',('UserInfo;-><init>','->putUserInfo(','->mNextSerialNumber:','->writeUserLP(','->writeUserListLP()'))
 check('user-registry-relative-root','samsung-services','Lcom/android/server/pm/UserManagerService;','<clinit>()V',('string=system','string=users','->USER_INFO_DIR:'))
 check('user-record-recovery-paths','samsung-services','Lcom/android/server/pm/UserManagerService;','getUserFile(I)Lcom/android/server/pm/ResilientAtomicFile;',('string=.xml','string=.xml.backup','string=.xml.reservecopy','ResilientAtomicFile;-><init>'))
 check('context-only-service-constructor-uses-cache-dir','samsung-services','Lcom/android/server/pm/UserManagerService;','<init>(Landroid/content/Context;)V',('Context;->getCacheDir()',))
 check('internal-user-info-original-owner','samsung-services','Lcom/android/server/pm/UserManagerService$LocalService;','getUserInfo(I)Landroid/content/pm/UserInfo;',('->mUsersLock:','->mUsers:','UserData;->info:'))
 check('runtime-user-state-is-current-owner-state','samsung-services','Lcom/android/server/pm/UserManagerService$LocalService;','isUserUnlockingOrUnlocked(I)Z',('->mUserStates:','WatchedUserStates;->get(','StorageManager;->isCeStorageUnlocked('))
 check('runtime-state-invalidates-cache','samsung-services','Lcom/android/server/pm/UserManagerService$LocalService;','setUserState(II)V',('SparseIntArray;->put(','UserManager;->invalidateIsUserUnlockedCache()'))
 check('main-user-admin-real-resource-policy','samsung-services','Lcom/android/server/pm/UserManagerService;','isMainUserPermanentAdmin()Z',('Context;->getResources()','Resources;->getBoolean('))
 check('user-properties-original-policy-owner','samsung-services','Lcom/android/server/pm/UserManagerService;','getUserPropertiesInternal(I)Landroid/content/pm/UserProperties;',('->mUsersLock:','->getUserDataLU(','UserData;->userProperties:'))
 check('public-property-copy-is-caller-filtered','samsung-services','Lcom/android/server/pm/UserManagerService;','getUserPropertiesCopy(I)Landroid/content/pm/UserProperties;',('->checkQueryOrInteractPermissionIfCallerInOtherProfileGroup(','Binder;->getCallingUid()','->hasManageUsersPermission()','UserProperties;-><init>(Landroid/content/pm/UserProperties;ZZZ)'))
 check('supervision-loaded-policy','samsung-services','Lcom/android/server/supervision/SupervisionService$SupervisionManagerInternalImpl;','isEscrowTokenRequired(I)Z',('->mSupervisionSettings:','->getUserData(','->escrowTokenRequired:'))
 check('supervision-guest-extra-flag','coloros-services','Lcom/android/server/supervision/SupervisionService$SupervisionManagerInternalImpl;','isEscrowTokenRequired(I)Z',('->verifySupervisionRoleHoldersBeforeDestroyingEscrowToken()',))
 check('supervision-state-files','samsung-services','Lcom/android/server/supervision/SupervisionSettings;','<init>()V',('Environment;->getDataSystemDirectory()','string=supervision_recovery_info.xml','string=supervision_settings.xml','AtomicFile;->openRead()'))
 check('samsung-user-attributes-used-by-policy','samsung-framework','Landroid/content/pm/UserInfo;','isSuperLocked()Z',('->flags:I','->attributes:I'))
 exported={'schema':'security-user-binding/v1','status':'STATIC_REQUIRED_SURFACE_AND_PROTOCOL_PINNED_LIVE_OWNER_OPEN','sourceAssertions':checks,'methodProofs':proofs,'directRequiredSurface':surface['requiredTargets'],'requiredCallsites':surface['directLocksettingsUserEdges'],'selectedContextCallsites':surface['contextEdgesInReusedBodies'],'wireCases':wire,'userInfoParcel':schema,'reusedRawPins':surface['reusedRawPins'],'receiptLedger':'out/security-user-binding/receipts.json','receiptLedgerSha256':sha(WORK/'receipts.json'),'toolSha256':sha(Path(__file__)),'uniqueSelectedMethods':len(bodies),'uniqueSelectedCodeBodies':sum(x['body']['hasCode'] for x in bodies.values()),'archivePins':{a:{'path':p,'sha256':h} for a,(p,h) in ARCHIVES.items()},'goalSha256':sha(ROOT/'GOAL.md'),'runtimeVerified':False,'privateStateRead':False,'phoneActions':False,'oemExecuted':False,'limits':surface['limits']+['Same Parcel operation signatures do not prove semantic or live authority equivalence','IUserManager does not expose the required local maintenance-listener or supervision policy contract','No service is instantiated and no current user ID/serial/profile mapping was acquired']}
 exported['candidateCut']={'classification':'source-supported design inference; no transport/authority instantiated','smallestClientOwner':'Actual UserManager(Context,IUserManager), not UserManagerService(Context)','beforeEagerCleanup':['same bound user client through original and application Context plus string/class lookups','real original user serial records and recoverable DB generation; unknown transport/identity must not be converted to missing-user -1','coherent same-source policy/resources/local-service and native/FBE owner binding retained before publication'], 'typedRemoteSurface':'11 exact required IUserManager projections; candidate property-copy12 is caller-filtered and not automatically equivalent to full local properties','requiredAdditionalLocalSemantics':['UserManagerInternal.getUserProperties credential-sharing value from actual owner','isMainUserPermanentAdmin genuine resource policy','maintenance lifecycle registration/callback ownership for unchanged reached branch','SupervisionManagerInternal.isEscrowTokenRequired from original loaded supervision settings'], 'contextEscapeAndCaches':['getApplicationContext returns LoadedApk/ActivityThread application','UserManager caches serial/profile/info/unlocked state and static headless query resolves global user Binder','generation replacement must cover cached objects, callbacks and global service queries; new client alone is insufficient'], 'liveOwnerOpen':['OneOS stops original system_server; no surviving genuine host user Binder/local owner proved','controlled import would need authoritative registry and genuine production dependencies before eager reads/migrations; never create a fresh guest user registry','running/unlocking state depends on actual active user-state owner and CE storage route, not immutable identity snapshot']}
 (ROOT/'inventory/security-user-binding.json').write_text(json.dumps(exported,indent=2)+'\n')
 print('PASS '+str(len(checks))+' source assertions; '+str(len(wire))+' exact proxy cases; '+str(len(bodies))+' unique selected methods')
 for row in wire:print(row['method']+' Samsung='+str(row['samsung']['code'])+' ColorOS='+str(row['coloros']['code']))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collect',action='store_true');a=p.parse_args()
 WORK.mkdir(parents=True,exist_ok=True);ledger=WORK/'receipts.json'
 for path,pin in ARCHIVES.values():
  if sha(ROOT/path)!=pin:raise ValueError('Source archive drift before audit')
 receipts=json.loads(ledger.read_text()) if ledger.exists() else {}
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 def query(key,archive,**selector):
  path,pin=ARCHIVES[archive]
  if key in receipts and 'methods' in selector and receipts[key]['query']['exactMethods']!=selector['methods']:
   key+=':'+hashlib.sha256(json.dumps(selector['methods']).encode()).hexdigest()[:12]
  if key not in receipts:
   if not a.collect:raise ValueError('Missing source receipt: '+key)
   receipts[key]=read(ROOT/path,pin,stream='security-user-binding',**selector)
   ledger.write_text(json.dumps(receipts,indent=2)+'\n')
   print(key+': '+str(len(receipts[key]['selectedMethodProofs']))+' bodies, '+str(receipts[key]['referenceMatchCount'])+' refs',flush=True)
  r=receipts[key]
  if r['archiveSha256']!=pin:raise ValueError('Archive identity differs')
  rows(r);return r
 edges=[]
 for target in TARGETS:
  r=query('samsung-directrefs:'+target,'samsung-services',reference=target)
  for x in rows(r):
   if x['record']!='reference' or not x['caller'].startswith('Lcom/android/server/locksettings/'):continue
   edges.append({'caller':x['caller'],'pc':x['instruction']['pc'],'target':x['instruction']['reference'],'opcode':x['instruction']['opcode'],'raw':r['raw'],'receipt':r['receipt']})
 required={target:sorted(set(e['target'] for e in edges if e['target'].startswith(target+'->'))) for target in TARGETS}
 def selected(archive,owner,names,tag='required'):
  key=archive+':'+owner+':'+tag
  decl=query(key+':declarations',archive,class_name=owner)
  classes=decl['selectedClassDeclarations']
  if len(classes)!=1:return None
  methods=[m['signature'] for m in classes[0]['methods'] if m['signature'].split('(')[0] in names]
  absent=sorted(set(names)-{m.split('(')[0] for m in methods})
  print(key+' absent '+','.join(absent),flush=True)
  if not methods:return None
  return query(key,archive,class_name=owner,methods=methods)
 for archive in ('samsung-framework','coloros-framework'):
  selected(archive,'android.app.ContextImpl',{'getApplicationContext','getSystemService','getSystemServiceName'},'required-context')
  selected(archive,'android.content.Context',{'getSystemService'},'required-context')
  names={s.split('->')[1].split('(')[0] for s in required['Landroid/os/UserManager;']}
  selected(archive,'android.os.UserManager',names)
  selected(archive,'android.os.UserManager',{'<init>','getUserSerialNumber','getProfileIds'},'required-helpers')
  selected(archive,'android.os.UserManager',{'getUserProperties'},'local-policy-equivalent')
  selected(archive,'android.os.UserManagerCache',{'<clinit>','getUserInfo','getProfileIdsWithDisabled','getProfiles','getProfileParent','isQuietModeEnabled','isUserUnlockingOrUnlocked','getUserSerialNumber'},'required-cache')
  selected(archive,'android.os.UserManagerCache',{'<init>'},'client-cache-constructor')
  selected(archive,'android.os.UserManager$1',{'<init>'},'client-cache-constructor')
  callbacks=set()
  for key,r in list(receipts.items()):
   if not key.startswith(archive+':android.os.UserManager:required') or key.endswith(':declarations'):continue
   for row in rows(r):
    if row['record']!='method':continue
    for i in row['body']['instructions']:
     ref=i.get('reference','')
     if ref.startswith('Landroid/os/UserManager$$ExternalSyntheticLambda'):callbacks.add(ref.split(';')[0]+';')
  for callback in sorted(callbacks):selected(archive,callback,{'apply','applyOrThrow','<init>'},'cache-callback')
  dispatch=set()
  for key,r in list(receipts.items()):
   if not key.startswith(archive+':Landroid/os/UserManager$$ExternalSyntheticLambda') or key.endswith(':declarations'):continue
   for row in rows(r):
    if row['record']=='method':dispatch.update(i['reference'].split('->')[1].split('(')[0] for i in row['body']['instructions'] if i.get('reference','').startswith('Landroid/os/UserManager;->'))
  selected(archive,'android.os.UserManager',dispatch,'cache-dispatch')
  for depth in range(4):
   known=set();wanted=set()
   for key,r in list(receipts.items()):
    if not key.startswith(archive+':android.os.UserManager:') or key.endswith(':declarations'):continue
    for row in rows(r):
     if row['record']!='method':continue
     known.add(row['body']['signature'].split('(')[0])
     for ins in row['body']['instructions']:
      ref=ins.get('reference','')
      if ref.startswith('Landroid/os/UserManager;->'):
       name=ref.split('->')[1].split('(')[0]
       if name.startswith(('lambda$','$r8$lambda$')):wanted.add(name)
   if not wanted-known:break
   selected(archive,'android.os.UserManager',wanted-known,'cache-reached-'+str(depth))
 for archive in ('samsung-services','coloros-services'):
  for owner in ('Lcom/android/server/pm/UserManagerInternal;',):
   names={s.split('->')[1].split('(')[0] for s in required[owner]}
   selected(archive,owner,names)
  selected(archive,'com.android.server.pm.UserManagerService$LocalService',{'getMainUserId','getProfileParentId','getUserInfo','getUserProperties','isMainUserPermanentAdmin','addMaintenanceModeLifecycleListener'},'required-owner')
  selected(archive,'com.android.server.pm.UserManagerService$LocalService',{'isUserRunning','isUserUnlockingOrUnlocked','setUserState','removeUserState'},'lifecycle-owner')
  selected(archive,'com.android.server.pm.UserManagerService',{'getUserSerialNumber','getUserInfo','getUsers','getProfiles','getProfileIds','getProfileParent','getUserProperties','isUserRunning','isUserUnlockingOrUnlocked','isHeadlessSystemUserMode','isQuietModeEnabled','getMainUserId'},'required-owner')
  selected(archive,'com.android.server.pm.UserManagerService',{'<init>','readUserListLP','readUserLP','fallbackToSingleUserLP'},'state-owner-startup')
  selected(archive,'com.android.server.pm.UserManagerService',{'<clinit>','getInstance','getUserFile','getMainUserIdUnchecked','getProfileParentIdUnchecked','getUserPropertiesInternal','isMainUserPermanentAdmin'},'required-owner-helpers')
  selected(archive,'com.android.server.pm.UserManagerService',{'getUserPropertiesCopy'},'local-policy-equivalent')
  selected(archive,'com.android.server.supervision.SupervisionService$SupervisionManagerInternalImpl',{'isEscrowTokenRequired'},'required-owner')
  selected(archive,'com.android.server.supervision.SupervisionSettings',{'<init>','getUserData','getUserFile','loadUserData'},'required-owner')
 for archive in ('samsung-framework','coloros-framework'):
  for owner in ('Landroid/app/supervision/SupervisionManagerInternal;','Landroid/content/pm/UserInfo;','Landroid/content/pm/UserProperties;'):
   names={s.split('->')[1].split('(')[0] for s in required[owner] if '(' in s}
   if owner in ('Landroid/content/pm/UserInfo;','Landroid/content/pm/UserProperties;'):names|={'<init>','writeToParcel'}
   selected(archive,owner,names)
 binder=set()
 for key,r in list(receipts.items()):
  if not any(t in key for t in (':android.os.UserManager:',':Landroid/os/UserManager$$ExternalSyntheticLambda')) or key.endswith(':declarations'):continue
  for x in rows(r):
   if x['record']=='method':
    binder.update(i['reference'].split('->')[1].split('(')[0] for i in x['body']['instructions'] if i.get('reference','').startswith('Landroid/os/IUserManager;->'))
 for archive in ('samsung-framework','coloros-framework'):
  selected(archive,'android.os.IUserManager$Stub$Proxy',binder)
  selected(archive,'android.os.IUserManager$Stub$Proxy',{'getUserPropertiesCopy'},'candidate-local-policy-equivalent')
 r=query('samsung-user-client-factory-refs','samsung-framework',reference='Landroid/os/UserManager;-><init>(Landroid/content/Context;Landroid/os/IUserManager;)V')
 for row in rows(r):
  if row['record']=='reference':
   owner,sig=row['caller'].split('->')
   selected('samsung-framework',owner,{sig.split('(')[0]},'client-factory')
 decl=receipts['samsung-services:com.android.server.pm.UserManagerService:state-owner-startup:declarations']
 ctor=next(m['signature'] for m in decl['selectedClassDeclarations'][0]['methods'] if m['signature'].startswith('<init>') and 'PersonaManagerService;' in m['signature'])
 r=query('samsung-production-user-server-factory-refs','samsung-services',reference='Lcom/android/server/pm/UserManagerService;->'+ctor)
 for row in rows(r):
  if row['record']=='reference':
   owner,sig=row['caller'].split('->')
   if owner=='Lcom/android/server/pm/UserManagerService;':continue
   query('samsung-services:'+owner+':production-user-owner-factory','samsung-services',class_name=owner,methods=[sig])
 context=[];seen=set();reused=[]
 sources=[json.loads((ROOT/'inventory/construction-credentials.json').read_text())['methods'],json.loads((ROOT/'inventory/credentials.json').read_text())['methodProofs']]
 for methods in sources:
  for name,m in methods.items():
   if name.startswith('coloros:') or m.get('archiveSha256',ARCHIVES['samsung-services'][1])==ARCHIVES['coloros-services'][1]:continue
   raw=m['raw']
   receipt=json.loads((ROOT/m['receipt']).read_text())
   if receipt['raw']!=raw:raise ValueError('Reused raw/receipt path differs')
   expected=m.get('rawSha256',receipt['rawSha256'])
   if expected!=receipt['rawSha256']:raise ValueError('Reused raw/receipt hash differs')
   r={'raw':raw,'rawSha256':expected}
   if raw in seen:continue
   seen.add(raw);reused.append({'raw':raw,'rawSha256':r['rawSha256']})
   for x in rows(r):
    if x['record']!='method':continue
    b=x['body']
    for ins in b['instructions']:
     target=ins.get('reference','')
     if target.startswith(('Landroid/content/Context;->','Landroid/content/ContextWrapper;->')):
      context.append({'caller':b['owner']+'->'+b['signature'],'pc':ins['pc'],'target':target,'bodySha256':x['normalizedBodySha256'],'raw':raw})
 surface={'directLocksettingsUserEdges':edges,'requiredTargets':required,'contextEdgesInReusedBodies':context,'reusedRawPins':reused,'limits':['User edges are complete direct references owned by selected three types in locksettings package of actual Samsung services; indirect calls/reflection/JNI are not expanded','Context edges cover reused selected method bodies, not all services','Source graph only; live IDs/serials/profiles/native policy not acquired']}
 (WORK/'surface.json').write_text(json.dumps(surface,indent=2)+'\n')
 report(receipts,surface)
 for path,pin in ARCHIVES.values():
  if sha(ROOT/path)!=pin:raise ValueError('Source archive drift after audit')
 print('SURFACE '+str(len(edges))+' direct user edges; '+str(len(context))+' selected Context edges')
 for target,methods in required.items():print(target+' '+json.dumps(methods))
if __name__=='__main__':main()
