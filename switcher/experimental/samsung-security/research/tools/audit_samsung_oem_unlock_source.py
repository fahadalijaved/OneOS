"""Replay finite captured Samsung OEM-lock source facts. No phone/IPC/OEM execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STREAM = 'samsung-oem-unlock-source'
PINS = {'../firmware/samsung/framework.jar': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe', '../firmware/samsung/runtime-20261104/services.jar': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6', 'firmware/samsung-oem-unlock-source/SecSettings.apk': 'ae40a4c3a91fc599aa26e8c8e7c6ddfab795fddfed0ae334395006206039b316', 'tools/SecurityDexReader.java': '9ee6f28750779f289bbb85049472d5261b7bacad5655faf01c8395f2f6d244cc', 'tools/static_security_reader.py': '0bbe5418e74bc928e770a634f7cfc7b734131afeb69a7aa0b26676b6ccaa1407', 'out/phone-code-profile/20261106T002544288151Z-9626ce8db0044ffeb7816616f04b00c0/observation.json': 'c1b3acc0396e501553a3301dcb1a22330335a3c95de33460fb2c61ac79e3b1c3', 'out/bootloader-feasibility/20261106T003304422485Z-9b013e3fc4894a4b8ce9152413fe8798/properties.json': '6e0ffecff9a7e36c9a5cc4bb7e10d5f2ceacaa6c998a9e09229ccfc98124cc0c', 'out/bootloader-feasibility/20261106T003554459439Z-851d8498b9c84adf90f82ead3ede3b1b/additional-properties.json': '07c08200087066e0b9fa4731714c36025758c9309a34f3d325cc301253efa19d', 'out/samsung-oem-unlock-source/settings-acquisition.json': '2df5ef123a01267c40a2d259fd03a77db49c0fdc567f9715f918a8896f565262', 'out/samsung-oem-unlock-source/service.json': 'fe134c0607dcb3c141401bdb1aefa69ec1b346c8e37d58ea5a43e66a13c36ffa', 'firmware/samsung-oem-unlock-source/20261106T003602522530Z-035e6d1a0f8642138cdf813af0d04e71.jsonl': '0eb2c95dd807203d516793a7b9e1af7e1d664b65756d8bab2cf445eb57561651', 'out/tooling/20261106T003602522530Z-035e6d1a0f8642138cdf813af0d04e71/receipt.json': '6c58cc07b65e4ad34a1066cd069f2a5cd0d6b80deca31d49c8436306e1d08546', 'out/samsung-oem-unlock-source/binder.json': '21ed05d66c5bd879e5db814ff5f390146c87166cafe968c41a36aa9197f7803c', 'firmware/samsung-oem-unlock-source/20261106T003602522530Z-ea78dce7bc75441a9291a53a43ddcdad.jsonl': '94f7c875acc69a7ff47e369f1a8261222b9c340dd632f33c6bdf70fb85621030', 'out/tooling/20261106T003602522530Z-ea78dce7bc75441a9291a53a43ddcdad/receipt.json': '19f3b740594741080f515f2d53891c689753a4e0690904dd8d0733aeac3b342a', 'out/samsung-oem-unlock-source/ui.json': '1a8d5d1533191deced89c4084dfecd2f02c8329e81ce202ad56b773f4b1a28d0', 'firmware/samsung-oem-unlock-source/20261106T003602551612Z-b21fa2c7654f4f3fb67f92f27b405fd3.jsonl': '47320d0fa0ed78af8630c6c1442461b334c3be79e42072a5eb96b93312e31313', 'out/tooling/20261106T003602551612Z-b21fa2c7654f4f3fb67f92f27b405fd3/receipt.json': 'e3f686fb2b468a49f0930ddf8d3e47f8b2bf8459cc67c43d8b997224d4a7b9f1', 'out/samsung-oem-unlock-source/stub.json': 'c47951937b7ff45e4c06eab3984c97db55868c0356ec07ddd95fe7e88a4fdbb3', 'firmware/samsung-oem-unlock-source/20261106T003654811923Z-21b0f52b53f146f883215a780bba26e7.jsonl': 'b479da92ff77a39bc4493ed1d4abc38d2826249480599f6dfe82da94657a060c', 'out/tooling/20261106T003654811923Z-21b0f52b53f146f883215a780bba26e7/receipt.json': '9f5df9da406b409f48fabe104ee02a1f93a4c1bd3635e19554f5d54a86b7201d', 'out/samsung-oem-unlock-source/proxy.json': 'f1cb25778e3b789da0022e71ec587e9eb92a4a4e2fe024ea06ea67375acde15c', 'firmware/samsung-oem-unlock-source/20261106T003654811423Z-11dc231751614aba869b3bcc0729880e.jsonl': '49855cad057b41928c9b4747888f69393b70aac93e9003513752f0c7622b8724', 'out/tooling/20261106T003654811423Z-11dc231751614aba869b3bcc0729880e/receipt.json': '636c6aa27e1e357ccd13c6b969f6b7b9b6c8cb7226e91e8f3b6c953a0ac3c352', 'out/samsung-oem-unlock-source/aidl.json': 'f54f2d7e79cbb189195f15b5874dfef926ae938f2d241185484a44df8e7f81fc', 'firmware/samsung-oem-unlock-source/20261106T003654792818Z-56016a7d25aa472492533a0a2a8fff8b.jsonl': '09cb4ddca9eaf50c0f5bb33063a477f22a48407fb0f40fbe4ffd5a1910cbf1ac', 'out/tooling/20261106T003654792818Z-56016a7d25aa472492533a0a2a8fff8b/receipt.json': '0a0e8f1a3988fb8a948178256f11f818765d3a344133766731a5f9cc105b56fc', 'out/samsung-oem-unlock-source/pdb.json': '4cff09116d93595bc8961d12c1baf083ea30d60420b0a1fdb7bd56d91a1fe36a', 'firmware/samsung-oem-unlock-source/20261106T003656256157Z-689adcf912964374ba4900ed15b77aa7.jsonl': '009572276cefd23fe6edaf290acb8a81db14c68b7f08da5147279ca26256e178', 'out/tooling/20261106T003656256157Z-689adcf912964374ba4900ed15b77aa7/receipt.json': 'a0fef0a5d645eac35d6fba94071aaad046f9e67ff58a6b73961f32f9506c7fa4', 'out/samsung-oem-unlock-source/pdbservice.json': '7d0475781b70b7e98c8ba1e9f36bdd4c58dab7d15fbf81420685941f3b0fd876', 'firmware/samsung-oem-unlock-source/20261106T003656581356Z-4b7cebb2528243a9b8679c5afd0494b6.jsonl': 'bda126dab12d96f6bcacb509a87a65719c50b691f0797c9516b1cde679722b8c', 'out/tooling/20261106T003656581356Z-4b7cebb2528243a9b8679c5afd0494b6/receipt.json': '7e0287675cba02fc39eb31ad19390b5af597a178ff31e64d902bf717f92e35d2', 'out/samsung-oem-unlock-source/hidl.json': '7773c4df8b55138e5a6f00f5b88d4979336b07902ceac71ad0dd01b4a89f0181', 'firmware/samsung-oem-unlock-source/20261106T003739977481Z-5b276b6c35ca4e0f8456eeaeb701252a.jsonl': '3d6eb105775cd4fc46711988a1380cf5717ecfe23d8278e614abdc92459ea88e', 'out/tooling/20261106T003739977481Z-5b276b6c35ca4e0f8456eeaeb701252a/receipt.json': 'e61bc6300c03120b5064f3ccf388913b9792d9f887a4e72e701e1e12e42acc72', 'out/samsung-oem-unlock-source/pdbbinder.json': '33ed074bbe47f2dfe87582be70b05b543469d498012fd5ab25a7100e402c8465', 'firmware/samsung-oem-unlock-source/20261106T003739976982Z-d167f1b23ae44273a2683019fc849533.jsonl': '4252730ff57fdcd021e8e25e9fe020a6e226fe9afca6bdd33044b4fe08c8052c', 'out/tooling/20261106T003739976982Z-d167f1b23ae44273a2683019fc849533/receipt.json': 'c97c66474dd6c1991be6032890d841f705fc7c7c586553eb808387c92ea2423b', 'out/samsung-oem-unlock-source/halproxy.json': '7e6a6baf60328626723dc3713df0b089587cce5df0cd28c8af5d4ba128dcc7b1', 'firmware/samsung-oem-unlock-source/20261106T003739976982Z-d5a35c49be2b43f1aa354c660f27ede1.jsonl': 'd638091c7ea0b2bb00f956a7e4311d60acd9a8b93b87417b16f63ad20059cf1d', 'out/tooling/20261106T003739976982Z-d5a35c49be2b43f1aa354c660f27ede1/receipt.json': '9c026793606426a67ed28c6138263b2fac32e8bf52516f0644e6fb636a48d096'}  # Literal reviewed identities.

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def need(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    for name, expected in PINS.items():
        need(sha(ROOT / name) == expected, 'Source/evidence drift: ' + name)
    out = ROOT / 'out' / STREAM
    labels = ['service', 'binder', 'ui', 'stub', 'proxy', 'aidl', 'pdb', 'pdbservice', 'hidl', 'pdbbinder', 'halproxy']
    methods, evidence = {}, []
    for label in labels:
        path = out / (label + '.json'); receipt = json.loads(path.read_text())
        need(sha(ROOT / receipt['raw']) == receipt['rawSha256'], 'Raw source receipt identity')
        need(sha(Path(receipt['archive'])) == receipt['archiveSha256'], 'Actual source archive identity')
        need(receipt['readerExitCode'] == 0 and not receipt['oemCodeExecuted'], 'Static reader boundary')
        selected = []
        for line in (ROOT / receipt['raw']).read_text().splitlines():
            row = json.loads(line)
            if row['record'] != 'method':
                continue
            body = row['body']; key = label, body['signature']
            need(key not in methods, 'Unique selected method')
            methods[key] = body
            selected.append({'owner': body['owner'], 'signature': body['signature'], 'accessFlags': body['accessFlags'],
                             'bodySha256': row['normalizedBodySha256'], 'physicalDex': row['physicalDex'],
                             'logicalHeaderOffset': row['logicalHeaderOffset']})
        need(len(selected) == len(receipt['selectedMethodProofs']), 'Complete finite readback')
        evidence.append({'label': label, 'receipt': path.relative_to(ROOT).as_posix(), 'receiptSha256': sha(path),
                         'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'],
                         'archive': receipt['archive'], 'archiveSha256': receipt['archiveSha256'], 'methods': selected})
    checks = []
    def check(label, method, pc, field, expected):
        actual = next(i for i in methods[label, method]['instructions'] if i['pc'] == pc)[field]
        need(actual == expected, 'Exact source assertion ' + label + ' ' + method + ':' + str(pc))
        checks.append({'label': label, 'method': method, 'pc': pc, 'field': field, 'expected': expected})
    check('ui', 'isAvailable()Z', 21, 'reference', 'string=ro.boot.other.locked')
    check('ui', 'isAvailable()Z', 56, 'reference', 'string=1')
    check('ui', 'isAvailable()Z', 62, 'targetPc', 81)
    check('ui', 'isAvailable()Z', 49, 'literal', 0)
    check('ui', 'isAvailable()Z', 81, 'registers', [1])
    check('ui', 'isAvailable()Z', 7, 'reference', 'string=ro.frp.pst')
    check('ui', 'isAvailable()Z', 50, 'targetPc', 81)
    check('ui', 'isAvailable()Z', 68, 'reference', 'Lcom/samsung/android/knoxguard/KnoxGuardManager;->shouldBlockCustomRom()Z')
    check('ui', 'updateState(Landroidx/preference/Preference;)V', 5, 'reference', 'Lcom/android/settings/development/OemUnlockPreferenceController;->isOemUnlockedAllowed()Z')
    check('ui', 'isOemUnlockedAllowed()Z', 2, 'reference', 'Landroid/service/oemlock/OemLockManager;->isOemUnlockAllowed()Z')
    check('service', 'onStart()V', 0, 'reference', 'string=oem_lock')
    check('service', 'onStart()V', 5, 'reference', 'Lcom/android/server/SystemService;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    check('binder', 'isDeviceOemUnlocked()Z', 0, 'reference', 'Landroid/service/oemlock/IOemLockService$Stub;->isDeviceOemUnlocked_enforcePermission()V')
    check('binder', 'isDeviceOemUnlocked()Z', 3, 'reference', 'string=ro.boot.flash.locked')
    check('binder', 'isDeviceOemUnlocked()Z', 13, 'reference', 'string=0')
    check('binder', 'isOemUnlockAllowed()Z', 34, 'reference', 'Lcom/android/server/oemlock/OemLockService;->-$$Nest$msetPersistentDataBlockOemUnlockAllowedBit(Lcom/android/server/oemlock/OemLockService;Z)V')
    helper = '-$$Nest$msetPersistentDataBlockOemUnlockAllowedBit(Lcom/android/server/oemlock/OemLockService;Z)V'
    check('service', helper, 8, 'targetPc', 47)
    check('service', helper, 14, 'targetPc', 47)
    check('service', helper, 34, 'reference', 'Lcom/android/server/pdb/PersistentDataBlockService;->-$$Nest$mdoSetOemUnlockEnabledLocked(Lcom/android/server/pdb/PersistentDataBlockService;Z)V')
    check('service', helper, 39, 'reference', 'Lcom/android/server/pdb/PersistentDataBlockService;->computeAndWriteDigestLocked()Z')
    write = '-$$Nest$mdoSetOemUnlockEnabledLocked(Lcom/android/server/pdb/PersistentDataBlockService;Z)V'
    check('pdbservice', write, 7, 'reference', 'string=rw')
    check('pdbservice', write, 38, 'reference', 'Ljava/nio/channels/FileChannel;->write(Ljava/nio/ByteBuffer;)I')
    check('pdbservice', 'computeAndWriteDigestLocked()Z', 37, 'reference', 'Ljava/nio/channels/FileChannel;->write(Ljava/nio/ByteBuffer;)I')
    check('stub', '<clinit>()V', 0, 'reference', 'string=android.permission.READ_OEM_UNLOCK_STATE')
    check('stub', '<clinit>()V', 2, 'reference', 'string=android.permission.OEM_UNLOCK_STATE')
    check('stub', 'isDeviceOemUnlocked_enforcePermission()V', 12, 'reference', 'Landroid/os/PermissionEnforcer;->enforcePermissionAnyOf([Ljava/lang/String;II)V')
    check('proxy', 'isDeviceOemUnlocked()Z', 12, 'reference', 'string=android.service.oemlock.IOemLockService')
    check('proxy', 'isDeviceOemUnlocked()Z', 19, 'literal', 7)
    check('proxy', 'isDeviceOemUnlocked()Z', 20, 'literal', 0)
    check('proxy', 'isDeviceOemUnlocked()Z', 24, 'reference', 'Landroid/os/Parcel;->readException()V')
    check('proxy', 'isDeviceOemUnlocked()Z', 27, 'reference', 'Landroid/os/Parcel;->readBoolean()Z')
    check('stub', 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 21, 'reference', 'Landroid/service/oemlock/IOemLockService$Stub;->isDeviceOemUnlocked()Z')
    for name, code in [('isOemUnlockAllowed()Z', 6), ('isOemUnlockAllowedByCarrier()Z', 3), ('isOemUnlockAllowedByUser()Z', 5), ('getLockName()Ljava/lang/String;', 1)]:
        check('proxy', name, 19, 'literal', code)
    check('pdbbinder', 'getOemUnlockEnabled()Z', 19, 'reference', 'Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V')
    check('pdbbinder', 'getOemUnlockEnabled()Z', 38, 'reference', 'Ljava/io/DataInputStream;->readByte()B')
    check('binder', 'setOemUnlockAllowedByUser(Z)V', 40, 'targetPc', 105)
    check('binder', 'setOemUnlockAllowedByUser(Z)V', 59, 'targetPc', 97)
    check('binder', 'setOemUnlockAllowedByUser(Z)V', 69, 'targetPc', 89)
    check('binder', 'setOemUnlockAllowedByUser(Z)V', 75, 'reference', 'Lcom/android/server/oemlock/OemLock;->setOemUnlockAllowedByDevice(Z)V')
    calls = [i['reference'] for i in methods['binder', 'isDeviceOemUnlocked()Z']['instructions'] if i['opcode'].startswith('INVOKE')]
    need(calls == ['Landroid/service/oemlock/IOemLockService$Stub;->isDeviceOemUnlocked_enforcePermission()V',
                   'Landroid/os/SystemProperties;->get(Ljava/lang/String;)Ljava/lang/String;',
                   'Ljava/lang/Object;->getClass()Ljava/lang/Class;', 'Ljava/lang/String;->equals(Ljava/lang/Object;)Z'], 'Complete device getter call closure')
    switch = next(i for i in methods['stub', 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']['instructions'] if i['pc'] == 108)
    need(next(x for x in switch['switchElements'] if x['key'] == 7)['offsetFromReferringSwitchPc'] + 13 == 21, 'Actual transaction7 target')
    for name, expected in PINS.items():
        need(sha(ROOT / name) == expected, 'Post-read input identity')
    result = {'schema': 'samsung-oem-unlock-source/v1', 'status': 'STATIC_USERSPACE_GATES_ONLY; NO_UNLOCK_PATH_PROVED',
              'selected': False, 'phoneCalls': False, 'binderQueries': False, 'oemExecuted': False, 'deviceChanged': False,
              'inputPins': PINS, 'methodEvidence': evidence, 'sourceAssertions': checks,
              'selectedMethods': len(methods), 'assertionCount': len(checks),
              'readonlyCandidate': {'service': 'oem_lock', 'descriptor': 'android.service.oemlock.IOemLockService',
                                    'method': 'isDeviceOemUnlocked()Z', 'actualTransaction': 7, 'flags': 0,
                                    'request': 'Interface token only; no setter arguments', 'reply': 'readException then readBoolean',
                                    'permissionAnyOf': ['android.permission.READ_OEM_UNLOCK_STATE', 'android.permission.OEM_UNLOCK_STATE'],
                                    'meaning': 'Property ro.boot.flash.locked exactly equals0. No HAL/PDB/file/setter path in captured getter.',
                                    'notExecuted': True, 'redundantWithAlreadyObservedProperty': True},
              'unsafeAggregateGetter': {'method': 'isOemUnlockAllowed()Z', 'actualTransaction': 6,
                                        'sideEffect': 'HAL-mode/local-PDB-dependent OEM byte and digest writes; may also throw under FRP protection.',
                                        'notReadOnly': True},
              'capturedUiGate': {'method': 'OemUnlockPreferenceController.isAvailable()Z',
                                 'falseIf': ['ro.frp.pst empty', 'ro.boot.other.locked exactly1', 'KnoxGuard.shouldBlockCustomRom true', 'OemLockManager absent'],
                                 'observedOtherLocked': '1', 'capturedUiPrediction': 'unavailable',
                                 'currentSettingsHashObservedInFreshSix': False},
              'limits': ['Current framework/services hash match is observed; captured Settings equality to current installed Settings is not established by that six-file observation.',
                         'Service instance/backend/HAL selection and permission grant not queried; constructing/probing HAL availability is not a passive substitute.',
                         'Separate carrier/user getters delegate to HAL or PDB fallback; native HAL side effects unclosed, PDB user fallback reads partition byte and is outside current no-raw-partition scope.',
                         'KG0x4 and EM0x0 meanings are unassigned in this finite audit.',
                         'UI hiding, allowed state, persistent allow byte and actual bootloader unlock are different states. No native bootloader implementation/capability or feasible unlock chain proved.',
                         'No UI/property/root patch, setters, broadcasts, FRP access, reboot/unlock/flash command or modifying action performed or proposed.']}
    inventory = ROOT / 'inventory' / (STREAM + '.json')
    inventory.write_text(json.dumps(result, indent=2) + '\n')
    (out / 'checks.json').write_text(json.dumps({'pass': True, 'sourceAssertions': len(checks), 'selectedMethods': len(methods), 'binderQueries': False, 'oemExecuted': False}, indent=2) + '\n')
    print(json.dumps({'pass': True, 'sourceAssertions': len(checks), 'selectedMethods': len(methods), 'binderQueries': False}))

if __name__ == '__main__':
    main()
