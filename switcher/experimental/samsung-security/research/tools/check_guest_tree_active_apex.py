"""Check the held telephonycore payload and donor apexd alias paths as data."""

import hashlib
import json
import os
import re
import stat
import struct
from pathlib import Path


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
OUT = ROOT / "out/guest-tree-active-apex"
NAME = "com.android.telephonycore"
SOURCE = DONOR / "apex/006-com.android.telephonycore"
PINS = {
    "treeProof": (ROOT / "out/guest-tree-apex-inputs/actual-source-check.json", 45786,
                  "f090a965b2013c0dfa5b38b40edc722bbd8ee215de3676d255ed2b22a4da53bc"),
    "apexd": (DONOR / "extracted/system/bin/apexd", 1118304,
              "58b2bf72f66ab7cbe276da422211b2819016a86d7a18de2ac98c70559a1c0077"),
    "apexdRc": (DONOR / "extracted/system/etc/init/apexd.rc", 1229,
                "d9eb6188a043bf04504951741a87a8dae18972ac4ce3c691d26d4df5363eec72"),
    "fileContexts": (DONOR / "extracted/system/etc/selinux/plat_file_contexts", 51108,
                     "80d870c4346f0df1c4b99cce6b217f04f709f19006e7075539d10cc391da2c66"),
    "payload": (SOURCE / "apex_payload.img", 344064,
                "d01d488e87146b39fd3320861ddc90bdc5fd1f5c44a93ae2ab112d63e9588153"),
    "bootFragment": (SOURCE / "files/etc/classpaths/bootclasspath.pb", 73,
                     "5c66e6f44d8fd915ff106efa81ef9ee012eceb357d29a5ceb4b1f6c114db600d"),
    "bootJar": (SOURCE / "files/javalib/framework-telephony.jar", 540069,
                "559e2efd8626066990436f04943e46c813be933d25ef6a807199b858542d4b01"),
}
# Exact file-backed .text windows read from the donor ELF. Function boundaries
# come from its embedded .gnu_debugdata, and edges below are direct A64 calls.
ALIAS_WINDOWS = {
    "GetPackageId": (0xd3e64, 328, "ddfd3fdef0d2766756217a57faa45224e6871b76de99a416f170c4e908c4d2eb"),
    "ActivatePackageImpl": (0x66678, 3572, "bbd57f2db21abf1b3fbaa5c8247c9fe6419af3628d5ad39f8ade2360bc9409a6"),
    "MountPackageImpl": (0x63fc8, 6388, "2ecfff708907a6f6f28c08c0b057c4e5b7977c45192783edeca036ed94626364"),
    "StableBindCallback": (0x9bfe4, 140, "1f6bbaade6874ee6d9a59970bd98cde17058b12e6d5fd5a67dd12828da6d0a67"),
    "BindMount": (0xbceb4, 3928, "f105d1c842159062fbdd2ffed0388cdee240b1fff92673ffa19266fd617014eb"),
    "DecimalVersionPlt": (0xfe2b8, 24, "e2ed48e3e7e1fafb926f6bf8959473c3481bca6bf03f1e5a3187df0a3363eb5f"),
    "MountPlt": (0xfdec8, 24, "ecc9d1714593052237f55aa4f96163932cf1bceac3f04e5bda6b3a5720e617b8"),
}
ALIAS_CALLS = {
    0xd3f30: 0xfe2b8, 0x669b4: 0xd3e64, 0x669dc: 0xfd808, 0x66a38: 0x63fc8,
    0x9c030: 0xfd808, 0x9c040: 0xbceb4, 0xbd5f0: 0xfdec8,
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def plain_directory(path):
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        require(stat.S_ISDIR(info.st_mode) and not linked(info), f"Unsafe directory: {part.name}")


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def read_exact(path, size):
    plain_directory(path.parent)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and not linked(before) and before.st_size == size,
            f"Unexpected input type or size: {path.name}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and identity(opened) == identity(before),
                f"Opened identity: {path.name}")
        data = stream.read(size + 1)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    require(len(data) == size and not linked(after) and identity(before) == identity(after)
            and before.st_ctime_ns == after.st_ctime_ns and identity(opened) == identity(finished)
            and opened.st_ctime_ns == finished.st_ctime_ns, f"Input changed: {path.name}")
    return data


def inputs():
    data = {}
    records = {}
    for key, (path, size, sha256) in PINS.items():
        data[key] = read_exact(path, size)
        require(digest(data[key]) == sha256, f"Input digest: {key}")
        records[key] = {"path": Path(os.path.relpath(path, ROOT)).as_posix(), "bytes": size,
                        "sha256": sha256}
    return data, records


