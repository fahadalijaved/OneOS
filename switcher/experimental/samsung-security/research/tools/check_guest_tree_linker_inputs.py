"""Bind the held donor linkerconfig producer and selected native providers as data."""

import ast
import io
import json
import os
import struct
import sys

from check_guest_tree_active_apex import DONOR, ROOT, digest, plain_directory, read_exact, require
from check_guest_tree_runtime_apex import held_reader, pin


OUT = ROOT / "out/guest-tree-linker-inputs"
SYSTEM = DONOR / "extracted/system"
RUNTIME = DONOR / "apex/005-com.android.runtime/files"
I18N = DONOR / "apex/003-com.android.i18n"
PINS = {
    "fileReader": (ROOT / "tools/check_guest_tree_active_apex.py", 13501,
                   "4fe18c87e9e0b45203ef97a0a4e9a0ce69127128da3d446154fc0e042292c3e8"),
    "runtimeView": (ROOT / "out/guest-tree-runtime-apex/receipt.json", 23165,
                    "33cc6e4a2e263b54cd27174388924cdf6803d35c72cf398fc5883819123b25d4"),
    "priorInputs": (ROOT / "out/guest-linkerconfig-apex-inputs/actual-source-check.json", 8352,
                    "ef1b525953c16c43f93f4867ad544ea4a8eb9c3c494bf52154f55258ac64d342"),
    "elfReader": (ROOT / "tools/audit_guest_runtime_apex.py", 15155,
                  "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de"),
    "manifestReader": (ROOT / "tools/audit_guest_linkerconfig_apex_inputs.py", 12371,
                       "c5b9f4dcb550d329f4a4b413b6d524c9eec7e7fc4eb48e0321a7f1ea5e081772"),
    "initRc": (SYSTEM / "etc/init/hw/init.rc", 117704,
               "d14ca8301c0795a6fe10425a3d20bf8fbf628b0aeed4b7b6f560fd061e78dcd1"),
    "init": (SYSTEM / "bin/init", 2888328, "8db6b39facd5af0745d9bd27c588dacedb6ae5e21a87870644d0b49d33e19757"),
    "generator": (RUNTIME / "bin/linkerconfig", 496480,
                  "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb"),
    "artPayload": (DONOR / "apex/016-com.google.android.art_compressed/apex_payload.img", 31633408,
                   "391e25c00f71217669879482c4055ae27855e8b5be8df9f4dfcd018fa02fc148"),
    "i18nPayload": (I18N / "apex_payload.img", 21409792,
                    "1750220fbfa2af1611a8ed7b1b3526074953b3a863f0e066a3fede2a4ea7d756"),
    "i18nManifest": (I18N / "files/apex_manifest.pb", 151,
                     "b3f750cc2e929d6a665f734411052cce2b035780d2e8539fb0df5d7b681cbf58"),
}
INIT_WINDOWS = {
    "performApexConfig": (0xb0e0c, 2516, "31adba6ea44f0cbd65cb0e6c5ac84ece7bac65d51051c8cbdd6313bd71f89d1a"),
}
GENERATOR_WINDOWS = {
    "main": (0x140c0, 7228, "236ac66dfb972e19c6dc9eb0a3b28023f534eef81a2f2ced9ac25390ffc6d6a0"),
    "scanActiveApexes": (0x2d2f4, 11040, "f2447283ac19d6382f095388300c7856cd3a0eb61c89f593e7f1c49d4ed020de"),
    "getActivePackages": (0x3aecc, 2776, "c438fbb9cf0efb07b53917dfa76c031af32b1ba32e7ce6ddda329a5da1d69d66"),
    "generateApexConfiguration": (0x18390, 1216, "a8ae0dfcacaa20c3049dbd4179c7924992dc2879b395ead6e19791c8a82891f9"),
}
INIT_CALLS = {
    0xb0e74: 0xd467c,  # GetApexListFrom
    0xb1174: 0xfa848,  # GetCurrentMountNamespace
    0xb1280: 0xd5774,  # ParseRcScriptsFromAllApexes
    0xb1308: 0x2a1a40,  # logwrap_fork_execvp
}
GENERATOR_CALLS = {
    0x143c4: 0x189bc, 0x14464: 0x2d2f4,  # LoadVariables and ScanActiveApexes
    0x2d3f4: 0x3aecc, 0x2d924: 0x31a98, 0x2e61c: 0x398a8,  # package scan, inner config, XML
    0x14b04: 0x31a98, 0x14c98: 0x31a98, 0x14e34: 0x31a98, 0x14fd4: 0x31a98,  # partition config
    0x15418: 0x2810c, 0x15608: 0x16e84, 0x1571c: 0x18390,  # base, write, then per-APEX
    0x18510: 0x1cfe4, 0x18524: 0x16e84,  # build/write per-APEX config
}
GENERATOR_PATHS = {
    0x4000: "/apex.libraries.config.txt", 0x4127: "/vendor/etc/linker.config.pb",
    0x4a17: "/system/etc/public.libraries.txt", 0x4f97: "/system/etc/llndk.libraries.txt",
    0x525b: "/system_ext/etc/linker.config.pb", 0x527c: "/ld.config.txt",
    0x54ab: "/product/etc/linker.config.pb", 0x5826: "/apex_manifest.pb",
    0x5a1c: "/system/bin/recovery", 0x5e05: "/apex-info-list.xml",
    0x6417: "/system/etc/sanitizer.libraries.txt", 0x658e: "/system/etc/linker.config.pb",
    0x6a0b: "/etc/linker.config.pb", 0x6b71: "/vendor/etc/public.libraries.txt",
}
ART_FILES = {
    "libdexfile.so": (266624, "c5ec41a3e41bd0b541e9a8ee3d44aadd4aa3756561f9061da01baf1945fed33a"),
    "libnativeloader.so": (170528, "9ccc3018fb3c2d8708488ccd225b09ed4ca4451bc5d6cc0b18256e5ab2d6e395"),
    "libsigchain.so": (68288, "e7ef711e06b33d5a6e4e4c58f7f7c7c7921672c77a90b8a07e45afeeef8b2093"),
    "libnativebridge.so": (51408, "209b23aef98408a49584c316032ca26b81c26a6bd8bcb38670acf7cc6faef3ec"),
    "libnativehelper.so": (51496, "d974e14ee74159048fcce7e35f2d595dc8a3b703f5e9e445594ed73c0ae18693"),
}
I18N_FILES = {
    "libicu_jni.so": (271112, "8e5fb7f90f8effe28d5ec34e03d32ba449543ffc800effa7296eefc2164543a3"),
    "libicu.so": (70696, "3da3d5bb5e95eef36e3e97b7c7917c41c67fd7d624f730099c04ccd8bc9a61e4"),
    "libicuuc.so": (2085064, "0938f2301cd990bddd0c86d76fc6d9e8b67895e35d4fd0b02afe73de56ea3010"),
    "libicui18n.so": (2928440, "849d10347af07ce3cc86bf556a81392db1a5f7301fd1835cf53617d6200498c8"),
}


