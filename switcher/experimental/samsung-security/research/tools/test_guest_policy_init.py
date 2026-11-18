"""Compile current first-party policy-init helpers and run authored JVM fixtures only."""
from pathlib import Path
import argparse,ast,hashlib,json,os,stat,struct,subprocess,threading,time,uuid

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'out/gpi-public-tests'
FIXTURES=ROOT/'compat/tests/guest_policy_init_model'
UTILITY=ROOT/'tools/build_retained_locksettings_local_owner.py'
UTILITY_SHA='9dbae6707abf4d0207aad57d1c2509b7ca26b2076d63f99a95b9d26dad480012'
STRIP={'CLASSPATH','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS'}
AUTHORITY='com/appleexploit/oneos/security/authority/'
PROGRAM=[ROOT/'compat/android'/AUTHORITY/(name+'.java') for name in
         ('PreparedGuestKeyguardGraphCapture','PreparedGuestPolicyInitCompletion')]
PROJECTIONS=[ROOT/'compat/compile-only/guest-policy-init'/name for name in
             ('com/android/server/policy/WindowManagerPolicy.java','android/view/WindowManagerPolicyConstants.java')]

def require(ok,message):
    if not ok:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def output(path):
    path=Path(path);path.relative_to(ROOT)
    for part in [path,*path.parents]:
        try:details=part.lstat()
        except FileNotFoundError:details=None
        if details is not None:
            require(not stat.S_ISLNK(details.st_mode),'Output symlink refused')
            if os.name=='nt':
                attributes=getattr(details,'st_file_attributes',None)
                require(type(attributes) is int and not attributes&0x400,'Output Windows reparse point or unavailable metadata refused')
        if part==ROOT:break
    path.resolve().relative_to(ROOT.resolve());return path
def save(path,value):
    with output(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2)+'\n')
def class_map(path):
    paths=[p for p in path.rglob('*') if p.is_file()]
    require(all(p.suffix=='.class' for p in paths),'Unexpected nonclass compiled output')
    return {p.relative_to(path).as_posix():sha(p) for p in paths}

