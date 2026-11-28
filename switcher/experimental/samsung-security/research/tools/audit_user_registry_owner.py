"""Bounded original-UMS construction/query evidence. Never executes OEM code."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/user-registry-owner'
ARCHIVE = ROOT.parent / 'firmware/samsung/runtime-20261104/services.jar'
PIN = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def evidence():
    result = {}
    for name in ['authority-bootstrap-users', 'security-user-binding']:
        data = json.loads((ROOT / ('inventory/' + name + '.json')).read_text())
        result.update({k: v for k, v in data['methodProofs'].items() if k.startswith('samsung-services:')})
    for query in json.loads((WORK / 'queries.json').read_text()) if (WORK / 'queries.json').exists() else []:
        receipt = json.loads((ROOT / query['receipt']).read_text())
        assert receipt['readerExitCode'] == 0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter']
        assert receipt['archiveSha256'] == PIN
        for proof in receipt['selectedMethodProofs']:
            result['samsung-services:' + proof['owner'] + '->' + proof['signature']] = {
                'bodySha256': proof['normalizedBodySha256'], 'raw': receipt['raw'],
                'rawSha256': receipt['rawSha256'], 'receipt': query['receipt']}
    return result

def body(key, proofs=None):
    proofs = evidence() if proofs is None else proofs
    proof = proofs[key]
    return next(row['body'] for row in map(json.loads, (ROOT / proof['raw']).read_text(encoding='utf-8').splitlines())
                if row.get('record') == 'method' and row['body']['owner'] + '->' + row['body']['signature'] == key.split(':', 1)[1])

def capture(class_name, methods, label):
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'queries.json'
    queries = json.loads(path.read_text()) if path.exists() else []
    old = next((query for query in queries if query['label'] == label), None)
    if old:
        return json.loads((ROOT / old['receipt']).read_text())
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    receipt = read(ARCHIVE, PIN, class_name=class_name, methods=methods, stream='user-registry-owner')
    queries.append({'label': label, 'class': class_name, 'receipt': receipt['receipt']})
    path.write_text(json.dumps(queries, indent=2) + '\n')
    return receipt

def report():
    proofs = evidence()
    allowed = ('Lcom/android/server/pm/UserManagerService;',
               'Lcom/android/server/pm/UserManagerService$',
               'Lcom/android/server/pm/UserTypeFactory;',
               'Lcom/android/server/pm/UserVisibilityMediator;',
               'Lcom/android/server/pm/UserSystemPackageInstaller;',
               'Lcom/android/server/pm/PersonaManagerService;',
               'Lcom/android/server/pm/PersonaManagerService$14;',
               'Lcom/android/server/pm/ResilientAtomicFile;',
               'Lcom/samsung/android/server/pm/lifecycle/PmCustomInjector',
               'Lcom/android/server/SystemConfig;')
    proofs = {k: v for k, v in proofs.items() if k.split(':', 1)[1].startswith(allowed)}
    def select(part):
        return body(next(k for k in proofs if part in k), proofs)
    def at(b, pc):
        return next(i for i in b['instructions'] if i['pc'] == pc)
    ctor = select('UserManagerService;-><init>(Landroid/content/Context;Lcom/android/server/pm/PackageManagerService;')
    short = select('UserManagerService;-><init>(Landroid/content/Context;)V')
    checks = {
        'contextOnlyCacheRoot': 'getCacheDir()' in at(short, 12)['reference'],
        'unconditionalPmsHandlerRead': 'mCustomInjector:' in at(ctor, 254)['reference'],
        'globalUserTypeXml': at(ctor, 409)['literal'] == 18284553 and 'Resources;->getSystem' in at(ctor, 405)['reference'],
        'registryLoadBeforeSingleton': 'readUserListLP' in at(ctor, 1010)['reference'] and 'sInstance:' in at(ctor, 1013)['reference'],
        'localPublicationBeforeFinalMutationTail': 'LocalServices;->addService' in at(ctor, 1076)['reference'] and all('writeUserLP' in at(ctor, pc)['reference'] for pc in [1254, 1322, 1365]),
        'debugEmulationGate': 'Build;->isDebuggable' in at(ctor, 1114)['reference'] and at(ctor, 1118)['targetPc'] == 1122 and at(ctor, 1133)['targetPc'] == 1137,
        'finalCacheInvalidationTail': 'invalidateUserRestriction' in at(ctor, 1397)['reference'] and at(ctor, 1400)['opcode'] == 'RETURN_VOID',
        'profileQueryRequiresPersona': 'sPersonaManager:' in at(select('UserManagerService;->getProfileIds(Ljava/lang/String;IZZ)'), 24)['reference'] and 'getClass()' in at(select('UserManagerService;->getProfileIds(Ljava/lang/String;IZZ)'), 26)['reference'],
        'personaListRealPmQuery': 'queryIntentActivitiesAsUser' in at(select('-$$Nest$mgetWorkTabSupportLauncherUids('), 34)['reference'] and 'getPackageInfo' in at(select('-$$Nest$mgetWorkTabSupportLauncherUids('), 98)['reference'],
        'personaAsyncListReplacement': 'workTabSupportLauncherUids:' in at(select('PersonaManagerService$14;->handleMessage'), 851)['reference'],
        'delayedUserWrite': at(select('->scheduleWriteUser('), 25)['literal'] == 2000 and 'sendMessageDelayed' in at(select('->scheduleWriteUser('), 27)['reference'],
        'handlerRealWrites': 'writeUserListLP' in at(select('MainHandler;->handleMessage'), 19)['reference'] and 'writeUserLP' in at(select('MainHandler;->handleMessage'), 55)['reference'],
        'restrictionPosts': all('post(' in at(select('->updateUserRestrictionsInternalLR('), pc)['reference'] for pc in [96, 134]),
        'existingUserStartNeedsDataPreparer': 'mUserDataPreparer:' in at(select('->onBeforeStartUser('), 46)['reference'],
        'existingUserUnlockNeedsDataPreparer': 'mUserDataPreparer:' in at(select('->onBeforeUnlockUser('), 40)['reference'],
    }
    assert all(checks.values()), checks
    receipts, raws = {}, {}
    for p in proofs.values():
        assert sha(ROOT / p['raw']) == p['rawSha256']
        receipts[p['receipt']] = sha(ROOT / p['receipt'])
        raws[p['raw']] = p['rawSha256']
    fields = []
    for q in json.loads((WORK / 'field-queries.json').read_text()):
        r = json.loads((ROOT / q['receipt']).read_text())
        assert r['archiveSha256'] == PIN and r['archiveAndToolPinsVerifiedBeforeAndAfter'] and r['readerExitCode'] == 0
        assert sha(ROOT / r['raw']) == r['rawSha256']
        receipts[q['receipt']] = sha(ROOT / q['receipt']); raws[r['raw']] = r['rawSha256']
        matches = [{'caller': row['caller'], 'pc': row['instruction']['pc']} for row in map(json.loads, (ROOT / r['raw']).read_text(encoding='utf-8').splitlines()) if row.get('record') == 'reference']
        assert len(matches) == r['referenceMatchCount']
        fields.append(dict(q, matches=matches))
    resource_base = json.loads((ROOT / 'inventory/resource-compat.json').read_text())
    parse = runpy.run_path(str(ROOT / 'tools/audit_security_resources.py'))['table']
    resource_rows = {}
    for side, p in resource_base['rawResourceDumps'].items():
        assert sha(ROOT / p['raw']) == p['sha256']; raws[p['raw']] = p['sha256']
        table = parse(ROOT / p['raw'])
        resource_rows[side] = [table[n] for n in [18284553, 17891815]]
    assert resource_rows['samsung'][0]['name'] == 'xml/config_user_types'
    assert resource_rows['coloros'][0]['name'] == 'xml/haptic_feedback_customization'
    xml = json.loads((WORK / 'resource-receipt.json').read_text())
    assert sha(ROOT / xml['raw']) == xml['rawSha256'] and sha(ROOT / xml['input']) == xml['inputSha256']
    raws[xml['raw']] = xml['rawSha256']
    ledger = json.loads((ROOT / 'out/security-user-binding/receipts.json').read_text())
    state = ledger['samsung-directrefs:Lcom/android/server/pm/UserManagerInternal;']
    assert sha(ROOT / state['raw']) == state['rawSha256']; raws[state['raw']] = state['rawSha256']
    producers = [{'caller': row['caller'], 'pc': row['instruction']['pc'], 'target': row['instruction']['reference']} for row in map(json.loads, (ROOT / state['raw']).read_text(encoding='utf-8').splitlines()) if row.get('record') == 'reference' and any(s in row['instruction'].get('reference', '') for s in ['->setUserState(', '->removeUserState('])]
    assert len(producers) == 9 and sha(ARCHIVE) == PIN
    value = {
        'schema': 'user-registry-owner/v1', 'status': 'SOURCE_API_PROPOSAL_BLOCKED_REAL_ADMISSION',
        'evidenceKind': 'bounded static original construction/query paths',
        'oemExecuted': False, 'androidExecuted': False, 'privateStateRead': False, 'runtimePatchImplemented': False,
        'archive': {'path': str(ARCHIVE.resolve()), 'sha256': PIN},
        'sourceAssertions': checks, 'methodProofs': proofs, 'fieldReferences': fields,
        'resourceCollisions': resource_rows, 'selectedUserTypeXml': xml,
        'originalStateProducers': producers,
        'retargetProposal': {'approvedForDocumentationOnly': True, 'contextOnlyRootPc': 12, 'fullCtorHandlerSpanPc': [254, 271], 'singletonPublicationPc': 1013, 'localPublicationPc': 1076, 'constructorFinalReturnPc': 1400, 'personaNullCheckPc': [24, 26], 'personaListReadPc': 29, 'requiresRealDexIndexTypeInverseCallerProof': True},
        'missingBeforeConstruction': ['sole original physical registry ownership and current generation', 'source-selected original system and Context resource identities plus actual overlays', 'owned source-derived HandlerThread/Looper and original queued-work acknowledgement', 'publication interception and failure retention through constructor tail', 'actual Persona-derived caller policy initial population and update owner', 'genuine complete lifecycle/CE/cache order and user/profile/serial identity'],
        'unsupportedWithoutSeparateOwner': ['create/remove user and durable removeUserState', 'onBeforeStartUser/onBeforeUnlockUser/reconcileUsers', 'maintenance user77', 'ASEC and full LifeCycle callbacks', 'virtual/DualDAR realms without genuine policy/storage owner'],
        'receiptPins': receipts, 'rawPins': raws,
        'reusedInventoryPins': {str(p): sha(ROOT / p) for p in ['inventory/authority-bootstrap-users.json', 'inventory/security-user-binding.json', 'inventory/resource-compat.json']},
        'limits': ['Exact direct field refs cover captured Samsung services only, not reflection/every archive', 'Method edges do not prove Binder/ART/physical registry/current installed state', 'SystemConfig cold construction and migration-posted restriction callback closure remain explicit admission requirements', 'No stale registry snapshot, default user, null owner substitute, transaction-wide rollback or empty-queue/native-drain claim'],
        'authoredPins': {p: sha(ROOT / p) for p in ['docs/user-registry-owner.md', 'tools/audit_user_registry_owner.py']},
    }
    dest = ROOT / 'inventory/user-registry-owner.json'
    dest.write_text(json.dumps(value, indent=2) + '\n')
    freeze = {'status': value['status'], 'sourceAssertions': len(checks), 'files': {p: sha(ROOT / p) for p in ['docs/user-registry-owner.md', 'inventory/user-registry-owner.json', 'tools/audit_user_registry_owner.py']}, 'receiptCount': len(receipts), 'rawCount': len(raws), 'androidExecuted': False, 'oemExecuted': False}
    (WORK / 'FROZEN.json').write_text(json.dumps(freeze, indent=2) + '\n')
    print(json.dumps(freeze))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--class-name')
    parser.add_argument('--method', action='append', default=[])
    parser.add_argument('--label')
    args = parser.parse_args()
    if args.class_name:
        result = capture(args.class_name, args.method, args.label or args.class_name)
        print(json.dumps({k: result[k] for k in ['receipt', 'raw', 'rawSha256', 'selectedClassDeclarations']}))
    else:
        report()

if __name__ == '__main__':
    main()
