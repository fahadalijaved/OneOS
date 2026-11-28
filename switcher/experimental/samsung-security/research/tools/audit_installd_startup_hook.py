#!/usr/bin/env python3
"""Verify a fixed, zero-cookie AArch64 startup-hook fixture in memory."""

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
IMAGE = "firmware/retained-installd-native-owner/20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd"
ELF = "firmware/retained-installd-native-owner/static/elf.json"
SOURCE_SHA = "ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc"
ELF_SHA = "897ee77644a17a8f7c2ef97d77588a06c5cb8a29620ff9c6c86cd90b014d108a"
SITE, RESUME, PLT = 0x8B098, 0x8B09C, 0x8C380
HOOK, COOKIE, ACK = 0x8E300, 0x8E380, 0x8E388
ACK_BYTES = b"OIDR\x01\x00\x01\x00" + bytes(8)
END = ACK + len(ACK_BYTES)
RESTORE = HOOK + 27 * 4
CHILD_FD = 198


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def read_pinned(path, expected):
    data = (ROOT / path).read_bytes()
    require(sha(data) == expected, f"identity drift: {path}")
    return data


def signed(value, bits):
    require(-(1 << (bits - 1)) <= value < (1 << (bits - 1)), "immediate range")
    return value & ((1 << bits) - 1)


