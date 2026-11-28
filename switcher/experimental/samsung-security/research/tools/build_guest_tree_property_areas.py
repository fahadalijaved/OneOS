"""Populate offline donor property-area snapshots from a fixed source-backed boot slice."""

import argparse
import ast
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import struct


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-property-areas"
DONOR = "../firmware/donor/extracted/"
INFO = "out/guest-tree-property-info-full/donor-v1/"
LAYOUT = "out/guest-tree-property-view/layout-source.json"
BOOT = "out/guest-tree-boot-properties/receipt.json"
SEED = (
    "ro.build.version.sdk", "ro.build.version.sdk_full", "ro.build.version.preview_sdk",
    "ro.build.version.preview_sdk_fingerprint", "ro.build.version.codename",
    "ro.build.version.all_codenames", "ro.build.version.known_codenames",
    "ro.treble.enabled", "ro.vndk.lite",
)
AREA_SIZE = 262144
HEADER = 128
INITIAL_USED = 112
MAGIC, VERSION = 0x504F5250, 0xFC6ED0AB
LONG_SERIAL = 0x32010000
LONG_WARNING = b"Must use __system_property_read_callback() to read\0"
KNOWN = "ro.build.version.known_codenames"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def file_key(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_held(path, size):
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and first.st_size == size,
            f"Plain exact-size input: {path}")
    with path.open("rb") as stream:
        fd = os.fstat(stream.fileno())
        require(file_key(fd) == file_key(first), "Input identity on open")
        raw = stream.read(size + 1)
        after_fd = os.fstat(stream.fileno())
        require(len(raw) == size and file_key(after_fd) == file_key(fd) and
                after_fd.st_ctime_ns == fd.st_ctime_ns, "Unchanged input descriptor")
    last = path.lstat()
    require(plain(last) and file_key(last) == file_key(first) and
            last.st_ctime_ns == first.st_ctime_ns, "Unchanged input name")
    return raw


def held_definitions(raw, names, constants, scope):
    selected = []
    for node in ast.parse(raw).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            selected.append(node)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in constants:
                selected.append(node)
    require(len(selected) == len(names) + len(constants), "Exact selected first-party definitions")
    exec(compile(ast.Module(body=selected, type_ignores=[]), "pinned definitions", "exec"), scope)
    return scope


def add_seed(area, name, value):
    raw = value.encode("ascii")
    if len(raw) < 92:
        return {"encoding": "short", **area.add(name, value)}
    require(name == KNOWN and 92 <= len(raw) <= 512 and name.startswith("ro."),
            "One source-supported read-only long property")
    at = 0
    key = name.encode("ascii")
    for part in key.split(b"."):
        at = area.child(at, part)
    require(area.get(at + 4) == 0, "Duplicate property")
    prop = area.allocate(96 + len(key) + 1)
    value_at = area.allocate(len(raw) + 1)
    area.put(prop, LONG_SERIAL)
    area.store(prop + 4, LONG_WARNING)
    area.put(prop + 60, value_at - prop)
    area.store(prop + 96, key + b"\0")
    area.store(value_at, raw + b"\0")
    area.put(at + 4, prop)
    return {"encoding": "read-only-long", "trieOffset": at,
            "propertyOffset": prop, "longValueOffset": value_at}


