"""Pin original ColorOS guest security startup sites; never execute OEM/JNI code."""
import argparse,gzip,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;WORK=ROOT/'out/construction-startup'
SOURCE='66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
FRAMEWORK='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def input_for(role):
 p=PARENT/('out/os-comparison-resumed/archive-index/comparisons/'+role+'/summary.json');s=json.loads(p.read_text())['coloros'];expected=SOURCE if role=='system-server-services' else FRAMEWORK
 if s['archiveSha256']!=expected or sha(PARENT/s['archive'])!=expected:raise ValueError('Literal original guest input required')
 return s
def selected_declarations(names):
 s=input_for('system-server-services');p=PARENT/s['declarations']
 if sha(p)!=s['declarationsSha256']:raise ValueError('Pinned guest declaration index changed')
 result={};wanted={'L'+n.replace('.','/')+';':n for n in names}
 with gzip.open(p,'rt') as f:
  for line in f:
   r=json.loads(line)
   if r.get('record')=='class' and r['descriptor'] in wanted:result[wanted[r['descriptor']]]=r
 if set(result)!=set(names):raise ValueError('Exact original guest classes missing '+str(set(names)-set(result)))
 return result
def collect():
 WORK.mkdir(parents=True,exist_ok=True);reader=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];reads=[]
 names=['com.android.server.SystemServer','com.android.server.SystemServiceManager','com.android.server.SystemService','com.android.server.biometrics.AuthService','com.android.server.biometrics.BiometricService','com.android.server.biometrics.sensors.fingerprint.FingerprintService']
 declarations=selected_declarations(names)
 plans=[]
 for name in names:
  available=[m['name']+m['descriptor'] for m in declarations[name]['methods']]
  if name.endswith('.SystemServer'):
   selected=[s for s in available if s.startswith(('main(','run(','startBootstrapServices(','startCoreServices(','startOtherServices(','lambda$startOtherServices$6(','startSystemUi('))]
  elif name.endswith('.SystemServiceManager'):
   selected=[s for s in available if s.startswith(('startService(','startBootPhase(','lambda$startBootPhase$0(','sealStartedServices('))]
  elif name.endswith('.SystemService'):selected=[s for s in available if s.startswith(('publishBinderService(','publishLocalService('))]
  else:selected=[s for s in available if s.startswith(('onStart(','onBootPhase('))]
  if not selected:raise ValueError('Required exact lifecycle selectors absent '+name)
  plans.append(('system-server-services',name,selected))
 for role,name,methods in plans:
  s=input_for(role);r=reader(PARENT/s['archive'],s['archiveSha256'],class_name=name,methods=methods,stream='construction-startup');reads.append({'role':role,'class':name,'origin':'new exact shared-reader body selection','receipt':r['receipt']})
 # Reuse the existing exact guest Lifecycle evidence, with fresh source/raw integrity checks.
 credentials=json.loads((ROOT/'inventory/credentials.json').read_text());matching={p['receipt'] for k,p in credentials['methodProofs'].items() if k.startswith('coloros:Lcom/android/server/locksettings/LockSettingsService$Lifecycle;->')}
 if len(matching)!=1:raise ValueError('One exact existing guest LockSettings Lifecycle receipt required')
 for p in matching:
  r=json.loads((ROOT/p).read_text())
  if r['archiveSha256']!=SOURCE or sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Guest Lifecycle evidence changed')
  reads.append({'role':'system-server-services','class':'com.android.server.locksettings.LockSettingsService$Lifecycle','origin':'reused exact credentials shared-reader receipt','receipt':p})
 r=reader(PARENT/input_for('system-server-services')['archive'],SOURCE,reference='Lcom/android/server/SystemServiceManager;->startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V',stream='construction-startup');reads.append({'role':'system-server-services','class':None,'origin':'whole supplied guest services archive direct boot-phase references','receipt':r['receipt']})
 s=input_for('framework');r=reader(PARENT/s['archive'],FRAMEWORK,class_name='com.android.server.LocalServices',methods=['addService(Ljava/lang/Class;Ljava/lang/Object;)V','getService(Ljava/lang/Class;)Ljava/lang/Object;'],stream='construction-startup');reads.append({'role':'framework','class':'com.android.server.LocalServices','origin':'new exact shared-reader body selection','receipt':r['receipt']})
 (WORK/'reads.json').write_text(json.dumps(reads,indent=2)+'\n');print(json.dumps({'reads':len(reads),'manifest':'out/construction-startup/reads.json'}))
