"""Verify five held donor APEX tree sources without materializing a guest tree."""

import ast
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
from zipfile import ZipFile


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
REV = "45abb3df03cbd4a8b006519baaebefdb2c68658a"
UPSTREAM = ROOT / f"firmware/upstream-oneos-0.4.58/{REV}/raw/{REV}"
EMPTY_LINKS = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
MODULES = {
    "001-com.android.compos": {
        "container": ("com.android.compos.apex", 3121152, "2bdb164415d862d497af8ef44d8cf04fbdcdba971844cba7d5935b539abae8b3"),
        "payload": (2924544, "300fdfdcb640fe98737ab0d5855b7f418dfe5401ade53f1a51f0f832202e7cb2"),
        "index": (1396, "beaf79ce816221c959f0ced23d8a3853b64c9a90ac44ce5b591fb6275c534e8e"),
        "regular": (17, 4709995, "d0945009a762577d1114f203702ddf0bf5d02fd8e8b7323a52bd840f2df6b8d2"),
        "links": (7, "ae4b079e04a94c1193e0f512102d0d2b82a41ded9a1b3a1eacbd50fb11195e9e"),
    },
    "004-com.android.npumanager": {
        "container": ("com.android.npumanager.capex", 2252800, "627ef5ba42f62d4b241f7f09fa965e7b0dbb132a0f92a1295aad40129c553f72"),
        "original": (3006464, "0ccdabf0e7bfc3ff40ee293db8e74d68f1b6a8e71c76b3c9b91e6baa5ed63e44"),
        "outerManifestBytes": 215,
        "payload": (2805760, "043936725b516ac54ec01c92d568e6be04d3c951f5ac67ef73c643a0fa1dacf1"),
        "index": (4453, "acea04a7761fbdf5c6ef967285b65d53ed1f71e2ca5981aabbc2c75c61a882b9"),
        "regular": (50, 6058530, "100716d7d32356cbf25d70720199cf3322346cabb2a133c14056c7e5f1b06138"),
        "links": (0, EMPTY_LINKS),
    },
    "006-com.android.telephonycore": {
        "container": ("com.android.telephonycore.capex", 442368, "98a881319c3f2d13da5e31473bd80640a978d913f42336bd88074ac0392e462e"),
        "original": (503808, "2c30ed055f075cd85275c2630bbf33e41a7b9a9a2968b8a22ad317011cb79138"),
        "outerManifestBytes": 101,
        "payload": (344064, "d01d488e87146b39fd3320861ddc90bdc5fd1f5c44a93ae2ab112d63e9588153"),
        "index": (634, "bde402c81b9ca3c668bb17ca8fb47edaa25cbe3b98b4beef1aa6c112b4f9e2ae"),
        "regular": (8, 551668, "2922073bb855fd19b8985fcd30053838f2ea17ca2f464d780862ee0042eb5b45"),
        "links": (0, EMPTY_LINKS),
    },
    "007-com.android.virt": {
        "container": ("com.android.virt.apex", 63021056, "d5d6ad5ef1ec18ddf841496d2292dbc40bf588b721c13554ad41182432456d7e"),
        "payload": (62750720, "6cebb20d0deef73c7f37cde6754d9c75cc9eb1fc60a9ab7f605ebe734436eb0b"),
        "index": (3514, "768e1eeed4914131ae4c0c853b9033671bf67226fd5c12b799878699faed9f2b"),
        "regular": (40, 89435195, "0f09c5d944cda08ea01d1f160fee89714154250e27282b4d27da0eec212a7b9b"),
        "links": (14, "9f0dba7bdb3e7c36ecfa55040ea0ffda52981ab293d269e28991d40ec6dc2c3c"),
    },
    "012-com.android.webapp": {
        "container": ("com.android.webapp.capex", 3309568, "87818d2f5ecb29a36cb0ff199ab5d5e2eeac904d1de0825e7572665b73ffda9d"),
        "original": (4214784, "8a2cdd1b4f14d9a49c43a4f577a90b94be71423a9e77ddcc63300e9c5a013de8"),
        "outerManifestBytes": 142,
        "payload": (4018176, "71af8beee24c3249a2fd658a6fc43e04ffb203b23a3b43ad19cd518b252a9dd7"),
        "index": (1218, "80f224213581448945cdfe2cce22489da415a1f0f807c48cc4bd73190101881a"),
        "regular": (14, 5981171, "6c40b2e93ebeab8963238c4199099110c744973dca1480d773d679c87b46b627"),
        "links": (0, EMPTY_LINKS),
    },
}
SIDECARS = {
    "001-com.android.compos/app/CompOSPayloadApp@CP2A.260605.016/CompOSPayloadApp.apk.badging.txt": (550, "d14234062655b90095123240489a1113c37ecca1a7696422ec662b833f657d14"),
    "007-com.android.virt/app/EmptyPayloadApp@CP2A.260605.016/EmptyPayloadApp.apk.badging.txt": (728, "cbde719eb44ca7dec6b7aad65b9bc3da941fbecbd04e685bbdf604cbcb6b23df"),
    "007-com.android.virt/app/android.system.virtualmachine.res@CP2A.260605.016/android.system.virtualmachine.res.apk.badging.txt": (548, "c64b8cf605b83ea52e52e24aeb300cc62a6cc04960f0d89acda7d49920fc52c8"),
    "007-com.android.virt/priv-app/VmTerminalApp@CP2A.260605.016/VmTerminalApp.apk.badging.txt": (6625, "1197791cbb7cda3c5ad0a8265df381c397ae68d732a9af0dc8cd0657f0ae8bdc"),
    "012-com.android.webapp/priv-app/WebAppService@CP2A.260605.016/WebAppService.apk.badging.txt": (6528, "d9205adbb4c2ba621a8d14f752205f9f5562296bef7e9c4833014c5bd9421b4a"),
}
LIBRARIES = {
    "android.system.virtualizationcommon-ndk.so": (85936, "a50e3b76e857c604332ca4a28e4f239750c04951d545cd50e1a887f5943fc5a4"),
    "android.system.virtualizationservice-ndk.so": (185992, "5f1f1ba800d913454f7738526edb223c4bd402bbac15b423be929a9c16726c96"),
    "libanyhow.dylib.so": (38648, "0acd282162a0b64f8e92792ca2ef823a38ef653fc1278ac9a0201b1973bb7e28"),
    "libbase.so": (218592, "a2319b3c1f186762d12da8064cd51140535e001b503110386edebaf2f9acabd5"),
    "libc++.so": (1152760, "cb118e98c74d3454858921123b9b51ba13df9cad7dfa141dd892c453661a4d78"),
    "libcap.so": (68272, "11d28e58bc3c1ca4e0bdc20ec4e352f458b19338b4d99a06e3faa8056aa2ccd1"),
    "libcrypto.so": (1782168, "671506ba77b60d707b393928d53dc7b241da92537a60dd9d87046c0c53aa602b"),
    "libcutils.so": (334176, "3d51b9f757f4233856ac3420923badf3ee96221fdca5a24684ae4bd640c4a872"),
    "libminijail.so": (215832, "5544170e67164f0467cc49985d563e73fa5501b09f0460002ef7365c19b181ef"),
    "libprocessgroup.so": (400256, "376d8be528e3003457299a052b592dfed9dfea84c1cf8021d0b7cae61d76bd01"),
    "libsqlite.so": (1522632, "4177ad39be239076f489c7bcbc4e40a0de0f3257d3de611d677e614e65b3f628"),
    "libssl.so": (621584, "7a6a9b6928b62b9e97fd994881ddcea7e6cb4856ea62ca964ba302402cd1e188"),
    "libstd.dylib.so": (948760, "1b656d82be749751208de1625dff0ca40f477009c368d639a792f467461528b1"),
    "libtombstoned_client.so": (36528, "073e05232a2b36cfa0b84d70ce0fa8b1783033eecc388e002392556cb7d8bbec"),
    "libutils.so": (168872, "f142848b2eddd8090c28771f708aa055da5f5204bf5cb986562a2f76abbadaa6"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def directory(path):
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        require(stat.S_ISDIR(info.st_mode) and not is_link(info), "Non-plain source directory")


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def file_data(path, size):
    directory(path.parent)
    before = path.lstat()
    require(not is_link(before) and stat.S_ISREG(before.st_mode) and before.st_size == size, "Regular file extent")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and identity(opened) == identity(before), "Opened file identity")
        data = stream.read(size + 1)
        finished = os.fstat(stream.fileno())
    after = path.lstat()
    require(len(data) == size and not is_link(after) and identity(before) == identity(after)
            and before.st_ctime_ns == after.st_ctime_ns and identity(opened) == identity(finished)
            and opened.st_ctime_ns == finished.st_ctime_ns, "Source changed during bounded read")
    return data


def pinned(path, size, expected):
    data = file_data(path, size)
    require(digest(data) == expected, f"Source digest: {path.name}")
    return data, {"path": Path(os.path.relpath(path, ROOT)).as_posix(), "bytes": size, "sha256": expected}


def reader(path, size, expected, names, scope):
    raw, proof = pinned(ROOT / path, size, expected)
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(nodes) == len(names) and {node.name for node in nodes} == names, "Bounded reader definitions")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), scope)
    return scope, proof