def command(argv,run,env,label,tools):
    """Execute only the two supplied canonical JDK tools, with bounded owned cleanup."""
    argv=list(map(str,argv))
    require(Path(argv[0]) in set(tools.values()),'Canonical explicitly supplied JDK executable required')
    require(output(run)==run.resolve(),'Own canonical cwd required');run.relative_to(BASE)
    require(not any(key.upper() in STRIP for key in env),'Inherited JVM injection option')
    for key,folder in [('java.io.tmpdir','tmp'),('user.home','runtime-home'),('java.library.path','empty-native')]:
        flag='-D'+key+'='+str(run/folder)
        require(flag in argv or '-J'+flag in argv,'Owned JVM tmp/home/native path required')
    record={'argv':argv,'cwd':str(run),'timeoutSeconds':45,'combinedTextOutputLimitBytes':2*1024*1024,
            'ownedEnvironment':{key:env[key] for key in ('TMP','TEMP','TMPDIR','HOME','USERPROFILE')},
            'childPath':env.get('PATH'),'clearedInjectionNames':sorted(STRIP)}
    save(run/(label+'.command.json'),record)
    start=time.monotonic();outputs=[bytearray(),bytearray()];lock=threading.Lock()
    overflow=threading.Event();reader_failed=threading.Event();reader_errors=[]
    proc=None;threads=[];reason=None;primary=None;cleanup_errors=[];code=None
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
        proc=subprocess.Popen(argv,cwd=run,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
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
    incomplete=any(thread.is_alive() for thread in threads)
    if incomplete:reason=reason or 'reader-incomplete'
    if cleanup_errors:reason=reason or 'owned-cleanup-uncertain'
    with lock:frozen=[bytes(value) for value in outputs]
    streams={}
    for index,suffix in enumerate(('stdout','stderr')):
        path=output(run/(label+'.'+suffix))
        with path.open('xb') as stream:stream.write(frozen[index])
        streams[suffix]={'path':path.relative_to(ROOT).as_posix(),'bytes':len(frozen[index]),'sha256':digest(frozen[index])}
    record.update(exitCode=code,boundedFailure=reason,primaryExceptionType=primary,ownedCleanupErrors=cleanup_errors,
                  ownedProcessReaped=proc is not None and code is not None,descendantCleanupClaimed=False,
                  readerFailures=reader_errors,readerIncomplete=incomplete,elapsedSeconds=round(time.monotonic()-start,3),**streams)
    save(run/(label+'.result.json'),record)
    require(code==0 and not reason and not primary and not cleanup_errors and not overflow.is_set() and not reader_failed.is_set() and not incomplete,
            'Bounded PC command failed: '+label)
    return record

def links(data):
    """Bounded authored class ancestry/InnerClasses reader; does not load a class."""
    require(data[:4]==b'\xca\xfe\xba\xbe' and len(data)<=1048576,'Bounded class file required')
    u2=lambda at:struct.unpack_from('>H',data,at)[0]
    u4=lambda at:struct.unpack_from('>I',data,at)[0]
    pool={};cursor=10;index=1
    while index<u2(8):
        tag=data[cursor];cursor+=1
        if tag==1:size=u2(cursor);cursor+=2;pool[index]=data[cursor:cursor+size].decode('utf-8');cursor+=size
        elif tag in (7,8,16):pool[index]=u2(cursor);cursor+=2
        elif tag==12:pool[index]=(u2(cursor),u2(cursor+2));cursor+=4
        elif tag in (3,4,9,10,11,18):cursor+=4
        elif tag in (5,6):cursor+=8;index+=1
        elif tag==15:cursor+=3
        else:raise ValueError('Unsupported class pool tag')
        require(cursor<=len(data),'Class pool extent');index+=1
    name=lambda value:pool[pool[value]] if value else None
    own=name(u2(cursor+2));parent=name(u2(cursor+4));count=u2(cursor+6)
    interfaces=[name(u2(cursor+8+2*n)) for n in range(count)];cursor+=8+2*count
    for _ in range(2):
        count=u2(cursor);cursor+=2
        for _ in range(count):
            attrs=u2(cursor+6);cursor+=8
            for _ in range(attrs):cursor+=6+u4(cursor+2);require(cursor<=len(data),'Member attribute extent')
    count=u2(cursor);cursor+=2;inner=[];enclosing=None
    for _ in range(count):
        label=pool[u2(cursor)];size=u4(cursor+2);start=cursor+6;end=start+size;require(end<=len(data),'Class attribute extent')
        if label=='InnerClasses':
            n=u2(start);require(size==2+8*n,'InnerClasses extent')
            for k in range(n):
                at=start+2+8*k
                if name(u2(at))==own:inner.append({'outer':name(u2(at+2)),'innerName':pool[u2(at+4)] if u2(at+4) else None,'flags':u2(at+6)})
        elif label=='EnclosingMethod':
            require(size==4 and enclosing is None,'EnclosingMethod shape');pair=pool[u2(start+2)] if u2(start+2) else None
            enclosing={'owner':name(u2(start)),'name':pool[pair[0]] if pair else None,'descriptor':pool[pair[1]] if pair else None}
        cursor=end
    require(cursor==len(data),'Trailing class bytes')
    return {'name':own,'superclass':parent,'interfaces':interfaces,'innerSelf':inner,'enclosingMethod':enclosing}

def build(java_home,android_jar):
    java_home=java_home.resolve(strict=True);android_jar=android_jar.resolve(strict=True)
    suffix='.exe' if os.name=='nt' else ''
    tools={name:(java_home/'bin'/(name+suffix)).resolve(strict=True) for name in ('javac','java')}
    require(all(path.is_file() for path in tools.values()) and android_jar.is_file(),'Existing JDK tools and android.jar required')
    manifest=FIXTURES/'manifest.json';manifest_bytes=manifest.read_bytes();fixture=json.loads(manifest_bytes)
    require(fixture['schema']=='guest-policy-init-public-authored-fixtures/v1' and len(fixture['sources'])==26,'Exact authored fixture manifest required')
    self_bytes=Path(__file__).read_bytes();utility_bytes=UTILITY.read_bytes()
    require(digest(utility_bytes)==UTILITY_SHA,'Reviewed committed bounded-command utility changed')
    tree=ast.parse(utility_bytes)
    readers=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='class_shape']
    require(len(readers)==1,'Exactly one reviewed pure class reader required')
    reader_bytes=(ast.get_source_segment(utility_bytes.decode('utf-8'),readers[0])+'\n').encode('utf-8')
    source_bytes={Path(__file__):self_bytes,UTILITY:utility_bytes,manifest:manifest_bytes}
    for path in [*PROGRAM,*PROJECTIONS]:source_bytes[path]=path.read_bytes()
    sources={role:[] for role in ('F','C','V','driver')};destinations=set()
    for item in fixture['sources']:
        require(item['role'] in sources and item['relative'].endswith('.java'),'Exact authored source role')
        path=(FIXTURES/item['path']).resolve(strict=True);path.relative_to(FIXTURES.resolve())
        data=path.read_bytes();require(len(data)==item['bytes'] and digest(data)==item['sha256'],'Promoted fixture bytes changed: '+item['path'])
        target=(item['role'],item['relative']);require(target not in destinations,'Duplicate source destination');destinations.add(target)
        source_bytes[path]=data;sources[item['role']].append((item,data))
    actual_fixture_files={path.resolve() for path in FIXTURES.rglob('*.java')}
    require(actual_fixture_files=={path for path in source_bytes if path in actual_fixture_files},'Unexpected fixture Java source closure')
    inputs={str(path):{'sha256':digest(data),'bytes':len(data),'kind':'source'} for path,data in source_bytes.items()}
    for path in [*tools.values(),android_jar]:inputs[str(path)]={'sha256':sha(path),'bytes':path.stat().st_size,'kind':'tool-or-sdk'}
    def admit():
        for path,item in inputs.items():require(sha(path)==item['sha256'],'Input changed: '+path)
    admit();output(BASE);BASE.mkdir(parents=True,exist_ok=True)
    run=output(BASE/('r-'+uuid.uuid4().hex[:8]));run.mkdir(exist_ok=False)
    print(json.dumps({'run':run.relative_to(ROOT).as_posix(),'scope':'authored JVM fixtures only'}),flush=True)
    result={'schema':'guest-policy-init-public-jvm-test/v1','status':'FAILED','run':run.relative_to(ROOT).as_posix(),
            'inputsBeforeAfter':inputs,'commands':{},'androidJar':str(android_jar),'javaHome':str(java_home),
            'd8Invoked':False,'androidOemNativePhoneExecuted':False,'classfilePatched':False,
            'androidRuntimeOrApiLevelAcceptance':False,'descendantCleanupClaimed':False}
    try:
        for folder in ('inputs','src','abi','program','runtime-program','F','C','V','driver','tmp','runtime-home','empty-native','empty-classpath'):(run/folder).mkdir()
        snapshots={}
        for index,(path,data) in enumerate(sorted(source_bytes.items(),key=lambda entry:str(entry[0]))):
            target=run/'inputs'/('%02d-'%index+path.name);target.write_bytes(data)
            snapshots[str(path)]={'path':target.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':digest(data)}
        # Execute only the unchanged pure reader selected from retained normal
        # source bytes. No old builder globals, commands or ignored paths run.
        reader_snapshot=run/'inputs'/'executed-class-reader.py';reader_snapshot.write_bytes(reader_bytes)
        reader={'__name__':'_retained_public_policy_init_reader','__file__':str(reader_snapshot),'struct':struct,'require':require}
        exec(compile(reader_bytes,str(reader_snapshot),'exec'),reader);shape=reader['class_shape']
        result['executedClassReader']={'path':reader_snapshot.relative_to(ROOT).as_posix(),'sha256':digest(reader_bytes),'sourceSha256':UTILITY_SHA}
        env={key:value for key,value in os.environ.items() if key.upper() not in STRIP}
        env.update(TMP=str(run/'tmp'),TEMP=str(run/'tmp'),TMPDIR=str(run/'tmp'),HOME=str(run/'runtime-home'),USERPROFILE=str(run/'runtime-home'))
        staged={};fixture_paths={role:[] for role in sources}
        def stage(role,relative,data):
            target=output(run/'src'/role/relative);target.resolve().relative_to((run/'src'/role).resolve())
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            staged[target.relative_to(ROOT).as_posix()]={'bytes':len(data),'sha256':digest(data)};return target
        abi_paths=[stage('abi',path.relative_to(ROOT/'compat/compile-only/guest-policy-init'),source_bytes[path]) for path in PROJECTIONS]
        program_paths=[stage('program',path.name,source_bytes[path]) for path in PROGRAM]
        for role,items in sources.items():
            for item,data in items:fixture_paths[role].append(stage(role,item['relative'],data))
        def boundary():
            admit()
            require(sha(reader_snapshot)==digest(reader_bytes),'Retained executed class reader changed')
            require({path.relative_to(ROOT).as_posix() for path in (run/'src').rglob('*') if path.is_file()}==set(staged),'Staged source closure changed')
            for path,item in staged.items():require(sha(ROOT/path)==item['sha256'],'Staged source changed')
            for item in snapshots.values():require(sha(ROOT/item['path'])==item['sha256'],'Retained code/source snapshot changed')
        def invoke(label,args):
            boundary()
            try:result['commands'][label]=command(args,run,env,label,tools)
            except BaseException:
                record=run/(label+'.result.json')
                if record.is_file():result['commands'][label]=json.loads(record.read_bytes())
                raise
        jvm=['-Xmx512m','-Djava.io.tmpdir='+str(run/'tmp'),'-Duser.home='+str(run/'runtime-home'),'-Djava.library.path='+str(run/'empty-native')]
        javac=[tools['javac'],*['-J'+value for value in jvm],'-proc:none','-implicit:none','-encoding','UTF-8','-source','8','-target','8','-sourcepath','']
        invoke('compile-abi',[*javac,'-bootclasspath',android_jar,'-classpath',run/'empty-classpath','-d',run/'abi',*abi_paths])
        abi=class_map(run/'abi');policy='com/android/server/policy/WindowManagerPolicy'
        expected_abi={policy+'.class',policy+'$WindowManagerFuncs.class','android/view/WindowManagerPolicyConstants.class'}
        require(set(abi)==expected_abi,'Exact compiler-only three-interface closure required')
        abi_meta={name:shape((run/'abi'/name).read_bytes()) for name in abi}
        init_descriptor='(Landroid/content/Context;L'+policy+'$WindowManagerFuncs;)V'
        for name,metadata in abi_meta.items():
            require(metadata['flags']==1537 and not metadata['fields'],'Declaration-only interface required')
            methods=[(method['name'],method['descriptor'],method['flags']) for method in metadata['methods']]
            require(methods==([('init',init_descriptor,1025)] if name==policy+'.class' else []),'Exact abstract projection method required')
            ancestry=links((run/'abi'/name).read_bytes())
            require(ancestry['superclass']=='java/lang/Object' and ancestry['interfaces']==(['android/view/WindowManagerPolicyConstants'] if name==policy+'.class' else []),'Compiler-only interface hierarchy differs')
        invoke('compile-program',[*javac,'-bootclasspath',android_jar,'-classpath',run/'abi','-d',run/'program',*program_paths])
        program=class_map(run/'program');require(set(program)=={name+'.class' for name in fixture['expectedProgramDefinitions']},'Exact first-party five-class program closure required')
        program_meta={name:shape((run/'program'/name).read_bytes()) for name in program}
        completion=program_meta[AUTHORITY+'PreparedGuestPolicyInitCompletion.class']
        wrapper=[method for method in completion['methods'] if method['name']=='invokeOriginal']
        require(len(wrapper)==1 and wrapper[0]['flags']==9 and wrapper[0]['descriptor']=='(L'+policy+';Landroid/content/Context;L'+policy+'$WindowManagerFuncs;)V','Exact public static typed wrapper required')
        graph=program_meta[AUTHORITY+'PreparedGuestKeyguardGraphCapture.class']
        bridge=[method for method in graph['methods'] if method['name']=='checkPolicyInitOwners']
        require(len(bridge)==1 and bridge[0]['flags']==0 and bridge[0]['descriptor']=='(Ljava/lang/Object;Ljava/lang/Object;Ljava/lang/Object;)V','Actual package-private compare bridge required')
        for name in program:
            target=run/'runtime-program'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((run/'program'/name).read_bytes())
        cp={'F':run/'empty-classpath','C':run/'F','V':str(run/'F')+os.pathsep+str(run/'C'),'driver':run/'empty-classpath'}
        for role in ('F','C','V','driver'):
            require(class_map(run/'program')==program and class_map(run/'runtime-program')==program,'Program changed before fixture compile')
            invoke('compile-'+role,[*javac,'-classpath',cp[role],'-d',run/role,*fixture_paths[role]])
            require(set(class_map(run/role))=={name+'.class' for name in fixture['expectedCompiledModelNames'][role]},'Compiled '+role+' fixture closure differs')
        actual={role:class_map(run/role) for role in sources}
        metadata={role:{name:shape((run/role/name).read_bytes()) for name in names} for role,names in actual.items()}
        require(all(value['name']==name[:-6] for values in metadata.values() for name,value in values.items()),'Class internal name differs')
        field_checks=[]
        for item in fixture['declaringFields']:
            name=item['declaringClass'][1:-1]+'.class';owners=[values[name] for values in metadata.values() if name in values]
            require(len(owners)==1,'One authored declaring class required');fields=[field for field in owners[0]['fields'] if field['name']==item['name']]
            require(len(fields)==1 and fields[0]['descriptor']==item['descriptor'] and fields[0]['flags']==item['accessFlags'],'Authored declaring-field metadata differs')
            field_checks.append({'class':name,'field':fields[0]})
        parents=[]
        for item in fixture['expectedParents']:
            ancestry=links((run/'C'/(item['class']+'.class')).read_bytes());require(ancestry==item['links'],'Natural parent/InnerClasses/EnclosingMethod differs; no shaping fallback')
            parents.append({'class':item['class'],'links':ancestry})
        require(links((run/'C'/(policy+'.class')).read_bytes())['interfaces']==['android/view/WindowManagerPolicyConstants'],'Runtime authored interface hierarchy differs')
        boundary();require(class_map(run/'program')==program and class_map(run/'runtime-program')==program,'Program drift before JVM')
        require({role:class_map(run/role) for role in sources}==actual and class_map(run/'abi')==abi,'Fixture or ABI drift before JVM')
        invoke('models',[tools['java'],*jvm,'-Xint','-cp',run/'driver',fixture['runtimeMain'],run/'runtime-program',run/'F',run/'C',run/'V'])
        lines=(run/'models.stdout').read_text(encoding='utf-8').splitlines();require(len(lines)==1,'One exact JSON result line required');tests=json.loads(lines[0])
        require(set(tests)=={'pass','modeledOnly','cases','checks','sameCoreLoader','distinctVendorLoader'} and all(tests[name] is True for name in ('pass','modeledOnly','sameCoreLoader','distinctVendorLoader')),'Authored model success required')
        require(type(tests['cases']) is int and tests['cases']==fixture['expectedCases']==14 and type(tests['checks']) is int and tests['checks']==fixture['expectedChecks']==122,'Exact selected authored case/check count differs')
        boundary();require(class_map(run/'program')==program and class_map(run/'runtime-program')==program and class_map(run/'abi')==abi,'Program or ABI drift after JVM')
        require({role:class_map(run/role) for role in sources}==actual,'Compiled fixture drift after JVM')
        # Interface declarations can yield identical class bytes. Runtime provenance
        # is separately compiled model directories and URLs, not hash inequality.
        result.update(status='PASS_AUTHORED_POLICY_INIT_PUBLIC_JVM_TESTS_ONLY',tests=tests,programClassPinsBeforeAfter=program,
                      modelClassPinsBeforeAfter=actual,compilerOnlyInterfacePins=abi,programClassMetadata=program_meta,
                      modelClassMetadata=metadata,declaringFieldChecks=field_checks,naturalParents=parents,
                      stagedSources=staged,snapshots=snapshots,projectionRuntimeDirectoryUsed=False,
                      compilerOnlyInterfaceBytesMayEqualAuthoredRuntimeDeclarations=True)
    except BaseException as failure:
        result.update(failureType=type(failure).__name__,failureMessage=str(failure)[:2048]);raise
    finally:
        save(run/'receipt.json',result)
        print(json.dumps({'status':result['status'],'receipt':(run/'receipt.json').relative_to(ROOT).as_posix(),'receiptSha256':sha(run/'receipt.json')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home',required=True,type=Path,help='Existing JDK home containing java and javac (JDK 9 or newer)')
    parser.add_argument('--android-jar',required=True,type=Path,help='Existing Android SDK android.jar, used for compilation only')
    args=parser.parse_args();build(args.java_home,args.android_jar)
