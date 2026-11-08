"""Offline bounded OS-file/key-authority evidence. Never reads /data, credentials, or a device."""
import argparse,gzip,hashlib,json,re,struct,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT.parent
BASE=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
MANIFEST=BASE/'samsung-manifest.jsonl.gz'
MANIFEST_SHA='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
ARCHIVE=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
ARCHIVE_SHA='28eb27547fcc96348aa54f614a77aecd8bfcdbf875b61de2dd5279787985d96e'
STREAM=ROOT/'firmware/storage-keys'
WORK=ROOT/'out/storage-keys'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def elf_needed(data):
    if data[:6]!=b'\x7fELF\x02\x01':return []
    phoff=struct.unpack_from('<Q',data,32)[0];phsize,phnum=struct.unpack_from('<HH',data,54)
    segments=[struct.unpack_from('<IIQQQQQQ',data,phoff+i*phsize) for i in range(phnum)]
    dynamic=[s for s in segments if s[0]==2]
    if not dynamic:return []
    values=[]
    for p in range(dynamic[0][2],dynamic[0][2]+dynamic[0][5],16):
        tag,value=struct.unpack_from('<qQ',data,p)
        if tag==0:break
        values.append((tag,value))
    table=next((v for t,v in values if t==5),None)
    if table is None:return []
    segment=next(s for s in segments if s[0]==1 and s[3]<=table<s[3]+s[5])
    table=segment[2]+table-segment[3]
    return [data[table+v:data.index(b'\0',table+v)].decode('ascii') for t,v in values if t==1]

def service_blocks(text):
    result=[];current=None
    logical=[];pending=''
    for line in text.splitlines():
        pending+=line
        if pending.endswith('\\'):pending=pending[:-1]+' ';continue
        logical.append(pending);pending=''
    if pending:raise ValueError('Truncated init continuation')
    for line in logical:
        value=line.strip()
        if not value or value.startswith('#'):continue
        if line.startswith('service '):
            tokens=value.split();current={'name':tokens[1],'executable':tokens[2],'arguments':tokens[3:],'options':[]};result.append(current)
        elif not line[0].isspace():current=None
        elif current is not None:current['options'].append(value)
    return result

def selected(path):
    if path in ['system/bin/vold','system/bin/keystore2','system/bin/gatekeeperd','vendor/bin/hermesd','system/etc/init/vold.rc','system/etc/init/keystore2.rc','system/etc/init/gatekeeperd.rc']:return True
    if path.endswith('_keystore2_key_contexts'):return True
    return path.startswith(('vendor/bin/hw/','vendor/etc/init/','vendor/etc/vintf/manifest/','system/etc/vintf/manifest/')) and any(k in path.lower() for k in ('keymint','gatekeeper','weaver','keystore2','hermes','strongbox'))

