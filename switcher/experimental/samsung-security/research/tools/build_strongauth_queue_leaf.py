"""Build the approved, UNSELECTED cold ColorOS StrongAuth queue instruction leaf.

Offline authored parsing/byte transformation only. No OEM/Android execution.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'out/strongauth-queue-leaf'
RAW = ROOT / 'firmware/strongauth-queue-leaf'
SOURCE = ROOT.parent / 'firmware/donor/extracted/system/framework/framework.jar'
SOURCE_SHA = 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'
DEX = 'classes6.dex'
DEX_SHA = '47f3b688c6365610afce4f24a03e8f601c7f3f240f73bd03fabee384ab1110a4'
OWNER = 'Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker$1;'
METHOD = 'onStrongAuthRequiredChanged(II)V'
BODY = '83d55f01ac64a4c30023a9db3777fdb423d23033bf8473b32f3472912f86813c'
OLD_REF = 'Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker$H;->sendMessageAtFrontOfQueue(Landroid/os/Message;)Z'
NEW_REF = 'Landroid/os/Message;->sendToTarget()V'
ABSENT_REF = 'Landroid/os/Handler;->sendMessage(Landroid/os/Message;)Z'
HELPER_SHA = '9ff4731807dad9df99ba8468b17611bf21b03fd17d2db917d4ba204f67fab8a7'
CALLBACK_INVENTORY_SHA = '64b9203cd5821e8124ea3ed44e3df79935ce3dcdbfa454a4aea147c016af5b7b'
SOURCE_XREF = 'firmware/strongauth-queue-leaf/20261105T180611637770Z-e699893128b54374841e1a63e637c5f0.jsonl'
SOURCE_XREF_SHA = '269a55eb816bb39241d52e8d99fce591989c8396da0a9556e71724346e12261b'

from build_coloros_pin_metadata_leaf import header, seal, uleb, u16, u32, digest
from static_security_reader import _classes, _env, JDK, DEXLIB


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def layout(data):
    profile = header(data)
    def string(index):
        if index >= u32(data, 56):
            raise ValueError('String index')
        pos = u32(data, u32(data, 60) + 4 * index)
        _, pos = uleb(data, pos)
        end = data.find(b'\0', pos, min(len(data), pos + 1048576))
        if end < 0:
            raise ValueError('Bounded string terminator')
        return data[pos:end]

    def typename(index):
        if index >= u32(data, 64):
            raise ValueError('Type index')
        return string(u32(data, u32(data, 68) + 4 * index))

    def signature(index):
        owner, proto, name = struct.unpack_from('<HHI', data, u32(data, 92) + 8 * index)
        if proto >= u32(data, 72):
            raise ValueError('Prototype index')
        entry = u32(data, 76) + 12 * proto
        ret, params = u32(data, entry + 4), u32(data, entry + 8)
        args = []
        if params:
            count = u32(data, params)
            if count > 65535 or params + 4 + 2 * count > len(data):
                raise ValueError('Parameter extent')
            args = [typename(u16(data, params + 4 + 2 * n)) for n in range(count)]
        return (typename(owner) + b'->' + string(name) + b'(' + b''.join(args)
                + b')' + typename(ret)).decode('ascii')

    references = {}
    for index in range(u32(data, 88)):
        sig = signature(index)
        if sig in [OLD_REF, NEW_REF, ABSENT_REF]:
            if sig in references:
                raise ValueError('Duplicate selected method reference')
            references[sig] = index
    if references != {NEW_REF: 832, OLD_REF: 4283}:
        raise ValueError('Existing reference table changed')
    target, ranges, encoded = [], [], 0
    for n in range(u32(data, 96)):
        definition = u32(data, 100) + 32 * n
        owner, pos = u32(data, definition), u32(data, definition + 24)
        if not pos:
            continue
        counts = []
        for _ in range(4):
            count, pos = uleb(data, pos)
            counts.append(count)
        if sum(counts) > 2000000:
            raise ValueError('Encoded member bound')
        for count in counts[:2]:
            index = 0
            for _ in range(count):
                delta, pos = uleb(data, pos)
                index += delta
                _, pos = uleb(data, pos)
                if index >= u32(data, 80):
                    raise ValueError('Encoded field index')
        for count in counts[2:]:
            index = 0
            for _ in range(count):
                delta, pos = uleb(data, pos)
                index += delta
                access, pos = uleb(data, pos)
                code, pos = uleb(data, pos)
                encoded += 1
                if index >= u32(data, 88) or u16(data, u32(data, 92) + 8 * index) != owner:
                    raise ValueError('Encoded method owner/index')
                if not code:
                    continue
                if code % 4 or code + 16 > len(data):
                    raise ValueError('Code alignment/extent')
                units = u32(data, code + 12)
                start, end = code + 16, code + 16 + 2 * units
                if units > 10000000 or end > len(data):
                    raise ValueError('Instruction extent')
                ranges.append({'methodId': index, 'start': start, 'end': end})
                if typename(owner) == OWNER.encode() and signature(index) == OWNER + '->' + METHOD:
                    target.append({'methodId': index, 'codeOffset': code,
                                   'instructionsOffset': start, 'instructionUnits': units,
                                   'registers': u16(data, code), 'incomingWords': u16(data, code + 2),
                                   'outgoingWords': u16(data, code + 4), 'tryItems': u16(data, code + 6),
                                   'accessFlags': access})
    if len(target) != 1:
        raise ValueError('Ambiguous target definition')
    selected = target[0]
    if {k: selected[k] for k in ['instructionUnits', 'registers', 'incomingWords', 'outgoingWords', 'tryItems']} != {
            'instructionUnits': 21, 'registers': 5, 'incomingWords': 3, 'outgoingWords': 4, 'tryItems': 0}:
        raise ValueError('Target code shape changed')
    start, end = selected['instructionsOffset'], selected['instructionsOffset'] + 42
    overlap = [r for r in ranges if r['start'] < end and start < r['end']]
    if len(overlap) != 1 or overlap[0]['methodId'] != selected['methodId']:
        raise ValueError('Target code alias/overlap')
    return profile, references, selected, {'encodedMethods': encoded,
            'codeMethodRanges': len(ranges), 'targetOverlappingRanges': overlap}


def read_actual(archive, label, owner=OWNER, selected_methods=None):
    cache, pins = _classes()
    raw, err = RAW / (label + '.jsonl'), OUT / (label + '-reader.stderr.txt')
    command = [JDK / 'java.exe', '-Xmx2g', '-Duser.home=' + str(OUT / 'runtime-home'),
               '-Djava.io.tmpdir=' + str(OUT / 'tmp'), '-cp', str(cache) + os.pathsep + str(DEXLIB),
               'SecurityDexReader', archive, owner, '-',
               *(selected_methods or ['--ALL-DECLARED-METHODS--'])]
    before = digest(archive)
    with raw.open('wb') as output, err.open('wb') as errors:
        result = subprocess.run(list(map(str, command)), stdout=output, stderr=errors,
                                env=_env(), creationflags=subprocess.CREATE_NO_WINDOW, timeout=60)
    if result.returncode or raw.stat().st_size > 1048576 or digest(archive) != before:
        raise ValueError('Bounded actual-byte reader failed')
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    summary = next((r for r in rows if r['record'] == 'summary'), None)
    if summary is None:
        raise ValueError('Reader final summary absent')
    methods = {r['body']['signature']: r for r in rows if r['record'] == 'method'}
    declarations = [r for r in rows if r['record'] == 'class']
    return methods, declarations, {'raw': raw.relative_to(ROOT).as_posix(),
            'rawSha256': digest(raw), 'archiveSha256': before, 'readerExitCode': result.returncode,
            'tools': pins, 'summary': summary}


def prove_target_chain():
    handler, handler_decl, handler_read = read_actual(SOURCE, 'target-chain-handler', 'Landroid/os/Handler;', [
        'obtainMessage(III)Landroid/os/Message;', 'sendMessage(Landroid/os/Message;)Z'])
    message, _, message_read = read_actual(SOURCE, 'target-chain-message', 'Landroid/os/Message;', [
        'obtain(Landroid/os/Handler;III)Landroid/os/Message;', 'sendToTarget()V'])
    accessor_signature = '-$$Nest$fgetmHandler(Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker;)Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker$H;'
    accessor, tracker_decl, tracker_read = read_actual(SOURCE, 'target-chain-tracker',
        'Lcom/android/internal/widget/LockPatternUtils$StrongAuthTracker;', [accessor_signature])
    expected = [
        (handler, 'obtainMessage(III)Landroid/os/Message;', '38947f99eb770becca450087ed9ad4d3a07db9293904e8f60c6d45c315475caa'),
        (handler, 'sendMessage(Landroid/os/Message;)Z', '47ab4403c9a63eca9bfad0ec030172e0f657d01a3580e934bea048272f43c486'),
        (message, 'obtain(Landroid/os/Handler;III)Landroid/os/Message;', 'ac0e961d550a025edb3abcb487264d93a7eecf3cf374cb2b810d219a396b2f9d'),
        (message, 'sendToTarget()V', '52da144089e06f170208b309dd4e73e7ce2cfcbdc4d565a1844b96659b1a452e'),
        (accessor, accessor_signature, '251abd6281af1b3cf680337c4f04414a718feb4146813ec7a4383c711de09f5f')]
    selected_proofs = []
    for methods, signature, expected_hash in expected:
        row = methods[signature]
        if row['normalizedBodySha256'] != expected_hash:
            raise ValueError('Exact Message target provenance changed')
        selected_proofs.append({'owner': row['body']['owner'], 'signature': signature,
                                'bodySha256': expected_hash})
    for signature in ['obtainMessage(III)Landroid/os/Message;', 'sendMessage(Landroid/os/Message;)Z']:
        declaration = next(m for m in handler_decl[0]['methods'] if m['signature'] == signature)
        if declaration['accessFlags'] != 17:
            raise ValueError('Handler method is not original public final')
    field = next(f for f in tracker_decl[0]['fields'] if f['name'] == 'mHandler')
    if field['accessFlags'] != 18:
        raise ValueError('Tracker handler is not original private final')
    samsung = ROOT.parent / 'firmware/samsung/framework.jar'
    samsung_sha = '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
    if digest(samsung) != samsung_sha:
        raise ValueError('Samsung comparison source pin')
    host_message, _, host_read = read_actual(samsung, 'samsung-target-message',
                                            'Landroid/os/Message;', ['sendToTarget()V'])
    if host_message['sendToTarget()V']['normalizedBodySha256'] != '7b51e1dbbeba378cc4e4ee283e2855b78dbbccd93448508cb3d18df68410d453':
        raise ValueError('Samsung original Message path changed')
    callback = json.loads((ROOT / 'inventory/strongauth-callback-adapter.json').read_text())
    host_callback_key = 'samsung-queue:' + OWNER + '->' + METHOD
    host_callback = callback['methodProofs'][host_callback_key]
    if digest(ROOT / host_callback['raw']) != host_callback['rawSha256']:
        raise ValueError('Samsung callback raw pin')
    if digest(samsung) != samsung_sha:
        raise ValueError('Samsung source changed')
    return {'sourceReads': [handler_read, message_read, tracker_read],
            'selectedBodyProofs': selected_proofs, 'samsungMessageRead': host_read,
            'samsungOriginalCallbackProof': host_callback,
            'handlerObtainAndSendArePublicFinal': True, 'trackerHandlerIsPrivateFinal': True,
            'messageObtainTargetWritePc': 4, 'messageWhatArg1Arg2WritePcs': [6, 8, 10],
            'bothMessageWrappersCallCanonicalHandlerSendPc': 2,
            'scope': 'Same original obtained Message and its genuine target only; no global FIFO/readiness/drain claim'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    if digest(SOURCE) != SOURCE_SHA or digest(ROOT / 'tools/build_coloros_pin_metadata_leaf.py') != HELPER_SHA:
        raise ValueError('Source/integrity helper pin')
    if digest(ROOT / 'inventory/strongauth-callback-adapter.json') != CALLBACK_INVENTORY_SHA:
        raise ValueError('Frozen callback evidence changed')
    if digest(ROOT / SOURCE_XREF) != SOURCE_XREF_SHA:
        raise ValueError('Frozen exact reference evidence changed')
    reference_rows = [json.loads(line) for line in (ROOT / SOURCE_XREF).read_text().splitlines()]
    callers = [r for r in reference_rows if r['record'] == 'reference']
    if len(callers) != 1 or callers[0]['caller'] != OWNER + '->' + METHOD or callers[0]['instruction']['pc'] != 17:
        raise ValueError('Current method-reference caller changed')
    target_chain = prove_target_chain()
    with zipfile.ZipFile(SOURCE) as archive:
        infos = archive.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError('Duplicate archive entries')
        entries = {info.filename: archive.read(info.filename) for info in infos}
    versions = {name: header(data) for name, data in entries.items()
                if name.startswith('classes') and name.endswith('.dex')}
    source = entries[DEX]
    if sha(source) != DEX_SHA:
        raise ValueError('Target DEX pin')
    profile, references, location, ownership = layout(source)
    old, decl, source_read = read_actual(SOURCE, 'source-callback-owner')
    row = old[METHOD]
    body = row['body']
    if row['normalizedBodySha256'] != BODY or body['catches'] or any(
            'targetPc' in i or 'switchElements' in i or 'PAYLOAD' in i['opcode'] for i in body['instructions']):
        raise ValueError('Exact source body/branch/try admission')
    call = next(i for i in body['instructions'] if i['pc'] == 17)
    if call != {'pc': 17, 'opcode': 'INVOKE_VIRTUAL', 'codeUnits': 3, 'registers': [1, 0],
                'referenceKind': 'method', 'reference': OLD_REF}:
        raise ValueError('Source invoke shape')
    if body['instructions'][-1] != {'pc': 20, 'opcode': 'RETURN_VOID', 'codeUnits': 1}:
        raise ValueError('Ignored result/return shape')
    first = location['instructionsOffset'] + 34
    last = first + 6
    before_bytes = bytes.fromhex('6e20bb100100')
    after_bytes = bytes.fromhex('6e1040030000')
    if source[first:last] != before_bytes:
        raise ValueError('Exact original invoke bytes')
    changed = bytearray(source)
    changed[first:last] = after_bytes
    patched = seal(changed)
    patched_profile, patched_refs, patched_loc, patched_ownership = layout(patched)
    if references != patched_refs or location != patched_loc or ownership != patched_ownership:
        raise ValueError('References/code ownership changed')
    allowed = set(range(8, 32)) | set(range(first, last))
    actual_changes = [i for i, (a, b) in enumerate(zip(source, patched)) if a != b]
    if len(source) != len(patched) or any(i not in allowed for i in actual_changes):
        raise ValueError('Non-approved byte change')
    inverse = bytearray(patched)
    inverse[first:last] = before_bytes
    inverse = seal(inverse)
    if inverse != source:
        raise ValueError('Actual inverse failed')
    roundtrip = bytearray(inverse)
    roundtrip[first:last] = after_bytes
    if seal(roundtrip) != patched:
        raise ValueError('Actual roundtrip failed')
    artifact = OUT / 'framework.strongauth-queue.unselected.jar'
    with zipfile.ZipFile(artifact, 'w') as archive:
        for info in infos:
            archive.writestr(info, patched if info.filename == DEX else entries[info.filename])
    (OUT / 'classes6.patched.dex').write_bytes(patched)
    (OUT / 'classes6.inverse.dex').write_bytes(inverse)
    new, newdecl, patched_read = read_actual(artifact, 'patched-callback-owner')
    expected = json.loads(json.dumps(body))
    instruction = next(i for i in expected['instructions'] if i['pc'] == 17)
    instruction['registers'], instruction['reference'] = [0], NEW_REF
    if set(old) != set(new) or decl != newdecl or new[METHOD]['body'] != expected:
        raise ValueError('Actual decoded output mismatch')
    if any(old[name] != new[name] for name in old if name != METHOD):
        raise ValueError('Other owner method changed')
    with zipfile.ZipFile(artifact) as archive:
        if archive.namelist() != [info.filename for info in infos]:
            raise ValueError('ZIP entries changed')
        entry_proofs = []
        for info in infos:
            data = archive.read(info.filename)
            if data != (patched if info.filename == DEX else entries[info.filename]):
                raise ValueError('Archive payload preservation')
            entry_proofs.append({'name': info.filename, 'sourceSha256': sha(entries[info.filename]),
                                 'patchedSha256': sha(data), 'unchanged': data == entries[info.filename]})
    dump(OUT / 'entry-payload-proofs.json', entry_proofs)
    if digest(SOURCE) != SOURCE_SHA or digest(ROOT / 'tools/build_coloros_pin_metadata_leaf.py') != HELPER_SHA:
        raise ValueError('Input/helper changed during build')
    receipt = {
        'schema': 'coloros-strongauth-queue-leaf/v1', 'status': 'UNSELECTED_PC_ONLY_COLD_START_QUEUE_LEAF',
        'sourceArchive': str(SOURCE), 'sourceArchiveSha256': SOURCE_SHA,
        'patchedArchive': artifact.relative_to(ROOT).as_posix(), 'patchedArchiveSha256': digest(artifact),
        'selected': False, 'coldStartOnly': True,
        'sourceDexVersions': {name: item['version'] for name, item in versions.items()},
        'sourceClassCount': sum(item['classes'] for item in versions.values()),
        'patches': [{'physicalDex': DEX, 'logicalHeaderOffset': 0, 'owner': OWNER, 'method': METHOD,
                     'sourceBodySha256': BODY, 'patchedBodySha256': new[METHOD]['normalizedBodySha256'],
                     'codeLocation': location, 'firstPc': 17, 'endExclusivePc': 20,
                     'instructionByteRange': [first, last], 'beforeHex': before_bytes.hex(),
                     'afterHex': after_bytes.hex(), 'oldReference': OLD_REF, 'newReference': NEW_REF,
                     'oldRegisters': [1, 0], 'newRegisters': [0], 'inverseVerified': True}],
        'dex': {DEX: {'sourceSha256': sha(source), 'patchedSha256': sha(patched),
                      'inverseSha256': sha(inverse), 'sourceHeader': profile, 'patchedHeader': patched_profile,
                      'actualChangedByteOffsets': actual_changes, 'codeOwnership': ownership,
                      'allBytesOutsideApprovedInstructionAndIntegrityFieldsUnchanged': True}},
        'existingMethodReferences': references, 'absentMethodReference': ABSENT_REF,
        'sourceRead': source_read, 'patchedRead': patched_read,
        'sameTargetProvenance': target_chain,
        'currentReferenceCallers': {'raw': SOURCE_XREF, 'rawSha256': SOURCE_XREF_SHA,
                                    'count': 1, 'caller': OWNER + '->' + METHOD, 'pc': 17,
                                    'scope': 'Exact H.sendMessageAtFrontOfQueue reference in supplied ColorOS framework only'},
        'entryPayloadProof': {'path': 'out/strongauth-queue-leaf/entry-payload-proofs.json',
                              'sha256': digest(OUT / 'entry-payload-proofs.json'),
                              'totalEntries': len(entry_proofs),
                              'unchangedEntries': sum(p['unchanged'] for p in entry_proofs)},
        'checks': {'exactOriginalAndOutputDecoding': True, 'sameClassAndMethodDeclarations': True,
                   'allOtherOwnerMethodsIdentical': True, 'noBranchesPayloadsOrTryItems': True,
                   'exclusiveTargetCodeOwnership': True, 'sameRegistersAndCodeExtent': True,
                   'allOtherBytesPreservedExceptDexIntegrity': True, 'inverse': True, 'roundtrip': True,
                   'allDex039Checksums': True, 'originalArchiveUnmodified': True},
        'requiredSelectionConditions': [
            'Cold fresh process only; existing front-queued callbacks, registered trackers and active consumers need genuine disconnect/drain before replacement.',
            'Resolve genuine Samsung code/state/service authority, caller/user/profile and immutable callback generation admission before use.',
            'Same genuine Message target from final original Handler.obtainMessage is required; this cut preserves what1/full flags/user and only changes ordinary queue ingress.',
            'Source-owned initial snapshot/subscription ordering and actual applied-state acknowledgement remain required; queued send/void return/default/silence is never readiness.',
            'Delegate tracker-level eligibility to genuine Samsung original policy and preserve real nonStrongAllowed, lockout, additional-factor and higher finish/Keystore policy; no biometric mask patch is included.',
            'Remote registration/removal, source broadcasts/Binder delivery, local queue and active-consumer drain remain unimplemented obligations; uncertain progress stays retained and unavailable.',
            'Validate exact installed host/guest/profile/resources and actual Android behavior before any selection; disclose accepted OneOS platform limitations.'
        ],
        'negativeEvidenceScope': 'Positive exact-input actual-byte ownership/preservation/decoding/inverse only; no malformed-byte negatives or runtime fault campaign.',
        'limits': ['Ordinary queue behavior matches Samsung sendToTarget only through the same genuine Message target; no global FIFO/initial/applied/cancel/drain proof.',
                   'ZIP reserialized; entry payload preservation is proved, not identical ZIP physical bytes or JAR signing/ART acceptance.',
                   'No OEM class, Android, hardware or cryptographic execution; no phone action or complete adapter.'],
        'callbackInventorySha256': CALLBACK_INVENTORY_SHA,
        'integrityHelper': {'path': 'tools/build_coloros_pin_metadata_leaf.py', 'sha256': HELPER_SHA},
        'producerSha256': digest(__file__), 'oemCodeExecuted': False, 'phoneActions': []}
    dump(OUT / 'leaf-receipt.json', receipt)
    dump(ROOT / 'inventory/strongauth-queue-leaf.json', receipt)
    print(json.dumps({'pass': True, 'selected': False, 'coldStartOnly': True,
                      'patchedArchiveSha256': digest(artifact), 'changedMethods': 1,
                      'sourceClassCount': receipt['sourceClassCount']}))


if __name__ == '__main__':
    main()
