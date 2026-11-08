"""Build and verify the fixed Runtime, ART, I18N source deployment cohort."""

import io
import json
import os
from pathlib import Path
import re
import stat
import struct

from check_guest_tree_active_apex import DONOR, ROOT, digest, plain_directory, read_exact, require
from check_guest_tree_linker_inputs import manifest_reader
from check_guest_tree_runtime_apex import held_reader, pin
from stage_guest_apex_active_inputs import MODULES, members


OUT = ROOT / "out/guest-tree-core-apex-cohort"
SELECTED = ("art", "i18n", "runtime")
PINS = {
    "linkerPrerequisites": (ROOT / "out/guest-tree-linker-inputs/receipt.json", 16625,
                            "6a41ddb659835dc5580520de71bf24be4f812112a3a31cf911674ec1a01cb039"),
    "runtimeSources": (ROOT / "out/guest-tree-runtime-apex/receipt.json", 23165,
                       "33cc6e4a2e263b54cd27174388924cdf6803d35c72cf398fc5883819123b25d4"),
    "donorSourceSet": (ROOT / "out/guest-apex-active-inputs/r-27f937479ad7483a893a399d6f8b94eb/receipt.json", 7782,
                       "8bdfef9391822e16b566943c11e2210f81cf4adbbc53faa8b37b6fd7060340b5"),
    "elfReader": (ROOT / "tools/audit_guest_runtime_apex.py", 15155,
                  "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de"),
    "manifestReader": (ROOT / "tools/audit_guest_linkerconfig_apex_inputs.py", 12371,
                       "c5b9f4dcb550d329f4a4b413b6d524c9eec7e7fc4eb48e0321a7f1ea5e081772"),
    "containerReader": (ROOT / "tools/stage_guest_apex_active_inputs.py", 12334,
                        "1b9b7c5a8626f6247bf25616cb98ed36ec1d81462b92946a789a0f32321e828a"),
    "donorGenerator": (DONOR / "apex/005-com.android.runtime/files/bin/linkerconfig", 496480,
                       "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb"),
}
FILES = ("apex_manifest.pb", "etc/linker.config.pb")


def file_record(path, raw):
    return {"path": Path(os.path.relpath(path, ROOT)).as_posix(), "bytes": len(raw), "sha256": digest(raw)}


