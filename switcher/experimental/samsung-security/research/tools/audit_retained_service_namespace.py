"""Audit fixed saved ServiceManager evidence only; never load OEM implementations."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / 'inventory/retained-service-namespace-proof.json'
OUT = ROOT / 'out/retained-service-namespace'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    data = json.loads(INVENTORY.read_text())
    checks = []

    def check(condition, label):
        if not condition:
            raise ValueError(label)
        checks.append(label)

    for path, pin in {**data['inputCards'], **data['readerPins']}.items():
        check(sha(ROOT / path) == pin, 'frozen input ' + path)
    methods = {}
    declarations = {}
    for label, query in data['queries'].items():
        check(sha(ROOT / query['receipt']) == query['receiptSha256'], label + ' receipt')
        check(sha(ROOT / query['raw']) == query['rawSha256'], label + ' raw')
        receipt = json.loads((ROOT / query['receipt']).read_text())
        check(receipt['archiveSha256'] == query['archiveSha256']
              and receipt['archiveAndToolPinsVerifiedBeforeAndAfter']
              and receipt['readerExitCode'] == 0, label + ' source identity')
        for row in map(json.loads, (ROOT / query['raw']).read_text().splitlines()):
            if row['record'] == 'class':
                declarations[label] = row
            if row['record'] == 'method':
                methods[label + ':' + row['body']['signature']] = row
    for key, proof in data['reusedMethodProofs'].items():
        check(sha(ROOT / proof['raw']) == proof['rawSha256'], 'reused raw ' + key)
        owner, signature = key.split(':', 1)[1].split('->', 1)
        matches = [row for row in map(json.loads, (ROOT / proof['raw']).read_text().splitlines())
                   if row['record'] == 'method' and row['body']['owner'] == owner
                   and row['body']['signature'] == signature]
        check(len(matches) == 1 and matches[0]['normalizedBodySha256'] == proof['bodySha256'],
              'reused method ' + key)
        methods[key] = matches[0]

    def body(label, signature):
        return methods[label + ':' + signature]['body']

    def site(label, signature, pc, reference=None, opcode=None, registers=None):
        matches = [v for v in body(label, signature)['instructions'] if v['pc'] == pc]
        check(len(matches) == 1, label + ' PC ' + str(pc) + ' ' + signature)
        value = matches[0]
        check((reference is None or value.get('reference') == reference)
              and (opcode is None or value['opcode'] == opcode)
              and (registers is None or value.get('registers') == registers),
              label + ' instruction ' + str(pc) + ' ' + signature)
        return value

    sm = 'Landroid/os/ServiceManager;->'
    get = 'getService(Ljava/lang/String;)Landroid/os/IBinder;'
    chk = 'checkService(Ljava/lang/String;)Landroid/os/IBinder;'
    for signature in (get, chk):
        site('guest-sm', signature, 0, sm + 'sCache:Ljava/util/Map;')
        site('guest-sm', signature, 2, 'Ljava/util/Map;->get(Ljava/lang/Object;)Ljava/lang/Object;')
        site('guest-sm', signature, 10, opcode='RETURN_OBJECT')
    site('guest-sm', get, 11, sm + 'rawGetService(Ljava/lang/String;)Landroid/os/IBinder;')
    site('guest-sm', chk, 15, 'Landroid/os/IServiceManager;->checkService2(Ljava/lang/String;)Landroid/os/Service;')
    site('guest-sm', 'rawGetService(Ljava/lang/String;)Landroid/os/IBinder;', 12,
         'Landroid/os/IServiceManager;->getService2(Ljava/lang/String;)Landroid/os/Service;')
    site('guest-sm', 'getIServiceManager()Landroid/os/IServiceManager;', 7,
         'Lcom/android/internal/os/BinderInternal;->getContextObject()Landroid/os/IBinder;')
    site('guest-sm', 'getIServiceManager()Landroid/os/IServiceManager;', 15,
         'Landroid/os/ServiceManagerNative;->asInterface(Landroid/os/IBinder;)Landroid/os/IServiceManager;')
    add = 'addService(Ljava/lang/String;Landroid/os/IBinder;ZI)V'
    site('guest-sm', add, 4, 'Landroid/os/IServiceManager;->' + add)
    site('guest-sm', 'addService(Ljava/lang/String;Landroid/os/IBinder;)V', 3, sm + add)
    site('guest-sm', 'addService(Ljava/lang/String;Landroid/os/IBinder;Z)V', 2, sm + add)
    wait = 'waitForService(Ljava/lang/String;)Landroid/os/IBinder;'
    for label in ('guest-sm', 'host-sm'):
        site(label, wait, 0, sm + 'waitForServiceNative(Ljava/lang/String;)Landroid/os/IBinder;')
        native = body(label, 'waitForServiceNative(Ljava/lang/String;)Landroid/os/IBinder;')
        check(not native['hasCode'] and native['accessFlags'] & 0x100, label + ' native wait boundary')
    site('guest-sm', 'initServiceCache(Ljava/util/Map;)V', 6, opcode='IF_NEZ')
    site('guest-sm', 'initServiceCache(Ljava/util/Map;)V', 10,
         'Ljava/util/Map;->putAll(Ljava/util/Map;)V', registers=[0, 2])
    bind = next(k.split(':', 1)[1] for k in methods if k.startswith('guest-bind:bindApplication'))
    call = site('guest-bind', bind, 49, sm + 'initServiceCache(Ljava/util/Map;)V')
    check(call['registerStart'] == 35 and call['registerCount'] == 1, 'incoming bind Map35 enters cache unchanged')
    throws = ['registerClientCallback(Ljava/lang/String;Landroid/os/IBinder;Landroid/os/IClientCallback;)V',
              'unregisterForNotifications(Ljava/lang/String;Landroid/os/IServiceCallback;)V',
              'tryUnregisterService(Ljava/lang/String;Landroid/os/IBinder;)V']
    for label in ('guest-proxy', 'host-proxy'):
        for signature in throws:
            site(label, signature, 0, 'Landroid/os/RemoteException;', opcode='NEW_INSTANCE')
            site(label, signature, 5, opcode='THROW')
        site(label, 'getService2(Ljava/lang/String;)Landroid/os/Service;', 0,
             'Landroid/os/ServiceManagerProxy;->checkService2(Ljava/lang/String;)Landroid/os/Service;')

    expected = {'getService': 1, 'getService2': 2, 'checkService': 3, 'checkService2': 4,
                'addService': 5, 'listServices': 6, 'registerForNotifications': 7,
                'unregisterForNotifications': 8, 'isDeclared': 9, 'getDeclaredInstances': 10,
                'updatableViaApex': 11, 'getUpdatableNames': 12, 'getConnectionInfo': 13,
                'registerClientCallback': 14, 'tryUnregisterService': 15,
                'getServiceDebugInfo': 16, 'checkServiceAccess': 17}

    def wire(label, signature):
        instructions = body(label, signature)['instructions']
        call, = [v for v in instructions if v.get('reference', '').startswith('Landroid/os/IBinder;->transact(')]
        constants = {}
        for value in instructions:
            if value['pc'] >= call['pc']:
                break
            if value['opcode'].startswith('CONST') and 'literal' in value:
                constants[value['registers'][0]] = value['literal']
        refs = [v.get('reference', '') for v in instructions]
        return {'code': constants[call['registers'][1]], 'flags': constants[call['registers'][4]],
                'writes': [x.split('->')[1] for x in refs if x.startswith('Landroid/os/Parcel;->write')],
                'reads': [x.split('->')[1] for x in refs if x.startswith('Landroid/os/Parcel;->read') or x.startswith('Landroid/os/Parcel;->create')],
                'creators': [x for x in refs if '->CREATOR:' in x]}

    routes = []
    for signature in sorted(k.split(':', 1)[1] for k in methods if k.startswith('guest-aidl:')):
        name = signature.split('(')[0]
        if name not in expected:
            continue
        guest, host = wire('guest-aidl', signature), wire('host-aidl', signature)
        check(guest == host and guest['code'] == expected[name] and guest['flags'] == 0,
              'actual guest/host generated wire ' + name)
        routes.append({'signature': signature, **guest})
    check(len(routes) == 17, 'complete selected IServiceManager wire table')
    cb = 'onRegistration(Ljava/lang/String;Landroid/os/IBinder;)V'
    guest, host = wire('guest-callback', cb), wire('host-callback', cb)
    check(guest == host and guest['code'] == 1 and guest['flags'] == 1, 'actual callback wire code1 oneway')
    for label in ('guest-callback-stub', 'host-callback-stub'):
        site(label, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 10,
             'Landroid/os/Parcel;->enforceInterface(Ljava/lang/String;)V')
        site(label, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 21 if label == 'guest-callback-stub' else 20,
             'Landroid/os/Parcel;->readString()Ljava/lang/String;')
        site(label, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 25 if label == 'guest-callback-stub' else 24,
             'Landroid/os/Parcel;->readStrongBinder()Landroid/os/IBinder;')
        site(label, 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 29 if label == 'guest-callback-stub' else 28,
             'Landroid/os/Parcel;->enforceNoDataAvail()V')
    site('guest-sms-connect', 'connectVold()V', 0, 'string=gvld')
    site('guest-sms-connect', 'connectVold()V', 3, sm + get)
    site('guest-sms-connect', 'connectVold()V', 15,
         'Landroid/os/IBinder;->linkToDeath(Landroid/os/IBinder$DeathRecipient;I)V')
    site('guest-lss-start', 'onStart()V', 9,
         'Lcom/android/server/locksettings/LockSettingsService;-><init>(Landroid/content/Context;)V')
    site('guest-lss-start', 'onStart()V', 14, 'string=lock_settings')
    site('guest-lss-start', 'onStart()V', 19,
         'Lcom/android/server/locksettings/LockSettingsService$Lifecycle;->publishBinderService(Ljava/lang/String;Landroid/os/IBinder;)V')
    check(any(v.get('reference') == sm + add for v in body('guest-systemservice', 'publishBinderService(Ljava/lang/String;Landroid/os/IBinder;ZI)V')['instructions']),
          'actual guest SystemService publication reaches unchanged ServiceManager add')
    installer = 'stage:Lcom/android/server/pm/Installer;->connect()V'
    instructions = methods[installer]['body']['instructions']
    check(instructions[0].get('reference') == 'string=installd', 'existing Installer canonical lookup')
    check(any(v['pc'] == 23 and 'OneOSInstalldProxy;->asInterface' in v.get('reference', '') for v in instructions),
          'existing per-service OneOSInstalldProxy is not namespace routing')
    for name, script in data['scripts'].items():
        check(sha(ROOT / script['path']) == script['sha256'], 'installed script identity ' + name)
    prepare = (ROOT / data['scripts']['guest_prepare.sh']['path']).read_text()
    check('$BB mount --rbind /dev "$ROOTFS/dev"' in prepare, 'installed script shares existing device nodes')
    check('echo gvld > "$STAGE/data/oneos_vold_name"' in prepare, 'installed script explicit gvld marker')
    start = (ROOT / data['scripts']['guest_start.sh']['path']).read_text()
    check('VOLD_NAME=gvld' in start and 'SELinux is enforcing: servicemanager refuses gvld' in start,
          'existing alias marker and explicit policy gate')
    result = {'status': 'PASS_STATIC_NAMESPACE_SOURCE_ONLY', 'checks': len(checks),
              'assertions': checks, 'generatedWireRoutes': routes, 'callbackWire': guest,
              'rawMethodProofCount': len(methods), 'runtimeVerified': False,
              'oemExecuted': False, 'phoneActions': False, 'routingImplemented': False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'checks', 'rawMethodProofCount', 'routingImplemented')}))


if __name__ == '__main__':
    main()
