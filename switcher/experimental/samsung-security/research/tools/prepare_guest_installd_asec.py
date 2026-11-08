"""Verify the unselected GVO ASEC patch in memory against its exact inputs."""

import ast
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = (
    "firmware/upstream-oneos-0.4.58/45abb3df03cbd4a8b006519baaebefdb2c68658a/raw/"
    "45abb3df03cbd4a8b006519baaebefdb2c68658a/switcher/assets/"
)
OWNER = "compat/native/guest_private_view_owner.c"
PATCH = "compat/native/guest-installd-asec.patch"
PATCH_READER = "tools/build_retained_root_view.py"
SAMSUNG_INIT = "firmware/guest-native-launch-profile/static/system__etc__init__hw__init.rc"
ENV = "out/guest-installd-environment/actual-source-check.json"
PINS = {
    OWNER: "9e17a235cfdde8ef919720a887ce9224fb41e39ff4ad6dbb868f684047769540",
    PATCH: "2c71faa43c50e322752638da85c65216398184623f5d6cdb1da49fc06530b8aa",
    PATCH_READER: "ae832d396b32fd30f61b20ab06e3e3f5620274c088304562e688cd0ecad9231a",
    SAMSUNG_INIT: "94a786990f73b176d8d31a2cdeb8f7d6daab65e7ba766d5214df44d29e7a92bb",
    ENV: "ef9af0e03b7fed50c78337ea14ba2942ed7164e56fe22df2b145966d6b32327f",
    UPSTREAM + "guest_prepare.sh": "486f67f90ca7c39eb0d4c8c1696f4041b59010585091c1e70032cc3beca8b36d",
    UPSTREAM + "guest_start.sh": "81460c5f089a21d9684ae9023af9938392621c8296a093ec8045fac5c81482c2",
}
CANDIDATE_SHA = "30cabdb9d9f2cf39260dc213e52b694714695a54dfae85734b8f7778bebe8a21"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit():
    raw = {name: (ROOT / name).read_bytes() for name in PINS}
    for name, digest in PINS.items():
        require(hashlib.sha256(raw[name]).hexdigest() == digest, f"Input differs: {name}")
    # Load only the established, data-only exact patch function from pinned
    # bytes. The native builder's module, imports and entrypoint never run.
    tree = ast.parse(raw[PATCH_READER], filename=PATCH_READER)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "apply_exact_patch"]
    require(len(functions) == 1, "Unique authored patch reader")
    scope = {"re": re, "require": require}
    exec(compile(ast.Module(body=functions, type_ignores=[]), PATCH_READER, "exec"), scope)
    patch = scope["apply_exact_patch"]
    original = {OWNER: raw[OWNER]}
    derived = patch(raw[PATCH], original)
    require(hashlib.sha256(derived[OWNER]).hexdigest() == CANDIDATE_SHA,
            "Exact one-file GVO candidate")
    require(patch(raw[PATCH], derived, inverse=True) == original, "Exact CRLF original inverse")

    prepare = raw[UPSTREAM + "guest_prepare.sh"].decode("utf-8").splitlines()
    start = raw[UPSTREAM + "guest_start.sh"].decode("utf-8").splitlines()
    require('mount --rbind /mnt "$ROOTFS/mnt"' in prepare[1230]
            and 'mount --make-rslave "$ROOTFS/mnt"' in prepare[1234],
            "Pinned legacy /mnt import and propagation")
    require(all("pass_through|installer|androidwritable|runtime|user" in start[i]
                for i in (56, 59))
            and "mkdir -p /mnt/user/0 /mnt/installer /mnt/androidwritable" in start[69]
            and "mount --make-shared /mnt" in start[70]
            and "mount --rbind /mnt/user /mnt/$v" in start[72]
            and "/data/media/0 /mnt/user/0/emulated" in start[96],
            "Pinned legacy guest storage exclusions and receivers")
    require(not any("/mnt/asec" in line or "ASEC_MOUNTPOINT" in line
                    for line in prepare + start), "Unexpected ASEC-specific shell edge")
    require("ASEC_MOUNTPOINT=/mnt/asec" in json.loads(raw[ENV])["environment"]
            and raw[SAMSUNG_INIT].decode("utf-8").splitlines()[324].split()
            == ["mkdir", "/mnt/asec", "0755", "root", "system"],
            "Fixed ASEC environment path and captured Samsung directory profile")
    return {
        "schema": "guest-installd-asec-patch/v1",
        "status": "STATIC_CHILD_OWNED_ASEC_PATCH_UNSELECTED",
        "inputs": {name: {"sha256": digest, "bytes": len(raw[name])}
                   for name, digest in PINS.items()},
        "candidate": {"path": OWNER, "sha256": CANDIDATE_SHA, "bytes": len(derived[OWNER]),
                      "heldInMemoryOnly": True},
        "target": "/mnt/asec",
        "sourceOwnedMount": "GVO child-private /mnt scaffold tmpfs",
        "forwardInverseExact": True,
        "prepareHostMntImportLines": [1231, 1235],
        "startStorageLines": [[53, 75], [94, 97]],
        "samsungAsecMkdirLine": 325,
        "parentWireRolesChanged": False,
        "nativeCompiledOrExecuted": False,
        "deviceAccessed": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
