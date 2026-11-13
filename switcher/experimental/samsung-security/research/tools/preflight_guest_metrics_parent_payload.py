"""Read-only ordinary039 pool/instruction/HAPI preflight; never invokes a writer."""
from pathlib import Path
import bisect, hashlib, json, struct, uuid, zipfile, zlib
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT.parent/'firmware/donor/extracted/system/framework/services.jar'
ARCHIVE_SHA='66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
PINS={'docs/guest-metrics-parent-transport.md':'b46fe4c1f06b0ea96e1dc5fd41a9d18b4d48d9ef9e90e3fc828e56754f72f296','inventory/guest-metrics-parent-transport.json':'c7d0b900ec59e701eac64ba4189d2bc84849d99103142a85894843588d32b09f','docs/guest-metrics-parent-cell.md':'4e793d8b4110bae7df75f9bb4532d47d59ac5f785c294264c64266552258d71f','inventory/guest-metrics-parent-cell.json':'15885b7e0ab51c5024f5447022711d39e727f9a7795833ca2535666420341fc8','inventory/guest-metrics-endpoint.json':'847affee9f18fa16b09c5d064b4bf247c7f70ae76dc797f54048b0e2d766c015'}
DMS='Lcom/android/server/display/DisplayManagerService;'
BINDER=DMS[:-1]+'$BinderService;'
CELL='Lcom/appleexploit/oneos/security/authority/PreparedGuestMetricsParentCell;'
DISPATCH='dispatchOneOsGuestMetricsFromParent(Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z'
FIELD='mOneOsGuestMetricsLifecycle'
METHODS=[DMS+'->'+DISPATCH,CELL+'->captureAfterOnStart(Ljava/lang/Object;Landroid/os/Binder;)'+CELL,CELL+'->onOriginalBootPhaseCompleted(Ljava/lang/Object;I)'+CELL[:-1]+'$PhaseDisposition;',CELL+'->dispatchFromParent(Ljava/lang/Object;Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z']

def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def uleb(d,p):
    value=0
    for i in range(5):
        b=d[p];p+=1;value|=(b&127)<<(7*i)
        if b<128:return value,p
    raise ValueError('Oversized ULEB')

