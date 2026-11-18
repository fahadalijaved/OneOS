"""Bounded offline launch-owner evidence. Never runs ART/OEM/device commands."""
import argparse,gzip,hashlib,json,lzma,re,runpy,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
RAW=ROOT/'firmware/samsung-authority-vm-launch';OUT=ROOT/'out/samsung-authority-vm-launch'
MANIFEST=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
MEMBER='system/lib64/server_configurable_flags.so'
FLAG_SHA='69dde39d705ae09a98dc17e1ed77d040d85dd8400dbdb42440ff0ae81f941169'
ART=ROOT/'firmware/authority-art-option-selection/libart.so'
ART_SHA='4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa'
PINS={
 'docs/authority-boot-framework.md':'498c2fc83901a8a34d6902b7135d771f8d5e46f8a72d8a8192ff8a6472b742fc',
 'inventory/authority-boot-framework.json':'8a7b144c1c9024ffbff548568439b2e81a9c072ecd05683469a7fbc33f31f96a',
 'docs/authority-vm-options.md':'6a844f305d30877f3bae7e1fb79d04db32f84c1b2a48a5c5ae0634fffc353d18',
 'inventory/authority-vm-options.json':'ef555b5bb8b57e2323b12f63aae557c4fc5083f0271208e683ec144215df8db4',
 'docs/authority-art-option-selection.md':'3598c91fbdc33fbc4098516572aee7a5409f44660248ba4a3d501ac69cd99be8',
 'inventory/authority-art-option-selection.json':'95a29c6524c2b393b7fe89d16c34929f66d12bab3be45baae0587cdfa770d8e8',
 'firmware/authority-vm-options/selected-native.json':'dc90bc834e5af30ab05bb63e93530b4b067e6c66c68a230b271a07613768dccd',
 'firmware/authority-art-option-selection/selected-native.json':'56f6bf1b52dcd3456d76fe16a29a310c7532b5c83999cb7d7df02b3279d8e670',
 'tools/audit_security_native_linkage.py':'33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'}

def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def need(ok,message):
 if not ok:raise ValueError(message)

