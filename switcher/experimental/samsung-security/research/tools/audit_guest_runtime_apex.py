"""Read the exact donor image and held APEX files as data. No mounting or execution."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import stat
import struct
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT.parent / "firmware/donor"
IMAGE = DONOR / "OneOS_ColorOS17_FindX9Ultra_IN_Full.img"
RUNTIME = DONOR / "apex/005-com.android.runtime"
ART = DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img"
SEED = "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379"
INTERPRETER = "/apex/com.android.runtime/bin/linker64"
PREPARE = (
    ROOT / "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/raw"
    / "45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/guest_prepare.sh"
)


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return sha256(data).hexdigest()


def pinned(path, expected, bound):
    with path.open("rb") as stream:
        raw = stream.read(bound + 1)
    need(len(raw) <= bound and digest(raw) == expected, f"Input differs: {path.name}")
    return raw


def u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


class SelectedExt4:
    """Only the observed 4 KiB, depth-zero selected inode profiles."""

    def __init__(self, stream, extent, uuid, features, inodes_per_group, filesystem_bytes):
        self.stream = stream
        self.extent = extent
        self.bytes_read = 0
        sb = self.read(1024, 1024)
        need(u16(sb, 56) == 0xef53 and sb[104:120].hex() == uuid
             and u32(sb, 24) == 2 and u16(sb, 88) == 256
             and u32(sb, 96) == features and u32(sb, 40) == inodes_per_group
             and not u32(sb, 100) & 0x400, "Selected ext4 profile")
        self.blocks = u32(sb, 4)
        self.inodes = u32(sb, 0)
        self.inodes_per_group = inodes_per_group
        need(self.blocks * 4096 == filesystem_bytes <= extent, "Filesystem extent")

    def read(self, offset, size):
        need(0 <= offset and 0 < size <= 6 * 1024 * 1024 and offset + size <= self.extent
             and self.bytes_read + size <= 8 * 1024 * 1024, "Bounded selected read")
        self.stream.seek(offset)
        raw = self.stream.read(size)
        need(len(raw) == size, "Short image read")
        self.bytes_read += size
        return raw

    def inode(self, number, limit):
        need(1 <= number <= self.inodes, "Inode bounds")
        group, index = divmod(number - 1, self.inodes_per_group)
        desc = self.read(4096 + group * 32, 32)
        table = u32(desc, 8)
        need(0 < table < self.blocks, "Inode table block")
        raw = self.read(4096 * table + index * 256, 256)
        mode = u16(raw, 0)
        size = u32(raw, 4) + (u32(raw, 108) << 32)
        flags = u32(raw, 32)
        uid = u16(raw, 2) + (u16(raw, 120) << 16)
        gid = u16(raw, 24) + (u16(raw, 122) << 16)
        need(0 < size <= limit, "Selected inode file extent")
        if stat.S_ISLNK(mode):
            need(flags == 0 and size <= 60, "Only fast symlinks")
            data = raw[40:40 + size]
        else:
            need(flags == 0x80000 and (stat.S_ISREG(mode) or stat.S_ISDIR(mode)),
                 "Selected inode type and flags")
            magic, count, capacity, depth = struct.unpack_from("<HHHH", raw, 40)
            need(magic == 0xf30a and depth == 0 and 0 < count <= capacity <= 4,
                 "Selected inode inline extent tree")
            buffer = bytearray(size)
            last = 0
            for i in range(count):
                logical, blocks, high, low = struct.unpack_from("<IHHI", raw, 52 + i * 12)
                physical = (high << 32) + low
                start = logical * 4096
                need(0 < blocks <= 32768 and 0 < physical < physical + blocks <= self.blocks
                     and last <= start < size, "Ordered initialized extent")
                need(not stat.S_ISDIR(mode) or start == last, "No sparse directory")
                last = min(start + blocks * 4096, size)
                buffer[start:last] = self.read(physical * 4096, last - start)
            need(not stat.S_ISDIR(mode) or last == size, "Complete directory")
            data = bytes(buffer)
        return data, {"inode": number, "mode": oct(mode), "uid": uid, "gid": gid,
                      "bytes": size, "sha256": digest(data)}

    def directory(self, number):
        data, row = self.inode(number, 16384)
        need(stat.S_ISDIR(int(row["mode"], 8)) and not len(data) % 4096, "Directory framing")
        names = {}
        cursor = 0
        while cursor < len(data):
            inode, rec, count, kind = struct.unpack_from("<IHBB", data, cursor)
            need(rec >= 8 and not rec % 4 and cursor % 4096 + rec <= 4096
                 and count <= rec - 8 and kind <= 7, "Directory record")
            if inode:
                name = data[cursor + 8:cursor + 8 + count].decode()
                need(0 < inode <= self.inodes and name and "/" not in name
                     and "\0" not in name and name not in names, "Unique directory name")
                names[name] = (inode, kind)
            cursor += rec
        return names, row

    def lookup(self, path, kind, limit):
        parts = path.split("/")
        number = 2
        for part in parts[:-1]:
            number, entry_type = self.directory(number)[0][part]
            need(entry_type == 2, "Directory-only path ancestors")
        number, entry_type = self.directory(number)[0][parts[-1]]
        need(entry_type == kind, "Selected directory entry type")
        return self.inode(number, limit)


def elf(raw):
    need(raw[:7] == b"\x7fELF\x02\x01\x01" and struct.unpack_from("<HH", raw, 16) == (3, 183),
         "AArch64 ELF64 little-endian ET_DYN")
    phoff = struct.unpack_from("<Q", raw, 32)[0]
    entsize, count = struct.unpack_from("<HH", raw, 54)
    need(entsize == 56 and 0 < count <= 32 and phoff + count * entsize <= len(raw), "ELF program table")
    rows = [struct.unpack_from("<IIQQQQQQ", raw, phoff + i * entsize) for i in range(count)]
    need(all(row[2] + row[5] <= len(raw) for row in rows), "File-backed ELF extents")
    interps = [raw[row[2]:row[2] + row[5]] for row in rows if row[0] == 3]
    need(len(interps) <= 1 and all(s.endswith(b"\0") and s.count(b"\0") == 1 for s in interps),
         "ELF interpreter framing")
    dynamic, = [row for row in rows if row[0] == 2]
    tags = []
    for offset in range(dynamic[2], dynamic[2] + dynamic[5], 16):
        tag, value = struct.unpack_from("<QQ", raw, offset)
        if tag == 0:
            break
        tags.append((tag, value))
    else:
        raise ValueError("ELF dynamic terminator")
    address, = [value for tag, value in tags if tag == 5]
    extent, = [value for tag, value in tags if tag == 10]
    mapping, = [row for row in rows if row[0] == 1 and row[3] <= address
                and address + extent <= row[3] + row[5]]
    start = mapping[2] + address - mapping[3]
    strings = raw[start:start + extent]

    def text(offset):
        need(0 <= offset < len(strings), "Dynamic string offset")
        end = strings.index(b"\0", offset)
        return strings[offset:end].decode("ascii")

    return {
        "bytes": len(raw), "sha256": digest(raw), "machine": "AArch64", "elfType": "ET_DYN",
        "interpreter": interps[0][:-1].decode("ascii") if interps else None,
        "needed": [text(value) for tag, value in tags if tag == 1],
        "soname": next((text(value) for tag, value in tags if tag == 14), None),
        "searchOverrides": [text(value) for tag, value in tags if tag in (15, 29)],
        "loadAlignments": [row[7] for row in rows if row[0] == 1],
    }


def audit():
    manifest = ROOT.parent / "inventory/donor-image.json"
    inv = json.loads(pinned(manifest, "fa1734294e0d8a5d03a1a96a3b0f7ebbfdb0172838d7ca62f812f5ab9d606c3d", 4096))
    before = IMAGE.stat()
    need(before.st_size == inv["rawBytes"] == 14669168640, "Exact held donor extent")
    with IMAGE.open("rb") as stream:
        image = SelectedExt4(stream, before.st_size, "e9555a2828944946be2892b50d3545a9", 0x242,
                             8160, inv["filesystemBytes"])
        root, _ = image.directory(2)
        targets = {}
        for name, number in (("apex", 13), ("linkerconfig", 31)):
            need(root[name] == (number, 2), "Exact boot target")
            children, targets[name] = image.directory(number)
            need(children == {".": (number, 2), "..": (2, 2)}
                 and targets[name]["mode"] == "0o40755"
                 and targets[name]["uid"] == targets[name]["gid"] == 0, "Empty root-owned boot target")
        link, link_row = image.lookup("system/bin/linker64", 7, 60)
        app, app_row = image.lookup("system/bin/app_process64", 1, 65536)
        apex, apex_row = image.lookup("system/apex/com.android.runtime.apex", 1, 6 * 1024 * 1024)
    after = IMAGE.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    need(identity(before) == identity(after) and link.decode() == INTERPRETER, "Held image identity and link")
    extracted = DONOR / "extracted"
    for path, raw, expected in (
        ("system/bin/app_process64", app, "78d3bf52333a151a6f4859f5144de5578adf009503b792a91db307435a0f21dc"),
        ("system/apex/com.android.runtime.apex", apex, "f92cbc75018c8620dff83afc47288aa3391f0cbbb1b6578279cd51156dd257d0"),
    ):
        need(pinned(extracted / path, expected, len(raw)) == raw, "Direct image/extraction equality")
    with ZipFile(BytesIO(apex)) as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)) == 10, "Unique held APEX ZIP members")
        payload = archive.read("apex_payload.img")
        pb = archive.read("apex_manifest.pb")
    need(len(payload) == 5296128 and u32(payload, 1024) == 0xe0f5e1e2
         and pinned(RUNTIME / "apex_payload.img", SEED, 5296128) == payload, "Exact EROFS payload")
    need(pb.startswith(b"\x0a\x13com.android.runtime\x10\x01")
         and (RUNTIME / "files/apex_manifest.pb").read_bytes() == pb, "Runtime module name and version")
    sets = pinned(ROOT / "firmware/oneos-pr/OneOS/app-android/packages/x9u-in-sultra.sha256",
                  "cca1a57021c781d7fb590c311194a009b98345304520e56d46828e670cbdbc57", 8192)
    need([line.split() for line in sets.decode().splitlines() if "runtime_payload.img" in line]
         == [[SEED, "runtime_payload.img"]], "OneOS x9u-in payload equality")
    prep = pinned(PREPARE, "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d", 300000)
    prep_lines = prep.decode().splitlines()
    need('mount --rbind /linkerconfig "$ROOTFS/linkerconfig"' in prep_lines[333]
         and prep_lines[3934] == 'mount_payload "runtime" "com.android.runtime"', "Legacy placement")

    extraction_index = json.loads(pinned(RUNTIME / "erofs-regular-files.json",
        "3b8617b93a307b5693e309eb54479d0a1402454ef44ae4dba75fa619c3bcea58", 4096))
    sizes = {row["Path"]: int(row["Size"]) for row in extraction_index}
    cohort_pins = {
        "bin/linker64": "97f31018817926c4997b77bd7f91372ecbe8345976cc2019d4168b00586430c8",
        "bin/linkerconfig": "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb",
        "lib64/bionic/libc.so": "c9057b270a62b45b0dcae87e5d6a187a2dde1e7f86f8a2e0d68f2eb180e57d99",
        "lib64/bionic/libdl.so": "9805c2a013d994bdefc1c124027c53de81060afc901d2188b6eafdf6783140d4",
        "lib64/bionic/libm.so": "ed5836b43ab5acb7c374f2a414949d2716ec0e38914ffd34875a193ffcf1d722",
        "lib64/bionic/libdl_android.so": "6ad8ee8bc0a67a2582f9a9bcc37a40af4aa21236b968a08a895099058066305a",
    }
    cohort = {name: elf(pinned(RUNTIME / "files" / name, pin, sizes[name]))
              for name, pin in cohort_pins.items()}
    need(all(row["bytes"] == sizes[name] for name, row in cohort.items()), "Saved EROFS member extents")
    app_elf = elf(app)
    need(app_elf["interpreter"] == "/system/bin/linker64"
         and cohort["bin/linker64"]["interpreter"] is None
         and cohort["bin/linker64"]["soname"] == "ld-android.so"
         and cohort["bin/linker64"]["needed"] == [], "Interpreter ABI framing")

    art_bytes = pinned(ART, "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148", 31633408)
    art = SelectedExt4(BytesIO(art_bytes), len(art_bytes), "7d1522e19dfa5edba43e98e3a4d20250",
                       0x42, 96, 7660 * 4096)
    locations = {}
    for name in app_elf["needed"]:
        runtime_path = f"lib64/bionic/{name}"
        if runtime_path in cohort:
            location, info = "/apex/com.android.runtime/" + runtime_path, cohort[runtime_path]
        elif name in {"libnativeloader.so", "libsigchain.so"}:
            raw, _ = art.lookup(f"lib64/{name}", 1, 262144)
            location, info = f"/apex/com.android.art/lib64/{name}", elf(raw)
        else:
            location = f"/system/lib64/{name}"
            info = elf((extracted / location[1:]).read_bytes())
        need(info["soname"] == name, f"Selected direct dependency SONAME {name}")
        locations[name] = {"candidate": location, **info}
    need(len(locations) == 14, "Exact direct app_process64 dependency names")
    init = pinned(extracted / "system/etc/init/hw/init.rc",
                  "d14ca8301c0795a6fe10425a3d20bf8fbf628b0aeed4b7b6f560fd061e78dcd1", 512000)
    init_lines = init.decode().splitlines()
    need(init_lines[120].strip() == "mkdir /linkerconfig/bootstrap 0755"
         and init_lines[155].strip() == "exec_start apexd-bootstrap"
         and init_lines[156].strip() == init_lines[1662].strip() == "perform_apex_config",
         "Donor boot configuration producer")
    return {
        "schema": "guest-donor-runtime-apex/v1",
        "status": "STATIC_DONOR_RUNTIME_APEX_AND_DIRECT_ELF_INPUTS_PINNED",
        "image": {"path": "../firmware/donor/" + IMAGE.name, "bytes": before.st_size,
                  "sha256InheritedNotRecomputed": inv["rawSha256"],
                  "bytesRead": image.bytes_read, "statStable": True},
        "emptyImageDirectories": targets,
        "interpreterLink": {"path": "/system/bin/linker64", "target": INTERPRETER, **link_row},
        "outerRuntimeApex": {"path": "/system/apex/com.android.runtime.apex", **apex_row},
        "runtimePayload": {"sha256": SEED, "bytes": len(payload), "filesystem": "EROFS",
                           "oneOsSet": "x9u-in-sultra", "module": "com.android.runtime", "version": 1},
        "runtimeSavedExtraction": cohort,
        "runtimeExtractionFreshlyReplayed": False,
        "appProcess64": {"path": "/system/bin/app_process64", "sourceInode": app_row, **app_elf},
        "directLibraryCandidates": locations,
        "donorLinkerConfigInitLines": [121, 122, 134, 135, 140, 156, 157, 1663],
        "legacyOneOsPlacementLines": [334, 335, 3935],
        "actualNamespaceResolutionProved": False,
        "nativeOrDeviceExecuted": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
