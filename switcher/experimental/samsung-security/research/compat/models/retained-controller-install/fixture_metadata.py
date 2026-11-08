"""Synthetic UID/mode and adversarial actions for a contained MSYS shell world.
Real stat identity, hashes, FD dereferences and no-clobber link run in MSYS tools.
No root ownership or permission claim follows from this profile adapter.
"""
from pathlib import Path
import hashlib,json,os,re,sys,subprocess


def require(ok,message):
    if not ok:raise ValueError(message)


def path_value(raw,root):
    if re.match(r'^/[a-zA-Z]/',raw):raw=raw[1].upper()+':'+raw[2:]
    path=Path(raw).absolute()
    require(path.is_relative_to(root),'Outside private case path')
    resolved=path.resolve(strict=False)
    require(resolved.is_relative_to(root),'Outside private case resolved path')
    return path,resolved


def main():
    root=Path(sys.argv[1]).resolve(strict=True);state_path=Path(sys.argv[2]).resolve(strict=True)
    require(state_path.is_relative_to(root),'State must be case-owned')
    state=json.loads(state_path.read_text());require(root==Path(state['root']),'Exact configured root')
    command=sys.argv[3];raw=sys.argv[4];path,resolved=path_value(raw,root)
    present=resolved.exists();key=None
    if present:
        st=resolved.stat();key=str(st.st_dev)+':'+str(st.st_ino)
    event={'command':command,'path':str(path),'resolved':str(resolved)}
    state.setdefault('events',[]).append(event)
    state_path.write_text(json.dumps(state,indent=2)+'\n') # Persist reached boundary BEFORE any fallible action.
    profile=state.setdefault('profiles',{})
    if command=='stat':
        fmt=sys.argv[5];require(fmt in ('%u','%a'),'Synthetic fields only')
        require(present,'Existing object required')
        value=profile.get(key,{'uid':0,'mode':'700' if resolved.is_dir() else '600'})
        print(value['uid'] if fmt=='%u' else value['mode'])
    elif command in ('chown','chmod'):
        require(present,'Existing owned newly-created object required')
        if key in state['preexisting']:
            state.setdefault('forbiddenMutations',[]).append(event)
            state_path.write_text(json.dumps(state));return 19
        if state['scenario']=='chmod_failure' and command=='chmod' and path.name=='payload' and sys.argv[5]=='0755':
            state['injectedChmodFailure']=True;state_path.write_text(json.dumps(state));return 1
        value=profile.setdefault(key,{'uid':0,'mode':'700' if resolved.is_dir() else '600'})
        if command=='chown':require(sys.argv[5]=='0:0','Exact synthetic owner');value['uid']=0
        else:
            require(sys.argv[5] in ('0700','0755','0600','0555'),'Known newly-created object mode')
            value['mode']=sys.argv[5].lstrip('0')
    elif command in ('rm','rmdir'):
        if key in state['preexisting']:
            state.setdefault('forbiddenMutations',[]).append(event);state_path.write_text(json.dumps(state));return 19
        if state['scenario']=='cleanup_failure' and command=='rm' and path.name=='payload':
            state['injectedCleanupFailure']=True;state_path.write_text(json.dumps(state));return 1
    elif command=='link_target':
        if state['scenario']=='racing_target' and not state.get('raceInjected'):
            require(not present,'Race requires absent target')
            path.write_bytes(b'foreign racing target stays unchanged')
            st=path.stat();identity=str(st.st_dev)+':'+str(st.st_ino)
            profile[identity]={'uid':0,'mode':'755'};state['preexisting'].append(identity);state['raceInjected']=True
    elif command=='after_target_hash':
        if state['scenario']=='replace_after_hash' and not state.get('replacementInjected'):
            target=Path(state['target']);require(target.is_relative_to(root),'Own target')
            replacement=target.with_name('fixture-replacement');replacement.write_bytes(b'foreign replaced leaf stays unchanged')
            state['replacementAttempted']=True;state_path.write_text(json.dumps(state,indent=2)+'\n')
            before=target.stat();incoming=replacement.stat()
            original_identity=(before.st_dev,before.st_ino);replacement_identity=(incoming.st_dev,incoming.st_ino)
            tool=Path(state['renameTool']).resolve(strict=True)
            require(tool.is_file() and tool.name.lower() in ('mv','mv.exe'),'Existing selected MSYS mv required')
            with tool.open('rb') as stream:require(hashlib.file_digest(stream,'sha256').hexdigest()==state['renameToolSha256'],'Selected rename tool changed')
            state['replacementOriginalIdentity']=list(original_identity);state['replacementIncomingIdentity']=list(replacement_identity)
            state_path.write_text(json.dumps(state,indent=2)+'\n')
            # Existing MSYS process, no shell interpolation or broader script; both paths are case-owned.
            completed=subprocess.run([str(tool),'-T','--',str(replacement),str(target)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
            state['renameResult']={'exitCode':completed.returncode,'reaped':True,'stdoutSha256':hashlib.sha256(completed.stdout).hexdigest(),'stderrSha256':hashlib.sha256(completed.stderr).hexdigest(),'stderrBytes':len(completed.stderr)}
            state_path.write_text(json.dumps(state,indent=2)+'\n')
            require(completed.returncode==0,'MSYS rename did not succeed')
            st=target.stat();observed=(st.st_dev,st.st_ino)
            require(observed==replacement_identity and observed!=original_identity,'Real incoming inode must replace the named target')
            require(not replacement.exists() and target.read_bytes()==b'foreign replaced leaf stays unchanged','Exact foreign bytes/consumed incoming name required')
            state['replacementAfterIdentity']=list(observed);state['replacementInjected']=True
            profile[str(st.st_dev)+':'+str(st.st_ino)]={'uid':0,'mode':'755'}
    elif command=='guard':pass
    else:raise ValueError('Unsupported fixture command')
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    return 0

def record_fault(failure):
    # The source function hides command stderr. Persist only bounded local error facts.
    try:
        state_path=Path(sys.argv[2]).resolve(strict=True);root=Path(sys.argv[1]).resolve(strict=True)
        require(state_path.is_relative_to(root),'Own fault record only')
        require(state_path.stat().st_size<=512*1024,'Bounded fixture state')
        state=json.loads(state_path.read_text());require(root==Path(state['root']),'Configured root differs')
        faults=state.setdefault('adapterFaults',[])
        if len(faults)<8:faults.append({'command':sys.argv[3][:64],'type':type(failure).__name__,'errno':getattr(failure,'errno',None),'winerror':getattr(failure,'winerror',None)})
        state_path.write_text(json.dumps(state,indent=2)+'\n')
    except BaseException:
        pass # Failure must remain failure even if the diagnostic record cannot be written.

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as failure:
        record_fault(failure)
        raise
