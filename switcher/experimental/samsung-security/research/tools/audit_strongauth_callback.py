"""Replay bounded static StrongAuth proofs; never execute OEM classes or methods."""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parent.parent
STREAM = 'strongauth-callback-adapter'
TRACKER = 'Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker;'
CALLBACK = 'Landroid/app/trust/IStrongAuthTracker$Stub$Proxy;'
# Literal receipt identities are filled from the frozen, independently hashed reads.
PINS = {
    "out/strongauth-callback-adapter/coloros-exception.json": "652778b5e2aab8488901f4173eaf37a15fa632051499f239b66fa4f1f5345a85",
    "out/strongauth-callback-adapter/coloros-framework-eligibility-xref.json": "3b733008ac0246a214acbca1e8a2a770986b7e02d6db0c36407b489a29d4a31a",
    "out/strongauth-callback-adapter/coloros-handler.json": "e4ef366e0c65b612872602bc3db7def0bcbeb7687323369c2c75bb43a0d7148e",
    "out/strongauth-callback-adapter/coloros-proxy.json": "76398ef5d9ff7881ec5780fb21bef4d5cd17f1bc79ac97a8de2016206d61e814",
    "out/strongauth-callback-adapter/coloros-queue.json": "c85b5cc26b6e6709d6c873f779f090ca2ccd553c0bbac936f9fd2621a24526a7",
    "out/strongauth-callback-adapter/coloros-stub.json": "ad051345935a1a30bbea7418ee3c87db9eb8d68e8aff16016890698bd947bb63",
    "out/strongauth-callback-adapter/coloros-system-server-services-eligibility-xref.json": "317a293d7b4a420eccb16d1a47a9eb70b97b01b5171ae64598d8facda74101fd",
    "out/strongauth-callback-adapter/coloros-systemui-caller-0.json": "e790c851472048c213e2532e6855b2101ee96824f65f663cab829fce427a9134",
    "out/strongauth-callback-adapter/coloros-systemui-caller-1.json": "3d92d1e8dbf1811458e2ae945169ba7a8a5b4031e5a24280d00d5ceb9f20c60b",
    "out/strongauth-callback-adapter/coloros-systemui-caller-2.json": "5a85f53b19dd4a52271bbe13e891a278f2f51aabf574dc37936ba99c3b693828",
    "out/strongauth-callback-adapter/coloros-systemui-eligibility-xref.json": "8e6a067ca9597ac4d930e44069f090c5725c0d4fc97110605b643a205dab72fa",
    "out/strongauth-callback-adapter/coloros-tracker.json": "54d8313258da2a0db2976a294c2ab7813710ad08510b74e8d9c07ff8e154ec8d",
    "out/strongauth-callback-adapter/samsung-framework-eligibility-xref.json": "dafa99aed5c0d5f169e108e0cd5f1ed285457303a1e33433ced966792b7ec4c6",
    "out/strongauth-callback-adapter/samsung-handler.json": "15044204d142c3f064108187cc595855a2a68722ab099cb4a65503553d38a85b",
    "out/strongauth-callback-adapter/samsung-owner.json": "529766bb237b5dd021d7cd42faf37afd66743f6cbc17bcf6354fcc362c9aeb03",
    "out/strongauth-callback-adapter/samsung-proxy.json": "7fd4500c8ce107d10d2a1b64459d6eedafcd5dc361b9f804d3a541934ec0db5f",
    "out/strongauth-callback-adapter/samsung-queue.json": "90e9af9418e207c22d52938518f56d78f177bc7c159cf310907f4be888da8ce3",
    "out/strongauth-callback-adapter/samsung-stub.json": "76d7434783c6dce1fa23bc26ffa2545da9dc6992c7647146b5ce66e8daafbbd5",
    "out/strongauth-callback-adapter/samsung-synchronized-query.json": "fa2515acd4b2c3bd4ed76f7e08405963eeefb9a9aedc1c35e3dbac273095fd94",
    "out/strongauth-callback-adapter/samsung-system-server-services-caller-0.json": "6e1f67d81de50fc3433e38115e3c9ef0e581c55a713b992c82529f05b8eff81c",
    "out/strongauth-callback-adapter/samsung-system-server-services-eligibility-xref.json": "38ce321569e7bdcde3cb6a89be299f7205c63f641ae1581543e4dc202c90760e",
    "out/strongauth-callback-adapter/samsung-systemui-caller-0.json": "1667e3a8b62f30cac8b689a4992d05ca7300f32f44b0a01c9e5d7cf602e13770",
    "out/strongauth-callback-adapter/samsung-systemui-caller-1.json": "3b09ff927858fb9126d4ab13c5735b67df1d4526d7b32471382ea2e3b111b787",
    "out/strongauth-callback-adapter/samsung-systemui-caller-2.json": "9980de401ccabff17f3e4771dc86d29284c398efff654c5c0026e64ea0841499",
    "out/strongauth-callback-adapter/samsung-systemui-caller-3.json": "980bdb73de5b44ed01b9d072ddf75689d80a48583882159553089a0750867158",
    "out/strongauth-callback-adapter/samsung-systemui-eligibility-xref.json": "0b83080cd646a5de46fb17125d2def2c50fec0c97406f22602d05483a09d4442",
    "out/strongauth-callback-adapter/samsung-tracker.json": "dafb6cf4c0b54f65b05d808a9bee12f902cb1810713bd5312138aab055f85bde",
    "inventory/construction-protocol.json": "aa2baaa0b449d5f93a4b796704176659ad54315a082547cb06c39f3acff13d18",
    "inventory/credentials.json": "333118f3876c61f641d9a8aae82bd11ed61d6366a28e916ddd58755c4a5ef3b8",
    "inventory/strong-auth-gating.json": "ed61471281b56c2b5741e7316d393d52dd0627274fc5292e35321207954836fd",
    "out/construction-protocol/lockpattern-bodies.json": "029f58728e22ef9298e6957b30ed8902fd052c4bcc9a4247c5d62eef240601e3",
    "firmware/credentials/20261105T123455400710Z-abcf752d9c6d43dc800809479c2547f3.jsonl": "be4e73939f072ca0358a5af212e25f69e9214a44206607ef8100f8dfa40c14fd",
    "out/tooling/20261105T123455400710Z-abcf752d9c6d43dc800809479c2547f3/receipt.json": "3f0f3b0773ccf75ddfa9e6243d5fa32be783ef7e88bf8c4a82b13277f18a93da",
    "firmware/credentials/20261105T123455989311Z-d85a85b57c2a4cc9a8f8601e054ece2d.jsonl": "0e2f4ef54cb3c52fe835cdd7d06391b61eb2db52514b8f597c0bcc894d18047b",
    "out/tooling/20261105T123455989311Z-d85a85b57c2a4cc9a8f8601e054ece2d/receipt.json": "9c7365079d5655d71bd562096afe676f09a0e09fd87da96fa6dbb43c1075c2e4",
    "firmware/strongauth-callback-adapter/caller-tracker-declarations.json": "907a84906c9bcd9b16d210f36f93649a3054d1de5349db04da88611603a41ae0"
}  # FROZEN_PINS


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def checked(path, expected):
    p = ROOT / path
    if sha(p) != expected:
        raise ValueError('Pinned evidence changed: ' + path)
    return p


