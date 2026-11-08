"""Exact selected ColorOS biometric statusbar transport, static source only.

--collect reads named methods. Default validates saved source proofs. No OEM or
Android execution, runtime adapter, Binder publication, or phone operation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
OUT=ROOT/'out/biometric-statusbar-wire'
LEDGER=OUT/'ledger.json'
INPUTS={
 'framework':('firmware/donor/extracted/system/framework/framework.jar','d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
 'services':('firmware/donor/extracted/system/framework/services.jar','66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
 'systemui':('firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk','0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'),
}
OPS=['showAuthenticationDialog','hideAuthenticationDialog','onBiometricAuthenticated','onBiometricHelp','onBiometricError']
QUERIES=[
 ('framework','com.android.internal.statusbar.IStatusBarService$Stub$Proxy',OPS),
 ('framework','com.android.internal.statusbar.IStatusBar$Stub$Proxy',OPS),
 ('framework','com.android.internal.statusbar.IStatusBarService$Stub',['onTransact']),
 ('framework','com.android.internal.statusbar.IStatusBar$Stub',['onTransact']),
 ('services','com.android.server.statusbar.StatusBarManagerService',OPS+['enforceBiometricDialog','enforceValidCallingUser','runWithStatusBarIfPresent']),
 ('systemui','com.android.systemui.statusbar.CommandQueue',OPS),
 ('systemui','com.android.systemui.statusbar.CommandQueue$H',['handleMessage']),
 ('services','com.android.server.statusbar.StatusBarManagerService$$ExternalSyntheticLambda20',['<init>','execute']),
 ('services','com.android.server.statusbar.StatusBarManagerService$$ExternalSyntheticLambda19',['<init>','execute']),
 ('services','com.android.server.statusbar.StatusBarManagerService$$ExternalSyntheticLambda21',['<init>','execute']),
 ('services','com.android.server.statusbar.StatusBarManagerService$$ExternalSyntheticLambda17',['<init>','execute']),
 ('services','com.android.server.statusbar.StatusBarManagerService$$ExternalSyntheticLambda34',['<init>','execute']),
 ('services','com.android.server.statusbar.StatusBarManagerService',['isVisibleBackgroundUser']),
 ('systemui','com.android.systemui.statusbar.CommandQueue',['<init>']),
 ('systemui','com.android.systemui.statusbar.CommandQueue$H',['<init>']),
 ('systemui','com.android.systemui.biometrics.AuthController',['start']),
 ('services','com.android.server.statusbar.StatusBarManagerService',['lambda$showAuthenticationDialog$8','lambda$onBiometricAuthenticated$9','lambda$onBiometricHelp$10','lambda$onBiometricError$11','lambda$hideAuthenticationDialog$12']),
]


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def collect():
    from static_security_reader import read_archive
    ledger=json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    for role,owner,names in QUERIES:
        key={'role':role,'owner':owner,'names':names}
        old=next((r for r in ledger if r['key']==key),None)
        if old:
            if digest(ROOT/old['raw'])!=old['rawSha256']:raise ValueError('Saved raw changed')
            continue
        path,pin=INPUTS[role]
        declaration=read_archive(PARENT/path,pin,class_name=owner,stream='biometric-statusbar-wire')
        classes=declaration['selectedClassDeclarations']
        if len(classes)!=1:raise ValueError('Exact class unavailable '+owner)
        methods=[m['signature'] for m in classes[0]['methods'] if m['signature'].split('(',1)[0] in names]
        if {m.split('(',1)[0] for m in methods}!=set(names):raise ValueError('Selected method absent '+owner)
        result=read_archive(PARENT/path,pin,class_name=owner,methods=methods,stream='biometric-statusbar-wire')
        ledger.append({'key':key,'declaration':declaration,**result})
        LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')


def saved():
    ledger=json.loads(LEDGER.read_text());bodies={};proofs=[]
    expected={(r,o,tuple(n)) for r,o,n in QUERIES}
    actual={(p['key']['role'],p['key']['owner'],tuple(p['key']['names'])) for p in ledger}
    if len(ledger)!=len(expected) or actual!=expected:raise ValueError('Bounded query set changed')
    for p in ledger:
        if digest(ROOT/p['raw'])!=p['rawSha256'] or p['archiveSha256']!=INPUTS[p['key']['role']][1] or p['readerExitCode']!=0:raise ValueError('Saved source proof drift')
        for line in (ROOT/p['raw']).read_text().splitlines():
            row=json.loads(line)
            if row['record']!='method':continue
            b=row['body'];key=p['key']['role']+':'+b['owner']+'->'+b['signature']
            if key in bodies:raise ValueError('Duplicate selected method')
            bodies[key]=b
            proofs.append({'key':key,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'normalizedBodySha256':row['normalizedBodySha256'],'raw':p['raw'],'rawSha256':p['rawSha256'],'receipt':p['receipt']})
    return ledger,bodies,proofs


def one(bodies,selector):
    found=[(k,v) for k,v in bodies.items() if selector in k]
    if len(found)!=1:raise ValueError('Nonunique selected method '+selector)
    return found[0]


def case_instructions(body,code):
    bypc={i['pc']:i for i in body['instructions']}
    found=[]
    for switch in body['instructions']:
        if switch['opcode'] not in ('PACKED_SWITCH','SPARSE_SWITCH'):continue
        elements=bypc[switch['targetPc']].get('switchElements',[])
        for e in elements:
            if e['key']!=code:continue
            start=switch['pc']+e['offsetFromReferringSwitchPc']
            targets=[switch['pc']+x['offsetFromReferringSwitchPc'] for x in elements]
            end=min((p for p in targets if p>start),default=max(bypc)+1)
            found.append((switch['pc'],start,end,[i for i in body['instructions'] if start<=i['pc']<end]))
    if len(found)!=1:raise ValueError('Selected switch case ambiguous/unavailable')
    return found[0]


def proxy_shape(body):
    # Selected generated senders have straight-line setup before transact.
    # Track only constants/moves and invalidate object/result destinations.
    descriptor_text=body['signature'].split('(',1)[1].split(')',1)[0]
    types=[];pos=0
    while pos<len(descriptor_text):
        start=pos
        while descriptor_text[pos]=='[':pos+=1
        pos=descriptor_text.index(';',pos)+1 if descriptor_text[pos]=='L' else pos+1
        types.append(descriptor_text[start:pos])
    widths=[2 if t in ('J','D') else 1 for t in types]
    if body['accessFlags']&8:raise ValueError('Selected proxy is unexpectedly static')
    argument_register=body['registerCount']-sum(widths)
    origins={}
    for index,(kind,width) in enumerate(zip(types,widths)):
        for word in range(width):origins[argument_register+word]={'index':index,'type':kind,'word':word}
        argument_register+=width
    constants={};writes=[];transaction=None;descriptor=None
    for i in body['instructions']:
        op=i['opcode'];r=i.get('registers',[]);ref=i.get('reference','')
        if 'Landroid/os/Parcel;->write' in ref:
            name=ref.split('->',1)[1].split('(',1)[0]
            if name=='writeInterfaceToken':descriptor=constants.get(r[1])
            else:
                row={'pc':i['pc'],'operation':name,'reference':ref,'sourceArgument':origins.get(r[1])}
                if name=='writeLong' and origins.get(r[2])!={**origins.get(r[1],{}),'word':1}:raise ValueError('Long source words no longer pair')
                if name=='writeTypedObject':row['parcelableFlags']=constants.get(r[2])
                writes.append(row)
        if ref=='Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z':
            transaction={'pc':i['pc'],'code':constants.get(r[1]),'flags':constants.get(r[4]),'nullReply':constants.get(r[3])==0}
            break
        if op.startswith('CONST_STRING'):
            constants[r[0]]=ref.removeprefix('string=');origins.pop(r[0],None)
        elif op.startswith('CONST') and 'literal' in i:
            constants[r[0]]=i['literal'];origins.pop(r[0],None)
        elif op.startswith('MOVE') and not op.startswith(('MOVE_RESULT','MOVE_EXCEPTION')):
            origin=origins.get(r[1]);wide_origin=origins.get(r[1]+1)
            val=constants.get(r[1]);constants.pop(r[0],None)
            if val is not None:constants[r[0]]=val
            origins.pop(r[0],None)
            if origin is not None:origins[r[0]]=origin
            if op.startswith('MOVE_WIDE'):
                origins.pop(r[0]+1,None)
                if wide_origin is not None:origins[r[0]+1]=wide_origin
        elif r and op.startswith(('MOVE_RESULT','MOVE_EXCEPTION','IGET','SGET','NEW_','CONST_CLASS')):
            constants.pop(r[0],None);origins.pop(r[0],None)
        if op.startswith(('IF_','GOTO','PACKED_SWITCH','SPARSE_SWITCH')):raise ValueError('Generated proxy setup gained control flow')
    if transaction is None or descriptor is None:raise ValueError('Incomplete selected sender')
    return {'descriptor':descriptor,'writes':writes,**transaction,'readExceptionPCs':[i['pc'] for i in body['instructions'] if 'Parcel;->readException()V' in i.get('reference','')]}


def wire_contracts(bodies):
    expected_writes={
      'showAuthenticationDialog':['writeTypedObject','writeStrongInterface','writeIntArray','writeBoolean','writeBoolean','writeInt','writeLong','writeString','writeLong'],
      'hideAuthenticationDialog':['writeLong'],
      'onBiometricAuthenticated':['writeInt'],
      'onBiometricHelp':['writeInt','writeString'],
      'onBiometricError':['writeInt','writeInt','writeInt'],
    }
    expected_reads={
      'showAuthenticationDialog':['readTypedObject','readStrongBinder','createIntArray','readBoolean','readBoolean','readInt','readLong','readString','readLong'],
      'hideAuthenticationDialog':['readLong'],
      'onBiometricAuthenticated':['readInt'],
      'onBiometricHelp':['readInt','readString'],
      'onBiometricError':['readInt','readInt','readInt'],
    }
    result=[]
    for family,base,flags in [('IStatusBarService',50,0),('IStatusBar',47,1)]:
        stub_key,stub=one(bodies,f'/{family}$Stub;->onTransact(')
        for index,name in enumerate(['showAuthenticationDialog','onBiometricAuthenticated','onBiometricHelp','onBiometricError','hideAuthenticationDialog']):
            proxy_key,proxy=one(bodies,f'/{family}$Stub$Proxy;->{name}(')
            shape=proxy_shape(proxy);code=base+index
            if shape['descriptor']!='com.android.internal.statusbar.'+family or shape['code']!=code or shape['flags']!=flags or shape['nullReply']!=(flags==1):raise ValueError('Selected sender code/descriptor/flags drift')
            if [w['operation'] for w in shape['writes']]!=expected_writes[name]:raise ValueError('Selected sender payload drift')
            if [(w.get('sourceArgument') or {}).get('index') for w in shape['writes']]!=list(range(len(expected_writes[name]))):raise ValueError('Selected sender argument binding drift')
            if any(w.get('parcelableFlags')!=0 for w in shape['writes'] if w['operation']=='writeTypedObject'):raise ValueError('Selected parcelable write flags drift')
            if bool(shape['readExceptionPCs'])!=(flags==0):raise ValueError('Selected sender reply contract drift')
            switch,start,end,arm=case_instructions(stub,code)
            reads=[{'pc':i['pc'],'operation':i['reference'].split('->',1)[1].split('(',1)[0]} for i in arm if i.get('reference','').startswith('Landroid/os/Parcel;->') and any(t in i['reference'] for t in ['->read','->createIntArray'])]
            if [r['operation'] for r in reads]!=expected_reads[name]:raise ValueError('Selected Stub payload drift')
            dispatch=[i for i in arm if f'/{family}$Stub;->{name}(' in i.get('reference','')]
            enforce=[i['pc'] for i in arm if 'Parcel;->enforceNoDataAvail()V' in i.get('reference','')]
            noexception=[i['pc'] for i in arm if 'Parcel;->writeNoException()V' in i.get('reference','')]
            if len(dispatch)!=1 or len(enforce)!=1 or enforce[0]>=dispatch[0]['pc'] or bool(noexception)!=(flags==0):raise ValueError('Selected Stub dispatch/strictness/reply drift')
            result.append({'family':family,'name':name,'proxyMethod':proxy_key,'stubMethod':stub_key,'sender':shape,'stubCase':{'switchPC':switch,'entryPC':start,'endExclusivePC':end,'reads':reads,'enforceNoDataAvailPC':enforce[0],'dispatchPC':dispatch[0]['pc'],'writeNoExceptionPCs':noexception}})
    return result


def source_assertions(bodies):
    rows=[]
    def check(label,selector,pc,opcode,ref=None,**fields):
        key,body=one(bodies,selector);ins=next((i for i in body['instructions'] if i['pc']==pc),None)
        if ins is None or ins['opcode']!=opcode or (ref is not None and ref not in ins.get('reference','')) or any(ins.get(k)!=v for k,v in fields.items()):raise ValueError('Source edge drift '+label)
        rows.append({'id':label,'method':key,'pc':pc,'instruction':ins})
    for op in OPS:
        check(op+'-permission','StatusBarManagerService;->'+op+'(',0,'INVOKE_DIRECT','->enforceBiometricDialog()V')
        check(op+'-calling-user','StatusBarManagerService;->'+op+'(',3,'INVOKE_DIRECT','->enforceValidCallingUser()V')
    check('permission-name','StatusBarManagerService;->enforceBiometricDialog(',2,'CONST_STRING','string=android.permission.MANAGE_BIOMETRIC_DIALOG')
    check('permission-actual-caller','StatusBarManagerService;->enforceBiometricDialog(',6,'INVOKE_VIRTUAL','->enforceCallingOrSelfPermission(')
    check('calling-user-feature-guard','StatusBarManagerService;->enforceValidCallingUser(',2,'IF_NEZ',targetPc=5)
    check('calling-user-native-query','StatusBarManagerService;->enforceValidCallingUser(',5,'INVOKE_STATIC','->getCallingUserId()I')
    check('calling-user-background-rejection','StatusBarManagerService;->enforceValidCallingUser(',20,'IF_NEZ',targetPc=23)
    check('calling-user-real-background-owner','StatusBarManagerService;->isVisibleBackgroundUser(',8,'INVOKE_VIRTUAL','->isVisibleBackgroundFullUser(I)Z')
    check('forwarding-real-bar','StatusBarManagerService;->runWithStatusBarIfPresent(Lcom/android/server/statusbar/StatusBarManagerService$StatusBarAction;Ljava/lang/String;',0,'IGET_OBJECT','->mBar:')
    check('forwarding-no-bar-path','StatusBarManagerService;->runWithStatusBarIfPresent(Lcom/android/server/statusbar/StatusBarManagerService$StatusBarAction;Ljava/lang/String;',2,'IF_EQZ',targetPc=17)
    check('main-looper-source','CommandQueue;-><init>(Landroid/content/Context;Lcom/android/systemui/settings/DisplayTracker;Lcom/android/systemui/statusbar/commandline/',19,'INVOKE_STATIC','->getMainLooper()')
    check('main-looper-handler','CommandQueue$H;-><init>(',2,'INVOKE_DIRECT','Handler;-><init>(Landroid/os/Looper;)V')
    check('original-controller-registration','AuthController;->start(',2,'INVOKE_VIRTUAL','->addCallback(')
    check('controller-start-has-global-write','AuthController;->start(',53,'INVOKE_STATIC','Settings$Global;->putInt(')
    for name,pc,message in [('showAuthenticationDialog',35,2555904),('onBiometricAuthenticated',11,2621440),('onBiometricHelp',13,2686976),('onBiometricError',15,2752512),('hideAuthenticationDialog',11,2818048)]:
        check(name+'-queue-code','CommandQueue;->'+name+'(',pc,'CONST_HIGH16',literal=message)
    check('show-asynchronous-message','CommandQueue;->showAuthenticationDialog(',42,'INVOKE_VIRTUAL','->setAsynchronous(Z)V')
    for label,pc in [('show-removes-error',1600),('show-removes-help',1609),('show-removes-authenticated',1618)]:
        check(label,'CommandQueue$H;->handleMessage(',pc,'INVOKE_VIRTUAL','->removeMessages(I)V')
    for name,message,start,call in [('showAuthenticationDialog',2555904,1594,1688),('onBiometricAuthenticated',2621440,1560,1586),('onBiometricHelp',2686976,1522,1552),('onBiometricError',2752512,1484,1514),('hideAuthenticationDialog',2818048,1450,1476)]:
        key,body=one(bodies,'CommandQueue$H;->handleMessage(')
        switch,actual_start,end,arm=case_instructions(body,message)
        if actual_start!=start:raise ValueError('Selected message dispatch changed')
        check(name+'-original-callback','CommandQueue$H;->handleMessage(',call,'INVOKE_INTERFACE_RANGE' if name=='showAuthenticationDialog' else 'INVOKE_INTERFACE','Callbacks;->'+name+'(')
        rows.append({'id':name+'-message-case','method':key,'message':message,'switchPC':switch,'entryPC':start,'endExclusivePC':end,'callbackPC':call})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.collect:collect()
    for path,pin in INPUTS.values():
        if digest(PARENT/path)!=pin:raise ValueError('Original archive identity changed')
    ledger,bodies,proofs=saved()
    wire=wire_contracts(bodies);checks=source_assertions(bodies)
    report={'schema':'biometric-statusbar-wire-methods/v1','scope':'Selected static source methods only; no adapter/runtime acceptance','inputs':INPUTS,'proofs':proofs,'wireContracts':wire,'sourceAssertions':checks,'toolSha256':digest(__file__),'oemExecuted':False,'androidExecuted':False,'phoneActions':False}
    (OUT/'method-proofs.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'selectedQueries':len(ledger),'selectedMethods':len(bodies),'wireContracts':len(wire),'sourceAssertions':len(checks),'report':'out/biometric-statusbar-wire/method-proofs.json'}))


if __name__=='__main__':main()
