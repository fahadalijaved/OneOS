"""Verify the held donor app_process64 and runtime APEX source chain offline."""

import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
from zipfile import ZipFile

from check_guest_tree_active_apex import DONOR, ROOT, digest, plain_directory, read_exact, require


OUT = ROOT / "out/guest-tree-runtime-apex"
NAME = "com.android.runtime"
APEX = "/apex/" + NAME
RUNTIME = DONOR / "apex/005-com.android.runtime"
IMAGE = DONOR / "OneOS_ColorOS17_FindX9Ultra_IN_Full.img"
REV = "45abb3df03cbd4a8b006519baaebefdb2c68658a"
UPSTREAM = ROOT / "firmware/upstream-oneos-0.4.58" / REV / "raw" / REV
PINS = {
    "fileReader": (ROOT / "tools/check_guest_tree_active_apex.py", 13501,
                   "4fe18c87e9e0b45203ef97a0a4e9a0ce69127128da3d446154fc0e042292c3e8"),
    "reader": (ROOT / "tools/audit_guest_runtime_apex.py", 15155,
               "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de"),
    "priorRuntime": (ROOT / "out/guest-runtime-apex/actual-source-check.json", 17079,
                     "ec8d59bdc9453c08bb26b9b144f270338869d76386f0c5e5b63bdb698f13e705"),
    "donorAliasPolicy": (ROOT / "out/guest-tree-active-apex/candidate.json", 8693,
                        "77d91de3e8405fc87d0b02ee9efe5efcaadf241fb90b66611094680046698328"),
    "runtimeApex": (DONOR / "extracted/system/apex/com.android.runtime.apex", 5435392,
                    "f92cbc75018c8620dff83afc47288aa3391f0cbbb1b6578279cd51156dd257d0"),
    "runtimePayload": (RUNTIME / "apex_payload.img", 5296128,
                       "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379"),
    "artPayload": (DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img", 31633408,
                   "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148"),
    "legacyPrepare": (UPSTREAM / "switcher/assets/guest_prepare.sh", 285232,
                      "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d"),
    "legacySet": (UPSTREAM / "app-android/packages/x9u-in-sultra.sha256", 4594,
                  "132a0db046d64d5056f8783611829159d0bdc2a822507b256eb4e298fce0790c"),
}


def pin(path, size, expected):
    data = read_exact(path, size)
    require(digest(data) == expected, f"Input digest: {path.name}")
    return data


