"""Audit selected donor entry files beyond runtime and ART, without executing them."""

from io import BytesIO
from hashlib import sha256
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
DONOR = "../firmware/donor/"
SYSTEM = DONOR + "extracted/system/"
UPSTREAM = (
    "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/raw/"
    "45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/"
)
SDK = DONOR + "apex/036-com.google.android.sdkext_compressed/"
I18N = DONOR + "apex/003-com.android.i18n/"
TZ = DONOR + "apex/038-com.google.android.tzdata6/"
PROCESS_DUP = (
    "_Z21createProcessGroupDupjiNSt3__112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEEb"
)


def dynamic_symbol(raw, name):
    offset = struct.unpack_from("<Q", raw, 40)[0]
    width, count = struct.unpack_from("<HH", raw, 58)
    if width != 64 or not 0 < count <= 128 or offset + width * count > len(raw):
        raise ValueError("ELF section table bounds")
    sections = [struct.unpack_from("<IIQQQQIIQQ", raw, offset + i * width) for i in range(count)]
    symtab, = [section for section in sections if section[1] == 11]
    _, _, _, _, start, size, link, _, _, stride = symtab
    strings = sections[link]
    if (stride != 24 or size % stride or start + size > len(raw)
            or strings[1] != 3 or strings[4] + strings[5] > len(raw)):
        raise ValueError("Dynamic symbol table bounds")
    data = raw[strings[4]:strings[4] + strings[5]]
    matches = []
    for index in range(start, start + size, stride):
        pos, flags, visibility, section, address, length = struct.unpack_from("<IBBHQQ", raw, index)
        if pos < len(data) and data.startswith(name.encode() + b"\0", pos):
            matches.append({"name": name, "defined": section != 0, "address": address,
                            "bytes": length, "binding": flags >> 4, "visibility": visibility & 3})
    symbol, = matches
    return symbol


