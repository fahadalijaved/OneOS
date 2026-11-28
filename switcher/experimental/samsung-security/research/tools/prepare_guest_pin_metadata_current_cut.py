"""Fixed, unselected PIN audit-metadata byte leaf; never executes target code.

Default/--prepare validates inputs and publishes metadata only. --emit requires
separate source-review/root-GO documents. No DEX writer or compiler is invoked.
Strict Windows path-resolution errors intentionally refuse; there is no fallback.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import uuid
import zipfile
import zlib

ROOT = Path(__file__).resolve(strict=True).parents[1]
OUT = ROOT / 'out/guest-pin-metadata-current-cut'
ORIGINAL = 'firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/framework_patched.jar'
BASE_WORK = 'out/guest-locksettings-proxy-retarget/20261106T100501810887Z-45c47b00be484852aa2ab78b20d70e85/dex/'
BASE_JAR = BASE_WORK + 'framework-proxy33.jar'
BASE_DEX = BASE_WORK + 'proxy33-forward.dex'
ORIGINAL_SHA = '5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246'
SOURCE_SHA = '47f3b688c6365610afce4f24a03e8f601c7f3f240f73bd03fabee384ab1110a4'
BASE_SHA = 'fb8b60d2b4f49fc8c8254d11aa985340d429f6af4aeceae7f95e969231a5fde5'
BASE_JAR_SHA = '0e368299e06672ecf884a372f62be44d1c35a28490584088d90d7aedce58fe45'
PLAN = 'out/guest-pin-metadata-current-cut/PREPARATION.json'
PLAN_SHA = '4cd28ba915d62189aa6f5c1c0edf328a13d229aecf808f1826b7eb9723b067cb'
PINS = {
    PLAN: PLAN_SHA,
    'out/guest-pin-metadata-current-cut/API-PROPOSAL.md': '273c6916f83abb818603bdf35cc729acf4db81c8c8660a18135790f97ac8d0b7',
    'out/guest-pin-metadata-current-cut/SOURCE-FROZEN.json': 'c2cab1637137808fc817f6d875b8ad39dad59c718664f4e6e3c707d7bd7ff358',
    'out/guest-pin-metadata-current-cut-review/source-plan-pass.json': '94689b9fb2a21510d5380aaf8469c3563d7ec0898b3650db7dfe65fbec38c1fc',
    ORIGINAL: ORIGINAL_SHA, BASE_JAR: BASE_JAR_SHA, BASE_DEX: BASE_SHA,
}
OWNER = b'Lcom/android/internal/widget/LockPatternUtils;'
SIGNATURE = b'setLockCredential(Lcom/android/internal/widget/LockscreenCredential;Lcom/android/internal/widget/LockscreenCredential;I)Z'
FIRST, END = 2055316, 2055344
CODE_SHA = '1a705cb9d4272b08f05e73f434ef04e00892ac1140f0e51684624deb2b346a0d'
SLICE_SHA = '24c23ea9d553f81084d3fd66bcc90f6aa0d14de32c33d5b4a28a84dd1c92fde4'
DEBUG_SHA = '19dfd8385902a33fd266bc6a8126a6203454e24a71a9fdb2be0f26c6df0ffa21'
HAPI_SHA = 'a7cc1920616ae709a4590386dfe65435b2bb07ee64c8f333a17ada3320e069f1'


class Refused(ValueError):
    pass


def need(value, message):
    if not value:
        raise Refused(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf8')


def checked_path(value, directory=False):
    """Strict canonical containment, no symlink/reparse or lexical fallback."""
    path = Path(value)
    need('..' not in path.parts, 'PATH_PARENT_COMPONENT')
    if not path.is_absolute():
        path = ROOT / path
    canonical = path.resolve(strict=True)  # WinError5 is NOT caught or weakened.
    need(canonical.is_relative_to(ROOT), 'PATH_OUTSIDE_REPOSITORY')
    # Reject even in-repository links, including junctions on supported Windows.
    for item in [ROOT] + [ROOT.joinpath(*canonical.relative_to(ROOT).parts[:n])
                           for n in range(1, len(canonical.relative_to(ROOT).parts) + 1)]:
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'PATH_LINK_OR_REPARSE')
    # Also examine lexical ancestors, so resolving an in-tree link is not admission.
    need(path.is_relative_to(ROOT), 'PATH_LEXICAL_OUTSIDE')
    for n in range(1, len(path.relative_to(ROOT).parts) + 1):
        info = ROOT.joinpath(*path.relative_to(ROOT).parts[:n]).lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400), 'LEXICAL_LINK_OR_REPARSE')
    mode = canonical.stat().st_mode
    need(stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode), 'PATH_TYPE')
    return canonical


def read_checked(value, limit):
    path = checked_path(value)
    before = path.stat()
    need(before.st_size <= limit, 'INPUT_SIZE')
    with path.open('rb') as handle:
        opened = os.fstat(handle.fileno())
        data = handle.read(limit + 1)
        final = os.fstat(handle.fileno())
    after = path.stat()
    need(len(data) <= limit and read_identity_stable(before, opened, final, after), 'INPUT_MOVED_DURING_READ')
    need(checked_path(path) == path, 'INPUT_CANONICAL_MOVED')
    names = ['st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns']
    witness = {role: {name: str(getattr(observed, name)) for name in names}
               for role, observed in [('pathBefore', before), ('fdOpened', opened),
                                      ('fdAfterRead', final), ('pathAfter', after)]}
    return data, {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(data),
                  'sha256': sha(data), 'readIdentity': witness}


def read_identity_stable(before, opened, final, after):
    """Exact integers; compare ctime only within its original API channel."""
    common = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    return (common(before) == common(opened) == common(final) == common(after)
            and before.st_ctime_ns == after.st_ctime_ns
            and opened.st_ctime_ns == final.st_ctime_ns)


def u16(data, offset):
    need(0 <= offset <= len(data) - 2, 'U16_BOUNDS')
    return struct.unpack_from('<H', data, offset)[0]


def u32(data, offset):
    need(0 <= offset <= len(data) - 4, 'U32_BOUNDS')
    return struct.unpack_from('<I', data, offset)[0]


def leb(data, offset, signed=False):
    value = 0
    for index in range(5):
        need(offset < len(data), 'LEB_BOUNDS')
        byte = data[offset]
        offset += 1
        value |= (byte & 127) << (index * 7)
        if byte < 128:
            if signed and byte & 64:
                value -= 1 << ((index + 1) * 7)
            need(-(1 << 31) <= value < (1 << 31) if signed else value <= 0xffffffff, 'LEB_OVERFLOW')
            return value, offset
    raise Refused('LEB_TERMINATION')


def parse_dex(data):
    """Bounded fixed-profile declaration/code ownership and metadata read only."""
    need(data[:8] == b'dex\n039\0' and len(data) >= 112, 'ORDINARY039_ONLY')
    need(u32(data, 32) == len(data) and u32(data, 36) == 112 and u32(data, 40) == 0x12345678, 'DEX_HEADER')
    need(hashlib.sha1(data[32:]).digest() == data[12:32] and zlib.adler32(data[12:]) & 0xffffffff == u32(data, 8), 'DEX_INTEGRITY')
    need(u32(data, 104) + u32(data, 108) == len(data), 'DEX_DATA_EXTENT')
    counts = [u32(data, o) for o in [56, 64, 72, 80, 88, 96]]
    need(counts == [33938, 3137, 4253, 17828, 21699, 2209], 'FIXED_POOL_COUNTS')
    for o, width in [(56, 4), (64, 4), (72, 12), (80, 8), (88, 8), (96, 32)]:
        need(112 <= u32(data, o + 4) and u32(data, o + 4) + u32(data, o) * width <= len(data), 'POOL_EXTENT')
    strings = []
    for index in range(counts[0]):
        cursor = u32(data, u32(data, 60) + 4 * index)
        _, cursor = leb(data, cursor)
        stop = data.find(b'\0', cursor, min(len(data), cursor + 1048576))
        need(stop >= cursor, 'STRING_TERMINATION')
        strings.append(data[cursor:stop])
    def string(index):
        need(index < len(strings), 'STRING_INDEX')
        return strings[index]
    types = [string(u32(data, u32(data, 68) + 4 * i)) for i in range(counts[1])]
    def typ(index):
        need(index < len(types), 'TYPE_INDEX')
        return types[index]
    signatures = []
    for i in range(counts[2]):
        cursor = u32(data, 76) + 12 * i
        typ_index, params = u32(data, cursor + 4), u32(data, cursor + 8)
        args = []
        if params:
            count = u32(data, params)
            need(count <= 65535 and params + 4 + count * 2 <= len(data), 'PARAMETERS_EXTENT')
            args = [typ(u16(data, params + 4 + 2 * j)) for j in range(count)]
        signatures.append(b'(' + b''.join(args) + b')' + typ(typ_index))
    methodids = []
    for i in range(counts[4]):
        cursor = u32(data, 92) + 8 * i
        owner, proto, name = u16(data, cursor), u16(data, cursor + 2), u32(data, cursor + 4)
        need(proto < len(signatures), 'PROTO_INDEX')
        methodids.append((typ(owner), string(name) + signatures[proto]))
    declarations, ranges, targets = [], [], []
    for ci in range(counts[5]):
        cursor = u32(data, 100) + 32 * ci
        owner = u32(data, cursor)
        cursor = u32(data, cursor + 24)
        if not cursor:
            continue
        sizes = []
        for _ in range(4):
            value, cursor = leb(data, cursor)
            sizes.append(value)
        need(sum(sizes) <= 200000, 'DECLARATION_BOUND')
        for part, count in enumerate(sizes):
            index = 0
            for _ in range(count):
                delta, cursor = leb(data, cursor)
                index += delta
                flags, cursor = leb(data, cursor)
                if part < 2:
                    need(index < counts[3], 'FIELD_INDEX')
                    continue
                code, cursor = leb(data, cursor)
                need(index < len(methodids) and methodids[index][0] == typ(owner), 'ENCODED_METHOD_IDENTITY')
                declarations.append((index, part, flags, bool(code)))
                if not code:
                    continue
                need(code % 4 == 0 and code >= u32(data, 108) and code + 16 <= len(data), 'CODE_LOCATION')
                units = u32(data, code + 12)
                start, end = code + 16, code + 16 + 2 * units
                need(end <= len(data), 'CODE_EXTENT')
                ranges.append((index, start, end))
                if methodids[index] == (OWNER, SIGNATURE):
                    targets.append({'methodId': index, 'partition': part, 'flags': flags, 'code': code,
                                    'start': start, 'end': end, 'debug': u32(data, code + 8),
                                    'header': [u16(data, code + i) for i in [0, 2, 4, 6]] + [units]})
    need(len(declarations) == 17065 and len(ranges) == 14893 and len(targets) == 1, 'DECLARED_METHOD_FRONTIER')
    target = targets[0]
    need(target['methodId'] == 4418 and target['partition'] == 3 and target['flags'] == 1 and target['header'] == [7, 4, 4, 1, 63], 'TARGET_DECLARATION_HEADER')
    table = target['end'] + 2  # odd63 units: original two-byte code-item padding.
    need(data[target['end']:table] == b'\0\0', 'TARGET_CODE_PADDING')
    need(u32(data, table) == 22 and u16(data, table + 4) == 29 and u16(data, table + 6) == 1, 'TARGET_TRY22_51')
    cursor = table + 8
    number, cursor = leb(data, cursor)
    count, cursor = leb(data, cursor, signed=True)
    exception, cursor = leb(data, cursor)
    handler, cursor = leb(data, cursor)
    need(number == 1 and count == 1 and typ(exception) == b'Landroid/os/RemoteException;' and handler == 54, 'TARGET_HANDLER54')
    debug = target['debug']
    need(debug + 38 <= len(data) and sha(data[debug:debug + 38]) == DEBUG_SHA, 'EXACT_TARGET_RAW_DEBUG_END55')
    mp = u32(data, 52)
    n = u32(data, mp)
    need(n <= 65535 and mp + 4 + n * 12 <= len(data), 'MAP_EXTENT')
    maps = [(u16(data, mp + 4 + 12 * i), u32(data, mp + 8 + 12 * i), u32(data, mp + 12 + 12 * i)) for i in range(n)]
    need(len({x[0] for x in maps}) == len(maps), 'MAP_DUPLICATE')
    hapi = [x for x in maps if x[0] == 0xf000]
    need(len(hapi) == 1 and hapi[0][1] == 1 and u32(data, hapi[0][2]) == 42949, 'HAPI_PROFILE')
    hp = hapi[0][2]
    need(hp + 42949 <= len(data) and sha(data[hp:hp + 42949]) == HAPI_SHA, 'HAPI_RAW_POLICY')
    return {'target': target, 'declarations': declarations, 'ranges': ranges, 'maps': maps, 'hapi': [hp, hp + 42949]}


def seal(data):
    data = bytearray(data)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into('<I', data, 8, zlib.adler32(data[12:]) & 0xffffffff)
    return bytes(data)


def validate_pair(original, base):
    need(type(original) is bytes and type(base) is bytes, 'IMMUTABLE_BYTES_ONLY')
    need(len(original) == 3304704 and sha(original) == SOURCE_SHA, 'EXACT_ORIGINAL_CLASSES6')
    need(len(base) == 3329888 and sha(base) == BASE_SHA, 'EXACT_REVIEWED_PROXY33')
    a, b = parse_dex(original), parse_dex(base)
    ta, tb = a['target'], b['target']
    need(ta['start'] == 706972 and ta['debug'] == 1817620 and tb['start'] == 2055240 and tb['debug'] == 1621588, 'EXACT_CURRENT_LOCATIONS')
    need(a['declarations'] == b['declarations'], 'SOURCE_DECLARATION_IDENTITY')
    need(original[ta['start']:ta['end']] == base[tb['start']:tb['end']] and sha(base[tb['start']:tb['end']]) == CODE_SHA, 'UNCHANGED_FULL_LPU_CODE')
    need(FIRST == tb['start'] + 2 * 38 and END == tb['start'] + 2 * 52 and sha(base[FIRST:END]) == SLICE_SHA, 'EXACT_OPTIONAL_SOURCE_SLICE')
    need(not any(i != 4418 and max(FIRST, start) < min(END, end) for i, start, end in b['ranges']), 'OTHER_METHOD_ALIAS_OR_OVERLAP')
    need(not (FIRST < b['hapi'][1] and b['hapi'][0] < END), 'PATCH_OVERLAPS_HAPI')
    return b


def verify_candidate(base, candidate):
    """Exact-base verifier; accepts only the literal byte omission and reseal."""
    need(type(base) is bytes and type(candidate) is bytes, 'IMMUTABLE_CANDIDATE_BYTES_ONLY')
    need(sha(base) == BASE_SHA and len(candidate) == len(base), 'CANDIDATE_BASE_SIZE')
    need(candidate[FIRST:END] == bytes(END - FIRST), 'CANDIDATE_NOPS')
    need(candidate[:8] == base[:8] and candidate[32:FIRST] == base[32:FIRST] and candidate[END:] == base[END:], 'CANDIDATE_BYTE_WHITELIST')
    before, after = parse_dex(base), parse_dex(candidate)
    need(before == after, 'CANDIDATE_REPARSE_METADATA')
    changed = [i for i, (x, y) in enumerate(zip(base, candidate)) if x != y]
    need(changed and all(8 <= i < 32 or FIRST <= i < END for i in changed), 'CANDIDATE_CHANGED_OFFSETS')
    return {'changedByteCount': len(changed), 'instructionRange': [FIRST, END],
            'allOtherBytesIncludingCodeHeadersTriesDebugHapiAnnotationsExact': True,
            'declaredMethods': 17065, 'codedMethods': 14893, 'method4418Header': [7, 4, 4, 1, 63]}


def omit_optional_pin_metadata(original_classes6, reviewed_proxy33_classes6):
    """No I/O, caller-selected profiles, method exemptions or authority claim."""
    validate_pair(original_classes6, reviewed_proxy33_classes6)
    candidate = bytearray(reviewed_proxy33_classes6)
    candidate[FIRST:END] = bytes(END - FIRST)
    candidate = seal(candidate)
    proof = verify_candidate(reviewed_proxy33_classes6, candidate)
    inverse = bytearray(candidate)
    inverse[FIRST:END] = reviewed_proxy33_classes6[FIRST:END]
    inverse = seal(inverse)
    need(inverse == reviewed_proxy33_classes6, 'INVERSE_EXACT_FB8B')
    again = bytearray(inverse)
    again[FIRST:END] = bytes(END - FIRST)
    need(seal(again) == candidate, 'REAPPLY_EXACT_FORWARD')
    return candidate, {**proof, 'inverseExactReviewedProxy33': True, 'reapplyExactForward': True,
                       'writerRoundtripClaimed': False, 'sourceDexSha256': SOURCE_SHA,
                       'proxy33BaseDexSha256': BASE_SHA, 'patchedDexSha256': sha(candidate)}


def archive_entries(data):
    archive = zipfile.ZipFile(io.BytesIO(data))
    infos = archive.infolist()
    need(0 < len(infos) <= 10000 and len({i.filename for i in infos}) == len(infos), 'ZIP_MEMBER_CLOSURE')
    need(sum(i.file_size for i in infos) <= 128 * 1024 * 1024 and all(i.file_size <= 64 * 1024 * 1024 for i in infos), 'ZIP_EXPANDED_BOUND')
    need(all(not (i.flag_bits & 1) for i in infos), 'ZIP_ENCRYPTED')
    contents = {i.filename: archive.read(i) for i in infos}  # read verifies CRC.
    need('classes6.dex' in contents, 'ZIP_SELECTED_ENTRY')
    return archive, infos, contents


def package(base_jar, dex):
    archive, infos, contents = archive_entries(base_jar)
    need(sha(contents['classes6.dex']) == BASE_SHA, 'JAR_BASE_DEX')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as target:
        target.comment = archive.comment
        for info in infos:
            target.writestr(info, dex if info.filename == 'classes6.dex' else contents[info.filename])
    result = buffer.getvalue()
    output, new_infos, new_contents = archive_entries(result)
    need([x.filename for x in infos] == [x.filename for x in new_infos] and archive.comment == output.comment, 'JAR_NAMES_ORDER_COMMENT')
    need(all(new_contents[n] == (dex if n == 'classes6.dex' else old) for n, old in contents.items()), 'JAR_PAYLOAD_CLOSURE')
    proof = {'entryCount': len(infos), 'allNonselectedExpandedBytesExact': True,
             'namesOrderCommentExact': True, 'allEntryCrcVerified': True,
             'physicalCompressedZipIdentityClaimed': False, 'jarSha256': sha(result)}
    output.close()
    archive.close()
    return result, proof


def inputs():
    data, admitted = {}, {}
    for name, expected in PINS.items():
        value, pin = read_checked(name, 64 * 1024 * 1024)
        need(pin['sha256'] == expected, 'FIXED_INPUT_PIN:' + name)
        data[name], admitted[name] = value, pin
    proof = json.loads(data['out/guest-pin-metadata-current-cut-review/source-plan-pass.json'])
    need(proof['status'] == 'PASS_BOUNDED_LPU_PLAN_API_ONLY', 'PLAN_REVIEW_STATUS')
    original_archive, _, original_contents = archive_entries(data[ORIGINAL])
    base_archive, _, base_contents = archive_entries(data[BASE_JAR])
    original, base = original_contents['classes6.dex'], data[BASE_DEX]
    need(base_contents['classes6.dex'] == base, 'JAR_STANDALONE_BASE_IDENTITY')
    validate_pair(original, base)
    original_archive.close()
    base_archive.close()
    authored = {admitted[name]['path']: value for name, value in data.items()
                if name not in [ORIGINAL, BASE_JAR, BASE_DEX]}
    return original, base, data[BASE_JAR], admitted, authored


def gate(value, tool_sha):
    raw, pin = read_checked(value, 65536)
    document = json.loads(raw)
    need(set(document) == {'schema', 'sourceToolSha256', 'sourcePlanSha256', 'sourceReview', 'rootDecision'}, 'GATE_SCHEMA')
    need(document['schema'] == 'guest-pin-metadata-current-cut-gate/v1' and document['sourceToolSha256'] == tool_sha and document['sourcePlanSha256'] == PLAN_SHA, 'GATE_BINDING')
    pins, paths, identities = {pin['path']: pin}, {pin['path'].casefold()}, set()
    captured = {pin['path']: raw}
    s = checked_path(pin['path']).stat()
    identities.add((s.st_dev, s.st_ino))
    for role, status in [('sourceReview', 'SOURCE_PASS'), ('rootDecision', 'ONE_PC_EMIT_GO')]:
        ref = document[role]
        need(set(ref) == {'path', 'sha256'}, 'GATE_REFERENCE_SCHEMA')
        payload, actual = read_checked(ref['path'], 65536)
        canonical = actual['path'].casefold()
        s = checked_path(actual['path']).stat()
        ident = (s.st_dev, s.st_ino)
        need(canonical not in paths and ident not in identities, 'DUPLICATE_GATE_ROLE')
        paths.add(canonical)
        identities.add(ident)
        review = json.loads(payload)
        need(actual['sha256'] == ref['sha256'] and review.get('status') == status and review.get('sourceToolSha256') == tool_sha and review.get('sourcePlanSha256') == PLAN_SHA, 'GATE_ROLE_BINDING')
        pins[actual['path']] = actual
        captured[actual['path']] = payload
    return pins, captured


def recheck(pins):
    for name, old in pins.items():
        _, actual = read_checked(name, max(old['bytes'], 1))
        need(actual == old, 'FINAL_INPUT_MOVED:' + name)


def publish_file(work, name, data):
    need('/' not in name and '\\' not in name, 'OUTPUT_NAME')
    need(checked_path(work, directory=True).is_relative_to(checked_path(OUT, directory=True)), 'OUTPUT_CONTAINMENT')
    path = work / name
    with path.open('xb') as handle:
        handle.write(data)
    actual, pin = read_checked(path, len(data))
    need(actual == data, 'SAVED_OUTPUT_READBACK')
    return pin


def snapshot_inputs(work, captured, admitted):
    """Write the actual captured authored bytes, never reopen them as replicas."""
    expected = {pin['path']: pin for pin in admitted.values()}
    rows = []
    for index, (origin, payload) in enumerate(sorted(captured.items())):
        need(origin in expected and sha(payload) == expected[origin]['sha256']
             and len(payload) == expected[origin]['bytes'], 'CAPTURED_INPUT_IDENTITY')
        snapshot = publish_file(work, 'executed-input-%03d.bin' % index, payload)
        rows.append({'origin': expected[origin], 'snapshot': snapshot,
                     'scope': 'captured authored source/plan/control bytes; not OEM archives'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare', action='store_true', help='metadata-only validation; default')
    mode.add_argument('--emit', type=Path, help='exact reviewed source/root one-emission gate')
    args = parser.parse_args()
    original, base, base_jar, pins, captured = inputs()
    own_bytes, own = read_checked(__file__, 1024 * 1024)
    pins[own['path']] = own
    controls, control_bytes = gate(args.emit, own['sha256']) if args.emit is not None else ({}, {})
    for origin, payload in [(own['path'], own_bytes)] + list(control_bytes.items()):
        need(origin not in captured or captured[origin] == payload, 'CAPTURED_PATH_CONFLICT')
        captured[origin] = payload
    # Existing output root must itself pass strong canonical/type checks first.
    root = checked_path(OUT, directory=True)
    need(root.is_relative_to(checked_path(ROOT / 'out', directory=True)), 'OUTPUT_ROOT')
    work = root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex)
    work.mkdir(exist_ok=False)
    checked_path(work, directory=True)
    receipt = {'schema': 'guest-pin-metadata-current-cut/v1', 'status': 'PLAN_ONLY_NO_CANDIDATE',
               'selected': False, 'coldStartOnly': True, 'sourcePins': pins, 'gatePins': controls,
               'target': (OWNER + b'->' + SIGNATURE).decode(), 'instructionRange': [FIRST, END],
               'oplusUnchanged': True, 'compilerOrWriterExecuted': False, 'oemOrPhoneExecuted': False,
               'admission': 'Receipt bytes alone never admit: independently observed terminal0 AND independent actual saved-output review are mandatory. Partial or uncertain final files remain unadmitted.',
               'readIdentityPolicy': {'crossApiExact': ['st_dev', 'st_ino', 'st_size', 'st_mtime_ns'],
                   'pathChannelExact': 'before.st_ctime_ns == after.st_ctime_ns',
                   'fdChannelExact': 'opened.st_ctime_ns == final.st_ctime_ns',
                   'recordedIntegers': 'exact decimal strings; assertion uses original values without rounding',
                   'atimeNotAddedToEquality': True, 'continuingFilesystemLeaseClaimed': False},
               'requiredSelectionConditions': ['All noncore/lifecycle26/local18/endpoint/principal/user/readiness remain separately unbound.',
                   'Removing one known optional caller does not remove or make guest Proxy62 safe.',
                   'Genuine commit/reconciliation/StrongAuth/timeout/auth-bound key/CE/return ownership remains required.']}
    try:
        receipt['executedInputSnapshots'] = snapshot_inputs(work, captured, {**pins, **controls})
        snapshot_pins = {row['snapshot']['path']: row['snapshot'] for row in receipt['executedInputSnapshots']}
        if args.emit is not None:
            dex, receipt['dexProof'] = omit_optional_pin_metadata(original, base)
            jar, receipt['jarProof'] = package(base_jar, dex)
            bad = bytearray(dex)
            bad[2055224] ^= 1  # off-target registers word, valid reseal.
            negative = {}
            for label, altered in [('off-target-code-header', seal(bad)), ('omitted-required-cut', base)]:
                try:
                    verify_candidate(base, altered)
                except Refused as error:
                    negative[label] = str(error)
                else:
                    raise Refused('NEGATIVE_ACCEPTED:' + label)
            receipt['negativeProbes'] = {'scope': 'in-memory verifier copies, not extra emissions or OEM execution', 'refusals': negative}
            recheck(pins)
            recheck(controls)
            recheck(snapshot_pins)
            outputs = receipt['outputs'] = {}
            outputs['classes6-proxy33-pin-metadata.dex'] = publish_file(work, 'classes6-proxy33-pin-metadata.dex', dex)
            outputs['framework-proxy33-pin-metadata.jar'] = publish_file(work, 'framework-proxy33-pin-metadata.jar', jar)
            saved, _ = read_checked(work / 'classes6-proxy33-pin-metadata.dex', len(dex))
            saved_jar, _ = read_checked(work / 'framework-proxy33-pin-metadata.jar', len(jar))
            need(saved == dex and saved_jar == jar, 'FRESH_FORWARD_READBACK')
            verify_candidate(base, saved)
            # Dependency is the fresh actual saved forward, not a source replica.
            inverse = bytearray(saved)
            inverse[FIRST:END] = base[FIRST:END]
            inverse = seal(inverse)
            need(inverse == base, 'ACTUAL_SAVED_FORWARD_INVERSE')
            outputs['classes6-inverse-proxy33.dex'] = publish_file(work, 'classes6-inverse-proxy33.dex', inverse)
            saved_inverse, _ = read_checked(work / 'classes6-inverse-proxy33.dex', len(inverse))
            need(saved_inverse == base, 'FRESH_INVERSE_EXACT_FB8B')
            again = bytearray(saved_inverse)
            again[FIRST:END] = bytes(END - FIRST)
            again = seal(again)
            need(again == saved, 'ACTUAL_SAVED_INVERSE_REAPPLY')
            outputs['classes6-reapplied.dex'] = publish_file(work, 'classes6-reapplied.dex', again)
            saved_again, _ = read_checked(work / 'classes6-reapplied.dex', len(again))
            verify_candidate(base, saved_again)
            inverse_jar, _ = package(base_jar, saved_inverse)
            baseline_jar, _ = package(base_jar, base)
            reapplied_jar, _ = package(base_jar, saved_again)
            need(inverse_jar == baseline_jar and reapplied_jar == saved_jar, 'ACTUAL_JAR_INVERSE_REAPPLY')
            outputs['framework-inverse-deterministic-proxy33.jar'] = publish_file(work, 'framework-inverse-deterministic-proxy33.jar', inverse_jar)
            outputs['framework-reapplied-pin-metadata.jar'] = publish_file(work, 'framework-reapplied-pin-metadata.jar', reapplied_jar)
            receipt['actualSavedOutputDependencies'] = {'inverseInput': outputs['classes6-proxy33-pin-metadata.dex'],
                'reapplyInput': outputs['classes6-inverse-proxy33.dex'], 'inverseExactFb8b': True,
                'reappliedJarExactSavedForward': True, 'dexWriterRoundtrip': False}
            receipt['status'] = 'PASS_UNSELECTED_CURRENT_SOURCE_BYTE_LEAF'
        recheck(pins)
        recheck(controls)
        recheck(snapshot_pins)
        receipt['inputsAndControlsUnchangedBeforePublication'] = True
    except BaseException as error:
        receipt['status'] = 'FAILED_NOT_ADMITTED'
        receipt['failureType'] = type(error).__name__
        try:
            publish_file(work, 'receipt.json', encoded(receipt))
        except BaseException:
            pass  # Never replace the original failure with failure-report I/O.
        raise
    publish_file(work, 'receipt.json', encoded(receipt))
    print(json.dumps({'status': receipt['status'], 'receipt': (work / 'receipt.json').relative_to(ROOT).as_posix()}))


if __name__ == '__main__':
    main()
