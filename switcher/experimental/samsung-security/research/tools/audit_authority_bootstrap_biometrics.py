"""Recheck finite biometric bootstrap source receipts, never execute OEM code.

Default reads saved bodies only. --collect reproduces three narrow SysUiManager
methods through the shared static reader; all other evidence is reused.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
OUT = ROOT/'out/authority-bootstrap-biometrics'
SERVICES = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
PINS = {
 'inventory/construction-fingerprint.json': 'd106f8ba847e866bcf10df8ae4c9c5cc0a81d74276cfd243d4ad01351e2217dd',
 'inventory/fingerprint.json': 'bddf8d9c9580acb205a3dd6649530d0bcc23bad135c2da7bdb16e392185b6b4c',
 'inventory/construction-state.json': 'db1cf18b25eac47666ade696f0f539fdb5d2b771144e5aa891fd1591c1cca1dd',
 'inventory/construction-startup.json': '998bd293e7cf598e76d4f60ec1b45a22e4417001aa38d4fe953f6b697a9706ef',
 'inventory/security-code-realm.json': '63ba98318e9c7c9b528c07208400e833e615a05091313f0779e3b8fe88063346',
}
OWNER = 'com.android.server.biometrics.SemBiometricSysUiManager'
GROUPS = {
 'sysui-constructor-receipt.json': ['<init>(Landroid/content/Context;Landroid/os/Looper;)V'],
 'sysui-bind-receipt.json': ['bind()V','openSession(Ljava/lang/String;Lcom/android/server/biometrics/SemBiometricSysUiManager$SysUiListener;)I'],
}
POWER = {
 'enableEarlyWakeUp()V': '405c511a3826dd84a0460621e0b5e7312adec5ed903553c35f3b7469477af93f',
 'isInteractive()Z': '6fd8ef8c121a17de142332320420c5ce68a8ae3d1918db20b4f11d066b65b3c3',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def legacy(raw,signature,expected):
    text=Path(raw).read_text(encoding='utf8')
    section=next(s for s in re.split(r'(?m)^METHOD ',text)[1:] if s.startswith(signature+' FLAGS '))
    instructions='\n'.join(s for s in section.splitlines()[1:] if re.match(r'^[0-9a-f]{4} ',s))
    if hashlib.sha256(instructions.encode()).hexdigest()!=expected:
        raise ValueError('Reused instruction body drift '+signature)
    return instructions


def collect():
    from static_security_reader import read_archive
    for filename,methods in GROUPS.items():
        result=read_archive(PARENT/'firmware/samsung/runtime-20261104/services.jar',SERVICES,class_name=OWNER,methods=methods,stream='authority-bootstrap-biometrics')
        (OUT/filename).write_text(json.dumps(result,indent=2)+'\n')


def inspect():
    for path,pin in PINS.items():
        if digest(ROOT/path)!=pin: raise ValueError('Frozen input inventory differs '+path)
    original=json.loads((ROOT/'inventory/construction-fingerprint.json').read_text())
    bodies={};proofs=[];legacy_bodies={};assertions=[]
    for key,proof in original['newBodyProofs'].items():
        receipt=json.loads((ROOT/proof['receipt']).read_text())
        if digest(ROOT/proof['raw'])!=receipt['rawSha256']: raise ValueError('Reused raw receipt drift')
        row=json.loads((ROOT/proof['raw']).read_text().splitlines()[proof['rawLine']-1])
        if row['normalizedBodySha256']!=proof['sha256']: raise ValueError('Reused normalized body identity')
        bodies[key]=row['body']
        proofs.append({'key':key,'raw':proof['raw'],'rawSha256':receipt['rawSha256'],'rawLine':proof['rawLine'],'normalizedBodySha256':proof['sha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'reused':True})
    for key,proof in original['reusedBodyProofs'].items():
        legacy_bodies[key]=legacy(ROOT/proof['raw'],key.split('->',1)[1],proof['sha256'])
        proofs.append({'key':key,'raw':proof['raw'],'rawSha256':digest(ROOT/proof['raw']),'rawMethodLine':proof['rawMethodLine'],'instructionTextSha256':proof['sha256'],'reused':True})
    power_raw=ROOT/'firmware/fingerprint/samsung/com.android.server.biometrics.sensors.fingerprint.aidl.SemFingerprintAuthenticationClient.txt'
    for signature,pin in POWER.items():
        key='samsung:com.android.server.biometrics.sensors.fingerprint.aidl.SemFingerprintAuthenticationClient->'+signature
        legacy_bodies[key]=legacy(power_raw,signature,pin)
        proofs.append({'key':key,'raw':power_raw.relative_to(ROOT).as_posix(),'rawSha256':digest(power_raw),'instructionTextSha256':pin,'reused':True,'scope':'Deferred operation owner, not observed cold constructor effect'})
    for filename,methods in GROUPS.items():
        receipt=json.loads((OUT/filename).read_text())
        if receipt['archiveSha256']!=SERVICES or receipt['readerExitCode']!=0 or digest(ROOT/receipt['raw'])!=receipt['rawSha256']:
            raise ValueError('New narrow source identity/completion differs')
        seen=[]
        for line in (ROOT/receipt['raw']).read_text().splitlines():
            row=json.loads(line)
            if row['record']!='method': continue
            body=row['body'];seen.append(body['signature']);key=body['owner']+'->'+body['signature'];bodies[key]=body
            proofs.append({'key':key,'raw':receipt['raw'],'rawSha256':receipt['rawSha256'],'normalizedBodySha256':row['normalizedBodySha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'receipt':(OUT/filename).relative_to(ROOT).as_posix(),'receiptSha256':digest(OUT/filename),'reused':False})
        if set(seen)!=set(methods): raise ValueError('Narrow selected methods differ')
    def instruction(key,pc,**expected):
        actual=next(i for i in bodies[key]['instructions'] if i['pc']==pc)
        if any(actual.get(k)!=v for k,v in expected.items()): raise ValueError('Source gate differs '+key+' '+str(pc))
        assertions.append({'method':key,'pc':pc,'scope':'Observed source assertion','pass':True})
    bio='Lcom/android/server/biometrics/BiometricService;'
    ctor=bio+'-><init>(Landroid/content/Context;Lcom/android/server/biometrics/BiometricService$Injector;Lcom/android/server/biometrics/BiometricHandlerProvider;)V'
    instruction(ctor,71,reference='Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;')
    instruction(ctor,349,reference='Landroid/hardware/fingerprint/FingerprintManager;->addAuthenticatorsRegisteredCallback(Landroid/hardware/fingerprint/IFingerprintAuthenticatorsRegisteredCallback;)V')
    instruction(ctor,495,reference='Lcom/android/server/LocalServices;->getService(Ljava/lang/Class;)Ljava/lang/Object;')
    instruction(bio+'->onStart()V',113,reference='Lcom/android/server/SystemService;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    instruction(bio+'->onStart()V',183,opcode='IF_EQZ',targetPc=197)
    instruction(bio+'->onStart()V',190,opcode='IF_EQZ',targetPc=197)
    base='Lcom/android/server/biometrics/SemBiometricSysUiManager;'
    # Constructor allocates only local owners in the selected actual body.
    init=bodies[base+'-><init>(Landroid/content/Context;Landroid/os/Looper;)V']
    if any('->bind' in i.get('reference','') or 'ServiceManager;' in i.get('reference','') for i in init['instructions']):
        raise ValueError('New cold endpoint effect in SysUi constructor')
    instruction(base+'->openSession(Ljava/lang/String;Lcom/android/server/biometrics/SemBiometricSysUiManager$SysUiListener;)I',120,reference=base+'->bind()V')
    instruction(base+'->bind()V',57,reference='Landroid/content/Context;->bindService(Landroid/content/Intent;ILjava/util/concurrent/Executor;Landroid/content/ServiceConnection;)Z')
    instruction(base+'->bind()V',41,reference='string=com.samsung.android.biometrics.app.setting.BiometricsUIService')
    phase=next(v for k,v in legacy_bodies.items() if 'FingerprintService$$ExternalSyntheticLambda1->run' in k)
    for fragment in ['0026 IF_NE v0 v7 target=0299','0057 IF_EQZ v0 target=01ec','01da INVOKE_STATIC','029d IF_NE v0 v1 target=055e','0560 IF_NE v0 v1 target=067c','0593 INVOKE_INTERFACE v14 Ljava/lang/Runnable;->run()V']:
        if fragment not in phase: raise ValueError('Original phase/feature gate differs')
        assertions.append({'method':'FingerprintService$$ExternalSyntheticLambda1.run','instructionPcHex':fragment[:4],'scope':'Observed phase/feature boundary','pass':True})
    result={'schema':'authority-bootstrap-biometrics-proof/v1','scope':'Finite E source card evidence; no startup/lifecycle/native operation','inputInventories':[{'path':p,'sha256':s} for p,s in PINS.items()],'sourceInputs':original['sourceInputs'],'proofs':proofs,'sourceAssertions':assertions,'newBodies':3,'reusedBodies':len(proofs)-3,'toolSha256':digest(__file__),'oemExecuted':False,'jniExecuted':False,'servicesStarted':False,'hardwareRequested':False,'phoneActions':False}
    (OUT/'method-proofs.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pass':True,'newBodies':3,'reusedBodies':result['reusedBodies'],'sourceAssertions':len(assertions),'report':'out/authority-bootstrap-biometrics/method-proofs.json'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.collect: collect()
    inspect()


if __name__=='__main__': main()
