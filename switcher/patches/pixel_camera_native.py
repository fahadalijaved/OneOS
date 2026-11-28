"""A guest's native camera client library with One UI's transaction codes.

The native twin of pixel_camera_abi.py (docs/pixel-guest.md, "What differs"):
the guest's legacy camera API (BpCameraService::connect) and the NDK camera2
path are marshalled by /system/lib64/libcamera_client.so, not by framework.jar.
It carries the same differences, which an aarch64 build exposes as immediates:

  - BpCameraService and BpCameraDeviceUser pass the transaction code to
    IBinder::transact as `mov w1, #N` (the last such mov in each Bp method).
    Each becomes One UI's number from the host table (host_camera.txt, the
    same file the Java patcher reads; Bp<Interface> = android.hardware.I<...>).
    A guest-only method (ColorOS's notifySmartWindowChange and
    notifyDisplayRotationChange, both void; 0.4.31: HyperOS's addFaceListener
    and removeFaceListener, which return a result; 0.4.59: vivo OriginOS's
    oneway onFrozenPackage and setVersionName, whose Bp returns on a non-zero
    transact status with `cbnz w0` before any reply read) goes to UNUSED_CODE, which
    One UI answers with "unknown transaction". The C++ Bp code checks that
    status and returns the error without reading a reply (unlike Java's
    Proxy, where pixel_camera_abi.py throws instead); any other one stops
    the build.
  - BnCameraServiceListener / BnCameraDeviceCallbacks::onTransact: a case whose
    code is another method on the host (the Pixel 9 Pro XL's
    onStatusChangedBatched at 9, One UI's onCameraDeviceStateChanged) is
    skipped, so the host's call returns "unknown transaction" and is not
    misparsed. `cmp w1, #N; b.ne X` becomes `b X`, `cmp; b.eq` a nop.
  - libcameracompatbilityinfo.so (the native CameraCompatibilityInfo): a
    build that has shouldOverrideLensFacingFrontToBack (the Pixel 9 Pro XL)
    writes and reads a sixth field, which One UI reads as the next parcelable's
    null marker. The last write and the last read (the call after loading that
    field's offset) become nops.
Every pattern must match exactly once or the build stops (fail closed). An
already patched library gives "unchanged".

Usage: pixel_camera_native.py <host_camera.txt> <in.so> <out.so>
         patches libcamera_client.so or libcameracompatbilityinfo.so
         (told apart by its symbols); writes <out.so> only when it changed
         and prints "changed" on stdout.
       pixel_camera_native.py --dump <lib.so>
         prints "<class> <method> <code>" for every Bp method of the library,
         to diff a host's libcamera_client.so against the guest's.
No dependencies: the ELF symbol table and the encodings are read here.
"""
import os
import re
import struct
import sys

UNUSED_CODE = 200
# Guest-only void or oneway methods (ColorOS; vivo's onFrozenPackage is oneway, flags 1).
# One UI 9.5 (S948BXXU6ZZKN): injectSessionParamsN (9) and notifyPrewarmId (29), both void, which One UI 9.0's cameraserver does not have.
# One UI 8.0/8.5 hosts also lack ICameraService.warmUp (oneway void) and ICameraDeviceUser.updateOutputConfigurations (void, checks transact status with cbnz w0).
GUEST_ONLY_VOID = {
    "notifySmartWindowChange", "notifyDisplayRotationChange", "onFrozenPackage",
    "injectSessionParamsN", "notifyPrewarmId", "warmUp", "updateOutputConfigurations",
}
# Guest-only methods with a result whose Bp returns transact's error status as it is (HyperOS; vivo;
# One UI 8.0/8.5 hosts lack Android 17's ICameraDeviceUser.configureStreams, whose Bp branches on cbnz w0 to Status::setFromStatusT before reading a reply).
GUEST_ONLY_STATUS = {"addFaceListener", "removeFaceListener", "setVersionName", "configureStreams"}
# One UI 9.5: same signature as One UI 9.0's, contents its cameraserver crashes on (pixel_camera_abi.py).
NOT_TO_HOST = {"notifyPkgListParamChange"}
# A One UI 9.5 host (0.5.37, ONEOS_CAMERA_KEEP_COMPAT=1 builds) parses One UI 9.5's lists itself.
if os.environ.get("ONEOS_CAMERA_KEEP_COMPAT") == "1":
    NOT_TO_HOST = set()