def rows():
 proofs=[];bodies=[];references=[]
 for query in json.loads((WORK/'reads.json').read_text()):
  p=ROOT/query['receipt'];r=json.loads(p.read_text());raw=ROOT/r['raw']
  if r['archiveSha256'] not in [SOURCE,FRAMEWORK] or sha(raw)!=r['rawSha256'] or sha(r['archive'])!=r['archiveSha256']:raise ValueError('Guest raw/source evidence drift')
  proofs.append(dict(query,receiptSha256=sha(p),archiveSha256=r['archiveSha256'],raw=r['raw'],rawSha256=r['rawSha256'],physicalLogicalDex=r['physicalLogicalDex'],methodProofs=r['selectedMethodProofs']))
  for line in raw.read_text().splitlines():
   row=json.loads(line)
   if row['record']=='method' and (not query.get('methods') or row['body']['signature'] in query['methods']):bodies.append(row)
   elif row['record']=='reference':references.append(row)
 return proofs,bodies,references
def extend():
 reader=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];reads=json.loads((WORK/'reads.json').read_text())
 names=['com.android.server.am.ActivityManagerService','com.android.server.SystemServer$$ExternalSyntheticLambda8','com.android.server.biometrics.AuthService','com.android.server.biometrics.AuthService$Injector','com.android.server.biometrics.BiometricService$Injector','com.android.server.locksettings.LockSettingsService','com.android.server.locksettings.LockSettingsService$LocalService']
 declarations=selected_declarations(names)
 for name in names:
  available=[m['name']+m['descriptor'] for m in declarations[name]['methods']]
  if name.endswith('.ActivityManagerService'):methods=[s for s in available if s in ['finishBooting()V','systemReady(Ljava/lang/Runnable;Lcom/android/server/utils/TimingsTraceAndSlog;)V']]
  elif name.endswith('ExternalSyntheticLambda8'):methods=[s for s in available if s=='run()V']
  elif name.endswith('.AuthService'):methods=[s for s in available if s.startswith(('registerAuthenticators(','registerFingerprintSensors(','lambda$registerFingerprintSensors$1('))]
  elif name.endswith('AuthService$Injector'):methods=[s for s in available if s.startswith(('getBiometricService(','getFingerprintService(','publishBinderService('))]
  elif name.endswith('BiometricService$Injector'):methods=[s for s in available if s.startswith('publishBinderService(')]
  elif name.endswith('.LockSettingsService'):methods=[s for s in available if s.startswith(('systemReady(','onBootPhase(','onThirdPartyAppsStarted(','-$$Nest$monBootPhase('))]
  else:methods=[s for s in available if s.startswith('onThirdPartyAppsStarted(')]
  if not methods:raise ValueError('Exact reached guest methods absent '+name)
  source=input_for('system-server-services');r=reader(PARENT/source['archive'],SOURCE,class_name=name,methods=methods,stream='construction-startup');reads.append({'role':'system-server-services','class':name,'origin':'reached immediate guest startup consumer/dispatcher','methods':methods,'receipt':r['receipt']})
 # The Runnable calls this actual compiler bridge before the private boot callback.
 ss=declarations.get('com.android.server.SystemServer') or selected_declarations(['com.android.server.SystemServer'])['com.android.server.SystemServer'];methods=[m['name']+m['descriptor'] for m in ss['methods'] if m['name'].startswith('$r8$lambda$Zs26TzwLVmpFF2G8LTrYh_8ptIk')]
 if len(methods)!=1:raise ValueError('Exact compiler boot callback bridge absent')
 r=reader(PARENT/input_for('system-server-services')['archive'],SOURCE,class_name='com.android.server.SystemServer',methods=methods,stream='construction-startup');reads.append({'role':'system-server-services','class':'com.android.server.SystemServer','origin':'reached compiler boot Runnable bridge','methods':methods,'receipt':r['receipt']})
 (WORK/'reads.json').write_text(json.dumps(reads,indent=2)+'\n');print(json.dumps({'extendedReads':len(reads)}))