def erofs_metadata(image, short):
    # Only the two held compact-inode EROFS profiles, selected inline data and
    # one security label per selected inode. Compressed file data stays pinned
    # by the whole payload; this reader does not decompress it.
    sizes = {"runtime": (27, 1280), "i18n": (20, 5183)}
    count, blocks = sizes[short]
    require(image[1024:1028] == b"\xe2\xe1\xf5\xe0" and image[1036:1040] == b"\x0c\x00\x27\x00"
            and struct.unpack_from("<Q", image, 1040) == (count,)
            and struct.unpack_from("<III", image, 1060) == (blocks, 0, 0), "Fixed compact EROFS profile")
    selected = {}
    contents = {}

    def inode(path, nid, typ):
        offset = nid * 32
        require(1024 < offset < blocks * 4096 - 128, "Selected EROFS inode extent")
        form, xcount, mode, _, size = struct.unpack_from("<HHHHI", image, offset)
        uid, gid = struct.unpack_from("<HH", image, offset + 24)
        require(form in (4, 6) and xcount in (2, 12) and mode & 0o170000 == typ,
                f"Selected EROFS inode: {path}")
        xstart = offset + 32
        extent = 12 + 4 * (xcount - 1)
        shared = image[xstart + 4]
        require((shared, xcount) in ((1, 2), (0, 12)) and image[xstart + 5:xstart + 12] == b"\0" * 7,
                "Single security xattr profile")
        pos = 4 * struct.unpack_from("<I", image, xstart + 12)[0] if shared else xstart + 12
        require(0 < pos < len(image) - 60, "EROFS security xattr extent")
        name_len, index, length = struct.unpack_from("<BBH", image, pos)
        end = pos + 11 + length
        require((name_len, index) == (7, 6) and image[pos + 4:pos + 11] == b"selinux"
                and 0 < length <= 40 and (shared or end <= xstart + extent), "EROFS security xattr")
        label = image[pos + 11:end].decode("ascii")
        require(re.fullmatch(r"u:object_r:[a-z0-9_]+:s0", label), "Exact EROFS label")
        selected[path] = {"inode": nid, "mode": oct(mode), "uid": uid, "gid": gid, "bytes": size,
                          "security.selinux": label, "labelOffset": pos + 11}
        if form == 4:
            start = xstart + extent
            require(0 < size < 4096 and start // 4096 == (start + size - 1) // 4096, "Inline EROFS extent")
            contents[path] = image[start:start + size]

    def directory(path, nid, parent):
        inode(path, nid, stat.S_IFDIR)
        raw = contents[path]
        first, = struct.unpack_from("<H", raw, 8)
        require(24 <= first < len(raw) and first % 12 == 0 and first // 12 <= count, "EROFS directory table")
        entries = [struct.unpack_from("<QHBB", raw, i) for i in range(0, first, 12)]
        ends = [entry[1] for entry in entries[1:]] + [len(raw)]
        names = {}
        for (child, start, kind, reserved), end in zip(entries, ends):
            require(first <= start < end <= len(raw) and reserved == 0 and kind in (1, 2, 7), "EROFS dirent")
            name = raw[start:end].decode("ascii")
            require(re.fullmatch(r"[a-zA-Z0-9_.+-]+", name) and name not in names, "EROFS name")
            names[name] = (child, kind)
        require(names["."] == (nid, 2) and names[".."] == (parent, 2), "EROFS directory parent")
        return names

    root = directory("/", 39, 39)
    require(root["apex_manifest.pb"][1] == 1 and root["etc"][1] == root["lib64"][1] == 2, "APEX scanner inputs")
    inode(FILES[0], root["apex_manifest.pb"][0], stat.S_IFREG)
    directory("lib64", root["lib64"][0], 39)
    etc = directory("etc", root["etc"][0], 39)
    if short == "runtime":
        require(root["bin"][1] == 2 and etc["linker.config.pb"][1] == 1, "Runtime namespace directories")
        binaries = directory("bin", root["bin"][0], 39)
        for name in ("linker64", "linkerconfig"):
            require(binaries[name][1] == 1, f"Runtime executable entry: {name}")
            inode("bin/" + name, binaries[name][0], stat.S_IFREG)
        inode(FILES[1], etc["linker.config.pb"][0], stat.S_IFREG)
    else:
        require("bin" not in root and "lib" not in root and "linker.config.pb" not in etc,
                "I18N exact namespace layout")
    return selected, contents[FILES[0]], contents.get(FILES[1])


def art_metadata(image, reader):
    fs = reader(io.BytesIO(image), len(image), "7d1522e19dfa5edba43e98e3a4d20250", 0x42, 96, 7660 * 4096)
    root, row = fs.directory(2)
    selected = {"/": row}
    for directory in ("bin", "etc", "lib64"):
        nid, typ = root[directory]
        require(typ == 2, f"ART directory type: {directory}")
        _, selected[directory] = fs.directory(nid)
    pb, selected[FILES[0]] = fs.lookup(FILES[0], 1, 4096)
    cfg, selected[FILES[1]] = fs.lookup(FILES[1], 1, 4096)
    for row in selected.values():
        nid = row["inode"]
        group, index = divmod(nid - 1, 96)
        table, = struct.unpack("<I", fs.read(4096 + group * 32 + 8, 4))
        offset = table * 4096 + index * 256
        inode = fs.read(offset, 256)
        require(inode[104:108] == b"\0" * 4 and inode[128:130] == b"\x20\0"
                and inode[160:164] == b"\0\0\x02\xea", "ART inline xattr header")
        name_size, name_index, value_offset, external, length = struct.unpack_from("<BBHII", inode, 164)
        start = 164 + value_offset
        require((name_size, name_index, external) == (7, 6, 0) and inode[180:187] == b"selinux"
                and inode[188:192] == b"\0" * 4 and 192 <= start < start + length <= 256,
                "ART inline security.selinux")
        raw_label = inode[start:start + length]
        require(re.fullmatch(rb"u:object_r:[a-z0-9_]+:s0\x00", raw_label), "ART inode SELinux label")
        row.update({"security.selinux": raw_label[:-1].decode("ascii"), "labelOffset": offset + start})
    return selected, pb, cfg


def source_module(short, reader, fields):
    p = MODULES[short]
    name = "com.android." + short
    held = DONOR / "apex" / p["held"]
    filename, size, sha = p["container"]
    path = DONOR / "extracted/system/apex" / filename
    container = pin(path, size, sha)
    sources = {"preinstalledContainer": file_record(path, container)}
    if "original" in p:
        wrapped = members(container, {"original_apex": p["original"][0],
                                      "apex_manifest.pb": p["outerManifestBytes"]})
        inner = pin(held / "original.apex", *p["original"])
        require(inner == wrapped["original_apex"], "Exact ART CAPEX inner APEX")
        outer_fields = fields(wrapped["apex_manifest.pb"])
        require(outer_fields.get(1) == [name.encode()] and outer_fields.get(2) == [p["version"]],
                "ART outer manifest identity")
        sources["originalApex"] = file_record(held / "original.apex", inner)
    else:
        inner = container
    zip_data = members(inner, {"apex_payload.img": p["payload"][0], FILES[0]: p["manifest"][0]})
    image = pin(held / "apex_payload.img", *p["payload"])
    require(image == zip_data["apex_payload.img"], f"Exact original payload: {name}")
    sources["payload"] = file_record(held / "apex_payload.img", image)
    rows, pb, config = art_metadata(image, reader) if short == "art" else erofs_metadata(image, short)
    require(pb == zip_data[FILES[0]] and (len(pb), digest(pb)) == p["manifest"], f"Raw inner manifest: {name}")
    manifest = fields(pb)
    require(manifest.get(1) == [name.encode()] and manifest.get(2) == [p["version"]]
            and manifest.get(11, [0]) == [0], f"Ordinary named APEX role: {name}")
    if short == "runtime":
        require(config == b"\x10\x01", "Exact visible Runtime namespace")
    elif short == "art":
        require(fields(config) == {1: [b"/data", b"/apex/com.android.art/javalib"]}, "Exact ART permitted paths")
    else:
        require(config is None, "No selected I18N inner linker config")
    return {"name": name, "version": p["version"], "sources": sources, "manifestSha256": digest(pb),
            "innerLinkerConfigSha256": None if config is None else digest(config),
            "stableTarget": "/apex/" + name, "versionedTarget": f"/apex/{name}@{p['version']}",
            "hasBin": "bin" in rows, "hasLib64": "lib64" in rows, "sourceInodes": rows}


def scan_names(entries):
    """Independent data projection of the observed donor name/type filter."""
    accepted = []
    names = set()
    for entry in entries:
        name, kind = entry["name"], entry["dType"]
        require(re.fullmatch(r"[a-zA-Z0-9_.@+-]+", name) and name not in names, "Unique directory-entry name")
        names.add(name)
        if name.startswith(".") or kind != 4 or "@" in name or name == "sharedlibs":
            continue
        accepted.append(name)
    return sorted(accepted)


def validate_candidate(raw, expected_rows):
    require(0 < len(raw) < 65536, "Bounded source cohort manifest")
    value = json.loads(raw)
    require(value["schema"] == "oneos-guest-apex-core-source-cohort/v1" and value["runtimeAdmission"] is None
            and value["activationXml"] is None, "Source-only cohort schema")
    require(value["sourceCohort"] == expected_rows and len(expected_rows) == 3, "Exact source-cohort readback")
    entries = value["projectedDirents"]
    require(scan_names(entries) == sorted(row["name"] for row in expected_rows), "Donor stable directory projection")
    require(entries == [{"name": row[key].rsplit("/", 1)[1], "dType": 4}
                        for row in expected_rows for key in ("stableTarget", "versionedTarget")],
            "Exact proposed stable and versioned directory pair")
    return value


def build():
    data = {k: pin(*item) for k, item in PINS.items()}
    prior = json.loads(data["linkerPrerequisites"])
    runtime = json.loads(data["runtimeSources"])["sourceCandidate"]
    source_set = json.loads(data["donorSourceSet"])
    reader, _ = held_reader(data["elfReader"])
    _, fields = manifest_reader(data["manifestReader"])
    rows = [source_module(short, reader, fields) for short in SELECTED]
    for row in rows:
        name = row["name"]
        source_row, = [item for item in source_set["candidates"] if item["moduleName"] == name]
        require(row["version"] == int(source_row["versionCode"]) and row["stableTarget"] == source_row["proposedMountTarget"]
                and row["manifestSha256"] == source_row["manifestSha256"]
                and row["sources"]["payload"]["sha256"] == source_row["payloadSha256"], "Previous source selection join")
    require(rows[2]["sourceInodes"]["bin/linker64"]["security.selinux"] ==
            runtime["selectedRawInodes"]["/bin/linker64"]["security.selinux"]
            and rows[2]["sourceInodes"]["bin/linkerconfig"]["security.selinux"] ==
            "u:object_r:linkerconfig_exec:s0", "Runtime interpreter and generator labels")
    generator = data["donorGenerator"]
    require(digest(generator[0x3afe0:0x3b028]) ==
            "d26d5693351311465ce43a1f4614a62fb6834a1b3661d9539b450632f8a84f17"
            and generator[0x46cf:0x46da] == b"sharedlibs\0", "Exact donor GetActivePackages directory filter")
    projected = [{"name": row[key].rsplit("/", 1)[1], "dType": 4}
                 for row in rows for key in ("stableTarget", "versionedTarget")]
    result = {"schema": "oneos-guest-apex-core-source-cohort/v1",
              "status": "THREE_SOURCE_PAYLOADS_BOUND_PRIVATE_ACTIVATION_UNSELECTED",
              "pins": {key: file_record(PINS[key][0], raw) for key, raw in data.items()},
              "sourceCohort": rows, "projectedDirents": projected, "donorScanEligibleNames": scan_names(projected),
              "donorGetActivePackagesFilter": {"offset": 0x3afe0, "bytes": 0x48,
                                              "requiredDType": 4, "ignored": ["dot-leading names", "@ names", "sharedlibs"]},
              "unselectedNamedEdges": prior["unselectedNamedApexEdges"],
              "activationXml": None, "runtimeAdmission": None,
              "missing": ["Private version winner and actual same-payload directory mounts",
                          "Complete active module set and effective partition/property view",
                          "Activation XML matching those mounts and generated linker files"]}
    return result, rows


def main():
    result, rows = build()
    data = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    validate_candidate(data, rows)
    plain_directory(OUT.parent)
    OUT.mkdir(exist_ok=True)
    plain_directory(OUT)
    output = OUT / "source-cohort.json"
    try:
        with output.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        pass
    actual = read_exact(output, len(data))
    validate_candidate(actual, rows)
    require(actual == data, "Exact source-cohort bytes")
    print(result["status"], digest(actual), output.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
