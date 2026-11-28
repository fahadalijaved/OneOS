"""Static proof for a proposed private metrics transaction on original DMS."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/guest-metrics-parent-transport'
TX = 0x00FE0001
SIGNATURE = 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z'
SOURCES = {
    'services': ('services.jar', '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'),
    'framework': ('framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
    'oplus': ('oplus-services.jar', 'cd2be8190990242cfcf01327ff4482404dbc308093fa3871a749f053f3849a39'),
}
QUERIES = {
    'DisplayManagerService$BinderService': ('services', 'com.android.server.display.DisplayManagerService$BinderService', [SIGNATURE]),
    'Binder': ('framework', 'android.os.Binder', ['transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z']),
    'IDisplayManager$Stub': ('framework', 'android.hardware.display.IDisplayManager$Stub', [SIGNATURE]),
    'DisplayManagerServiceExtImpl': ('oplus', 'com.android.server.display.DisplayManagerServiceExtImpl', [SIGNATURE]),
    'Binder-default': ('framework', 'android.os.Binder', [SIGNATURE]),
}
PINS = {
    'inventory/guest-metrics-endpoint.json': '847affee9f18fa16b09c5d064b4bf247c7f70ae76dc797f54048b0e2d766c015',
    'inventory/guest-metrics-endpoint-implementation.json': '1b1ee77106f95b0d0eba0caeb391efd9b034c407c9f33119a4e513b9348de85b',
    'inventory/guest-metrics-lifecycle.json': '1250a1f263edf47dd8a9a446e0c026297940dba1a7cba6a80084304ff1f74cb6',
    'compat/android/com/appleexploit/oneos/security/boot/PreparedGuestMetricsClient.java': 'afd99ebe98a09b209bb7f6a42d23c9d88313597f5d6760105def73213ea625d1',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read():
    WORK.mkdir(parents=True, exist_ok=True)
    reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
    for key, (source, name, methods) in QUERIES.items():
        target = WORK / (key + '.json')
        if not target.exists():
            filename, pin = SOURCES[source]
            receipt = reader(ROOT.parent / 'firmware/donor/extracted/system/framework' / filename, pin,
                             class_name=name, methods=methods, stream='guest-metrics-parent-transport')
            target.write_text(json.dumps(receipt, indent=2) + '\n')
        receipt = json.loads(target.read_text())
        if receipt['archiveSha256'] != SOURCES[source][1] or receipt['query']['exactMethods'] != methods:
            raise ValueError('Source/query changed: ' + key)
        if digest(ROOT / receipt['raw']) != receipt['rawSha256']:
            raise ValueError('Raw changed: ' + key)
        print(key, receipt['receipt'])


def report():
    for path, pin in PINS.items():
        if digest(ROOT / path) != pin:
            raise ValueError('Frozen input changed: ' + path)
    endpoint = json.loads((ROOT / 'inventory/guest-metrics-endpoint.json').read_text())
    dms_declaration = None
    for item in endpoint['methodEvidence']:
        if digest(ROOT / item['receipt']) != item['receiptSha256'] or digest(ROOT / item['raw']) != item['rawSha256']:
            raise ValueError('Original capture/phase/loader proof changed')
        if item['key'] == 'com.android.server.display.DisplayManagerService':
            for line in (ROOT / item['raw']).read_text().splitlines():
                row = json.loads(line)
                if row.get('record') == 'class' and row['descriptor'] == 'Lcom/android/server/display/DisplayManagerService;':
                    dms_declaration = row
    proposed_dispatch = 'dispatchOneOsGuestMetricsFromParent(Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z'
    if dms_declaration is None or any(m['signature'] == proposed_dispatch for m in dms_declaration['methods']) or any(f['name'] == 'mOneOsGuestMetricsLifecycle' for f in dms_declaration['fields']):
        raise ValueError('Proposed new source member collides')
    for item in endpoint['oneos']['files']:
        if digest(ROOT / item['path']) != item['sha256']:
            raise ValueError('Pinned OneOS source changed')
    bodies, evidence = {}, []
    for key, (source, name, methods) in QUERIES.items():
        receipt = json.loads((WORK / (key + '.json')).read_text())
        if receipt['archiveSha256'] != SOURCES[source][1] or receipt['query']['exactMethods'] != methods:
            raise ValueError('Selected source/query mismatch')
        if digest(ROOT / receipt['raw']) != receipt['rawSha256'] or receipt['oemCodeExecuted']:
            raise ValueError('Raw mismatch/invalid execution claim')
        for line in (ROOT / receipt['raw']).read_text().splitlines():
            row = json.loads(line)
            if row.get('record') == 'method':
                bodies[key] = row['body']
        evidence.append({'key': key, 'receipt': receipt['receipt'], 'receiptSha256': digest(ROOT / receipt['receipt']),
                         'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'],
                         'methods': receipt['selectedMethodProofs']})
    assertions = []

    def instruction(key, pc):
        value, = [item for item in bodies[key]['instructions'] if item['pc'] == pc]
        return value

    def edge(key, pc, suffix):
        if not instruction(key, pc).get('reference', '').endswith(suffix):
            raise ValueError((key, pc, suffix))
        assertions.append({'selection': key, 'pcHex': hex(pc), 'referenceSuffix': suffix})

    edge('DisplayManagerService$BinderService', 0, 'Landroid/hardware/display/IDisplayManager$Stub;->' + SIGNATURE)
    edge('DisplayManagerService$BinderService', 0x12, 'Lcom/android/server/display/IDisplayManagerServiceExt;->' + SIGNATURE)
    if bodies['DisplayManagerService$BinderService']['registerCount'] != 7:
        raise ValueError('Original parent register budget changed')
    edge('IDisplayManager$Stub', 0xa, '->enforceInterface(Ljava/lang/String;)V')
    if instruction('IDisplayManager$Stub', 3)['literal'] != 0x00ffffff or not 1 <= TX <= 0x00ffffff:
        raise ValueError('Private transaction range changed')
    original_keys = [e['key'] for i in bodies['IDisplayManager$Stub']['instructions'] for e in i.get('switchElements', [])]
    extension_keys = [e['key'] for i in bodies['DisplayManagerServiceExtImpl']['instructions'] for e in i.get('switchElements', [])]
    if original_keys != list(range(1, 73)) or extension_keys != [10111] or TX in original_keys + extension_keys:
        raise ValueError('Private transaction collision/dispatch changed')
    for pc, literal in [(6, 1598968902), (0x14, 1598311760), (0x3d, 1598246212)]:
        if instruction('Binder-default', pc)['literal'] != literal or literal == TX:
            raise ValueError('Binder default control-code collision')
    if instruction('Binder-default', 0xad)['literal'] != 0 or instruction('Binder-default', 0xae)['opcode'] != 'RETURN':
        raise ValueError('Binder fallback changed')
    edge('Binder', 3, '->setDataPosition(I)V')
    edge('Binder', 6, 'Landroid/os/Binder;->' + SIGNATURE)
    edge('Binder', 0xc, '->setDataPosition(I)V')
    local = bodies['Binder']
    if local['accessFlags'] != 0x11 or len(local['instructions']) != 8 or local['catches']:
        raise ValueError('Local Binder.transact shape changed')
    calls = [i['reference'] for i in local['instructions'] if i['opcode'].startswith('INVOKE')]
    if calls != ['Landroid/os/Parcel;->setDataPosition(I)V', 'Landroid/os/Binder;->' + SIGNATURE, 'Landroid/os/Parcel;->setDataPosition(I)V']:
        raise ValueError('Local Binder.transact is no longer direct/no-clear path')
    implementation = json.loads((ROOT / 'inventory/guest-metrics-endpoint-implementation.json').read_text())
    for item in implementation['productionSources']:
        if digest(ROOT / item['path']) != item['sha256']:
            raise ValueError('Frozen component source changed')
    result = {'schema': 'guest-metrics-parent-transport/v1', 'status': 'SOURCE_PROPOSAL_EXISTING_PARENT_NO_NEW_ALIAS',
              'frozenInputs': [{'path': p, 'sha256': h} for p, h in PINS.items()], 'methodEvidence': evidence,
              'newBodies': len(bodies), 'assertions': assertions, 'assertionCount': len(assertions),
              'collisionProof': {'privateCodeHex': hex(TX), 'privateCodeDecimal': TX, 'originalStubCodes': original_keys,
                                 'originalExtensionCodes': extension_keys, 'originalBinderControlCodes': [1598968902, 1598311760, 1598246212],
                                 'scope': 'Exact captured Java dispatch chain only; actual selected OneOS-patched bytes/profile and Android native dispatch remain unverified'},
              'proposedSourceFootprint': ['Prefix existing BinderService.onTransact with exact private-code branch BEFORE original Stub token check; all other codes enter identical original body', 'Add package-private actual DMS dispatch method reading its private lifecycle field; pass actual outer DMS and born Binder identity to owned cell', 'Use exact onStart capture and normal successful phase100 activation of same Endpoint; no alias/candidate/finishPublication path', 'Direct local owned Endpoint Binder.transact(1,borrowedData,borrowedReply,unchangedFlags); no arbitrary target supplied'],
              'parcelAndCaller': ['Actual final Binder.transact performs direct Java onTransact on same thread, no explicit identity clear/JNI IPC/hop', 'Canonical local transact resets borrowed data position0 BEFORE endpoint; resets borrowed reply position0 ONLY on normal return; exceptional position left as reached', 'Frozen endpoint itself still never recycles/resets borrowed Parcels; transport must not claim end-to-end position immutability', 'Same native-thread caller frame is source-supported, not a live Android/native caller acceptance test'],
              'retirement': ['Cell must refuse parent admission until exact captured phase100 ACTIVE; no fake ABSENT/default/readiness', 'Forward flags unchanged so existing Endpoint rejects nonzero flags; size512 before unique token parsing remains enforced there', 'Terminal retirement closes parent admission then applies Endpoint.retire; cutoff guaranteed after actual Endpoint retirement, not cell Boolean alone', 'Reply-admitted-before-retire results may arrive later; parent/endpoint Java frame counts do not prove native/global drain'],
              'clientBinding': {'currentFrozenClientCode': 1, 'parentCode': TX, 'currentClientDirectParentBindingValid': False, 'proposedApi': 'future source-approved PreparedGuestMetricsClient.prepareParent(IBinder retainedRealDms)', 'rules': ['Internally fixed parent code, never caller-supplied arbitrary transaction code', 'Retain and Parcel.obtain for the actual same parent Binder, no extra local wrapper or ambiguous markForBinder target', 'Preserve v1 token/request/reply/error/cleanup/absent semantics and plain-header profile limits', 'No current client edit or new client artifact emitted']},
              'limits': ['Global display is original DMS publication only; no wrapper replacement, alias write, descriptor change or new publication acknowledgement', 'Original parent acquisition/code/profile/loader/current generation/lifetime remains external; private token/high code is not source or authority attestation', 'One per selected defining-loader cell and actual DMS/born identity, no fresh service creation or inherited native policy defaults', 'Source edits/inverse preservation, config producer, actual Android reflection/caller/Parcel/native behavior and Samsung consumer remain unimplemented'],
              'runtimeCodeEmitted': False, 'sourceRetargetEmitted': False, 'endpointPublished': False, 'oemCodeExecuted': False,
              'failedHistoricalQuery': {'path': 'out/tooling/20261105T232402644768Z-6ddf59d59c7e4196a5ba675605785e4e/stderr.txt', 'reason': 'getMaxTransactionId()I absent in optimized Stub; exact onTransact dispatch/body supplies collision evidence instead'},
              'toolSha256': digest(__file__)}
    (ROOT / 'inventory/guest-metrics-parent-transport.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'newBodies': len(bodies), 'referenceAssertions': len(assertions), 'privateCodeHex': hex(TX), 'originalStubCodes': len(original_keys), 'extensionCodes': extension_keys, 'runtimeCodeEmitted': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.report:
        report()
