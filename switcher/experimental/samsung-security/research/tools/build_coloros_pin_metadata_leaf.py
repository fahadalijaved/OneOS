"""Build an UNSELECTED offline ColorOS optional PIN-audit-metadata DEX leaf.

Only the exact admitted DEX039 source is supported. No OEM/JNI/Android execution.
The source archive is immutable. All generated binaries remain under out/.
"""
import hashlib,json,os,struct,subprocess,sys,zipfile,zlib
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent;PARENT=ROOT.parent
OUT=ROOT/'out/coloros-pin-metadata-leaf';RAW=ROOT/'firmware/construction-protocol'
SOURCE=PARENT/'firmware/donor/extracted/system/framework/framework.jar'
SOURCE_SHA='d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
DEX_NAME='classes6.dex';OWNER='Lcom/android/internal/widget/LockPatternUtils;'
METHOD='setLockCredential(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;I)Z'
SOURCE_BODY='c6f0ba72dc78f9c351632cbd4a470d29d681ba50c7eade5c6952f3159923f069'
FIRST=38;END=52

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def u16(b,p):
 if p<0 or p+2>len(b):raise ValueError('u16 bounds')
 return struct.unpack_from('<H',b,p)[0]
def u32(b,p):
 if p<0 or p+4>len(b):raise ValueError('u32 bounds')
 return struct.unpack_from('<I',b,p)[0]
def uleb(b,p):
 v=0
 for i in range(5):
  if p>=len(b):raise ValueError('ULEB bounds')
  x=b[p];p+=1;v|=(x&127)<<(7*i)
  if i==4 and x>15:raise ValueError('ULEB overflow')
  if x<128:return v,p
 raise ValueError('ULEB termination')
def header(b):
 if b[:8]!=b'dex\n039\0':raise ValueError('Only exact ordinary DEX039 is admitted; no041 fallback')
 if len(b)<112 or u32(b,32)!=len(b)or u32(b,36)!=112 or u32(b,40)!=0x12345678:raise ValueError('DEX039 header/extent/endian')
 if hashlib.sha1(b[32:]).digest()!=b[12:32]:raise ValueError('DEX SHA1 signature mismatch')
 if zlib.adler32(b[12:])&0xffffffff!=u32(b,8):raise ValueError('DEX Adler32 checksum mismatch')
 for off,width in [(56,4),(64,4),(72,12),(80,8),(88,8),(96,32)]:
  n,p=u32(b,off),u32(b,off+4)
  if n>2000000 or n and(p<112 or p+n*width>len(b)):raise ValueError('DEX table extent')
 data_size,data_off=u32(b,104),u32(b,108)
 if data_off<112 or data_off+data_size!=len(b):raise ValueError('DEX data extent')
 mp=u32(b,52)
 if mp<data_off or mp+4>len(b) or u32(b,mp)>65535 or mp+4+u32(b,mp)*12>len(b):raise ValueError('DEX map extent')
 return {'version':'039','headerBytes':112,'fileBytes':len(b),'classes':u32(b,96),'methodIds':u32(b,88),'signatureSha1':b[12:32].hex(),'adler32':u32(b,8),'dataOffset':data_off,'dataBytes':data_size}
def seal(b):
 b=bytearray(b);b[12:32]=hashlib.sha1(b[32:]).digest();struct.pack_into('<I',b,8,zlib.adler32(b[12:])&0xffffffff);return bytes(b)
