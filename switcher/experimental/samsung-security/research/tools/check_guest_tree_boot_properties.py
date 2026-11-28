"""Verify held private-tree boot property inputs and report the effective-view hold."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-boot-properties/receipt.json"
DONOR = "../firmware/donor/"
SYSTEM = DONOR + "extracted/system/"
RUNTIME = DONOR + "apex/005-com.android.runtime/files/"
SAVED = "firmware/installed-oneos-code-profile/static/assets/"
PROP_INPUTS = (
    ("system/build.prop", 28816, "4661edb3c8e09ac75af0bd19a0c48fecba86511f3d6bec383c0db4bd31709582"),
    ("system/system_ext/etc/build.prop", 8085, "76108b9c2cd1d9c2058e9e0df4ff1d1074d94bac3c75e68fab3b693afe2a534b"),
    ("system/product/etc/build.prop", 4668, "768eca01390a557b871c75b9c4abfc728c4916a8101a0628421d57f2de02b94b"),
    ("my_bigball/build.prop", 93, "32ce4036aa1cd906b083fb39fc854cf6498486d92dbf75ef501e116bab51d096"),
    ("my_carrier/build.prop", 93, "06d9ddccecb9bfad27b0e7967cfc3add6d92dc1f0fc52d22fc315806388deb77"),
    ("my_engineering/build.prop", 331, "29b30c4dc8bbc2cb28a51701cad4c0f266329a82d86d08347cc6c227efe0bce0"),
    ("my_heytap/build.prop", 91, "e30b4bcc5282141231f468d2d0d428afb4364e1c6ef9d8ecb7542e4edf9f1075"),
    ("my_manifest/build.prop", 4993, "b1b1ae56310be0e77dcb81d2b53a800a274af5fb9b92897d419e8dbcfdc926a8"),
    ("my_product/build.prop", 8744, "6219ed51565925e3a7e4a922bac423c0decc918f6536e9c59a71909329396563"),
    ("my_region/build.prop", 901, "d67f868af6e716888868bcc44d928f00a73f701005494af308028dd718002623"),
    ("my_stock/build.prop", 1619, "1c62bd72f3d022770116e3b50f6f8a90cf5fd40677d6ca4d31767dd385356251"),
)


def require(condition, label):
    if not condition:
        raise ValueError(label)


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def file_key(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_held(path, size):
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and first.st_size == size,
            f"Plain input of exact size required: {path}")
    with path.open("rb") as stream:
        fd = os.fstat(stream.fileno())
        require(file_key(fd) == file_key(first), "Input identity changed on open")
        raw = stream.read(size + 1)
        after_fd = os.fstat(stream.fileno())
        require(len(raw) == size and file_key(after_fd) == file_key(fd) and
                after_fd.st_ctime_ns == fd.st_ctime_ns, "Input descriptor changed during read")
    after_name = path.lstat()
    require(plain(after_name) and file_key(after_name) == file_key(first) and
            after_name.st_ctime_ns == first.st_ctime_ns, "Input name changed during read")
    return raw


def signed(bits, width):
    return bits - (1 << width) if bits & (1 << (width - 1)) else bits


def word(raw, pc):
    return int.from_bytes(raw[pc:pc + 4], "little")


def call(raw, pc, expected, tail=False):
    insn = word(raw, pc)
    require(insn >> 26 == (5 if tail else 0x25) and
            pc + 4 * signed(insn & 0x3FFFFFF, 26) == expected, f"Native edge {pc:#x}")


def literal_ref(raw, pc, expected, key, page=False, prefix_bytes=None):
    insn = word(raw, pc)
    immediate = signed((insn >> 5 & 0x7FFFF) << 2 | (insn >> 29 & 3), 21)
    require(insn & 0x9F000000 == (0x90000000 if page else 0x10000000), f"Address edge {pc:#x}")
    if page:
        add = word(raw, pc + 4)
        require(add & 0xFFC00000 == 0x91000000 and add >> 5 & 31 == insn & 31,
                f"Literal ADD source {pc + 4:#x}")
        address = (pc & ~0xFFF) + (immediate << 12) + (add >> 10 & 0xFFF)
    else:
        address = pc + immediate
    literal = key.encode("ascii") + b"\0"
    if prefix_bytes is not None:
        literal = literal[:prefix_bytes]
    require(address == expected and raw.startswith(literal, address), f"Exact native literal {key}")


def native_property_rows(linker, libc, group, android):
    literal_ref(libc, 0xC4014, 0x239BF, "/dev/__properties__")
    call(libc, 0xC4018, 0xA4D18)
    call(libc, 0xA4D90, 0xA4DDC)
    literal_ref(libc, 0xAF4D8, 0x23454, "ro.build.version.sdk")
    call(libc, 0xAF4F8, 0x11E9E8)
    call(android, 0x237D90, 0x2AD168, tail=True)
    call(android, 0x130510, 0x2B1638)
    call(linker, 0x394A4, 0x6E5E0)
    rows = []

    def add(raw, consumer, key, ref, offset, pcs, target, behavior, page=True, prefix=None):
        literal_ref(raw, ref, offset, key, page=page, prefix_bytes=prefix)
        for pc in pcs:
            call(raw, pc, target)
        rows.append({"consumer": consumer, "key": key, "keyReferencePc": hex(ref),
                     "callPc": [hex(pc) for pc in pcs], "behavior": behavior})

    add(linker, "linkerconfig", "ro.debuggable", 0x2CBE0, 0x4144, (0x2CC1C,),
        0x6E568, "GetBoolProperty default false. Policy input, not selected from the donor.",
        page=False)
    add(linker, "linkerconfig", "ro.vndk.lite", 0x32898, 0x647A, (0x328CC,),
        0x39324, "Variable lookup, then exact true-string comparison.", page=False)
    add(linker, "linkerconfig", "ro.vndk.version", 0x32AA8, 0x5120, (0x32ADC, 0x32C70),
        0x39324, "Variable lookup and presence test. Values depend on the selected vendor view.")
    add(linker, "linkerconfig", "ro.product.vndk.version", 0x32B7C, 0x4545,
        (0x32BB0, 0x32D38), 0x39324,
        "Variable lookup and presence test. Values depend on the selected product view.")
    add(group, "libprocessgroup", "ro.product.first_api_level", 0x38D5C, 0x114DD,
        (0x38D94, 0x3DD0C), 0x5A8F0, "Unsigned getter default 0, max UINT_MAX. TaskProfiles and ReadDescriptors select configuration by this API.")
    add(group, "libprocessgroup", "ro.config.low_ram", 0x2CD4C, 0x10BBE, (0x2CD74,),
        0x5A200, "UsePerAppMemcg reads with default false. The literal's final m is encoded in an immediate.", prefix=16)
    require(word(group, 0x2CD5C) == 0x52800DAA, "Low RAM final character immediate")
    add(group, "libprocessgroup", "ro.config.per_app_memcg", 0x2CD9C, 0x11183, (0x2CDD0,),
        0x5A200, "UsePerAppMemcg reads with the low-RAM result as default.")
    for key, ref, offset, pc in (
        ("ro.oplus.osense_app_memcg", 0x30C1C, 0x1134F, 0x30C50),
        ("ro.vendor.config.oplus.low_ram", 0x30F4C, 0x11483, 0x30F64),
        ("ro.vendor.config.oplus.disable_malloc_abench_opt", 0x30F74, 0xFDDB, 0x30F8C),
        ("persist.sys.oplus.hybridswap_app_memcg", 0x310D8, 0x11B84, 0x3110C),
        ("persist.sys.oplus.hybridswap_app_uid_memcg", 0x31370, 0x11A5C, 0x313A4),
    ):
        add(group, "libprocessgroup", key, ref, offset, (pc,), 0x5A200,
            "Conditional createProcessGroupDup read, default false. No runtime branch was selected.")
    return rows


def derive():
    pins = {}

    def read(name, size, digest):
        raw = read_held(ROOT / name, size)
        require(sha256(raw).hexdigest() == digest, f"Exact held source: {name}")
        pins[name] = {"bytes": size, "sha256": digest}
        return raw

    def data(name, size, digest):
        return json.loads(read(name, size, digest))

    linker = read(RUNTIME + "bin/linkerconfig", 496480,
                  "a031a17cd4d1c50cecee8959c6f155c9d3b8f377f2e03798636e37835f23fefb")
    libc = read(RUNTIME + "lib64/bionic/libc.so", 1550096,
                "c9057b270a62b45b0dcae87e5d6a187a2dde1e7f86f8a2e0d68f2eb180e57d99")
    group = read(SYSTEM + "lib64/libprocessgroup.so", 400256,
                 "376d8be528e3003457299a052b592dfed9dfea84c1cf8021d0b7cae61d76bd01")
    android = read(SYSTEM + "lib64/libandroid_runtime.so", 3138824,
                   "edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279")
    native = native_property_rows(linker, libc, group, android)
    cp = data("out/guest-classpath-selection/receipt.json", 42906,
              "38fb09fdf184b9edbad2b1846a18d706ed09a4ccf0ef2c567b1fbf3f0fff5acb")
    launcher = data("out/guest-entry-exec-profile/PROFILE.json", 14274,
                    "bcb875cdaca995f3802ef971b635003d696a9893041d549d2ff3157e9e70cdef")
    raw_launcher = read("firmware/guest-entry-exec-profile/zygote_exec", 891104,
                        "d8096b25e63764072a8790a3a9c76c92158418923fc25a409e727feb1261e635")
    require(launcher["launcher"]["sha256"] == sha256(raw_launcher).hexdigest() and
            launcher["selected"] is False and not launcher["actualStagedExecutableProved"],
            "Exact packaged launcher, staged/loaded cohort unbound")
    tree = data("out/guest-tree-toolchain-admission/EVIDENCE.json", 7623,
                "8bcba6544bebab9e506958d4d5f0cb1647de45791ee32996fe1595cd894054cc")
    dev = data("out/guest-private-socket-view-plan/image-target/DIRECT-EXT4.json", 4371,
               "7878ece9efd32aea5b68e09fc97ae19cdef8d6d7f345ca6024ec6ebd2749e8b4")
    inode = [row for row in tree["image"]["selectedInodes"] if row["path"] == "/dev"]
    require(len(inode) == 1 and inode[0]["inode"] == dev["dev"]["inode"] == 24 and
            tree["image"]["knownAcquisitionSha256"] == dev["wholeImageSha256Inherited"] and
            dev["nonDotDevChildren"] == [] and tree["filesystemMounted"] is False,
            "Same donor image's empty /dev")
    cg = data("out/guest-zygote-cgroup-lifetime/ADMISSION.json", 4283,
              "bcbeb73b8267e499f2d8be740ad582bb4c56205f0f64218d7a8b343ce3cc9b29")
    cgroups = data(SYSTEM + "etc/cgroups.json", 804,
                   "a6903cbef1321281c74fe007b29161aad136837908b222c424f141d86d4d67bd")
    require(cgroups["Cgroups2"]["Path"] == "/sys/fs/cgroup" and
            cg["status"] == "ENTRY_BLOCKED_SCOPE_AND_MIGRATION_UNPROVED", "Cgroup scope stays held")
    read(SYSTEM + "etc/task_profiles.json", 29576,
         "a928742b8697cd78dece935dfc07238c5bbddde58764210e633c8332b95d5c1c")

    scripts = (
        ("guest_prepare.sh", 278725, "000d0a168d6d32ad08f6905df0b7424a241bb7029a8dc43c2fe292189d7a2d70",
         ((304, 'mount --rbind /sys'), (316, 'mount --rbind /dev'), (327, 'mount --rbind /linkerconfig'))),
        ("guest_props.sh", 63145, "f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a",
         ((102, 'getprop | awk'), (147, '(key in host)'), (702, '"$RP" -n -f "$NEW"'))),
        ("oneos_switch.sh", 228581, "e0433f913856b3fbe775ffc1768948a4581434111eab79a21df1f1c443809150",
         ((755, 'set_prop persist.sys.disable_rescue true'), (1149, 'guest_props.sh" add'),
          (1418, 'unshare -m'))),
        ("guest_start.sh", 78054, "896b72cc5bafadf975e29c05da0280e92b56a8f508c378d2c24e25a2b7f30446",
         ((116, '"$DERIVE" "$CLASSPATH_FILE"'), (123, "keeps the host's class paths"),
          (703, 'persist.sys.disable_rescue'), (704, 'persist.sys.enable_rescue'),
          (1239, 'export ONEOS_GUEST_JIT_ZYGOTE'), (1284, 'exec /data/zygote_exec'))),
        ("@init.zygote64.rc", 1634, "f87b7f19215b26aaae28b624d43ad4416cc2cc33a1b72ee2a5ad539172ba8b4e",
         ((1, "service zygote"), (23, "task_profiles"), (24, "zygote.critical_window.minute"))),
    )
    source_lines = {}
    for name, size, digest, checks in scripts:
        path = SYSTEM + "etc/init/hw/" + name[1:] if name.startswith("@") else SAVED + name
        lines = read(path, size, digest).splitlines()
        require(all(value.encode("ascii") in lines[line - 1] for line, value in checks),
                f"Source anchors: {path}")
        source_lines[path] = [line for line, _ in checks]

    declarations = {key: [] for key in sorted(
        {row["key"] for row in native} |
        {"ro.build.version.sdk", "ro.build.version.codename", "ro.build.version.preview_sdk",
         "ro.treble.enabled", "persist.sys.disable_rescue", "persist.sys.enable_rescue"})}
    for name, size, digest in PROP_INPUTS:
        raw = read(DONOR + "extracted/" + name, size, digest)
        for number, line in enumerate(raw.splitlines(), 1):
            match = re.fullmatch(rb"([a-zA-Z0-9._-]+)=(.*)", line)
            if match and (key := match[1].decode("ascii")) in declarations:
                declarations[key].append({"file": name, "line": number, "value": match[2].decode("ascii")})
    for key, expected in (("ro.build.version.sdk", "37"), ("ro.build.version.codename", "REL"),
                          ("ro.build.version.preview_sdk", "0")):
        rows = declarations[key]
        require([row["file"] for row in rows] == ["system/build.prop", "system/product/etc/build.prop"]
                and all(row["value"] == expected for row in rows)
                and rows[0]["line"] == cp["donorBuildPropDeclarations"][key]["line"]
                and cp["donorBuildPropDeclarations"][key]["value"] == expected,
                "Matched donor system and product classpath declarations")
    require(cp["legacyPropertyProducer"]["effectiveSdk"] is None and
            cp["legacyPropertyProducer"]["effectiveCodename"] is None,
            "Source declarations have no effective-property admission")
    return {
        "schema": "guest-tree-boot-properties/v1",
        "status": "HELD_ON_EFFECTIVE_PRIVATE_PROPERTY_VIEW",
        "pins": pins,
        "nativePropertyArea": {
            "path": "/dev/__properties__", "bionicInitPc": "0xc3ffc",
            "contextInitPc": "0xa4ddc", "originalDonorDevInode": 24, "nonDotDonorChildren": [],
            "requiredBefore": "First native process initialization of linkerconfig, derive or app_process in the selected view",
        },
        "actualConsumerReads": native,
        "deriveClasspath": {
            "sdkKey": "ro.build.version.sdk", "codenameKey": "ro.build.version.codename",
            "sdkGetterPc": "0xaf4b8", "sourceOnlyScenario": {"sdk": 37, "codename": "REL"},
        },
        "zygoteAndCgroup": {
            "packagedJitSelector": launcher["optionalJit"],
            "directLauncherVsInit": "The inspected launcher main uses getenv, not the init RC property substitution. Zygote's critical window and task_profiles directives belong to init's service route.",
            "androidRuntimeCgroupImportEdges": ["0x237d90", "0x130510"],
            "hold": "Cgroup config selection cannot establish migration confinement or replace real scope placement and drain. Full Zygote/ART property reachability is outside this slice.",
        },
        "savedOneOS": {
            "sourceLines": source_lines,
            "finding": "The legacy mount namespace imports host /dev, /sys and linkerconfig. The switch changes shared properties and the generic donor importer skips keys already defined on the host. The preserved rescue gate needs genuine safety ownership, not a manufactured property value.",
        },
        "declarationsInElevenPinnedFiles": declarations,
        "missing": [
            "Actual private property area, context mapping and read access tied to the same retained tree and namespace, present before process initialization",
            "Source-owned effective values or observed absence for the selected consumers, with vendor and product config identity",
            "Generated linker output, complete classpath view, cgroup migration confinement and the still-closed rescue policy path",
        ],
        "effectiveProperties": None,
        "runtimeExports": None,
        "entryAdmitted": False,
        "hostFallbackUsed": False,
        "propertyWrites": False,
        "targetExecuted": False,
        "toolSha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--stage", action="store_true")
    actions.add_argument("--verify", action="store_true")
    actions.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        receipt = derive()
        if args.require_ready:
            require(receipt["entryAdmitted"], "The held inputs do not admit an effective private property view")
        raw = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
        for folder in (OUT.parent.parent, OUT.parent):
            if args.stage:
                folder.mkdir(exist_ok=True)
            info = folder.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain output directory")
        if args.stage:
            with OUT.open("xb") as stream:
                stream.write(raw)
        require(read_held(OUT, len(raw)) == raw, "Exact saved receipt")
    except (KeyError, IndexError, ValueError, OSError) as exc:
        parser.exit(2, f"Refused: {exc}\n")
    print(f"{OUT.relative_to(ROOT).as_posix()} {len(raw)} bytes SHA-256 {sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
