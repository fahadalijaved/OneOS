#!/usr/bin/env python3
"""Boot animation on every panel: patch an image's libbootanimation.

Android's bootanimation can draw on every physical display, but only with the
build flag com.android.graphics.bootanimation.flags.multidisplay; without it
BootAnimation::initDisplaysAndSurfaces() drops every display id after the
first:

    if (!flags::multidisplay()) displayIds.erase(displayIds.begin() + 1, displayIds.end());

With the flag fixed off at build time the check is gone and the erase is
unconditional; its only guard is the "begin + 1 == end" test (one display, so
nothing to erase):

    add  xA, xB, #0x8      // begin + 1
    cmp  xA, xC            // == end?
    b.eq skip              // -> b skip: never erase

SurfaceFlinger powers on every display at start (initializeDisplays), so on a
Fold the cover panel is lit during the guest's boot but stayed empty; the
guest's main display is the inner panel, where the animation played unseen
with the phone folded. Each display gets its own surface at its own size and
layer stack, as with the flag on.

The function is found by its symbol, the three instructions by their encoding
(registers and offsets differ per build); exactly one match or nothing is
written. Usage: patch-bootanim-multidisplay.py <lib.so> <out.so>
Exit 0 with a patched file, 2 when the build has no such site (nothing written).
"""
import struct
import sys

SYM = b"_ZN7android13BootAnimation23initDisplaysAndSurfacesEv"


def symbol(data, name):
    """(vaddr, size) of name from .dynsym or .symtab, or None."""
    if data[:4] != b"\x7fELF" or data[4] != 2:
        sys.exit("not an ELF64 file")
    shoff, = struct.unpack_from("<Q", data, 0x28)
    shentsize, shnum = struct.unpack_from("<HH", data, 0x3A)
    secs = [struct.unpack_from("<IIQQQQIIQQ", data, shoff + i * shentsize) for i in range(shnum)]
    for s in secs:
        if s[1] not in (2, 11):  # SHT_SYMTAB, SHT_DYNSYM
            continue
        strtab = secs[s[6]]
        for off in range(s[4], s[4] + s[5], 24):
            st_name, _, _, _, value, size = struct.unpack_from("<IBBHQQ", data, off)
            p = strtab[4] + st_name
            if data[p:p + len(name) + 1] == name + b"\0" and value:
                return value, size
    return None


def file_offset(data, vaddr):
    phoff, = struct.unpack_from("<Q", data, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    for i in range(phnum):
        p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if p_type == 1 and p_vaddr <= vaddr < p_vaddr + p_filesz:
            return vaddr - p_vaddr + p_offset
    sys.exit("%#x is in no loaded segment" % vaddr)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    sym = symbol(data, SYM)
    if sym is None:
        print("bootanimation: no initDisplaysAndSurfaces in %s (older bootanimation), not patched" % src)
        return 2
    start = file_offset(data, sym[0])
    words = [struct.unpack_from("<I", data, start + i)[0] for i in range(0, sym[1] - sym[1] % 4, 4)]
    sites = []
    for i in range(len(words) - 2):
        add, cmp_, beq = words[i:i + 3]
        rd = add & 0x1F
        if ((add & 0xFFFFFC00) == 0x91002000 and           # add xd, xn, #8
                (cmp_ & 0xFFE0FC1F) == 0xEB00001F and       # cmp xd, xm
                (cmp_ >> 5) & 0x1F == rd and
                (beq & 0xFF00001F) == 0x54000000):          # b.eq
            imm19 = (beq >> 5) & 0x7FFFF
            if imm19 & 0x40000:
                imm19 -= 0x80000
            if imm19 > 0:
                sites.append((start + (i + 2) * 4, imm19))
    if len(sites) != 1:
        print("bootanimation: %d candidate sites in initDisplaysAndSurfaces, not patched" % len(sites))
        return 2
    off, imm = sites[0]
    struct.pack_into("<I", data, off, 0x14000000 | (imm & 0x3FFFFFF))  # b skip
    open(dst, "wb").write(data)
    print("built %s (boot animation on every display; b.eq -> b at file offset %#x)" % (dst, off))
    return 0


if __name__ == "__main__":
    sys.exit(main())
