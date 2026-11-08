"""Check the fixed saved ColorOS cgroup path cohort. Output is always disabled."""

import hashlib
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DONOR = "../firmware/donor/extracted/system/"
PINS = {
    "priorNoGo": ("out/guest-cgroup-private-view/FINDINGS.json", 17157,
                  "11110ef64cc246cbe810bd72053cd7fb9ee8038c2fd96a666298a2c73061d638"),
    "hostMountinfo": ("firmware/read-only-resume-20261106/mountinfo.stdout", 80533,
                      "f696e0bd403d60c5ca7a0641b6df5deb96c027d9cd35e4ec78eb710915a7f157"),
    "baseCgroups": (DONOR + "etc/cgroups.json", 804,
                    "a6903cbef1321281c74fe007b29161aad136837908b222c424f141d86d4d67bd"),
    "baseProfiles": (DONOR + "etc/task_profiles.json", 29576,
                     "a928742b8697cd78dece935dfc07238c5bbddde58764210e633c8332b95d5c1c"),
    "systemProperties": (DONOR + "build.prop", 28816,
                         "4661edb3c8e09ac75af0bd19a0c48fecba86511f3d6bec383c0db4bd31709582"),
    "systemExtProperties": (DONOR + "system_ext/etc/build.prop", 8085,
                            "76108b9c2cd1d9c2058e9e0df4ff1d1074d94bac3c75e68fab3b693afe2a534b"),
    "runtime": (DONOR + "lib64/libandroid_runtime.so", 3138824,
                "edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279"),
    "processgroup": (DONOR + "lib64/libprocessgroup.so", 400256,
                     "376d8be528e3003457299a052b592dfed9dfea84c1cf8021d0b7cae61d76bd01"),
    "utils": (DONOR + "lib64/libutils.so", 168872,
              "f142848b2eddd8090c28771f708aa055da5f5204bf5cb986562a2f76abbadaa6"),
    "zygoteJava": ("firmware/retained-pin-guest-delivery/20261106T170656324425Z-7bd17964edaf4e7c9182c376dbe83a63/selected.jsonl", 45485,
                   "89ee61a7c316df42927d14a7ac2e7560d20a0f38ba51457c3dd1684bf90f27a1"),
    "systemServerJava": ("firmware/construction-startup/20261105T144235058123Z-c0248b12b8364dc3af57d59b8e8f69ca.jsonl", 633939,
                         "a96a83a43985d6533b62aa18f3f171cd6a85f9f7ad876f6a8bc592e1adbfdca1"),
}

