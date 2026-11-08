"""UNSELECTED cold-start-only ColorOS optional RoR/SP callback ingress removal.

Uses the literal original SystemUI APK, never another worker's output. No OEM
execution, installation, live callback teardown or Samsung runtime is implied.
"""
import hashlib,json,os,struct,subprocess,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent;PARENT=ROOT.parent
OUT=ROOT/'out/ror-leaf';RAW=ROOT/'firmware/ror-leaf'
SOURCE=PARENT/'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk'
SOURCE_SHA='0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'
MANAGER='Lcom/oplus/keyguard/security/verify/OplusKeyguardVerifyManagerExImpl;'
CALLBACK=MANAGER[:-1]+'$checkRpmbWhenReboot$1$1;'
CTOR='<init>(Landroid/content/Context;Lcom/android/internal/widget/LockPatternUtils;Landroid/app/trust/TrustManager;Lcom/oplus/systemui/keyguard/OplusKeyguardViewMediatorExImpl;Ldagger/Lazy;)V'
HELPER_SHA='9ff4731807dad9df99ba8468b17611bf21b03fd17d2db917d4ba204f67fab8a7'
from build_coloros_pin_metadata_leaf import header,seal,uleb,u16,u32,digest,sha
PLAN=[
 (MANAGER,CTOR,'825fd121b3a319240f1729619c7c30a906845b444447e6cc797148276fa1f84d',[(83,114,'NOP')]),
 (MANAGER,'init(Lcom/android/keyguard/KeyguardUpdateMonitor;)V','759b8a15db2913326f2f5e825e187ba562b239cf4c162012b7c9083919f21ffe',[(56,63,'NOP')]),
 (MANAGER,'handleSystemRebooted()V','b35e708be6a568ad71c637ed44bb3bfd50c4b0329e5e22eb7a4adee30e5201ed',[(333,336,'NOP'),(337,340,'NOP')]),
 (MANAGER,'checkRpmbWhenReboot()V','0041c6469906b6ee8bfc1c6963c1aa1f7c0de1d61bd1b3cf81f6dc1cdd424f6a',[(0,1,'RETURN_VOID')]),
 (MANAGER,'checkRpmbWhenRebootWithSP()V','06a1f66d0e7651fa95491079473c6752f465d1a3ce4407dcad6253ba92c6dba3',[(0,1,'RETURN_VOID')]),
 (MANAGER,'access$checkFromLockPatternChecker('+MANAGER+'Ljava/lang/String;)V','f61b7d1b4094f56036cfb8ceac3d0c64f2dcd3671565fc0cc5af9a8d847d7e11',[(0,2,'RETURN_VOID')]),
 (MANAGER,'access$checkFormSyntheticPasswordManager('+MANAGER+'[B)V','b70a46dcf9c69d174c64c3a49efb2ae92accda2d31f493b09d992f398cc56fa7',[(0,2,'RETURN_VOID')]),
 (CALLBACK,'onChecked(Ljava/lang/String;Z)V','85de3fc007655418f408a5f6dbf68ede2ab5fbafabf5b4dc3d106e496eae9fcd',[(0,2,'RETURN_VOID')]),
 (CALLBACK,'onChecked(Z[B)V','7f7dc640dfafa02b87e3bb6b88950974a0b8cb3312058739be23f7c06c1119b8',[(0,2,'RETURN_VOID')]),
]

