"""Cold-start-only UNSELECTED ColorOS RPMB input-removal leaf, offline.

Uses the frozen first-leaf DEX039 integrity helpers without editing that tool.
Raw original/patched method bodies stay in ignored firmware/rpmb-input-leaf.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import struct
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
OUT = ROOT/'out/rpmb-input-leaf'
RAW = ROOT/'firmware/rpmb-input-leaf'
SOURCE = PARENT/'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk'
SOURCE_SHA = '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'
DEP = ROOT/'tools/build_coloros_pin_metadata_leaf.py'
DEP_SHA = '9ff4731807dad9df99ba8468b17611bf21b03fd17d2db917d4ba204f67fab8a7'
if hashlib.sha256(DEP.read_bytes()).hexdigest() != DEP_SHA:
    raise ValueError('Frozen first-leaf integrity dependency changed')
UTIL = runpy.run_path(str(DEP))
header, seal, u16, u32, uleb = [UTIL[n] for n in ['header', 'seal', 'u16', 'u32', 'uleb']]
SETTER = 'Lcom/oplus/keyguard/security/OplusLockPatternChecker;->setEntry(Ljava/lang/String;)V'
GETTER = 'Lcom/oplus/keyguard/security/OplusLockPatternChecker;->getEntry()Ljava/lang/String;'
SOURCE_XREF = ROOT/'firmware/construction-frontend/20261105T145647788467Z-fad912ed0d134a32814131dd3a68edca.jsonl'
CALLBACKS = ['Lcom/oplus/keyguard/security/OplusLockPatternChecker$checkCredential$1;', 'Lcom/oplus/keyguard/security/OplusLockPatternChecker$checkMultiUserCredential$1;']
CALLBACK_SIG = 'onChecked(Lcom/android/internal/widget/VerifyCredentialResponse;IZ)V'
TASK = 'Lcom/oplus/keyguard/security/verify/RpmbCheckTask;'
TASK_INIT = TASK+'-><init>(Ljava/lang/String;ILcom/android/internal/widget/LockscreenCredential;ILcom/android/internal/widget/VerifyCredentialResponse;Lcom/oplus/keyguard/security/OplusLockPatternChecker$rpmbCallback$1;)V'
TASK_FIELD = 'Lcom/oplus/keyguard/security/OplusLockPatternChecker;->mRpmbCheckTask:'+TASK
TASK_SET = 'Lcom/oplus/keyguard/security/OplusLockPatternChecker;->access$setMRpmbCheckTask$p(Lcom/oplus/keyguard/security/OplusLockPatternChecker;'+TASK+')V'
# Authored edit metadata only. PC ranges are half-open DEX code-unit ranges.
PLAN = {
 'OplusKeyguardFixedPinViewController': ('8649d14ce0725c9f38c881ada3fd193c83c93eca7a677327092244768f63de3a', [(0,11)]),
 'OplusKeyguardPasswordViewController': ('e5a20a026ee4efa2c68644cf16789941de86ad7adc858fce4d3583eee5d54ddd', [(0,27)]),
 'OplusKeyguardPinViewController': ('7e9bd42cee4cbadae637859aa37c27571029421fdd53bfababa94ce3327503a2', [(0,27)]),
 'OplusKeyguardLockDeadPasswordViewController': ('75034054f20801d5faa78296f089896387e5db3c51bab36a4a4fa97162a1237c', [(0,27)]),
 'OplusSubDisplayKeyguardPinViewController': ('3f70611c19bf62f33efd7325aafeac2a59f013f3f993f8bcf1ad3141dd62c381', [(0,27)]),
 'PresentationFixedPinViewController': ('446458c27b56138050a42da1634e2736011c14e1dfa98ca0760b51d13e52a859', [(0,11)]),
 'PresentationPasswordViewController': ('22a0e8232be92eb7094755d4818ceb03fdf6ce8798251f7960663de2292689ec', [(0,25)]),
 'PresentationPinViewController': ('a77de1d7ad6a9f29ec6f51c951dd66d2f5e2454406c8b402809c4b348473d77f', [(0,25)]),
 'PresentationPatternViewController': ('e9c392fb25d21b2ea569091e19fa62e9efa0b22fc6bd3faeaab221f3299800c0', [(0,9)]),
 'OplusSubDisplayKeyguardFixedPinViewController': ('f4279bd08770209cd52b6174502afff749d96e1377508e33027368e6fba8954f', [(0,11)]),
 'OplusKeyguardPatternViewController': ('7628a9aa886de654b5e36ad627ee87b742c58f356878788df97e7b1dae26046f', [(127,140)]),
 'OplusKeyguardPatternViewController$UnlockPatternListener': ('97af61fea163080ffeb4c3b458f3357742573b3a03d7a66ef3c73ec1fe51332c', [(18,33)]),
 'OplusLockPatternChecker$checkCredential$1': ('e93665b55eef226729296d95944a7100f9ebd69688f1bcad3aea34a2097884e6', [(59,111),(114,117)]),
 'OplusLockPatternChecker$checkMultiUserCredential$1': ('23c9ec03b989875abdc86b042c48897339da0176d1be740cfb113899657e17f8', [(29,82),(85,88)]),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def plan_for(row):
    return PLAN[row['body']['owner'].rsplit('/',1)[1][:-1]]


def in_cut(pc, cuts):
    return any(a <= pc < z for a,z in cuts)


def validate_source(row):
    body = row['body']; expected, cuts = plan_for(row); ins = body['instructions']
    if row['normalizedBodySha256'] != expected or body['catches']:
        raise ValueError('Exact target body/empty try contract changed')
    bounds = {i['pc'] for i in ins}; end = ins[-1]['pc']+ins[-1]['codeUnits']
    by_pc = {i['pc']:i for i in ins}
    for a,z in cuts:
        if a not in bounds or z not in bounds|{end} or sum(i['codeUnits'] for i in ins if a<=i['pc']<z) != z-a:
            raise ValueError('Cut is not an exact complete instruction slice')
        if any('PAYLOAD' in i['opcode'] for i in ins if a<=i['pc']<z):
            raise ValueError('Payload cannot be removed')
    edges = []
    for i in ins:
        if 'targetPc' not in i: continue
        target = i['targetPc']
        if target not in bounds: raise ValueError('Unaligned branch/payload target')
        if not in_cut(i['pc'],cuts):
            if any(a<target<z for a,z in cuts): raise ValueError('Retained edge enters removed interior')
            edges.append((i['pc'],target))
        if i['opcode'] in ['PACKED_SWITCH','SPARSE_SWITCH']:
            for element in by_pc[target]['switchElements']:
                dest = i['pc']+element['offsetFromReferringSwitchPc']
                if dest not in bounds or any(a<dest<z for a,z in cuts):
                    raise ValueError('Switch case enters removed interior/unaligned target')
                edges.append((i['pc'],dest))
    if body['owner'] in CALLBACKS:
        null_pc, clear_pc, reg = (58,111,2) if body['owner']==CALLBACKS[0] else (28,82,4)
        if by_pc[null_pc] != {'pc':null_pc,'opcode':'CONST_4','codeUnits':1,'registers':[reg],'literal':0} or by_pc[clear_pc]['reference']!=TASK_SET or by_pc[clear_pc]['registers'][-1]!=reg:
            raise ValueError('Retained null assignment/field clear contract changed')
        removed = [i.get('reference') for i in ins if in_cut(i['pc'],cuts)]
        if removed.count(GETTER)!=1 or removed.count(TASK_INIT)!=1 or not any('->duplicate()' in (x or '') for x in removed):
            raise ValueError('Exact optional duplicate/allocation/getter block missing')
    else:
        if sum(i.get('reference')==SETTER for i in ins if in_cut(i['pc'],cuts))!=1:
            raise ValueError('One optional entry copy must be removed')
    return {'retainedBranchAndSwitchEdges':len(edges),'removedCodeUnits':sum(z-a for a,z in cuts),'tryHandlerCount':0,'payloadsPreserved':sum('PAYLOAD' in i['opcode'] for i in ins),'retainedInteriorEntries':0}


def locate_all(data, wanted):
    """Bounded ordinary-039 metadata walk; never invokes OEM code."""
    header(data)
    strings,types,protos,methodids,classes = [u32(data,p) for p in (60,68,76,92,100)]
    def string(index):
        if index>=u32(data,56): raise ValueError('String index')
        p=u32(data,strings+4*index);_,p=uleb(data,p);end=data.find(b'\0',p,min(len(data),p+1048576))
        if end<0: raise ValueError('Bounded string terminator')
        return data[p:end]
    def typ(index):
        if index>=u32(data,64): raise ValueError('Type index')
        return string(u32(data,types+4*index))
    def signature(index):
        owner,proto,name=struct.unpack_from('<HHI',data,methodids+8*index)
        if proto>=u32(data,72): raise ValueError('Proto index')
        ret,params=u32(data,protos+12*proto+4),u32(data,protos+12*proto+8);parts=[]
        if params:
            n=u32(data,params)
            if n>65535 or params+4+2*n>len(data): raise ValueError('Parameter extent')
            parts=[typ(u16(data,params+4+2*i)) for i in range(n)]
        return (string(name)+b'('+b''.join(parts)+b')'+typ(ret)).decode('ascii')
    found={};ranges=[];encoded=0;wanted_bytes={x.encode() for x in wanted}
    for ci in range(u32(data,96)):
        row=classes+32*ci;owner=u32(data,row);p=u32(data,row+24)
        if not p: continue
        counts=[]
        for _ in range(4):n,p=uleb(data,p);counts.append(n)
        if sum(counts)>2000000: raise ValueError('Encoded member bound')
        for count in counts[:2]:
            idx=0
            for _ in range(count):
                delta,p=uleb(data,p);idx+=delta;_,p=uleb(data,p)
                if idx>=u32(data,80): raise ValueError('Field index')
        owner_bytes=typ(owner)
        for count in counts[2:]:
            idx=0
            for _ in range(count):
                delta,p=uleb(data,p);idx+=delta;access,p=uleb(data,p);code,p=uleb(data,p);encoded+=1
                if idx>=u32(data,88) or u16(data,methodids+idx*8)!=owner: raise ValueError('Encoded method identity')
                if not code: continue
                if code%4 or code+16>len(data): raise ValueError('Code alignment/extent')
                units=u32(data,code+12);start=code+16;end=start+2*units
                if units>10000000 or end>len(data): raise ValueError('Instruction extent')
                ranges.append((idx,start,end))
                if owner_bytes in wanted_bytes:
                    own=owner_bytes.decode('ascii');sig=signature(idx)
                    if sig in wanted[own]:
                        key=own+'->'+sig
                        if key in found: raise ValueError('Duplicate target method')
                        found[key]={'methodId':idx,'codeOffset':code,'instructionsOffset':start,'instructionUnits':units,'registers':u16(data,code),'incomingWords':u16(data,code+2),'outgoingWords':u16(data,code+4),'tryItems':u16(data,code+6),'debugInfoOffset':u32(data,code+8),'accessFlags':access}
    return found,ranges,{'encodedMethods':encoded,'codeBodies':len(ranges)}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def raw_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]


def targets():
    inv = json.loads((ROOT/'inventory/construction-frontend.json').read_text())
    proof = next(p for p in inv['proofs'] if p['key']['role'] == 'systemui' and p['key']['reference'] == SETTER)
    if digest(ROOT/proof['raw']) != proof['rawSha256']:
        raise ValueError('Frozen source setter xref proof changed')
    rows = [r for r in raw_rows(ROOT/proof['raw']) if r['record'] == 'reference']
    if len(rows) != 12:
        raise ValueError('Exact twelve original entry callers required')
    result = {}
    for row in rows:
        owner, sig = row['caller'].split('->', 1)
        result.setdefault(owner, []).append(sig)
    for owner in CALLBACKS:
        result.setdefault(owner, []).append(CALLBACK_SIG)
    return result


def read_java(archive, label, owners):
    from static_security_reader import _classes, _env, JDK, DEXLIB
    cache, pins = _classes()
    records = []; receipts = []
    for index, owner in enumerate(owners):
        raw = RAW/(label+'-'+str(index)+'.jsonl')
        error = OUT/(label+'-'+str(index)+'-stderr.txt')
        cmd = [JDK/'java.exe', '-Xmx2g', '-Duser.home='+str(OUT/'runtime-home'), '-Djava.io.tmpdir='+str(OUT/'tmp'), '-cp', str(cache)+os.pathsep+str(DEXLIB), 'SecurityDexReader', archive, owner, '-', '--ALL-DECLARED-METHODS--']
        with raw.open('wb') as stdout, error.open('wb') as stderr:
            result = subprocess.run(list(map(str, cmd)), stdout=stdout, stderr=stderr, env=_env(), creationflags=subprocess.CREATE_NO_WINDOW, timeout=60)
        if result.returncode or raw.stat().st_size > 32*1024*1024:
            raise ValueError('Selected original/patched class read failed: '+owner)
        rows = raw_rows(raw)
        summary = next((r for r in rows if r['record'] == 'summary'), None)
        if summary is None or summary['classDefinitions'] != 73080:
            raise ValueError('Actual whole archive definition count changed')
        records += rows
        receipts.append({'owner': owner, 'raw': raw.relative_to(ROOT).as_posix(), 'rawSha256': digest(raw), 'summary': summary, 'tools': pins})
    return records, receipts


def inspect():
    if digest(SOURCE) != SOURCE_SHA:
        raise ValueError('Exact source archive changed')
    owners = targets()
    rows, receipts = read_java(SOURCE, 'source', owners)
    (OUT/'source-receipts.json').write_text(json.dumps(receipts, indent=2)+'\n')
    selected = []
    for row in rows:
        if row['record'] == 'method' and row['body']['signature'] in owners.get(row['body']['owner'], []):
            selected.append(row)
    if len(selected) != 14:
        raise ValueError('Fourteen target original methods required')
    (RAW/'selected-source-methods.json').write_text(json.dumps(selected, indent=2)+'\n')
    print(json.dumps({'selectedMethods': len(selected), 'selectedClasses': len(owners), 'selectedClassAllMethods': sum(r['record'] == 'method' for r in rows), 'raw': 'firmware/rpmb-input-leaf/selected-source-methods.json'}))


def reference_read(archive,label,reference):
    from static_security_reader import _classes,_env,JDK,DEXLIB
    cache,pins=_classes();raw=RAW/(label+'.jsonl');error=OUT/(label+'-stderr.txt')
    cmd=[JDK/'java.exe','-Xmx2g','-Duser.home='+str(OUT/'runtime-home'),'-Djava.io.tmpdir='+str(OUT/'tmp'),'-cp',str(cache)+os.pathsep+str(DEXLIB),'SecurityDexReader',archive,'--ALL-CLASSES--',reference]
    with raw.open('wb') as stdout,error.open('wb') as stderr:
        result=subprocess.run(list(map(str,cmd)),stdout=stdout,stderr=stderr,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
    if result.returncode or raw.stat().st_size>32*1024*1024: raise ValueError('Reference scan failed')
    rows=raw_rows(raw);summary=next((r for r in rows if r['record']=='summary'),None)
    if not summary or summary['classDefinitions']!=73080: raise ValueError('Reference scan completion/count')
    matches=[r for r in rows if r['record']=='reference']
    return matches,{'reference':reference,'raw':raw.relative_to(ROOT).as_posix(),'rawSha256':digest(raw),'matchCount':len(matches),'tools':pins,'summary':summary}


def reused_source_contracts():
    inventory=json.loads((ROOT/'inventory/construction-frontend.json').read_text())
    field='Lcom/oplus/keyguard/security/OplusLockPatternChecker;->entry:Ljava/lang/String;'
    proof=next(p for p in inventory['proofs'] if p['key'].get('reference')==field)
    if digest(ROOT/proof['raw'])!=proof['rawSha256']: raise ValueError('Frozen entry field proof changed')
    refs=[r for r in raw_rows(ROOT/proof['raw']) if r['record']=='reference']
    if len(refs)!=3 or sum(r['instruction']['opcode'].startswith('IPUT') for r in refs)!=2:
        raise ValueError('Unexpected direct entry field frontier')
    allowed={'getEntry()Ljava/lang/String;','setEntry(Ljava/lang/String;)V','<init>(Lcom/android/keyguard/KeyguardSecurityModel$SecurityMode;Ldagger/Lazy;Ldagger/Lazy;Lcom/android/keyguard/KeyguardUpdateMonitor;)V'}
    if {r['caller'].split('->',1)[1] for r in refs}!=allowed: raise ValueError('Unclassified entry field consumer')
    manager_sig='postRpmbCheckTask(Lcom/oplus/keyguard/security/verify/RpmbCheckTask;Z)V'
    manager=next(p for p in inventory['proofs'] if p['key'].get('role')=='systemui' and manager_sig in p['key'].get('methods',[]))
    if digest(ROOT/manager['raw'])!=manager['rawSha256']: raise ValueError('Frozen downstream null guard proof changed')
    row=next(r for r in raw_rows(ROOT/manager['raw']) if r['record']=='method' and r['body']['signature']==manager_sig)
    if row['normalizedBodySha256']!='1fd05e8cc5762ff763c2252221fc0527089f0a2c00a36e36ca469e2b1b0c562a' or row['body']['instructions'][0]!={'pc':0,'opcode':'IF_EQZ','codeUnits':2,'registers':[4],'targetPc':79} or row['body']['instructions'][-1]['opcode']!='RETURN_VOID' or row['body']['instructions'][-1]['pc']!=79:
        raise ValueError('Downstream null rejection changed')
    return {'entryField':{'raw':proof['raw'],'rawSha256':proof['rawSha256'],'directReferences':3,'consumers':sorted(allowed),'plainEntryWriters':'Constructor initialization and setter only; all twelve direct setter invocations removed'},'managerNullTask':{'raw':manager['raw'],'rawSha256':manager['rawSha256'],'sourceBodySha256':row['normalizedBodySha256'],'method':manager_sig,'nullGuardPc':0,'returnPc':79,'beforeCacheWritePc':28,'beforeExecutorSubmitPc':76}}


def build():
    if digest(SOURCE)!=SOURCE_SHA: raise ValueError('Immutable original APK differs')
    reused=reused_source_contracts()
    owners=targets();original_rows,original_reads=read_java(SOURCE,'source',owners)
    old_methods={r['body']['owner']+'->'+r['body']['signature']:r for r in original_rows if r['record']=='method'}
    selected={k:r for k,r in old_methods.items() if r['body']['signature'] in owners.get(r['body']['owner'],[])}
    if len(selected)!=14 or len(old_methods)!=183: raise ValueError('Original selected class/method count')
    boundaries={k:validate_source(r) for k,r in selected.items()}
    entries={};headers={}
    with zipfile.ZipFile(SOURCE) as archive:
        infos=archive.infolist()
        if len(infos)>10000 or len({i.filename for i in infos})!=len(infos): raise ValueError('Archive inventory bound/duplicates')
        for info in infos:
            if info.file_size>256*1024*1024: raise ValueError('Expanded entry bound')
            entries[info.filename]=archive.read(info)
            if info.filename.endswith('.dex'): headers[info.filename]=header(entries[info.filename])
        if archive.testzip() is not None: raise ValueError('Source ZIP CRC')
    if list(headers)!=['classes.dex']+['classes'+str(n)+'.dex' for n in range(2,10)] or sum(h['classes'] for h in headers.values())!=73080:
        raise ValueError('Exact nine ordinary DEX039 inputs/count required')
    edits=[];dex_proofs=[];patched_entries={};seen=set()
    for name in headers:
        original=entries[name];locations,code_ranges,ownership=locate_all(original,owners);byte_ranges=[]
        for key,location in locations.items():
            if key in seen or key not in selected: raise ValueError('Ambiguous/unselected target')
            seen.add(key);row=selected[key];_,cuts=plan_for(row)
            if row['physicalDex']!=name or row['logicalHeaderOffset']!=0 or location['registers']!=row['body']['registerCount'] or location['tryItems']!=0:
                raise ValueError('DEX/body location mismatch')
            method_ranges=[]
            for first,end in cuts:
                a=location['instructionsOffset']+2*first;z=location['instructionsOffset']+2*end
                if end>location['instructionUnits']: raise ValueError('Cut beyond code item')
                if any(idx!=location['methodId'] and max(a,s)<min(z,e) for idx,s,e in code_ranges):
                    raise ValueError('Other method overlaps/aliases changed instructions')
                method_ranges.append({'firstPc':first,'endExclusivePc':end,'byteStart':a,'byteEndExclusive':z,'byteCount':z-a,'sourceBytesSha256':sha(original[a:z]),'patchedBytesSha256':sha(bytes(z-a))})
                byte_ranges.append((a,z,key))
            edits.append({'owner':row['body']['owner'],'method':row['body']['signature'],'physicalDex':name,'logicalHeaderOffset':0,'sourceBodySha256':row['normalizedBodySha256'],'codeLocation':location,'ranges':method_ranges,'branchTryProof':boundaries[key]})
        if not byte_ranges: continue
        byte_ranges.sort()
        if any(byte_ranges[i][1]>byte_ranges[i+1][0] for i in range(len(byte_ranges)-1)): raise ValueError('Overlapping edits')
        changed=bytearray(original)
        for a,z,_ in byte_ranges: changed[a:z]=bytes(z-a)
        patched=seal(changed);header(patched)
        # Compare every unedited byte segment, rather than only known methods.
        cursor=32
        for a,z,_ in byte_ranges:
            if original[cursor:a]!=patched[cursor:a] or patched[a:z]!=bytes(z-a): raise ValueError('Nonpatch change/NOP mismatch')
            cursor=z
        if original[:8]!=patched[:8] or original[cursor:]!=patched[cursor:]: raise ValueError('Outside patch change')
        inverse=bytearray(patched)
        for a,z,_ in byte_ranges: inverse[a:z]=original[a:z]
        inverse=seal(inverse)
        if inverse!=original: raise ValueError('Exact inverse failed')
        repeat=bytearray(inverse)
        for a,z,_ in byte_ranges: repeat[a:z]=bytes(z-a)
        if seal(repeat)!=patched: raise ValueError('Exact patched roundtrip failed')
        (OUT/(name+'.patched')).write_bytes(patched);(OUT/(name+'.inverse')).write_bytes(inverse)
        patched_entries[name]=patched
        dex_proofs.append({'physicalDex':name,'sourceSha256':sha(original),'patchedSha256':sha(patched),'inverseSha256':sha(inverse),'sourceHeader':headers[name],'patchedHeader':header(patched),'codeOwnership':ownership,'methodCountEdited':len(locations),'rangeCount':len(byte_ranges),'byteRanges':[[a,z] for a,z,_ in byte_ranges],'outsideRangesAndIntegrityHeaderEqual':True,'otherMethodCodeAliasOverlapCount':0,'inverseEqualsOriginal':True,'roundtripEqualsPatched':True})
    if seen!=set(selected): raise ValueError('Not every target method located exactly once')
    output=OUT/'SystemUI.rpmb-input-leaf.apk'
    with zipfile.ZipFile(output,'w') as archive:
        for info in infos: archive.writestr(info,patched_entries.get(info.filename,entries[info.filename]))
    payloads=[]
    with zipfile.ZipFile(output) as archive:
        if archive.namelist()!=[i.filename for i in infos] or archive.testzip() is not None: raise ValueError('Output ZIP inventory/CRC')
        for name,old in entries.items():
            new=archive.read(name)
            if new!=patched_entries.get(name,old): raise ValueError('Unexpected entry payload')
            if name in headers: header(new)
            payloads.append({'name':name,'sourceSha256':sha(old),'patchedSha256':sha(new),'unchanged':old==new})
    new_rows,new_reads=read_java(output,'patched',owners)
    new_methods={r['body']['owner']+'->'+r['body']['signature']:r for r in new_rows if r['record']=='method'}
    if set(old_methods)!=set(new_methods): raise ValueError('Method identity drift')
    if [r for r in original_rows if r['record']=='class']!=[r for r in new_rows if r['record']=='class']:
        raise ValueError('Class/field/method descriptor drift')
    for key,row in old_methods.items():
        new=new_methods[key]
        if key not in selected:
            if row!=new: raise ValueError('Other selected-class method changed')
            continue
        body=row['body'];_,cuts=plan_for(row);expected=[]
        for i in body['instructions']:
            if in_cut(i['pc'],cuts): expected += [{'pc':pc,'opcode':'NOP','codeUnits':1} for pc in range(i['pc'],i['pc']+i['codeUnits'])]
            else: expected.append(i)
        if new['body']['instructions']!=expected or {k:v for k,v in body.items() if k!='instructions'}!={k:v for k,v in new['body'].items() if k!='instructions'}:
            raise ValueError('Unexpected body/register/try/payload change')
        next(e for e in edits if e['owner']+'->'+e['method']==key)['patchedBodySha256']=new['normalizedBodySha256']
    # Close direct getter/setter/task constructor and task-field writer frontiers.
    closure=[]
    for index,(ref,before,after) in enumerate([(SETTER,12,0),(GETTER,2,0),(TASK_INIT,2,0),(TASK_SET,4,2),(TASK_FIELD,4,4)]):
        old_refs,old_proof=reference_read(SOURCE,'source-xref-'+str(index),ref)
        new_refs,new_proof=reference_read(output,'patched-xref-'+str(index),ref)
        if len(old_refs)!=before or len(new_refs)!=after: raise ValueError('Direct caller/field closure changed')
        if ref in [SETTER,GETTER,TASK_INIT,TASK_SET]:
            if any(r['caller'] not in selected for r in old_refs): raise ValueError('Unclassified external direct caller')
            if ref==TASK_SET and sorted((r['caller'],r['instruction']['pc']) for r in new_refs)!=sorted([(CALLBACKS[0]+'->'+CALLBACK_SIG,111),(CALLBACKS[1]+'->'+CALLBACK_SIG,82)]):
                raise ValueError('Only retained null setters may remain')
        if ref==TASK_FIELD:
            if old_refs!=new_refs or sum(x['instruction']['opcode'].startswith('IPUT') for x in old_refs)!=1 or next(x for x in old_refs if x['instruction']['opcode'].startswith('IPUT'))['caller'].split('->',1)[1]!=TASK_SET.split('->',1)[1]:
                raise ValueError('Unexpected task field writer/constructor state')
        closure.append({'source':old_proof,'patched':new_proof})
    # Decoded-record admission probes, not OEM/runtime or malformed-byte tests.
    sample=next(iter(selected.values()));wrong=json.loads(json.dumps(sample));wrong['normalizedBodySha256']='0'*64
    for label,record in [('wrongBody',wrong)]:
        try: validate_source(record)
        except ValueError: pass
        else: raise ValueError('Negative admission accepted '+label)
    branch=next(r for r in selected.values() if r['body']['owner'].endswith('/OplusKeyguardPatternViewController;'))
    wrong=json.loads(json.dumps(branch));next(i for i in wrong['body']['instructions'] if i.get('targetPc')==123)['targetPc']=130
    # Retain the literal hash so this specifically exercises the retained-edge invariant.
    try: validate_source(wrong)
    except ValueError: pass
    else: raise ValueError('Interior-branch negative accepted')
    if digest(SOURCE)!=SOURCE_SHA or digest(DEP)!=DEP_SHA: raise ValueError('Input/dependency changed during build')
    checks={'sourceArchiveUnchanged':True,'allNineInputOutputOrdinaryDex039IntegrityValid':True,'exactFourteenTargetBodiesAdmitted':True,'twelveEntryCopiesAndTwoGetterConsumersRemoved':True,'bothTaskAllocationsAndCredentialDuplicatesRemoved':True,'retainedMatchedResultsNullTaskSettersZeroizeAndCleanup':True,'allOutsideRangesAndIntegrityHeaderBytesEqual':True,'allOtherArchivePayloadsEqual':all(x['unchanged'] for x in payloads if x['name'] not in patched_entries),'inverseAndRoundtripEveryChangedDexEqual':True,'otherMethodCodeOverlapCount':0,'unchangedOtherSelectedClassMethodBodies':len(old_methods)-len(selected),'allClassFieldMethodDescriptorsPreserved':True,'allRetainedBranchesSwitchPayloadsRegistersAndTriesPreserved':True,'wholeArchiveClassDefinitions':73080,'decodedWrongBodyAndInteriorBranchNegativesRejected':True}
    payload_path=OUT/'archive-entry-payloads.json';payload_path.write_text(json.dumps(payloads,indent=2)+'\n')
    required=['Admit only the exact original source profile and reviewed composition; this leaf is unselected and not a runnable Samsung integration.','Cold fresh process with newly constructed checker and verify-manager owners; no retained old task, cached credential, queued callback or live byte replacement.','Retain native credential factories, verification full results, zeroize/task cleanup, cancellation ownership, selected-user and all genuine StrongAuth/additional-factor/finish gates. Unknown authority/policy state must deny completion.','Assemble genuine Samsung credential/fingerprint authority and typed bindings separately, including shared Settings changes, app authentication, encrypted storage and authentication-bound keys.','Compose separately reviewed optional RoR/SP registration/reboot and Settings RPMB/cache removal when declaring that broader optional feature unavailable; this leaf alone does not establish full OEM removal.','Revalidate installed image, Android/ART/signing behavior and the full cross-OS acceptance matrix before any runtime selection.']
    receipt={'schema':'coloros-rpmb-input-leaf/v1','status':'UNSELECTED_PC_ONLY_COLD_START_OPTIONAL_INPUT_REMOVAL','selected':False,'coldStartOnly':True,'sourceArchive':str(SOURCE),'sourceArchiveSha256':SOURCE_SHA,'patchedArchive':output.relative_to(ROOT).as_posix(),'patchedArchiveSha256':digest(output),'edits':edits,'dexProofs':dex_proofs,'allInputDexHeaders':headers,'originalRead':original_reads,'patchedRead':new_reads,'directClosure':closure,'reusedSourceContracts':reused,'archiveEntryPayloadReceipt':{'path':payload_path.relative_to(ROOT).as_posix(),'sha256':digest(payload_path),'entryCount':len(payloads),'changedPayloadCount':sum(not x['unchanged'] for x in payloads)},'checks':checks,'dependency':{'path':DEP.relative_to(ROOT).as_posix(),'sha256':DEP_SHA},'producerSha256':digest(Path(__file__)),'signatureLimits':'DEX checksums are format integrity, not authenticity. ZIP payload preservation excludes physical ZIP encoding and APK signing block. Android signing/ART acceptance untested.','coldAdmission':'Fresh process and fresh checker/verify-manager owners only, with no preexisting task/cache/queued callback. No live patch, drain, teardown or old-generation recovery claim.','requiredSelectionConditions':required,'residualScope':['Unmodified checker entry/getter/setter declarations and dead task implementation remain; no direct entry setter/getter invocation or task constructor remains in this exact APK. Reflection/dynamic injection and other archives are outside the direct static graph.','Separate RoR/SP registration/reboot/encrypted-SP removal and Settings RPMB/cache removal are not implemented by this leaf.','Other checker postRpmbCheckTask calls can still realize VerifyManager; original downstream method rejects null task before cache/executor effects. This leaf does not promise removal of all optional manager initialization.','Real Samsung authority/typed transport, additional-factor/StrongAuth readiness, confirmation, user/profile, lockout, CE/Keystore and app policy remain separate required integration gates.'],'negativeEvidenceScope':'Decoded-record admission invariant probes only, not malformed DEX-byte fixtures or runtime failure injection.','oemCodeExecuted':False,'androidExecuted':False,'phoneAction':False,'runtimeAccepted':False}
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (ROOT/'inventory/coloros-rpmb-input-leaf.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'patchedArchiveSha256':receipt['patchedArchiveSha256'],'changedDex':list(patched_entries),'methodEdits':len(edits),'checks':checks}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True); (OUT/'tmp').mkdir(exist_ok=True)
    if args.inspect:
        inspect()
    else:
        build()


if __name__ == '__main__':
    main()
