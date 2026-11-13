"""Static ownership/caller proof for a genuine guest DMS metrics extractor."""
import argparse, hashlib, json, runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
WORK = ROOT / 'out/guest-metrics-producer'
ARCHIVE = PARENT / 'firmware/donor/extracted/system/framework/services.jar'
PIN = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
EXT = PARENT / 'firmware/donor/extracted/system/framework/oplus-services.jar'
EXT_PIN = 'cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39'
QUERIES = {
    'com.android.server.display.DisplayManagerService': ['getDisplayInfoForOverrides([Landroid/view/DisplayEventReceiver$FrameRateOverride;Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;'],
    'com.android.server.display.LogicalDisplay': ['getDisplayInfoLocked()Landroid/view/DisplayInfo;', 'getNonOverrideDisplayInfoLocked(Landroid/view/DisplayInfo;)V', 'setDisplayInfoOverrideFromWindowManagerLocked(Landroid/view/DisplayInfo;)Z'],
    'com.android.server.display.LogicalDisplay$CachedDisplayInfo': ['<init>(ZLandroid/view/DisplayInfo;[Landroid/view/DisplayEventReceiver$FrameRateOverride;)V', 'info()Landroid/view/DisplayInfo;'],
    'com.android.server.display.LogicalDisplay#compute': ['computeCurrentDisplayInfoLocked()Landroid/view/DisplayInfo;'],
    'com.android.server.display.DisplayInfoProxy': ['get()Landroid/view/DisplayInfo;', 'set(Landroid/view/DisplayInfo;)V', 'set(ILandroid/view/DisplayInfo$DisplayInfoChangeSource;)V'],
    'com.android.server.display.DisplayManagerService#overrides': ['applyFrameRateOverride([Landroid/view/DisplayEventReceiver$FrameRateOverride;Landroid/view/DisplayInfo;I)V', 'applyPresentationMaskingOverride(Landroid/view/DisplayInfo;I)V'],
    'ext:com.android.server.wm.OplusZoomWindowManagerService': ['getZoomModeDisplayInfo(Landroid/view/DisplayInfo;II)Landroid/view/DisplayInfo;'],
    'ext:com.android.server.display.LogicalDisplayExt': ['isAlwaysRotateDisplayDeviceEnabled(ZLcom/android/server/display/DisplayDevice;Landroid/view/DisplayInfo;)Z', 'adjustRotatedForMirage(ZILandroid/view/DisplayInfo;)Z'],
    'ext:com.android.server.wm.FlexibleWindowManagerService': ['onDisplayUpdate(Landroid/view/DisplayInfo;)V'],
    'ext:com.android.server.wm.OplusConnectedDisplayManager': ['onDisplayUpdate(Landroid/view/DisplayInfo;)V'],
    'ext:com.android.server.display.OplusMirageDisplayManagerService': ['adjustRotatedForMirage(ZILandroid/view/DisplayInfo;)Z'],
    'ext:com.android.server.display.DisplayManagerServiceExtImpl': ['getBacklightTypeDisplayInfo(Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;', 'getZoomModeDisplayInfo(Landroid/view/DisplayInfo;II)Landroid/view/DisplayInfo;', 'getBenchMarkDisplayInfo(Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;'],
}

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read():
    WORK.mkdir(parents=True, exist_ok=True)
    target = WORK / 'reads.json'
    reads = json.loads(target.read_text()) if target.exists() else {}
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for name, methods in QUERIES.items():
        archive, pin = (EXT, EXT_PIN) if name.startswith('ext:') else (ARCHIVE, PIN)
        class_name = name.removeprefix('ext:').split('#')[0]
        if name == 'ext:com.android.server.display.DisplayManagerServiceExtImpl' and name not in reads and (WORK / 'extensions.json').exists():
            reads[name] = json.loads((WORK / 'extensions.json').read_text())['receipt']
            target.write_text(json.dumps(reads, indent=2) + '\n')
        if name not in reads:
            receipt = reader(archive, pin, class_name=class_name, methods=methods, stream='guest-metrics-producer')
            reads[name] = receipt['receipt']
            target.write_text(json.dumps(reads, indent=2) + '\n')
        receipt = json.loads((ROOT / reads[name]).read_text())
        assert receipt['archiveSha256'] == pin and receipt['query']['exactMethods'] == methods
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        print(name, reads[name], flush=True)

