"""Bounded offline native property-view/VM-option seam investigation.

Only reads exact supplied ELF files. No interposer, patch, launcher, OEM/native
execution, ART/device operation, environment activation or global property edit.
"""
import argparse,gzip,hashlib,json,lzma,re,runpy,struct,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
RAW=ROOT/'firmware/samsung-vm-property-view';OUT=ROOT/'out/samsung-vm-property-view'
MANIFEST=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
MANIFEST_SHA='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
MEMBERS={
 'system/lib64/libbase.so':'6c328ad4107810fa7a5e3f58e06c3e9142af1aabe159c6c51ec08b83296aacc2',
 'system/lib64/libcutils.so':'08db43c44cda1ff5d1d93778a4aadccee408379b53655640388e6622c01c6cb9',
 'apex/com.android.runtime/lib64/bionic/libc.so':'88fba68b3d1fded4bfd25197f6de24f5b8794d3253de860ee261a4272be9e861',
 'apex/com.android.runtime/bin/linker64':'8ec70ab6a3175a9cf5ac6ea5e7f18dfd3d9771f9a734f7ab7ebb71455bd225c1',
}
EXISTING={
 'runtime':('../firmware/samsung/runtime-20261104/libandroid_runtime.so','f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d'),
 'app-process':('firmware/authority-bootstrap-runtime/app_process64','08891284f79ebd9411d7ebd2e267bd2c083e8d5a02f2f192629fb126fabfeec8'),
}

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def extract():
 assert sha(MANIFEST)==MANIFEST_SHA
 records={}
 with gzip.open(MANIFEST,'rt') as f:
  for line in f:
   row=json.loads(line)
   if row['path'] in MEMBERS:records[row['path']]=row
 assert set(records)==set(MEMBERS)
 pending={p for p,h in MEMBERS.items() if not (RAW/p).exists()}
 for p,h in MEMBERS.items():
  assert records[p]['kind']=='file' and records[p]['sha256']==h
  if (RAW/p).exists():assert sha(RAW/p)==h
 if pending:
  with tarfile.open(TAR,'r:') as t:
   found=set()
   for member in t:
    name=member.name.removeprefix('./')
    if name not in pending:continue
    assert name not in found and member.isfile() and member.size==records[name]['size'] and member.size<5*1024*1024
    data=t.extractfile(member).read(member.size+1)
    assert len(data)==member.size and hashlib.sha256(data).hexdigest()==MEMBERS[name]
    dest=RAW/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);found.add(name)
   assert found==pending
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'extraction.json').write_text(json.dumps({'scope':'four exact regular tar members only, no alias resolution or broad extraction','manifestSha256':MANIFEST_SHA,'records':list(records.values()),'files':{p:sha(RAW/p) for p in MEMBERS},'oemExecuted':False},indent=2)+'\n')

