"""Cold, UNSELECTED two-catch-tail ColorOS DEX leaf. Never runs OEM code.

Preserves normal paths and the original caught RemoteException register; this
does not implement protected UI recovery, stale-cache control or an authority.
"""
import hashlib, json, os, runpy, struct, subprocess, sys, zipfile, zlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'out/coloros-readiness'
SOURCE=ROOT.parent/'firmware/donor/extracted/system/framework/framework.jar'
PIN='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
DEX='classes6.dex'
TARGETS={
 'Lcom/android/internal/widget/LockPatternUtils$1;':('apply(Ljava/lang/Integer;)Ljava/lang/Integer;',33,'04b5a5473b4c8c0c6ea03ba00e93542deb4cd1018b3ae493a461c0580a50e2bc'),
 'Lcom/android/internal/widget/LockPatternUtils$2;':('apply(Ljava/lang/Integer;)Ljava/time/Duration;',30,'e2bf187e88f264ab5f984e790d21282f04b2853808880ca89c0381589853e4a8')}

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def u16(b,p):return struct.unpack_from('<H',b,p)[0]
def u32(b,p):return struct.unpack_from('<I',b,p)[0]
def uleb(b,p):
 v=0
 for n in range(5):
  if p>=len(b):raise ValueError('ULEB extent')
  x=b[p];p+=1;v|=(x&127)<<(7*n)
  if n==4 and x>15:raise ValueError('ULEB overflow')
  if x<128:return v,p
 raise ValueError('ULEB termination')
def header(b):
 if b[:8]!=b'dex\n039\0' or len(b)<112:raise ValueError('Only pinned ordinary DEX039')
 if (u32(b,32),u32(b,36),u32(b,40))!=(len(b),112,0x12345678):raise ValueError('Header shape')
 if hashlib.sha1(b[32:]).digest()!=b[12:32]or zlib.adler32(b[12:])&0xffffffff!=u32(b,8):raise ValueError('DEX integrity')
 for off,width in [(56,4),(64,4),(72,12),(80,8),(88,8),(96,32)]:
  n,p=u32(b,off),u32(b,off+4)
  if n>2000000 or n and(p<112 or p+n*width>len(b)):raise ValueError('Table extent')
 if u32(b,104)+u32(b,108)!=len(b):raise ValueError('Data extent')
 return {'version':'039','fileBytes':len(b),'classes':u32(b,96),'methods':u32(b,88)}
def seal(b):
 b=bytearray(b);b[12:32]=hashlib.sha1(b[32:]).digest();struct.pack_into('<I',b,8,zlib.adler32(b[12:])&0xffffffff);return bytes(b)

def locate(b):
 header(b)
 def string(index):
  if index>=u32(b,56):raise ValueError('String index')
  p=u32(b,u32(b,60)+4*index);_,p=uleb(b,p);end=b.find(b'\0',p,min(len(b),p+1048576))
  if end<0:raise ValueError('String extent')
  return b[p:end].decode('utf8')
 def typ(index):
  if index>=u32(b,64):raise ValueError('Type index')
  return string(u32(b,u32(b,68)+4*index))
 def signature(index):
  owner,proto,name=struct.unpack_from('<HHI',b,u32(b,92)+index*8)
  if proto>=u32(b,72):raise ValueError('Proto index')
  pos=u32(b,76)+12*proto;ret,params=u32(b,pos+4),u32(b,pos+8);args=[]
  if params:
   n=u32(b,params)
   if n>65535 or params+4+2*n>len(b):raise ValueError('Parameter extent')
   args=[typ(u16(b,params+4+2*i))for i in range(n)]
  return typ(owner),string(name)+'('+''.join(args)+')'+typ(ret)
 found={};ranges=[];count=0
 for ci in range(u32(b,96)):
  row=u32(b,100)+32*ci;owner=u32(b,row);p=u32(b,row+24)
  if not p:continue
  counts=[]
  for _ in range(4):n,p=uleb(b,p);counts.append(n)
  if sum(counts)>2000000:raise ValueError('Class member bound')
  for n in counts[:2]:
   index=0
   for _ in range(n):
    delta,p=uleb(b,p);index+=delta;_,p=uleb(b,p)
    if index>=u32(b,80):raise ValueError('Field index')
  for n in counts[2:]:
   index=0
   for _ in range(n):
    delta,p=uleb(b,p);index+=delta;_,p=uleb(b,p);code,p=uleb(b,p);count+=1
    if index>=u32(b,88)or u16(b,u32(b,92)+8*index)!=owner:raise ValueError('Method owner/index')
    if not code:continue
    if code%4 or code+16>len(b):raise ValueError('Code offset')
    units=u32(b,code+12);start=code+16;end=start+2*units
    if end>len(b):raise ValueError('Code extent')
    ranges.append((index,start,end))
    o=typ(owner)
    if o in TARGETS and signature(index)==(o,TARGETS[o][0]):
     if o in found:raise ValueError('Duplicate target')
     if (units,u16(b,code),u16(b,code+6))!=(TARGETS[o][1],5,1):raise ValueError('Target code shape')
     found[o]={'methodId':index,'codeOffset':code,'instructionsOffset':start,'instructionUnits':units,'registers':5,'tryItems':1}
 if set(found)!=set(TARGETS):raise ValueError('Missing target')
 for f in found.values():
  a=f['instructionsOffset']+54;c=f['instructionsOffset']+f['instructionUnits']*2
  if any(index!=f['methodId']and max(a,s)<min(c,e)for index,s,e in ranges):raise ValueError('Aliased method code')
 return found,{'encodedMethods':count,'codeBodies':len(ranges),'otherMethodCodeOverlap':0}

