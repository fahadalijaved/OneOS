"""Verify selected ColorOS startup facts against frozen static-reader output."""

import json

from run_guest_tree_install_transport import load_io, pinned


DONOR = '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3'
STAGED = 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'
FRAMEWORK = '5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246'
PROOFS = {
    'donorBootstrap': (DONOR, '20261105T144235058123Z-c0248b12b8364dc3af57d59b8e8f69ca', 'da02c566982304fcc905222105878b2cfd90d6ee8bce749ce4a27d9f48c018ee'),
    'donorAms': (DONOR, '20261107T174416927706Z-01b29308086f48259a7b6486b538ccfe', '30592b3aabcdf345f1aeb465aa84f889601b55ae96ee967e669576b4f0e1bee7'),
    'bootstrap': (STAGED, '20261107T174349899007Z-3886f8fc15914c1c9e5b961e162163d7', '993a4179a87e896b457bd9439d018a55a6fa275f7f7e378e16facf0959227bfb'),
    'ams': (STAGED, '20261107T174349899007Z-0b520dd5fcb9400a9f449314d4897bfb', 'd374680d1401804828235c49167a26ac8042df7e42c508a5255a0515185b1ff1'),
    'pidOwner': (STAGED, '20261107T174416927706Z-31c65288bd164255b5759fb0f627a099', '17e1e4dcfac89ab0d64219c20840689b27f73072ff247fcb85a9375ffe87039b'),
    'pidMap': (STAGED, '20261107T174451665486Z-ae2ef675a4ba4d85bd99a6a247393fa2', 'aa4b6438b51dc6e4241caf8f9b336ae4857a9db72711812a110bf4ac55a652d7'),
    'phase': (STAGED, '20261107T174349898506Z-e1a64df8eace4baaa484e0db21d8a572', '46f9562641e5129664f4e558211dc635201f69ae81a78fa80af6279d3a342d6b'),
    'run': (STAGED, '20261107T174451665486Z-2e94548d1f83496abde2d893b837def1', 'a3232e2e3b071dcf8ad8c33de804140e37652c361147696a423027b17c838cc5'),
    'watchdog': (STAGED, '20261107T174523169718Z-ca28014083c349f7b56622753f549861', '643b9cd43e1feb513a0cb66187e06a4f517b541516c2537abe37aa928a6f9b88'),
    'watchdogCallers': (STAGED, '20261107T174523170218Z-92c98787ba704d9b9d33456212f2bb45', 'ba2b08b132a0cc75ed13a11f744adb8f7d26a7a9db85db2be39f2cdd96839498'),
    'watchdogField': (STAGED, '20261107T174523170218Z-d52aa9ddcb3a4e8fa8fafd32629a8f62', '0429c0c945b4fb650d0bc28cdc494ce08c5f31dd167b682ef0d44494874efdab'),
    'activityThread': (FRAMEWORK, '20261107T174416929709Z-262859d2d710438693e6f380804b556f', '5ee4c280974c2596eb11e7ffafdfd0190ad5054bc78347f934ae742f203708f6'),
    'localServices': (FRAMEWORK, '20261107T174416935706Z-3b97cf8b1ecb42dcb0a2a07acd6b0b8a', 'bf1f0149f08bb4029f714907c5d23ee4325e26174130114e4a43c7adbdf6c912'),
    'wrapper': (STAGED, '20261107T174451676986Z-fbf4ec748b3845409e179d00414532e9', 'd2ad3b10eef964b7cb62defbe882d63b7ce9a739c7d57c8a0c7d85531406edc5'),
    'record': (STAGED, '20261107T174451701486Z-4403a90729314f97ab57c9705a111738', '2f736b229f9b9cee3cdf396d0f502cc764661ab0f99ab2a1489ae3adb299ee73'),
}


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def read_source(io, archive, stamp, digest):
    path = f'out/tooling/{stamp}/receipt.json'
    receipt = json.loads(pinned(io, path, digest, 1024 * 1024), object_pairs_hook=io['unique_object'])
    require(receipt['archiveSha256'] == archive and receipt['readerExitCode'] == 0
            and receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] is True
            and receipt['oemCodeExecuted'] is False and receipt['androidExecuted'] is False,
            'Wrong held source-reader provenance')
    raw = pinned(io, receipt['raw'], receipt['rawSha256'], 8 * 1024 * 1024)
    require(len(raw) == receipt['rawBytes'], 'Raw source record length differs')
    rows = [json.loads(line, object_pairs_hook=io['unique_object']) for line in raw.splitlines()]
    return rows, {'receipt': path, 'receiptSha256': digest, 'archiveSha256': archive,
                  'raw': receipt['raw'], 'rawSha256': receipt['rawSha256']}