# One UI 8.0 hosts (host_camera_oneui8.txt): getCameraInfo, connect, connectDevice, getCameraCharacteristics
# and getSessionCharacteristics take Android 16's int32_t rotationOverride where One UI 9.0/9.5 take a
# CameraCompatibilityInfo parcelable. With ONEOS_CAMERA_COMPAT_AS_INT=1 each BpCameraService method's
# writeParcelable(in_cameraCompatibilityInfo) becomes writeInt32(0) (ROTATION_OVERRIDE_NONE).
COMPAT_AS_INT = os.environ.get("ONEOS_CAMERA_COMPAT_AS_INT") == "1"
CCI_JAVA = "Landroid/content/res/CameraCompatibilityInfo;"
CCI_MANGLED = "23CameraCompatibilityInfo"
SYM_WRITE_IFACE = "_ZN7android6Parcel19writeInterfaceTokenERKNS_8String16E"
SYM_WRITE_PARCELABLE = "_ZN7android6Parcel15writeParcelableERKNS_10ParcelableE"
SYM_WRITE_INT32 = "_ZN7android6Parcel10writeInt32Ei"
NOP = 0xD503201F
BTI_J = 0xD503249F
BTI_JC = 0xD50324DF
MOV_W1_ZERO = 0x52800001
# (interface, mangled namespace, Bp class, Bn class)
AIDL = {
    "android.hardware.ICameraService": ("7android8hardware", "BpCameraService"),
    "android.hardware.camera2.ICameraDeviceUser": ("7android8hardware7camera2", "BpCameraDeviceUser"),
}
CALLBACKS = {
    "android.hardware.ICameraServiceListener": ("7android8hardware", "BpCameraServiceListener", "BnCameraServiceListener"),
    "android.hardware.camera2.ICameraDeviceCallbacks": ("7android8hardware7camera2", "BpCameraDeviceCallbacks", "BnCameraDeviceCallbacks"),
}


def die(msg):
    sys.exit(f"pixel_camera_native: {msg}")


def read_table(path):
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                iface, name, code, sig = line.split(None, 3)
                out.setdefault(iface, {})[name] = (int(code), sig)
    return out


def sign_ext(val, bits):
    return val - (1 << bits) if val & (1 << (bits - 1)) else val


def decode_bl(pc, w):
    if (w & 0xFC000000) != 0x94000000:
        return None
    return pc + sign_ext(w & 0x3FFFFFF, 26) * 4


def encode_bl(pc, target):
    diff = target - pc
    if diff & 3:
        die(f"unaligned BL target {target:#x} from {pc:#x}")
    imm = diff >> 2
    if not (-(1 << 25) <= imm < (1 << 25)):
        die(f"BL target {target:#x} out of range from {pc:#x}")
    return 0x94000000 | (imm & 0x3FFFFFF)


def encode_b(pc, target):
    diff = target - pc
    if diff & 3:
        die(f"unaligned B target {target:#x} from {pc:#x}")
    imm = diff >> 2
    if not (-(1 << 25) <= imm < (1 << 25)):
        die(f"B target {target:#x} out of range from {pc:#x}")
    return 0x14000000 | (imm & 0x3FFFFFF)