def manifest_reader(raw):
    names = {"require", "varint", "fields", "manifest"}
    body = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(body) == len(names) and {node.name for node in body} == names, "Exact manifest reader")
    namespace = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), "pinned-linker-manifest-reader", "exec"), namespace)
    return namespace["manifest"], namespace["fields"]


def verify_native(raw, windows, calls, paths):
    require(raw[:7] == b"\x7fELF\x02\x01\x01" and struct.unpack_from("<H", raw, 18) == (183,),
            "Donor AArch64 source")
    result = {}
    for name, (offset, size, expected) in windows.items():
        require(digest(raw[offset:offset + size]) == expected, f"Source body: {name}")
        result[name] = {"offset": offset, "bytes": size, "sha256": expected}
    for pc, target in calls.items():
        op, = struct.unpack_from("<I", raw, pc)
        delta = op & 0x3ffffff
        if delta & 0x2000000:
            delta -= 1 << 26
        require(op >> 26 == 0b100101 and pc + delta * 4 == target, f"Direct call at {pc:#x}")
    for offset, value in paths.items():
        encoded = value.encode("ascii") + b"\0"
        require(raw[offset:offset + len(encoded)] == encoded, f"Source path: {value}")
    return {"windows": result, "directCalls": {hex(pc): hex(target) for pc, target in calls.items()},
            "pathOperands": {hex(offset): value for offset, value in paths.items()}}