def analyse():
 proofs,bodies,references=rows();by={(r['body']['owner'],r['body']['signature']):r for r in bodies}
 def location(owner,method,pc,reference=None):
  row=by[(owner,method)];matches=[i for i in row['body']['instructions'] if i['pc']==pc]
  if len(matches)!=1 or reference and matches[0].get('reference')!=reference:raise ValueError('Exact guest code site changed '+owner+method+hex(pc))
  i=matches[0];return {'owner':owner,'method':method,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'codeUnitPc':pc,'hexPc':hex(pc),'opcode':i['opcode'],'reference':i.get('reference'),'registers':i.get('registers'),'registerStart':i.get('registerStart'),'registerCount':i.get('registerCount'),'normalizedBodySha256':row['normalizedBodySha256']}
 SS='Lcom/android/server/SystemServer;';OTHER='startOtherServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V';START='Lcom/android/server/SystemServiceManager;->startService(Ljava/lang/Class;)Lcom/android/server/SystemService;'
 cuts=[]
 for role,pc,call in [('lockSettings',0x6b0,0x6b2),('fingerprint',0x112d,0x112f),('biometric',0x113f,0x1141),('auth',0x114e,0x1150)]:
  target=location(SS,OTHER,pc);invoke=location(SS,OTHER,call,START)
  if target['opcode']!='CONST_CLASS' or target['registers'][0]!=invoke['registers'][1]:raise ValueError('Actual Class-to-startService argument edge changed')
  cuts.append({'role':role,'classProducer':target,'creationCall':invoke,'decision':'source replacement boundary pinned; no replacement implemented'})
 sites={label:location(SS,OTHER,pc,ref) for label,pc,ref in [
  ('lockSettingsLookup',0x6b8,'Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;'),('lockSettingsAsInterface',0x6bc,'Lcom/android/internal/widget/ILockSettings$Stub;->asInterface(Landroid/os/IBinder;)Lcom/android/internal/widget/ILockSettings;'),('lockSettingsSystemReady',0x15f9,'Lcom/android/internal/widget/ILockSettings;->systemReady()V'),('activityManagerSystemReady',0x195f,'Lcom/android/server/am/ActivityManagerService;->systemReady(Ljava/lang/Runnable;Lcom/android/server/utils/TimingsTraceAndSlog;)V'),('lockSettingsLocalLookup',0x1980,'Lcom/android/server/LocalServices;->getService(Ljava/lang/Class;)Ljava/lang/Object;'),('lockSettingsLocalAppsStarted',0x1989,'Lcom/android/server/locksettings/LockSettingsInternal;->onThirdPartyAppsStarted()V'),('startSystemUi',0x1996,'Lcom/android/server/SystemServer;->startSystemUi(Landroid/content/Context;Lcom/android/server/wm/WindowManagerService;)V')]}
 cast={label:location(SS,OTHER,pc) for label,pc in [('returnedObject',0x1132),('originalTypeCheck',0x1133),('firstFollowingOverwrite',0x1138)]}
 if cast['returnedObject']['opcode']!='MOVE_RESULT_OBJECT' or cast['originalTypeCheck']['opcode']!='CHECK_CAST' or cast['originalTypeCheck']['reference']!='Lcom/android/server/biometrics/sensors/fingerprint/FingerprintService;' or cast['firstFollowingOverwrite']['opcode']!='CONST_STRING':raise ValueError('Original FP result/cast/overwrite shape changed')
 if any(i.get('registers') and 0 in i['registers'] for i in by[(SS,OTHER)]['body']['instructions'] if 0x1135<=i['pc']<0x1138):raise ValueError('New intermediate FP result use')
 phases=[]
 for r in references:
  owner,method=r['caller'].split('->',1);row=by.get((owner,method))
  if row is None:raise ValueError('Uninspected direct boot phase caller '+r['caller'])
  ins=row['body']['instructions'];n=next(n for n,i in enumerate(ins) if i['pc']==r['instruction']['pc']);arg=ins[n]['registers'][-1] if 'registers' in ins[n] else ins[n]['registerStart']+ins[n]['registerCount']-1
  producer=next((i for i in reversed(ins[max(0,n-6):n]) if i.get('registers',[None])[0]==arg and 'literal'in i),None)
  if producer is None:raise ValueError('Unresolved phase integer at actual call')
  phases.append({'phase':producer['literal'],'literalPc':producer['pc'],'site':location(owner,method,ins[n]['pc'])})
 if sorted(p['phase'] for p in phases)!=[100,200,480,500,520,550,600,1000]:raise ValueError('Actual guest phase set changed')
 lifecycle=[];oem=[];async_sites=[]
 for row in bodies:
  b=row['body'];owner=b['owner'];method=b['signature']
  for i in b['instructions']:
   ref=i.get('reference','')
   if method.startswith(('onStart(','onBootPhase(','publishBinderService(','getFingerprintService(','getBiometricService(','onThirdPartyAppsStarted(','systemReady(')) and any(t in ref for t in ['publishBinderService','ServiceManager;->getService','LocalServices;->','ILockSettingsServiceExt;->','IFingerprintServiceExt;->','registerAuthenticators','migrateOldData','migrateUserToSp','Runnable;->run']):lifecycle.append(location(owner,method,i['pc']))
   if owner==SS and 'Lcom/android/server/ISystemServerExt;->' in ref:oem.append(location(owner,method,i['pc']))
   if owner=='Lcom/android/server/biometrics/AuthService;' and any(t in ref for t in ['Handler;->post(','IFingerprintService;->registerAuthenticators']):async_sites.append(location(owner,method,i['pc']))
 bindings=[{'contract':name,'requiredCanonicalGuestContract':True,'status':'unbound to genuine selected Samsung owner','replacement':'authored typed facade/lifecycle may replace original producer, preserving real policy and completion'} for name in ['lock_settings / ILockSettings','LockSettingsInternal','fingerprint / IFingerprintService','biometric / IBiometricService','auth / IAuthService','SystemService boot/user callbacks and LocalServices class keys']]
 report={'schema':'original-coloros-guest-startup-closure/v1','scope':'Stage1 original guest creation/phase/consumer gap; not complete authority construction','source':input_for('system-server-services'),'frameworkSource':input_for('framework'),'methodEvidence':proofs,'originalGuestCreationCuts':cuts,'immediateAndLateConsumers':sites,'fingerprintReturnedInstanceCast':cast,'bootPhaseSites':phases,'selectedLifecyclePublicationAndConsumerEdges':lifecycle,'authRegistrationAsyncSites':async_sites,'independentOemStartupSeams':oem,'requiredBindings':bindings,'optionalOppoRemovalBoundary':{'classification':'source-supported proposed cut; not implementation or blanket extension removal approval','wholeGuestSecurityProducerReplacementCutsItsOwnedLegacySubgraph':True,'preserveCanonicalContracts':True,'independentISystemServerExtImplementationsInspected':False,'blanketRemovalSafe':False,'mustPreserveRealFinishStrongAuthAndAdditionalFactorGates':True},'gapStatus':{'originalGuestCoreSitesPinned':True,'installedOneOsPatchedSitesPinned':False,'actualSamsungConstructionClosed':False,'policyReadinessImplemented':False,'safeToActivateCandidate':False},'toolSha256':sha(Path(__file__)),'recheckCommand':'python tools/audit_guest_startup.py','freshCollectionCommand':'python tools/audit_guest_startup.py --collect --extend','oemCodeExecuted':False,'androidExecuted':False,'phoneChanged':False,'oldColorGlassResumed':False,'limits':['PCs are 16-bit DEX code-unit offsets in named methods, not archive byte offsets','Exact original donor evidence is not the installed OneOS patched image or a patch authorization','Class-to-startService edges are checked; full branch dominance/SSA or every independent OEM/APEX startup is not claimed','Compiler publication delegates access$000 and the Auth handler Runnable bridge are not all followed; handler posting is not provider readiness','Source phase returns do not certify pending native/authentication/maintenance work is complete','No authorizing/ready placeholder, implementation payload or device acceptance follows']}
 (ROOT/'inventory/construction-startup.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'inventory':'inventory/construction-startup.json','originalSites':4,'phaseSites':len(phases),'selectedMethods':len(bodies),'safeToActivate':False}))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collect',action='store_true');p.add_argument('--extend',action='store_true');a=p.parse_args()
 if a.collect:collect()
 if a.extend:extend()
 proofs,bodies,refs=rows();summary={'selectedMethods':len(bodies),'bootPhaseDirectReferences':len(refs),'proofs':proofs,'oemCodeExecuted':False,'androidExecuted':False}
 (WORK/'collected.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'selectedMethods':len(bodies),'bootPhaseDirectReferences':len(refs),'collected':'out/construction-startup/collected.json'}))
 analyse()
if __name__=='__main__':main()
