"""Nothing OS ringtones on a phone that is not a Nothing Phone (3).

NothingGenerateRingtoneService builds every ringtone from the vendor kits, a
Glyph pattern (libgenerative_glyph) and a haptic track (libaudio2vib).
libaudio2vib's RichTap generator only starts on a Nothing Phone (3):
RichtapGenerator_init reads ro.product.vendor.device (its name decoded at run
time, not a plain string) and looks for Nothing's name in it; on the Fold the
value is Samsung's ("failed, key: ro.product.vendor.device, value:q8q",
"RichTapGenerator not init!"), and the service stopped after 3 of its 10
ringtones (runs 17-18: Nothing Signals empty). The prop is the phone's own and
Samsung's services read it, so it stays; the check's branch to the failure
("cbnz x8" after strstr, 0x18afdc) becomes the branch to the success path, as
when the name matched. Run 18 tried a renamed plain-string prop: that string
belongs to a second check this path never reaches.

The library is stored uncompressed in the APK, which keeps its size and every
offset: the bytes change in place, then the entry's CRC in the local header and
the central directory. A system app's signature digests are not checked again
(apk-replace-dex.py: only the verity layout is, and nothing moves). The
compiled odex stays valid: it checks the dex, which is untouched.

Usage: nothing_ringtone_device.py <NothingGenerateRingtoneService.apk> <out.apk>
"""
import struct
import sys
import zlib

ENTRY = b"lib/arm64-v8a/libaudio2vib.so"
# In the library: cbnz x8, +0x40 (strstr found Nothing's name) -> b +0x40.
SITE = 0x18afdc
OLD = bytes.fromhex("080200b5")
NEW = bytes.fromhex("10000014")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    # End of central directory, then the entry's central record.
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0:
        sys.exit("no end of central directory")
    count, cd_size, cd_off = struct.unpack_from("<HII", data, eocd + 10)
    p = cd_off
    for _ in range(count):
        if data[p:p + 4] != b"PK\x01\x02":
            sys.exit("bad central directory")
        method, = struct.unpack_from("<H", data, p + 10)
        csize, usize = struct.unpack_from("<II", data, p + 20)
        nlen, xlen, clen = struct.unpack_from("<HHH", data, p + 28)
        loff, = struct.unpack_from("<I", data, p + 42)
        name = bytes(data[p + 46:p + 46 + nlen])
        if name == ENTRY:
            break
        p += 46 + nlen + xlen + clen
    else:
        sys.exit("%s not in the APK" % ENTRY.decode())
    if method != 0 or csize != usize:
        sys.exit("%s is compressed, cannot patch in place" % ENTRY.decode())
    lnlen, lxlen = struct.unpack_from("<HH", data, loff + 26)
    start = loff + 30 + lnlen + lxlen
    body = data[start:start + usize]
    if b"Java_com_appaac_haptic_RichtapGenerator_init" not in body or body[SITE:SITE + 4] != OLD:
        sys.exit("unexpected libaudio2vib build (no cbnz at %#x), not patching" % SITE)
    body[SITE:SITE + 4] = NEW
    data[start:start + usize] = body
    crc = zlib.crc32(body) & 0xFFFFFFFF
    struct.pack_into("<I", data, loff + 14, crc)   # local header
    struct.pack_into("<I", data, p + 16, crc)      # central directory
    open(dst, "wb").write(data)
    print("built %s (libaudio2vib RichTap init without the Nothing device check)" % dst)


if __name__ == "__main__":
    main()
