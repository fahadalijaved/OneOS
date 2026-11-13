"""Stage ordered donor classpath fragments as evidence, without exporting an env."""

import argparse
import ast
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import stat
import struct
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DONOR = ROOT.parent / "firmware/donor"
OUT = ROOT / "out/guest-classpath-inputs/receipt.json"
ART = DONOR / "apex/016-com.google.android.art_compressed"
SDK = DONOR / "apex/036-com.google.android.sdkext_compressed"
I18N = DONOR / "apex/003-com.android.i18n"
UUID = "7d1522e19dfa5edba43e98e3a4d20250"
KEYS = {
    1: "BOOTCLASSPATH", 2: "SYSTEMSERVERCLASSPATH",
    3: "DEX2OATBOOTCLASSPATH", 4: "STANDALONE_SYSTEMSERVER_JARS",
}
FRAGMENT_DIR = "etc/classpaths/"


def require(condition, label):
    if not condition:
        raise ValueError(label)


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def path_for_receipt(path):
    return (path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT)
            else "../" + path.relative_to(ROOT.parent).as_posix())


def stat_key(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def held(path, limit, expected=None, collect=True):
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and 0 < first.st_size <= limit,
            f"Fixed regular input: {path_for_receipt(path)}")
    with path.open("rb") as stream:
        if collect:
            data = stream.read(limit + 1)
            require(len(data) == first.st_size, "Exact bounded read")
            digest = sha256(data).hexdigest()
        else:
            digest = sha256()
            remaining = first.st_size
            while remaining:
                piece = stream.read(min(remaining, 1 << 20))
                require(piece, "Short bounded input")
                remaining -= len(piece)
                digest.update(piece)
            require(not stream.read(1), "Input grew during read")
            with ZipFile(stream) as archive:
                require("classes.dex" in archive.namelist(), "Selected donor code jar")
            digest = digest.hexdigest()
            data = None
    require(stat_key(first) == stat_key(path.lstat()) and (expected is None or digest == expected),
            f"Unchanged pinned input: {path_for_receipt(path)}")
    return data, {"path": path_for_receipt(path), "bytes": first.st_size, "sha256": digest}


