"""Narrow offline fingerprint construction frontier over frozen source receipts."""
import argparse,gzip,hashlib,json,re,runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
WORK=ROOT/'out/construction-fingerprint'
INDEX=PARENT/'out/os-comparison-resumed/archive-index'
SERVICES='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'

SELECTIONS={
 'com.android.server.biometrics.AuthService':['<init>','onStart','generateRSdkCompatibleConfiguration'],
 'com.android.server.biometrics.AuthService$Injector':['<init>','getAppOps','getBiometricService','getFingerprintAidlInstances','getFingerprintConfiguration','getFingerprintService','isHidlDisabled','publishBinderService'],
 'com.android.server.biometrics.BiometricService':['<init>','onStart','onBootPhase'],
 'com.android.server.biometrics.BiometricService$Injector':['<init>'],
 'com.android.server.biometrics.log.BiometricContext':['getInstance'],
 'com.android.server.biometrics.log.BiometricContextProvider':['<init>'],
 'com.android.server.biometrics.sensors.fingerprint.SemFingerprintServiceExtImpl$Injector':['<init>','createAodController'],
 'com.android.server.biometrics.SemBiometricDisplayStateMonitor':['<init>'],
 'com.android.server.biometrics.SemBiometricDisplayStateMonitor$InstanceHolder':['<clinit>'],
 'com.android.server.biometrics.sensors.SensorList':['<init>','addSensor'],
 'com.android.server.biometrics.sensors.BiometricServiceRegistry':['<init>','registerAllInBackground'],
 'com.android.server.biometrics.sensors.BiometricStateCallback':['<init>','broadcastCurrentEnrollmentState'],
 'com.android.server.biometrics.sensors.LockoutResetDispatcher':['<init>'],
 'com.android.server.biometrics.AuthenticationStatsBroadcastReceiver':['<init>'],
 'com.android.server.biometrics.BiometricDanglingReceiver':['<init>'],
 'com.android.server.biometrics.sensors.fingerprint.SemFpProviderEx':['<init>'],
 'com.android.server.biometrics.sensors.fingerprint.SemFpCallbackDispatcher':['<init>'],
}
EXTRA_SELECTIONS={
 'com.android.server.biometrics.AuthService$Injector':['getConfiguration'],
 'com.android.server.biometrics.AuthService$$ExternalSyntheticLambda1':['run'],
 'com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$6':['onUserSwitching'],
 'com.android.server.biometrics.BiometricService$BiometricServiceWrapper':['registerAuthenticator'],
 'com.android.server.biometrics.BiometricService$SettingObserver':['updateContentObserver'],
}
FACTORY_SELECTIONS={
 'com.android.server.biometrics.sensors.fingerprint.FingerprintService$1$$ExternalSyntheticLambda2':['get'],
 'com.android.server.biometrics.sensors.fingerprint.FingerprintService':['getDeclaredInstances','getFpLooper'],
 'com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda9':['run'],
 'com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda31':['run'],
}
FRAMEWORK_SELECTIONS={
 'android.hardware.fingerprint.FingerprintSensorConfigurations':['getSensorPropForInstance'],
 'android.hardware.fingerprint.FingerprintSensorPropertiesInternal':['isOpticalType','isUltrasonicType'],
}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def declarations(role,side):
    summary=json.loads((INDEX/'comparisons'/role/'summary.json').read_text());info=summary[side];path=PARENT/info['declarations']
    if sha(path)!=info['declarationsSha256']:raise ValueError('Frozen declaration index changed')
    values={v['descriptor']:v for line in gzip.open(path,'rt',encoding='utf-8')if 'descriptor'in(v:=json.loads(line))and'methods'in v}
    return info,values

