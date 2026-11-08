"""Static final-JNI-call owner proposal. No native gate, patch or OEM execution."""
import argparse,hashlib,json,lzma,re,runpy,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'firmware/samsung-vm-final-options';OUT=ROOT/'out/samsung-vm-final-options'
RUNTIME=ROOT.parent/'firmware/samsung/runtime-20261104/libandroid_runtime.so'
ART=ROOT/'firmware/authority-art-option-selection/libart.so'
HELPER=RAW/'apex/com.android.art/lib64/libnativehelper.so'
PINS={
 '../firmware/samsung/runtime-20261104/libandroid_runtime.so':'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d',
 'firmware/authority-art-option-selection/libart.so':'4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa',
 'firmware/samsung-vm-final-options/apex/com.android.art/lib64/libnativehelper.so':'d974e14ee74159048fcce7e35f2d595dc8a3b703f5e9e445594ed73c0ae18693',
 'firmware/authority-vm-options/selected-native.json':'dc90bc834e5af30ab05bb63e93530b4b067e6c66c68a230b271a07613768dccd',
 'firmware/authority-art-option-selection/selected-native.json':'56f6bf1b52dcd3456d76fe16a29a310c7532b5c83999cb7d7df02b3279d8e670',
 'docs/samsung-authority-vm-launch.md':'8dc85dfffa6862730ff350f2ea8518e51cac0677cf35359e9ba4776a8f031364',
 'inventory/samsung-authority-vm-launch.json':'34f768f6abfcc3a6e0fc65350d5ae82556319bbb9613ead84909e6cdf1a42a60',
 'docs/samsung-vm-property-view.md':'dbca0d7266a6e2d2d2d45e3066ea9c663c3cb336de3043ad74ffade152202ebc',
 'inventory/samsung-vm-property-view.json':'07b519766d964535c8613debccc7810dc2e29f8a32bfc95b9deefc29f06c1e21',
 'firmware/authority-bootstrap-runtime/app_process64':'08891284f79ebd9411d7ebd2e267bd2c083e8d5a02f2f192629fb126fabfeec8',
 'tools/audit_security_native_linkage.py':'33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'}
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def verify():
 for p,pin in PINS.items():need(sha(ROOT/p)==pin,'Frozen input '+p)

