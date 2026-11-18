"""Bounded Samsung startup/import evidence; no OEM/JNI execution or OneOS patching."""
import argparse,gzip,hashlib,json,re,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
PAIRS={name:json.loads((PARENT/('out/os-comparison-resumed/archive-index/comparisons/'+name+'/summary.json')).read_text()) for name in ['system-server-services','framework']}
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def classes(pair,side,wanted):
 source=PAIRS[pair][side];p=PARENT/source['declarations']
 if digest(p)!=source['declarationsSha256']:raise ValueError('Immutable declaration index changed')
 result={}
 with gzip.open(p,'rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line)
   if r.get('record')=='class' and r['descriptor'] in wanted:result[r['descriptor']]=r
 return result
QUERIES=[('system-server-services','samsung','com.android.server.SystemServer',['main([Ljava/lang/String;)V','startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V','startCoreServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V','startOtherServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V']),('system-server-services','samsung','com.android.server.SystemServiceManager',['startService(Ljava/lang/String;)Lcom/android/server/SystemService;','startService(Ljava/lang/Class;)Lcom/android/server/SystemService;','startService(Lcom/android/server/SystemService;)V','startServiceFromJar(Ljava/lang/String;Ljava/lang/String;)V','startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V']),('system-server-services','samsung','com.android.server.SystemService',['publishBinderService(Ljava/lang/String;Landroid/os/IBinder;ZI)V','publishLocalService(Ljava/lang/Class;Ljava/lang/Object;)V']),('framework','samsung','com.android.server.LocalServices',['addService(Ljava/lang/Class;Ljava/lang/Object;)V','getService(Ljava/lang/Class;)Ljava/lang/Object;']),('framework','samsung','com.android.internal.os.ZygoteInit',['createPathClassLoader(Ljava/lang/String;I)Ljava/lang/ClassLoader;','getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;','handleSystemServerProcess(Lcom/android/internal/os/ZygoteArguments;)Ljava/lang/Runnable;'])]
QUERIES.extend([('system-server-services','samsung','com.android.server.SystemConfig$$ExternalSyntheticOutline0',['m(Lcom/android/server/SystemServiceManager;Ljava/lang/Class;Lcom/android/server/utils/TimingsTraceAndSlog;Ljava/lang/String;)V']),('system-server-services','samsung','com.android.server.biometrics.BiometricHandlerProvider',['<clinit>()V','getBiometricCallbackHandler()Landroid/os/Handler;','getFingerprintHandler()Landroid/os/Handler;']),('framework','samsung','com.android.internal.os.SystemServerClassLoaderFactory',['getOrCreateClassLoader(Ljava/lang/String;Ljava/lang/ClassLoader;Z)Ldalvik/system/PathClassLoader;']),('framework','samsung','com.android.internal.os.ClassLoaderFactory',['createClassLoader(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;IZLjava/lang/String;)Ljava/lang/ClassLoader;'])])
def collect():
 reader=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];receipts=[]
 for pair,side,name,methods in QUERIES:
  source=PAIRS[pair][side];r=reader(PARENT/source['archive'],source['archiveSha256'],class_name=name,methods=methods,stream='startup-import');receipts.append({'pair':pair,'side':side,'class':name,'receipt':r['receipt']})
  if name=='com.android.server.SystemServer':
   late=[m['signature'] for m in r['selectedClassDeclarations'][0]['methods'] if m['signature'].startswith('$r8$lambda$ze4ydnjnwAETERPyRVm2nwHIY1Y(')]
   if len(late)!=1:raise ValueError('Exact actual late boot callback required')
   q=reader(PARENT/source['archive'],source['archiveSha256'],class_name=name,methods=late,stream='startup-import');receipts.append({'pair':pair,'side':side,'class':name,'receipt':q['receipt']})
 out=ROOT/'out/startup-import';out.mkdir(parents=True,exist_ok=True);(out/'reads.json').write_text(json.dumps(receipts,indent=2)+'\n')