def body(rows, owner, signature):
    selected = [row for row in rows if row['record'] == 'method'
                and (row['body']['owner'], row['body']['signature']) == (owner, signature)]
    require(len(selected) == 1 and selected[0]['body']['hasCode'], f'Expected one method: {owner}->{signature}')
    return selected[0]


def at(row, pc, opcode, ref=None, registers=None):
    selected = [i for i in row['body']['instructions'] if i['pc'] == pc]
    require(len(selected) == 1 and selected[0]['opcode'] == opcode
            and (ref is None or selected[0].get('reference') == ref)
            and (registers is None or selected[0].get('registers') == registers),
            f"Source edge differs: {row['body']['signature']} at {pc}")
    return selected[0]


def verify():
    io = load_io()
    rows, sources = {}, {}
    for name, proof in PROOFS.items():
        rows[name], sources[name] = read_source(io, *proof)

    server = 'Lcom/android/server/SystemServer;'
    ams = 'Lcom/android/server/am/ActivityManagerService;'
    record = 'Lcom/android/server/am/ProcessRecord;'
    manager = 'Lcom/android/server/SystemServiceManager;'
    watchdog = 'Lcom/android/server/Watchdog;'
    local = 'Lcom/android/server/LocalServices;'
    bootstrap_sig = 'startBootstrapServices(Lcom/android/server/utils/TimingsTraceAndSlog;)V'
    registration_sig = 'setSystemProcess()V'
    pid_sig = 'addPidLocked(Lcom/android/server/am/ProcessRecord;)V'
    init_sig = 'init(Landroid/content/Context;Lcom/android/server/am/ActivityManagerService;)V'
    manager_field = server + '->mSystemServiceManager:' + manager
    ams_field = server + '->mActivityManagerService:' + ams
    watchdog_field = watchdog + '->mActivity:' + ams
    bootstrap = body(rows['bootstrap'], server, bootstrap_sig)
    registration = body(rows['ams'], ams, registration_sig)
    pid_owner = body(rows['pidOwner'], ams, pid_sig)
    parity = {}
    for staged, donor_name in ((bootstrap, 'donorBootstrap'), (registration, 'donorAms'),
                               (pid_owner, 'donorAms')):
        current = staged['body']
        original = body(rows[donor_name], current['owner'], current['signature'])
        require(staged['normalizedBodySha256'] == original['normalizedBodySha256']
                and current == original['body'], 'Donor and staged normalized bodies differ')
        parity[current['signature']] = staged['normalizedBodySha256']

    run = body(rows['run'], server, 'run()V')
    at(run, 343, 'IPUT_OBJECT', manager_field, [0, 1])
    at(run, 367, 'CONST_CLASS', manager, [0])
    at(run, 369, 'IGET_OBJECT', manager_field, [9, 1])
    at(run, 371, 'INVOKE_STATIC', local + '->addService(Ljava/lang/Class;Ljava/lang/Object;)V', [0, 9])
    at(bootstrap, 315, 'IGET_OBJECT', manager_field, [8, 11])
    at(bootstrap, 317, 'INVOKE_VIRTUAL', ams + '->setSystemServiceManager(' + manager + ')V', [6, 8])
    lookup = body(rows['localServices'], local, 'getService(Ljava/lang/Class;)Ljava/lang/Object;')
    at(lookup, 5, 'INVOKE_VIRTUAL', 'Landroid/util/ArrayMap;->get(Ljava/lang/Object;)Ljava/lang/Object;', [1, 2])
    at(bootstrap, 736, 'IGET_OBJECT', ams_field, [0, 11])
    call = at(bootstrap, 738, 'INVOKE_VIRTUAL', ams + '->' + registration_sig, [0])
    at(bootstrap, 756, 'IGET_OBJECT', ams_field, [8, 11])
    init = at(bootstrap, 758, 'INVOKE_VIRTUAL', watchdog + '->' + init_sig, [1, 0, 8])
    code = bootstrap['body']['instructions']
    require(all(not (738 < i.get('targetPc', -1) <= 758) for i in code)
            and not any('switchElements' in i for i in code)
            and all(not (738 < h['handlerPc'] <= 758)
                    and not (h['startPc'] <= 738 < h['startPc'] + h['codeUnits'])
                    for h in bootstrap['body']['catches'])
            and all(not i['opcode'].startswith(('IF_', 'GOTO', 'RETURN', 'THROW'))
                    for i in code if 738 < i['pc'] < 758),
            'Original registration continuation is no longer a normal-return-only path')
    require(call['pc'] + call['codeUnits'] == 741, 'Registration continuation moved')
    write = at(body(rows['watchdog'], watchdog, init_sig), 0, 'IPUT_OBJECT', watchdog_field, [6, 4])
    callers = [row for row in rows['watchdogCallers'] if row['record'] == 'reference']
    writes = [row for row in rows['watchdogField'] if row['record'] == 'reference'
              and row['instruction']['opcode'].startswith(('IPUT', 'SPUT'))]
    require(len(callers) == len(writes) == 1
            and callers[0]['caller'] == server + '->' + bootstrap_sig and callers[0]['instruction'] == init
            and writes[0]['caller'] == watchdog + '->' + init_sig and writes[0]['instruction'] == write,
            'Staged archive contains a different Watchdog caller or writer')

    at(registration, 0, 'CONST_STRING', 'string=activity', [0])
    at(registration, 5, 'INVOKE_STATIC', 'Landroid/os/ServiceManager;->addService(Ljava/lang/String;Landroid/os/IBinder;ZI)V', [0, 14, 2, 1])
    at(registration, 175, 'INVOKE_VIRTUAL', record + '->setPid(I)V', [0, 3])
    thread = 'Landroid/app/ActivityThread;'
    thread_type = 'Landroid/app/ActivityThread$ApplicationThread;'
    get_thread = 'getApplicationThread()' + thread_type
    wrapper = 'Lcom/android/server/am/ApplicationThreadDeferred;'
    constructor = '<init>(Landroid/app/IApplicationThread;)V'
    make_active = 'makeActive(' + wrapper + 'Lcom/android/server/am/ProcessStatsService;)V'
    at(registration, 187, 'IGET_OBJECT', ams + '->mSystemThread:' + thread, [5, 14])
    at(registration, 189, 'INVOKE_VIRTUAL', thread + '->' + get_thread, [5])
    at(registration, 193, 'INVOKE_DIRECT', wrapper + '->' + constructor, [3, 5])
    at(registration, 198, 'INVOKE_VIRTUAL', record + '->' + make_active, [0, 3, 5])
    at(body(rows['activityThread'], thread, get_thread), 0, 'IGET_OBJECT', thread + '->mAppThread:' + thread_type, [0, 1])
    at(body(rows['wrapper'], wrapper, constructor), 22, 'IPUT_OBJECT', wrapper + '->mBase:Landroid/app/IApplicationThread;', [4, 3])
    as_binder = 'asBinder()Landroid/os/IBinder;'
    at(body(rows['wrapper'], wrapper, as_binder), 2, 'INVOKE_INTERFACE', 'Landroid/app/IApplicationThread;->' + as_binder, [0])
    at(body(rows['record'], record, make_active), 5, 'IPUT_OBJECT', record + '->mThread:' + wrapper, [4, 3])
    at(registration, 206, 'INVOKE_VIRTUAL', ams + '->' + pid_sig, [14, 0])
    at(registration, 235, 'INVOKE_VIRTUAL', 'Lcom/android/server/appop/AppOpsService;->startWatchingMode(ILjava/lang/String;Lcom/android/internal/app/IAppOpsCallback;)V')
    at(registration, 251, 'INVOKE_VIRTUAL', 'Lcom/android/server/appop/AppOpsService;->startWatchingActive([ILcom/android/internal/app/IAppOpsActiveCallback;)V')
    at(registration, 254, 'RETURN_VOID')
    pid_map = 'Lcom/android/server/am/ActivityManagerService$PidMap;'
    put = 'doAddInternal(ILcom/android/server/am/ProcessRecord;)V'
    at(pid_owner, 6, 'MONITOR_ENTER', registers=[1])
    at(pid_owner, 9, 'INVOKE_VIRTUAL', pid_map + '->' + put, [2, 0, 5])
    at(pid_owner, 12, 'MONITOR_EXIT', registers=[1])
    at(body(rows['pidMap'], pid_map, put), 31, 'INVOKE_VIRTUAL', 'Landroid/util/SparseArray;->put(ILjava/lang/Object;)V', [0, 3, 4])

    phase_sig = 'startBootPhase(Lcom/android/server/utils/TimingsTraceAndSlog;I)V'
    phase = body(rows['phase'], manager, phase_sig)
    at(phase, 6, 'IPUT', manager + '->mCurrentPhase:I', [13, 11])
    at(phase, 171, 'INVOKE_VIRTUAL', 'Lcom/android/server/SystemService;->onBootPhase(I)V')
    at(phase, 314, 'INVOKE_INTERFACE', 'Ljava/util/concurrent/Future;->get()Ljava/lang/Object;')
    return {'schema': 'guest-ams-startup-source/v1', 'status': 'PASS_HELD_SOURCE_ONLY',
            'sources': sources, 'matchingDonorBodies': parity,
            'registrationCallPc': 738, 'normalContinuationPc': 741, 'watchdogInitCallPc': 758,
            'watchdogStorePc': 0, 'activityPublicationAttemptPc': 5, 'pidRegistrationCallPc': 206,
            'runtimeObserved': False, 'deviceEligible': False}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
