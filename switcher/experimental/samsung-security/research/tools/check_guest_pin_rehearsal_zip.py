"""Compare an unsigned SystemUI split rehearsal against its donor ZIP."""

from hashlib import sha256
import re
import struct
import zlib

from read_guest_pin_rehearsal_zip import parse_layout


TARGET = 'classes3.dex'
APPENDED = 'classes10.dex'
ORIGINAL_DEX = ('classes.dex', *(f'classes{index}.dex' for index in range(2, 10)))
ALIGN_TAG = 0xd935
ZIP_ALIGNMENT = 4
NATIVE_ALIGNMENT = 16384
ORIGINAL_EXTRA = struct.pack('<HHH', ALIGN_TAG, 2, ZIP_ALIGNMENT)


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def central(data, row):
    return data[row['centralOffset']:row['centralEnd']]


def signer_entry(name):
    upper = name.upper()
    if not upper.startswith('META-INF/'):
        return False
    leaf = upper.removeprefix('META-INF/')
    return '/' not in leaf and (leaf == 'MANIFEST.MF' or leaf.startswith('SIG-')
                                or leaf.endswith(('.RSA', '.DSA', '.EC', '.SF')))


def extra_with_padding(size):
    need(0 <= size <= 0xffff - 6, 'ZIP alignment extension exceeds the local extra bound')
    return struct.pack('<HHH', ALIGN_TAG, 2 + size, ZIP_ALIGNMENT) + b'\0' * size


def verify_stored_payload(candidate, row, expected, label):
    need(row['packed'] == row['size'] == len(expected)
         and candidate[row['dataOffset']:row['dataEnd']] == expected,
         label + ' stored payload differs')
    need(zlib.crc32(expected) & 0xffffffff == row['crc'], label + ' CRC differs')


def verify_target(donor, candidate, before, after, replacement):
    old_at, new_at = before['localOffset'], after['localOffset']
    need(old_at == new_at and before['method'] == after['method'] == 0
         and before['flags'] == after['flags'] == 0x800
         and before['descriptorOffset'] is after['descriptorOffset'] is None,
         'Replacement must keep its exact stored local slot')
    need(donor[old_at:old_at + 14] == candidate[new_at:new_at + 14]
         and donor[old_at + 26:old_at + 28] == candidate[new_at + 26:new_at + 28]
         and before['nameBytes'] == after['nameBytes'], 'Original replacement local header drift')
    growth = len(replacement) - before['size']
    padding = -growth % NATIVE_ALIGNMENT
    previous_padding = len(before['localExtra']) - len(ORIGINAL_EXTRA)
    need(previous_padding >= 0 and before['localExtra'] == extra_with_padding(previous_padding)
         and before['alignment'] == ZIP_ALIGNMENT and before['centralExtra'] == after['centralExtra']
         and after['localExtra'] == extra_with_padding(previous_padding + padding)
         and after['dataOffset'] == before['dataOffset'] + padding,
         'Replacement local alignment TLV differs from the exact zero extension')
    need(zlib.crc32(donor[before['dataOffset']:before['dataEnd']]) & 0xffffffff == before['crc'],
         'Donor replacement-entry CRC differs')
    verify_stored_payload(candidate, after, replacement, 'Replacement DEX')
    return growth + padding, padding


def verify_append(donor, candidate, target, row, addition):
    at = row['localOffset']
    new_central = central(candidate, row)
    old_central = central(donor, target)
    need(row['method'] == 0 and row['flags'] == 0x800 and row['descriptorOffset'] is None
         and row['packed'] == row['size'] == len(addition),
         'Appended DEX does not use the fixed stored profile')
    need(candidate[at + 4:at + 14] == donor[target['localOffset'] + 4:target['localOffset'] + 14]
         and new_central[4:16] == old_central[4:16]
         and new_central[34:42] == old_central[34:42]
         and new_central[32:34] == b'\0\0' and row['centralExtra'] == ORIGINAL_EXTRA,
         'Appended DEX ZIP metadata differs from the fixed profile')
    minimal_data_start = at + 30 + len(row['nameBytes']) + len(ORIGINAL_EXTRA)
    padding = -minimal_data_start % ZIP_ALIGNMENT
    need(row['localExtra'] == extra_with_padding(padding)
         and row['dataOffset'] == minimal_data_start + padding,
         'Appended DEX alignment extra is not the minimal exact TLV')
    verify_stored_payload(candidate, row, addition, 'Appended DEX')


def verify_alignment(rows):
    stored = [row for row in rows if row['method'] == 0]
    need(all(row['dataOffset'] % ZIP_ALIGNMENT == 0 for row in stored),
         'Stored entry lost four-byte alignment')
    libraries = [row for row in rows if row['name'].startswith('lib/') and row['name'].endswith('.so')]
    need(libraries and all(row['method'] == 0 and row['alignment'] == NATIVE_ALIGNMENT
                           and row['dataOffset'] % NATIVE_ALIGNMENT == 0 for row in libraries),
         'Original native library page alignment differs')
    resources = [row for row in rows if row['name'] == 'resources.arsc']
    need(len(resources) == 1 and resources[0]['method'] == 0
         and resources[0]['dataOffset'] % ZIP_ALIGNMENT == 0, 'Resource table alignment differs')
    return len(stored), len(libraries)