def elf_view(path):
 data=Path(path).read_bytes();parser=ROOT/'tools/audit_security_native_linkage.py';base=runpy.run_path(str(parser))['elf'](data)
 off=struct.unpack_from('<Q',data,40)[0];size,count,ni=struct.unpack_from('<HHH',data,58);assert size==64
 sections=[struct.unpack_from('<IIQQQQIIQQ',data,off+64*n) for n in range(count)]
 for row,s in zip(base['sections'],sections):row['flags']=s[2]
 namesec=sections[ni];names=data[namesec[4]:namesec[4]+namesec[5]]
 def text(blob,p):return blob[p:blob.index(0,p)].decode('utf8')
 byname={text(names,s[0]):s for s in sections};dyn=byname['.dynsym'];strsec=sections[dyn[6]];strings=data[strsec[4]:strsec[4]+strsec[5]]
 versions={}
 for secname in ['.gnu.version_d','.gnu.version_r']:
  if secname not in byname:continue
  sec=byname[secname];p=sec[4];end=p+sec[5]
  while p<end:
   if secname.endswith('_d'):
    _,flags,index,n,_,aux,nxt=struct.unpack_from('<HHHHIII',data,p)
    name,_=struct.unpack_from('<II',data,p+aux);versions[index]={'name':text(strings,name),'definition':True}
   else:
    _,n,file,aux,nxt=struct.unpack_from('<HHIII',data,p);q=p+aux
    for _ in range(n):
     _,flags,index,name,anext=struct.unpack_from('<IHHII',data,q)
     versions[index&0x7fff]={'name':text(strings,name),'neededLibrary':text(strings,file),'definition':False}
     if not anext:break
     q+=anext
   if not nxt:break
   p+=nxt
 versym=byname.get('.gnu.version');syms=[]
 for index,p in enumerate(range(dyn[4],dyn[4]+dyn[5],24)):
  name,info,other,section,value,extent=struct.unpack_from('<IBBHQQ',data,p)
  vi=None if versym is None else struct.unpack_from('<H',data,versym[4]+2*index)[0]
  syms.append({'index':index,'name':text(strings,name),'value':value,'bytes':extent,'binding':info>>4,'type':info&15,'visibility':other&3,'sectionIndex':section,'versionIndex':vi,'symbolVersion':None if vi is None else versions.get(vi&0x7fff)})
 dynamics=[]
 for s in sections:
  if s[1]==6:
   for p in range(s[4],s[4]+s[5],16):
    tag,value=struct.unpack_from('<qQ',data,p)
    if tag in (16,30,0x6ffffffb):dynamics.append({'tag':tag,'value':value})
 interp=[];segments=[];phoff=struct.unpack_from('<Q',data,32)[0];phsize,phnum=struct.unpack_from('<HH',data,54)
 for n in range(phnum):
  p=phoff+n*phsize;kind,flags,fo,va,pa,fs,ms,align=struct.unpack_from('<II6Q',data,p)
  if kind==3:interp.append(data[fo:fo+fs].rstrip(b'\0').decode())
  if kind in (0x6474e552,0x6474e551):segments.append({'type':kind,'flags':flags,'offset':fo,'address':va,'bytes':fs})
 return data,base,syms,dynamics,interp,segments

