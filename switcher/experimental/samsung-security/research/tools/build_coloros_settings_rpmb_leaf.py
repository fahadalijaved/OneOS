"""Exact cold-start-only UNSELECTED Settings RPMB ingress leaf; no OEM execution."""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
OUT = ROOT / 'out/settings-rpmb-leaf'
RAW = ROOT / 'firmware/settings-rpmb-leaf'
SOURCE = PARENT / 'firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk'
SOURCE_SHA = '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b'
OWNER = 'Lcom/oplus/settings/feature/password/LockSaveAndFinishWorker;'
METHOD = 'lambda$saveAndVerifyInBackground$0(Landroid/content/Intent;)V'
SOURCE_BODY = 'ea03a4aa622889842a00924044e9da47e30644f5b7e9ca16d71b49336250b281'
DEX_NAME = 'classes13.dex'
END = 11
EVIDENCE_RECEIPTS = {
    '20261105T144248156440Z-311e4c429310439e8e1b56b2223cc02c': '7dac95f831e72b411ad6fa5ab530d147365773a8b505ad90a1ec4327c7a15d16',
    '20261105T145645234597Z-146fea5ffec64ea0aeb25318e397da34': 'f614af95ed8464b13c31121fd1372bba95f38c449e5ab8681ec3a13a22274e08',
    '20261105T150230801815Z-49f58f5d50274a02b638f0975c84b3f3': 'e53908cb253fa5ffc5d0e9903a3b83cf10a386139a849cdd56b7909679c5c2e5',
    '20261105T150232168543Z-0b6b6183edc14a84bc2d07d5b04a3e5e': '7d032ec138ff47bc803cb6e85089852ca840455b059a3a45b6ea368c149e0a16',
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def digest(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def u16(b,p):
    if p<0 or p+2>len(b): raise ValueError('u16 bounds')
    return struct.unpack_from('<H',b,p)[0]

def u32(b,p):
    if p<0 or p+4>len(b): raise ValueError('u32 bounds')
    return struct.unpack_from('<I',b,p)[0]

def uleb(b,p):
    v=0
    for i in range(5):
        if p>=len(b): raise ValueError('ULEB bounds')
        x=b[p];p+=1;v|=(x&127)<<(7*i)
        if i==4 and x>15: raise ValueError('ULEB overflow')
        if x<128:return v,p
    raise ValueError('ULEB termination')

def encode_uleb(v):
    out=bytearray()
    while v>=128:out.append((v&127)|128);v>>=7
    out.append(v);return bytes(out)

def header(b):
    if b[:8]!=b'dex\n039\0':raise ValueError('Only admitted ordinary DEX039; no DEX041 fallback')
    if len(b)<112 or u32(b,32)!=len(b) or u32(b,36)!=112 or u32(b,40)!=0x12345678:raise ValueError('DEX extent/header/endian')
    if hashlib.sha1(b[32:]).digest()!=b[12:32] or zlib.adler32(b[12:])&0xffffffff!=u32(b,8):raise ValueError('DEX integrity fields')
    for off,width in ((56,4),(64,4),(72,12),(80,8),(88,8),(96,32)):
        n,p=u32(b,off),u32(b,off+4)
        if n>2000000 or n and (p<112 or p+n*width>len(b)):raise ValueError('DEX table extent')
    if u32(b,108)<112 or u32(b,108)+u32(b,104)!=len(b):raise ValueError('DEX data extent')
    mp=u32(b,52)
    if mp<112 or u32(b,mp)>65535 or mp+4+12*u32(b,mp)>len(b):raise ValueError('DEX map extent')
    return {'version':'039','bytes':len(b),'classes':u32(b,96),'methodIds':u32(b,88)}

def seal(b):
    out=bytearray(b);out[12:32]=hashlib.sha1(out[32:]).digest();struct.pack_into('<I',out,8,zlib.adler32(out[12:])&0xffffffff);return bytes(out)

def locate(b, require_shape=True, require_no_alias=True):
    header(b);strings,types,protos,methodids,classes=(u32(b,o) for o in (60,68,76,92,100))
    def string(idx):
        if idx>=u32(b,56):raise ValueError('String index')
        p=u32(b,strings+4*idx);_,p=uleb(b,p);end=b.find(b'\0',p,min(len(b),p+1048576))
        if end<0:raise ValueError('String terminator')
        return b[p:end]
    def typ(idx):
        if idx>=u32(b,64):raise ValueError('Type index')
        return string(u32(b,types+4*idx))
    def signature(idx):
        owner,proto,name=struct.unpack_from('<HHI',b,methodids+8*idx)
        if proto>=u32(b,72):raise ValueError('Proto index')
        ret,params=u32(b,protos+12*proto+4),u32(b,protos+12*proto+8);args=[]
        if params:
            count=u32(b,params)
            if count>65535 or params+4+2*count>len(b):raise ValueError('Params extent')
            args=[typ(u16(b,params+4+2*i)) for i in range(count)]
        return typ(owner),string(name)+b'('+b''.join(args)+b')'+typ(ret)
    found=[];ranges=[];encoded=0
    for ci in range(u32(b,96)):
        row=classes+32*ci;owner=u32(b,row);p=u32(b,row+24)
        if not p:continue
        counts=[]
        for _ in range(4):n,p=uleb(b,p);counts.append(n)
        if sum(counts)>2000000:raise ValueError('Encoded member bound')
        for count in counts[:2]:
            idx=0
            for _ in range(count):
                delta,p=uleb(b,p);idx+=delta;_,p=uleb(b,p)
                if idx>=u32(b,80):raise ValueError('Field index')
        for count in counts[2:]:
            idx=0
            for _ in range(count):
                delta,p=uleb(b,p);idx+=delta;access,p=uleb(b,p);coff=p;code,p=uleb(b,p);encoded+=1
                if idx>=u32(b,88) or u16(b,methodids+8*idx)!=owner:raise ValueError('Encoded method identity')
                if not code:continue
                if code%4 or code+16>len(b):raise ValueError('Code item extent/alignment')
                units=u32(b,code+12);start=code+16;end=start+2*units
                if units>1000000 or end>len(b):raise ValueError('Instruction extent')
                ranges.append({'methodId':idx,'start':start,'end':end,'codeOffset':code,'codeOffsetField':coff,'codeOffsetFieldEnd':p})
                if typ(owner)==OWNER.encode() and signature(idx)==(OWNER.encode(),METHOD.encode()):
                    found.append({'methodId':idx,'codeOffset':code,'instructionsOffset':start,'instructionUnits':units,'registers':u16(b,code),'incomingWords':u16(b,code+2),'outgoingWords':u16(b,code+4),'tryItems':u16(b,code+6),'debugInfoOffset':u32(b,code+8),'accessFlags':access})
    if len(found)!=1:raise ValueError('Exact target absent/ambiguous')
    f=found[0]
    if require_shape and (f['instructionUnits'],f['registers'],f['tryItems'])!=(52,8,0):raise ValueError('Target code shape changed')
    a,c=f['instructionsOffset'],f['instructionsOffset']+END*2
    aliases=[r for r in ranges if r['methodId']!=f['methodId'] and max(a,r['start'])<min(c,r['end'])]
    if aliases and require_no_alias:raise ValueError('Another method aliases/overlaps patch instructions')
    return f,{'encodedMethods':encoded,'codeBodies':len(ranges),'aliases':len(aliases)},ranges

def boundaries(row, require_hash=True):
    b=row['body'];ins=b['instructions'];bounds={i['pc'] for i in ins};patch=[i for i in ins if i['pc']<END]
    if b['owner']!=OWNER or b['signature']!=METHOD or require_hash and row['normalizedBodySha256']!=SOURCE_BODY:raise ValueError('Exact body identity')
    if sum(i['codeUnits'] for i in patch)!=END or [i['pc'] for i in patch]!=[0,3,5,8] or END not in bounds:raise ValueError('Complete prefix slice')
    if b['catches']:raise ValueError('Unexpected try/handler')
    for i in ins:
        if 'PAYLOAD' in i['opcode']:raise ValueError('Unexpected payload')
        if 'targetPc' in i and (i['targetPc'] not in bounds or i['targetPc']<END):raise ValueError('Branch enters removed prefix or nonboundary')
    if patch[0].get('reference')!=OWNER+'->saveScreenLockInRpmb(Landroid/content/Intent;)V':raise ValueError('Exact optional ingress')
    if patch[2].get('reference')!='string=save_rpmb_success' or patch[3].get('reference')!='Lcom/oplus/settings/utils/LogUtils;->d(Ljava/lang/String;Ljava/lang/String;)V':raise ValueError('Exact associated diagnostic')
    if next(i for i in ins if i['pc']==11).get('reference')!='Lcom/oplus/settings/utils/SysFeatureUtils;->isSupportPasswordRetrieve()Z':raise ValueError('Mixed tail changed')
    if next(i for i in ins if i['pc']==48).get('reference')!=OWNER+'->recordScreenLockPassword()V':raise ValueError('Record tail changed')
    return {'firstPc':0,'endExclusivePc':END,'codeUnits':END,'bytes':2*END,'branchEntriesIntoRemovedPrefix':0,'tryItems':0,'payloads':0}

def tail_register_liveness(body):
    """Prove prefix-defined r0/r7 are overwritten before any unchanged-tail read."""
    instructions={i['pc']:i for i in body['instructions'] if i['pc']>=END}
    pending=[(END,frozenset((0,7)))];seen=set()
    while pending:
        pc,tainted=pending.pop()
        if (pc,tainted) in seen:continue
        seen.add((pc,tainted));i=instructions[pc];op=i['opcode'];regs=i.get('registers',[]);writes=[];reads=[]
        if op.startswith('INVOKE'):
            reads=regs if 'registerStart' not in i else list(range(i['registerStart'],i['registerStart']+i['registerCount']))
        elif op=='MOVE_RESULT':writes=regs
        elif op.startswith('IGET'):writes=regs[:1];reads=regs[1:]
        elif op=='MOVE_OBJECT':writes=regs[:1];reads=regs[1:]
        elif op.startswith('IF_'):reads=regs
        elif op not in ('GOTO','RETURN_VOID'):raise ValueError('Unreviewed tail dataflow opcode '+op)
        if tainted.intersection(reads):raise ValueError('Tail reads removed prefix definition')
        tainted=tainted.difference(writes)
        if op=='RETURN_VOID':continue
        if op=='GOTO':pending.append((i['targetPc'],tainted))
        else:
            pending.append((pc+i['codeUnits'],tainted))
            if op.startswith('IF_'):pending.append((i['targetPc'],tainted))
    return {'removedPrefixWrittenRegisters':[0,7],'tailReadsBeforeOverwrite':0,'reviewedDataflowStates':len(seen)}

def compile_helper():
    from static_security_reader import _classes,_env,JDK,DEXLIB
    shared,pins=_classes();src=ROOT/'tools/SettingsRpmbLeafProof.java';classes=OUT/'classes';classes.mkdir(exist_ok=True)
    cp=str(shared)+os.pathsep+str(DEXLIB)
    r=subprocess.run([str(JDK/'javac.exe'),'-proc:none','-encoding','UTF-8','-source','17','-target','17','-cp',cp,'-d',str(classes),str(src)],capture_output=True,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
    (OUT/'compile.txt').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise ValueError('Static proof helper compilation failed')
    return str(classes)+os.pathsep+cp,{**pins,'tools/static_security_reader.py':digest(ROOT/'tools/static_security_reader.py'),'tools/SettingsRpmbLeafProof.java':digest(src),'compiledHelperSha256':digest(classes/'SettingsRpmbLeafProof.class')}

def java_proof(archive,label,cp,pins):
    from static_security_reader import _env,JDK
    raw=RAW/(label+'-all-method-hashes.jsonl');err=OUT/(label+'-stderr.txt')
    with raw.open('wb') as output,err.open('wb') as errors:
        r=subprocess.run([str(JDK/'java.exe'),'-Xmx2g','-cp',cp,'SettingsRpmbLeafProof',str(archive)],stdout=output,stderr=errors,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    if r.returncode or raw.stat().st_size>256*1024*1024:raise ValueError('Static all-method proof failed: '+label)
    return {'raw':raw.relative_to(ROOT).as_posix(),'rawSha256':digest(raw),'bytes':raw.stat().st_size,'readerExitCode':r.returncode,'tools':pins}

def evidence():
    selected=[];all_rows=[]
    for stamp,pin in EVIDENCE_RECEIPTS.items():
        p=ROOT/'out/tooling'/stamp/'receipt.json'
        if digest(p)!=pin:raise ValueError('Immutable selected receipt drift')
        r=json.loads(p.read_text(encoding='utf-8'))
        if r['archiveSha256']!=SOURCE_SHA or digest(ROOT/r['raw'])!=r['rawSha256'] or r['readerExitCode'] or not r['archiveAndToolPinsVerifiedBeforeAndAfter']:raise ValueError('Original evidence drift')
        rows=[json.loads(l) for l in (ROOT/r['raw']).read_text(encoding='utf-8').splitlines()];all_rows.extend(rows)
        selected.append({'receipt':p.relative_to(ROOT).as_posix(),'receiptSha256':pin,'raw':r['raw'],'rawSha256':r['rawSha256']})
    callers=[v for v in all_rows if v.get('record')=='reference']
    if len(callers)!=1 or callers[0]['caller']!=OWNER+'->'+METHOD or callers[0]['instruction']['pc']!=0:raise ValueError('Exact single direct caller changed')
    row=next(v for v in all_rows if v.get('record')=='method' and v['body']['signature']==METHOD)
    return row,{'immutableReceipts':selected,'directCallerCount':1,'callerScope':'All explicit invocation references in this exact original Settings archive; no reflection/dynamic or other-archive completeness claim'}

def actual_negatives(original,location,ranges,row):
    a=location['instructionsOffset'];results={}
    bad=bytearray(original);struct.pack_into('<h',bad,a+2*16,1-15);bad=seal(bad);header(bad)
    OUT.joinpath('negative-interior-branch.dex').write_bytes(bad)
    # Decode the actual changed IF_EQZ operand from bytes; do not merely mutate JSON.
    if bad[a+2*15]!=0x38:raise ValueError('Unexpected real branch opcode')
    decoded=json.loads(json.dumps(row));next(i for i in decoded['body']['instructions'] if i['pc']==15)['targetPc']=15+struct.unpack_from('<h',bad,a+2*16)[0]
    try:boundaries(decoded,require_hash=False)
    except ValueError:results['actualByteInteriorBranchRejected']=True
    else:raise ValueError('Interior-branch negative accepted')
    bad=bytearray(original);struct.pack_into('<H',bad,location['codeOffset']+6,1);bad=seal(bad);header(bad);OUT.joinpath('negative-try-count.dex').write_bytes(bad)
    try:locate(bad)
    except ValueError as e:
        if 'Target code shape' not in str(e):raise
        results['actualByteUnexpectedTryCountRejected']=True
    else:raise ValueError('Try-count negative accepted')
    encoded=encode_uleb(location['codeOffset']);other=next(v for v in ranges if v['methodId']!=location['methodId'] and v['codeOffsetFieldEnd']-v['codeOffsetField']==len(encoded))
    bad=bytearray(original);bad[other['codeOffsetField']:other['codeOffsetFieldEnd']]=encoded;bad=seal(bad);header(bad);OUT.joinpath('negative-method-alias.dex').write_bytes(bad)
    try:locate(bad)
    except ValueError as e:
        if 'aliases/overlaps' not in str(e):raise
        results['actualByteMethodCodeAliasRejected']=True
    else:raise ValueError('Method-alias negative accepted')
    return results

def main():
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
    source_before=digest(SOURCE)
    if source_before!=SOURCE_SHA:raise ValueError('Exact source archive mismatch')
    producer_before=digest(Path(__file__));helper_before=digest(ROOT/'tools/SettingsRpmbLeafProof.java');row,source_evidence=evidence();boundary=boundaries(row);liveness=tail_register_liveness(row['body'])
    print('Admitted original source and prefix; locating all encoded methods',flush=True)
    with zipfile.ZipFile(SOURCE) as z:
        infos=z.infolist()
        if len(infos)!=10549 or len({i.filename for i in infos})!=len(infos):raise ValueError('Exact ZIP inventory/duplicate admission')
        if sum(i.file_size for i in infos)>384*1024*1024 or any(i.file_size>128*1024*1024 for i in infos):raise ValueError('ZIP expansion bound')
        original=z.read(DEX_NAME);headers={i.filename:header(z.read(i)) for i in infos if i.filename.endswith('.dex')}
        if len(headers)!=14 or sum(v['classes'] for v in headers.values())!=78960:raise ValueError('Exact DEX/class inventory')
    location,ownership,ranges=locate(original);a=location['instructionsOffset'];c=a+END*2
    saved=original[a:c];patched=bytearray(original);patched[a:c]=bytes(c-a);patched=seal(patched);header(patched)
    if patched[:8]!=original[:8] or patched[32:a]!=original[32:a] or patched[c:]!=original[c:] or patched==original:raise ValueError('Outside-cut bytes changed')
    inverse=bytearray(patched);inverse[a:c]=saved;inverse=seal(inverse)
    if inverse!=original:raise ValueError('Exact inverse failed')
    roundtrip=bytearray(inverse);roundtrip[a:c]=bytes(c-a);roundtrip=seal(roundtrip)
    if roundtrip!=patched:raise ValueError('Exact roundtrip failed')
    negative=actual_negatives(original,location,ranges,row)
    patched_path=OUT/'classes13.settings-rpmb-leaf.dex';patched_path.write_bytes(patched)
    inverse_path=OUT/'classes13.inverse.dex';inverse_path.write_bytes(inverse)
    archive=OUT/'Settings.settings-rpmb-leaf.apk';payload_rows=[]
    with zipfile.ZipFile(SOURCE) as source,zipfile.ZipFile(archive,'w') as target:
        target.comment=source.comment
        for i in infos:
            old=source.read(i);new=patched if i.filename==DEX_NAME else old
            target.writestr(i,new);payload_rows.append({'name':i.filename,'sourceSha256':sha(old),'outputSha256':sha(new),'unchanged':old==new})
    payload_path=RAW/'archive-entry-payloads.json';payload_path.write_text(json.dumps(payload_rows,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(archive) as z:
        if z.namelist()!=[i.filename for i in infos] or z.testzip() is not None:raise ValueError('Output ZIP inventory/CRC')
        for p in payload_rows:
            if sha(z.read(p['name']))!=p['outputSha256']:raise ValueError('Output payload differs')
            if p['name'].endswith('.dex'):header(z.read(p['name']))
    cp,pins=compile_helper();print('Running hash-only all-method original proof',flush=True)
    before=java_proof(SOURCE,'original',cp,pins);print('Running hash-only all-method patched proof',flush=True)
    after=java_proof(archive,'patched',cp,pins);changed=[];summary=None;class_rows=0;method_rows=0;source_hash=None;output_hash=None
    from itertools import zip_longest
    with (ROOT/before['raw']).open(encoding='utf-8') as old,(ROOT/after['raw']).open(encoding='utf-8') as new:
        for left,right in zip_longest(old,new):
            if left is None or right is None:raise ValueError('All-method proof row count changed')
            p,q=json.loads(left),json.loads(right)
            if p['record']=='class':class_rows+=1
            if p['record']=='method':method_rows+=1
            if p['record']=='summary':
                summary={'original':p,'patched':q}
                # Replacing four instructions with eleven NOPs changes only this count.
                if {k:v for k,v in p.items() if k!='instructions'}!={k:v for k,v in q.items() if k!='instructions'} or q['instructions']!=p['instructions']+7:raise ValueError('Unexpected all-method summary change')
            elif p!=q:
                if p.get('record')!='method' or {k:v for k,v in p.items() if k!='sha256'}!={k:v for k,v in q.items() if k!='sha256'}:raise ValueError('Declaration/identity changed')
                changed.append(p['owner']+'->'+p['signature']);source_hash=p['sha256'];output_hash=q['sha256']
    if changed!=[OWNER+'->'+METHOD] or source_hash!=SOURCE_BODY or class_rows!=78960 or summary is None:raise ValueError('Unexpected all-method delta')
    # Independently decode the exact output owner, including branch/try metadata.
    from static_security_reader import _classes,_env,JDK,DEXLIB
    shared,_=_classes();decoded_path=RAW/'patched-owner.jsonl';err=OUT/'patched-owner-stderr.txt'
    with decoded_path.open('wb') as output,err.open('wb') as errors:
        r=subprocess.run([str(JDK/'java.exe'),'-Xmx2g','-cp',str(shared)+os.pathsep+str(DEXLIB),'SecurityDexReader',str(archive),OWNER,'-',METHOD],stdout=output,stderr=errors,env=_env(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
    if r.returncode:raise ValueError('Patched owner decode failed')
    decoded=[json.loads(l) for l in decoded_path.read_text(encoding='utf-8').splitlines()]
    newrow=next(v for v in decoded if v['record']=='method');oldbody=row['body'];newbody=newrow['body']
    expected=[{'pc':pc,'opcode':'NOP','codeUnits':1} for pc in range(END)]+[i for i in oldbody['instructions'] if i['pc']>=END]
    if newbody['instructions']!=expected or {k:v for k,v in oldbody.items() if k!='instructions'}!={k:v for k,v in newbody.items() if k!='instructions'} or newrow['normalizedBodySha256']!=output_hash:raise ValueError('Exact decoded tail/try/register proof failed')
    if digest(SOURCE)!=source_before or digest(Path(__file__))!=producer_before or digest(ROOT/'tools/SettingsRpmbLeafProof.java')!=helper_before:raise ValueError('Source/producer/helper changed during build')
    print('All-method and inverse proofs passed',flush=True)
    result={'schema':'coloros-settings-rpmb-leaf/v1','status':'UNSELECTED_COLD_START_PC_ONLY_OPTIONAL_SETTINGS_RPMB_INGRESS_REMOVAL','selected':False,'oemExecuted':False,'phoneActions':False,
            'sourceArchive':str(SOURCE),'sourceArchiveSha256':SOURCE_SHA,'physicalDex':DEX_NAME,'logicalHeaderOffset':0,'owner':OWNER,'method':METHOD,
            'sourceBodySha256':SOURCE_BODY,'patchedBodySha256':output_hash,'boundary':boundary,'tailRegisterLiveness':liveness,'codeLocation':location,'codeOwnership':ownership,
            'patchedDex':patched_path.relative_to(ROOT).as_posix(),'patchedDexSha256':digest(patched_path),'patchedArchive':archive.relative_to(ROOT).as_posix(),'patchedArchiveSha256':digest(archive),
            'inverseDex':inverse_path.relative_to(ROOT).as_posix(),'inverseDexSha256':digest(inverse_path),'sourceDexSha256':sha(original),'sourceEvidence':source_evidence,
            'allMethodProof':{'original':before,'patched':after,'summary':summary,'classDeclarationsEqual':class_rows,'methodDeclarationsEqual':method_rows,'unchangedMethods':method_rows-1,'unchangedCodeBodies':summary['original']['codeBodies']-1,'unchangedNoCodeDeclarations':method_rows-summary['original']['codeBodies'],'changedMethods':changed},
            'archivePayloadProof':{'raw':payload_path.relative_to(ROOT).as_posix(),'rawSha256':digest(payload_path),'entries':len(payload_rows),'unchangedPayloads':sum(p['unchanged'] for p in payload_rows),'changedPayloadNames':[p['name'] for p in payload_rows if not p['unchanged']]},
            'patchedOwnerRead':{'raw':decoded_path.relative_to(ROOT).as_posix(),'rawSha256':digest(decoded_path)},'actualByteNegatives':negative,
            'checks':{'sourceArchiveUnchanged':True,'all14DexIntegrityFieldsValid':True,'exact22BytePrefixNopCut':True,'outsideCutAndDexIntegrityFieldsEqual':True,'allOtherMethodsAndDeclarationsEqual':True,'sameRegistersBranchesTailAndTries':True,'noCodeAliasOverlap':True,'inverseExactOriginalDex':True,'roundtripExactPatchedDex':True,'associatedRpmbSuccessDiagnosticRemoved':True},
            'selectionConditions':['Cold start before this job/challenge/callback chain exists; no live job/callback drain claimed','Original Samsung typed authority and actual caller/user/policy/commit/readback/key/data closure remain mandatory','Optional old-retrieval UI/background and static credential cache are untouched separate admission conditions; no policy-false stub is introduced','Mixed background post, record update, copied Intent and worker/credential retention remain; actual ownership/cleanup requires separate closure','Required set/verify/remove/enrollment and extra-factor/StrongAuth paths are unchanged bytes, not runtime-accepted','Other Settings/SystemUI RPMB/RoR entrypoints and optional capability/UI removal are not closed by this leaf'],
            'limits':['Original donor source profile only; installed OneOS bytes unverified','Static inverse/decoded/alias checks do not prove ART execution or authentication','APK wrapper is reserialized and unsigned/stale-signed; ZIP alignment/signature/install acceptance not claimed','No global feature selection, trustlet/backend replacement or live teardown'],
            'producerSha256':producer_before,'helperSourceSha256':digest(ROOT/'tools/SettingsRpmbLeafProof.java')}
    (OUT/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');(ROOT/'inventory/coloros-settings-rpmb-leaf.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'archiveSha256':result['patchedArchiveSha256'],'dexSha256':result['patchedDexSha256'],'bodySha256':output_hash,'classes':class_rows,'methods':method_rows,'negative':negative}))

if __name__=='__main__':main()
