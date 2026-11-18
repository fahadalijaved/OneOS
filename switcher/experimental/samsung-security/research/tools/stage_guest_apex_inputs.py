"""Write or verify the exact two-payload guest APEX reference manifest."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import stat
import struct
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DONOR = "../firmware/donor/"
RECEIPT = ROOT / "out/guest-apex-staging/receipt.json"
RUNTIME = DONOR + "apex/005-com.android.runtime/"
ART = DONOR + "apex/016-com.google.android.art_compressed/"
RUNTIME_SHA = "f45b10cbc8deb9d2cf32a33df4e778904334cc8cdb0cb628043153029ddf9379"
ART_SHA = "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148"
AUDIT = "out/guest-runtime-apex/actual-source-check.json"
READER = "tools/audit_guest_runtime_apex.py"
SET = "firmware/oneos-pr/OneOS/app-android/packages/x9u-in-sultra.sha256"
PREPARE = (
    "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/raw/"
    "45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/guest_prepare.sh"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def checked(path, maximum, digest, exact=None):
    path = ROOT / path
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and 0 < first.st_size <= maximum
            and (exact is None or first.st_size == exact), f"Selected regular input extent: {path.name}")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) == first.st_size and identity(path.lstat()) == identity(first)
            and sha(raw) == digest, f"Input changed or digest differs: {path.name}")
    return raw


def zip_members(raw, members):
    with ZipFile(BytesIO(raw)) as archive:
        names = archive.namelist()
        require(len(names) <= 24 and len(names) == len(set(names)), "Unique selected ZIP contents")
        result = {}
        for name, size in members.items():
            info = archive.getinfo(name)
            require(not info.is_dir() and info.file_size == size, "Exact selected ZIP member extent")
            with archive.open(info) as stream:
                result[name] = stream.read(size + 1)
            require(len(result[name]) == size, "Exact expanded ZIP member extent")
        return result


def manifest_identity(raw):
    # The exact held manifests have canonical leading protobuf name/version fields.
    require(4 <= len(raw) <= 512 and raw[0] == 0x0a and 0 < raw[1] < 64, "APEX manifest name field")
    end = 2 + raw[1]
    require(end + 1 < len(raw) and raw[end] == 0x10, "APEX manifest version field")
    version = 0
    for index, octet in enumerate(raw[end + 1:end + 6]):
        version |= (octet & 127) << (7 * index)
        if octet < 128:
            require(0 < version <= 0xffffffff and (not index or octet), "Canonical version")
            return raw[2:end].decode("ascii"), version
    raise ValueError("Unterminated version field")


def filesystem(raw, expected):
    sb = raw[1024:2048]
    if expected == "erofs":
        require(sb[:4] == b"\xe2\xe1\xf5\xe0" and sb[12] == 12, "EROFS 4 KiB superblock")
        blocks = struct.unpack_from("<I", sb, 36)[0]
    else:
        require(expected == "ext4" and sb[56:58] == b"\x53\xef"
                and struct.unpack_from("<I", sb, 24)[0] == 2, "Ext4 4 KiB superblock")
        blocks = struct.unpack_from("<I", sb, 4)[0]
    fs_bytes = blocks * 4096
    footer = len(raw) - 64
    magic, major, minor, original, metadata, size = struct.unpack_from(">4sIIQQQ", raw, footer)
    require(magic == b"AVBf" and (major, minor) == (1, 0)
            and 0 < fs_bytes == original <= metadata < metadata + size <= footer
            and raw[metadata:metadata + 4] == b"AVB0", "Payload filesystem and footer bounds")
    return {"type": expected, "blockSize": 4096, "filesystemBytes": fs_bytes,
            "vbmetaOffset": metadata, "vbmetaBytes": size, "avbSignatureVerified": False}


def derive():
    evidence = {}

    def hold(path, maximum, digest, exact=None):
        raw = checked(path, maximum, digest, exact)
        evidence[path] = {"bytes": len(raw), "sha256": digest}
        return raw

    proof = json.loads(hold(AUDIT, 65536, "ec8d59bdc9453c08bb26b9b144f270338869d76386f0c5e5b63bdb698f13e705"))
    require(proof["emptyImageDirectories"]["apex"]["inode"] == 13
            and proof["interpreterLink"]["target"] == "/apex/com.android.runtime/bin/linker64",
            "Held donor root and interpreter target")
    sets = hold(SET, 8192, "cca1a57021c781d7fb590c311194a009b98345304520e56d46828e670cbdbc57")
    exact_set = {"runtime_payload.img": RUNTIME_SHA, "art_payload.img": ART_SHA}
    rows = [line.split() for line in sets.decode().splitlines()]
    for name, digest in exact_set.items():
        require([row for row in rows if row and row[-1] == name] == [[digest, name]],
                "Unique original OneOS set selection")
    prep = hold(PREPARE, 300000, "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d")
    lines = prep.decode().splitlines()
    require(lines[3932] == 'mount_payload "art" "com.android.art"'
            and lines[3934] == 'mount_payload "runtime" "com.android.runtime"'
            and lines[3923].strip() == 'for vdir in "$ROOTFS/apex/\x24{TARGET}"@*; do'
            and lines[3924].strip() == 'if [ -d "$vdir" ]; then'
            and lines[3852] == '    DEST="$ROOTFS/apex/$TARGET"', "Canonical and conditional legacy alias layout")

    runtime_outer = hold(DONOR + "extracted/system/apex/com.android.runtime.apex", 5435392,
                         "f92cbc75018c8620dff83afc47288aa3391f0cbbb1b6578279cd51156dd257d0", 5435392)
    runtime_zip = zip_members(runtime_outer, {"apex_payload.img": 5296128, "apex_manifest.pb": 143})
    runtime_payload = hold(RUNTIME + "apex_payload.img", 5296128, RUNTIME_SHA, 5296128)
    runtime_manifest = hold(RUNTIME + "files/apex_manifest.pb", 143,
                            "48e74bbf3dead7386e9a16ba8ff51cd9983c5d5ab6973bb7fb8c445a9653d0d9", 143)
    require(runtime_payload == runtime_zip["apex_payload.img"]
            and runtime_manifest == runtime_zip["apex_manifest.pb"], "Runtime outer and held payload equality")

    art_wrapper = hold(DONOR + "extracted/system/apex/com.google.android.art_compressed.apex", 13841002,
                       "cdc914c23e8912e27ec7dfee6b7bde6ccfcd4ae57d8411e570cf5ed7fbc36cfe", 13841002)
    art_zip = zip_members(art_wrapper, {"original_apex": 31850496, "apex_manifest.pb": 468})
    art_inner = hold(ART + "original.apex", 31850496,
                     "5a84faabd4a077baea25a24b2d62b63b1f69466e3e6674ff295ac111cac706c9", 31850496)
    require(art_zip["original_apex"] == art_inner, "Exact ART compressed wrapper member")
    art_zip_inner = zip_members(art_inner, {"apex_payload.img": 31633408, "apex_manifest.pb": 400})
    art_payload = hold(ART + "apex_payload.img", 31633408, ART_SHA, 31633408)
    art_manifest = art_zip_inner["apex_manifest.pb"]
    require(art_zip_inner["apex_payload.img"] == art_payload
            and manifest_identity(art_zip["apex_manifest.pb"]) == manifest_identity(art_manifest),
            "ART inner payload and wrapper identity")
    # Reuse the pinned authored ext4 reader without running its CLI.
    source = hold(READER, 32768, "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de")
    reader = {"__file__": str(ROOT / READER), "__name__": "held_apex_reader"}
    exec(compile(source, READER, "exec"), reader)
    image = reader["SelectedExt4"](BytesIO(art_payload), len(art_payload),
                                    "7d1522e19dfa5edba43e98e3a4d20250", 0x42, 96, 7660 * 4096)
    embedded, inode = image.lookup("apex_manifest.pb", 1, 4096)
    require(embedded == art_manifest and inode["inode"] == 81, "ART actual payload manifest")

    def row(key, payload, manifest, source, kind, expected):
        module, version = manifest_identity(manifest)
        require((module, version) == expected, "Exact donor module identity")
        path = "/apex/" + module
        return {"oneOsName": key, "payloadPath": source, "sha256": exact_set[key],
                "bytes": len(payload), "filesystem": filesystem(payload, kind),
                "module": module, "versionCode": version, "manifestSha256": sha(manifest),
                "canonicalTarget": path,
                "conditionalVersionAlias": {"path": f"{path}@{version}", "samePayloadSha256": exact_set[key],
                                            "selected": False, "observedInDonorImage": False}}

    payloads = [
        row("runtime_payload.img", runtime_payload, runtime_manifest, RUNTIME + "apex_payload.img",
            "erofs", ("com.android.runtime", 1)),
        row("art_payload.img", art_payload, art_manifest, ART + "apex_payload.img",
            "ext4", ("com.android.art", 371000140)),
    ]
    return {
        "schema": "guest-apex-staged-inputs/v1",
        "status": "EXACT_PC_PAYLOAD_REFERENCES_STAGED",
        "cohort": "OneOS 0.4.58 x9u-in-sultra",
        "producerSha256": sha(Path(__file__).read_bytes()),
        "payloads": payloads,
        "inputs": evidence,
        "donorApexInode": 13,
        "artEmbeddedManifestInode": inode,
        "aliasSource": "OneOS prepare 3924–3928 handles preexisting versioned directories only",
        "canonicalSource": "OneOS prepare 3853, 3933 and 3935",
        "payloadBytesCopied": 0,
        "mountsCreated": False,
        "linkerConfigSelected": False,
        "activeApexInfoListSelected": False,
        "nativeOrDeviceExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    raw = (json.dumps(derive(), indent=2, ensure_ascii=False) + "\n").encode()
    for directory in (RECEIPT.parent.parent, RECEIPT.parent):
        if args.stage:
            directory.mkdir(exist_ok=True)
        info = directory.lstat()
        require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain owned output directory")
    if args.stage:
        with RECEIPT.open("xb") as stream:
            stream.write(raw)
    require(checked(RECEIPT, len(raw), sha(raw), len(raw)) == raw, "Exact staged manifest")
    print(f"{RECEIPT.relative_to(ROOT).as_posix()} {len(raw)} bytes SHA-256 {sha(raw)}")


if __name__ == "__main__":
    main()
