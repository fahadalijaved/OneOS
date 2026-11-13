"""Read the selected donor linkerconfig inputs and distinct saved host candidates."""

import ast
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tarfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
EXTRACTED = DONOR / "extracted"
RUNTIME = DONOR / "apex/005-com.android.runtime/files"
ART = DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img"
HOST = ROOT.parent / "firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar"
HOST_BYTES = 20434769920
HOST_MEMBERS = {
    "apex/apex-info-list.xml": (18886180864, 29380, "bb62c065939d0ec16993a3168dc595ce4b48c55e6ea4d78b391d77c2c86ed0fe"),
    "vendor/etc/linker.config.pb": (13516409856, 829, "25c95bb1e082402033b54a9123d4d94c05550a74e55c5633a18de76160135d88"),
    "vendor/etc/public.libraries.txt": (14708899840, 1188, "267fe4f8f3889f1c11bc84bc2e7b857ae297bdec3337a6f223df2a34d9da74ca"),
}
DONOR_FILES = {
    "system/etc/linker.config.pb": (1207, "f9782b93cc1e7bd9989fd145380850ff2df5196cb1a314b6a8a41fe78eec076c"),
    "system/product/etc/linker.config.pb": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "system/etc/public.libraries.txt": (549, "63522af72a927a5edb7df539f0f3643f44a91fa11b64cac977796b8ee50bd96f"),
    "system/etc/llndk.libraries.txt": (489, "c64bfb9681cff05af1137cde6164b489dbe5c4ba8bd9d561c7dfb1dd4a4370ff"),
    "system/etc/sanitizer.libraries.txt": (122, "508c402cca42e92f23bf9e2adfbfd9124347fd55aa521aa2d5cd62c12cd723b4"),
    "system/build.prop": (28816, "4661edb3c8e09ac75af0bd19a0c48fecba86511f3d6bec383c0db4bd31709582"),
    "system/product/etc/build.prop": (4668, "768eca01390a557b871c75b9c4abfc728c4916a8101a0628421d57f2de02b94b"),
}
REPORTED_PROPERTIES = {"ro.vndk.version", "ro.product.vndk.version", "ro.vndk.lite", "ro.treble.enabled"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def record(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def relative(path):
    return Path(os.path.relpath(path, ROOT)).as_posix()


def plain_source(path):
    for parent in reversed(path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Input ancestor is not a plain directory")
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
            "Input is not a plain regular file")
    return info


def pinned(path, size, expected):
    require(plain_source(path).st_size == size, f"Length differs: {relative(path)}")
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    proof = record(data)
    require(proof == {"bytes": size, "sha256": expected}, f"Pin differs: {relative(path)}")
    return data, {"path": relative(path), **proof}


def ext4_reader():
    path = ROOT / "tools/audit_guest_runtime_apex.py"
    source, proof = pinned(path, 15155, "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de")
    names = {"need", "digest", "u16", "u32", "SelectedExt4"}
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
    require(len(nodes) == len(names) and {node.name for node in nodes} == names, "Ext4 reader definition set")
    namespace = {"sha256": hashlib.sha256, "stat": stat, "struct": struct}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["SelectedExt4"], proof


def varint(data, offset):
    value = 0
    for shift in range(0, 64, 7):
        require(offset < len(data), "Truncated protobuf integer")
        part = data[offset]
        offset += 1
        require(shift < 63 or part <= 1, "Protobuf integer overflow")
        value |= (part & 127) << shift
        if part < 128:
            require(shift == 0 or part != 0, "Noncanonical protobuf integer")
            return value, offset
    raise ValueError("Unterminated protobuf integer")


def fields(data):
    """Decode only the selected length-delimited and integer top-level fields."""
    output = {}
    offset = 0
    while offset < len(data):
        tag, offset = varint(data, offset)
        field, wire = tag >> 3, tag & 7
        require(0 < field < 1 << 29 and wire in (0, 2), "Unreviewed protobuf field")
        value, offset = varint(data, offset)
        if wire == 2:
            end = offset + value
            require(end <= len(data), "Truncated protobuf payload")
            value, offset = data[offset:end], end
        output.setdefault(field, []).append(value)
    return output


def manifest(data, expected_name, expected_version):
    values = fields(data)
    require(values.get(1) == [expected_name.encode()] and values.get(2) == [expected_version], "APEX identity")
    return {"module": expected_name, "version": expected_version,
            **{name: [value.decode("ascii") for value in values.get(number, [])]
               for number, name in ((7, "provideNativeLibs"), (8, "requireNativeLibs"), (9, "jniLibs"))}}


def read_host_candidates():
    require(plain_source(HOST).st_size == HOST_BYTES, "Mounted capture length")
    selected = {}
    with HOST.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(before.st_size == HOST_BYTES, "Mounted capture FD length")
        for path, (offset, size, expected) in HOST_MEMBERS.items():
            stream.seek(offset)
            header = tarfile.TarInfo.frombuf(stream.read(512), "utf-8", "strict")
            require(header.name == path and header.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    and header.size == size, "Selected mounted capture header")
            data = stream.read(size)
            require(record(data) == {"bytes": size, "sha256": expected}, "Selected mounted capture bytes")
            selected[path] = (data, {"headerOffset": offset, "dataOffset": offset + 512, **record(data)})
        after = os.fstat(stream.fileno())
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "Mounted capture FD changed")
    xml = selected["apex/apex-info-list.xml"][0]
    require(b"<!" not in xml, "Unexpected markup declaration")
    root = ET.fromstring(xml)
    require(root.tag == "apex-info-list", "Mounted APEX XML root")
    modules = {}
    for name in ("com.android.art", "com.android.runtime"):
        matches = [element for element in root if element.tag == "apex-info"
                   and element.get("moduleName") == name and element.get("isActive") == "true"]
        require(len(matches) == 1, "Mounted APEX identity")
        modules[name] = {key: matches[0].attrib[key] for key in ("modulePath", "preinstalledModulePath",
                                                              "versionCode", "isFactory", "partition")}
    return {"archive": relative(HOST), "archiveBytes": HOST_BYTES,
            "members": {path: proof for path, (_, proof) in selected.items()}, "activeRows": modules,
            "archiveFullRehashPerformed": False}


def audit():
    check, proof = pinned(ROOT / "out/guest-linkerconfig-inputs/r-b331f853278348b2878cc1f84f7562ed/receipt.json",
                          4662, "52287d65f2b34c18c93f15d2e5ef554938ec78d131e0770232b6b9c0456f5833")
    earlier = json.loads(check)
    require(earlier["outputManifest"] is None and earlier["launchAdmitted"] is False, "Expected closed predecessor")
    generator, generator_pin = pinned(RUNTIME / "bin/linkerconfig", 496480,
                                      "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb")
    paths = {0x4127: "/vendor/etc/linker.config.pb", 0x4a17: "/system/etc/public.libraries.txt",
             0x4f97: "/system/etc/llndk.libraries.txt", 0x525b: "/system_ext/etc/linker.config.pb",
             0x54ab: "/product/etc/linker.config.pb", 0x5826: "/apex_manifest.pb", 0x5e05: "/apex-info-list.xml",
             0x6417: "/system/etc/sanitizer.libraries.txt", 0x658e: "/system/etc/linker.config.pb",
             0x6a0b: "/etc/linker.config.pb", 0x6b71: "/vendor/etc/public.libraries.txt"}
    for offset, path in paths.items():
        text = path.encode() + b"\0"
        require(generator[offset:offset + len(text)] == text, f"Generator literal differs: {path}")

    runtime_pb, runtime_manifest_pin = pinned(RUNTIME / "apex_manifest.pb", 143,
                                              "48e74bbf3dead7386e9a16ba8ff51cd9983c5d5ab6973bb7fb8c445a9653d0d9")
    runtime_config, runtime_config_pin = pinned(RUNTIME / "etc/linker.config.pb", 2,
                                                "27c24fcb8474773e2af799d0848495ff053272d33c432dc26277993df45c9276")
    require(fields(runtime_config) == {2: [1]}, "Runtime namespace config")
    art_raw, art_pin = pinned(ART, 31633408, "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148")
    reader, reader_pin = ext4_reader()
    art = reader(io.BytesIO(art_raw), len(art_raw), "7d1522e19dfa5edba43e98e3a4d20250", 0x42, 96, 7660 * 4096)
    art_pb, art_manifest_pin = art.lookup("apex_manifest.pb", 1, 16384)
    art_config, art_config_pin = art.lookup("etc/linker.config.pb", 1, 16384)
    native_loader, loader_pin = art.lookup("lib64/libnativeloader.so", 1, 262144)
    allowed = [b"/data", b"/apex/com.android.art/javalib"]
    require(fields(art_config) == {1: allowed}, "ART permitted path fields")
    output_path = b"/linkerconfig/apex.libraries.config.txt\0"
    require(native_loader[18402:18402 + len(output_path)] == output_path, "ART native loader path literal")

    donor_inputs = {}
    properties = {}
    for name, (size, expected) in DONOR_FILES.items():
        data, donor_inputs[name] = pinned(EXTRACTED / name, size, expected)
        if name.endswith(".prop"):
            values = [line.partition("=") for line in data.decode().splitlines() if "=" in line]
            properties[name] = [[key, value] for key, _, value in values if key in REPORTED_PROPERTIES]
    absent = [name for name in ("apex/apex-info-list.xml", "linkerconfig/ld.config.txt",
                               "linkerconfig/apex.libraries.config.txt", "system/system_ext/etc/linker.config.pb",
                               "vendor/etc/linker.config.pb", "vendor/etc/public.libraries.txt")
              if not os.path.lexists(EXTRACTED / name)]
    host = read_host_candidates()
    return {
        "schema": "guest-linkerconfig-apex-inputs/v1",
        "status": "HELD_INPUT_CANDIDATES_PINNED_PRIVATE_VIEW_UNSELECTED",
        "priorRefusal": proof, "ext4ReaderSource": reader_pin, "generator": generator_pin,
        "generatorPathLiterals": {hex(offset): path for offset, path in paths.items()},
        "donorPartitionInputs": donor_inputs, "savedPropertyLinesNotEffectiveProperties": properties,
        "notFoundInRawDonorExtraction": absent,
        "donorRuntime": {"manifest": runtime_manifest_pin, "fields": manifest(runtime_pb, "com.android.runtime", 1),
                         "config": runtime_config_pin, "visible": True, "activeAliasSelected": False},
        "donorArt": {"payload": art_pin, "manifest": art_manifest_pin,
                     "fields": manifest(art_pb, "com.android.art", 371000140), "config": art_config_pin,
                     "permittedPaths": [item.decode() for item in allowed], "nativeLoader": loader_pin,
                     "generatedLibraryListLiteralOffset": 18402, "activeAliasSelected": False},
        "savedSamsungOnly": host,
        "generationOrder": [
            "Select and retain the actual app_process64 interpreter, partition aliases and active APEX payloads",
            "Bind the matching active APEX info list, inner manifests, optional configs/lists and effective property inputs",
            "Obtain generated base and companion output bytes from a matching capture or separately reviewed producer",
            "Verify the selected entry/library paths in that same owned view before staging immutable output",
        ],
        "outputManifest": None, "launchAdmitted": False, "generatorExecuted": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