def boundary(r):
 b=r['body'];owner=b['owner'];signature,units,pin=TARGETS[owner]
 if b['signature']!=signature or r['normalizedBodySha256']!=pin:raise ValueError('Exact source body')
 ins=b['instructions'];pcs={i['pc']for i in ins};by={i['pc']:i for i in ins}
 if b['registerCount']!=5 or by[19]['opcode']!='MOVE_EXCEPTION' or by[19]['registers']!=[0]:raise ValueError('Captured error identity')
 if by[24]['reference']!='Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I'or by[24]['registers']!=[1,2,0]:raise ValueError('Captured v0 log preservation')
 if any(0 in i.get('registers',[])for i in ins if 20<=i['pc']<24):raise ValueError('Error register overwritten')
 if b['catches']!=[{'startPc':0,'codeUnits':18,'exceptionType':'Landroid/os/RemoteException;','handlerPc':19}]:raise ValueError('Catch shape')
 if 27 not in pcs or sum(i['codeUnits']for i in ins if i['pc']>=27)!=units-27:raise ValueError('Complete tail boundary')
 for i in ins:
  if 'PAYLOAD'in i['opcode']or 'switchElements'in i:raise ValueError('Unexpected payload')
  if 'targetPc'in i and(i['targetPc']not in pcs or i['targetPc']>=27):raise ValueError('Unexpected tail entry/branch')
 return {'firstPc':27,'endExclusivePc':units,'throwRegister':0,'caughtAtPc':19,'originalLogPc':24,'interiorBranchEntries':0,'tryRange':[0,18],'handlerPc':19}