def boot_order(rc):
    expected = {
        121: "mkdir /linkerconfig/bootstrap 0755", 122: "mkdir /linkerconfig/default 0755",
        134: "write /linkerconfig/bootstrap/ld.config.txt \\#", 135: "write /linkerconfig/default/ld.config.txt \\#",
        140: "mount none /linkerconfig/bootstrap /linkerconfig bind rec",
        156: "exec_start apexd-bootstrap", 157: "perform_apex_config",
        1659: "wait_for_prop apexd.status activated",
        1662: "wait_for_prop keystore.module_hash.sent true", 1663: "perform_apex_config",
    }
    lines = rc.decode("utf-8").splitlines()
    require(all(lines[i - 1].strip() == text for i, text in expected.items()), "Donor boot producer order")
    return expected


def read_prior(row):
    return pin(ROOT / row["path"], row["bytes"], row["sha256"])


def module_inputs(data, previous, runtime, reader, elf, manifest, fields):
    runtime_input = previous["donorRuntime"]
    runtime_manifest = manifest(read_prior(runtime_input["manifest"]), "com.android.runtime", 1)
    runtime_config = fields(read_prior(runtime_input["config"]))
    require(runtime_manifest == runtime_input["fields"] and runtime_config == {2: [1]},
            "Runtime manifest and namespace visibility")

    art = reader(io.BytesIO(data["artPayload"]), len(data["artPayload"]),
                 "7d1522e19dfa5edba43e98e3a4d20250", 0x42, 96, 7660 * 4096)
    art_pb, art_pb_pin = art.lookup("apex_manifest.pb", 1, 16384)
    art_cfg, art_cfg_pin = art.lookup("etc/linker.config.pb", 1, 16384)
    art_manifest = manifest(art_pb, "com.android.art", 371000140)
    require(art_pb_pin == previous["donorArt"]["manifest"] and art_cfg_pin == previous["donorArt"]["config"]
            and art_manifest == previous["donorArt"]["fields"]
            and fields(art_cfg) == {1: [b"/data", b"/apex/com.android.art/javalib"]}, "ART manifest and policy")
    i18n_manifest = manifest(data["i18nManifest"], "com.android.i18n", 1)
    require(data["i18nPayload"][1024:1028] == b"\xe2\xe1\xf5\xe0", "Held I18N EROFS")
    libraries = {}
    for name, (size, sha) in ART_FILES.items():
        raw, row = art.lookup("lib64/" + name, 1, 2 * 1024 * 1024)
        current = elf(raw)
        require((row["bytes"], row["sha256"]) == (size, sha) and current["soname"] == name
                and name in art_manifest["provideNativeLibs"], f"ART provider: {name}")
        libraries[name] = {"candidatePath": "/apex/com.android.art/lib64/" + name, **current}
    for name, (size, sha) in I18N_FILES.items():
        raw = pin(I18N / "files/lib64" / name, size, sha)
        current = elf(raw)
        require(current["soname"] == name and name in i18n_manifest["provideNativeLibs"],
                f"I18N provider: {name}")
        libraries[name] = {"candidatePath": "/apex/com.android.i18n/lib64/" + name, **current}
    routes = runtime["appProcessDirectLibraryCandidates"]
    for name in ("libnativeloader.so", "libsigchain.so"):
        candidate = libraries[name].copy()
        candidate["candidate"] = candidate.pop("candidatePath")
        require(candidate == routes[name], f"Original app-process ART dependency: {name}")
    require("libdexfile.so" in runtime_manifest["requireNativeLibs"]
            and {"libicu_jni.so", "libicu.so"} <= set(art_manifest["requireNativeLibs"])
            and "libnativehelper.so" in libraries["libicu_jni.so"]["needed"]
            and {"libicuuc.so", "libicui18n.so"} <= set(libraries["libicu.so"]["needed"]),
            "Selected namespace edges")
    return {"runtimeManifest": runtime_manifest, "runtimeConfigVisible": True,
            "artManifest": art_manifest, "artConfigPermittedPaths": previous["donorArt"]["permittedPaths"],
            "i18nManifest": i18n_manifest, "verifiedProviders": libraries}


