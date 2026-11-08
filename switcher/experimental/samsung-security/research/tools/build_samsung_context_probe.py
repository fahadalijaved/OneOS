"""Compile/package authored host-only probe; never launch Android/OEM code or ADB."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import uuid
import zipfile

ROOT=Path(__file__).resolve().parent.parent
PARENT=ROOT.parent
SOURCE='compat/android/com/appleexploit/oneos/security/probe/SamsungContextProbe.java'
EXPECTED='com/appleexploit/oneos/security/probe/SamsungContextProbe'
PROFILE={'model':'SM-S948U1','sdk':37,'display':'CP2A.260605.016.S948U1UES4BZIG',
 'fingerprint':'samsung/m3quew/m3q:17/CP2A.260605.016/S948U1UES4BZIG_OYM4BZIG:user/release-keys'}
CRASH_LOG=PARENT/'out/recon/vector-current-verbose.txt'
CRASH_SHA='97e893d6e1a7db9445089ec4b6d60aae57293f689a3f121355a6fb69e59fecee'


def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
 # Reuse bounded existing build runner and own-output parsers, not OEM execution.
 helper=ROOT/'tools/test_credential_transport.py';helpersha=sha(helper)
 h=runpy.run_path(str(helper));run=h['run'];jdk=h['JDK'];sdk=h['ANDROID'];d8=h['D8']
 assert sha(sdk)==h['ANDROID_SHA'] and sha(d8)==h['D8_SHA']
 assert sha(CRASH_LOG)==CRASH_SHA
 # Read only the selected public fingerprint line; never copy the raw crash log.
 with CRASH_LOG.open(encoding='utf-8',errors='strict')as f:
  line=next(text for index,text in enumerate(f,1)if index==17553)
 assert "Build fingerprint: '"+PROFILE['fingerprint']+"'" in line
 source=ROOT/SOURCE;before=sha(source);toolsha=sha(__file__)
 dependencies=['docs/authority-bootstrap-runtime.md','inventory/authority-bootstrap-runtime.json','docs/samsung-context-probe.md','out/samsung-context-probe/guard-source.json']
 pins={name:sha(ROOT/name)for name in dependencies}
 guardproof=[]
 for r in json.loads((ROOT/'out/samsung-context-probe/guard-source.json').read_text()):
  assert r['readerExitCode']==0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
  assert r['archiveSha256']=='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
  assert sha(ROOT/r['raw'])==r['rawSha256']
  guardproof.append({'receipt':r['receipt'],'receiptSha256':sha(ROOT/r['receipt']),'raw':r['raw'],'rawSha256':r['rawSha256'],'methods':r['selectedMethodProofs']})
 work=ROOT/'out/samsung-context-probe'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
 work.mkdir(parents=True,exist_ok=False)
 for folder in ['tmp','runtime-home','classes','dex']:(work/folder).mkdir()
 print(json.dumps({'startedWork':work.relative_to(ROOT).as_posix(),'sourceSha256':before}),flush=True)
 options=['-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'runtime-home')]
 javac=[jdk/'javac.exe',*['-J'+o for o in options],'-proc:none','-source','8','-target','8','-encoding','UTF-8','-sourcepath','','-cp',sdk,'-d',work/'classes',source]
 compilation=run(javac,work,'sdk37-compile')
 classes=sorted((work/'classes').rglob('*.class'))
 assert [h['class_name'](p)for p in classes]==[EXPECTED], 'Only exact authored probe may be packaged'
 emission=run([jdk/'java.exe',*options,'-cp',d8,'com.android.tools.r8.D8','--min-api','37','--lib',sdk,'--output',work/'dex',*classes],work,'d8')
 dexes=sorted((work/'dex').glob('*.dex'));assert len(dexes)==1
 assert h['dex_names'](dexes[0])==['L'+EXPECTED+';'], 'No SDK or compiler-only stubs permitted'
 artifact=work/'samsung-context-probe.jar'
 with zipfile.ZipFile(artifact,'x',compression=zipfile.ZIP_STORED)as z:
  entry=zipfile.ZipInfo('classes.dex',(1980,1,1,0,0,0));z.writestr(entry,dexes[0].read_bytes())
 with zipfile.ZipFile(artifact)as z:assert z.namelist()==['classes.dex']and z.read('classes.dex')==dexes[0].read_bytes()
 assert sha(source)==before and sha(__file__)==toolsha and sha(helper)==helpersha
 assert all(sha(ROOT/p)==pin for p,pin in pins.items())
 assert sha(sdk)==h['ANDROID_SHA']and sha(d8)==h['D8_SHA']
 result={'schema':'samsung-context-probe-build/v1','status':'PC_COMPILED_UNEXECUTED_HOST_ONLY','source':{'path':SOURCE,'sha256':before},'toolSha256':toolsha,
  'profile':PROFILE,'profileStatus':'recorded-only; fresh host/guest/runtime admission required before any later phone proposal',
  'fingerprintProvenance':{'path':'../out/recon/vector-current-verbose.txt','sha256':CRASH_SHA,'line':17553,'kind':'captured November2 crash Build fingerprint; not getprop or current profile'},
  'dependencies':pins,'guardSourceEvidence':guardproof,'buildHelper':{'path':'tools/test_credential_transport.py','sha256':helpersha},
  'toolchain':{str(p):sha(p)for p in [jdk/'javac.exe',jdk/'java.exe',sdk,d8]},'commands':{'sdk37Compile':compilation,'d8':emission},
  'javaSourceTarget':8,'javaReleaseApiCheck':False,'sdkApi':37,'d8Diagnostics':emission['stderr'],
  'classes':{p.relative_to(ROOT).as_posix():sha(p)for p in classes},'dex':{'path':dexes[0].relative_to(ROOT).as_posix(),'sha256':sha(dexes[0]),'definitions':['L'+EXPECTED+';']},
  'artifact':{'path':artifact.relative_to(ROOT).as_posix(),'sha256':sha(artifact),'bytes':artifact.stat().st_size,'entries':['classes.dex']},
  'sourceAndDependencyPinsVerifiedBeforeAfter':True,'sdkOrOemStubsBundled':False,'androidExecuted':False,'oemExecuted':False,'phoneActions':False,'authorityBootstrapOrReadiness':False,
  'limits':['OneUI/original-services host-only; forbidden under ColorOS','Build guards are recorded-value refusal guards, not authoritative runtime attestation','Hidden public reflection can be denied; no access exemption/bypass','systemMain has real Binder/Looper/HWUI/font/Application/module/configuration effects; not inert','Original Application can read configured font files; no authored private-file or security-service access','Synchronous initialization may hang; later approved launch needs external bounded own-PID termination and no restart','System.exit terminates own fresh process, not a service drain/cleanup acknowledgement','No security policy/user/credential/biometric/key/CE acceptance']}
 (work/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 (ROOT/'inventory/samsung-context-probe.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'receipt':(work/'receipt.json').relative_to(ROOT).as_posix(),'artifact':result['artifact'],'androidExecuted':False}),flush=True)


if __name__=='__main__':main()