def derive():
    inputs = []

    def read(path, limit, expected):
        data, pin = held(path, limit, expected)
        inputs.append(pin)
        return data

    reader = read(ROOT / "tools/audit_guest_runtime_apex.py", 32768,
                  "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de")
    scope = {"__name__": "held_ext4_reader",
             "__file__": str(ROOT / "tools/audit_guest_runtime_apex.py")}
    exec(compile(reader, "held_ext4_reader", "exec"), scope)
    ext4 = scope["SelectedExt4"]
    # Reuse only the bounded data decoder definitions, without the Samsung CLI.
    parser = read(ROOT / "tools/audit_samsung_boot_classpath_cohort.py", 32768,
                  "a900fe478abfacbba98bb344cffe7970458883298d35730c15e1e6a859925f17")
    nodes = [n for n in ast.parse(parser).body if isinstance(n, ast.FunctionDef)
             and n.name in {"wire", "fragment"}]
    require(len(nodes) == 2, "Selected wire decoder")
    wire_scope = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "held_classpath_decoder", "exec"), wire_scope)

    staging = json.loads(read(ROOT / "out/guest-apex-staging/receipt.json", 16384,
        "6b4deb968e6fb8ffcc672fc4f17e858d779c34e5c02df572a2d68d8c88c5325a"))
    deps = json.loads(read(ROOT / "out/guest-entry-runtime-deps/actual-source-check.json", 65536,
        "f782c1c0a95c99ef0e3152a55e4220fc1cfb32799bdc3455610b5a47010e53b1"))
    modules = {
        r["module"]: {"version": r["versionCode"], "payloadSha256": r["sha256"],
                      "target": r["canonicalTarget"]}
        for r in staging["payloads"]
    }
    for short, folder, digest in (
        ("i18n", I18N, "1750220fbfa2af1611a8ed7b1b3526074953b3a863f0e066a3fede2a4ea7d756"),
        ("sdkext", SDK, "448f4909cc27a33be33ea85d3d950d38d285c2964c930c043eb3827c89ff267f"),
    ):
        require(deps["inputs"][path_for_receipt(folder / "apex_payload.img")]["sha256"] == digest
                and deps[short]["setPinned"], "Exact held extended APEX cohort")
        target = deps[short]["target"]
        modules[target.rsplit("/", 1)[1]] = {"version": deps[short]["versionCode"],
                                            "payloadSha256": digest, "target": target}
    require(set(modules) == {"com.android.art", "com.android.runtime", "com.android.i18n",
                            "com.android.sdkext"}, "Bounded donor module set")

    art = read(ART / "apex_payload.img", 31633408, modules["com.android.art"]["payloadSha256"])
    sdk = read(SDK / "apex_payload.img", 1212416, modules["com.android.sdkext"]["payloadSha256"])

    def art_fs():
        return ext4(BytesIO(art), len(art), UUID, 0x42, 96, 7660 * 4096)

    def sdk_fs():
        return ext4(BytesIO(sdk), len(sdk), UUID, 0x42, 32, 290 * 4096)

    producer, producer_inode = sdk_fs().lookup("bin/derive_classpath", 1, 1048576)
    proof = json.loads(read(ROOT / "firmware/samsung-boot-classpath-cohort/producer-native.json", 700000,
        "a9da108c3b8b28f66145f88e3ff59f863d9606904be2178a724f665b2b2dd935"))
    require(producer_inode["sha256"] == proof["sourceSha256"] == deps["sdkext"]["deriveClasspath"]["sha256"],
            "The donor and held native semantics proof use the same producer bytes")
    instructions = {}
    require(len(proof["functions"]) == 5, "Complete held semantics spans")
    for fn in proof["functions"]:
        start = fn["fileOffset"]
        code = producer[start:start + fn["bytes"]]
        require(sha256(code).hexdigest() == fn["sha256"]
                and code == b"".join(bytes.fromhex(i["bytes"]) for i in fn["instructions"]),
                "Exact donor producer instruction spans")
        instructions.update({i["pc"]: i for i in fn["instructions"]})
    enums = {}
    for i in range(5):
        pointer, size, value, padding = struct.unpack_from("<QQiI", producer, 0x82c68 + 24 * i)
        require(0 < size <= 64 and padding == 0 and pointer + size <= len(producer),
                "Actual generated enum entry")
        enums[value] = producer[pointer:pointer + size].decode("ascii")
    require(enums == {0: "UNKNOWN", **KEYS}
            and instructions[0x47ce0]["targetSymbol"] == "glob"
            and "ReadFileToString" in instructions[0x48220]["targetSymbol"]
            and "android_get_device_api_level" in instructions[0x491d0]["targetSymbol"]
            and producer.startswith(b"/apex/com.android.art\0", 0x44da),
            "Actual producer enum and discovery evidence")

    for module, dirname, digest in (
        ("com.android.runtime", "005-com.android.runtime", "3b8617b93a307b5693e309eb54479d0a1402454ef44ae4dba75fa619c3bcea58"),
        ("com.android.i18n", "003-com.android.i18n", "018fff2c561904ee9aa43d330e6925599f4ecd5c3cf1423db51d8cfc6e0739da"),
    ):
        rows = json.loads(read(DONOR / "apex" / dirname / "erofs-regular-files.json", 4096, digest))
        require(not any(r["Path"].startswith(FRAGMENT_DIR) for r in rows),
                "Held EROFS regular-file index has no classpath fragments")
        modules[module]["fragmentsInHeldErofsIndex"] = []

    roots = {"com.android.art": art_fs, "com.android.sdkext": sdk_fs}
    fragments = []
    boot, server = "bootclasspath.pb", "systemserverclasspath.pb"
    platform = DONOR / "extracted/system"
    plat_pins = {
        boot: "76177dd92015f52655dde366efa84bf28643782142547d65191a00bf59a677bd",
        server: "3ce7f81f64a3cf395c728a4d54130eebc05bd96ab08bde52bb2bc0c3d7c71531",
    }
    jars = {}
    references = set()
    capacity = 0

    def jar(path):
        nonlocal capacity
        if path in jars:
            return jars[path]
        if path.startswith("/system/framework/"):
            source = DONOR / "extracted" / path[1:]
            _, result = held(source, 64 * 1024 * 1024, collect=False)
            result["sourceKind"] = "original donor partition extraction"
        elif path == "/apex/com.android.i18n/javalib/core-icu4j.jar":
            result = {"path": path_for_receipt(I18N / "files/javalib/core-icu4j.jar"),
                      "bytes": 3078649,
                      "sha256": "951ea2edfbbcd780ae3cb1394fefbe7fb41d92d43bdc6270843d3703eadd7fe7",
                      "sourceKind": "held donor EROFS extraction"}
            held(ROOT / result["path"], result["bytes"], result["sha256"], collect=False)
        else:
            require(path.startswith("/apex/"), "Selected APEX jar path")
            _, _, name, relative = path.split("/", 3)
            require(name in roots and relative.startswith("javalib/"), "Owned APEX jar source")
            raw, result = roots[name]().lookup(relative, 1, 7_000_000)
            with ZipFile(BytesIO(raw)) as archive:
                require("classes.dex" in archive.namelist(), "APEX code jar")
            result.update(sourceKind="exact payload inode", module=name, payloadMember=relative,
                          payloadSha256=modules[name]["payloadSha256"])
        capacity += result["bytes"]
        require(capacity <= 200 * 1024 * 1024, "Selected classpath jar aggregate bound")
        jars[path] = result
        return result

    def add(source, name, data, inode=None):
        origin = "/system" if source == "system" else "/apex/" + source
        allowed = {1, 3} if name == boot else {2, 4}
        entries = wire_scope["fragment"](data)
        require(0 < len(entries) <= 64, "Bounded nonempty fragment")
        groups = {KEYS[k]: [] for k in sorted(allowed)}
        for entry in entries:
            path = entry["path"]
            key = entry["classpathRaw"]
            require(key in allowed and (key, path) not in references
                    and re.fullmatch(r"/(?:[A-Za-z0-9._+-]+/)+[A-Za-z0-9._+-]+\.jar", path)
                    and all(part not in (".", "..") for part in path[1:].split("/")),
                    "Unique classpath entry with safe absolute jar path")
            require(source == "system" or path.startswith(origin + "/javalib/"),
                    "APEX fragment cannot export another module's jar")
            require(all(not entry[k] or re.fullmatch(r"[1-9][0-9]{0,2}", entry[k])
                        for k in ("minSdkRaw", "maxSdkRaw")), "Held fragment SDK qualifier grammar")
            references.add((key, path))
            jar(path)
            groups[KEYS[key]].append(entry)
        fragments.append({"path": f"{origin}/{FRAGMENT_DIR}{name}", "origin": source,
                          "sha256": sha256(data).hexdigest(), "bytes": len(data),
                          "payloadInode": inode, "orderedGroups": groups})

    for name, digest in plat_pins.items():
        add("system", name, read(platform / FRAGMENT_DIR / name, 8192, digest))
    for module, names in (("com.android.art", [boot, server]), ("com.android.sdkext", [boot])):
        view = roots[module]()
        root = view.directory(2)[0]
        etc = view.directory(root["etc"][0])[0]
        contents = view.directory(etc["classpaths"][0])[0]
        require(set(contents) == {".", "..", *names}, "Exact selected module fragment directory")
        for name in names:
            data, row = view.lookup(FRAGMENT_DIR + name, 1, 8192)
            add(module, name, data, row["inode"])

    counts = {key: sum(len(f["orderedGroups"].get(key, [])) for f in fragments) for key in KEYS.values()}
    require(counts == dict(zip(KEYS.values(), (24, 5, 23, 0))) and len(jars) == 29,
            "Exact held subset category counts")
    return {
        "schema": "guest-classpath-input-subset/v1",
        "status": "VERIFIED_PARTIAL_INPUTS_NO_ENV_EXPORT",
        "producerSha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": inputs,
        "sameByteDonorDeriveClasspath": producer_inode,
        "primaryProducerEvidence": {"globPc": "0x47ce0", "readPc": "0x48220",
                                    "apiQueryPc": "0x491d0", "artPrefixFileOffset": "0x44da"},
        "heldModuleCandidates": modules,
        "fragments": fragments,
        "heldJarObjects": jars,
        "heldJarBytes": capacity,
        "declaredEntryCounts": counts,
        "ordering": "Per-fragment protobuf ordinal only. Manifest array order is not merged runtime order.",
        "missingRuntimeInputs": ["complete active guest module and partition scan",
                                 "effective SDK/codename filter inputs",
                                 "merged four-group order and standalone-group completeness",
                                 "selected mounted jar and loader identities"],
        "complete": False,
        "exportedEnvironment": None,
        "hostFallbackUsed": False,
        "nativeOrDeviceExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--stage", action="store_true")
    actions.add_argument("--verify", action="store_true")
    actions.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    proof = derive()
    if args.require_complete and not proof["complete"]:
        parser.exit(2, "Refused: held subset cannot supply a complete runtime classpath\n")
    raw = (json.dumps(proof, indent=2) + "\n").encode()
    for path in (OUT.parent.parent, OUT.parent):
        if args.stage:
            path.mkdir(exist_ok=True)
        info = path.lstat()
        require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain private output directory")
    if args.stage:
        with OUT.open("xb") as stream:
            stream.write(raw)
    verified, _ = held(OUT, len(raw), sha256(raw).hexdigest())
    require(verified == raw, "Exact saved input receipt")
    print(f"{path_for_receipt(OUT)} {len(raw)} bytes SHA-256 {sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