def read_receipts():
 path=ROOT/'out/startup-import/reads.json';receipts=json.loads(path.read_text());bodies=[];proofs=[]
 for query in receipts:
  receipt=ROOT/query['receipt'];r=json.loads(receipt.read_text());raw=ROOT/r['raw']
  if digest(raw)!=r['rawSha256'] or digest(r['archive'])!=r['archiveSha256']:raise ValueError('Body evidence drift')
  proofs.append({'receipt':query['receipt'],'receiptSha256':digest(receipt),'raw':r['raw'],'rawSha256':r['rawSha256'],'archiveSha256':r['archiveSha256'],'physicalLogicalDex':r['physicalLogicalDex'],'selectedMethods':r['selectedMethodProofs']})
  for line in raw.read_text(encoding='utf-8').splitlines():
   row=json.loads(line)
   if row['record']=='method':bodies.append((query,row))
 return proofs,bodies
def metadata_target(pair,descriptor,indexes):
 found={side:indexes[pair][side].get(descriptor) for side in ['samsung','coloros']};a,b=found['samsung'],found['coloros'];am={m['name']+m['descriptor'] for m in a['methods']} if a else set();bm={m['name']+m['descriptor'] for m in b['methods']} if b else set()
 return {'descriptor':descriptor,'pair':pair,'samsungPresent':bool(a),'colorosPresent':bool(b),'samsungSuperclass':a['superclass'] if a else None,'colorosSuperclass':b['superclass'] if b else None,'samsungOnlyMethods':sorted(am-bm),'colorosOnlyMethods':sorted(bm-am),'sameNameDoesNotProvePolicy':True}