def held_reader(data):
    names = {"need", "digest", "u16", "u32", "SelectedExt4", "elf"}
    body = [node for node in ast.parse(data).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    require({node.name for node in body} == names and len(body) == len(names), "Exact selected reader")
    scope = {"sha256": hashlib.sha256, "struct": struct, "stat": stat}
    exec(compile(ast.Module(body=body, type_ignores=[]), "pinned-runtime-reader", "exec"), scope)
    return scope["SelectedExt4"], scope["elf"]


def image_records(ext4, prior, outer):
    # Only selected original ext4 records are reread. The full-image hash
    # remains inherited from the exact previous held image inventory.
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    plain_directory(IMAGE.parent)
    before = IMAGE.lstat()
    require(stat.S_ISREG(before.st_mode) and not getattr(before, "st_file_attributes", 0) & 0x400
            and before.st_size == prior["image"]["bytes"], "Held donor image extent or type")
    with IMAGE.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(identity(before) == identity(opened), "Opened donor image identity")
        fs = ext4(stream, before.st_size, "e9555a2828944946be2892b50d3545a9",
                  0x242, 8160, 14554550272)
        link, link_row = fs.lookup("system/bin/linker64", 7, 60)
        app, app_row = fs.lookup("system/bin/app_process64", 1, 65536)
        raw_apex, apex_row = fs.lookup("system/apex/com.android.runtime.apex", 1, 6 * 1024 * 1024)
        root, _ = fs.directory(2)
        stock = {}
        for name in ("data", "apex", "bootstrap-apex"):
            nid, kind = root[name]
            require(kind == 2, f"Donor image directory: {name}")
            entries, row = fs.directory(nid)
            require(entries == {".": (nid, 2), "..": (2, 2)}, f"Nonempty held image directory: {name}")
            stock["/" + name] = row
        finished = os.fstat(stream.fileno())
    after = IMAGE.lstat()
    require(stat.S_ISREG(after.st_mode) and not getattr(after, "st_file_attributes", 0) & 0x400
            and identity(before) == identity(after) and before.st_ctime_ns == after.st_ctime_ns
            and identity(opened) == identity(finished) and opened.st_ctime_ns == finished.st_ctime_ns,
            "Donor image changed during selected read")
    require(link == (APEX + "/bin/linker64").encode() and link_row["sha256"] == prior["interpreterLink"]["sha256"]
            and app_row == prior["appProcess64"]["sourceInode"] and raw_apex == outer
            and apex_row["sha256"] == prior["outerRuntimeApex"]["sha256"], "Original donor path continuity")
    return app, {"imageHashInherited": prior["image"]["sha256InheritedNotRecomputed"],
                 "selectedBytesRead": fs.bytes_read, "emptyShippedDirectories": stock,
                 "app": app_row, "interpreterLink": {"target": link.decode(), **link_row}, "outerApex": apex_row}


def runtime_inodes(data):
    require(data[1024:1028] == b"\xe2\xe1\xf5\xe0" and data[1036:1038] == b"\x0c\0"
            and struct.unpack_from("<H", data, 1038) == (39,)
            and struct.unpack_from("<Q", data, 1040) == (27,)
            and struct.unpack_from("<III", data, 1060) == (1280, 0, 0), "Exact compact 4 KiB EROFS profile")
    rows = {}
    inline = {}

    def inode(path, nid, type_bits):
        offset = nid * 32
        require(1024 < offset < 1280 * 4096 - 128 and path not in rows, "Selected inode bounds")
        fmt, count, mode, links, size = struct.unpack_from("<HHHHI", data, offset)
        uid, gid = struct.unpack_from("<HH", data, offset + 24)
        require(fmt in (4, 6) and mode & 0o170000 == type_bits and count in (2, 12),
                f"Selected inode type: {path}")
        xattr_size = 12 + 4 * (count - 1)
        xattrs = data[offset + 32:offset + 32 + xattr_size]
        shared = xattrs[4]
        require(xattrs[5:12] == b"\0" * 7 and (shared, count) in ((1, 2), (0, 12)),
                f"Expected one selected xattr: {path}")
        xoff = 4 * struct.unpack_from("<I", xattrs, 12)[0] if shared else offset + 44
        require(0 < xoff < len(data) - 60, "Selected xattr bounds")
        name_len, index, val_len = struct.unpack_from("<BBH", data, xoff)
        end = xoff + 4 + name_len + val_len
        require((name_len, index) == (7, 6) and data[xoff + 4:xoff + 11] == b"selinux"
                and 0 < val_len <= 40 and (shared or end <= offset + 32 + xattr_size),
                f"Missing security.selinux: {path}")
        label = data[xoff + 11:end]
        require(re.fullmatch(rb"u:object_r:[a-z0-9_]+:s0", label), f"Invalid SELinux label: {path}")
        rows[path] = {"nid": nid, "inodeOffset": offset, "modeOctal": oct(mode),
                      "uid": uid, "gid": gid, "links": links, "bytes": size,
                      "security.selinux": label.decode("ascii"), "xattrOffset": xoff,
                      "xattrStorage": "shared" if shared else "inline"}
        if fmt == 4:
            start = offset + 32 + xattr_size
            require(0 < size < 4096 and start // 4096 == (start + size - 1) // 4096,
                    f"Inline data extent: {path}")
            inline[path] = data[start:start + size]

    def directory(path, nid, parent):
        inode(path, nid, stat.S_IFDIR)
        raw = inline[path]
        first, = struct.unpack_from("<H", raw, 8)
        require(24 <= first < len(raw) and first % 12 == 0 and first // 12 <= 27,
                f"Directory records: {path}")
        entries = [struct.unpack_from("<QHBB", raw, i) for i in range(0, first, 12)]
        offsets = [entry[1] for entry in entries] + [len(raw)]
        require(all(a < b for a, b in zip(offsets, offsets[1:])), "Ordered directory names")
        by_name = {}
        for i, (child, start, kind, reserved) in enumerate(entries):
            name = raw[start:offsets[i + 1]].decode("ascii")
            require(re.fullmatch(r"[a-zA-Z0-9_.+-]+", name) and name not in by_name
                    and kind in (1, 2, 7) and reserved == 0, "Selected EROFS directory entry")
            by_name[name] = (child, kind)
        require(by_name["."] == (nid, 2) and by_name[".."] == (parent, 2), "Directory parent identity")
        return by_name

    top = directory("/", 39, 39)
    require(top["bin"][1] == top["lib64"][1] == 2 and top["apex_manifest.pb"][1] == 1,
            "Runtime APEX root role")
    inode("/apex_manifest.pb", top["apex_manifest.pb"][0], stat.S_IFREG)
    bin_nid, _ = top["bin"]
    bin_names = directory("/bin", bin_nid, 39)
    require(bin_names["linker64"][1] == 1, "Regular linker64 directory entry")
    inode("/bin/linker64", bin_names["linker64"][0], stat.S_IFREG)
    lib_nid, _ = top["lib64"]
    lib = directory("/lib64", lib_nid, 39)
    require(lib["bionic"][1] == 2 and lib["ld-android.so"][1] == 7, "Bionic ancestor or linker alias")
    inode("/lib64/ld-android.so", lib["ld-android.so"][0], stat.S_IFLNK)
    bionic = directory("/lib64/bionic", lib["bionic"][0], lib_nid)
    for name in ("libc.so", "libm.so", "libdl.so"):
        require(bionic[name][1] == 1, f"Regular bionic directory entry: {name}")
        inode("/lib64/bionic/" + name, bionic[name][0], stat.S_IFREG)
    link = rows["/bin/linker64"]
    require((link["uid"], link["gid"], link["modeOctal"], link["security.selinux"]) ==
            (0, 2000, "0o100755", "u:object_r:system_linker_exec:s0"), "Original linker executable profile")
    return rows, inline["/apex_manifest.pb"], inline["/lib64/ld-android.so"].decode("ascii")


def check():
    data = {name: pin(*item) for name, item in PINS.items()}
    ext4, elf = held_reader(data["reader"])
    prior = json.loads(data["priorRuntime"])
    aliases = json.loads(data["donorAliasPolicy"])
    app, image = image_records(ext4, prior, data["runtimeApex"])
    inodes, manifest, ld_link = runtime_inodes(data["runtimePayload"])
    with ZipFile(io.BytesIO(data["runtimeApex"])) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == 10 and
                archive.getinfo("apex_payload.img").file_size == len(data["runtimePayload"]) and
                archive.getinfo("apex_manifest.pb").file_size == len(manifest), "Exact APEX member extents")
        require(archive.read("apex_payload.img") == data["runtimePayload"]
                and archive.read("apex_manifest.pb") == manifest, "Runtime APEX inner and outer identity")
    require(manifest.startswith(b"\x0a\x13com.android.runtime\x10\x01")
            and digest(manifest) == "48e74bbf3dead7386e9a16ba8ff51cd9983c5d5ab6973bb7fb8c445a9653d0d9"
            and prior["runtimePayload"]["version"] == 1, "Held runtime name and version")
    require(data["legacyPrepare"].splitlines()[3934] == b'mount_payload "runtime" "com.android.runtime"'
            and any(line.split() == [digest(data["runtimePayload"]).encode(), b"runtime_payload.img"]
                    for line in data["legacySet"].splitlines()), "Legacy source payload designation")
    linker_expected = prior["runtimeSavedExtraction"]["bin/linker64"]
    linker = elf(pin(RUNTIME / "files/bin/linker64", linker_expected["bytes"], linker_expected["sha256"]))
    executable = elf(app)
    require(linker == linker_expected and linker["interpreter"] is None and linker["needed"] == []
            and linker["soname"] == "ld-android.so" and inodes["/bin/linker64"]["bytes"] == linker["bytes"]
            and executable["interpreter"] == "/system/bin/linker64", "App process and interpreter framing")
    art = ext4(io.BytesIO(data["artPayload"]), len(data["artPayload"]),
               "7d1522e19dfa5edba43e98e3a4d20250", 0x42, 96, 7660 * 4096)
    dependencies = {}
    for name in executable["needed"]:
        expected = prior["directLibraryCandidates"][name]
        path = expected["candidate"]
        if path.startswith(APEX + "/"):
            rel = path[len(APEX):]
            require(inodes[rel]["bytes"] == expected["bytes"], f"Runtime dependency raw inode: {name}")
            raw = pin(RUNTIME / "files" / rel[1:], expected["bytes"], expected["sha256"])
        elif path.startswith("/apex/com.android.art/lib64/"):
            raw, _ = art.lookup("lib64/" + name, 1, 262144)
        else:
            require(path == "/system/lib64/" + name, f"Unadmitted source partition: {name}")
            raw = pin(DONOR / "extracted" / path[1:], expected["bytes"], expected["sha256"])
        current = elf(raw)
        require(current["soname"] == name and {"candidate": path, **current} == expected,
                f"Exact direct ELF candidate: {name}")
        dependencies[name] = expected
    require(len(dependencies) == 14 and dependencies.keys() == prior["directLibraryCandidates"].keys(),
            "Exact direct dependency set")
    return {
        "schema": "oneos-guest-tree-runtime-apex/v1",
        "status": "BLOCKED_NO_ADMITTED_RUNTIME_APEX_WINNER_OR_PRIVATE_MOUNT_VIEW",
        "pins": {k: {"path": Path(os.path.relpath(p, ROOT)).as_posix(), "bytes": n, "sha256": h}
                 for k, (p, n, h) in PINS.items()},
        "originalDonorRecords": image,
        "sourceCandidate": {
            "module": NAME, "version": 1, "manifestSha256": digest(manifest),
            "preinstalledPath": "/system/apex/com.android.runtime.apex",
            "stablePathCandidate": APEX, "versionedPathCandidate": APEX + "@1",
            "donorAliasCode": aliases["donorAliasEvidence"], "selectedRawInodes": inodes,
            "appProcess64": executable, "linker64": linker, "runtimeLdAndroidSymlink": ld_link,
            "appProcessDirectLibraryCandidates": dependencies,
        },
        "missing": ["Private active runtime APEX winner and actual stable/versioned path binding",
                    "Executable and SELinux mount view containing the same retained payload",
                    "Effective private linker configuration and actual namespace resolution"],
        "runtimeAdmissionInput": None,
    }


def main():
    result = check()
    body = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    plain_directory(OUT.parent)
    OUT.mkdir(exist_ok=True)
    plain_directory(OUT)
    path = OUT / "receipt.json"
    try:
        with path.open("xb") as stream:
            stream.write(body)
    except FileExistsError:
        pass
    require(read_exact(path, len(body)) == body, "Receipt readback")
    print(result["status"], digest(body), path.relative_to(ROOT).as_posix())
    return 2


if __name__ == "__main__":
    sys.exit(main())