def read_leaf(jar,owner,methods,label):
 # The source-reader wrapper intentionally refuses generated out/ archives.
 # Invoke its same pinned authored Java reader directly, retaining that guard.
 n=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))
 classes,pins=n['_classes']();before=digest(jar)
 raw=ROOT/'firmware/coloros-readiness'/('cold-leaf-'+label+'.jsonl');raw.parent.mkdir(parents=True,exist_ok=True)
 (OUT/'tmp').mkdir(exist_ok=True)
 command=[n['JDK']/'java.exe','-Xmx2g','-Duser.home='+str(OUT/'runtime-home'),'-Djava.io.tmpdir='+str(OUT/'tmp'),'-cp',str(classes)+os.pathsep+str(n['DEXLIB']),'SecurityDexReader',jar,owner,'-',*methods]
 with raw.open('wb')as output,(OUT/('cold-leaf-'+label+'-stderr.txt')).open('wb')as err:
  r=subprocess.run(list(map(str,command)),stdout=output,stderr=err,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW,env=dict(os.environ,TMP=str(OUT/'tmp'),TEMP=str(OUT/'tmp')))
 if r.returncode or raw.stat().st_size>2*1024*1024:raise ValueError('Bounded generated-leaf static read')
 records=[json.loads(l)for l in raw.read_text(encoding='utf8').splitlines()]
 summary=next((r for r in records if r['record']=='summary'),None)
 if summary is None or digest(jar)!=before:raise ValueError('Leaf read incomplete/drift')
 if any(digest(ROOT/k)!=v for k,v in pins.items()if k!='parentDexlibSha256')or digest(n['DEXLIB'])!=pins['parentDexlibSha256']:raise ValueError('Reader tool drift')
 return {'raw':raw.relative_to(ROOT).as_posix(),'rawSha256':digest(raw),'archiveSha256':before,'readerExitCode':r.returncode,'summary':summary,'tools':pins,'wrapperLimit':'Source-only wrapper path policy retained; same authored Java reader invoked for generated out/ leaf'},records

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if digest(SOURCE)!=PIN:raise ValueError('Immutable source pin')
 audit=runpy.run_path(str(ROOT/'tools/audit_coloros_readiness.py'))
 _,records=audit['evidence']();original_rows={}
 for _,r in records:
  if r.get('record')=='method'and r['body']['owner']in TARGETS:
   original_rows[r['body']['owner']+'->'+r['body']['signature']]=r
 bounds={o:boundary(original_rows[o+'->'+v[0]])for o,v in TARGETS.items()}
 with zipfile.ZipFile(SOURCE)as z:
  infos=z.infolist()
  if len(infos)>10000 or len({i.filename for i in infos})!=len(infos)or any(i.file_size>256*1024*1024 for i in infos):raise ValueError('ZIP inventory/extent')
  entries={i.filename:z.read(i)for i in infos}
  if z.testzip()is not None:raise ValueError('Input CRC')
 for name,data in entries.items():
  if name.endswith('.dex'):header(data)
 original=entries[DEX];locations,ownership=locate(original);patched=bytearray(original);saved=[]
 for o,f in locations.items():
  a=f['instructionsOffset']+54;c=f['instructionsOffset']+2*f['instructionUnits'];saved.append((a,c,original[a:c]))
  patched[a:c]=b'\x27\x00'+b'\0'*(c-a-2) # THROW v0; unreachable equal-width NOPs.
 patched=seal(patched);header(patched)
 if any(not(8<=i<32)and not any(a<=i<c for a,c,_ in saved)for i,(a,b)in enumerate(zip(original,patched))if a!=b):raise ValueError('Nonpatch byte change')
 inverse=bytearray(patched)
 for a,c,old in saved:inverse[a:c]=old
 inverse=seal(inverse)
 if inverse!=original:raise ValueError('Exact inverse')
 again=bytearray(inverse)
 for a,c,_ in saved:again[a:c]=b'\x27\x00'+b'\0'*(c-a-2)
 if seal(again)!=patched:raise ValueError('Exact roundtrip')
 dex=OUT/'classes6.readiness-leaf.dex';dex.write_bytes(patched)
 jar=OUT/'framework.readiness-leaf.jar'
 with zipfile.ZipFile(jar,'w')as z:
  for info in infos:z.writestr(info,patched if info.filename==DEX else entries[info.filename])
 with zipfile.ZipFile(jar)as z:
  if z.namelist()!=[i.filename for i in infos]or z.testzip()is not None:raise ValueError('Output inventory/CRC')
  for name,data in entries.items():
   if z.read(name)!=(patched if name==DEX else data):raise ValueError('Other archive payload changed')
 reads=[];changes=[]
 for owner,(sig,units,_)in TARGETS.items():
  result,decoded=read_leaf(jar,owner,['apply(Ljava/lang/Object;)Ljava/lang/Object;',sig],owner[-2]);reads.append(result)
  for r in decoded:
   if r.get('record')!='method':continue
   b=r['body'];old=original_rows[owner+'->'+b['signature']];ob=old['body']
   if b['signature']==sig:
    expected=[i for i in ob['instructions']if i['pc']<27]+[{'pc':27,'opcode':'THROW','codeUnits':1,'registers':[0]}]+[{'pc':pc,'opcode':'NOP','codeUnits':1}for pc in range(28,units)]
    if b['instructions']!=expected or {k:v for k,v in b.items()if k!='instructions'}!={k:v for k,v in ob.items()if k!='instructions'}:raise ValueError('Decoded patch/try/register preservation')
    changes.append({'owner':owner,'signature':sig,'sourceBodySha256':old['normalizedBodySha256'],'outputBodySha256':r['normalizedBodySha256'],'boundary':bounds[owner],'codeLocation':locations[owner]})
   elif r['normalizedBodySha256']!=old['normalizedBodySha256']:raise ValueError('Bridge body changed')
 if len(changes)!=2:raise ValueError('Exact changed method count')
 # Refusal probes validate decoded-record admission, not ART or malformed bytes.
 probes={}
 sample=original_rows[next(iter(TARGETS))+'->'+next(iter(TARGETS.values()))[0]]
 for label,edit in [('wrongBody',lambda r:r.update(normalizedBodySha256='0'*64)),('wrongCatchRegister',lambda r:r['body']['instructions'][10].update(registers=[1])),('interiorBranch',lambda r:r['body']['instructions'][0].update(targetPc=28))]:
  bad=json.loads(json.dumps(sample));edit(bad)
  try:boundary(bad)
  except ValueError:probes[label]=True
  else:raise ValueError('Negative accepted: '+label)
 if digest(SOURCE)!=PIN:raise ValueError('Input changed during producer')
 receipt={'schema':'coloros-readiness-leaf/v1','status':'COLD_UNSELECTED_ERROR_PROPAGATION_ONLY','selected':False,'sourceArchive':str(SOURCE),'sourceArchiveSha256':PIN,'sourceDexSha256':sha(original),'outputArchive':jar.relative_to(ROOT).as_posix(),'outputArchiveSha256':digest(jar),'outputDex':dex.relative_to(ROOT).as_posix(),'outputDexSha256':digest(dex),'changes':changes,'ownership':ownership,'reads':reads,'checks':{'exactInverseDex':True,'exactRoundtripDex':True,'onlyTwoTailSlicesAndDexIntegrityHeaderDiffer':True,'everyOtherArchivePayloadEqual':True,'allOriginalDescriptorsRegistersTriesAndNormalInstructionsPreserved':True,'twoBridgeBodiesEqual':True,'noOtherMethodCodeOverlap':True,'allInputDex039IntegrityValid':True,'outputDex039IntegrityValid':True,'decodedRefusalProbes':probes},'limits':['No protected unknown-state UI or recovery owner is implemented','Existing valid/stale cached NONE or ZERO still bypasses recompute','No new caller/user/generation policy is supplied','Original SecureLockDevice/additional-factor/StrongAuth guards remain mandatory','Independent leaf over immutable original, not composed with PIN metadata or RPMB leaves','ZIP is reserialized; no ART/JAR-signature/install/runtime acceptance'],'producerSha256':digest(__file__),'oemCodeExecuted':False,'phoneActions':0}
 receipt.update(patchedArchive=receipt['outputArchive'],patchedArchiveSha256=receipt['outputArchiveSha256'],coldStartOnly=True,requiredSelectionConditions=[
  'Keep this artifact cold and unselected until a coherent complete integration is reviewed; no hot-patching an already loaded framework or live cache.',
  'Retain a real current Samsung authority/user/generation owner before mode, confirmation, resume, queued input/progress and finish; revalidate after external work.',
  'Invalidate and reconcile both original credential-type and lockout cache namespaces on authority death/replacement, selected-user changes and committed credential/policy changes; cache hits are not authority readiness.',
  'Implement protected unknown-state presentation and owned safe-return/recovery/drain; an exception or process crash alone is not safe recovery.',
  'Preserve original StrongAuth, trust, SIM, lock-dead, SecureLockDevice/additional-factor and authenticated-pending dismissal gates, with policy applied from the actual same authority before activation.',
  'Make native Settings abort or retain its operation on authority loss; reconcile uncertain credential commits without no-credential substitution, success fabrication or blind retry.',
  'Compose with other selected source changes using exact immutable source identities and the union of every leaf selection condition; this independent leaf contains neither PIN metadata nor RPMB removals.',
  'Identify actual installed OneOS/profile bytes and establish ART, caller/permission, policy, input/callback, app/key/CE, death/recovery and cross-OS runtime acceptance separately.'])
 (OUT/'leaf-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'status':receipt['status'],'archiveSha256':receipt['outputArchiveSha256'],'dexSha256':receipt['outputDexSha256'],'changes':changes,'checks':receipt['checks']}))

if __name__=='__main__':main()
