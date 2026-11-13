"""Bounded offline captured ART option-selection inspection; no OEM execution."""
import argparse,gzip,hashlib,json,lzma,runpy,sys,tarfile,re
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]; PARENT=ROOT.parent
RAW=ROOT/'firmware/authority-art-option-selection'; OUT=ROOT/'out/authority-art-option-selection'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
DIFF=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
MEMBER='apex/com.android.art/lib64/libart.so'
PIN='4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa'
SOURCE=RAW/'libart.so'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def extract():
 manifest=DIFF/'samsung-manifest.jsonl.gz'
 assert sha(manifest)=='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
 with gzip.open(manifest,'rt')as f:row,=[r for line in f if(r:=json.loads(line))['path']==MEMBER]
 assert row['kind']=='file' and row['size']==15010176 and row['sha256']==PIN and TAR.stat().st_size==20434769920
 if SOURCE.exists():assert sha(SOURCE)==PIN;return
 with tarfile.open(TAR,'r:')as tar:
  for member in tar:
   if member.name.removeprefix('./')!=MEMBER:continue
   assert member.isfile() and member.size==row['size']
   data=tar.extractfile(member).read(member.size+1);assert len(data)==member.size and hashlib.sha256(data).hexdigest()==PIN
   SOURCE.parent.mkdir(parents=True,exist_ok=True);SOURCE.write_bytes(data)
   save(OUT/'acquisition.json',{'sourceTar':str(TAR),'tarBytes':TAR.stat().st_size,'priorStrictReceipt':str(DIFF/'report.json'),'priorStrictReceiptSha256':sha(DIFF/'report.json'),'fullTarRehashedThisRun':False,'member':MEMBER,'headerOffset':member.offset,'dataOffset':member.offset_data,'bytes':len(data),'sha256':PIN,'oemExecuted':False});break
  else:raise ValueError('Named captured member missing')
def symbols():
 assert sha(SOURCE)==PIN
 parse=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];data=SOURCE.read_bytes();p=parse(data)
 syms=p['dynamicSymbols'];debug=next((s for s in p['sections'] if s['name']=='.gnu_debugdata'),None)
 if debug:
  mini=lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']]);assert len(mini)<128*1024*1024
  syms+=parse(mini)['dynamicSymbols']
 save(RAW/'symbols.json',{'sourceSha256':PIN,'sections':p['sections'],'symbols':syms,'needed':p['needed'],'oemExecuted':False})
 print(json.dumps({'symbols':len(syms),'miniDebug':bool(debug),'selected':[s for s in syms if any(k in s['name'] for k in ['ParsedOptions','ParseRuntimeOptions','JNI_CreateJavaVM','Runtime4Init','GetDefaultBootImageLocation','GetJitZygoteBootImageLocation'])]}))
