"""Source-only admission/proposal for one Samsung permission supplier retarget.

Reads original DEX and frozen proofs. Does not create a patched archive, compile,
load OEM classes, bind a service, or execute cache/native/Android operations.
"""
import hashlib
import json
import struct
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/permission-query-retarget'
ARCHIVE = ROOT / '../firmware/samsung/framework.jar'
ARCHIVE_SHA = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
OWNER = 'Landroid/permission/PermissionManager;'
METHOD = 'checkPermissionUncached(Ljava/lang/String;III)I'
ORIGINAL = 'Landroid/app/ActivityManager;->getService()Landroid/app/IActivityManager;'
PROPOSED = 'Lcom/appleexploit/oneos/security/boot/PermissionQueryBinding;->get()Landroid/app/IActivityManager;'
PINS = {
    'inventory/authority-permission-binding.json': 'be782a7a9c3357b77d59faa64bb541673dc9c7ad7dd395563fb134f7d4030bc9',
    'compat/android/com/appleexploit/oneos/security/authority/PreparedSamsungPermissionBridge.java': '8b601fa599b211df79f360d086014d47d49a307f663ff8abbb1a7ee33316534c',
    'out/authority-permission-binding/samsung-permission-checks.json': '467b1e3fe1b722e865272260af5b92cb5b942ffe89205d25e9c7d49bf87e4e35',
    'out/authority-permission-binding/samsung-permission-recompute.json': '810aa31e07f2e0a87f1bde2b2d13d02e4d76e57ca7e12b7f196a6f0d26d8bfcc',
    'out/authority-permission-binding/samsung-activity-service.json': '167919e89a8a45499bf6efea5c1ed7e08d842f72711b35b9f9887f9152ba0ed4',
    'out/authority-permission-binding/samsung-am-stub.json': '046125956771f65609baabe19acf18b5eeac2e5518336dafe261b4767683abde',
    'out/permission-query-retarget/uncached-callers.json': '101ebf875a302c079bddfd884c4da821f045dbdda0950ba7d7e9d789a77f0ee7',
    'out/permission-query-retarget/uncached-nest.json': '778cffca411c3625fa6f038f9014300da160cbeb262ebab267ca57a9888e0da4',
    'out/permission-query-retarget/samsung-am-interface.json': '7f94813ce256d9c07fba13c4faf6971632fe1abdf86d43798b880632b7ff098e',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def uleb(data, offset):
    value = 0
    for shift in range(0, 35, 7):
        item = data[offset]
        offset += 1
        if shift == 28 and item > 15:
            raise ValueError('ULEB overflow')
        value |= (item & 127) << shift
        if item < 128:
            return value, offset
    raise ValueError('ULEB termination')


def locate(data):
    if data[:8] != b'dex\n039\0' or u32(data, 32) != len(data) or u32(data, 36) != 112 or u32(data, 40) != 0x12345678:
        raise ValueError('Exact ordinary DEX039 required; no 041 fallback')
    if hashlib.sha1(data[32:]).digest() != data[12:32] or zlib.adler32(data[12:]) & 0xffffffff != u32(data, 8):
        raise ValueError('Original DEX signature/checksum')
    sizes = [u32(data, off) for off in (56, 64, 72, 80, 88, 96)]
    offsets = [u32(data, off) for off in (60, 68, 76, 84, 92, 100)]
    for count, offset, width in zip(sizes, offsets, (4, 4, 12, 8, 8, 32)):
        if count > 2000000 or offset < 112 or offset + count * width > len(data):
            raise ValueError('DEX table bound')
    strings, types, protos, _, method_ids, classes = offsets

    def string(index):
        if index >= sizes[0]:
            raise ValueError('String index')
        _, start = uleb(data, u32(data, strings + index * 4))
        end = data.find(b'\0', start, min(len(data), start + 1048576))
        if end < 0:
            raise ValueError('String bound')
        return data[start:end]

    def typ(index):
        if index >= sizes[1]:
            raise ValueError('Type index')
        return string(u32(data, types + index * 4))

    def method(index):
        if index >= sizes[4]:
            raise ValueError('Method index')
        owner, proto, name = struct.unpack_from('<HHI', data, method_ids + index * 8)
        if proto >= sizes[2]:
            raise ValueError('Proto index')
        result, params = struct.unpack_from('<II', data, protos + proto * 12 + 4)
        args = []
        if params:
            count = u32(data, params)
            if count > 65535 or params + 4 + 2 * count > len(data):
                raise ValueError('Proto parameters')
            args = [typ(struct.unpack_from('<H', data, params + 4 + 2 * n)[0]) for n in range(count)]
        return typ(owner) + b'->' + string(name) + b'(' + b''.join(args) + b')' + typ(result)

    references = [method(index) for index in range(sizes[4])]
    expected = (OWNER + '->' + METHOD).encode('ascii')
    found = []
    for index in range(sizes[5]):
        row = classes + index * 32
        if typ(u32(data, row)) != OWNER.encode('ascii'):
            continue
        cursor = u32(data, row + 24)
        counts = []
        for _ in range(4):
            count, cursor = uleb(data, cursor)
            counts.append(count)
        if sum(counts) > 100000:
            raise ValueError('Class data bound')
        for count in counts[:2]:
            for _ in range(count):
                _, cursor = uleb(data, cursor)
                _, cursor = uleb(data, cursor)
        for count in counts[2:]:
            method_index = 0
            for _ in range(count):
                delta, cursor = uleb(data, cursor)
                method_index += delta
                access, cursor = uleb(data, cursor)
                code, cursor = uleb(data, cursor)
                if references[method_index] == expected:
                    found.append((method_index, access, code))
    if len(found) != 1:
        raise ValueError('Unique original encoded method')
    index, access, code = found[0]
    registers, incoming, outgoing, tries, debug, units = struct.unpack_from('<HHHHII', data, code)
    start = code + 16
    first, method_ref, third = struct.unpack_from('<HHH', data, start)
    if (access, registers, incoming, outgoing, tries, units, first, third) != (10, 6, 4, 5, 1, 49, 0x71, 0):
        raise ValueError('Exact original code/invoke shape')
    if references[method_ref] != ORIGINAL.encode('ascii'):
        raise ValueError('Actual source method reference')
    return {'dexVersion': '039', 'physicalDex': 'classes3.dex', 'methodId': index,
            'codeOffset': code, 'instructionsOffset': start, 'instructionUnits': units,
            'sourceInstructionByteRange': [start, start + 6], 'sourceInstructionSha256': sha(data[start:start + 6]),
            'registers': registers, 'incomingWords': incoming, 'outgoingWords': outgoing,
            'tryItems': tries, 'debugInfoOffset': debug, 'sourceMethodRefId': method_ref,
            'methodIds': sizes[4], 'methodIdsBelow65536': sizes[4] < 65536,
            'proposedReferenceAlreadyPresent': PROPOSED.encode('ascii') in references,
            'proposedOwnerTypeAlreadyPresent': PROPOSED.split('->')[0].encode('ascii') in [typ(i) for i in range(sizes[1])],
            'originalDexSha256': sha(data), 'originalDexIntegrityVerified': True}


def main():
    for path, expected in PINS.items():
        if digest(ROOT / path) != expected:
            raise ValueError('Frozen evidence drift: ' + path)
    if digest(ARCHIVE) != ARCHIVE_SHA:
        raise ValueError('Original archive drift')
    methods, proofs, reference_rows, declarations = {}, {}, [], {}
    for path in PINS:
        if not path.startswith('out/'):
            continue
        receipt = json.loads((ROOT / path).read_text())
        if receipt['archiveSha256'] != ARCHIVE_SHA or receipt['readerExitCode'] or not receipt['archiveAndToolPinsVerifiedBeforeAndAfter']:
            raise ValueError('Static reader receipt')
        if digest(ROOT / receipt['raw']) != receipt['rawSha256']:
            raise ValueError('Raw proof drift')
        for declaration in receipt['selectedClassDeclarations']:
            declarations[declaration['descriptor']] = declaration
        for line in (ROOT / receipt['raw']).read_text().splitlines():
            record = json.loads(line)
            if record['record'] == 'reference':
                reference_rows.append(record)
            if record['record'] != 'method':
                continue
            body = record['body']
            key = body['owner'] + '->' + body['signature']
            methods[key] = body
            proofs[key] = {'normalizedBodySha256': record['normalizedBodySha256'], 'raw': receipt['raw'],
                           'rawSha256': receipt['rawSha256'], 'physicalDex': record['physicalDex']}
    target = methods[OWNER + '->' + METHOD]
    if proofs[OWNER + '->' + METHOD]['normalizedBodySha256'] != '9337df69165b01e95e5f834e89cd4cc4ed9abc86008f20493d0aa5aab63877fe':
        raise ValueError('Exact target body')
    if target['instructions'][0] != {'pc': 0, 'opcode': 'INVOKE_STATIC', 'codeUnits': 3, 'registers': [], 'referenceKind': 'method', 'reference': ORIGINAL}:
        raise ValueError('Exact retarget instruction')
    if target['catches'] != [{'startPc': 36, 'codeUnits': 6, 'exceptionType': 'Landroid/os/RemoteException;', 'handlerPc': 43}]:
        raise ValueError('Original exception region')
    if len(reference_rows) != 1 or reference_rows[0]['caller'] != OWNER + '->-$$Nest$sm' + METHOD:
        raise ValueError('Bounded direct-caller xref')
    visibility = []
    for owner, flags, signature, method_flags in [
            ('Landroid/app/ActivityManager;', 1, 'getService()Landroid/app/IActivityManager;', 9),
            ('Landroid/app/IActivityManager$Stub;', 1025, 'asInterface(Landroid/os/IBinder;)Landroid/app/IActivityManager;', 9),
            ('Landroid/app/IActivityManager;', 1537, 'checkPermissionForDevice(Ljava/lang/String;III)I', 1025)]:
        declaration = declarations[owner]
        method = next(m for m in declaration['methods'] if m['signature'] == signature)
        if declaration['accessFlags'] != flags or method['accessFlags'] != method_flags:
            raise ValueError('Original API visibility changed')
        visibility.append({'owner': owner, 'classAccessFlags': flags, 'method': signature, 'methodAccessFlags': method_flags})
    with zipfile.ZipFile(ARCHIVE) as archive:
        dex = archive.read('classes3.dex')
        dex_names = [name for name in archive.namelist() if name.endswith('.dex')]
    site = locate(dex)
    if site['proposedReferenceAlreadyPresent'] or site['proposedOwnerTypeAlreadyPresent']:
        raise ValueError('Expected new helper reference/owner absent')
    output = {'schema': 'permission-query-retarget/v1', 'status': 'SOURCE_ONLY_API_AND_REWRITE_PROPOSAL',
        'selected': False, 'coldStartOnly': True, 'runtimeCodeAdded': False, 'binaryProduced': False,
        'sourceArchive': str(ARCHIVE.resolve()), 'sourceArchiveSha256': ARCHIVE_SHA,
        'sourcePins': PINS, 'sourceMethod': OWNER + '->' + METHOD, 'sourceMethodBodySha256': proofs[OWNER + '->' + METHOD]['normalizedBodySha256'],
        'sourceDexNames': dex_names, 'sourceBodyProofs': proofs, 'site': site,
        'originalApiVisibility': visibility,
        'directCallerXref': reference_rows, 'xrefScope': 'Exact direct target reference in this captured framework only; not reflection, other archives or installed-image reachability',
        'candidateEdit': {'pc': 0, 'originalReference': ORIGINAL, 'proposedReference': PROPOSED,
            'opcode': 'INVOKE_STATIC', 'registers': [], 'codeUnits': 3, 'moveResultObjectPc': 3,
            'requiresNewDexReferenceTables': True, 'instructionWidthAloneProvesValidArtifact': False,
            'tryCoversNewGetter': False, 'unreadyBehavior': 'Proposed get throws IllegalStateException outside original RemoteException try; no null/default service or readiness claim'},
        'proposedHelper': {'descriptor': PROPOSED.split('->')[0], 'classAccess': 'public final',
            'methods': ['public static void bindOnce(android.os.IBinder)', 'public static android.app.IActivityManager get()'],
            'privateState': 'Private constructor and retained same-Samsung-realm IActivityManager; UNBOUND/BINDING/BOUND/FAILED one-shot state, no reset or rebind',
            'bind': 'Cold bootstrap only, nonnull exact sourceProtocolBinder from separately admitted frozen PreparedSamsungPermissionBridge; convert using same Samsung Stub.asInterface; conversion failure is terminal, publish BOUND only after complete success',
            'get': 'Constant bounded state read; return the retained exact typed view only when BOUND, otherwise throw; no callback/lookup/loading/allocation/policy on query path beyond exception construction when unready',
            'publicVisibilityReason': 'Original android.permission caller and app bootstrap are distinct packages/runtime loaders; private/package access cannot cross that boundary',
            'publicBindIsAuthorityAuthentication': False, 'arbitraryBinderOrDescriptorIsOwnerAttestation': False,
            'bridgeClassStaticDependency': False, 'globalActivityManagerMutation': False},
        'requiredSelectionConditions': [
            'Root reviews exact API and producer before implementation; this card is proposal only.',
            'Supply the helper before first source permission check through the actual dedicated-process BOOT loader; an app child class loader cannot satisfy a boot parent reference.',
            'Original PermissionManager, helper getter signature, Samsung IActivityManager/Stub/Proxy resolve the same actual admitted Samsung interface family; do not parent-delegate to a guest-protocol namesake.',
            'Any compile-only hidden-IActivityManager declarations must match original descriptors and remain excluded from produced helper DEX; never duplicate canonical Binder/IBinder/Parcel/IInterface.',
            'Bootstrap admits the exact frozen prepared bridge class/code/object and genuine current guest AM/state generation, then supplies its exact Binder; helper signature/public API/type/descriptor does not authenticate that owner.',
            'Perform original same-realm PermissionManager.disablePermissionCache under cold/quiesced ownership before any earlier in-flight or accepted permission decision; original appId0/1000 shortcuts remain and are not readiness.',
            'Keep real native original caller and feature caller/role/user/operation admission; no clearIdentity, hop, subject rewrite, copied permission table, fabricated grant or public arbitrary-subject service.',
            'Retain helper, bridge and real endpoint through actual original permission calls and nested work; stop admission and drain before process retirement. Returned references cannot be hot-revoked by clearing a field; no hot rebind is proposed.',
            'A future producer must add sorted reference tables and remap every affected index/offset safely, or present another reviewed lowering; same three-code-unit width does not establish byte-only patchability.',
            'Decode future output independently: only target PC0 changes symbolic call semantics; all other methods/fields/class definitions, instruction operands after symbolic normalization, branches/tries/payloads/debug contracts and non-DEX entries remain source-preserved, with exact inverse/roundtrip and DEX integrity.',
            'Bind/readiness is not cryptographic authentication or full authority bootstrap; actual Context/native/policy/state generation and lifecycle remain separate acceptance gates.'
        ],
        'limits': ['No helper implementation, patch, compilation, constructor/cache/native/Android/OEM execution or phone action.',
                   'No method reference or final code offset is invented for an unbuilt output. New reference tables and boot insertion remain unassembled.',
                   'Global ActivityManager singleton, other AM callers, public33 credential routes, corrected65-body permission card and prepared bridge remain unchanged.'],
        'audit': {'pass': True, 'sourceOnly': True, 'toolSha256': digest(__file__)}}
    OUT.mkdir(parents=True, exist_ok=True)
    destination = ROOT / 'inventory/permission-query-retarget.json'
    destination.write_text(json.dumps(output, indent=2) + '\n')
    result = {'pass': True, 'proposalOnly': True, 'binaryProduced': False, 'inventorySha256': digest(destination), 'toolSha256': digest(__file__), 'site': site}
    (OUT / 'audit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
