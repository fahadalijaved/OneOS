"""Audit the source-only, eighteen-operation local LockSettings control proposal."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAM = 'local-locksettings-contract'
PINS = {
    "out/local-locksettings-contract/coloros-dpm-metrics-helpers.json": "0238555d3e7f9d875027307feb1cabf1a8ade5e70f8b3e30a99d3a58ea312a4f",
    "out/local-locksettings-contract/coloros-escrow-activation.json": "67ea0417b7e4022a7d18a2419f4790e262a9e6368db2dac4f4960977ce680db6",
    "out/local-locksettings-contract/coloros-escrow-event-xref.json": "90173f6a41caacdc35491aae3bd17c30839c097ea13797745ad3328ba2ad0be9",
    "out/local-locksettings-contract/coloros-EscrowTokenStateChangeCallback-declarations.json": "a7063259648a7a105067b8b0d0aa84ac58299c0e86fa3c6530c6aaddcf5a2c65",
    "out/local-locksettings-contract/coloros-listener-0.json": "0b5125a18555bef15114c8e6b3c7dba3b33c0a51da988f735313237f901a6257",
    "out/local-locksettings-contract/coloros-listener-1.json": "64be51f40c87b17cea22f9ab5662a4187c0ebfa12bf8623c24ccfd50417fdfd1",
    "out/local-locksettings-contract/coloros-listener-2.json": "57d60397b965400e76d47458a1a1775959786e80d7e0ee1b76190ed0fd4acebd",
    "out/local-locksettings-contract/coloros-local-backing.json": "8fbe4e24b396d50570c64842316c40191c3db18fec4f7233212410e2e9d31bbf",
    "out/local-locksettings-contract/coloros-local-bridges.json": "1faa7006b522a6b8ad12e9a7a837eaccc9fbe1311871e79b85707fa12d1870a1",
    "out/local-locksettings-contract/coloros-localservice.json": "a807bd3d00c1751f1bab83145102346385296c88b0785ea8704502a37d991d6c",
    "out/local-locksettings-contract/coloros-LockSettingsStateListener-declarations.json": "7795a5c48029ce13393c9eb5dc904131afe64e8631d3628a4ffd937a73cb466e",
    "out/local-locksettings-contract/coloros-metrics-base-constructor.json": "b41fe7ffaf3e121438043d71cd4b9253f9a1c65b05fa5c3c76c025be872350cd",
    "out/local-locksettings-contract/coloros-metrics-constructor.json": "2326a76f4604a5b69a7808cbda3d5f267095e163cfdf3e479d6eaf0bc489a84d",
    "out/local-locksettings-contract/coloros-metrics-consumers.json": "0b7e4a71dc032bb627085477e86f3339fd24269e54efc13bc9949e8dc2a4c1f7",
    "out/local-locksettings-contract/coloros-metrics-policy-leaves.json": "4f719aaa2375c756f0730856c07c2da98044513650062db32ad6eb8e49ab4562",
    "out/local-locksettings-contract/coloros-metrics-policy.json": "9e7cfc24a53cdfd1bb7aa452a4aee010d35069793b518add2347bb1d64043f1a",
    "out/local-locksettings-contract/coloros-metrics-reader.json": "73b86ba7f888b2e0b1ab33363babfd0322cb218fd5b8a8d906c53deb93fb08cc",
    "out/local-locksettings-contract/coloros-metrics-writer.json": "f7b7d843948b22484db491afcd3d88529c10526197d893ccb900d52bdabbeb48",
    "out/local-locksettings-contract/coloros-RebootEscrowListener-declarations.json": "0534df3117c5c2d75e9885dfbb973fba4f73be6d124e0aff4364b26c2b528034",
    "out/local-locksettings-contract/coloros-ror-manager.json": "54d0dde079d03ead0ac548d2f08bc18fff1d5461771b2736867e043aaed468b2",
    "out/local-locksettings-contract/coloros-state-notify-xref.json": "0141a9e8ee6fa08b99155dfaf3015e67c0ac7ff6caeb64230bfbe7480a029fd6",
    "out/local-locksettings-contract/samsung-agent-listener-registration.json": "9f8a2cf2239d548da8b728500204b7484b24b8eae619e081a7ad8cc94343598f",
    "out/local-locksettings-contract/samsung-ce-lock-xref.json": "aebe680b9c078b6ac5519f98a9f70445470944d10cbb4ec6c7f1a09748de9c09",
    "out/local-locksettings-contract/samsung-escrow-activation.json": "7b2b15e128b3f76bf01d0ed630b20f30e3930f259574ef9801395205a7d69825",
    "out/local-locksettings-contract/samsung-escrow-event-xref.json": "597f12ce83b0bb1a1da350996df238ea8b685eac3332745e0cdace6ea864d57c",
    "out/local-locksettings-contract/samsung-EscrowTokenStateChangeCallback-declarations.json": "56167e2711849504f39838dd6611b310649d4db192c13f60537c738dc4a725ea",
    "out/local-locksettings-contract/samsung-listener-0.json": "d80f160642fb6c7a5d289a924cc4a20cf1a1d0a30d54bb78115970d3b05325ee",
    "out/local-locksettings-contract/samsung-listener-1.json": "30c907b2d98bd9f4edb62e538e403f083d50a285690fbfec7e6783e1753506cc",
    "out/local-locksettings-contract/samsung-local-backing.json": "dc50d223abdfba364fa7c08af797c8fbbe5dc399d20d2837e6444bc6e16b64ed",
    "out/local-locksettings-contract/samsung-localservice.json": "98b467caa764aab115e186a0a003fcf1ad7da7d7bf8d7bf6bae6cf41fae91d0d",
    "out/local-locksettings-contract/samsung-LockSettingsStateListener-declarations.json": "ed3dc35c9e41c19896e72584be8ba533a30d5d0f671d587fe3807c80bb6a7695",
    "out/local-locksettings-contract/samsung-metrics-base-constructor.json": "c1236322e9df85efb1ec95293b58d29ad54bb74112fd721e408c8592687f39dd",
    "out/local-locksettings-contract/samsung-metrics-cache-xref.json": "ed364e9fb1cbf0a3315710ca448ad89102c9fc9e8b2032d4751a781d1f54fabd",
    "out/local-locksettings-contract/samsung-metrics-constructor.json": "ac69d520014b4260444de11abd6717e363a07b39384b4690e6e9ee365858ba5c",
    "out/local-locksettings-contract/samsung-metrics-reader.json": "b3327496fdc7434854cb973ef16ccad7ba31453fc3e464c63fdfbb66bead78b3",
    "out/local-locksettings-contract/samsung-metrics-writer.json": "f9626ed6406d9d83e6008daae67d1babee09805cf1716e4e896c82d46fd2da6a",
    "out/local-locksettings-contract/samsung-policy-listener-registration.json": "d3906ffd0a65909756bd698c0b0575883e042d22c44399fa066725d6681dc923",
    "out/local-locksettings-contract/samsung-ror-consumer.json": "da82387655c64848ef53eab030c581d3ae4e2a5e86754bcc7ed73f6b7c547961",
    "out/local-locksettings-contract/samsung-ror-dispatch.json": "ccd7397dd45134046344dd33eabbf4706cd0b441a60e9f77c25d328b5812d045",
    "out/local-locksettings-contract/samsung-ror-event.json": "9147e67b3a98e2fc4b5889e9aae026463c1180c409a8554a86af6303a840b6ce",
    "out/local-locksettings-contract/samsung-state-list-xref.json": "6b80f935cfc180da577156def802a9f3ac6fd6b89fde0e2b6c6e615cf6f31f52",
    "out/local-locksettings-contract/samsung-user-lock-backing.json": "7fb803dc31af3dc5cb2115652933b594971e9598a994a939887c973ce1401fe9",
    "inventory/credentials.json": "333118f3876c61f641d9a8aae82bd11ed61d6366a28e916ddd58755c4a5ef3b8",
    "inventory/authority-bootstrap-endpoints.json": "2e99d62f8287b9fcf16a4cd32439ce1e91d2a83ad2f4fb95006a36b6411284b0",
    "inventory/construction-protocol.json": "aa2baaa0b449d5f93a4b796704176659ad54315a082547cb06c39f3acff13d18",
    "firmware/local-locksettings-contract/state-listener-declarations.json": "d1398786a0a42190259adfa616a9ae0b4652624ff64d3e9323da396d722fe2c5",
    "firmware/credentials/20261105T123705889135Z-94ca2a5cf4984aa38475568e752587d6.jsonl": "3d98459af85df8b6df4dd88a81bb62f0f5a32e7be98268f23c4c30a6f3ba062e",
    "firmware/credentials/20261105T123454212027Z-7bee1deb9d7c403087492c4d788a2cd6.jsonl": "005f96ae16337e31ea8195cab9e98ffbc40da6d23c8f108745dd3448183d9377"
}  # FROZEN_PINS
LSS = 'Lcom/android/server/locksettings/LockSettingsService;'
LOCAL = 'Lcom/android/server/locksettings/LockSettingsService$LocalService;'


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text())


def records(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def main():
    if not PINS:
        raise ValueError('Unfrozen evidence')
    for path, expected in PINS.items():
        if sha(ROOT / path) != expected:
            raise ValueError('Evidence changed: ' + path)
    receipts, methods, proofs, declarations, references, archives = {}, {}, {}, {}, {}, {}
    for path in PINS:
        if not path.startswith('out/' + STREAM + '/'):
            continue
        r = load(path)
        if r['readerExitCode'] or not r['archiveAndToolPinsVerifiedBeforeAndAfter']:
            raise ValueError('Source reader admission')
        if sha(ROOT / r['raw']) != r['rawSha256']:
            raise ValueError('Raw source drift')
        label = Path(path).stem
        receipts[label] = r
        declarations[label] = r['selectedClassDeclarations']
        archives[r['archive']] = r['archiveSha256']
        for record in records(r['raw']):
            if record['record'] == 'method':
                body = record['body']
                key = label + ':' + body['owner'] + '->' + body['signature']
                methods[key] = body
                proofs[key] = {'bodySha256': record['normalizedBodySha256'],
                               'archiveSha256': r['archiveSha256'],
                               'raw': r['raw'], 'rawSha256': r['rawSha256'],
                               'physicalDex': record['physicalDex'],
                               'logicalHeaderOffset': record['logicalHeaderOffset']}
            elif record['record'] == 'reference':
                references.setdefault(label, []).append({'caller': record['caller'],
                    'pc': record['instruction']['pc'], 'target': record['instruction']['reference']})
    for path, expected in archives.items():
        if sha(path) != expected:
            raise ValueError('Actual source archive changed')
    credentials = load('inventory/credentials.json')
    for side in ['coloros', 'samsung']:
        key, proof = next((k, p) for k, p in credentials['methodProofs'].items()
                          if k.startswith(side + ':') and '->doVerifyCredential(' in k)
        if sha(ROOT / proof['raw']) != PINS[proof['raw']]:
            raise ValueError('Reused verification source')
        match = next(r for r in records(proof['raw']) if r['record'] == 'method' and
                     r['body']['owner'] + '->' + r['body']['signature'] == key.split(':', 1)[1])
        if match['normalizedBodySha256'] != proof['bodySha256']:
            raise ValueError('Reused verification body')
        full = side + '-verify:' + key.split(':', 1)[1]
        methods[full] = match['body']
        proofs[full] = dict(proof, rawSha256=PINS[proof['raw']], reused=True)

    assertions = []
    def site(key, pc, **expected):
        instruction = next(i for i in methods[key]['instructions'] if i['pc'] == pc)
        if any(instruction.get(name) != value for name, value in expected.items()):
            raise ValueError('Exact instruction changed: ' + key + ':' + str(pc))
        assertions.append({'proof': key, 'pc': pc, **expected})
    g = 'coloros-localservice:' + LOCAL + '->'
    h = 'samsung-localservice:' + LOCAL + '->'
    site(g + 'addEscrowToken([BILcom/android/server/locksettings/EscrowTokenStateChangeCallback;)J',
         2, literal=0, registers=[1])
    site(g + 'addEscrowToken([BILcom/android/server/locksettings/EscrowTokenStateChangeCallback;)J',
         3, registers=[0, 3, 1, 4, 5])
    site(g + 'registerLockSettingsStateListener(Lcom/android/server/locksettings/LockSettingsStateListener;)V',
         3, reference='Ljava/util/Objects;->requireNonNull(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/Object;')
    site(g + 'registerLockSettingsStateListener(Lcom/android/server/locksettings/LockSettingsStateListener;)V',
         12, reference='Ljava/util/concurrent/CopyOnWriteArrayList;->add(Ljava/lang/Object;)Z')
    site(g + 'unregisterLockSettingsStateListener(Lcom/android/server/locksettings/LockSettingsStateListener;)V',
         6, reference='Ljava/util/concurrent/CopyOnWriteArrayList;->remove(Ljava/lang/Object;)Z')
    site('coloros-ror-manager:Lcom/android/server/locksettings/RebootEscrowManager;->clearRebootEscrow()Z',
         0, reference='Lcom/android/server/locksettings/RebootEscrowManager;->clearRebootEscrowIfNeeded()V')
    site('coloros-ror-manager:Lcom/android/server/locksettings/RebootEscrowManager;->clearRebootEscrow()Z', 3, literal=1)
    site(h + 'clearRebootEscrow()V', 4,
         reference='Lcom/android/server/locksettings/RebootEscrowManager;->clearRebootEscrowIfNeeded()V')
    site(h + 'clearRebootEscrow()V', 15, literal=64)
    site(h + 'clearRebootEscrow()V', 17, literal=-1)
    token_set = h + 'setLockCredentialWithToken(Lcom/android/internal/widget/LockscreenCredential;J[BI)Z'
    site(token_set, 22, reference='Landroid/os/Binder;->clearCallingIdentity()J')
    site(token_set, 32, reference='string=n_digits_pin_enabled')
    site(token_set, 52, opcode='IF_NEZ', targetPc=55)
    site(token_set, 55, reference=LSS + '->onPostLockCredentialChanged(Lcom/android/internal/widget/LockscreenCredential;I)V')
    lock = 'samsung-user-lock-backing:Lcom/android/server/am/UserController$$ExternalSyntheticLambda3;->run()V'
    for pc, target in [(373, 'Landroid/os/storage/IStorageManager;->lockCeStorage(I)V'),
                       (378, 'Landroid/security/KeyStoreAuthorization;->onUserStorageLocked(I)I'),
                       (383, 'Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker;->getDefaultFlags(Landroid/content/Context;)I'),
                       (387, LSS + '->requireStrongAuth(II)V'),
                       (393, 'Landroid/util/SparseArray;->remove(I)V')]:
        site(lock, pc, reference=target)
    verify = next(k for k in methods if k.startswith('samsung-verify:'))
    site(verify, 760, reference='Lcom/android/internal/widget/VerifyCredentialResponse;->isMatched()Z')
    for pc, name in [(784, 'Succeeded'), (788, 'Failed')]:
        site(verify, pc, reference='Lcom/android/server/locksettings/LockSettingsStateListener;->onAuthentication' + name + '(I)V')
    for side, pc, descriptor in [('coloros', 168, '(JI)V'), ('samsung', 213, '(IJ)V')]:
        key = next(k for k in methods if k.startswith(side + '-escrow-activation:'))
        site(key, pc, reference='Lcom/android/server/locksettings/EscrowTokenStateChangeCallback;->onEscrowTokenActivated' + descriptor)

    fields = ['credType', 'length', 'letters', 'upperCase', 'lowerCase', 'numeric',
              'symbols', 'nonLetter', 'nonNumeric', 'seqLength']
    metric_proof = {}
    for side in ['coloros', 'samsung']:
        writer = methods[side + '-metrics-writer:Landroid/app/admin/PasswordMetrics;->writeToParcel(Landroid/os/Parcel;I)V']
        sequence = [i['reference'].split('->')[1].split(':')[0] for i in writer['instructions']
                    if i.get('opcode') == 'IGET' and i.get('reference', '').startswith('Landroid/app/admin/PasswordMetrics;->')]
        if sequence != fields:
            raise ValueError('PasswordMetrics field order')
        reader_key = side + '-metrics-reader:Landroid/app/admin/PasswordMetrics$1;->createFromParcel(Landroid/os/Parcel;)Landroid/app/admin/PasswordMetrics;'
        reader = methods[reader_key]
        if sum(i.get('reference') == 'Landroid/os/Parcel;->readInt()I' for i in reader['instructions']) != 10:
            raise ValueError('PasswordMetrics read count')
        metric_proof[side] = {'writerProof': side + '-metrics-writer:Landroid/app/admin/PasswordMetrics;->writeToParcel(Landroid/os/Parcel;I)V',
                              'readerProof': reader_key,
                              'constructorProof': side + '-metrics-constructor:Landroid/app/admin/PasswordMetrics;-><init>(IIIIIIIIII)V'}
    consumer_keys = [k for k in methods if k.startswith('coloros-metrics-consumers:')]
    if len(consumer_keys) != 5 or any(i['opcode'].startswith('IPUT') and
            i.get('reference', '').startswith('Landroid/app/admin/PasswordMetrics;->')
            for k in consumer_keys for i in methods[k]['instructions']):
        raise ValueError('Selected DPM metrics consumers changed')
    for signature in ['comparePasswordMetrics(Landroid/app/admin/PasswordMetrics;Landroid/app/admin/PasswordMetrics$ComplexityBucket;Landroid/app/admin/PasswordMetrics;Ljava/util/ArrayList;)V',
                      'satisfiesBucket(Landroid/app/admin/PasswordMetrics$ComplexityBucket;)Z']:
        body = methods['coloros-metrics-policy-leaves:Landroid/app/admin/PasswordMetrics;->' + signature]
        if any(i['opcode'].startswith('IPUT') for i in body['instructions']):
            raise ValueError('Actual metrics read path gained mutation')
    copy = 'coloros-metrics-policy-leaves:Landroid/app/admin/PasswordMetrics;->applyComplexity(Landroid/app/admin/PasswordMetrics;ZLandroid/app/admin/PasswordMetrics$ComplexityBucket;)Landroid/app/admin/PasswordMetrics;'
    site(copy, 0, opcode='NEW_INSTANCE', registers=[0], reference='Landroid/app/admin/PasswordMetrics;')
    if any(i['registers'][1] != 0 for i in methods[copy]['instructions'] if i['opcode'].startswith('IPUT')):
        raise ValueError('Complexity mutation no longer targets its new copy')

    baseline = load('inventory/authority-bootstrap-endpoints.json')
    protocol = load('inventory/construction-protocol.json')
    if len(protocol['operations']) != 33 or any(op['name'] == 'systemReady' for op in protocol['operations']):
        raise ValueError('Public credential transport baseline changed')
    all_callers = baseline['localDirectReferences']
    guest_methods = [row for row in methods.values() if row['owner'] == LOCAL and
                     row['signature'].split('(', 1)[0] not in ['<init>'] and
                     any(row is methods[k] for k in methods if k.startswith('coloros-localservice:'))]
    by_name = {b['signature'].split('(', 1)[0]: b for b in guest_methods}
    if len(by_name) != 18:
        raise ValueError('Expected exactly eighteen guest operations')
    contracts = []
    def operation(name, target, arguments, result, duties, owner_role, adaptation=False):
        body = by_name[name]
        sig = body['signature']
        contracts.append({'name': name, 'guestSignature': sig, 'required': True,
            'guestBodyProof': 'coloros-localservice:' + LOCAL + '->' + sig,
            'originalGuestCallers': [x for x in all_callers if x['target'] ==
                                    'Lcom/android/server/locksettings/LockSettingsInternal;->' + sig],
            'proposedHostTarget': target, 'argumentProvenance': arguments,
            'resultSemantics': result, 'requiredDuties': duties,
            'proposedCallerRole': owner_role,
            'sourceDerivedAdaptationRequired': adaptation,
            'runtimeImplementation': 'not implemented; proposal requires root review'})
    operation('addEscrowToken', LSS + '->addEscrowToken([BIILcom/android/server/locksettings/EscrowTokenStateChangeCallback;)J',
              ['same token bytes', 'literal type0 from guest LocalService PC2', 'same actual user', 'nullable actual-owned host callback carrier'],
              'actual Samsung long handle; no default handle or invented activation',
              ['retain callback before entry; activation may occur before add returns',
               'source syncState and pending-token removal precede activation callback',
               'translate host callback(user,handle) to guest(handle,user); do not export SP/keys'], 'DPM or Trust token owner')
    operation('armRebootEscrow', LOCAL + '->armRebootEscrow()I', [], 'exact original int result or exception',
              ['real ready/provider/key wrapping/storage checks and original result codes', 'not primary authentication or reboot approval'], 'RecoverySystem RoR owner')
    operation('clearRebootEscrow', LOCAL + '->clearRebootEscrow()V', [],
              'guest true only after real original host LocalService normal completion; exception/uncertainty is not true',
              ['real clear and StrongAuth64/-1 removal post required', 'true means original synchronous clear wrapper completed, not provider/readiness/drain success'],
              'RecoverySystem RoR owner', True)
    operation('createNewUser', LOCAL + '->createNewUser(II)V', ['same actual user', 'same actual serial'],
              'original void return; may mean accepted into genuine early-user queue',
              ['original KeyStoreMaintenance.onUserAdded', 'preserve user/serial reuse cleanup, early-created/removed maps, SP initialization and later third-party drain'], 'UserManager lifecycle owner')
    operation('disableSecureLockDevice', LOCAL + '->disableSecureLockDevice(IZ)V', ['same actual user', 'actual policy-derived authenticationComplete'],
              'original void return; StrongAuth work is posted',
              ['actual message12 user/authComplete; no arbitrary caller-supplied completion grant',
               'when genuinely complete preserve original unlock and tied-profile TrustManager effects', 'separate factor/finish and Handler completion remain required'], 'actual SecureLockDevice policy owner')
    operation('getUserPasswordMetrics', LOCAL + '->getUserPasswordMetrics(I)Landroid/app/admin/PasswordMetrics;', ['same actual user'],
              'nullable authoritative ten-int value; secure uncached null is preserved; real insecure metrics(-1) only from source',
              ['preserve original identity clear/restore and synchronized cache getter', 'no unknown/unavailable->insecure/default conversion',
               'exact codec and selected five DPM readonly paths are source-pinned; carry current authoritative value, not object identity'], 'DPM policy owner')
    operation('isEscrowTokenActive', LSS + '->isEscrowTokenActive(IJ)Z', ['guest user argument moved before unchanged long handle'],
              'exact original boolean', ['no activation inferred from handle existence/format', 'bind handle to actual user and current token owner'], 'DPM or Trust token owner', True)
    operation('lockUser', 'source-owned Samsung user-lock control, actual UserController$$ExternalSyntheticLambda3.run PCs373..396',
              ['same actual user under current user-lifecycle/serial owner'], 'void only after the real ordered sequence returns; partial progress remains uncertain',
              ['real lockCeStorage -> KeyStoreAuthorization.onUserStorageLocked -> genuine Context defaultStrongAuth/requireStrongAuth -> synchronized metric removal',
               'complete before guest UserController resumes its user-locking callbacks',
               'do not invoke whole synthetic Runnable/construct AMS; do not map to clearStorageForUser, which deletes enterprise/SecureFolder storage'], 'UserController lifecycle owner', True)
    operation('onThirdPartyAppsStarted', LOCAL + '->onThirdPartyAppsStarted()V', [],
              'actual original return, not fabricated boot-complete',
              ['source migrations and early-user queues drain before original mThirdPartyAppsStarted commit',
               'one admitted phase occurrence, no replay/repeated startup migrations', 'child work/exception disposition stays owned'], 'bootstrap phase controller')
    operation('prepareRebootEscrow', 'source-owned host RoR prepare operation: RecoverySystemService.requestLskf actual inlined core PCs223..300', [],
              'false only from genuine provider-unavailable path; true only after original wanted/event/StrongAuth preparation path',
              ['real manager clear -> real provider acquisition -> original mRebootEscrowWanted/event5 -> requireStrongAuth64/-1',
               'prepare is not actual SP capture or ready', 'reviewed source-derived entry/real RecoverySystem owner required; no public request identity fabrication'], 'RecoverySystem RoR owner', True)
    operation('refreshStrongAuthTimeout', LOCAL + '->refreshStrongAuthTimeout(I)V', ['same actual user'],
              'original posted message10 return, not applied deadline acknowledgement',
              ['real current DPM policy/default timeout owner', 'actual Handler completion and retirement remain owned'], 'DPM or Trust policy owner')
    operation('registerLockSettingsStateListener', 'actual Samsung LSS.mLockSettingsStateListeners owned carrier registration; same source path as real APM/AgentAuth',
              ['nonnull guest listener -> genuine host-interface carrier for this registration'], 'original void publication; no initial event/readiness',
              ['preserve duplicate add semantics with separately owned actual entries', 'retain before list publication; no private-field/class-name attestation',
               'forward only real verify-tail user events; no synthetic DPM/Trust reporting', 'own source iterator, IPC and actual guest Handler/consumer lifetime'], 'bootstrap-owned Trust/APM/AgentAuth subscriber', True)
    operation('removeEscrowToken', LOCAL + '->removeEscrowToken(IJ)Z', ['guest user moved before unchanged long handle'],
              'exact original boolean/exception', ['genuine protector/current-LSKF checks and deletion; no synthetic removal ack'], 'DPM or Trust token owner', True)
    operation('removeUser', LOCAL + '->removeUser(I)V', ['same actual user with current serial-generation validation'],
              'original void return may queue early removal', ['preserve actual early-created/removed reconciliation and removeUserState security cleanup'], 'UserManager lifecycle owner')
    operation('setLockCredentialWithToken', LOCAL + '->setLockCredentialWithToken(Lcom/android/internal/widget/LockscreenCredential;J[BI)Z',
              ['actual source-compatible credential', 'unchanged long handle', 'same token bytes', 'same actual user'],
              'actual original boolean, or exception/uncertain mutation disposition; never auto-retry',
              ['preserve original secure-lock capability check', 'preserve real n_digits_pin_enabled reset under identity clear/restore before setter',
               'invoke original setter and post-change only on true; post-change can fail after committed mutation',
               'publish guest credential/cache/policy change only from real committed source event/readback, never boolean guessed from transport'], 'DPM credential-token policy owner')
    operation('setRebootEscrowListener', 'real host RebootEscrowManager/RecoverySystem source-owned event seam; concrete host listener is RecoverySystemService',
              ['actual guest RecoverySystem listener occurrence; no raw cross-realm interface cast'],
              'registration acknowledgement only; no initial/prepared callback invented',
              ['host generic RebootEscrowListener API is absent from selected services; concrete field cannot hold guest Binder',
               'requires reviewed source-owned carrier/hook at genuine ready-change dispatch and actual host RecoverySystem consumer/state owner',
               'retain actual source boolean, post/order and original host client/IntentSender/persistence effects; drain before release'], 'RecoverySystem RoR owner', True)
    operation('unlockUserWithToken', LOCAL + '->unlockUserWithToken(I[BJ)Z',
              ['guest user first', 'same token bytes second', 'unchanged long handle last'], 'exact original boolean/exception',
              ['real escrow data/protector verification and actual onCredentialVerified/metrics/storage/key effects', 'no arbitrary SID/handle match or synthetic unlock event'], 'Trust token owner', True)
    operation('unregisterLockSettingsStateListener', 'remove exact owned host-list carrier entry and retire its local/remote admission',
              ['same guest registration owner; first matching original entry semantics'], 'no source guarantee of active-iterator/Handler drain from remove return',
              ['preserve duplicate/removal identity semantics; null/absent removal does not attest uncertain registrations removed',
               'reject late retired generation; retain through actual iterator/IPC/guest Handler/consumer drain', 'no blind retry or successful disconnect on failed/uncertain removal'],
              'same bootstrap subscriber owner', True)
    if {c['name'] for c in contracts} != set(by_name):
        raise ValueError('Incomplete proposed surface')
    ror = ['armRebootEscrow', 'clearRebootEscrow', 'prepareRebootEscrow', 'setRebootEscrowListener']
    ror_callers = {c['name']: c['originalGuestCallers'] for c in contracts if c['name'] in ror}
    if any(not calls or any('Lcom/android/server/recoverysystem/RecoverySystemService;' not in c['caller']
                           for c in calls) for calls in ror_callers.values()):
        raise ValueError('RoR caller grouping changed')
    output = {
        'schema': 'local-locksettings-contract/v1', 'status': 'FULL_REQUIRED_SOURCE_API_PROPOSAL_NOT_RUNTIME',
        'selected': False, 'runtimeCodeAdded': False, 'publicCredentialRouteCount': 33,
        'extendsPublicCredentialRoutes': False, 'sourcePins': PINS, 'archives': archives,
        'sourceBodyCount': len(methods), 'methodProofs': proofs, 'instructionAssertions': assertions,
        'operations': contracts, 'operationCount': len(contracts),
        'proposedControl': {'visibility': 'private bootstrap-owned transport; no public transaction numbers proposed',
            'guestOwner': 'actual guest LockSettingsInternal proxy published before early consumers',
            'authorityOwner': 'same real Samsung LSS/LocalService, code/state/native/user generation and retirement owner as both Binder endpoints',
            'admission': ['actual admitted guest system_server/controller lifetime and trusted local caller/operation role; never UID1000 or caller-supplied role alone',
                'preserve upstream real DPM/Trust/User/SLD checks before delegation; capture original policy ownership before any identity hop',
                'check authority/user/serial/operation before and after original entry; all failures after entry preserve uncertainty, never retry/rollback by guess'],
            'originalLocalServiceTrustBoundary': 'trusted in-process Java; its methods do not establish a generic remote Binder caller/operation ownership gate',
            'disposition': ['not-entered refusal', 'original returned its real value/void', 'original threw or postcheck/transport failed after entry: uncertain effects retained'],
            'unsupported': 'all eighteen are required; missing owner/carrier/source adaptation blocks selection, not a default result'},
        'metricsCodec': {'fieldOrder': fields, 'types': ['int'] * 10, 'proofs': metric_proof,
            'nullableSecureCacheResultPreserved': True, 'insecureMetricsAreOnlyOriginalSourceResult': True,
            'mutableLiveObjectIdentityNotCarriedAcrossProcess': True,
            'selectedReadonlyConsumerUsageVerified': True,
            'selectedDirectConsumerProofs': consumer_keys,
            'scope': 'Five selected guest DPM users and followed comparison/complexity paths; not arbitrary future consumers or global atomic runtime proof'},
        'events': {'state': {'guest': ['onAuthenticationSucceeded(I)V', 'onAuthenticationFailed(I)V'],
                'host': ['onAuthenticationSucceeded(I)V', 'onAuthenticationFailed(I)V'],
                'source': 'real Samsung doVerifyCredential isMatched tail; inline before final result/SP cleanup',
                'noInitialDelivery': True, 'perListenerExceptionContainedByOriginalLoop': False,
                'registeredConsumerMethodsMayPostHandlerWork': True, 'bridgeAddsDpmOrTrustReports': False,
                'eventIsChallengeHatOrAuthenticatorProof': False},
            'escrow': {'guest': 'onEscrowTokenActivated(JI)V', 'host': 'onEscrowTokenActivated(IJ)V',
                'argumentTranslation': ['actual handle', 'actual user'],
                'producer': 'real createTokenBasedProtector after syncState and pending-map removal',
                'mayArriveBeforeAddReturns': True, 'lostCallbackAfterCommitIsRollback': False},
            'ror': {'guest': 'onPreparedForReboot(Z)V',
                'hostActualFieldType': 'Lcom/android/server/recoverysystem/RecoverySystemService;',
                'hostProducer': 'setRebootEscrowReady -> actual Handler Runnable0 -> real RecoverySystem client/IntentSender/prefs handling',
                'reviewedSourceCarrierHookImplemented': False}},
        'rorStatus': {'required': True, 'methods': ror, 'actualSelectedGuestCallers': ror_callers,
            'oppoOnly': False, 'currentUnavailablePathCutReviewed': False,
            'futureRemovalCondition': 'separately reviewed complete guest RecoverySystem/public/OTA/client/listener unavailable-path cut; none supplied here'},
        'referenceEvidence': references,
        'limits': ['Static supplied-source behavior and authored API proposal only; no runtime implementation, source patch or OEM execution.',
            'Exact source-derived recipes for lockUser/RoR and genuine carrier registration still require reviewed implementation and actual owner construction.',
            'No listener return, original void, posted work or default cache is readiness/commit/drain proof.',
            'Cross-process control preserves source values and disposition, not Java object or Throwable identity across processes.',
            'Original source callbacks, token bytes and credentials must remain ephemeral owned transport; no logs/private SP or key export.',
            'Existing accepted OneOS platform limitations stay disclosed; no new global Enforcing requirement.'],
        'audit': {'pass': True, 'oemCodeExecuted': False, 'androidExecuted': False, 'phoneActions': []},
        'toolSha256': sha(__file__)}
    destination = ROOT / 'inventory/local-locksettings-contract.json'
    destination.write_text(json.dumps(output, indent=2) + '\n')
    result = {'pass': True, 'sourceBodies': len(methods), 'operations': len(contracts),
              'instructionAssertions': len(assertions), 'runtimeImplemented': False,
              'inventorySha256': sha(destination), 'toolSha256': sha(__file__)}
    (ROOT / 'out' / STREAM / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
