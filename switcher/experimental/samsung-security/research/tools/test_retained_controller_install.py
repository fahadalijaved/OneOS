"""Test exact authored installer slices in repository-contained fixtures only.

Root owns execution. This tool never runs the full OneOS root script or native
asset. The installed sample is inert bytes, never an executable command.
"""
from pathlib import Path
import argparse
import subprocess,threading,time
import hashlib
import json
import os
import re
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'out/retained-controller-install-tests'
FIXTURES = ROOT / 'compat/models/retained-controller-install'
SHELL_CASES=['installed','old_rootsh','already_installed','short','long','corrupt','prefix_short','prefix_corrupt','stage_missing','bin_missing','stage_writable','bin_writable','existing_different','existing_directory','symlink_target','work_owned','racing_target','chmod_failure','cleanup_failure','replace_after_hash']
APP_CASES=['good','short','long','corrupt','asset_close','bad_expected_pin','bad_script','wrong_context','main','feed_error','lost_ack','duplicate_ack','reenter']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def exact_function(source, name):
    """Read a finite column-zero function from retained shell bytes.

    The admitted functions use no heredoc/column-zero inner brace. The selected
    raw span is hashed and staged unchanged; the full source is never sourced.
    """
    require(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name) is not None, 'Plain function name required')
    starts = list(re.finditer(rb'(?m)^' + name.encode('ascii') + rb'\(\)\s*([\{\(])[^\r\n]*(?:\r?\n|$)', source))
    require(len(starts) == 1, 'Exactly one source function required: ' + name)
    start = starts[0].start()
    first = starts[0].group().rstrip(b'\r\n')
    delimiter=starts[0].group(1);close=b'}' if delimiter==b'{' else b')'
    if first.rstrip().endswith(close):
        end = starts[0].end()
    else:
        closing = re.search(rb'(?m)^' + re.escape(close) + rb'[ \t]*(?:\r?\n|$)', source[starts[0].end():])
        require(closing is not None, 'Function close missing: ' + name)
        end = starts[0].end() + closing.end()
    raw = source[start:end]
    require(len(raw) <= 32768 and b'<<' not in raw, 'Bounded non-heredoc source profile required')
    return raw, {'name': name, 'offset': start, 'bytes': len(raw), 'sha256': digest(raw)}