def capture():
 for path,pin in PINS.items():need(sha(ROOT/path)==pin,'Frozen dependency '+path)
 need(sha(MANIFEST)=='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a','Immutable file manifest')
 with gzip.open(MANIFEST,'rt')as f:row,=[r for l in f if(r:=json.loads(l))['path']==MEMBER]
 need(row['sha256']==FLAG_SHA and row['size']==36392 and row['kind']=='file','Actual exact flag backend member')
 dest=RAW/MEMBER
 if dest.exists():need(sha(dest)==FLAG_SHA,'Cached selected backend')
 else:
  need(TAR.stat().st_size==20434769920,'Prior captured tar extent')
  with tarfile.open(TAR,'r:')as tar:
   for m in tar:
    if m.name.removeprefix('./')!=MEMBER:continue
    need(m.isfile()and m.size==36392,'Bounded selected regular file');b=tar.extractfile(m).read(m.size+1);need(hashlib.sha256(b).hexdigest()==FLAG_SHA,'Exact member content')
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    save(OUT/'acquisition.json',{'sourceTar':str(TAR),'tarBytes':TAR.stat().st_size,'fullTarRehashedThisRun':False,'priorStrictManifestSha256':sha(MANIFEST),'member':MEMBER,'headerOffset':m.offset,'dataOffset':m.offset_data,'bytes':len(b),'sha256':FLAG_SHA,'oemExecuted':False});break
   else:raise ValueError('Exact local member missing')
 parser=ROOT/'tools/audit_security_native_linkage.py';parse=runpy.run_path(str(parser))['elf'];parser_pin=sha(parser)
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'));import capstone
 decoder=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);decoder.detail=True
 sources=[]
 for path,pin,selectors in [(dest,FLAG_SHA,['_ZN25server_configurable_flags25GetServerConfigurableFlagE']),(ART,ART_SHA,['_ZN3art7Runtime4InitEONS_18RuntimeArgumentMapE','_ZN3art2gc4HeapC1','_ZN3art11ClassLinker16InitWithoutImage','_ZN3art2gc5space10ImageSpace13LoadBootImageE','_ZN3artL16OpenBootDexFilesE'])]:
  need(sha(path)==pin,'Pinned selected native input');data=path.read_bytes();elf=parse(data);sections=elf['sections'];symbols=list(elf['dynamicSymbols']);debug=next((s for s in sections if s['name']=='.gnu_debugdata'),None)
  if debug:
   mini=lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']]);need(len(mini)<128*1024*1024,'Minidebug bound');symbols+=parse(mini)['dynamicSymbols']
  if path==ART:
   old=load(ROOT/'firmware/authority-art-option-selection/symbols.json');need(old['sourceSha256']==pin,'Frozen ART symbols');symbols=old['symbols']
  def offset(address,size=1):
   s,=[s for s in sections if s['type']!=8 and s['address']<=address and address+size<=s['address']+s['bytes']];return s['offset']+address-s['address']
  def string(address):
   try:
    off=offset(address);end=data.index(b'\0',off,min(len(data),off+512));b=data[off:end];return b.decode('ascii')if b and all(32<=x<127 or x in[9,10,13]for x in b)else None
   except(ValueError,UnicodeError):return None
  relocs={r['target']:r for r in elf['rela']if r['symbolIndex']}
  def call(address):
   matches=[s['name']for s in symbols if s['sectionIndex']and s['value']==address]
   if matches:return matches[0]
   plt=next((s for s in sections if s['name']=='.plt'and s['address']<=address<s['address']+s['bytes']),None)
   if not plt:return None
   ins=list(decoder.disasm(data[offset(address,min(32,plt['address']+plt['bytes']-address)):offset(address)+min(32,plt['address']+plt['bytes']-address)],address));pages={}
   for i in ins:
    if i.mnemonic=='adrp':pages[i.reg_name(i.operands[0].reg)]=i.operands[1].imm
    if i.mnemonic=='ldr'and len(i.operands)==2 and i.operands[1].type==capstone.CS_OP_MEM:
     mem=i.operands[1].mem;base=i.reg_name(mem.base)
     if base in pages and not mem.index:
      r=relocs.get(pages[base]+mem.disp)
      if r:return elf['dynamicSymbols'][r['symbolIndex']]['name']
   return None
  functions=[];seen=set()
  for s in symbols:
   if not s['sectionIndex']or s['type']!=2 or not s['size']or not any(s['name'].startswith(k)or k=='GetServerConfigurableFlag'and k in s['name']for k in selectors)or s['value']in seen:continue
   seen.add(s['value']);need(s['size']<=20000,'Bounded selected function');off=offset(s['value'],s['size']);body=data[off:off+s['size']];rows=[];pages={}
   for i in decoder.disasm(body,s['value']):
    r={'pc':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str};assigned=None
    if i.mnemonic=='adrp':assigned=(i.reg_name(i.operands[0].reg),i.operands[1].imm)
    if i.mnemonic=='add'and len(i.operands)==3 and i.operands[2].type==capstone.CS_OP_IMM:
     base=i.reg_name(i.operands[1].reg)
     if base in pages:
      address=pages[base]+(i.operands[2].imm<<i.operands[2].shift.value);assigned=(i.reg_name(i.operands[0].reg),address);value=string(address)
      if value:r['literal']=value
    if i.mnemonic=='adr':
     address=i.operands[1].imm;assigned=(i.reg_name(i.operands[0].reg),address);value=string(address)
     if value:r['literal']=value
    if i.mnemonic=='ldr'and len(i.operands)==2 and i.operands[1].type==capstone.CS_OP_MEM:
     mem=i.operands[1].mem;base=i.reg_name(mem.base)
     if base in pages and not mem.index:
      reloc=relocs.get(pages[base]+mem.disp)
      if reloc:r['gotReference']=elf['dynamicSymbols'][reloc['symbolIndex']]['name']
    if i.mnemonic in['bl','b']and i.op_str.startswith('#0x'):
     target=call(int(i.op_str[1:],16))
     if target:r['targetSymbol']=target
    for reg in i.regs_access()[1]:pages.pop(i.reg_name(reg),None)
    if i.mnemonic in['bl','blr']:
     for reg in range(19):pages.pop('x'+str(reg),None)
    if assigned:pages[assigned[0]]=assigned[1]
    rows.append(r)
   need(len(rows)*4==len(body),'Complete function decode');functions.append({'symbol':s['name'],'address':s['value'],'fileOffset':off,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'instructions':rows})
  need(len(functions)==(5 if path==ART else 1),'Exact bounded selected function set');sources.append({'path':path.relative_to(ROOT).as_posix(),'sha256':pin,'needed':elf['needed'],'functions':functions})
 need(sha(parser)==parser_pin,'Parser unchanged');save(RAW/'selected-native.json',{'schema':'samsung-authority-vm-launch-native/v1','parser':parser.relative_to(ROOT).as_posix(),'parserSha256':parser_pin,'capstoneVersion':capstone.__version__,'pcKind':'Captured ELF virtual address, not live address','sources':sources,'oemExecuted':False,'annotationLimits':'Local register-tracked literal/GOT address pairs and verified PLT calls; not emulation'})
 print(json.dumps({'raw':'firmware/samsung-authority-vm-launch/selected-native.json','functions':sum(len(s['functions'])for s in sources),'instructions':sum(len(f['instructions'])for s in sources for f in s['functions']),'oemExecuted':False}))

