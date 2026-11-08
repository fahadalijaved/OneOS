"""Run source-issued private-view models plus the original 32 handoff regressions.

Compiles authored Android-public-API/Spawn fixtures only; never su, C, Android/OEM or JNI implementations.
"""
import argparse
import ast
import subprocess
import threading
import time
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'out/retained-root-view-tests'
FIXTURES = ROOT / 'compat/models/retained-root-view'
SUPPORT = ROOT / 'tools/test_guest_policy_init.py'
SUPPORT_SHA = 'd0be8dd63d2eef588e36c5d0008930301414f4b509c9d6a5b2ab597d2eaad121'
COMMAND_SUPPORT = ROOT / 'tools/build_retained_root_handoff.py'
COMMAND_SUPPORT_SHA = '7c55e2c3863924f191c68d16e6a8a46ecf48ce9b7017a39af41e1dc4bc076544'
PACKAGE = 'com/fahadali/oneos/core/root/'
SPAWN = PACKAGE + 'RetainedRootOfferSpawn.class'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(value):
    require(isinstance(value, str) and bool(value), 'Nonempty relative string required')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in value and ':' not in value,
            'Contained POSIX relative path required')
    return path


def build(java_home, sdk_receipt):
    captured, pins = {}, {}
    def capture(path, expected=None):
        path=path.resolve(strict=True)
        require(path.is_file(),'Regular source input required')
        if path not in captured:
            data=path.read_bytes();require(len(data)<=32*1024*1024,'Bounded input required')
            captured[path]=data;pins[path]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        require(expected is None or pins[path]['sha256']==expected,'Input hash differs: '+str(path))
        return captured[path]
    support={'__name__':'retained_root_view_test_support','__file__':str(SUPPORT)}
    exec(compile(capture(SUPPORT,SUPPORT_SHA),str(SUPPORT),'exec'),support)
    output,save,class_map,links=[support[n] for n in ('output','save','class_map','links')]
    # Select only the reviewed safe command definition from its FIRST retained bytes.
    command_bytes=capture(COMMAND_SUPPORT,COMMAND_SUPPORT_SHA)
    tree=ast.parse(command_bytes,filename=str(COMMAND_SUPPORT))
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='command']
    require(len(nodes)==1,'Exactly one reviewed bounded command definition required')
    scope={'Path':Path,'time':time,'threading':threading,'subprocess':subprocess,
           'STRIP':support['STRIP'],'require':require,'owned':output,'save':save,
           'relative':lambda p:Path(p).relative_to(ROOT).as_posix(),'sha':sha}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(COMMAND_SUPPORT),'exec'),scope)
    def command(argv,run,env,label,tools):
        argv=list(map(str,argv))
        require(Path(argv[0]) in set(tools.values()),'Canonical explicitly supplied JDK executable required')
        require(output(run)==run.resolve(),'Own canonical cwd required');run.relative_to(BASE)
        require(not any(key.upper() in support['STRIP'] for key in env),'Inherited JVM injection option')
        for key,folder in [('java.io.tmpdir','tmp'),('user.home','runtime-home'),('java.library.path','empty-native')]:
            flag='-D'+key+'='+str(run/folder)
            require(flag in argv or '-J'+flag in argv,'Owned JVM tmp/home/native path required')
        return scope['command'](argv,run,env,label)
    java_home=java_home.resolve(strict=True)
    tools={n:(java_home/'bin'/(n+('.exe' if os.name=='nt' else ''))).resolve(strict=True) for n in ('java','javac')}
    require(all(p.is_file() and p.parent==java_home/'bin' for p in tools.values()),'Canonical existing JDK required')
    manifest=FIXTURES/'manifest.json';fixture=json.loads(capture(manifest))
    require(fixture['schema']=='retained-root-view-authored-models/v1','Model source schema differs')
    selected=fixture['actualSelectedSdk'];require(isinstance(selected,dict),'Actual SDK selection required before use')
    sdk_receipt=sdk_receipt.resolve(strict=True);sdk_receipt.relative_to(ROOT/'out')
    sdk=json.loads(capture(sdk_receipt,selected['receiptSha256']))
    require(sdk['schema']=='retained-root-guard-view-source-build/v2' and sdk['status']=='PASS_ROOT_GUARD_VIEW_COMPOSED_NATIVE_STATIC_AND_SDK_ONLY','Actual complete guard/readiness SDK receipt required')
    require(sdk['classPins']==selected['classPins'] and sdk['modelClassPins']==selected['modelClassPins'],'SDK maps differ')
    program=sdk['modelClassPins'];groups=sdk['logicalClassGroups']
    require(set(sdk['classPins'])-set(program)=={SPAWN} and all(sdk['classPins'][n]==h for n,h in program.items()),'Only actual Spawn may be excluded')
    group_names={k:set(v) for k,v in groups.items()}
    require(set(group_names)=={'host','app','sharedProtocol'} and not(group_names['host']&group_names['app']) and not(group_names['host']&group_names['sharedProtocol']) and not(group_names['app']&group_names['sharedProtocol']) and set.union(*group_names.values())==set(sdk['classPins']),'Exact SDK role closure required')
    host={n:h for n,h in program.items() if n in group_names['host']}
    app={n:h for n,h in program.items() if n not in group_names['host']}
    run_source=(ROOT/relative(sdk['run'])).resolve(strict=True);run_source.relative_to(ROOT/'out')
    model_source=(ROOT/relative(sdk['modelClassDirectory'])).resolve(strict=True);model_source.relative_to(ROOT/'out')
    require(sdk_receipt.parent==run_source and class_map(run_source/'classes')==sdk['classPins'] and class_map(model_source)==program,'Actual SDK bytes/placement differ')
    for path in [Path(__file__),*tools.values()]:capture(path)
    require(sdk['sourcePins']==selected['sourcePins'],'Source binding differs')
    for name,expected in sdk['sourcePins'].items():capture(ROOT/relative(name),expected)
    baseline=fixture['baselineManifest'];capture(ROOT/relative(baseline['path']),baseline['sha256'])
    actual_staged={}
    for p,h in sdk['stagedSourcePins'].items():
        actual=Path(p).resolve(strict=True);actual.relative_to(run_source)
        actual_staged[actual.relative_to(ROOT).as_posix()]=h
    require(actual_staged==selected['compiledSourcePins'],'Actual composed compiler sources differ')
    compiled=sdk['compiledSourceInputs']
    require(sdk['composedSourcePins']==selected['composedSourcePins']
            and {p:v['compiledSha256'] for p,v in compiled.items()}==sdk['composedSourcePins'],
            'Actual compiler composition map differs')
    for logical,record in compiled.items():
        require(record['logicalOriginalPath']==logical
                and record['baseSha256']==sdk['sourcePins'][logical]
                and actual_staged[(ROOT/relative(record['stagedPath'])).resolve(strict=True).relative_to(ROOT).as_posix()]==record['compiledSha256'],
                'Staged composed compiler bytes differ')
    for name,expected in actual_staged.items():capture(ROOT/relative(name),expected)
    sources={role:[] for role in ('framework','integration-framework','service','regression-driver','view-framework','control','view-driver')};destinations=set()
    for item in fixture['sourceRows']:
        role=item['role'];name=relative(item['relative']);source=(ROOT/relative(item['repoPath'])).resolve(strict=True)
        require(role in sources and source.suffix=='.java' and source.is_relative_to(ROOT/'compat'),'Only normal authored sources permitted')
        require((role,str(name)) not in destinations,'Duplicate destination');destinations.add((role,str(name)))
        capture(source,item['sha256']);sources[role].append((name,source))
    for name,expected in program.items():capture(model_source/relative(name),expected)
    def boundary():
        for path,pin in pins.items():require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'Original input changed: '+str(path))
        require(class_map(run_source/'classes')==sdk['classPins'] and class_map(model_source)==program,'Original SDK closure changed')
    boundary();output(BASE).mkdir(exist_ok=True);run=output(BASE/('r-'+uuid.uuid4().hex[:8]));run.mkdir()
    print(json.dumps({'run':run.relative_to(ROOT).as_posix(),'productionRecompiled':False}),flush=True)
    result={'schema':'retained-root-view-authored-tests/v1','status':'FAILED','commands':{},'productionRecompiled':False,'onlyProductionReplacement':SPAWN,'privateProductionStateInspected':False,'nativeOrAndroidExecuted':False,'sdkReceipt':{'path':sdk_receipt.relative_to(ROOT).as_posix(),**pins[sdk_receipt]}}
    try:
        for folder in ('inputs','src','program-host','program-app','framework','integration-framework','service','regression-driver','view-framework','control','view-driver','tmp','runtime-home','empty-native','empty-classpath','fixture-data'):output(run/folder).mkdir()
        snapshots={};staged={role:[] for role in sources}
        for index,(path,pin) in enumerate(sorted(pins.items(),key=lambda x:str(x[0]))):
            target=run/'inputs'/('%03d-'%index+path.name);target.write_bytes(captured[path]);snapshots[str(path)]={'path':target.relative_to(ROOT).as_posix(),**pin}
        for role,rows in sources.items():
            for name,path in rows:
                target=output(run/'src'/role/name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(captured[path]);staged[role].append(target)
        for role,rows in (('host',host),('app',app)):
            for name,expected in rows.items():
                target=output(run/('program-'+role)/relative(name));target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(captured[(model_source/name).resolve(strict=True)])
        env={k:v for k,v in os.environ.items() if k.upper() not in support['STRIP']}
        env.update(TMP=str(run/'tmp'),TEMP=str(run/'tmp'),TMPDIR=str(run/'tmp'),HOME=str(run/'runtime-home'),USERPROFILE=str(run/'runtime-home'))
        jvm=['-Xmx256m','-Djava.io.tmpdir='+str(run/'tmp'),'-Duser.home='+str(run/'runtime-home'),'-Djava.library.path='+str(run/'empty-native')]
        javac=[tools['javac'],*['-J'+v for v in jvm],'-proc:none','-implicit:none','-encoding','UTF-8','-source','8','-target','8','-sourcepath','']
        def copies():
            boundary()
            require(class_map(run/'program-app')==app and class_map(run/'program-host')==host,'Copied SDK bytes differ')
            for record in snapshots.values():require(sha(ROOT/record['path'])==record['sha256'],'Retained snapshot changed')
            for role,rows in sources.items():
                for (_,source),target in zip(rows,staged[role]):require(sha(target)==pins[source]['sha256'],'Staged source differs')
        for role in sources:
            copies()
            cp_roles=(('program-app','program-host') if role in ('framework','integration-framework')
                      else ('integration-framework',) if role=='service'
                      else ('view-framework','integration-framework','program-app','program-host') if role=='control'
                      else ('integration-framework','program-app','program-host') if role=='view-framework'
                      else ('empty-classpath',))
            cp=os.pathsep.join(str(run/name) for name in cp_roles)
            result['commands']['compile-'+role]=command([*javac,'-classpath',cp,'-d',run/role,*staged[role]],run,env,'compile-'+role,tools)
        maps={role:class_map(run/role) for role in sources}
        require(all(set(maps[r])&set(sdk['classPins'])=={SPAWN} for r in ('framework','integration-framework')) and not(set(maps['service'])&set(sdk['classPins'])),'Only fake OfferSpawn may shadow production')
        metadata={role:{name:links((run/role/name).read_bytes()) for name in rows} for role,rows in maps.items()}
        require(all(record['name']+'.class'==name for records in metadata.values() for name,record in records.items()),'Fixture internal names differ')
        require(set(maps['view-framework']).isdisjoint(sdk['classPins']) and set(maps['control']).isdisjoint(sdk['classPins']),'View fixtures must not shadow production')
        copies()
        result['commands']['regressions']=command([tools['java'],*jvm,'-Xint','-cp',run/'regression-driver','model.RetainedRootHandoffTest',run/'program-host',run/'program-app',run/'integration-framework',run/'service',run/'framework',run/'fixture-data',ROOT],run,env,'regressions',tools)
        lines=(run/'regressions.stdout').read_text(encoding='utf-8').splitlines();regressions=json.loads(lines[-1])
        require(lines[:-1]==['MODEL_CASE '+str(n) for n in range(16)]+['HOST_MODEL_CASE '+str(n) for n in range(16)] and regressions.get('pass') is True and regressions.get('modeledOnly') is True and regressions.get('cases')==32,'Original 32 regression cases or cleanup discriminator failed')
        copies()
        result['commands']['view-models']=command([tools['java'],*jvm,'-Xint','-cp',run/'view-driver','model.RetainedRootViewTest',run/'program-host',run/'program-app',run/'integration-framework',run/'service',run/'view-framework',run/'fixture-data',ROOT,run/'control'],run,env,'view-models',tools)
        lines=(run/'view-models.stdout').read_text(encoding='utf-8').splitlines();tests=json.loads(lines[-1])
        require(lines[:-1]==['VIEW_HARNESS_CLEANUP_DISCRIMINATOR']+['VIEW_MODEL_CASE '+str(n) for n in range(fixture['viewCases'])] and tests.get('pass') is True and tests.get('modeledOnly') is True and tests.get('cases')==fixture['viewCases'] and type(tests.get('checks')) is int and tests['checks']>0,'Actual source-issued view result differs')
        copies();require(maps=={r:class_map(run/r) for r in sources},'Fixture class map changed')
        require(not list((run/'fixture-data').iterdir()),'Fixture data not empty after cleanup')
        result.update(status='PASS_AUTHORED_PRIVATE_VIEW_AND_HANDOFF_MODELS_ONLY',tests=tests,regressions=regressions,programClassPinsBeforeAfter=program,fixtureClassPinsBeforeAfter=maps,fixtureClassMetadata=metadata,inputSnapshots=snapshots,stagedSourcePins={p.relative_to(ROOT).as_posix():sha(p) for paths in staged.values() for p in paths})
    except BaseException as failure:
        result.update(failureType=type(failure).__name__,failureMessage=str(failure)[:2048])
        # command() saves the actual terminal/reap record before raising on exit!=0.
        # Preserve that earned result in this receipt without replacing the original failure.
        for label in ['compile-'+r for r in sources]+['regressions','view-models']:
            terminal=run/(label+'.result.json')
            if label not in result['commands'] and terminal.is_file():
                try:
                    require(terminal.stat().st_size<=2*1024*1024,'Bounded command record required')
                    result['commands'][label]=json.loads(terminal.read_bytes())
                except BaseException as metadata_failure:
                    result.setdefault('commandRecordReadFailures',{})[label]=type(metadata_failure).__name__
        raise
    finally:
        save(run/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':(run/'receipt.json').relative_to(ROOT).as_posix(),'receiptSha256':sha(run/'receipt.json')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home',type=Path,required=True)
    parser.add_argument('--sdk-receipt',type=Path,required=True)
    args=parser.parse_args();build(args.java_home,args.sdk_receipt)
