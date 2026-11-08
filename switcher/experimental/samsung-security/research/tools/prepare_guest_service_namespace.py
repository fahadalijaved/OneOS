"""Prepare an unselected Java/native namespace integration contract from saved proof.

This emits authored plan metadata only: no DEX writer, patch, loader or OEM run.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PARENT = Path('out/guest-service-namespace-preparation')
SOURCE_NAME = 'tools/prepare_guest_service_namespace.py'
MAX_INPUT_BYTES = 2 * 1024 * 1024
REPARSE_POINT = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
CARD = 'inventory/retained-service-namespace-proof.json'
CARD_SHA = '8ca7b1dee82b91835f6b056be7f02d3a9663709d7b69379a418ad3ccbfa4b9f6'
FREEZE = 'out/retained-service-namespace/FROZEN-MANIFEST.json'
FREEZE_SHA = '9f78aa370ec65050007b54d2780daef01edf6c9475fdd4ae6b2be5dee03eaa68'
NATIVE_PINS = {
    'docs/guest-native-service-manager.md': '1cf3f6104fa2e00393b41576b0dd0e599e34aca67f913df41008518e5adae34f',
    'inventory/guest-native-service-manager.json': '236e1bc90e176329f449aa575ff8911c8f6603e2a30a2e98472258b8c5a35dcf',
    'out/guest-native-service-manager/FROZEN-MANIFEST.json': 'abe7aff8160a0ff6169a4df84184d24721dad47476035aba9b691d14adfc8ed8',
}
LABELS = ['guest-sm', 'guest-proxy', 'guest-native', 'guest-stub-as', 'guest-aidl',
          'guest-callback', 'guest-callback-stub', 'guest-bind', 'guest-cache-xref']
SM = 'Landroid/os/ServiceManager;'
CB = 'Landroid/os/IServiceCallback$Stub;'
HELPER = 'Landroid/os/GuestServiceNamespace;'
API = [
    {'signature': 'requireLogicalName(Ljava/lang/String;)V',
     'access': 'package-private static; proposed, not emitted',
     'contract': 'Validate an admitted logical name against the SAME actual installed native route owner before Java cache use/wait. Unknown or unavailable owner throws; no boolean, prefix grant, public setter or Binder substitution.'},
    {'signature': 'coldSeed(Ljava/util/Map;)Ljava/util/Map;',
     'access': 'package-private static; proposed, not emitted',
     'contract': 'Cold-only profile: preserve null failure and original cache-empty guard, return a newly owned empty Map instead of importing supplied Binder seeds. No cache clear, warm adoption or renamed host Binder. Required seeded names must be genuinely resolvable before startup.'},
    {'signature': 'logicalNotificationName(Ljava/lang/String;)Ljava/lang/String;',
     'access': 'package-private static; proposed, not emitted',
     'contract': 'Recipient-decode variant only: inverse one physical name using the SAME native route owner; preserve exact original callback Binder and incoming thread/identity. Must not run after an already-inverting native callback wrapper.'},
]
WIRE_TREATMENT = {
    1: 'Native sole forward name mapping; original returned Binder unchanged.',
    2: 'Native sole forward name mapping; original Service/metadata union unchanged.',
    3: 'Native sole forward name mapping; original returned Binder unchanged.',
    4: 'Native sole forward name mapping; original Service/metadata union unchanged.',
    5: 'Native sole publication-name mapping; original Binder/allowIsolated/dump flags and server policy unchanged.',
    6: 'Native view projects names from genuine results; flags, relative order and collision refusal explicit; no invented entries.',
    7: 'Translate subscription name once. Prefer original callback Binder plus recipient decode; generic remote forwarding cannot preserve kernel caller identity.',
    8: 'Existing ServiceManagerProxy explicitly throws RemoteException. Preserve that failure; generated route existence is not removal/drain acknowledgement.',
    9: 'Genuine declaration result for selected physical endpoint only; aliases do not manufacture VINTF declarations.',
    10: 'Interface/instance query requires exact manifest-aware projection; never prefix an opaque interface argument.',
    11: 'Actual APEX declaration result must remain genuine; endpoint argument mapping requires native semantic contract.',
    12: 'Opaque APEX/query argument is not blanket service-name input; exact native semantic/projection contract required.',
    13: 'Preserve genuine ConnectionInfo payload; endpoint mapping requires native semantic contract, no fabricated address.',
    14: 'Existing ServiceManagerProxy explicitly throws RemoteException; no fake client registration or callback.',
    15: 'Existing ServiceManagerProxy explicitly throws RemoteException; no fabricated unregister success.',
    16: 'Native projection of genuine typed debug rows; exact name-field construction/copy contract required, no guessed Parcelable layout.',
    17: 'BLOCKED alias rewrite: CallerContext and both String positions stay untouched until actual native positional semantics are proved. No caller reconstruction or permission grant.',
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


def is_reparse(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & REPARSE_POINT)


def directory_identity(path):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not is_reparse(info), f'plain directory required: {path}')
    return info.st_dev, info.st_ino


def input_path(name):
    path = Path(name)
    require(path.parts and not path.is_absolute() and not path.drive and not path.root
            and '..' not in path.parts and not any(':' in part for part in path.parts)
            and '/'.join(path.parts) == name,
            f'canonical repository input path required: {name}')
    directory = ROOT
    for part in path.parts[:-1]:
        directory /= part
        directory_identity(directory)
    return ROOT / path


def file_identity(info):
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns


def capture_input(name):
    path = input_path(name)
    named = path.lstat()
    require(stat.S_ISREG(named.st_mode) and not is_reparse(named)
            and 0 < named.st_size <= MAX_INPUT_BYTES, f'bounded regular input required: {name}')
    identity = file_identity(named)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        require(file_identity(opened) == identity, f'input changed at open: {name}')
        raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(stream.fileno())
        require(len(raw) == named.st_size and file_identity(after) == identity
                and after.st_ctime_ns == opened.st_ctime_ns,
                f'input changed while reading: {name}')
    final = path.lstat()
    require(not is_reparse(final) and file_identity(final) == identity
            and final.st_ctime_ns == named.st_ctime_ns, f'input changed after read: {name}')
    # MSYS Python reports different ctime values for these two APIs. Retain
    # both independent witnesses across reads instead of equating them.
    return raw, (identity, named.st_ctime_ns, opened.st_ctime_ns)


def output_path(name):
    path = Path(name)
    require(not path.is_absolute() and not path.drive and not path.root and path.parent == OUTPUT_PARENT,
            f'choose a new JSON file directly under {OUTPUT_PARENT.as_posix()}')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}\.json', path.name)
            and not re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', path.name.split('.')[0], re.IGNORECASE),
            'plain JSON output filename required')
    return ROOT / path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New JSON file under out/guest-service-namespace-preparation')
    args = parser.parse_args()
    output = output_path(args.output)
    output_parents = [ROOT, ROOT / 'out', output.parent]
    parent_identities = [directory_identity(path) for path in output_parents]
    pins = {}
    checks = []
    captured = {}
    source_bytes, source_identity = capture_input(SOURCE_NAME)

    def pin(name, expected):
        if name not in captured:
            captured[name] = capture_input(name)
        raw, _ = captured[name]
        require(sha(raw) == expected, f'pin mismatch: {name}')
        pins[name] = {'sha256': expected, 'bytes': len(raw)}
        checks.append('pin ' + name)
        return raw

    data = parse_json(pin(CARD, CARD_SHA))
    pin(FREEZE, FREEZE_SHA)
    for name, expected in NATIVE_PINS.items():
        pin(name, expected)
    native = parse_json(captured['inventory/guest-native-service-manager.json'][0])
    for name, expected in native['files'].items():
        pin(name, expected)
    for record in native['nativeInputs'].values():
        pin(record['raw'], record['rawSha256'])
    require(native['code17StringSemanticsClosed'] is False and native['rawHandleZeroPhysical'] is True,
            'native boundary differs')
    require(native['patches'] == 0 and native['oemExecutions'] == 0, 'native proof scope differs')
    methods = {}
    proofs = []
    query_roles = set()
    for label in LABELS:
        q = data['queries'][label]
        for role in ('receipt', 'raw'):
            name = q[role]
            require(name not in query_roles, f'ambiguous query role: {name}')
            query_roles.add(name)
        receipt = parse_json(pin(q['receipt'], q['receiptSha256']))
        raw = pin(q['raw'], q['rawSha256'])
        require(receipt['readerExitCode'] == 0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] is True,
                f'unverified reader receipt: {label}')
        require(receipt['archiveSha256'] == q['archiveSha256'] and receipt['oemCodeExecuted'] is False,
                f'archive or execution scope differs: {label}')
        require(receipt['raw'] == q['raw'] and receipt['rawSha256'] == q['rawSha256']
                and receipt['rawBytes'] == len(raw) and receipt['androidExecuted'] is False,
                f'raw receipt binding differs: {label}')
        by_key = {(x['owner'], x['signature']): x for x in receipt['selectedMethodProofs']}
        require(len(by_key) == len(receipt['selectedMethodProofs']), f'duplicate method proof: {label}')
        for row in map(parse_json, raw.splitlines()):
            if row['record'] != 'method':
                continue
            b = row['body']
            proof = by_key.pop((b['owner'], b['signature']))
            require(proof['normalizedBodySha256'] == row['normalizedBodySha256'], f'body pin differs: {label}')
            require(proof['physicalDex'] == row['physicalDex'] and proof['logicalHeaderOffset'] == row['logicalHeaderOffset'],
                    f'logical DEX placement differs: {label}')
            require((label, b['signature']) not in methods, f'ambiguous method signature: {label}')
            methods[(label, b['signature'])] = b
            proofs.append(dict(proof, label=label, receipt=q['receipt'], raw=q['raw'], rawSha256=q['rawSha256']))
        require(not by_key, f'missing selected body: {label}')
    facades = [x for x in proofs if x['label'] == 'guest-sm']
    require(len(facades) == 19, 'expected 19 original facade declarations')
    wire = data['generatedIServiceManagerWireTable']
    require(sorted(x['code'] for x in wire) == list(range(1, 18)), 'unexpected wire table')
    require(all(x['flags'] == 0 for x in wire), 'unexpected wire flags')
    cuts = []

    def site(label, signature, pc, target, proposal):
        b = methods[(label, signature)]
        i, = [i for i in b['instructions'] if i['pc'] == pc]
        require(i.get('reference') == target, f'cut reference differs: {label}:{signature}@{pc}')
        cuts.append({'owner': b['owner'], 'signature': signature, 'pcCodeUnits': pc,
                     'originalReference': target, 'proposal': proposal})
        checks.append('site ' + label + ':' + signature + '@' + str(pc))

    for signature in ['getService(Ljava/lang/String;)Landroid/os/IBinder;', 'checkService(Ljava/lang/String;)Landroid/os/IBinder;']:
        site('guest-sm', signature, 0, SM + '->sCache:Ljava/util/Map;',
             'Insert requireLogicalName before this cache access; retain logical key and original hit/miss/exception behavior for admitted names. Native owner alone maps misses.')
    site('guest-sm', 'waitForService(Ljava/lang/String;)Landroid/os/IBinder;', 0,
         SM + '->waitForServiceNative(Ljava/lang/String;)Landroid/os/IBinder;',
         'Validate logical name only; retain JNI wait and native sole translation, no Java physical-name rewrite.')
    site('guest-sm', 'initServiceCache(Ljava/util/Map;)V', 10,
         'Ljava/util/Map;->putAll(Ljava/util/Map;)V',
         'After original empty-cache check, coldSeed incoming Map before putAll; do not erase warm cache or import host Binder seeds.')
    site('guest-callback-stub', 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 29,
         'Landroid/os/Parcel;->enforceNoDataAvail()V',
         'Recipient-decode variant: AFTER original trailing-data check and BEFORE original onRegistration32, inverse the existing name register only. Same original callback Binder/thread/flags/payload Binder.')
    site('guest-callback-stub', 'onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z', 32,
         CB + '->onRegistration(Ljava/lang/String;Landroid/os/IBinder;)V',
         'Preserve original virtual dispatch and exact IBinder argument; no forwarding Binder wrapper.')
    site('guest-sm', 'getIServiceManager()Landroid/os/IServiceManager;', 15,
         'Landroid/os/ServiceManagerNative;->asInterface(Landroid/os/IBinder;)Landroid/os/IServiceManager;',
         'NO wrapper replacement: retain genuine factory/proxy; native owner must precede first acquisition/cache.')
    bind_signature, = [s for label, s in methods if label == 'guest-bind' and s.startswith('bindApplication(')]
    site('guest-bind', bind_signature, 49, SM + '->initServiceCache(Ljava/util/Map;)V',
         'Keep original input/call; cold seed policy runs in canonical guest ServiceManager. Source Map producer/required native resolvability still needs admission.')
    for signature in ['unregisterForNotifications(Ljava/lang/String;Landroid/os/IServiceCallback;)V',
                      'registerClientCallback(Ljava/lang/String;Landroid/os/IBinder;Landroid/os/IClientCallback;)V',
                      'tryUnregisterService(Ljava/lang/String;Landroid/os/IBinder;)V']:
        body = methods[('guest-proxy', signature)]
        require(body['instructions'][0]['reference'] == 'Landroid/os/RemoteException;'
                and next(x for x in body['instructions'] if x['pc'] == 5)['opcode'] == 'THROW',
                f'unsupported original proxy method differs: {signature}')
        checks.append('preserved unsupported ' + signature)
    pins[SOURCE_NAME] = {'sha256': sha(source_bytes), 'bytes': len(source_bytes)}
    result = {
        'schema': 'guest-service-namespace-preparation/v1', 'status': 'SOURCE_API_PROPOSAL_ONLY',
        'selected': False, 'patchEmitted': False, 'implementationEmitted': False,
        'sourceArchives': data['archives'], 'pins': pins, 'staticChecks': checks,
        'guestServiceManagerDeclarations': facades, 'reusedMethodProofs': proofs,
        'proposedHelperOwner': HELPER, 'proposedJavaApi': API, 'exactCuts': cuts,
        'protocol17': [dict(x, integration=WIRE_TREATMENT[x['code']]) for x in sorted(wire, key=lambda x: x['code'])],
        'nativePairBoundary': {
            'status': 'FROZEN_PEER_SOURCE_PROOF_NOT_NATIVE_IMPLEMENTATION',
            'proof': 'inventory/guest-native-service-manager.json',
            'proposal': 'One actual in-process route adapter at physical os::IServiceManager delegate in BackendUnifiedServiceManager construction, installed before cache use. Preserve outer logical cache. Shared by Java native manager and C++ shim/native wait; no new Binder server or context.',
            'rawContextBinder': 'Remains physical; raw handle0/asBinder transactions and unadmitted native clients are not confined by Java policy.',
        },
        'callbackDecision': {
            'preferredJavaVariant': 'Original recipient Stub decode inverses once; original callback Binder passed to native manager unchanged.',
            'pairedNativeVariant': 'Same policy owner, inverse at ORIGINAL Cpp RegistrationWaiter/NDKNotificationRegistration receiver entries. No generic native forwarding wrapper. Unadmitted remote/manual recipients remain blocked.',
            'rootSelectionPending': True,
        },
        'coldOnlyConditions': [
            'Actual native route owner installed before any manager, native-wait or seed access; same immutable root-selected route/source profile as Java helper.',
            'New guest process/classloader generation; no migration or clearing of live cached handles.',
            'Every required omitted seeded endpoint genuinely resolvable through selected manager before application startup; empty seed is no availability proof.',
            'Actual admitted publisher/protocol/local-lifecycle owners for all routes; alias/profile text is naming, not authentication authority.',
            'Exactly one request/result translation layer and one callback inversion per selected path.',
        ],
        'remainingBindings': ['Complete root-selected endpoint table and original publisher suppression/replacement',
                              'Actual native implementation/installation and pair pin',
                              'Code17 two-String semantic roles and any blocked declaration/APEX/debug projections',
                              'Native/manual/direct-local callback recipients outside canonical guest Stub',
                              'Real callback registration/unregistration/death/uncertain-commit and process-lifetime retirement owner',
                              'Boot-visible helper/JNI registration and original-source DEX emission contract',
                              'Actual runtime endpoints, caller/user/security policy and device acceptance'],
        'execution': {'savedRecordsOnly': True, 'newReaderQueries': 0, 'oem': False, 'android': False, 'phone': False},
    }
    text = json.dumps(result, indent=2) + '\n'
    encoded = text.replace('\n', os.linesep).encode('utf-8')
    for name, original in captured.items():
        require(capture_input(name) == original, f'input changed before publication: {name}')
    require(capture_input(SOURCE_NAME) == (source_bytes, source_identity), 'producer changed before publication')
    require([directory_identity(path) for path in output_parents] == parent_identities,
            'output directory changed before publication')
    with output.open('xb') as stream:
        require(stream.write(encoded) == len(encoded), 'incomplete output write')
    require([directory_identity(path) for path in output_parents] == parent_identities,
            'output directory changed during publication')
    written, _ = capture_input(output.relative_to(ROOT).as_posix())
    require(written == encoded, 'output readback differs')
    print(json.dumps({'status': result['status'], 'facades': len(facades), 'protocolRoutes': len(wire),
                      'proposedCuts': len(cuts), 'proofs': len(proofs), 'sha256': sha(encoded)}))


if __name__ == '__main__':
    main()
