"""HyperOS SurfaceFlinger: no Xring metadata query without Xiaomi's mapper.

DolbyRenderer::requiresDolbyEffect (libsurfaceflinger.so, RenderEngine, every
layer the GPU draws) asks the buffer's "xring.graphics.XringMetadataType"
metadata through a mapper object it keeps at this+0x7360, without checking it.
That object is Xiaomi's (its XRING chip's stable-C mapper); on a Galaxy with
older vendor software (S24 Ultra, S23, A57: vendor API 33/34) its loader
leaves it null, and SurfaceFlinger died at the first GPU-composed frame
(SIGSEGV, fault addr 0x40: the call through null+0x40). 0.4.38 reports
548e7b73, 609d7c2f, 709f72bc; 0.4.39 944b2952 with the shader pre-warm off,
the same crash in drawLayers. The Z Fold8 Ultra's vendor has it.

The four instructions after the buffer's incStrong become: load the mapper,
if null take the function's own "no buffer handle" exit (0x6792d4: return
false, decStrong), then the two calls one slot later. The null check of
GraphicBuffer::toAHardwareBuffer's result goes: it is the GraphicBuffer itself
seen as an AHardwareBuffer, never null for a buffer that is there.

Only for the exact build: every word in the range is checked first.
Usage: hyperos_dolby_mapper.py <libsurfaceflinger.so in> <out>
"""
import struct
import sys

BASE = 0x679014  # file offset == vaddr in this segment (LOAD 0x350000 at 0x350000)
TO_AHB = 0xC66EA0        # GraphicBuffer::toAHardwareBuffer@plt
GET_HANDLE = 0xC69760    # AHardwareBuffer_getNativeHandle@plt
NO_HANDLE_EXIT = 0x6792D4  # mov w20, wzr; ldr x0, [sp]; ... decStrong; b 0x679078
LDR_MAPPER = 0xF979B2BC  # ldr x28, [x21, #0x7360]


def bl(pc, target):
    return 0x94000000 | (((target - pc) >> 2) & 0x3FFFFFF)


def cbz_x(rt, pc, target):
    return 0xB4000000 | ((((target - pc) >> 2) & 0x7FFFF) << 5) | rt


ORIG = [
    bl(BASE + 0, TO_AHB),             # bl toAHardwareBuffer
    cbz_x(0, BASE + 4, NO_HANDLE_EXIT),  # cbz x0, 0x6792d4
    bl(BASE + 8, GET_HANDLE),         # bl AHardwareBuffer_getNativeHandle
    LDR_MAPPER,                       # ldr x28, [x21, #0x7360]
    0xF0FFD901,                       # adrp x1, 0x19c000 (unchanged, checked)
    0x913CDC21,                       # add x1, x1, #0xf37 ("xring.graphics.XringMetadataType")
    0x52800102,                       # mov w2, #0x8
    0xAA1F03E3,                       # mov x3, xzr
    0xAA1F03E4,                       # mov x4, xzr
    0xF9402388,                       # ldr x8, [x28, #0x40]  (the faulting load)
]
NEW = [
    LDR_MAPPER,
    cbz_x(28, BASE + 4, NO_HANDLE_EXIT),  # cbz x28, 0x6792d4
    bl(BASE + 8, TO_AHB),
    bl(BASE + 12, GET_HANDLE),
] + ORIG[4:]


def main(src, dst):
    d = bytearray(open(src, "rb").read())
    got = list(struct.unpack_from("<%dI" % len(ORIG), d, BASE))
    if got == NEW:
        sys.exit(f"{src}: already patched")
    if got != ORIG:
        sys.exit(f"{src}: not the expected build at {BASE:#x}: " + " ".join(f"{w:08x}" for w in got))
    if struct.unpack_from("<I", d, NO_HANDLE_EXIT)[0] != 0x2A1F03F4:  # mov w20, wzr
        sys.exit(f"{src}: the exit at {NO_HANDLE_EXIT:#x} is not the expected one")
    struct.pack_into("<%dI" % len(NEW), d, BASE, *NEW)
    open(dst, "wb").write(d)
    print(f"{dst}: requiresDolbyEffect returns false without the Xring mapper (4 words at {BASE:#x})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