def source_facts(receipts):
    bodies={}
    for name,r in receipts.items():
        for line in (ROOT/r['raw']).read_text().splitlines():
            row=json.loads(line)
            if row['record']=='method':bodies[(name,row['body']['signature'])]=row
    facts=[]
    def one(suffix,method):
        rows=[r for (c,s),r in bodies.items() if c.endswith(suffix) and (s==method if '(' in method else s.split('(')[0]==method)]
        if len(rows)!=1:raise ValueError('Exact source fact selector ambiguous/missing: '+suffix+'.'+method)
        return rows[0]
    def check(name,suffix,method,need=(),numbers=(),kind='observed-source'):
        row=one(suffix,method);code=row['body']['instructions'];refs=[i.get('reference','') for i in code]
        assert all(any(n in r for r in refs) for n in need),name
        assert all(any(i.get('literal')==n for i in code) for n in numbers),name
        facts.append({'fact':name,'kind':kind,'owner':row['body']['owner'],'signature':row['body']['signature'],'normalizedBodySha256':row['normalizedBodySha256']})
    check('Normal SP path uses system_de(user)/spblob; Samsung virtual-user path uses system/users/user/spblob','LockSettingsStorage','getSyntheticPasswordDirectoryForUser',('isVirtualUser()Z','getDataSystemDeDirectory(I)','string=spblob/','string=users'))
    check('Protector file name is hex protector ID plus state suffix','LockSettingsStorage','getSyntheticPasswordStateFileForUser',('string=%016x.%s',))
    check('Password slot directory is metadata/password_slots','PasswordSlotManager','getSlotMapDir',('string=/metadata/password_slots',))
    check('Slot allocator loads the slot_map file','PasswordSlotManager','ensureSlotMapLoaded',('string=slot_map',))
    check('Slot mode depends on ro.gsid.image_running, not arbitrary container identity','PasswordSlotManager','getGsiImageNumber',('string=ro.gsid.image_running',))
    check('Refreshing active slots removes/updates entries and persists the map','PasswordSlotManager','refreshActiveSlots',('->remove(','->put(','->saveSlotMap()'))
    check('Samsung fake Gatekeeper user maps Android user plus100000','SyntheticPasswordManager','fakeUserId',numbers=(100000,))
    check('Protector aliases derive from original protector IDs','SyntheticPasswordManager','getProtectorKeyAlias',('string=synthetic_password_','string=%s%x'))
    check('LockSettingsService loads existing AndroidKeyStore namespace103','LockSettingsService','<init>',('string=AndroidKeyStore','AndroidKeyStoreLoadStoreParameter;-><init>(I)','KeyStore;->load('),numbers=(103,))
    check('SP blob key protection has critical-encryption/SID/auth-duration15 and rollback-resistant import/fallback paths','SyntheticPasswordManager','createSyntheticPasswordBlob',('->setCriticalToDeviceEncryption(','->setBoundToSpecificSecureUserId(','->setUserAuthenticationRequired(','->setUserAuthenticationValidityDurationSeconds(','->setRollbackResistant(','KeyStore;->setEntry('),numbers=(15,))
    check('Unwrap loads original protector alias from existing keystore and has blob recreation/upgrade path','SyntheticPasswordManager','unwrapSyntheticPasswordBlob',('KeyStore;->getKey(','->createSyntheticPasswordBlob('))
    check('Weaver initialization refreshes slot map from actual current protector inventory','SyntheticPasswordManager','getWeaverServiceLocked',('->getConfig()','->getUsedWeaverSlots()','->refreshActiveSlots('))
    check('Samsung Weaver inventory can remove conflicting virtual-user state','SyntheticPasswordManager','getUsedWeaverSlots',('->listSyntheticPasswordProtectorsForAllUsers(','->isVirtualUserId(','->destroyState('))
    check('Gatekeeper verify can request reenrollment then save/sync and verify again','SyntheticPasswordManager','verifyChallengeInternal',('->verifyChallenge(','->getShouldReEnroll()','->enroll(','->syncState('))
    check('Keystore unlock uses SP keystore-password subkey and onDeviceUnlocked','LockSettingsService','unlockKeystore',('PERSONALIZATION_KEY_STORE_PASSWORD','->deriveSubkey(','->onDeviceUnlocked('))
    check('CE unlock can skip already-unlocked user and otherwise uses SP FBE subkey plus concrete Samsung storage owner','LockSettingsService','unlockCeStorage',('->isCeStorageUnlocked(','PERSONALIZATION_FBE_KEY','->deriveSubkey(','StorageManagerInternalImpl;->unlockCeStorage('))
    check('Samsung CE backend hex encodes optional HAT and passes HSUM mode to actual IVold','StorageManagerInternalImpl','unlockCeStorage',('HexDump;->toHexString(','string=!','->isHSUMMode:Z','IVold;->unlockCeStorage(ILjava/lang/String;[BZ)V'))
    check('Super-key initialization derives SP keystore password and invokes native-maintenance boundary','LockSettingsService','initKeystoreSuperKeys',('PERSONALIZATION_KEY_STORE_PASSWORD','->deriveSubkey(','->initUserSuperKeys('))
    check('Java HAT bytes are decoded then sent to keystore authorization service','KeyStoreAuthorization','addAuthToken([B)I',('AuthTokenUtils;->toHardwareAuthToken(','->addAuthToken(Landroid/hardware/security/keymint/HardwareAuthToken;)I'))
    check('HAT structure carries challenge/userSID/authenticatorId/type/timestamp/MAC fields','AuthTokenUtils','toHardwareAuthToken',('->challenge:J','->userId:J','->authenticatorId:J','->authenticatorType:I','->timestamp:','->mac:[B'))
    check('Native operation challenge is obtained from CreateOperationResponse','KeyStoreSecurityLevel','createOperation',('IKeystoreSecurityLevel;->createOperation(','->operationChallenge:','OperationChallenge;->challenge:J'))
    check('getOrMakeOperationChallenge can substitute random long when real operation challenge is absent','KeyStoreCryptoOperationUtils','getOrMakeOperationChallenge',('KeyStoreOperation;->getChallenge()','SecureRandom;->nextLong()'))
    check('Auth-required key parameters include SIDs, auth type and timeout policy','KeyStore2ParameterUtils','addUserAuthArgs',('->addSids(','->getUserAuthenticationType()','->getUserAuthenticationValidityDurationSeconds()'))
    check('Root auth SID is read from GateKeeper, not Android user or Linux UID','KeyStore2ParameterUtils','getRootSid',('GateKeeper;->getSecureUserId()J',))
    return facts

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-only',action='store_true');p.add_argument('--refresh-java',action='store_true',help='Re-read the exact successful queries in the retained authored inventory with the shared DEX041 reader');args=p.parse_args()
    if args.refresh_java:
        import runpy
        previous=json.loads((ROOT/'inventory/storage-keys.json').read_text())['javaStaticEvidence']
        read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];results={}
        for name,query in previous.items():
            options={'reference':'Landroid/os/IVold;'} if name=='IVold-direct-refs' else {'class_name':name,'methods':[m['signature'] for m in query['methodProofs']]}
            results[name]=read(query['archive'],query['archiveSha256'],stream='storage-keys',**options)
        WORK.mkdir(parents=True,exist_ok=True);(WORK/'java-receipts.json').write_text(json.dumps(results,indent=2)+'\n')
    assert sha(MANIFEST)==MANIFEST_SHA,'Immutable source index changed'
    rows=[json.loads(x) for x in gzip.open(MANIFEST,'rt')]
    wanted={r['originalPath']:r for r in rows if r['kind']=='file' and selected(r['path'])}
    STREAM.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    missing={n for n,r in wanted.items() if not (STREAM/n).is_file() or sha(STREAM/n)!=r['sha256']}
    if missing:
        # Previously strict-framed archive is opened only locally; no link is extracted and every selected body is rehashed.
        assert ARCHIVE.stat().st_size==20434769920
        with tarfile.open(ARCHIVE,'r:') as tar:
            for member in tar:
                name=member.name.removeprefix('./')
                if name not in missing:continue
                row=wanted[name];assert member.isfile() and member.size==row['size'] and member.size<=32*1024*1024
                data=tar.extractfile(member).read(member.size+1);assert len(data)==member.size and hashlib.sha256(data).hexdigest()==row['sha256']
                dest=(STREAM/name).resolve();assert dest.is_relative_to(STREAM.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);missing.remove(name)
                if not missing:break
        assert not missing,'Selected members absent'
    evidence=[]
    for name,row in sorted(wanted.items()):
        path=STREAM/name;assert sha(path)==row['sha256'];data=path.read_bytes()
        item={'path':row['path'],'kind':'observed-file','sha256':row['sha256'],'bytes':len(data),'raw':str(path.relative_to(ROOT)).replace('\\','/')}
        if data.startswith(b'\x7fELF'):
            strings=[x.decode('ascii') for x in re.findall(rb'[\x20-\x7e]{5,}',data)]
            item['dtNeeded']=elf_needed(data)
            item['boundedPathAndServiceLiterals']=sorted(set(x for x in strings if len(x)<220 and (x.startswith(('/data/','/metadata/','android.hardware.','android.system.','android.service.')) or x in ['user.auth','keystore2','gatekeeper','vold'])))[:100]
            item['semanticLimit']='ELF imports/strings only; no native function behavior or cryptographic acceptance established'
        elif name.endswith('.rc'):
            text=data.decode();item['serviceDeclarations']=service_blocks(text)
            item['initTriggerConditions']=[line[3:].strip() for line in text.splitlines() if line.startswith('on ')]
        elif name.endswith('_keystore2_key_contexts'):
            item['namespaceDeclarations']=[line.strip() for line in data.decode().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        elif name.endswith('.xml'):
            item['interfaceDeclarationTokens']=sorted(set(re.findall(r'(?:android\.(?:hardware|system)\.[a-zA-Z0-9_.]+|I[A-Z][A-Za-z]+/[A-Za-z0-9_]+)',data.decode())))
        evidence.append(item)
    # Derived metadata only; never import state from outside the OS-root dump.
    report={'status':'bounded offline storage/key authority source inventory','sourceManifest':str(MANIFEST.relative_to(PARENT)).replace('\\','/'),'sourceManifestSha256':MANIFEST_SHA,'sourceArchive':str(ARCHIVE.relative_to(PARENT)).replace('\\','/'),'sourceArchiveSha256FromStrictCapture':ARCHIVE_SHA,'archiveWholeHashRecomputedThisRun':False,'selectedBodiesIndividuallyVerified':True,'capturedRoots':['apex','odm','odm_dlkm','oem','product','system','system_dlkm','system_ext','vendor','vendor_dlkm'],'excludedStateRoots':['data','metadata'],'selectedFiles':evidence,'codeOrServiceExecuted':False,'credentialStateReadOrCopied':False,'phoneActions':False,'toolSha256':sha(Path(__file__).resolve())}
    java=WORK/'java-receipts.json'
    if not java.exists() and not args.native_only:raise ValueError('Full report requires retained exact Java receipts; use --refresh-java against the authored inventory, or explicitly --native-only')
    if java.exists() and not args.native_only:
        selected_java={};refs=[]
        receipts=json.loads(java.read_text())
        for name,r in receipts.items():
            raw=ROOT/r['raw'];assert sha(raw)==r['rawSha256'],'Raw static evidence drift'
            selected_java[name]={'archive':r['archive'],'archiveSha256':r['archiveSha256'],'receipt':r['receipt'],'raw':r['raw'],'rawSha256':r['rawSha256'],'logicalDex':r['physicalLogicalDex'],'methodProofs':r['selectedMethodProofs'],'historicalReaderPins':r['tools']}
            if name=='IVold-direct-refs':
                for line in raw.read_text().splitlines():
                    row=json.loads(line)
                    if row['record']=='reference' and any(k in row['instruction']['reference'] for k in ['unlockCeStorage','lockCeStorage','setCeStorageProtection','createUserStorageKeys','destroyUserStorageKeys']):refs.append({'caller':row['caller'],'target':row['instruction']['reference'],'pc':row['instruction']['pc']})
        report['javaStaticEvidence']=selected_java;report['voldKeyManagementDirectEdges']=refs;report['checkedSourceFacts']=source_facts(receipts)
    oneos=PARENT/'firmware/reference/OneOS/2a5f41043b4a69399cae058bad213cdef7408e88'
    report['oneosSourcePins']={n:sha(oneos/n) for n in ['switcher/patches/guest_no_gatekeeper.py','switcher/patches/guest_no_weaver.py','switcher/patches/guest_no_vold_keys.py','switcher/assets/guest_prepare.sh','switcher/assets/guest_start.sh','switcher/assets/oneos_switch.sh','switcher/assets/return_to_oneui.sh']}
    credential=ROOT/'inventory/credentials.json'
    if credential.exists():
        key='samsung:Lcom/android/server/locksettings/LockSettingsStorage$DatabaseHelper;-><init>(Landroid/content/Context;)V'
        entry=json.loads(credential.read_text()).get('methodProofs',{}).get(key)
        if entry:
            receipt=json.loads((ROOT/entry['receipt']).read_text());assert sha(ROOT/entry['raw'])==receipt['rawSha256']
            assert entry['bodySha256']=='35a3e4cc44501037ce308a94f82438a3f60e164932b11301ccd5e11a4ca24059'
            report['crossStreamDatabaseConstructor']={'selector':key,**entry,'limit':'Context-resolved locksettings.db name/version3/WAL-disabled constructor, not actual runtime DB path or schema contents'}
    report['ownershipGraph']={'kind':'authored source-supported candidate boundary; not runtime execution','nodes':['ColorOS presentation','authorized Samsung host-user credential owner','original host protector/storage inventory','existing Weaver or Gatekeeper protector','namespace103 original protector key','original synthetic password','native keystore authorization/super-key owner','actual Samsung StorageManagerInternalImpl','original host vold/mount/key owner','exact UID/domain/key/native operation','original KeyMint and secure component'],
        'edges':[
            ['ColorOS presentation','authorized Samsung host-user credential owner','authenticated request required; unassembled'],
            ['original host protector/storage inventory','existing Weaver or Gatekeeper protector','existing IDs/handles/slots; no new assignment'],
            ['existing Weaver or Gatekeeper protector','original synthetic password','exact blob + namespace103 existing key, conditional paths'],
            ['original synthetic password','native keystore authorization/super-key owner','keystore-password subkey'],
            ['original synthetic password','actual Samsung StorageManagerInternalImpl','FBE subkey plus source-selected optional HAT'],
            ['actual Samsung StorageManagerInternalImpl','original host vold/mount/key owner','actual Samsung IVold and user/HSUM policy'],
            ['authorized Samsung host-user credential owner','original KeyMint and secure component','real signed HAT; native acceptance unverified'],
            ['exact UID/domain/key/native operation','original KeyMint and secure component','actual native challenge and key authentication policy required']],
        'missing':['live host user/protector/SID/slot/key metadata','actual daemon/Binder/HAL owners','host/guest filesystem and namespace mapping','native HAT/MAC/KeyMint acceptance','single credential-change writer and transactional recovery','post-return/cold-boot cryptographic acceptance']}
    report['runtimeBehaviorVerified']=False
    target=ROOT/'inventory/storage-keys.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'verifiedFiles':len(evidence),'services':[s['name'] for x in evidence for s in x.get('serviceDeclarations',[])],'javaQueries':len(report.get('javaStaticEvidence',{})),'nativeExecution':False}))

if __name__=='__main__':main()