def alias_evidence(data):
    require(data[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", data, 18) == (183,),
            "Expected donor AArch64 ELF")
    require(data[0x12a4f:0x12a55] == b"/apex\0" and data[0x13db9:0x13dbf] == b"%s/%s\0",
            "Donor path operands")
    windows = {}
    for name, (offset, size, sha256) in ALIAS_WINDOWS.items():
        require(digest(data[offset:offset + size]) == sha256, f"Donor code window: {name}")
        windows[name] = {"offset": offset, "bytes": size, "sha256": sha256}
    for pc, target in ALIAS_CALLS.items():
        opcode, = struct.unpack_from("<I", data, pc)
        immediate = opcode & 0x3ffffff
        if immediate & 0x2000000:
            immediate -= 0x4000000
        require(opcode >> 26 == 0b100101 and pc + 4 * immediate == target,
                f"Donor direct call at {pc:#x}")
    return {"codeWindows": windows, "directCalls": {hex(pc): hex(target) for pc, target in ALIAS_CALLS.items()},
            "packageId": "manifest.name + @ + decimal manifest.version",
            "versionedPath": "ActivatePackageImpl passes /apex/<package-id> to MountPackageImpl",
            "stablePath": "Activation callback passes /apex/<manifest.name> as BindMount destination",
            "selectionOrMountObserved": False}


def read_tree(image):
    # This held compact-inode EROFS image has 4 KiB blocks, no packed inodes,
    # no side devices, and exactly one shared xattr per inode. Restrict directory
    # and inline data parsing to that profile. File size is the uncompressed size.
    require(image[1024:1028] == bytes.fromhex("e2e1f5e0") and image[1036:1038] == b"\x0c\0",
            "Expected 4 KiB EROFS")
    root_nid, = struct.unpack_from("<H", image, 1038)
    count, = struct.unpack_from("<Q", image, 1040)
    blocks, meta, shared = struct.unpack_from("<III", image, 1060)
    require((root_nid, count, blocks, meta, shared) == (38, 12, 81, 0, 0),
            "Unexpected EROFS superblock profile")
    rows = {}
    seen = set()
    inline_files = {}

    def visit(nid, parent, name, depth, expected_type):
        offset = nid * 32
        require(depth <= 3 and len(rows) < count and nid not in seen and 1024 < offset <= 12288 - 48,
                "Unsupported inode reachability or extent")
        seen.add(nid)
        fmt, xcount, mode, nlink, size = struct.unpack_from("<HHHHI", image, offset)
        uid, gid = struct.unpack_from("<HH", image, offset + 24)
        require(xcount == 2 and (fmt, mode & 0o170000) in ((4, stat.S_IFDIR),
                (4, stat.S_IFREG), (6, stat.S_IFREG)), "Unexpected inode or xattr layout")
        kind = "directory" if stat.S_ISDIR(mode) else "regular"
        require(kind == expected_type, "Directory entry type disagrees with inode")
        xattr = image[offset + 32:offset + 48]
        require(xattr[4:12] == b"\x01" + b"\0" * 7, "Expected one shared xattr, no inline xattr")
        index, = struct.unpack_from("<I", xattr, 12)
        xoff = shared * 4096 + 4 * index
        require(0 < xoff <= len(image) - 64, "Shared xattr extent")
        name_len, namespace, value_len = struct.unpack_from("<BBH", image, xoff)
        require((name_len, namespace) == (7, 6) and 0 < value_len <= 48
                and image[xoff + 4:xoff + 11] == b"selinux", "Missing security.selinux")
        label = image[xoff + 11:xoff + 11 + value_len]
        require(re.fullmatch(rb"u:object_r:[a-z0-9_]+:s0", label), "Unsupported source label")
        rows[name] = {"nid": nid, "type": kind, "modeOctal": oct(mode), "uid": uid, "gid": gid,
                      "links": nlink, "bytes": size, "security.selinux": label.decode("ascii"),
                      "sharedXattrOffset": xoff}
        if fmt == 4:
            start = offset + 48
            require(0 < size < 4096 and start // 4096 == (start + size - 1) // 4096,
                    "Unexpected inline data extent")
            inline = image[start:start + size]
            if kind == "regular":
                inline_files[name] = inline
                return
        if kind != "directory":
            return
        first, = struct.unpack_from("<H", inline, 8)
        require(24 <= first < size and first % 12 == 0 and first // 12 <= count,
                "EROFS dirent table extent")
        entries = [struct.unpack_from("<QHBB", inline, i) for i in range(0, first, 12)]
        starts = [entry[1] for entry in entries] + [size]
        require(starts[0] == first and all(a < b for a, b in zip(starts, starts[1:])), "Dirent names")
        local_names = set()
        for i, (child, begin, dtype, reserved) in enumerate(entries):
            child_name = inline[begin:starts[i + 1]].decode("ascii")
            require(dtype in (1, 2) and reserved == 0 and child_name not in local_names
                    and re.fullmatch(r"[a-zA-Z0-9_.-]+", child_name), "Unsupported dirent")
            local_names.add(child_name)
            if child_name in (".", ".."):
                require(dtype == 2 and child == (nid if child_name == "." else parent),
                        "Directory self or parent link")
            else:
                visit(child, nid, f"{name}/{child_name}".lstrip("/"), depth + 1,
                      "regular" if dtype == 1 else "directory")
        require({".", ".."} <= local_names, "Missing directory links")

    visit(root_nid, root_nid, "", 0, "directory")
    require(len(rows) == count, "Incomplete raw inode closure")
    return rows, inline_files


def candidate(data):
    proof = json.loads(data["treeProof"])["candidates"][NAME]
    rows, inline = read_tree(data["payload"])
    tree = proof["tree"]
    require(rows.keys() == {"", *tree["directories"], *tree["regularFiles"]}
            and not tree["guestLinks"] and not proof["activeAliasAdmitted"], "Source tree closure")
    for name, expected in tree["regularFiles"].items():
        require(rows[name]["type"] == "regular" and rows[name]["bytes"] == expected["bytes"],
                f"Source file row: {name}")
        if name in inline:
            require(digest(inline[name]) == expected["sha256"], f"Inline source hash: {name}")
    manifest = inline["apex_manifest.pb"]
    prefix = bytes((0x0a, len(NAME))) + NAME.encode("ascii") + b"\x10"
    encoded = manifest[len(prefix):]
    require(manifest.startswith(prefix) and 1 <= len(encoded) <= 9 and encoded[-1] in range(1, 128)
            and all(byte >= 128 for byte in encoded[:-1]), "Manifest name and version-only profile")
    version = sum((byte & 0x7f) << (7 * i) for i, byte in enumerate(encoded))
    require(version == proof["versionCode"], "Manifest version disagrees with prior source")
    require(proof["source"]["payload"]["sha256"] == digest(data["payload"]), "Prior payload identity")
    fragment, = proof["classpathFragments"]
    role = fragment["entry"]
    require((role["classpathRaw"], role["minSdkRaw"], role["maxSdkRaw"], role["path"]) ==
            (1, "36", "", f"/apex/{NAME}/javalib/framework-telephony.jar")
            and fragment["fragment"]["sha256"] == digest(data["bootFragment"])
            and fragment["jar"]["sha256"] == digest(data["bootJar"])
            and inline["etc/classpaths/bootclasspath.pb"] == data["bootFragment"],
            "Required bootclasspath role evidence")
    require(b"service apexd /system/bin/apexd\n" in data["apexdRc"], "Donor apexd init declaration")
    require([b"/apex", b"u:object_r:apex_mnt_dir:s0"] in
            [line.split() for line in data["fileContexts"].splitlines()], "Donor mount-root context")
    return {"package": NAME, "versionCode": version, "source": proof["source"],
            "candidateStablePath": f"/apex/{NAME}", "candidateVersionedPath": f"/apex/{NAME}@{version}",
            "bootClasspathDeclaration": role, "payloadInodes": rows,
            "payloadRootLabel": rows[""]["security.selinux"],
            "donorParentApexDirectoryPolicyLabel": "u:object_r:apex_mnt_dir:s0",
            "destinationLabelOrMountPermissionAdmitted": False}


def main():
    data, pins = inputs()
    result = {"schema": "oneos-donor-apex-alias-candidate/v1", "status": "ONE_SOURCE_CANDIDATE_ONLY",
              "pins": pins, "donorAliasEvidence": alias_evidence(data["apexd"]),
              "candidate": candidate(data), "activeAliases": None, "linkerconfigInput": None,
              "remaining": ["active-version winner and competing updates", "private mount ownership and labels",
                            "effective guest SDK and complete APEX cohort"]}
    body = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    plain_directory(OUT.parent)
    OUT.mkdir(exist_ok=True)
    plain_directory(OUT)
    output = OUT / "candidate.json"
    try:
        with output.open("xb") as stream:
            stream.write(body)
    except FileExistsError:
        require(read_exact(output, len(body)) == body, "Existing candidate differs")
    require(read_exact(output, len(body)) == body, "Candidate readback differs")
    print(f"{result['status']} {digest(body)} {output.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
