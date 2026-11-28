"""Static factory/lifecycle proof; emits a proposal, never an endpoint or DEX hook."""
import argparse, hashlib, json, runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
WORK = ROOT / 'out/guest-metrics-endpoint'
ARCHIVE = PARENT / 'firmware/donor/extracted/system/framework/services.jar'
PIN = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
COMMIT = '1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe'
QUERIES = {
    'com.android.server.display.DisplayManagerService': ['<init>(Landroid/content/Context;)V', '<init>(Landroid/content/Context;Lcom/android/server/display/DisplayManagerService$Injector;)V', 'onStart()V', 'onBootPhase(I)V'],
    'com.android.server.display.DisplayManagerService$BinderService': ['<init>(Lcom/android/server/display/DisplayManagerService;)V'],
}
AUXILIARY = {
    'extension-onstart': ('oplus-services.jar', 'cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39', 'com.android.server.display.DisplayManagerServiceExtImpl', ['onStart(Landroid/os/Binder;)V']),
    'extension-bootphase': ('oplus-services.jar', 'cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39', 'com.android.server.display.DisplayManagerServiceExtImpl', ['onBootComplete(I)V']),
    'loader-0': ('framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2', 'com.android.internal.os.ZygoteInit', ['getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;', 'createPathClassLoader(Ljava/lang/String;I)Ljava/lang/ClassLoader;']),
    'loader-1': ('services.jar', PIN, 'com.android.server.SystemServiceManager', ['startService(Ljava/lang/Class;)Lcom/android/server/SystemService;']),
    'publication': ('services.jar', PIN, 'com.android.server.SystemService', ['publishBinderService(Ljava/lang/String;Landroid/os/IBinder;Z)V', 'publishBinderService(Ljava/lang/String;Landroid/os/IBinder;ZI)V']),
    'lifecycle-dispatch': ('services.jar', PIN, 'com.android.server.SystemServiceManager', ['startService(Lcom/android/server/SystemService;)V', 'startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V']),
}

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read():
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'reads.json'
    reads = json.loads(path.read_text()) if path.exists() else {}
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for name, methods in QUERIES.items():
        if name not in reads:
            receipt = reader(ARCHIVE, PIN, class_name=name, methods=methods, stream='guest-metrics-endpoint')
            reads[name] = receipt['receipt']
            path.write_text(json.dumps(reads, indent=2) + '\n')
        receipt = json.loads((ROOT / reads[name]).read_text())
        assert receipt['archiveSha256'] == PIN and receipt['query']['exactMethods'] == methods
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        print(name, reads[name], flush=True)
    for name, (filename, pin, class_name, methods) in AUXILIARY.items():
        target = WORK / (name + '.json')
        if not target.exists():
            receipt = reader(PARENT / 'firmware/donor/extracted/system/framework' / filename, pin, class_name=class_name, methods=methods, stream='guest-metrics-endpoint')
            target.write_text(json.dumps(receipt, indent=2) + '\n')
        receipt = json.loads(target.read_text())
        assert receipt['archiveSha256'] == pin and receipt['query']['exactMethods'] == methods
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        print(name, receipt['receipt'], flush=True)