def check():
    data = {k: pin(*item) for k, item in PINS.items()}
    previous = json.loads(data["priorInputs"])
    runtime = json.loads(data["runtimeView"])["sourceCandidate"]
    reader, elf = held_reader(data["elfReader"])
    manifest, fields = manifest_reader(data["manifestReader"])
    phases = boot_order(data["initRc"])
    init_paths = {0x1a863: "/apex/com.android.runtime/bin/linkerconfig", 0x2a150: "--target", 0x2bf12: "/linkerconfig"}
    init = verify_native(data["init"], INIT_WINDOWS, INIT_CALLS, init_paths)
    generator = verify_native(data["generator"], GENERATOR_WINDOWS, GENERATOR_CALLS, GENERATOR_PATHS)
    producer = elf(data["generator"])
    require(producer["interpreter"] == "/system/bin/linker64" and producer["needed"] ==
            ["libbase.so", "libc++.so", "libc.so", "libm.so", "libdl.so"]
            and all(name in runtime["appProcessDirectLibraryCandidates"] for name in producer["needed"]),
            "Generator's own interpreter and direct dependency identities")
    parts = previous["donorPartitionInputs"]
    for row in parts.values():
        read_prior(row)
    modules = module_inputs(data, previous, runtime, reader, elf, manifest, fields)
    return {
        "schema": "oneos-guest-tree-linker-inputs/v1",
        "status": "BLOCKED_PRIVATE_ACTIVE_APEX_AND_EFFECTIVE_LINKER_VIEW",
        "pins": {k: {"path": os.path.relpath(p, ROOT).replace("\\", "/"), "bytes": n, "sha256": h}
                 for k, (p, n, h) in PINS.items()},
        "bootInitOrder": phases, "initCode": init, "generatorCode": generator,
        "generatorElf": producer, "generatorArgumentVector": [init_paths[i] for i in (0x1a863, 0x2a150, 0x2bf12)],
        "generatorDirectLibraryCandidates": {
            name: runtime["appProcessDirectLibraryCandidates"][name]["candidate"] for name in producer["needed"]},
        "verifiedPartitionSourceBytes": parts, "effectivePartitionViewSelected": False,
        "moduleInputs": modules,
        "orderedPrivatePrerequisites": [
            "Retain private system/partition/data mounts and effective property inputs, then admit the generator interpreter and its five direct file candidates",
            "Select the active package set and bind its stable mounted manifests, optional inner configs and matching XML",
            "Bind effective system/system_ext/vendor/product protobufs and conditional library lists to that same view",
            "Obtain and verify actual base ld.config.txt, applicable per-APEX configs and apex.libraries.config.txt before guest entry",
        ],
        "unselectedNamedApexEdges": [
            {"source": "app_process64 DT_NEEDED", "provider": "com.android.art", "libraries": ["libnativeloader.so", "libsigchain.so"]},
            {"source": "com.android.runtime manifest", "provider": "com.android.art", "libraries": ["libdexfile.so"]},
            {"source": "com.android.art manifest", "provider": "com.android.i18n", "libraries": ["libicu_jni.so", "libicu.so"]},
        ],
        "generatedConfig": None, "entryAdmission": None,
    }


def main():
    result = check()
    body = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    plain_directory(OUT.parent)
    OUT.mkdir(exist_ok=True)
    plain_directory(OUT)
    receipt = OUT / "receipt.json"
    try:
        with receipt.open("xb") as stream:
            stream.write(body)
    except FileExistsError:
        pass
    require(read_exact(receipt, len(body)) == body, "Receipt readback")
    print(result["status"], digest(body), receipt.relative_to(ROOT).as_posix())
    return 2


if __name__ == "__main__":
    sys.exit(main())
