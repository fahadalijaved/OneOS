"""Static header-source audit plus an authored outer-framing model, not a decoder.

The model never runs Java serialization, Parcel, AppOps, StrictMode or OEM code.
Serialized bytes are opaque spans; accepted framing is not accepted native data.
"""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/guest-metrics-extended-headers'
PINS = {
 'guest-appops-writer': 'ba17b8f18d80c10bb211c84b8c1b79611e4cc89a992696a1d0c45f55e1c0ecfb',
 'guest-serial-writer': '1678e6d4482d060a5c5934b0f13e953292236083ce893bf958c12ed09efc2159',
 'guest-strictmode-writer': '77d497fd90256778a7ac07468977e2860a63f27d9dcad0a16876cec0f3ff22c7',
 'guest-violation-base': '3e8d20f1b0dbe4820a6b143dd8ee7b655b76157b514f815759bd537040e38e0c',
 'guest-violation-writer': 'd136f0375a1755a45c175de4b90ad120286cd93664fa5ec63208e6f75fbf4ca6',
 'samsung-appops-reader': 'e59855aac9a24844e4f72cd5740f5c8298d90e092bffe5896426dabbb2ffc319',
 'samsung-parcel-leaves': 'e9ebd17ee1fdc8774e315158434a9440791bed68715a0e65efd1b803ab187cc0',
 'samsung-parcel-object-ranges': '9d86893c75d40788cd4b4d70c434dceb2768bcdc88b9087c412d59ab180e7998',
 'samsung-parcel-transitive': 'dbe6db37c2bcb6d67c4a6fe98ba6930f72df0dddd1bd152a77fb21259f8413d8',
 'samsung-serial-resolver': '3378129340a972286c152344ac366ebbaf84e4eb3c1d3225f0b6ca5f9af8b116',
 'samsung-strictmode-reader': '4ea5e795926acc70c30cfde31ca44b5c489cbe36bd9c39f0113df7ef8eea24d8',
 'samsung-violation-base': 'a5ed8fbb80efe822c5c649fe6cbe259d2a6118afc116fc5e7a7ac1cf094262d1',
 'samsung-violation-reader': '1eabe9fa904557890d1b861115c0a0c3d2f1743a621ecc8432003423e885ae90',
}
FROZEN = {
 'compat/android/com/appleexploit/oneos/security/boot/PreparedGuestMetricsClient.java': 'afd99ebe98a09b209bb7f6a42d23c9d88313597f5d6760105def73213ea625d1',
 'compat/android/com/appleexploit/oneos/security/authority/PreparedGuestMetricsEndpoint.java': 'a3e01dc99c4a879640e55ac0416859abba12dea47cd447824e6e4f329d6466ed',
 'firmware/binder-direct-dispatch/20261105T174115595660Z-c05ae15d0b304064926f810047a3d569.jsonl': '94818e222d40b925851099cc5ee4f55e6e7648725cc149a0c7827894cbace559',
 'firmware/binder-direct-dispatch/20261105T174118129645Z-8e2a45528f5c47bf86408dc807a8e71e.jsonl': 'a36b0bdba36886ddff59d47421e1e0096683fb6c60e4ba79f8239b489878055c',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Cursor:
    """Synthetic ordinary-Parcel framing model; no native object table exists here."""
    def __init__(self, data, maximum):
        if not 4 <= len(data) <= maximum:
            raise ValueError('total bound')
        self.data, self.pos, self.limit = data, 0, len(data)
        self.serialized_spans = []

    def span(self, count):
        if count < 0 or count > self.limit - self.pos:
            raise ValueError('span bound')
        start = self.pos; self.pos += count
        return start

    def integer(self):
        return struct.unpack_from('<i', self.data, self.span(4))[0]

    def string16(self):
        size = self.integer()
        if size == -1:
            return False
        if size < 0 or self.limit - self.pos < 2 or size > (self.limit - self.pos - 2) // 2:
            raise ValueError('string bound')
        count = (2 * (size + 1) + 3) & ~3
        start = self.span(count)
        if self.data[start + 2 * size:start + 2 * size + 2] != b'\0\0':
            raise ValueError('string terminator')
        return True

    def count(self, minimum):
        count = self.integer()
        if count < 0 or count > (self.limit - self.pos) // minimum:
            raise ValueError('count bound')
        return count

    def header_start(self):
        start = self.pos; length = self.integer()
        if length < 8 or length % 4 or length > self.limit - start:
            raise ValueError('header length')
        old_limit = self.limit; self.limit = start + length
        return old_limit

    def header_end(self, old_limit):
        if self.pos != self.limit:
            raise ValueError('header exact end')
        self.limit = old_limit

    def appops(self):
        old_limit = self.header_start()
        for _ in range(self.count(28)):
            self.string16(); self.span(24)
        self.header_end(old_limit)

    def violation(self):
        if self.string16():
            size = self.integer()
            if size < 0:
                raise ValueError('serialized byte count')
            start = self.span((size + 3) & ~3)
            self.serialized_spans.append({'offset': start, 'bytes': size, 'contentsValidated': False})
        for _ in range(self.count(4)):
            for _ in range(self.count(16)):
                self.string16(); self.string16(); self.string16(); self.span(4)
        self.span(32)  # four ints and two longs, unchanged penalty/timing values
        self.string16()
        tags = self.integer()
        if tags < -1 or tags > (self.limit - self.pos) // 4:
            raise ValueError('tag count')
        for _ in range(max(tags, 0)):
            self.string16()

    def strictmode(self):
        old_limit = self.header_start()
        count = self.integer()
        if not 0 <= count <= 3:
            raise ValueError('source writer violation count')
        for _ in range(count):
            self.violation()
        self.header_end(old_limit)


def inspect_outer(data, display_id=7, maximum=4096):
    cursor = Cursor(data, maximum)
    code = cursor.integer(); appops = False; strict = False
    if code == -127:
        appops = True; cursor.appops(); code = cursor.integer()
        if code == -127:
            raise ValueError('repeated AppOps prefix')
    if code == -128:
        strict = True; cursor.strictmode(); success = True
    else:
        success = code == 0
    decoder_end = cursor.pos
    if not success:
        return {'kind': 'native-exception-must-throw', 'appops': appops,
                'nativeExceptionCode': code, 'framingIsNativeAcceptance': False}
    remaining = len(data) - cursor.pos
    if remaining not in (12, 32):
        raise ValueError('payload length')
    version, echo, status = cursor.integer(), cursor.integer(), cursor.integer()
    if version != 1 or echo != display_id or (status, remaining) not in [(0, 12), (1, 32)]:
        raise ValueError('v1 payload')
    if status == 1:
        cursor.span(20)
    if cursor.pos != len(data):
        raise ValueError('trailing data')
    return {'kind': 'outer-success-framing', 'appops': appops, 'strictmode': strict,
            'expectedRealDecoderEnd': decoder_end, 'serializedSpans': cursor.serialized_spans,
            'framingIsNativeAcceptance': False, 'requiresGenuineReaderAndSourceAdmission': True}


def modeled_probes():
    integer = lambda n: struct.pack('<i', n)
    def string(value):
        if value is None:
            return integer(-1)
        raw = value.encode('utf-16le') + b'\0\0'
        return integer(len(raw) // 2 - 1) + raw + b'\0' * (-len(raw) % 4)
    def header(tag, payload):
        return integer(tag) + integer(4 + len(payload)) + payload
    absent = integer(1) + integer(7) + integer(0)
    sample = integer(1) + integer(7) + integer(1) + struct.pack('<5i', -1, 0, 123, -2147483648, 2147483647)
    app = header(-127, integer(1) + string('tag') + bytes(24))
    empty_app = header(-127, integer(0))
    empty_strict = header(-128, integer(0))
    # Opaque placeholder, deliberately NOT a valid complete serialized Violation.
    violation = (string('fixture.Violation') + integer(4) + b'\xac\xed\0\x05' +
        integer(1) + integer(1) + string('fixture.Class') + string('method') + string(None) +
        integer(1) + bytes(32) + string(None) + integer(0))
    strict = header(-128, integer(1) + violation)
    positives = {'plainAbsent': integer(0) + absent, 'plainSample': integer(0) + sample,
        'appops': app + integer(0) + sample, 'emptyAppops': empty_app + integer(0) + absent,
        'strictOuter': strict + sample, 'emptyStrict': empty_strict + absent,
        'both': app + strict + sample, 'ordinaryException': integer(-1) + bytes(8),
        'appopsOrdinaryException': app + integer(-1) + bytes(8)}
    negatives = {'strictZeroLength': integer(-128) + integer(0) + absent,
        'strictNegativeLength': integer(-128) + integer(-4) + absent,
        'strictUnalignedLength': integer(-128) + integer(9) + integer(0) + absent,
        'strictOverrun': integer(-128) + integer(4096) + absent,
        'negativeViolationCount': header(-128, integer(-1)) + absent,
        'tooManyViolations': header(-128, integer(4)) + absent,
        'appopsZeroLength': integer(-127) + integer(0) + integer(0) + absent,
        'appopsNegativeCount': header(-127, integer(-1)) + integer(0) + absent,
        'appopsHugeCount': header(-127, integer(2147483647)) + integer(0) + absent,
        'appopsLengthMismatch': header(-127, integer(0) + integer(88)) + integer(0) + absent,
        'repeatedAppops': empty_app + empty_app + integer(0) + absent,
        'truncatedBitset': header(-127, integer(1) + string(None) + bytes(20)) + integer(0) + absent,
        'wrongVersion': integer(0) + integer(2) + absent[4:],
        'wrongEcho': integer(0) + integer(1) + integer(8) + integer(0),
        'trailingByte': integer(0) + absent + b'x',
        'absentWithSampleTail': integer(0) + absent + bytes(20),
        'sampleWithNoTail': integer(0) + integer(1) + integer(7) + integer(1),
        'badStringTerminator': header(-127, integer(1) + integer(1) + b'A\0X\0' + bytes(24)) + integer(0) + absent,
        'negativeStackCount': header(-128, integer(1) + string(None) + integer(-1) + bytes(32) + string(None) + integer(0)) + absent,
        'hugeFrameCount': header(-128, integer(1) + string(None) + integer(1) + integer(2147483647) + bytes(32) + string(None) + integer(0)) + absent,
        'negativeSerializedByteCount': header(-128, integer(1) + string('fixture.Violation') + integer(-1) + integer(0) + bytes(32) + string(None) + integer(0)) + absent,
        'hugeTagsCount': header(-128, integer(1) + string(None) + integer(0) + bytes(32) + string(None) + integer(2147483647)) + absent,
        'overCap': integer(0) + bytes(4096), 'shortHeader': b'\0\0\0'}
    results = []
    for name, data in positives.items():
        results.append({'case': name, 'expected': 'outer-framing-only', 'result': inspect_outer(data)})
    for name, data in negatives.items():
        try:
            inspect_outer(data)
        except ValueError:
            results.append({'case': name, 'expected': 'reject', 'rejected': True})
        else:
            raise ValueError('Malformed model accepted: ' + name)
    return {'pass': True, 'positiveOuterFramingCases': len(positives), 'negativeFramingCases': len(negatives),
            'serializedObjectsValidatedOrExecuted': False, 'nativeObjectsRepresented': False,
            'nativeStringEncodingProvedByModels': False, 'results': results}


def main():
    for path, pin in FROZEN.items():
        if sha(ROOT / path) != pin:
            raise ValueError('Frozen input drift ' + path)
    methods, proofs, declarations, archives = {}, {}, {}, {}
    receipt_pins = {}
    for label, pin in PINS.items():
        path = OUT / (label + '.json')
        if sha(path) != pin:
            raise ValueError('Receipt drift ' + label)
        receipt_pins[path.relative_to(ROOT).as_posix()] = pin
        receipt = json.loads(path.read_text())
        if receipt['readerExitCode'] or not receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] or sha(ROOT / receipt['raw']) != receipt['rawSha256']:
            raise ValueError('Static body receipt/raw')
        archives[receipt['archive']] = receipt['archiveSha256']
        for declaration in receipt['selectedClassDeclarations']:
            declarations[label + ':' + declaration['descriptor']] = declaration
        for line in (ROOT / receipt['raw']).read_text().splitlines():
            record = json.loads(line)
            if record['record'] != 'method':
                continue
            body = record['body']; key = label + ':' + body['owner'] + '->' + body['signature']
            methods[key] = body
            proofs[key] = {'bodySha256': record['normalizedBodySha256'], 'raw': receipt['raw'],
                'rawSha256': receipt['rawSha256'], 'physicalDex': record['physicalDex'], 'logicalHeaderOffset': record['logicalHeaderOffset']}
    for role, raw in [('samsung', next(p for p in FROZEN if '174115' in p)), ('guest', next(p for p in FROZEN if '174118' in p))]:
        selected = ['readException()V', 'readExceptionCode()I', 'readException(ILjava/lang/String;)V'] if role == 'samsung' else ['writeNoException()V']
        for line in (ROOT / raw).read_text().splitlines():
            record = json.loads(line)
            if record['record'] != 'method' or record['body']['signature'] not in selected:
                continue
            body = record['body']; key = role + '-parcel-envelope:' + body['owner'] + '->' + body['signature']
            methods[key] = body
            proofs[key] = {'bodySha256': record['normalizedBodySha256'], 'raw': raw,
                'rawSha256': FROZEN[raw], 'physicalDex': record['physicalDex'], 'logicalHeaderOffset': record['logicalHeaderOffset']}
    for path, pin in archives.items():
        if sha(path) != pin:
            raise ValueError('Archive changed')
    assertions = []
    def at(prefix, pc, **fields):
        keys = [k for k in methods if k.startswith(prefix)]
        if len(keys) != 1:
            raise ValueError('Method selector ' + prefix)
        ins = next(i for i in methods[keys[0]]['instructions'] if i['pc'] == pc)
        if any(ins.get(k) != v for k, v in fields.items()):
            raise ValueError('Source edge changed ' + keys[0] + ':' + str(pc))
        assertions.append({'method': keys[0], 'pc': pc, **fields})
    at('samsung-appops-reader:', 0, reference='Landroid/os/Parcel;->readInt()I')
    at('samsung-appops-reader:', 3, reference='Landroid/os/Parcel;->readInt()I')
    at('samsung-appops-reader:', 11, reference='Landroid/os/Parcel;->readString()Ljava/lang/String;')
    at('samsung-appops-reader:', 15, literal=3)
    at('samsung-appops-reader:', 21, reference='Landroid/os/Parcel;->readLong()J')
    for pc in [60, 122]:
        at('samsung-appops-reader:', pc, reference='Landroid/app/AppOpsManager$OnOpNotedCallback;->onNoted(Landroid/app/SyncNotedAppOp;)V')
    for pc, fields in [(11, {'literal': -127}), (28, {'reference': 'Landroid/os/Parcel;->writeInt(I)V'}), (54, {'literal': 3}), (84, {'opcode': 'SUB_INT', 'registers': [4, 3, 1]})]:
        at('guest-appops-writer:', pc, **fields)
    for pc, fields in [(19, {'reference': 'Landroid/os/Parcel;->readInt()I'}), (29, {'reference': 'Landroid/os/StrictMode$ViolationInfo;-><init>(Landroid/os/Parcel;Z)V'}), (32, {'reference': 'Landroid/os/StrictMode$ViolationInfo;->addLocalStack(Ljava/lang/Throwable;)V'}), (45, {'reference': 'Landroid/os/StrictMode$AndroidBlockGuardPolicy;->handleViolationWithTimingAttempt(Landroid/os/StrictMode$ViolationInfo;)V'})]:
        at('samsung-strictmode-reader:', pc, **fields)
    at('guest-strictmode-writer:', 19, literal=3)
    at('guest-strictmode-writer:', 20, reference='Ljava/lang/Math;->min(II)I')
    at('guest-strictmode-writer:', 36, reference='Landroid/os/StrictMode$ViolationInfo;->writeToParcel(Landroid/os/Parcel;I)V')
    at('samsung-violation-reader:', 28, reference='Landroid/os/Parcel;->readSerializable(Ljava/lang/ClassLoader;Ljava/lang/Class;)Ljava/lang/Object;')
    at('samsung-violation-reader:', 47, opcode='NEW_ARRAY', registers=[4, 3])
    at('samsung-violation-reader:', 137, reference='Landroid/os/Parcel;->readStringArray()[Ljava/lang/String;')
    at('guest-violation-writer:', 2, reference='Landroid/os/Parcel;->writeSerializable(Ljava/io/Serializable;)V')
    serial = 'samsung-parcel-transitive:Landroid/os/Parcel;->readSerializableInternal('
    at(serial, 21, reference='Ljava/lang/Class;->forName(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;')
    at(serial, 71, reference='Landroid/os/Parcel;->createByteArray()[B')
    at(serial, 85, reference='Ljava/io/ObjectInputStream;->readObject()Ljava/lang/Object;')
    at('samsung-serial-resolver:Landroid/os/Parcel$2;->resolveClass(', 11, reference='Ljava/lang/Class;->forName(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;')
    for name, method in [('hasBinders()Z', 'nativeHasBinders(J)Z'), ('hasFileDescriptors()Z', 'nativeHasFileDescriptors(J)Z'), ('marshall()[B', 'nativeMarshall(J)[B')]:
        at('samsung-parcel-transitive:Landroid/os/Parcel;->' + name, 2, reference='Landroid/os/Parcel;->' + method)
    for name, method in [('hasBinders(II)Z', 'nativeHasBindersInRange(JII)Z'), ('hasFileDescriptors(II)Z', 'nativeHasFileDescriptorsInRange(JII)Z')]:
        at('samsung-parcel-object-ranges:Landroid/os/Parcel;->' + name, 2, reference='Landroid/os/Parcel;->' + method)
    at('samsung-parcel-leaves:Landroid/os/Parcel;->readString16(', 2, reference='Landroid/os/Parcel$ReadWriteHelper;->readString16(Landroid/os/Parcel;)Ljava/lang/String;')
    for pc, fields in [(15, {'literal': -128}), (29, {'reference': 'Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I'}), (36, {'literal': 0})]:
        at('samsung-parcel-envelope:Landroid/os/Parcel;->readExceptionCode(', pc, **fields)
    guest_base = declarations['guest-violation-base:Landroid/os/strictmode/Violation;']
    samsung_base = declarations['samsung-violation-base:Landroid/os/strictmode/Violation;']
    shape_keys = ['descriptor', 'accessFlags', 'superclass', 'interfaces', 'methods', 'fields']
    base_shape = {k: guest_base[k] for k in shape_keys}
    if base_shape != {k: samsung_base[k] for k in shape_keys}:
        raise ValueError('Base Violation declaration compatibility changed')
    probes = modeled_probes()
    result = {'schema': 'guest-metrics-extended-headers/v1', 'status': 'SOURCE_PROPOSAL_NO_PRODUCTION_SUCCESSOR',
        'selected': False, 'frozenPlainClientChanged': False, 'sourcePins': {**FROZEN, **receipt_pins},
        'sourceArchives': archives, 'bodyProofs': proofs, 'sourceBodyCount': len(methods), 'sourceAssertions': assertions,
        'violationBaseDeclarationComparison': {'sameShape': True, 'shape': base_shape,
            'concreteSubclassOrThrowableGraphCompatibilityProved': False, 'numericSerialUidComputedOrOemDeserializationExecuted': False},
        'model': probes,
        'recommendation': 'Use actual admitted Samsung Parcel.readException once after strict outer preflight; do not rewrite Java serialization or disable/strip policy. Original trusted source/reader contract is the same kind used by AIDL, not arbitrary endpoint attestation.',
        'preflight': ['Bound complete original owned reply before parsing; no normalization or native header rewriting.',
            'Source writer emits no Binder/FD objects in these metadata headers; use genuine native hasBinders/hasFileDescriptors range checks over inspected header and successful scalar regions, and a matching canonical fresh Parcel/string helper. Prefer an owned-Parcel primitive walk; whole-packet marshall is optional only for an object-free packet and must not strip error-tail sidecars.',
            'At most one AppOps−127 prefix, exact positive aligned size including sizefield, nonnegative count, nullable String16 plus exactly three longwords each, exact declared header end.',
            'Then ordinary exception code, plain0, or StrictMode−128; reject repeated/out-of-order prefixes, zero/negative/misaligned/overrun lengths before effects.',
            'StrictMode positive exact size includes sizefield; source writer count0..3; walk Serializable class-string plus opaque bytearray span, bounded stack/frame vectors, fourints/twolongs/actionstring/tagstringarray; no ObjectInputStream in preflight.',
            'For success validate whole exact v1 metrics payload before genuine decoder, record expected native decoder end, then reset only original owned reply and invoke original readException exactly once.',
            'On original decoder success require expected position/exact remaining payload and version/echo/status again; on exception propagate unchanged. A nonzero ordinary exception reader returning normally is an error, never ABSENT.',
            'Keep endpoint/source lifetime through callbacks/policy work and recheck actual consumer epoch before Snapshot use; no lock across genuine effectful reader.'],
        'trustedReaderAndNativeLimits': ['Opaque Serializable bytes are decoded only by the actual original Parcel/ObjectInputStream and original Violation class loader; outer preflight is not serialized graph validation or an allocation bound.',
            'Selected base Violation has matching field/method declaration shape across inputs. Runtime class name comes from actual serialized object; original resolver/readObject/type/stream errors remain real. Use the admitted genuine writer/real platform reader trust contract as AIDL does; encountered incompatibility needs targeted source/runtime evidence, not an up-front whole-class graph rewrite or whole-platform allocation proof.',
            'AppOps reader invokes original OnOpNotedCallback and collector; StrictMode adds local stack and executes real current thread policy handling. These are real effects, permitted only once after structural preflight; exceptions/death are not swallowed.',
            'marshall bytes alone cannot prove absence of native Binder/FD sidecars. hasBinders/hasFileDescriptors/marshall/createByteArray are native-backed; selected Java proofs do not establish native object table/encoding implementation or runtime identity.',
            'A finite reply cap is a reviewed profile/resource contract; current4096 cap is not a source bound on every genuine serialized violation. Source writers have variable strings/object bytes. Select/validate the successor cap explicitly without claiming all legal native replies fit.'],
        'requiredOpenGates': ['Root review of exact successor parser/API/size profile before production changes', 'Actual canonical native object predicates/string framing/helper and original real reader/source/epoch ownership', 'Encountered genuine donor/Samsung violation-stream compatibility and decoder policy effects under actual configuration', 'Independent malformed/prefix/length/count/decode-position/error/reentry/native-sidecar fixtures and eventual native Binder acceptance'],
        'verification': {'pass': True, 'oemExecuted': False, 'sdkOrAndroidExecuted': False, 'phoneActions': [], 'sourceOnly': True, 'toolSha256': sha(__file__)}}
    destination = ROOT / 'inventory/guest-metrics-extended-headers.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    summary = {'pass': True, 'sourceBodies': len(methods), 'sourceAssertions': len(assertions),
        'positiveOuterFramingCases': probes['positiveOuterFramingCases'], 'negativeFramingCases': probes['negativeFramingCases'],
        'productionChanged': False, 'inventorySha256': sha(destination), 'toolSha256': sha(__file__)}
    (OUT / 'validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