def locate(b):
 header(b);strings=u32(b,60);types=u32(b,68);protos=u32(b,76);methodids=u32(b,92);classes=u32(b,100)
 def string(index):
  if index>=u32(b,56):raise ValueError('String index')
  p=u32(b,strings+4*index);_,p=uleb(b,p);end=b.find(b'\0',p,min(len(b),p+1048576))
  if end<0:raise ValueError('Bounded string terminator')
  return b[p:end]
 def typ(index):
  if index>=u32(b,64):raise ValueError('Type index')
  return string(u32(b,types+4*index))
 def signature(index):
  owner,proto,name=struct.unpack_from('<HHI',b,methodids+index*8)
  if proto>=u32(b,72):raise ValueError('Proto index')
  ret,params=u32(b,protos+proto*12+4),u32(b,protos+proto*12+8);p=[]
  if params:
   n=u32(b,params)
   if n>65535 or params+4+2*n>len(b):raise ValueError('Parameter list bounds')
   p=[typ(u16(b,params+4+2*i))for i in range(n)]
  return typ(owner),string(name)+b'('+b''.join(p)+b')'+typ(ret)
 found=[];ranges=[];encoded_methods=0
 for ci in range(u32(b,96)):
  row=classes+32*ci;owner=u32(b,row);p=u32(b,row+24)
  if not p:continue
  counts=[]
  for _ in range(4):n,p=uleb(b,p);counts.append(n)
  if sum(counts)>2000000:raise ValueError('Encoded member bound')
  for count in counts[:2]:
   idx=0
   for _ in range(count):
    delta,p=uleb(b,p);idx+=delta;_,p=uleb(b,p)
    if idx>=u32(b,80):raise ValueError('Field index')
  for count in counts[2:]:
   idx=0
   for _ in range(count):
    delta,p=uleb(b,p);idx+=delta;access,p=uleb(b,p);code,p=uleb(b,p);encoded_methods+=1
    if idx>=u32(b,88)or u16(b,methodids+idx*8)!=owner:raise ValueError('Encoded method identity')
    if not code:continue
    if code%4 or code+16>len(b):raise ValueError('Code header alignment/bounds')
    size=u32(b,code+12);start=code+16;end=start+2*size
    if size>10000000 or end>len(b):raise ValueError('Code instructions extent')
    ranges.append((idx,start,end))
    if typ(owner)==OWNER.encode()and signature(idx)==(OWNER.encode(),METHOD.encode()):found.append({'methodId':idx,'codeOffset':code,'instructionsOffset':start,'instructionUnits':size,'registers':u16(b,code),'incomingWords':u16(b,code+2),'outgoingWords':u16(b,code+4),'tryItems':u16(b,code+6),'debugInfoOffset':u32(b,code+8),'accessFlags':access})
 if len(found)!=1:raise ValueError('Exact target method absent/ambiguous')
 f=found[0];a=f['instructionsOffset']+2*FIRST;c=f['instructionsOffset']+2*END
 if f['instructionUnits']!=63 or f['registers']!=7 or f['tryItems']!=1:raise ValueError('Target code shape changed')
 collisions=[x for x in ranges if x[0]!=f['methodId']and max(a,x[1])<min(c,x[2])]
 if collisions:raise ValueError('Another method aliases/overlaps changed instructions')
 return f,{'encodedMethods':encoded_methods,'codeBodies':len(ranges),'otherMethodOverlapCount':len(collisions)}
def source_boundaries(row):
 b=row['body'];ins=b['instructions'];bounds={i['pc']for i in ins};patch=[i for i in ins if FIRST<=i['pc']<END]
 if row['normalizedBodySha256']!=SOURCE_BODY or b['owner']!=OWNER or b['signature']!=METHOD:raise ValueError('Exact normalized source body mismatch')
 if FIRST not in bounds or END not in bounds or sum(i['codeUnits']for i in patch)!=END-FIRST:raise ValueError('Patch is not a complete instruction slice')
 if any('PAYLOAD'in i['opcode']for i in ins):raise ValueError('Unexpected payload')
 for i in ins:
  if 'targetPc'in i and FIRST<i['targetPc']<END:raise ValueError('Branch enters removed block interior')
  if 'targetPc'in i and i['targetPc']not in bounds:raise ValueError('Branch target not an instruction boundary')
 for c in b['catches']:
  if c['handlerPc']not in bounds or FIRST<=c['handlerPc']<END:raise ValueError('Handler enters removed block')
  if c['startPc']not in bounds or c['startPc']+c['codeUnits']not in bounds|{63}:raise ValueError('Try extent not aligned')
 if b['catches']!=[{'startPc':22,'codeUnits':29,'exceptionType':'Landroid/os/RemoteException;','handlerPc':54}]:raise ValueError('Original catch contract changed')
 calls=[i for i in patch if i.get('referenceKind')=='method']
 if [i['pc']for i in calls]!=[38,44,48]or 'setLockscreenPasswordType('not in calls[-1]['reference']:raise ValueError('Exact optional block changed')
 return {'firstPc':FIRST,'endExclusivePc':END,'instructionUnits':END-FIRST,'bytes':2*(END-FIRST),'branchToPatchStartPreserved':True,'interiorBranchOrHandlerEntries':0,'payloadCount':0,'tryStartPc':22,'tryEndExclusivePc':51,'handlerPc':54,'tryEndWithinNopRegionRemainsInstructionBoundary':True}
