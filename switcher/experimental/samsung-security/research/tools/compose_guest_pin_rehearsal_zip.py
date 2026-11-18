"""Compose the unsigned rehearsal ZIP from already admitted payload bytes."""

from io import BytesIO
import struct
import zlib

from read_guest_pin_rehearsal_zip import parse_layout


TARGET = 'classes3.dex'
ADDITION = b'classes10.dex'
DEX_NAMES = {'classes.dex', *(f'classes{index}.dex' for index in range(2, 10))}
ALIGNMENT_TLV = struct.pack('<HHH', 0xD935, 2, 4)
PAYLOAD_GROWTH = 6716
SUFFIX_SHIFT = 16 * 1024
TARGET_PADDING = SUFFIX_SHIFT - PAYLOAD_GROWTH
MAX_DEX_BYTES = 32 * 1024 * 1024


def compose(donor: bytes, replacement: bytes, addition: bytes) -> bytes:
    """Replace the exact stored DEX, append one stored DEX, and drop the old signing tail."""
    if not all(type(value) is bytes for value in (donor, replacement, addition)):
        raise TypeError('Immutable ZIP and payload bytes required')
    layout = parse_layout(donor, signed_donor=True)
    rows = layout['rows']
    dex_names = {row['name'] for row in rows if '/' not in row['name']
                 and row['name'].startswith('classes') and row['name'].endswith('.dex')}
    if dex_names != DEX_NAMES or len(rows) + 1 >= 0xFFFF:
        raise ValueError('Expected nine original DEX entries and classic ZIP counts')
    target = next(row for row in rows if row['name'] == TARGET)
    if (target['nameBytes'] != TARGET.encode('ascii') or target['method'] != 0 or target['flags'] != 0x800
            or target['packed'] != target['size'] or target['descriptorOffset'] is not None
            or target['alignment'] != 4 or target['dataOffset'] % 4
            or target['localExtra'] != ALIGNMENT_TLV or target['centralExtra'] != ALIGNMENT_TLV
            or target['centralEnd'] - target['centralOffset'] != 46 + len(target['nameBytes']) + len(ALIGNMENT_TLV)):
        raise ValueError('Unexpected stored classes3 ZIP layout')
    if (len(replacement) != target['size'] + PAYLOAD_GROWTH or len(replacement) > MAX_DEX_BYTES
            or not 0 < len(addition) <= MAX_DEX_BYTES):
        raise ValueError('Unexpected replacement or addition payload extent')

    source = memoryview(donor)
    local = target['localOffset']
    central = target['centralOffset']
    if any(row['localOffset'] > local and row['alignment'] is not None
           and SUFFIX_SHIFT % row['alignment'] for row in rows):
        raise ValueError('Fixed suffix shift would change a declared entry alignment')
    replacement_crc = zlib.crc32(replacement)
    replacement_header = bytearray(source[local:target['dataOffset']])
    struct.pack_into('<III', replacement_header, 14, replacement_crc, len(replacement), len(replacement))
    struct.pack_into('<H', replacement_header, 28, len(ALIGNMENT_TLV) + TARGET_PADDING)
    alignment_size_offset = 30 + len(target['nameBytes']) + 2
    struct.pack_into('<H', replacement_header, alignment_size_offset, 2 + TARGET_PADDING)

    output = BytesIO()
    output.write(source[:local])
    output.write(replacement_header)
    output.write(bytes(TARGET_PADDING))
    output.write(replacement)
    output.write(source[target['localEnd']:layout['entriesEnd']])
    addition_offset = output.tell()
    if addition_offset != layout['entriesEnd'] + SUFFIX_SHIFT:
        raise ValueError('Existing suffix did not move by the exact alignment span')

    addition_crc = zlib.crc32(addition)
    padding = -(addition_offset + 30 + len(ADDITION) + len(ALIGNMENT_TLV)) % 4
    addition_extra = struct.pack('<HHH', 0xD935, 2 + padding, 4) + bytes(padding)
    addition_header = bytearray(source[local:local + 30])
    struct.pack_into('<IIIHH', addition_header, 14, addition_crc, len(addition), len(addition),
                     len(ADDITION), len(addition_extra))
    output.write(addition_header)
    output.write(ADDITION)
    output.write(addition_extra)
    output.write(addition)

    central_offset = output.tell()
    for row in rows:
        header = bytearray(source[row['centralOffset']:row['centralEnd']])
        if row is target:
            struct.pack_into('<III', header, 16, replacement_crc, len(replacement), len(replacement))
        elif row['localOffset'] > local:
            struct.pack_into('<I', header, 42, row['localOffset'] + SUFFIX_SHIFT)
        output.write(header)

    addition_central = bytearray(source[central:central + 46])
    struct.pack_into('<IIIHH', addition_central, 16, addition_crc, len(addition), len(addition),
                     len(ADDITION), len(ALIGNMENT_TLV))
    struct.pack_into('<I', addition_central, 42, addition_offset)
    output.write(addition_central)
    output.write(ADDITION)
    output.write(ALIGNMENT_TLV)

    central_size = output.tell() - central_offset
    eocd = bytearray(source[layout['eocdOffset']:])
    struct.pack_into('<HHII', eocd, 8, len(rows) + 1, len(rows) + 1, central_size, central_offset)
    output.write(eocd)
    return output.getvalue()