def capture():
 verify();parse=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf']
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'));import capstone
 cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);cs.detail=True;sources=[]
 for path,values in [(RUNTIME,[0x174c2c,0x174efc]),(ART,[0x3cd8cc,0x5d3d38,0x5d3db8,0x5d21f8]),(HELPER,[24280,24372,24584,25012])]:
  data=path.read_bytes();e=parse(data);sections=e['sections'];symbols=list(e['dynamicSymbols']);mini=next((s for s in sections if s['name']=='.gnu_debugdata'),None)
  if mini:
   b=lzma.decompress(data[mini['offset']:mini['offset']+mini['bytes']]);need(len(b)<128*1024*1024,'Bounded minidebug');symbols+=parse(b)['dynamicSymbols']
  if path==ART:symbols=load(ROOT/'firmware/authority-art-option-selection/symbols.json')['symbols']
  def offset(address,size=1):
   s,=[s for s in sections if s['type']!=8 and s['address']<=address and address+size<=s['address']+s['bytes']];return s['offset']+address-s['address']
  def string(address):
   try:
    off=offset(address);end=data.index(b'\0',off,min(len(data),off+512));b=data[off:end];return b.decode('ascii')if b and all(32<=x<127 or x in[9,10,13]for x in b)else None
   except(ValueError,UnicodeError):return None
  relocs={r['target']:r for r in e['rela']if r['symbolIndex']}
  def call(address):
   m=[s['name']for s in symbols if s['sectionIndex']and s['value']==address]
   if m:return m[0]
   plt=next((s for s in sections if s['name']=='.plt'and s['address']<=address<s['address']+s['bytes']),None)
   if not plt:return None
   n=min(32,plt['address']+plt['bytes']-address);pages={}
   for i in cs.disasm(data[offset(address,n):offset(address)+n],address):
    if i.mnemonic=='adrp':pages[i.reg_name(i.operands[0].reg)]=i.operands[1].imm
    if i.mnemonic=='ldr'and len(i.operands)==2 and i.operands[1].type==capstone.CS_OP_MEM:
     mem=i.operands[1].mem;base=i.reg_name(mem.base)
     if base in pages and not mem.index:
      r=relocs.get(pages[base]+mem.disp)
      if r:return e['dynamicSymbols'][r['symbolIndex']]['name']
   return None
  functions=[]
  for value in values:
   matches=[s for s in symbols if s['value']==value and s['sectionIndex']and s['type']==2 and s['size']];need(bool(matches),'Exact selected function');s=matches[0];need(all(s['size']==x['size']for x in matches),'Alias size');off=offset(value,s['size']);body=data[off:off+s['size']];pages={};rows=[]
   for i in cs.disasm(body,value):
    r={'pc':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str};assigned=None
    if i.mnemonic=='adrp':assigned=(i.reg_name(i.operands[0].reg),i.operands[1].imm)
    if i.mnemonic=='add'and len(i.operands)==3 and i.operands[2].type==capstone.CS_OP_IMM:
     base=i.reg_name(i.operands[1].reg)
     if base in pages:
      address=pages[base]+(i.operands[2].imm<<i.operands[2].shift.value);assigned=(i.reg_name(i.operands[0].reg),address);v=string(address)
      if v:r['literal']=v
    if i.mnemonic=='adr':
     address=i.operands[1].imm;assigned=(i.reg_name(i.operands[0].reg),address);v=string(address)
     if v:r['literal']=v
    if i.mnemonic in['b','bl']and i.op_str.startswith('#0x'):
     name=call(int(i.op_str[1:],16))
     if name:r['targetSymbol']=name
    if i.mnemonic=='ldr'and len(i.operands)==2 and i.operands[1].type==capstone.CS_OP_MEM:
     mem=i.operands[1].mem;base=i.reg_name(mem.base)
     if base in pages and not mem.index:
      rel=relocs.get(pages[base]+mem.disp)
      if rel:r['gotReference']=e['dynamicSymbols'][rel['symbolIndex']]['name']
    for reg in i.regs_access()[1]:pages.pop(i.reg_name(reg),None)
    if i.mnemonic in['bl','blr']:
     for reg in range(19):pages.pop('x'+str(reg),None)
    if assigned:pages[assigned[0]]=assigned[1]
    rows.append(r)
   need(len(rows)*4==s['size'],'Complete selected function');functions.append({'symbol':s['name'],'address':value,'fileOffset':off,'bytes':s['size'],'sha256':hashlib.sha256(body).hexdigest(),'instructions':rows})
  sources.append({'path':str(path.relative_to(ROOT))if path.is_relative_to(ROOT)else'../'+path.relative_to(ROOT.parent).as_posix(),'sha256':sha(path),'functions':functions})
 verify();save(RAW/'selected-native.json',{'sources':sources,'capstoneVersion':capstone.__version__,'oemExecuted':False,'annotationLimits':'Local register-tracked literal and verified PLT/static call targets, not emulation'})
 print(json.dumps({'functions':sum(len(s['functions'])for s in sources),'instructions':sum(len(f['instructions'])for s in sources for f in s['functions']),'oemExecuted':False}))