def analyse():
 proofs,bodies=read_receipts();edges=[];service_sites=[];phase_sites=[]
 security=re.compile(r'LockSettings|Fingerprint|Biometric|SyntheticPassword|Weaver|GateKeeper|gatekeeper|Knox|knox|Persona|DarManager|DualDar|SecureLock|StorageManager|KeyStore|keystore|LockPattern|Supervision')
 for query,row in bodies:
  body=row['body'];ins=body['instructions'];owner=body['owner'];signature=body['signature'];allrefs=[]
  for n,i in enumerate(ins):
   ref=i.get('reference','')
   if not ref:continue
   if security.search(ref) or any(k in ref for k in ['SystemServiceManager;->start','LocalServices;->','SystemServerClassLoader','ClassLoaderFactory','System;->loadLibrary','ServiceManager;->addService','ZygoteInit;->createPathClassLoader']):
    edges.append({'owner':owner,'method':signature,'pc':i['pc'],'opcode':i['opcode'],'reference':ref,'logicalHeaderOffset':row['logicalHeaderOffset']})
   if 'SystemServiceManager;->startService' in ref:
    candidates=[x.get('reference') for x in ins[max(0,n-8):n] if x.get('opcode') in ['CONST_CLASS','CONST_STRING','CONST_STRING_JUMBO']]
    if any(security.search(x or '') for x in candidates):service_sites.append({'method':signature,'pc':i['pc'],'call':ref,'nearbyLiteralReferences':candidates,'sourceFact':'literal and invoke occur in this bounded window; branch/order context remains in raw body'})
   if 'SystemServiceManager;->startBootPhase' in ref:
    literals=[{'pc':x['pc'],'literal':x['literal']} for x in ins[max(0,n-7):n] if 'literal'in x];phase_sites.append({'method':signature,'pc':i['pc'],'call':ref,'precedingLiterals':literals})
 wanted=[('system-server-services','Lcom/android/server/SystemService;'),('system-server-services','Lcom/android/server/SystemServiceManager;'),('system-server-services','Lcom/android/server/locksettings/LockSettingsService;'),('system-server-services','Lcom/android/server/locksettings/LockSettingsService$Lifecycle;'),('system-server-services','Lcom/android/server/locksettings/SyntheticPasswordManager;'),('framework','Lcom/android/server/LocalServices;'),('framework','Lcom/android/internal/widget/ILockSettings;'),('framework','Lcom/android/internal/widget/ILockSettings$Stub;'),('framework','Landroid/hardware/fingerprint/IFingerprintService;'),('framework','Landroid/hardware/fingerprint/IFingerprintService$Stub;'),('framework','Lcom/samsung/android/knox/SemPersonaManager;')]
 indexes={pair:{side:classes(pair,side,{d for p,d in wanted if p==pair}) for side in ['samsung','coloros']} for pair in PAIRS};collisions=[metadata_target(*v,indexes) for v in wanted]
 oneos=PARENT/'firmware/reference/OneOS/2a5f41043b4a69399cae058bad213cdef7408e88';facts=[]
 selectors=[('switcher/assets/oneos_switch.sh',r'^setenforce 0','switch requests global permissive SELinux'),('switcher/assets/oneos_switch.sh',r'^setprop ctl.stop zygote$','switch stops host zygote'),('switcher/assets/oneos_switch.sh',r'^kill -9 \$\(pidof system_server\)','switch kills host system_server'),('switcher/assets/oneos_switch.sh',r'^nohup .*while true.*ctl.stop zygote','persistent host zygote suppression loop'),('switcher/assets/guest_start.sh',r'^DERIVE=','guest classpaths are derived from the guest mounted APEX classpath tool'),('switcher/assets/guest_start.sh',r'^if .*DERIVE.*CLASSPATH_FILE','successful classpath derivation replaces inherited host values'),('switcher/assets/return_to_oneui.sh',r'^HOST_NAMES=','host-owned native service names have return ownership checks')]
 for rel,pattern,meaning in selectors:
  p=oneos/rel;lines=p.read_text().splitlines();hits=[n+1 for n,line in enumerate(lines) if re.search(pattern,line)]
  if len(hits)!=1:raise ValueError('OneOS source fact selector changed '+rel+' '+pattern+' '+str(hits))
  facts.append({'source':str(p.relative_to(PARENT)),'sha256':digest(p),'line':hits[0],'fact':meaning,'classification':'observed source; not installed-image/runtime verification'})
 paths={};cp=PARENT/'firmware/samsung/os-mirror-20261104/metadata'
 for name in ['bootclasspath','systemserverclasspath']:
  p=cp/(name+'.txt');paths[name]={'source':str(p.relative_to(PARENT)),'sha256':digest(p),'entries':p.read_text().strip().split(':')}
 peers={p:{'sha256':digest(ROOT/p),'classification':'peer authored static body/native/resource evidence; no runtime acceptance'} for p in ['inventory/credentials.json','inventory/fingerprint.json','inventory/storage-keys.json','inventory/resource-compat.json'] if (ROOT/p).exists()}
 report={'scope':'Actual security subsystem startup/import boundary; no architecture selected','inputs':{pair:{s:{'archive':v['archive'],'archiveSha256':v['archiveSha256'],'declarations':v['declarations'],'declarationsSha256':v['declarationsSha256']} for s,v in data.items() if s in ['samsung','coloros']} for pair,data in PAIRS.items()},'sharedReaderBodyEvidence':proofs,'peerEvidence':peers,'selectedStartupSecurityEdges':edges,'securityStartServiceWindows':service_sites,'bootPhaseCallSites':phase_sites,'boundedCanonicalClassCollisions':collisions,'capturedSamsungClasspaths':paths,'oneosSourceVersion':'0.4.55 /2a5f41043b4a69399cae058bad213cdef7408e88','oneosSourceFacts':facts,'toolSha256':digest(Path(__file__)),'oemCodeExecuted':False,'androidExecuted':False,'phoneChanged':False,'limits':['Source bodies/declarations do not prove Android startup/hardware/cryptographic behavior','Window literals are contextual evidence, not a general register/data-flow solver','Declared class presence is limited to the two pinned archives per side, not the entire mountedOS','Current OneOS source guards and switch intent are not proof of the installed patched image','Same-FQN private-service linkage requires both canonical ABI and actual LocalServices/data authority review']}
 (ROOT/'inventory').mkdir(exist_ok=True);(ROOT/'inventory/startup-import.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'selectedBodies':sum(len(p['selectedMethods']) for p in proofs),'securityEdges':len(edges),'startServiceWindows':len(service_sites),'phaseSites':len(phase_sites),'boundedClasses':len(collisions),'inventory':'inventory/startup-import.json'}))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collect',action='store_true');a=p.parse_args()
 if a.collect:collect()
 analyse()
if __name__=='__main__':main()
