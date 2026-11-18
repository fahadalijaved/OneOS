"""Cold-only UNSELECTED OPPO retrieval capability leaf, never an auth result."""
import hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path
from itertools import zip_longest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
OUT=ROOT/'out/retrieval-capability-leaf';RAW=ROOT/'firmware/retrieval-capability-leaf'
SOURCE=PARENT/'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk'
SOURCE_SHA='33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
OWNER='Lcom/oplus/settings/utils/SysFeatureUtils;';METHOD='isSupportPasswordRetrieve()Z'
BODY_SHA='9356ef0eecaf5e606577c12e928be89f8ea5fabd62c73a8db6bd1d7e589fa556'
LOCK_SHA='69769c3e09027807455199ccaec768af2d8456cf59504f6fdfeb7a9a4a283ac1'
DEP_SHA='d4286f85908d92b2f9118c51d332d32b8600934c237cabbc4006bd3e7228fca8'
JAVA_SHA='33bc1eeba3407cefae0bb33df36878cc2f3c65c68cbce3aa15d31a203ca38aeb'

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')

def source_proof():
    path=OUT/'source-lock.json'
    if digest(path)!=LOCK_SHA:raise ValueError('Immutable source proof lock changed')
    lock=load(path);methods={};refs=[]
    for p in lock['receipts']:
        if digest(ROOT/p['receipt'])!=p['receiptSha256'] or digest(ROOT/p['raw'])!=p['rawSha256']:raise ValueError('Source proof drift')
        receipt=load(ROOT/p['receipt'])
        if receipt['archiveSha256']!=SOURCE_SHA or receipt['readerExitCode'] or not receipt['archiveAndToolPinsVerifiedBeforeAndAfter']:raise ValueError('Source reader identity')
        for line in (ROOT/p['raw']).read_text(encoding='utf-8').splitlines():
            r=json.loads(line)
            if r['record']=='method':methods[r['body']['owner']+'->'+r['body']['signature']]=r
            if r['record']=='reference':refs.append(r)
    target=methods[OWNER+'->'+METHOD]
    b=target['body']
    if target['normalizedBodySha256']!=BODY_SHA or b['registerCount']!=1 or b['catches'] or b['instructions'][0]!={'pc':0,'opcode':'SGET_OBJECT','codeUnits':2,'registers':[0],'referenceKind':'field','reference':OWNER+'->sIsSupportPwdRetrieve:Ljava/lang/Boolean;'}:raise ValueError('Exact original getter shape')
    if b['instructions'][-1]['pc']!=22 or b['instructions'][-1]['opcode']!='RETURN':raise ValueError('Original getter extent')
    if any(i.get('targetPc',2)<2 for i in b['instructions']):raise ValueError('Branch enters replaced prefix')
    calls=[r for r in refs if r['instruction'].get('reference')==OWNER+'->'+METHOD]
    if len(calls)!=11:raise ValueError('Exact eleven direct getter callers required')
    field=OWNER+'->sIsSupportPwdRetrieve:Ljava/lang/Boolean;'
    fieldrefs=[r for r in refs if r['instruction'].get('reference')==field]
    if len(fieldrefs)!=3 or {r['caller'] for r in fieldrefs}!={OWNER+'->'+METHOD}:raise ValueError('Capability cache has another direct consumer')
    caller_proofs=[]
    for r in calls:
        row=methods[r['caller']];ins=row['body']['instructions'];pc=r['instruction']['pc'];near=[i for i in ins if pc<i['pc']<=pc+9]
        move=next((i for i in near if i['opcode']=='MOVE_RESULT'),None)
        guard=next((i for i in near if i['opcode'] in ('IF_EQZ','IF_NEZ')),None)
        if move is None or guard is None or guard['registers']!=move['registers']:raise ValueError('Caller result/guard coupling changed')
        false_pc=guard['targetPc'] if guard['opcode']=='IF_EQZ' else guard['pc']+guard['codeUnits']
        caller_proofs.append({'caller':r['caller'],'sourceBodySha256':row['normalizedBodySha256'],'getterPc':pc,'guardPc':guard['pc'],'guardOpcode':guard['opcode'],'falseSuccessorPc':false_pc})
    for p in lock['resources']:
        if digest(ROOT/p['raw'])!=p['sha256']:raise ValueError('Resource source proof drift')
    for name in ('choose_lock_password_oplus','navigation_choose_lock_pattern'):
        text=(RAW/(name+'.xmltree.txt')).read_text(encoding='utf-8');lines=text.splitlines();hits=[j for j,s in enumerate(lines) if 'id(0x010100d0)=@0x7f0b0c60' in s]
        if len(hits)!=1 or 'visibility(0x010100dc)=2' not in '\n'.join(lines[hits[0]:hits[0]+3]):raise ValueError('Cold reset view visibility changed')
    category=methods['Lcom/oplus/settings/feature/password/controller/OldPasswordCategoryController;->updatePreferenceState()V']
    ci={i['pc']:i for i in category['body']['instructions']}
    if ci[29].get('literal')!=0 or ci[30].get('literal')!=1 or ci[31].get('targetPc')!=52 or [ci[p].get('registers')[-1] for p in (54,59,64)]!=[4,4,5]:raise ValueError('Category false-state visibility changed')
    sdk=methods['Lcom/oplus/settings/privacy/sdk/ScreenLockResetController;-><init>(Landroid/content/Context;)V']
    if [i['reference'] for i in sdk['body']['instructions'] if i['opcode'].startswith('INVOKE')]!=['Ljava/lang/Object;-><init>()V']:raise ValueError('SDK constructor became active')
    return target,{'sourceLock':path.relative_to(ROOT).as_posix(),'sourceLockSha256':LOCK_SHA,'receipts':lock['receipts'],'resources':lock['resources'],'aapt2Sha256':lock['aapt2Sha256'],'directGetterCallers':caller_proofs,'cachedBooleanDirectRefs':3,'coldResetViewXmlVisibilityEnum':2,
        'categoryFalseState':{'sourceBodySha256':category['normalizedBodySha256'],'hiddenKeys':['delete_old_password_category_key','old_password_time_summary_key'],'visibleKey':'lock_pwd_footer','setVisiblePcs':[54,59,64],'countdownStartPcNotReached':48},
        'controllerWrapperConstructor':{'sourceBodySha256':sdk['normalizedBodySha256'],'effect':'Object init and storing Context/system type only; no TEE acquisition call in this body'},
        'limits':'Exact original Settings explicit references and selected layouts only; independent old-mode Intent/result paths remain admission obligations'}

