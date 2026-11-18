"""Read back the fixed disabled SystemUI lifecycle bridge from one DEX039."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from preflight_guest_metrics_parent_payload import Dex


MAX_BYTES = 64 * 1024 * 1024
SECURITY = "Lcom/oplus/keyguard/security/"
CHECKER = SECURITY + "OplusLockPatternChecker;"
INPUT = SECURITY + "view/OplusKeyguardInputViewController;"
CONTROLLER = SECURITY + "view/OplusKeyguardAbsKeyInputViewController;"
SLOT = SECURITY + "GuestPinCheckRequest$Slot;"
VIEW = "Landroid/view/View;"
ENTRY = CONTROLLER + "->oneos$retirePinAtLifecycleEntry(" + CONTROLLER + ")V"
FORWARDER = CHECKER + "->oneos$retirePinForController(" + CONTROLLER + ")V"
GETTER = INPUT + "->getChecker()" + CHECKER
RETIRE = SLOT + "->retireAtOriginalLifecycleEntry(Ljava/lang/Object;Ljava/lang/Object;" + VIEW + "Ljava/lang/Object;)Z"
SLOT_FIELD = CHECKER + "->oneos$pinSlot:" + SLOT
VIEW_FIELD = "Lcom/android/systemui/util/ViewController;->mView:" + VIEW
MONITOR_FIELD = CHECKER + "->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;"

# Ordinary 039 instruction widths in code units. Reserved and quickened
# opcodes stay unsupported. Payloads have their own bounded extents.
WIDTHS = {
    opcode: width
    for first, stop, width in (
        (0, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 1), (5, 6, 2), (6, 7, 3),
        (7, 8, 1), (8, 9, 2), (9, 10, 3), (10, 19, 1), (19, 20, 2), (20, 21, 3),
        (21, 23, 2), (23, 24, 3), (24, 25, 5), (25, 27, 2), (27, 28, 3), (28, 29, 2),
        (29, 31, 1), (31, 33, 2), (33, 34, 1), (34, 36, 2), (36, 39, 3), (39, 41, 1),
        (41, 42, 2), (42, 45, 3), (45, 62, 2), (68, 110, 2), (110, 115, 3),
        (116, 121, 3), (123, 144, 1), (144, 176, 2), (176, 208, 1), (208, 227, 2),
        (250, 252, 4), (252, 254, 3), (254, 256, 2),
    )
    for opcode in range(first, stop)
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def pool_index(pool, reference):
    require(pool.count(reference) == 1, "Missing or duplicate reference: " + reference)
    return pool.index(reference)


def member(dex, reference, partition, flags):
    found = [row for row in dex.members if row["descriptor"] == reference]
    require(len(found) == 1 and found[0]["partition"] == partition
            and found[0]["accessFlags"] == flags, "Unexpected declaration: " + reference)
    return found[0]


def read_code(dex, offset, limit):
    require(offset % 4 == 0 and 0 < offset <= limit - 16, "Code header extent")
    header = struct.unpack_from("<4HII", dex.d, offset)
    size = header[-1]
    require(0 < size <= (limit - offset - 16) // 2, "Code instructions extent")
    return header, struct.unpack_from(f"<{size}H", dex.d, offset + 16)


def instructions(words):
    pc = 0
    while pc < len(words):
        unit = words[pc]
        opcode = unit & 0xff
        if opcode == 0 and unit != 0:
            require(pc % 2 == 0 and pc + 2 <= len(words), "DEX payload alignment or header")
            if unit == 0x100:
                width = 4 + 2 * words[pc + 1]
            elif unit == 0x200:
                width = 2 + 4 * words[pc + 1]
            elif unit == 0x300:
                require(pc + 4 <= len(words) and words[pc + 1] in (1, 2, 4, 8), "Array payload header")
                count = words[pc + 2] | words[pc + 3] << 16
                width = 4 + (words[pc + 1] * count + 1) // 2
            else:
                raise ValueError("Unknown DEX payload")
        else:
            width = WIDTHS.get(opcode, 0)
            require(width > 0, "Unsupported ordinary DEX opcode")
        require(pc + width <= len(words), "Instruction or payload exceeds code item")
        yield pc, opcode
        pc += width


def mapped_extent(dex, kind):
    rows = [row for row in dex.map if row["type"] == kind]
    require(len(rows) <= 1, "Duplicate DEX map kind")
    if not rows:
        return None
    row = rows[0]
    start = row["offset"]
    limit = min((item["offset"] for item in dex.map if item["offset"] > start), default=len(dex.d))
    require(0 < start < limit <= len(dex.d), "Unexpected DEX map extent")
    return row["size"], start, limit


def scan_slot_accesses(dex, field_id, forwarder):
    code_map = mapped_extent(dex, 0x2001)
    require(code_map is not None, "Missing code map")
    count, start, limit = code_map
    offsets = sorted({row["codeOffset"] for row in dex.codes})
    require(offsets and len(offsets) == count and offsets[0] == start
            and offsets[-1] < limit, "Unexpected code item coverage")
    reads = []
    for offset, following in zip(offsets, offsets[1:] + [limit]):
        _, words = read_code(dex, offset, following)
        for pc, opcode in instructions(words):
            if 0x52 <= opcode <= 0x6d and words[pc + 1] == field_id:
                require(opcode == 0x54, "Unexpected Slot field opcode, including any write")
                reads.append((offset, pc))
    require(reads == [(forwarder, 0)], "Expected only the forwarder's single Slot read")

    handles = mapped_extent(dex, 0x0008)
    if handles:
        size, start, limit = handles
        require(size <= (limit - start) // 8, "Method handle section extent")
        for offset in range(start, start + size * 8, 8):
            kind, reserved_a, index, reserved_b = struct.unpack_from("<4H", dex.d, offset)
            require(0 <= kind <= 8 and reserved_a == reserved_b == 0, "Method handle format")
            require(kind >= 4 or index != field_id, "Unexpected Slot field method handle")
    return len(offsets)


def verify_bridge(raw):
    """Return static evidence for the two bridge bodies and the exact Slot field."""
    require(type(raw) is bytes and 112 <= len(raw) <= MAX_BYTES, "Expected bounded ordinary DEX bytes")
    dex = Dex(raw)
    entry = member(dex, ENTRY, "directMethods", 0x0a)
    forward = member(dex, FORWARDER, "virtualMethods", 0x11)
    slot = member(dex, SLOT_FIELD, "instanceFields", 0x02)
    slot_id = pool_index(dex.fields, SLOT_FIELD)
    require(slot["memberIndex"] == slot_id, "Expected exact private instance field")
    getter_id = pool_index(dex.methods, GETTER)
    forward_id = pool_index(dex.methods, FORWARDER)
    retire_id = pool_index(dex.methods, RETIRE)
    view_id = pool_index(dex.fields, VIEW_FIELD)
    monitor_id = pool_index(dex.fields, MONITOR_FIELD)

    entry_words = (
        0x106e, getter_id, 0x0001,  # v1 controller, stock getChecker
        0x000c,                     # v0 checker
        0x0038, 5,                  # PC4, absent checker goes to PC9
        0x206e, forward_id, 0x0010,  # v0 checker, v1 controller
        0x000e,
    )
    forward_words = (
        0x3054, slot_id,             # v0 Slot from v3 checker
        0x0038, 9,                   # PC2, absent Slot goes to PC11
        0x4154, view_id,             # v1 view from v4 controller
        0x3254, monitor_id,          # v2 monitor from v3 checker
        0x526e, retire_id, 0x1430,   # v0, v3, v4, v1, v2
        0x000e,                      # Ignore boolean result, no effects on original continuation
    )
    for row, expected_header, expected_words in (
        (entry, (2, 1, 2, 0, 0, 10), entry_words),
        (forward, (5, 2, 5, 0, 0, 12), forward_words),
    ):
        offset = row["codeOffset"]
        require(sum(item["codeOffset"] == offset for item in dex.codes) == 1, "Unexpected bridge code alias")
        require(read_code(dex, offset, len(raw)) == (expected_header, expected_words),
                "Unexpected exact body or header: " + row["descriptor"])
    count = scan_slot_accesses(dex, slot_id, forward["codeOffset"])
    return {
        "status": "PASS_STATIC_DISABLED_PIN_LIFECYCLE_BRIDGE",
        "dexSha256": hashlib.sha256(raw).hexdigest(),
        "entry": {"descriptor": ENTRY, "codeOffset": entry["codeOffset"], "nullCheckerReturnPc": 9},
        "forwarder": {"descriptor": FORWARDER, "codeOffset": forward["codeOffset"], "nullSlotReturnPc": 11},
        "slot": {"descriptor": SLOT_FIELD, "fieldId": slot_id, "directReads": 1, "directWrites": 0,
                 "fieldMethodHandles": 0},
        "scannedCodeItems": count,
        "androidOrOemExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dex", type=Path)
    args = parser.parse_args()
    with args.dex.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    print(json.dumps(verify_bridge(raw), indent=2))


if __name__ == "__main__":
    main()