def capture():
 assert sha(SOURCE)==PIN
 parse=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];data=SOURCE.read_bytes();p=parse(data)
 syms=json.loads((RAW/'symbols.json').read_text())['symbols'];secs=p['sections']
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'));import capstone
 cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);cs.detail=True
 def offset(addr,size=1):
  s,=[s for s in secs if s['type']!=8 and s['address']<=addr and addr+size<=s['address']+s['bytes']]
  return s['offset']+addr-s['address']
 def string(addr):
  try:
   off=offset(addr);end=data.index(b'\0',off,min(len(data),off+512));b=data[off:end]
   return b.decode('ascii')if b and all(32<=c<127 or c in[9,10,13]for c in b)else None
  except(ValueError,UnicodeError):return None
 plt,=[s for s in secs if s['name']=='.plt'];slots=[r for r in p['rela']if r['type']==1026]
 def call(addr):
  if plt['address']+32<=addr<plt['address']+plt['bytes']and(addr-plt['address']-32)%16==0:
   reloc=slots[(addr-plt['address']-32)//16];stub=list(cs.disasm(data[offset(addr,16):offset(addr,16)+16],addr))
   adrp=next(i for i in stub if i.mnemonic=='adrp'and i.op_str.startswith('x16,'));ldr=next(i for i in stub if i.mnemonic=='ldr'and i.op_str.startswith('x17,'));disp=re.search(r'#(0x[0-9a-f]+|\d+)',ldr.op_str)
   assert int(adrp.op_str.split('#')[1],16)+(int(disp.group(1),0)if disp else 0)==reloc['target']
   return p['dynamicSymbols'][reloc['symbolIndex']]['name']
  m=[s['name']for s in syms if s['sectionIndex']and s['value']==addr];return m[0]if m else None
 wanted=['_ZN3art13ParsedOptions10MakeParser','_ZN3art13ParsedOptions7DoParse','_ZN3art13ParsedOptions5Parse','_ZN3art7Runtime12ParseOptions','_ZN3art7Runtime6CreateERK','_ZN3art7Runtime6CreateEONS','_ZN3art13ParsedOptions5UsageE','JNI_CreateJavaVM']
 funcs=[];seen=set()
 for s in syms:
  if not s['sectionIndex']or s['type']!=2 or not s['size']or not(any(s['name'].startswith(k)for k in wanted)or s['value']==0x598598)or s['value']in seen:continue
  seen.add(s['value']);off=offset(s['value'],s['size']);body=data[off:off+s['size']];insns=[];pages={}
  reloc_by_addr={r['target']:r for r in p['rela']}
  for i in cs.disasm(body,s['value']):
   row={'pc':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str}
   assigned=None
   if i.mnemonic=='adrp':reg,v=i.op_str.split(', ');assigned=(reg,int(v[1:],0))
   if i.mnemonic=='add'and len(i.operands)==3 and i.operands[2].type==capstone.CS_OP_IMM:
    reg=i.reg_name(i.operands[1].reg)
    if reg in pages:
     addr=pages[reg]+(i.operands[2].imm<<i.operands[2].shift.value);literal=string(addr);assigned=(i.reg_name(i.operands[0].reg),addr)
     row['addressPair']={'address':addr,'symbol':[s['name']for s in syms if s['sectionIndex']and s['value']==addr]}
     if literal:row['literal']=literal
   if i.mnemonic=='adr':
    addr=i.operands[1].imm;assigned=(i.reg_name(i.operands[0].reg),addr);row['addressPair']={'address':addr,'symbol':[s['name']for s in syms if s['sectionIndex']and s['value']==addr]};literal=string(addr)
    if literal:row['literal']=literal
   if i.mnemonic=='ldr'and len(i.operands)==2 and i.operands[1].type==capstone.CS_OP_MEM:
    mem=i.operands[1].mem;base=i.reg_name(mem.base)
    if base in pages and not mem.index:
     addr=pages[base]+mem.disp;reloc=reloc_by_addr.get(addr)
     if reloc and reloc['symbolIndex']:
      row['gotReference']={'address':addr,'symbol':p['dynamicSymbols'][reloc['symbolIndex']]['name']}
   if i.mnemonic in['b','bl']and i.op_str.startswith('#0x'):
    name=call(int(i.op_str[1:],16))
    if name:row['targetSymbol']=name
   for reg in i.regs_access()[1]:pages.pop(i.reg_name(reg),None)
   if i.mnemonic in['bl','blr']:
    for reg in range(19):pages.pop('x'+str(reg),None)
   if assigned:pages[assigned[0]]=assigned[1]
   insns.append(row)
  assert len(insns)*4==len(body)
  funcs.append({'symbol':s['name'],'address':s['value'],'fileOffset':off,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'instructions':insns})
 assert len(funcs)==9 and sha(SOURCE)==PIN
 save(RAW/'selected-native.json',{'sourceSha256':PIN,'pcKind':'ELF virtual address; not live address','functions':funcs,'annotationLimits':'Local ADRP/ADD or ADR pairs; not emulation','oemExecuted':False})
 print(json.dumps({'functions':[{k:v for k,v in f.items()if k!='instructions'}for f in funcs],'instructions':sum(len(f['instructions'])for f in funcs),'oemExecuted':False}))
def audit():
 assert sha(SOURCE)==PIN
 rawpath=RAW/'selected-native.json';raw=json.loads(rawpath.read_text());data=SOURCE.read_bytes();checks=[]
 for f in raw['functions']:
  body=data[f['fileOffset']:f['fileOffset']+f['bytes']]
  assert hashlib.sha256(body).hexdigest()==f['sha256']and b''.join(bytes.fromhex(i['bytes'])for i in f['instructions'])==body
  assert all(i['pc']==f['address']+4*n for n,i in enumerate(f['instructions']))
 assert len(raw['functions'])==9
 index={i['pc']:i for f in raw['functions']for i in f['instructions']}
 def check(pc,key,value):
  assert index[pc][key]==value,(hex(pc),key,index[pc].get(key),value)
  checks.append({'pc':pc,'pcHex':hex(pc),'field':key,'expected':value})
 for pc,value in[(0x51cbb0,'-Xbootclasspath:_'),(0x51d244,'-Ximage:_'),(0x51d288,'-Xforcejitzygote'),(0x51d2b8,'-Xallowinmemorycompilation'),(0x51d328,'-Xbootclasspath-locations:_'),(0x597cac,'BOOTCLASSPATH'),(0x598540,'-Ximage and -Xforcejitzygote cannot be specified together\n')]:check(pc,'literal',value)
 for pc,key in[(0x51cbe4,'13BootClassPathE'),(0x51d278,'5ImageE'),(0x51d2ac,'14ForceJitZygoteE'),(0x51d2ec,'24AllowInMemoryCompilationE'),(0x597c80,'13BootClassPathE'),(0x597dec,'14ForceJitZygoteE'),(0x597e00,'6ZygoteE'),(0x597e18,'20CompilerCallbacksPtrE'),(0x5982d8,'5ImageE'),(0x59833c,'24AllowInMemoryCompilationE'),(0x598350,'5ImageE'),(0x598370,'20DenyArtApexDataFilesE'),(0x5985b4,'13BootClassPathE'),(0x597a6c,'exit')]:
  assert index[pc]['gotReference']['symbol'].endswith(key);checks.append({'pc':pc,'pcHex':hex(pc),'gotSymbolSuffix':key})
 for pc,value in[(0x597df4,'w0, #0, #0x5982d0'),(0x5982e4,'#0x59853c'),(0x597e08,'w0, #0, #0x598334'),(0x597e28,'#0x598348'),(0x59835c,'#0x597e2c'),(0x598364,'#0x597e2c'),(0x5985c4,'#0x5985e8'),(0x5985ec,'x8, #0x5985c8'),(0x946db4,'x8, [x19, #0x10]'),(0x946db8,'w0, ne'),(0x946dbc,'x8')]:check(pc,'operands',value)
 for pc,word in[(0x8a5114,'Runtime6CreateERK'),(0x46c7d0,'Runtime12ParseOptions'),(0x46c904,'ParsedOptions5Parse'),(0x597a80,'ParsedOptions7DoParse'),(0x46c86c,'Runtime4Init'),(0x597cd8,'SetIfMissing'),(0x5982ec,'GetJitZygoteBootImageLocation'),(0x598398,'GetDefaultBootImageLocation'),(0x598340,'3SetINS_4UnitE'),(0x598548,'ParsedOptions5Usage'),(0x597be8,'CmdlineParser')]:
  assert word in index[pc]['targetSymbol'];checks.append({'pc':pc,'pcHex':hex(pc),'targetContains':word})
 cards={'docs/authority-boot-framework.md':'498c2fc83901a8a34d6902b7135d771f8d5e46f8a72d8a8192ff8a6472b742fc','inventory/authority-boot-framework.json':'8a7b144c1c9024ffbff548568439b2e81a9c072ecd05683469a7fbc33f31f96a','docs/authority-vm-options.md':'6a844f305d30877f3bae7e1fb79d04db32f84c1b2a48a5c5ae0634fffc353d18','inventory/authority-vm-options.json':'ef555b5bb8b57e2323b12f63aae557c4fc5083f0271208e683ec144215df8db4','docs/security-authority-quiescence.md':'946604e673df1c989e552b2e915e5ddeb3977ac834f64abc558e37e09a8f9da3','inventory/security-authority-quiescence.json':'352d9b2ddd3f003f49b6027e2f9bb13dbad57f09a0e8208c562e220847ff43bd'}
 for path,pin in cards.items():assert sha(ROOT/path)==pin
 syms=json.loads((RAW/'symbols.json').read_text())['symbols']
 names=['_ZN3art29GetJitZygoteBootImageLocationEv','_ZN3art27GetDefaultBootImageLocationERKNSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEb']
 imports=[s for s in syms if s['name']in names];assert len(imports)==2 and all(s['sectionIndex']==0 for s in imports)
 frontiers=[s for s in syms if s['sectionIndex']and s['value']in[0x5d3d38,0x5d3db8,0x608c58,0x3cd8cc,0x591f7c]]
 assert len(frontiers)==5
 inv={'schema':'authority-art-option-selection/v1','status':'BOUNDED_MATCHED_SAMSUNG_ELF_PARSER_CONSTRAINTS; no launch recipe','selected':False,'oemExecuted':False,'deviceInspected':False,
      'source':{'capturedPath':'/'+MEMBER,'path':SOURCE.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':PIN},'acquisition':{'path':'out/authority-art-option-selection/acquisition.json','sha256':sha(OUT/'acquisition.json')},
      'raw':{'path':rawpath.relative_to(ROOT).as_posix(),'sha256':sha(rawpath),'symbolsPath':'firmware/authority-art-option-selection/symbols.json','symbolsSha256':sha(RAW/'symbols.json')},
      'functions':[{k:v for k,v in f.items()if k!='instructions'}for f in raw['functions']],'checks':checks,
      'provedConstraints':['Actual MakeParser registers Image/ForceJitZygote/BootClassPath/AllowInMemoryCompilation to exact keys','Actual ForceJitZygote plus Image reaches Usage error path with nonzero configured exit callback argument','Actual Zygote key sets AllowInMemoryCompilation; explicit flag is independently registered','Populated explicit BootClassPath survives environment SetIfMissing; default-image helper called only without compiler callbacks, explicit BootClassPath, or Image','Actual JNI export -> Runtime Create -> ParseOptions -> ParsedOptions Parse/DoParse -> Runtime Init entry pinned; no live dispatch target claim'],
      'externalImageHelpers':imports,'unclosedFunctions':frontiers,'remaining':['Repeated Image/BootClassPath occurrence assignment and parser callback semantics remain uninspected in CmdlineParser/IntoKey frontier','Special-option exit/abort hook overrides not resolved here; default exit slot alone is not actual AndroidRuntime hook attestation','Imported image helper implementations/returned paths, coherent artifact validation and actual in-memory compilation remain unproved','Actual future VM option vector/env/server-property flags/data caches/library selection/live process ownership remain unobserved'],
      'aospRole':'Prior primary source mechanism reference; assertions here use captured Samsung ELF bytes rather than assigning its source revision','preservedCards':[{'path':p,'sha256':pin}for p,pin in cards.items()]}
 inventory=ROOT/'inventory/authority-art-option-selection.json';save(inventory,inv)
 save(OUT/'checks.json',{'pass':True,'functions':9,'instructions':sum(len(f['instructions'])for f in raw['functions']),'assertions':len(checks),'oemExecuted':False,'selected':False})
 paths=[ROOT/'docs/authority-art-option-selection.md',inventory,Path(__file__),OUT/'checks.json',OUT/'acquisition.json',rawpath,RAW/'symbols.json']
 save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'oemExecuted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in paths]})
 print(json.dumps({'pass':True,'functions':9,'assertions':len(checks),'oemExecuted':False,'selected':False}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--extract',action='store_true');ap.add_argument('--symbols',action='store_true');ap.add_argument('--capture',action='store_true');args=ap.parse_args()
 if args.extract:extract()
 if args.symbols:symbols()
 if args.capture:capture()
 if not(args.extract or args.symbols or args.capture):audit()