class Dex:
    def __init__(self,d):
        self.d=d;self.u32=lambda p:struct.unpack_from('<I',d,p)[0];self.u16=lambda p:struct.unpack_from('<H',d,p)[0]
        need(d[:8]==b'dex\n039\0' and self.u32(32)==len(d) and self.u32(36)==112 and self.u32(40)==0x12345678,'Only complete ordinary039 input admitted; no slicing/rebase')
        need(hashlib.sha1(d[32:]).digest()==d[12:32] and zlib.adler32(d[12:])&0xffffffff==self.u32(8),'DEX integrity differs')
        self.counts=dict(zip(['strings','types','protos','fields','methods','classes'],[self.u32(p)for p in [56,64,72,80,88,96]]))
        self.strings=[]
        for i in range(self.counts['strings']):
            p=self.u32(self.u32(60)+4*i);_,p=uleb(d,p);end=d.index(0,p)
            # Pool comparison uses raw MUTF8 bytes (ASCII added symbols); no lossy decode.
            self.strings.append(d[p:end])
        self.types=[self.strings[self.u32(self.u32(68)+4*i)].decode('ascii')for i in range(self.counts['types'])]
        self.protos=[]
        for i in range(self.counts['protos']):
            p=self.u32(76)+12*i;params=self.u32(p+8)
            args=[]if not params else[self.types[self.u16(params+4+2*j)]for j in range(self.u32(params))]
            self.protos.append('('+''.join(args)+')'+self.types[self.u32(p+4)])
        self.methods=[]
        for i in range(self.counts['methods']):
            p=self.u32(92)+8*i;self.methods.append(self.types[self.u16(p)]+'->'+self.strings[self.u32(p+4)].decode('utf-8','backslashreplace')+self.protos[self.u16(p+2)])
        self.fields=[]
        for i in range(self.counts['fields']):
            p=self.u32(84)+8*i;self.fields.append(self.types[self.u16(p)]+'->'+self.strings[self.u32(p+4)].decode('utf-8','backslashreplace')+':'+self.types[self.u16(p+2)])
        self.classes=[];self.members=[];self.codes=[]
        for i in range(self.counts['classes']):
            p=self.u32(100)+32*i;name=self.types[self.u32(p)];data=self.u32(p+24);parts=[]
            if data:
                sizes=[]
                for _ in range(4):n,data=uleb(d,data);sizes.append(n)
                for part,n in zip(['staticFields','instanceFields','directMethods','virtualMethods'],sizes):
                    index=0
                    for _ in range(n):
                        delta,data=uleb(d,data);index+=delta;flags,data=uleb(d,data)
                        code=0
                        if part.endswith('Methods'):code,data=uleb(d,data)
                        row={'owner':name,'partition':part,'descriptor':(self.methods if part.endswith('Methods')else self.fields)[index],'accessFlags':flags,'memberIndex':index,'codeOffset':code}
                        parts.append(row);self.members.append(row)
                        if code:self.codes.append(row)
            self.classes.append({'descriptor':name,'classIndex':i,'members':parts})
        mp=self.u32(52);self.map=[]
        for i in range(self.u32(mp)):
            p=mp+4+12*i;self.map.append({'type':self.u16(p),'size':self.u32(p+4),'offset':self.u32(p+8)})

    def hapi(self):
        rows=[r for r in self.map if r['type']==0xf000]
        if not rows:return {'present':False,'memberCount':len(self.members),'newMemberPolicy':'No source hiddenAPI section; do not fabricate a copied Samsung profile'}
        need(len(rows)==1 and rows[0]['size']==1,'Unexpected hiddenAPI map shape')
        start=rows[0]['offset'];length=self.u32(start);need(start+length<=len(self.d)and length>=4+4*len(self.classes),'HiddenAPI extent invalid')
        prefix=4+4*len(self.classes);result=[];explicit=0;extents=[]
        for c in self.classes:
            off=self.u32(start+4+4*c['classIndex']);p=start+off
            if off:need(prefix<=off<length,'HAPI class offset invalid');explicit+=1
            begin=p
            for m in c['members']:
                value=None
                if off:value,p=uleb(self.d,p);need(p<=start+length,'HAPI member outside section')
                result.append({'descriptor':m['descriptor'],'partition':m['partition'],'accessFlags':m['accessFlags'],'raw':value,'classRecordPresent':bool(off)})
            if off:extents.append((begin,p))
        need(all(a[1]<=b[0]for a,b in zip(sorted(extents),sorted(extents)[1:])),'Overlapping HAPI records')
        return {'present':True,'offset':start,'length':length,'sha256':hashlib.sha256(self.d[start:start+length]).hexdigest(),'explicitClasses':explicit,'absentClasses':len(self.classes)-explicit,'memberCount':len(result),'numericPolicyMapSha256':hashlib.sha256(json.dumps(result,separators=(',',':')).encode()).hexdigest(),'classOrderSha256':hashlib.sha256('\n'.join(c['descriptor']for c in self.classes).encode()).hexdigest(),'mapping':'class_defs order, static/instance/direct/virtual encoded member order; raw ULEBs or explicit class absence','newMemberPolicy':'Insertion invalidates whole-section-copy shortcut; preserve original descriptor/partition/presence/numeric flags with explicit reviewed new-member policy and rebuilt offsets'}

    def const_strings(self):
        # Standard039 opcode sizes in 16-bit code units; reserved/quickened opcodes refused.
        widths={}
        for a,b,w in [(0,1,1),(1,2,1),(2,3,2),(3,4,3),(4,5,1),(5,6,2),(6,7,3),(7,8,1),(8,9,2),(9,10,3),(10,19,1),(19,20,2),(20,21,3),(21,23,2),(23,24,3),(24,25,5),(25,27,2),(27,28,3),(28,29,2),(29,31,1),(31,33,2),(33,34,1),(34,36,2),(36,39,3),(39,41,1),(41,42,2),(42,45,3),(45,62,2),(68,110,2),(110,115,3),(116,121,3),(123,144,1),(144,176,2),(176,208,1),(208,227,2),(250,252,4),(252,254,3),(254,256,2)]:
            for op in range(a,b):widths[op]=w
        seen=set();count=0;refs=[];selected_refs=[]
        for m in self.codes:
            p=m['codeOffset']
            if p in seen:continue
            seen.add(p);n=self.u32(p+12);pc=0;base=p+16
            need(base+2*n<=len(self.d),'Code extent invalid')
            while pc<n:
                unit=self.u16(base+2*pc);op=unit&255
                if op==0 and unit:
                    if unit==0x100:w=4+2*self.u16(base+2*pc+2)
                    elif unit==0x200:w=2+4*self.u16(base+2*pc+2)
                    elif unit==0x300:w=4+(self.u16(base+2*pc+2)*self.u32(base+2*pc+4)+1)//2
                    else:raise ValueError('Unknown payload')
                else:
                    need(op in widths,'Unknown/reserved039 opcode '+hex(op));w=widths[op]
                need(pc+w<=n,'Instruction overflow')
                if op==0x1a:
                    idx=self.u16(base+2*pc+2);need(idx<len(self.strings),'String reference outside pool')
                    refs.append({'method':m['descriptor'],'pc':pc,'stringIndex':idx,'literalBytesHex':self.strings[idx].hex()})
                if op in list(range(0x6e,0x73))+list(range(0x74,0x79))and m['owner']in [DMS,BINDER]and m['descriptor'].split('->')[1]in ['onStart()V','onBootPhase(I)V','onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']:
                    selected_refs.append({'method':m['descriptor'],'pc':pc,'reference':self.methods[self.u16(base+2*pc+2)]})
                count+=1;pc+=w
        return refs,count,len(seen),selected_refs

