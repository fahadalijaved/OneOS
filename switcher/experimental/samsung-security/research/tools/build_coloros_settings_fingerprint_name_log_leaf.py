"""Derive an unselected Settings DEX with one enrollment-name log removed."""

from hashlib import sha256
import json
from uuid import uuid4
from zipfile import ZipFile

from build_coloros_settings_rpmb_leaf import ROOT, SOURCE, SOURCE_SHA, digest, header, seal
from settings_fingerprint_name_log_location import locate


OWNER = 'Lcom/oplus/settings/feature/fingerprint/OplusFingerprintSettings$FingerprintSettingsFragment;'
METHOD = 'addFingerprintItemPreferences(Ljava/util/List;)V'
ENTRY = 'classes2.dex'
DEX_BYTES = 5_737_616
SOURCE_DEX_SHA = 'f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21'
OUTPUT_DEX_SHA = 'bea7993c428bb828a75882b525e744cf6f22a51cf1ca41ad6d8c89919ac5207b'
SOURCE_BODY_SHA = '32bd72b7c34534e711ae43776ad744a4f7914fad103939b829aea25da7e32284'
SLICE_SHA = 'ac8ce72525f41e208a514a3a519b833d01bdf23e5ced0bee5b0fe2b310c17cd2'
FIRST_PC, END_PC = 86, 110
FIRST_BYTE, END_BYTE = 0x187A7C, 0x187AAC


def patch_dex(original: bytes) -> tuple[bytes, dict]:
    """Patch only the exact source image, and prove the whole-image inverse."""
    if type(original) is not bytes or len(original) != DEX_BYTES or sha256(original).hexdigest() != SOURCE_DEX_SHA:
        raise ValueError('Expected the exact original ColorOS Settings classes2.dex')
    location, ownership = locate(original)
    if (location['byteStart'], location['byteEndExclusive']) != (FIRST_BYTE, END_BYTE):
        raise ValueError('Decoded fingerprint name log location differs')
    original_log = original[FIRST_BYTE:END_BYTE]
    if sha256(original_log).hexdigest() != SLICE_SHA:
        raise ValueError('Original fingerprint name log bytes differ')
    nops = b'\0' * len(original_log)
    patched = seal(original[:FIRST_BYTE] + nops + original[END_BYTE:])
    header(patched)
    if sha256(patched).hexdigest() != OUTPUT_DEX_SHA:
        raise ValueError('Settings fingerprint name-log DEX differs from the reviewed result')
    if (patched[:8] != original[:8] or patched[32:FIRST_BYTE] != original[32:FIRST_BYTE]
            or patched[FIRST_BYTE:END_BYTE] != nops or patched[END_BYTE:] != original[END_BYTE:]):
        raise ValueError('Bytes outside the approved name log and DEX integrity fields changed')
    restored = seal(patched[:FIRST_BYTE] + original_log + patched[END_BYTE:])
    if restored != original or seal(restored[:FIRST_BYTE] + nops + restored[END_BYTE:]) != patched:
        raise ValueError('Settings name-log inverse or roundtrip differs')
    return patched, {
        'owner': OWNER, 'signature': METHOD, 'sourceNormalizedBodySha256': SOURCE_BODY_SHA,
        'firstPc': FIRST_PC, 'endExclusivePc': END_PC, 'firstByte': FIRST_BYTE, 'endExclusiveByte': END_BYTE,
        'sourceSliceSha256': SLICE_SHA, 'location': location, 'ownership': ownership,
        'inverseExact': True, 'roundtripExact': True,
    }


def build():
    if digest(SOURCE) != SOURCE_SHA:
        raise ValueError('Expected the exact donor Settings APK')
    with ZipFile(SOURCE) as archive:
        names = archive.namelist()
        if len(names) != 10_549 or len(names) != len(set(names)) or archive.getinfo(ENTRY).file_size != DEX_BYTES:
            raise ValueError('Donor Settings archive shape differs')
        original = archive.read(ENTRY)
    patched, method = patch_dex(original)
    if digest(SOURCE) != SOURCE_SHA:
        raise ValueError('Donor Settings APK changed while reading')

    base = ROOT / 'out/settings-fingerprint-name-log-leaf'
    if base.resolve() != base:
        raise ValueError('Settings leaf output escapes the expected repository path')
    run = base / ('r-' + uuid4().hex[:8])
    run.mkdir(parents=True)
    dex = run / 'classes2.dex'
    with dex.open('xb') as stream:
        stream.write(patched)
    if dex.stat().st_size != DEX_BYTES or digest(dex) != OUTPUT_DEX_SHA:
        raise ValueError('Settings name-log DEX readback differs')
    receipt = {
        'schema': 'oneos-coloros-settings-fingerprint-name-log-leaf/v1',
        'status': 'PASS_EXACT_UNSELECTED_SETTINGS_FINGERPRINT_NAME_LOG_LEAF',
        'sourceArchive': {'path': SOURCE.relative_to(ROOT.parent).as_posix(),
                          'bytes': SOURCE.stat().st_size, 'sha256': SOURCE_SHA},
        'sourceDex': {'entry': ENTRY, 'bytes': DEX_BYTES, 'sha256': SOURCE_DEX_SHA},
        'outputDex': {'path': dex.relative_to(ROOT).as_posix(), 'bytes': DEX_BYTES, 'sha256': OUTPUT_DEX_SHA},
        'method': method,
        'selected': False, 'deviceAction': False, 'targetExecuted': False,
    }
    path = run / 'receipt.json'
    with path.open('x', encoding='ascii', newline='\n') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    return path


if __name__ == '__main__':
    output = build()
    print(output.relative_to(ROOT).as_posix(), digest(output))
