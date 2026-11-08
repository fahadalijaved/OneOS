"""Captured Samsung boot-classpath config/cohort provenance; offline only."""
import argparse,gzip,hashlib,json,lzma,runpy,sys,tarfile,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
RAW=ROOT/'firmware/samsung-boot-classpath-cohort';OUT=ROOT/'out/samsung-boot-classpath-cohort'
DIFF=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
MANIFEST=DIFF/'samsung-manifest.jsonl.gz';MANIFEST_SHA='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
INIT='system/etc/init/hw/init.rc';DERIVE='apex/com.android.sdkext/bin/derive_classpath';RC='apex/com.android.sdkext/etc/derive_classpath.rc'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def manifest():
 assert sha(MANIFEST)==MANIFEST_SHA
 with gzip.open(MANIFEST,'rt')as f:return{r['path']:r for line in f if(r:=json.loads(line))}
def config_paths(rows):
 return sorted(p for p in rows if p.endswith('/etc/classpaths/bootclasspath.pb')and '@'not in p)+[INIT,DERIVE,RC]
def extract():
 rows=manifest();wanted=set(config_paths(rows));proof=[];assert TAR.stat().st_size==20434769920
 for n in list(wanted):
  p=RAW/'captured'/n
  if p.exists():assert sha(p)==rows[n]['sha256'];wanted.remove(n)
 if not wanted:return
 with tarfile.open(TAR,'r:')as tar:
  for m in tar:
   n=m.name.removeprefix('./')
   if n not in wanted:continue
   row=rows[n];assert m.isfile()and row['kind']=='file'and m.size==row['size']and m.size<1024*1024
   b=tar.extractfile(m).read(m.size+1);assert len(b)==m.size and hashlib.sha256(b).hexdigest()==row['sha256']
   p=RAW/'captured'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
   proof.append({'member':n,'headerOffset':m.offset,'dataOffset':m.offset_data,'bytes':len(b),'sha256':row['sha256']});wanted.remove(n)
   if not wanted:break
 assert not wanted
 old=json.loads((OUT/'acquisition.json').read_text())['members']if(OUT/'acquisition.json').exists()else[]
 proof={x['member']:x for x in old+proof}
 save(OUT/'acquisition.json',{'sourceTar':str(TAR),'priorStrictReceipt':str(DIFF/'report.json'),'priorStrictReceiptSha256':sha(DIFF/'report.json'),'fullTarRehashed':False,'scope':'Named boot fragments/init/derive producer only; no jars or full tree','members':[proof[n]for n in sorted(proof)],'oemExecuted':False})
def wire(data):
 if len(data)>65536:raise ValueError('Bounded config required')
 pos=0;result=[]
 def varint():
  nonlocal pos
  n=0
  for shift in range(0,70,7):
   if pos>=len(data):raise ValueError('Truncated varint')
   b=data[pos];pos+=1;n|=(b&127)<<shift
   if not b&128:return n
  raise ValueError('Oversized varint')
 while pos<len(data):
  start=pos;tag=varint();field=tag>>3;kind=tag&7
  if field==0:raise ValueError('Zero field')
  if kind==0:value=varint()
  elif kind==2:
   length=varint()
   if pos+length>len(data):raise ValueError('Length overrun')
   value=data[pos:pos+length];pos+=length
  else:raise ValueError('Unadmitted protobuf wire kind')
  result.append({'field':field,'kind':kind,'offset':start,'value':value})
 return result
def fragment(data):
 out=[]
 for top in wire(data):
  if(top['field'],top['kind'])!=(1,2):raise ValueError('Unknown top-level config field')
  fields=wire(top['value']);values={}
  for f in fields:
   if f['field']in values or(f['field'],f['kind'])not in[(1,2),(2,0),(3,2),(4,2)]:raise ValueError('Duplicate/unadmitted jar field')
   v=f['value'];values[f['field']]=v.decode('ascii')if isinstance(v,bytes)else v
  path=values.get(1)
  if not path or not path.startswith(('/system/','/apex/','/system_ext/','/product/'))or not path.endswith('.jar')or '..'in path.split('/'):raise ValueError('Unadmitted jar path')
  out.append({'ordinal':len(out),'messageOffset':top['offset'],'path':path,'classpathRaw':values.get(2,0),'minSdkRaw':values.get(3,''),'maxSdkRaw':values.get(4,'')})
 return out
