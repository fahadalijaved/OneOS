"""Check exact original DEX ID capacity for the closed Settings attach cut."""

from hashlib import file_digest, sha256
import json
from pathlib import Path
import struct
from zipfile import ZipFile

from preserve_dex_code_headers import Dex039


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ('firmware/installed-oneos-staged-code/20261106T021318359707Z-'
           'dfb840a7be91477091886e754bfec0be/services_patched.jar')
ARCHIVE_SHA = 'efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671'
DEX_SHA = 'bcc9cb821ffc6a37b3838ca2391253652a0d40245a4b75b8b35eccd17779ca20'
DEX_BYTES = 12_186_672
AMS = b'Lcom/android/server/am/ActivityManagerService;'
RECORD = b'Lcom/android/server/am/ProcessRecord;'
THREAD = b'Landroid/app/IApplicationThread;'
DEFERRED = b'Lcom/android/server/am/ApplicationThreadDeferred;'
HELPER = b'Lcom/android/server/am/PreparedGuestFingerprintAttach;'
OBSERVATION = HELPER[:-1] + b'$Observation;'
TUPLE_ARGS = (RECORD, THREAD, b'J', b'I', b'I')
ADDITIONS = (
    (AMS, b'finishAttachApplicationForFingerprintObservation', OBSERVATION, (b'J', b'I', b'I')),
    (HELPER, b'snapshot', OBSERVATION, TUPLE_ARGS),
    (HELPER, b'matchesAfterRestore', b'Z', (OBSERVATION,) + TUPLE_ARGS),
)
LIMIT = 65_536


def _utf16(mutf8):
    # DEX orders strings by UTF-16 code units. Modified UTF-8 stores NUL and surrogates separately.
    return mutf8.replace(b'\xc0\x80', b'\0').decode('utf-8', 'surrogatepass').encode('utf-16-be', 'surrogatepass')


def _shorty(descriptor):
    return b'L' if descriptor.startswith((b'L', b'[')) else descriptor


def audit_pool(raw: bytes) -> dict:
    if type(raw) is not bytes or len(raw) != DEX_BYTES or sha256(raw).hexdigest() != DEX_SHA:
        raise ValueError('Expected the exact original staged guest services classes.dex')
    dex = Dex039(raw)
    ns, nt, np, nf, nm = (dex.u32(offset) for offset in (56, 64, 72, 80, 88))
    strings_off, types_off, protos_off, fields_off, methods_off = (
        dex.u32(offset) for offset in (60, 68, 76, 84, 92))
    string_limit = dex.sections[0x2002][1]
    strings = []
    for index in range(ns):
        _, start = dex.uleb(dex.u32(strings_off + 4 * index), string_limit)
        strings.append(raw[start:raw.index(0, start, string_limit)])
    string_keys = [_utf16(value) for value in strings]
    if any(a >= b for a, b in zip(string_keys, string_keys[1:])):
        raise ValueError('Original DEX strings are out of UTF-16 order')
    types = [strings[dex.u32(types_off + 4 * index)] for index in range(nt)]
    protos = []
    for index in range(np):
        _, result, parameters = struct.unpack_from('<III', raw, protos_off + 12 * index)
        args = () if not parameters else tuple(
            types[dex.u16(parameters + 4 + 2 * word)] for word in range(dex.u32(parameters)))
        protos.append((types[result], args))
    methods = set()
    for index in range(nm):
        owner, proto, name = struct.unpack_from('<HHI', raw, methods_off + 8 * index)
        methods.add((types[owner], strings[name], *protos[proto]))
    if len(methods) != nm or any(ref in methods for ref in ADDITIONS):
        raise ValueError('Planned attach method identities overlap the original method pool')
    thread_fields = []
    for index in range(nf):
        owner, kind, name = struct.unpack_from('<HHI', raw, fields_off + 8 * index)
        if (types[owner], types[kind], strings[name]) == (RECORD, DEFERRED, b'mThread'):
            thread_fields.append(index)
    if thread_fields != [0x6FE1]:
        raise ValueError('Original ProcessRecord thread field reference differs')

    added_types = {part for owner, _, result, args in ADDITIONS for part in (owner, result, *args)}
    added_protos = {(result, args) for _, _, result, args in ADDITIONS}
    shorties = {b''.join(_shorty(part) for part in (result, *args)) for result, args in added_protos}
    added_strings = added_types | shorties | {name for _, name, _, _ in ADDITIONS}
    new_string_keys = {_utf16(value) for value in added_strings} - set(string_keys)
    combined_keys = sorted([*string_keys, *new_string_keys])
    ranks = {key: index for index, key in enumerate(combined_keys)}
    crossing = [index for index, key in enumerate(string_keys[:LIMIT]) if ranks[key] >= LIMIT]
    counts = {'strings': ns, 'types': nt, 'protos': np, 'fields': nf, 'methods': nm}
    projected = {'strings': len(combined_keys), 'types': len(set(types) | added_types),
                 'protos': len(set(protos) | added_protos), 'fields': nf, 'methods': nm + len(ADDITIONS)}
    if any(projected[key] > LIMIT for key in ('types', 'protos', 'fields', 'methods')):
        raise ValueError('The planned attach references exceed the original DEX ID capacity')
    return {
        'status': 'EXACT_GUEST_ATTACH_ID_CAPACITY_REVIEW_ONLY',
        'inputDexSha256': DEX_SHA,
        'originalCounts': counts,
        'projectedCounts': projected,
        'remainingMethodIds': LIMIT - projected['methods'],
        'existingThreadFieldId': thread_fields[0],
        'plannedMethods': [(owner + b'->' + name + b'(' + b''.join(args) + b')' + result).decode('ascii')
                           for owner, name, result, args in ADDITIONS],
        'oldStringIdsCrossingShortLimit': crossing,
        'selected': False, 'targetExecuted': False, 'retargetEmitted': False,
    }


def main():
    path = ROOT / ARCHIVE
    with path.open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != ARCHIVE_SHA:
            raise ValueError('Expected the exact held staged guest services archive')
    with ZipFile(path) as archive:
        entries = archive.infolist()
        if [entry.filename for entry in entries].count('classes.dex') != 1:
            raise ValueError('Missing or ambiguous staged services classes.dex')
        member = archive.getinfo('classes.dex')
        if member.file_size != DEX_BYTES:
            raise ValueError('Unexpected staged services DEX size')
        result = audit_pool(archive.read(member))
    with path.open('rb') as stream:
        if file_digest(stream, 'sha256').hexdigest() != ARCHIVE_SHA:
            raise ValueError('Staged guest services archive changed during read')
    print(json.dumps({'sourceArchive': ARCHIVE, 'sourceArchiveSha256': ARCHIVE_SHA, **result}, indent=2))


if __name__ == '__main__':
    main()