def dump(p,obj):Path(p).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf8')
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def code_locations(b):
 header(b);strings=u32(b,60);types=u32(b,68);protos=u32(b,76);ids=u32(b,92);classdefs=u32(b,100)
 def st(ix):
  if ix>=u32(b,56):raise ValueError('String index')
  pos=u32(b,strings+4*ix);_,pos=uleb(b,pos);end=b.find(b'\0',pos,min(len(b),pos+1048576))
  if end<0:raise ValueError('String bounds')
  return b[pos:end]
 def typ(ix):
  if ix>=u32(b,64):raise ValueError('Type index')
  return st(u32(b,types+4*ix))
 def sig(ix):
  owner,proto,name=struct.unpack_from('<HHI',b,ids+8*ix)
  if proto>=u32(b,72):raise ValueError('Proto index')
  ret,params=u32(b,protos+12*proto+4),u32(b,protos+12*proto+8);args=[]
  if params:
   count=u32(b,params)
   if count>65535 or params+4+2*count>len(b):raise ValueError('Parameter bounds')
   args=[typ(u16(b,params+4+2*j))for j in range(count)]
  return typ(owner).decode('ascii'),(st(name)+b'('+b''.join(args)+b')'+typ(ret)).decode('ascii')
 targets={(o,s)for o,s,_,_ in PLAN};found={};ranges=[]
 for ci in range(u32(b,96)):
  p=classdefs+32*ci;owner=u32(b,p);data=u32(b,p+24)
  if not data:continue
  p=data;counts=[]
  for _ in range(4):v,p=uleb(b,p);counts.append(v)
  if sum(counts)>2000000:raise ValueError('Member bound')
  for count in counts[:2]:
   ix=0
   for _ in range(count):delta,p=uleb(b,p);ix+=delta;_,p=uleb(b,p)
  for count in counts[2:]:
   ix=0
   for _ in range(count):
    delta,p=uleb(b,p);ix+=delta;flags,p=uleb(b,p);code,p=uleb(b,p)
    if ix>=u32(b,88)or u16(b,ids+8*ix)!=owner:raise ValueError('Encoded method identity')
    if not code:continue
    if code%4 or code+16>len(b):raise ValueError('Code header bounds/alignment')
    size=u32(b,code+12);start=code+16;end=start+2*size
    if size>10000000 or end>len(b):raise ValueError('Code instruction bounds')
    ranges.append({'methodId':ix,'start':start,'end':end})
    if typ(owner)in {MANAGER.encode(),CALLBACK.encode()}:
     key=sig(ix)
     if key in targets:
      if key in found:raise ValueError('Duplicate target definition')
      found[key]={'methodId':ix,'codeOffset':code,'instructionsOffset':start,'instructionUnits':size,'registers':u16(b,code),'incomingWords':u16(b,code+2),'tryItems':u16(b,code+6),'accessFlags':flags}
 return found,ranges