def discover():
 rows=manifest();configs=[]
 for n in config_paths(rows):
  p=RAW/'captured'/n;assert sha(p)==rows[n]['sha256']
  if n.endswith('.pb'):configs.append({'path':n,'sha256':sha(p),'entries':fragment(p.read_bytes())})
 save(OUT/'decoded-fragments.json',configs)
 parse=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];p=RAW/'captured'/DERIVE;b=p.read_bytes();elf=parse(b);syms=elf['dynamicSymbols'];debug=next((s for s in elf['sections']if s['name']=='.gnu_debugdata'),None)
 if debug:
  mini=lzma.decompress(b[debug['offset']:debug['offset']+debug['bytes']]);assert len(mini)<16*1024*1024;syms+=parse(mini)['dynamicSymbols']
 save(RAW/'producer-symbols.json',{'sourceSha256':sha(p),'sections':elf['sections'],'symbols':syms,'needed':elf['needed'],'oemExecuted':False})
 print(json.dumps({'configFragments':len(configs),'entries':sum(len(x['entries'])for x in configs),'rawCategories':sorted({e['classpathRaw']for c in configs for e in c['entries']}),'producerSymbols':[s for s in syms if s['sectionIndex']and s['type']==2 and any(k in s['name']for k in['main','Classpath','classpath','Generate','Export','ReadConfig','Derive'])][:35]}))
def native():
 rows=manifest();path=RAW/'captured'/DERIVE;assert sha(path)==rows[DERIVE]['sha256'];b=path.read_bytes()
 parse=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];p=parse(b);sections=p['sections'];syms=json.loads((RAW/'producer-symbols.json').read_text())['symbols'];relocs={r['target']:r for r in p['rela']}
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'));import capstone
 cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);cs.detail=True
 def off(addr,size=1):
  s,=[s for s in sections if s['type']!=8 and s['address']<=addr and addr+size<=s['address']+s['bytes']];return s['offset']+addr-s['address']
 def string(addr):
  try:
   n=off(addr);end=b.index(b'\0',n,min(len(b),n+512));v=b[n:end]
   return v.decode('ascii')if v and all(32<=c<127 or c in[9,10,13]for c in v)else None
  except(ValueError,UnicodeError):return None
 plt,=[s for s in sections if s['name']=='.plt']
 def call(addr):
  if plt['address']<=addr<plt['address']+plt['bytes']:
   stub=list(cs.disasm(b[off(addr,24):off(addr,24)+24],addr));a=next(i for i in stub if i.mnemonic=='adrp'and i.op_str.startswith('x16,'));l=next(i for i in stub if i.mnemonic=='ldr'and i.op_str.startswith('x17,'));d=re.search(r'#(0x[0-9a-f]+|\d+)',l.op_str);got=int(a.op_str.split('#')[1],16)+(int(d.group(1),0)if d else 0);r=relocs[got];return p['dynamicSymbols'][r['symbolIndex']]['name']
  found=[s['name']for s in syms if s['sectionIndex']and s['value']==addr];return found[0]if found else None
 functions=[];wanted=['main','_Z14Classpath_Name9Classpath','_ZN7android16derive_classpath14ParseFragments','_ZN7android16derive_classpath24GenerateClasspathExports','_GLOBAL__sub_I_derive_classpath.cpp']
 for s in syms:
  if not s['sectionIndex']or s['type']!=2 or not s['size']or not any(s['name']==k or s['name'].startswith(k)for k in wanted):continue
  offset=off(s['value'],s['size']);body=b[offset:offset+s['size']];insns=[];known={}
  for i in cs.disasm(body,s['value']):
   x={'pc':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str};assigned=None
   if i.mnemonic in['adr','adrp']:assigned=(i.reg_name(i.operands[0].reg),i.operands[1].imm)
   if i.mnemonic=='add'and len(i.operands)==3 and i.operands[2].type==capstone.CS_OP_IMM:
    src=i.reg_name(i.operands[1].reg)
    if src in known:assigned=(i.reg_name(i.operands[0].reg),known[src]+(i.operands[2].imm<<i.operands[2].shift.value))
   if assigned:
    text=string(assigned[1]);x['addressPair']=assigned[1]
    if text:x['literal']=text
   if i.mnemonic in['b','bl']and i.op_str.startswith('#0x'):
    target=call(int(i.op_str[1:],16))
    if target:x['targetSymbol']=target
   for reg in i.regs_access()[1]:known.pop(i.reg_name(reg),None)
   if i.mnemonic in['bl','blr']:
    for reg in range(19):known.pop('x'+str(reg),None)
   if assigned:known[assigned[0]]=assigned[1]
   insns.append(x)
  assert len(insns)*4==len(body)
  functions.append({'symbol':s['name'],'address':s['value'],'bytes':len(body),'fileOffset':offset,'sha256':hashlib.sha256(body).hexdigest(),'instructions':insns})
 assert len(functions)==5
 enums=[]
 for n in range(5):
  pointer,length,value,padding=struct.unpack_from('<QQiI',b,off(0x82c68+n*24,24));assert 0<length<=64 and padding==0
  name=b[off(pointer,length):off(pointer,length)+length].decode('ascii');assert re.fullmatch(r'[A-Z0-9_]+',name)
  enums.append({'tableEntryAddress':0x82c68+n*24,'nameAddress':pointer,'name':name,'value':value,'length':length})
 save(RAW/'producer-native.json',{'source':DERIVE,'sourceSha256':sha(path),'pcKind':'ELF virtual address, not live address','functions':functions,'enumTable':{'address':0x82c68,'sourceAnchorPc':0x55e50,'countPc':0x55e5c,'entries':enums},'oemExecuted':False})
 print(json.dumps({'functions':len(functions),'instructions':sum(len(f['instructions'])for f in functions),'oemExecuted':False}))
