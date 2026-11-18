"""Narrow UserInfo reply-conversion evidence. Static read only; no OEM execution."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parent.parent
INPUTS={
    'samsung-framework':('firmware/samsung/framework.jar','8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
    'coloros-framework':('firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2')}
OWNER='Landroid/content/pm/UserInfo;'
BASE=ROOT/'inventory/security-user-binding.json'
WORK=ROOT/'out/userinfo-adapter'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def capture():
    read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
    WORK.mkdir(parents=True,exist_ok=True)
    save=WORK/'queries.json';queries=json.loads(save.read_text()) if save.exists() else []
    selections=[
        ('android.content.pm.UserInfo',['<clinit>()V','isMainUnlogged()Z','isPrimaryUnlogged()Z']),
        ('android.content.pm.UserInfo$1',None),
        ('android.os.UserManager',['isUserTypeManagedProfile(Ljava/lang/String;)Z']),
        ('android.os.IUserManager$Stub',['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
        ('android.os.Parcel',['readTypedObject(Landroid/os/Parcelable$Creator;)Ljava/lang/Object;',
                              'createTypedArrayList(Landroid/os/Parcelable$Creator;)Ljava/util/ArrayList;',
                              'writeTypedObject(Landroid/os/Parcelable;I)V',
                              'writeTypedList(Ljava/util/List;I)V']),
    ]
    for side,(path,pin) in INPUTS.items():
        for cls,methods in selections:
            if any(q['side']==side and q['class']==cls for q in queries):continue
            r=read(ROOT.parent/path,pin,class_name=cls,methods=methods or (),all_methods=methods is None,stream='userinfo-adapter')
            queries.append({'side':side,'class':cls,'receipt':r['receipt']})
            save.write_text(json.dumps(queries,indent=2)+'\n')
            print(side,cls,r['receipt'],flush=True)


def report():
    base_pin=sha(BASE);base=json.loads(BASE.read_text());rows={};proofs={};receipts={}
    archive_pins={side:sha(ROOT.parent/path) for side,(path,pin) in INPUTS.items()}
    assert all(archive_pins[s]==INPUTS[s][1] for s in INPUTS)
    def load(side,receipt_path,expected_raw=None):
        key=(side,receipt_path)
        if key in receipts:return
        path=ROOT/receipt_path;r=json.loads(path.read_text())
        assert r['readerExitCode']==0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
        assert r['archiveSha256']==INPUTS[side][1]
        assert sha(ROOT/r['raw'])==r['rawSha256']
        if expected_raw is not None:assert r['rawSha256']==expected_raw
        for tool,pin in r['tools'].items():
            target=ROOT.parent/'out/toolchain/jadx-1.5.6/lib/jadx-1.5.6-all.jar' if tool=='parentDexlibSha256' else ROOT/tool
            assert sha(target)==pin
        receipts[key]={'side':side,'receipt':receipt_path,'receiptSha256':sha(path),'raw':r['raw'],'rawSha256':r['rawSha256'],'tools':r['tools']}
        for item in map(json.loads,(ROOT/r['raw']).open(encoding='utf-8')):
            if item['record']!='method':continue
            body=item['body'];method=(side,body['owner'],body['signature'])
            if method in rows:assert rows[method]['normalizedBodySha256']==item['normalizedBodySha256']
            rows[method]=item
    # Reuse the exact already-frozen class bodies and only the three selected proxies.
    for key,proof in base['methodProofs'].items():
        side,method=key.split(':',1)
        if side not in INPUTS:continue
        if method.startswith(OWNER+'->') or method.startswith('Landroid/os/IUserManager$Stub$Proxy;->') and any(m in method for m in ('->getUsers(','->getProfiles(','->getUserInfo(')):
            load(side,proof['receipt'],proof['rawSha256'])
    for q in json.loads((WORK/'queries.json').read_text()):load(q['side'],q['receipt'])
    def get(side,owner,signature):
        row=rows[(side,owner,signature)]
        key=side+':'+owner+'->'+signature
        proofs[key]={'bodySha256':row['normalizedBodySha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset']}
        return row['body']
    layouts={}
    for side in INPUTS:
        writer=get(side,OWNER,'writeToParcel(Landroid/os/Parcel;I)V')
        reader=get(side,OWNER,'<init>(Landroid/os/Parcel;)V')
        writes=[];reads=[];field=None;operation=None
        for i in writer['instructions']:
            if i['opcode'].startswith('IGET') and i.get('reference','').startswith(OWNER+'->'):field=i['reference'].split('->')[1]
            if i.get('reference','').startswith('Landroid/os/Parcel;->write'):
                assert field is not None
                writes.append({'field':field,'write':i['reference'].split('->')[1],'writePc':i['pc']});field=None
        for i in reader['instructions']:
            if i.get('reference','').startswith('Landroid/os/Parcel;->read'):operation=(i['reference'].split('->')[1],i['pc'])
            if i['opcode'].startswith('IPUT') and i.get('reference','').startswith(OWNER+'->'):
                assert operation is not None
                reads.append({'field':i['reference'].split('->')[1],'read':operation[0],'readPc':operation[1]});operation=None
        assert [x['field'] for x in writes]==[x['field'] for x in reads]
        assert not writer['catches'] and not reader['catches']
        assert all('targetPc' not in i for b in (writer,reader) for i in b['instructions'])
        layouts[side]=[{**a,**b,'position':index+1} for index,(a,b) in enumerate(zip(writes,reads))]
    samsung=layouts['samsung-framework'];coloros=layouts['coloros-framework']
    assert len(samsung)==16 and len(coloros)==15
    assert [{k:v for k,v in x.items() if k not in ('writePc','readPc')} for x in samsung[:15]]==[{k:v for k,v in x.items() if k not in ('writePc','readPc')} for x in coloros]
    assert samsung[-1]['field']=='attributes:I' and samsung[-1]['read']=='readInt()I' and samsung[-1]['write']=='writeInt(I)V'
    fields_and_readers={'I':('readInt()I','writeInt(I)V'),'J':('readLong()J','writeLong(J)V'),'Z':('readBoolean()Z','writeBoolean(Z)V'),'Ljava/lang/String;':('readString8()Ljava/lang/String;','writeString8(Ljava/lang/String;)V')}
    for layout in layouts.values():
        for item in layout:assert (item['read'],item['write'])==fields_and_readers[item['field'].split(':',1)[1]]
    creator_links=[];framing=[];cases=[];flags=[]
    for side in INPUTS:
        clinit=get(side,OWNER,'<clinit>()V')
        creator='Landroid/content/pm/UserInfo$1;'
        assert any(i.get('reference')==creator for i in clinit['instructions'])
        typed=get(side,creator,'createFromParcel(Landroid/os/Parcel;)Landroid/content/pm/UserInfo;')
        bridge=get(side,creator,'createFromParcel(Landroid/os/Parcel;)Ljava/lang/Object;')
        delegate=get(side,OWNER,'<init>(Landroid/os/Parcel;Landroid/content/pm/UserInfo-IA;)V')
        assert any(i.get('reference')==OWNER+'-><init>(Landroid/os/Parcel;Landroid/content/pm/UserInfo-IA;)V' for i in typed['instructions'])
        assert any(i.get('reference')==OWNER+'-><init>(Landroid/os/Parcel;)V' for i in delegate['instructions'])
        assert any('->createFromParcel(' in i.get('reference','') for i in bridge['instructions'])
        creator_links.append({'side':side,'creator':creator,'typedConstructor':'<init>(Landroid/os/Parcel;Landroid/content/pm/UserInfo-IA;)V','delegatesTo':'<init>(Landroid/os/Parcel;)V','extraSchemaNegotiation':False})
        for signature in ('readTypedObject(Landroid/os/Parcelable$Creator;)Ljava/lang/Object;','createTypedArrayList(Landroid/os/Parcelable$Creator;)Ljava/util/ArrayList;','writeTypedObject(Landroid/os/Parcelable;I)V','writeTypedList(Ljava/util/List;I)V'):
            body=get(side,'Landroid/os/Parcel;',signature)
            if signature.startswith('readTypedObject'):
                assert body['instructions'][0].get('reference')=='Landroid/os/Parcel;->readInt()I'
                assert any('Parcelable$Creator;->createFromParcel(' in i.get('reference','') for i in body['instructions'])
            if signature.startswith('createTypedArrayList'):
                assert any('->readTypedObject(' in i.get('reference','') for i in body['instructions'])
                assert any(i['opcode']=='IF_GEZ' for i in body['instructions'])
            if signature.startswith('writeTypedList'):
                assert any(i.get('literal')==-1 for i in body['instructions'])
                assert any('->writeTypedObject(' in i.get('reference','') for i in body['instructions'])
            if signature.startswith('writeTypedObject'):
                assert all(any(i.get('literal')==v for i in body['instructions']) for v in (0,1))
                assert any('Parcelable;->writeToParcel(' in i.get('reference','') for i in body['instructions'])
            framing.append({'side':side,'method':signature,'references':[{'pc':i['pc'],'target':i['reference']} for i in body['instructions'] if 'reference' in i],
                            'literals':[{'pc':i['pc'],'value':i['literal']} for i in body['instructions'] if 'literal' in i]})
        stub=get(side,'Landroid/os/IUserManager$Stub;','onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')
        bypc={i['pc']:i for i in stub['instructions']}
        switch=next(i for i in stub['instructions'] if i['opcode'] in ('PACKED_SWITCH','SPARSE_SWITCH'))
        mapping={e['key']:switch['pc']+e['offsetFromReferringSwitchPc'] for e in bypc[switch['targetPc']]['switchElements']}
        for code,signature,write in [(23,'getUsers(Z)Ljava/util/List;','writeTypedList(Ljava/util/List;I)V'),(24,'getProfiles(IZ)Ljava/util/List;','writeTypedList(Ljava/util/List;I)V'),(36,'getUserInfo(I)Landroid/content/pm/UserInfo;','writeTypedObject(Landroid/os/Parcelable;I)V')]:
            case=[];pc=mapping[code]
            for _ in range(30):
                ins=bypc[pc];case.append(ins)
                if ins['opcode'].startswith('GOTO') or ins['opcode'].startswith('RETURN'):break
                pc+=ins['codeUnits']
            assert any(i.get('reference')=='Landroid/os/IUserManager$Stub;->'+signature for i in case)
            assert any(i.get('reference')=='Landroid/os/Parcel;->'+write for i in case)
            assert any('->enforceNoDataAvail()' in i.get('reference','') for i in case)
            assert any('->writeNoException()' in i.get('reference','') for i in case)
            proxy=get(side,'Landroid/os/IUserManager$Stub$Proxy;',signature)
            assert any(i.get('reference')=='string=android.os.IUserManager' for i in proxy['instructions'])
            assert any('->readException()V' in i.get('reference','') for i in proxy['instructions'])
            assert any(i.get('reference')==OWNER+'->CREATOR:Landroid/os/Parcelable$Creator;' for i in proxy['instructions'])
            calls=[i for i in proxy['instructions'] if '->transact(' in i.get('reference','')]
            assert len(calls)==1
            invoke=calls[0];constants={}
            for i in proxy['instructions']:
                if i['pc']>=invoke['pc']:break
                if 'literal' in i and len(i.get('registers',[]))==1:constants[i['registers'][0]]=i['literal']
            assert constants[invoke['registers'][1]]==code and constants[invoke['registers'][4]]==0
            cases.append({'side':side,'code':code,'method':signature,'flags':0,'stubCasePc':mapping[code],
                          'serverReferences':[{'pc':i['pc'],'target':i['reference']} for i in case if 'reference' in i],
                          'proxyReferences':[{'pc':i['pc'],'target':i['reference']} for i in proxy['instructions'] if 'reference' in i]})
        for signature,mask in [('isPrimaryUnlogged()Z',1),('isMainUnlogged()Z',16384),('isFull()Z',1024),('isForTesting()Z',32768)]:
            body=get(side,OWNER,signature)
            assert any(i.get('literal')==mask for i in body['instructions'])
            flags.append({'side':side,'method':signature,'field':'flags:I','mask':mask,'predicate':'(flags & mask) == mask'})
        get(side,OWNER,'isManagedProfile()Z')
        helper=get(side,'Landroid/os/UserManager;','isUserTypeManagedProfile(Ljava/lang/String;)Z')
        assert any(i.get('reference')=='string=android.os.usertype.profile.MANAGED' for i in helper['instructions'])
    samsung_masks={'isSecureFolder()Z':131072,'isSdpNotSupportedSecureFolder()Z':262144,'isVirtualUser()Z':-2147483648}
    for signature,mask in samsung_masks.items():
        body=get('samsung-framework',OWNER,signature);assert any(i.get('literal')==mask for i in body['instructions'])
        flags.append({'side':'samsung-framework','method':signature,'field':'flags:I','maskSigned32':mask,'predicate':'(flags & mask) == mask'})
    locked=get('samsung-framework',OWNER,'isSuperLocked()Z')
    assert all(any(i.get('literal')==n for i in locked['instructions']) for n in (100663296,28,12))
    flags.append({'side':'samsung-framework','method':'isSuperLocked()Z','fields':['flags:I','attributes:I'],
                  'predicate':'(flags & 0x06000000) > 0 ? (attributes & 0x1c) > 0 : (attributes & 0x0c) > 0'})
    assert sha(BASE)==base_pin and all(sha(ROOT.parent/INPUTS[s][0])==pin for s,pin in archive_pins.items())
    result={'schema':'userinfo-adapter-source/v1','status':'SOURCE_SUPPORTED_TYPED_REPLY_CONVERSION_NOT_IMPLEMENTED','baseInventory':BASE.relative_to(ROOT).as_posix(),'baseInventorySha256':base_pin,
            'archivePins':{s:{'path':'../'+INPUTS[s][0],'sha256':pin} for s,pin in archive_pins.items()},
            'layouts':layouts,'commonFieldCount':15,'samsungOnlyWireField':'attributes:I','creatorLinks':creator_links,
            'selectedIUserManagerCases':cases,'parcelFraming':framing,'selectedPredicateSemantics':flags,
            'receipts':list(receipts.values()),'methodProofs':proofs,'sourceAndReaderPinsVerified':True,
            'conversionBoundary':{'authorityRecord':'Preserve all16 Samsung fields, exact nulls/order/bit patterns plus admitted authority generation; never use guest15 projection as policy state',
                                  'guestProjection':'Write exact15 common fields using original String8/boolean/int/long operations and correct typed-object/list markers',
                                  'reverseConversion':'Guest15 does not determine Samsung attributes; refuse unsupported reverse policy conversion rather than defaulting attributes',
                                  'construction':'No additional UserManagerService is needed merely to decode/convert these selected replies; genuine original authority remains required'},
            'remainingPolicyOwners':['One authoritative user/serial/profile registry and current generation','Original caller/user/profile authorization for selected server methods','Samsung flags/attributes/userType evaluation; guest projection is not policy authority','Local UserManagerInternal, SupervisionManagerInternal and credential-sharing policy','Current user/lifecycle/CE state, cache invalidation and transport-death ownership'],
            'limits':['Source methods and derived metadata only; no actual user objects or values read','No OEM/Android/Binder/Parcel code executed','No actual field adapter, ART/parcel execution, native authority or profile acceptance','Unexamined guest flag consumers may need further adaptation; all raw flag/attribute bits remain authoritative'],
            'toolSha256':sha(Path(__file__)),'oemExecuted':False,'phoneActions':False,'privateUserStateRead':False}
    (ROOT/'inventory/userinfo-adapter-source.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'commonFields':15,'samsungFields':16,'newQueries':10,'selectedMethods':len(proofs),'wireCases':len(cases),'oemExecuted':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',action='store_true')
    parser.add_argument('--report',action='store_true')
    args=parser.parse_args()
    if args.capture:capture()
    if args.report:report()


if __name__=='__main__':main()