def decode_area(raw, expected_serial):
    """Walk the emitted bionic tree and check independent record/extent coverage."""
    require(len(raw) == AREA_SIZE, "Exact selected area size")
    used, serial, magic, version = struct.unpack_from("<4I", raw)
    require(INITIAL_USED <= used <= AREA_SIZE - HEADER and used % 4 == 0 and
            (serial, magic, version) == (expected_serial, MAGIC, VERSION), "Area framing and serial")
    require(not any(raw[16:HEADER]) and not any(raw[HEADER + used:]),
            "Zero reserved and unused bytes in a fresh snapshot")
    data = memoryview(raw)[HEADER:HEADER + used]
    require(not any(data[:16]) and not any(data[20:INITIAL_USED]), "Root and dirty backup shape")
    occupied = bytearray(used // 4)
    occupied[:INITIAL_USED // 4] = b"\1" * (INITIAL_USED // 4)
    properties = {}

    def span(at, size):
        slots = (size + 3) // 4
        start = at // 4
        require(at % 4 == 0 and INITIAL_USED <= at and at + slots * 4 <= used and
                not any(occupied[start:start + slots]), "Disjoint in-bounds area record")
        occupied[start:start + slots] = b"\1" * slots
        require(not any(data[at + size:at + slots * 4]), "Zero record padding")

    def value_at(offset, key):
        span(offset, 96 + len(key) + 1)
        require(bytes(data[offset + 96:offset + 97 + len(key)]) == key + b"\0",
                "Property name matches the actual trie")
        bits, = struct.unpack_from("<I", data, offset)
        if bits == LONG_SERIAL:
            require(key.startswith(b"ro.") and bytes(data[offset + 4:offset + 55]) == LONG_WARNING and
                    not any(data[offset + 55:offset + 60]) and not any(data[offset + 64:offset + 96]),
                    "Donor long record header and compatibility warning")
            relative, = struct.unpack_from("<I", data, offset + 60)
            require(relative == (96 + len(key) + 4) & ~3, "Writer long value follows the name")
            start = offset + relative
            end = raw.find(b"\0", HEADER + start, HEADER + min(start + 513, used)) - HEADER
            require(92 <= end - start <= 512, "Bounded terminated long value")
            span(start, end - start + 1)
            return bytes(data[start:end]).decode("ascii"), "read-only-long"
        size = bits >> 24
        require(bits & 0xFFFFFF == 0 and 0 < size < 92 and data[offset + 4 + size] == 0 and
                not any(data[offset + 4 + size:offset + 96]), "Unchanged short record serial and value")
        value = bytes(data[offset + 4:offset + 4 + size])
        require(b"\0" not in value, "No embedded value terminator")
        return value.decode("ascii"), "short"

    def walk(offset, path, lower, upper, depth):
        if not offset:
            return
        require(depth <= 64 and offset % 4 == 0 and INITIAL_USED <= offset <= used - 20,
                "Bounded trie traversal")
        size, prop, left, right, child = struct.unpack_from("<5I", data, offset)
        require(0 < size <= 255, "Bounded node segment")
        span(offset, 21 + size)
        name = bytes(data[offset + 20:offset + 20 + size])
        require(data[offset + 20 + size] == 0 and re.fullmatch(rb"[A-Za-z0-9_:@-]+", name),
                "Terminated selected node segment")
        order = (size, name)
        require((lower is None or lower < order) and (upper is None or order < upper),
                "Bionic length-then-byte sibling order")
        key = (*path, name)
        if prop:
            full = b".".join(key)
            require(full not in properties, "Distinct property record")
            properties[full] = value_at(prop, full)
        walk(left, path, lower, order, depth + 1)
        walk(right, path, order, upper, depth + 1)
        walk(child, key, None, None, depth + 1)

    root, = struct.unpack_from("<I", data, 16)
    walk(root, (), None, None, 0)
    require(all(occupied), "All used area bytes accounted for")
    return {key.decode("ascii"): value for key, value in sorted(properties.items())}


def derive():
    pins = {}

    def load(name, size, expected):
        raw = read_held(ROOT / name, size)
        require(digest(raw) == expected, f"Exact held input {name}")
        pins[name] = {"bytes": size, "sha256": expected}
        return raw

    def metadata(name, size, expected):
        return json.loads(load(name, size, expected))

    boot = metadata(BOOT, 13744, "e7e458a1541ee25f7a5b5432a12ec6e2fd76c0809c50fb2c37d53ed0b901985e")
    info = metadata(INFO + "receipt.json", 5802, "4be17a0b3501543a7055db9c1d16b29f3d9024c8078cb89ae669d73a6c1092bf")
    layout = metadata(LAYOUT, 4379, "2ef78829d096c734caf19124a35ff9286540fa07000cffc0444b898da90e544d")
    require(boot["effectiveProperties"] is None and info["effectiveValues"] is None and
            not info["runtimePropertyInfoAdmitted"] and layout["privateArea"] is None,
            "Held source declarations and context policy only")
    context_bin = load(INFO + "property_info.donor.bin", info["output"]["bytes"], info["output"]["sha256"])
    parser = load("tools/build_guest_tree_property_info.py", 18044,
        "c6c90b2ee5043cf7c05ce563929c0d9685052724b17543a8eece372d7615fdd9")
    reader = held_definitions(parser, {"decode", "lookup", "override"},
        {"DEFAULT", "UNSET", "MISSING", "LIMIT", "NAME"},
        {"Counter": Counter, "struct": struct, "re": re, "require": require})
    tree, source_rules, _, table_sizes = reader["decode"](context_bin)
    require(len(source_rules) == 2255 and table_sizes == (450, 27), "Full donor context metadata")
    contexts_ref, = struct.unpack_from("<I", context_bin, 12)
    count, = struct.unpack_from("<I", context_bin, contexts_ref)
    require(count == 450, "All donor context names")
    contexts = []
    for address in struct.unpack_from(f"<{count}I", context_bin, contexts_ref + 4):
        end = context_bin.index(0, address)
        contexts.append(context_bin[address:end].decode("ascii"))

    libc_pin = layout["libc"]
    libc = load(libc_pin["path"], libc_pin["bytes"], libc_pin["sha256"])
    long_anchors = {0xA49CC: "9f700171", 0xA49E0: "6b797e92", 0xA4A28: "9d000094",
                    0xA4CD0: "c93ac110", 0xA4CD4: "2840a652", 0xA4CE4: "880200b9",
                    0xA4CF4: "8a3203b8", 0xA4D00: "933e00b9", 0xA567C: "08018037",
                    0xA569C: "883e40b9", 0xA56B4: "8202088b"}
    require(all(libc[pc:pc + 4].hex() == word for pc, word in long_anchors.items()) and
            libc.startswith(LONG_WARNING, 0x27428), "Actual donor long writer/reader ABI")
    previous = load("tools/prepare_guest_tree_property_inputs.py", 12327,
        "543ff2a0690ba38f7c22136fe96fb2093a216c86df89229e8501e992d49ccb87")
    writer = held_definitions(previous, {"AreaFixture"}, {"AREA_SIZE", "HEADER_SIZE", "INITIAL_USED"},
        {"KEYS": SEED, "MAGIC": MAGIC, "VERSION": VERSION, "struct": struct, "require": require})
    writer_class = writer["AreaFixture"]

    targets = set(SEED) | set(info["readback"]["criticalKeyMetadata"])
    declarations = {key: [] for key in sorted(targets)}
    prop_pins = {name: row for name, row in boot["pins"].items()
                 if name.startswith(DONOR) and name.endswith("/build.prop")}
    require(len(prop_pins) == 11, "Exact known donor declaration scope")
    for source, pin in prop_pins.items():
        raw = load(source, pin["bytes"], pin["sha256"])
        for number, line in enumerate(raw.splitlines(), 1):
            key, sep, value = line.partition(b"=")
            if sep and key.decode("ascii", "replace") in declarations:
                declarations[key.decode("ascii")].append({"source": source, "line": number,
                                                          "value": value.decode("ascii")})
    for key, old in boot["declarationsInElevenPinnedFiles"].items():
        require(declarations[key] == [{"source": DONOR + row["file"], "line": row["line"], "value": row["value"]}
                                       for row in old], "Previously observed donor declarations agree")

    expected = ("37", "37.0", "0", "REL", "REL", "REL", None, "true", "false")
    required_sources = ([DONOR + "system/build.prop", DONOR + "system/product/etc/build.prop"],) * 7 + (
        [DONOR + "system/build.prop"], [DONOR + "system/product/etc/build.prop"],
    )
    grouped = defaultdict(dict)
    areas = {}
    selected = []
    for key, fixed, sources in zip(SEED, expected, required_sources):
        found = declarations[key]
        require([row["source"] for row in found] == sources and len({row["value"] for row in found}) == 1,
                "Exact source cohort and common declaration value")
        value = found[0]["value"]
        if fixed is not None:
            require(value == fixed, "Expected donor release/platform declaration")
        else:
            require(len(value) == 328 and re.fullmatch(r"[A-Za-z0-9]+(?:,[A-Za-z0-9]+)*", value),
                    "Actual long codename list")
        context, kind = reader["lookup"](tree, key)
        require(context in contexts and kind in ("bool", "int", "string"), "Exact selected context/type")
        if context not in areas:
            areas[context] = writer_class()
        record = add_seed(areas[context], key, value)
        grouped[context][key] = (value, record["encoding"])
        selected.append({"key": key, "context": context, "metadataType": kind, "storedSourceValue": value,
                         "declarations": found, **record})

    files = {}
    members = {}
    for i, (context, area) in enumerate(sorted(areas.items())):
        name = f"context-{i:02d}.fixture.bin"
        raw = bytes(area.bytes)
        require(decode_area(raw, 0) == grouped[context], "Independent exact context-area readback")
        files[name] = raw
        members[name] = {"intendedContextBasename": context, "serial": 0, "usedBytes": area.used,
                         "records": len(grouped[context]), "bytes": len(raw), "sha256": digest(raw)}
    serial = writer_class()
    struct.pack_into("<I", serial.bytes, 4, len(selected))
    serial_bytes = bytes(serial.bytes)
    require(decode_area(serial_bytes, len(selected)) == {}, "Independent exact serial companion readback")
    files["serial.fixture.bin"] = serial_bytes
    members["serial.fixture.bin"] = {"intendedContextBasename": "properties_serial", "serial": len(selected),
                                     "usedBytes": INITIAL_USED, "records": 0, "bytes": len(serial_bytes),
                                     "sha256": digest(serial_bytes)}

    held = []
    for key in sorted(targets - set(SEED)):
        context, kind = reader["lookup"](tree, key)
        require(info["readback"]["criticalKeyMetadata"][key] == [context, kind],
                "Unseeded context remains original")
        source = declarations[key]
        held.append({"key": key, "context": context, "metadataType": kind, "declarations": source,
                     "state": "DECLARED_BUT_POLICY_OR_LIFETIME_UNBOUND" if source else "NO_HELD_DECLARATION",
                     "storedValue": None, "effectiveValue": None})

    receipt = {
        "schema": "guest-tree-property-area-seed/v1",
        "status": "SOURCE_BACKED_SNAPSHOT_BYTES_ONLY",
        "toolSha256": digest(Path(__file__).read_bytes()), "pins": pins,
        "propertyInfo": info["output"], "fullContextNameTable": contexts,
        "contextCount": count, "populatedContextCount": len(areas), "otherContextsMaterialized": False,
        "selectedInsertionOrder": selected, "members": members, "unseededCriticalKeys": held,
        "nativeLongRecordAnchors": {hex(pc): word for pc, word in long_anchors.items()},
        "missing": ["Actual staged retained property_info and context file mapping/labels/read access",
                    "Private producer for other context areas, effective initial values and any later writes",
                    "Ownership or deliberate exclusion of debug/rescue/cgroup/persistent inputs"],
        "effectiveProperties": None, "runtimeExports": None, "entryAdmitted": False,
        "hostFallbackUsed": False, "propertyWrites": False, "targetExecuted": False,
    }
    files["receipt.json"] = (json.dumps(receipt, indent=2) + "\n").encode()
    return files, grouped, members


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--stage", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--require-effective", action="store_true")
    args = parser.parse_args()
    try:
        files, groups, members = derive()
        require(not args.require_effective, "Actual private effective property input is unbound")
        target = OUT / "donor-v1"
        for folder in (OUT.parent, OUT, target):
            if args.stage:
                folder.mkdir(exist_ok=folder != target)
            info = folder.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain private output path")
        for name, raw in files.items():
            path = target / name
            if args.stage:
                with path.open("xb") as stream:
                    stream.write(raw)
            saved = read_held(path, len(raw))
            require(saved == raw, "Exact saved area/receipt")
            if name in members:
                row = members[name]
                require(decode_area(saved, row["serial"]) == groups.get(row["intendedContextBasename"], {}),
                        "Saved independent area readback")
            print(f"{path.relative_to(ROOT).as_posix()} {len(raw)} {digest(raw)}")
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        parser.exit(2, f"Refused: {error}\n")


if __name__ == "__main__":
    main()