def windows_lx_target(path):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.DeviceIoControl.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
                                       wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID)
    kernel.DeviceIoControl.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    # Zero access, OPEN_EXISTING, and FILE_FLAG_OPEN_REPARSE_POINT.
    handle = kernel.CreateFileW(str(path), 0, 7, None, 3, 0x00200000, None)
    if handle in (None, ctypes.c_void_p(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    output = ctypes.create_string_buffer(1024)
    got = wintypes.DWORD()
    try:
        if not kernel.DeviceIoControl(handle, 0x000900a8, None, 0, output, len(output), ctypes.byref(got), None):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    tag, length, _, version = struct.unpack_from("<IHHI", output.raw)
    require(12 < got.value <= len(output) and tag == 0xa000001d and length + 8 == got.value
            and version == 2, "Selected WSL link framing")
    return output.raw[12:got.value].decode("ascii")


def tree_layout(files, expected, profile, sidecars):
    directory(files)
    stack = [files]
    regular, links, excluded, directories = {}, {}, {}, set()
    count = 0
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                name = path.relative_to(files).as_posix()
                require(re.fullmatch(r"[A-Za-z0-9._+@/-]+", name) and len(name) <= 240, "Tree path grammar")
                info = path.lstat()
                count += 1
                require(count <= 256, "Selected tree entry bound")
                if is_link(info):
                    require(name not in expected and name not in sidecars and name == f"lib64/{path.name}"
                            and path.name in LIBRARIES and getattr(info, "st_reparse_tag", 0) == 0xa000001d,
                            "Unadmitted source link")
                    target = windows_lx_target(path)
                    require(target == f"/system/lib64/{path.name}", "Guest-root link target")
                    links[name] = target
                elif stat.S_ISDIR(info.st_mode):
                    directories.add(name)
                    stack.append(path)
                elif name in sidecars:
                    _, excluded[name] = pinned(path, *sidecars[name])
                else:
                    require(name in expected, "Unindexed tree file")
                    data = file_data(path, expected[name])
                    regular[name] = {"bytes": len(data), "sha256": digest(data)}
    require(set(regular) == set(expected) and set(excluded) == set(sidecars), "Held tree file closure")
    parents = {p.as_posix() for name in (*regular, *links) for p in PurePosixPath(name).parents if p.as_posix() != "."}
    require(directories == parents, "Held tree directory closure")
    require((len(regular), sum(row["bytes"] for row in regular.values()), canonical_digest(regular)) == profile["regular"]
            and (len(links), canonical_digest(links)) == profile["links"], "Held tree pins")
    return {"regularFiles": regular, "directories": sorted(directories), "guestLinks": links,
            "excludedInspectionSidecars": excluded, "regularMapSha256": profile["regular"][2],
            "linkMapSha256": profile["links"][1]}


def audit():
    zip_scope, zip_proof = reader("tools/stage_guest_apex_active_inputs.py", 12334,
        "1b9b7c5a8626f6247bf25616cb98ed36ec1d81462b92946a789a0f32321e828a", {"members"},
        {"ZipFile": ZipFile, "io": io, "require": require})
    pb_scope, pb_proof = reader("tools/audit_guest_linkerconfig_apex_inputs.py", 12371,
        "c5b9f4dcb550d329f4a4b413b6d524c9eec7e7fc4eb48e0321a7f1ea5e081772", {"varint", "fields"}, {"require": require})
    frag_scope, frag_proof = reader("tools/audit_samsung_boot_classpath_cohort.py", 19961,
        "a900fe478abfacbba98bb344cffe7970458883298d35730c15e1e6a859925f17", {"wire", "fragment"}, {})
    frontier, frontier_proof = pinned(ROOT / "out/guest-active-apex-frontier/actual-source-check.json", 11093,
        "f43b65d0d0d911c46c321a118d5a206b7d5c28df192b4a3fb276dd25d6c01d4d")
    fragments = {row["path"]: row for row in json.loads(frontier)["heldClasspathFragmentsNotSelected"]}
    require(len(fragments) == 7, "Seven selected fragment predecessors")
    sums, sums_proof = pinned(UPSTREAM / "app-android/packages/x9u-in-sultra.sha256", 4594,
        "132a0db046d64d5056f8783611829159d0bdc2a822507b256eb4e298fce0790c")
    prep, prep_proof = pinned(UPSTREAM / "switcher/assets/guest_prepare.sh", 285232,
        "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d")
    require('"$STAGE/${m}_payload.img" ] && mount_payload' in prep.decode().splitlines()[3960],
            "Legacy conditional telephonycore source")
    payload_names = {row.split()[-1] for row in sums.decode().splitlines() if row.strip()}
    candidates, dependencies = {}, {}
    for folder, profile in MODULES.items():
        name = folder.split("-", 1)[1]
        short = name.removeprefix("com.android.")
        require(f"{short}_payload.img" not in payload_names, "Additional legacy module selection differs")
        base = DONOR / "apex" / folder
        files = base / "files"
        index_raw, index_pin = pinned(base / "erofs-regular-files.json", *profile["index"])
        index = json.loads(index_raw)
        require(all(row["Mode"] == "-" for row in index), "Held regular-file index shape")
        expected = {row["Path"]: int(row["Size"]) for row in index}
        require(len(expected) == len(index) == profile["regular"][0], "Unique held index paths")
        sidecars = {path.split("/", 1)[1]: spec for path, spec in SIDECARS.items() if path.startswith(folder + "/")}
        layout = tree_layout(files, expected, profile, sidecars)
        regular = layout["regularFiles"]
        manifest_pin = regular["apex_manifest.pb"]
        manifest, _ = pinned(files / "apex_manifest.pb", manifest_pin["bytes"], manifest_pin["sha256"])
        fields = pb_scope["fields"](manifest)
        require(fields.get(1) == [name.encode()] and fields.get(2) == [370399999], "Held APEX identity")
        filename, size, sha = profile["container"]
        outer, outer_pin = pinned(DONOR / "extracted/system/apex" / filename, size, sha)
        evidence = {"preinstalled": outer_pin, "regularExtractionIndex": index_pin}
        if "original" in profile:
            compressed = zip_scope["members"](outer, {"apex_manifest.pb": profile["outerManifestBytes"],
                                                       "original_apex": profile["original"][0]})
            original, evidence["originalApex"] = pinned(base / "original.apex", *profile["original"])
            compressed_fields = pb_scope["fields"](compressed["apex_manifest.pb"])
            require(original == compressed["original_apex"] and all(compressed_fields[k] == fields[k] for k in (1, 2)),
                    "Held CAPEX origin")
        else:
            original = outer
        package = zip_scope["members"](original, {"apex_payload.img": profile["payload"][0],
                                                  "apex_manifest.pb": manifest_pin["bytes"]})
        payload, evidence["payload"] = pinned(base / "apex_payload.img", *profile["payload"])
        require(payload == package["apex_payload.img"] and manifest == package["apex_manifest.pb"]
                and payload[1024:1028] == b"\xe2\xe1\xf5\xe0" and payload[1036] == 12, "Exact held EROFS origin")
        module_fragments = []
        for member, pin in regular.items():
            if not member.startswith("etc/classpaths/"):
                continue
            data, proof = pinned(files / member, pin["bytes"], pin["sha256"])
            previous = fragments.pop(proof["path"])
            require(all(previous[key] == proof[key] for key in proof), "Exact predecessor fragment")
            entries = frag_scope["fragment"](data)
            require(len(entries) == 1, "One selected classpath row")
            entry = entries[0]
            prefix = f"/apex/{name}/"
            path = entry["path"]
            jar_member = path.removeprefix(prefix)
            expected_group = {"etc/classpaths/bootclasspath.pb": 1, "etc/classpaths/systemserverclasspath.pb": 2}[member]
            require(path == previous["literalPath"] and path.startswith(prefix) and jar_member.startswith("javalib/")
                    and jar_member in regular and entry["classpathRaw"] == expected_group
                    and entry["minSdkRaw"] in ("", "36", "37") and not entry["maxSdkRaw"], "Selected local classpath source")
            jar = regular[jar_member]
            raw, jar_proof = pinned(files / jar_member, jar["bytes"], jar["sha256"])
            with ZipFile(io.BytesIO(raw)) as archive:
                require(archive.namelist().count("classes.dex") == 1, "Held classpath code JAR")
            module_fragments.append({"fragment": proof, "entry": entry, "jar": jar_proof})
        for target in layout["guestLinks"].values():
            if target not in dependencies:
                raw, proof = pinned(DONOR / "extracted" / target[1:], *LIBRARIES[PurePosixPath(target).name])
                require(raw.startswith(b"\x7fELF\x02\x01") and struct.unpack_from("<H", raw, 18)[0] == 183,
                        "Held guest-root link ELF identity")
                dependencies[target] = proof
        candidates[name] = {"versionCode": 370399999, "proposedTreeRoot": f"/apex/{name}",
                            "source": evidence, "tree": layout, "classpathFragments": module_fragments,
                            "legacySetPayloadListed": False, "activeAliasAdmitted": False}
    require(not fragments and set(dependencies) == {f"/system/lib64/{name}" for name in LIBRARIES}, "Exact frontier closure")
    return {"schema": "guest-tree-apex-input-proof/v1", "status": "VERIFIED_HELD_TREE_SOURCE_CANDIDATES",
            "source": {"frontier": frontier_proof, "set": sums_proof, "prepare": prep_proof,
                       "zipReader": zip_proof, "manifestReader": pb_proof, "fragmentReader": frag_proof},
            "candidates": candidates, "heldGuestSystemLinkTargets": dependencies,
            "runtimeApexInfoList": None, "materializedTree": None,
            "unresolved": ["Original filesystem mode, ownership and label application for projected trees",
                           "Exact active module and mount selection plus effective SDK and classpath merge",
                           "Runtime linker configuration and transitive native dependency resolution"],
            "hostFallbackUsed": False, "nativeOrDeviceExecuted": False}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