def read_java(archive,label):
 from static_security_reader import _classes,_env,JDK,DEXLIB,JAVA_SOURCE
 cache,pins=_classes();raw=RAW/('pin-metadata-leaf-'+label+'.jsonl');err=OUT/(label+'-reader-stderr.txt')
 cmd=[JDK/'java.exe','-Xmx2g','-Duser.home='+str(OUT/'runtime-home'),'-Djava.io.tmpdir='+str(OUT/'tmp'),'-cp',str(cache)+os.pathsep+str(DEXLIB),'SecurityDexReader',archive,OWNER,'-','--ALL-DECLARED-METHODS--']
 with raw.open('wb')as output,err.open('wb')as errors:r=subprocess.run(list(map(str,cmd)),stdout=output,stderr=errors,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
 if r.returncode or raw.stat().st_size>32*1024*1024:raise ValueError('Actual static DEX read failed '+label)
 data=[json.loads(l)for l in raw.read_text(encoding='utf8').splitlines()];summary=next((x for x in data if x['record']=='summary'),None)
 if summary is None:raise ValueError('Missing reader completion')
 return data,{'raw':raw.relative_to(ROOT).as_posix(),'rawSha256':digest(raw),'archiveSha256':digest(archive),'readerExitCode':r.returncode,'tools':pins,'summary':summary,'dex':[x for x in data if x['record']=='dex']}
def main():
 OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True);(OUT/'tmp').mkdir(exist_ok=True)
 before=digest(SOURCE)
 if before!=SOURCE_SHA:raise ValueError('Immutable source archive differs')
 original_rows,original_read=read_java(SOURCE,'original')
 om={r['body']['signature']:r for r in original_rows if r['record']=='method'}
 if METHOD not in om:raise ValueError('Target source method absent')
 boundaries=source_boundaries(om[METHOD]);entries={};infos=[];headers={}
 with zipfile.ZipFile(SOURCE)as z:
  infos=z.infolist()
  if len(infos)>10000 or len({i.filename for i in infos})!=len(infos):raise ValueError('Archive entry bound/duplicates')
  for info in infos:
   if info.file_size>256*1024*1024:raise ValueError('Archive entry expanded bound')
   entries[info.filename]=z.read(info)
   if info.filename.endswith('.dex'):headers[info.filename]=header(entries[info.filename])
  if z.testzip()is not None:raise ValueError('Source ZIP CRC validation')
 if list(headers)!=['classes.dex','classes2.dex','classes3.dex','classes4.dex','classes5.dex','classes6.dex']:raise ValueError('Exact six-DEX order changed')
 original=entries[DEX_NAME];location,ownership=locate(original);a=location['instructionsOffset']+FIRST*2;c=location['instructionsOffset']+END*2
 saved=original[a:c];patched=bytearray(original);patched[a:c]=b'\0'*(c-a);patched=seal(patched);patched_header=header(patched)
 if patched==original or patched[:8]!=original[:8]or patched[32:a]!=original[32:a]or patched[c:]!=original[c:]:raise ValueError('Unexpected nonpatch DEX changes')
 if any(i not in range(8,32)and not a<=i<c for i,(x,y)in enumerate(zip(original,patched))if x!=y):raise ValueError('Changed bytes outside admitted spans')
 inverse=bytearray(patched);inverse[a:c]=saved;inverse=seal(inverse)
 if inverse!=original:raise ValueError('Inverse does not reproduce exact original DEX')
 again=bytearray(inverse);again[a:c]=b'\0'*(c-a);again=seal(again)
 if again!=patched:raise ValueError('Roundtrip does not reproduce exact patched DEX')
 patched_path=OUT/'classes6.pin-metadata-leaf.dex';patched_path.write_bytes(patched);(OUT/'classes6.inverse.dex').write_bytes(inverse)
 jar=OUT/'framework.pin-metadata-leaf.jar'
 with zipfile.ZipFile(jar,'w')as z:
  for info in infos:z.writestr(info,patched if info.filename==DEX_NAME else entries[info.filename])
 payloads=[]
 with zipfile.ZipFile(jar)as z:
  if z.namelist()!=[i.filename for i in infos]or z.testzip()is not None:raise ValueError('Output ZIP inventory/CRC')
  for name,old in entries.items():
   new=z.read(name)
   if new!=(patched if name==DEX_NAME else old):raise ValueError('Unintended entry payload change')
   if name.endswith('.dex'):header(new)
   payloads.append({'name':name,'sourceSha256':sha(old),'outputSha256':sha(new),'unchanged':new==old})
 new_rows,new_read=read_java(jar,'patched');nm={r['body']['signature']:r for r in new_rows if r['record']=='method'}
 original_class=next(r for r in original_rows if r['record']=='class');new_class=next(r for r in new_rows if r['record']=='class')
 if original_class!=new_class or set(om)!=set(nm):raise ValueError('Class/method/field signatures changed')
 if original_read['summary']!=new_read['summary']:raise ValueError('Class count or selected method count changed')
 changed=[s for s in om if om[s]['normalizedBodySha256']!=nm[s]['normalizedBodySha256']]
 if changed!=[METHOD]:raise ValueError('Unexpected normalized method change')
 old=om[METHOD]['body'];new=nm[METHOD]['body'];expected=[i for i in old['instructions']if i['pc']<FIRST]+[{'pc':pc,'opcode':'NOP','codeUnits':1}for pc in range(FIRST,END)]+[i for i in old['instructions']if i['pc']>=END]
 if new['instructions']!=expected or {k:v for k,v in old.items()if k!='instructions'}!={k:v for k,v in new.items()if k!='instructions'}:raise ValueError('Patched instruction/try/register contract differs')
 # Decoded-record negative admission probes; no malformed DEX bytes are created.
 wrong=json.loads(json.dumps(om[METHOD]));wrong['normalizedBodySha256']='0'*64
 try:source_boundaries(wrong)
 except ValueError:pass
 else:raise ValueError('Wrong-body negative accepted')
 wrong=json.loads(json.dumps(om[METHOD]));next(i for i in wrong['body']['instructions']if i['pc']==34)['targetPc']=41
 try:source_boundaries(wrong)
 except ValueError:pass
 else:raise ValueError('Interior-entry negative accepted')
 if digest(SOURCE)!=before:raise ValueError('Source archive changed during producer')
 source_header=header(original);checks={'sourceArchiveUnchanged':True,'allSixInputOutputDex039SignaturesAndChecksumsValid':True,'patchIsExactNopSlice':True,'outsidePatchAndDexIntegrityHeaderBytesEqual':True,'exactInverseOriginalDexEqual':True,'exactRoundtripPatchedDexEqual':True,'allOtherArchiveEntryPayloadsEqual':all(x['unchanged']for x in payloads if x['name']!=DEX_NAME),'classFieldMethodDescriptorsEqual':True,'allOtherSelectedClassMethodBodiesEqual':len(om)-1,'wholeArchiveClassCountEqual':True,'noOtherMethodCodeAliasOverlap':True,'triesHandlersBranchesAndNoPayloadPreserved':True,'decodedRecordWrongBodyNegativeRejected':True,'decodedRecordInteriorBranchEntryNegativeRejected':True}
 receipt={'schema':'coloros-pin-metadata-leaf/v1','status':'UNSELECTED_PC_ONLY_OPTIONAL_AUDIT_METADATA_REMOVAL','sourceArchive':str(SOURCE),'sourceArchiveSha256':SOURCE_SHA,'sourceBodySha256':SOURCE_BODY,'owner':OWNER,'method':METHOD,'physicalDex':DEX_NAME,'logicalHeaderOffset':0,'sourceHeader':source_header,'patchedHeader':patched_header,'codeLocation':location,'codeOwnership':ownership,'patchBoundary':boundaries,'patchedDex':patched_path.relative_to(ROOT).as_posix(),'patchedDexSha256':digest(patched_path),'patchedArchive':jar.relative_to(ROOT).as_posix(),'patchedArchiveSha256':digest(jar),'patchedBodySha256':nm[METHOD]['normalizedBodySha256'],'inverseDex':'out/coloros-pin-metadata-leaf/classes6.inverse.dex','inverseDexSha256':sha(inverse),'originalDexSha256':sha(original),'originalDexClassCount':source_header['classes'],'archiveEntryPayloads':payloads,'originalRead':original_read,'patchedRead':new_read,'checks':checks,'negativeEvidenceScope':'Decoded JSON-record admission invariant checks only; not malformed-byte DEX fixtures or runtime fault injection','unexecutedNegativeCases':['actual-byte altered branch target fixture','actual-byte altered try/handler fixture','actual-byte method code-offset alias fixture','Android/ART/runtime fault campaign'],'requiredSelectionConditions':['Original Samsung authority,actual commit/policy/readback and exact typed transport must be assembled separately','Exclude optional OPPO dots-key audit producer/logging consumer from selected family,or remove its exact optional read/log slice;do not remove independent timeout hook work','Keep quality/password length/StrongAuth/lockout/credential/storage/key behavior and unknown/locked readiness gates','No input-profile,installed-image,Android,ART,JAR signature,hardware,credential or phone acceptance is inferred'],'signatureLimits':'DEX SHA1 is a format integrity field,not authenticity. ZIP wrapper is reserialized; unchanged non-target entry payloads are proved,not identical physical ZIP encoding. No Android/JAR signing acceptance claimed.','protocolInventorySha256':digest(ROOT/'inventory/construction-protocol.json'),'producerSha256':digest(Path(__file__)),'oemCodeExecuted':False,'phoneAction':False,'selected':False}
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(ROOT/'inventory/coloros-pin-metadata-leaf.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':receipt['status'],'archiveSha256':receipt['patchedArchiveSha256'],'patchedDexSha256':receipt['patchedDexSha256'],'patchedBodySha256':receipt['patchedBodySha256'],'unchangedClassMethods':len(om)-1,'wholeArchiveClasses':new_read['summary']['classDefinitions'],'checks':checks}))
if __name__=='__main__':main()