def summarize():
    source = ROOT / 'compat/android/com/appleexploit/oneos/security/authority/PreparedGuestMetricsProducer.java'
    source_pin = '72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7'
    assert digest(source) == source_pin
    reads = json.loads((WORK / 'reads.json').read_text())
    evidence, methods = [], {}
    def collect(key, receipt_path, only=None):
        receipt = json.loads((ROOT / receipt_path).read_text())
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256'] and not receipt['oemCodeExecuted']
        selected = []
        for number, line in enumerate((ROOT / receipt['raw']).read_text().splitlines(), 1):
            row = json.loads(line)
            if row['record'] != 'method' or (only and row['body']['signature'] not in only):
                continue
            body = row['body']
            methods[(key, body['signature'])] = body
            proof, = [proof for proof in receipt['selectedMethodProofs'] if proof['signature'] == body['signature']]
            selected.append({**proof, 'rawMethodLine': number})
        evidence.append({'key': key, 'receipt': receipt_path, 'receiptSha256': digest(ROOT / receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': selected})
    for key, path in reads.items():
        collect(key, path)
    context = ROOT / 'inventory/context-display-contract.json'
    assert digest(context) == '89c6320f961e7cd1cceb0d519ed79c5515c29b2e6f8e2493ad529fb82f505069'
    previous = json.loads(context.read_text())['methodEvidence']
    for key, signatures in [('coloros-services:com.android.server.display.DisplayManagerService$BinderService', ['getDisplayInfo(I)Landroid/view/DisplayInfo;']), ('coloros-services:com.android.server.display.DisplayManagerService#reads', ['getDisplayInfoInternal(II)Landroid/view/DisplayInfo;'])]:
        item, = [item for item in previous if item['key'] == key]
        collect('reuse:' + key, item['receipt'], signatures)
    assertions = []
    def edge(key, signature, pc, suffix):
        instruction, = [instruction for instruction in methods[(key, signature)]['instructions'] if instruction['pc'] == pc]
        assert instruction.get('reference', '').endswith(suffix), (key, signature, pc)
        assertions.append({'selection': key, 'method': signature, 'pc': hex(pc), 'referenceSuffix': suffix})
    getter = 'reuse:coloros-services:com.android.server.display.DisplayManagerService$BinderService'
    signature = 'getDisplayInfo(I)Landroid/view/DisplayInfo;'
    edge(getter, signature, 0, '->getCallingUid()I')
    edge(getter, signature, 4, '->clearCallingIdentity()J')
    edge(getter, signature, 10, '->-$$Nest$mgetDisplayInfoInternal(Lcom/android/server/display/DisplayManagerService;II)Landroid/view/DisplayInfo;')
    edge(getter, signature, 14, '->restoreCallingIdentity(J)V')
    edge(getter, signature, 19, '->restoreCallingIdentity(J)V')
    signature = 'getDisplayInfoForOverrides([Landroid/view/DisplayEventReceiver$FrameRateOverride;Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;'
    edge('com.android.server.display.DisplayManagerService', signature, 0, 'Landroid/view/DisplayInfo;')
    edge('com.android.server.display.DisplayManagerService', signature, 5, '->copyFrom(Landroid/view/DisplayInfo;)V')
    edge('com.android.server.display.DisplayManagerService', signature, 8, '->applyFrameRateOverride([Landroid/view/DisplayEventReceiver$FrameRateOverride;Landroid/view/DisplayInfo;I)V')
    edge('com.android.server.display.DisplayManagerService', signature, 11, '->applyPresentationMaskingOverride(Landroid/view/DisplayInfo;I)V')
    compute = 'computeCurrentDisplayInfoLocked()Landroid/view/DisplayInfo;'
    edge('com.android.server.display.LogicalDisplay#compute', compute, 0, 'Landroid/view/DisplayInfo;')
    edge('com.android.server.display.LogicalDisplay#compute', compute, 0x1d, '-><init>(ZLandroid/view/DisplayInfo;[Landroid/view/DisplayEventReceiver$FrameRateOverride;)V')
    edge('com.android.server.display.LogicalDisplay#compute', compute, 0x20, '->put(ILjava/lang/Object;)V')
    edge('com.android.server.display.DisplayInfoProxy', 'set(ILandroid/view/DisplayInfo$DisplayInfoChangeSource;)V', 5, '->mInfo:Landroid/view/DisplayInfo;')
    edge('ext:com.android.server.wm.OplusZoomWindowManagerService', 'getZoomModeDisplayInfo(Landroid/view/DisplayInfo;II)Landroid/view/DisplayInfo;', 0x2e, '->appWidth:I')
    edge('ext:com.android.server.wm.OplusZoomWindowManagerService', 'getZoomModeDisplayInfo(Landroid/view/DisplayInfo;II)Landroid/view/DisplayInfo;', 0x3a, '->appHeight:I')
    ext = 'ext:com.android.server.display.DisplayManagerServiceExtImpl'
    edge(ext, 'getBenchMarkDisplayInfo(Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;', 0x2f, '->physicalXDpi:F')
    edge(ext, 'getBenchMarkDisplayInfo(Landroid/view/DisplayInfo;I)Landroid/view/DisplayInfo;', 0x37, '->physicalYDpi:F')
    for key, signature in [('ext:com.android.server.wm.OplusConnectedDisplayManager', 'onDisplayUpdate(Landroid/view/DisplayInfo;)V'), ('ext:com.android.server.display.OplusMirageDisplayManagerService', 'adjustRotatedForMirage(ZILandroid/view/DisplayInfo;)Z')]:
        body = methods[(key, signature)]
        assert not any(instruction['opcode'].startswith(('IPUT', 'SPUT')) and 'Landroid/view/DisplayInfo;->' in instruction.get('reference', '') for instruction in body['instructions'])
    result = {'schema': 'guest-metrics-producer/v1', 'status': 'authored prepared RAW extractor; external genuine-owner/runtime admission unassembled', 'productionSource': {'path': source.relative_to(ROOT).as_posix(), 'sha256': source_pin}, 'sourceInputs': {'servicesJar': str(ARCHIVE), 'servicesSha256': PIN, 'oplusServicesJar': str(EXT), 'oplusServicesSha256': EXT_PIN}, 'methodEvidence': evidence, 'assertions': assertions, 'assertionCount': len(assertions), 'newBodyCount': sum(len(item['methods']) for item in evidence if not item['key'].startswith('reuse:')), 'reusedBodyCount': sum(len(item['methods']) for item in evidence if item['key'].startswith('reuse:')), 'approvedApi': {'prepare': 'PreparedGuestMetricsProducer prepare(Object retainedRealDmsBinderService) throws ReflectiveOperationException', 'capture': 'Sample capture(int displayId) throws Throwable', 'sample': ['appWidth():int', 'appHeight():int', 'logicalDensityDpi():int', 'physicalXDpiBits():int', 'physicalYDpiBits():int']}, 'runtimeRules': ['Cache exact getter/return Class/six primitive Field metadata once; source shape is not admission', 'One direct same-thread getter invocation; original native Binder UID/PID capture/check on success/null and after extraction', 'Original invoked Throwable cause rethrown without a postcheck replacing it; genuine null remains absent', 'Exact returned Class/displayId validated before reads and subject checked after reads', 'Only five primitive quantities escape; DPI bits mean Float.floatToRawIntBits of Java Field.getFloat reads, not untouched native/Parcelable representations', 'Sample has five private final int fields and no DisplayInfo/producer/service reference; no new lock/default/sanitizer/cache/lookup/publisher'], 'sourceOwnership': ['CachedDisplayInfo stores an alias, but fresh compute publishes completed DisplayInfo five-scalar values; proxy updates replace/null reference', 'CopyOnWriteSparseArray existing-key put may use setValueAt; do not claim container clone every update', 'DMS getDisplayInfoForOverrides always makes fresh copy; override helpers do not escape it', 'Pinned backlight/zoom/benchmark paths return same private copy; known vendor alias leaves read/copy primitives without retaining DisplayInfo', 'Independent Table source review covers exact five-scalar writers/copy/publication/alias cut; no claim all nested DisplayInfo data immutable/current'], 'independentReview': {'sourcePhase': 'accepted by /root/sol_table_review for exact pinned implementations', 'codePhase': 'source reviewed with no concrete defect; bounded authored fixtures/build pending', 'sourceReviewReport': 'docs/guest-metrics-producer-review.md'}, 'limitations': ['Raw retained receiver/member shapes/Sample are not source/endpoint/subject/currentness/generation/lifetime admission', 'Actual incoming metadata caller preserved only for same-thread direct getter; no arbitrary forwarded credential caller preservation', 'Actual guest framework reflection/hidden API/native Binder operation, source-owner lifetime, current generation and runtime admission remain external', 'RAW guest values are not final Samsung metrics; future consumer must apply actual CompatSandbox configuration/flag transformation, then actual RM config/CompatibilityInfo and boot-helper/callsite admission', 'No endpoint/wire/cache installation or boot retarget implemented; no OEM/Android/JNI/phone execution'], 'toolSha256': digest(__file__)}
    path = ROOT / 'inventory/guest-metrics-producer.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'assertions': len(assertions), 'newBodies': result['newBodyCount'], 'reusedBodies': result['reusedBodyCount'], 'productionSourceSha256': source_pin, 'oemExecuted': False}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.summarize:
        summarize()