def summarize():
    evidence, methods, declarations = [], {}, {}
    def collect(key, receipt_path, only=None):
        receipt = json.loads((ROOT / receipt_path).read_text())
        assert not receipt['oemCodeExecuted']
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        selected = []
        for number, line in enumerate((ROOT / receipt['raw']).read_text().splitlines(), 1):
            row = json.loads(line)
            if row['record'] == 'class':
                declarations[row['descriptor']] = row
            if row['record'] != 'method' or (only and row['body']['signature'] not in only):
                continue
            body = row['body']
            methods[(key, body['signature'])] = body
            proof, = [p for p in receipt['selectedMethodProofs'] if p['signature'] == body['signature']]
            selected.append({**proof, 'rawMethodLine': number})
        evidence.append({'key': key, 'receipt': receipt_path, 'receiptSha256': digest(ROOT / receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': selected})
    for name, receipt in json.loads((WORK / 'reads.json').read_text()).items():
        collect(name, receipt)
    for name in AUXILIARY:
        item = json.loads((WORK / (name + '.json')).read_text())
        collect(name, item['receipt'])
    prior = ROOT / 'inventory/construction-startup.json'
    assert digest(prior) == '998bd293e7cf598e76d4f60ec1b45a22e4417001aa38d4fe953f6b697a9706ef'
    entry, = [e for e in json.loads(prior.read_text())['methodEvidence'] if isinstance(e, dict) and e.get('receipt') == 'out/tooling/20261105T144235058123Z-c0248b12b8364dc3af57d59b8e8f69ca/receipt.json']
    collect('reuse:guest-SystemServer', entry['receipt'], ['startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V'])
    producer = ROOT / 'inventory/guest-metrics-producer.json'
    assert digest(producer) == '0995fcd8238ca88e674cc7e6ef8d54e0e3b2433c0d84d864e0c795822d4161f9'
    for e in json.loads(producer.read_text())['methodEvidence']:
        if e['key'] == 'reuse:coloros-services:com.android.server.display.DisplayManagerService$BinderService':
            collect('reuse:original-getter', e['receipt'], ['getDisplayInfo(I)Landroid/view/DisplayInfo;'])
    assertions = []
    def edge(key, signature, pc, suffix):
        instruction, = [i for i in methods[(key, signature)]['instructions'] if i['pc'] == pc]
        assert instruction.get('reference', '').endswith(suffix), (key, signature, hex(pc))
        assertions.append({'selection': key, 'method': signature, 'pc': hex(pc), 'referenceSuffix': suffix})
    dms = 'com.android.server.display.DisplayManagerService'
    ctor = '<init>(Landroid/content/Context;Lcom/android/server/display/DisplayManagerService$Injector;)V'
    for pc, suffix in [(0x2a, '->mSyncRoot:Lcom/android/server/display/DisplayManagerService$SyncRoot;'), (0xcd, '->create(Ljava/lang/Class;Ljava/lang/Object;)Ljava/lang/Object;'), (0xd3, '->mDmsExt:Lcom/android/server/display/IDisplayManagerServiceExt;'), (0xfe, '->mInjector:Lcom/android/server/display/DisplayManagerService$Injector;'), (0x100, '->mContext:Landroid/content/Context;'), (0x10d, '->mHandler:Lcom/android/server/display/DisplayManagerService$DisplayManagerHandler;'), (0x2ce, '->init(Landroid/content/Context;Lcom/android/server/display/DisplayManagerService$SyncRoot;)V')]:
        edge(dms, ctor, pc, suffix)
    for pc, suffix in [(5, '->loadIfNeeded()V'), (0xf, '->sendEmptyMessage(I)Z'), (0x12, '->invalidateLocalDisplayInfoCaches()V'), (0x15, 'Lcom/android/server/display/DisplayManagerService$BinderService;'), (0x17, '-><init>(Lcom/android/server/display/DisplayManagerService;)V'), (0x1c, '->onStart(Landroid/os/Binder;)V'), (0x21, '->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;Z)V'), (0x32, '->publishLocalService(Ljava/lang/Class;Ljava/lang/Object;)V')]:
        edge(dms, 'onStart()V', pc, suffix)
    onstart = methods[(dms, 'onStart()V')]['instructions']
    for pc in [0x15, 0x17, 0x1c, 0x21]:
        ins, = [i for i in onstart if i['pc'] == pc]
        assert 0 in ins['registers']
    assert next(i for i in onstart if i['pc'] == 0x35)['opcode'] == 'RETURN_VOID'
    for pc, suffix in [(0x1a, '->getDisplayLocked(I)Lcom/android/server/display/LogicalDisplay;'), (0x20, '->mVirtualDisplayAdapter:Lcom/android/server/display/VirtualDisplayAdapter;'), (0x53, '->wait(J)V'), (0xfb, '->onBootComplete(I)V'), (0x111, '->onBootPhase(I)V')]:
        edge(dms, 'onBootPhase(I)V', pc, suffix)
    phase = methods[(dms, 'onBootPhase(I)V')]['instructions']
    assert next(i for i in phase if i['pc'] == 0)['literal'] == 100
    assert next(i for i in phase if i['pc'] == 0x25)['opcode'] == 'MONITOR_EXIT'
    assert next(i for i in phase if i['pc'] == 0x26)['targetPc'] == 0xf9
    assert phase[-1]['pc'] == 0x114 and phase[-1]['opcode'] == 'RETURN_VOID'
    edge('com.android.server.display.DisplayManagerService$BinderService', '<init>(Lcom/android/server/display/DisplayManagerService;)V', 6, '->fromContext(Landroid/content/Context;)Landroid/os/PermissionEnforcer;')
    edge('extension-onstart', 'onStart(Landroid/os/Binder;)V', 0xd, '->setExtension(Landroid/os/IBinder;)V')
    edge('loader-0', 'getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;', 6, '->getenv(Ljava/lang/String;)Ljava/lang/String;')
    edge('loader-0', 'getOrCreateSystemServerClassLoader()Ljava/lang/ClassLoader;', 0xe, '->createPathClassLoader(Ljava/lang/String;I)Ljava/lang/ClassLoader;')
    edge('loader-0', 'createPathClassLoader(Ljava/lang/String;I)Ljava/lang/ClassLoader;', 0x13, '->createClassLoader(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/ClassLoader;IZLjava/lang/String;)Ljava/lang/ClassLoader;')
    edge('loader-1', 'startService(Ljava/lang/Class;)Lcom/android/server/SystemService;', 0x53, '->newInstance([Ljava/lang/Object;)Ljava/lang/Object;')
    edge('lifecycle-dispatch', 'startService(Lcom/android/server/SystemService;)V', 0x30, '->add(Ljava/lang/Object;)Z')
    edge('lifecycle-dispatch', 'startService(Lcom/android/server/SystemService;)V', 0x37, '->onStart()V')
    edge('lifecycle-dispatch', 'startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V', 0xab, '->onBootPhase(I)V')
    edge('publication', 'publishBinderService(Ljava/lang/String;Landroid/os/IBinder;ZI)V', 0, '->addService(Ljava/lang/String;Landroid/os/IBinder;ZI)V')
    ss = 'startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V'
    for pc, suffix in [(0x1fd, 'Lcom/android/server/display/DisplayManagerService;'), (0x1ff, '->startService(Ljava/lang/Class;)Lcom/android/server/SystemService;'), (0x213, '->startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V')]:
        edge('reuse:guest-SystemServer', ss, pc, suffix)
    for pc, suffix in [(0, '->getCallingUid()I'), (4, '->clearCallingIdentity()J'), (0xe, '->restoreCallingIdentity(J)V')]:
        edge('reuse:original-getter', 'getDisplayInfo(I)Landroid/view/DisplayInfo;', pc, suffix)
    fields = declarations['Lcom/android/server/display/DisplayManagerService;']['fields']
    assert not any('mBinderService' in str(field) for field in fields)
    upstream = ROOT / 'firmware/guest-metrics-endpoint/upstream' / COMMIT
    assert digest(upstream / 'FETCH.json') == '79d519121eab61ed0950abef01240bd24428ac8ba1d85d5b62ffeac2ae75d96f'
    fetched = json.loads((upstream / 'FETCH.json').read_text())
    pins = []
    for item in fetched['files']:
        path = upstream / item['upstreamPath']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
        pins.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': item['bytes'], 'sha256': item['sha256'], 'upstreamPath': item['upstreamPath']})
    source_root = ROOT / 'firmware/method-review-upstream' / COMMIT
    for rel, pin in [('scripts/make-overlays.sh', '0b78130dc8872a0d57a566a24359c1e3132f331b37bb4e373231c870b79f58d2'), ('switcher/assets/guest_start.sh', '896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446')]:
        path = source_root / rel
        assert digest(path) == pin
        pins.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path), 'upstreamPath': rel})
    result = {'schema': 'guest-metrics-endpoint/v1', 'status': 'SOURCE_API_PROPOSAL_ONLY_DEFAULT_OFF', 'methodEvidence': evidence, 'assertions': assertions, 'assertionCount': len(assertions), 'newBodyCount': sum(len(e['methods']) for e in evidence if not e['key'].startswith('reuse:')), 'reusedBodyCount': sum(len(e['methods']) for e in evidence if e['key'].startswith('reuse:')), 'producerInput': {'path': producer.relative_to(ROOT).as_posix(), 'sha256': digest(producer)}, 'oneos': {'commit': COMMIT, 'files': pins, 'fetchReceiptSha256': digest(upstream / 'FETCH.json'), 'scriptsExecuted': False, 'installedBytesIdentified': False}, 'proposedLifecycle': ['Original base DMS.onStart normal tail after PC32 and before35 captures actual this and live born Binder v0; prepare once, no getter/readiness/publication', 'Original DMS.onBootPhase normal completion PC114 with actual phase100 activates the same owner only after original default-display wait and existing extension/tail work', 'Default off; selected source/DEX/loader hooks and publication are NOT emitted or installed', 'Retain exact DMS/Binder/producer/endpoint and source loader for the same process lifetime; endpoint death/retirement invalidates consumer bootstrap, no silent relookup/retry/default', 'OneOS return/quiescence and real physical-display/cache-generation admission remain unassembled'], 'proposedWire': {'descriptor': 'com.appleexploit.oneos.security.IGuestDisplayMetrics.v1', 'transaction': 1, 'flags': 0, 'request': ['interface token', 'int version=1', 'int displayId', 'no trailing data'], 'successReply': ['writeNoException', 'int version=1', 'int displayId echo', 'int status: 0=ABSENT,1=SAMPLE', 'SAMPLE only: int appWidth,int appHeight,int logicalDensityDpi,int physicalXDpiBits,int physicalYDpiBits', 'no trailing data'], 'errors': 'original getter exceptions preserve cause/type to normal Binder-supported exception transport; unsupported Throwable fails transaction, never absent/default. No automatic retry. Version/token/flags/length mismatch rejected before getter.', 'boundedSizes': 'request contains two scalar ints after bounded interface token; reply has three scalar ints or eight after exception envelope; no arbitrary Parcelable, list, array, string payload or caller identity args'}, 'callerPolicy': ['Feature-specific metadata protocol under exactly original getDisplayInfo caller/access visibility policy', 'One same-thread direct getter; no identity clear by authored endpoint/extractor, no handler hop, no caller-supplied UID/PID', 'Original getter captures native callingUID then clears/restores internally as original policy; producer checks native UID/PID around successful extraction', 'Discoverable alias/shared UID/class shape are not Samsung authority or code/source/state attestation; no extra grants or security-authentication claims'], 'unclosed': ['Exact default-off source-profile/DEX retarget/inverse and helper classloader selection', 'Approved endpoint implementation and actual publication owner/order/no-collision handling', 'Selected patched guest byte identity; seven inspected patchers are producer intent only, not installed image audit', 'Actual endpoint/source/cache/physical-generation lifetime, exception serialization and process death/return drain', 'Samsung CompatSandbox/RM/config/CompatibilityInfo consumer plus boot-visible helper/callsite admission and complete process-local cache-map installation'], 'toolSha256': digest(__file__), 'runtimeCodeEmitted': False, 'oemCodeExecuted': False, 'phoneChanged': False}
    (ROOT / 'inventory/guest-metrics-endpoint.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'assertions': len(assertions), 'newBodies': result['newBodyCount'], 'reusedBodies': result['reusedBodyCount'], 'sourceOnly': True, 'oemCodeExecuted': False}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.summarize:
        summarize()