def raw_records(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def uleb(data, pos):
    value = 0
    for n in range(5):
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << (7 * n)
        if not byte & 128:
            if n == 4 and byte > 15:
                raise ValueError('ULEB overflow')
            return value, pos
    raise ValueError('Unterminated ULEB')


def static_ints(receipt):
    """Decode only the selected ordinary-039 class's int encoded_array values.

    All supplied class static fields are int constants. Any other value kind,
    implicit value, duplicate class, unusual DEX profile or absent field refuses.
    Offsets here are physical ordinary-039 offsets, never a 041 approximation.
    """
    member = receipt['selectedMethodProofs'][0]['physicalDex']
    with zipfile.ZipFile(receipt['archive']) as archive:
        data = archive.read(member)
    if data[:8] != b'dex\n039\0':
        raise ValueError('Static-value decoder admits ordinary 039 only')
    u32 = lambda p: struct.unpack_from('<I', data, p)[0]
    if u32(32) != len(data) or u32(36) != 112 or u32(40) != 0x12345678:
        raise ValueError('Unexpected DEX header')
    if hashlib.sha1(data[32:]).digest() != data[12:32]:
        raise ValueError('DEX source signature')
    import zlib
    if zlib.adler32(data[12:]) & 0xffffffff != u32(8):
        raise ValueError('DEX source checksum')

    def string(index):
        if index >= u32(56):
            raise ValueError('String index')
        p = u32(u32(60) + 4 * index)
        _, p = uleb(data, p)
        # Selected identifiers are ASCII, a strict subset of DEX MUTF-8.
        return data[p:data.index(0, p)].decode('ascii')

    def typename(index):
        if index >= u32(64):
            raise ValueError('Type index')
        return string(u32(u32(68) + 4 * index))

    matches = [p for p in range(u32(100), u32(100) + 32 * u32(96), 32)
               if typename(u32(p)) == TRACKER]
    if len(matches) != 1:
        raise ValueError('Selected class count')
    definition = matches[0]
    class_data = u32(definition + 24)
    values = u32(definition + 28)
    count, cursor = uleb(data, class_data)
    for _ in range(3):
        _, cursor = uleb(data, cursor)
    fields, index = [], 0
    for _ in range(count):
        delta, cursor = uleb(data, cursor)
        access, cursor = uleb(data, cursor)
        index += delta
        if index >= u32(80):
            raise ValueError('Field index')
        entry = u32(84) + 8 * index
        if typename(struct.unpack_from('<H', data, entry)[0]) != TRACKER:
            raise ValueError('Field owner')
        if typename(struct.unpack_from('<H', data, entry + 2)[0]) != 'I':
            raise ValueError('Selected constants are not all int')
        if access & 0x18 != 0x18:
            raise ValueError('Expected static final field')
        fields.append((string(u32(entry + 4)), index))
    encoded_count, cursor = uleb(data, values)
    if encoded_count != count or not count:
        raise ValueError('Explicit static constants required')
    result = []
    for name, index in fields:
        offset = cursor
        tag = data[cursor]
        cursor += 1
        size = (tag >> 5) + 1
        if tag & 31 != 4 or size > 4:
            raise ValueError('Expected encoded int')
        value = int.from_bytes(data[cursor:cursor + size], 'little', signed=True)
        cursor += size
        result.append({'name': name, 'value': value, 'fieldIndex': index,
                       'encodedValueOffset': offset})
    proof = {'archiveSha256': receipt['archiveSha256'], 'physicalDex': member,
             'physicalDexSha256': hashlib.sha256(data).hexdigest(),
             'classDefOffset': definition, 'classDataOffset': class_data,
             'staticValuesOffset': values, 'constants': result,
             'dexVersion': '039', 'sourceHeaderChecksPassed': True}
    return proof


def main():
    if not PINS:
        raise ValueError('Unfrozen proof set')
    receipts, methods, proofs, references, archives = {}, {}, {}, {}, {}
    for path, expected in PINS.items():
        p = checked(path, expected)
        if not path.startswith('out/' + STREAM + '/'):
            continue
        r = json.loads(p.read_text())
        checked(r['raw'], r['rawSha256'])
        if not r['archiveAndToolPinsVerifiedBeforeAndAfter'] or r['readerExitCode']:
            raise ValueError('Reader admission')
        archives[r['archive']] = r['archiveSha256']
        receipts[p.stem] = r
        for q in raw_records(r['raw']):
            if q['record'] == 'method':
                b = q['body']
                key = p.stem + ':' + b['owner'] + '->' + b['signature']
                methods[key] = b
                proofs[key] = {'archiveSha256': r['archiveSha256'],
                               'raw': r['raw'], 'rawSha256': r['rawSha256'],
                               'bodySha256': q['normalizedBodySha256'],
                               'physicalDex': q['physicalDex'],
                               'logicalHeaderOffset': q['logicalHeaderOffset']}
            elif q['record'] == 'reference':
                references.setdefault(p.stem, []).append({
                    'caller': q['caller'], 'pc': q['instruction']['pc'],
                    'target': q['instruction']['reference']})
    for path, expected in archives.items():
        if sha(path) != expected:
            raise ValueError('Source archive changed')
    inheritance = []
    declarations = json.loads((ROOT / 'firmware' / STREAM / 'caller-tracker-declarations.json').read_text())
    for archive, record in declarations.items():
        checked(record['index'], record['indexSha256'])
        for declaration in record['selectedDeclarations']:
            if declaration['superclass'] != TRACKER or any(
                    method['name'] == 'isBiometricAllowedForUser' for method in declaration['methods']):
                raise ValueError('Caller tracker no longer inherits selected helper')
            inheritance.append({'archive': archive, 'descriptor': declaration['descriptor'],
                                'superclass': TRACKER, 'declaresEligibilityOverride': False,
                                'index': record['index'], 'indexSha256': record['indexSha256']})

    protocol = json.loads((ROOT / 'inventory/construction-protocol.json').read_text())
    credentials = json.loads((ROOT / 'inventory/credentials.json').read_text())
    inherited = {}
    for op in protocol['operations']:
        if op['name'] in ['registerStrongAuthTracker', 'unregisterStrongAuthTracker',
                          'getStrongAuthForUser']:
            for side in ['coloros', 'samsung']:
                pr = op[side]['service']
                checked(pr['raw'], pr['rawSha256'])
                key = side + '-service:' + pr['owner'] + '->' + pr['signature']
                inherited[key] = pr
    for key, pr in credentials['methodProofs'].items():
        if key.startswith('samsung:') and ('LockSettingsStrongAuth$1;->handleMessage' in key
                or 'LockSettingsStrongAuth;-><init>' in key):
            r = json.loads((ROOT / pr['receipt']).read_text())
            checked(pr['raw'], r['rawSha256'])
            inherited[key] = dict(pr, rawSha256=r['rawSha256'])
    lpu = json.loads((ROOT / 'out/construction-protocol/lockpattern-bodies.json').read_text())
    checked(lpu['raw'], lpu['rawSha256'])
    for q in raw_records(lpu['raw']):
        if q['record'] == 'method' and 'StrongAuthTracker' in q['body']['signature']:
            key = 'coloros-lpu:' + q['body']['owner'] + '->' + q['body']['signature']
            methods[key] = q['body']
            inherited[key] = {'bodySha256': q['normalizedBodySha256'],
                              'raw': lpu['raw'], 'rawSha256': lpu['rawSha256']}
    for key, pr in list(inherited.items()):
        if key in methods:
            continue
        for q in raw_records(pr['raw']):
            if q['record'] == 'method':
                b = q['body']
                if key.split(':', 1)[1] == b['owner'] + '->' + b['signature']:
                    if q['normalizedBodySha256'] != pr.get('bodySha256'):
                        raise ValueError('Inherited body hash mismatch')
                    methods[key] = b

    assertions = []
    def at(key, pc, **expected):
        instruction = next(i for i in methods[key]['instructions'] if i['pc'] == pc)
        if any(instruction.get(k) != v for k, v in expected.items()):
            raise ValueError('Instruction assertion: ' + key + ':' + str(pc))
        assertions.append({'proof': key, 'pc': pc, **expected})

    constants = {}
    for side in ['coloros', 'samsung']:
        constants[side] = static_ints(receipts[side + '-tracker'])
        prefix = side + '-tracker:' + TRACKER + '->'
        at(prefix + 'getStrongAuthForUser(I)I', 4,
           reference='Landroid/util/SparseIntArray;->get(II)I')
        at(prefix + 'isNonStrongBiometricAllowedAfterIdleTimeout(I)Z', 2, literal=1)
        at(prefix + 'isBiometricAllowedForUser(ZI)Z', 4,
           literal=-5893 if side == 'coloros' else -5901, opcode='AND_INT_LIT16')
        at(prefix + 'handleStrongAuthRequiredChanged(II)V', 19,
           reference=TRACKER + '->onStrongAuthRequiredChanged(I)V')
        for signature, code, txpc, args in [
                ('onStrongAuthRequiredChanged(II)V', 1, 23, ['writeInt(I)V'] * 2),
                ('onIsNonStrongBiometricAllowedChanged(ZI)V', 2, 24,
                 ['writeBoolean(Z)V', 'writeInt(I)V'])]:
            key = side + '-proxy:' + CALLBACK + '->' + signature
            at(key, 13, reference='Landroid/os/Parcel;->' + args[0])
            at(key, 16, reference='Landroid/os/Parcel;->' + args[1])
            at(key, 21, literal=0)
            at(key, 22, literal=1)
            if code == 2:
                at(key, 23, literal=2)
            at(key, txpc, reference='Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')
        queue = side + '-queue:Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker$1;->'
        if side == 'coloros':
            at(queue + 'onStrongAuthRequiredChanged(II)V', 17,
               reference='Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker$H;->sendMessageAtFrontOfQueue(Landroid/os/Message;)Z')
        else:
            at(queue + 'onStrongAuthRequiredChanged(II)V', 11,
               reference='Landroid/os/Message;->sendToTarget()V')
    cv = {side: {x['name']: x['value'] for x in p['constants']}
          for side, p in constants.items()}
    common = set(cv['coloros']) & set(cv['samsung']) - {'ALLOWING_BIOMETRIC'}
    if any(cv['coloros'][name] != cv['samsung'][name] for name in common):
        raise ValueError('Named flags differ')
    if cv['coloros']['ALLOWING_BIOMETRIC'] ^ cv['samsung']['ALLOWING_BIOMETRIC'] != 8:
        raise ValueError('Unexpected policy delta')

    minimum = [
        'Retain actual Samsung authority/code/state owners and immutable callback/user generation before registration; authenticate callback ingress and original caller before identity changes.',
        'Preserve full flags and actual nonStrongAllowed boolean; admit exact two-callback wire and user mapping, never strip unknown/Knox or additional-factor flags.',
        'Obtain same-authority selected-user initial snapshot/default policy plus a source-owned subscription ordering barrier and actual consumer-application acknowledgement; neither void return, query, silence nor cached defaults is readiness.',
        'Resolve ColorOS front-of-queue flag scheduling without stale state publication; preserve ordered current updates across snapshot, callback and selected-user changes.',
        'Delegate tracker-level biometric eligibility to genuine Samsung original policy under the same current user/generation; preserve actual host lockout/higher policy and separate additional-factor/finish gates. No mask-only patch is selected.',
        'Close callback admission first; use the exact registered Binder for remote removal, drain source broadcast/Binder/local queue and active consumer stacks before releasing retained owners; uncertain registration/removal remains owned and unavailable.',
        'Retire on authority/profile/version/user mismatch; reject late callbacks and rebuild genuine current state before republication. No blind retry, replay or synthetic callback.',
        'Source-owned initial snapshot, ordering/application receipt and drain mechanism remain unimplemented; keep protected UI unavailable/locked until all obligations are met.'
    ]
    output = {
        'schema': 'oneos-strongauth-callback-adapter/v1', 'classification': 'static-source-prerequisite',
        'selected': False, 'runtimeAdapterImplemented': False,
        'sourceReceiptPins': PINS, 'archives': archives,
        'methodProofs': proofs, 'inheritedMethodProofs': inherited,
        'sourceBodyCount': len(methods), 'newBodyCount': len(proofs),
        'instructionAssertions': assertions, 'staticConstants': constants,
        'wire': {'descriptor': 'android.app.trust.IStrongAuthTracker',
                 'callbacks': [{'code': 1, 'signature': 'onStrongAuthRequiredChanged(II)V',
                                'arguments': ['full-int-flags', 'actual-user-id']},
                               {'code': 2, 'signature': 'onIsNonStrongBiometricAllowedChanged(ZI)V',
                                'arguments': ['actual-allowed-boolean', 'actual-user-id']}],
                 'onewayFlag': 1, 'reply': None, 'parcelCompatibility': 'exact-selected-wire'},
        'trackerPolicy': {'colorosAllowingBiometric': 5892, 'samsungAllowingBiometric': 5900,
                          'difference': 8, 'sharedNamedFlagsEqual': sorted(common),
                          'helperExpression': '((flags & ~ALLOWING_BIOMETRIC) == 0) && (isStrong || nonStrongAllowed)',
                          'additionalFactorCompletionImpliedByHelper': False,
                          'delegationImplemented': False},
        'sourceFacts': {
            'registration': {'samsungServiceMessage': 2, 'serviceEnqueuePc': 12,
                             'handlerSwitchPc': 27, 'handlerCasePc': 493,
                             'remoteListRegisterPc': 499,
                             'registrationBooleanConsumed': False,
                             'initialFlagsCallbackPc': 523,
                             'initialNonStrongCallbackPc': 556,
                             'initialDeliveryScope': 'existing sparse-map entries only',
                             'initialCompleteCallbackPresent': False,
                             'initialCallbackRemoteExceptions': 'logged, continue loop'},
            'removal': {'samsungServiceMessage': 3, 'serviceEnqueuePc': 12,
                        'handlerCasePc': 483, 'remoteListUnregisterPc': 489,
                        'removalBooleanConsumed': False,
                        'sourceOrClientDrainAcknowledgedByReturn': False,
                        'colorosWrapperRemoteException': 'log at17 and return20'},
            'initialCaches': {'mapsInitiallyEmpty': True,
                              'defaultNonStrongAllowed': True,
                              'defaultFlagsResourceId': {'coloros': 17891997, 'samsung': 17892001},
                              'effectiveResourcePolicyVerified': False,
                              'equalToDefaultCallbackEmitsConsumerChange': False,
                              'defaultIsReadiness': False},
            'queue': {'colorosFlags': 'sendMessageAtFrontOfQueue at17',
                      'samsungFlags': 'Message.sendToTarget at11',
                      'bothNonStrong': 'ordinary Message.sendToTarget',
                      'arrivalGuaranteesAppliedOrder': False,
                      'orderingAdapterImplemented': False},
            'currentQuery': {'serviceCallerCheckPc': 0,
                             'serviceSynchronizedTrackerQueryPc': 5,
                             'synchronizedSuperclassCacheQueryPc': 1,
                             'demonstratedProducerRegistrationBarrier': False,
                             'returnsNonStrongBoolean': False},
            'policyGap': {'flag8GuestHelperBlocks': True,
                          'flag8SamsungStrongHelperAllows': True,
                          'flag2048BothHelpersBlock': True,
                          'flag4096BothHelpersAllowBeforeIndependentPolicy': True,
                          'guestStricterResultCountsAsFullUxAcceptance': False,
                          'maskOnlyPatchSelected': False}
        },
        'exactMethodReferenceScope': references,
        'callerTrackerInheritance': inheritance,
        'referenceCountsIncludingZero': {k: r['referenceMatchCount'] for k, r in receipts.items()
                                        if k.endswith('-eligibility-xref')},
        'minimumAdapterRequirements': minimum,
        'limits': ['Selected supplied archives only; reflection, other apps and installed OneOS are outside this direct-reference scope.',
                   'Static source facts and derived requirements; no scheduler, Binder, hardware, Android or cryptographic acceptance.',
                   'No original resource value or effective overlay is assumed from its numeric ID.',
                   'Existing OneOS permissive SELinux/relaxed privileged permissions remain disclosed platform limits, not a new global enforcing gate.',
                   'A genuine helper result is policy eligibility, never authentication success, enrollment, HAT acceptance or permission to finish.'],
        'audit': {'pass': True, 'oemCodeExecuted': False, 'androidExecuted': False, 'phoneActions': []},
        'toolSha256': sha(__file__)}
    destination = ROOT / 'inventory/strongauth-callback-adapter.json'
    destination.write_text(json.dumps(output, indent=2) + '\n')
    out = ROOT / 'out' / STREAM
    out.mkdir(parents=True, exist_ok=True)
    (out / 'audit-result.json').write_text(json.dumps({
        'pass': True, 'sourceBodyCount': len(methods), 'newBodyCount': len(proofs),
        'instructionAssertionCount': len(assertions),
        'inventorySha256': sha(destination), 'toolSha256': sha(__file__),
        'runtimeVerified': False}, indent=2) + '\n')
    print(json.dumps({'pass': True, 'sourceBodies': len(methods),
                      'instructionAssertions': len(assertions), 'runtimeVerified': False}))


if __name__ == '__main__':
    main()
