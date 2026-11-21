#!/usr/bin/env python3
"""Generate the fixed APK patch for hiding One UI 9.5's status bar media chip."""

import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import struct
import zipfile
import zlib


# invokeSuspend(Object) in MediaControlChipInteractor$mediaControlChipModel$1.
# Its normal return is the media model; redirect it to the existing null path.
ORIGINAL = bytes.fromhex(
    "54 30 e6 89 55 31 e7 89 62 02 6d c2 52 33 e8 89 12 02 "
    "39 03 09 00 71 10 7c e4 04 00 38 01 03 00 11 00 11 02 "
    "1b 03 7d af 02 00 71 10 97 eb 03 00 11 02"
)
MODEL_RETURN = 32


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def patch(apk):
    def word(offset):
        return struct.unpack_from("<I", apk, offset)[0]

    with zipfile.ZipFile(BytesIO(apk)) as archive:
        entry = archive.getinfo("classes.dex")
        dex = archive.read(entry)
    local = entry.header_offset
    flags, method = struct.unpack_from("<HH", apk, local + 6)
    if flags & 8 or method != zipfile.ZIP_STORED or word(local + 14) != entry.CRC:
        raise ValueError("Expected a stored classes.dex with its CRC in the local header")
    name_bytes, extra_bytes = struct.unpack_from("<HH", apk, local + 26)
    dex_start = local + 30 + name_bytes + extra_bytes

    code = dex.find(ORIGINAL)
    if code < 0 or dex.find(ORIGINAL, code + 1) >= 0:
        raise ValueError("Expected exactly one media-chip model gate")
    if struct.unpack_from("<I", dex, code - 4)[0] != len(ORIGINAL) // 2:
        raise ValueError("Media-chip model method length differs from the donor")
    dex = bytearray(dex)
    dex[code + MODEL_RETURN + 1] = 2  # return-object v0 -> return-object v2 (null)
    head = 0
    while head < len(dex):
        if dex[head:head + 8] != b"dex\n041\0":
            raise ValueError("Expected DEX 041")
        size = struct.unpack_from("<I", dex, head + 32)[0]
        if size < 120 or head + size > len(dex):
            raise ValueError("Invalid DEX section size")
        end = head + size
        if head <= code < end:
            dex[head + 12:head + 32] = hashlib.sha1(dex[head + 32:end]).digest()
            struct.pack_into("<I", dex, head + 8, zlib.adler32(dex[head + 12:end]))
            break
        head = end
    else:
        raise ValueError("Media-chip method outside the DEX container")

    eocd = len(apk) - 22
    if apk[eocd:eocd + 4] != b"PK\x05\x06":
        raise ValueError("Expected a ZIP with no comment")
    central = word(eocd + 16)
    while central < eocd and apk[central:central + 4] == b"PK\x01\x02":
        if word(central + 42) == local:
            break
        central += 46 + sum(struct.unpack_from("<HHH", apk, central + 28))
    else:
        raise ValueError("classes.dex is missing from the central directory")
    crc = struct.pack("<I", zlib.crc32(dex))
    edits = [
        (local + 14, crc),
        (dex_start + head + 8, bytes(dex[head + 8:head + 32])),
        (dex_start + code + MODEL_RETURN + 1, b"\x02"),
        (central + 16, crc),
    ]
    result = bytearray(apk)
    for offset, replacement in edits:
        result[offset:offset + len(replacement)] = replacement
    return result, edits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    apk_path = args.apk
    original = apk_path.read_bytes()
    patched, edits = patch(original)
    args.output.write_bytes(patched)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip():
            raise ValueError("Rewritten APK failed CRC verification")
    print(f"Source SHA-256: {sha256(original)}")
    print(f"Output SHA-256: {sha256(patched)}")
    for offset, replacement in edits:
        octal = "".join(f"\\{byte:03o}" for byte in replacement)
        print(f"printf '{octal}' | $BB dd of=\"$2\" bs=1 seek={offset} conv=notrunc 2>/dev/null")
