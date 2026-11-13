"""Narrow static continuation of genuine system-Context display acquisition."""
import argparse, hashlib, json, runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
WORK = ROOT / 'out/context-display-contract'
SOURCES = {
    'samsung-framework': (PARENT / 'firmware/samsung/framework.jar', '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'),
    'coloros-framework': (PARENT / 'firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'samsung-services': (PARENT / 'firmware/samsung/runtime-20261104/services.jar', 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'),
    'coloros-services': (PARENT / 'firmware/donor/extracted/system/framework/services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
}
QUERY = [
    ('samsung-framework', 'android.hardware.display.DisplayManagerGlobal', ['getDisplayInfoInternal(I)Landroid/view/DisplayInfo;', 'registerCallbackIfNeeded()V', 'updateCallbackIfNeededLocked()V']),
    ('samsung-framework', 'android.hardware.display.DisplayManagerGlobal$1', ['recompute(Ljava/lang/Integer;)Landroid/view/DisplayInfo;']),
    ('samsung-framework', 'android.hardware.display.DisplayManagerGlobal#mask', ['calculateEventsMaskLocked()J']),
    ('samsung-framework', 'com.samsung.android.core.CompatSandbox', ['applyDisplaySandboxingIfNeeded(Landroid/view/DisplayInfo;)V']),
    ('samsung-framework', 'android.hardware.display.IDisplayManager$Stub$Proxy', ['getDisplayInfo(I)Landroid/view/DisplayInfo;', 'registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V']),
    ('coloros-framework', 'android.hardware.display.IDisplayManager$Stub$Proxy', ['getDisplayInfo(I)Landroid/view/DisplayInfo;', 'registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V']),
    ('samsung-framework', 'android.view.DisplayInfo', ['readFromParcel(Landroid/os/Parcel;)V', 'writeToParcel(Landroid/os/Parcel;I)V']),
    ('coloros-framework', 'android.view.DisplayInfo', ['readFromParcel(Landroid/os/Parcel;)V', 'writeToParcel(Landroid/os/Parcel;I)V']),
    ('samsung-services', 'com.android.server.display.DisplayManagerService$BinderService', ['getDisplayInfo(I)Landroid/view/DisplayInfo;', 'registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V']),
    ('coloros-services', 'com.android.server.display.DisplayManagerService$BinderService', ['getDisplayInfo(I)Landroid/view/DisplayInfo;', 'registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V']),
    ('samsung-services', 'com.android.server.display.LogicalDisplay', ['updateLocked(Lcom/android/server/display/DisplayDeviceRepository;)V']),
    ('samsung-framework', 'android.hardware.display.DisplayManagerGlobal$DisplayManagerCallback', ['<init>(Landroid/hardware/display/DisplayManagerGlobal;)V', 'onDisplayEvent(II)V', 'onDisplaySnapshot([I[I)V']),
    ('samsung-framework', 'android.hardware.display.IDisplayManagerCallback$Stub$Proxy', ['onDisplayEvent(II)V', 'onDisplaySnapshot([I[I)V', 'onTopologyChanged(Landroid/hardware/display/DisplayTopology;)V']),
    ('coloros-framework', 'android.hardware.display.IDisplayManagerCallback$Stub$Proxy', ['onDisplayEvent(II)V', 'onDisplaySnapshot([I[I)V', 'onTopologyChanged(Landroid/hardware/display/DisplayTopology;)V']),
    ('samsung-services', 'com.android.server.wm.WindowManagerService$LocalService', ['getAppSensorAxisRemapRequired(I)I']),
    ('samsung-services', 'com.android.server.display.LogicalDisplayMapper', ['createNewLogicalDisplayLocked(Lcom/android/server/display/DisplayDevice;I)Lcom/android/server/display/LogicalDisplay;']),
    ('samsung-services', 'com.android.server.wm.MultiTaskingAppCompatController', ['getAppSensorAxisRemapRequired(Ljava/lang/String;)I']),
    ('samsung-services', 'com.android.server.display.DisplayManagerService$$ExternalSyntheticLambda34', ['accept(Ljava/lang/Object;)V']),
    ('samsung-services', 'com.android.server.display.DisplayManagerService#reads', ['getDisplayInfoInternal(II)Landroid/view/DisplayInfo;', '-$$Nest$mregisterCallbackInternal(IIJLandroid/hardware/display/IDisplayManagerCallback;Lcom/android/server/display/DisplayManagerService;)V']),
    ('coloros-services', 'com.android.server.display.DisplayManagerService#reads', ['getDisplayInfoInternal(II)Landroid/view/DisplayInfo;', 'registerCallbackInternal(Landroid/hardware/display/IDisplayManagerCallback;IIJ)V']),
    ('samsung-framework', 'android.hardware.display.DisplayManagerGlobal#events', ['handleDisplayEvents(IIZ)V', 'handleDisplaySnapshot([I[I)V']),
    ('coloros-framework', 'android.hardware.display.DisplayManagerGlobal#events', ['handleDisplayEvents(IIZ)V', 'handleDisplaySnapshot([I[I)V']),
    ('samsung-framework', 'android.view.DisplayInfo#metrics', ['getAppMetrics(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;)V', 'getMetricsWithSize(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;II)V']),
    ('samsung-framework', 'android.app.PropertyInvalidatedCache', ['query(Ljava/lang/Object;)Ljava/lang/Object;']),
    ('samsung-framework', 'android.hardware.display.IDisplayManagerCallback$Stub', ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
    ('coloros-framework', 'android.hardware.display.IDisplayManagerCallback$Stub', ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
    ('samsung-framework', 'android.app.PropertyInvalidatedCache#nonce', ['getCurrentNonce()J']),
    ('samsung-framework', 'android.app.PropertyInvalidatedCache$NonceHandler', ['getNonce()J']),
    ('samsung-framework', 'android.app.PropertyInvalidatedCache#handler', ['getNonceHandler(Landroid/app/PropertyInvalidatedCache$Args;)Landroid/app/PropertyInvalidatedCache$NonceHandler;', 'getNonceHandler(Landroid/app/PropertyInvalidatedCache$CacheKey;)Landroid/app/PropertyInvalidatedCache$NonceHandler;']),
    ('samsung-framework', 'android.os.RemoteException', ['rethrowFromSystemServer()Ljava/lang/RuntimeException;']),
]

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read():
    WORK.mkdir(parents=True, exist_ok=True)
    target = WORK / 'reads.json'
    reads = json.loads(target.read_text()) if target.exists() else {}
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for side, name, methods in QUERY:
        key = side + ':' + name
        if key not in reads:
            archive, pin = SOURCES[side]
            receipt = reader(archive, pin, class_name=name.split('#')[0], methods=methods, stream='context-display-contract')
            reads[key] = receipt['receipt']
            target.write_text(json.dumps(reads, indent=2) + '\n')
        receipt = json.loads((ROOT / reads[key]).read_text())
        assert receipt['archiveSha256'] == SOURCES[side][1]
        assert receipt['query']['exactMethods'] == methods
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        print(key, reads[key], flush=True)

def summarize():
    reads = json.loads((WORK / 'reads.json').read_text())
    evidence = []
    methods = {}
    def collect(key, receipt_path, only=None):
        receipt = json.loads((ROOT / receipt_path).read_text())
        assert digest(ROOT / receipt['raw']) == receipt['rawSha256']
        assert not receipt['oemCodeExecuted'] and receipt['readerExitCode'] == 0
        selected = []
        for line_number, line in enumerate((ROOT / receipt['raw']).read_text().splitlines(), 1):
            row = json.loads(line)
            if row['record'] != 'method' or (only and row['body']['signature'] not in only):
                continue
            body = row['body']
            methods[(key, body['signature'])] = body
            proof, = [proof for proof in receipt['selectedMethodProofs'] if proof['signature'] == body['signature']]
            selected.append({**proof, 'rawMethodLine': line_number})
        evidence.append({'key': key, 'receipt': receipt_path, 'receiptSha256': digest(ROOT / receipt_path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': selected})
    for key, path in reads.items():
        collect(key, path)
    old = ROOT / 'inventory/authority-bootstrap-runtime.json'
    assert digest(old) == 'b527fa96edc027866559e6fe8a54abaf15176af3767486c5d4e246b047f3fccc'
    previous = json.loads(old.read_text())['methodEvidence']
    wanted = {'android.app.ContextImpl#inner': ['createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;'], 'android.app.ResourcesManager#display': ['getDisplayMetrics()Landroid/util/DisplayMetrics;', 'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;'], 'android.hardware.display.DisplayManagerGlobal': ['<init>(Landroid/hardware/display/IDisplayManager;)V', 'getDisplayInfo(I)Landroid/view/DisplayInfo;']}
    for key, signatures in wanted.items():
        item, = [item for item in previous if item['key'] == key]
        collect('reuse:' + key, item['receipt'], signatures)
    proof = ROOT / 'inventory/authority-display-bootstrap.json'
    assert digest(proof) == '8856956d7460c39537672f2773061243793d629729aa68f2aedfd250e5a3bba7'
    previous = json.loads(proof.read_text())['methodEvidence']
    for side in ['samsung', 'coloros']:
        key = side + '-framework:android.hardware.display.IDisplayManager$Stub'
        item, = [item for item in previous if item['key'] == key]
        collect('reuse:' + key, item['receipt'], ['onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'])
    assertions = []
    def edge(key, signature, pc, suffix):
        instruction, = [instruction for instruction in methods[(key, signature)]['instructions'] if instruction['pc'] == pc]
        assert instruction.get('reference', '').endswith(suffix), (key, signature, pc)
        assertions.append({'selection': key, 'method': signature, 'pc': hex(pc), 'referenceSuffix': suffix})
    base = 'samsung-framework:android.hardware.display.DisplayManagerGlobal'
    edge(base, 'getDisplayInfoInternal(I)Landroid/view/DisplayInfo;', 0xd, '->query(Ljava/lang/Object;)Ljava/lang/Object;')
    edge(base, 'getDisplayInfoInternal(I)Landroid/view/DisplayInfo;', 0x35, '->getDisplayInfo(I)Landroid/view/DisplayInfo;')
    edge(base, 'getDisplayInfoInternal(I)Landroid/view/DisplayInfo;', 0x42, '->applyDisplaySandboxingIfNeeded(Landroid/view/DisplayInfo;)V')
    edge(base, 'getDisplayInfoInternal(I)Landroid/view/DisplayInfo;', 0x45, '->registerCallbackIfNeeded()V')
    edge(base, 'registerCallbackIfNeeded()V', 0xa, '->mCallback:Landroid/hardware/display/DisplayManagerGlobal$DisplayManagerCallback;')
    edge(base, 'updateCallbackIfNeededLocked()V', 0x5b, '->registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V')
    edge(base, 'updateCallbackIfNeededLocked()V', 0x5e, '->mRegisteredInternalEventFlag:J')
    edge('samsung-framework:android.hardware.display.DisplayManagerGlobal$1', 'recompute(Ljava/lang/Integer;)Landroid/view/DisplayInfo;', 0xa, '->getDisplayInfo(I)Landroid/view/DisplayInfo;')
    edge('reuse:android.app.ContextImpl#inner', 'createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;', 0x26, '->getDisplayMetrics()Landroid/util/DisplayMetrics;')
    edge('reuse:android.app.ContextImpl#inner', 'createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;', 0x2a, '->updateConfiguration(Landroid/content/res/Configuration;Landroid/util/DisplayMetrics;)V')
    edge('reuse:android.app.ResourcesManager#display', 'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;', 0xb, '->getDisplayInfo(I)Landroid/view/DisplayInfo;')
    edge('reuse:android.app.ResourcesManager#display', 'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;', 0x29, '->getAppMetrics(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;)V')
    edge('samsung-services:com.android.server.display.DisplayManagerService$BinderService', 'getDisplayInfo(I)Landroid/view/DisplayInfo;', 0x1c, '->getAppSensorAxisRemapRequired(I)I')
    edge('samsung-services:com.android.server.display.LogicalDisplay', 'updateLocked(Lcom/android/server/display/DisplayDeviceRepository;)V', 0xb3, '->refreshRateMode:I')
    edge('samsung-services:com.android.server.wm.MultiTaskingAppCompatController', 'getAppSensorAxisRemapRequired(Ljava/lang/String;)I', 5, '->get(Ljava/lang/Object;)Ljava/lang/Object;')
    edge('samsung-services:com.android.server.display.DisplayManagerService$$ExternalSyntheticLambda34', 'accept(Ljava/lang/Object;)V', 0x58, '->mRefreshRateMode:I')
    schema = {}
    for side in ['samsung', 'coloros']:
        key = side + '-framework:android.view.DisplayInfo'
        fields = []
        read_fields = []
        writes = []
        for instruction in methods[(key, 'writeToParcel(Landroid/os/Parcel;I)V')]['instructions']:
            reference = instruction.get('reference', '')
            if instruction['opcode'].startswith('IGET') and reference.startswith('Landroid/view/DisplayInfo;') and reference not in fields:
                fields.append(reference)
            if instruction['opcode'].startswith('INVOKE'):
                writes.append({'pc': hex(instruction['pc']), 'method': reference})
        for instruction in methods[(key, 'readFromParcel(Landroid/os/Parcel;)V')]['instructions']:
            reference = instruction.get('reference', '')
            if instruction['opcode'].startswith('IPUT') and reference.startswith('Landroid/view/DisplayInfo;'):
                read_fields.append(reference)
        assert fields == read_fields
        schema[side] = {'orderedFields': fields, 'fieldCount': len(fields), 'writerCalls': writes, 'topLevelReadWriteFieldOrderEqual': True}
    source_set, guest_set = set(schema['samsung']['orderedFields']), set(schema['coloros']['orderedFields'])
    assert len(source_set) == 59 and len(guest_set) == 58 and len(source_set & guest_set) == 57
    assert source_set - guest_set == {'Landroid/view/DisplayInfo;->refreshRateMode:I', 'Landroid/view/DisplayInfo;->appSensorAxisRemapRequired:I'}
    assert guest_set - source_set == {'Landroid/view/DisplayInfo;->backlightType:I'}
    schemas = {'getDisplayInfo(I)Landroid/view/DisplayInfo;': ([7, 1], 0x16, 0x18), 'registerCallbackWithEventMask(Landroid/hardware/display/IDisplayManagerCallback;J)V': ([11, 5], 0x19, None)}
    wire = {}
    for signature, (numbers, literal_pc, _) in schemas.items():
        wire[signature] = {}
        for side, number in zip(['samsung', 'coloros'], numbers):
            key = side + '-framework:android.hardware.display.IDisplayManager$Stub$Proxy'
            instructions = {instruction['pc']: instruction for instruction in methods[(key, signature)]['instructions']}
            assert instructions[literal_pc]['literal'] == number
            transaction = next(instruction for instruction in instructions.values() if '->transact(' in instruction.get('reference', ''))
            flags_register = transaction['registers'][-1]
            constants = {instruction['registers'][0]: instruction['literal'] for instruction in instructions.values() if instruction['pc'] < transaction['pc'] and 'literal' in instruction}
            assert constants[flags_register] == 0
            key = 'reuse:' + side + '-framework:android.hardware.display.IDisplayManager$Stub'
            body = methods[(key, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')]
            by_pc = {instruction['pc']: instruction for instruction in body['instructions']}
            switch = next(instruction for instruction in body['instructions'] if instruction['opcode'] == 'PACKED_SWITCH')
            payload = by_pc[switch['targetPc']]
            item, = [item for item in payload['switchElements'] if item['key'] == number]
            case_pc = switch['pc'] + item['offsetFromReferringSwitchPc']
            calls = [instruction for instruction in body['instructions'] if case_pc <= instruction['pc'] < case_pc + 32 and instruction['opcode'].startswith('INVOKE')]
            assert any(instruction.get('reference', '').endswith('->' + signature) for instruction in calls)
            wire[signature][side] = {'transaction': number, 'flags': 0, 'stubCasePc': hex(case_pc)}
    callback_wire = {}
    for side in ['samsung', 'coloros']:
        key = side + '-framework:android.hardware.display.IDisplayManagerCallback$Stub$Proxy'
        callback_wire[side] = {}
        for signature, number in [('onDisplayEvent(II)V', 1), ('onTopologyChanged(Landroid/hardware/display/DisplayTopology;)V', 2), ('onDisplaySnapshot([I[I)V', 3)]:
            instructions = methods[(key, signature)]['instructions']
            transaction = next(instruction for instruction in instructions if '->transact(' in instruction.get('reference', ''))
            values = {instruction['registers'][0]: instruction['literal'] for instruction in instructions if instruction['pc'] < transaction['pc'] and 'literal' in instruction}
            regs = transaction['registers']
            assert values[regs[1]] == number and values[regs[3]] == 0 and values[regs[4]] == 1
            stub_key = side + '-framework:android.hardware.display.IDisplayManagerCallback$Stub'
            body = methods[(stub_key, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')]
            by_pc = {instruction['pc']: instruction for instruction in body['instructions']}
            switch = next(instruction for instruction in body['instructions'] if instruction['opcode'] == 'PACKED_SWITCH')
            payload = by_pc[switch['targetPc']]
            element, = [element for element in payload['switchElements'] if element['key'] == number]
            case_pc = switch['pc'] + element['offsetFromReferringSwitchPc']
            calls = [instruction for instruction in body['instructions'] if case_pc <= instruction['pc'] < case_pc + 32 and instruction['opcode'].startswith('INVOKE')]
            assert any(instruction.get('reference', '').endswith('->' + signature) for instruction in calls)
            callback_wire[side][signature] = {'transaction': number, 'flags': 1, 'replyNull': True, 'stubCasePc': hex(case_pc), 'writerCalls': [instruction['reference'] for instruction in instructions if instruction['opcode'].startswith('INVOKE') and '->write' in instruction.get('reference', '')]}
    metric_fields = set()
    for signature in ['getAppMetrics(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;)V', 'getMetricsWithSize(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;II)V']:
        for instruction in methods[('samsung-framework:android.view.DisplayInfo#metrics', signature)]['instructions']:
            if instruction['opcode'].startswith('IGET') and instruction.get('reference', '').startswith('Landroid/view/DisplayInfo;'):
                metric_fields.add(instruction['reference'])
    assert metric_fields == {'Landroid/view/DisplayInfo;->appWidth:I', 'Landroid/view/DisplayInfo;->appHeight:I', 'Landroid/view/DisplayInfo;->logicalDensityDpi:I', 'Landroid/view/DisplayInfo;->physicalXDpi:F', 'Landroid/view/DisplayInfo;->physicalYDpi:F'}
    result = {'schema': 'context-display-contract/v1', 'status': 'full DisplayInfo conversion blocked; narrower genuine metrics projection proposed for investigation only', 'methodEvidence': evidence, 'assertions': assertions, 'assertionCount': len(assertions), 'newBodyCount': sum(len(item['methods']) for item in evidence if not item['key'].startswith('reuse:')), 'reusedBodyCount': sum(len(item['methods']) for item in evidence if item['key'].startswith('reuse:')), 'displayWire': wire, 'callbackWire': callback_wire, 'displayInfoSchema': schema, 'sourceOnlyFields': sorted(source_set - guest_set), 'guestOnlyFields': sorted(guest_set - source_set), 'freshManager': {'registeredMask': 0, 'implicitFlags': False, 'nativeCallbacks': False, 'displayAndTopologyListenersEmpty': True, 'computedMask': 0, 'remoteRegistration': 'skipped if this exact fresh state is retained; no runtime state claimed'}, 'metricsProjection': {'sourceFields': sorted(metric_fields), 'sourceCallsite': 'ContextImpl.createSystemContextInner@0x26 -> ResourcesManager.getDisplayMetrics()', 'hypotheticalStaticTarget': 'DisplayMetrics snapshotForSystemContext(ResourcesManager exactOriginalOwner)', 'requires': ['One coherent raw five-field snapshot from genuine current guest DisplayInfo with display/user/authority-generation provenance, no pre-scaled guest metrics', 'Exact original Configuration/appBounds/fontScale and CompatibilityInfo semantics applied once', 'Actual authenticated producer or complete source-profile parser, real lifetime/error/cache/retirement admission', 'Original DEX/runtime/loader admission and inverse-verifiable single-call retarget, not implemented'], 'avoids': ['Fabricating a full Samsung DisplayInfo or guessing Samsung-only policy fields', 'Changing public/global display or claiming two-read component closes Context'], 'implemented': False}, 'unresolved': ['Full nested DisplayInfo Parcelable classes and DisplayTopology payload equivalence not certified; top-level complete field order is not full parcel compatibility', 'Genuine Samsung refresh-rate policy and sensor-axis override owners remain absent from full-info conversion', 'NonceHandler actual native/shared-memory/system-property invalidation owner/generation and source-to-guest coherency remain unproved', 'Callback registration can link death/store PID/UID state/send snapshot before return; applied-state barrier/removal/drain remains unassembled', 'All source claims are captured original profiles, not installed guest/runtime acceptance'], 'oemExecuted': False, 'phoneUsed': False, 'runtimeRetargetAuthored': False, 'frozenInputs': {'inventory/authority-bootstrap-runtime.json': digest(old), 'inventory/authority-display-bootstrap.json': digest(proof)}, 'toolSha256': digest(__file__)}
    target = ROOT / 'inventory/context-display-contract.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'assertions': len(assertions), 'newBodies': result['newBodyCount'], 'reusedBodies': result['reusedBodyCount'], 'sourceFields': 59, 'guestFields': 58, 'metricsFields': 5, 'runtimeRetargetAuthored': False}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.summarize:
        summarize()