def audit():
    evidence = {}
    # The two held authored tools contain only definitions at import time.
    tools = (
        ("tools/stage_guest_apex_inputs.py", "f9304bc2ae68b08adb6702f3a2ccad60e140b03852d05cd5876c53147b769288"),
        ("tools/audit_guest_runtime_apex.py", "c9481656bc3f794375768a3d22189b48c975d4bf7f2ee3d5b90584d9294696de"),
    )
    modules = []
    for name, digest in tools:
        raw = (ROOT / name).read_bytes()
        if len(raw) > 32768 or sha256(raw).hexdigest() != digest:
            raise ValueError("Selected authored tool changed")
        evidence[name] = {"sha256": digest, "bytes": len(raw)}
        scope = {"__file__": str(ROOT / name), "__name__": "held_apex_tools"}
        exec(compile(raw, name, "exec"), scope)
        modules.append(scope)
    stage, native = modules
    require, elf = stage["require"], native["elf"]
    zip_members, filesystem, manifest = (stage[k] for k in ("zip_members", "filesystem", "manifest_identity"))

    def read(path, expected, maximum):
        raw = stage["checked"](path, maximum, expected)
        evidence[path] = {"sha256": expected, "bytes": len(raw)}
        return raw

    extra = {
        "i18n_payload.img": "1750220fbfa2af1611a8ed7b1b3526074953b3a863f0e066a3fede2a4ea7d756",
        "sdkext_payload.img": "448f4909cc27a33be33ea85d3d950d38d285c2964c930c043eb3827c89ff267f",
    }
    sets = read(stage["SET"], "cca1a57021c781d7fb590c311194a009b98345304520e56d46828e670cbdbc57", 8192)
    pairs = [row.split() for row in sets.decode().splitlines()]
    for name, digest in extra.items():
        require([pair for pair in pairs if pair and pair[-1] == name] == [[digest, name]],
                "Exact OneOS cohort")
    require(not any(pair and pair[-1] == "tzdata_payload.img" for pair in pairs),
            "Timezone set admission requires separate review")
    prep = read(stage["PREPARE"], "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d", 300000)
    require(prep.decode().splitlines()[3933] == 'mount_payload "i18n" "com.android.i18n"'
            and prep.decode().splitlines()[3935] == 'mount_payload "sdkext" "com.android.sdkext"',
            "OneOS module placement")
    start = read(UPSTREAM + "guest_start.sh",
                 "81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2", 90000)
    start_lines = start.decode().splitlines()
    require(start_lines[112:114] == ["DERIVE=/apex/com.android.sdkext/bin/derive_classpath",
                                     "CLASSPATH_FILE=/data/system/environ/classpath"]
            and "keeps the host's class paths" in start_lines[122], "Actual guest classpath producer and fallback")
    profile = json.loads(read("out/guest-entry-exec-profile/PROFILE.json",
        "bcb875cdaca995f3802ef971b635003d696a9893041d549d2ff3157e9e70cdef", 128000))
    defaults = {row["name"]: row["default"] for row in profile["execEnvironment"]["table"]}
    require(defaults["ANDROID_I18N_ROOT"] == "/apex/com.android.i18n"
            and defaults["ANDROID_TZDATA_ROOT"] == "/apex/com.android.tzdata"
            and defaults["BOOTCLASSPATH"] is None and defaults["SYSTEMSERVERCLASSPATH"] is None,
            "Original launcher root and classpath defaults")

    i18n_outer = read(SYSTEM + "apex/com.android.i18n.apex",
                      "3112df21cb7dab93e0b2866706502df6f624c96ea0aeb6bb83c83c4a552443c1", 21557248)
    i18n = read(I18N + "apex_payload.img", extra["i18n_payload.img"], 21409792)
    i18n_entries = zip_members(i18n_outer, {"apex_payload.img": 21409792, "apex_manifest.pb": 151})
    i18n_manifest = read(I18N + "files/apex_manifest.pb",
                        "b3f750cc2e929d6a665f734411052cce2b035780d2e8539fb0df5d7b681cbf58", 151)
    require(i18n == i18n_entries["apex_payload.img"] and i18n_manifest == i18n_entries["apex_manifest.pb"]
            and manifest(i18n_manifest) == ("com.android.i18n", 1), "I18N payload and identity")
    icu_path = I18N + "files/lib64/libicu.so"
    # The existing EROFS extraction supplies the selected library, not a new unpack.
    icu = elf(read(icu_path, "3da3d5bb5e95eef36e3e97b7c7917c41c67fd7d624f730099c04ccd8bc9a61e4", 70696))
    require(icu["soname"] == "libicu.so", "I18N native library")
    jar = read(I18N + "files/javalib/core-icu4j.jar",
               "951ea2edfbbcd780ae3cb1394fefbe7fb41d92d43bdc6270843d3703eadd7fe7", 3078649)
    classpath = read(SYSTEM + "etc/classpaths/bootclasspath.pb",
                     "76177dd92015f52655dde366efa84bf28643782142547d65191a00bf59a677bd", 8192)
    icu_boot_jar = "/apex/com.android.i18n/javalib/core-icu4j.jar"
    require(jar.startswith(b"PK\x03\x04") and classpath.count(icu_boot_jar.encode()) == 2,
            "Held donor boot classpath entry")

    sdk_outer = read(SYSTEM + "apex/com.google.android.sdkext_compressed.apex",
                     "c83ce550b2b679113343f52a833645c67bc650241b715b9049ac4074c75eccf1", 610920)
    sdk_wrapper = zip_members(sdk_outer, {"original_apex": 1384448, "apex_manifest.pb": 133})
    sdk_inner = read(SDK + "original.apex", "915179f8aa39b48402e14aae1d3e3f044370dc9ca2cfa6505d880e8017b7ca12", 1384448)
    sdk_entries = zip_members(sdk_inner, {"apex_payload.img": 1212416, "apex_manifest.pb": 65})
    sdk = read(SDK + "apex_payload.img", extra["sdkext_payload.img"], 1212416)
    require(sdk_inner == sdk_wrapper["original_apex"] and sdk == sdk_entries["apex_payload.img"],
            "SDKEXT compressed wrapper and payload")
    ext4 = native["SelectedExt4"]
    uuid = "7d1522e19dfa5edba43e98e3a4d20250"
    sdkfs = ext4(BytesIO(sdk), len(sdk), uuid, 0x42, 32, 290 * 4096)
    embedded, _ = sdkfs.lookup("apex_manifest.pb", 1, 4096)
    require(embedded == sdk_entries["apex_manifest.pb"]
            and manifest(embedded) == manifest(sdk_wrapper["apex_manifest.pb"])
            == ("com.android.sdkext", 370547060), "SDKEXT actual filesystem module")
    binary, executable = sdkfs.lookup("bin/derive_classpath", 1, 1048576)
    rc, service = sdkfs.lookup("etc/derive_classpath.rc", 1, 4096)
    require(executable["inode"] == 13 and executable["mode"] == "0o100755"
            and executable["sha256"] == "015e20a3dba724c2dae7ff8015bc50658f6f1a89e329e620200504568d7a0f2e"
            and rc.startswith(b"service derive_classpath /apex/com.android.sdkext/bin/derive_classpath\n"),
            "Actual derive_classpath producer and init service")
    derivation = elf(binary)
    require(derivation["interpreter"] == "/system/bin/linker64"
            and derivation["needed"] == ["liblog.so", "libc.so", "libm.so", "libdl.so"],
            "Classpath producer ELF inputs")
    init = read(SYSTEM + "etc/init/hw/init.rc",
                "d14ca8301c0795a6fe10425a3d20bf8fbf628b0aeed4b7b6f560fd061e78dcd1", 512000)
    require([line.strip() for line in init.decode().splitlines()[1688:1690]]
            == ["exec_start derive_classpath", "load_exports /data/system/environ/classpath"],
            "Original classpath producer and consumer")

    tz = read(TZ + "apex_payload.img", "d76bc9cfecb30568082cfac6c09b7e843e794fbd364b98f210a9d0815398ad59", 864256)
    tzfs = ext4(BytesIO(tz), len(tz), uuid, 0x42, 48, 206 * 4096)
    tz_manifest, _ = tzfs.lookup("apex_manifest.pb", 1, 4096)
    tzdata, timezone = tzfs.lookup("etc/tz/tzdata", 1, 524288)
    require(manifest(tz_manifest) == ("com.android.tzdata", 371021100)
            and tzdata.startswith(b"tzdata2026c\0"), "Actual donor timezone asset")

    runtime = read(SYSTEM + "lib64/libandroid_runtime.so",
                   "edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279", 3200000)
    pg = read(SYSTEM + "lib64/libprocessgroup.so",
              "376d8be528e3003457299a052b592dfed9dfea84c1cf8021d0b7cae61d76bd01", 400256)
    require({"libicu.so", "libprocessgroup.so"} <= set(elf(runtime)["needed"])
            and elf(pg)["soname"] == "libprocessgroup.so", "Actual native dependencies")
    importer, provider = dynamic_symbol(runtime, PROCESS_DUP), dynamic_symbol(pg, PROCESS_DUP)
    require(not importer["defined"] and provider["defined"] and provider["address"] == 0x30ae4
            and provider["bytes"] == 1284 and provider["binding"] == 1 and provider["visibility"] == 0,
            "Matching actual process-group dynamic symbol")
    caller = json.loads(read("firmware/guest-common-namespace-proof/coloros-zygote-selected.json",
        "5568c1a4c5ad983b3d3ab0828fec95b44397c22b388f8479c80a72445d5bb631", 900000))
    edge, = [instruction for method in caller["functions"] if "SpecializeCommon" in method["symbol"]
             for instruction in method["instructions"] if instruction.get("targetSymbol") == PROCESS_DUP]
    require(caller["sourceSha256"] == stage["sha"](runtime) and edge["pc"] == 0x130510
            and runtime[edge["pc"]:edge["pc"] + 4].hex() == edge["bytes"], "Exact specialization call")
    literals = {
        0xfa82: "%s/uid_%u", 0xfbcf: "%s/system/uid_%u", 0x110a7: "%s/pid_%d",
        0x11dc9: "%s/apps/uid_%u", 0x10c43: "/etc/cgroups.json",
        0x110fb: "/vendor/etc/cgroups.json", 0x10152: "/system_ext/etc/task_profiles.json",
        0x105f3: "/etc/task_profiles.json", 0x11c82: "/vendor/etc/task_profiles.json",
        0x1145c: "cgroup.procs",
    }
    for offset, value in literals.items():
        require(pg.startswith(value.encode() + b"\0", offset), "Exact native config/path literal")
    groups = json.loads(read(SYSTEM + "etc/cgroups.json",
        "a6903cbef1321281c74fe007b29161aad136837908b222c424f141d86d4d67bd", 4096))
    profiles = json.loads(read(SYSTEM + "etc/task_profiles.json",
        "a928742b8697cd78dece935dfc07238c5bbddde58764210e633c8332b95d5c1c", 30000))
    joins = [{"profile": profile["Name"], **action["Params"]} for profile in profiles["Profiles"]
             for action in profile["Actions"] if action["Name"] == "JoinCgroup"]
    require(groups["Cgroups2"]["Path"] == "/sys/fs/cgroup" and len(joins) == 59, "Held donor profile selection")

    return {
        "schema": "guest-entry-runtime-deps/v1",
        "status": "EXACT_HELD_EXTRA_ENTRY_INPUTS_AND_CGROUP_FRONTIER",
        "inputs": evidence,
        "oneOsSet": "x9u-in-sultra",
        "i18n": {"target": "/apex/com.android.i18n", "versionCode": 1, "setPinned": True,
                 "filesystem": filesystem(i18n, "erofs"), "libicu": icu, "bootClasspathJar": icu_boot_jar},
        "sdkext": {"target": "/apex/com.android.sdkext", "versionCode": 370547060, "setPinned": True,
                   "filesystem": filesystem(sdk, "ext4"), "deriveClasspath": derivation,
                   "executableInode": executable, "serviceInode": service,
                   "outputPathInLegacySource": "/data/system/environ/classpath",
                   "generatedOutputAvailable": False},
        "tzdata": {"targetCandidate": "/apex/com.android.tzdata", "versionCode": 371021100,
                   "setPinned": False, "filesystem": filesystem(tz, "ext4"), "tzdata": timezone,
                   "tzdataVersion": "2026c"},
        "processgroup": {"caller": edge, "import": importer, "provider": provider,
                         "binaryFileLiterals": {hex(key): value for key, value in literals.items()},
                         "donorBaseCgroups": groups, "donorBaseJoinActions": joins,
                         "effectiveOverridesAndPathSelectionProved": False},
        "launcherRootDefaults": defaults,
        "linkerConfigInventedOrSelected": False,
        "nativeOrDeviceExecuted": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
