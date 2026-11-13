"""Replay original permission checks and exact Samsung-to-ColorOS AM wire proof."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAM = 'authority-permission-binding'
PINS = {
    "out/authority-permission-binding/coloros-activitythread-permission.json": "2e07abf597487f85cf904818c776729e5e78aebbd7f3a08b80721ae2ab5bc3ab",
    "out/authority-permission-binding/coloros-am-component-permission.json": "8a13b4bfab95d126c1e9f50e09f17159045e5117a6005d8bb71a4966a698f3a3",
    "out/authority-permission-binding/coloros-am-factory.json": "404665fc5deaf01878db946e6a60446556e9543b37ca22ac77630a2dcfa39518",
    "out/authority-permission-binding/coloros-am-initializer.json": "9c757cfd0f0bc8bba6648f3559f4ef010cf93e220210f0d22eca9e787fa2ebbd",
    "out/authority-permission-binding/coloros-am-permission-service.json": "7839a294bef16683ebb901ae84d25d5026bdd38d65353c88146fa5717e624f68",
    "out/authority-permission-binding/coloros-am-proxy.json": "8f0d9f4717130b5e84cd00bb57c6af2692a76d439846f58d853d7e0d0aa0c296",
    "out/authority-permission-binding/coloros-am-stub.json": "30587c9e11b972e8b99044f1fd57e1653e0355fb8e67663a75947897ecb757c1",
    "out/authority-permission-binding/coloros-appglobals-permission.json": "e1822d064176a552a0130f08b6afbf99df1849e6040fc2a621ae93790357bd52",
    "out/authority-permission-binding/coloros-framework-component-permission.json": "7b39c64ca9b5e95ab7d87d10ee677a54653a5da23ab6e6c1a93752fbb3a2523d",
    "out/authority-permission-binding/coloros-ipm-proxy.json": "d65419fb1d1b673632a610777c940b56d9a391aa5d71f9c273c0b79ea8830cb3",
    "out/authority-permission-binding/coloros-ipm-stub.json": "009f3cf880252c96c8162347d0b58ed5ee3eed95c53d9fa68819c558e2d739f3",
    "out/authority-permission-binding/coloros-permission-initializer.json": "0ceec118910c478c72edaeda05a4cd37ff962f4de3e86195b31f8a70839d7de3",
    "out/authority-permission-binding/coloros-permission-service.json": "5fcac99ef8d62d8c944f716b5bedc5d9d5cc046e98476790077e5a7dc4c2e991",
    "out/authority-permission-binding/coloros-permission-state-check.json": "2366b1edd02aaba2ee5cf6138531f31e2556780e221273b94b156e6993aee2b9",
    "out/authority-permission-binding/coloros-permission-state-owner.json": "66029a24609dfa181c7c3cbb5bdaa0e68fb2a0ca74a7215e3eef349d43296d01",
    "out/authority-permission-binding/coloros-persistent-device.json": "1e2d7756394e19724f5f8ed795d791f2bd3c7fe6b33f95e297581b151b150851",
    "out/authority-permission-binding/samsung-activity-service.json": "167919e89a8a45499bf6efea5c1ed7e08d842f72711b35b9f9887f9152ba0ed4",
    "out/authority-permission-binding/samsung-am-factory.json": "a44a2055d0faf0eac910b74983f91f06381b84c09429d59cad33b42f3a16a025",
    "out/authority-permission-binding/samsung-am-initializer.json": "27e911bef503f63e1cc93351d695e101aa36c3128aad9e6ad76aa5d64b2cd907",
    "out/authority-permission-binding/samsung-am-permission-stub-helper.json": "2099a0b3618e82a2649b3a182beb1782d16a2ab61c24a71f33652e4da7069b05",
    "out/authority-permission-binding/samsung-am-proxy.json": "8e008b4429fd082bf0bc24bdedb3a4c5d7a0ae4195f15acedc09402e3a694d9e",
    "out/authority-permission-binding/samsung-am-stub.json": "046125956771f65609baabe19acf18b5eeac2e5518336dafe261b4767683abde",
    "out/authority-permission-binding/samsung-cache-disable-current.json": "5a201e027a92b9a7d6e0d23ed5279d02dbd5141f0b9e1dba35efa179520281ed",
    "out/authority-permission-binding/samsung-cache-disable-instance.json": "a379a5378293611959f39180289701f4414e38ffd6d96a4e80dab20465f04e42",
    "out/authority-permission-binding/samsung-cache-disable-named.json": "c6f566abe2a276f79cfba2ba2f15b898b0fd212516380a7b53375bb07f1701f3",
    "out/authority-permission-binding/samsung-cache-disable.json": "647168487c67143f9abbeecf4ec19caa71aac23042d74cd171f1fa9d4c52de6f",
    "out/authority-permission-binding/samsung-cache-disabled-state.json": "2f27085785524b8c85a11256f02e9ff1cd5ea9cba6a3ff1550540297becfc432",
    "out/authority-permission-binding/samsung-cache-query-behavior.json": "6746a330c7874e678be55d52b3c7cff819b5fe366ff5407108793325926ba94e",
    "out/authority-permission-binding/samsung-cache-reserved-nonce.json": "db62e3aeeac032c796646ca6d11ab1e77b7656033d6103b30c345d445b8d47b5",
    "out/authority-permission-binding/samsung-cachemap-clear.json": "4d7d60c9e993c4a37b3132400c6c9523a29d573e18e8699c760079b1fdf2358c",
    "out/authority-permission-binding/samsung-context-checks.json": "00d08b72dd8d37de383fedd4a729df1e92db35f765f35db488f0f2c9f09301ae",
    "out/authority-permission-binding/samsung-context-enforce.json": "cf8243bad9a2df23d1b96c16a42fdffc858db1976b548a356772c0cbbd05dd5f",
    "out/authority-permission-binding/samsung-lss-checks.json": "912e6c81ce9aabb22605d3596a326cb471db9acd071c11d8d868f2dcf93758ce",
    "out/authority-permission-binding/samsung-permission-checks.json": "467b1e3fe1b722e865272260af5b92cb5b942ffe89205d25e9c7d49bf87e4e35",
    "out/authority-permission-binding/samsung-permission-initializer.json": "7c67c23ad8820e4c8dd7613b29acfe1bdc48afc488bba60aaa63ed123f89c0d4",
    "out/authority-permission-binding/samsung-permission-query.json": "a25a2db5e63d4bbf8e3ca18fb0ce0f82330ef4024a12af705354426a513a9c42",
    "out/authority-permission-binding/samsung-permission-recompute.json": "810aa31e07f2e0a87f1bde2b2d13d02e4d76e57ca7e12b7f196a6f0d26d8bfcc",
    "out/authority-permission-binding/samsung-user-appid.json": "ecdc9c1b110370645f7c3582815c8d7cf8a3f4ab9832aeeaa19c866735360045",
    "inventory/binder-direct-dispatch-source.json": "dad6a98b5a42e94aa2610446aa3339e88e2e58ad4dc05d65dd2737716c5417fe",
    "inventory/construction-protocol.json": "aa2baaa0b449d5f93a4b796704176659ad54315a082547cb06c39f3acff13d18",
    "inventory/local-locksettings-contract.json": "06f8e5b00e27e1e57fae7bb9ed9c225ba4de4dc6c244f6cdf5e24894ce9e86c0"
}  # FROZEN_PINS


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text())


def rows(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def case_entry(body, code):
    for instruction in body['instructions']:
        if not instruction['opcode'].endswith('SWITCH'):
            continue
        payload = next(i for i in body['instructions'] if i['pc'] == instruction['targetPc'])
        for element in payload.get('switchElements', []):
            if element['key'] == code:
                return instruction['pc'] + element['offsetFromReferringSwitchPc']
    return None


def main():
    if not PINS:
        raise ValueError('Unfrozen evidence')
    for path, expected in PINS.items():
        if sha(ROOT / path) != expected:
            raise ValueError('Evidence drift: ' + path)
    receipts, methods, proofs, archives = {}, {}, {}, {}
    for path in PINS:
        if not path.startswith('out/' + STREAM + '/'):
            continue
        r = load(path)
        if r['readerExitCode'] or not r['archiveAndToolPinsVerifiedBeforeAndAfter']:
            raise ValueError('Reader admission')
        if sha(ROOT / r['raw']) != r['rawSha256']:
            raise ValueError('Raw changed')
        label = Path(path).stem
        receipts[label] = r
        archives[r['archive']] = r['archiveSha256']
        for record in rows(r['raw']):
            if record['record'] != 'method':
                continue
            body = record['body']
            key = label + ':' + body['owner'] + '->' + body['signature']
            methods[key] = body
            proofs[key] = {'archiveSha256': r['archiveSha256'],
                'bodySha256': record['normalizedBodySha256'], 'raw': r['raw'], 'rawSha256': r['rawSha256'],
                'physicalDex': record['physicalDex'], 'logicalHeaderOffset': record['logicalHeaderOffset']}
    for path, expected in archives.items():
        if sha(path) != expected:
            raise ValueError('Input archive drift')
    assertions = []
    def at(key, pc, **expected):
        instruction = next(i for i in methods[key]['instructions'] if i['pc'] == pc)
        if any(instruction.get(name) != value for name, value in expected.items()):
            raise ValueError('Source instruction changed: ' + key + ':' + str(pc))
        assertions.append({'proof': key, 'pc': pc, **expected})
    context = 'samsung-context-checks:Landroid/app/ContextImpl;->'
    at(context + 'checkCallingOrSelfPermission(Ljava/lang/String;)I', 2,
       reference='Landroid/os/Binder;->getCallingPid()I')
    at(context + 'checkCallingOrSelfPermission(Ljava/lang/String;)I', 6,
       reference='Landroid/os/Binder;->getCallingUid()I')
    at(context + 'checkCallingOrSelfPermission(Ljava/lang/String;)I', 10, registers=[2, 3, 0, 1])
    at(context + 'checkPermission(Ljava/lang/String;II)I', 52,
       reference='Landroid/permission/PermissionManager;->resolveDeviceIdForPermissionCheck(Landroid/content/Context;ILjava/lang/String;)I')
    at(context + 'checkPermission(Ljava/lang/String;II)I', 56, registers=[2, 3, 4, 1])
    lss = 'samsung-lss-checks:Lcom/android/server/locksettings/LockSettingsService;->'
    for name in ['checkReadPermission()V', 'checkWritePermission()V']:
        at(lss + name, 2, reference='string=android.permission.ACCESS_KEYGUARD_SECURE_STORAGE')
        at(lss + name, 8, reference='Landroid/content/Context;->enforceCallingOrSelfPermission(Ljava/lang/String;Ljava/lang/String;)V')
    at(lss + 'checkDatabaseReadPermission(ILjava/lang/String;)V', 3,
       reference='Lcom/android/server/locksettings/LockSettingsService;->hasPermission(Ljava/lang/String;)Z')
    at(lss + 'checkDatabaseReadPermission(ILjava/lang/String;)V', 50, opcode='THROW')
    at('samsung-context-enforce:Landroid/app/ContextImpl;->enforce(Ljava/lang/String;IZILjava/lang/String;)V',
       94, opcode='THROW')
    manager = 'samsung-permission-checks:Landroid/permission/PermissionManager;->'
    at(manager + 'checkPermission(Ljava/lang/String;III)I', 0,
       reference='Landroid/os/UserHandle;->getAppId(I)I')
    at(manager + 'checkPermission(Ljava/lang/String;III)I', 4, literal=1000)
    at(manager + 'checkPermission(Ljava/lang/String;III)I', 29, literal=0)
    at(manager + 'checkPermissionUncached(Ljava/lang/String;III)I', 38,
       reference='Landroid/app/IActivityManager;->checkPermissionForDevice(Ljava/lang/String;III)I',
       registers=[0, 2, 3, 4, 5])
    at('samsung-user-appid:Landroid/os/UserHandle;->getAppId(I)I', 0, literal=100000)

    am = 'Landroid/app/IActivityManager$Stub;'
    proxy = 'Landroid/app/IActivityManager$Stub$Proxy;'
    transact_sig = 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'
    query_sig = 'checkPermissionForDevice(Ljava/lang/String;III)I'
    wire = {}
    for side, code in [('samsung', 287), ('coloros', 264)]:
        key = side + '-am-proxy:' + proxy + '->' + query_sig
        body = methods[key]
        base = body['registerCount'] - 5
        for pc, method, register in [(17, 'writeString(Ljava/lang/String;)V', base + 1),
                                     (20, 'writeInt(I)V', base + 2),
                                     (23, 'writeInt(I)V', base + 3),
                                     (26, 'writeInt(I)V', base + 4)]:
            instruction = next(i for i in body['instructions'] if i['pc'] == pc)
            if instruction['registers'][1] != register:
                raise ValueError('Subject parameter provenance')
            at(key, pc, reference='Landroid/os/Parcel;->' + method)
        at(key, 31, literal=code)
        at(key, 33, literal=0)
        stub_key = side + '-am-stub:' + am + '->' + transact_sig
        case = case_entry(methods[stub_key], code)
        expected_case = 799 if side == 'samsung' else 332
        if case != expected_case:
            raise ValueError('Actual Stub case changed')
        at(stub_key, 10 if side == 'samsung' else 18,
           reference='Landroid/os/Parcel;->enforceInterface(Ljava/lang/String;)V')
        if side == 'samsung':
            at(stub_key, 799, reference=am + '->onTransact$checkPermissionForDevice$(Landroid/os/Parcel;Landroid/os/Parcel;)Z')
            decode_key = 'samsung-am-permission-stub-helper:' + am + '->onTransact$checkPermissionForDevice$(Landroid/os/Parcel;Landroid/os/Parcel;)Z'
            read_pcs, trailing, invoke, no_exception, result = [0, 4, 8, 12], 16, 19, 23, 26
        else:
            decode_key = stub_key
            read_pcs, trailing, invoke, no_exception, result = [332, 336, 340, 344], 348, 351, 355, 358
        for n, pc in enumerate(read_pcs):
            at(decode_key, pc, reference='Landroid/os/Parcel;->' +
               ('readString()Ljava/lang/String;' if n == 0 else 'readInt()I'))
        at(decode_key, trailing, reference='Landroid/os/Parcel;->enforceNoDataAvail()V')
        at(decode_key, invoke, reference=am + '->' + query_sig)
        at(decode_key, no_exception, reference='Landroid/os/Parcel;->writeNoException()V')
        at(decode_key, result, reference='Landroid/os/Parcel;->writeInt(I)V')
        wire[side] = {'code': code, 'proxyProof': key, 'stubProof': stub_key,
                      'casePc': case, 'decoderProof': decode_key,
                      'readPcs': read_pcs, 'enforceNoDataAvailPc': trailing,
                      'invokePc': invoke, 'writeNoExceptionPc': no_exception, 'writeResultPc': result}
    if case_entry(methods['coloros-am-stub:' + am + '->' + transact_sig], 287) is not None:
        raise ValueError('Guest source code287 now reaches another case')
    query_class = 'samsung-permission-query:Landroid/permission/PermissionManager$PermissionQuery;->'
    cache_key_fields = {}
    for signature in ['equals(Ljava/lang/Object;)Z', 'hashCode()I']:
        fields = sorted({i['reference'].split('->')[1].split(':')[0] for i in methods[query_class + signature]['instructions']
                         if i.get('reference', '').startswith('Landroid/permission/PermissionManager$PermissionQuery;->')})
        if fields != ['deviceId', 'permission', 'uid']:
            raise ValueError('Permission-cache equality/hash scope changed')
        cache_key_fields[signature] = fields
    at('samsung-cache-disable-instance:Landroid/app/PropertyInvalidatedCache;->disableInstance()V', 4,
       reference='Landroid/app/PropertyInvalidatedCache;->mDisabled:Z')
    at('samsung-cachemap-clear:Landroid/app/PropertyInvalidatedCache$CacheMap;->clear()V', 2,
       reference='Landroid/util/SparseArray;->clear()V')
    at('samsung-cache-query-behavior:Landroid/app/PropertyInvalidatedCache;->query(Ljava/lang/Object;)Ljava/lang/Object;', 54,
       reference='Landroid/app/PropertyInvalidatedCache;->recompute(Ljava/lang/Object;)Ljava/lang/Object;')
    nonce = 'samsung-cache-reserved-nonce:Landroid/app/PropertyInvalidatedCache;->isReservedNonce(J)Z'
    if methods[nonce]['registerCount'] != 4 or methods[nonce]['catches'] or len(methods[nonce]['instructions']) != 10:
        raise ValueError('Reserved-nonce helper shape changed')
    for pc, expected in [
            (0, dict(opcode='CONST_WIDE_16', registers=[0], literal=0)),
            (2, dict(opcode='CMP_LONG', registers=[0, 2, 0])),
            (4, dict(opcode='IF_LTZ', registers=[0], targetPc=14)),
            (6, dict(opcode='CONST_WIDE_16', registers=[0], literal=3)),
            (8, dict(opcode='CMP_LONG', registers=[2, 2, 0])),
            (10, dict(opcode='IF_GTZ', registers=[2], targetPc=14)),
            (12, dict(opcode='CONST_4', registers=[2], literal=1)),
            (13, dict(opcode='RETURN', registers=[2])),
            (14, dict(opcode='CONST_4', registers=[2], literal=0)),
            (15, dict(opcode='RETURN', registers=[2]))]:
        at(nonce, pc, **expected)
    cache_query = 'samsung-cache-query-behavior:Landroid/app/PropertyInvalidatedCache;->query(Ljava/lang/Object;)Ljava/lang/Object;'
    for pc, expected in [
            (0, dict(reference='Landroid/app/PropertyInvalidatedCache;->isDisabled()Z', registers=[9])),
            (3, dict(opcode='MOVE_RESULT', registers=[0])),
            (4, dict(opcode='CONST_WIDE_16', registers=[1], literal=1)),
            (6, dict(opcode='IF_NEZ', registers=[0], targetPc=13)),
            (13, dict(opcode='MOVE_WIDE', registers=[3, 1])),
            (14, dict(reference='Landroid/app/PropertyInvalidatedCache;->isReservedNonce(J)Z', registers=[3, 4])),
            (17, dict(opcode='MOVE_RESULT', registers=[0])),
            (18, dict(opcode='IF_NEZ', registers=[0], targetPc=28)),
            (28, dict(reference='Landroid/app/PropertyInvalidatedCache;->isReservedNonce(J)Z', registers=[3, 4])),
            (31, dict(opcode='MOVE_RESULT', registers=[0])),
            (32, dict(opcode='IF_EQZ', registers=[0], targetPc=59)),
            (34, dict(reference='Landroid/app/PropertyInvalidatedCache;->mDisabled:Z', registers=[0, 9])),
            (36, dict(opcode='IF_NEZ', registers=[0], targetPc=54))]:
        at(cache_query, pc, **expected)
    am_component = 'coloros-am-component-permission:Lcom/android/server/am/ActivityManagerService;->checkComponentPermission(Ljava/lang/String;IIIIZ)I'
    at(am_component, 0, reference='Lcom/android/server/am/ActivityManagerService;->MY_PID:I')
    at(am_component, 10, reference='Lcom/android/server/am/IActivityManagerServiceExt$IStaticExt;->checkSafeWindowPermission(Ljava/lang/String;II)Z')
    at(am_component, 37, reference='Landroid/content/pm/ProcessInfo;->deniedPermissions:Landroid/util/ArraySet;')
    at('coloros-framework-component-permission:Landroid/app/ActivityManager;->checkComponentPermission(Ljava/lang/String;IIIZ)I', 90,
       reference='Landroid/permission/IPermissionManager;->checkUidPermission(ILjava/lang/String;I)I')
    native = load('inventory/binder-direct-dispatch-source.json')
    native_declarations = []
    for declaration in native['declarations']:
        if declaration['owner'] != 'Landroid/os/Binder;':
            continue
        for method in declaration['methods']:
            if method['signature'] in ['getCallingUid()I', 'getCallingPid()I']:
                if method['accessFlags'] != 281:
                    raise ValueError('Native Binder caller shape changed')
                native_declarations.append({'role': declaration['role'], **method})
    if len(native_declarations) != 4:
        raise ValueError('Native caller declaration scope')
    routes = load('inventory/construction-protocol.json')['operations']
    if len(routes) != 33:
        raise ValueError('Public route baseline changed')
    output = {
        'schema': 'authority-permission-binding/v1', 'status': 'SOURCE_BINDING_PROPOSAL_NOT_LIVE_PERMISSION_ACCEPTANCE',
        'selected': False, 'runtimeCodeAddedByThisAudit': False, 'publicCredentialRoutesChanged': False,
        'sourcePins': PINS, 'archives': archives, 'methodProofs': proofs, 'sourceBodyCount': len(methods),
        'revision': {'reason': 'Pin original reserved-nonce classification needed for disabled-query recomputation',
            'initialFreezeHistory': 'out/authority-permission-binding/history-initial-freeze/manifest.json'},
        'instructionAssertions': assertions, 'nativeCallerDeclarationsReused': native_declarations,
        'selectedLssPermission': 'android.permission.ACCESS_KEYGUARD_SECURE_STORAGE',
        'lssChecks': {'readAndWrite': 'original Context.enforceCallingOrSelfPermission',
            'databaseRead': 'hasPermission -> Context.checkCallingOrSelfPermission; original user/key are used in denial text, no independent user admission here',
            'denial': 'original SecurityException, never default grant'},
        'subjectProvenance': ['actual canonical Binder native getCallingPid/getCallingUid at ContextImpl PCs2/6',
            'Context permission/device resolution passes original full pid/uid unchanged',
            'PermissionQuery fields retain original permission,pid,uid,deviceId',
            'uncached AM method receives exact same explicit subject values',
            'outbound remote caller is authority process, while queried subject remains original payload; no clear/hop/ID rewrite allowed'],
        'wire': {'descriptor': 'android.app.IActivityManager', 'method': query_sig,
            'payloadAfterToken': ['nullable String via writeString/readString', 'int pid', 'int uid', 'int deviceId'],
            'flags': 0, 'reply': ['original exception envelope', 'actual int permission result'],
            'sides': wire, 'guest287': 'no actual Stub switch case; Binder fallback',
            'legacyCheckPermission': {'sourceCode': 9, 'guestCode': 9, 'reachedBySelectedUncachedPath': False}},
        'serviceLookups': {'samsungActivityManager': 'ActivityManager.getService -> IActivityManagerSingleton -> ActivityManager$4.create: activity getServicePC2/asInterfacePC6',
            'guestPermissionManager': 'AppGlobals -> ActivityThread.sPermissionManager cache; permissionmgr getServicePC10/asInterfacePC14',
            'guestInnerProtocol': 'IPermissionManager.checkUidPermission(uid,permission,deviceId), proxy code31/flags0',
            'lookupOrDescriptorIsAuthorityProof': False},
        'originalPolicy': {'samsungAppIdShortcut': {'getAppIdModulo': 100000, 'grantForAppIds': [0, 1000], 'beforeCacheAndIpc': True},
            'contextRenouncedSelfPermissionCheckPreserved': True,
            'selectedPermissionDeviceResolution': 'ACCESS_KEYGUARD is outside original CAMERA/RECORD_AUDIO device-aware set; source resolves deviceId0',
            'guestDefaultPersistentDeviceId': 'default:0',
            'guestAm': ['null permission -> -1', 'supplied pid==AMS.MY_PID grants before later checks',
                'real vendor safe-window hook', 'actual per-process deniedPermissions',
                'framework component rules and real permission-manager path'],
            'guestPermissionService': ['real vendor shouldSkip/hook', 'optional actual CheckPermissionDelegate',
                'actual LocalServices PermissionManagerServiceInterface, supplied by AccessCheckingService PermissionService',
                'actual user/package/SystemConfig/AccessCheckingService.state and permission policies'],
            'copiedPackagePermissionTableOrFreshEmptyServiceAllowed': False},
        'cache': {'permissionQueryStoresPid': True, 'equalityAndHashFields': cache_key_fields,
            'pidPartOfCacheKey': False, 'cacheHitEstablishesCurrentGuestPerPidPolicy': False,
            'disabledRecomputeProof': {'nonceHelper': nonce, 'queryProof': cache_query,
                'reservedNonceInclusiveRange': [0, 3], 'disabledNonce': 1, 'disabledNonceIsReserved': True,
                'sourcePath': 'isDisabledPC0 -> nonce1PC4/13 -> reservedPC14 -> branch18to28 -> reservedPC28 -> branch32 falls through -> mDisabledPC34 -> branch36to54 -> recomputePC54',
                'kind': 'Static instruction/control-flow deduction; no OEM execution or query drain'},
            'sourceSupportedPreparation': 'original Samsung PermissionManager.disablePermissionCache before first admitted query under cold/quiesced same-realm ownership, pending prepared owner/API integration review',
            'disableEffects': ['source-local named checkPermission cache group: set matching mDisabled, clear local entries and increment clear counter',
                'record disabled cacheName in local static sDisabledKeys for this source cache registry',
                'disabled query recomputes through original PermissionManager$1 and actual AM query',
                'no permission grant, package-table copy, global property write or remote permission mutation in selected disable chain'],
            'executed': False, 'hiddenInsideTransportBridge': False,
            'outstandingQueryOrResultDrainEstablishedByDisable': False,
            'preparationRequiresNoEarlierInflightQueryOrStaleAcceptedResult': True,
            'shortcutGrantForAppId0Or1000StillRemains': True},
        'preparedBindingProposal': {'route': 'Samsung287 -> genuine current ColorOS264 only',
            'owner': 'actual admitted initialized guest AM and permission-state publication, retained same source/profile/process/native/user generation',
            'sourceClientView': 'same-realm original Samsung IActivityManager.Stub.asInterface over the one-method bridge; canonical Binder/Parcel',
            'narrowIntegrationSite': 'PermissionManager.checkPermissionUncached original ActivityManager.getService atPC0 needs a reviewed permission-specific prepared view; do not globally replace activity or seed a partial general AM Singleton',
            'wireBehavior': 'fresh owned request with exact original String/pid/uid/deviceId; borrowed reply, actual transact boolean/errors unchanged; no result fabrication',
            'separatePreparation': ['admit actual endpoint/code/state owner; name/descriptor/holder/UID alone is insufficient',
                'prepare process-local original cache currentness/disable separately before first check; cold/quiesced same-realm source ownership and prior-query/result drain are required',
                'keep actual native incoming caller provenance and feature caller/user/profile/operation admission before original LSS',
                'retain source client/view/target through all actual checks, child work and retirement/death drain; no silent rebind to another service generation'],
            'component': 'separately root-approved authored PreparedSamsungPermissionBridge; its construction/build is not live binding or installation'},
        'limits': ['Original source/body and wire evidence only; no OEM, Binder-native, Android, permission-state or phone execution.',
            'Native caller getters have declarations only in these Java proofs; same Java thread is not kernel identity acceptance.',
            'Actual installed OneOS UID/native behavior, active class/APEX definitions, vendor hooks/delegates and effective service/cache namespaces still need profile/runtime admission.',
            'Real permission result0 is not backend authority, cryptographic authentication, scoped operation ownership or readiness.',
            'A direct IPermissionManager shortcut would omit reached AM per-process/vendor policy and is not this proposal.',
            'Accepted OneOS permissive SELinux/relaxed privileged permissions remain disclosed; no new global Enforcing gate or global permission changes.'],
        'audit': {'pass': True, 'oemCodeExecuted': False, 'androidExecuted': False, 'phoneActions': []},
        'toolSha256': sha(__file__)}
    destination = ROOT / 'inventory/authority-permission-binding.json'
    destination.write_text(json.dumps(output, indent=2) + '\n')
    result = {'pass': True, 'sourceBodies': len(methods), 'instructionAssertions': len(assertions),
              'permissionRoute': '287->264', 'runtimeBindingImplementedByAudit': False,
              'inventorySha256': sha(destination), 'toolSha256': sha(__file__)}
    (ROOT / 'out' / STREAM / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