def audit():
 for path,pin in PINS.items():need(sha(ROOT/path)==pin,'Frozen dependency '+path)
 rawpath=RAW/'selected-native.json';raw=load(rawpath);need(sha(ROOT/raw['parser'])==raw['parserSha256'],'Actual static parser pin')
 rawpin=sha(rawpath);binarypins={};index={};functionmeta=[]
 for source in raw['sources']:
  p=ROOT/source['path'];need(sha(p)==source['sha256'],'Selected captured binary');binarypins[source['path']]=source['sha256'];data=p.read_bytes()
  for f in source['functions']:
   b=data[f['fileOffset']:f['fileOffset']+f['bytes']];need(hashlib.sha256(b).hexdigest()==f['sha256'],'Selected function bytes');need(b''.join(bytes.fromhex(i['bytes'])for i in f['instructions'])==b,'Complete native instruction bytes');need(all(i['pc']==f['address']+4*n for n,i in enumerate(f['instructions'])),'Function PC extent')
   functionmeta.append({'source':source['path'],**{k:v for k,v in f.items()if k!='instructions'}});index.update({i['pc']:i for i in f['instructions']})
 need(len(functionmeta)==6 and sum(f['bytes']for f in functionmeta)==39392,'Exact finite six-function source set')
 oldvm=load(ROOT/'firmware/authority-vm-options/selected-native.json');oldart=load(ROOT/'firmware/authority-art-option-selection/selected-native.json')
 oldindices={name:{i['pc']:i for f in r['functions']for i in f['instructions']}for name,r in [('vm',oldvm),('art',oldart)]}
 checks=[]
 def check(scope,pc,key,value,contains=False):
  row=(index if scope=='new'else oldindices[scope])[pc];actual=row.get(key)
  need((value in actual if contains else actual==value),'Source assertion '+scope+' '+hex(pc)+' '+key)
  checks.append({'source':scope,'pc':pc,'pcHex':hex(pc),'field':key,'contains'if contains else'expected':value})
 for pc,key,value in[(0x4794,'literal','persist.device_config.'),(0x47f8,'operands','w10, #0x2e'),(0x583e70,'operands','x8, x9, [x19]'),(0x583e74,'operands','x8, x9'),(0x583e78,'operands','#0x583f9c'),(0x583f9c,'operands','w20, wzr'),(0x583fa0,'operands','#0x583f60'),(0x593e9c,'operands','x9, [x8, #0x680]'),(0x593ea0,'operands','x8, [x8, #0x688]'),(0x593ea8,'operands','#0x59463c'),(0x80a8c8,'operands','#0x80bb00')]:check('new',pc,key,value)
 for pc,word in[(0x4938,'GetProperty'),(0x592250,'ReleaseOrDefault'),(0x6b04d0,'LoadBootImage'),(0x5946a8,'OpenBootDexFiles'),(0x5946d0,'InitWithoutImage'),(0x593eb4,'InitFromBootImage'),(0x603f04,'DexFileLoader4Open')]:check('new',pc,'targetSymbol',word,True)
 check('new',0x59224c,'gotReference','5ImageE',True)
 for pc,key,value in[(0x184ef0,'literal','dalvik.vm.usejit'),(0x184ef8,'literal','-Xusejit:'),(0x185570,'operands','x2, xzr'),(0x1849e0,'operands','w19, #0, #0x185bc8'),(0x1849f4,'operands','w0, #0, #0x185bc8'),(0x185f30,'operands','w21, #0x185f44')]:check('vm',pc,key,value)
 for pc,word in[(0x184f08,'parseRuntimeOption'),(0x185574,'parseExtraOpts'),(0x184a18,'parseRuntimeOption'),(0x185ba0,'JNI_CreateJavaVM')]:check('vm',pc,'targetSymbol',word,True)
 for pc,key,value in[(0x597c88,'operands','x22, x0'),(0x59835c,'operands','#0x597e2c'),(0x598364,'operands','#0x597e2c'),(0x597ca4,'operands','w0, #0, #0x598168'),(0x5981ac,'operands','#0x598460'),(0x5981b0,'operands','wzr, [sp, #0x20]'),(0x598464,'literal','-Xusejit:true and -Xint cannot be specified together\n'),(0x598540,'literal','-Ximage and -Xforcejitzygote cannot be specified together\n')]:check('art',pc,key,value)
 for pc,word in[(0x597cd8,'SetIfMissing'),(0x5981c4,'3SetIb'),(0x5982ec,'GetJitZygoteBootImageLocation')]:check('art',pc,'targetSymbol',word,True)
 boot=load(ROOT/'inventory/authority-boot-framework.json');need(sha(Path(boot['manifest']))==boot['manifestSha256'],'Captured immutable manifest');needed={p.lstrip('/')for p in boot['bootClassPath']};cohort=[]
 with gzip.open(boot['manifest'],'rt')as f:
  records={r['path']:r for line in f if(r:=json.loads(line))['path']in needed}
 for n,p in enumerate(boot['bootClassPath']):
  r=records.get(p.lstrip('/'));need(r is not None and r['kind']=='file'and bool(r.get('sha256')),'Complete exact recorded BCP member');cohort.append({'index':n,'location':p,'bytes':r['size'],'sha256':r['sha256']})
 need(len(cohort)==61 and cohort[5]['sha256']=='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe','Actual complete recorded BCP')
 for r in boot['captureMetadata'].values():need(sha(Path(r['path']))==r['sha256'],'Captured mount/classpath/APEX metadata')
 primary=[]
 for p in ['runtime/parsed_options.cc','runtime/gc/space/image_space.cc','core/jni/AndroidRuntime.cpp']:
  row,=[r for r in boot['aospSources']if r['sourceRelativePath']==p];need(sha(ROOT/row['path'])==row['sha256'],'Primary mechanism source');primary.append(row)
 result={'schema':'samsung-authority-vm-launch/v1','status':'CONDITIONAL_IMAGELESS_SOURCE_ROUTE; PROCESS_LOCAL_PROPERTY_AND_FINAL_VECTOR_OWNER_MISSING','selected':False,'launcherAdmitted':False,'runnableCommandGenerated':False,'oemExecuted':False,'artExecuted':False,'phoneActions':False,'newNetworkFetches':0,'sourcePins':PINS,'newRaw':{'path':rawpath.relative_to(ROOT).as_posix(),'sha256':rawpin,'functions':functionmeta,'instructions':9848},'binaryPins':binarypins,'checks':checks,'capturedBootCohort':cohort,'recordedMetadata':boot['captureMetadata'],'primaryMechanismSources':primary,
 'sourceSupportedRoute':{'exactlyOneExplicitCompleteBootClassPath':True,'canonicalRecordedLocations':'Same61 original locations, actual per-process file view must be admitted; framework slot5 remains original for this source-only probe','noImageOptionFromAnyProducer':True,'noForceJitZygoteFromAnyProducer':True,'singleInterpretOption':'-Xint','noExplicitTrueUseJitFromAnyProducer':True,'noCompetingFdBootImageOatVdexInputs':True,'noBootClasspathOrImageDuplicatePrecedenceAssumption':True,'explicitBootClassPathSuppressesDefaultImageSelection':True,'actualEmptyImageListSkipsImageFileDiscovery':True,'actualEmptyBootImageSpaceReachesOpenBootDexFilesAndInitWithoutImage':True,'allowInMemoryCompilationRequiredForChosenEmptyImageRoute':False,'scope':'Static selected branch route; not demonstrated successful initialization or executable launcher'},
 'nativePropertyInputs':[{'key':'persist.device_config.runtime_native_boot.profilebootclasspath','role':'Source GetServerConfigurableFlag then native ParseBool; profiling can force image; source-selected input and actual resulting branch required'},{'key':'dalvik.vm.profilebootclasspath','role':'Native GetBoolProperty fallback when server flag ParseBool uses fallback; actualfalse branch needed'},{'key':'persist.device_config.runtime_native_boot.enable_apex_image','role':'Actual exacttrue selects ForceJitZygote; must take original nonforce branch'},{'key':'dalvik.vm.boot-image','role':'Nonempty appends Ximage; admitted no-image property view must be empty'},{'key':'dalvik.vm.usejit','role':'Nonempty can append Xusejit; absent/empty avoids conflict and Interpret setsfalse itself'},{'key':'dalvik.vm.execution-mode','role':'Must not append additional interpreter/JIT mode option that recreates duplicate/conflict uncertainty'},{'key':'dalvik.vm.extra-opts','role':'Native ASCII-space token source; must contain no competing launch selection; sourceempty avoids duplicate uncertainty'}],
 'finiteMissingPrerequisites':[{'id':'VM-OWNER','missing':'A reviewed process-local native property/read owner before dynamic-library initialization, covering actual GetProperty/property_get/GetBoolProperty and persistent device_config keys without global edits; alternatively a reviewed source-owned final AndroidRuntime option-list seam','why':'Captured launchcode appends native-derived options after caller argv. No source-supported env/Java-D substitution or native interposition admitted here.'},{'id':'VM-VECTOR','missing':'Exact complete final JavaVMOption vector and nativeJNI dispatch binding for the proposed cold process','why':'Need unique explicit BCP and no Image/ForceJit/trueUseJit/conflictingmode/fd inputs, including all late sources; do not depend on repeated-option behavior.'},{'id':'VM-VIEW','missing':'Admitted per-process original61jar/source/image-free option plus Samsung ART/runtime/APEX/native/resource/linker view and actual root/environment/cache identities before VM creation','why':'Recorded host mount/classpath metadata is not the future dedicated namespace. Do not inherit guest derived classpath or redirect credential ANDROID_DATA.'},{'id':'VM-PROBE','missing':'Separately reviewed non-auth Context-only main and genuine metrics/config/application input owner before Context firsteffects','why':'No Context probe/cohort/launcher is authored here; scalar diagnostic is not a boot helper or display readiness.'}],
 'retainedAuthorityAlternative':{'avoids':['Creating a second cold Samsung VM and selecting/rebuilding its boot cohort/image policy','Re-entering original framework constructors merely to obtain a new same-name authority'],'stillRequires':['Retain original process through OneOS current kill boundary with real admission/drain/return ownership','Genuine guest presentation transport and all required credential/policy/key/storage semantics'],'architectureSelected':False},
 'limits':['Static native branch/function evidence only; no native function or ART process runs','No new image, full framework cohort, launcher, property wrapper, library interposition or global property change','No duplicate-option precedence proof is required by the conditional unique-option route; availability of its exact native input owner remains open','Existing frozen scalar/proposal/boot/VM/ART cards remain unchanged'],'toolSha256':sha(Path(__file__))}
 need(sha(rawpath)==rawpin and all(sha(ROOT/p)==v for p,v in PINS.items())and all(sha(ROOT/p)==v for p,v in binarypins.items()),'Before/after inputs unchanged')
 save(ROOT/'inventory/samsung-authority-vm-launch.json',result);save(OUT/'checks.json',{'pass':True,'assertions':len(checks),'newFunctions':6,'newInstructions':9848,'capturedBootEntries':61,'oemExecuted':False,'launcherAdmitted':False})
 paths=[ROOT/'docs/samsung-authority-vm-launch.md',ROOT/'inventory/samsung-authority-vm-launch.json',Path(__file__),rawpath,OUT/'checks.json',OUT/'acquisition.json',RAW/MEMBER]
 save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'launcherAdmitted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}for p in paths]})
 print(json.dumps({'pass':True,'assertions':len(checks),'launcherAdmitted':False,'newFunctions':6,'newInstructions':9848,'capturedBootEntries':61,'oemExecuted':False}))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture',action='store_true');args=ap.parse_args()
 if args.capture:capture()
 else:audit()
