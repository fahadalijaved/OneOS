"""Finite static native/body proof for one compositor alternative; no OEM execution.

--collect-native disassembles only named existing ARM64 functions. Default
rechecks frozen own receipts; neither mode invokes Binder/display/input APIs.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re
import runpy
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/retained-single-compositor-proof'
RAW = ROOT / 'firmware/retained-single-compositor-proof'
PARSER = ROOT / 'tools/audit_security_native_linkage.py'
PARSER_SHA = '33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'
NATIVE = {
 'input-jni':('firmware/security-native/samsung/system/lib64/libandroid_servers.so',
     '9482076b93ae97db3cb0e4a2c6e45b93c6dc6fd7d264afe2df7e8bdd25d80a16',[
     '_ZN7android18NativeInputManager20setInputDispatchModeEbb',
     '_ZN7androidL26nativeSetInputDispatchModeEP7_JNIEnvP8_jobjecthh']),
 'input-dispatcher':('firmware/retained-single-compositor-proof/libinputflinger.so',
     'ef0f189682af4691e10ccd3b06730b23becc14a20a7923a996cb35d9e9d51c76',[
     '_ZN7android15inputdispatcher15InputDispatcher20setInputDispatchModeEbb',
     '_ZN7android15inputdispatcher15InputDispatcher28resetAndDropEverythingLockedEPKc']),
 'samsung-gui':('../firmware/samsung/runtime-20261104/libgui.so',
     '3f241a05183cbced5d82a05b162d02ef6b90a0f81b970b22711ebf0293a43443',[
     '_ZN7android17BpSurfaceComposer19setTransactionStateEONS_16TransactionStateERKNS_2spINS_7IBinderEEE',
     '_ZNK7android16TransactionState13writeToParcelEPNS_6ParcelE',
     '_ZNK7android13layer_state_t5writeERNS_6ParcelE',
     '_ZN7android16TransactionState14readFromParcelEPKNS_6ParcelE',
     '_ZN7android13layer_state_t4readERKNS_6ParcelE',
     '_ZN7android17BnSurfaceComposer10onTransactEjRKNS_6ParcelEPS1_j']),
 'coloros-gui':('../firmware/donor/extracted/system/lib64/libgui.so',
     'b99957d724a1364c7d52727c61c0d76372eb0e083ebbe243272c1a9e66e0e765',[
     '_ZN7android17BpSurfaceComposer19setTransactionStateEONS_16TransactionStateERKNS_2spINS_7IBinderEEE',
     '_ZNK7android16TransactionState13writeToParcelEPNS_6ParcelE',
     '_ZNK7android13layer_state_t5writeERNS_6ParcelE',
     '_ZNK7android19oplus_layer_state_t5writeERNS_6ParcelE']),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def require(condition,message):
    if not condition:
        raise ValueError(message)


def collect_native():
    require(sha(PARSER)==PARSER_SHA,'existing bounded ELF parser changed')
    elf=runpy.run_path(str(PARSER))['elf']
    sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'))
    import capstone
    cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
    result={}
    for label,(relative,pin,wanted) in NATIVE.items():
        path=ROOT/relative
        require(sha(path)==pin,'literal native source changed')
        data=path.read_bytes();parsed=elf(data)
        require(parsed['machine']==183,'ARM64 source required')
        sections=parsed['sections'];symbols=list(parsed['dynamicSymbols'])
        debug=next((s for s in sections if s['name']=='.gnu_debugdata'),None)
        if debug:
            mini=lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']],memlimit=64*1024*1024)
            require(len(mini)<=16*1024*1024,'mini debug bound exceeded')
            symbols+=elf(mini)['dynamicSymbols']
        def offset(address,length):
            matches=[s for s in sections if s['type']!=8 and s['address']<=address
                     and address+length<=s['address']+s['bytes']]
            require(len(matches)==1,'exact mapped native span required')
            return matches[0]['offset']+address-matches[0]['address']
        by_address={s['value']:s['name'] for s in symbols if s['sectionIndex'] and s['type']==2}
        plt=next((s for s in sections if s['name']=='.plt'),None)
        slots={r['target']:r for r in parsed['rela'] if r['type']==1026}
        def resolve(address):
            if address in by_address:return by_address[address]
            if plt and plt['address']<=address<plt['address']+plt['bytes']:
                off=offset(address,24);stub=list(cs.disasm(data[off:off+24],address))
                adrp=next((i for i in stub if i.mnemonic=='adrp' and i.op_str.startswith('x16,')),None)
                load=next((i for i in stub if i.mnemonic=='ldr' and i.op_str.startswith('x17,')),None)
                if adrp and load:
                    displacement=re.search(r'#(0x[0-9a-f]+|\d+)',load.op_str)
                    target=int(adrp.op_str.split('#')[1],0)+(int(displacement.group(1),0) if displacement else 0)
                    slot=slots.get(target)
                    if slot:return parsed['dynamicSymbols'][slot['symbolIndex']]['name']
            return None
        functions=[]
        for name in wanted:
            matches={s['value']:s for s in symbols if s['name']==name and s['sectionIndex']
                     and s['type']==2 and s['size']}
            require(len(matches)==1,'unique exact bounded function required '+name)
            sym=next(iter(matches.values()));require(sym['size']<=16384,'function scope exceeds16KiB')
            off=offset(sym['value'],sym['size']);code=data[off:off+sym['size']];instructions=[]
            for ins in cs.disasm(code,sym['value']):
                row={'pc':ins.address,'mnemonic':ins.mnemonic,'operands':ins.op_str}
                if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
                    target=int(ins.op_str[1:],0);row.update(target=target,symbol=resolve(target))
                instructions.append(row)
            require(instructions and instructions[-1]['pc']+4==sym['value']+sym['size'],'complete fixed-width disassembly required')
            functions.append({'symbol':name,'address':sym['value'],'bytes':sym['size'],
                 'bodySha256':hashlib.sha256(code).hexdigest(),'instructions':instructions})
        require(sha(path)==pin,'native input changed during static read')
        result[label]={'path':relative,'sha256':pin,'functions':functions}
    RAW.mkdir(parents=True,exist_ok=True);p=RAW/'selected-native.json'
    p.write_text(json.dumps(result,indent=2)+'\n')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'native-receipt.json').write_text(json.dumps({'schema':'single-compositor-native-source/v1',
        'raw':p.relative_to(ROOT).as_posix(),'rawSha256':sha(p),'parserSha256':PARSER_SHA,
        'nativeInputs':{k:{'path':v[0],'sha256':v[1]} for k,v in NATIVE.items()},
        'namedFunctionCount':sum(len(v['functions']) for v in result.values()),'oemExecuted':False},indent=2)+'\n')
    print(json.dumps({'pass':True,'raw':p.relative_to(ROOT).as_posix(),'functions':sum(len(v['functions']) for v in result.values()),'oemExecuted':False}))


def inspect():
    receipt=json.loads((OUT/'native-receipt.json').read_text())
    require(sha(ROOT/receipt['raw'])==receipt['rawSha256'],'selected native receipt drift')
    require(sha(PARSER)==PARSER_SHA,'parser pin drift')
    for label,(relative,pin,wanted) in NATIVE.items():
        require(sha(ROOT/relative)==pin,'pinned native source drift')
    native=json.loads((ROOT/receipt['raw']).read_text())
    assertions=[]
    def at(label,index,pc,field,expected):
        fn=native[label]['functions'][index]
        row=next(i for i in fn['instructions'] if i['pc']==pc)
        require(row.get(field)==expected,'native assertion drift '+hex(pc))
        assertions.append({'kind':'native','input':label,'symbol':fn['symbol'],
                           'pc':hex(pc),'field':field,'expected':expected})
    at('samsung-gui',0,0x12477c,'operands','w1, #8')
    at('samsung-gui',0,0x12478c,'operands','w4, #1')
    at('coloros-gui',0,0x153d94,'operands','w1, #8')
    at('coloros-gui',0,0x153da4,'operands','w4, #1')
    at('samsung-gui',5,0x11c4b4,'operands','w1, #8')
    at('samsung-gui',5,0x11c4b8,'operands','#0x11ce64')
    at('samsung-gui',5,0x11c534,'symbol','_ZN7android16TransactionState14readFromParcelEPKNS_6ParcelE')
    at('samsung-gui',3,0xe160c,'symbol','_ZN7android13layer_state_t4readERKNS_6ParcelE')
    at('samsung-gui',4,0x176098,'symbol','_ZNK7android6Parcel9readInt32Ev')
    at('samsung-gui',4,0x17609c,'operands','w0, #0x176334')
    at('samsung-gui',4,0x1760a8,'symbol','_ZNK7android6Parcel15readFloatVectorEPNSt3__16vectorIfNS1_9allocatorIfEEEE')
    for pc in [0x1760b8+i*16 for i in range(6)]+[0x176128+i*16 for i in range(10)]:
        at('samsung-gui',4,pc,'symbol','_ZNK7android6Parcel9readFloatEPf')
    at('samsung-gui',4,0x176118,'symbol','_ZNK7android6Parcel8readBoolEPb')
    at('samsung-gui',4,0x1761cc,'symbol','_ZNK7android6Parcel9readInt32EPi')
    at('samsung-gui',2,0x1253b4,'symbol','_ZN7android6Parcel16writeFloatVectorERKNSt3__16vectorIfNS1_9allocatorIfEEEE')
    at('coloros-gui',2,0x154a50,'symbol','_ZN7android6Parcel10writeInt32Ei')
    at('coloros-gui',2,0x154a58,'symbol','_ZNK7android6Region16getFlattenedSizeEv')
    at('coloros-gui',2,0x154a70,'symbol','_ZN7android6Parcel10writeInt32Ei')
    at('input-dispatcher',0,0x422460,'symbol','_ZN7android15inputdispatcher15InputDispatcher28resetAndDropEverythingLockedEPKc')
    at('input-dispatcher',1,0x4225cc,'symbol','_ZN7android15inputdispatcher15InputDispatcher51synthesizeCancellationEventsForAllConnectionsLockedEONS0_19CancellationOptionsE')
    at('input-dispatcher',1,0x42261c,'symbol','_ZN7android15inputdispatcher15InputDispatcher23drainInboundQueueLockedEv')
    java={};java_inputs=[]
    for name in ['wms','ims','display','container','transaction','apply']:
        path=OUT/(name+'.json');proof=json.loads(path.read_text())
        require(sha(ROOT/proof['raw'])==proof['rawSha256'],'java raw drift')
        require(sha(proof['archive'])==proof['archiveSha256'],'java source archive drift')
        rows=[json.loads(line) for line in (ROOT/proof['raw']).read_text().splitlines()]
        for row in rows:
            if row.get('record')=='method':
                body=row['body'];java[(body['owner'],body['signature'])]=body
        java_inputs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),
                           'raw':proof['raw'],'rawSha256':proof['rawSha256'],
                           'methods':proof['selectedMethodProofs']})
    def jat(owner,method,pc,field,expected):
        row=next(i for i in java[(owner,method)]['instructions'] if i['pc']==pc)
        require(row.get(field)==expected,'DEX assertion drift '+method+':'+str(pc))
        assertions.append({'kind':'dex','owner':owner,'method':method,'pc':pc,
                           'field':field,'expected':expected})
    wm='Lcom/android/server/wm/WindowManagerService;';dc='Lcom/android/server/wm/DisplayContent;'
    tx='Landroid/view/SurfaceControl$Transaction;'
    for pc,field,value in [(0,'reference','string=android.permission.MANAGE_APP_TOKENS'),
             (27,'reference',wm+'->mDisplayEnabled:Z'),(29,'targetPc',50),
             (37,'registers',[4,3]),(43,'literal',0),(44,'registers',[3,4,1])]:
        jat(wm,'setEventDispatching(Z)V',pc,field,value)
    for pc,ref in [(113,tx+'->addWindowInfosReportedListener(Ljava/lang/Runnable;)'+tx),
                   (117,tx+'->apply()V'),
                   (180,'Ljava/util/concurrent/CountDownLatch;->await(JLjava/util/concurrent/TimeUnit;)Z')]:
        jat(wm,'syncInputTransactions(IZ)V',pc,'reference',ref)
    jat(wm,'syncInputTransactions(IZ)V',183,'opcode','INVOKE_STATIC')
    for pc,ref in [(33,'Lcom/android/server/wm/WindowContainer;->mSurfaceControl:Landroid/view/SurfaceControl;'),
                   (338,tx+'->setLayerStack(Landroid/view/SurfaceControl;I)'+tx),
                   (344,tx+'->show(Landroid/view/SurfaceControl;)'+tx)]:
        jat(dc,'configureSurfaces('+tx+')V',pc,'reference',ref)
    jat(tx,'hide(Landroid/view/SurfaceControl;)'+tx,57,'literal',1)
    jat(tx,'show(Landroid/view/SurfaceControl;)'+tx,58,'literal',0)
    jat(tx,'apply(ZZ)V',114,'reference','Landroid/view/SurfaceControl;->-$$Nest$smnativeApplyTransaction(JZZ)V')
    report={'schema':'retained-single-compositor-checks/v1','pass':True,
       'javaInputs':java_inputs,'nativeReceiptSha256':sha(OUT/'native-receipt.json'),
       'assertions':assertions,'oemExecuted':False,'binderOrDisplayInputCalls':False}
    (OUT/'source-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pass':True,'savedNativeFunctions':receipt['namedFunctionCount'],
       'savedJavaMethods':len(java),'assertions':len(assertions),
       'oemExecuted':False,'binderOrDisplayInputCalls':False}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect-native',action='store_true')
    args=parser.parse_args()
    collect_native() if args.collect_native else inspect()
