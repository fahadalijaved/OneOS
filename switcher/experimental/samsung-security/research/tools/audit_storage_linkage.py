"""Bounded source linkage evidence; no OEM execution. Raw bodies remain ignored."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import gzip

ROOT = Path(__file__).resolve().parent.parent
INPUTS = {
    'samsung-services': ('firmware/samsung/runtime-20261104/services.jar', 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
    'coloros-services': ('firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
    'samsung-framework': ('firmware/samsung/framework.jar', '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
    'coloros-framework': ('firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
}

def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def capture():
    read = runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
    out = ROOT/'out/construction-storage'
    out.mkdir(parents=True, exist_ok=True)
    save = out/'queries.json'
    queries = json.loads(save.read_text()) if save.exists() else [
        {'input': 'samsung-services', 'class': 'com.android.server.StorageManagerService$StorageManagerInternalImpl', 'receipt': 'out/tooling/20261105T143724191293Z-6273ef3ccde043a8b5dc234e04a3a9ba/receipt.json'},
        {'input': 'samsung-services', 'class': 'com.android.server.StorageManagerService', 'receipt': 'out/tooling/20261105T143724783900Z-b0029ee5bc574284b807626fab95cd2a/receipt.json'},
        {'input': 'samsung-framework', 'class': 'com.android.server.LocalServices', 'receipt': 'out/tooling/20261105T143725325994Z-56a2536d379046dbb2286635c9f13a0b/receipt.json'},
    ]
    for side in ('samsung', 'coloros'):
        for archive, cls, all_methods in [
            ('services', 'com.android.server.StorageManagerService$StorageManagerInternalImpl', True),
            ('services', 'com.android.server.StorageManagerService', False),
            ('framework', 'com.android.server.LocalServices', True),
            ('framework', 'android.os.IVold', False),
            ('services', 'android.os.IVold', False),
            ('services', 'com.android.server.StorageManagerService$Lifecycle', True),
        ]:
            key = side+'-'+archive
            if any(q['input'] == key and q['class'] == cls for q in queries):
                continue
            path, digest = INPUTS[key]
            r = read(ROOT.parent/path, digest, class_name=cls,
                     all_methods=all_methods, stream='construction-storage')
            queries.append({'input': key, 'class': cls, 'receipt': r['receipt']})
            save.write_text(json.dumps(queries, indent=2)+'\n')
            print(key, cls, r['receipt'], flush=True)
    path, digest = INPUTS['coloros-services']
    if not any(q['class'] == 'com.android.server.StorageManagerInternal' for q in queries):
        r = read(ROOT.parent/path, digest, class_name='com.android.server.StorageManagerInternal', all_methods=True, stream='construction-storage')
        queries.append({'input': 'coloros-services', 'class': 'com.android.server.StorageManagerInternal', 'receipt': r['receipt']})
        save.write_text(json.dumps(queries, indent=2)+'\n')

def report():
    evidence = []
    all_rows = {}
    queries = json.loads((ROOT/'out/construction-storage/queries.json').read_text())
    queries += json.loads((ROOT/'out/construction-storage/edges.json').read_text())
    queries += [{'input': 'samsung-services', 'class': 'com.android.server.locksettings.LockSettingsService', 'receipt': 'out/tooling/20261105T123602189303Z-13cb9b7c9f294be296de6da0d63a43c0/receipt.json'}]
    for q in queries:
        receipt_path = ROOT/q['receipt']
        r = json.loads(receipt_path.read_text())
        assert r['readerExitCode'] == 0 and r['archiveAndToolPinsVerifiedBeforeAndAfter']
        for tool, digest in r['tools'].items():
            tool_path = ROOT.parent/'out/toolchain/jadx-1.5.6/lib/jadx-1.5.6-all.jar' if tool == 'parentDexlibSha256' else ROOT/tool
            assert sha(tool_path) == digest, 'Reader or dexlib moved: '+tool
        assert r['archiveSha256'] == INPUTS[q['input']][1]
        assert sha(ROOT/r['raw']) == r['rawSha256']
        rows = [json.loads(line) for line in (ROOT/r['raw']).open(encoding='utf-8')]
        all_rows.setdefault(q['input'], []).extend(rows)
        evidence.append(dict(q, receiptSha256=sha(receipt_path), raw=r['raw'], rawSha256=r['rawSha256'],
                             readerPins=r['tools'], logicalDex=r['physicalLogicalDex'], methodProofs=r['selectedMethodProofs']))
    def method(side, owner, signature):
        matches = [r for r in all_rows[side] if r['record'] == 'method' and r['body']['owner'] == owner and r['body']['signature'] == signature]
        assert matches and len({r['normalizedBodySha256'] for r in matches}) == 1
        return matches[0]
    checks = []
    registry = []
    for side in ('samsung', 'coloros'):
        m = method(side+'-framework', 'Lcom/android/server/LocalServices;', 'addService(Ljava/lang/Class;Ljava/lang/Object;)V')
        ins = m['body']['instructions']
        contains = next(i for i in ins if '->containsKey(' in i.get('reference', ''))
        branch = next(i for i in ins if i['pc'] > contains['pc'] and i['opcode'] == 'IF_NEZ')
        put = next(i for i in ins if '->put(' in i.get('reference', ''))
        throw = next(i for i in ins if i['pc'] >= branch['targetPc'] and i['opcode'] == 'THROW')
        assert put['pc'] < branch['targetPc'] < throw['pc']
        assert any(i['opcode'] == 'MONITOR_ENTER' for i in ins)
        registry.append({'side': side, 'containsKeyPc': contains['pc'], 'duplicateBranchTargetPc': branch['targetPc'], 'putPc': put['pc'], 'throwPc': throw['pc'], 'bodySha256': m['normalizedBodySha256']})
    checks.append('Both actual registry duplicate paths throw before replacement; synchronized insertion uses Class key')
    transport = []
    for side in ('samsung', 'coloros'):
        for r in all_rows[side+'-framework']:
            if r['record'] != 'method' or r['body']['owner'] != 'Landroid/os/IVold$Stub$Proxy;':
                continue
            ins = r['body']['instructions']
            invoke = next(i for i in ins if '->transact(' in i.get('reference', ''))
            reg = invoke['registers'][1]
            code = [i['literal'] for i in ins if i['pc'] < invoke['pc'] and i.get('registers') == [reg] and 'literal' in i][-1]
            writes = [i['reference'].split('->')[1] for i in ins if 'Landroid/os/Parcel;->write' in i.get('reference', '')]
            transport.append({'side': side, 'signature': r['body']['signature'], 'transactionCode': code, 'writes': writes, 'transactPc': invoke['pc'], 'bodySha256': r['normalizedBodySha256']})
    assert {(t['side'], t['transactionCode']) for t in transport} == {('samsung', 46), ('samsung', 60), ('coloros', 54), ('coloros', 56)}
    checks.append('Actual IVold proxy transaction registers prove distinct codes and argument serialization')
    xrefs = [r for r in all_rows['samsung-services'] if r['record'] == 'reference']
    local = [{'caller': r['caller'], 'pc': r['instruction']['pc'], 'target': r['instruction']['reference'], 'physicalDex': r['physicalDex'], 'logicalHeaderOffset': r['logicalHeaderOffset']} for r in xrefs if '/locksettings/' in r['caller']]
    assert len(local) == 8
    checks.append('Whole Samsung services concrete-owner reference scan has107 matches, exactly8 in locksettings package')
    lss_owner = 'Lcom/android/server/locksettings/LockSettingsService;'
    storage_field = lss_owner+'->mStorageManagerInternal:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;'
    lss_rows = [r for r in all_rows['samsung-services'] if r['record'] == 'method' and r['body']['owner'] == lss_owner]
    field_uses = [{'caller': lss_owner+'->'+r['body']['signature'], 'pc': i['pc'], 'opcode': i['opcode'], 'target': storage_field}
                  for r in lss_rows for i in r['body']['instructions'] if i.get('reference') == storage_field]
    assert sorted(e['pc'] for e in field_uses) == [83, 105, 163, 177, 651]
    lss_class = next(r for r in all_rows['samsung-services'] if r['record'] == 'class' and r['descriptor'] == lss_owner)
    field_declaration = next(f for f in lss_class['fields'] if f['name'] == 'mStorageManagerInternal')
    assert field_declaration['accessFlags'] == 17  # public final
    policy_bodies = []
    for prefix, expected in [('setCeStorageProtection(', '64be48a967a43d72afaa0d4ba7311a648379f2f7d36bde63b201b60d9d136433'),
                             ('unlockCeStorage(', '9d74a9bc7bdc6d82c87d6ad719e134cdb073d0700e0ef27ec2a8046e469c8cbf')]:
        r = next(r for r in lss_rows if r['body']['signature'].startswith(prefix))
        assert r['normalizedBodySha256'] == expected
        policy_bodies.append({'owner': lss_owner, 'signature': r['body']['signature'], 'bodySha256': expected,
                              'selectedReferences': [{'pc': i['pc'], 'reference': i['reference']} for i in r['body']['instructions'] if any(t in i.get('reference', '') for t in ('deriveSubkey', 'PERSONALIZATION_FBE_KEY', 'DualDAR', 'DualDar', 'fetchOuterLayerKey', 'verifyChallenge', 'getGatekeeperHAT', 'zeroize'))],
                              'zeroizePcs': [i['pc'] for i in r['body']['instructions'] if '->zeroize(' in i.get('reference', '')]})
    checks.append('Five additional LSS-owned field uses plus public-final declaration and exact secret/HAT/cleanup policy bodies verified')
    classes = {}
    for side in ('samsung', 'coloros'):
        c = next(r for r in all_rows[side+'-services'] if r['record'] == 'class' and r['descriptor'].endswith('StorageManagerInternalImpl;'))
        classes[side] = {k:c[k] for k in ('descriptor', 'superclass', 'fields', 'methods')}
    assert classes['samsung']['superclass'] == 'Ljava/lang/Object;'
    assert classes['coloros']['superclass'] == 'Lcom/android/server/StorageManagerInternal;'
    assert 'isHSUMMode' in [f['name'] for f in classes['samsung']['fields']]
    assert 'isHSUMMode' not in [f['name'] for f in classes['coloros']['fields']]
    checks.append('Actual implementation inheritance, missing HSUM field and unlock signature differences verified')
    index_evidence = []
    for role in ('framework', 'system-server-services'):
        summary_path = ROOT.parent/'out/os-comparison-resumed/archive-index/comparisons'/role/'summary.json'
        summary = json.loads(summary_path.read_text())
        for side in ('samsung', 'coloros'):
            index = ROOT.parent/summary[side]['declarations']
            assert sha(index) == summary[side]['declarationsSha256']
            rows = [json.loads(l) for l in gzip.open(index, 'rt', encoding='utf-8')]
            selected = [r['descriptor'] for r in rows if r.get('descriptor') == 'Lcom/android/server/StorageManagerInternal;']
            index_evidence.append({'side': side, 'role': role, 'index': str(index.relative_to(ROOT.parent)).replace('\\','/'), 'sha256': sha(index), 'canonicalStorageManagerInternalOccurrences': len(selected), 'scope': 'specific captured archive only'})
    assert [e['canonicalStorageManagerInternalOccurrences'] for e in index_evidence] == [0, 0, 0, 1]
    patch = ROOT.parent/'firmware/reference/OneOS/2a5f41043b4a69399cae058bad213cdef7408e88/switcher/patches/guest_no_vold_keys.py'
    assert sha(patch) == '442027bf3f5b80ba0086460f84dd54cae9040872fa935452b80eccf4e3b01658'
    inputs = {k: {'path': '../'+v[0], 'sha256': v[1], 'currentSha256Verified': sha(ROOT.parent/v[0]) == v[1]} for k,v in INPUTS.items()}
    assert all(v['currentSha256Verified'] for v in inputs.values())
    required_bodies = []
    for side, owner, sig in [
        ('samsung-services', 'Lcom/android/server/StorageManagerService$Lifecycle;', 'onStart()V'),
        ('coloros-services', 'Lcom/android/server/StorageManagerService;', '<init>(Landroid/content/Context;)V'),
        ('samsung-services', 'Lcom/android/server/StorageManagerService;', 'connectVold$1()V'),
        ('coloros-services', 'Lcom/android/server/StorageManagerService;', 'connectVold()V'),
        ('samsung-services', 'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;', 'unlockCeStorage(I[B[B)V'),
        ('coloros-services', 'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;', 'unlockCeStorage(I[B)V'),
    ]:
        m = method(side, owner, sig)
        required_bodies.append({'input': side, 'owner': owner, 'signature': sig, 'bodySha256': m['normalizedBodySha256'],
                               'physicalDex': m['physicalDex'], 'logicalHeaderOffset': m['logicalHeaderOffset'],
                               'selectedReferences': [{'pc': i['pc'], 'reference': i['reference']} for i in m['body']['instructions'] if 'reference' in i and any(t in i['reference'] for t in ('LocalServices', 'StorageManagerInternal', 'IVold', 'ServiceManager', 'mVold', 'UserManager', 'mCeUnlockedUsers', 'invalidate', 'HexDump', 'string=!'))]})
    result = {'schema': 'construction-storage-linkage/v1', 'classification': 'observed static linkage and transport facts; runtime authority unverified',
              'inputs': inputs, 'evidence': evidence, 'declarationIndexes': index_evidence,
              'implementationDeclarations': classes, 'locksettingsConcreteEdges': local, 'concreteReferenceScanMatches': len(xrefs),
              'locksettingsOwnedStorageField': field_declaration, 'locksettingsOwnedFieldUses': field_uses,
              'locksettingsSecretHatLifetimeBodies': policy_bodies,
              'localRegistryCollisionProofs': registry, 'ivoldProxyProofs': transport,
              'registrationAndBackendBodies': required_bodies,
              'oneosPatch': {'path': '../'+str(patch.relative_to(ROOT.parent)).replace('\\','/'), 'sha256': sha(patch), 'classification': 'producer source only; installed bytes not verified'},
              'checks': checks, 'toolSha256': sha(Path(__file__)), 'oemCodeExecuted': False, 'phoneActions': False,
              'remainingBlockers': ['Selected canonical/private class ownership and exact relinking proof', 'Single real native storage/user/mount/key authority and caller identity', 'Current installed patched bytes and service generation', 'Real CE key acceptance, cache/notification coherence and mutation recovery']}
    result['guestAdaptationAlternative'] = {
        'status': 'source-supported design; not implemented or runtime verified',
        'direction': 'Adapt ColorOS APIs to genuine Samsung backend; full Samsung SMS import is not presumed mandatory',
        'retargetSites': 'concrete-key acquisition, public-final LSS field declaration and five uses, two unlock invocations, both direct outer/IVold protection paths',
        'typedSemantics': ['original user', 'HAT from same-SP verifyChallenge on actual branch; genuine conditional null preserved', 'SP-derived FBE or genuine DualDAR outer-layer key according to actual policy', 'HSUM policy', 'authoritative status', 'synchronous borrowed-array consumption and exact zeroization/exception boundaries', 'real failure and notification completion'],
        'mandatory': ['one native/current-writer authority', 'correct Samsung wire contract', 'coherent cache and listener ownership', 'full shared PIN/FP/policy/app-key/CE behavior'],
        'optionalOppoRemoval': 'Only audited unsupported optional UI/background/implementation pieces; no missing-signature no-op success'}
    (ROOT/'inventory/construction-storage-linkage.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'checks': len(checks), 'receipts': len(evidence), 'concreteReferences': len(xrefs), 'locksettingsEdges': len(local), 'runtimeVerified': False}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true', help='Issue exact bounded static queries')
    parser.add_argument('--close-edges', action='store_true', help='Read only missing registration/transport bodies')
    parser.add_argument('--report', action='store_true', help='Verify frozen actual evidence and emit derived inventory')
    args = parser.parse_args()
    if args.report:
        report()
    if args.capture:
        capture()
    if args.close_edges:
        read = runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
        save = ROOT/'out/construction-storage/edges.json'
        qs = json.loads(save.read_text()) if save.exists() else []
        for side in ('samsung', 'coloros'):
            for archive, cls, methods in [
                ('services', 'com.android.server.StorageManagerService',
                 ['connectVold$1()V', 'isCeStorageUnlocked(I)Z'] if side == 'samsung' else ['<init>(Landroid/content/Context;)V', 'connectVold()V', 'isCeStorageUnlocked(I)Z']),
                ('framework', 'android.os.IVold$Stub$Proxy',
                 ['unlockCeStorage(ILjava/lang/String;[BZ)V', 'setCeStorageProtection(I[BZ)V'] if side == 'samsung' else ['unlockCeStorage(I[B)V', 'setCeStorageProtection(I[B)V']),
            ]:
                key = side+'-'+archive
                if any(q['input'] == key and q['class'] == cls for q in qs):
                    continue
                path, digest = INPUTS[key]
                r = read(ROOT.parent/path, digest, class_name=cls, methods=methods, stream='construction-storage')
                qs.append({'input': key, 'class': cls, 'receipt': r['receipt']})
                save.write_text(json.dumps(qs, indent=2)+'\n')
                print(key, cls, r['receipt'], flush=True)
        if not any(q.get('reference') for q in qs):
            path, digest = INPUTS['samsung-services']
            ref = 'Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;'
            r = read(ROOT.parent/path, digest, reference=ref, stream='construction-storage')
            qs.append({'input': 'samsung-services', 'reference': ref, 'receipt': r['receipt']})
            save.write_text(json.dumps(qs, indent=2)+'\n')
            print('concrete implementation direct references', r['receipt'], flush=True)

if __name__ == '__main__':
    main()