def compile_reader():
    from static_security_reader import _classes,_env,JDK,DEXLIB
    source=ROOT/'tools/SettingsRpmbLeafProof.java'
    if digest(source)!=JAVA_SHA:raise ValueError('Frozen hash-only proof helper changed')
    shared,pins=_classes();classes=OUT/'classes';classes.mkdir(exist_ok=True);cp=str(shared)+os.pathsep+str(DEXLIB)
    r=subprocess.run([str(JDK/'javac.exe'),'-proc:none','-encoding','UTF-8','-source','17','-target','17','-cp',cp,'-d',str(classes),str(source)],capture_output=True,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    (OUT/'compile.txt').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise ValueError('Hash-only reader compilation failed')
    return str(classes)+os.pathsep+cp,{**pins,'tools/SettingsRpmbLeafProof.java':JAVA_SHA,'helperClassSha256':digest(classes/'SettingsRpmbLeafProof.class')}

def read_all(archive,label,cp,pins):
    from static_security_reader import _env,JDK
    path=RAW/(label+'-all-method-hashes.jsonl')
    with path.open('wb') as o,(OUT/(label+'-stderr.txt')).open('wb') as e:
        r=subprocess.run([str(JDK/'java.exe'),'-Xmx2g','-cp',cp,'SettingsRpmbLeafProof',str(archive)],stdout=o,stderr=e,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    if r.returncode or path.stat().st_size>256*1024*1024:raise ValueError('All-method static proof failed')
    return {'raw':path.relative_to(ROOT).as_posix(),'rawSha256':digest(path),'readerExitCode':0,'tools':pins}

def main():
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
    if digest(SOURCE)!=SOURCE_SHA or digest(ROOT/'tools/build_coloros_settings_rpmb_leaf.py')!=DEP_SHA:raise ValueError('Literal source/integrity dependency mismatch')
    # Import only pure byte-format utilities from the frozen first Settings producer.
    from build_coloros_settings_rpmb_leaf import header,seal
    from retrieval_capability_dex import locate
    producer_pin=digest(Path(__file__));private_pin=digest(ROOT/'tools/retrieval_capability_dex.py')
    original_row,proof=source_proof();print('Admitted capability and eleven guarded callers',flush=True)
    with zipfile.ZipFile(SOURCE) as z:
        infos=z.infolist()
        if len(infos)!=10549 or len({i.filename for i in infos})!=len(infos) or sum(i.file_size for i in infos)>384*1024*1024 or any(i.file_size>128*1024*1024 for i in infos):raise ValueError('Exact bounded archive inventory')
        found=[];class_count=0
        for info in infos:
            if not info.filename.endswith('.dex'):continue
            data=z.read(info);h=header(data);class_count+=h['classes'];location,ownership=locate(data,OWNER,METHOD)
            if location:found.append((info.filename,data,location,ownership))
        if len(found)!=1 or class_count!=78960:raise ValueError('Target/whole class identity')
    dex_name,original,location,ownership=found[0]
    if (location['instructionUnits'],location['registers'],location['tryItems'])!=(23,1,0):raise ValueError('Target physical code shape changed')
    a=location['instructionsOffset'];c=a+4;patched=bytearray(original);patched[a:c]=b'\x12\x00\x0f\x00';patched=seal(patched);header(patched)
    if patched[:8]!=original[:8] or patched[32:a]!=original[32:a] or patched[c:]!=original[c:]:raise ValueError('Outside cut changed')
    inverse=bytearray(patched);inverse[a:c]=original[a:c];inverse=seal(inverse)
    forward=bytearray(inverse);forward[a:c]=patched[a:c];forward=seal(forward)
    if inverse!=original or forward!=patched:raise ValueError('Exact inverse/roundtrip failed')
    dex_path=OUT/(dex_name+'.retrieval-capability.dex');dex_path.write_bytes(patched);inverse_path=OUT/(dex_name+'.inverse.dex');inverse_path.write_bytes(inverse)
    archive=OUT/'Settings.retrieval-capability.unselected.apk';entries=[]
    with zipfile.ZipFile(SOURCE) as source,zipfile.ZipFile(archive,'w') as target:
        target.comment=source.comment
        for info in infos:
            old=source.read(info);new=patched if info.filename==dex_name else old;target.writestr(info,new)
            entries.append({'name':info.filename,'sourceSha256':sha(old),'patchedSha256':sha(new),'unchanged':old==new})
    entry_path=RAW/'entry-payloads.json';dump(entry_path,entries)
    with zipfile.ZipFile(archive) as z:
        if z.namelist()!=[i.filename for i in infos] or z.testzip() is not None:raise ValueError('Output inventory/CRC')
        for p in entries:
            data=z.read(p['name'])
            if sha(data)!=p['patchedSha256']:raise ValueError('Output payload drift')
            if p['name'].endswith('.dex'):header(data)
    cp,pins=compile_reader();print('Hashing all original and patched methods',flush=True)
    old_read=read_all(SOURCE,'original',cp,pins);new_read=read_all(archive,'patched',cp,pins)
    changed=[];summary=None;output_hash=None
    with (ROOT/old_read['raw']).open(encoding='utf-8') as old,(ROOT/new_read['raw']).open(encoding='utf-8') as new:
        for l,r in zip_longest(old,new):
            if l is None or r is None:raise ValueError('All-method row count mismatch')
            p,q=json.loads(l),json.loads(r)
            if p['record']=='summary':
                summary={'original':p,'patched':q}
                if {k:v for k,v in p.items() if k!='instructions'}!={k:v for k,v in q.items() if k!='instructions'} or q['instructions']!=p['instructions']+1:raise ValueError('Summary changed beyond one inserted return')
            elif p!=q:
                if p['record']!='method' or {k:v for k,v in p.items() if k!='sha256'}!={k:v for k,v in q.items() if k!='sha256'}:raise ValueError('Class/declaration identity changed')
                changed.append(p['owner']+'->'+p['signature']);output_hash=q['sha256']
                if p['sha256']!=BODY_SHA:raise ValueError('Original normalized body differs')
    if changed!=[OWNER+'->'+METHOD] or summary is None:raise ValueError('Unexpected method changes')
    from static_security_reader import _classes,_env,JDK,DEXLIB
    shared,_=_classes();decoded_path=RAW/'patched-capability.jsonl'
    with decoded_path.open('wb') as o,(OUT/'capability-stderr.txt').open('wb') as e:
        r=subprocess.run([str(JDK/'java.exe'),'-Xmx2g','-cp',str(shared)+os.pathsep+str(DEXLIB),'SecurityDexReader',str(archive),OWNER,'-',METHOD],stdout=o,stderr=e,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
    if r.returncode:raise ValueError('Patched capability decode failed')
    new=next(json.loads(l) for l in decoded_path.read_text(encoding='utf-8').splitlines() if json.loads(l).get('record')=='method');b=original_row['body'];nb=new['body']
    expected=[{'pc':0,'opcode':'CONST_4','codeUnits':1,'registers':[0],'literal':0},{'pc':1,'opcode':'RETURN','codeUnits':1,'registers':[0]}]+[i for i in b['instructions'] if i['pc']>=2]
    if nb['instructions']!=expected or {k:v for k,v in b.items() if k!='instructions'}!={k:v for k,v in nb.items() if k!='instructions'} or new['normalizedBodySha256']!=output_hash:raise ValueError('Exact return/tail/try metadata changed')
    if digest(SOURCE)!=SOURCE_SHA or digest(Path(__file__))!=producer_pin or digest(ROOT/'tools/retrieval_capability_dex.py')!=private_pin or digest(ROOT/'tools/build_coloros_settings_rpmb_leaf.py')!=DEP_SHA:raise ValueError('Immutable source/producer/helper changed')
    result={'schema':'coloros-retrieval-capability-leaf/v1','status':'UNSELECTED_COLD_START_ONLY_OPTIONAL_OPPO_RETRIEVAL_CAPABILITY_UNAVAILABLE','selected':False,'coldStartOnly':True,'sourceArchive':str(SOURCE),'sourceArchiveSha256':SOURCE_SHA,
        'patchedArchive':archive.relative_to(ROOT).as_posix(),'patchedArchiveSha256':digest(archive),'owner':OWNER,'method':METHOD,'physicalDex':dex_name,'logicalHeaderOffset':0,'sourceBodySha256':BODY_SHA,'patchedBodySha256':output_hash,
        'edits':[{'owner':OWNER,'method':METHOD,'physicalDex':dex_name,'logicalHeaderOffset':0,'firstPc':0,'endExclusivePc':2,'instructionByteStart':a,'instructionByteEndExclusive':c,'methodInstructionByteStart':a,'methodInstructionByteEndExclusive':a+46,'sourceBytesSha256':sha(original[a:c]),'patchedBytesSha256':sha(patched[a:c]),'sourceBodySha256':BODY_SHA,'patchedBodySha256':output_hash,'replacement':'CONST_4 v0,0; RETURN v0'}],
        'patchedDex':dex_path.relative_to(ROOT).as_posix(),'patchedDexSha256':digest(dex_path),'inverseDex':inverse_path.relative_to(ROOT).as_posix(),'inverseDexSha256':digest(inverse_path),'sourceDexSha256':sha(original),'codeLocation':location,'codeOwnership':ownership,
        'sourceProof':proof,'allMethodProof':{'original':old_read,'patched':new_read,'summary':summary,'unchangedCodeBodies':summary['original']['codeBodies']-1,'unchangedNoCodeDeclarations':summary['original']['methods']-summary['original']['codeBodies'],'changedMethods':changed},
        'entryPayloadProof':{'raw':entry_path.relative_to(ROOT).as_posix(),'rawSha256':digest(entry_path),'entries':len(entries),'unchangedEntries':sum(p['unchanged'] for p in entries)},'patchedRead':{'raw':decoded_path.relative_to(ROOT).as_posix(),'rawSha256':digest(decoded_path)},
        'checks':{'allInputOutput14Dex039Integrity':True,'oneChangedMethodAllOtherDeclarationsBodiesEqual':True,'exactFalseCapabilityNotAuthenticationResult':True,'allOutsideCutAndIntegrityBytesEqual':True,'allOriginalBranchesRegistersTriesTailPreserved':True,'noCodeAlias':True,'inverseExactOriginalDex':True,'forwardRoundtripExactPatchedDex':True,'allOtherArchivePayloadsEqual':True,'all11DirectGetterCallersAndCacheRefsPinned':True,'coldPairedResetViewResourcesPinned':True},
        'requiredSelectionConditions':['Cold fresh Settings process/fragment/controller owners with no preexisting retrieval jobs, callbacks, timers, click listeners or capability-dependent state; no hot teardown is supplied','Scope is only the unsupported OPPO capability and its queried branches; independently supplied old-mode Intents, restored old-mode state and activity results require explicit rejection/cancellation/admission before runtime selection; this leaf does not claim every old-password screen hidden','Samsung genuine previous-credential recovery remains a separate mapped policy; earlier PINs must fail ordinary unlock in both systems','Preserve current-credential confirmation, LockPatternUtils set/verify/removal, StrongAuth/lockout/additional-factor, real fingerprint enrollment and app/key/CE behavior through the actual authority','Compose the separately reviewed Settings RPMB ingress cut; static credential caches and pattern-specific/other optional RPMB routes remain separate source-closed removal/adaptation obligations','Optional reset view initial GONE and guarded new fetches are observed source facts, not installed layout/overlay, caller authorization or Android runtime acceptance'],
        'limits':['Exact original Settings archive explicit references only; no reflection/dynamic/other-APK or installed-byte closure','No actual UI inflation, timer, callback drain, TEE, authentication or OEM execution','APK wrapper reserialized; payload equality does not prove ZIP alignment/signing/ART/install acceptance'],
        'negativeEvidenceScope':'Positive actual-byte whole-method, boundary/try, alias, inverse and roundtrip proofs; no malformed-byte negative fixtures or runtime fault injection executed',
        'producerSha256':producer_pin,'privateHelperSha256':private_pin,'integrityDependency':{'path':'tools/build_coloros_settings_rpmb_leaf.py','sha256':DEP_SHA},'hashProofHelper':{'path':'tools/SettingsRpmbLeafProof.java','sha256':JAVA_SHA},'oemCodeExecuted':False,'phoneActions':False}
    dump(OUT/'receipt.json',result);dump(ROOT/'inventory/coloros-retrieval-capability-leaf.json',result)
    print(json.dumps({'archiveSha256':result['patchedArchiveSha256'],'dexSha256':result['patchedDexSha256'],'bodySha256':output_hash,'physicalDex':dex_name,'allMethods':summary['original']['methods'],'callerGuards':len(proof['directGetterCallers'])}))

if __name__=='__main__':main()
