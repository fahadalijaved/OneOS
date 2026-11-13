"""Bounded captured boot-framework/ART loading feasibility metadata.

No OEM/native execution, class loading, phone operations or global edits.
--extract reads only eight named regular members from the existing local tar;
default verifies existing captures, class ownership, source and primary refs.
"""
import argparse,gzip,hashlib,json,re,tarfile,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;OUT=ROOT/'out/authority-boot-framework';RAW=ROOT/'firmware/authority-boot-framework'
DIFF=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
MANIFEST=DIFF/'samsung-manifest.jsonl.gz';MANIFEST_SHA='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
FRAME='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
EXTRACT=['system/framework/arm64/boot.art','system/framework/arm64/boot.oat','system/framework/boot.vdex','system/framework/arm64/boot-framework.art','system/framework/arm64/boot-framework.oat','system/framework/boot-framework.vdex','system/etc/classpaths/bootclasspath.pb','system/etc/classpaths/systemserverclasspath.pb']
CTX='Landroid/app/ContextImpl;';TARGET='createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
def manifest():
 if sha(MANIFEST)!=MANIFEST_SHA:raise ValueError('Strict manifest drift')
 with gzip.open(MANIFEST,'rt',encoding='utf8')as f:return {r['path']:r for line in f if(r:=json.loads(line))['path']in EXTRACT+['system/framework/framework.jar','system/bin/app_process64','apex/com.android.art/lib64/libart.so','apex/com.android.art/bin/dex2oat64','system/bin/dex2oat64','system/framework/arm64/boot-framework.vdex','system/framework/arm64/boot.vdex']or(r['path'].startswith('apex/com.android.art/')and r['path'].endswith('.jar'))}
def extract():
 rows=manifest();proof=[]
 if TAR.stat().st_size!=20434769920:raise ValueError('Captured tar extent')
 wanted=set(EXTRACT)
 for name in list(wanted):
  p=RAW/'captured'/name
  if p.exists():
   if sha(p)!=rows[name]['sha256']:raise ValueError('Cached artifact drift')
   wanted.remove(name)
 if wanted:
  with tarfile.open(TAR,'r:')as tar:
   for member in tar:
    name=member.name.removeprefix('./')
    if name not in wanted:continue
    row=rows[name]
    if not member.isfile()or row['kind']!='file'or member.size!=row['size']or member.size>16*1024*1024:raise ValueError('Bounded regular member identity')
    data=tar.extractfile(member).read(member.size+1)
    if len(data)!=member.size or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Member content pin')
    p=RAW/'captured'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    proof.append({'member':name,'headerOffset':member.offset,'dataOffset':member.offset_data,'bytes':member.size,'sha256':row['sha256']});wanted.remove(name)
    if not wanted:break
 if wanted:raise ValueError('Required artifact missing')
 if proof:save(OUT/'artifact-acquisition.json',{'sourceTar':str(TAR),'tarBytes':TAR.stat().st_size,'priorStrictReceipt':str(DIFF/'report.json'),'priorStrictReceiptSha256':sha(DIFF/'report.json'),'fullTarRehashedThisRun':False,'scope':'Only named regular members extracted; earlier full strict framing/hash evidence reused','members':proof})
