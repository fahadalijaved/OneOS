"""In-memory regression tests for the unsigned file-stage host assembler."""

import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile
import zlib

from package_file_stage_early_exit_host import compose_host_apk


ROOT = Path(__file__).resolve().parents[1]
READINESS = 'out/file-stage-readiness-package/r-6c688c4ff1'
SUCCESSOR = 'out/file-stage-early-exit-host-dex/r-cbc36dc3'
PAYLOADS = (
    'AndroidManifest.xml',
    'resources.arsc',
    'classes.dex',
    'META-INF/xposed/module.prop',
    'META-INF/xposed/scope.list',
    'META-INF/xposed/java_init.list',
)


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pinned(name, sha256, size):
    with (ROOT / name).open('rb') as stream:
        raw = stream.read(size + 1)
    require(len(raw) == size and digest(raw) == sha256, 'Fixture pin differs: ' + name)
    return raw


def read_unsigned(raw):
    """Check local extents independently of the assembler's ZIP reader."""
    footer = len(raw) - 22
    fields = struct.unpack_from('<4s4H2IH', raw, footer)
    require(fields[:5] == (b'PK\x05\x06', 0, 0, 6, 6) and fields[-1] == 0, 'Expected classic footer')
    central = fields[6]
    require(central + fields[5] == footer, 'Unexpected central extent')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(archive.namelist() == list(PAYLOADS), 'Payload names or order changed')
        require(archive.start_dir == central, 'Unexpected ZIP prefix or central offset')
        cursor = 0
        for entry in archive.infolist():
            require(entry.header_offset == cursor and raw[cursor:cursor + 4] == b'PK\x03\x04',
                    'Local entries must be contiguous')
            name_len, extra_len = struct.unpack_from('<HH', raw, cursor + 26)
            start = cursor + 30 + name_len + extra_len
            require(start % 4 == 0 and entry.compress_type == zipfile.ZIP_STORED and entry.flag_bits == 0,
                    'Unsigned entry must be aligned and stored without flags')
            cursor = start + entry.compress_size
        require(cursor == central, 'Unsigned archive has a signing block or other local gap')
        return {name: archive.read(name) for name in PAYLOADS}


def alter_scope(raw):
    """Alter the scope payload without causing a ZIP/CRC failure."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entry = archive.getinfo(PAYLOADS[4])
        local = entry.header_offset
        central = archive.start_dir
    name_len, extra_len = struct.unpack_from('<HH', raw, local + 26)
    start = local + 30 + name_len + extra_len
    scope = raw[start:start + entry.file_size]
    require(scope == b'android\n', 'Expected original android scope')
    changed = b'xndroid\n'
    result = bytearray(raw)
    result[start:start + len(scope)] = changed
    crc = zlib.crc32(changed)
    struct.pack_into('<I', result, local + 14, crc)
    for name in PAYLOADS:
        size, extra, comment = struct.unpack_from('<HHH', raw, central + 28)
        require(raw[central:central + 4] == b'PK\x01\x02'
                and raw[central + 46:central + 46 + size] == name.encode('ascii'), 'Expected central entry')
        if name == entry.filename:
            struct.pack_into('<I', result, central + 16, crc)
            return bytes(result)
        central += 46 + size + extra + comment
    raise AssertionError('Missing central scope entry')


def add_signing_like_gap(raw):
    footer = len(raw) - 22
    central = struct.unpack_from('<I', raw, footer + 16)[0]
    # The envelope has the two size fields and magic, but no signer data.
    gap = struct.pack('<QQ16s', 24, 24, b'APK Sig Block 42')
    result = bytearray(raw[:central] + gap + raw[central:])
    struct.pack_into('<I', result, footer + len(gap) + 16, central + len(gap))
    return bytes(result)


def rejects(label, predecessor, dex, pins):
    try:
        compose_host_apk(predecessor, dex, pins)
    except ValueError:
        return
    raise AssertionError('Accepted ' + label)


def main():
    readiness = json.loads(read_pinned(READINESS + '/receipt.json',
        '63892c552dee93bc017731ddd4aec8b0c51b7809bb472d54f6faaafc1bdecabb', 61609))
    build = json.loads(read_pinned(SUCCESSOR + '/receipt.json',
        'df536331acbc472ec8159b588457777a81b0b739d7c513eaffcdd819933ecee0', 57350))
    host = readiness['packages']['host']
    old, new = host['unsignedApk'], build['dex']
    require(old['path'] == READINESS + '/host/OneOS-File-View-Host-Readiness-unsigned.apk'
            and new['path'] == SUCCESSOR + '/dex/classes.dex', 'Fixture role path differs')
    predecessor = read_pinned(old['path'], old['sha256'], old['bytes'])
    successor_dex = read_pinned(new['path'], new['sha256'], new['bytes'])
    pins = host['payloadPins']
    original = read_unsigned(predecessor)
    require({name: digest(data) for name, data in original.items()} == pins, 'Exact original payload pins differ')
    require(successor_dex != original['classes.dex'], 'Expected distinct successor DEX')

    output, report = compose_host_apk(predecessor, successor_dex, pins)
    require(compose_host_apk(predecessor, successor_dex, pins) == (output, report), 'Assembly is not deterministic')
    require(read_unsigned(output) == {**original, 'classes.dex': successor_dex}, 'Only DEX replacement is allowed')

    rejects('old DEX in the successor role', predecessor, original['classes.dex'], pins)
    rejects('malformed successor DEX', predecessor, b'bad\0' + successor_dex[4:], pins)
    scope_changed = alter_scope(predecessor)
    require(read_unsigned(scope_changed) == {**original, PAYLOADS[4]: b'xndroid\n'}, 'Scope mutant is not valid ZIP')
    rejects('changed android scope with original pins', scope_changed, successor_dex, pins)
    rejects('trailing bytes', predecessor + b'extra', successor_dex, pins)
    gap = add_signing_like_gap(predecessor)
    with zipfile.ZipFile(io.BytesIO(gap)) as archive:
        require({name: archive.read(name) for name in archive.namelist()} == original,
                'Signing-gap mutant does not preserve all logical payloads')
    rejects('signing-block-like gap', gap, successor_dex, pins)
    print('FILE_STAGE_EARLY_EXIT_HOST_PACKAGE PASS (1 deterministic assembly, 5 refusals)')


if __name__ == '__main__':
    main()
