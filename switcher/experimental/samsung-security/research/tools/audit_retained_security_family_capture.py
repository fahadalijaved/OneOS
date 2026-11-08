"""Verify finite ORIGINAL Samsung retained-family source proofs; never run OEM code.

Default is a saved-proof recheck, writing only bounded derived metadata. It does
not construct/capture/query an Android object or claim a runtime source issuer.
"""
import gzip
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/retained-security-family-capture'
SERVICES = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
FRAMEWORK = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
DECL = ROOT.parent / ('out/os-comparison-resumed/archive-index/indexes/' + SERVICES + '/declarations.jsonl.gz')
DECL_HASH = '60b1d4eca9f3601d62eb127e55191cc01239a75cab27164cc1f0a846888ede5f'
INPUT_HASH = '344686a694248c1fcc9f1873b7764dbaaa2ccc287a5b62b9bfa8b192108e0183'
S = 'Lcom/android/server/'
LSS = S+'locksettings/LockSettingsService;'
SPM = S+'locksettings/SyntheticPasswordManager;'
STORE = S+'locksettings/LockSettingsStorage;'
STRONG = S+'locksettings/LockSettingsStrongAuth;'
LIFE = S+'locksettings/LockSettingsService$Lifecycle;'
SMS = S+'StorageManagerService;'
SMI = S+'StorageManagerService$StorageManagerInternalImpl;'
FP = S+'biometrics/sensors/fingerprint/FingerprintService;'
FPW = S+'biometrics/sensors/fingerprint/FingerprintService$1;'
REG = S+'biometrics/sensors/fingerprint/FingerprintServiceRegistry;'
BIO = S+'biometrics/BiometricService;'
BW = S+'biometrics/BiometricService$BiometricServiceWrapper;'
AUTH = S+'biometrics/AuthService;'
AW = S+'biometrics/AuthService$AuthServiceImpl;'
SSM = S+'SystemServiceManager;'
CONTEXT = 'Landroid/content/Context;'
# Exact access preparation is exceptional only for these individually named
# fields. Public fields on a package-private declaring class also need access.
FIELDS = [
 (SSM,'mServices','Ljava/util/List;',1,False),
 (SSM,'mCurrentPhase','I',1,False),
 (LIFE,'mLockSettingsService',LSS,1,False),
 (S+'StorageManagerService$Lifecycle;','mStorageManagerService',SMS,1,False),
 (LSS,'mStrongAuth',STRONG,17,False),
 (LSS,'mStrongAuthTracker',S+'locksettings/LockSettingsService$SynchronizedStrongAuthTracker;',17,False),
 (LSS,'mSpManager',SPM,17,False),
 (LSS,'mStorage',STORE,20,True),
 (LSS,'mStorageManager','Landroid/os/storage/IStorageManager;',17,False),
 (LSS,'mStorageManagerInternal',SMI,17,False),
 (LSS,'mContext',CONTEXT,17,False),
 (LSS,'mUserCreationAndRemovalLock','Ljava/lang/Object;',17,False),
 (LSS,'mThirdPartyAppsStarted','Z',1,False),
 (LSS,'mEarlyCreatedUsers','Landroid/util/SparseIntArray;',1,False),
 (LSS,'mEarlyRemovedUsers','Landroid/util/SparseIntArray;',1,False),
 (SPM,'mStorage',STORE,1,True),
 (SPM,'mContext',CONTEXT,1,True),
 (STORE,'mContext',CONTEXT,1,False),
 (STRONG,'mContext',CONTEXT,17,False),
 (SMI,'this$0',SMS,4097,False),
 (SMS,'mStorageManagerInternal',SMI,1,False),
 (FP,'mServiceWrapper','Landroid/hardware/fingerprint/IFingerprintService$Stub;',16,True),
 (FP,'mRegistry',REG,17,False),
 (FPW,'this$0',FP,4113,False),
 (REG,'mService',FPW,1,False),
 (BIO,'mImpl','Landroid/hardware/biometrics/IBiometricService$Stub;',16,True),
 (BW,'this$0',BIO,4113,False),
 (AUTH,'mImpl','Landroid/hardware/biometrics/IAuthService$Stub;',16,True),
 (AUTH,'mBiometricService','Landroid/hardware/biometrics/IBiometricService;',1,False),
 (AW,'this$0',AUTH,4113,False),
]


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def inspect():
    require(digest(DECL)==DECL_HASH,'original declaration index drift')
    physical=set()
    for path,pin in [(ROOT.parent/'firmware/samsung/runtime-20261104/services.jar',SERVICES),
                     (ROOT.parent/'firmware/samsung/framework.jar',FRAMEWORK)]:
        require(digest(path)==pin,'literal original archive drift')
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if re.fullmatch(r'classes[0-9]*\.dex',name):
                    physical.add(hashlib.sha256(archive.read(name)).hexdigest())
    manifest=OUT/'proof-inputs.json'
    require(digest(manifest)==INPUT_HASH,'finite proof input manifest drift')
    inputs=json.loads(manifest.read_text())
    for path,pin in inputs['dependencies'].items():
        require(digest(ROOT/path)==pin,'frozen source dependency drift')
    classes={}
    wanted={f[0] for f in FIELDS}
    with gzip.open(DECL,'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('descriptor') in wanted:
                require(row['descriptor'] not in classes,'duplicate selected declaration')
                classes[row['descriptor']]=row
    fields=[]
    for owner,name,kind,flags,access in FIELDS:
        cls=classes[owner]
        found=[f for f in cls['fields'] if f['name']==name]
        require(len(found)==1 and found[0]['descriptor']==kind and found[0]['accessFlags']==flags,
                'exact field declaration drift '+owner+' '+name)
        fields.append({'owner':owner,'declaringClassFlags':cls['accessFlags'],'field':name,
                       'descriptor':kind,'accessFlags':flags,'prepareExactReadAccess':access,
                       'physicalDex':cls['physicalDex'],'logicalHeaderOffset':cls['logicalHeaderOffset']})
    require(classes[SPM]['accessFlags']==0,'SPM must remain package-private')
    require(classes[SMS]['superclass']=='Landroid/os/storage/IStorageManager$Stub;', 'SMS Binder ancestry drift')
    methods={};proofs=[]
    def load(raw,pin):
        require(digest(ROOT/raw)==pin,'raw proof drift')
        rows=[json.loads(line) for line in (ROOT/raw).read_text().splitlines()]
        dex=[r for r in rows if r['record']=='dex']
        require(dex and all(r['physicalDexSha256'] in physical for r in dex),
                'raw DEX identity outside literal original inputs')
        return rows
    for path,pin in inputs['newReceipts'].items():
        require(digest(ROOT/path)==pin,'selected receipt drift')
        receipt=json.loads((ROOT/path).read_text())
        require(receipt['archiveSha256'] in [SERVICES,FRAMEWORK] and receipt['readerExitCode']==0,
                'original source identity/completion differs')
        for line,row in enumerate(load(receipt['raw'],receipt['rawSha256']),1):
            if row['record']!='method':continue
            body=row['body'];key=body['owner']+'->'+body['signature']
            methods[key]=body
            proofs.append({'key':key,'raw':receipt['raw'],'rawSha256':receipt['rawSha256'],
                           'rawLine':line,'normalizedBodySha256':row['normalizedBodySha256'],
                           'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],
                           'receipt':path,'receiptSha256':pin,'reused':False})
    for proof in inputs['reused']:
        if 'receipt' in proof:
            require(digest(ROOT/proof['receipt'])==proof['receiptSha256'],'reused receipt drift')
            receipt=json.loads((ROOT/proof['receipt']).read_text())
            require(receipt['archiveSha256']==SERVICES and receipt['readerExitCode']==0,
                    'reused original source identity/completion differs')
        rows=load(proof['raw'],proof['rawSha256'])
        matches=[r for r in rows if r['record']=='method' and r['body']['owner']+'->'+r['body']['signature']==proof['key']]
        require(len(matches)==1 and matches[0]['normalizedBodySha256']==proof['normalizedBodySha256'],
                'selected reused method drift')
        methods[proof['key']]=matches[0]['body'];proofs.append(dict(proof,reused=True))
    legacy={}
    for key,proof in inputs['legacy'].items():
        text=(ROOT/proof['raw']).read_text();sig=key.split('->',1)[1]
        matches=[s for s in re.split(r'(?m)^METHOD ',text)[1:] if s.startswith(sig+' FLAGS ')]
        require(len(matches)==1,'selected legacy method missing/duplicate')
        lines='\n'.join(s for s in matches[0].splitlines()[1:] if re.match(r'^[0-9a-f]{4} ',s))
        require(hashlib.sha256(lines.encode()).hexdigest()==proof['sha256'],'legacy selected instruction identity drift')
        legacy[key]=lines
        proofs.append({'key':key,'raw':proof['raw'],'rawSha256':digest(ROOT/proof['raw']),
                       'instructionTextSha256':proof['sha256'],'reused':True})
    assertions=[]
    def at(key,pc,**expected):
        ins=[i for i in methods[key]['instructions'] if i['pc']==pc]
        require(len(ins)==1 and all(ins[0].get(k)==v for k,v in expected.items()),'source assertion drift '+key+' '+str(pc))
        assertions.append({'method':key,'pc':pc,'expected':expected,'pass':True})
    def ref(owner,sig,pc,value):at(owner+'->'+sig,pc,reference=value)
    start='startService(Lcom/android/server/SystemService;)V'
    ref(SSM,start,37,'Ljava/util/List;->add(Ljava/lang/Object;)Z')
    ref(SSM,start,44,S+'SystemService;->onStart()V')
    phase='startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V'
    ref(SSM,phase,7,SSM+'->mCurrentPhase:I')
    ref(SSM,phase,177,S+'SystemService;->onBootPhase(I)V')
    ref(SSM,'<init>(Landroid/content/Context;)V',20,SSM+'->mServices:Ljava/util/List;')
    ref(LIFE,'onStart()V',16,LSS+'-><init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V')
    ref(LIFE,'onStart()V',19,LIFE+'->mLockSettingsService:'+LSS)
    ref(LIFE,'onStart()V',24,S+'SystemService;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    ref(LIFE,'onBootPhase(I)V',32,SPM+'->getWeaverService()Landroid/hardware/weaver/IWeaver;')
    ref(LIFE,'onBootPhase(I)V',137,'Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z')
    ctor='<init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V'
    for pc,name,kind in [(438,'mStrongAuth',STRONG),(597,'mStorage',STORE),(641,'mStorageManager','Landroid/os/storage/IStorageManager;'),(651,'mStorageManagerInternal',SMI),(670,'mStrongAuthTracker',S+'locksettings/LockSettingsService$SynchronizedStrongAuthTracker;'),(755,'mSpManager',SPM)]:
        ref(LSS,ctor,pc,LSS+'->'+name+':'+kind)
    ref(LSS,ctor,744,SPM+'->mStorage:'+STORE)
    ref(LSS,ctor,1019,S+'locksettings/LockSettingsService$LocalService;->this$0:'+LSS)
    ref(LSS,ctor,1024,S+'LocalServices;->addService(Ljava/lang/Class;Ljava/lang/Object;)V')
    sms_start=S+'StorageManagerService$Lifecycle;->onStart()V'
    at(sms_start,533,opcode='CONST_CLASS',registers=[1],reference=SMI)
    at(sms_start,535,opcode='IGET_OBJECT',registers=[2,0],reference=SMS+'->mStorageManagerInternal:'+SMI)
    at(sms_start,537,opcode='INVOKE_STATIC',registers=[1,2],reference=S+'LocalServices;->addService(Ljava/lang/Class;Ljava/lang/Object;)V')
    # Exact operand lineage, not a reference/name-only constructor assumption.
    init=LSS+'->'+ctor
    for pc,regs in [(156,[4,1]),(158,[4,0]),(428,[6,1]),(435,[2,6,7]),
                    (438,[2,0]),(529,[4]),(531,[5,1]),(571,[5,4]),(597,[4,0]),
                    (628,[5]),(631,[5]),(634,[5]),(637,[5]),(641,[5,0]),
                    (643,[5]),(645,[5]),(648,[5]),(649,[5]),(651,[5,0]),
                    (693,[2]),(695,[5,1]),(742,[5,2]),(744,[4,2]),(755,[2,0])]:
        at(init,pc,registers=regs)
    at(init,643,reference=SMI)
    at(init,632,opcode='IF_EQZ',targetPc=639)
    at(init,638,opcode='GOTO',targetPc=641)
    at(init,529,opcode='NEW_INSTANCE',reference=STORE)
    at(init,693,opcode='NEW_INSTANCE',reference=SPM)
    at(STRONG+'-><init>(Landroid/content/Context;Lcom/android/server/locksettings/LockSettingsStrongAuth$Injector;)V',
       56,registers=[3,2],reference=STRONG+'->mContext:'+CONTEXT)
    def stable_register(key,lo,hi,reg):
        # Only these finite selected straight/control-flow spans are inspected.
        # Refuse an unclassified opcode rather than infer general DEX semantics.
        no_def=('INVOKE','IPUT','SPUT','APUT','IF_','GOTO','MONITOR','RETURN','THROW',
                'FILLED_NEW_ARRAY','FILL_ARRAY_DATA','NOP')
        dest=('MOVE','CONST','NEW_','IGET','SGET','AGET','CHECK_CAST','INSTANCE_OF',
              'ARRAY_LENGTH','ADD','SUB','MUL','DIV','REM','AND','OR','XOR','SHL','SHR','USHR','CMP')
        body=methods[key];by_pc={i['pc']:i for i in body['instructions']};edges={}
        require(lo in by_pc and hi in by_pc,'lineage boundary missing')
        for pc,ins in by_pc.items():
            op=ins['opcode'];successors=set()
            require(not op.startswith(('PACKED_SWITCH','SPARSE_SWITCH')),'switch outside bounded lineage grammar')
            if pc!=hi:
                if 'targetPc' in ins:successors.add(ins['targetPc'])
                if not op.startswith(('GOTO','RETURN','THROW')):
                    following=pc+ins['codeUnits']
                    if following in by_pc:successors.add(following)
                for catch in body['catches']:
                    if catch['startPc']<=pc<catch['startPc']+catch['codeUnits']:
                        successors.add(catch['handlerPc'])
            edges[pc]=successors
        forward=set();todo=[lo]
        while todo:
            pc=todo.pop()
            if pc in forward:continue
            forward.add(pc);todo.extend(edges[pc]-forward)
        back={hi}
        while True:
            previous=len(back)
            back.update(pc for pc,targets in edges.items() if targets&back)
            if len(back)==previous:break
        require(hi in forward,'selected lineage cannot reach target')
        active=(forward&back)-{lo,hi}
        for pc in sorted(active):
            ins=by_pc[pc]
            op=ins['opcode']
            if op.startswith(no_def):continue
            require(op.startswith(dest) and ins.get('registers'),'unclassified selected dataflow opcode')
            if op=='CHECK_CAST':continue  # reference value unchanged
            first=ins['registers'][0]
            wide=('WIDE' in op or (('_LONG' in op or '_DOUBLE' in op) and not op.startswith('CMP')))
            require(reg not in ({first,first+1} if wide else {first}),
                    'selected register lineage overwritten '+str((lo,hi,reg,ins['pc'],op)))
        assertions.append({'method':key,'rangeExclusive':[lo,hi],
                           'unmodifiedRegister':reg,'survivingPathInstructionCount':len(active),
                           'normalAndTryHandlerEdgesIncluded':True,'pass':True})
    for lo,hi,reg in [(156,695,1),(156,158,4),(428,435,6),(426,438,2),
                      (529,744,4),(531,571,5),(693,755,2),(695,742,5)]:
        stable_register(init,lo,hi,reg)
    local=S+'locksettings/LockSettingsService$LocalService;'
    ref(local,'onThirdPartyAppsStarted()V',12,LSS+'->migrateLockSettingsDB()V')
    ref(local,'onThirdPartyAppsStarted()V',15,LSS+'->migrateSpblob()V')
    at(local+'->onThirdPartyAppsStarted()V',20,opcode='MONITOR_ENTER')
    ref(local,'onThirdPartyAppsStarted()V',64,LSS+'->mEarlyRemovedUsers:Landroid/util/SparseIntArray;')
    ref(local,'onThirdPartyAppsStarted()V',112,LSS+'->mEarlyCreatedUsers:Landroid/util/SparseIntArray;')
    ref(local,'onThirdPartyAppsStarted()V',214,LSS+'->mThirdPartyAppsStarted:Z')
    late=local+'->onThirdPartyAppsStarted()V'
    for pc,regs in [(0,[8,8]),(18,[0,8]),(20,[0]),(63,[2]),(64,[2,8]),
                    (112,[2,8]),(124,[4]),(214,[4,8]),(216,[0])]:
        at(late,pc,registers=regs)
    at(late,18,reference=LSS+'->mUserCreationAndRemovalLock:Ljava/lang/Object;')
    at(late,63,opcode='CONST_4',literal=0)
    at(late,124,opcode='CONST_4',literal=1)
    at(late,216,opcode='MONITOR_EXIT')
    for lo,hi,reg in [(18,216,0),(63,112,2),(124,214,4),(0,216,8)]:
        stable_register(late,lo,hi,reg)
    for owner,parent in [(FPW,FP),(BW,BIO),(AW,AUTH)]:
        ref(owner,'<init>('+parent+')V',0,owner+'->this$0:'+parent)
    ref(AUTH,'onStart()V',8,AUTH+'->mBiometricService:Landroid/hardware/biometrics/IBiometricService;')
    ref(AUTH,'onStart()V',437,S+'biometrics/AuthService$Injector;->publishBinderService(Lcom/android/server/biometrics/AuthService;Landroid/hardware/biometrics/IAuthService$Stub;)V')
    ref(BIO,'onStart()V',113,S+'SystemService;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    injector=S+'biometrics/AuthService$Injector;'
    ref(injector,'getBiometricService()Landroid/hardware/biometrics/IBiometricService;',3,'Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;')
    stub='Landroid/hardware/biometrics/IBiometricService$Stub;'
    ref(stub,'asInterface(Landroid/os/IBinder;)Landroid/hardware/biometrics/IBiometricService;',6,'Landroid/os/IBinder;->queryLocalInterface(Ljava/lang/String;)Landroid/os/IInterface;')
    at(stub+'->asInterface(Landroid/os/IBinder;)Landroid/hardware/biometrics/IBiometricService;',18,opcode='RETURN_OBJECT')
    storage_stub='Landroid/os/storage/IStorageManager$Stub;'
    ref(storage_stub,'asInterface(Landroid/os/IBinder;)Landroid/os/storage/IStorageManager;',6,
        'Landroid/os/IBinder;->queryLocalInterface(Ljava/lang/String;)Landroid/os/IInterface;')
    at(storage_stub+'->asInterface(Landroid/os/IBinder;)Landroid/os/storage/IStorageManager;',18,
       opcode='RETURN_OBJECT',registers=[0])
    for suffix,needle in [('FingerprintProviderFunction;)V','0076 IPUT_OBJECT v5 v2 '+REG+'->mService:'+FPW),('onStart()V','0005 INVOKE_VIRTUAL v2 v0 v1 '+S+'SystemService;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')]:
        matches=[(k,v) for k,v in legacy.items() if k.endswith(suffix)]
        require(len(matches)==1 and needle in matches[0][1],'FP existing owner/publication proof drift')
        assertions.append({'method':matches[0][0],'pc':118 if suffix.startswith('Fingerprint') else 5,
                           'scope':'exact selected legacy field/call operand assertion','pass':True})
    result={'schema':'retained-security-family-capture-source/v1','selected':False,
            'status':'FINITE_SOURCE_CONTRACT; runtime implementation/admission unselected',
            'originalInputs':{'servicesSha256':SERVICES,'frameworkSha256':FRAMEWORK,
                              'declarationsSha256':DECL_HASH},
            'proofInputManifest':{'path':'out/retained-security-family-capture/proof-inputs.json','sha256':INPUT_HASH},
            'fieldWhitelist':fields,'methodProofs':proofs,'sourceAssertions':assertions,
            'sourceAssertionCount':len(assertions),'fieldCount':len(fields),
            'proposedApi':['captureExisting(PreparedRetainedUserRegistryCapture)','checkStillBound()'],
            'runtimeComponentAuthored':False,'runtimeCaptureExecuted':False,'oemExecuted':False,
            'serviceQueries':False,'phoneActions':False,'sourceProfile':'ORIGINAL def967/8095 only; not staged guest',
            'limits':['Object/source placement admission is external; class/field/hash equality does not attest it',
                      'No native/authentication/enrollment/CE/policy readiness, lease, drain or generation is minted',
                      'No service getters, registration, constructors, secret/protector reads or policy-map queries',
                      'SSM membership precedes onStart and phase store precedes callbacks',
                      'Bounded main-only read consistency cannot retain a killed SystemServer process']}
    (OUT/'source-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pass':True,'fields':len(fields),'assertions':len(assertions),'methods':len(proofs),
                      'output':'out/retained-security-family-capture/source-checks.json','oemExecuted':False}))


if __name__=='__main__':
    inspect()