class Elf:
    def __init__(self, path):
        self.buf = bytearray(open(path, "rb").read())
        b = self.buf
        if b[:4] != b"\x7fELF" or b[4] != 2 or b[5] != 1 or struct.unpack_from("<H", b, 0x12)[0] != 183:
            die(f"{path}: not an aarch64 ELF64")
        phoff, shoff = struct.unpack_from("<QQ", b, 0x20)
        phentsize, phnum, shentsize, shnum = struct.unpack_from("<HHHH", b, 0x36)
        shstrndx = struct.unpack_from("<H", b, 0x3E)[0]
        self.loads = []
        for i in range(phnum):
            t, _, off, va, _, filesz, _, _ = struct.unpack_from("<IIQQQQQQ", b, phoff + i * phentsize)
            if t == 1:
                self.loads.append((va, off, filesz))
        secs = [struct.unpack_from("<IIQQQQIIQQ", b, shoff + i * shentsize) for i in range(shnum)]
        shstr = secs[shstrndx][4] if shstrndx < len(secs) else 0
        sec_by_name = {}
        if shstr:
            for s in secs:
                end = b.index(b"\0", shstr + s[0])
                sec_by_name[bytes(b[shstr + s[0]:end]).decode()] = s
        self.funcs = {}
        dynsyms = []
        for s in secs:
            if s[1] != 11:  # SHT_DYNSYM
                continue
            stroff = secs[s[6]][4]
            for j in range(s[5] // 24):
                nm, info, _, shndx, val, size = struct.unpack_from("<IBBHQQ", b, s[4] + j * 24)
                e = b.index(b"\0", stroff + nm)
                sname = bytes(b[stroff + nm:e]).decode()
                dynsyms.append(sname)
                if shndx and size and (info & 0xF) == 2:
                    self.funcs.setdefault(sname, []).append((val, size))
        # Map PLT stub addresses to imported symbol names (for Parcel::writeParcelable / writeInt32).
        got_to_sym = {}
        for rname in (".rela.plt", ".rela.dyn"):
            rs = sec_by_name.get(rname)
            if not rs:
                continue
            for j in range(rs[5] // 24):
                r_off, r_info, _ = struct.unpack_from("<QQq", b, rs[4] + j * 24)
                si = r_info >> 32
                if si < len(dynsyms):
                    got_to_sym[r_off] = dynsyms[si]
        self.plt_to_sym = {}
        self.sym_to_plt = {}
        ps = sec_by_name.get(".plt")
        if ps:
            pva, poff, psz = ps[3], ps[4], ps[5]
            for off in range(0, psz - 4, 4):
                w = struct.unpack_from("<I", b, poff + off)[0]
                if (w & 0x9F00001F) == 0x90000010:  # adrp x16, ...
                    w2 = struct.unpack_from("<I", b, poff + off + 4)[0]
                    if (w2 & 0xFFC003FF) == 0xF9400211:  # ldr x17, [x16, #imm]
                        imm = sign_ext((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21)
                        va = pva + off
                        got = ((va & ~0xFFF) + (imm << 12)) + (((w2 >> 10) & 0xFFF) * 8)
                        sym = got_to_sym.get(got)
                        if sym:
                            self.plt_to_sym[va] = sym
                            self.sym_to_plt.setdefault(sym, va)

    def off(self, va):
        for v, o, n in self.loads:
            if v <= va < v + n:
                return va - v + o
        die(f"address {va:#x} is in no segment")

    def words(self, va, size):
        o = self.off(va)
        return [(va + 4 * i, o + 4 * i, struct.unpack_from("<I", self.buf, o + 4 * i)[0]) for i in range(size // 4)]

    def put(self, fileoff, word):
        struct.pack_into("<I", self.buf, fileoff, word)

    def find(self, rx):
        hits = [(n, v) for n, v in self.funcs.items() if re.match(rx, n)]
        return hits


def is_movz_w1(w):
    return (w & 0xFFE0001F) == 0x52800001


def bp_methods(elf, ns, cls):
    """{method: (file offset of its transact mov, code, mangled symbol, (va, size))} of a Bp class."""
    out = {}
    for name, fs in elf.find(rf"^_ZN{ns}{len(cls)}{cls}\d+\w+E"):
        m = re.match(rf"^_ZN{ns}{len(cls)}{cls}(\d+)(\w+)", name)
        n = int(m.group(1))
        meth = m.group(2)[:n]
        if m.group(2)[n:n + 1] != "E" or meth in (cls, "") or meth[0] in "CD" and meth[1:2].isdigit():
            continue
        if len(fs) != 1:
            die(f"{cls}::{meth}: {len(fs)} definitions")
        movs = [(o, w) for _, o, w in elf.words(*fs[0]) if is_movz_w1(w)]
        if not movs:
            die(f"{cls}::{meth}: no mov w1 before transact")
        o, w = movs[-1]
        if meth in out:
            die(f"{cls}::{meth}: overloaded, not handled")
        out[meth] = (o, (w >> 5) & 0xFFFF, name, fs[0])
    if not out:
        die(f"no {cls} methods (stripped or another library)")
    codes = [c for _, c, _, _ in out.values() if c != UNUSED_CODE]
    if len(set(codes)) != len(codes):
        die(f"{cls}: two methods with one code")
    return out


def patch_bp_compat_as_int(elf, cls, meth, sym, fn, changed):
    """Rewrite writeParcelable(CameraCompatibilityInfo) to writeInt32(0) in a BpCameraService method."""
    plt_iface = elf.sym_to_plt.get(SYM_WRITE_IFACE)
    plt_wp = elf.sym_to_plt.get(SYM_WRITE_PARCELABLE)
    plt_wi = elf.sym_to_plt.get(SYM_WRITE_INT32)
    if plt_iface is None or plt_wp is None or plt_wi is None:
        die(f"{cls}::{meth}: missing Parcel PLT imports (iface={plt_iface}, wp={plt_wp}, wi={plt_wi})")
    # Count how many Parcelable input arguments precede the output pointer: CameraCompatibilityInfo is
    # always first among them (followed by SessionConfiguration and/or AttributionSourceState).
    parcelable_markers = (CCI_MANGLED, "20SessionConfiguration", "22AttributionSourceState")
    positions = sorted((sym.index(t), t) for t in parcelable_markers if t in sym)
    if not positions or positions[0][1] != CCI_MANGLED:
        die(f"{cls}::{meth}: CameraCompatibilityInfo is not the first Parcelable input in {sym}")
    expected_wp = len(positions)
    ws = elf.words(*fn)
    iface_hits = [i for i, (pc, _, w) in enumerate(ws) if decode_bl(pc, w) == plt_iface]
    if len(iface_hits) != 1:
        die(f"{cls}::{meth}: {len(iface_hits)} writeInterfaceToken calls (one expected)")
    mov_hits = [i for i, (_, _, w) in enumerate(ws) if is_movz_w1(w)]
    i0, i1 = iface_hits[0], mov_hits[-1]
    wp_hits = [i for i in range(i0 + 1, i1) if decode_bl(ws[i][0], ws[i][2]) == plt_wp]
    if len(wp_hits) == expected_wp - 1:
        # Already patched: confirm a mov w1, #0; bl writeInt32; cbnz w0 sits before the next writeParcelable.
        limit = wp_hits[0] if wp_hits else i1
        already = [
            i for i in range(i0 + 2, limit)
            if ws[i - 1][2] == MOV_W1_ZERO
            and decode_bl(ws[i][0], ws[i][2]) == plt_wi
            and i + 1 < len(ws) and (ws[i + 1][2] & 0xFF00001F) == 0x35000000
        ]
        if len(already) == 1:
            return 0
    if len(wp_hits) != expected_wp:
        die(f"{cls}::{meth}: {len(wp_hits)} writeParcelable calls before transact ({expected_wp} expected)")
    idx = wp_hits[0]
    if idx < 1 or idx + 1 >= len(ws):
        die(f"{cls}::{meth}: unexpected writeParcelable position")
    prev_pc, prev_off, prev_w = ws[idx - 1]
    bl_pc, bl_off, _ = ws[idx]
    nxt_w = ws[idx + 1][2]
    is_mov_x1 = (prev_w & 0xFFE0FFE0) == 0xAA0003E0 and (prev_w & 31) == 1
    is_ldr_x1 = (prev_w & 0xFFC0001F) == 0xF9400001
    if not (is_mov_x1 or is_ldr_x1):
        die(f"{cls}::{meth}: instruction before writeParcelable at {prev_pc:#x} is {prev_w:#x} (expected mov/ldr x1)")
    if (nxt_w & 0xFF00001F) != 0x35000000:  # cbnz w0, ...
        die(f"{cls}::{meth}: instruction after writeParcelable is {nxt_w:#x} (expected cbnz w0)")
    elf.put(prev_off, MOV_W1_ZERO)
    elf.put(bl_off, encode_bl(bl_pc, plt_wi))
    changed.append(f"{cls}::{meth}: CameraCompatibilityInfo written as One UI 8's int32 rotationOverride (0)")
    return 1


def patch_bp(elf, host, changed):
    n = 0
    for iface, (ns, cls) in AIDL.items():
        guest = bp_methods(elf, ns, cls)
        for meth, (o, gcode, sym, fn) in sorted(guest.items()):
            if meth in NOT_TO_HOST:
                hcode, hsig = UNUSED_CODE, None
            elif meth in host[iface]:
                hcode, hsig = host[iface][meth]
            elif meth in GUEST_ONLY_VOID or meth in GUEST_ONLY_STATUS:
                hcode, hsig = UNUSED_CODE, None
            else:
                die(f"{iface}.{meth} ({gcode}) is not in the host table: the host would take it for another method")
            if hsig is not None and CCI_MANGLED in sym and CCI_JAVA not in hsig:
                if not COMPAT_AS_INT:
                    die(f"{iface}.{meth}: guest takes CameraCompatibilityInfo, host expects int ({hsig}); set ONEOS_CAMERA_COMPAT_AS_INT=1")
                n += patch_bp_compat_as_int(elf, cls, meth, sym, fn, changed)
            if hcode == gcode:
                continue
            elf.put(o, 0x52800001 | (hcode << 5))
            changed.append(f"{cls}::{meth}: {gcode} -> {hcode}")
            n += 1
    return n


def find_jump_table(ws):
    """Find Clang/LLVM's aarch64 halfword switch jump table in Bn::onTransact.

    Pattern (e.g. One UI 9.5 BnCameraServiceListener::onTransact):
        sub  wR, w1, #min_code
        ...
        cmp  wR, #max_idx
        ...
        b.hi default_va
        ...
        adr  xT, tbl_va
        adr  xB, base_va
        ldrh wO, [xT, xR, lsl #1]
        add  xB, xB, xO, lsl #2
        br   xB
    Returns (min_code, max_idx, default_va, tbl_va, base_va) or None.
    """
    for i in range(min(40, len(ws) - 4)):
        pc_t, _, w_t = ws[i]
        pc_b, _, w_b = ws[i + 1]
        _, _, w_ldr = ws[i + 2]
        _, _, w_add = ws[i + 3]
        _, _, w_br = ws[i + 4]
        if (w_t & 0x9F000000) != 0x10000000 or (w_b & 0x9F000000) != 0x10000000:
            continue
        rt, rb = w_t & 31, w_b & 31
        if w_br != (0xD61F0000 | (rb << 5)):
            continue
        if (w_ldr & 0xFFE0FC00) != 0x78607800 or ((w_ldr >> 5) & 31) != rt:
            continue
        ro = w_ldr & 31
        rr = (w_ldr >> 16) & 31
        if (w_add & 0xFFE0FC00) not in (0x8B000800, 0x8B200800):
            continue
        if (w_add & 31) != rb or ((w_add >> 5) & 31) != rb or ((w_add >> 16) & 31) != ro:
            continue
        # Walk backwards to find b.hi default_va, cmp wR, #max_idx, and sub wR, w1, #min_code.
        default_va = max_idx = min_code = None
        for j in range(i - 1, -1, -1):
            pc, _, w = ws[j]
            if default_va is None and (w & 0xFF00001F) == 0x54000008:  # b.hi
                default_va = pc + sign_ext((w >> 5) & 0x7FFFF, 19) * 4
            elif max_idx is None and (w & 0xFFC0001F) == 0x7100001F and ((w >> 5) & 31) == rr:  # cmp wR, #imm
                max_idx = (w >> 10) & 0xFFF
            elif min_code is None and (w & 0xFFC003E0) == 0x51000020 and (w & 31) == rr:  # sub wR, w1, #imm
                min_code = (w >> 10) & 0xFFF
        if default_va is None or max_idx is None or min_code is None:
            continue
        tbl_va = pc_t + sign_ext((((w_t >> 5) & 0x7FFFF) << 2) | ((w_t >> 29) & 3), 21)
        base_va = pc_b + sign_ext((((w_b >> 5) & 0x7FFFF) << 2) | ((w_b >> 29) & 3), 21)
        return (min_code, max_idx, default_va, tbl_va, base_va)
    return None


def patch_bn(elf, host, changed):
    n = 0
    for iface, (ns, bp, bn) in CALLBACKS.items():
        guest = {m: c for m, (_, c, _, _) in bp_methods(elf, ns, bp).items()}
        by_host = {c: m for m, (c, _) in host[iface].items()}
        drop = {c: m for m, c in guest.items() if c in by_host and by_host[c] != m}
        if not drop:
            continue
        fs = elf.find(rf"^_ZN{ns}{len(bn)}{bn}10onTransactE")
        if len(fs) != 1 or len(fs[0][1]) != 1:
            die(f"{bn}::onTransact: {len(fs)} definitions (one expected)")
        ws = elf.words(*fs[0][1][0])
        jtab = find_jump_table(ws)
        for c, m in sorted(drop.items()):
            hits = [i for i, (_, _, w) in enumerate(ws[:-1]) if (w & ~(0xFFF << 10)) == 0x7100003F and (w >> 10) & 0xFFF == c]
            if len(hits) != 1:
                if not hits and jtab is not None:
                    min_code, max_idx, default_va, tbl_va, base_va = jtab
                    if not (min_code <= c <= min_code + max_idx):
                        die(f"{bn}::onTransact: code {c} outside jump table [{min_code}..{min_code + max_idx}]")
                    hw = struct.unpack_from("<H", elf.buf, elf.off(tbl_va) + (c - min_code) * 2)[0]
                    case_va = base_va + hw * 4
                    case_off = elf.off(case_va)
                    first_w = struct.unpack_from("<I", elf.buf, case_off)[0]
                    # Keep the BTI landing pad intact so `br xB` never triggers an ARMv8.5-A BTI SIGILL.
                    patch_va = case_va + 4 if first_w in (BTI_J, BTI_JC) else case_va
                    patch_off = elf.off(patch_va)
                    b_default = encode_b(patch_va, default_va)
                    if struct.unpack_from("<I", elf.buf, patch_off)[0] == b_default:
                        continue  # already patched
                    elf.put(patch_off, b_default)
                    changed.append(f"{bn}::onTransact: code {c} ({m}) ignored via jump table -> {default_va:#x}; the host's {by_host[c]}")
                    n += 1
                    continue
                if not hits and os.environ.get("ONEOS_CAMERA_NATIVE_SKIP_BN") == "1":
                    changed.append(f"{bn}::onTransact: code {c} ({m}) NOT ignored (jump table, ONEOS_CAMERA_NATIVE_SKIP_BN=1); the host's {by_host[c]}")
                    continue
                die(f"{bn}::onTransact: `cmp w1, #{c}` found {len(hits)} times (one expected; a jump table?)")
            _, _, cw = ws[hits[0]]
            va, o, bw = ws[hits[0] + 1]
            if (bw & 0xFC000000) == 0x14000000:
                continue  # already patched
            if (bw & 0xFF000010) != 0x54000000 or (bw & 0xF) not in (0, 1):
                die(f"{bn}::onTransact: `cmp w1, #{c}` is not followed by b.eq/b.ne ({bw:#x})")
            if bw & 0xF:  # b.ne default: always default
                imm = (bw >> 5) & 0x7FFFF
                imm -= 1 << 19 if imm >> 18 else 0
                elf.put(o, 0x14000000 | (imm & 0x3FFFFFF))
            else:  # b.eq case: never taken
                elf.put(o, NOP)
            changed.append(f"{bn}::onTransact: code {c} ({m}) ignored; the host's {by_host[c]}")
            n += 1
    return n


def patch_compat(elf, changed):
    gets = elf.find(r"^_ZNK7android7content3res23CameraCompatibilityInfo35shouldOverrideLensFacingFrontToBackEv$")
    if not gets:
        return 0
    off = None
    for _, _, w in elf.words(*gets[0][1][0]):
        if (w & 0xFFC003FF) == 0x39400000:  # ldrb w0, [x0, #imm]
            off = (w >> 10) & 0xFFF
    if off is None:
        die("shouldOverrideLensFacingFrontToBack: no ldrb")
    n = 0
    for rx, kind in ((r"^_ZNK7android7content3res23CameraCompatibilityInfo13writeToParcelEPNS_6ParcelE$", "write"),
                     (r"^_ZN7android7content3res23CameraCompatibilityInfo14readFromParcelEPKNS_6ParcelE$", "read")):
        fs = elf.find(rx)
        if len(fs) != 1:
            die(f"CameraCompatibilityInfo::{kind}ToParcel: {len(fs)} definitions")
        ws = elf.words(*fs[0][1][0])
        bls = [i for i, (_, _, w) in enumerate(ws) if (w & 0xFC000000) == 0x94000000]
        if kind == "write":
            at = [i for i, (_, _, w) in enumerate(ws) if (w & 0xFFC0001F) == 0x39400001 and (w >> 10) & 0xFFF == off]
        else:
            at = [i for i, (_, _, w) in enumerate(ws) if (w & 0xFFC0001F) == 0x91000001 and (w >> 10) & 0xFFF == off]
        if len(at) != 1:
            die(f"CameraCompatibilityInfo::{kind}FromParcel: the field at +{off:#x} is loaded {len(at)} times (one expected)")
        if any(ws[i][2] == NOP for i in range(at[0] + 1, min(at[0] + 4, len(ws)))) and not any(0 < i - at[0] <= 4 for i in bls):
            continue  # already patched
        nxt = [i for i in bls if i > at[0]]
        if not nxt or nxt[0] - at[0] > 4 or nxt[0] != bls[-1]:
            die(f"CameraCompatibilityInfo: the sixth field's {kind} is not the last call")
        elf.put(ws[nxt[0]][1], NOP)
        changed.append(f"CameraCompatibilityInfo: sixth field (+{off:#x}) not {kind}n"
                       .replace("writen", "written").replace("readn", "read"))
        n += 1
    return n


def patch_capture_result_extras(elf, host, changed):
    """Skip CaptureResultExtras's Android 17 multiResConcurrentReadersStartInfo read on Android 16 hosts.

    One UI 8.0/8.5 (Android 16, BP2A/BP4A; host tables without ICameraDeviceUser.configureStreams)
    writes CaptureResultExtras up to readoutTimestamp and nothing after it. An Android 17
    libcamera_client.so unconditionally calls Parcel::readParcelableVector for
    multiResConcurrentReadersStartInfo right after readoutTimestamp, consuming the timestamp
    bytes in onCaptureStarted and PhysicalCaptureResultInfo[] in onResultReceived.
    """
    if "configureStreams" in host.get("android.hardware.camera2.ICameraDeviceUser", {}):
        return 0
    if not elf.find(r".*MultiResConcurrentReadersStartInfo"):
        return 0
    fs = elf.find(r"^_ZN7android8hardware7camera24impl19CaptureResultExtras14readFromParcelEPKNS_6ParcelE$")
    if len(fs) != 1:
        die(f"CaptureResultExtras::readFromParcel: {len(fs)} definitions (one expected)")
    ws = elf.words(*fs[0][1][0])
    read64_plt = elf.sym_to_plt.get("_ZNK7android6Parcel9readInt64EPl")
    read32_plt = elf.sym_to_plt.get("_ZNK7android6Parcel9readInt32EPi")
    if read64_plt is None or read32_plt is None:
        die("CaptureResultExtras::readFromParcel: missing Parcel readInt64/readInt32 PLT")
    # Locate the last readInt64 (readoutTimestamp) and the subsequent mov w0, wzr (return OK).
    last_r64 = None
    for i, (pc, _, w) in enumerate(ws):
        if decode_bl(pc, w) == read64_plt:
            last_r64 = i
    if last_r64 is None:
        die("CaptureResultExtras::readFromParcel: no Parcel::readInt64 call")
    ret_zero = next((i for i in range(last_r64 + 1, min(last_r64 + 10, len(ws))) if ws[i][2] == 0x2A1F03E0), None)
    if ret_zero is None:
        die("CaptureResultExtras::readFromParcel: no mov w0, wzr after readoutTimestamp")
    # Already patched (BL replaced with NOP)?
    if ws[ret_zero - 1][2] == NOP and all(decode_bl(pc, w) is None for pc, _, w in ws[last_r64 + 1:ret_zero]):
        return 0
    bls = [(i, ws[i][1], ws[i][0], decode_bl(ws[i][0], ws[i][2]))
           for i in range(last_r64 + 1, ret_zero) if decode_bl(ws[i][0], ws[i][2]) is not None]
    if len(bls) != 1:
        die(f"CaptureResultExtras::readFromParcel: {len(bls)} calls between readoutTimestamp and return OK (one expected)")
    _, off, pc, tgt = bls[0]
    if tgt in elf.plt_to_sym:
        die(f"CaptureResultExtras::readFromParcel: unexpected PLT call {elf.plt_to_sym[tgt]} at {pc:#x}")
    # Verify the local helper calls Parcel::readInt32 before returning (readParcelableVector).
    helper_reads_int32 = False
    for hpc, _, hw in elf.words(tgt, 0x100):
        if decode_bl(hpc, hw) == read32_plt:
            helper_reads_int32 = True
            break
        if hw == 0xD65F03C0:  # ret
            break
    if not helper_reads_int32:
        die(f"CaptureResultExtras::readFromParcel: helper {tgt:#x} does not call Parcel::readInt32")
    elf.put(off, NOP)
    changed.append(f"CaptureResultExtras::readFromParcel: skipped multiResConcurrentReadersStartInfo read at {pc:#x} (Android 16 host)")
    return 1


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        elf = Elf(sys.argv[2])
        for iface, (ns, cls) in list(AIDL.items()) + [(i, v[:2]) for i, v in CALLBACKS.items()]:
            for m, (_, c, _, _) in sorted(bp_methods(elf, ns, cls).items(), key=lambda x: x[1][1]):
                print(cls, m, c)
        return
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    host = read_table(sys.argv[1])
    elf = Elf(sys.argv[2])
    changed = []
    if elf.find(r"^_ZN7android8hardware15BpCameraService"):
        n = patch_bp(elf, host, changed) + patch_bn(elf, host, changed) + patch_capture_result_extras(elf, host, changed)
    elif elf.find(r"^_ZNK?7android7content3res23CameraCompatibilityInfo"):
        # ONEOS_CAMERA_KEEP_COMPAT=1: a One UI 9.5 host reads the sixth field too (see pixel_camera_abi.py).
        n = 0 if os.environ.get("ONEOS_CAMERA_KEEP_COMPAT") == "1" else patch_compat(elf, changed)
    else:
        die("neither libcamera_client.so nor libcameracompatbilityinfo.so")
    for c in changed:
        print(f"pixel_camera_native: {c}", file=sys.stderr)
    if not n:
        print("pixel_camera_native: unchanged", file=sys.stderr)
        return
    open(sys.argv[3], "wb").write(elf.buf)
    print("changed")


if __name__ == "__main__":
    main()
