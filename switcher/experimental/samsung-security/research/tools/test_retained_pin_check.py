"""Compile authored check-route fixtures and run unchanged saved SDK program bytes.

No production compile, Android/OEM/JNI implementation, real callback or device run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'out/retained-pin-check-tests'
FIXTURES=ROOT/'compat/tests/retained_pin_check_model'
SUPPORT=ROOT/'tools/test_guest_policy_init.py'
SUPPORT_SHA='d0be8dd63d2eef588e36c5d0008930301414f4b509c9d6a5b2ab597d2eaad121'
AUTH='com/appleexploit/oneos/security/authority/'
PRODUCTION={'compat/android/'+AUTH+n+'.java' for n in (
    'PreparedRetainedUserRegistryCapture','PreparedRetainedSecurityFamilyCapture',
    'PreparedRetainedPinBinding','PreparedRetainedPinOperationOwner','PreparedRetainedPinCheckOwner',
    'PreparedRetainedLockSettingsLocalOwner','PreparedRetainedPasswordMetrics','PreparedRetainedPinEndpoint')}
PRODUCTION|={'compat/android/com/appleexploit/oneos/security/transport/PreparedRetainedPinEndpointClient.java',
             'compat/host-module/'+AUTH+'RetainedPinHostModule.java','compat/host-module/'+AUTH+'HostBootstrapPermit.java'}
ABI={'compat/compile-only/pin-endpoint/'+n+'.java' for n in (
    'android/os/Parcel','com/android/internal/widget/LockscreenCredential','com/android/internal/widget/VerifyCredentialResponse')}
EXCLUDED={AUTH+n+'.class' for n in (
    'RetainedPinHostModule','RetainedPinHostModule$1','RetainedPinHostModule$Entry',
    'RetainedPinHostModule$HostBootstrapController','HostBootstrapPermit')}


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def relative(value):
    require(isinstance(value,str) and value,'Relative string required')
    p=PurePosixPath(value)
    require(not p.is_absolute() and all(v not in ('','..','.') and ':' not in v and '\\' not in v for v in p.parts),'Contained path required')
    return p


def build(java_home,sdk_receipt,model_export):
    captured,pins={},{}
    def capture(path,expected=None,size=None):
        path=path.resolve(strict=True)
        require(path.is_file(),'Regular input required')
        if path not in captured:
            data=path.read_bytes();require(len(data)<=32*1024*1024,'Bounded input required')
            captured[path]=data;pins[path]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        require(expected is None or pins[path]['sha256']==expected,'Input hash differs: '+str(path))
        require(size is None or pins[path]['bytes']==size,'Input size differs: '+str(path))
        return captured[path]
    support={'__name__':'retained_pin_check_support','__file__':str(SUPPORT)}
    exec(compile(capture(SUPPORT,SUPPORT_SHA),str(SUPPORT),'exec'),support)
    output,save,command=support['output'],support['save'],support['command']
    class_map,links=support['class_map'],support['links']
    command.__globals__['BASE']=BASE
    java_home=java_home.resolve(strict=True);suffix='.exe' if os.name=='nt' else ''
    tools={n:(java_home/'bin'/(n+suffix)).resolve(strict=True) for n in ('java','javac')}
    require(all(p.is_file() and p.parent==java_home/'bin' for p in tools.values()),'Canonical existing JDK tools required')
    manifest=FIXTURES/'manifest.json';fixture=json.loads(capture(manifest))
    require(fixture['schema']=='retained-pin-check-authored-models/v1','Fixture schema differs')
    selected=fixture['actualSelectedSdk'];require(isinstance(selected,dict),'Actual SDK and nineteen-class export must be selected')
    sdk_receipt=sdk_receipt.resolve(strict=True);model_export=model_export.resolve(strict=True)
    sdk_receipt.relative_to(ROOT/'out');model_export.relative_to(ROOT/'out')
    sdk=json.loads(capture(sdk_receipt,selected['sdkReceiptSha256']))
    exported=json.loads(capture(model_export,selected['modelExportSha256']))
    require(sdk['status']=='PASS_PC_PUBLIC_SOURCE_SDK_D8_ONLY' and len(sdk['classPins'])==24
            and sdk['classPins']==selected['allClassPins'],'Actual complete public SDK receipt required')
    require(sdk['sourcePins']==selected['sourcePins'] and set(sdk['sourcePins'])==PRODUCTION|ABI
            and sdk['inputPinsUnchanged'] and not sdk['changedInputs'],'Actual eleven production plus three ABI source pins required')
    require(exported['status']=='PASS_SAVED_SDK_MODEL_COHORT_EXPORT_ONLY'
            and exported['publicReceipt']['sha256']==pins[sdk_receipt]['sha256']
            and (ROOT/relative(exported['publicReceipt']['path'])).resolve(strict=True)==sdk_receipt
            and exported['receiptSourcePins']==sdk['sourcePins'],'Export must bind this exact public SDK receipt')
    program=exported['classPins']
    require(program==selected['modelClassPins'] and len(program)==19
            and set(sdk['classPins'])-set(program)==EXCLUDED
            and set(exported['excludedProgramDefinitions'])==EXCLUDED
            and all(sdk['classPins'].get(n)==h for n,h in program.items()),'Exact nineteen-class model subset required')
    original_classes=(sdk_receipt.parent/'classes').resolve(strict=True)
    exported_classes=(ROOT/relative(exported['classDirectory'])).resolve(strict=True)
    original_classes.relative_to(ROOT/'out');exported_classes.relative_to(ROOT/'out')
    require(class_map(original_classes)==sdk['classPins'] and class_map(exported_classes)==program,'Actual original/export bytes differ')
    for path in [Path(__file__),*tools.values()]:capture(path)
    for n,h in sdk['sourcePins'].items():capture(ROOT/relative(n),h)
    sources={role:[] for role in ('framework','service','control','tests')};destinations=set()
    allowed=[(ROOT/'compat/tests'/n).resolve(strict=True) for n in (
        'retained_pin_bootstrap_model','retained_pin_endpoint_model','retained_pin_check_model')]
    own_files=set()
    for item in fixture['sources']:
        role=item['role'];require(role in sources,'Unexpected authored role')
        name=relative(item['relative']);require(name.suffix=='.java','Java fixture required')
        path=(ROOT/relative(item['path'])).resolve(strict=True)
        require(any(path.is_relative_to(folder) for folder in allowed),'Only selected normal authored fixture roots allowed')
        require((role,str(name)) not in destinations,'Duplicate destination');destinations.add((role,str(name)))
        capture(path,item['sha256'],item['bytes']);sources[role].append((name,path))
        if path.is_relative_to(FIXTURES.resolve(strict=True)):own_files.add(path)
    require(len(destinations)==77 and {p.resolve() for p in FIXTURES.rglob('*.java')}==own_files,'Exact selected authored source closure required')
    for folder,records in [(original_classes,sdk['classPins']),(exported_classes,program)]:
        for n,h in records.items():capture(folder/relative(n),h)

    def boundary():
        for path,v in pins.items():require(path.stat().st_size==v['bytes'] and sha(path)==v['sha256'],'Input changed: '+str(path))
        require(class_map(original_classes)==sdk['classPins'] and class_map(exported_classes)==program,'SDK/export closure changed')
    boundary();output(BASE).mkdir(exist_ok=True);work=output(BASE/('r-'+uuid.uuid4().hex[:8]));work.mkdir()
    print(json.dumps({'run':work.relative_to(ROOT).as_posix(),'productionRecompiled':False}),flush=True)
    result={'schema':'retained-pin-check-authored-tests/v1','status':'FAILED','commands':{},'productionRecompiled':False,
            'classfileShaping':False,'privateHelperStateInspected':False,'completionCellUsed':False,
            'sdkReceipt':{'path':sdk_receipt.relative_to(ROOT).as_posix(),**pins[sdk_receipt]},
            'modelExport':{'path':model_export.relative_to(ROOT).as_posix(),**pins[model_export]},'androidNativeOrPhoneActions':False}
    try:
        for folder in ('inputs','src','program','deps','framework','service','control','tests','tmp','runtime-home','empty-native','empty-classpath'):
            output(work/folder).mkdir()
        snapshots,staged={},{role:[] for role in sources}
        for index,(path,v) in enumerate(sorted(pins.items(),key=lambda row:str(row[0]))):
            target=work/'inputs'/('%03d-'%index+path.name);target.write_bytes(captured[path])
            snapshots[str(path)]={'path':target.relative_to(ROOT).as_posix(),**v}
        for role,rows in sources.items():
            for name,path in rows:
                target=output(work/'src'/role/name);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(captured[path]);staged[role].append(target)
        for n,h in program.items():
            target=output(work/'program'/relative(n));target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(captured[(exported_classes/n).resolve(strict=True)])
        env={k:v for k,v in os.environ.items() if k.upper() not in support['STRIP']}
        env.update(TMP=str(work/'tmp'),TEMP=str(work/'tmp'),TMPDIR=str(work/'tmp'),HOME=str(work/'runtime-home'),USERPROFILE=str(work/'runtime-home'))
        jvm=['-Xmx512m','-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'runtime-home'),'-Djava.library.path='+str(work/'empty-native')]
        javac=[tools['javac'],*['-J'+v for v in jvm],'-proc:none','-implicit:none','-encoding','UTF-8','-source','8','-target','8','-sourcepath','']
        def copies():
            boundary();require(class_map(work/'program')==program and not list((work/'deps').iterdir()),'Actual model cohort changed or empty placeholder populated')
            for v in snapshots.values():require(sha(ROOT/v['path'])==v['sha256'],'Retained input changed')
            for role,rows in sources.items():
                for (_,original),target in zip(rows,staged[role]):require(sha(target)==pins[original]['sha256'],'Staged source changed')
        for role in sources:
            copies()
            cp=work/'framework' if role=='service' else os.pathsep.join(str(work/n) for n in ('program','framework')) if role=='control' else str(work/'empty-classpath')
            result['commands']['compile-'+role]=command([*javac,'-classpath',cp,'-d',work/role,*staged[role]],work,env,'compile-'+role,tools)
        actual={role:class_map(work/role) for role in sources}
        require(all(actual.values()) and set(actual['control'])=={AUTH+'CheckFixtureControl.class'},'Exact one authored lifecycle-control definition required')
        require(not any(n.startswith('com/appleexploit/oneos/security/') for role in ('framework','service','tests') for n in actual[role]),'Fixture production replacement refused')
        metadata={role:{n:links((work/role/n).read_bytes()) for n in records} for role,records in actual.items()}
        require(all(v['name']+'.class'==n for records in metadata.values() for n,v in records.items()),'Fixture internal name differs')
        copies()
        result['commands']['models']=command([tools['java'],*jvm,'-Xint','-cp',work/'tests','model.RetainedPinCheckTest',
            work/'program',work/'deps',work/'framework',work/'service',work/'control'],work,env,'models',tools)
        lines=(work/'models.stdout').read_text(encoding='utf-8').splitlines();require(len(lines)==1,'One bounded result line required')
        tests=json.loads(lines[0]);require(tests=={'status':'PASS_AUTHORED_RETAINED_PIN_CHECK_MODELS_ONLY','scenarios':30,'checks':tests.get('checks'),'completionCellUsed':False}
            and type(tests['checks']) is int and tests['checks']>0,'Actual focused model result required')
        copies();require({role:class_map(work/role) for role in sources}==actual,'Fixture output changed')
        result.update(status='PASS_UNCHANGED_SDK_AUTHORED_PIN_CHECK_MODELS_ONLY',tests=tests,
            programClassPinsBeforeAfter=program,fixtureClassPinsBeforeAfter=actual,fixtureClassMetadata=metadata,
            inputSnapshots=snapshots,stagedSourcePins={p.relative_to(ROOT).as_posix():sha(p) for rows in staged.values() for p in rows})
    except BaseException as failure:
        result.update(failureType=type(failure).__name__,failureMessage=str(failure)[:2048]);raise
    finally:
        save(work/'receipt.json',result)
        print(json.dumps({'status':result['status'],'receipt':(work/'receipt.json').relative_to(ROOT).as_posix(),'receiptSha256':sha(work/'receipt.json')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home',type=Path,required=True)
    parser.add_argument('--sdk-receipt',type=Path,required=True)
    parser.add_argument('--model-export',type=Path,required=True)
    args=parser.parse_args();build(args.java_home,args.sdk_receipt,args.model_export)