def inspect():
 parser=ROOT/'tools/audit_security_native_linkage.py';parser_pin=sha(parser)
 paths={k:ROOT/p for k,(p,_) in EXISTING.items()}
 paths.update({Path(p).name:RAW/p for p in MEMBERS})
 for k,(p,h) in EXISTING.items():assert sha(ROOT/p)==h
 for p,h in MEMBERS.items():assert sha(RAW/p)==h
 views={};symbols={}
 for role,path in paths.items():
  data,base,syms,tags,interp,segments=elf_view(path)
  selected=[s for s in syms if any(k in s['name'] for k in ['property_get','system_property_','GetProperty','GetBoolProperty','GetServerConfigurableFlag','JNI_CreateJavaVM','AndroidRuntime7startVm'])]
  views[role]={'path':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),'sha256':sha(path),'bytes':len(data),'needed':base['needed'],'selectedDynamicSymbols':selected,'selectedDynamicTags':tags,'selectedProgramHeaders':segments,'interpreter':interp,'machine':base['machine']}
  local=base['dynamicSymbols']
  for sec in base['sections']:
   if sec['name']=='.gnu_debugdata':
    mini=lzma.decompress(data[sec['offset']:sec['offset']+sec['bytes']]);assert len(mini)<16*1024*1024
    local=local+runpy.run_path(str(parser))['elf'](mini)['dynamicSymbols']
  symbols[role]=[s for s in local if any(x in s['name'] for x in ['property_get','system_property_','GetProperty','GetBoolProperty','LD_PRELOAD','linker_main','find_libraries','lookup_version','check_symbol_version','linker_init_post'])]
 assert sha(parser)==parser_pin
 RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 (RAW/'selected-symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')
 report={'scope':'selected ELF imports/exports/flags and exact helper symbol discovery only','parserSha256':parser_pin,'views':views,'symbolDiscoveryRaw':'firmware/samsung-vm-property-view/selected-symbols.json','symbolDiscoveryRawSha256':sha(RAW/'selected-symbols.json'),'oemExecuted':False}
 (OUT/'elf-views.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'elfFiles':len(views),'selectedSymbols':{k:len(v) for k,v in symbols.items()},'oemExecuted':False}))

def capture():
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'))
 import capstone
 decoder=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);decoder.detail=True
 discovery=json.loads((RAW/'selected-symbols.json').read_text())
 wanted={'libbase.so':['GetPropertyERK','GetBoolPropertyERK'],'libcutils.so':['property_get'],
         'libc.so':['__system_property_find','__system_property_get','__system_property_read_callback'],
         'linker64':['__dl__ZL29__linker_init_post_relocationR19KernelArgumentBlockR6soinfo']}
 functions=[]
 for role,names in wanted.items():
  path=next(RAW/p for p in MEMBERS if Path(p).name==role);data,base,dyn,*_=elf_view(path)
  symbols=list(base['dynamicSymbols'])
  for s in base['sections']:
   if s['name']=='.gnu_debugdata':symbols+=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'](lzma.decompress(data[s['offset']:s['offset']+s['bytes']]))['dynamicSymbols']
  def offset(address,size=1):
   s,=[s for s in base['sections'] if s['flags']&2 and s['type']!=8 and s['address']<=address and address+size<=s['address']+s['bytes']]
   return s['offset']+address-s['address']
  def string(address):
   try:
    p=offset(address);end=data.index(0,p,min(len(data),p+256));b=data[p:end]
    return b.decode() if b and all(32<=v<127 for v in b) else None
   except (ValueError,UnicodeError):return None
  def target_name(address):
   found=[s['name'] for s in symbols if s['sectionIndex'] and s['type']==2 and s['value']==address]
   if found:return {'symbol':found[0],'bindingKind':'direct-local'}
   plt=[s for s in base['sections'] if s['name']=='.plt' and s['address']<=address<s['address']+s['bytes']]
   if plt:
    po=offset(address,24);page=None
    for i in decoder.disasm(data[po:po+24],address):
     if i.mnemonic=='adrp' and i.op_str.startswith('x16,'):page=int(i.op_str.split('#')[1],0)
     if i.mnemonic=='ldr' and i.op_str.startswith('x17,') and page is not None:
      match=re.search(r'#(0x[0-9a-f]+|\d+)',i.op_str);got=page+(int(match.group(1),0) if match else 0)
      rel=[r for r in base['rela'] if r['target']==got and r['type']==1026]
      if len(rel)==1:return {'symbol':dyn[rel[0]['symbolIndex']]['name'],'bindingKind':'plt-import','relocationTarget':got,'relocationType':1026,'symbolIndex':rel[0]['symbolIndex']}
   return None
  selected={}
  for name in names:
   candidates=[s for s in symbols if s['sectionIndex'] and s['type']==2 and s['size'] and (s['name']==name if name.startswith(('property_','__system_','__dl_')) else s['name'].startswith('_ZN7android4base') and name in s['name'])]
   for s in candidates:selected[s['value']]=s
  assert len(selected)==len(names),(role,len(selected),names)
  for s in selected.values():
   po=offset(s['value'],s['size']);body=data[po:po+s['size']];rows=[];pages={}
   for ins in decoder.disasm(body,s['value']):
    row={'pc':ins.address,'bytes':ins.bytes.hex(),'mnemonic':ins.mnemonic,'operands':ins.op_str}
    if ins.mnemonic=='adrp':reg,val=ins.op_str.split(', ');pages[reg]=(int(val[1:],0),ins.address)
    if ins.mnemonic=='add' and len(ins.operands)==3 and ins.operands[2].type==capstone.CS_OP_IMM:
     reg=ins.reg_name(ins.operands[1].reg)
     if reg in pages and ins.address-pages[reg][1]<=40:
      address=pages[reg][0]+ins.operands[2].imm;value=string(address)
      if value:row.update(literal=value,literalAddress=address,adrpPc=pages[reg][1])
    if ins.mnemonic in ('bl','b') and ins.op_str.startswith('#0x'):
     target=int(ins.op_str[1:],16);resolved=target_name(target)
     if resolved:row.update(target=target,**resolved)
    rows.append(row)
   assert len(rows)*4==len(body)
   functions.append({'role':role,'source':str(path.relative_to(ROOT)),'sourceSha256':sha(path),'symbol':s['name'],'address':s['value'],'fileOffset':po,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'instructions':rows})
 (RAW/'selected-native.json').write_text(json.dumps({'functions':functions,'annotationLimits':'bounded ADRP/ADD annotations; not general dataflow, emulation or OEM execution','oemExecuted':False},indent=2)+'\n')
 (OUT/'native-capture.json').write_text(json.dumps({'raw':'firmware/samsung-vm-property-view/selected-native.json','rawSha256':sha(RAW/'selected-native.json'),'capstoneVersion':capstone.__version__,'functions':[{k:v for k,v in f.items() if k!='instructions'} for f in functions],'oemExecuted':False},indent=2)+'\n')
 print(json.dumps({'functions':len(functions),'instructions':sum(len(f['instructions']) for f in functions),'oemExecuted':False}))