NATIVE = (
    ("runtime", "nativeForkSystemServer", 0x27f804, 648, "6e8279890d13882f14bba0c6b4d5e15d410eefabfe448d162c7d32df46b33c0f"),
    ("runtime", "SpecializeCommon", 0x12df88, 19828, "54f9f118b2e980c0b4802786c26a234d7229d2a0800a9fbd5475b0a0111349ef"),
    ("runtime", "setThreadPriorityNative", 0x185024, 136, "0a70347a9c7e0437ed6f387cc65bf919838d2a9db84c8c341e413982a6532def"),
    ("runtime", "setCgroupProcsProcessGroup", 0x2378fc, 728, "4e1462734a4d9614858e80aeefdebe4d4d45565662ad0fc318168d5fb62821f1"),
    ("processgroup", "createProcessGroupDup", 0x30ae4, 1284, "d9510ec86ba6e514816cd97885e844f3d8be570032a12910ce212f6a6603e79f"),
    ("processgroup", "createProcessGroupInternal", 0x30578, 1388, "ee68cf85a362a7c89e09e66cbaf9735e28ddc249b8700ff3bef72ced4de026d2"),
    ("processgroup", "ConvertUidPidToPath", 0x3463c, 188, "edd14a59765766ac68ada3c621960ad5a7da749f6da9253d82a555e9f597c2d0"),
    ("processgroup", "ReadDescriptors", 0x3dc58, 2264, "e2433fc7f3700cf261762772421e930183b3608cb9bc95341219bdb606217f89"),
    ("processgroup", "TaskProfiles constructor", 0x38c9c, 1364, "663e000f1a5d98227919a6f04d1fce4063044ea159e499875f60800f577901f4"),
    ("processgroup", "ExecuteForTask", 0x35f64, 636, "58bfffa79c973b7f3fdd778184fad7fd5d4f4cf00541e2b30f626725df76679a"),
    ("processgroup", "AddTidToCgroup", 0x35790, 656, "b48fa7604d73327a7b0eeffbdb0386737407fe2f699575236692e4b47df44691"),
    ("processgroup", "GetTasksFilePath", 0x20ba0, 976, "14166fad7f9c21ed914c91e92b1b8f66490dbff94496a510457d6ddcbbf2097f"),
    ("processgroup", "UsePerAppMemcg", 0x2cd38, 208, "9151e56e666d751b09940a481b8ac230d2475a335ac7b79bb1da452ecae5ff72"),
    ("utils", "androidSetThreadPriority", 0x1b600, 68, "8ec7700c44865d3694dd66861db12c52f85c7cbf184ce975ad509ae815110c05"),
)


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_inputs():
    result = {}
    for role, (path, length, digest) in PINS.items():
        with (ROOT / path).open("rb") as stream:
            data = stream.read(length + 1)
        require(len(data) == length and sha(data) == digest, f"Profile drift: {role}")
        result[role] = data
    return result


def executable_span(data, address, length):
    require(data[:7] == b"\x7fELF\x02\x01\x01"
            and struct.unpack_from("<HH", data, 16) == (3, 183), "Wrong AArch64 ELF profile")
    phoff, = struct.unpack_from("<Q", data, 32)
    size, count = struct.unpack_from("<HH", data, 54)
    require(size == 56 and 0 < count <= 64 and phoff + size * count <= len(data),
            "ELF program-header bounds")
    ranges = [struct.unpack_from("<IIQQQQQQ", data, phoff + i * size) for i in range(count)]
    row, = (row for row in ranges if row[0] == 1 and row[1] == 5
        and row[3] <= address and address + length <= row[3] + row[5]
    )
    _, _, offset, base, _, file_size, _, _ = row
    require(offset + file_size <= len(data), "ELF executable file extent")
    start = offset + address - base
    return data[start:start + length]


def selected_method(data, body_sha):
    records = [json.loads(line, object_pairs_hook=unique_keys) for line in data.splitlines()]
    record, = (row for row in records if row.get("normalizedBodySha256") == body_sha)
    return {row["pc"]: row.get("reference") for row in record["body"]["instructions"]}


