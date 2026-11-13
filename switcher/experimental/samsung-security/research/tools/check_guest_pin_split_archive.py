"""Read the held APK and check a proposed split DEX layout without building an APK."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import unicodedata
from uuid import uuid4
import zipfile

from prepare_guest_policy_init_retarget import owned
from run_full_apk_build import dex_defined_classes


ROOT = Path(__file__).resolve().parents[1]
APK = ROOT.parent / 'firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk'
APK_SHA = '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'
APK_SIZE = 116_521_421
READER_SHA = '50d8aeefee395571ceadc48c914a148817cf83baea6986effd2681b3a9647eb5'
SPLIT_RECEIPT = ('out/guest-pin-worker-return-retarget/r-80cbb577/receipt.json',
                 '99efda3723f4a18184b198e6fc8c1eeb7b31d20ac43d63d2d65b09c0374f86cb')
HELPER_RECEIPT = ('out/guest-pin-final-callback-build/r-32a284d7/receipt.json',
                  'c0b1df054f8f9d36c621bc03220d21ef2789555eed9203162ae0d35291a8dd40')
REPLACEMENT = ('firmware/guest-pin-worker-return-retarget/r-80cbb577/disabled-classes3.dex',
               'a5f9b014ff14b06f796bd8bb19a3388fd4b562ef9bcd1d635029a3ec26fa8612')
ADDITION = ('out/guest-pin-final-callback-build/r-32a284d7/dex/classes.dex',
            'fa8acc549e57ece7892073e60675d764df80d48bd02dbec5e165cf5bb29f2a98')
LOCAL_HEADER = struct.Struct('<4s5H3I2H')
MAX_ENTRY = 32 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def root_dex_entries(archive, expected_count):
    require(1 <= expected_count <= 100, 'DEX member count outside bound')
    expected = ['classes.dex', *(f'classes{index}.dex' for index in range(2, expected_count + 1))]
    found = {}
    aliases = set()
    for item in archive.infolist():
        name = item.filename
        path = name.removesuffix('/')
        parts = path.split('/')
        require(name == item.orig_filename and '\0' not in name and '\\' not in name
                and all(part not in ('', '.', '..') and ':' not in part for part in parts),
                'Unsafe archive member name')
        alias = unicodedata.normalize('NFC', path).casefold()
        require(alias not in aliases, 'Duplicate or aliased archive member')
        aliases.add(alias)
        if len(parts) == 1 and path.casefold().endswith('.dex'):
            require(name in expected and item.compress_type == zipfile.ZIP_STORED
                    and not item.flag_bits & 9, 'Unexpected root DEX member or storage mode')
            found[name] = item
    require(set(found) == set(expected), 'Root DEX members must be contiguous')
    return [found[name] for name in expected]


def stored_payload_offset(archive, entry, alignment):
    stream = archive.fp
    require(stream is not None and entry.compress_type == zipfile.ZIP_STORED and not entry.flag_bits & 9,
            'Expected an open archive and stored member')
    prior = stream.tell()
    try:
        require(0 <= entry.header_offset <= archive.start_dir - LOCAL_HEADER.size, 'Invalid local header offset')
        stream.seek(entry.header_offset)
        raw = stream.read(LOCAL_HEADER.size)
        require(len(raw) == LOCAL_HEADER.size, 'Truncated local header')
        magic, _, flags, method, _, _, crc, compressed, size, name_len, extra_len = LOCAL_HEADER.unpack(raw)
        expected_name = entry.filename.encode('utf-8' if entry.flag_bits & 0x800 else 'cp437')
        require(magic == b'PK\x03\x04' and flags == entry.flag_bits and method == entry.compress_type
                and crc == entry.CRC and compressed == entry.compress_size and size == entry.file_size
                and compressed == size and name_len == len(expected_name), 'Local and central headers differ')
        require(stream.read(name_len) == expected_name, 'Local member name differs')
        offset = entry.header_offset + LOCAL_HEADER.size + name_len + extra_len
        limit = min((item.header_offset for item in archive.infolist() if item.header_offset > entry.header_offset),
                    default=archive.start_dir)
        require(offset % alignment == 0 and offset + size <= min(limit, archive.start_dir),
                'Stored payload extent or alignment differs')
        return offset
    finally:
        stream.seek(prior)


def stored_dex_offset(archive, entry):
    return stored_payload_offset(archive, entry, 4)


def held(pin, limit):
    name, expected = pin
    path = owned(ROOT / name, ROOT / Path(name).parts[0])
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit and digest(raw) == expected, 'Pinned input differs: ' + name)
    return raw


def inspect():
    split = json.loads(held(SPLIT_RECEIPT, 256 * 1024))
    helper = json.loads(held(HELPER_RECEIPT, 256 * 1024))
    replacement = held(REPLACEMENT, MAX_ENTRY)
    addition = held(ADDITION, MAX_ENTRY)
    held(('tools/run_full_apk_build.py', READER_SHA), 2 * 1024 * 1024)
    require(split['status'] == 'PASS_UNSELECTED_DONOR_PIN_WORKER_RETURN_DEX_ONLY'
            and helper['status'] == 'PASS_UNSELECTED_PIN_FINAL_CALLBACK_WORKER_SDK37_D8_ONLY'
            and split['selected'] is False and helper['selected'] is False
            and split['deviceEligible'] is False and helper['deviceEligible'] is False
            and split['targetExecuted'] is False and helper['androidOrOemExecuted'] is False
            and split['proposedDexPlacement'] == {'classes3.dex': REPLACEMENT[0], 'classes10.dex': ADDITION[0]}
            and split['outputSha256'] == REPLACEMENT[1] and split['bytes'] == len(replacement)
            and helper['dex']['sha256'] == ADDITION[1] and helper['dex']['bytes'] == len(addition),
            'Split placement or held receipts differ')

    owners = {}
    donor_rows = []
    preserved = hashlib.sha256()
    preserved_entries = 0
    signing_entries = 0
    named = {}
    native_offsets = []
    with APK.open('rb') as stream:
        require(APK.stat().st_size == APK_SIZE and hashlib.file_digest(stream, 'sha256').hexdigest() == APK_SHA,
                'Held donor archive differs')
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            require(len(entries) == 8449 and sum(item.file_size for item in entries) <= 512 * 1024 * 1024,
                    'Donor archive size or member count differs')
            dex_entries = root_dex_entries(archive, 9)
            for item in dex_entries:
                require(112 <= item.file_size <= MAX_ENTRY, 'Donor DEX extent outside bound')
                offset = stored_dex_offset(archive, item)
                raw = archive.read(item)
                names = dex_defined_classes(raw)
                require(not owners.keys() & names, 'Class definition occurs in more than one donor DEX')
                owners.update((name, item.filename) for name in names)
                donor_rows.append({'member': item.filename, 'bytes': len(raw), 'sha256': digest(raw),
                                   'dataOffset': offset, 'definitions': len(names)})
            dex_names = {item.filename for item in dex_entries}
            for item in sorted(entries, key=lambda entry: entry.filename):
                name = item.filename
                if name in dex_names:
                    continue
                upper = name.upper()
                if upper.startswith('META-INF/') and '/' not in upper[9:] and (
                        upper.endswith(('.SF', '.RSA', '.DSA', '.EC'))
                        or upper == 'META-INF/MANIFEST.MF' or upper[9:].startswith('SIG-')):
                    signing_entries += 1
                    continue
                require(item.file_size <= MAX_ENTRY, 'Donor payload member outside bound')
                with archive.open(item) as payload:
                    item_digest = hashlib.file_digest(payload, 'sha256').hexdigest()
                row = [name, item.file_size, item_digest]
                preserved.update(json.dumps(row, ensure_ascii=True, separators=(',', ':')).encode('ascii') + b'\n')
                preserved_entries += 1
                if name in {'AndroidManifest.xml', 'resources.arsc'}:
                    named[name] = {'bytes': item.file_size, 'sha256': item_digest}
                if name.startswith('lib/arm64-v8a/') and name.endswith('.so'):
                    native_offsets.append(stored_payload_offset(archive, item, 16 * 1024))
    require(len(owners) == 73080 and len(named) == 2, 'Donor class, manifest or resource inventory differs')
    require(len(native_offsets) == 8 and all(offset > donor_rows[2]['dataOffset'] for offset in native_offsets),
            'Donor arm64 alignment or placement differs')
    replaced_names = {name for name, member in owners.items() if member == 'classes3.dex'}
    added_names = dex_defined_classes(addition)
    require(dex_defined_classes(replacement) == replaced_names and len(added_names) == 21
            and not owners.keys() & added_names, 'Planned split class ownership differs')
    replacement_growth = len(replacement) - donor_rows[2]['bytes']
    return {'schema': 'oneos-guest-pin-split-archive-preflight/v1',
            'status': 'PASS_PLANNED_SPLIT_ARCHIVE_LAYOUT_ONLY',
            'donor': {'bytes': APK_SIZE, 'sha256': APK_SHA, 'zipEntries': 8449, 'dexMembers': donor_rows,
                      'definitions': len(owners), 'namedPayloads': named,
                      'passThroughPayloads': preserved_entries, 'passThroughPayloadSha256': preserved.hexdigest(),
                      'excludedV1SigningEntries': signing_entries, 'storedArm64Libraries': len(native_offsets)},
            'proposed': {'replace': {'member': 'classes3.dex', 'path': REPLACEMENT[0], 'sha256': REPLACEMENT[1],
                                     'bytes': len(replacement), 'definitions': len(replaced_names)},
                         'add': {'member': 'classes10.dex', 'path': ADDITION[0], 'sha256': ADDITION[1],
                                 'bytes': len(addition), 'definitions': len(added_names)},
                         'definitions': len(owners) + len(added_names), 'dexMembers': 10,
                         'requiredDexStorage': 'stored', 'requiredDexDataAlignmentBytes': 4,
                         'requiredArm64DataAlignmentBytes': 16 * 1024, 'replacementGrowthBytes': replacement_growth,
                         'minimumExtraBytesIfShiftingRemainingEntriesTogether': -replacement_growth % (16 * 1024)},
            'inputReceipts': dict((SPLIT_RECEIPT, HELPER_RECEIPT)),
            'assembled': False, 'signed': False, 'loaded': False, 'selected': False, 'deviceEligible': False}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = inspect()
    base = ROOT / 'out/guest-pin-split-archive'
    run = owned(base / ('r-' + uuid4().hex[:8]), base)
    run.mkdir(parents=True)
    receipt = run / 'receipt.json'
    with receipt.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(f"{result['status']} {receipt}")


if __name__ == '__main__':
    main()
