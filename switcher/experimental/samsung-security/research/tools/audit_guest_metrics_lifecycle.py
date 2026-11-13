"""Static lifecycle proposal and exact publication-wrapper failure boundary."""
import argparse
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/guest-metrics-lifecycle'
PINS = {
    'inventory/guest-metrics-endpoint.json': '847affee9f18fa16b09c5d064b4bf247c7f70ae76dc797f54048b0e2d766c015',
    'inventory/guest-metrics-endpoint-implementation.json': '1b1ee77106f95b0d0eba0caeb391efd9b034c407c9f33119a4e513b9348de85b',
    'inventory/guest-metrics-producer.json': '0995fcd8238ca88e674cc7e6ef8d54e0e3b2433c0d84d864e0c795822d4161f9',
}
QUERIES = ['addService(Ljava/lang/String;Landroid/os/IBinder;ZI)V',
           'checkService(Ljava/lang/String;)Landroid/os/IBinder;']
BODY_PINS = {
    QUERIES[0]: '8abcbd31b034c056c61e7e56f4a338967b9bd52eb4e2495ac78baf7f2a3c9612',
    QUERIES[1]: '6fbf26b9d7b07480d90d19bbee8adf7b676700066e5a218800517c6647e38e3e',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read():
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / 'publication-readback.json'
    if not path.exists():
        reader = runpy.run_path(str(ROOT / 'tools/static_security_reader.py'))['read_archive']
        receipt = reader(ROOT.parent / 'firmware/donor/extracted/system/framework/framework.jar',
                         'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2',
                         class_name='android.os.ServiceManager', methods=QUERIES,
                         stream='guest-metrics-lifecycle')
        path.write_text(json.dumps(receipt, indent=2) + '\n')
    receipt = json.loads(path.read_text())
    if receipt['archiveSha256'] != 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2' or receipt['query']['exactMethods'] != QUERIES:
        raise ValueError('Selected framework/query changed')
    if {p['signature']: p['normalizedBodySha256'] for p in receipt['selectedMethodProofs']} != BODY_PINS:
        raise ValueError('Publication method identities changed')
    if receipt['query']['exactMethods'] != QUERIES or digest(ROOT / receipt['raw']) != receipt['rawSha256']:
        raise ValueError('Publication receipt drift')
    print(receipt['receipt'])


def report():
    inherited = {}
    for path, pin in PINS.items():
        if digest(ROOT / path) != pin:
            raise ValueError('Frozen input drift: ' + path)
        inherited[path] = json.loads((ROOT / path).read_text())
    endpoint = inherited['inventory/guest-metrics-endpoint.json']
    for evidence in endpoint['methodEvidence']:
        if digest(ROOT / evidence['receipt']) != evidence['receiptSha256'] or digest(ROOT / evidence['raw']) != evidence['rawSha256']:
            raise ValueError('Source factory/lifecycle evidence drift')
    for item in endpoint['oneos']['files']:
        if digest(ROOT / item['path']) != item['sha256']:
            raise ValueError('Immutable OneOS source drift')
    for item in inherited['inventory/guest-metrics-endpoint-implementation.json']['productionSources']:
        if digest(ROOT / item['path']) != item['sha256']:
            raise ValueError('Prepared component source drift')
    selected = json.loads((WORK / 'publication-readback.json').read_text())
    path = ROOT / selected['receipt']
    receipt = json.loads(path.read_text())
    if receipt['archiveSha256'] != 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2' or receipt['query']['exactMethods'] != QUERIES:
        raise ValueError('Selected framework/query changed')
    if {p['signature']: p['normalizedBodySha256'] for p in receipt['selectedMethodProofs']} != BODY_PINS:
        raise ValueError('Publication method identities changed')
    if receipt['rawSha256'] != selected['rawSha256'] or digest(ROOT / receipt['raw']) != receipt['rawSha256'] or receipt['oemCodeExecuted']:
        raise ValueError('Publication raw evidence changed')
    bodies = {}
    for line in (ROOT / receipt['raw']).read_text().splitlines():
        row = json.loads(line)
        if row.get('record') == 'method':
            bodies[row['body']['signature']] = row['body']
    assertions = []

    def edge(signature, pc, suffix):
        ins, = [ins for ins in bodies[signature]['instructions'] if ins['pc'] == pc]
        if not ins.get('reference', '').endswith(suffix):
            raise ValueError((signature, pc, suffix))
        assertions.append({'method': signature, 'pcHex': hex(pc), 'referenceSuffix': suffix})

    edge(QUERIES[0], 4, '->addService(Ljava/lang/String;Landroid/os/IBinder;ZI)V')
    edge(QUERIES[0], 0xd, '->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I')
    if bodies[QUERIES[0]]['catches'] != [{'startPc': 0, 'codeUnits': 7, 'exceptionType': 'Landroid/os/RemoteException;', 'handlerPc': 8}]:
        raise ValueError('addService suppression changed')
    edge(QUERIES[1], 0, '->sCache:Ljava/util/Map;')
    edge(QUERIES[1], 0xf, '->checkService2(Ljava/lang/String;)Landroid/os/Service;')
    edge(QUERIES[1], 0x23, '->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I')
    if bodies[QUERIES[1]]['catches'] != [{'startPc': 0, 'codeUnits': 29, 'exceptionType': 'Landroid/os/RemoteException;', 'handlerPc': 30}]:
        raise ValueError('checkService suppression changed')
    result = {'schema': 'guest-metrics-lifecycle/v1', 'status': 'SOURCE_API_PROPOSAL_PUBLICATION_OWNER_OPEN',
              'frozenInputs': [{'path': p, 'sha256': h} for p, h in PINS.items()],
              'reusedFactoryEvidence': {'inventory': 'inventory/guest-metrics-endpoint.json', 'assertionCount': endpoint['assertionCount'], 'oneosCommit': endpoint['oneos']['commit'], 'oneosFileCount': len(endpoint['oneos']['files'])},
              'newMethodEvidence': {'receipt': selected['receipt'], 'receiptSha256': digest(path), 'raw': receipt['raw'], 'rawSha256': receipt['rawSha256'], 'archiveSha256': receipt['archiveSha256'], 'methods': receipt['selectedMethodProofs']},
              'newAssertions': assertions, 'newAssertionCount': len(assertions), 'newBodies': 2,
              'proposedConfiguration': {'kind': 'process-local build-owned literal, not a runtime authorization/attestation flag', 'default': 'OFF', 'owner': 'future explicit OneOS candidate build profile generated/pinned with patched services source and helper closure', 'acquisition': 'same selected lifecycle class reads its own literal once; no caller bool/UID/config callback, property, SettingsProvider or new persistent-file read', 'persistentToggleImplemented': False, 'runtimeSourceAdmission': 'external and unassembled; compiled flag only permits a feature attempt'},
              'proposedApi': ['captureAfterOnStart(Object actualDms,Binder actualBorn):GuestMetricsLifecycle?; only exact source tail, null when off/failed', 'candidateAfterPhase100(Object sameDms,int actualPhase):IBinder?; original normal-success tail only; endpoint remains INACTIVE', 'finishPublication(Object sameDms,IBinder attemptedCandidate):void; internal genuine registry acquisition/readback NOT CLOSED; may not activate from void-return/null wrapper', 'publicationFailed(Object sameDms,IBinder attemptedCandidate,Throwable ownPublicationFault):void; terminal disable/retire, no retry', 'retire(Object sameDms):void; terminal/idempotent, retain actual active/uncertain owners'],
              'sourceEditFootprint': ['One private DMS lifecycle-cell field', 'Exact onStart normal tail capture from this and still-live actual born v0 after original publications', 'Exact onBootPhase normal return tail with actual phase100 guard; original protected DMS publishBinderService owns alias write, endpoint inactive through uncertain publication', 'Own hook exception regions only; preserve every original extension call/failure', 'Complete lifecycle+Endpoint+Producer dependency closure in actual DMS defining loader; default-OFF OneOS build profile, exact source/DEX/inverse checks'],
              'unclosed': ['Genuine noncached registry owner and same-Binder identity readback with transport errors distinct from absent', 'Alias collision/exclusive publication semantics; check-then-add is not atomic no-overwrite proof', 'Exact default-off profile producer/selected patched artifact and real loader/current source admission', 'Actual lifecycle hooks, publication, source/epoch/client admission, native completion/retirement/drain and Samsung consumer'],
              'runtimeCodeEmitted': False, 'endpointPublished': False, 'oemCodeExecuted': False, 'phoneChanged': False, 'toolSha256': digest(__file__)}
    (ROOT / 'inventory/guest-metrics-lifecycle.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'pass': True, 'reusedFactoryAssertions': endpoint['assertionCount'], 'newBodies': 2, 'newAssertions': len(assertions), 'publicationOwnerOpen': True, 'runtimeCodeEmitted': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.read:
        read()
    if args.report:
        report()
