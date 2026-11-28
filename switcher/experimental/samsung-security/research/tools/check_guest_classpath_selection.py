"""Check the default relative scan order of five held donor classpath fragments."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-classpath-selection/receipt.json"
UPSTREAM = "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a"
SWITCH = UPSTREAM + "/raw/45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/"
CAPTURE = "firmware/samsung-boot-classpath-cohort/"
DONOR = "../firmware/donor/"
BOOT_SUFFIX = "/etc/classpaths/bootclasspath.pb"
SERVER_SUFFIX = "/etc/classpaths/systemserverclasspath.pb"
BOOT = ("BOOTCLASSPATH", "DEX2OATBOOTCLASSPATH")
SERVER = ("SYSTEMSERVERCLASSPATH", "STANDALONE_SYSTEMSERVER_JARS")
ENUM = dict(zip(BOOT + SERVER, (1, 3, 2, 4)))
PATTERNS = (
    (BOOT, ("/apex/com.android.art", "/system", "/apex/*"), BOOT_SUFFIX),
    (SERVER, ("/system", "/apex/*"), SERVER_SUFFIX),
)
EXPECTED_ORDER = (
    ("/apex/com.android.art", "/system", "/apex/com.android.sdkext"),
    ("/system", "/apex/com.android.art"),
)


def require(condition, label):
    if not condition:
        raise ValueError(label)


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def read_held(path, limit):
    first = path.lstat()
    require(plain(first) and stat.S_ISREG(first.st_mode) and 0 < first.st_size <= limit,
            f"Bounded plain input required: {path}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(identity(opened) == identity(first), "Input changed on open")
        raw = stream.read(limit + 1)
        final_fd = os.fstat(stream.fileno())
        require(len(raw) == first.st_size and identity(final_fd) == identity(opened) and
                final_fd.st_ctime_ns == opened.st_ctime_ns, "Input changed during read")
    final_path = path.lstat()
    require(plain(final_path) and identity(final_path) == identity(first) and
            final_path.st_ctime_ns == first.st_ctime_ns, "Input path changed during read")
    return raw


def check_native(producer, proof, libc, cohort):
    require(sha256(producer).hexdigest() == proof["sourceSha256"] ==
            cohort["sameByteDonorDeriveClasspath"]["sha256"], "Exact donor-matching producer")
    instructions = {}
    require(len(proof["functions"]) == 5, "Held native function scope")
    for fn in proof["functions"]:
        code = producer[fn["fileOffset"]:fn["fileOffset"] + fn["bytes"]]
        require(sha256(code).hexdigest() == fn["sha256"] and
                code == b"".join(bytes.fromhex(row["bytes"]) for row in fn["instructions"]),
                "Disassembly matches the producer bytes")
        instructions.update({row["pc"]: row for row in fn["instructions"]})
    # The patterns below are strings recovered from these exact construction branches.
    # glob result iteration does not give a cross-module order in a different /apex view.
    anchors = {
        0x471F0: ("b.eq", "#0x47440"),       # default boot vector
        0x4731C: ("b.eq", "#0x47484"),       # default server vector
        0x47508: ("add", "x8, x8, #0x4da"), # /apex/com.android.art
        0x475A0: ("cbz", "x8, #0x47618"),   # no single system boot override
        0x47498: ("cbz", "x8, #0x475cc"),   # no single system server override
        0x479D0: ("str", "w10, [x11]"),    # boot /system prefix
        0x47720: ("str", "w9, [x11]"),     # server /system prefix
        0x47AD4: ("str", "w10, [x11]"),    # boot /apex/* prefix
        0x47888: ("str", "w9, [x11]"),     # server /apex/* prefix
        0x47BCC: ("add", "x12, x12, #0x18"),
        0x47CC8: ("mov", "w1, #8"),
        0x47D40: ("ldr", "x19, [x8, x21, lsl #3]"),
        0x47ED4: ("tbz", "w26, #0, #0x47ef4"), # skip numeric @version
        0x47F68: ("b", "#0x47ed8"),           # skip repeated fragment path
        0x481D4: ("add", "x22, x22, #0x18"),
        0x48510: ("add", "x20, x20, #8"),
        0x48C70: ("str", "x0, [x27, #0x20]"), # append selected enum vector
        0x48658: ("b.eq", "#0x4867c"),        # REL min
        0x486D4: ("b.lt", "#0x484f8"),        # reject SDK below min
        0x48718: ("cbz", "x9, #0x48900"),     # no max
        0x48828: ("b.eq", "#0x48874"),        # REL max
        0x48AF4: ("b.le", "#0x48900"),        # accept SDK at or below max
        0x491EC: ("mov", "w2, #1"),
        0x4920C: ("mov", "w2, wzr"),
    }
    for pc, expected in anchors.items():
        row = instructions[pc]
        require((row["mnemonic"], row["operands"]) == expected, f"Native anchor at {pc:#x}")
    for pc, name in ((0x47CE0, "glob"), (0x48640, "__system_property_get"),
                     (0x48810, "__system_property_get"), (0x4868C, "android_get_device_api_level"),
                     (0x48AB0, "android_get_device_api_level"), (0x486AC, "strtol"), (0x48AD0, "strtol")):
        require(instructions[pc]["targetSymbol"] == name, f"Native call at {pc:#x}")
    for offset, value in ((0x44DA, "/apex/com.android.art"), (0x44C6, "/apex/[^/]+@[0-9]+/"),
                          (0x39A7, BOOT_SUFFIX), (0x3142, SERVER_SUFFIX),
                          (0x3600, "ro.build.version.codename")):
        require(producer.startswith(value.encode("ascii") + b"\0", offset), "Exact native literal")
    # Donor bionic android_get_device_api_level uses ADR x0 to the key and calls
    # __system_property_get at 0xaf4f8, then atoi and the positive-value guard.
    adr = int.from_bytes(libc[0xAF4D8:0xAF4DC], "little")
    require(adr & 0x9F00001F == 0x10000000, "Bionic property key ADR")
    displacement = ((adr >> 5 & 0x7FFFF) << 2) | (adr >> 29 & 3)
    key_offset = 0xAF4D8 + displacement - (1 << 21 if displacement & (1 << 20) else 0)
    require(key_offset == 0x23454 and libc.startswith(b"ro.build.version.sdk\0", key_offset) and
            sha256(libc[0xAF4B8:0xAF544]).hexdigest() ==
            "0785843c33daabdd4532c1dddfcc26fe5ac50a69d106d1b77fc8963318fdd5bd",
            "Exact donor bionic SDK query span")
    return {
        "relativeOrderAnchors": [hex(pc) for pc in anchors],
        "codenameGetPc": ["0x48640", "0x48810"],
        "sdkQueriesPc": ["0x491d0", "0x4868c", "0x48ab0"],
        "bionicSdkFunctionPc": "0xaf4b8", "bionicPropertyGetPc": "0xaf4f8",
        "bionicSdkKeyFileOffset": hex(key_offset),
        "qualifierSemantics": "In the REL decimal subset, nonempty min and max are inclusive.",
        "globSemantics": "Within each pattern visit returned paths in order. Skip numeric version aliases and exact repeated fragment paths.",
    }


def bound(value):
    if value == "":
        return None
    require(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,9}", value) and
            int(value) <= 0x7FFFFFFF, "Positive canonical decimal SDK bound required")
    return int(value)


def filter_row(entry, sdk):
    low, high = (bound(entry[key]) for key in ("minSdkRaw", "maxSdkRaw"))
    require(low is None or high is None or low <= high, "Inverted SDK bounds")
    if low is not None and sdk < low:
        return "BELOW_MIN"
    if high is not None and sdk > high:
        return "ABOVE_MAX"
    return "INCLUDED"


def select(cohort, module_names, sdk, codename):
    require(type(sdk) is int and 0 < sdk <= 0x7FFFFFFF and codename == "REL",
            "Only a numeric REL scenario is supported")
    fragments = {row["path"]: row for row in cohort["fragments"]}
    require(len(fragments) == len(cohort["fragments"]) == 5, "Exact five unique fragment paths")
    ordered = {}
    included, excluded = ({key: [] for key in ENUM} for _ in range(2))
    used = set()
    for (keys, patterns, suffix), expected_roots in zip(PATTERNS, EXPECTED_ORDER):
        visited = []
        for pattern in patterns:
            if pattern == "/apex/*":
                matches = [f"/apex/{module}{suffix}" for module in module_names]
            else:
                matches = [pattern + suffix]
            unseen = [path for path in matches if path in fragments and path not in used]
            require(len(unseen) <= 1, "This subset cannot establish order between multiple wildcard matches")
            for path in unseen:
                row = fragments[path]
                used.add(path)
                visited.append(path)
                require(set(row["orderedGroups"]) == set(keys), "Exact fragment category scope")
                for key, rows in row["orderedGroups"].items():
                    ordinals = [entry["ordinal"] for entry in rows]
                    require(ordinals == sorted(set(ordinals)), "Per-category protobuf order")
                    for entry in rows:
                        jar = entry["path"]
                        require(entry["classpathRaw"] == ENUM[key] and jar in cohort["heldJarObjects"],
                                "Exact held JAR membership")
                        result = filter_row(entry, sdk)
                        item = {"fragment": path, "result": result, **entry}
                        (included if result == "INCLUDED" else excluded)[key].append(item)
        require(visited == [root + suffix for root in expected_roots], "Exact held fragment order")
        ordered[suffix.rsplit("/", 1)[1]] = visited
    require(used == set(fragments), "All held fragments accounted for")
    counts = {key: len(included[key]) for key in ENUM}
    require({key: counts[key] + len(excluded[key]) for key in ENUM} == cohort["declaredEntryCounts"],
            "No held entry omitted from the audit")
    return {"sdk": sdk, "codename": codename, "counts": counts, "relativeFragmentOrder": ordered,
            "includedRows": included, "excludedRows": excluded}


def derive():
    inputs = {}

    def read(name, size, digest):
        data = read_held(ROOT / name, size)
        require(len(data) == size and sha256(data).hexdigest() == digest, f"Exact input {name}")
        inputs[name] = {"bytes": size, "sha256": digest}
        return data

    cohort = json.loads(read("out/guest-classpath-inputs/receipt.json", 28361,
        "9f4a847728ece4f2b31652497991eda4d59fe1559b88feeafefd0396fcaba7a4"))
    apex = json.loads(read("out/guest-apex-active-inputs/r-27f937479ad7483a893a399d6f8b94eb/receipt.json",
        7782, "8bdfef9391822e16b566943c11e2210f81cf4adbbc53faa8b37b6fd7060340b5"))
    require(cohort["complete"] is False and cohort["exportedEnvironment"] is None and
            apex["requiredModuleSetClosed"] is False and apex["runtimeApexInfoList"] is None,
            "Both inputs are incomplete static candidates")
    candidates = {row["moduleName"]: row for row in apex["candidates"]}
    require(len(candidates) == len(apex["candidates"]) == 4 and
            set(candidates) == set(cohort["heldModuleCandidates"]), "Same four candidate modules")
    for module, candidate in candidates.items():
        held = cohort["heldModuleCandidates"][module]
        require(candidate["payloadSha256"] == held["payloadSha256"] and
                str(held["version"]) == candidate["versionCode"] and
                candidate["proposedMountTarget"] == held["target"] == f"/apex/{module}",
                "Candidate payload, version and alias identity")

    producer = read(CAPTURE + "captured/apex/com.android.sdkext/bin/derive_classpath", 562896,
        "015e20a3dba724c2dae7ff8015bc50658f6f1a89e329e620200504568d7a0f2e")
    proof = json.loads(read(CAPTURE + "producer-native.json", 685302,
        "a9da108c3b8b28f66145f88e3ff59f863d9606904be2178a724f665b2b2dd935"))
    libc = read(DONOR + "apex/005-com.android.runtime/files/lib64/bionic/libc.so", 1550096,
        "c9057b270a62b45b0dcae87e5d6a187a2dde1e7f86f8a2e0d68f2eb180e57d99")
    evidence = check_native(producer, proof, libc, cohort)
    prop = read(DONOR + "extracted/system/build.prop", 28816,
        "4661edb3c8e09ac75af0bd19a0c48fecba86511f3d6bec383c0db4bd31709582")
    declarations = {}
    for key in ("ro.build.version.sdk", "ro.build.version.codename", "ro.build.version.preview_sdk"):
        prefix = key.encode("ascii") + b"="
        rows = [(i, row[len(prefix):].decode("ascii")) for i, row in enumerate(prop.splitlines(), 1)
                if row.startswith(prefix)]
        require(len(rows) == 1, "Unique donor build.prop declaration")
        declarations[key] = dict(zip(("line", "value"), rows[0]))
    require([row["value"] for row in declarations.values()] == ["37", "REL", "0"],
            "Held donor release scenario")
    script_checks = (
        ("guest_prepare.sh", 285232, "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d",
         ((323, b'mount --rbind /dev "$ROOTFS/dev"'),)),
        ("guest_props.sh", 66429, "4b1c78ae7682e74d12a50bab955b0e36373a7ece3fc447f1e55098e756bc625e",
         ((102, b"getprop | awk"), (147, b"(key in host)"),
          (748, b'"$RP" -n -f "$NEW"'), (754, b'"$RP" -n "${line%%=*}"'))),
        ("oneos_switch.sh", 240947, "b80fe03b0ccd43ae874a43e38aa58d832a3eaf70106819f0eb9d475df77ab6ab",
         ((1265, b'guest_props.sh" add "$STAGE/rootfs"'), (1534, b'unshare -m'))),
        ("guest_start.sh", 78563, "81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2",
         ((113, b"DERIVE=/apex/com.android.sdkext/bin/derive_classpath"),
          (116, b'"$DERIVE" "$CLASSPATH_FILE"'), (123, b"keeps the host's class paths"))),
    )
    source_lines = {}
    for name, size, digest, anchors in script_checks:
        lines = read(SWITCH + name, size, digest).splitlines()
        require(all(literal in lines[line - 1] for line, literal in anchors), "Exact legacy property source")
        source_lines[name] = [line for line, _ in anchors]

    donor = select(cohort, candidates, bound(declarations["ro.build.version.sdk"]["value"]), "REL")
    sdk36 = select(cohort, candidates, 36, "REL")
    expected_cut = {f"/system/framework/framework-{name}.jar" for name in
                    ("graphics", "location", "ondeviceintelligence-platform", "telecom")}
    require(donor["counts"] == dict(zip(BOOT + SERVER, (24, 23, 5, 0))) and
            sdk36["counts"] == dict(zip(BOOT + SERVER, (20, 19, 5, 0))) and
            all({row["path"] for row in sdk36["excludedRows"][key]} == expected_cut for key in BOOT),
            "Exact donor declaration result and below-min comparison")
    return {
        "schema": "guest-classpath-selection/v1",
        "status": "VERIFIED_RELATIVE_ORDER_AND_RELEASE_SCENARIO_ONLY",
        "toolSha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs": inputs,
        "sameByteDonorDeriveClasspath": cohort["sameByteDonorDeriveClasspath"],
        "nativeEvidence": evidence,
        "defaultScanPatterns": {suffix.rsplit("/", 1)[1]: [pattern + suffix for pattern in patterns]
                                for _, patterns, suffix in PATTERNS},
        "apexCandidates": list(candidates.values()),
        "legacyPropertyProducer": {
            "sourceLines": source_lines,
            "finding": "Legacy prepare binds the shared /dev. Before launch the switch calls guest_props add. It excludes nonempty host keys from generic donor additions and writes additions with resetprop. Derive reads effective properties after pivot, with no scan or SDK override.",
            "nativePrivatePropertyView": None,
            "effectiveSdk": None,
            "effectiveCodename": None,
        },
        "donorBuildPropDeclarations": declarations,
        "donorDeclarationScenario": donor,
        "counterfactualSdk36Scenario": sdk36,
        "unresolved": ["complete default scan in the owned guest partition and active APEX view",
                       "effective process property view and provenance at derive invocation",
                       "mounted JAR identities, selected overlays and complete standalone group"],
        "runtimeClasspath": None,
        "exportedEnvironment": None,
        "hostFallbackUsed": False,
        "targetExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--stage", action="store_true")
    actions.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        raw = (json.dumps(derive(), indent=2) + "\n").encode()
        for folder in (OUT.parent.parent, OUT.parent):
            if args.stage:
                folder.mkdir(exist_ok=True)
            info = folder.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain output directory")
        if args.stage:
            with OUT.open("xb") as output:
                output.write(raw)
        require(read_held(OUT, len(raw)) == raw, "Exact saved selection receipt")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Refused: {exc}\n")
    print(f"{OUT.relative_to(ROOT).as_posix()} {len(raw)} bytes SHA-256 {sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
