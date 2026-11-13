"""Read the classic ZIP layout for the offline donor archive rehearsal."""

import struct


_EOCD = struct.Struct('<4s4H2IH')
_CENTRAL = struct.Struct('<4s6H3I5H2I')
_LOCAL = struct.Struct('<4s5H3I2H')
_DESCRIPTOR = struct.Struct('<4s3I')
_MAX_ARCHIVE = 256 * 1024 * 1024
_MAX_ENTRY = 32 * 1024 * 1024
_MAX_ENTRIES = 16384
_MAX_SIGNING_BLOCK = 1024 * 1024


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _alignment(extra):
    offset = 0
    alignment = None
    while offset < len(extra):
        _require(offset + 4 <= len(extra), 'Truncated ZIP extra header')
        tag, size = struct.unpack_from('<HH', extra, offset)
        offset += 4
        end = offset + size
        _require(tag != 1 and end <= len(extra), 'ZIP64 or truncated ZIP extra data')
        if tag == 0xd935:
            _require(alignment is None and size >= 2, 'Malformed or duplicate ZIP alignment extra')
            alignment, = struct.unpack_from('<H', extra, offset)
            _require(alignment in (4, 16384) and not any(extra[offset + 2:end]),
                     'Unsupported ZIP alignment declaration or padding')
        offset = end
    return alignment


def _signing_block_offset(data, central):
    _require(central >= 32 and data[central - 16:central] == b'APK Sig Block 42',
             'Missing APK Signing Block footer')
    size, = struct.unpack_from('<Q', data, central - 24)
    start = central - size - 8
    _require(24 <= size <= _MAX_SIGNING_BLOCK and start >= 0 and
             struct.unpack_from('<Q', data, start)[0] == size, 'Invalid APK Signing Block size')
    cursor = start + 8
    end = central - 24
    identifiers = set()
    while cursor < end:
        _require(cursor + 12 <= end, 'Truncated APK Signing Block pair')
        pair_size, identifier = struct.unpack_from('<QI', data, cursor)
        _require(4 < pair_size <= end - cursor - 8 and identifier not in identifiers,
                 'Invalid or duplicate APK Signing Block pair')
        identifiers.add(identifier)
        cursor += 8 + pair_size
    _require(identifiers, 'Empty APK Signing Block')
    return start


def parse_layout(data: bytes, *, signed_donor: bool) -> dict:
    """Return record metadata and absolute, end-exclusive offsets.

    This checks ZIP structure and alignment without inflating payloads or
    verifying APK signatures. The caller owns payload and archive identity.
    """
    _require(type(data) is bytes and type(signed_donor) is bool and
             _EOCD.size <= len(data) <= _MAX_ARCHIVE, 'Invalid ZIP input or archive size')
    eocd = len(data) - _EOCD.size
    magic, disk, start_disk, disk_count, count, central_size, central, comment = _EOCD.unpack_from(data, eocd)
    _require(magic == b'PK\x05\x06' and disk == start_disk == comment == 0 and
             disk_count == count and 0 < count <= _MAX_ENTRIES and
             0 < central < eocd and central + central_size == eocd,
             'Expected a classic single-disk ZIP without archive comment or trailing bytes')
    signing = _signing_block_offset(data, central) if signed_donor else None
    local_limit = central if signing is None else signing

    rows = []
    names = set()
    central_cursor = central
    local_cursor = 0
    for _ in range(count):
        _require(central_cursor + _CENTRAL.size <= eocd, 'Truncated ZIP central record')
        (signature, _, version, flags, method, clock, date, crc, packed, size,
         name_len, extra_len, comment_len, entry_disk, _, external, local) = (
            _CENTRAL.unpack_from(data, central_cursor))
        name_start = central_cursor + _CENTRAL.size
        name_end = name_start + name_len
        extra_end = name_end + extra_len
        central_end = extra_end + comment_len
        descriptor = bool(flags & 8)
        _require(signature == b'PK\x01\x02' and central_end <= eocd and
                 0 < name_len <= 1024 and entry_disk == 0 and version <= 20 and
                 flags & ~0x808 == 0 and method in (0, 8) and
                 packed <= _MAX_ENTRY and size <= _MAX_ENTRY and
                 (method != 0 or (packed == size and not descriptor)),
                 'Unsupported ZIP central record')
        name_bytes = data[name_start:name_end]
        name = name_bytes.decode('utf-8' if flags & 0x800 else 'cp437')
        directory = name.endswith('/')
        parts = (name[:-1] if directory else name).split('/')
        _require(name not in names and '\\' not in name and ':' not in name and
                 all(ord(ch) >= 32 for ch in name) and all(part not in ('', '.', '..') for part in parts),
                 'Duplicate or noncanonical ZIP entry name')
        file_type = (external >> 16) & 0xf000
        _require(file_type in (0, 0x4000 if directory else 0x8000) and
                 (not directory or (method == 0 and crc == packed == size == 0)),
                 'Unsupported ZIP entry type')
        names.add(name)

        _require(local == local_cursor and local + _LOCAL.size <= local_limit,
                 'ZIP local record gap, overlap, or extent')
        local_header = _LOCAL.unpack_from(data, local)
        _require(local_header[:6] == (b'PK\x03\x04', version, flags, method, clock, date) and
                 local_header[9] == name_len, 'ZIP local and central headers disagree')
        local_name = local + _LOCAL.size
        local_extra_start = local_name + name_len
        payload = local_extra_start + local_header[10]
        data_end = payload + packed
        local_end = data_end + (_DESCRIPTOR.size if descriptor else 0)
        _require(local_end <= local_limit and data[local_name:local_extra_start] == name_bytes,
                 'ZIP local name or payload extent differs')
        expected = (crc, packed, size)
        if descriptor:
            _require(local_header[6:9] in ((0, 0, 0), expected) and
                     _DESCRIPTOR.unpack_from(data, data_end) == (b'PK\x07\x08', *expected),
                     'Invalid signed ZIP data descriptor')
        else:
            _require(local_header[6:9] == expected, 'ZIP local CRC or sizes disagree')

        local_extra = data[local_extra_start:payload]
        central_extra = data[name_end:extra_end]
        alignment = _alignment(local_extra)
        _require(alignment == _alignment(central_extra) and
                 (alignment is None or (method == 0 and payload % alignment == 0)),
                 'ZIP alignment metadata or payload offset differs')
        rows.append({'name': name, 'nameBytes': name_bytes, 'centralOffset': central_cursor,
                     'centralEnd': central_end, 'localOffset': local, 'dataOffset': payload,
                     'dataEnd': data_end, 'localEnd': local_end, 'packed': packed, 'size': size,
                     'crc': crc, 'flags': flags, 'method': method, 'alignment': alignment,
                     'localExtra': local_extra, 'centralExtra': central_extra,
                     'descriptorOffset': data_end if descriptor else None})
        central_cursor = central_end
        local_cursor = local_end

    _require(central_cursor == eocd and sum(row['size'] for row in rows) <= _MAX_ARCHIVE,
             'Unexpected ZIP central directory bytes or expanded extent')
    padding = local_limit - local_cursor
    if signed_donor:
        _require(0 <= padding <= 4095 and not any(data[local_cursor:local_limit]),
                 'Invalid gap before APK Signing Block')
    else:
        _require(padding == 0, 'Unexpected unsigned ZIP tail before central directory')
    return {'rows': tuple(rows), 'entriesEnd': local_cursor, 'centralOffset': central,
            'eocdOffset': eocd, 'signingBlockOffset': signing, 'signingPaddingBytes': padding}
