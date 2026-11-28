"""PC-only classic ZIP composition from three literal immutable binary inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import struct
import time
import uuid
import zipfile
import zlib

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'out/guest-metrics-services-bundle'
ORIGINAL = ROOT.parent / 'firmware/donor/extracted/system/framework/services.jar'
PRIMARY_RUN = ROOT / 'out/guest-metrics-parent-payload/20261106T011052061685Z-ba932ae76594455e9b3447d7f836693b'
PRIMARY = PRIMARY_RUN / 'dex/guest-metrics-parent-forward.dex'
HELPER_RUN = ROOT / 'out/guest-metrics-helper-bundle/20261106T010206436165Z-b58fefe14ac64199be1948e64047da4e'
HELPER = HELPER_RUN / 'dex/classes.dex'
OFF_READER = ROOT / 'tools/build_guest_metrics_helper_bundle.py'
PINS = {
    ORIGINAL: '66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3',
    PRIMARY: 'a93fe9b89a0d1f247f47072df8ce24de9060be9efcd9bfac1d69a75d8a678c9b',
    PRIMARY_RUN / 'receipt.json': '12dd669e55098626ac5d1c93593517d084a41b3a91709fc3b4d8d44aaa4bbe8a',
    HELPER: '11fd05dcd1a69ce6b8fb0e585f5ae573c8cbadc929713a29afcf36d0831dc7c8',
    HELPER_RUN / 'receipt.json': 'fdd4f61908be3ff473654d6121b625a942dcd91468df6a4fa5fcfc6eac6c5504',
    OFF_READER: 'f4e4d43dec3ddd5e89556a94e5af44abc7dc51c07f1f52151866f2a22bec8cea',
}
PREFIX = 'Lcom/appleexploit/oneos/security/authority/'
HELPERS = {PREFIX + name + ';' for name in (
    'PreparedGuestMetricsParentCell', 'PreparedGuestMetricsParentCell$PhaseDisposition',
    'PreparedGuestMetricsParentCell$RetirementDisposition', 'PreparedGuestMetricsEndpoint',
    'PreparedGuestMetricsProducer', 'PreparedGuestMetricsProducer$Sample', 'PreparedGuestMetricsProducer$1')}
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_ENTRY = 32 * 1024 * 1024


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bounded(path, limit):
    need(path.stat().st_size <= limit, 'Input/output size bound')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit, 'Input grew beyond bound')
    return data


def admit(freeze):
    need(freeze.resolve().is_relative_to(WORK.resolve()), 'Own source freeze required')
    value = json.loads(freeze.read_text())
    need(value.get('schema') == 'guest-metrics-services-bundle-source/v1' and value.get('frozen') is True,
         'Explicit frozen source required')
    need(value.get('toolSha256') == sha(__file__), 'Reviewed source changed')
    need(isinstance(value.get('review'), str) and 1 <= len(value['review']) <= 1500 and
         not value['review'].startswith('PENDING'), 'Independent source clearance required')
    for path, pin in PINS.items():
        need(sha(path) == pin, 'Literal binary/tool/receipt input changed: ' + str(path))
    return value


def dex_names(data):
    """Read ordinary complete DEX039 bytes only; no container rebasing."""
    need(112 <= len(data) <= MAX_ENTRY and data[:8] == b'dex\n039\0', 'Exact ordinary DEX039 required')
    def u32(p):
        need(0 <= p <= len(data) - 4, 'DEX integer extent')
        return struct.unpack_from('<I', data, p)[0]
    need((u32(32), u32(36), u32(40)) == (len(data), 112, 0x12345678), 'DEX header')
    need(hashlib.sha1(data[32:]).digest() == data[12:32] and
         zlib.adler32(data[12:]) & 0xffffffff == u32(8), 'DEX integrity')
    for count, offset, width in [(u32(56), u32(60), 4), (u32(64), u32(68), 4), (u32(96), u32(100), 32)]:
        need(count <= 200000 and 112 <= offset <= len(data) and offset + count * width <= len(data), 'DEX table extent')
    names = []
    for i in range(u32(96)):
        type_index = u32(u32(100) + i * 32)
        need(type_index < u32(64), 'DEX class type index')
        string_index = u32(u32(68) + type_index * 4)
        need(string_index < u32(56), 'DEX descriptor index')
        cursor = u32(u32(60) + string_index * 4)
        for _ in range(5):
            need(cursor < len(data), 'DEX string extent')
            byte = data[cursor]
            cursor += 1
            if byte < 128:
                break
        else:
            raise ValueError('DEX string length')
        end = data.find(b'\0', cursor, min(len(data), cursor + 2048))
        need(end >= cursor, 'DEX descriptor bound')
        name = data[cursor:end].decode('ascii')
        need(name.startswith('L') and name.endswith(';'), 'DEX class descriptor')
        names.append(name)
    need(len(names) == len(set(names)), 'Duplicate class definition inside DEX')
    return names


def extra_ok(data, local=False):
    cursor = 0
    while cursor < len(data):
        # The pinned archive has zipalign-style suffix padding in local extras.
        # Central-directory extras remain strict TLV; no bytes are normalized.
        if local and 1 <= len(data) - cursor <= 3 and not any(data[cursor:]):
            return
        need(cursor + 4 <= len(data), 'ZIP extra framing')
        tag, size = struct.unpack_from('<HH', data, cursor)
        cursor += 4
        need(tag != 1 and cursor + size <= len(data), 'ZIP64/extra extent unsupported')
        cursor += size


def inspect_zip(data):
    """Require classic ZIP, contiguous original local records and central directory."""
    need(22 <= len(data) <= MAX_ARCHIVE, 'ZIP archive bound')
    end = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    need(end >= 0 and end + 22 <= len(data), 'ZIP end record')
    e = struct.unpack_from('<4s4H2IH', data, end)
    need(e[1:3] == (0, 0) and e[3] == e[4] and 1 <= e[4] <= 256 and
         end + 22 + e[7] == len(data) and e[6] + e[5] == end, 'Classic single-disk ZIP without trailing bytes')
    rows = []
    cursor = e[6]
    seen = set()
    for _ in range(e[4]):
        need(cursor + 46 <= end and data[cursor:cursor + 4] == b'PK\x01\x02', 'ZIP central record')
        fields = struct.unpack_from('<4s6H3I5H2I', data, cursor)
        made, version, flags, method, clock, date, crc, packed, size, nl, xl, cl, disk, internal, external, offset = fields[1:]
        length = 46 + nl + xl + cl
        need(cursor + length <= end and disk == 0 and flags & ~0x808 == 0 and method in (0, 8) and
             packed <= MAX_ENTRY and size <= MAX_ENTRY and version <= 20, 'ZIP entry flags/method/bounds')
        raw_name = data[cursor + 46:cursor + 46 + nl]
        name = raw_name.decode('utf-8' if flags & 0x800 else 'cp437')
        parts = name.rstrip('/').split('/')
        need(1 <= len(raw_name) <= 512 and '\\' not in name and '\0' not in name and ':' not in name and
             not name.startswith('/') and all(p not in ('', '.', '..') for p in parts) and name not in seen,
             'Canonical unique non-traversing ZIP name required')
        seen.add(name)
        need((external >> 16) & 0xf000 in (0, 0x4000, 0x8000), 'Non-file ZIP member unsupported')
        extra_ok(data[cursor + 46 + nl:cursor + 46 + nl + xl])
        rows.append({'name': name, 'rawName': raw_name, 'central': data[cursor:cursor + length],
                     'offset': offset, 'flags': flags, 'method': method, 'clock': clock, 'date': date,
                     'crc': crc, 'packed': packed, 'size': size})
        cursor += length
    need(cursor == end and sum(row['size'] for row in rows) <= MAX_ARCHIVE, 'ZIP directory/expanded bound')
    physical = 0
    for index, row in enumerate(rows):
        offset = row['offset']
        need(offset == physical and offset + 30 <= e[6], 'ZIP local order/gap/overlap')
        local = struct.unpack_from('<4s5H3I2H', data, offset)
        need(local[0] == b'PK\x03\x04' and local[1:6] == struct.unpack_from('<5H', row['central'], 6), 'ZIP local metadata')
        nl, xl = local[9:]
        start = offset + 30 + nl + xl
        finish = start + row['packed']
        next_offset = rows[index + 1]['offset'] if index + 1 < len(rows) else e[6]
        need(data[offset + 30:offset + 30 + nl] == row['rawName'] and finish <= next_offset <= e[6], 'ZIP local name/extent')
        extra_ok(data[offset + 30 + nl:start], local=True)
        values = (row['crc'], row['packed'], row['size'])
        if row['flags'] & 8:
            need(local[6:9] in ((0, 0, 0), values), 'ZIP descriptor local sizes')
            descriptor = data[finish:next_offset]
            need((len(descriptor) == 12 and struct.unpack('<3I', descriptor) == values) or
                 (len(descriptor) == 16 and descriptor[:4] == b'PK\x07\x08' and struct.unpack('<3I', descriptor[4:]) == values),
                 'ZIP exact classic data descriptor')
        else:
            need(local[6:9] == values and finish == next_offset, 'ZIP exact stored-size extent')
        row['local'] = data[offset:next_offset]
        row['dataStart'] = start - offset
        physical = next_offset
    need(physical == e[6], 'ZIP local data termination')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        need(archive.namelist() == [r['name'] for r in rows], 'Independent ZIP entry order')
        for row in rows:
            with archive.open(row['name']) as stream:
                raw = stream.read(MAX_ENTRY + 1)
            need(len(raw) == row['size'] and zlib.crc32(raw) & 0xffffffff == row['crc'], 'ZIP bounded bytes/CRC')
            row['bytes'] = raw
    return rows, data[end:]


def compose(rows, end, primary, helper, append_name):
    chunks = []
    central = []
    offset = 0
    for row in rows:
        local = row['local']
        record = bytearray(row['central'])
        if row['name'] == 'classes2.dex':
            need(row['method'] == 0 and row['flags'] == 0, 'Pinned replacement must be plain stored')
            local = bytearray(local[:row['dataStart']])
            crc = zlib.crc32(primary) & 0xffffffff
            struct.pack_into('<3I', local, 14, crc, len(primary), len(primary))
            struct.pack_into('<3I', record, 16, crc, len(primary), len(primary))
            local = bytes(local) + primary
        struct.pack_into('<I', record, 42, offset)
        chunks.append(local)
        central.append(bytes(record))
        offset += len(local)
    name = append_name.encode('ascii')
    crc = zlib.crc32(helper) & 0xffffffff
    local = struct.pack('<4s5H3I2H', b'PK\x03\x04', 20, 0, 0, 0, 33, crc, len(helper), len(helper), len(name), 0) + name + helper
    record = struct.pack('<4s6H3I5H2I', b'PK\x01\x02', 0x314, 20, 0, 0, 0, 33, crc, len(helper), len(helper), len(name), 0, 0, 0, 0, 0x81a40000, offset) + name
    chunks.append(local)
    central.append(record)
    offset += len(local)
    directory = b''.join(central)
    final = bytearray(end)
    struct.pack_into('<HHII', final, 8, len(central), len(central), len(directory), offset)
    result = b''.join(chunks) + directory + final
    need(len(result) <= MAX_ARCHIVE, 'Composed archive bound')
    return result


def verify(data, rows, end, primary, helper, append_name, original_names):
    current, current_end = inspect_zip(data)
    need([r['name'] for r in current] == [r['name'] for r in rows] + [append_name], 'Output names/order')
    need(current_end[22:] == end[22:], 'Archive comment changed')
    for before, after in zip(rows, current):
        a, b = bytearray(before['central']), bytearray(after['central'])
        a[42:46] = b[42:46] = b'\0' * 4
        if before['name'] == 'classes2.dex':
            a[16:28] = b[16:28] = b'\0' * 12
            need(after['bytes'] == primary, 'Wrong primary DEX replacement')
            x, y = bytearray(before['local'][:before['dataStart']]), bytearray(after['local'][:after['dataStart']])
            x[14:26] = y[14:26] = b'\0' * 12
            need(x == y, 'Target local metadata changed beyond CRC/sizes')
        else:
            need(before['local'] == after['local'] and before['bytes'] == after['bytes'], 'Original non-target bytes/header/descriptor changed')
        need(a == b, 'Original central metadata changed beyond admitted offset/target integrity')
    need(current[-1]['bytes'] == helper, 'Wrong appended helper')
    all_names = set()
    dex_rows = []
    for row in current:
        if re.fullmatch(r'classes(?:[2-9][0-9]*)?\.dex', row['name']):
            names = dex_names(row['bytes'])
            need(not all_names.intersection(names), 'Cross-DEX definition collision')
            all_names.update(names)
            dex_rows.append({'name': row['name'], 'bytes': len(row['bytes']), 'sha256': digest(row['bytes']), 'classCount': len(names)})
    need(all_names == original_names | HELPERS, 'Complete original plus seven definition closure')
    return current, dex_rows


def build(freeze):
    source = admit(freeze)
    freeze_pin = sha(freeze)
    started = time.monotonic()
    work = WORK / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex)
    work.mkdir(parents=True, exist_ok=False)
    print(json.dumps({'runHandle': work.relative_to(ROOT).as_posix(), 'compilerOrOemExecution': False}), flush=True)
    original, primary, helper = bounded(ORIGINAL, MAX_ARCHIVE), bounded(PRIMARY, MAX_ENTRY), bounded(HELPER, MAX_ENTRY)
    need(all(digest(data) == PINS[p] for p, data in [(ORIGINAL, original), (PRIMARY, primary), (HELPER, helper)]), 'Pinned read changed')
    rows, end = inspect_zip(original)
    dex_rows = [r for r in rows if r['name'].endswith('.dex')]
    expected = ['classes.dex'] + ['classes' + str(i) + '.dex' for i in range(2, len(dex_rows) + 1)]
    need([r['name'] for r in dex_rows] == expected and len(dex_rows) == 4, 'Original contiguous DEX entry sequence')
    append_name = 'classes' + str(len(dex_rows) + 1) + '.dex'
    original_names = set()
    for row in dex_rows:
        names = dex_names(row['bytes'])
        need(not original_names.intersection(names), 'Original cross-DEX duplicates')
        original_names.update(names)
        if row['name'] == 'classes2.dex':
            need(set(names) == set(dex_names(primary)), 'Original primary class definition set changed')
    need(set(dex_names(helper)) == HELPERS and not original_names.intersection(HELPERS), 'Exact seven helpers disjoint from all originals')
    off = runpy.run_path(str(OFF_READER))['off_proof'](HELPER)
    artifacts = []
    for filename in ['services-prepared.jar', 'services-reproduced.jar']:
        data = compose(rows, end, primary, helper, append_name)
        path = work / filename
        with path.open('xb') as stream:
            stream.write(data)
        saved = bounded(path, MAX_ARCHIVE)
        verified, outputs = verify(saved, rows, end, primary, helper, append_name, original_names)
        need(saved == data, 'Saved archive differs')
        artifacts.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(saved), 'bytes': len(saved)})
    need(artifacts[0]['sha256'] == artifacts[1]['sha256'] and bounded(work / 'services-prepared.jar', MAX_ARCHIVE) == bounded(work / 'services-reproduced.jar', MAX_ARCHIVE), 'Two writes not byte-identical')
    need(admit(freeze) == source and sha(freeze) == freeze_pin and time.monotonic() - started <= 45, 'Input/source drift or elapsed bound')
    signatures = [r['name'] for r in rows if r['name'].upper().startswith('META-INF/') and
                  (re.search(r'\.(SF|RSA|DSA|EC)$', r['name'].upper()) or r['name'].upper().split('/')[-1].startswith('SIG-'))]
    result = {'schema': 'guest-metrics-services-bundle/v1', 'status': 'PASS_PC_COMPOSITION_FIXED_OFF_UNSELECTED',
              'work': work.relative_to(ROOT).as_posix(), 'sourceFreeze': source, 'sourceFreezeSha256': freeze_pin,
              'literalInputPins': {str(p): pin for p, pin in PINS.items()}, 'inputPinsVerifiedBeforeAfter': True,
              'artifacts': artifacts, 'twoWritesByteIdentical': True, 'reopenedAndVerifiedBothSavedArchives': True,
              'entryCountBefore': len(rows), 'entryCountAfter': len(verified), 'appendedEntry': append_name,
              'originalClassCount': len(original_names), 'outputClassCount': len(original_names) + 7,
              'dexEntries': outputs, 'helperOffProof': off,
              'entryPreservation': [{'name': r['name'], 'sha256': digest(r['bytes']), 'localRecordSha256': digest(r['local']),
                                     'centralRecordSha256': digest(r['central']), 'targetReplacement': r['name'] == 'classes2.dex'} for r in rows],
              'metaInfEntriesPreserved': [r['name'] for r in rows if r['name'].upper().startswith('META-INF/')],
              'signatureEntries': signatures, 'signatureOrOemAuthenticityVerified': False,
              'signatureLimit': 'Existing META-INF bytes are preserved. No resigning/verification occurs; any signature covering changed contents cannot be claimed valid. ZIP CRC/DEX checksums prove integrity only.',
              'subprocesses': [], 'compilerOrOemExecution': False, 'parentClientIncluded': False,
              'primaryHelperMerge': False, 'oneOsPipelineInvoked': False, 'phoneChanged': False,
              'runtimeSelected': False, 'elapsedSeconds': time.monotonic() - started,
              'limits': ['PC ZIP composition only; no ART/loader/OEM authenticity or device acceptance',
                         'Public cell stays fixed OFF; all seven helpers remain separate appended DEX',
                         'Actual SDK resource APK/OneOS0.4.57 patch composition/DMS services-loader/native/current-parent/retire control remain unselected required gates']}
    receipt = work / 'receipt.json'
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'inventory/guest-metrics-services-bundle.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'receipt': receipt.relative_to(ROOT).as_posix(),
                      'receiptSha256': sha(receipt), 'artifact': artifacts[0]}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        admit(args.freeze)
        print(json.dumps({'literalPinsValid': True, 'archiveBuilt': False}))
    else:
        build(args.freeze)
