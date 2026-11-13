"""Derive one non-executable private-view operation plan from pinned source.

No shell/launcher is emitted: the actual private-preparation and two-view
mirror/volume/retirement owners do not yet exist. This tool parses/hash-checks
saved source and metadata only; it never invokes scripts, mounts or OEM code.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'out/guest-private-data-plan'
RAW = ROOT / 'firmware/guest-private-data-plan'
INPUTS = {
    'inventory/guest-installd-data-view.json': 'b1381a57c778366a5e3c6586dfffd58c63b89ef237a2bd10c0b39448dbf64801',
    'inventory/retained-installd-native-owner.json': '14d15d212d09deffd0decd0a2c0657af79e15dedadaa7251322bfaa0da2f9f47',
    'inventory/retained-installd-routing.json': 'effb6cef11e13ee4c42f626f110e746ecbdace812f52f3af9eaaf00deeb0f62a',
    'inventory/guest-installd-alias.json': '5bbe42e826d3851bff2d3348657b28008c1c893ad5d510b167f3bd9ecaaf5068',
    'out/installed-oneos-code-profile/static/appdata-bridge-source.json': '07e8bcf175ece148ae86a7d81435fbe0c40bdb9b6fab4aeffa8d91702691c040',
    'out/retention-native-view-observation/20261106T022427951464Z-d70f0ad08106435bb3bcac4bf737f458/observation.json': '2d55a1ae77a5886787926b307aaad1d2e76c33c2d167a7a1e72e6738bdec0f04',
    'out/guest-installd-alias/20261106T040812300982Z-271fd9053e2c4d8983463e6e76a43a76/receipt.json': 'e81fd1dc1e04d6ac78a13b3303e229f360210c0c87550dbcd5e0d199881f34a5',
    'out/guest-installd-alias/20261106T040812300982Z-271fd9053e2c4d8983463e6e76a43a76/installd-guest-nstalld': '511dac7eae780ad476c84953805a380e4943175672503d9c53b264b6cad54a1e',
}
ASSETS = 'firmware/installed-oneos-code-profile/static/assets/'
SPANS = {
    'oneos_switch.sh': [(72, 80), (969, 1000), (1086, 1091), (1417, 1428)],
    'guest_prepare.sh': [(1, 24), (3239, 3292)],
    'guest_start.sh': [(11, 20), (53, 85)],
    'return_to_oneui.sh': [(343, 363), (575, 588)],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main():
    checks = []
    for path, expected in INPUTS.items():
        assert sha(ROOT / path) == expected, path
        checks.append('immutable input ' + path)
    bridge = load('out/installed-oneos-code-profile/static/appdata-bridge-source.json')
    assets = {}
    excerpts = {}
    for name, pin in bridge['assets'].items():
        assert pin['path'] == ASSETS + name
        assert sha(ROOT / pin['path']) == pin['sha256']
        assets[name] = (ROOT / pin['path']).read_text(encoding='utf-8').splitlines()
        checks.append('installed asset ' + name)
        excerpts[name] = [{'first': a, 'last': b, 'lines': assets[name][a - 1:b]} for a, b in SPANS.get(name, [])]

    def edge(name, line, token):
        assert token in assets[name][line - 1], (name, line, token)
        checks.append(f'{name}:{line} {token}')

    for name, line, token in [
        ('oneos_switch.sh', 79, 'nsenter -t 1 -m'),
        ('oneos_switch.sh', 971, 'setprop ctl.stop zygote'),
        ('oneos_switch.sh', 999, 'kill -9 $(pidof system_server)'),
        ('oneos_switch.sh', 1087, '/system/bin/sh "$STAGE/guest_prepare.sh"'),
        ('oneos_switch.sh', 1418, 'unshare -m'),
        ('guest_prepare.sh', 7, 'readlink /proc/1/ns/mnt'),
        ('guest_prepare.sh', 21, '/proc/self/mountinfo'),
        ('guest_prepare.sh', 3244, 'mount --bind "$STAGE/data/$s" "/data/$h"'),
        ('guest_prepare.sh', 3252, 'stat -c %d:%i'),
        ('guest_prepare.sh', 3260, 'mount --bind "$STAGE/data" "$ROOTFS/data"'),
        ('guest_prepare.sh', 3266, 'mount --make-private "$ROOTFS/data"'),
        ('guest_prepare.sh', 3267, 'mount --bind /data/adb'),
        ('guest_prepare.sh', 3268, 'mount --bind /data/apex'),
        ('guest_prepare.sh', 3287, 'remount,bind,ro,nosuid,nodev,noatime'),
        ('guest_start.sh', 12, 'cd /data/local/tmp/oneos/rootfs'),
        ('guest_start.sh', 13, 'mount --make-rprivate /'),
        ('guest_start.sh', 14, 'pivot_root . postinstall'),
        ('guest_start.sh', 57, 'pass_through|installer|androidwritable|runtime|user'),
        ('guest_start.sh', 71, 'mount --make-shared /mnt'),
        ('guest_start.sh', 77, 'mount --bind /data/user/0 /data/data'),
        ('guest_start.sh', 78, 'mount -t tmpfs tmpfs /data_mirror'),
        ('guest_start.sh', 81, 'data_mirror/data_de/null/0'),
        ('guest_start.sh', 82, 'data_mirror/data_ce/null/0'),
        ('return_to_oneui.sh', 351, 'umnt "/data/$d" || umnt -l'),
        ('return_to_oneui.sh', 580, 'nsenter -t "${p##*/}" -m'),
        ('return_to_oneui.sh', 588, 'umount -l "$mp"'),
    ]:
        edge(name, line, token)
    pairs = bridge['bridgePairs']
    assert len(pairs) == 14 and len({p['host'] for p in pairs}) == 14
    assert all(p['host'].startswith('/data/') and p['staged'].startswith('/data/local/tmp/oneos/data/') for p in pairs)
    matrix = []
    for p in pairs:
        relative = p['host'].removeprefix('/data/')
        ordinary_source = '/data/local/tmp/oneos/data/' + relative
        covered = p['staged'] == ordinary_source
        matrix.append({**p, 'proposedDaemonPath': p['host'], 'proposedGuestPath': p['host'],
                       'coverageAfterPrivateWholeDataBind': 'same-relative subtree' if covered else 'requires explicit user0 legacy alias',
                       'additionalBind': None if covered else {'source': '/data/user/0', 'target': '/data/data'},
                       'runtimeObjectIdentity': 'UNOBSERVED; future owner must open/admit actual directory objects',
                       'exclusiveConsumerProved': False})
    assert sum(r['additionalBind'] is None for r in matrix) == 13
    assert [r for r in matrix if r['additionalBind']][0]['host'] == '/data/data'
    checks.append('all14 source/target rows;13 inherited by private whole-data bind+1 explicit alias')

    observation_path = next(p for p in INPUTS if p.endswith('/observation.json'))
    observation = load(observation_path)
    roles = {p['role']: p for p in observation['processes']}
    assert roles['installd']['identity']['pid'] == 2493
    assert roles['init']['mountNamespaceBeforeAfter'] == roles['installd']['mountNamespaceBeforeAfter'] == 'mnt:[4026532781]'
    server = next(p for p in observation['processes'] if p['identity']['pid'] == 27202)
    assert server['mountNamespaceBeforeAfter'] == 'mnt:[4026536359]'
    def data_mount(p):
        return next(m for m in p['selectedMounts'] if m['mountpoint'] == '/data')
    assert data_mount(roles['init'])['propagation'] == ['shared:48']
    assert data_mount(roles['installd'])['propagation'] == ['shared:48']
    assert data_mount(server)['propagation'] == ['master:48']
    assert not observation['allThreadViewsObserved'] and not observation['futureOneOsMountPropagationProved']
    checks.append('qualified actual init/installd shared48 and SS master48 main-thread observation')

    routing = load('inventory/retained-installd-routing.json')
    quota_receipt = 'out/tooling/20261106T025912570524Z-585546ab773648fc94550068036d10b4/receipt.json'
    assert sha(ROOT / quota_receipt) == routing['receiptPins'][quota_receipt]
    qreceipt = load(quota_receipt)
    assert sha(ROOT / qreceipt['raw']) == qreceipt['rawSha256']
    qrows = [json.loads(s) for s in (ROOT / qreceipt['raw']).read_text(encoding='utf-8').splitlines()]
    quota, = [r for r in qrows if r['record'] == 'method' and r['body']['owner'] == 'Lcom/android/server/storage/CacheQuotaStrategy;' and r['body']['signature'] == 'pushProcessedQuotas(Ljava/util/List;)V']
    assert quota['normalizedBodySha256'] == '156acdc63b073389fa65d2d86d9a067eb7d0a078065874e33293c93e033cdbea'
    qcall, = [i for i in quota['body']['instructions'] if i['pc'] == 52]
    assert qcall['reference'] == 'Landroid/os/IInstalld;->setAppQuota(Ljava/lang/String;IIJ)V'
    checks.append('actual host CacheQuotaStrategy native quota writerPC52; namespace does not supply separate kernel quota')

    operations = [
        {'id': 'P0', 'kind': 'required-source-integration', 'namespace': 'none-created',
         'action': 'Replace the current switch/prepare entry before ctl.stop971; never execute unchanged switch or non-init-refusing preparer as this recipe.',
         'requires': 'new reviewed preparation/return producer that owns actual child namespace/root/source handles before any mutation', 'implemented': False},
        {'id': 'P1', 'kind': 'retain-actual-objects', 'namespace': 'proposed-supervisor',
         'action': 'Open/admit staged data, prepared ColorOS root, immutable Samsung code/library/APEX cohort and only required explicit host read-only children; retain opened identities/generations across later /data shadow.',
         'requires': 'real handles and filesystem/label/user/state admission; source spelling alone is insufficient', 'implemented': False},
        {'id': 'N1', 'kind': 'create-private-mount-view', 'namespace': 'proposed-daemon-child',
         'action': 'Create fresh mount namespace; apply recursive-private propagation before any bind; verify all relevant root/data ancestor mounts and host invariants before proceeding.',
         'requires': 'actual kernel namespace/propagation owner; unshare alone still inherits propagation', 'implemented': False},
        {'id': 'M1', 'kind': 'bind-existing-object', 'namespace': 'proposed-daemon-child', 'sourceObject': 'admitted staged-data directory handle', 'target': '/data',
         'action': 'Bind whole actual staged data into the Samsung-root child only; do not change init/canonical installd/retained SS views.',
         'inverse': 'ordinary unmount of this exact child mount after all descendants/users drain; retain on uncertainty'},
        {'id': 'M2', 'kind': 'bind-existing-object', 'namespace': 'proposed-daemon-child', 'sourceObject': 'admitted staged user/0 directory handle', 'target': '/data/data',
         'action': 'Create explicit legacy alias; other13 bridge rows are descendants ofM1.', 'inverse': 'unmount exact child alias beforeM1 after users drain'},
        {'id': 'M3', 'kind': 'explicit-shared-readonly-children', 'namespace': 'proposed-daemon-child',
         'action': 'Only if required/admitted, import retained original adb/APEX child objects and prove per-bind read-only; no fallback to the preparer warning-only writable case.',
         'requires': 'actual original runtime/root-manager owner; not guest-owned mutable metadata', 'inverse': 'unmount exact imports beforeM1 after users drain'},
        {'id': 'G1', 'kind': 'prepare-second-receiver', 'namespace': 'proposed-ColorOS-child',
         'action': 'Provide same admitted staged-data backing and explicit legacy alias inside the admitted ColorOS root; keep a distinct mount/root view so its pivot never substitutes the Samsung clone runtime.',
         'requires': 'real original-root/current-directory/executable handles before /data shadow and source-owned guest_start derivation', 'implemented': False},
        {'id': 'V1', 'kind': 'required-volume-and-mirror-owner', 'namespace': 'both-proposed-children',
         'action': 'Supply actual user/UUID mappings, data_ce/de and misc_ce/de mirrors plus profiles to both receivers; acknowledged later native mount/unmount changes must reach the actual guest app/zygote view.',
         'requires': 'new two-view update/acknowledgement owner; backing-directory equality does not propagate mount events', 'implemented': False},
        {'id': 'Q1', 'kind': 'required-filesystem-policy-owner', 'namespace': 'both-proposed-children',
         'action': 'Admit actual filesystem/UID/project-ID/quota/labels/serial/FBE and each caller-selected path; do not force null UUID or return fabricated success.',
         'requires': 'real /mnt/expand objects and native quota/project policy; no distinct quota or UID namespace is implied', 'implemented': False},
        {'id': 'W1', 'kind': 'required-other-writer-owners', 'namespace': 'host-and-guest-routes',
         'action': 'Replace every reliance on global14binds for actual guest/native/profile/artd/idmap/scaffolding consumers while preserving host canonical data routes.',
         'requires': 'complete same-object route/epoch and real script/native asynchronous drain, not exclusive installd assumption', 'implemented': False},
        {'id': 'A1', 'kind': 'deferred-native-admission', 'namespace': 'proposed-daemon-child',
         'action': 'Only after previous real obligations, admit the unselected511dac nstalld prototype and complete guest protocol/name/caller routing, retaining host canonical endpoint.',
         'requires': 'actual loaded identity/policy/pre-main layout/migration/state owner and post-publication cache acknowledgement', 'implemented': False},
        {'id': 'R1', 'kind': 'required-inverse-owner', 'namespace': 'owned-child-views-only',
         'action': 'Stop new guest admission, drain actual file/native/mirror/scaffolder operations and persistent commits, then unmount owned child descendants in reverse order. Never run the old global14-target return loop or namespace path sweep as this inverse.',
         'requires': 'actual accepted-work and exact mount-ID/namespace-handle ledger; lazy detach/PID/log do not acknowledge drain', 'implemented': False},
    ]
    assert all(o['namespace'] not in ('init', 'host-installd', 'host-system-server') for o in operations)
    inverse_order = ['stop-admission-and-drain-R1', 'all-native-generated-UUID/mirror/submounts', 'guest-receiver-submounts-and-view', 'M3-imports', 'M2-legacy-alias', 'M1-private-data', 'release-child-namespace-and-held-objects']
    assert inverse_order.index('M2-legacy-alias') < inverse_order.index('M1-private-data')
    save(RAW / 'selected-script-lines.json', excerpts)
    plan = {'schema': 'guest-private-data-operation-plan/v1', 'status': 'NON_EXECUTABLE_SOURCE_RECIPE_BLOCKED_AT_P0',
            'candidateTopology': 'B: retained host canonical daemon plus proposed fresh guest Samsung-root clone and separate ColorOS-root receiver',
            'operations': operations, 'bridgeCoverage': matrix, 'inverseOrder': inverse_order,
            'inverseScope': 'only future-owned mount topology after real drain; never undo native layout migrations, app-data writes, quotas or legitimate security commits',
            'shellEmitted': False, 'launcherEmitted': False, 'selected': False,
            'firstUnboundOwner': operations[0],
            'nextConcreteImplementationBoundary': {'replace': ['oneos_switch entry before971 and prepare invocation1087', 'guest_prepare init-namespace guard7–10 and global14loop3240–3258', 'guest_prepare data/readonly-child receiver3260–3292', 'guest_start pathname/pivot/private-root11–20 and mirrors77–85', 'return_to_oneui global14unmount349–363 and cross-namespace sweep575–588'],
                                                   'supply': 'one reviewed private-preparation/return owner with real source/root/namespace handles and owned operation ledger, before any original host stop or global overbind',
                                                   'notEnough': 'editing only unshare/guard, using alias511dac, or emitting an always-refusing shell with fake capabilities'},
            'laterUnclosed': ['nonnullUUID/expand real mapping','two independent private mirror/user/volume receivers and future updates','other globalbind consumers and background writers','quota/projectID/caller-path/serial/labels/physicalFBE owner','service protocol/property/context generation and native drain']}
    save(OUT / 'operation-plan.json', plan)
    result = {'schema': 'guest-private-data-plan/v1', 'status': plan['status'], 'selected': False, 'shellEmitted': False, 'launcherEmitted': False,
              'scriptsExecuted': False, 'nativeExecuted': False, 'deviceAccess': False,
              'toolSha256': sha(Path(__file__)), 'inputs': INPUTS, 'assetPins': bridge['assets'],
              'rawSource': {'path': (RAW / 'selected-script-lines.json').relative_to(ROOT).as_posix(), 'sha256': sha(RAW / 'selected-script-lines.json')},
              'operationPlan': {'path': (OUT / 'operation-plan.json').relative_to(ROOT).as_posix(), 'sha256': sha(OUT / 'operation-plan.json')},
              'checkCount': len(checks), 'checks': checks, 'all14Matrix': matrix,
              'observedNativeViews': {'observation': observation_path, 'initAndInstalldMainNamespace': '4026532781', 'systemServerMainNamespace': '4026536359',
                                      'dataPropagation': 'init+installd shared48; SS master48', 'allThreadViews': False, 'futurePropagationProved': False,
                                      'observedDataFilesystem': data_mount(roles['init'])},
              'quotaWriter': {'owner': quota['body']['owner'], 'method': quota['body']['signature'], 'pc': 52, 'reference': qcall['reference'],
                              'bodySha256': quota['normalizedBodySha256'], 'receipt': quota_receipt, 'receiptSha256': sha(ROOT / quota_receipt),
                              'raw': qreceipt['raw'], 'rawSha256': qreceipt['rawSha256'],
                              'scope': 'real native quota request; no new native setter decode or separate project/UID quota assignment claimed'},
              'firstUnboundOwner': plan['nextConcreteImplementationBoundary'], 'inverseScope': plan['inverseScope'],
              'limits': ['Path spellings are not acquired directory objects or immutable contents/label/policy epochs.',
                         'Private mount topology does not isolate shared backing files, filesystem quota, properties, Binder driver or native object state.',
                         'No shell emitted because the first real preparation owner and later UUID/mirror/native-consumer obligations are unassembled.',
                         'Alias511dac is a static component only; host canonical endpoint/native identity not reattested here.']}
    save(ROOT / 'inventory/guest-private-data-plan.json', result)
    save(OUT / 'receipt.json', {'status': result['status'], 'checkCount': len(checks), 'bridgePairs': len(matrix), 'coveredByWholeData': 13, 'explicitAlias': 1,
                              'operationCount': len(operations), 'inventorySha256': sha(ROOT / 'inventory/guest-private-data-plan.json'),
                              'toolSha256': result['toolSha256'], 'shellEmitted': False, 'scriptsOrNativeExecuted': False})
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'bridgePairs': len(matrix), 'coveredByWholeData': 13,
                      'explicitLegacyAlias': 1, 'operations': len(operations), 'shellEmitted': False}, indent=2))


if __name__ == '__main__':
    main()