def audit():
 rows=manifest();configs=[];inputs=[];tests=[]
 for n in config_paths(rows):
  path=RAW/'captured'/n;assert sha(path)==rows[n]['sha256']
  inputs.append({'capturedPath':'/'+n,'rawPath':path.relative_to(ROOT).as_posix(),'bytes':rows[n]['size'],'sha256':rows[n]['sha256']})
  if n.endswith('.pb'):configs.append({'capturedPath':'/'+n,'sha256':rows[n]['sha256'],'entries':fragment(path.read_bytes())})
 base=PARENT/'out/os-comparison-resumed/samsung-inventory.json';meta=json.loads(base.read_text());bcmeta=meta['queries']['bootclasspath'];bcfile=PARENT/bcmeta['file'];assert sha(bcfile)==bcmeta['sha256']=='524b012a77f96ab580ae9a7d25ad14ec1d8620fdc08b6c5cd6d8e2e7288858d1'
 bcp=bcfile.read_text().strip().split(':');assert len(bcp)==61 and len(set(bcp))==61
 rawpath=RAW/'producer-native.json';raw=json.loads(rawpath.read_text());producer=(RAW/'captured'/DERIVE).read_bytes();ix={i['pc']:i for f in raw['functions']for i in f['instructions']}
 assert len(raw['functions'])==5
 for f in raw['functions']:
  body=producer[f['fileOffset']:f['fileOffset']+f['bytes']];assert hashlib.sha256(body).hexdigest()==f['sha256']and b''.join(bytes.fromhex(i['bytes'])for i in f['instructions'])==body
 def check(pc,key,wanted):
  assert ix[pc][key]==wanted,(hex(pc),key,wanted);tests.append({'pc':pc,'pcHex':hex(pc),'field':key,'expected':wanted})
 for pc,expected in[(0x491ec,'w2, #1'),(0x4920c,'w2, wzr'),(0x471d4,'w21, #0, #0x4730c'),(0x471e0,'x21, #0x85550'),(0x47cc8,'w1, #8'),(0x55e50,'x0, #0x82c68'),(0x55e5c,'w2, #5'),(0x54b18,'x8, x8, #0x9a7'),(0x54b60,'x9, x9, #0x142')]:check(pc,'operands',expected)
 for pc,word in[(0x491d0,'android_get_device_api_level'),(0x491fc,'ParseFragments'),(0x49210,'ParseFragments'),(0x47ce0,'glob'),(0x48220,'ReadFileToString'),(0x49bdc,'WriteStringToFile')]:assert word in ix[pc]['targetSymbol'];tests.append({'pc':pc,'pcHex':hex(pc),'targetContains':word})
 # Exact generated EnumEntry(name pointer,length,value,padding) table, linked
 # by Classpath_Name's actual ADR and count instructions. Names are not C strings.
 enums={}
 for n in range(5):
  pointer,length,value,padding=struct.unpack_from('<QQiI',producer,0x82c68+n*24);assert 0<length<=64 and padding==0
  enums[value]=producer[pointer:pointer+length].decode('ascii')
 assert enums=={1:'BOOTCLASSPATH',3:'DEX2OATBOOTCLASSPATH',4:'STANDALONE_SYSTEMSERVER_JARS',2:'SYSTEMSERVERCLASSPATH',0:'UNKNOWN'}
 assert producer[0x39a7:0x39a7+33]==b'/etc/classpaths/bootclasspath.pb\0'and producer[0x3142:0x3142+41]==b'/etc/classpaths/systemserverclasspath.pb\0'
 bypath={}
 for c in configs:
  for e in c['entries']:
   e['classpath']=enums[e['classpathRaw']]
   if e['classpathRaw']==1:
    assert e['path']not in bypath;bypath[e['path']]={'config':c['capturedPath'],**e}
 assert len(configs)==30 and len(bypath)==61 and set(bypath)==set(bcp)
 apexmeta=meta['queries']['apex-info'];apexfile=PARENT/apexmeta['file'];assert sha(apexfile)==apexmeta['sha256']=='6c8ebe0b93c4f9147d568678fd7909d748ff17e4211eb71255fa0fc6a801e8af'
 apex=[dict(x.attrib)for x in ET.fromstring(apexfile.read_text()).findall('apex-info')]
 cohort=[]
 for i,location in enumerate(bcp):
  key=location.removeprefix('/');r=rows[key];assert r['kind']=='file'and r['sha256']and r['size']>0
  aliases=[];module=None;active=[]
  if location.startswith('/apex/'):
   module=location.split('/')[2];suffix='/'.join(location.split('/')[3:])
   aliases=[{'path':'/'+n,'kind':x['kind'],'bytes':x['size'],'sha256':x.get('sha256'),'matchesCapturedActiveBytes':x.get('sha256')==r['sha256']}for n,x in rows.items()if n.startswith('apex/'+module+'@')and n.endswith('/'+suffix)]
   active=[{k:x.get(k)for k in('moduleName','modulePath','preinstalledModulePath','versionCode','isActive','isFactory')}for x in apex if x.get('moduleName')==module and x.get('isActive')=='true']
  cohort.append({'index':i,'location':location,'bytes':r['size'],'sha256':r['sha256'],'fragment':bypath[location],'apexModule':module,'capturedVersionedAliasEntries':aliases,'capturedActiveApexInfo':active,'runtimeAdmitted':False})
 canonical=[{k:x[k]for k in('index','location','bytes','sha256')}for x in cohort]
 cohort_sha=hashlib.sha256(json.dumps(canonical,separators=(',',':')).encode()).hexdigest()
 for c in configs:
  positions=[bcp.index(e['path'])for e in c['entries']if e['classpathRaw']==1];assert positions==sorted(positions)
  c['indicesInCapturedBcp']=positions
 init=(RAW/'captured'/INIT).read_text().splitlines();rc=(RAW/'captured'/RC).read_text()
 assert init[6]=='import /init.environ.rc'and 'exec_start derive_classpath'in init[1353]and 'load_exports /data/system/environ/classpath'in init[1354]and 'exec_start art_boot'in init[1359]
 assert 'service derive_classpath /apex/com.android.sdkext/bin/derive_classpath'in rc and all(x in rc for x in['user system','group system reserved_disk','oneshot','disabled'])
 assert not any(p.endswith('init.environ.rc')for p in rows)and not any('data/system/environ/classpath'in p for p in rows)
 # Adversarial wire fixtures only; no protobuf/native implementation executes.
 invalid=[b'\x00',b'\x0a\x80',b'\x0a\x03x',b'\x09'+b'\0'*8,b'\x0a\x04\x10\x01\x10\x01']
 for d in invalid:
  try:fragment(d)
  except(ValueError,UnicodeError):pass
  else:raise AssertionError('Malformed protobuf accepted')
 scalarpath=ROOT/'inventory/context-metrics-scalar-implementation.json';scalar=json.loads(scalarpath.read_text());assert scalar['selected']is False and scalar['wholeFrameworkProduced']is False and scalar['runtimeCohortProduced']is False
 preserved={'docs/authority-boot-framework.md':'498c2fc83901a8a34d6902b7135d771f8d5e46f8a72d8a8192ff8a6472b742fc','docs/authority-vm-options.md':'6a844f305d30877f3bae7e1fb79d04db32f84c1b2a48a5c5ae0634fffc353d18','docs/authority-art-option-selection.md':'3598c91fbdc33fbc4098516572aee7a5409f44660248ba4a3d501ac69cd99be8','docs/retained-authority-control.md':'1d3cc146e87f1c709dedbfddca7fed539eec43e101785108ce548e2d7a691d97','tools/collect_authority_topology.py':'a752ed0866ac9aee610ab2e002f11be09aaf811fd9fb53aa3da4133e479f2ace','docs/authority-topology-capture.md':'c465c5df2f64d2ce69631928a2a825ee4e7c2e7a2396303c5fe9f645b4f7f54a','inventory/authority-topology-capture.json':'bb19affbaf10963fd38e53e9a362421a88adda30cd0c604abcc22f72e054735a'}
 for p,pin in preserved.items():assert sha(ROOT/p)==pin
 inv={'schema':'samsung-boot-classpath-cohort-provenance/v1','status':'ORIGINAL_CAPTURED_CANDIDATE_COHORT_ONLY; no edited cohort, boot artifact or runtime selected','selected':False,'oemExecuted':False,'adbInvoked':False,'networkUsed':False,'manifest':{'path':str(MANIFEST),'sha256':MANIFEST_SHA},'configInputs':inputs,'configFragments':configs,'enumMapping':enums,
      'capturedBcpMetadata':{'path':str(bcfile),'sha256':bcmeta['sha256'],'exitCode':bcmeta['exitCode'],'orderBasis':'Captured metadata list only, not current/init/system_server/future VM environment proof'},'capturedApexMetadata':{'path':str(apexfile),'sha256':apexmeta['sha256']},'orderedOriginalCandidateJars':cohort,'orderedCandidateCanonicalSha256':cohort_sha,
      'configCoverage':{'fragments':30,'bootEntries':61,'dex2oatBootEntries':sum(e['classpathRaw']==3 for c in configs for e in c['entries']),'capturedSetEqual':True,'withinFragmentOrderAgrees':True,'globalProducerEnumerationFullyReconstructed':False},'nativeProducer':{'path':rawpath.relative_to(ROOT).as_posix(),'sha256':sha(rawpath),'sourceSha256':rows[DERIVE]['sha256'],'functions':[{k:v for k,v in f.items()if k!='instructions'}for f in raw['functions']],'checks':tests},
      'initEdges':[{'file':'/'+INIT,'line':7,'edge':'imports /init.environ.rc; uncaptured root file'},{'file':'/'+INIT,'line':1354,'edge':'exec_start derive_classpath'},{'file':'/'+INIT,'line':1355,'edge':'load_exports /data/system/environ/classpath; uncaptured generated output'},{'file':'/'+INIT,'line':1360,'edge':'exec_start art_boot after classpath loading'}],
      'editBoundary':{'originalFrameworkIndex':5,'originalFrameworkSha256':cohort[5]['sha256'],'wholeEditedFrameworkSelected':False,'authoredHelperBootEntriesSelected':[],'diagnosticScalarInventory':{'path':scalarpath.relative_to(ROOT).as_posix(),'sha256':sha(scalarpath),'wholeFrameworkProduced':False,'runtimeCohortProduced':False,'projectionArtifactSha256':scalar['summary']['artifactSha256']},'rule':'A future edited whole-framework component must have its own preservation/source/HAPI receipt and exact output hash at the intended boot slot; helper containers need explicit same-boot visibility/definition closure. A method projection or app-classpath helper does not supply that cohort.'},
      'remaining':['Exact /init.environ.rc and generated classpath output outside capture; no new pull','Current/future process environment, active APEX/linker/mount views and exact file identities before first resolution','Global fragment ordering/filtering and SDK/codename eligibility must not be inferred from filename sorting; candidate order is captured metadata','Actual edited framework plus all boot-visible helpers and native/resource dependencies; no helpers selected here','Property/final VM vector owners from Detail and UI workers plus actual Context bootstrap/input lifecycle'],
      'preservedPins':[{'path':p,'sha256':v}for p,v in preserved.items()]}
 assert cohort[5]['location']=='/system/framework/framework.jar'and cohort[5]['sha256']=='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
 dest=ROOT/'inventory/samsung-boot-classpath-cohort.json';save(dest,inv)
 save(OUT/'original-candidate-jars.json',{'selected':False,'canonicalSha256':cohort_sha,'orderBasis':'captured metadata','jars':canonical});save(OUT/'checks.json',{'pass':True,'configFiles':len(inputs),'fragments':30,'bootEntries':61,'dex2oatBootEntries':22,'nativeFunctions':5,'nativeAssertions':len(tests),'malformedWireRefusals':len(invalid),'oemExecuted':False,'selected':False})
 paths=[Path(__file__),ROOT/'docs/samsung-boot-classpath-cohort.md',dest,OUT/'acquisition.json',OUT/'original-candidate-jars.json',OUT/'checks.json',rawpath]
 save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'oemExecuted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in paths]})
 print(json.dumps({'pass':True,'configFiles':len(inputs),'fragments':30,'candidateJars':61,'nativeFunctions':5,'nativeAssertions':len(tests),'malformedWireRefusals':len(invalid),'selected':False,'oemExecuted':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--extract',action='store_true');p.add_argument('--discover',action='store_true');p.add_argument('--native',action='store_true');a=p.parse_args()
 if a.extract:extract()
 if a.discover:discover()
 if a.native:native()
 if not(a.extract or a.discover or a.native):audit()
