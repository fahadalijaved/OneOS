"""Audit saved Samsung bind-path evidence; never query, load, or execute OEM code."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'out/retained-biometric-bind-path'
MANIFESTS = {
    'chain-collection.json': 'c9e75d14a5b23ce752e58d6a505674185629e32cc44f0ace1c85b8fc2f43cc08',
    'tail-collection.json': '007e3cf6221396ffb722dadc40cc544371cdfaa9ede64f66e3da19e2fc5f4e69',
    'final-tail-collection.json': '64578464e3da17d2eccbb486fc063dadd1716222a1988ae0a3492c713ca45447',
    'scheduler-collection.json': '93d1da55c4e7e830d2827536f33f9995ba003c83660b329d3533f275778c7b30',
    # Historical collector label does not prove a prewarm/session-free origin.
    'prewarm-collection.json': 'cac5c5e3e3e8043f13091cda1f13f9a61ff1218a168e21aa3fc405c6f8d3c668',
}
REUSE = {
    'out/authority-bootstrap-biometrics/sysui-constructor-receipt.json': '0a51c2fb7374ff07127a3b987e5c3d94398a2a08b72451ca883cc20a7447681e',
    'out/authority-bootstrap-biometrics/sysui-bind-receipt.json': '0c716eac5c415f0cdc6b2ab7783018ceabc9ffdf4a60fcd961ca2fef5b225168',
    'inventory/biometric-ui-authority.json': '418a65da4c80997a7ee01f3a6becd5b7fd25b5ad570656028bafae6dc9ba5084',
}
ARCHIVES = {
    '../firmware/samsung/framework.jar': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
    '../firmware/samsung/runtime-20261104/services.jar': 'def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6',
}
# Exact original code-unit PCs; descriptors in output disambiguate every overload.
# Selector: owner suffix, method prefix, optional unique signature substring.
EDGES = [
 ('SemBiometricSysUiManager;', 'bind()', '', 57, '->bindService('),
 ('SemBiometricSysUiManager;', 'bind()', '', 69, '->postDelayed('),
 ('SemBiometricSysUiManager;', 'bind()', '', 102, '->sendConnectionError('),
 ('SemBiometricSysUiManager;', 'openSession(', '', 120, '->bind()'),
 ('SemBiometricSysUiManager;', 'onServiceConnected(', '', 8, '->removeCallbacks('),
 ('SemBiometricSysUiManager;', 'onServiceConnected(', '', 17, '->asInterface('),
 ('SemBiometricSysUiManager;', 'onServiceConnected(', '', 45, '->linkToDeath('),
 ('SemBiometricSysUiManager;', 'unBind()', '', 54, '->unbindService('),
 ('SemBiometricSysUiManager;', 'sendConnectionError(', '', 26, '->post('),
 ('SemBiometricSysUiManager;', 'notifySysUiErrorEvent(', '', 35, '->onError('),
 ('SemBiometricSysUiManager$$ExternalSyntheticLambda0;', 'run()', '', 17, '->notifySysUiErrorEvent('),
 ('SemBiometricSysUiManager$$ExternalSyntheticLambda0;', 'run()', '', 20, '->unBind()'),
 ('SemFingerprintServiceExtImpl$$ExternalSyntheticLambda7;', 'run()', '', 28, '->bind()'),
 ('SemFingerprintServiceExtImpl$$ExternalSyntheticLambda7;', 'run()', '', 41, '->handleRequest('),
 ('ContextImpl;', 'bindService(', 'ILjava/util/concurrent/Executor;', 0, '->toUnsignedLong('),
 ('ContextImpl;', 'bindService(', 'ILjava/util/concurrent/Executor;', 5, '->getUser()'),
 ('ContextImpl;', 'bindService(', 'ILjava/util/concurrent/Executor;', 14, '->bindServiceCommon('),
 ('ContextImpl;', 'bindServiceCommon(', '', 30, '->getServiceDispatcher('),
 ('ContextImpl;', 'bindServiceCommon(', '', 49, '->validateServiceIntent('),
 ('ContextImpl;', 'bindServiceCommon(', '', 90, '->getService()'),
 ('ContextImpl;', 'bindServiceCommon(', '', 96, '->getApplicationThread('),
 ('ContextImpl;', 'bindServiceCommon(', '', 112, '->getOpPackageName('),
 ('ContextImpl;', 'bindServiceCommon(', '', 116, '->getIdentifier('),
 ('ContextImpl;', 'bindServiceCommon(', '', 123, '->bindServiceInstance('),
 ('ContextImpl;', 'bindServiceCommon(', '', 155, '->rethrowFromSystemServer('),
 ('LoadedApk;', 'getServiceDispatcher(', 'Executor;', 6, '->getServiceDispatcherCommon('),
 ('LoadedApk;', 'getServiceDispatcherCommon(', '', 64, '->validate('),
 ('LoadedApk;', 'getServiceDispatcherCommon(', '', 67, '->getIServiceConnection('),
 ('ActivityManagerService;', 'bindServiceInstance(', 'JLjava/lang/String;Ljava/lang/String;I)', 23, '->bindServiceInstance('),
 ('ActivityManagerService;', 'bindServiceInstance(', 'ApplicationThreadDeferred;', 14, '->enforceNotIsolatedCaller('),
 ('ActivityManagerService;', 'bindServiceInstance(', 'ApplicationThreadDeferred;', 25, '->enforceCallingPackage('),
 ('ActivityManagerService;', 'bindServiceInstance(', 'ApplicationThreadDeferred;', 327, '->bindServiceLocked('),
 ('ActiveServices;', 'bindServiceLocked(', '', 15, '->getCallingPid()'),
 ('ActiveServices;', 'bindServiceLocked(', '', 26, '->getCallingUid()'),
 ('ActiveServices;', 'bindServiceLocked(', '', 530, '->retrieveServiceLocked('),
 ('ActiveServices;', 'bindServiceLocked(', '', 1039, '->clearCallingIdentity()'),
 ('ActiveServices;', 'bindServiceLocked(', '', 1628, '->bringUpServiceLocked('),
 ('ActiveServices;', 'bindServiceLocked(', '', 1650, '->restoreCallingIdentity('),
 ('ActiveServices;', 'retrieveServiceLocked(', '', 775, '->resolveService('),
 ('ActiveServices;', 'retrieveServiceLocked(', '', 1550, '->resolveService('),
 ('ActiveServices;', 'retrieveServiceLocked(', '', 2132, '->checkComponentPermission('),
 ('ActiveServices;', 'bringUpServiceLocked(', '', 32, '->bringUpServiceInnerLocked('),
 ('ActiveServices;', 'bringUpServiceInnerLocked(', '', 403, '->getProcessRecordLocked('),
 ('ActiveServices;', 'bringUpServiceInnerLocked(', '', 465, '->realStartServiceLocked('),
 ('ActiveServices;', 'bringUpServiceInnerLocked(', '', 887, '->startProcessLocked('),
 ('ActiveServices;', 'bringUpServiceInnerLocked(', '', 923, '->startProcessLocked('),
 ('ActiveServices;', 'bringUpServiceInnerLocked(', '', 987, '->bringDownServiceLocked('),
 ('ActivityManagerService;', 'startProcessLocked(', '', 34, '->startProcessLocked('),
 ('ProcessList;', 'startProcessLocked(', '', 528, '->newProcessRecordLocked('),
 ('ProcessList;', 'startProcessLocked(', '', 794, '->startProcessLocked('),
 ('ActiveServices;', 'realStartServiceLocked(', '', 117, '->scheduleCreateService('),
 ('ActiveServices;', 'realStartServiceLocked(', '', 151, '->requestServiceBindingLocked('),
 ('ActiveServices;', 'realStartServiceLocked(', '', 400, '->scheduleServiceRestartLocked('),
 ('ActiveServices;', 'requestServiceBindingLocked(', '', 142, '->scheduleBindService('),
 ('ActiveServices;', 'attachApplicationLocked(', '', 150, '->realStartServiceLocked('),
 ('ActiveServices;', 'scheduleServiceRestartLocked(', '', 567, '->performScheduleRestartLocked('),
 ('ActiveServices;', 'performScheduleRestartLocked(', '', 135, '->tryPerformScheduleRestartLocked('),
 ('ActiveServices;', 'tryPerformScheduleRestartLocked(', '', 31, '->postAtTime('),
 ('ActiveServices$ServiceRestarter;', 'run()', '', 18, '->performServiceRestartLocked('),
 ('ActiveServices;', 'performServiceRestartLocked(', '', 155, '->bringUpServiceLocked('),
 ('AuthSession;', '<init>(', '', 241, '->openSession('),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', default='inventory/retained-biometric-bind-path.json')
    args = ap.parse_args()
    output = (ROOT / args.output).resolve()
    assert output.is_relative_to(ROOT)
    pins = {}

    def pin(name, expected=None):
        path = ROOT / name
        actual = digest(path)
        if expected is not None:
            assert actual == expected, f'pin mismatch: {name}'
        pins[name] = {'sha256': actual, 'bytes': path.stat().st_size}
        return path

    def load(name, expected=None):
        return json.loads(pin(name, expected).read_text(encoding='utf-8'))

    for name, sha in ARCHIVES.items():
        pin(name, sha)
    collections = {n: load(f'{SCOPE}/{n}', sha) for n, sha in MANIFESTS.items()}
    reused = {n: load(n, sha) for n, sha in REUSE.items()}
    batches = []
    for n in ['chain-collection.json', 'tail-collection.json', 'final-tail-collection.json']:
        batches.extend(collections[n])
    batches.extend([collections['scheduler-collection.json']['method'], collections['prewarm-collection.json']])
    receipt_names = [b['receipt'] for b in batches]
    expected_batches = {b['receipt']: b for b in batches}
    receipt_names.extend(n for n in REUSE if n.endswith('receipt.json'))
    bio = reused['inventory/biometric-ui-authority.json']
    selected_bio = [x for x in bio['methodProofs'] if 'AuthSession;-><init>' in x['key'] or 'SemFpSysUiImpl;-><init>' in x['key']]
    assert len(selected_bio) == 2
    bio_keys = {x['key'].split(':', 1)[1] for x in selected_bio}
    bio_receipts = {x['receipt'] for x in selected_bio}
    receipt_names.extend(x['receipt'] for x in selected_bio)
    query = collections['scheduler-collection.json']['bindCallers']
    receipt_names.append(query['receipt'])
    methods = {}
    bodies = {}
    references = []
    dex_profiles = {}
    for name in receipt_names:
        r = load(name)
        assert r['readerExitCode'] == 0 and r['archiveAndToolPinsVerifiedBeforeAndAfter'] is True
        assert r['oemCodeExecuted'] is False and r['androidExecuted'] is False
        assert r['archiveSha256'] in ARCHIVES.values()
        if name in expected_batches:
            expected = expected_batches[name]
            assert r['raw'] == expected['raw'] and r['rawSha256'] == expected['rawSha256']
            assert r['archiveSha256'] == expected['archiveSha256']
            assert r['selectedMethodProofs'] == expected['methods']
        if name == query['receipt']:
            assert r['raw'] == query['raw'] and r['rawSha256'] == query['rawSha256']
        raw = pin(r['raw'], r['rawSha256'])
        assert raw.stat().st_size == r['rawBytes']
        rows = [json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
        proofs = {(x['owner'], x['signature']): x for x in r['selectedMethodProofs']}
        for row in rows:
            if row['record'] == 'dex':
                dex_profiles[(r['archiveSha256'], row['physicalDex'], row['logicalHeaderOffset'])] = row
            elif row['record'] == 'reference':
                references.append(row)
            elif row['record'] == 'method':
                b = row['body']
                key = (b['owner'], b['signature'])
                if name in bio_receipts and key[0] + '->' + key[1] not in bio_keys:
                    continue
                proof = proofs[key]
                if name in bio_receipts:
                    expected = next(x for x in selected_bio if x['key'].split(':', 1)[1] == key[0] + '->' + key[1])
                    assert expected['raw'] == r['raw'] and expected['rawSha256'] == r['rawSha256']
                    assert expected['normalizedBodySha256'] == row['normalizedBodySha256']
                assert proof['normalizedBodySha256'] == row['normalizedBodySha256']
                assert proof['hasCode'] and len(b['instructions']) == proof['instructionCount']
                assert proof['physicalDex'] == row['physicalDex'] and proof['logicalHeaderOffset'] == row['logicalHeaderOffset']
                assert proof['accessFlags'] == b['accessFlags']
                methods[key] = dict(proof, archiveSha256=r['archiveSha256'], receipt=name, raw=r['raw'], rawSha256=r['rawSha256'])
                bodies[key] = b
    assert len(methods) == 36, len(methods)
    assert len(references) == query['referenceMatches'] == 2
    assert sorted(x['instruction']['pc'] for x in references) == [28, 120]
    edges = []
    for owner, prefix, contains, pc, target in EDGES:
        keys = [k for k in bodies if k[0].endswith(owner) and k[1].startswith(prefix) and contains in k[1]]
        assert len(keys) == 1, (owner, prefix, contains, keys)
        key = keys[0]
        matches = [i for i in bodies[key]['instructions'] if i['pc'] == pc]
        assert len(matches) == 1 and target in matches[0].get('reference', ''), (key, pc, target, matches)
        i = matches[0]
        edges.append({'owner': key[0], 'signature': key[1], 'pcCodeUnits': pc, 'opcode': i['opcode'], 'target': i['reference']})
    def body(owner, prefix):
        return next(v for k, v in bodies.items() if k[0].endswith(owner) and k[1].startswith(prefix))
    def at(b, pc):
        return next(i for i in b['instructions'] if i['pc'] == pc)
    bind = body('SemBiometricSysUiManager;', 'bind()')
    assert at(bind, 54)['literal'] == 603979777
    assert at(bind, 67)['literal'] == 3000
    assert at(bind, 60)['opcode'].startswith('CONST')  # No MOVE_RESULT consuming bind boolean.
    constructor = body('SemBiometricSysUiManager;', '<init>(')
    assert at(constructor, 40)['literal'] == 4
    for pc, field in [(49, 'mRunnableHandleBindTimeout:'), (62, 'mExecutor:'), (71, 'mContext:'), (78, 'mHandler:')]:
        assert at(constructor, pc)['opcode'].startswith('IPUT') and field in at(constructor, pc)['reference']
    timeout = body('SemBiometricSysUiManager$$ExternalSyntheticLambda0;', 'run()')
    payload = next(i for i in timeout['instructions'] if i.get('switchElements'))
    assert [x['key'] for x in payload['switchElements']] == [0, 1, 2, 3]
    assert at(timeout, 16)['literal'] == 2
    common = body('ContextImpl;', 'bindServiceCommon(')
    assert at(common, 127)['opcode'].startswith('IF_')
    assert at(common, 133)['literal'] == 0 and at(common, 152)['opcode'] == 'THROW'
    assert at(common, 159)['opcode'] == 'THROW'
    pin('tools/audit_retained_biometric_bind_path.py')
    result = {
        'schema': 'retained-biometric-bind-path/v1',
        'status': 'PASS_SAVED_SOURCE_CHAIN_ONLY', 'selected': False,
        'newMethodBodies': 31, 'reusedMethodBodies': 5, 'methodBodyCount': len(methods),
        'exactDirectBindCallers': references, 'checkedCallEdges': edges,
        'methodProofs': sorted(methods.values(), key=lambda m: (m['owner'], m['signature'])),
        'dexProfiles': list(dex_profiles.values()), 'pins': pins,
        'sourceFacts': {
            'bindBooleanConsumed': False, 'bindTimeoutMilliseconds': 3000,
            'managerExecutorAndConnectionPreserved': True,
            'missingProcessAndHandlerRestartRequestProven': True,
            'secondBindOriginSchedulingClassified': False,
        },
        'proposedRestriction': 'Source-owned manager/dispatcher/connection correlation, checked after genuine service resolution/permission checks; retain exact record association through attach/restart/unbind. Separate foreground activity admission is not audited here.',
        'unresolved': [
            'Actual current manager Context implementation/loader/user and live caller/session owners',
            'Extension Runnable allocation/scheduling and legitimate lifetime beyond its direct bind branch',
            'Implemented unforgeable origin admission and exact ConnectionRecord/ServiceRecord restart association',
            'Foreground ATMS admission hook/body and live display/input/power ownership',
            'Current PID/process launch, endpoint callbacks and authentication/device acceptance',
        ],
        'execution': {'savedDataAuditorOnly': True, 'newReaderQueries': 0, 'oemCodeExecuted': False, 'androidExecuted': False, 'phoneAccess': False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'methods': len(methods), 'edges': len(edges), 'directCallers': 2, 'output': str(output), 'sha256': digest(output)}))


if __name__ == '__main__':
    main()
