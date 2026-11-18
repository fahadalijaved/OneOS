"""Bounded Java Installer routing/drain source audit. No native or OEM execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/retained-installd-routing'
SAMSUNG = ROOT.parent / 'firmware/samsung/runtime-20261104/services.jar'
HOST_SHA = 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
FRAMEWORK = ROOT.parent / 'firmware/samsung/framework.jar'
FRAMEWORK_SHA = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
STAGED = ROOT / 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/services_patched.jar'
STAGED_SHA = 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def query(archive, pin, label, **selector):
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'queries.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    old = next((row for row in rows if row['label'] == label), None)
    if old:
        assert old['selector'] == selector
        return json.loads((ROOT / old['receipt']).read_text())
    read = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    result = read(archive, pin, stream='retained-installd-routing', **selector)
    rows.append({'label': label, 'archiveSha256': pin, 'selector': selector, 'receipt': result['receipt']})
    path.write_text(json.dumps(rows, indent=2) + '\n')
    print(label, result['receipt'], flush=True)
    return result


def capture():
    query(SAMSUNG, HOST_SHA, 'host-Installer', class_name='com.android.server.pm.Installer', all_methods=True)
    for label, reference in [('host-Installer-roots', 'Lcom/android/server/pm/Installer;'),
                             ('host-IInstalld-roots', 'Landroid/os/IInstalld;'),
                             ('host-canonical-name', 'string=installd')]:
        query(SAMSUNG, HOST_SHA, label, reference=reference)
    query(FRAMEWORK, FRAMEWORK_SHA, 'framework-Installer-roots', reference='Lcom/android/server/pm/Installer;')
    query(STAGED, STAGED_SHA, 'guest-canonical-name', reference='string=installd')
    query(STAGED, STAGED_SHA, 'guest-IInstalld-roots', reference='Landroid/os/IInstalld;')


def references(label):
    ledger = json.loads((WORK / 'queries.json').read_text())
    saved = next(row for row in ledger if row['label'] == label)
    rec = json.loads((ROOT / saved['receipt']).read_text())
    assert sha(ROOT / rec['raw']) == rec['rawSha256']
    return [row for row in map(json.loads, (ROOT / rec['raw']).read_text().splitlines()) if row.get('record') == 'reference']


def capture_callers():
    groups = {}
    def add(caller):
        owner, method = caller.split('->', 1)
        if owner != 'Lcom/android/server/pm/Installer;':
            groups.setdefault(owner, set()).add(method)
    for row in references('host-IInstalld-roots'):
        if not row['caller'].startswith('Landroid/os/IInstalld$Stub;') and row['instruction']['opcode'].startswith('INVOKE'):
            add(row['caller'])
    for row in references('host-Installer-roots'):
        if row['instruction']['opcode'] in ('NEW_INSTANCE', 'CONST_CLASS'):
            add(row['caller'])
    for row in references('host-canonical-name'):
        add(row['caller'])
    for owner, methods in sorted(groups.items()):
        methods = sorted(methods)
        tag = hashlib.sha256(json.dumps(methods).encode()).hexdigest()[:8]
        query(SAMSUNG, HOST_SHA, 'callers-' + owner.split('/')[-1].rstrip(';') + '-' + tag,
              class_name=owner, methods=methods)
    for cls, label in [
        ('com.android.server.pm.Installer$$ExternalSyntheticLambda0', 'host-death-callback'),
        ('com.android.server.pm.Installer$$ExternalSyntheticLambda1', 'host-delayed-reconnect'),
        ('com.android.server.pm.Installer$Batch', 'host-batch'),
        ('com.android.server.files.InstalldProcessor$InstalldCallback', 'host-file-operation-callback'),
        ('com.android.server.files.InstalldProcessor$1', 'host-file-operation-result'),
    ]:
        query(SAMSUNG, HOST_SHA, label, class_name=cls, all_methods=True)
    query(SAMSUNG, HOST_SHA, 'host-HeimdAll-admission', class_name='com.android.server.HeimdAllFsService', methods=[
          'get(Landroid/content/Context;)Lcom/android/server/HeimdAllFsService;',
          'onRunRequested(Ljava/lang/Runnable;)Z', 'safeRun(Ljava/lang/Runnable;)V'])
    query(SAMSUNG, HOST_SHA, 'host-injector-getInstaller', class_name='com.android.server.pm.PackageManagerServiceInjector',
          methods=['getInstaller()Lcom/android/server/pm/Installer;'])


def report():
    """Verify saved static evidence; do not rerun archive readers or OEM code."""
    for path, pin in [(SAMSUNG, HOST_SHA), (FRAMEWORK, FRAMEWORK_SHA), (STAGED, STAGED_SHA)]:
        assert sha(path) == pin
    queries = json.loads((WORK / 'queries.json').read_text())
    receipts, raws, methods, declarations, by_label = {}, {}, {}, {}, {}
    for q in queries:
        rec = json.loads((ROOT / q['receipt']).read_text())
        assert rec['archiveSha256'] == q['archiveSha256']
        assert rec['readerExitCode'] == 0 and rec['archiveAndToolPinsVerifiedBeforeAndAfter']
        assert not rec['oemCodeExecuted'] and not rec['androidExecuted']
        assert sha(ROOT / rec['raw']) == rec['rawSha256']
        receipts[q['receipt']] = sha(ROOT / q['receipt'])
        raws[rec['raw']] = rec['rawSha256']
        rows = [json.loads(line) for line in (ROOT / rec['raw']).read_text().splitlines()]
        by_label[q['label']] = rows
        for row in rows:
            if row.get('record') == 'class':
                declarations[row['descriptor']] = row
            if row.get('record') == 'method':
                body = row['body']
                key = body['owner'] + '->' + body['signature']
                proof = {'bodySha256': row['normalizedBodySha256'], 'receipt': q['receipt'],
                         'raw': rec['raw'], 'physicalDex': row['physicalDex'],
                         'logicalHeaderOffset': row['logicalHeaderOffset']}
                if key in methods:
                    assert methods[key]['proof']['bodySha256'] == proof['bodySha256']
                methods[key] = {'body': body, 'proof': proof}
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(name)
    def refs(label):
        return [row for row in by_label[label] if row.get('record') == 'reference']
    all_native = refs('host-IInstalld-roots')
    native = [row for row in all_native if row['instruction']['opcode'].startswith('INVOKE')
              and not row['caller'].startswith('Landroid/os/IInstalld$Stub;')]
    check('IInstalld owner records exactly162 including160 invokes and2 type checks',
          len(all_native) == 162 and sum(x['instruction']['opcode'].startswith('INVOKE') for x in all_native) == 160)
    check('non-generated direct native cohort exactly75 sites/65 methods/29 classes',
          (len(native), len({x['caller'] for x in native}), len({x['caller'].split('->')[0] for x in native})) == (75, 65, 29))
    for row in native:
        check('native site ' + row['caller'] + '@' + str(row['instruction']['pc']),
              row['caller'] in methods and row['instruction'] in methods[row['caller']]['body']['instructions'])
    installer_refs = refs('host-Installer-roots')
    check('Samsung services Installer owner references exactly200', len(installer_refs) == 200)
    check('captured Samsung framework has no direct Installer owner references', len(refs('framework-Installer-roots')) == 0)
    check('canonical name source callers Installer plus independent HeimdAll',
          len(refs('host-canonical-name')) == 2 and
          {x['caller'].split('->')[0] for x in refs('host-canonical-name')} ==
          {'Lcom/android/server/pm/Installer;', 'Lcom/android/server/HeimdAllFsService;'})
    check('actual staged services has one canonical name lookup in Installer',
          len(refs('guest-canonical-name')) == 1 and refs('guest-canonical-name')[0]['caller'].startswith('Lcom/android/server/pm/Installer;->connect('))
    roots = [x for x in installer_refs if x['instruction']['opcode'] in ('NEW_INSTANCE', 'CONST_CLASS')]
    check('five source Installer creation roots include one reflective source root',
          len(roots) == 5 and Counter(x['instruction']['opcode'] for x in roots) == {'NEW_INSTANCE': 4, 'CONST_CLASS': 1})
    decl = declarations['Lcom/android/server/pm/Installer;']
    check('Installer19 methods and public volatile native interface/latch fields', decl['declaredMethodCount'] == 19 and
          all(next(x for x in decl['fields'] if x['name'] == n)['accessFlags'] == 65 for n in ['mInstalld', 'mInstalldLatch', 'mVold']))
    def at(owner, sig, pc, opcode=None, ref=None):
        key = owner + '->' + sig
        ins = next(x for x in methods[key]['body']['instructions'] if x['pc'] == pc)
        check(key + '@' + str(pc), (opcode is None or ins['opcode'] == opcode) and
              (ref is None or ref in ins.get('reference', '')))
    i = 'Lcom/android/server/pm/Installer;'
    for pc, ref in [(3, 'ServiceManager;->getService'), (21, 'linkToDeath'), (28, 'Stub;->asInterface'),
                    (32, 'mInstalld:'), (36, 'countDown'), (39, 'checkBeforeRemote'),
                    (44, 'invalidateMounts'), (51, 'setFirstBoot'), (84, 'postDelayed')]:
        at(i, 'connect()V', pc, ref=ref)
    at(i, 'checkBeforeRemote()V', 68, ref='await')
    at(i, 'checkBeforeRemote()V', 83, opcode='THROW')
    at(i, 'checkBeforeRemote()V', 84, opcode='RETURN_VOID')
    at(i, 'connectVold()V', 32, ref='mVold:')
    death = 'Lcom/android/server/pm/Installer$$ExternalSyntheticLambda0;'
    at(death, 'binderDied()V', 38, opcode='NEW_INSTANCE', ref='CountDownLatch')
    at(death, 'binderDied()V', 46, ref='Installer;->connect()')
    at('Lcom/android/server/pm/Installer$$ExternalSyntheticLambda1;', 'run()V', 4, ref='Installer;->connect()')
    batch = 'Lcom/android/server/pm/Installer$Batch;'
    at(batch, 'execute(Lcom/android/server/pm/Installer;)V', 65, ref='mInstalld:')
    at(batch, 'execute(Lcom/android/server/pm/Installer;)V', 67, ref='createAppDataBatched')
    at(batch, 'execute(Lcom/android/server/pm/Installer;)V', 93, ref='CompletableFuture;->complete')
    at(batch, 'execute(Lcom/android/server/pm/Installer;)V', 104, ref='completeExceptionally')
    heim = 'Lcom/android/server/HeimdAllFsService;'
    at(heim, '<init>(Landroid/content/Context;)V', 32, ref='mInstalld:')
    at(heim, '<init>(Landroid/content/Context;)V', 44, ref='newSingleThreadExecutor')
    at('Lcom/android/server/pm/PackageManagerServiceInjector;', 'getInstaller()Lcom/android/server/pm/Installer;', 0, ref='->mInstaller:')
    at('Lcom/android/server/pm/PackageManagerServiceInjector;', 'getInstaller()Lcom/android/server/pm/Installer;', 2, opcode='RETURN_OBJECT')
    # Reuse only the three exact production-instance factory bodies, not a new cold owner.
    owner_path = ROOT / 'inventory/samsung-user-registry-owner.json'
    check('frozen original production owner inventory pin', sha(owner_path) == 'd9470806703b02ddaf2a18b580b244061565a6c96a501292c0e3d353b8261f9e')
    owner = json.loads(owner_path.read_text())
    reused = {}
    reused_bodies = {}
    for key, proof in owner['methodProofs'].items():
        if any(term in key for term in ['PackageManagerService;->main(', 'PackageManagerService;-><init>(Lcom/android/server/pm/PackageManagerServiceInjector;Z)', 'PackageManagerService$$ExternalSyntheticLambda39;->produce(']):
            assert sha(ROOT / proof['raw']) == proof['rawSha256']
            reused[key] = proof
            raw_rows = [json.loads(x) for x in (ROOT / proof['raw']).read_text().splitlines()]
            chosen = next(x for x in raw_rows if x.get('record') == 'method' and
                          key.endswith(x['body']['owner'] + '->' + x['body']['signature']))
            assert chosen['normalizedBodySha256'] == proof['bodySha256']
            reused_bodies[key] = chosen['body']
    check('three actual PMS/preparer source factory proofs reused', len(reused) == 3)
    for fragment, pc, ref in [('PackageManagerService;->main(', 103, 'ExternalSyntheticLambda39;->f$1:'),
                              ('PackageManagerService;->main(', 374, 'Injector;->mInstaller:'),
                              ('PackageManagerService;-><init>(', 382, 'Injector;->getInstaller('),
                              ('PackageManagerService;-><init>(', 386, 'PackageManagerService;->mInstaller:'),
                              ('PackageManagerService;-><init>(', 956, 'EnterprisePartitionManager;->setInstaller('),
                              ('ExternalSyntheticLambda39;->produce(', 22, 'UserDataPreparer;->mInstaller:')]:
        body = next(v for k, v in reused_bodies.items() if fragment in k)
        check('production owner ' + fragment + '@' + str(pc),
              any(x['pc'] == pc and ref in x.get('reference', '') for x in body['instructions']))
    inputs = {
        'inventory/retained-guest-user-lifecycle.json': '731ac8031bf051c283d1cbb7ec23425d69d90c7a12b1895a547e9a64a5421040',
        'inventory/samsung-user-registry-owner.json': 'd9470806703b02ddaf2a18b580b244061565a6c96a501292c0e3d353b8261f9e',
        'inventory/installed-oneos-code-profile.json': 'e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a',
        'inventory/retained-installd-native-owner.json': '14d15d212d09deffd0decd0a2c0657af79e15dedadaa7251322bfaa0da2f9f47',
        'docs/retained-installd-native-owner.md': '1ea4aad9b4471c1f3a06edf70bfaa1309fa6d7f1ad9298d5762fccb8855f7b8c',
        'out/installed-oneos-code-profile/static/appdata-bridge-source.json': '07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
        'out/retention-native-view-observation/20261106T022427951464Z-d70f0ad08106435bb3bcac4bf737f458/observation.json': '2d55a1ae77a5886787926b307aaad1d2e76c33c2d167a7a1e72e6738bdec0f04'}
    for path, pin in inputs.items():
        check('literal existing evidence pin ' + path, sha(ROOT / path) == pin)
    result = {
        'schema': 'retained-installd-routing/v1', 'status': 'SOURCE_ROUTING_AND_DRAIN_FRONTIER_UNASSEMBLED',
        'selected': False, 'oemExecuted': False, 'androidExecuted': False, 'nativeExecuted': False, 'phoneActions': [],
        'sourceArchives': [{'path': str(p), 'sha256': h} for p, h in [(SAMSUNG, HOST_SHA), (FRAMEWORK, FRAMEWORK_SHA), (STAGED, STAGED_SHA)]],
        'inputs': inputs,
        'queryCount': len(queries), 'receiptPins': receipts, 'rawPins': raws,
        'methodProofs': {k: v['proof'] for k, v in sorted(methods.items())},
        'reusedProductionFactoryProofs': reused,
        'checks': checks, 'checkCount': len(checks),
        'installerReferences': [{'caller': x['caller'], **x['instruction']} for x in installer_refs],
        'nativeSites': [{'caller': x['caller'], **x['instruction']} for x in native],
        'nativeSitesByOwner': dict(sorted(Counter(x['caller'].split('->')[0] for x in native).items())),
        'creationRoots': roots, 'canonicalLookupSites': refs('host-canonical-name'),
        'guestIInstalldOwnerReferenceCount': len(refs('guest-IInstalld-roots')),
        'installerDeclaration': {'declaredMethodCount': decl['declaredMethodCount'], 'fields': decl['fields']},
        'routeA': 'Host cohort and independent cached interfaces require real admission/active-call/async/death/reconnect drain before private endpoint migration; global guest binds still expose native state outside14 pairs.',
        'routeB': 'Keep initialized host canonical endpoint/cache relationships; change guest first lookup and native publisher/view before effects, and replace or segregate global14 binds for every host native consumer.',
        'firstMissingOwner': 'No source-owned complete native-writer admission/drain and endpoint-generation/view handoff covers the captured host cohort, independent HeimdAll and native pending operations.',
        'nextEngineeringAction': 'Root selects whether to prove guest-private native publisher plus coherent private pre-main path plan (B) before authoring any host-interface migration (A); neither alias nor PID/cache capture is readiness.',
        'limits': ['Direct reference closure in these pinned archives only; reflection/other archives/loaded heap not inventoried.',
                   'All source construction roots are potential, not observed live instances.',
                   'No native completion, exclusive writer, namespace handoff, runtime routing or crypto acceptance proved.',
                   'Guest OneOSInstalldProxy IBinder.transact operations are not exhaustively represented by IInstalld-owner counts.',
                   'Peer native analysis reused without duplicate native decoding.'],
        'toolSha256': sha(Path(__file__))}
    target = ROOT / 'inventory/retained-installd-routing.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'inventory': str(target), 'checks': len(checks), 'methods': len(methods),
                      'nativeSites': len(native), 'queries': len(queries)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--capture-callers', action='store_true')
    p.add_argument('--report', action='store_true')
    args = p.parse_args()
    if args.capture:
        capture()
    if args.capture_callers:
        capture_callers()
    if args.report:
        report()
