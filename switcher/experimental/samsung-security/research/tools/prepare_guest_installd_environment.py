"""Verify fixed installd path inputs against captured source and emit JSON."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = "firmware/guest-entry-exec-profile/zygote_exec"
DONOR = "../firmware/donor/tree/init.environ.rc"
SAMSUNG = "firmware/guest-native-launch-profile/static/system__etc__init__hw__init.rc"
INDEX = (
    "../out/os-comparison-resumed/manifest-diff/"
    "20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz"
)
READS = "inventory/guest-native-launch-profile.json"
PREPARE = (
    "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/raw/"
    "45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/guest_prepare.sh"
)
HEADER = "compat/native/guest_installd_environment.h"
PINS = {
    LAUNCHER: "d8096b25e63764072a8790a3a9c76c92158418923fc25a409e727feb1261e635",
    DONOR: "84085163a12f27c76724173ce3491825deafe1e13a7af7bf0fd6e793378f3774",
    SAMSUNG: "94a786990f73b176d8d31a2cdeb8f7d6daab65e7ba766d5214df44d29e7a92bb",
    INDEX: "6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a",
    READS: "0e6980ecdad5877f74360cb76b900bf853970bbfc09b71265b2929104aa6bc72",
    PREPARE: "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d",
}
PAIRS = (0x2DB370, 0x2DB380, 0x2DB420)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_pairs(blob):
    require(
        blob[:7] == b"\x7fELF\x02\x01\x01"
        and struct.unpack_from("<HH", blob, 16) == (2, 183),
        "Packaged launcher must be ELF64 LE AArch64 ET_EXEC",
    )
    phoff, = struct.unpack_from("<Q", blob, 32)
    entsize, count = struct.unpack_from("<HH", blob, 54)
    require(entsize == 56 and 0 < count <= 16 and phoff + count * entsize <= len(blob),
            "Launcher program table bounds")
    programs = [
        struct.unpack_from("<IIQQQQQQ", blob, phoff + i * entsize)
        for i in range(count)
    ]

    def at(va, size):
        ranges = [
            off + va - start
            for kind, _, off, start, _, filesz, _, _ in programs
            if kind == 1 and start <= va and va + size <= start + filesz
        ]
        require(len(ranges) == 1 and ranges[0] + size <= len(blob), "File-backed launcher range")
        return blob[ranges[0]:ranges[0] + size]

    def string(va):
        value, separator, _ = at(va, 32).partition(b"\0")
        require(value and separator, "Bounded launcher literal")
        return value.decode("ascii")

    return [
        tuple(string(ptr) for ptr in struct.unpack("<QQ", at(pair, 16)))
        for pair in PAIRS
    ]


def audit():
    inputs = {name: (ROOT / name).read_bytes() for name in PINS}
    for name, digest in PINS.items():
        require(hashlib.sha256(inputs[name]).hexdigest() == digest, f"Input digest differs: {name}")

    pairs = source_pairs(inputs[LAUNCHER])
    reads = json.loads(inputs[READS])["requiredSelectedEnvironmentReads"]
    names = {name for name, _ in pairs}
    require(len(names) == 3 and names == {read["name"] for read in reads},
            "Each selected Samsung environment read must have one launcher value")
    require(all(value.startswith("/") for _, value in pairs), "Absolute launcher paths")

    donor = inputs[DONOR].decode("utf-8").splitlines()
    donor_exports = []
    for number, line in enumerate(donor, 1):
        words = line.split()
        if len(words) >= 2 and words[0] == "export" and words[1] in names:
            donor_exports.append((number, words[1:]))
    require([tuple(fields) for _, fields in donor_exports] == pairs,
            "ColorOS donor early-init exports must match the exact launcher values")
    require(donor[1] == "on early-init" and all(line < 20 for line, _ in donor_exports),
            "ColorOS source action scope")

    samsung = inputs[SAMSUNG].decode("utf-8").splitlines()
    require(samsung[6] == "import /init.environ.rc"
            and samsung[324].split() == ["mkdir", "/mnt/asec", "0755", "root", "system"],
            "Samsung environment import and ASEC directory source")
    index = [json.loads(line)["path"] for line in gzip.decompress(inputs[INDEX]).splitlines()]
    require(not any(path.rsplit("/", 1)[-1] == "init.environ.rc" for path in index),
            "Samsung index now contains an environment member requiring separate review")
    prepare = inputs[PREPARE].decode("utf-8").splitlines()
    require(prepare[1230] == 'if mount | grep -q "$ROOTFS/mnt " || $BB mount --rbind /mnt "$ROOTFS/mnt"; then',
            "Held OneOS prepare host-mnt import")

    header = (ROOT / HEADER).read_bytes()
    lines = header.decode("ascii").splitlines()
    env = [f"{name}={value}" for name, value in pairs]
    start = lines.index("#define ONEOS_GUEST_INSTALLD_PATH_ENVIRONMENT { " + chr(92))
    expected = [f'    "{entry}", ' + chr(92) for entry in env] + ["    NULL " + chr(92), "}"]
    require(lines[start + 1:start + 1 + len(expected)] == expected, "C initializer source readback")

    return {
        "schema": "guest-installd-path-environment/v1",
        "status": "VERIFIED_FIXED_PATH_INPUTS_UNSELECTED",
        "environment": env,
        "inputs": {name: {"sha256": digest, "bytes": len(inputs[name])}
                   for name, digest in PINS.items()},
        "provider": {"path": HEADER, "sha256": hashlib.sha256(header).hexdigest(),
                     "bytes": len(header), "nullTerminatedInitializer": True},
        "launcherPairAddresses": [hex(pair) for pair in PAIRS],
        "donorExportLines": [line for line, _ in donor_exports],
        "samsungSelectedReads": reads,
        "samsungEnvironmentImportLine": 7,
        "samsungAsecMkdirLine": 325,
        "samsungEnvironmentFileFoundInIndex": False,
        "oneosHostMntImportLine": 1231,
        "nativeProfileSelected": False,
        "runtimeExecuted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(audit(), indent=2))


if __name__ == "__main__":
    main()
