#!/usr/bin/env python3
"""Read the held Samsung deferral branches without admitting a new writer gate."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INVENTORY = "inventory/retained-physical-user-worker-boundary.json"
PINS = {
    INVENTORY: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
    "out/retained-pin-writer-fence/READBACK.json":
        "7b86dc771e8041c040756114a9b853719a2a585623043308d9d09a1c3fa19de0",
}
UC = "Lcom/android/server/am/UserController;"
AMS = "Lcom/android/server/am/ActivityManagerService;"
WORKER = UC[:-1] + "$$ExternalSyntheticLambda4;"
START = "startUserInternal(IIIILandroid/os/IProgressListener;Lcom/android/server/utils/TimingsTraceAndSlog;)Z"
NO_CHECKS = "startUserNoChecks(IIIILandroid/os/IProgressListener;)Z"
STOPPED = "finishUserStopped(Lcom/android/server/am/UserState;Z)V"


def read(path, digest, size=None):
    with (ROOT / path).open("rb") as source:
        data = source.read(1024 * 1024 + 1)
    if (len(data) > 1024 * 1024 or (size is not None and len(data) != size)
            or hashlib.sha256(data).hexdigest() != digest):
        raise ValueError("Held evidence differs: " + path)
    return data


def check():
    inputs = {name: json.loads(read(name, digest)) for name, digest in PINS.items()}
    inventory = inputs[INVENTORY]
    methods = {}
    raw_pins = []
    for label in ("uc-core", "uc-finish", "uc-worker4", "ams-entry"):
        raw = inventory["queries"][label]["raw"]
        raw_pins.append(raw)
        for line in read(raw["path"], raw["sha256"], raw["bytes"]).splitlines():
            row = json.loads(line)
            if row["record"] != "method":
                continue
            body = row["body"]
            name = body["owner"] + "->" + body["signature"]
            proof = inventory["methodProofs"][name]
            exact_body = line.split(b',"body":', 1)[1][:-1]
            if (name in methods or proof["query"] != label
                    or row["physicalDex"] != "classes.dex" or row["logicalHeaderOffset"] != 0
                    or hashlib.sha256(exact_body).hexdigest() != proof["bodySha256"]
                    or row["normalizedBodySha256"] != proof["bodySha256"]):
                raise ValueError("Stock method differs: " + name)
            methods[name] = {i["pc"]: i for i in body["instructions"]}

    checks = []

    def at(owner, signature, pc, opcode, suffix=None, **attrs):
        name = owner + "->" + signature
        i = methods[name][pc]
        if (i["opcode"] != opcode or (suffix and not i.get("reference", "").endswith(suffix))
                or any(i.get(key) != value for key, value in attrs.items())):
            raise ValueError(f"Stock deferral edge differs: {name}@{pc}")
        checks.append({"method": name, "pc": pc, "instruction": i})

    switch = "switchUser(I)Z"
    at(UC, switch, 58, "CONST_16", literal=-10000, registers=[10])
    at(UC, switch, 60, "CONST_4", literal=1, registers=[11])
    at(UC, switch, 230, "IGET", "->mTargetUserId:I", registers=[1, 13])
    at(UC, switch, 232, "IF_EQ", targetPc=278, registers=[1, 10])
    at(UC, switch, 273, "INVOKE_VIRTUAL", "ArrayDeque;->offer(Ljava/lang/Object;)Z")
    at(UC, switch, 276, "MONITOR_EXIT")
    at(UC, switch, 277, "RETURN", registers=[11])
    at(UC, switch, 278, "IPUT", "->mTargetUserId:I")
    at(UC, switch, 310, "INVOKE_VIRTUAL", "Handler;->sendMessage(Landroid/os/Message;)Z")
    at(UC, switch, 327, "INVOKE_VIRTUAL", "Handler;->sendMessage(Landroid/os/Message;)Z")
    at(UC, "dispatchUserSwitchComplete(II)V", 141, "INVOKE_VIRTUAL", "->endUserSwitch()V")
    at(UC, "endUserSwitch()V", 11, "INVOKE_VIRTUAL", "ArrayDeque;->poll()Ljava/lang/Object;")
    at(UC, "endUserSwitch()V", 58, "MONITOR_EXIT")
    at(UC, "endUserSwitch()V", 61, "INVOKE_VIRTUAL", "->" + switch)

    at(AMS, "startUserInForegroundWithListener(ILandroid/os/IProgressListener;)Z", 20,
       "INVOKE_VIRTUAL_RANGE", "->" + NO_CHECKS)
    at(UC, NO_CHECKS, 190, "INVOKE_VIRTUAL_RANGE", "->" + START)
    at(UC, NO_CHECKS, 197, "RETURN", registers=[7])
    at(UC, START, 146, "INVOKE_STATIC", "Binder;->getCallingUid()I")
    at(UC, START, 150, "INVOKE_STATIC", "Binder;->getCallingPid()I")
    at(UC, START, 231, "INVOKE_VIRTUAL", "->clearAllLockedTasks()V")
    at(UC, START, 358, "INVOKE_VIRTUAL", "->assignUserToDisplayOnStart(IIII)I")
    at(UC, START, 461, "CONST_4", literal=5, registers=[10])
    at(UC, START, 462, "IF_EQ", targetPc=596, registers=[9, 10])
    at(UC, START, 464, "IGET_OBJECT", "->mDoNotAbortShutdownUserIds:Landroid/util/ArraySet;")
    at(UC, START, 470, "INVOKE_VIRTUAL", "ArraySet;->contains(Ljava/lang/Object;)Z")
    at(UC, START, 474, "IF_EQZ", targetPc=478)
    at(UC, START, 476, "GOTO_16", targetPc=596)
    at(UC, START, 639, "INVOKE_VIRTUAL", "ArrayList;->add(Ljava/lang/Object;)Z")
    at(UC, START, 645, "MONITOR_EXIT")
    at(UC, START, 646, "INVOKE_STATIC_RANGE", "Binder;->restoreCallingIdentity(J)V")
    at(UC, START, 649, "RETURN", registers=[17])

    at(UC, STOPPED, 48, "CONST_4", literal=1, registers=[12])
    at(UC, STOPPED, 609, "MONITOR_ENTER")
    at(UC, STOPPED, 666, "INVOKE_DIRECT", WORKER + "-><init>(I)V", registers=[8, 12])
    at(UC, STOPPED, 671, "IPUT_OBJECT", "->f$1:Ljava/lang/Object;", registers=[6, 8])
    at(UC, STOPPED, 676, "INVOKE_VIRTUAL", "Handler;->post(Ljava/lang/Runnable;)Z", registers=[7, 8])
    at(UC, STOPPED, 689, "INVOKE_VIRTUAL", "ArrayList;->removeAll(Ljava/util/Collection;)Z")
    at(UC, STOPPED, 692, "MONITOR_EXIT")
    at(WORKER, "run()V", 3, "PACKED_SWITCH")
    at(WORKER, "run()V", 114, "CHECK_CAST", "UserController$PendingUserStart;")
    at(WORKER, "run()V", 129, "CONST_4", literal=0, registers=[3])
    at(WORKER, "run()V", 130, "INVOKE_VIRTUAL_RANGE", "->" + NO_CHECKS,
       registerStart=1, registerCount=6)
    at(WORKER, "run()V", 133, "RETURN_VOID")
    body = methods[WORKER + "->run()V"]
    if {"key": 1, "offsetFromReferringSwitchPc": 104} not in body[158]["switchElements"] or any(
            i["opcode"] == "MONITOR_ENTER" for pc, i in body.items() if 107 <= pc <= 133):
        raise ValueError("Stock pending-start worker dispatch differs")

    return {"status": "STOCK_DEFERRAL_BRANCHES_VERIFIED_PIN_DEFERRAL_REFUSED",
            "pinDeferralAdmitted": False, "selectedHooks": [],
            "archiveSha256": inventory["archiveSha256"], "checkedSourceEdges": checks,
            "heldPins": PINS, "rawMethodPins": raw_pins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-deferral", action="store_true")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 2 if args.require_deferral and not result["pinDeferralAdmitted"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
