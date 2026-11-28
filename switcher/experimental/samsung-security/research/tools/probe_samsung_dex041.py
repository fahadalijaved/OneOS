"""Bounded no-edit static Samsung041 subset re-emission; never execute OEM code."""
from datetime import datetime,timezone
import hashlib,json,os,runpy,struct,uuid,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
PARENT=ROOT.parent
ARCHIVE=PARENT/'firmware/samsung/runtime-20261104/services.jar'
ARCHIVE_SHA='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
DEXLIB=PARENT/'out/toolchain/jadx-1.5.6/lib/jadx-1.5.6-all.jar'
DEXLIB_SHA='fe3e12c45acf75f92369685fd02d1d7a7323385dc725680a9b98a0dac0ea554b'
SOURCE=ROOT/'tools/Probe-SamsungDex041.java'
READER=ROOT/'tools/SecurityDexReader.java'
READER_SHA='9ee6f28750779f289bbb85049472d5261b7bacad5655faf01c8395f2f6d244cc'


def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
 helper=ROOT/'tools/test_credential_transport.py';h=runpy.run_path(str(helper));run=h['run'];jdk=h['JDK']
 assert sha(ARCHIVE)==ARCHIVE_SHA and sha(DEXLIB)==DEXLIB_SHA and sha(READER)==READER_SHA
 source_maps=[]
 with zipfile.ZipFile(ARCHIVE)as z:container=z.read('classes.dex')
 u32=lambda p:struct.unpack_from('<I',container,p)[0]
 for header in (0,10057984):
  offset=u32(header+52);count=u32(offset)
  assert 0<count<=64 and offset+4+12*count<=len(container)
  entries=[{'type':struct.unpack_from('<H',container,offset+4+12*i)[0],'size':u32(offset+8+12*i),'offset':u32(offset+12+12*i)}for i in range(count)]
  source_maps.append({'logicalHeaderOffset':header,'mapOffset':offset,'mapEntryCount':count,'hiddenApiMapEntries':[e for e in entries if e['type']==0xf000]})
 pins={str(p):sha(p)for p in [SOURCE,READER,Path(__file__),helper,jdk/'javac.exe',jdk/'java.exe',jdk/'javap.exe',DEXLIB,ARCHIVE]}
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex
 work=ROOT/'out/samsung-dex041-rewrite'/stamp;work.mkdir(parents=True,exist_ok=False)
 raw=ROOT/'firmware/samsung-dex041-rewrite'/stamp;raw.mkdir(parents=True,exist_ok=False)
 for folder in ['tmp','runtime-home','classes','dex']:(work/folder).mkdir()
 print(json.dumps({'work':work.relative_to(ROOT).as_posix(),'raw':raw.relative_to(ROOT).as_posix()}),flush=True)
 options=['-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'runtime-home')]
 # Inspect actual installed API signatures/hidden-API writer gate before writing.
 api=run([jdk/'javap.exe',*['-J'+o for o in options],'-classpath',DEXLIB,'-p',
  'com.android.tools.smali.dexlib2.writer.pool.DexPool','com.android.tools.smali.dexlib2.writer.io.MemoryDataStore','com.android.tools.smali.dexlib2.VersionMap','com.android.tools.smali.dexlib2.iface.Method','com.android.tools.smali.dexlib2.iface.Field'],work,'writer-api')
 assert 'internClass('in api['stdout']and'getData()'in api['stdout']and'getHiddenApiRestrictions()'in api['stdout']
 implementation=run([jdk/'javap.exe',*['-J'+o for o in options],'-classpath',DEXLIB,'-c','-p','com.android.tools.smali.dexlib2.writer.DexWriter'],work,'writer-bytecode')
 assert 'shouldWriteHiddenApiRestrictions()'in implementation['stdout']
 with zipfile.ZipFile(DEXLIB)as z:manifest=z.read('META-INF/MANIFEST.MF').decode('utf-8')
 (work/'jadx-manifest.txt').write_text(manifest)
 compile_result=run([jdk/'javac.exe',*['-J'+o for o in options],'-proc:none','-source','17','-target','17','-encoding','UTF-8','-cp',DEXLIB,'-d',work/'classes',SOURCE,READER],work,'compile')
 result=run([jdk/'java.exe','-Xmx2g',*options,'-cp',str(work/'classes')+os.pathsep+str(DEXLIB),'ProbeSamsungDex041',ARCHIVE,raw,work/'dex'],work,'probe',timeout=90)
 summary=json.loads(result['stdout']);assert summary['status']=='PASS_STATIC_SUBSET_ONLY'
 assert summary['selectedClasses']==2 and summary['roundtripByteEqual']and summary['allNormalizedMetadataEqual']
 assert summary['originalHeaders']==[{'headerOffset':0,'classCount':9252},{'headerOffset':10057984,'classCount':9664}]
 assert set(summary['selectedClassHeaders'].values())=={10057984}
 expected={'original-normalized.jsonl','decoded-normalized.jsonl','roundtrip-normalized.jsonl'}
 assert {p.name for p in raw.iterdir()}==expected
 rawpins={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(raw.iterdir())}
 assert {p.name for p in (work/'dex').iterdir()}=={'subset-039.dex','roundtrip-039.dex'}
 binarypins={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted((work/'dex').iterdir())}
 assert sha(work/'dex/subset-039.dex')==summary['subsetDexSha256']==sha(work/'dex/roundtrip-039.dex')
 assert all(sha(p)==pin for p,pin in pins.items()),'Source/input/tool changed during probe'
 receipt={'schema':'samsung-dex041-rewrite/v1','status':'PASS_STATIC_TWO_CLASS_SUBSET_ONLY','input':{'path':'../firmware/samsung/runtime-20261104/services.jar','sha256':ARCHIVE_SHA},
  'work':work.relative_to(ROOT).as_posix(),'sourceAndToolPinsVerifiedBeforeAfter':True,'pins':pins,
  'toolApiEvidence':{'apiLog':api['log'],'apiLogSha256':sha(ROOT/api['log']),'implementationLog':implementation['log'],'implementationLogSha256':sha(ROOT/implementation['log']),'jadxVersion':'1.5.6 archive; relocated com.android.tools.smali.dexlib2 APIs pinned by actual jar SHA','dexlibJarSha256':DEXLIB_SHA,'writerOpcodesApi':29,'ordinaryDexVersion':39,'hiddenApiWriterRequiresApiAtLeast':29},
  'compile':compile_result,'execution':{'exitCode':result['exitCode'],'log':result['log']},'summary':summary,'sourceMapEvidence':source_maps,'rawOutputPins':rawpins,'generatedBinaryPins':binarypins,
  'preservationBoundary':['class descriptor/access/superclass/interface-order/sourcefile/annotations','static-versus-instance fields, owner/name/type/access/typed encoded initial values/annotations/hidden-API restrictions','direct-versus-virtual method descriptor/access/parameters/names/signatures/annotations/hidden-API restrictions','registers, opcode widths, literal bits, exact referenced values, branch/payload PCs, ordered try/handlers','debug item kind/address/local-register/name/type/signature/line/source','decode emitted ordinary039 then compare all normalized records; second emit exact039 byte equality'],
  'androidExecuted':False,'oemExecuted':False,'authOrMetadataEditApplied':False,'inputDex041RebasedOrSliced':False,'cohortReady':False,'artAcceptance':False,
  'limits':['Only two original top-level definitions; nested/dependency classes deliberately not included, no ready cohort','Both selected definitions occur in second logical header; both original headers enumerated/count-validated, no selected first-header re-emission claim','Normalized represented metadata equality, not input041 physical byte equality/inverse or arbitrary unknown map-section preservation','An empty source metadata category provides absence evidence only, not a nonempty-category preservation test','Unselected ordinary039 OEM output is static evidence only; no ART loading, linking, initialization, JNI, Android service or phone test','No PMS handler/storage/auth retarget in this scope']}
 (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (ROOT/'inventory/samsung-dex041-rewrite.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'receipt':(work/'receipt.json').relative_to(ROOT).as_posix(),'summary':{k:v for k,v in summary.items()if k!='memberHashes'}}),flush=True)


if __name__=='__main__':main()