def collect(extra=False,factory=False,framework=False):
    WORK.mkdir(parents=True,exist_ok=True);read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];info,decl=declarations('framework'if framework else 'system-server-services','samsung')
    if not framework and info['archiveSha256']!=SERVICES:raise ValueError('Expected Samsung service identity required')
    prior=json.loads((WORK/'reads.json').read_text())if extra or factory or framework else {'reads':[],'undeclaredSelectedMethods':[]}
    results=[];absent=prior['undeclaredSelectedMethods'];covered={}
    for item in prior['reads']:
        signatures={m['signature']for m in item['methods']};known=covered.setdefault(item['owner'],set())
        if signatures<=known:continue
        results.append(item);known.update(signatures)
    for name,names in (FRAMEWORK_SELECTIONS if framework else FACTORY_SELECTIONS if factory else EXTRA_SELECTIONS if extra else SELECTIONS).items():
        value=decl.get('L'+name.replace('.','/')+';')
        if value is None:raise ValueError('Exact construction type absent '+name)
        signatures=[m['name']+m['descriptor']for m in value['methods']if m['name']in names]
        for missing in sorted(set(names)-{m['name']for m in value['methods']}):absent.append({'owner':name,'undeclaredMethodName':missing,'noReplacementInvented':True})
        signatures=[s for s in signatures if s not in covered.get(name,set())]
        if not signatures:continue
        receipt=read(PARENT/info['archive'],info['archiveSha256'],class_name=name,methods=signatures,stream='construction-fingerprint')
        results.append({'owner':name,'receipt':receipt['receipt'],'raw':receipt['raw'],'rawSha256':receipt['rawSha256'],'methods':receipt['selectedMethodProofs']})
    (WORK/'reads.json').write_text(json.dumps({'reads':results,'undeclaredSelectedMethods':absent},indent=2)+'\n')
    print(json.dumps({'pass':True,'newTypes':len(results),'newBodies':sum(len(v['methods'])for v in results),'undeclaredSelectedMethods':absent,'oemExecuted':False}))

def normalized_old():
    path=ROOT/'out/fingerprint/bodies.json';old=json.loads(path.read_text());values={};proofs={}
    selectors=['FingerprintService-><init>','FingerprintService->onStart','FingerprintService->onBootPhase','FingerprintService$1->registerAuthenticators','FingerprintService$$ExternalSyntheticLambda1->run','FingerprintService$$ExternalSyntheticLambda2->get','FingerprintServiceRegistry->registerService','FingerprintServiceRegistry$$ExternalSyntheticLambda0->run','SemFingerprintServiceExtImpl-><init>','aidl.FingerprintProvider-><init>','aidl.FingerprintProvider->getHalInstance','aidl.Sensor-><init>','aidl.Sensor->getFingerprintSensorPropertiesInternal','aidl.FingerprintProvider->createSemFp','FingerprintService$2->onAllAuthenticatorsRegistered','FingerprintUtils->getStateForUser']
    for key,proof in old['bodies'].items():
        if not key.startswith('samsung:')or not any(v in key for v in selectors):continue
        text=(ROOT/proof['raw']).read_text(encoding='utf-8');sig=key.split('->',1)[1];block=next(v for v in re.split(r'(?m)^METHOD ',text)[1:]if v.startswith(sig+' FLAGS '));lines='\n'.join(v for v in block.splitlines()[1:]if re.match(r'^[0-9a-f]{4} ',v))
        if hashlib.sha256(lines.encode()).hexdigest()!=proof['sha256']:raise ValueError('Frozen original construction body changed')
        values[key]=lines;proofs[key]=proof
    return values,proofs

