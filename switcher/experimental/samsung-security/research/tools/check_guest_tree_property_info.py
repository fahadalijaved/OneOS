"""Prepare and verify a two-rule inert donor property_info schema fixture."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import stat
import struct


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-property-info"
DONOR = "../firmware/donor/"
SYSTEM = DONOR + "extracted/system/"
LAYOUT = "out/guest-tree-property-view/layout-source.json"
NO_INDEX = 0xFFFFFFFF
BUILD = "u:object_r:build_prop:s0"
DEFAULT = "u:object_r:default_prop:s0"
KEYS = {"ro.build.version.codename": (BUILD, "string"), "ro.build.version.sdk": (BUILD, "int")}
CONTEXT_SLOTS = (
    ("/system/etc/selinux/plat_property_contexts", 0x10601C, 0x2917B, 0x1060EC),
    ("/system_ext/etc/selinux/system_ext_property_contexts", 0x106110, 0x31445, 0x106244),
    ("/vendor/etc/selinux/vendor_property_contexts", 0x106260, 0x13AE6, 0x1062F4),
    ("/product/etc/selinux/product_property_contexts", 0x106310, 0x2722B, 0x1063A4),
    ("/odm/etc/selinux/odm_property_contexts", 0x1063C0, 0x303CB, 0x106658),
)


def require(condition, label):
    if not condition:
        raise ValueError(label)


def digest(raw):
    return sha256(raw).hexdigest()


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def read_exact(path, size):
    info = path.lstat()
    require(plain(info) and stat.S_ISREG(info.st_mode) and info.st_size == size,
            f"Plain input of exact size: {path}")
    with path.open("rb") as stream:
        raw = stream.read(size + 1)
    final = path.lstat()
    require(len(raw) == size and plain(final) and
            (final.st_ino, final.st_dev, final.st_size, final.st_mtime_ns, final.st_ctime_ns) ==
            (info.st_ino, info.st_dev, info.st_size, info.st_mtime_ns, info.st_ctime_ns),
            f"Unchanged bounded input: {path}")
    return raw


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def branch(raw, pc, target):
    insn, = struct.unpack_from("<I", raw, pc)
    require(insn >> 26 == 0x25 and pc + 4 * signed(insn & 0x03FFFFFF, 26) == target,
            f"Exact BL at {pc:#x}")


def address(raw, pc, expected, text):
    page, add = struct.unpack_from("<II", raw, pc)
    imm = signed((page >> 5 & 0x7FFFF) << 2 | (page >> 29 & 3), 21)
    require(page & 0x9F000000 == 0x90000000 and add & 0xFFC00000 == 0x91000000 and
            add >> 5 & 31 == page & 31 and (pc & ~0xFFF) + (imm << 12) + (add >> 10 & 0xFFF) == expected
            and raw.startswith(text.encode("ascii") + b"\0", expected), f"Exact path literal at {pc:#x}")


def verify_native_schema(init, libc):
    for pc, target in ((0x106780, 0x16B3E8), (0x16B47C, 0x16CEB8),
                       (0x16D03C, 0x16C75C), (0x1073F4, 0x2A1E48)):
        branch(init, pc, target)
    branch(libc, 0xA4134, 0xA2C24)
    address(init, 0x1066E0, 0x1FFE6, DEFAULT)
    address(init, 0x1066F4, 0x1BDDD, "string")
    writer = {
        0x16CF48: "e9620091", 0x16CF98: "29008052", 0x16CF9C: "096937b8",
        0x16CFB4: "090500b9", 0x16CFD4: "280d00b9", 0x16D000: "281100b9",
        0x16D060: "151500b9", 0x16D080: "280900b9",
        0x16C7A0: "a9720091", 0x16C690: "09430091", 0x16C6E0: "006938b8",
        0x16C710: "090500b9", 0x16C728: "140900b9", 0x16C740: "160d00b9",
        0x16C39C: "366928b8", 0x16C474: "007938b8",
    }
    reader = {
        0xA2F98: "080440b9", 0xA2FA4: "080840b9", 0xA2C60: "081440b9",
        0xA2CF8: "090540b9", 0xA2D0C: "080940b9", 0xA2DA8: "141740b9",
        0xA2DB4: "191b40b9", 0xA2E60: "080940b9", 0xA2E94: "080d40b9",
        0xA3DDC: "090d40b9", 0xA3DE4: "166969b8", 0xA3E60: "8c696ab8",
    }
    for raw, anchors in ((init, writer), (libc, reader)):
        require(all(raw[pc:pc + 4].hex() == bits for pc, bits in anchors.items()),
                "Held native schema instruction anchors")
    return {"writerPcBytes": {hex(pc): v for pc, v in writer.items()},
            "readerPcBytes": {hex(pc): v for pc, v in reader.items()},
            "headerBytes": 24, "entryBytes": 16, "nodeBytes": 28, "version": 1,
            "minimumVersion": 1, "buildTrieCallPc": "0x106780",
            "rootDefaults": {"context": DEFAULT, "type": "string"}}


def make_fixture(rules):
    # All offsets are relative to the start of the serialized area.
    raw = bytearray(24)

    def append(data):
        offset = len(raw)
        raw.extend(data)
        raw.extend(b"\0" * (-len(raw) % 4))
        return offset

    def words(*values):
        return append(struct.pack("<" + "I" * len(values), *values))

    def text(value):
        return append(value.encode("ascii") + b"\0")

    def table(values):
        base = words(len(values), *([0] * len(values)))
        for index, value in enumerate(values):
            struct.pack_into("<I", raw, base + 4 + 4 * index, text(value))
        return base

    contexts = (BUILD, DEFAULT)
    types = ("int", "string")
    context_table, type_table = table(contexts), table(types)
    child = 0
    for name in ("version", "build", "ro", "root"):
        exact = []
        if name == "version":
            for full_key, (context, kind) in sorted(rules.items()):
                suffix = full_key.rsplit(".", 1)[1]
                exact.append(words(text(suffix), len(suffix), contexts.index(context), types.index(kind)))
        context, kind = (contexts.index(DEFAULT), types.index("string")) if name == "root" else (NO_INDEX, NO_INDEX)
        own_entry = words(text(name), len(name), context, kind)
        children = words(child) if child else 0
        exact_array = words(*exact) if exact else 0
        child = words(own_entry, bool(children), children, 0, 0, len(exact), exact_array)
    struct.pack_into("<6I", raw, 0, 1, 1, len(raw), context_table, type_table, child)
    return bytes(raw)


def decode_fixture(raw):
    """Read the saved binary through offsets and trie edges, independent of writer order."""
    require(24 <= len(raw) <= 4096 and len(raw) % 4 == 0, "Bounded serialized fixture")
    occupied = []

    def claim(offset, size):
        end = offset + size
        require(offset % 4 == 0 and size > 0 and end <= len(raw) and
                all(end <= low or offset >= high for low, high in occupied), "Disjoint in-bounds record")
        occupied.append((offset, end))

    def read(offset, count):
        claim(offset, 4 * count)
        return struct.unpack_from("<" + "I" * count, raw, offset)

    def read_text(offset):
        require(24 <= offset < len(raw), "Valid text offset")
        end = raw.find(b"\0", offset, offset + 129)
        require(end > offset, "Bounded terminated text")
        padded_end = (end + 4) & ~3
        claim(offset, padded_end - offset)
        require(not any(raw[end:padded_end]), "Zero string padding")
        return raw[offset:end].decode("ascii")

    def read_table(offset):
        count, = read(offset, 1)
        require(0 < count <= 8, "Bounded table")
        values = tuple(read_text(ref) for ref in read(offset + 4, count))
        require(values == tuple(sorted(set(values))), "Ordered unique table")
        return values

    major, minimum, size, context_ref, type_ref, node = read(0, 6)
    require((major, minimum, size) == (1, 1, len(raw)), "Exact serialized header")
    contexts, types = read_table(context_ref), read_table(type_ref)

    def read_entry(offset):
        name_offset, length, context, kind = read(offset, 4)
        name = read_text(name_offset)
        require(len(name) == length and "." not in name and
                (context == NO_INDEX or context < len(contexts)) and
                (kind == NO_INDEX or kind < len(types)), "Exact property entry")
        return name, contexts[context] if context != NO_INDEX else None, types[kind] if kind != NO_INDEX else None

    prefix = []
    defaults = None
    rules = {}
    for depth in range(4):
        entry, children, child_array, prefixes, prefix_array, count, exact = read(node, 7)
        name, context, kind = read_entry(entry)
        require(prefixes == prefix_array == 0 and children in (0, 1) and
                bool(children) == bool(child_array) and count in (0, 2) and
                bool(count) == bool(exact), "Exact-only one-branch fixture")
        if depth == 0:
            require(name == "root", "Root name")
            defaults = (context, kind)
        else:
            require(context is None and kind is None, "Intermediate metadata is inherited")
            prefix.append(name)
        if children:
            require(depth < 3 and count == 0, "Intermediate trie depth")
            node, = read(child_array, 1)
        else:
            require(depth == 3 and count == 2, "Two exact terminal rules")
            seen = []
            for offset in read(exact, count):
                name, context, kind = read_entry(offset)
                seen.append(name)
                rules[".".join((*prefix, name))] = (context, kind)
            require(seen == sorted(set(seen)), "Exact entries remain distinct and ordered")
    cursor = 0
    for low, high in sorted(occupied):
        require(low == cursor, "No hidden records or gaps")
        cursor = high
    require(cursor == len(raw), "All fixture bytes covered")
    return defaults, rules


def check_readback(raw):
    require(decode_fixture(raw) == ((DEFAULT, "string"), KEYS),
            "Serialized rules match the exact held two-key context map")
    for offset, value in ((0, 2), (4, 2), (8, len(raw) - 4), (12, 24 + len(raw)),
                          (16, 24), (20, 0), (20, len(raw) - 4)):
        corrupt = bytearray(raw)
        struct.pack_into("<I", corrupt, offset, value)
        try:
            decode_fixture(bytes(corrupt))
        except ValueError:
            continue
        raise ValueError(f"Fixture mutation at {offset} was accepted")


def derive():
    pins = {}

    def load(name, size, expected):
        raw = read_exact(ROOT / name, size)
        require(digest(raw) == expected, f"Exact held input: {name}")
        pins[name] = {"bytes": size, "sha256": expected}
        return raw

    layout = json.loads(load(LAYOUT, 4379,
        "2ef78829d096c734caf19124a35ff9286540fa07000cffc0444b898da90e544d"))
    init = load(SYSTEM + "bin/init", 2888328,
        "8db6b39facd5af0745d9bd27c588dacedb6ae5e21a87870644d0b49d33e19757")
    libc = load(layout["libc"]["path"], layout["libc"]["bytes"], layout["libc"]["sha256"])
    schema = verify_native_schema(init, libc)
    listing = load(DONOR + "7zip-image-listing.txt", 5504768,
        "06717bce364dbe578e8a2f2f68d37e1863eb6566f22d6947dd48acecd9939a20")
    image_paths = {line[7:].replace(b"\\", b"/") for line in listing.splitlines() if line.startswith(b"Path = ")}
    legacy = "firmware/installed-oneos-code-profile/static/assets/guest_prepare.sh"
    lines = load(legacy, 278725, "000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70").splitlines()
    require(b"for vb in vendor odm vendor_dlkm" in lines[329] and
            b'mount --bind "/$vb" "$ROOTFS/$vb"' in lines[330], "Exact legacy vendor/odm import")

    held = iter(layout["exactContextSources"])
    found = {}
    sources = []
    for ordinal, (target, ref, literal, load_pc) in enumerate(CONTEXT_SLOTS, 1):
        address(init, ref, literal, target)
        branch(init, load_pc, 0x105D60)
        row = {"ordinal": ordinal, "initPath": target, "pathPc": hex(ref), "parsePc": hex(load_pc)}
        if ordinal in (1, 2, 4):
            item = next(held)
            raw = load(item["path"], item["bytes"], item["sha256"])
            extracted = item["path"].split("/extracted/", 1)[1]
            require(extracted.encode("ascii") in image_paths and extracted.endswith(target.rsplit("/", 1)[1]),
                    "Held donor source is in the image listing")
            rules = []
            count = 0
            for n, line in enumerate(raw.splitlines(), 1):
                parts = line.split()
                if not parts or parts[0].startswith(b"#"):
                    continue
                count += 1
                name = parts[0].decode("ascii")
                if name in KEYS:
                    require(len(parts) == 4 and parts[2] == b"exact" and name not in found,
                            "Unique exact selected context rules")
                    found[name] = (parts[1].decode("ascii"), parts[3].decode("ascii"))
                    rules.append([n, *[part.decode("ascii") for part in parts]])
            require(rules == item["exactRules"], "Exact context source rows")
            row.update(heldDonorPath=item["path"], observedRows=count, exactSelectedRules=rules,
                       runtimePlacementVerified=False)
        else:
            require(target[1:].encode("ascii") not in image_paths, "No such member in held donor listing")
            row.update(heldDonorPath=None, pathInHeldImageListing=False,
                       runtimePlacementVerified=False, actualSelectedInput=None)
        sources.append(row)
    require(next(held, None) is None and found == KEYS and
            [s.get("observedRows") for s in sources] == [1431, 822, None, 2, None],
            "Exact three-file donor subset")
    fixture = make_fixture(found)
    check_readback(fixture)
    receipt = {
        "schema": "guest-tree-property-info/v1",
        "status": "INERT_ORIGINAL_SCHEMA_FIXTURE_COMPLETE_GUEST_CONTEXTS_HELD",
        "toolSha256": digest(Path(__file__).read_bytes()),
        "pins": pins,
        "nativeSchema": schema,
        "modernInitContextInputOrder": sources,
        "legacyImport": {"script": legacy, "lines": [330, 331],
                         "acceptedAsGuestInput": False},
        "fixture": {"bytes": len(fixture), "sha256": digest(fixture),
                    "lookupRows": found, "malformedReadbacksRefused": 7},
        "missing": ["Admit exact vendor and odm inputs or their absence in the final private root",
                    "Bind canonical system_ext and product aliases in that same root",
                    "Build full selected property_info, then bind owned area objects, labels and actual consumer read access"],
        "effectiveProperties": None, "runtimePropertyInfo": None, "entryAdmitted": False,
        "hostPropertyAreaUsed": False, "propertyWrites": False, "oemExecuted": False,
    }
    return fixture, (json.dumps(receipt, indent=2) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--stage", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        fixture, receipt = derive()
        require(not args.require_complete, "Complete private context-source view is unbound")
        for path in (OUT.parent, OUT, OUT / "fixture-v1"):
            if args.stage:
                path.mkdir(exist_ok=path != OUT / "fixture-v1")
            info = path.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain owned output directory")
        for name, raw in (("property-info.fixture.bin", fixture), ("receipt.json", receipt)):
            path = OUT / "fixture-v1" / name
            if args.stage:
                with path.open("xb") as stream:
                    stream.write(raw)
            saved = read_exact(path, len(raw))
            if name.endswith(".bin"):
                check_readback(saved)
            require(saved == raw, f"Exact saved output: {name}")
            print(f"{path.relative_to(ROOT).as_posix()} {len(raw)} {digest(raw)}")
    except (OSError, ValueError, IndexError, KeyError, struct.error) as error:
        parser.exit(2, f"Refused: {error}\n")


if __name__ == "__main__":
    main()