def audit():
 receipt=json.loads((OUT/'native-capture.json').read_text());assert sha(ROOT/receipt['raw'])==receipt['rawSha256']
 native=json.loads((ROOT/receipt['raw']).read_text());index={}
 for f in native['functions']:
  data=(ROOT/f['source']).read_bytes();assert hashlib.sha256(data).hexdigest()==f['sourceSha256']
  body=data[f['fileOffset']:f['fileOffset']+f['bytes']]
  assert hashlib.sha256(body).hexdigest()==f['sha256'] and b''.join(bytes.fromhex(i['bytes']) for i in f['instructions'])==body
  for i in f['instructions']:index[(f['role'],i['pc'])]=i
 vmraw=ROOT/'firmware/authority-vm-options/selected-native.json'
 assert sha(vmraw)=='dc90bc834e5af30ab05bb63e93530b4b067e6c66c68a230b271a07613768dccd'
 vm=json.loads(vmraw.read_text());data=(ROOT/EXISTING['runtime'][0]).read_bytes()
 for f in vm['functions']:
  body=data[f['fileOffset']:f['fileOffset']+f['bytes']];assert hashlib.sha256(body).hexdigest()==f['sha256']
  assert b''.join(bytes.fromhex(i['bytes']) for i in f['instructions'])==body
  for i in f['instructions']:index[('runtime',i['pc'])]=i
 peer=ROOT/'inventory/samsung-authority-vm-launch.json';assert sha(peer)=='34f768f6abfcc3a6e0fc65350d5ae82556319bbb9613ead84909e6cdf1a42a60'
 pi=json.loads(peer.read_text());pr=pi['newRaw'];assert sha(ROOT/pr['path'])==pr['sha256']
 ps=json.loads((ROOT/pr['path']).read_text())['sources'][0];assert ps['sha256']=='69dde39d705ae09a98dc17e1ed77d040d85dd8400dbdb42440ff0ae81f941169'
 pb=(ROOT/ps['path']).read_bytes();assert hashlib.sha256(pb).hexdigest()==ps['sha256']
 for f in ps['functions']:
  body=pb[f['fileOffset']:f['fileOffset']+f['bytes']];assert hashlib.sha256(body).hexdigest()==f['sha256'] and b''.join(bytes.fromhex(i['bytes']) for i in f['instructions'])==body
  for i in f['instructions']:index[('server-flags',i['pc'])]=i
 checks=[]
 def check(role,pc,key,expected):
  assert index[(role,pc)][key]==expected,(role,hex(pc),key,index[(role,pc)].get(key),expected)
  checks.append({'role':role,'pc':pc,'pcHex':hex(pc),'field':key,'expected':expected})
 for role,pc,target in [('libcutils.so',0xd9a4,'__system_property_get'),('libbase.so',0x17668,'__system_property_find'),('libbase.so',0x17680,'__system_property_read_callback')]:
  check(role,pc,'symbol',target);check(role,pc,'bindingKind','plt-import')
 check('libbase.so',0x1766c,'operands','x0, #0x176d8')
 prop='_ZN7android4base11GetPropertyERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEES9_'
 check('libbase.so',0x181a0,'symbol',prop);check('libbase.so',0x181a0,'bindingKind','plt-import')
 check('libbase.so',0x17648,'operands','x19, x8')
 check('server-flags',0x4794,'literal','persist.device_config.');check('server-flags',0x4938,'targetSymbol',prop)
 for pc,key,value in [(0x1a5fcc,'operands','w0, #0x17'),(0x1a5fd0,'symbol','__dl_getauxval'),(0x1a5fd4,'operands','x0, #0x1a64e8'),(0x1a64ec,'literal','LD_LIBRARY_PATH'),(0x1a64f0,'symbol','__dl_getenv'),(0x1a6508,'literal','LD_PRELOAD'),(0x1a650c,'symbol','__dl_getenv')]:check('linker64',pc,key,value)
 for pc,key,value in [(0x184924,'targetSymbol','_ZN7android4base15GetBoolPropertyERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEEb'),(0x184994,'targetSymbol','_ZN25server_configurable_flags25GetServerConfigurableFlagERKNSt3__112basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEES8_S8_'),(0x1849fc,'literal','dalvik.vm.boot-image'),(0x184ef0,'literal','dalvik.vm.usejit'),(0x185558,'literal','dalvik.vm.extra-opts'),(0x185b74,'operands','w8, #4'),(0x185b7c,'operands','w8, #1, lsl #16'),(0x185b80,'operands','w8, [x29, #-0xa8]'),(0x185b88,'operands','x0, [x29, #-0xa0]'),(0x185b90,'operands','x8, [x21, #0x18]'),(0x185b94,'operands','x2, x29, #0xa8'),(0x185b98,'operands','wzr, [x26, #0xe8]'),(0x185b9c,'operands','w8, [x29, #-0xa4]'),(0x185ba0,'operands','#0x1860dc'),(0x185ba0,'targetSymbol','JNI_CreateJavaVM'),(0x185ba8,'operands','w0, #0x1f, #0x185ea8')]:check('runtime',pc,key,value)
 views=json.loads((OUT/'elf-views.json').read_text())['views']
 for role,name,defined in [('runtime','property_get',False),('libcutils.so','property_get',True),('runtime',prop,False),('libbase.so',prop,True),('runtime','JNI_CreateJavaVM',True)]:
  s,=[s for s in views[role]['selectedDynamicSymbols'] if s['name']==name]
  assert s['binding']==1 and s['visibility']==(3 if name=='JNI_CreateJavaVM' else 0) and bool(s['sectionIndex'])==defined and s['versionIndex']==1
 for name,version in [('__system_property_find','LIBC'),('__system_property_get','LIBC'),('__system_property_read_callback','LIBC_O')]:
  s,=[s for s in views['libc.so']['selectedDynamicSymbols'] if s['name']==name]
  assert s['symbolVersion']=={'name':version,'definition':True}
 assert views['runtime']['selectedDynamicTags']==[{'tag':30,'value':8},{'tag':0x6ffffffb,'value':1}]
 assert any(x['type']==0x6474e552 for x in views['runtime']['selectedProgramHeaders'])
 result={'scope':'native source/ELF checks only; no interception/optiongate/runtime proof','sourceAssertions':checks,'ownNativeFunctions':7,'ownInstructions':1464,'reusedRuntimeRaw':{'path':str(vmraw.relative_to(ROOT)),'sha256':sha(vmraw)},'reusedServerFlagProof':{'inventory':str(peer.relative_to(ROOT)),'sha256':sha(peer),'raw':pr['path'],'rawSha256':pr['sha256']},'directJniPreloadCounterexample':{'callPc':0x185ba0,'directTarget':0x1860dc,'targetKind':'actual local definition; not PLT','exportVisibility':'STV_PROTECTED(3)','exportAloneInterposesThisCall':False},'candidatePropertySymbols':['property_get',prop],'jniInitArgsObserved':{'version':0x10004,'countOffset':4,'optionsPointerOffset':8,'ignoreUnrecognizedOffset':16,'ignoreUnrecognized':False,'argumentPointerPc':0x185b94},'oemExecuted':False,'nativeExecuted':False,'artExecuted':False,'phoneActions':False,'toolSha256':sha(__file__)}
 (OUT/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'sourceAssertions':len(checks),'ownNativeFunctions':7,'jniVersion':hex(0x10004),'interposerImplemented':False,'oemExecuted':False}))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--extract',action='store_true');ap.add_argument('--capture',action='store_true');a=ap.parse_args()
 if a.extract:extract()
 inspect()
 if a.capture:capture()
 audit()