def relative(pc, target, base, bits, shift=0):
    delta = target - pc
    require(delta % 4 == 0, "relative branch/literal alignment")
    return base | (signed(delta // 4, bits) << shift)


def adr(pc, target, register):
    delta = signed(target - pc, 21)
    return 0x10000000 | ((delta & 3) << 29) | ((delta >> 2) << 5) | register


def mov(register, value, wide=False):
    require(0 <= value <= 0xffff, "MOVZ immediate range")
    return (0xd2800000 if wide else 0x52800000) | value << 5 | register


def fixture_words():
    # Each tuple describes one exact 32-bit instruction. Arguments before the
    # two Linux syscalls are rebuilt from scratch. x18 and all saved registers
    # stay untouched. Zero cookie is a deliberate inert fixture sentinel.
    return (
        (0xd10043ff, "sub sp, sp, #16"),
        (mov(4, 8), "mov w4, #8"),
        (0xb9000be4, "str w4, [sp, #8]"),
        (mov(0, CHILD_FD), "mov w0, #198"),
        (mov(1, 1), "mov w1, #1"),
        (mov(2, 57), "mov w2, #57"),
        (0x910003e3, "mov x3, sp"),
        (0x910023e4, "add x4, sp, #8"),
        (mov(8, 209, True), "mov x8, #209"),
        (0xd4000001, "svc #0"),
        (relative(HOOK + 40, RESTORE, 0xb5000000, 19, 5), "cbnz x0, restore"),
        (0xb9400be4, "ldr w4, [sp, #8]"),
        (0x7100209f, "cmp w4, #8"),
        (relative(HOOK + 52, RESTORE, 0x54000001, 19, 5), "b.ne restore"),
        (0xf94003e4, "ldr x4, [sp]"),
        (relative(HOOK + 60, COOKIE, 0x58000005, 19, 5), "ldr x5, cookie"),
        (relative(HOOK + 64, RESTORE, 0xb4000005, 19, 5), "cbz x5, restore"),
        (0xeb05009f, "cmp x4, x5"),
        (relative(HOOK + 72, RESTORE, 0x54000001, 19, 5), "b.ne restore"),
        (mov(0, CHILD_FD), "mov w0, #198"),
        (adr(HOOK + 80, ACK, 1), "adr x1, ack"),
        (mov(2, len(ACK_BYTES)), "mov w2, #16"),
        (mov(3, 0x4040), "mov w3, #0x4040"),
        (mov(4, 0, True), "mov x4, #0"),
        (mov(5, 0, True), "mov x5, #0"),
        # x8 holds __NR_getsockopt until here. Set __NR_sendto explicitly.
        (mov(8, 206, True), "mov x8, #206"),
        (0xd4000001, "svc #0"),
        (0x910043ff, "add sp, sp, #16"),
        (adr(HOOK + 112, RESUME, 30), "adr x30, original_return"),
        (relative(HOOK + 116, PLT, 0x14000000, 26), "b original_plt"),
    )


def sign_extend(value, bits):
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def pc_reference(pc, word):
    if word & 0x7c000000 == 0x14000000:
        return pc + 4 * sign_extend(word & 0x03ffffff, 26)
    if (word & 0xff000010 == 0x54000000 or word & 0x7e000000 == 0x34000000
            or word & 0x3b000000 == 0x18000000):
        return pc + 4 * sign_extend((word >> 5) & 0x7ffff, 19)
    if word & 0x7e000000 == 0x36000000:
        return pc + 4 * sign_extend((word >> 5) & 0x3fff, 14)
    if word & 0x9f000000 == 0x10000000:
        immediate = (((word >> 5) & 0x7ffff) << 2) | ((word >> 29) & 3)
        return pc + sign_extend(immediate, 21)
    return None


def relr_targets(data):
    targets = []
    cursor = None
    for word, in struct.iter_unpack("<Q", data):
        if word & 1:
            require(cursor is not None, "RELR bitmap precedes base")
            targets.extend(cursor + bit * 8 for bit in range(63) if word & (2 << bit))
            cursor += 504
        else:
            require(word % 8 == 0, "RELR target alignment")
            targets.append(word)
            cursor = word + 8
    require(targets == sorted(set(targets)), "RELR target order")
    return targets


def round_up(value, size):
    return (value + size - 1) & -size


def main():
    original = read_pinned(IMAGE, SOURCE_SHA)
    elf = json.loads(read_pinned(ELF, ELF_SHA))
    require(len(original) == 640912 and original[:7] == b"\x7fELF\x02\x01\x01"
            and struct.unpack_from("<HH", original, 16) == (3, 183), "ELF profile")
    phoff, = struct.unpack_from("<Q", original, 32)
    phsize, phnum = struct.unpack_from("<HH", original, 54)
    require((phoff, phsize, phnum) == (0x40, 56, 14), "program-header profile")
    programs = [struct.unpack_from("<IIQQQQQQ", original, phoff + i * phsize)
                for i in range(phnum)]
    require(programs[3] == (1, 5, 0x20000, 0x20000, 0x20000, 0x6e300, 0x6e300, 0x4000)
            and programs[4][:4] == (1, 6, 0x90000, 0x90000), "RX/RW boundaries")
    require(original[HOOK:0x90000] == bytes(0x90000 - HOOK), "gap is occupied")
    for page in (4096, 16384):
        require(round_up(HOOK, page) == round_up(END, page) <= 0x90000, "RX page growth")
    sections = {row["name"]: row for row in elf["sections"]}
    require(all(row["bytes"] == 0 or row["offset"] + row["bytes"] <= HOOK
                or row["offset"] >= END for row in sections.values()), "section overlap")
    require(original[SITE-12:SITE+12].hex() ==
            "e008f8375b6cfe9760070035ba04009421008052e40b0094", "original success/failure edges")
    require(pc_reference(SITE, struct.unpack_from("<I", original, SITE)[0]) == PLT,
            "original call target")
    references = []
    for name in (".text", ".plt"):
        row = sections[name]
        require(row["address"] == row["offset"], "RX file mapping")
        start = row["offset"]
        for pc in range(start, start + row["bytes"], 4):
            target = pc_reference(pc, struct.unpack_from("<I", original, pc)[0])
            if target is not None and (target == SITE or HOOK <= target < END):
                references.append((pc, target))
    require(not references, "preexisting direct reference to selected range")
    relr = sections[".relr.dyn"]
    require((relr["offset"], relr["bytes"], relr["type"]) == (0x7d40, 264, 0x6fffff00),
            "Android RELR profile")
    packed = relr_targets(original[relr["offset"]:relr["offset"] + relr["bytes"]])
    targets = packed + [row["target"] for row in elf["rela"]]
    require(len(packed) == 756 and len(elf["rela"]) == 1039
            and all(not (target < SITE + 4 and target + 8 > SITE)
                    and not (target < END and target + 8 > HOOK) for target in targets),
            "relocation overlap")

    unwind = sections[".eh_frame_hdr"]["offset"]
    require(original[unwind:unwind+4] == bytes.fromhex("011b033b"), "unwind table encodings")
    _, count = struct.unpack_from("<iI", original, unwind + 4)
    entries = [(unwind + pc, unwind + fde) for pc, fde in struct.iter_unpack(
        "<ii", original[unwind + 12:unwind + 12 + count * 8])]
    require(count == 679 and entries[-1][0] == 0x8bd8c, "unwind index profile")
    fde, = (fde for pc, fde in entries if pc == 0x8aaf8)
    start_delta, extent = struct.unpack_from("<ii", original, fde + 8)
    require(fde + 8 + start_delta == 0x8aaf8 and extent == 1820, "main FDE range")

    words = fixture_words()
    require(HOOK + 27 * 4 == RESTORE and HOOK + 4 * len(words) <= COOKIE, "hook layout")
    targets = {index: RESTORE for index in (10, 13, 16, 18)}
    targets.update({15: COOKIE, 20: ACK, 28: RESUME, 29: PLT})
    for index, target in targets.items():
        require(pc_reference(HOOK + 4 * index, words[index][0]) == target,
                f"fixture target {index}")
    code = b"".join(struct.pack("<I", word) for word, _ in words)
    hook = code.ljust(COOKIE - HOOK, b"\0") + bytes(8) + ACK_BYTES
    size_field = phoff + 3 * phsize + 32
    patches = (
        (size_field, struct.pack("<QQ", END - 0x20000, END - 0x20000)),
        (SITE, struct.pack("<I", relative(SITE, HOOK, 0x14000000, 26))),
        (HOOK, hook),
    )
    require(len(hook) == END - HOOK, "payload extent")
    successor = bytearray(original)
    for offset, data in patches:
        successor[offset:offset + len(data)] = data
    inverse = bytearray(successor)
    for offset, data in patches:
        inverse[offset:offset + len(data)] = original[offset:offset + len(data)]
    require(bytes(inverse) == original, "inverse mismatch")

    print(json.dumps({
        "schema": "installd-startup-hook-static-fixture/v1",
        "status": "INERT_BYTE_FIXTURE_ONLY",
        "source": {"path": IMAGE, "sha256": SOURCE_SHA, "bytes": len(original)},
        "elfRecord": {"path": ELF, "sha256": ELF_SHA},
        "fixtureSha256InMemoryOnly": sha(successor),
        "replacementSpans": [
            {"offset": hex(offset), "beforeHex": original[offset:offset + len(data)].hex(),
             "afterHex": data.hex()} for offset, data in patches],
        "instructionReadback": [
            {"va": hex(HOOK + index * 4), "word": f"{word:08x}", "operation": operation}
            for index, (word, operation) in enumerate(words)],
        "rxDeclaredEndBefore": hex(HOOK), "rxDeclaredEndFixture": hex(END),
        "boundedDirectIncomingReferences": references, "inverseExact": True,
        "mainFde": {"entry": "0x8aaf8", "extent": extent, "hookHasFde": False},
        "abiFixture": {"fd": CHILD_FD, "zeroCookieSuppressesSend": True, "ackHex": ACK_BYTES.hex(),
                       "originalReturn": hex(RESUME), "originalPlt": hex(PLT)},
        "selectedForRuntime": False, "artifactWritten": False, "oemExecuted": False,
    }, indent=2))


if __name__ == "__main__":
    main()