def source_assertions(bodies,old):
    """Discriminate concrete early side effects and guarded ABI edges, not models."""
    checks=[]
    def require(owner,signature,pc,**expected):
        key='L'+owner.replace('.','/')+';->'+signature
        instruction=next(i for i in bodies[key]['instructions']if i['pc']==pc)
        if any(instruction.get(k)!=v for k,v in expected.items()):raise ValueError('Source assertion failed '+key+' @'+hex(pc))
        checks.append({'body':key,'pc':pc,'expected':expected,'pass':True})
    require('com.android.server.biometrics.log.BiometricContext','getInstance(Landroid/content/Context;)Lcom/android/server/biometrics/log/BiometricContextProvider;',0x16,reference='Landroid/os/ServiceManager;->getServiceOrThrow(Ljava/lang/String;)Landroid/os/IBinder;')
    require('com.android.server.biometrics.log.BiometricContextProvider','<init>(Landroid/content/Context;Landroid/view/WindowManager;Lcom/android/internal/statusbar/IStatusBarService;Landroid/os/Handler;Lcom/android/server/biometrics/sensors/AuthSessionCoordinator;)V',0x3f,reference='Lcom/android/internal/statusbar/IStatusBarService;->setBiometicContextListener(Landroid/hardware/biometrics/IBiometricContextListener;)V')
    require('com.android.server.biometrics.sensors.SensorList','addSensor(ILjava/lang/Object;ILandroid/app/SynchronousUserSwitchObserver;)V',0x12,reference='Landroid/app/SynchronousUserSwitchObserver;->onUserSwitching(I)V')
    require('com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$6','onUserSwitching(I)V',0x23,opcode='IF_NEZ',targetPc=0x26)
    require('com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$6','onUserSwitching(I)V',0x42,opcode='IF_NEZ',targetPc=0x45)
    require('com.android.server.biometrics.sensors.BiometricServiceRegistry','registerAllInBackground(Ljava/util/function/Supplier;)V',0,reference='Ljava/util/function/Supplier;->get()Ljava/lang/Object;')
    require('com.android.server.biometrics.sensors.BiometricServiceRegistry','registerAllInBackground(Ljava/util/function/Supplier;)V',0x0f,reference='Ljava/util/function/Supplier;->get()Ljava/lang/Object;')
    require('com.android.server.biometrics.BiometricService','onStart()V',0xb7,opcode='IF_EQZ',targetPc=0xc5)
    require('com.android.server.biometrics.BiometricService','onStart()V',0xb9,reference='Landroid/hardware/display/DisplayManagerInternal;->registerDisplayStateListener(Landroid/hardware/display/DisplayManagerInternal$DisplayStateListener;)V')
    require('com.android.server.biometrics.BiometricService','onStart()V',0xbe,opcode='IF_EQZ',targetPc=0xc5)
    require('com.android.server.biometrics.BiometricService','onStart()V',0xc2,reference='Landroid/hardware/display/DisplayManagerInternal;->registerDisplayBrightnessListener(Landroid/hardware/display/DisplayManagerInternal$DisplayBrightnessListener;)F')
    require('android.hardware.fingerprint.FingerprintSensorConfigurations','getSensorPropForInstance(Ljava/lang/String;)[Landroid/hardware/biometrics/fingerprint/SensorProps;',0x2b,reference='Landroid/hardware/biometrics/fingerprint/IFingerprint;->getSensorProps()[Landroid/hardware/biometrics/fingerprint/SensorProps;')
    require('android.hardware.fingerprint.FingerprintSensorPropertiesInternal','isOpticalType()Z',2,literal=3)
    require('android.hardware.fingerprint.FingerprintSensorPropertiesInternal','isUltrasonicType()Z',2,literal=2)
    require('com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda9','run()V',0x1ac,opcode='PACKED_SWITCH_PAYLOAD',switchElements=[{'key':0,'offsetFromReferringSwitchPc':360},{'key':1,'offsetFromReferringSwitchPc':254},{'key':2,'offsetFromReferringSwitchPc':194},{'key':3,'offsetFromReferringSwitchPc':188},{'key':4,'offsetFromReferringSwitchPc':163}])
    require('com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda9','run()V',0xc6,reference='Lcom/android/server/biometrics/sensors/fingerprint/aidl/FingerprintProvider;->getHalInstance()Landroid/hardware/biometrics/fingerprint/IFingerprint;')
    require('com.android.server.biometrics.sensors.fingerprint.aidl.FingerprintProvider$$ExternalSyntheticLambda31','run()V',0x33,reference='Lcom/android/server/biometrics/sensors/fingerprint/hidl/HidlToAidlSensorAdapter;->getIBiometricsFingerprint()Landroid/hardware/biometrics/fingerprint/V2_1/IBiometricsFingerprint;')
    provider=next((key,text)for key,text in old.items()if 'aidl.FingerprintProvider-><init>('in key)
    for fragment in ['00a8 CONST_4 v15 literal=3','02a9 INVOKE_DIRECT v2 v15','02b1 INVOKE_VIRTUAL','02f9 CONST_4 v5 literal=0','02fa INVOKE_VIRTUAL v0 v2 v5']:
        if fragment not in provider[1]:raise ValueError('Original provider edge changed '+fragment)
        checks.append({'body':provider[0],'requiredOriginalInstructionFragment':fragment,'pass':True})
    return checks

