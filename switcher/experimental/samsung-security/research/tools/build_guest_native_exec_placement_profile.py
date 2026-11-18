"""Emit the bounded early native placement pins from the reviewed ELF demand receipt."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEMAND = ROOT / "out/guest-exec-mount-demand-ce69fa4f/receipt.json"
DEMAND_SHA256 = "ce69fa4f536ef35f920265970f06578a25eab9d0e14d51014617146f90a39b7d"
PARENTS = {
    "/system/bin": ("GNX_SYSTEM_BIN", "carrierSystem"),
    "/system/bin/bootstrap": ("GNX_SYSTEM_BOOTSTRAP_BIN", "carrierSystem"),
    "/system/lib64": ("GNX_SYSTEM_LIB64", "carrierSystem"),
    "/system/lib64/bootstrap": ("GNX_SYSTEM_BOOTSTRAP_LIB64", "carrierSystem"),
    "/apex/com.android.runtime/bin": ("GNX_RUNTIME_BIN", "runtimeApex"),
    "/apex/com.android.runtime/lib64/bionic": ("GNX_RUNTIME_BIONIC", "runtimeApex"),
}
PHASES = (
    ("apexdBootstrap", "gnx_bootstrap_files", "/system/bin/apexd", "/system/bin/bootstrap/linker64",
     {"carrierSystem": 33}),
    ("linkerconfig", "gnx_linkerconfig_files", "/apex/com.android.runtime/bin/linkerconfig",
     "/apex/com.android.runtime/bin/linker64", {"carrierSystem": 3, "runtimeApex": 5}),
)


def phase_pins(demand, phase, entry, interpreter, counts):
    record = demand["phases"][phase]
    libraries = record["libraries"]
    if (record["entry"] != entry or record["interpreter"] != interpreter
            or libraries != sorted(set(libraries)) or record["executableFilesByMountRole"] != counts):
        raise ValueError(f"Unexpected phase roster {phase}")
    paths = [entry, interpreter, *libraries]
    if len(paths) != sum(counts.values()) or len(set(paths)) != len(paths):
        raise ValueError(f"Duplicate or missing object in {phase}")

    rows = []
    observed = Counter()
    for name in paths:
        path = PurePosixPath(name)
        parent, role = PARENTS[str(path.parent)]
        item = demand["objects"][name]
        size, digest = item["bytes"], item["sha256"]
        if (str(path) != name or not re.fullmatch(r"[A-Za-z0-9_.+\-]+", path.name)
                or item["mountRole"] != role or not 0 < size <= 16 * 1024**2
                or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError(f"Unexpected executable object {name}")
        loads = item["executableLoads"]
        if not loads or any(not load["flags"] & 1 or load["fileBytes"] <= 0
                            or load["fileOffset"] < 0 or load["fileOffset"] + load["fileBytes"] > size
                            for load in loads):
            raise ValueError(f"Unexpected file-backed executable segment {name}")
        observed[role] += 1
        rows.append((parent, path.name, size, bytes.fromhex(digest)))
    if observed != counts:
        raise ValueError(f"Wrong carrier or Runtime membership in {phase}")
    return paths, rows


def render():
    raw = DEMAND.read_bytes()
    if sha256(raw).hexdigest() != DEMAND_SHA256:
        raise ValueError("Pinned executable-demand receipt changed")
    demand = json.loads(raw)
    header = [
        "#ifndef ONEOS_GUEST_NATIVE_EXEC_PROFILE_H",
        "#define ONEOS_GUEST_NATIVE_EXEC_PROFILE_H",
        "",
        '#include "guest_native_exec_placement.h"',
        "",
        "struct guest_native_exec_pin {",
        "    enum guest_native_exec_dir parent;",
        "    const char *name;",
        "    uint64_t bytes;",
        "    unsigned char sha256[32];",
        "};",
    ]
    ordered = {}
    for phase, symbol, entry, interpreter, counts in PHASES:
        paths, rows = phase_pins(demand, phase, entry, interpreter, counts)
        ordered[phase] = paths
        header.extend(("", f"static const struct guest_native_exec_pin {symbol}[] = {{"))
        for parent, name, size, digest in rows:
            header.append(f'    {{ {parent}, "{name}", UINT64_C({size}), {{')
            for offset in (0, 16):
                header.append("        " + ", ".join(f"0x{b:02x}" for b in digest[offset:offset + 16]) + ",")
            header.append("    } },")
        header.append("};")
    header.extend(("", "#endif", ""))
    return "\n".join(header).encode("ascii"), ordered


def main():
    header, ordered = render()
    run = ROOT / "out/guest-native-exec-placement-profile" / f"r-{uuid4().hex[:8]}"
    run.mkdir(parents=True)
    (run / "guest_native_exec_profile.h").write_bytes(header)
    receipt = {
        "schema": 1, "status": "PASS_EXACT_EARLY_NATIVE_EXEC_PLACEMENT_PINS",
        "demandSha256": DEMAND_SHA256, "headerSha256": sha256(header).hexdigest(),
        "orderedPaths": ordered, "selected": False, "deviceEligible": False, "targetExecuted": False,
    }
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(run)


if __name__ == "__main__":
    main()