def contained(path):
    path = Path(path)
    path.relative_to(ROOT)
    for parent in (path, *path.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            info = None
        if info is not None:
            require(not stat.S_ISLNK(info.st_mode), 'Output symlink refused')
            if os.name == 'nt':
                attrs = getattr(info, 'st_file_attributes', None)
                require(type(attrs) is int and not attrs & 0x400, 'Output reparse point refused')
        if parent == ROOT:
            break
    path.resolve().relative_to(ROOT.resolve())
    return path


STRIP={"CLASSPATH","JAVA_TOOL_OPTIONS","_JAVA_OPTIONS","JDK_JAVA_OPTIONS","JDK_JAVAC_OPTIONS","BASH_ENV","ENV","SHELLOPTS","BASHOPTS","CDPATH","GLOBIGNORE","PYTHONPATH","PYTHONHOME","PYTHONSTARTUP","PYTHONINSPECT"}

def save(path,value):
    with contained(path).open("x",encoding="utf-8") as stream:stream.write(json.dumps(value,indent=2)+"\n")

def command(argv,run,env,label,tools,stdin_path=None,allow_failure=False):
    """Bounded retained-handle child; explicit JDK/shell tools, never su or a native asset."""
    argv=list(map(str,argv))
    require(Path(argv[0]) in set(tools.values()),'Canonical explicitly supplied JDK executable required')
    require(contained(run)==run.resolve(),'Own canonical cwd required');run.relative_to(BASE)
    require(not any(key.upper() in STRIP for key in env),'Inherited JVM injection option')
    for key,folder in ([] if Path(argv[0])==tools['shell'] else [('java.io.tmpdir','tmp'),('user.home','runtime-home'),('java.library.path','empty-native')]):
        flag='-D'+key+'='+str(run/folder)
        require(flag in argv or '-J'+flag in argv,'Owned JVM tmp/home/native path required')
    record={'argv':argv,'cwd':str(run),'timeoutSeconds':45,'combinedTextOutputLimitBytes':2*1024*1024,
            'ownedEnvironment':{key:env[key] for key in ('TMP','TEMP','TMPDIR','HOME','USERPROFILE')},
            'childPath':env.get('PATH'),'clearedInjectionNames':sorted(STRIP)}
    save(run/(label+'.command.json'),record)
    start=time.monotonic();outputs=[bytearray(),bytearray()];lock=threading.Lock()
    overflow=threading.Event();reader_failed=threading.Event();reader_errors=[]
    opened_stdin=None;proc=None;threads=[];reason=None;primary=None;cleanup_errors=[];code=None
    def reader_error(failure):
        with lock:reader_errors.append(type(failure).__name__)
        reader_failed.set()
    def drain(pipe,which):
        try:
            while True:
                block=pipe.read(4096)
                if not block:break
                with lock:
                    if sum(map(len,outputs))+len(block)>2*1024*1024:overflow.set();break
                    outputs[which].extend(block)
        except BaseException as failure:reader_error(failure)
        finally:
            try:pipe.close()
            except BaseException as failure:reader_error(failure)
    try:
        if stdin_path is not None:
            stdin_path=contained(stdin_path);stdin_path.relative_to(run)
            require(stdin_path.stat().st_size<=4*1024*1024,'Bounded retained input')
            opened_stdin=stdin_path.open('rb')
        proc=subprocess.Popen(argv,cwd=run,env=env,stdin=opened_stdin if opened_stdin is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        threads=[threading.Thread(target=drain,args=(pipe,index),daemon=True) for index,pipe in enumerate((proc.stdout,proc.stderr))]
        for thread in threads:thread.start()
        while proc.poll() is None:
            if overflow.is_set() or reader_failed.is_set() or time.monotonic()-start>45:
                reason='output-limit' if overflow.is_set() else 'reader-error' if reader_failed.is_set() else 'timeout';break
            time.sleep(0.02)
    except BaseException as failure:primary=type(failure).__name__;reason=reason or 'spawn-or-post-spawn-exception'
    finally:
        # A successful Popen establishes ownership before any reader setup.
        if proc is not None:
            try:
                if proc.poll() is None:proc.kill()  # retained process object/handle only
            except BaseException as failure:cleanup_errors.append('terminate:'+type(failure).__name__)
            try:code=proc.wait(timeout=5)
            except BaseException as failure:cleanup_errors.append('wait:'+type(failure).__name__)
            for thread in threads:
                try:
                    if thread.ident is not None:thread.join(2)
                except BaseException as failure:cleanup_errors.append('reader-join:'+type(failure).__name__)
            # Never block on a buffered pipe lock held by another reader.
            for index,pipe in enumerate((proc.stdout,proc.stderr)):
                if index>=len(threads) or threads[index].ident is None:
                    try:pipe.close()
                    except BaseException as failure:cleanup_errors.append('unstarted-pipe:'+type(failure).__name__)
    if opened_stdin is not None:
        try:opened_stdin.close()
        except BaseException as failure:cleanup_errors.append('stdin-close:'+type(failure).__name__)
    incomplete=any(thread.is_alive() for thread in threads)
    if incomplete:reason=reason or 'reader-incomplete'
    if cleanup_errors:reason=reason or 'owned-cleanup-uncertain'
    with lock:frozen=[bytes(value) for value in outputs]
    streams={}
    for index,suffix in enumerate(('stdout','stderr')):
        path=contained(run/(label+'.'+suffix))
        with path.open('xb') as stream:stream.write(frozen[index])
        streams[suffix]={'path':path.relative_to(ROOT).as_posix(),'bytes':len(frozen[index]),'sha256':digest(frozen[index])}
    record.update(exitCode=code,boundedFailure=reason,primaryExceptionType=primary,ownedCleanupErrors=cleanup_errors,
                  ownedProcessReaped=proc is not None and code is not None,descendantCleanupClaimed=False,
                  readerFailures=reader_errors,readerIncomplete=incomplete,elapsedSeconds=round(time.monotonic()-start,3),**streams)
    save(run/(label+'.result.json'),record)
    require((allow_failure or code==0) and not reason and not primary and not cleanup_errors and not overflow.is_set() and not reader_failed.is_set() and not incomplete,
            'Bounded PC command failed: '+label)
    return record

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def posix(path):
    value=Path(path).absolute().as_posix()
    return '/'+value[0].lower()+value[2:] if len(value)>2 and value[1]==':' else value


def quoted(value):
    return "'"+str(value).replace("'", "'\"'\"'")+"'"


def output_map(folder):
    return {p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}


def workflow(args):
    manifest_path=(FIXTURES/'manifest.json').resolve(strict=True)
    manifest_bytes=manifest_path.read_bytes()
    manifest=json.loads(manifest_bytes)
    require(manifest['status']=='SOURCE_PREPARED_ROOT_EXECUTION_ONLY','Reviewed fixture/source selection required before workflow')
    clone=args.oneos_root.resolve(strict=True);clone.relative_to(ROOT/'firmware')
    java=(args.java_home.resolve(strict=True)/'bin'/('java.exe' if os.name=='nt' else 'java')).resolve(strict=True)
    shell=args.shell.resolve(strict=True);kotlin=args.kotlin_home.resolve(strict=True)
    usr=shell.parent if shell.parent.name=='bin' and shell.parent.parent.name=='usr' else shell.parent.parent/'usr/bin'
    core={n:(usr/(n+('.exe' if os.name=='nt' else ''))).resolve(strict=True) for n in ('sh','stat','readlink','mkdir','rm','rmdir','ln','mv','sha256sum','awk','cut','head','sort','grep','cat','tr')}
    jars=[kotlin/'lib'/n for n in ('kotlin-compiler.jar','annotations-13.0.jar','kotlin-stdlib.jar','kotlin-reflect.jar','kotlin-script-runtime.jar','trove4j.jar','kotlinx-coroutines-core-jvm.jar')]
    require(all(p.is_file() for p in [java,shell,*core.values(),*jars]),'Existing selected tools required')
    source_bytes={};pins={}
    for relative,pin in manifest['sources'].items():
        source=(ROOT/relative).resolve(strict=True);source.relative_to(ROOT)
        raw=source.read_bytes();require(digest(raw)==pin,'Source changed: '+relative);source_bytes[source]=raw;pins[source]={'sha256':pin,'bytes':len(raw),'kind':'source'}
    # The normal source manifest and runner are retained too; tools are streaming-pinned, not copied.
    for source in [Path(__file__).resolve(),FIXTURES/'manifest.json']:
        raw=manifest_bytes if source==manifest_path else source.read_bytes();source_bytes[source]=raw;pins[source]={'sha256':digest(raw),'bytes':len(raw),'kind':'source'}
    for tool in [java,shell,Path(sys.executable).resolve(strict=True),*core.values(),*jars]:pins[tool]={'sha256':sha(tool),'bytes':tool.stat().st_size,'kind':'existing-tool'}
    rootsh=clone/'app-android/app/src/full/assets/root/oneos_root.sh'
    leaf=ROOT/'compat/app-integration/retained-controller-install.sh'
    installer_function,leaf_span=exact_function(source_bytes[leaf],'do_install_closed_controller')
    embedded,embedded_span=exact_function(source_bytes[rootsh],'do_install_closed_controller')
    require(installer_function==embedded,'Actual standalone/embedded installer function differs')
    helpers=[];spans=[]
    for name in ('ge','sha','say','refuse','die','usage','mountinfo_ok','mounted_under','bridged','raw_attached','idle_or_refuse'):
        body,span=exact_function(source_bytes[rootsh],name);helpers.append(body);spans.append(span)
    copy_pins={};staged_pins={};compiled_pins={}
    def boundary():
        for path,pin in pins.items():require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'Input changed: '+str(path))
        for path,pin in {**copy_pins,**staged_pins}.items():require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'Retained/staged copy changed: '+str(path))
        for folder,expected in compiled_pins.items():require(output_map(folder)==expected,'Compiled outputs changed during use')
    boundary();contained(BASE).mkdir(exist_ok=True);run=contained(BASE/('r-'+uuid.uuid4().hex[:8]));run.mkdir()
    result={'schema':'retained-controller-install-source-models/v1','status':'FAILED','commands':{},'selectedCaseFilters':sorted(set(args.case)),'fullDefaultMatrix':not args.case,'fullRootScriptExecuted':False,'nativeAssetExecuted':False,'suOrRootExecuted':False,'realRootShellLifetimeTested':False,'appConfiguration':'authored Android APIs + model BuildConfig pins; actual Kotlin source bodies unchanged','sourceSpans':{'standalone':leaf_span,'embedded':embedded_span,'helpers':spans}}
    print(json.dumps({'run':run.relative_to(ROOT).as_posix(),'scope':'contained functions-only source models'}),flush=True)
    try:
        for folder in ('inputs','src','static-root-shell','program','tmp','runtime-home','empty-native','cases'):contained(run/folder).mkdir()
        snapshots={};staged={}
        for i,(path,snapshot_bytes) in enumerate(sorted(source_bytes.items(),key=lambda x:str(x[0]))):
            target=run/'inputs'/('%03d-'%i+path.name);target.write_bytes(snapshot_bytes);snapshots[str(path)]={'path':target.relative_to(ROOT).as_posix(),'sha256':digest(snapshot_bytes),'bytes':len(snapshot_bytes)};copy_pins[target]={'sha256':digest(snapshot_bytes),'bytes':len(snapshot_bytes)}
            if path.suffix=='.kt':
                target=run/'src'/('%03d-'%i+path.name);target.write_bytes(snapshot_bytes);staged[path]=target;staged_pins[target]={'sha256':digest(snapshot_bytes),'bytes':len(snapshot_bytes)}
        env={k:v for k,v in os.environ.items() if k.upper() not in STRIP}
        env.update(TMP=str(run/'tmp'),TEMP=str(run/'tmp'),TMPDIR=str(run/'tmp'),HOME=str(run/'runtime-home'),USERPROFILE=str(run/'runtime-home'),PATH=str(usr),MSYS_NO_PATHCONV='1',MSYS2_ARG_CONV_EXCL='*',MSYS='winsymlinks:sys')
        tools={'java':java,'shell':shell}
        jvm=['-Xmx512m','-Djava.io.tmpdir='+str(run/'tmp'),'-Duser.home='+str(run/'runtime-home'),'-Djava.library.path='+str(run/'empty-native')]
        compile_base=[java,*jvm,'-cp',os.pathsep.join(map(str,jars)),'org.jetbrains.kotlin.cli.jvm.K2JVMCompiler','-no-stdlib','-no-reflect','-jvm-target','1.8','-Xmulti-dollar-interpolation','-classpath',os.pathsep.join(map(str,[jars[2],jars[1]]))]
        models=[p for p in staged if p.is_relative_to(clone/'app-android/core/model/src/main/kotlin')]
        actual_root=[p for p in staged if p.name in ('RootScript.kt','RootShell.kt') and p.is_relative_to(clone)]
        require(len(models)==32 and len(actual_root)==2,'Actual core32 and RootScript/real RootShell sources')
        boundary()
        result['commands']['compile-real-root-shell']=command([*compile_base,'-d',run/'static-root-shell',*[staged[p] for p in models+actual_root]],run,env,'compile-real-root-shell',tools)
        runtime=[p for p in staged if p.name!='RootShell.kt' or p.is_relative_to(FIXTURES)]
        require(sum(p.name=='RootShell.kt' for p in runtime)==1,'Only authored public process API adapter at runtime')
        boundary()
        result['commands']['compile-model-world']=command([*compile_base,'-d',run/'program',*[staged[p] for p in runtime]],run,env,'compile-model-world',tools)
        before={'static':output_map(run/'static-root-shell'),'runtime':output_map(run/'program')}
        compiled_pins.update({run/'static-root-shell':before['static'],run/'program':before['runtime']})
        boundary()
        cp=os.pathsep.join(map(str,[run/'program',jars[2]]))
        result['commands']['root-script-validation']=command([java,*jvm,'-cp',cp,'model.ControllerContract','validate'],run,env,'root-script-validation',tools)
        validation=json.loads((run/'root-script-validation.stdout').read_text().strip());require(validation['pass'] is True,'Actual validator contract failed')
        native=bytes((i*7+3)%251 for i in range(128));native_hash=digest(native)
        records=[]
        selected=set(args.case)
        cases=[('shell',m) for m in SHELL_CASES]+[('app',m) for m in APP_CASES]
        for index,(kind,mode) in enumerate(cases):
            if selected and kind+':'+mode not in selected:continue
            boundary();case=contained(run/'cases'/('%02d-'%index+kind+'-'+mode));case.mkdir();stage=case/'stage';binpath=stage/'bin';binpath.mkdir(parents=True);legacy=case/'legacy';legacy.mkdir();(legacy/'unmodified').write_bytes(b'legacy never adopted')
            proc=case/'proc';(proc/'1').mkdir(parents=True);(proc/'self').mkdir();mount=b'1 0 8:1 / / rw - ext4 /dev/model rw\n'
            (proc/'1/mountinfo').write_bytes(mount);(proc/'self/mountinfo').write_bytes(mount);(case/'sys').mkdir();target=binpath/'oneos_retained_root_session'
            if mode in ('old_rootsh','already_installed'):(binpath/'oneos_root.sh').write_bytes(b'old installed script is not run or replaced')
            if mode in ('already_installed','replace_after_hash'):target.write_bytes(native)
            elif mode=='existing_different':target.write_bytes(b'preexisting foreign image remains')
            elif mode=='existing_directory':target.mkdir();(target/'borrowed').write_bytes(b'preserved')
            elif mode=='symlink_target':
                actual=case/'borrowed-native';actual.write_bytes(native)
                probe=case/'make-model-symlink.sh';probe.write_text(quoted(core['ln'])+' -s '+quoted(posix(actual))+' '+quoted(posix(target))+'\n[ -L '+quoted(posix(target))+' ]\n')
                result['commands']['symlink-fixture']=command([shell,'--noprofile','--norc',probe],run,env,'symlink-fixture',tools)
            if mode=='work_owned':(binpath/'.oneos-retained-controller-install').mkdir();(binpath/'.oneos-retained-controller-install/foreign').write_bytes(b'not this invocation')
            preexisting={};profiles={}
            for path in [case,*case.rglob('*')]:
                if path.is_file() or path.is_dir():
                    st=path.stat();identity=str(st.st_dev)+':'+str(st.st_ino);preexisting[identity]=str(path)
                    profiles[identity]={'uid':0,'mode':'755' if path.is_dir() or path==target else '600'}
            if mode in ('stage_writable','bin_writable'):
                changed=stage if mode=='stage_writable' else binpath;st=changed.stat();profiles[str(st.st_dev)+':'+str(st.st_ino)]['mode']='777'
            if mode=='stage_missing':binpath.rmdir();stage.rmdir()
            if mode=='bin_missing':binpath.rmdir()
            state={'root':str(case),'scenario':mode,'profiles':profiles,'preexisting':list(preexisting),'target':str(target),'renameTool':str(core['mv']),'renameToolSha256':pins[core['mv']]['sha256'],'events':[]};statepath=case/'state.json';statepath.write_text(json.dumps(state))
            replacements={'PYTHON':quoted(Path(sys.executable).resolve())+' -I -B','ADAPTER':quoted(ROOT/snapshots[str(FIXTURES/'fixture_metadata.py')]['path']),'CASE':quoted(case),'STATE':quoted(statepath),**{k.upper():quoted(v) for k,v in core.items()}}
            replacements['SHA256']=quoted(core['sha256sum'])
            prelude=source_bytes[FIXTURES/'shell_adapters.sh'].decode()
            for name,value in replacements.items():prelude=prelude.replace('@@'+name+'@@',value)
            require('@@' not in prelude,'All harness tool tokens replaced');preludepath=case/'prelude.sh';preludepath.write_text(prelude)
            globals=('set -fu\nSTAGE='+quoted(posix(stage))+'\nROOT_UID=0\nROOT_OWNER=0:0\nPROC='+quoted(posix(proc))+'\nSYSFS='+quoted(posix(case/'sys'))+'\nDATA='+quoted(posix(case/'data'))+'\nBRIDGE_HOSTS="user data"\n')
            fixture_script=prelude.encode()+b'\n'+globals.encode()+b'\n'.join(helpers)+b'\n'+installer_function+b'\n[ "$1" = install-closed-controller ] || exit 93\nshift\ndo_install_closed_controller "$@"\n'
            require(fixture_script.count(installer_function)==1 and all(fixture_script.count(helper)==1 for helper in helpers),'Exact captured installer and helper functions must be embedded once')
            script=case/'verified-functions.sh';script.write_bytes(fixture_script)
            if kind=='shell':
                generated=case/'actual-launcher.sh';label='generate-'+str(index)
                result['commands'][label]=command([java,*jvm,'-cp',cp,'model.ControllerContract','launcher',ROOT,posix(stage),posix(legacy),posix(proc),script,digest(fixture_script),'128',native_hash,generated],run,env,label,tools)
                wrapper=case/'run-launcher.sh';wrapper.write_text(prelude+'\n'+generated.read_text())
                payload=fixture_script+(native[:-1] if mode=='short' else native+b'x' if mode=='long' else bytes([native[0]^1])+native[1:] if mode=='corrupt' else native)
                if mode=='prefix_short':payload=fixture_script[:len(fixture_script)//2]
                if mode=='prefix_corrupt':payload=bytes([fixture_script[0]^1])+payload[1:]
                stream=case/'stream.bin';stream.write_bytes(payload);label='shell-'+mode
                terminal=command([shell,'--noprofile','--norc',wrapper],run,env,label,tools,stream,True);result['commands'][label]=terminal
                stdout=(run/(label+'.stdout')).read_text();success=mode in ('installed','old_rootsh','already_installed')
                require((terminal['exitCode']==0)==success and ('@@OK closed-controller-installed' in stdout)==success,'Actual installer outcome differs: '+mode)
                if success:require(target.read_bytes()==native,'Exact installed bytes')
            else:
                label='app-'+mode;props=['-Dmodel.script.sha='+digest(fixture_script),'-Dmodel.script.bytes='+str(len(fixture_script)),'-Dmodel.native.sha='+native_hash,'-Dmodel.native.bytes=128']
                result['commands'][label]=command([java,*jvm,*props,'-cp',cp,'model.AppSetupTest',ROOT,case,script,preludepath,shell,mode],run,env,label,tools)
                actual=json.loads((run/(label+'.stdout')).read_text().strip());require(actual['pass'] is True,'Actual setup model failed')
            actual_state=json.loads(statepath.read_text());require(not actual_state.get('forbiddenMutations'),'Source tried mutating preexisting stage/bin/target')
            leftovers=[p.relative_to(case).as_posix() for p in binpath.glob('.oneos-*')] if binpath.is_dir() else []
            if mode=='cleanup_failure':require(actual_state.get('injectedCleanupFailure') and leftovers,'Uncertain cleanup must remain observable before forced fixture teardown')
            elif mode=='work_owned':require((binpath/'.oneos-retained-controller-install/foreign').read_bytes()==b'not this invocation','Foreign work not removed')
            else:require(not leftovers,'Owned temporary installer/bootstrap paths remain: '+mode)
            if mode=='existing_different':require(target.read_bytes()==b'preexisting foreign image remains','Existing image replaced')
            if mode=='racing_target':require(actual_state.get('raceInjected') and target.read_bytes()==b'foreign racing target stays unchanged','Racing target replaced')
            if mode=='replace_after_hash':require(actual_state.get('replacementInjected') and target.read_bytes()==b'foreign replaced leaf stays unchanged','Posthash foreign replacement mutated')
            require((legacy/'unmodified').read_bytes()==b'legacy never adopted','Legacy path was mutated')
            if (binpath/'oneos_root.sh').exists():require((binpath/'oneos_root.sh').read_bytes()==b'old installed script is not run or replaced','Normal root script changed')
            records.append({'kind':kind,'mode':mode,'statePath':statepath.relative_to(ROOT).as_posix(),'stateSha256':sha(statepath),'leftoversBeforeHarnessCleanup':leftovers})
            print('MODEL_CASE '+kind+':'+mode,flush=True)
        boundary();require(before=={'static':output_map(run/'static-root-shell'),'runtime':output_map(run/'program')},'Compiler outputs changed during tests')
        result.update(status='PASS_SELECTED_INSTALLER_CASES_ONLY' if selected else 'PASS_CONTAINED_INSTALLER_AND_ACTUAL_APP_SOURCE_MODELS_ONLY',selectedCaseFilters=sorted(selected),fullDefaultMatrix=not selected,validation=validation,cases=records,inputSnapshots=snapshots,toolPins={str(p):v for p,v in pins.items() if v['kind']=='existing-tool'},compiledOutputMaps=before,stagedSourcePins={p.relative_to(ROOT).as_posix():v for p,v in staged_pins.items()},sourcePins={str(p):v for p,v in pins.items() if v['kind']=='source'})
    except BaseException as failure:
        result.update(failureType=type(failure).__name__,failureMessage=str(failure)[:2048]);raise
    finally:
        for terminal in run.glob('*.result.json'):
            label=terminal.name[:-len('.result.json')]
            if label not in result['commands']:result['commands'][label]=json.loads(terminal.read_bytes())
        save(run/'receipt.json',result);print(json.dumps({'status':result['status'],'receipt':(run/'receipt.json').relative_to(ROOT).as_posix(),'sha256':sha(run/'receipt.json')}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--kotlin-home', type=Path, required=True)
    parser.add_argument('--shell', type=Path, required=True)
    parser.add_argument('--oneos-root', type=Path, required=True)
    parser.add_argument('--case',action='append',default=[],choices=['shell:'+m for m in SHELL_CASES]+['app:'+m for m in APP_CASES],help='Run only selected public cases; receipt cannot claim the full default matrix')
    workflow(parser.parse_args())