def summarize():
    WORK.mkdir(parents=True,exist_ok=True);new=json.loads((WORK/'reads.json').read_text());bodies={};proofs={};declaration_rows={}
    for item in new['reads']:
        raw=ROOT/item['raw']
        if sha(raw)!=item['rawSha256']:raise ValueError('New raw construction evidence changed')
        for line_number,line in enumerate(raw.read_text(encoding='utf-8').splitlines(),1):
            row=json.loads(line)
            if row['record']=='class':declaration_rows[row['descriptor']]=row
            if row['record']=='method':
                body=row['body'];key=body['owner']+'->'+body['signature'];bodies[key]=body;proofs[key]={'raw':item['raw'],'rawLine':line_number,'receipt':item['receipt'],'sha256':row['normalizedBodySha256'],'instructionCount':len(body['instructions'])}
    old,old_proofs=normalized_old()
    checks=source_assertions(bodies,old)
    invocations={key:[{'pc':i['pc'],'opcode':i['opcode'],'target':i['reference']}for i in b['instructions']if i['opcode'].startswith('INVOKE')and i.get('referenceKind')=='method']for key,b in bodies.items()}
    constructions={key:{'newInstances':[{'pc':i['pc'],'type':i['reference']}for i in b['instructions']if i['opcode']=='NEW_INSTANCE'],'staticFields':[{'pc':i['pc'],'field':i['reference']}for i in b['instructions']if i['opcode'].startswith('SGET')and i.get('referenceKind')=='field'],'directCalls':invocations[key]}for key,b in bodies.items()if '<init>('in key or '<clinit>('in key}
    # Resolve actual canonical call references against supplied guest declarations and ancestry.
    host={};guest={};index_pins={}
    for role in ['framework','system-server-services']:
        for side,target in [('samsung',host),('coloros',guest)]:
            info,rows=declarations(role,side);index_pins[role+':'+side]={'archive':info['archive'],'archiveSha256':info['archiveSha256'],'declarationsSha256':info['declarationsSha256']};target.update(rows)
    def has_method(table,owner,signature,visited=None):
        visited=set()if visited is None else visited
        if owner in visited:return False
        visited.add(owner);record=table.get(owner)
        if record is None:return False
        if any(m['name']+m['descriptor']==signature for m in record['methods']):return True
        if signature.startswith('<init>('):return False
        return any(p and has_method(table,p,signature,visited)for p in [record.get('superclass'),*record.get('interfaces',[])])
    references=set()
    for values in invocations.values():
        references.update(v['target']for v in values)
    for text in old.values():references.update(re.findall(r'L[^\s]+;->[^\s]+','\n'.join(v for v in text.splitlines()if'INVOKE_'in v)))
    canonical=[]
    for ref in sorted(references):
        owner,sig=ref.split('->',1)
        if not owner.startswith(('Landroid/','Lcom/android/internal/','Lcom/samsung/')):continue
        if owner not in host:continue
        host_resolved=has_method(host,owner,sig);guest_resolved=has_method(guest,owner,sig)
        canonical.append({'target':ref,'hostDeclarationResolvable':host_resolved,'guestSelectedFrameworkServicesClassPresent':owner in guest,'guestExactOrInheritedDescriptorPresent':guest_resolved,'classification':'present in selected guest declarations'if guest_resolved else 'missing from selected guest declarations'if host_resolved else 'unresolved in both selected indexes; external ancestry is not an ABI gap proof','absenceScope':'selected framework.jar/services.jar only; other guest jars are not excluded'})
    frontier=[
      {'stage':'public FingerprintService constructor','observed':'BiometricContext singleton creation can require statusbar/window, register remote biometric/session callbacks and a dock receiver; real fingerprint Looper, AppOps, LPU, UserManager, registry and Sem extension are retained','requiredOwner':'canonical context/resources, callback threads, actual service endpoints, registration lifetimes'},
      {'stage':'BiometricService constructor/start','observed':'all-user Secure observers, authenticator-registration callbacks, trust/UserManager/DP/FP/face managers, camera/privacy, KeyStoreAuthorization, GateKeeper, virtual-device local reference, Samsung SysUi manager and user-switch observer; onStart publishes biometric before other initialization finishes','requiredOwner':'genuine policy endpoints and Samsung-compatible typed UI/display boundary; constructor return alone is insufficient'},
      {'stage':'AuthService.onStart and posted FP lambda','observed':'gets biometric/fingerprint services, actual declared IFingerprint instances and configuration; posts genuine configuration registration, then publishes auth','requiredOwner':'single global service family, permission checks and registration readiness independently acknowledged'},
      {'stage':'provider factory','observed':'property cache miss performs actual HAL getSensorProps before provider constructor; original branch selects real versus virtual instance','requiredOwner':'pinned real sensor/instance, exclusive native ownership and no virtual/test substitution'},
      {'stage':'provider construction','observed':'registers statistics/dangling receivers and per-sensor user-switch observers, posts AIDL HAL acquisition, and reads literal user-0 enrollment metadata before returning','requiredOwner':'exclusive writer and final storage/user/sensor mapping before construction; keep actual pending work and registrations owned on failure'},
      {'stage':'deferred HAL acquisition','observed':'constructor AIDL post classId3 resolves to getHalInstance; that existing body links death and schedules all-alive-user cleanup/authenticator-ID loads. HIDL constructor post acquires adapter daemon','requiredOwner':'actual native/session/cleanup scheduler, coherent metadata before posted work can execute'},
      {'stage':'registration/readiness','observed':'registry creates providers before resolving biometric service; later registers each authenticator, stores provider/property lists and broadcasts; enrollment callback reads every alive user','requiredOwner':'no duplicate sensor authority, accepted strength/authenticator tuple, all relevant user metadata; publication/list callback is not crypto acceptance'},
      {'stage':'boot phases 550/600/1000','observed':'original posted extension work includes display/secure observers and sensor-feature-dependent touch/AOD/optical/controller support; boot completion can run pending metadata callbacks','requiredOwner':'phase-preserving callbacks, genuine device feature/resource facts, explicit supported/unavailable optional branches; exact teardown not demonstrated'},
    ]
    result={'schema':'fingerprint-construction-static/v1','scope':'Stage-1 narrow constructor/factory/registration frontier; no functioning biometric or protected key proof','sourceInputs':index_pins,'reusedBodyProofs':old_proofs,'newBodyProofs':proofs,'sourceAssertions':checks,'constructionFrontier':frontier,'newCallEdges':invocations,'newConstructionEdges':constructions,'canonicalDeclarationComparisons':canonical,'undeclaredSelectedMethods':new['undeclaredSelectedMethods'],'reusedInventorySha256':sha(ROOT/'inventory/fingerprint.json'),'toolSha256':sha(Path(__file__)),'classification':{'observed':'exact supplied static bodies, declared call shapes and branch-preserving dependency frontier','inference':'candidate owner order and required integration gates are in companion document','missing':'actual selected owners, guest-patched input and runtime/native/enrollment acceptance','verifiedRuntimeBehavior':False},'oemExecuted':False,'jniExecuted':False,'servicesStarted':False,'hardwareRequested':False,'phoneChanged':False}
    (ROOT/'inventory/construction-fingerprint.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'reusedBodies':len(old),'newBodies':len(bodies),'sourceAssertions':len(checks),'canonicalCallsCompared':len(canonical),'hostResolvedGuestMissingExactSelectedCalls':sum(r['hostDeclarationResolvable']and not r['guestExactOrInheritedDescriptorPresent']for r in canonical),'unresolvedBothSelectedIndexes':sum(not r['hostDeclarationResolvable']and not r['guestExactOrInheritedDescriptorPresent']for r in canonical),'runtimeAccepted':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collect',action='store_true');p.add_argument('--collect-extra',action='store_true');p.add_argument('--collect-factory',action='store_true');p.add_argument('--collect-framework',action='store_true');a=p.parse_args();collect(extra=a.collect_extra,factory=a.collect_factory,framework=a.collect_framework)if a.collect or a.collect_extra or a.collect_factory or a.collect_framework else summarize()
