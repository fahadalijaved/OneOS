"""Compile the eleven retained-PIN sources from this checkout; default is plan-only.

Explicit --build uses existing local JDK/SDK37/API102/D8 paths. No downloads,
saved classfile inputs, source rewriting, models, Android/OEM execution or ADB.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).absolute().parent.parent
OUT = ROOT/'out/retained-pin-source-build'
AUTH = 'com/appleexploit/oneos/security/authority/'
TRANSPORT = 'com/appleexploit/oneos/security/transport/'
SOURCES = ['compat/android/'+AUTH+n+'.java' for n in [
    'PreparedRetainedUserRegistryCapture', 'PreparedRetainedSecurityFamilyCapture',
    'PreparedRetainedPinBinding', 'PreparedRetainedPinOperationOwner',
    'PreparedRetainedPinCheckOwner',
    'PreparedRetainedLockSettingsLocalOwner', 'PreparedRetainedPasswordMetrics',
    'PreparedRetainedPinEndpoint']]+[
    'compat/android/'+TRANSPORT+'PreparedRetainedPinEndpointClient.java',
    'compat/host-module/'+AUTH+'RetainedPinHostModule.java',
    'compat/host-module/'+AUTH+'HostBootstrapPermit.java']
PROJECTIONS = ['compat/compile-only/pin-endpoint/'+n+'.java' for n in [
    'android/os/Parcel', 'com/android/internal/widget/LockscreenCredential',
    'com/android/internal/widget/VerifyCredentialResponse']]
ABI_NAMES = {n[len('compat/compile-only/pin-endpoint/'):-5]+'.class' for n in PROJECTIONS}
EXPECTED = {AUTH+n+'.class' for n in [
    'PreparedRetainedUserRegistryCapture', 'PreparedRetainedUserRegistryCapture$Metadata',
    'PreparedRetainedSecurityFamilyCapture', 'PreparedRetainedSecurityFamilyCapture$Metadata',
    'PreparedRetainedPinBinding', 'PreparedRetainedPinBinding$Current',
    'PreparedRetainedPinBinding$Subject', 'PreparedRetainedPinBinding$Metadata',
    'PreparedRetainedPinOperationOwner', 'PreparedRetainedPinOperationOwner$Call',
    'PreparedRetainedPinCheckOwner', 'PreparedRetainedPinCheckOwner$Call',
    'PreparedRetainedLockSettingsLocalOwner', 'PreparedRetainedLockSettingsLocalOwner$Metadata',
    'PreparedRetainedLockSettingsLocalOwner$MetricsMetadata', 'PreparedRetainedPasswordMetrics',
    'PreparedRetainedPasswordMetrics$Snapshot', 'PreparedRetainedPinEndpoint',
    'RetainedPinHostModule', 'RetainedPinHostModule$1', 'RetainedPinHostModule$Entry',
    'RetainedPinHostModule$HostBootstrapController', 'HostBootstrapPermit']}
EXPECTED.add(TRANSPORT+'PreparedRetainedPinEndpointClient.class')
HELPERS = {
    'tools/build_retained_pin_host_bootstrap.py': (
        '43637dd8d1618c925f5676abf9a0fd4d04336bdbb015eb3e2e94ba7b059815d5',
        {'require','sha','save','command'}),
    'tools/test_credential_transport.py': (
        'dc4bd404d0720402faabf367689843b3da8c4d23de8b5614ae95e9fd5db780b3',
        {'class_name','dex_names'})}
LIBRARY_PINS = {
    'android_jar':'bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177',
    'api102':'a515dd7a53cd7a47c05e101dff77d61acb3091a97b20a885b9ea3494412db985',
    'd8':'a26ee56252adcff6752c379ae255a0ad538ebec60189e078ec6855487107637d'}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def captured(path, limit):
    need(path.is_file() and not path.is_symlink(), 'regular nonsymlink input required: '+str(path))
    raw = path.read_bytes()
    need(0<len(raw)<=limit, 'bounded input required: '+str(path))
    return raw


def tree_map(path):
    result = {}
    for entry in sorted(path.rglob('*')):
        need(not entry.is_symlink(), 'no generated symlinks')
        if entry.is_file():
            result[entry.relative_to(path).as_posix()] = digest(entry.read_bytes())
        else:
            need(entry.is_dir(), 'generated regular file/directory only')
    return result


def load_helpers(blobs, work):
    scope = {'ROOT':ROOT,'Path':Path,'datetime':datetime,'timezone':timezone,
             'hashlib':hashlib,'json':json,'struct':struct,'subprocess':subprocess,
             'threading':threading,'time':time}
    retained = {}
    for name,(expected,wanted) in HELPERS.items():
        raw = blobs[name]
        need(digest(raw)==expected, 'reviewed normal helper differs: '+name)
        target = work/'captured-helpers'/Path(name).name
        target.write_bytes(raw)
        need(digest(target.read_bytes())==expected, 'retained helper differs')
        tree = ast.parse(raw.decode('utf-8'),filename=name)
        nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
        need(len(nodes)==len(wanted) and {n.name for n in nodes}==wanted, 'exact reviewed helper functions')
        # Execute only functions from the exact captured/retained normal source.
        exec(compile(ast.Module(body=nodes,type_ignores=[]),name,'exec'),scope)
        retained[name] = {'path':target.relative_to(ROOT).as_posix(),'sha256':expected,'functions':sorted(wanted)}
    return scope,retained


def build(args):
    source_blobs = {name:captured(ROOT/name,256*1024) for name in SOURCES+PROJECTIONS}
    helper_blobs = {name:captured(ROOT/name,256*1024) for name in HELPERS}
    for name,(expected,_) in HELPERS.items():
        need(digest(helper_blobs[name])==expected, 'reviewed helper pin differs')
    tools = {name:Path(getattr(args,name)).resolve(strict=True) for name in ['javac','java','android_jar','api102','d8']}
    need(len(set(tools.values()))==5, 'distinct explicit tool/library paths')
    need(all(path.is_file() for path in tools.values()), 'existing regular tool/library files required')
    tool_pins = {name:{'path':str(path),'sha256':digest(path.read_bytes())} for name,path in tools.items()}
    need(all(tool_pins[name]['sha256']==expected for name,expected in LIBRARY_PINS.items()),
         'captured SDK37/API102/D8 library differs; no version guessing or download')
    own_raw = captured(Path(__file__),256*1024)
    canonical_root = ROOT.resolve(strict=True)
    # A fresh checkout needs no preexisting ignored output tree.
    for directory in [OUT.parent,OUT]:
        need(directory.parent.resolve(strict=True).is_relative_to(canonical_root), 'owned output parent')
        if directory.exists() or directory.is_symlink():
            attributes = getattr(directory.lstat(),'st_file_attributes',0)
            need(not directory.is_symlink() and not attributes&0x400, 'no output reparse points')
        directory.mkdir(exist_ok=True)
        need(directory.resolve(strict=True)==canonical_root/directory.relative_to(ROOT), 'owned output root')
    work = OUT/('r-'+uuid.uuid4().hex[:12])
    work.mkdir()
    for name in ['tmp','home','empty-native','empty-classpath','source','projection-source','abi','classes','dex','captured-helpers']:
        (work/name).mkdir()
    print(json.dumps({'work':work.relative_to(ROOT).as_posix()}),flush=True)
    result = {'schema':'retained-pin-public-source-build/v1','status':'FAILED_OR_UNCERTAIN_PC_SOURCE_BUILD',
              'selected':False,'savedClassfileInputs':False,'sourceRewritten':False,
              'modelsExecuted':False,'androidOrOemRuntimeOrDevice':False,'commands':{},
              'sourcePins':{n:digest(v) for n,v in source_blobs.items()},'tools':tool_pins,
              'runnerSha256':digest(own_raw),'expectedProgramDefinitions':sorted(EXPECTED)}
    try:
        (work/'executed-runner.py').write_bytes(own_raw)
        helpers,retained = load_helpers(helper_blobs,work)
        result['capturedNormalHelpers'] = retained
        staged = {}
        for name,raw in source_blobs.items():
            folder = 'source' if name in SOURCES else 'projection-source'
            target = work/folder/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            staged[target.relative_to(work).as_posix()] = digest(raw)
        def staged_map():
            return {folder+'/'+name:value for folder in ['source','projection-source']
                    for name,value in tree_map(work/folder).items()}
        need(staged_map()==staged, 'complete exact fourteen-source closure')
        write_json(work/'precompiler-source-map.json',staged)
        jvm = ['-Xmx512m','-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'home'),'-Djava.library.path='+str(work/'empty-native')]
        javac = [tools['javac'],*['-J'+value for value in jvm],'-proc:none','-implicit:none',
                 '-encoding','UTF-8','-source','8','-target','8','-sourcepath','']
        allowed = {tools['javac'],tools['java']}
        command = helpers['command']
        class_name = helpers['class_name']
        commands = result['commands']
        commands['compileAbi'],_ = command([*javac,'-bootclasspath',tools['android_jar'],
            '-classpath',work/'empty-classpath','-d',work/'abi',
            *[work/'projection-source'/name for name in PROJECTIONS]],work,'compile-abi',allowed)
        abi = tree_map(work/'abi')
        need(set(abi)==ABI_NAMES, 'exact three compiler-only definitions')
        need(all(class_name(work/'abi'/name)+'.class'==name for name in abi), 'compiler ABI class identity')
        need(staged_map()==staged, 'staged source drift before production compiler')
        commands['compileProduction'],_ = command([*javac,'-bootclasspath',os.pathsep.join(map(str,[work/'abi',tools['android_jar']])),
            '-classpath',tools['api102'],'-d',work/'classes',
            *[work/'source'/name for name in SOURCES]],work,'compile-production',allowed)
        program = tree_map(work/'classes')
        result['observedProgramClasses'] = sorted(program)
        need(set(program)==EXPECTED and len(program)==24, 'actual complete twenty-four-class closure differs; no dropping or fallback')
        need(all(class_name(work/'classes'/name)+'.class'==name for name in program), 'authored Java8 class identity')
        need(tree_map(work/'abi')==abi and staged_map()==staged, 'pre-D8 complete map drift')
        write_json(work/'pred8-class-maps.json',{'program':program,'compilerOnlyAbi':abi})
        commands['d8'],diagnostics = command([tools['java'],*jvm,'-cp',tools['d8'],'com.android.tools.r8.D8',
            '--min-api','37','--lib',tools['android_jar'],'--classpath',tools['api102'],'--classpath',work/'abi',
            '--output',work/'dex',*[work/'classes'/name for name in sorted(program)]],work,'d8',allowed)
        dex = work/'dex/classes.dex'
        need({p.name for p in (work/'dex').iterdir()}=={'classes.dex'}, 'one fresh DEX required')
        definitions = helpers['dex_names'](dex)
        need(len(definitions)==24 and set(definitions)=={'L'+n[:-6]+';' for n in EXPECTED}, 'exact authored DEX closure; ABI/API/SDK/OEM excluded')
        need(tree_map(work/'classes')==program and tree_map(work/'abi')==abi
             and staged_map()==staged and not list((work/'empty-native').iterdir()), 'post-D8 complete input/output isolation drift')
        helper_map = {Path(name).name:expected for name,(expected,_) in HELPERS.items()}
        need(tree_map(work/'captured-helpers')==helper_map, 'retained executed helper bytes drifted')
        need((work/'executed-runner.py').read_bytes()==own_raw, 'retained runner drifted')
        result.update(status='PASS_PC_PUBLIC_SOURCE_SDK_D8_ONLY',classPins=program,compilerOnlyAbiPins=abi,
                      sourceMapsBeforeAfter=staged,capturedHelperPinsBeforeAfter=helper_map,dex={'path':dex.relative_to(ROOT).as_posix(),
                      'sha256':digest(dex.read_bytes()),'bytes':dex.stat().st_size,'definitions':sorted(definitions),
                      'sha1Adler32Verified':True},d8Diagnostics=diagnostics,api37RuntimeAccepted=False,
                      historicalLiteralReceiptModelsAccepted=False,prReadiness=False)
    except BaseException as failure:
        result['failure'] = type(failure).__name__+': '+str(failure)
        raise
    finally:
        changed = []
        for name,raw in {**source_blobs,**helper_blobs}.items():
            try:
                if (ROOT/name).read_bytes()!=raw:
                    changed.append(name)
            except OSError:
                changed.append(name)
        for name,path in tools.items():
            try:
                if digest(path.read_bytes())!=tool_pins[name]['sha256']:
                    changed.append(name)
            except OSError:
                changed.append(name)
        try:
            runner_changed = Path(__file__).read_bytes()!=own_raw
        except OSError:
            runner_changed = True
        if runner_changed:
            changed.append('runner')
        result['changedInputs'] = changed
        result['inputPinsUnchanged'] = not changed
        if changed:
            result['status'] = 'FAILED_INPUT_MOVED'
        write_json(work/'receipt.json',result)
    need(result['status']=='PASS_PC_PUBLIC_SOURCE_SDK_D8_ONLY', 'coherent pass required')
    print(json.dumps({'status':result['status'],'receipt':(work/'receipt.json').relative_to(ROOT).as_posix(),
                      'receiptSha256':digest((work/'receipt.json').read_bytes())}),flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    for name in ['javac','java','android-jar','api102','d8']:
        parser.add_argument('--'+name,type=Path)
    args = parser.parse_args(argv)
    if not args.build:
        print(json.dumps({'status':'PLAN_ONLY_NO_TOOLS','sources':SOURCES,'compilerOnlySources':PROJECTIONS,
                          'expectedProgramDefinitions':24,'oldClassfiles':False,'phone':False}))
        return
    need(all(getattr(args,n) is not None for n in ['javac','java','android_jar','api102','d8']),
         'explicit existing JDK/SDK37/API102/D8 paths required')
    build(args)


if __name__ == '__main__':
    main()
