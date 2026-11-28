"""Finite user/local-policy bootstrap gate. Static OEM parsing only, never construction."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'out/authority-bootstrap-users'
BASE=ROOT/'inventory/security-user-binding.json'
ARCHIVES={
 'samsung-services':('firmware/samsung/runtime-20261104/services.jar','def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
 'coloros-services':('firmware/donor/extracted/system/framework/services.jar','66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
 'samsung-framework':('firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe')}


def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def report():
 """Revalidate pinned saved source evidence; no new reader calls or OEM execution."""
 base=json.loads(BASE.read_text());queries=json.loads((WORK/'queries.json').read_text())
 proofs={};receipts={};rawpins={}
 for key,p in base['methodProofs'].items():
  if any(t in key for t in ('UserManager;', 'UserManagerService;', 'UserManagerService$LocalService;', 'UserProperties;', 'SupervisionSettings;', 'SupervisionManagerInternalImpl;')):
   proofs[key]=dict(p)
 for q in queries:
  rp=ROOT/q['receipt'];r=json.loads(rp.read_text())
  assert r['archiveSha256']==ARCHIVES[q['side']][1]
  assert r['readerExitCode']==0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
  assert not r['oemCodeExecuted'] and not r['androidExecuted']
  assert sha(ROOT/r['raw'])==r['rawSha256']
  receipts[q['receipt']]=sha(rp);rawpins[r['raw']]=r['rawSha256']
  for p in r['selectedMethodProofs']:
   key=q['side']+':'+p['owner']+'->'+p['signature']
   proofs[key]={'bodySha256':p['normalizedBodySha256'],'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':q['receipt'],'physicalDex':p['physicalDex'],'logicalHeaderOffset':p['logicalHeaderOffset']}
 field=json.loads((WORK/'pms-field-reference.json').read_text())
 assert field['referenceMatchCount']==25 and sha(ROOT/field['raw'])==field['rawSha256']
 receipts[field['receipt']]=sha(ROOT/field['receipt']);rawpins[field['raw']]=field['rawSha256']
 fieldrefs=[x for x in map(json.loads,(ROOT/field['raw']).read_text().splitlines()) if x.get('record')=='reference']
 for p in proofs.values():
  assert sha(ROOT/p['raw'])==p['rawSha256']
  receipts[p['receipt']]=sha(ROOT/p['receipt']);rawpins[p['raw']]=p['rawSha256']
 def body(part):
  key=next(k for k in proofs if part in k);p=proofs[key]
  return next(x['body'] for x in map(json.loads,(ROOT/p['raw']).read_text().splitlines()) if x.get('record')=='method' and x['body']['owner']+'->'+x['body']['signature']==key.split(':',1)[1])
 def at(b,pc):return next(i for i in b['instructions']if i['pc']==pc)
 producer=body('PmCustomInjector$$ExternalSyntheticLambda0;->produce(')
 assert at(producer,6)['opcode']=='PACKED_SWITCH'
 assert next(e for e in at(producer,378)['switchElements']if e['key']==1)['offsetFromReferringSwitchPc']+6==349
 assert 'HandlerThread;'in at(producer,349)['reference'] and '->start()V'in at(producer,357)['reference']
 assert 'getThreadHandler()'in at(producer,360)['reference']
 assert not any('PackageManagerService' in i.get('reference','')for i in producer['instructions']if 349<=i['pc']<=364)
 injector=body('PmCustomInjector;-><init>(Lcom/android/server/pm/PackageManagerServiceInjector;')
 assert at(injector,106)['literal']==1 and at(injector,149)['registers']==[11,9]
 assert 'mUserManagerHandlerProducer'in at(injector,155)['reference']
 # The existing LSS run is separate from the registry proofs selected above.
 maintenance=next(q for q in queries if q['label']=='maintenance-registration');r=json.loads((ROOT/maintenance['receipt']).read_text())
 m=next(x['body']for x in map(json.loads,(ROOT/r['raw']).read_text().splitlines())if x.get('record')=='method')
 assert at(m,49)['literal']==77 and at(m,51)['targetPc']==63 and at(m,62)['targetPc']==83
 assert 'addMaintenanceModeLifecycleListener'in at(m,74)['reference']
 throw=body('Uri$$ExternalSyntheticBUOutline0;->m$6(')
 assert 'SecurityException'in at(throw,0)['reference'] and at(throw,5)['opcode']=='THROW'
 sourcepins={side:{'path':str((ROOT.parent/path).resolve()),'sha256':pin} for side,(path,pin)in ARCHIVES.items()}
 for p in sourcepins.values():assert sha(p['path'])==p['sha256']
 localnames=['getMainUserId()I','getProfileParentId(I)I','getUserInfo(I)Landroid/content/pm/UserInfo;','getUserProperties(I)Landroid/content/pm/UserProperties;','isMainUserPermanentAdmin()Z','isUserRunning(I)Z','isUserUnlockingOrUnlocked(I)Z','setUserState(II)V','removeUserState(I)V','addMaintenanceModeLifecycleListener(Lcom/android/server/locksettings/LockSettingsService$1;)V','addUserLifecycleListener(Lcom/android/server/pm/UserManagerInternal$UserLifecycleListener;)V']
 localkeys=['samsung-services:Lcom/android/server/pm/UserManagerService$LocalService;->'+n for n in localnames]
 localkeys+=['samsung-services:Lcom/android/server/supervision/SupervisionService$SupervisionManagerInternalImpl;->isEscrowTokenRequired(I)Z']
 assert all(k in proofs for k in localkeys)
 value={'schema':'authority-bootstrap-users/v1','status':'BLOCKED_REAL_OWNER_NOT_ESTABLISHED','evidenceKind':'static captured source and exact instruction-edge validation','androidExecuted':False,'oemExecuted':False,'privateUserStateRead':False,'constructionOrAdapterImplemented':False,
 'scope':{'localMethods':localkeys,'noWholePmsOrAmNecessityClaim':True,'unsupportedSurfaceMustBeRefusedBeforeSideEffects':['arbitrary UMS creation/removal','unowned maintenance lifecycle','unowned ASEC lifecycle']},
 'decisions':{'unchangedContextOnlyUms':'rejected: delegated constructor reads null PMS','handlerRetarget':'source-supported candidate: owned original HandlerThread/UserManagerHandler Looper; no artifact','registryAuthority':'unresolved: exact sole writer/mount/generation, defaults and load/recovery effects must precede cleanup','lifecycle':'unresolved: genuine active guest state transport may avoid full Samsung AM, requires authenticated original user/serial/profile/CE mapping and ordered lifetime','supervision':'original loaded settings, UMI lifecycle and RoleManager producer required; empty/defaultfalse not authority'},
 'sourceAssertions':{'handlerFactoryClassId':1,'handlerSwitchPc':6,'handlerBranchStartPc':349,'handlerStartPc':357,'handlerReturnPc':364,'handlerBranchReadsPmsOrInjector':False,'maintenanceRegistrationOnlyActualUser':77,'propertyMissingDefaultThrowsSecurityException':True,'pmsFieldDirectReferenceCount':25,'noTransitivePmsFreeClaim':True,'sourceBranchAssertionsPassed':True},
 'pmsFieldReferences':[{'caller':x['caller'],'pc':x['instruction']['pc'],'logicalHeaderOffset':x['logicalHeaderOffset']}for x in fieldrefs],
 'archivePins':sourcepins,'reusedInventory':{'path':'inventory/security-user-binding.json','sha256':sha(BASE)},'queries':queries,'methodProofs':proofs,'receiptPins':receipts,'rawPins':rawpins,
 'authoredPins':{p:sha(ROOT/p)for p in ['GOAL.md','docs/authority-bootstrap-users.md','tools/audit_authority_bootstrap_users.py','tools/static_security_reader.py','tools/SecurityDexReader.java']},
 'unresolvedBeforeCleanup':['sole genuine registry owner and admitted actual source generation','real Samsung type-default/resource policy','source-preserving registry initialization/recovery ownership','complete original UserInfo attributes and serial/profile mapping','active lifecycle plus native CE state and snapshot/update barrier','supervision role/DPM producers and drain','original UMI class-key publication and unsupported operation admission'],
 'limits':['No OEM initialization, Binder/ART/native/phone test','Captured archives do not establish installed guest identity','Current lifecycle transport and handler retarget are proposals, not authority implementations','Direct field-reference absence does not establish a transitive dependency-free graph']}
 out=ROOT/'inventory/authority-bootstrap-users.json';out.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'status':value['status'],'localMethods':len(localkeys),'selectedMethodEvidence':len(proofs),'newQueries':len(queries),'report':str(out),'sha256':sha(out)}))


def capture():
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 WORK.mkdir(parents=True,exist_ok=True);save=WORK/'queries.json'
 queries=json.loads(save.read_text()) if save.exists() else []
 def query(side,cls,methods,label):
  old=next((q for q in queries if q['side']==side and q['label']==label),None)
  if old:return json.loads((ROOT/old['receipt']).read_text())
  archive,pin=ARCHIVES[side]
  r=read(ROOT.parent/archive,pin,class_name=cls,methods=methods,stream='authority-bootstrap-users')
  queries.append({'side':side,'class':cls,'label':label,'receipt':r['receipt']})
  save.write_text(json.dumps(queries,indent=2)+'\n');print(side,label,r['receipt'],flush=True);return r
 query('samsung-services','com.android.server.pm.UserManagerService',
       ['getUserDataLU(I)Lcom/android/server/pm/UserManagerService$UserData;',
        'getUserInfoLU(I)Landroid/content/pm/UserInfo;',
        'getUserListFile(Ljava/io/File;)Lcom/android/server/pm/ResilientAtomicFile;',
        'upgradeIfNecessaryLP(II)V','addUserInfoFlags(Landroid/content/pm/UserInfo;)V'],'registry-leaves')
 query('samsung-services','com.android.server.pm.ResilientAtomicFile',
       ['openRead()Ljava/io/FileInputStream;','failRead(Ljava/io/FileInputStream;Ljava/lang/Exception;)V'],'atomic-read-effects')
 query('samsung-services','com.android.server.locksettings.LockSettingsService$2',['run()V'],'maintenance-registration')
 declaration=query('samsung-services','com.android.server.supervision.SupervisionService',[],'supervision-declaration')
 query('samsung-services','com.android.server.supervision.SupervisionService',['<init>(Lcom/android/server/supervision/SupervisionService$Injector;)V'],'supervision-producer')
 declaration=query('samsung-services','com.android.server.supervision.SupervisionService$Lifecycle',[],'supervision-lifecycle-declaration')
 selected=[m['signature'] for m in declaration['selectedClassDeclarations'][0]['methods'] if m['signature'].startswith(('<init>(', 'onStart('))]
 query('samsung-services','com.android.server.supervision.SupervisionService$Lifecycle',selected,'supervision-lifecycle')
 for side in ('samsung-services','coloros-services'):
  declaration=query(side,'com.android.server.am.UserController',[],'lifecycle-declaration')
  selected=[m['signature'] for m in declaration['selectedClassDeclarations'][0]['methods'] if m['signature'].startswith(('finishUserBoot(','finishUserStopped('))]
  assert 2<=len(selected)<=4
  query(side,'com.android.server.am.UserController',selected,'lifecycle-producers')
 for cls,label in [('com.samsung.android.server.pm.lifecycle.PmCustomInjector','handler-injector'),('com.samsung.android.server.pm.lifecycle.PmCustomInjector$Singleton','handler-singleton'),('com.android.server.pm.UserManagerService$MainHandler','handler-owned'),('com.android.server.pm.UserManagerService$LifeCycle','ums-lifecycle')]:
  d=query('samsung-services',cls,[],label+'-declaration')
  selected=[m['signature'] for m in d['selectedClassDeclarations'][0]['methods'] if m['signature'].startswith(('<init>(', 'get(', 'onBootPhase(', 'onUserStarting(', 'onUserSwitching(', 'onUserUnlocked('))]
  query('samsung-services',cls,selected,label)
 query('samsung-services','com.android.server.pm.UserManagerService$LocalService',['addUserLifecycleListener(Lcom/android/server/pm/UserManagerInternal$UserLifecycleListener;)V'],'supervision-user-listener')
 query('samsung-services','com.android.server.supervision.SupervisionSettings',['parseUserData(Lcom/android/modules/utils/TypedXmlPullParser;)V'],'supervision-load-parser')
 query('samsung-services','com.samsung.android.server.pm.lifecycle.PmCustomInjector$$ExternalSyntheticLambda0',['produce(Lcom/android/server/pm/PackageManagerServiceInjector;Lcom/android/server/pm/PackageManagerService;)Ljava/lang/Object;'],'handler-producer')
 query('samsung-services','com.android.server.pm.UserManagerService',['cleanUpMaintenanceModeUserDebris(Lcom/android/server/pm/UserManagerService$UserData;)V'],'maintenance-cleanup')
 query('samsung-framework','android.content.pm.UserProperties',['isPresent(J)Z'],'property-presence')
 query('samsung-framework','android.net.Uri$$ExternalSyntheticBUOutline0',['m$6(Ljava/lang/String;)V'],'property-permission-throw')


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture',action='store_true');parser.add_argument('--report',action='store_true')
 args=parser.parse_args()
 if args.capture:capture()
 if args.report:report()


if __name__=='__main__':main()
