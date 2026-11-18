"""Source-compile the experimental cell and run authored JDK scheduling models.

Requires Python 3.9+ and an existing JDK 17+. No Android SDK, firmware, saved
classfiles, receipts, network, Gradle integration or project-tool imports.
All output must be explicitly placed outside the upstream checkout.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import time
import uuid

PROJECT=Path(__file__).resolve().parents[1]
UPSTREAM=PROJECT.parents[2]
STRIP={'CLASSPATH','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS'}
PKG='com/appleexploit/oneos/security/transport/'
CELL=PROJECT/'src'/PKG/'PinCheckCompletion.java'
ABI=[PROJECT/'compile-only'/name for name in (
    'android/os/Parcel.java','android/os/Parcelable.java',
    'com/android/internal/widget/VerifyCredentialResponse.java')]
FRAMEWORK=[PROJECT/'tests/framework'/name for name in (
    'android/os/Parcel.java','android/os/Parcelable.java',
    'com/android/internal/widget/VerifyCredentialResponse.java',PKG+'CompletionModelDispatcher.java')]
DRIVER=PROJECT/'tests/driver/model/CompletionModelTest.java'


def require(value,message):
    if not value:raise ValueError(message)


def digest(data):return hashlib.sha256(data).hexdigest()


def sha(path):
    hasher=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
    return hasher.hexdigest()


def no_links(path):
    for current in (path,*path.parents):
        try:details=current.lstat()
        except FileNotFoundError:continue
        require(not stat.S_ISLNK(details.st_mode),'Output symlink refused')
        if os.name=='nt':
            attributes=getattr(details,'st_file_attributes',None)
            require(type(attributes) is int and not attributes&0x400,'Output reparse point or missing metadata refused')


def output(path,base):
    path=Path(path);require(path.is_absolute(),'Absolute output path required')
    path.relative_to(base)
    require(not path.resolve().is_relative_to(UPSTREAM),'Output inside upstream checkout refused')
    no_links(path);require(path.resolve().is_relative_to(base.resolve()),'Output escaped selected directory')
    return path


def save(path,value,base):
    with output(path,base).open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,indent=2)+'\n')


def class_map(directory):
    files=[p for p in directory.rglob('*') if p.is_file()]
    require(all(p.suffix=='.class' for p in files),'Unexpected compiler output')
    return {p.relative_to(directory).as_posix():sha(p) for p in files}


def command(argv,work,env,label,tools,base):
    """Bounded local JDK command; cleanup owns only the retained process handle."""
    argv=list(map(str,argv));require(Path(argv[0]) in tools.values(),'Only supplied canonical JDK tools allowed')
    require(not any(k.upper() in STRIP for k in env),'JVM injection environment refused')
    output(work,base)
    record={'argv':argv,'cwd':str(work),'timeoutSeconds':45,'combinedOutputLimitBytes':2*1024*1024,
            'clearedInjectionNames':sorted(STRIP),
            'ownedEnvironment':{k:env[k] for k in ('TMP','TEMP','TMPDIR','HOME','USERPROFILE')}}
    save(work/(label+'.command.json'),record,base)
    start=time.monotonic();buffers=[bytearray(),bytearray()];lock=threading.Lock()
    overflow=threading.Event();reader_failed=threading.Event();reader_errors=[]
    process=None;threads=[];primary=None;reason=None;cleanup=[];code=None
    def reader_error(failure):
        with lock:reader_errors.append(type(failure).__name__)
        reader_failed.set()
    def drain(pipe,index):
        try:
            while True:
                block=pipe.read(4096)
                if not block:break
                with lock:
                    if sum(map(len,buffers))+len(block)>2*1024*1024:overflow.set();break
                    buffers[index].extend(block)
        except BaseException as failure:reader_error(failure)
        finally:
            try:pipe.close()
            except BaseException as failure:reader_error(failure)
    try:
        process=subprocess.Popen(argv,cwd=work,env=env,stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        threads=[threading.Thread(target=drain,args=(pipe,index),daemon=True)
                 for index,pipe in enumerate((process.stdout,process.stderr))]
        for thread in threads:thread.start()
        while process.poll() is None:
            if overflow.is_set() or reader_failed.is_set() or time.monotonic()-start>45:
                reason='output-limit' if overflow.is_set() else 'reader-error' if reader_failed.is_set() else 'timeout';break
            time.sleep(0.02)
    except BaseException as failure:primary=type(failure).__name__;reason=reason or 'spawn-or-post-spawn-exception'
    finally:
        if process is not None:
            try:
                if process.poll() is None:process.kill()
            except BaseException as failure:cleanup.append('terminate:'+type(failure).__name__)
            try:code=process.wait(timeout=5)
            except BaseException as failure:cleanup.append('wait:'+type(failure).__name__)
            for thread in threads:
                try:
                    if thread.ident is not None:thread.join(2)
                except BaseException as failure:cleanup.append('reader-join:'+type(failure).__name__)
            for index,pipe in enumerate((process.stdout,process.stderr)):
                if index>=len(threads) or threads[index].ident is None:
                    try:pipe.close()
                    except BaseException as failure:cleanup.append('unstarted-pipe:'+type(failure).__name__)
    incomplete=any(t.is_alive() for t in threads)
    if incomplete:reason=reason or 'reader-incomplete'
    if cleanup:reason=reason or 'owned-cleanup-uncertain'
    with lock:frozen=[bytes(value) for value in buffers]
    logs={}
    for suffix,data in zip(('stdout','stderr'),frozen):
        path=output(work/(label+'.'+suffix),base)
        with path.open('xb') as stream:stream.write(data)
        logs[suffix]={'path':str(path),'bytes':len(data),'sha256':digest(data)}
    record.update(exitCode=code,boundedFailure=reason,primaryExceptionType=primary,
        ownedProcessReaped=process is not None and code is not None,ownedCleanupErrors=cleanup,
        readerFailures=reader_errors,readerIncomplete=incomplete,descendantCleanupClaimed=False,
        elapsedSeconds=round(time.monotonic()-start,3),**logs)
    save(work/(label+'.result.json'),record,base)
    require(code==0 and not reason and not primary and not cleanup and not overflow.is_set()
            and not reader_failed.is_set() and not incomplete,'Bounded JDK command failed: '+label)
    return record


def run(java_home,out):
    java_home=java_home.resolve(strict=True);suffix='.exe' if os.name=='nt' else ''
    tools={name:(java_home/'bin'/(name+suffix)).resolve(strict=True) for name in ('java','javac')}
    require(all(p.is_file() and p.parent==java_home/'bin' for p in tools.values()),'Existing canonical JDK tools required')
    require(out.is_absolute(),'--out must be an absolute directory outside checkout')
    out=Path(os.path.abspath(out));output(out,out)
    source_paths=[Path(__file__).resolve(),CELL,*ABI,*FRAMEWORK,DRIVER]
    expected={p.resolve(strict=True) for p in [CELL,*ABI,*FRAMEWORK,DRIVER]}
    actual={p.resolve(strict=True) for folder in ('src','compile-only','tests') for p in (PROJECT/folder).rglob('*.java')}
    require(expected==actual,'Exact one cell, three projection and five fixture sources required')
    captured={};inputs={}
    for path in source_paths:
        path=path.resolve(strict=True);path.relative_to(PROJECT)
        data=path.read_bytes();require(len(data)<=1024*1024,'Bounded source required')
        captured[path]=data;inputs[str(path)]={'bytes':len(data),'sha256':digest(data)}
    for path in tools.values():inputs[str(path)]={'bytes':path.stat().st_size,'sha256':sha(path)}
    def originals():
        for path,value in inputs.items():
            p=Path(path);require(p.stat().st_size==value['bytes'] and sha(p)==value['sha256'],'Original input changed: '+path)
    originals();out.mkdir(parents=True,exist_ok=True)
    work=output(out/('r-'+uuid.uuid4().hex[:8]),out);work.mkdir()
    result={'schema':'experimental-pin-check-completion-jdk/v1','status':'FAILED','commands':{},
            'scope':'Authored scheduling models only; no Android SDK/DEX/OEM/JNI/device/authority acceptance',
            'inputs':inputs,'productionCompiledFromCurrentSource':True,'projectionRuntime':False}
    print(json.dumps({'output':str(work),'androidSdkRequired':False}),flush=True)
    try:
        for name in ('inputs','src','abi','program','framework','driver','tmp','home','empty-native','empty-classpath'):
            output(work/name,out).mkdir()
        snapshots={};staged={}
        for index,(path,data) in enumerate(captured.items()):
            target=work/'inputs'/('%02d-'%index+path.name);target.write_bytes(data)
            snapshots[str(path)]={'path':str(target),'sha256':digest(data)}
            if path.suffix=='.java':
                target=work/'src'/path.relative_to(PROJECT);target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data);staged[path]=target
        env={k:v for k,v in os.environ.items() if k.upper() not in STRIP}
        env.update(TMP=str(work/'tmp'),TEMP=str(work/'tmp'),TMPDIR=str(work/'tmp'),HOME=str(work/'home'),USERPROFILE=str(work/'home'))
        vm=['-Xmx256m','-Djava.io.tmpdir='+str(work/'tmp'),'-Duser.home='+str(work/'home'),'-Djava.library.path='+str(work/'empty-native')]
        javac=[tools['javac'],*['-J'+v for v in vm],'-proc:none','-implicit:none','-encoding','UTF-8','-source','8','-target','8','-sourcepath','']
        def boundary():
            originals()
            for path,target in staged.items():require(sha(target)==inputs[str(path)]['sha256'],'Staged source changed')
            for value in snapshots.values():require(sha(Path(value['path']))==value['sha256'],'Retained source changed')
        groups=[('abi',ABI,work/'empty-classpath'),('program',[CELL],work/'abi'),
                ('framework',FRAMEWORK,work/'program'),('driver',[DRIVER],work/'empty-classpath')]
        admitted={}
        for name,paths,classpath in groups:
            boundary()
            for old,values in admitted.items():require(class_map(work/old)==values,'Prior compiler output changed')
            result['commands']['compile-'+name]=command([*javac,'-classpath',classpath,'-d',work/name,
                *[staged[p.resolve(strict=True)] for p in paths]],work,env,'compile-'+name,tools,out)
            admitted[name]=class_map(work/name);require(admitted[name],'Missing class output')
        require(set(admitted['abi'])=={'android/os/Parcel.class','android/os/Parcelable.class',
            'com/android/internal/widget/VerifyCredentialResponse.class'},'Exact compile-only output required')
        require(set(admitted['program'])=={PKG+n+'.class' for n in ('PinCheckCompletion','PinCheckCompletion$FinalKind','PinCheckCompletion$Retirement')},'Exact source cell closure required')
        require(not set(admitted['framework'])&set(admitted['program']),'Fixture must not replace cell definitions')
        boundary()
        result['commands']['models']=command([tools['java'],*vm,'-Xint','-cp',work/'driver','model.CompletionModelTest',
            work/'program',work/'framework'],work,env,'models',tools,out)
        lines=(work/'models.stdout').read_text(encoding='utf-8').splitlines()
        require(len(lines)==17 and lines[:-1]==['MODEL_CASE '+str(n) for n in range(16)],'Exact authored case sequence required')
        tests=json.loads(lines[-1]);require(tests=={'pass':True,'modeledOnly':True,'cases':16,'checks':132,
            'privateCellStateInspected':False,'runnableInvocations':0},'Authored scheduling result differs')
        boundary();require({name:class_map(work/name) for name in admitted}==admitted,'Class bytes changed after models')
        result.update(status='PASS_AUTHORED_SCHEDULING_MODELS_ONLY',tests=tests,classMapsBeforeAfter=admitted,
            snapshots=snapshots,stagedSourcePins={str(p):sha(p) for p in staged.values()},
            noProjectCodeImportsOrIgnoredPrerequisites=True,noAppOrGradleIntegration=True)
    except BaseException as failure:
        result.update(failureType=type(failure).__name__,failureMessage=str(failure)[:2048]);raise
    finally:
        save(work/'receipt.json',result,out)
        print(json.dumps({'status':result['status'],'receipt':str(work/'receipt.json'),'sha256':sha(work/'receipt.json')}),flush=True)


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--java-home',type=Path,required=True)
    cli.add_argument('--out',type=Path,required=True)
    args=cli.parse_args();run(args.java_home,args.out)
