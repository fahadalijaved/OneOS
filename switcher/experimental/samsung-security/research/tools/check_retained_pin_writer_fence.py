#!/usr/bin/env python3
"""Verify the fixed stock writer cuts. No live lease or retarget is selected."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INVENTORY = "inventory/retained-physical-user-worker-boundary.json"
EARLIER = "out/retained-pin-user-lease/READBACK.json"
BINDING = ("compat/android/com/appleexploit/oneos/security/authority/"
           "PreparedRetainedPinBinding.java")
PINS = {
    INVENTORY: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
    EARLIER: "fe35fddf872912798ddf1e1f23b9d216e063535527620a9d213ec1995f05a849",
    BINDING: "f7f006d2d9db467d46abb1a14f94bcabd63f5e63f6218b1eef43d926729a35ed",
}
UC = "Lcom/android/server/am/UserController;"
AMS = "Lcom/android/server/am/ActivityManagerService;"
UMS = "Lcom/android/server/pm/UserManagerService;"
LOCAL_UMS = UMS[:-1] + "$LocalService;"
START = "startUserInternal(IIIILandroid/os/IProgressListener;Lcom/android/server/utils/TimingsTraceAndSlog;)Z"
STOP_ARGS = "(IZZLandroid/app/IStopUserCallback;Lcom/android/server/am/UserController$6;)I"


def read(path, digest, size=None):
    with (ROOT / path).open("rb") as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024 or (size is not None and len(data) != size):
        raise ValueError(path + " size differs")
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(path + " hash differs")
    return data


def check():
    sources = {path: read(path, digest) for path, digest in PINS.items()}
    inventory = json.loads(sources[INVENTORY])
    earlier = json.loads(sources[EARLIER])
    if earlier["leaseAcquired"] or earlier["archiveSha256"] != inventory["archiveSha256"]:
        raise ValueError("Wrong earlier stock proof")
    methods = {}
    raw_pins = []
    for label in ("uc-core", "ams-entry", "ams-local", "ums-mutation", "ums-attributes", "ums-record"):
        raw = inventory["queries"][label]["raw"]
        raw_pins.append(raw)
        for line in read(raw["path"], raw["sha256"], raw["bytes"]).splitlines():
            row = json.loads(line)
            if row["record"] != "method":
                continue
            body = row["body"]
            key = body["owner"] + "->" + body["signature"]
            expected = inventory["methodProofs"][key]
            encoded = line.split(b',"body":', 1)[1][:-1]
            if (key in methods or expected["query"] != label
                    or hashlib.sha256(encoded).hexdigest() != expected["bodySha256"]
                    or row["normalizedBodySha256"] != expected["bodySha256"]
                    or row["physicalDex"] != expected["physicalDex"]
                    or row["logicalHeaderOffset"] != expected["logicalHeaderOffset"]):
                raise ValueError(key + " source proof differs")
            methods[key] = {ins["pc"]: ins for ins in body["instructions"]}

    checked = []

    def at(owner, signature, pc, opcode, suffix=None, **attrs):
        key = owner + "->" + signature
        ins = methods[key][pc]
        if (ins["opcode"] != opcode or (suffix and not ins.get("reference", "").endswith(suffix))
                or any(ins.get(name) != value for name, value in attrs.items())):
            raise ValueError(f"{key}@{pc} source edge differs")
        checked.append({"method": key, "pc": pc, "instruction": ins})

    at(UC, START, 26, "MONITOR_ENTER")
    at(UC, START, 231, "INVOKE_VIRTUAL", "->clearAllLockedTasks()V")
    at(UC, START, 445, "INVOKE_VIRTUAL", "SparseArray;->put(ILjava/lang/Object;)V")
    at(UC, START, 530, "IPUT", "->mCurrentUserId:I")
    at(UC, "switchUser(I)Z", 57, "MONITOR_ENTER")
    at(UC, "switchUser(I)Z", 102, "INVOKE_VIRTUAL", "Handler;->post(Ljava/lang/Runnable;)Z")
    at(UC, "switchUser(I)Z", 273, "INVOKE_VIRTUAL", "ArrayDeque;->offer(Ljava/lang/Object;)Z")
    at(UC, "stopUser" + STOP_ARGS, 87, "MONITOR_ENTER")
    at(UC, "stopUser" + STOP_ARGS, 88, "INVOKE_VIRTUAL_RANGE", "->stopUsersLU" + STOP_ARGS)
    at(AMS, "stopProfile(I)Z", 55, "MONITOR_ENTER")
    at(AMS, "stopProfile(I)Z", 61, "INVOKE_VIRTUAL_RANGE", "->stopUsersLU" + STOP_ARGS)
    at(UC, "stopUsersLU" + STOP_ARGS, 6, "IF_NEZ", registers=[1])
    at(UC, "stopUsersLU" + STOP_ARGS, 8, "CONST_4", literal=-3)
    at(UC, "stopUsersLU" + STOP_ARGS, 9, "RETURN")
    at(UC, "stopUsersLU" + STOP_ARGS, 327, "INVOKE_VIRTUAL", "->getUserInfo(I)Landroid/content/pm/UserInfo;")
    at(UC, "stopUsersLU" + STOP_ARGS, 369, "INVOKE_VIRTUAL", "Handler;->post(Ljava/lang/Runnable;)Z")
    at(UC, "stopUsersLU" + STOP_ARGS, 379, "INVOKE_VIRTUAL", "UserState;->setState(I)V")
    at(UMS, "getUserInfo(I)Landroid/content/pm/UserInfo;", 23, "MONITOR_ENTER")
    at(LOCAL_UMS, "setAttributes(II)Z", 15, "MONITOR_ENTER")
    at(LOCAL_UMS, "setAttributes(II)Z", 54, "INVOKE_VIRTUAL", "UserInfo;->setAttributes(I)V")
    at(LOCAL_UMS, "clearAttributes(II)Z", 8, "MONITOR_ENTER")
    at(LOCAL_UMS, "clearAttributes(II)Z", 56, "INVOKE_VIRTUAL", "UserInfo;->setAttributes(I)V")
    put = "putUserInfo(Landroid/content/pm/UserInfo;)Lcom/android/server/pm/UserManagerService$UserData;"
    at(UMS, put, 9, "MONITOR_ENTER")
    at(UMS, put, 19, "INVOKE_VIRTUAL", "SparseArray;->put(ILjava/lang/Object;)V")
    remove = "removeUserState(I)V"
    at(UMS, remove, 25, "INVOKE_VIRTUAL", "LockSettingsInternal;->removeUser(I)V")
    at(UMS, remove, 44, "INVOKE_VIRTUAL", "->destroyUserStorageKeys(I)V")
    at(UMS, remove, 234, "MONITOR_ENTER")
    at(UMS, remove, 240, "INVOKE_VIRTUAL", "SparseArray;->remove(I)V")
    at(UMS, remove, 247, "INVOKE_VIRTUAL", "ActivityManagerInternal;->onUserRemoved(I)V")
    at(AMS[:-1] + "$LocalService;", "onUserRemoved(I)V", 6, "MONITOR_ENTER")
    at(AMS[:-1] + "$LocalService;", "onUserRemoved(I)V", 63, "INVOKE_VIRTUAL", "SparseArray;->remove(I)V")

    return {"status": "MULTI_SITE_STOCK_WRITER_CUT_VERIFIED_NO_LEASE", "leaseAcquired": False,
            "archiveSha256": inventory["archiveSha256"], "selectedHooks": [],
            "checkedSourceEdges": checked, "heldPins": PINS, "rawMethodPins": raw_pins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-lease", action="store_true", help="require live lease evidence")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 2 if args.require_lease and not result["leaseAcquired"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