def verify(donor: bytes, candidate: bytes, replacement: bytes, addition: bytes) -> dict:
    """Read back saved bytes without invoking or reconstructing the writer."""
    need(type(replacement) is bytes and replacement and type(addition) is bytes and addition,
         'Expected nonempty exact replacement and appended payload bytes')
    source = parse_layout(donor, signed_donor=True)
    result = parse_layout(candidate, signed_donor=False)
    old_rows, new_rows = source['rows'], result['rows']
    old_names = tuple(row['name'] for row in old_rows)
    new_names = tuple(row['name'] for row in new_rows)
    need(len(set(old_names)) == len(old_names) and APPENDED not in old_names
         and new_names == (*old_names, APPENDED), 'Original ZIP entries/order or appended slot differs')
    dex_pattern = re.compile(r'classes(?:[1-9][0-9]*)?\.dex\Z')
    need(tuple(name for name in old_names if dex_pattern.fullmatch(name)) == ORIGINAL_DEX,
         'Original nine DEX members differ')
    need(not any(signer_entry(name) for name in new_names), 'V1 signer payload present')

    old_block = source['signingBlockOffset']
    old_padding = source['signingPaddingBytes']
    need(old_block is not None and source['entriesEnd'] + old_padding == old_block,
         'Original signed APK tail differs')
    need(result['signingBlockOffset'] is None and result['signingPaddingBytes'] == 0
         and result['entriesEnd'] == result['centralOffset'], 'Unsigned candidate has extra tail bytes')
    old_end, new_end = source['eocdOffset'], result['eocdOffset']
    need(donor[old_end:old_end + 8] == candidate[new_end:new_end + 8]
         and donor[old_end + 20:] == candidate[new_end + 20:], 'EOCD disk fields or archive comment changed')

    old_view, new_view = memoryview(donor), memoryview(candidate)
    target_index = old_names.index(TARGET)
    target = old_rows[target_index]
    shift, padding = verify_target(old_view, new_view, target, new_rows[target_index], replacement)
    for index, (before, after) in enumerate(zip(old_rows, new_rows)):
        name = before['name']
        old_central, new_central = central(old_view, before), central(new_view, after)
        if index == target_index:
            need(old_central[:16] == new_central[:16] and old_central[28:42] == new_central[28:42]
                 and old_central[46:] == new_central[46:], 'Replacement central metadata drift')
            continue
        need(old_central[:42] == new_central[:42] and old_central[46:] == new_central[46:],
             'Original central metadata drift: ' + name)
        delta = shift if index > target_index else 0
        need(after['localOffset'] == before['localOffset'] + delta
             and after['dataOffset'] == before['dataOffset'] + delta
             and after['localEnd'] == before['localEnd'] + delta,
             'Original local record relocation drift: ' + name)
        need(old_view[before['localOffset']:before['localEnd']] ==
             new_view[after['localOffset']:after['localEnd']], 'Original local record bytes drift: ' + name)

    appended = new_rows[-1]
    need(appended['localOffset'] == source['entriesEnd'] + shift
         and appended['localEnd'] == result['entriesEnd'], 'Unexpected appended ZIP placement or gap')
    verify_append(old_view, new_view, target, appended, addition)
    stored_count, libraries_count = verify_alignment(new_rows)
    return {
        'status': 'PASS_UNSIGNED_PIN_REHEARSAL_ZIP_RAW_COMPARISON',
        'donorSha256': sha256(donor).hexdigest(), 'candidateSha256': sha256(candidate).hexdigest(),
        'candidateBytes': len(candidate), 'entryCount': len(new_names),
        'untouchedLocalRecords': len(old_names) - 1, 'originalCentralRecordsChecked': len(old_names),
        'storedFourByteAligned': stored_count, 'nativeSixteenKiBAligned': libraries_count,
        'resourcesStoredFourByteAligned': True,
        'entries': {
            TARGET: {'sha256': sha256(replacement).hexdigest(), 'bytes': len(replacement),
                     'dataOffset': new_rows[target_index]['dataOffset']},
            APPENDED: {'sha256': sha256(addition).hexdigest(), 'bytes': len(addition), 'dataOffset': appended['dataOffset']},
        },
        'targetLocalZeroPaddingBytes': padding, 'originalSuffixShiftBytes': shift,
        'omittedDonorSigningBlockBytes': source['centralOffset'] - old_block,
        'omittedDonorSigningPaddingBytes': old_padding, 'storedDexCrcsVerified': True,
        'v1SignerEntries': 0, 'archiveCommentExact': True,
        'selected': False, 'deviceEligible': False, 'targetExecuted': False,
    }