def audit():
 verify();parser=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];rawpath=RAW/'selected-native.json';raw=load(rawpath);rawpin=sha(rawpath);index={};meta=[]
 for s in raw['sources']:
  b=(ROOT/s['path']).read_bytes();need(hashlib.sha256(b).hexdigest()==s['sha256'],'Selected exact native source')
  for f in s['functions']:
   body=b[f['fileOffset']:f['fileOffset']+f['bytes']];need(hashlib.sha256(body).hexdigest()==f['sha256']and b''.join(bytes.fromhex(i['bytes'])for i in f['instructions'])==body,'Complete selected function bytes');need(all(i['pc']==f['address']+4*n for n,i in enumerate(f['instructions'])),'Selected PC extent');index.update({i['pc']:i for i in f['instructions']});meta.append({'source':s['path'],**{k:v for k,v in f.items()if k!='instructions'}})
 need(len(meta)==10 and sum(f['bytes']for f in meta)==4404,'Finite selected source set')
 oldvm=load(ROOT/'firmware/authority-vm-options/selected-native.json');oldart=load(ROOT/'firmware/authority-art-option-selection/selected-native.json');old={kind:{i['pc']:i for f in r['functions']for i in f['instructions']}for kind,r in [('vm',oldvm),('art',oldart)]};checks=[]
 def check(scope,pc,key,value,contains=False):
  actual=(index if scope=='new'else old[scope])[pc].get(key);need(value in actual if contains else actual==value,'Exact source '+scope+' '+hex(pc)+' '+key);checks.append({'source':scope,'pc':pc,'pcHex':hex(pc),'field':key,'contains'if contains else'expected':value})
 for pc,key,val in[(0x185b74,'operands','w8, #4'),(0x185b7c,'operands','w8, #1, lsl #16'),(0x185b80,'operands','w8, [x29, #-0xa8]'),(0x185b88,'operands','x0, [x29, #-0xa0]'),(0x185b8c,'operands','x0, x1, [sp, #8]'),(0x185b94,'operands','x2, x29, #0xa8'),(0x185b98,'operands','wzr, [x26, #0xe8]'),(0x185b9c,'operands','w8, [x29, #-0xa4]'),(0x185ba0,'operands','#0x1860dc'),(0x185ba8,'operands','w0, #0x1f, #0x185ea8'),(0x186104,'operands','x1, #0x174c2c'),(0x18611c,'operands','x8, [x8, #0x820]'),(0x186124,'operands','x8')]:check('vm',pc,key,val)
 for pc,word in[(0x185b84,'editArrayImpl'),(0x18610c,'pthread_once')]:check('vm',pc,'targetSymbol',word,True)
 for pc,key,val in[(0x174c50,'literal','libnativehelper.so'),(0x174ca0,'literal','JNI_CreateJavaVM'),(0x174ca8,'operands','w2, #3'),(0x174f44,'operands','x8, x8, #0x808'),(0x174f48,'operands','x0, [x8, w20, uxtw #3]'),(0x5ee8,'operands','x16'),(0x602c,'literal','ART_TEST_ON_VM'),(0x605c,'literal','ART_TEST_ON_SBC'),(0x6084,'literal','ro.debuggable'),(0x60b4,'literal','persist.sys.dalvik.vm.lib.2')]:check('new',pc,key,val)
 for pc,word in[(0x174c58,'dlopen'),(0x174f14,'dlsym'),(0x6200,'JniInvocationGetLibrary'),(0x620c,'dlopen'),(0x623c,'dlsym'),(0x5d3d70,'TokenRangeC2'),(0x5d222c,'vector'),(0x3cdbac,'push_back')]:check('new',pc,'targetSymbol',word,True)
 for pc,word in[(0x597bc8,'ProcessSpecialOptions'),(0x597be8,'CmdlineParser')]:check('art',pc,'targetSymbol',word,True)
 for pc,value in[(0x51c9d0,'-classpath _'),(0x51c9dc,'-cp _'),(0x51e398,'-Xcompiler-option _'),(0x51e3e8,'-Ximage-compiler-option _')]:check('art',pc,'literal',value)
 for pc,value in[(0x51cbb0,'-Xbootclasspath:_'),(0x51d328,'-Xbootclasspath-locations:_'),(0x51d244,'-Ximage:_'),(0x51d288,'-Xforcejitzygote'),(0x51ce00,'-Xint'),(0x51da70,'-Xusejit:_'),(0x51cbf4,'-Xbootclasspathfds:_'),(0x51cc38,'-Xbootclasspathimagefds:_'),(0x51cc7c,'-Xbootclasspathvdexfds:_'),(0x51ce64,'-Xzygote'),(0x51d2f8,'-Xprimaryzygote'),(0x51df0c,'-Ximage-dex2oat'),(0x51df1c,'-Xnoimage-dex2oat'),(0x51e530,'-Xzygote-max-boot-retry=_')]:check('art',pc,'literal',value)
 check('art',0x51daa0,'targetSymbol','CreateTypedBuilderIbE',True)
 for pc,value in[(0x18532c,'-Xint:portable'),(0x185d80,'-Xint:jit'),(0x185ecc,'-Xint:fast')]:check('vm',pc,'literal',value)
 artbytes=ART.read_bytes();apo=struct.unpack_from('<Q',artbytes,32)[0];aps,apn=struct.unpack_from('<HH',artbytes,54);aph=[struct.unpack_from('<IIQQQQQQ',artbytes,apo+n*aps)for n in range(apn)]
 for address,value in[(0x47712,'-Xbootclasspathoatfds:_'),(0x462fd,'false'),(0x6bc1c,'true')]:
  segment,=[p for p in aph if p[0]==1 and p[3]<=address< p[3]+p[5]];off=segment[2]+address-segment[3];actual=artbytes[off:artbytes.index(b'\0',off)].decode('ascii');need(actual==value,'Exact mapped grammar/value string');checks.append({'source':'art-mapped-string','address':address,'expected':value})
 for pc,value in[(0x3cdabc,'sensitiveThread'),(0x3cdad0,'vfprintf'),(0x3cdb40,'exit'),(0x3cdb90,'abort'),(0x3cd920,'compilercallbacks'),(0x3cd92c,'imageinstructionset')]:check('new',pc,'literal',value)
 b=RUNTIME.read_bytes();e=parser(b);phoff=struct.unpack_from('<Q',b,32)[0];phents,phnum=struct.unpack_from('<HH',b,54);need(phoff==64 and phents==56 and phnum==13,'Actual PH table');ph=[dict(zip(['type','flags','offset','vaddr','paddr','filesz','memsz','align'],struct.unpack_from('<IIQQQQQQ',b,phoff+i*phents)))for i in range(phnum)]
 rx,=[p for p in ph if p['type']==1 and p['flags']==5];rw=sorted([p for p in ph if p['type']==1 and p['flags']==6],key=lambda x:x['vaddr']);lo=rx['offset']+rx['filesz'];hi=rw[0]['offset'];entry=(lo+15)&~15;state=rw[-1]['vaddr']+rw[-1]['memsz']
 need((rx['offset'],rx['vaddr'],rx['filesz'],rx['memsz'],rx['align'])==(0x12c000,0x12c000,0x1a4cd8,0x1a4cd8,0x4000),'Exact RX shape');need(lo==0x2d0cd8 and hi==0x2d4000 and state==0x300ab0,'Actual reserved-region bounds');need(not any(b[lo:hi]),'All zero file gap')
 need(not[s for s in e['sections']if s['bytes']and s['type']!=8 and s['offset']<hi and lo<s['offset']+s['bytes']],'No intersecting section');need(not[r for r in e['rela']if lo<=r['target']<hi or state<=r['target']<state+16],'No relocation target in proposed owned ranges');need(not[s for s in e['dynamicSymbols']if s['sectionIndex']and(lo<=s['value']<hi or state<=s['value']<state+16)],'No dynamic symbol in proposed owned ranges')
 # Shared parser covers RELA/APS2; independently close actual Android RELR.
 shoff=struct.unpack_from('<Q',b,40)[0];shnum=struct.unpack_from('<H',b,60)[0];sections=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+64*i)for i in range(shnum)]
 relr_sections=[s for s in sections if s[1]in(19,0x6fffff00)];need(len(relr_sections)==1,'One selected RELR section');relr=relr_sections[0];need(relr[5]==1976 and relr[9]==8,'Actual RELR extent/entrysize');targets=[];cursor=0
 for p in range(relr[4],relr[4]+relr[5],8):
  value=struct.unpack_from('<Q',b,p)[0]
  if value&1:
   need(cursor!=0,'RELR bitmap needs base');targets.extend(cursor+8*n for n in range(63)if(value>>(n+1))&1);cursor+=63*8
  else:need(value%8==0,'Aligned RELR slot');targets.append(value);cursor=value+8
 need(len(targets)==len(set(targets)),'Unique RELR target slots')
 def in_owned(value):return lo<=value<hi or state<=value<state+16
 def in_place(address):
  segment,=[p for p in ph if p['type']==1 and p['vaddr']<=address and address+8<=p['vaddr']+p['memsz']];delta=address-segment['vaddr']
  if delta>=segment['filesz']:return 0
  need(delta+8<=segment['filesz'],'No partial file/BSS relocation slot');return struct.unpack_from('<Q',b,segment['offset']+delta)[0]
 relr_addends=[in_place(t)for t in targets];need(not[t for t in targets if in_owned(t)]and not[a for a in relr_addends if in_owned(a)],'No RELR slot or in-place pointer addend reaches proposed regions')
 need(not[r for r in e['rela']if in_owned(r['target'])or in_owned(r['addend'])],'No RELA/APS2 target/addend reaches proposed regions')
 mini=next(s for s in e['sections']if s['name']=='.gnu_debugdata');decoded=lzma.decompress(b[mini['offset']:mini['offset']+mini['bytes']]);need(len(decoded)<128*1024*1024,'Minidebug bound');local_symbols=parser(decoded)['dynamicSymbols'];need(not[s for s in local_symbols if s['sectionIndex']and s['size']and(s['value']<hi and lo<s['value']+s['size']or s['value']<state+16 and state<s['value']+s['size'])],'No intersecting sized minidebug symbol')
 relocation_coverage={'RELAAndAPS2Records':len(e['rela']),'RELRSectionBytes':relr[5],'RELRWords':relr[5]//8,'expandedRELRSlots':len(targets),'inPlaceRELRAddendsChecked':len(relr_addends),'allTargetsAddendsAndSizedLocalSymbolsAvoidProposedRegions':True}
 need(phoff+phnum*phents==792 and min(s['offset']for s in e['sections']if s['name'].startswith('.note'))==792,'No spare PH slot assumption')
 need(struct.unpack_from('<I',b,896)[0]==3,'Actual GNU AArch64 feature bits BTI/PAC');need((entry-0x185ba0)%4==0 and -(1<<27)<=entry-0x185ba0<(1<<27),'Direct BL target in range')
 # Independently read st_other/version; the shared parser intentionally does not expose visibility.
 ds,=[s for s in sections if s[1]==11];strings_sec=sections[ds[6]];strings=b[strings_sec[4]:strings_sec[4]+strings_sec[5]];jni=[]
 for n in range(ds[5]//24):
  p=ds[4]+n*24;name,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',b,p);text=strings[name:strings.index(b'\0',name)].decode()
  if text=='JNI_CreateJavaVM':jni.append({'index':n,'binding':info>>4,'visibility':other&3,'value':value,'bytes':size})
 need(jni==[{'index':3263,'binding':1,'visibility':3,'value':0x1860dc,'bytes':116}],'Exact protected JNI export')
 imports=[s['name']for s in e['dynamicSymbols']if not s['sectionIndex']and s['name']in['mmap','munmap','getpid','gettid']];need(set(imports)=={'mmap','munmap','getpid','gettid'},'Existing C import candidates')
 app=parser((ROOT/'firmware/authority-bootstrap-runtime/app_process64').read_bytes());need('libandroid_runtime.so'in app['needed'],'Original dependency loads runtime before main')
 result={'schema':'samsung-vm-final-options/v1','status':'CONSTRUCTIVE_PRE_CODE_PROPOSAL; ROOT_API_AND_NATIVE_PRODUCER_REVIEW_REQUIRED','selected':False,'gateImplemented':False,'patchedElfProduced':False,'runnableCommandGenerated':False,'oemExecuted':False,'artExecuted':False,'phoneActions':False,'inputPins':PINS,'raw':{'path':rawpath.relative_to(ROOT).as_posix(),'sha256':rawpin,'functions':meta,'instructions':1101},'checks':checks,
 'actualAbi':{'architecture':'AArch64','sourceCallPc':0x185ba0,'sourceReturnPc':0x185ba4,'originalCallee':0x1860dc,'JNIExport':jni[0],'x0':'original JavaVM** output pointer','x1':'original JNIEnv** output pointer','x2':'original JavaVMInitArgs* at x29-0xa8','version':65540,'versionOffset':0,'nOptionsOffset':4,'optionsPointerOffset':8,'ignoreUnrecognizedOffset':16,'ignoreUnrecognized':False,'initArgsNativeSize':24,'optionTupleNativeSize':16,'optionStringOffset':0,'extraInfoOffset':8,'originalSignedFailureBranch':0x185ba8},
 'placementProposal':{'programHeaders':ph,'noSpareHeaderSlot':True,'existingZeroRxGapStart':lo,'existingZeroRxGapEnd':hi,'gapBytes':hi-lo,'proposedAlignedEntry':entry,'payloadBudgetBytes':hi-entry,'branchDeltaBytes':entry-0x185ba0,'newProgramHeaderRequired':False,'newDsoOrNeededEntryRequired':False,'proposedOwnedBssStart':state,'proposedOwnedBssBytes':16,'existingRelroUnchanged':True,'gnuAarch64FeatureBits':3,'sourceFootprintChanges':['One BL at185ba0','ExistingRX filesz/memsz extended only into verifiedgap, payloadbounded below2d4000','LastRW memsz extended16B beyondallsourceBSS forownedone-shotstate; filesz unchanged','Newauthoredcode/readonlyprofile onlyinzeroRXgap','Derivativebuildidentity/optionalownunwindmetadata needexplicitfutureproducerproof'],'originalBindingPreserved':'Tail B to original protected1860dc wrapper; keep pthread_once, symboltable300808/slot300820 and nativehelper dispatch intact','existingCImportCandidates':imports},
 'defaultOffAdmissionProposal':{'default':'Embedded immutable DISABLED profile delegates originalargs/SP/LR withouttouchingvector orownedstate','enabledSelection':'Only a separately root-reviewed enabled privateartifact in a unique coldprocess mount/code view, selectedbeforeapp_process ELFload; no environment/propertyactivation','ownedCallGuard':'Match actualmodule/call return185ba4 and reviewedembeddedprofile; validateJNI1.4/falseignore/realunchangedoutputpointers/completeboundedvector and one-shotownedstate','notProvenance':'Embeddedexpectedhashes/profile/callerPC are localconstraints, not livecode/nativebackend/cohort attestation; genuine launch/viewowner remainsmandatory','ownedRefusal':'Fail before originalVMcall with negativeJNI_ERR into existing sourcefailurebranch; preserveoutputpointers, do not publishVMsuccess','oneShot':'OwnBSS NEW->BUILDING->ISSUED; racing/reentrant/repeatedownedcreate refuses. Afterissue keepstate/arena untilprocess exit; unknown progress never retry/free'},
 'vectorTransformationProposal':{'input':'Complete final originalJavaVMInitArgs and raw tuplearray afterall originalAndroidRuntime additions','shadowSpecialProjection':'Retain exit/vfprintf/sensitiveThread/abort tuples unchanged in rawoutput, but omit these originalspecials from the classification-only tokenindex; preserveeverypointer/extrainfo/order','opaqueBootSpecials':'Activecandidate rejects bootclasspath, compilercallbacks or imageinstructionset specialinputs; never substitute unknownDexFileList/CompilerCallbacks/ISA','twoTokenGrammars':['-classpath _','-cp _','-Xcompiler-option _','-Ximage-compiler-option _'],'groupRule':'Protect next projectednormal-token value, even acrossretainedhooktuples; malformed/missingvalues refuse, no hand-splitting/quotingreinterpretation','ownedTopLevelSelection':'Only recognized top-level bootclasspath/location/image/forcejit/interpret/usejit tokens are replaced; opaqueBCPfd/OAT/VDEX inputs and zygote modes refuse forstandalone candidate; nonnull extraInfo onchangedrow refuses','output':'Stable cloneunrelatedrawtuples unchanged, appendone reviewedexplicitcompleteBCP andone -Xint (optionallocation optionalonlyifexact), noImage/noForceJit/noUseJittrue; verifyfullshadowprojectionagainbeforeissue','storage':'Ownedanonymousarena forcloned24BInitArgs/tuplearray andownedreplacementstorage. PreserveborrowedunrelatedoptionString/extrainfo pointers andoriginalcaller lifetimes; do notclaimstackstringsbecomeprocesslifetime. Keepownedarena throughrealcallee consumption andconservativelyuntilprocessexit','transfer':'RestoreentrySP/LR andallpreservedregisters; forwardx0/x1unchanged,x2clone; tailBoriginalwrapper. Originalcallee return/error/exit/abort hooksrununchanged; no newframe survivesacrossVMcreation','extraOpts':'Never clear originaldalvik.vm.extra-opts or globalproperties; normalize onlyselectedtop-level flags afterallnative producers'},
 'discriminatingCounterexample':{'rawTupleOrder':['-Xcompiler-option','exit(nonnull genuinehook)','-Xusejit:true'],'actualSpecialProjection':['-Xcompiler-option','-Xusejit:true'],'required':'Preserveall3tuples; usejittextiscompilerpayload. Adjacentraw/prefixfilter iswrong.'},
 'nativeBinding':{'runtimeOnceInitializer':0x174c2c,'dlopenName':'libnativehelper.so','nativeHelperCapturedPath':'/apex/com.android.art/lib64/libnativehelper.so','nativeHelperSha256':PINS['firmware/samsung-vm-final-options/apex/com.android.art/lib64/libnativehelper.so'],'GetLibraryInputs':['ART_TEST_ON_VM','ART_TEST_ON_SBC','ro.debuggable','persist.sys.dalvik.vm.lib.2','actuallibartd.so filepresence'],'meaning':'Originalnativehelper canchoose/loadbackendbeforefinalcall; gate preservesitsdispatch anddoesnotforceorattestlibart byname. Actualhelper/backendmapping/provenance remainslaunchadmission.'},
 'remainingPrerequisites':['Rootapprovalofexactactivation/profile/vector/lifetimeAPI beforecode','Boundedauthorednativegatecode+profilemustactuallyfit13088B; originalbytes/inverse/relocations/header/rawmetadata/ABIproof notproduced','Actualcapturedlinker segment-loading/BTI/PAC/unwind/permissions andprivatefilemountadmission; declaredELFgap isnotexecutionapproval','Genuinetrustedcoldprocess/view/embeddedprofileissuer and actualnativehelper/libart/cohortmappingadmission beforeVM; no hash/name-only attestation','Nativearena/allocation failurepaths/completeparser-projection/one-shot assembly proof and independentreview; no implementationhere','Non-authContextentry,genuineconfig/metrics/applicationowners stillseparate']}
 result['placementProposal']['relocationCoverage']=relocation_coverage
 result['placementProposal']['capturedAppProcessRuntimeDependency']='libandroid_runtime.so'
 result['finiteVectorGrammar']={
  'classificationOrder':['Exact special-hook projection (retain raw tuples)','Exact two-token groups and protected value roles in projected stream','Exact unrelated registered exceptions','Exact controlled grammar below','Refuse unmatched bootstrap-family lookalikes; otherwise preserve unrelated tuple'],
  'stringListDomain':'One bounded NUL-terminated option string with nonempty colon-delimited components. No shell splitting or rewriting inside a component; this is a declared finite accepted input profile, not a claim of all ART list semantics.',
  'controlledRules':[
   {'sourcePattern':'-Xbootclasspath:_','acceptedInput':'Value must equal the one root-approved complete source-input BCP list; current candidate is recorded original ordered61. Any other input list refuses, not silently reclassified.','action':'Remove top-level input selections; append exactly one approved complete output BCP.'},
   {'sourcePattern':'-Xbootclasspath-locations:_','acceptedInput':'Nonempty colon-list exactly matching the approved source BCP locations/count.','action':'Remove input selections; output omitted, or exactly one count/subject-matching approved locations list.'},
   {'sourcePattern':'-Ximage:_','acceptedInput':'Nonempty bounded colon-list in the declared string-list domain. Empty/malformed/unclosed value refuses.','action':'Remove only top-level image selection; do not touch image-compiler payloads.'},
   {'sourcePattern':'-Xforcejitzygote','acceptedInput':'Exact complete token, no suffix.','action':'Remove top-level token.'},
   {'sourcePattern':'-Xint','acceptedInput':'Exact complete token.','action':'Normalize to exactly one appended -Xint.'},
   {'sourcePattern':'Legacy source-produced mode tokens','acceptedInput':['-Xint:portable','-Xint:fast','-Xint:jit'],'action':'Remove these top-level source mode tokens; append one -Xint. Any other -Xint:* value refuses.'},
   {'sourcePattern':'-Xusejit:_','acceptedInput':['true','false'],'action':'Remove only top-level selections; let actual Interpret branch set UseJitCompilation false. No true runtime selection in output.'}],
  'activeRefusalExactSpecials':['bootclasspath','compilercallbacks','imageinstructionset'],
  'activeRefusalSourcePatterns':['-Xbootclasspathfds:_','-Xbootclasspathimagefds:_','-Xbootclasspathvdexfds:_','-Xbootclasspathoatfds:_','-Xzygote','-Xprimaryzygote'],
  'preservedRegisteredBootstrapLookingExceptions':['-Ximage-dex2oat','-Xnoimage-dex2oat','-Xzygote-max-boot-retry=_'],
  'lookalikeRefusal':'After exact groups/exceptions/rules, unmatched top-level names in -Xbootclasspath*, -Ximage*, -Xnoimage*, -Xforcejit*, -Xint*, -Xusejit*, -Xzygote* or -Xprimaryzygote* refuse. Never apply this family check to protected group values.',
  'hookWhitelist':{'exit':'Require nonnull extraInfo; retain exact raw tuple.','vfprintf':'Require nonnull extraInfo; retain exact raw tuple.','abort':'Require nonnull extraInfo; retain exact raw tuple.','sensitiveThread':'Preserve actual nullable extraInfo (source accepts null); retain exact raw tuple.'},
  'extraInfoRule':'Unrelated tuples retain extraInfo exactly. Changed controlled rows require null extraInfo; nonnull refuses. Unknown unrelated rows are retained for original ART validation, not silently converted to a hook.',
  'appendBoundary':'Finish validating and closing every original projected group BEFORE appending owned tokens. A missing original value rejects; appended BCP/-Xint can never fill it.',
  'finalVerification':'Reproject the entire proposed raw output, retaining hook/raw tuple mapping; rederive group roles. Require exactly one TOP-LEVEL BCP and Interpret, matching optional locations, zero top-level Image/ForceJit/UseJit and refused special/fd/zygote forms, no pending group, and exact unchanged unrelated tuple pointer/order correspondence. Raw string counts are insufficient.',
  'notImplemented':True}
 verify();need(sha(rawpath)==rawpin,'Rawunchanged');save(ROOT/'inventory/samsung-vm-final-options.json',result);save(OUT/'checks.json',{'pass':True,'assertions':len(checks),'selectedFunctions':10,'instructions':1101,'payloadBudget':hi-entry,'patchedElfProduced':False,'oemExecuted':False})
 paths=[ROOT/'docs/samsung-vm-final-options.md',ROOT/'inventory/samsung-vm-final-options.json',Path(__file__),rawpath,OUT/'acquisition.json',OUT/'checks.json',HELPER]
 save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'gateImplemented':False,'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size}for p in paths]})
 print(json.dumps({'pass':True,'assertions':len(checks),'functions':10,'instructions':1101,'payloadBudget':hi-entry,'gateImplemented':False,'patchedElfProduced':False}))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture',action='store_true');a=ap.parse_args()
 if a.capture:capture()
 else:audit()
