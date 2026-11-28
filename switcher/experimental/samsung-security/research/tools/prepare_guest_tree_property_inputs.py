"""Produce inert donor-layout fixtures for two fixed boot properties."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import struct


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-property-inputs"
SYSTEM = "../firmware/donor/extracted/system/"
LIBC = "../firmware/donor/apex/005-com.android.runtime/files/lib64/bionic/libc.so"
LAYOUT = "out/guest-tree-property-view/layout-source.json"
SYSTEM_PROP = SYSTEM + "build.prop"
PRODUCT_PROP = SYSTEM + "product/etc/build.prop"
KEYS = ("ro.build.version.sdk", "ro.build.version.codename")
CONTEXT = "u:object_r:build_prop:s0"
SERIAL_CONTEXT = "u:object_r:properties_serial:s0"
HEADER_SIZE = 128
AREA_SIZE = 262144
INITIAL_USED = 112
MAGIC, VERSION = 0x504F5250, 0xFC6ED0AB


def require(condition, label):
    if not condition:
        raise ValueError(label)


def digest(raw):
    return sha256(raw).hexdigest()


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def key(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_held(path, size):
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and first.st_size == size,
            f"Plain file of exact size: {path}")
    with path.open("rb") as stream:
        initial = os.fstat(stream.fileno())
        require(key(initial) == key(first), "Input changed on open")
        raw = stream.read(size + 1)
        last = os.fstat(stream.fileno())
        require(len(raw) == size and key(last) == key(initial) and
                last.st_ctime_ns == initial.st_ctime_ns, "Input changed during read")
    final = path.lstat()
    require(plain(final) and key(final) == key(first) and
            final.st_ctime_ns == first.st_ctime_ns, "Input name changed during read")
    return raw


def call(raw, pc, expected):
    insn = struct.unpack_from("<I", raw, pc)[0]
    immediate = insn & 0x03FFFFFF
    displacement = (immediate - (1 << 26) if immediate & (1 << 25) else immediate) * 4
    require(insn >> 26 == 0x25 and pc + displacement == expected, f"Exact BL at {pc:#x}")


class AreaFixture:
    """Single-threaded serializer of the selected ordinary bionic area subset."""

    def __init__(self):
        self.bytes = bytearray(AREA_SIZE)
        self.used = INITIAL_USED
        struct.pack_into("<IIII", self.bytes, 0, self.used, 0, MAGIC, VERSION)

    def allocate(self, size):
        start = self.used
        self.used += (size + 3) & ~3
        require(self.used <= AREA_SIZE - HEADER_SIZE, "Bounded donor-format data")
        struct.pack_into("<I", self.bytes, 0, self.used)
        return start

    def get(self, offset):
        return struct.unpack_from("<I", self.bytes, HEADER_SIZE + offset)[0]

    def put(self, offset, value):
        struct.pack_into("<I", self.bytes, HEADER_SIZE + offset, value)

    def store(self, offset, value):
        start = HEADER_SIZE + offset
        self.bytes[start:start + len(value)] = value

    def child(self, parent, segment):
        edge = parent + 16
        while at := self.get(edge):
            length = self.get(at)
            start = HEADER_SIZE + at + 20
            node = bytes(self.bytes[start:start + length])
            if node == segment:
                return at
            edge = at + (8 if (len(segment), segment) < (length, node) else 12)
        at = self.allocate(20 + len(segment) + 1)
        self.put(at, len(segment))
        self.store(at + 20, segment + b"\0")
        self.put(edge, at)
        return at

    def add(self, name, value):
        encoded, value = name.encode("ascii"), value.encode("ascii")
        require(name in KEYS and 0 < len(value) < 92, "Fixed, short-property subset")
        at = 0
        for segment in encoded.split(b"."):
            at = self.child(at, segment)
        require(self.get(at + 4) == 0, "Duplicate property")
        prop = self.allocate(96 + len(encoded) + 1)
        self.put(prop, len(value) << 24)
        self.store(prop + 4, value + b"\0")
        self.store(prop + 96, encoded + b"\0")
        self.put(at + 4, prop)
        return {"trieOffset": at, "propertyOffset": prop}


def derive():
    inputs = {}

    def read(path, size, expected):
        raw = read_held(ROOT / path, size)
        require(digest(raw) == expected, f"Pinned source: {path}")
        inputs[path] = {"bytes": size, "sha256": expected}
        return raw

    layout = json.loads(read(LAYOUT, 4379,
        "2ef78829d096c734caf19124a35ff9286540fa07000cffc0444b898da90e544d"))
    libc = read(LIBC, 1550096, "c9057b270a62b45b0dcae87e5d6a187a2dde1e7f86f8a2e0d68f2eb180e57d99")
    require(layout["libc"]["sha256"] == digest(libc) and layout["privateArea"] is None and
            layout["compiledPropertyInfo"] is None, "Same layout source, genuine area still absent")
    for anchor in layout["nativeAnchors"]:
        pc = int(anchor["filePc"], 16)
        require(libc[pc:pc + 4].hex() == anchor["bytes"], "Exact writer/layout instruction")
    require(struct.unpack_from("<II", libc, 0x1B578) == (MAGIC, VERSION) and
            libc.startswith(b"properties_serial\0", 0x24CED) and
            libc.startswith(SERIAL_CONTEXT.encode("ascii") + b"\0", 0x1EDF1),
            "Original header and companion serial area")
    for pc, target in ((0xC4074, 0xA4F48), (0xA3FF0, 0xA2EA8),
                       (0xA4000, 0xA2EB8), (0xA400C, 0xA3DB0), (0xA4050, 0xA3010),
                       (0xA4084, 0xA43C8), (0xA4428, 0x11F1F8),
                       (0xA5A80, 0xA4BD8)):
        call(libc, pc, target)
    require(libc[0xA5C18:0xA5C28].hex() == "c80640b9d41200910805001188fe9f88",
            "Normal successful add increments and publishes serial at +4")

    init = read(SYSTEM + "bin/init", 2888328,
                "8db6b39facd5af0745d9bd27c588dacedb6ae5e21a87870644d0b49d33e19757")
    for pc, target in ((0x106018, 0x2A0B40), (0x106780, 0x16B3E8), (0x1073F4, 0x2A1E48),
                       (0x107434, 0x2A19E0), (0x1068B8, 0x2A2178), (0xFCE38, 0x2A2130)):
        call(init, pc, target)
    require(init.startswith(b"/dev/__properties__/property_info\0", 0x36CB9) and
            init.startswith(b"/dev/__properties__\0", 0x2E3FE) and
            init[0x106014:0x106018].hex() == "21398052" and
            init[0x1073E0:0x1073E4].hex() == "82248052", "Exact original directory and info modes")
    rc = read(SYSTEM + "etc/init/hw/init.rc", 117704,
              "d14ca8301c0795a6fe10425a3d20bf8fbf628b0aeed4b7b6f560fd061e78dcd1").splitlines()
    for line, expected in ((157, b"perform_apex_config"), (1663, b"perform_apex_config"),
                           (1689, b"exec_start derive_classpath"),
                           (1690, b"load_exports /data/system/environ/classpath"),
                           (1860, b"start zygote")):
        require(rc[line - 1].strip() == expected, f"Exact init phase line {line}")

    for item in layout["exactContextSources"]:
        raw = read(item["path"], item["bytes"], item["sha256"])
        exact = []
        for number, line in enumerate(raw.splitlines(), 1):
            parts = line.split()
            if parts and parts[0].decode("ascii", "replace") in KEYS:
                exact.append([number, *[part.decode("ascii") for part in parts]])
        require(exact == item["exactRules"], "Current exact donor context source rules")
    require(layout["exactContextSources"][0]["exactRules"] ==
            [[1144, KEYS[1], CONTEXT, "exact", "string"], [1152, KEYS[0], CONTEXT, "exact", "int"]],
            "Same source context for both keys")

    props = {
        SYSTEM_PROP: read(SYSTEM_PROP, 28816,
            "4661edb3c8e09ac75af0bd19a0c48fecba86511f3d6bec383c0db4bd31709582"),
        PRODUCT_PROP: read(PRODUCT_PROP, 4668,
            "768eca01390a557b871c75b9c4abfc728c4916a8101a0628421d57f2de02b94b"),
    }
    fixture, serial = AreaFixture(), AreaFixture()
    records = []
    for name, expected in zip(KEYS, ("37", "REL")):
        anchors = []
        prefix = name.encode("ascii") + b"="
        for path, raw in props.items():
            found = [(n, line[len(prefix):].decode("ascii")) for n, line in
                     enumerate(raw.splitlines(), 1) if line.startswith(prefix)]
            require(len(found) == 1 and found[0][1] == expected, "Matching donor declarations")
            anchors.append({"path": path, "line": found[0][0]})
        record = fixture.add(name, expected)
        records.append({"key": name, "sourceValue": expected, "declarations": anchors, **record})
        count = struct.unpack_from("<I", serial.bytes, 4)[0]
        struct.pack_into("<I", serial.bytes, 4, count + 1)
    fixtures = {
        "build-prop-area.fixture.bin": bytes(fixture.bytes),
        "serial-area.fixture.bin": bytes(serial.bytes),
    }
    receipt = {
        "schema": "guest-tree-property-inputs/v1",
        "status": "INERT_WRITER_LAYOUT_FIXTURES_ONLY",
        "toolSha256": digest(Path(__file__).read_bytes()),
        "inputs": inputs,
        "fixtures": {name: {"bytes": len(raw), "sha256": digest(raw)} for name, raw in fixtures.items()},
        "selectedInsertionOrder": records,
        "format": {"headerBytes": HEADER_SIZE, "areaBytes": AREA_SIZE, "initialUsed": INITIAL_USED,
                   "contextAreaUsed": fixture.used, "selectedSerial": len(records), "context": CONTEXT,
                   "serialContext": SERIAL_CONTEXT, "propertyInfoProduced": False},
        "originalProducer": {
            "initMkdirPc": "0x106018", "directoryMode": "0711",
            "propertyInfoWritePc": "0x1073f4", "propertyInfoRestoreconPc": "0x107434",
            "areaInitPc": "0x1068b8", "addPc": "0xfce38", "fileMode": "0444",
            "libcInfoLoadPc": "0xa3ff0", "libcContextCreatePc": "0xa4050",
            "libcSerialCreatePc": "0xa4084", "libcLabelPc": "0xa4428",
            "libcRecordPublishPc": "0xa4a48", "libcSerialPublishPc": "0xa5c24",
            "rcPhaseLines": [157, 1663, 1689, 1690, 1860],
        },
        "privateProvisioningBoundary": [
            "Retain a fresh private /dev in the actual final root before any selected consumer initializes bionic.",
            "The boot owner must first publish compiled property_info from the admitted partition contexts, verify its exact key-to-context selection, and create labelled context and serial areas in that same view.",
            "Seed source-owned effective values before the first linkerconfig/derive/app_process consumer. Verify actual path, mount identity, owner, mode, label and SELinux read access. No host /dev import or inherited property mapping.",
            "Any real property service, persistent store or update/wait capability needs its own private producer and retirement. The fixture supplies no service, context compilation, effective values, or complete boot input set.",
        ],
        "effectiveProperties": None, "runtimeExports": None, "entryAdmitted": False,
        "propertyWrites": False, "hostFallbackUsed": False, "targetExecuted": False,
    }
    fixtures["receipt.json"] = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
    return fixtures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--stage", action="store_true")
    actions.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        fixtures = derive()
        for folder in (OUT.parent, OUT, OUT / "fixture-v1"):
            if args.stage:
                folder.mkdir(exist_ok=folder != OUT / "fixture-v1")
            info = folder.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain owned output directory")
        for name, raw in fixtures.items():
            path = OUT / "fixture-v1" / name
            if args.stage:
                with path.open("xb") as stream:
                    stream.write(raw)
            require(read_held(path, len(raw)) == raw, f"Exact saved fixture: {name}")
            print(f"{path.relative_to(ROOT).as_posix()} {len(raw)} {digest(raw)}")
    except (OSError, ValueError, KeyError, IndexError) as error:
        parser.exit(2, f"Refused: {error}\n")


if __name__ == "__main__":
    main()