def main():
    require(len(sys.argv) == 1, "This check accepts no override or emission arguments")
    data = read_inputs()
    no_go = json.loads(data["priorNoGo"], object_pairs_hook=unique_keys)
    require(no_go["verdict"] == "NO_GO_CURRENT_COHORT_SUBTREE_VIEW_IS_NOT_MIGRATION_FENCE",
            "Prior no-go profile drift")
    cgroups = json.loads(data["baseCgroups"], object_pairs_hook=unique_keys)
    v1 = {row["Controller"]: row["Path"] for row in cgroups["Cgroups"]}
    require(len(cgroups["Cgroups"]) == len(v1) == 4
            and v1 == {"blkio": "/dev/blkio", "cpu": "/dev/cpuctl",
                       "cpuset": "/dev/cpuset", "memory": "/dev/memcg"}, "Legacy controller profile")
    v2 = cgroups["Cgroups2"]
    require(v2["Path"] == "/sys/fs/cgroup" and v2["Controllers"] ==
            [{"Controller": "freezer", "Path": "."}], "Unified controller profile")
    profiles = json.loads(data["baseProfiles"], object_pairs_hook=unique_keys)
    joins = {}
    for name, controller, path in (("SystemMemoryProcess", "memory", "system"),
                                   ("ProcessCapacityHigh", "cpuset", "foreground"),
                                   ("MaxPerformance", "cpu", "top-app"),
                                   ("NormalIoPriority", "blkio", "")):
        row, = (value for value in profiles["Profiles"] if value["Name"] == name)
        action, = (item for item in row["Actions"] if item["Name"] == "JoinCgroup")
        require(action["Params"] == {"Controller": controller, "Path": path}, name)
        joins[name] = v1[controller] + ("/" + path if path else "")
    require(b"\nro.oplus.osense_app_memcg=true\n" in data["systemProperties"]
            and b"\npersist.sys.oplus.hybridswap_app_memcg=true\n" in data["systemExtProperties"],
            "Held donor property literals drift")
    mounts = {}
    for raw in data["hostMountinfo"].splitlines():
        left, right = raw.split(b" - ", 1)
        kind, _, options = right.split()
        if kind in (b"cgroup", b"cgroup2"):
            target = left.split()[4].decode("ascii")
            require(target not in mounts, "Duplicate selected mount path")
            mounts[target] = {"kind": kind.decode("ascii"), "superOptions": options.decode("ascii")}
    require(set(mounts) == {"/sys/fs/cgroup", "/dev/cpuset", "/dev/cpuctl",
                            "/dev/acct", "/dev/blkio", "/dev/freezer"}
            and mounts["/sys/fs/cgroup"]["superOptions"] == "rw,memory_recursiveprot",
            "Held host mount profile drift")
    native = []
    for role, name, address, size, digest in NATIVE:
        require(sha(executable_span(data[role], address, size)) == digest, f"Native span drift: {name}")
        native.append({"role": role, "function": name, "va": hex(address), "bytes": size, "sha256": digest})
    zygote = selected_method(data["zygoteJava"], "ee7bb552ef640cb38963019ad3601218c897f4f42b8fabd4e7597ba8a90b21f3")
    server = selected_method(data["systemServerJava"], "1abb4e36b8ad3f43b42b19b8e8d36458ad06979c77d76c14c2430c8a8f47e660")
    require(zygote[137] == "string=--setuid=1000" and zygote[139] == "string=--setgid=1000"
            and "Zygote;->forkSystemServer" in zygote[351], "Zygote child request drift")
    require(server[611] == "Landroid/os/Process;->setThreadPriority(I)V", "SystemServer source drift")
    print(json.dumps({
        "schema": "guest-cgroup-path-profile/v1",
        "status": "MATCHED_SAVED_DISABLED_PROFILE",
        "entryEnabled": False,
        "writesAuthorized": False,
        "inputPins": {role: {"path": path, "bytes": size, "sha256": digest}
                      for role, (path, size, digest) in PINS.items()},
        "nativeBodyPins": native,
        "versionSelector": "ro.product.first_api_level",
        "configPathsInReadOrder": {
            "controllers": ["/etc/cgroups.json", "/etc/task_profiles/cgroups_%u.json",
                            "/vendor/etc/cgroups.json", "/proc/mounts (v1 mount discovery)"],
            "profiles": ["/etc/task_profiles.json", "/etc/task_profiles/task_profiles_%u.json",
                         "/vendor/etc/task_profiles.json", "/system_ext/etc/task_profiles.json"],
        },
        "baseV1JoinDirectories": joins,
        "baseV2Root": v2["Path"],
        "baseV2SystemServerGroupPath": "/sys/fs/cgroup/system/uid_1000/pid_<actual>/cgroup.procs",
        "heldHostMounts": mounts,
        "heldDonorPropertiesOnly": ["ro.oplus.osense_app_memcg=true",
                                    "persist.sys.oplus.hybridswap_app_memcg=true"],
        "missing": ["Actual guest root/config resolution and first-API/override/property cohort",
                    "Actual same-scope cgroup writers with no reachable writable host hierarchy",
                    "Controller/profile and hard-coded path compatibility, migration and drain ownership"],
    }, indent=2))


if __name__ == "__main__":
    main()