def read_actual(archive,owner,label):
 from static_security_reader import _classes,_env,JDK,DEXLIB
 cache,pins=_classes();raw=RAW/(label+'.jsonl');err=OUT/(label+'.stderr.txt')
 cmd=[JDK/'java.exe','-Xmx2g','-Duser.home='+str(OUT/'runtime-home'),'-Djava.io.tmpdir='+str(OUT/'tmp'),'-cp',str(cache)+os.pathsep+str(DEXLIB),'SecurityDexReader',archive,owner,'-','--ALL-DECLARED-METHODS--']
 with raw.open('wb')as output,err.open('wb')as errors:r=subprocess.run(list(map(str,cmd)),stdout=output,stderr=errors,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
 if r.returncode or raw.stat().st_size>32*1024*1024:raise ValueError('Actual static reader failed '+label)
 rows=[json.loads(l)for l in raw.read_text(encoding='utf8').splitlines()];summary=next((r for r in rows if r['record']=='summary'),None)
 if summary is None:raise ValueError('Missing final summary')
 return rows,{'raw':raw.relative_to(ROOT).as_posix(),'rawSha256':digest(raw),'archiveSha256':digest(archive),'readerExitCode':r.returncode,'tools':pins,'summary':summary,'dex':[r for r in rows if r['record']=='dex']}

def verify_slice(row,first,end,kind):
 b=row['body'];ins=b['instructions'];points={i['pc']for i in ins};size=sum(i['codeUnits']for i in ins)
 if first not in points or end not in points|{size}or first>=end:raise ValueError('Patch boundaries not aligned')
 selected=[i for i in ins if first<=i['pc']<end]
 if sum(i['codeUnits']for i in selected)!=end-first:raise ValueError('Incomplete instruction slice')
 if any('PAYLOAD'in i['opcode']for i in selected):raise ValueError('Payload in patch')
 for i in ins:
  if 'targetPc'in i:
   if first<i['targetPc']<end:raise ValueError('Interior branch entry')
   if i['targetPc']not in points:raise ValueError('Original branch boundary')
 for c in b['catches']:
  if first<=c['handlerPc']<end:raise ValueError('Handler in patch')
  if c['startPc']not in points or c['startPc']+c['codeUnits']not in points|{size}or c['handlerPc']not in points:raise ValueError('Try/catch alignment')
 if kind=='RETURN_VOID'and(first!=0 or b['signature'].split(')',1)[1]!='V'):raise ValueError('Optional void entry required')
 return selected

def frontier_proof(frontend, source_rows):
 r=load(OUT/'manager-source-xref.json')
 if digest(ROOT/r['raw'])!=r['rawSha256']or r['archiveSha256']!=SOURCE_SHA:raise ValueError('Frontier receipt drift')
 xs=[x for x in (json.loads(l)for l in (ROOT/r['raw']).read_text(encoding='utf8').splitlines())if x['record']=='reference']
 fields={k:[]for k in ['keyStoreManager','passwordChangedCallback','syntheticPasswordManager']}
 for x in xs:
  ref=x['instruction']['reference']
  for field in fields:
   if ref.startswith(MANAGER+'->'+field+':'):fields[field].append({'caller':x['caller'],'pc':x['instruction']['pc'],'opcode':x['instruction']['opcode']})
 expected={'keyStoreManager':[(CTOR,98),('access$checkFormSyntheticPasswordManager('+MANAGER+'[B)V',71)],'passwordChangedCallback':[(CTOR,105),('init(Lcom/android/keyguard/KeyguardUpdateMonitor;)V',58)],'syntheticPasswordManager':[(CTOR,112),('access$getSyntheticPasswordManager$p('+MANAGER+')Lcom/oplus/os/OplusSyntheticPasswordManager;',0),('init(Lcom/android/keyguard/KeyguardUpdateMonitor;)V',56)]}
 for field,pairs in expected.items():
  actual={(x['caller'],x['pc'])for x in fields[field]}
  if actual!={(MANAGER+'->'+s,pc)for s,pc in pairs}:raise ValueError('Optional field frontier changed '+field)
 getter=MANAGER+'->access$getSyntheticPasswordManager$p('+MANAGER+')Lcom/oplus/os/OplusSyntheticPasswordManager;'
 getter_callers=[x for x in xs if x['instruction']['reference']==getter]
 expected_caller=MANAGER[:-1]+'$checkFormSyntheticPasswordManager$3;->run()V'
 if len(getter_callers)!=1 or getter_callers[0]['caller']!=expected_caller:raise ValueError('Synthetic manager accessor frontier changed')
 nested = MANAGER[:-1]+'$checkFormSyntheticPasswordManager$3;'
 nr = load(OUT/'sp-runnable-source-xref.json')
 if digest(ROOT/nr['raw']) != nr['rawSha256'] or nr['archiveSha256'] != SOURCE_SHA:
  raise ValueError('Nested Runnable frontier receipt drift')
 nx = [x for x in (json.loads(l) for l in (ROOT/nr['raw']).read_text(encoding='utf8').splitlines()) if x['record']=='reference']
 allocators = [x for x in nx if x['instruction']['opcode']=='NEW_INSTANCE']
 guard_sig = 'access$checkFormSyntheticPasswordManager('+MANAGER+'[B)V'
 if len(allocators)!=1 or allocators[0]['caller']!=MANAGER+'->'+guard_sig or allocators[0]['instruction']['pc']!=197:
  raise ValueError('Non-guarded or changed nested Runnable allocation frontier')
 nested_constructors = [x for x in nx if x['instruction'].get('reference','').startswith(nested+'-><init>(')]
 if nested_constructors:
  raise ValueError('Unexpected separately referenced nested Runnable constructor')
 guarded = source_rows[(MANAGER,guard_sig)]['body']
 ctor_call = next(i for i in guarded['instructions'] if i['pc']==199)
 if ctor_call.get('reference')!='Ljava/lang/Object;-><init>()V' or ctor_call.get('registers')!=[3]:
  raise ValueError('Original nested Runnable Object initialization differs')
 run_proof = next(q for q in frontend['proofs'] if q['key'].get('owner')==nested[1:-1].replace('/','.') and q['key'].get('methods')==['run()V'])
 if digest(ROOT/run_proof['raw'])!=run_proof['rawSha256'] or run_proof['archiveSha256']!=SOURCE_SHA:
  raise ValueError('Reused nested Runnable body drift')
 run = next(x for x in (json.loads(l) for l in (ROOT/run_proof['raw']).read_text(encoding='utf8').splitlines()) if x['record']=='method' and x['body']['signature']=='run()V')
 if run['normalizedBodySha256']!='580621f9a4a48f0bf7b2d51fb0f3b51956aa5c55df36e11d1072a8268e3a575b':
  raise ValueError('Pinned SP Runnable run differs')
 prefix_calls = [i for i in run['body']['instructions'] if i['pc']<=7 and i.get('referenceKind')=='method']
 if [(i['pc'],i['reference']) for i in prefix_calls] != [(2,MANAGER+'->access$clearPendingLockCheck('+MANAGER+')V'),(7,getter)]:
  raise ValueError('Nested Runnable pre-accessor effects differ')
 clear = source_rows[(MANAGER,'access$clearPendingLockCheck('+MANAGER+')V')]
 if clear['normalizedBodySha256']!='13583075f3230f361306d98132b8d3c11ed3483408e6f54e73021368507bb24c':
  raise ValueError('Pending-lock-check cleanup body differs')
 nested_proof = {'receipt':'out/ror-leaf/sp-runnable-source-xref.json','raw':nr['raw'],'rawSha256':nr['rawSha256'],'typeReferenceCount':len(nx),'onlyNewInstanceCaller':allocators[0]['caller'],'onlyNewInstancePc':197,'originalObjectInitPc':199,'separatelyReferencedNestedConstructors':0,'runRaw':run_proof['raw'],'runRawSha256':run_proof['rawSha256'],'runBodySha256':run['normalizedBodySha256'],'beforeAccessor':{'pc':2,'operation':'access$clearPendingLockCheck cancels and clears mPendingLockCheck'},'accessorPc':7,'clearPendingBodySha256':clear['normalizedBodySha256'],'coldOnlyQualification':'An already queued SP Runnable can cancel a pending lock check before its manager accessor; entry guards do not drain or protect such live work'}
 return {'nestedRunnableFrontier':nested_proof,'receipt':'out/ror-leaf/manager-source-xref.json','raw':r['raw'],'rawSha256':r['rawSha256'],'referenceCount':len(xs),'optionalFieldReferences':fields,'syntheticAccessorOnlyCaller':expected_caller,'deadAllocationCondition':'Exact nested-type scan pins its only NEW_INSTANCE to guarded recovery PC197; cold process/no preexisting callback/jobs remains mandatory','limits':'Direct donor archive edges only; no reflection/JNI/global hostile-process isolation claim'}

def main():
 OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True);(OUT/'tmp').mkdir(exist_ok=True)
 helper=ROOT/'tools/build_coloros_pin_metadata_leaf.py'
 if digest(helper)!=HELPER_SHA:raise ValueError('Frozen integrity helper changed')
 if digest(SOURCE)!=SOURCE_SHA:raise ValueError('Exact original APK mismatch')
 frontend=load(ROOT/'inventory/construction-frontend.json')
 source_rows={};source_reads=[]
 for owner,label in [(MANAGER,'source-manager'),(CALLBACK,'source-reboot-callback')]:
  rows,receipt=read_actual(SOURCE,owner,label);source_reads.append(receipt)
  for r in rows:
   if r['record']=='method':source_rows[(owner,r['body']['signature'])]=r
 frontier=frontier_proof(frontend,source_rows)
 with zipfile.ZipFile(SOURCE)as z:
  infos=z.infolist()
  if len(infos)>20000 or len({i.filename for i in infos})!=len(infos):raise ValueError('Entry count/duplicates')
  originals={i.filename:z.read(i)for i in infos}
  if z.testzip()is not None:raise ValueError('Source ZIP CRC')
 dex={n:b for n,b in originals.items()if n.endswith('.dex')};headers={n:header(b)for n,b in dex.items()}
 if list(dex)!=['classes.dex']+['classes'+str(i)+'.dex'for i in range(2,10)]:raise ValueError('Expected9ordinaryDEX039')
 locations={};allranges={}
 for name in ['classes3.dex','classes8.dex']:
  found,ranges=code_locations(dex[name]);locations.update({k:{'physicalDex':name,**v}for k,v in found.items()});allranges[name]=ranges
 patched={n:bytearray(b)for n,b in dex.items()if n in ['classes3.dex','classes8.dex']};patches=[];changed_methods=set()
 for owner,sig,pin,spans in PLAN:
  key=(owner,sig);row=source_rows[key]
  if row['normalizedBodySha256']!=pin:raise ValueError('Pinned source method differs '+sig)
  loc=locations[key];name=loc['physicalDex'];b=row['body']
  if row['physicalDex']!=name or row['logicalHeaderOffset']!=0 or loc['registers']!=b['registerCount']:raise ValueError('Location/decoded-body mismatch')
  for first,end,kind in spans:
   verify_slice(row,first,end,kind);start=loc['instructionsOffset']+2*first;stop=loc['instructionsOffset']+2*end
   if any(r['methodId']!=loc['methodId']and max(start,r['start'])<min(stop,r['end'])for r in allranges[name]):raise ValueError('Another method code alias/overlap')
   new=b'\0'*(stop-start)
   if kind=='RETURN_VOID':new=b'\x0e\x00'+new[2:]
   old=dex[name][start:stop];patched[name][start:stop]=new
   patches.append({'owner':owner,'method':sig,'physicalDex':name,'logicalHeaderOffset':0,'firstPc':first,'endExclusivePc':end,'kind':kind,'instructionByteStart':start,'instructionByteEndExclusive':stop,'methodInstructionByteStart':loc['instructionsOffset'],'methodInstructionByteEndExclusive':loc['instructionsOffset']+2*loc['instructionUnits'],'sourceBytesSha256':sha(old),'patchedBytesSha256':sha(new),'sourceBodySha256':pin,'codeLocation':loc})
  changed_methods.add(key)
 patched={n:seal(bytes(b))for n,b in patched.items()};dex_proofs=[]
 for name,new in patched.items():
  old=dex[name];ranges=[p for p in patches if p['physicalDex']==name]
  allowed=set(range(8,32))
  for p in ranges:allowed.update(range(p['instructionByteStart'],p['instructionByteEndExclusive']))
  if len(new)!=len(old)or any(i not in allowed for i,(a,b)in enumerate(zip(old,new))if a!=b):raise ValueError('Unexpected changed bytes')
  inverse=bytearray(new)
  for p in ranges:
   a,c=p['instructionByteStart'],p['instructionByteEndExclusive'];inverse[a:c]=old[a:c]
  inverse=seal(bytes(inverse))
  if inverse!=old:raise ValueError('Exact inverse mismatch')
  roundtrip=bytearray(inverse)
  for p in ranges:
   a,c=p['instructionByteStart'],p['instructionByteEndExclusive'];roundtrip[a:c]=new[a:c]
  if seal(bytes(roundtrip))!=new:raise ValueError('Exact roundtrip mismatch')
  header(new);(OUT/name).write_bytes(new);inv=OUT/(name+'.inverse.dex');inv.write_bytes(inverse)
  dex_proofs.append({'physicalDex':name,'sourceSha256':sha(old),'patchedSha256':sha(new),'inverseSha256':sha(inverse),'artifact':(OUT/name).relative_to(ROOT).as_posix(),'inverseArtifact':inv.relative_to(ROOT).as_posix(),'sourceHeader':headers[name],'patchedHeader':header(new),'exactInverse':True,'exactRoundtrip':True,'allNonPatchNonIntegrityBytesEqual':True})
 artifact=OUT/'SystemUI.ror-removal.unselected.apk'
 with zipfile.ZipFile(artifact,'w')as z:
  for info in infos:z.writestr(info,patched.get(info.filename,originals[info.filename]))
 entryproof=[]
 with zipfile.ZipFile(artifact)as z:
  if z.namelist()!=[i.filename for i in infos]or z.testzip()is not None:raise ValueError('Output ZIP inventory/CRC')
  for n,old in originals.items():
   new=z.read(n)
   if new!=patched.get(n,old):raise ValueError('Unexpected entry payload')
   if n.endswith('.dex'):header(new)
   entryproof.append({'name':n,'sourceSha256':sha(old),'patchedSha256':sha(new),'unchanged':old==new})
 dump(OUT/'entry-payload-proofs.json',entryproof)
 newrows={};newreads=[];class_checks=[]
 for owner,label in [(MANAGER,'patched-manager'),(CALLBACK,'patched-reboot-callback')]:
  rows,r=read_actual(artifact,owner,label);newreads.append(r)
  for row in rows:
   if row['record']=='method':newrows[(owner,row['body']['signature'])]=row
  olddecl=next(x for x in source_reads if x['raw'].endswith('source-manager.jsonl'if owner==MANAGER else'source-reboot-callback.jsonl'))
  if olddecl['summary']!=r['summary']:raise ValueError('Whole class/method count changed')
  class_checks.append({'owner':owner,'originalMethodCount':olddecl['summary']['selectedMethods'],'patchedMethodCount':r['summary']['selectedMethods']})
 if set(newrows)!=set(source_rows):raise ValueError('Selected method signatures changed')
 actual_changed={k for k in source_rows if source_rows[k]['normalizedBodySha256']!=newrows[k]['normalizedBodySha256']}
 if actual_changed!=changed_methods:raise ValueError('Unexpected changed method set')
 for key in changed_methods:
  old=source_rows[key]['body'];new=newrows[key]['body'];spans=next(x[3]for x in PLAN if x[0:2]==key);expected=[]
  for ins in old['instructions']:
   if not any(a<=ins['pc']<c for a,c,_ in spans):expected.append(ins)
  for a,c,kind in spans:
   expected.extend({'pc':pc,'opcode':'RETURN_VOID'if pc==a and kind=='RETURN_VOID'else'NOP','codeUnits':1}for pc in range(a,c))
  expected.sort(key=lambda x:x['pc'])
  if new['instructions']!=expected or{k:v for k,v in old.items()if k!='instructions'}!={k:v for k,v in new.items()if k!='instructions'}:raise ValueError('Nonpatch instructions/registers/tries changed')
  for patch in patches:
   if(patch['owner'],patch['method'])==key:patch['patchedBodySha256']=newrows[key]['normalizedBodySha256']
 # Preserve actual mandatory registration and success/policy methods as bytes,
 # not as fabricated return stubs. Reader decodes are additional bounded evidence.
 init=newrows[(MANAGER,'init(Lcom/android/keyguard/KeyguardUpdateMonitor;)V')]['body']
 if not any(i['pc']==35 and i.get('reference','').endswith('->registerCallback(Lcom/android/keyguard/KeyguardUpdateMonitorCallback;)V')for i in init['instructions']):raise ValueError('Mandatory KUM registration lost')
 if not any(i['pc']==53 and i.get('reference','').endswith('->post(Ljava/lang/Runnable;)Z')for i in init['instructions']):raise ValueError('Mandatory queued KUM registration lost')
 if any('registerPasswordChangedCallback('in i.get('reference','')for i in init['instructions']):raise ValueError('Optional SP registration retained')
 if digest(SOURCE)!=SOURCE_SHA or digest(helper)!=HELPER_SHA:raise ValueError('Immutable input/helper drift')
 checks={'all9InputOutputDex039IntegrityChecksPass':True,'exactEditedMethodCount':len(changed_methods),'otherSelectedMethodBodiesUnchanged':len(source_rows)-len(changed_methods),'wholeArchiveClassCountEqual':True,'allOutsideInstructionAndIntegrityHeaderBytesEqual':True,'classFieldMethodDeclarationsPreservedByUnchangedTables':True,'allOtherEntryPayloadsEqual':True,'mandatoryDirectAndQueuedKumRegistrationPreserved':True,'originalRequiredSuccessStrongAuthFirstUnlockMethodsUntouched':True,'retryHandlerIncludingMessage101Untouched':True,'allOriginalBranchTargetsAndTryHandlersOutsideEditedInstructionsPreserved':True,'noEditedInstructionAliasesAnotherMethod':True,'perDexExactInverseAndRoundtrip':True,'coldOptionalConstructorFieldFrontierPinned':True}
 receipt={'schema':'coloros-ror-removal-leaf/v1','status':'UNSELECTED_PC_ONLY_COLD_START_OPTIONAL_ROR_SP_REMOVAL','sourceArchive':str(SOURCE),'sourceArchiveSha256':SOURCE_SHA,'patchedArchive':artifact.relative_to(ROOT).as_posix(),'patchedArchiveSha256':digest(artifact),'selected':False,'coldStartOnly':True,'sourceDexVersions':{n:h['version']for n,h in headers.items()},'patches':patches,'dex':dex_proofs,'sourceReads':source_reads,'patchedReads':newreads,'classChecks':class_checks,'checks':checks,'coldOptionalAllocationFrontier':frontier,'entryPayloadProof':{'path':'out/ror-leaf/entry-payload-proofs.json','sha256':digest(OUT/'entry-payload-proofs.json'),'totalEntries':len(entryproof),'unchangedEntries':sum(p['unchanged']for p in entryproof)},'requiredSelectionConditions':['Cold fresh process only:no prior registered OPPO SP callback,no queued recovery Runnable/Handler work,no active legacyRoRjob;existing instances require actual disconnect/drain before replacement; an old SP Runnable cancels/clears pending lock-check work before its manager accessor','Samsung committed credential-change notification must invalidate genuineColorOSPINlength/type caches for the same current user/generation before consumers resume;never export or fabricateSP to retain incidental callback cache invalidation','Real current credential/StrongAuth/firstunlock/additionalfactor/readiness and source-authoritativeCE/app-key behavior must be assembled separately;unknown remains locked','Optional regular-inputRPMB/extra credential copy removal is a separate same-original disjoint leaf to be reviewed/composed byroot','Do not treat retained dead code or removed optional void work as authenticating a user or completing actual recovery'],'negativeEvidenceScope':'No malformed-byte negative fixture or runtime fault campaign is executed by this producer;positive actual-byte decoding/inverse/preservation only','limits':['APK/ZIP is reserialized;non-target entry payload equality is proved,not identicalphysicalZIP/APKsignaturebytes','NoAPK signing,ARTverification,Androidstartup,hardware,credential,callbackdrain orhotteardown acceptance','Direct source references do not certify reflection/JNI/global compromised-process isolation'],'frontendInventorySha256':digest(ROOT/'inventory/construction-frontend.json'),'integrityHelper':{'path':'tools/build_coloros_pin_metadata_leaf.py','sha256':HELPER_SHA},'producerSha256':digest(Path(__file__)),'oemCodeExecuted':False,'phoneActions':False}
 dump(OUT/'receipt.json',receipt);dump(ROOT/'inventory/coloros-ror-leaf.json',receipt)
 print(json.dumps({'status':receipt['status'],'patchedArchiveSha256':receipt['patchedArchiveSha256'],'changedMethods':len(changed_methods),'otherSelectedMethodsUnchanged':checks['otherSelectedMethodBodiesUnchanged'],'classes':newreads[0]['summary']['classDefinitions'],'checks':checks}))
if __name__=='__main__':main()
