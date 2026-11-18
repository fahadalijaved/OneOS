"""Verify two explicit guest SystemServer APEX providers and their saved aliases."""

import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import tarfile
from zipfile import ZipFile


ROOT = Path(__file__).absolute().parents[1]
DONOR = ROOT.parent / "firmware/donor"
REV = "45abb3df03cbd4a8b006519baaebefdb2c68658a"
UPSTREAM = ROOT / f"firmware/upstream-oneos-0.4.58/{REV}/raw/{REV}"
HOST = ROOT.parent / "firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar"
HOST_BYTES = 20434769920
PROVIDERS = {
    "tethering": {
        "version": 371021120, "held": "037-com.google.android.tethering_compressed",
        "container": ("com.google.android.tethering_compressed.apex", 13202026, "ad3c462e1cb442dbf698a8d1f116642471cf03d32a4870b4bac157310300e6d3"),
        "outerManifestBytes": 666,
        "original": (30326784, "4152937491c76b41b14fa57f112ab8470d636a4216aef4212d79fba53d8dce0b"),
        "payload": (30027776, "ebeca4cf5c792d44a2093b4c7f08271d951b85b0c3ceb4610c08b6a8e6e596a1"),
        "manifest": (598, "4776430b9f12333e5693d60074b5737df48bee498536a363398710b55ab6154b"),
        "ext4": (96, 7271),
        "jar": ("service-connectivity.jar", 2282917, "59ce2687dd07b75096902fb2c6205b58f5362f2293bfa6c89484feda8a2f3ee1"),
        "dexBytes": 2241956, "zipEntries": 40,
        "calls": [(2368, 2372, 2374, "com.android.server.NetworkStatsServiceInitializer"),
                  (2656, 2658, 2660, "com.android.server.ConnectivityServiceInitializer")],
        "host": (371021120, 2282917, "59ce2687dd07b75096902fb2c6205b58f5362f2293bfa6c89484feda8a2f3ee1", 19164532736, 20144135680),
    },
    "wifi": {
        "version": 371020840, "held": "041-com.google.android.wifi_compressed",
        "container": ("com.google.android.wifi_compressed.apex", 7664231, "38b82416bf49b82d669b62452bd320eb158c28d2e2042df70fa5fadfac13975d"),
        "outerManifestBytes": 192,
        "original": (19456000, "ff2fbf1f7565749064eb58298745b6e1741dd8ddd346e63546145f47df87661c"),
        "payload": (19251200, "93f7758cee7ad56d20c4ee80cd270837d1ecb187efacfbc473f3d27c3184f2f6"),
        "manifest": (124, "3306d8adabe0dcd515eed24c192281a558f0ce46cb2ec0cbb3a950ac3523c731"),
        "ext4": (64, 4660),
        "jar": ("service-wifi.jar", 5538557, "07970ef09586d84c0ae5c1dbd9ff504dd30f9a85321ab6bb85cd3cb2786e748a"),
        "dexBytes": 5535000, "zipEntries": 12,
        "calls": [(2433, 2437, 2439, "com.android.server.wifi.WifiService")],
        "host": (370399999, 5530221, "a1ba3c2c177156a297896a1e1b65f2b51eaedf001539616bdf1e3f7ec921347d", 18900777472, 19756999168),
    },
}
FRAGMENTS = {
    "001-com.android.compos/files/etc/classpaths/systemserverclasspath.pb": (57, "9be5497144c397b69afc5103e7043c4bd04c0bf083660840baad99e81a3746c1"),
    "004-com.android.npumanager/files/etc/classpaths/bootclasspath.pb": (71, "46c371be0d4236be8a687afc18490347375c41348fe5d9630999b3f73411dbf7"),
    "004-com.android.npumanager/files/etc/classpaths/systemserverclasspath.pb": (65, "88ec76933da9e1482a82a3fa2f378f1e2ceecfe103f982725e37d30ef0409f78"),
    "006-com.android.telephonycore/files/etc/classpaths/bootclasspath.pb": (73, "5c66e6f44d8fd915ff106efa81ef9ee012eceb357d29a5ceb4b1f6c114db600d"),
    "007-com.android.virt/files/etc/classpaths/bootclasspath.pb": (69, "b6bc48f7a4c6509c9ec89a9f995b1e61eb4f520c61d22a18b857c57c29108bd9"),
    "007-com.android.virt/files/etc/classpaths/systemserverclasspath.pb": (63, "a4dd4caa56d6ed12bd8dbc6b14363fb9263d3f309720124371c7b80d9ad7a211"),
    "012-com.android.webapp/files/etc/classpaths/bootclasspath.pb": (63, "5e1a2f4e099b954a433f60fbcb812754dcd322d7b28bb455b7fdaa348f2f1400"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def stage_readers():
    path = ROOT / "tools/stage_guest_apex_active_inputs.py"
    for directory in reversed(path.parents):
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Stager source ancestor")
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400
            and info.st_size == 12334, "Stager source extent")
    with path.open("rb") as stream:
        raw = stream.read(12335)
    digest = "1b9b7c5a8626f6247bf25616cb98ed36ec1d81462b92946a789a0f32321e828a"
    require(len(raw) == 12334 and hashlib.sha256(raw).hexdigest() == digest, "Stager source pin")
    names = {"require", "plain", "check_directories", "read_helpers", "members", "selected_metadata", "module_row"}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    require(len(nodes) == len(names) and {node.name for node in nodes} == names, "Stager reader definitions")
    scope = {key: globals()[key] for key in ("ROOT", "DONOR", "Path", "os", "hashlib", "stat", "struct", "ast", "io", "ZipFile")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope, {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": digest}


def defined_classes(dex, descriptors):
    require(dex[:8] == b"dex\n039\0" and struct.unpack_from("<III", dex, 32) == (len(dex), 112, 0x12345678),
            "Selected DEX039 header")
    def table(header, stride):
        count, offset = struct.unpack_from("<II", dex, header)
        require(0 < count <= 1_000_000 and 112 <= offset <= offset + count * stride <= len(dex), "DEX table extent")
        return count, offset
    string_count, strings = table(56, 4)
    type_count, types = table(64, 4)
    class_count, classes = table(96, 32)
    target = {item.encode("ascii"): item for item in descriptors}
    found = {}
    for index in range(class_count):
        (type_index,) = struct.unpack_from("<I", dex, classes + index * 32)
        require(type_index < type_count, "Class definition type index")
        (string_index,) = struct.unpack_from("<I", dex, types + type_index * 4)
        require(string_index < string_count, "Class descriptor string index")
        (start,) = struct.unpack_from("<I", dex, strings + string_index * 4)
        require(0 < start < len(dex), "Class descriptor start")
        # Selected ASCII descriptors are shorter than 128 code units.
        size = dex[start]
        if size >= 128 or start + size + 1 >= len(dex) or dex[start + size + 1] != 0:
            continue
        candidate = dex[start + 1:start + size + 1]
        if candidate in target:
            name = target[candidate]
            require(name not in found, "Duplicate selected class definition")
            found[name] = index
    require(set(found) == set(descriptors), "Explicit provider definition missing")
    return found


def provider_dex(jar, profile):
    with ZipFile(io.BytesIO(jar)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == profile["zipEntries"], "Provider JAR entry set")
        require([name for name in names if re.fullmatch(r"classes[0-9]*\.dex", name)] == ["classes.dex"],
                "Single provider DEX")
        entry = archive.getinfo("classes.dex")
        require(entry.file_size == profile["dexBytes"], "Provider DEX extent")
        with archive.open(entry) as stream:
            data = stream.read(entry.file_size + 1)
        require(len(data) == entry.file_size, "Provider DEX length")
    return data


def read_host_aliases(short, profile, helpers):
    record, plain_source = helpers["record"], helpers["plain_source"]
    version, size, digest, first, second = profile["host"]
    require(plain_source(HOST).st_size == HOST_BYTES, "Host archive extent")
    jar = profile["jar"][0]
    selected = []
    with HOST.open("rb") as archive:
        before = os.fstat(archive.fileno())
        require(before.st_size == HOST_BYTES, "Host archive FD extent")
        for suffix, offset in (("", first), (f"@{version}", second)):
            path = f"apex/com.android.{short}{suffix}/javalib/{jar}"
            archive.seek(offset)
            header = tarfile.TarInfo.frombuf(archive.read(512), "utf-8", "strict")
            require(header.name == path and header.type in (tarfile.REGTYPE, tarfile.AREGTYPE)
                    and header.size == size, "Saved alias archive header")
            data = archive.read(size)
            proof = record(data)
            require(proof == {"bytes": size, "sha256": digest}, "Saved alias JAR bytes")
            selected.append(({"path": "/" + path, "headerOffset": offset, **proof}, data))
        after = os.fstat(archive.fileno())
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "Host archive FD changed")
    require(selected[0][1] == selected[1][1], "Two saved host alias JAR bytes differ")
    return {"versionCode": version, "members": [item[0] for item in selected]}, selected[0][1]


def audit():
    stage, stage_pin = stage_readers()
    helpers, reader_pin = stage["read_helpers"]()
    read, record = helpers["pinned"], helpers["record"]
    ext4, ext4_pin = helpers["ext4_reader"]()
    prep, prep_pin = read(UPSTREAM / "switcher/assets/guest_prepare.sh", 285232,
                         "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d")
    sums, sum_pin = read(UPSTREAM / "app-android/packages/x9u-in-sultra.sha256", 4594,
                         "132a0db046d64d5056f8783611829159d0bdc2a822507b256eb4e298fce0790c")
    lines = prep.decode().splitlines()
    for number, text in {
        3938: "tethering stays the HOST's module",
        3948: 'mount_payload "wifi" "com.android.wifi"',
        3960: "for m in telephonycore conscrypt profiling; do",
        3982: "for a in /apex/*; do",
        3993: '--bind "$a" "$ROOTFS/apex/$base"',
        4007: 'for vdir in "$ROOTFS/apex/${TARGET}"@*; do',
        4010: '"$LOOP" "$vdir"',
        4025: '"$ROOTFS/apex/com.android.wifi"@*',
    }.items():
        require(text in lines[number - 1], f"Legacy APEX line {number}")
    pairs = [row.split() for row in sums.decode().splitlines()]
    require(not any(row and row[-1] == "tethering_payload.img" for row in pairs), "Legacy tethering replacement selected")
    require([row for row in pairs if row and row[-1] == "wifi_payload.img"]
            == [[PROVIDERS["wifi"]["payload"][1], "wifi_payload.img"]], "Legacy Wi-Fi payload row")

    prior, prior_pin = read(ROOT / "out/guest-apex-active-inputs/r-27f937479ad7483a893a399d6f8b94eb/receipt.json", 7782,
                            "8bdfef9391822e16b566943c11e2210f81cf4adbbc53faa8b37b6fd7060340b5")
    require(json.loads(prior)["runtimeApexInfoList"] is None, "Expected candidate-only predecessor")
    source, source_pin = read(ROOT / "firmware/guest-credential-producer-preparation/20261106T063927238551Z-58b1face298d498e80463d58b625cc23.jsonl",
                             464096, "466e081a3101878f460cb4c257bb35c240732f634feeab21240b79c0101e2c1a")
    bodies = [row for line in source.splitlines() if (row := json.loads(line))["record"] == "method"
              and row["body"]["signature"].startswith("startOtherServices(")]
    require(len(bodies) == 1 and bodies[0]["body"]["owner"] == "Lcom/android/server/SystemServer;"
            and bodies[0]["normalizedBodySha256"] == "390130385ce05b4a21eafcb2151de78ecffddded71e84f4a5dbead4b897ceafa", "Staged SystemServer body")
    ins = {row["pc"]: row for row in bodies[0]["body"]["instructions"]}
    require(ins[2418]["reference"] == "string=android.hardware.wifi" and ins[2424]["targetPc"] == 2463,
            "Wi-Fi feature branch")
    host_groups, group_pin = read(ROOT.parent / "out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/proven-active-apex-payload-groups.json",
                                  100230, "da5d8ad65a02643b5af497457a31834cc5141ac9de5f5b7de87b0cdbb25c94f2")
    groups = json.loads(host_groups)["groups"]
    providers = {}
    for short, profile in PROVIDERS.items():
        row, proof = stage["module_row"](short, profile, helpers, ext4)
        target = "/apex/" + row["moduleName"]
        jar, size, digest = profile["jar"]
        jar_path = f"{target}/javalib/{jar}"
        calls, descriptors = [], []
        for class_pc, path_pc, call_pc, name in profile["calls"]:
            require(ins[class_pc]["reference"] == "string=" + name and ins[path_pc]["reference"] == "string=" + jar_path
                    and "SystemServiceManager;->startServiceFromJar(" in ins[call_pc]["reference"], "Direct staged provider call")
            calls.append({"class": name, "classPc": class_pc, "pathPc": path_pc, "callPc": call_pc})
            descriptors.append("L" + name.replace(".", "/") + ";")
        payload, _ = read(DONOR / "apex" / profile["held"] / "apex_payload.img", *profile["payload"])
        inodes, blocks = profile["ext4"]
        fs = ext4(io.BytesIO(payload), len(payload), "7d1522e19dfa5edba43e98e3a4d20250", 0x42, inodes, blocks * 4096)
        jar_bytes, jar_pin = fs.lookup("javalib/" + jar, 1, 6 * 1024 * 1024)
        require(record(jar_bytes) == {"bytes": size, "sha256": digest}, "Donor provider JAR pin")
        dex = provider_dex(jar_bytes, profile)
        defs = defined_classes(dex, descriptors)
        host, host_bytes = read_host_aliases(short, profile, helpers)
        aliases = {target, f"{target}@{host['versionCode']}"}
        group = [item for item in groups if {m["mountpoint"] for m in item["mounts"]} == aliases]
        require(len(group) == 1 and group[0]["provenUniqueActivePayloadGroup"], "Saved host alias group")
        host["savedMountIdentity"] = group[0]["mountIdentity"]
        host["hostJarBytesEqualDonor"] = host_bytes == jar_bytes
        providers[short] = {
            "module": row["moduleName"], "donorVersionCode": profile["version"],
            "donorPackageEvidence": proof, "requestedProviderPath": jar_path, "stagedSystemServerCalls": calls,
            "donorProviderJar": jar_pin, "donorClassDefIndices": defs, "savedHostOnly": host,
            "legacyProfile": "donor payload explicitly selected" if short == "wifi" else "host module retained for BPF dependency",
            "privateUnversionedOrVersionedAliasAdmitted": False,
        }
    require(providers["tethering"]["savedHostOnly"]["hostJarBytesEqualDonor"]
            and not providers["wifi"]["savedHostOnly"]["hostJarBytesEqualDonor"], "Exact provider comparison")

    fragments = []
    for path, (size, digest) in FRAGMENTS.items():
        data, pin = read(DONOR / "apex" / path, size, digest)
        literals = re.findall(rb"/apex/[a-zA-Z0-9._/-]+\.jar", data)
        require(len(literals) == 1, "Selected raw classpath path literal")
        fragments.append({**pin, "literalPath": literals[0].decode("ascii")})
    return {
        "schema": "guest-active-apex-frontier/v1",
        "status": "EXPLICIT_PROVIDER_CANDIDATES_VERIFIED_ALIASES_UNSELECTED",
        "source": {"candidateReceipt": prior_pin, "stager": stage_pin, "reader": reader_pin, "ext4": ext4_pin,
                   "legacyPreparation": prep_pin, "legacySet": sum_pin, "stagedSystemServer": source_pin,
                   "hostAliasGroups": group_pin},
        "providers": providers, "heldClasspathFragmentsNotSelected": fragments,
        "otherUnboundInputs": ["Actual active APEX list and owned mount/alias identities",
                              "Tethering BPF loader, live maps and complete selected module dependencies",
                              "Wi-Fi effective mounted bin policy and framework/service cohort",
                              "Complete classpath filtering, ordering and remaining active modules"],
        "runtimeApexInfoList": None, "hostArchiveRehashedInFull": False,
        "mountOrOemExecuted": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
