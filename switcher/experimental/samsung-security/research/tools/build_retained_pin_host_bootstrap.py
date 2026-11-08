"""Package the separately reviewed capture-only host module; default prints a plan.

--package requires explicit pinned SDK/source/peer inputs within owned output.
No javac, source rewriting, model/OEM/Android execution, installation or ADB.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import threading
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).absolute().parent.parent
OUT = ROOT / 'out/retained-pin-host-bootstrap-apk'
SOURCE = ROOT / 'compat/host-module'
AUTH = 'com/appleexploit/oneos/security/authority/'
FRESH = {AUTH+n+'.class' for n in [
    'RetainedPinHostModule', 'RetainedPinHostModule$1', 'RetainedPinHostModule$Entry',
    'RetainedPinHostModule$HostBootstrapController', 'HostBootstrapPermit',
    'PreparedRetainedPinBinding', 'PreparedRetainedPinBinding$Current',
    'PreparedRetainedPinBinding$Subject', 'PreparedRetainedPinBinding$Metadata']}
DEPS = {AUTH+n+'.class' for n in [
    'PreparedRetainedUserRegistryCapture', 'PreparedRetainedUserRegistryCapture$Metadata',
    'PreparedRetainedSecurityFamilyCapture', 'PreparedRetainedSecurityFamilyCapture$Metadata',
    'PreparedRetainedPinOperationOwner', 'PreparedRetainedPinOperationOwner$Call',
    'PreparedRetainedLockSettingsLocalOwner', 'PreparedRetainedLockSettingsLocalOwner$Metadata',
    'PreparedRetainedLockSettingsLocalOwner$MetricsMetadata',
    'PreparedRetainedPasswordMetrics', 'PreparedRetainedPasswordMetrics$Snapshot']}
ABI = {'com/android/internal/widget/'+n+'.class' for n in ['LockscreenCredential', 'VerifyCredentialResponse']}
DESCRIPTORS = ['META-INF/xposed/module.prop', 'META-INF/xposed/scope.list', 'META-INF/xposed/java_init.list']
PACKAGING = ['AndroidManifest.xml', *['resources/'+n for n in DESCRIPTORS]]
PACKAGE = 'com.appleexploit.oneos.security.pinhostbootstrap'
CERT = 'ad40f7c185abb46a5ba4798625e3245333987594379e5014aa0c977e69febfc9'
PARSER_SHA = 'dc4bd404d0720402faabf367689843b3da8c4d23de8b5614ae95e9fd5db780b3'
SOURCE_PASS_SHA = '792b7e2ce9ad01458c4fe9c3a92991cd036ce00c59472ce2741b40a4e680558f'
NS = '{http://schemas.android.com/apk/res/android}'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_json(path):
    raw = path.read_bytes()
    require(len(raw) <= 2*1024*1024, 'bounded metadata input required')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique)


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def pinned(row, repository_only=True):
    require(isinstance(row, dict) and set(row) == {'path', 'sha256'}, 'exact path/hash record')
    require(isinstance(row['path'], str) and re.fullmatch('[a-f0-9]{64}', row['sha256']), 'literal pin required')
    path = Path(row['path'])
    path = (ROOT/path if not path.is_absolute() else path).resolve(strict=True)
    require(path.is_file() and not path.is_symlink(), 'regular input required')
    if repository_only:
        require(path.is_relative_to(ROOT.parent.resolve(strict=True)), 'repository input required')
    require(sha(path) == row['sha256'], 'input pin differs: '+str(path))
    return path


def pointer(value, selected):
    require(isinstance(selected, str) and selected.startswith('/') and '~' not in selected, 'simple JSON pointer required')
    for key in selected[1:].split('/'):
        require(isinstance(value, dict) and key in value, 'missing SDK receipt map')
        value = value[key]
    require(isinstance(value, dict), 'SDK class pin map required')
    return value


def parsers(path):
    # Extract only two frozen first-party pure functions, never a producer main.
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PARSER_SHA, 'frozen declaration parser differs')
    tree = ast.parse(raw.decode('utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'class_name', 'dex_names'}]
    require(len(nodes) == 2, 'exact parser function subset')
    scope = {'struct': struct, 'hashlib': hashlib}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope, raw


def command(argv, work, label, allowed):
    argv = list(map(str, argv))
    require(Path(argv[0]).resolve(strict=True) in allowed, 'only admitted build executables')
    env = {k:str(work/v) for k,v in [('TMP','tmp'),('TEMP','tmp'),('TMPDIR','tmp'),('HOME','home'),('USERPROFILE','home')]}
    event = {'argv':argv,'cwd':str(work),'environment':env,'startedUtc':datetime.now(timezone.utc).isoformat(),
             'timeoutSeconds':45,'combinedOutputLimitBytes':2*1024*1024}
    save(work/(label+'.command.json'),event)
    streams = [bytearray(),bytearray()]
    lock = threading.Lock()
    capped = threading.Event()
    reader_failed = threading.Event()
    reader_errors = []
    proc = None
    readers = []
    reason = None
    primary = None
    cleanup_errors = []
    code = None
    started = time.monotonic()
    def reader_error(failure):
        with lock:
            reader_errors.append(type(failure).__name__)
        reader_failed.set()
    def drain(pipe, index):
        try:
            while True:
                block = pipe.read(4096)
                if not block:
                    break
                with lock:
                    if sum(map(len,streams))+len(block)>2*1024*1024:
                        capped.set()
                        break
                    streams[index].extend(block)
        except BaseException as failure:
            reader_error(failure)
        finally:
            try:
                pipe.close()
            except BaseException as failure:
                reader_error(failure)
    try:
        proc = subprocess.Popen(argv,cwd=work,env=env,stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        readers = [threading.Thread(target=drain,args=(pipe,i),daemon=True)
                   for i,pipe in enumerate((proc.stdout,proc.stderr))]
        for reader in readers:
            reader.start()
        while proc.poll() is None:
            if capped.is_set() or reader_failed.is_set() or time.monotonic()-started>45:
                reason = 'output-limit' if capped.is_set() else 'reader-error' if reader_failed.is_set() else 'timeout'
                break
            time.sleep(0.02)
    except BaseException as failure:
        primary = type(failure).__name__
        reason = reason or 'spawn-or-post-spawn-exception'
    finally:
        # The retained Popen owns cleanup from the instant creation succeeds.
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.kill()
            except BaseException as failure:
                cleanup_errors.append('terminate:'+type(failure).__name__)
            try:
                code = proc.wait(timeout=5)
            except BaseException as failure:
                cleanup_errors.append('wait:'+type(failure).__name__)
            for reader in readers:
                try:
                    if reader.ident is not None:
                        reader.join(timeout=2)
                except BaseException as failure:
                    cleanup_errors.append('reader-join:'+type(failure).__name__)
            # Do not block on a buffered lock held by an incomplete reader.
            for i,pipe in enumerate((proc.stdout,proc.stderr)):
                if i>=len(readers) or readers[i].ident is None:
                    try:
                        pipe.close()
                    except BaseException as failure:
                        cleanup_errors.append('unstarted-pipe:'+type(failure).__name__)
    incomplete = any(reader.is_alive() for reader in readers)
    if incomplete:
        reason = reason or 'reader-incomplete'
    if cleanup_errors:
        reason = reason or 'owned-cleanup-uncertain'
    with lock:
        frozen = [bytes(value) for value in streams]
    logs = []
    for i,name in enumerate(['stdout','stderr']):
        path = work/(label+'.'+name+'.log')
        path.write_bytes(frozen[i])
        logs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':len(frozen[i])})
    event.update(exitCode=code,boundedFailure=reason,primaryExceptionType=primary,
                 ownedCleanupErrors=cleanup_errors,ownedProcessReaped=proc is not None and code is not None,
                 descendantCleanupClaimed=False,readerFailures=reader_errors,readerIncomplete=incomplete,logs=logs)
    save(work/(label+'.result.json'),event)
    require(code==0 and not reason and not primary and not cleanup_errors and not capped.is_set()
            and not reader_failed.is_set() and not incomplete, 'bounded command failed; no retry: '+label)
    return event, (frozen[0]+frozen[1]).decode('utf-8','strict')


def source_profile(path):
    manifest = ET.fromstring((path/'AndroidManifest.xml').read_bytes())
    require(manifest.tag == 'manifest' and manifest.attrib == {'package':PACKAGE,NS+'versionCode':'1',NS+'versionName':'0.0.1-capture-only'}, 'manifest identity')
    require([n.tag for n in manifest] == ['uses-sdk','application'], 'no permissions or other components')
    sdk,app = list(manifest)
    require(sdk.attrib == {NS+'minSdkVersion':'37',NS+'targetSdkVersion':'37'}, 'SDK37 profile')
    require(not list(app) and app.attrib == {NS+'label':'OneOS PIN host bootstrap capture',NS+'allowBackup':'false',NS+'hasCode':'true',NS+'extractNativeLibs':'false'}, 'application profile')
    require((path/'resources'/DESCRIPTORS[0]).read_bytes() == b'minApiVersion=102\ntargetApiVersion=102\nstaticScope=true\nautoHotReload=false\n', 'Vector metadata')
    require((path/'resources'/DESCRIPTORS[1]).read_bytes() == b'android\n', 'android-only scope')
    require((path/'resources'/DESCRIPTORS[2]).read_bytes() == b'com.appleexploit.oneos.security.authority.RetainedPinHostModule\n', 'single module entry')


def apk_contents(path, payloads):
    with zipfile.ZipFile(path) as z:
        require(z.namelist() == list(payloads) and not z.comment and z.testzip() is None, 'exact APK entries/CRC')
        for name,data in payloads.items():
            item = z.getinfo(name)
            require(not item.is_dir() and not item.flag_bits & 1 and item.file_size == len(data)
                    and z.read(name) == data, 'APK payload differs: '+name)
    return {name:hashlib.sha256(data).hexdigest() for name,data in payloads.items()}


def stage_map(work):
    result = {}
    for folder in ['classes','abi','source']:
        for path in sorted((work/folder).rglob('*')):
            require(not path.is_symlink(), 'no staged symlinks')
            if path.is_file():
                result[path.relative_to(work).as_posix()] = sha(path)
            else:
                require(path.is_dir(), 'only staged directories/files')
    return result


def package(inputs_path):
    inputs_path = inputs_path.resolve(strict=True)
    m = read_json(inputs_path)
    require(m['schema'] == 'retained-pin-host-apk-inputs/v1', 'input schema')
    required = {'schema','sourcePass','sdkReceipt','sdkSavedReview','sdkFreshMap','sdkDependencyMap',
                'sdkAbiMap','classes','compilerOnlyAbi','packaging','tools','declarationParser'}
    require(set(m) == required, 'exact input schema')
    source_pass = pinned(m['sourcePass'])
    require(sha(source_pass) == SOURCE_PASS_SHA, 'reviewed production source pass required')
    receipt_path = pinned(m['sdkReceipt'])
    peer = pinned(m['sdkSavedReview'])
    receipt = read_json(receipt_path)
    require(receipt.get('status') == 'PASS_CAPTURE_ONLY_BOOTSTRAP_SDK_D8', 'successful actual SDK receipt required')
    review = read_json(peer)
    require(review.get('schema') == 'retained-pin-host-bootstrap-independent-sdk-saved-review/v1'
            and review.get('status') == 'PASS_SAVED_SDK_D8_CAPTURE_ONLY'
            and review.get('receipt',{}).get('sha256') == sha(receipt_path)
            and review.get('sourcePass',{}).get('sha256') == SOURCE_PASS_SHA
            and type(review.get('freshClassCount')) is int and review['freshClassCount'] == 9
            and type(review.get('unchangedDependencyCount')) is int and review['unchangedDependencyCount'] == 11
            and review.get('sdkApi102WidgetDefinitionsExcluded') is True,
            'independent SDK review must bind this actual receipt/source/closure')
    fresh = pointer(receipt,m['sdkFreshMap'])
    deps = pointer(receipt,m['sdkDependencyMap'])
    abi = pointer(receipt,m['sdkAbiMap'])
    require(set(fresh) == FRESH and set(deps) == DEPS and set(abi) == ABI, 'actual 9/11/2 receipt closure required')
    require(set(m['classes']) == FRESH|DEPS and set(m['compilerOnlyAbi']) == ABI, 'standalone20/ABI2 closure')
    for name,row in m['classes'].items():
        require(row['sha256'] == (fresh|deps)[name], 'actual SDK/dependency class differs')
    for name,row in m['compilerOnlyAbi'].items():
        require(row['sha256'] == abi[name], 'actual compiler-only ABI differs')
    require(set(m['packaging']) == set(PACKAGING), 'exact four packaging inputs')
    require(set(m['tools']) == {'java','aapt2','zipalign','apksigner','d8','androidJar','vectorApi','keystore'}, 'explicit existing toolpaths')
    tools = {key:pinned(row,repository_only=key!='java') for key,row in m['tools'].items()}
    parser_path = pinned(m['declarationParser'])
    functions, parser_bytes = parsers(parser_path)
    all_inputs = [inputs_path,Path(__file__).resolve(strict=True),source_pass,receipt_path,peer,parser_path,*tools.values()]
    for rows in [m['classes'],m['compilerOnlyAbi'],m['packaging']]:
        all_inputs.extend(pinned(row) for row in rows.values())
    pins = {str(p):sha(p) for p in all_inputs}
    require(OUT.parent.resolve(strict=True).is_relative_to(ROOT.resolve(strict=True)), 'owned output parent')
    OUT.mkdir(parents=True,exist_ok=True)
    require(OUT.resolve(strict=True).is_relative_to(ROOT.resolve(strict=True)), 'owned output root')
    work = OUT/('r-'+uuid.uuid4().hex[:12])
    work.mkdir()
    for n in ['tmp','home','empty-native','source','classes','abi','dex','linked','snapshots']:
        (work/n).mkdir()
    print(json.dumps({'work':work.relative_to(ROOT).as_posix()}),flush=True)
    result = {'schema':'retained-pin-host-apk-build/v1','status':'FAILED_OR_UNCERTAIN_PC_PACKAGING',
              'inputsBefore':pins,'commands':{},'selected':False,'installed':False,
              'javac':False,'models':False,'androidOrOemRuntimeOrDevice':False}
    allowed = {tools[k] for k in ['java','aapt2','zipalign']}
    try:
        metadata = [inputs_path,Path(__file__).resolve(strict=True),source_pass,receipt_path,peer]
        for index,path in enumerate(metadata):
            target = work/'snapshots'/('%03d-'%index+path.name)
            shutil.copyfile(path,target)
            require(sha(target) == pins[str(path)], 'snapshot differs')
        retained_parser = work/'snapshots/executed-declaration-parser.py'
        retained_parser.write_bytes(parser_bytes)
        require(sha(retained_parser) == PARSER_SHA, 'retained executed parser differs')
        result['executedParser'] = {'path':retained_parser.relative_to(ROOT).as_posix(),'sha256':PARSER_SHA}
        staged = {}
        for folder,rows in [('classes',m['classes']),('abi',m['compilerOnlyAbi'])]:
            for name,row in rows.items():
                target = work/folder/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(pinned(row),target)
                require(sha(target) == row['sha256'] and functions['class_name'](target)+'.class' == name, 'staged class identity')
                staged[target.relative_to(work).as_posix()] = sha(target)
        for name,row in m['packaging'].items():
            target = work/'source'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(pinned(row),target)
            require(sha(target) == row['sha256'], 'staged packaging differs')
            staged[target.relative_to(work).as_posix()] = sha(target)
        source_profile(work/'source')
        require(stage_map(work) == staged, 'complete staged closure before D8')
        save(work/'pre-tools-staged-pins.json',staged)
        jvm = ['-Xmx512m','-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'home'),'-Djava.library.path='+str(work/'empty-native')]
        java = [tools['java'],*jvm]
        commands = result['commands']
        commands['d8'],warning = command([*java,'-cp',tools['d8'],'com.android.tools.r8.D8','--min-api','37','--lib',tools['androidJar'],'--classpath',tools['vectorApi'],'--classpath',work/'abi','--output',work/'dex',*[work/'classes'/n for n in sorted(m['classes'])]],work,'compose20-d8',allowed)
        dex = work/'dex/classes.dex'
        require({p.name for p in (work/'dex').iterdir()} == {'classes.dex'}, 'one DEX only')
        expected = {'L'+name[:-6]+';' for name in FRESH|DEPS}
        names = functions['dex_names'](dex)
        require(len(names) == 20 and set(names) == expected, 'exact20 authored definitions; no ABI/API/OEM')
        commands['link'],_ = command([tools['aapt2'],'link','--output-to-dir','-o',work/'linked','--manifest',work/'source/AndroidManifest.xml','-I',tools['androidJar']],work,'manifest-link',allowed)
        linked = {p.name:p for p in (work/'linked').iterdir()}
        require(set(linked) in [{'AndroidManifest.xml'},{'AndroidManifest.xml','resources.arsc'}]
                and all(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<=1024*1024 for p in linked.values()), 'manifest-only aapt output profile')
        payloads = {name:linked[name].read_bytes() for name in ['AndroidManifest.xml','resources.arsc'] if name in linked}
        payloads.update({'classes.dex':dex.read_bytes(),**{name:(work/'source/resources'/name).read_bytes() for name in DESCRIPTORS}})
        unsigned = work/'unsigned.apk'
        with zipfile.ZipFile(unsigned,'x',allowZip64=False) as z:
            for name,data in payloads.items():
                info = zipfile.ZipInfo(name,(1980,1,1,0,0,0))
                info.create_system=3
                info.external_attr=(stat.S_IFREG|0o644)<<16
                info.compress_type=zipfile.ZIP_STORED
                z.writestr(info,data)
        apk_contents(unsigned,payloads)
        aligned = work/'aligned-unsigned.apk'
        commands['align'],_ = command([tools['zipalign'],'-p','4',unsigned,aligned],work,'zipalign',allowed)
        apk_contents(aligned,payloads)
        key = work/'debug.keystore'
        shutil.copyfile(tools['keystore'],key)
        require(sha(key) == m['tools']['keystore']['sha256'], 'own copied keystore differs')
        signer = [*java,'-jar',tools['apksigner']]
        apk = work/'OneOS-PIN-Host-Bootstrap-0.0.1-capture-only.apk'
        commands['sign'],_ = command([*signer,'sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--ks-key-alias','coloros-preview','--v1-signing-enabled','false','--v2-signing-enabled','true','--v3-signing-enabled','true','--v4-signing-enabled','false','--out',apk,aligned],work,'sign',allowed)
        payload_pins = apk_contents(apk,payloads)
        commands['verify'],signature = command([*signer,'verify','--verbose','--print-certs',apk],work,'verify-signature',allowed)
        certs = re.findall(r'certificate SHA-256 digest: ([a-f0-9]{64})',signature)
        require(certs and set(certs) == {CERT} and 'Verified using v3 scheme (APK Signature Scheme v3): true' in signature, 'genuine v3 verification and expected debug cert')
        commands['alignment'],_ = command([tools['zipalign'],'-c','4',apk],work,'verify-alignment',allowed)
        commands['badging'],badging = command([tools['aapt2'],'dump','badging',apk],work,'badging',allowed)
        require("package: name='"+PACKAGE+"' versionCode='1' versionName='0.0.1-capture-only'" in badging
                and "minSdkVersion:'37'" in badging and "targetSdkVersion:'37'" in badging
                and not any(x in badging for x in ['uses-permission:','launchable-activity:','native-code:']), 'compiled manifest profile')
        require(stage_map(work) == staged and not list((work/'empty-native').iterdir()), 'staged input/native isolation drift')
        result.update(status='PASS_PC_CAPTURE_ONLY_APK',apk={'path':apk.relative_to(ROOT).as_posix(),'sha256':sha(apk),'bytes':apk.stat().st_size},
                      dex={'path':dex.relative_to(ROOT).as_posix(),'sha256':sha(dex),'bytes':dex.stat().st_size,'definitions':sorted(names)},
                      payloadPins=payload_pins,stagedPinsBeforeAfter=staged,d8Diagnostics=warning,
                      api37RuntimeAccepted=False,scope=['android'],endpointOrOwnerOpenOrVerify=False)
    except BaseException as failure:
        result['failure'] = type(failure).__name__+': '+str(failure)
        raise
    finally:
        result['inputsAfter'] = {}
        for path in all_inputs:
            try:
                result['inputsAfter'][str(path)] = sha(path)
            except OSError:
                result['inputsAfter'][str(path)] = None
        result['inputPinsUnchanged'] = result['inputsBefore'] == result['inputsAfter']
        if not result['inputPinsUnchanged']:
            result['status'] = 'FAILED_INPUT_MOVED'
        save(work/'receipt.json',result)
    print(json.dumps({'status':result['status'],'receipt':(work/'receipt.json').relative_to(ROOT).as_posix(),'receiptSha256':sha(work/'receipt.json')}),flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',action='store_true')
    p.add_argument('--inputs',type=Path)
    a = p.parse_args(argv)
    if not a.package:
        print(json.dumps({'status':'PLAN_ONLY_NO_TOOLS','programDefinitions':20,'fresh':9,'immutableDependencies':11,
                          'sdkAndIndependentSavedReview':'PENDING_EXACT_INPUTS','sourcePass':SOURCE_PASS_SHA,
                          'toolPaths':'explicit existing path/hash records in --inputs','phone':False}))
        return
    require(a.inputs is not None, 'explicit pinned inputs required')
    package(a.inputs)


if __name__ == '__main__':
    main()