def main():
 rows=manifest();base=load(PARENT/'out/os-comparison-resumed/samsung-inventory.json');meta={}
 for key in ['bootclasspath','systemserverclasspath','mountinfo','apex-info']:
  r=base['queries'][key];p=PARENT/r['file']
  if sha(p)!=r['sha256']:raise ValueError('Captured metadata drift')
  meta[key]={'path':str(p),'sha256':r['sha256']}
 bcp=(PARENT/base['queries']['bootclasspath']['file']).read_text().strip().split(':');sscp=(PARENT/base['queries']['systemserverclasspath']['file']).read_text().strip().split(':')
 assert bcp.index('/system/framework/framework.jar')==5 and '/system/framework/services.jar'not in bcp
 assert '/system/framework/services.jar'in sscp
 artifacts=[]
 for name,row in rows.items():
  record={'capturedPath':'/'+name,'kind':row['kind'],'bytes':row['size'],'sha256':row.get('sha256'),'linkTarget':row.get('linkTarget',row.get('linkname'))}
  if name in EXTRACT:
   p=RAW/'captured'/name
   if not p.exists()or sha(p)!=row['sha256']:raise ValueError('Run --extract once for bounded image evidence')
   data=p.read_bytes();record.update(localPath=p.relative_to(ROOT).as_posix(),prefixHex=data[:16].hex(),prefixAscii=''.join(chr(x)if 32<=x<127 else'.'for x in data[:16]))
   if name.endswith('.oat'):
    offset=data.find(b'oat\n');record['oatMagicByteOffset']=offset;record['oatVersionBytes']=None if offset<0 else data[offset+4:offset+8].hex()
   record['headerInterpretation']='Magic bytes only; Samsung image/oat/vdex internals and selected runtime mapping not decoded'
  artifacts.append(record)
 assert rows['system/framework/framework.jar']['sha256']==FRAME
 if sha(PARENT/'firmware/samsung/framework.jar')!=FRAME:raise ValueError('Framework source drift')
 index_summary=load(PARENT/'out/os-comparison-resumed/archive-index/comparisons/framework/summary.json')['samsung'];index=PARENT/index_summary['declarations']
 if sha(index)!=index_summary['declarationsSha256']:raise ValueError('Class owner index drift')
 wanted={CTX,'Landroid/app/ResourcesManager;','Landroid/app/ActivityThread;','Landroid/util/DisplayMetrics;','Landroid/content/res/Resources;'};owners=[]
 with gzip.open(index,'rt',encoding='utf8')as f:
  for line in f:
   r=json.loads(line)
   if r.get('record')=='class'and r['descriptor']in wanted:owners.append({k:r[k]for k in ['descriptor','physicalDex','logicalHeaderOffset','superclass','accessFlags']})
 assert {r['descriptor']for r in owners}==wanted
 context_proof=None;inherited={}
 for name in ['authority-bootstrap-runtime','context-display-contract']:
  p=ROOT/('inventory/'+name+'.json');j=load(p);inherited[p.relative_to(ROOT).as_posix()]=sha(p)
  for r in j['methodEvidence']:
   if r.get('archiveSha256')!=FRAME or not any(x.get('signature')==TARGET for x in r.get('methods',r.get('selectedMethodProofs',[]))):continue
   if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Context raw drift')
   for line in(ROOT/r['raw']).read_text().splitlines():
    m=json.loads(line)
    if m.get('record')=='method'and m['body']['owner']==CTX and m['body']['signature']==TARGET:
     ins=next(i for i in m['body']['instructions']if i['pc']==0x26)
     assert ins['opcode']=='INVOKE_VIRTUAL'and ins['codeUnits']==3 and ins['reference']=='Landroid/app/ResourcesManager;->getDisplayMetrics()Landroid/util/DisplayMetrics;'
     context_proof={'owner':CTX,'signature':TARGET,'physicalDex':m['physicalDex'],'logicalHeaderOffset':m['logicalHeaderOffset'],'sourceBodySha256':m['normalizedBodySha256'],'raw':r['raw'],'rawSha256':r['rawSha256'],'pc':38,'opcode':ins['opcode'],'codeUnits':3,'reference':ins['reference']}
 if context_proof is None:raise ValueError('Pinned existing context proof selector not found')
 native=load(ROOT/'inventory/authority-bootstrap-runtime.json')['nativeEvidence'];native_edges=[]
 for role,row in native.items():
  if sha(ROOT/row['raw'])!=row['rawSha256']:raise ValueError('Native source proof drift')
  native_edges.extend({'binary':role,**r}for r in row['resolvedDirectCalls']if any(s in r['symbol']for s in ['AndroidRuntime9addOption','AndroidRuntime5start','AndroidRuntime7startVm','AndroidRuntime8startReg','ProcessState15startThreadPool']))
 runtime=PARENT/'firmware/samsung/runtime-20261104/libandroid_runtime.so';runtime_data=runtime.read_bytes()
 if hashlib.sha256(runtime_data).hexdigest()!='f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d':raise ValueError('Captured runtime binary drift')
 strings=[{'token':s,'byteOffset':runtime_data.find(s.encode())}for s in ['-Xforcejitzygote','-Ximage:','dalvik.vm.boot-image','dalvik.vm.extra-opts']]
 aosp=load(OUT/'aosp-inputs.json')
 for r in aosp:
  if sha(ROOT/r['path'])!=r['sha256']:raise ValueError('Primary source drift')
 primary=[]
 anchor_specs={'cmds/app_process/app_main.cpp':[(215,250,'runtime.addOption'),(330,339,'RuntimeInit')],'core/jni/AndroidRuntime.cpp':[(745,763,'dalvik.vm.boot-image'),(1021,1026,'dalvik.vm.extra-opts')],'runtime/parsed_options.cc':[(110,127,'-Xbootclasspath:_'),(174,191,'-Ximage:_'),(320,325,'-Xnoimage-dex2oat'),(688,711,'getenv("BOOTCLASSPATH")'),(747,782,'GetDefaultBootImageLocation')],'runtime/class_linker.cc':[(3308,3327,'boot_class_path_'),(10184,10211,'referrer->GetClassLoader()')],'runtime/gc/space/image_space.cc':[(2112,2142,'allow_in_memory_compilation'),(2161,2175,'should_compile_extension'),(2934,2974,'VerifyBootClassPathChecksums'),(3600,3616,'runtime boot class path')]}
 for r in aosp:
  lines=(ROOT/r['path']).read_text().splitlines()
  for a,b,token in anchor_specs[r['sourceRelativePath']]:
   text='\n'.join(lines[a-1:b]);assert token in text
   primary.append({'file':r['sourceRelativePath'],'commit':r['commit'],'firstLine':a,'lastLine':b,'sliceSha256':hashlib.sha256(text.encode()).hexdigest(),'sourceUrl':r['url'],'classification':'Primary AOSP mechanism only; Samsung matching implementation/option order not proved'})
 gpath=ROOT/'inventory/authority-bootstrap-handoff.json';inherited[gpath.relative_to(ROOT).as_posix()]=sha(gpath)
 report={'schema':'authority-boot-framework-source-plan/v1','status':'BOUNDED_LOADING_FEASIBILITY_ONLY; no boot retarget/helper or selected VM option set implemented','captureMetadata':meta,'manifest':str(MANIFEST),'manifestSha256':MANIFEST_SHA,'bootClassPath':bcp,'systemServerClassPath':sscp,'frameworkBootEntryIndex':5,'classOwners':owners,'classOwnerIndexSha256':index_summary['declarationsSha256'],'capturedArtifacts':artifacts,'contextCallsite':context_proof,'proposedHelperSeam':{'status':'proposal only; no named helper definition/leaf emitted','parameterDescriptor':'Landroid/app/ResourcesManager;','returnDescriptor':'Landroid/util/DisplayMetrics;','requiredVisibility':'Same actual boot class-loader realm as selected ContextImpl; application/SYSTEMSERVER classpath alone insufficient'},'capturedNativeCallEdges':native_edges,'capturedRuntimeStringPresence':strings,'stringLimits':'Byte-string presence is not selected runtime option/branch or parser acceptance proof','aospSources':aosp,'aospMechanismAnchors':primary,'inheritedInventories':inherited,'loadingOptions':[
  {'id':'coherent-process-local-boot-cohort','classification':'source-supported mechanism candidate, not implemented','requirements':'Before fresh VM creation, select patched framework in its real BCP slot and boot-visible helper plus complete dependency closure in same JAR or explicit BCP cohort; select coherent rebuilt images or prove non-stale DEX fallback for captured ART. An app-only producer needs a separately admitted boot-visible interface/registration/lifetime route. Preserve all canonical framework/native identities and exact source profile.'},
  {'id':'explicit-cold-dex-or-core-image-prefix','classification':'AOSP mechanism candidate; Samsung startVm option interactions unproved','requirements':'Full explicit BCP and deliberately verified image policy can avoid stale framework artifacts in principle. -Xint alone does not replace selected classes; nonexistent-image/partial-image/fallback options are not a prepared launch recipe. AndroidRuntime properties/force-JIT/default/extra options must be accounted for without global edits.'},
  {'id':'app-classpath-only-or-child-shadow','classification':'insufficient for chosen boot callsite','requirements':'Main/helper visibility to app loader does not replace boot-selected ContextImpl or resolve its boot-loader static helper dependency. A different private entire framework realm is a different design, not an accepted shortcut.'}], 'requiredNextProofs':['Produce exact retarget/helper source+preservation proof before selecting any boot artifact','Captured Samsung ART image/checksum/fallback/option ordering and effective VM profile; no current dalvik.vm.boot-image or live maps observed','Boot-loader helper visibility and actual modified ContextImpl selection including dependent compiled/inlined code','Private process-only mount/source view ready BEFORE app_process VM creation; no PID1/global framework/APEX/cache edits','Separate process launch before prepare1087 from genuine display producer availability before Context construction','Native JNI/startReg/Context/policy/user/state and real quiescence/return remain separate unclosed duties'], 'oemExecuted':False,'nativeExecuted':False,'oemLoaded':False,'phoneActions':0,'globalClasspathEdits':False,'runtimeAccepted':False,'toolSha256':sha(__file__)}
 save(ROOT/'inventory/authority-boot-framework.json',report);print('verified',len(owners),'boot-owned classes,',len(EXTRACT),'bounded artifacts,',len(primary),'AOSP mechanism anchors; no loader/VM executed')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--extract',action='store_true');a=p.parse_args()
 if a.extract:extract()
 main()