def main():
    before=dict(PINS);before[Path(__file__).relative_to(ROOT).as_posix()]=sha(__file__)
    for name,pin in before.items():need(sha(ROOT/name)==pin,'Frozen input differs '+name)
    need(sha(ARCHIVE)==ARCHIVE_SHA,'Archive differs')
    with zipfile.ZipFile(ARCHIVE)as z:
        names=[n for n in z.namelist()if n.endswith('.dex')];need(len(names)==len(set(names)),'Duplicate DEX names')
        overview=[];selected=None
        for name in names:
            d=z.read(name);x=Dex(d);matches=[c['descriptor']for c in x.classes if c['descriptor']in [DMS,BINDER]]
            overview.append({'entry':name,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'version':'039','logicalHeaderOffset':0,'pools':x.counts,'selectedDefinitions':matches})
            if matches:need(set(matches)=={DMS,BINDER}and selected is None,'Selected definitions split/duplicate');selected=x
    need(selected is not None,'Selected DMS definitions absent');x=selected
    field=DMS+'->'+FIELD+':'+CELL
    need(all(m not in x.methods for m in METHODS)and not any(m['owner']==DMS and (m['descriptor'].split('->')[1].split(':')[0]==FIELD or m['descriptor'].split('->')[1].split('(')[0]=='dispatchOneOsGuestMetricsFromParent')for m in x.members),'Added method/field name already exists')
    added_types=sorted(set([CELL,CELL[:-1]+'$PhaseDisposition;'])-set(x.types))
    added_names=[FIELD,*[m.split('->')[1].split('(')[0]for m in METHODS]]
    # Shorties are required string IDs for new proto IDs, even when all argument types already exist.
    new_protos=sorted(set(m[m.index('('):]for m in METHODS)-set(x.protos))
    def shorty(proto):
        args=proto[1:proto.index(')')];ret=proto[proto.index(')')+1:];out=[];i=0
        while i<len(args):
            c=args[i];out.append('L'if c in '[L'else c)
            if c=='[':
                while args[i]=='[':i+=1
                c=args[i]
            i=args.index(';',i)+1 if c=='L'else i+1
        return ('L'if ret[0]in '[L'else ret[0])+''.join(out)
    additions=sorted(set(s.encode()for s in added_types+added_names+[shorty(p)for p in new_protos])-set(x.strings))
    # DEX string order is UTF16 code units, not byte order; preserve encoded NUL/surrogates.
    keys=[s.replace(b'\xc0\x80',b'\0').decode('utf-8','surrogatepass').encode('utf-16-be','surrogatepass')for s in x.strings]
    need(keys==sorted(keys),'Original DEX string order differs')
    positions=[]
    for s in additions:
        position=bisect.bisect_left(keys,s.decode('ascii').encode('utf-16-be'))
        positions.append({'symbol':s.decode('ascii'),'originalInsertionIndex':position})
    refs,insns,codes,selected_refs=x.const_strings();impacts=[]
    for ref in refs:
        shift=sum(p['originalInsertionIndex']<=ref['stringIndex']for p in positions)
        if ref['stringIndex']+shift>65535:impacts.append(dict(ref,newIndex=ref['stringIndex']+shift,requiredChange='CONST_STRING to CONST_STRING_JUMBO; exact PC/branch/try/debug/inverse mapping required before any writer'))
    hapi=x.hapi()
    hooks=[]
    for m in x.members:
        if(m['owner']==DMS and m['descriptor'].split('->')[1]in ['onStart()V','onBootPhase(I)V'])or(m['owner']==BINDER and m['descriptor'].split('->')[1]=='onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'):
            p=m['codeOffset'];hooks.append(dict(m,registers=x.u16(p),inWords=x.u16(p+2),outWords=x.u16(p+4),tryCount=x.u16(p+6),debugOffset=x.u32(p+8),codeUnits=x.u32(p+12)))
    upstream=json.loads((ROOT/'inventory/guest-metrics-endpoint.json').read_text())['oneos'];sources=[]
    for item in upstream['files']:
        need(sha(ROOT/item['path'])==item['sha256'],'Frozen OneOS source differs')
        before[item['path']]=item['sha256']
        if '/patches/'in item['path']:
            lines=(ROOT/item['path']).read_text().splitlines();sources.append(dict(item,selectedMethodLiteralHits=[{'line':i+1,'text':line[:200]}for i,line in enumerate(lines)if any(s in line for s in ['DisplayManagerService;','DisplayManagerService.smali','DisplayManagerService$BinderService','onStart(','onTransact('])]))
    work=ROOT/'out/guest-metrics-parent-payload-preflight'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex);work.mkdir(parents=True,exist_ok=False)
    raw=ROOT/'firmware/guest-metrics-parent-payload-preflight'/work.name;raw.mkdir(parents=True,exist_ok=False)
    (raw/'const-string-width-impacts.json').write_text(json.dumps(impacts,indent=2)+'\n')
    (raw/'selected-method-references.json').write_text(json.dumps(selected_refs,indent=2)+'\n')
    need(not any('->waitForService('in row['reference']for row in selected_refs),'Selected hooks overlap generic waitForService patch')
    need(sha(ARCHIVE)==ARCHIVE_SHA,'Archive moved')
    for name,pin in before.items():need(sha(ROOT/name)==pin,'Input moved '+name)
    result={'schema':'guest-metrics-parent-payload-preflight/v1','status':'BLOCKED_EXACT_THREE_BODY_CONTRACT_BY_STRING_WIDTH'if impacts else 'PREFLIGHT_ONLY_NO_EMISSION','inputsBeforeAfter':before,'archive':{'path':str(ARCHIVE),'sha256':ARCHIVE_SHA},'dexes':overview,'selectedDex':'classes2.dex','newField':field,'newMethodReferences':METHODS,'missingTypes':added_types,'missingProtos':new_protos,'newStrings':positions,'projectedPools':dict(x.counts,methods=x.counts['methods']+len(METHODS),fields=x.counts['fields']+1,types=x.counts['types']+len(added_types),protos=x.counts['protos']+len(new_protos),strings=x.counts['strings']+len(additions)),'poolLimit':65536,'capacityFitsWithoutSplitting':x.counts['methods']+len(METHODS)<=65536 and x.counts['fields']+1<=65536 and x.counts['types']+len(added_types)<=65536,'addedMembersAbsent':True,'selectedHooks':hooks,'selectedDexMap':x.map,'rawHiddenApi':hapi,'selectedMethodReferenceProof':{'raw':str((raw/'selected-method-references.json').relative_to(ROOT)),'sha256':sha(raw/'selected-method-references.json'),'waitForServiceCalls':0},'instructionScan':{'decodedInstructions':insns,'uniqueCodeItems':codes,'shortConstStringReferences':len(refs),'widthImpactCount':len(impacts),'maxShortStringIndex':max(r['stringIndex']for r in refs),'maxProjectedShortStringIndex':max(r['stringIndex']+sum(p['originalInsertionIndex']<=r['stringIndex']for p in positions)for r in refs),'rawImpactFile':str((raw/'const-string-width-impacts.json').relative_to(ROOT)),'rawImpactSha256':sha(raw/'const-string-width-impacts.json')},'oneosSourcePatchInputs':sources,'oneosCommit':upstream['commit'],'patchersExecuted':False,'installedImageClaim':False,'writerInvoked':False,'oemExecuted':False,'phoneActions':False,'preservationContract':['Exact original constructors and every other class/member/value/annotation/access/debug/raw numeric HAPI entry unchanged','Only onStart/onBootPhase/BinderService.onTransact edits plus private null field/package-private dispatch addition initially proposed','Any pool-driven width impact is additional edit needing explicit approval; cannot hide through normalization','Added members require raw policy descriptor+partition mapping and explicit new-member policy; no whole-section transplant after insertion','Symbolic inverse removes new members/references/hooks, restores all original PC/try/debug and pool-driven forms; compare full original normalized metadata and admitted canonical noedit bytes','Authored helper definitions/loading/defaultOFF and actual OneOS patched inputs remain separate from this original-input preflight']}
    receipt=work/'receipt.json';receipt.write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'inventory/guest-metrics-parent-payload-preflight.json').write_text(json.dumps(dict(result,receipt={'path':str(receipt.relative_to(ROOT)),'sha256':sha(receipt)}),indent=2)+'\n')
    print(json.dumps({'status':result['status'],'receipt':str(receipt.relative_to(ROOT)),'widthImpacts':len(impacts),'projectedPools':result['projectedPools'],'hapi':hapi}))

if __name__=='__main__':main()
