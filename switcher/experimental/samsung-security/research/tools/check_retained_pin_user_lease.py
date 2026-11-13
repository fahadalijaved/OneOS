#!/usr/bin/env python3
"""Verify the held stock user-writer counterexamples. Never grants a live lease."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WRITERS = "inventory/retained-physical-user-worker-boundary.json"
CREDENTIALS = "inventory/credentials.json"
CHECK_OWNER = ("compat/android/com/appleexploit/oneos/security/authority/"
               "PreparedRetainedPinCheckOwner.java")
PINS = {
    WRITERS: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
    CREDENTIALS: "333118f3876c61f641d9a8aae82bd11ed61d6366a28e916ddd58755c4a5ef3b8",
    CHECK_OWNER: "4d3aeab1c80725506cb9f1ec074cc9929ff55fe5251d9abbfe253ef374770e02",
    "out/retained-pin-mutation-owner/r-f4ca3114/receipt.json":
        "8695ac06633cd8dab2ad49215f736a4df5def5208086172440e593a60390c3eb",
}
ARCHIVE = "def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6"
CONTROLLER = "Lcom/android/server/am/UserController;"
AMS = "Lcom/android/server/am/ActivityManagerService;"
LSS = "Lcom/android/server/locksettings/LockSettingsService;"
START = "startUserInternal(IIIILandroid/os/IProgressListener;Lcom/android/server/utils/TimingsTraceAndSlog;)Z"
NO_CHECKS = "startUserNoChecks(IIIILandroid/os/IProgressListener;)Z"


def require(ok, description):
    if not ok:
        raise ValueError(description)


def read(path, digest, size=None):
    with (ROOT / path).open("rb") as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    require(len(data) <= 2 * 1024 * 1024 and (size is None or len(data) == size), path + " size")
    require(hashlib.sha256(data).hexdigest() == digest, path + " SHA-256")
    return data


def load_methods(writers):
    methods = {}
    raw_pins = []
    for label in ("ams-entry", "uc-core", "uc-worker3", "uc-worker4", "uc-finish"):
        proof = writers["queries"][label]["raw"]
        blob = read(proof["path"], proof["sha256"], proof["bytes"])
        raw_pins.append(proof)
        for line in blob.splitlines():
            row = json.loads(line)
            if row["record"] != "method":
                continue
            body = row["body"]
            name = body["owner"] + "->" + body["signature"]
            encoded = line.split(b',"body":', 1)[1][:-1]
            actual = hashlib.sha256(encoded).hexdigest()
            expected = writers["methodProofs"][name]
            require(actual == row["normalizedBodySha256"] == expected["bodySha256"]
                    and row["physicalDex"] == "classes.dex" and row["logicalHeaderOffset"] == 0, name)
            require(name not in methods, "Duplicate selected method: " + name)
            methods[name] = {ins["pc"]: ins for ins in body["instructions"]}
    return methods, raw_pins


def check():
    inputs = {path: read(path, digest) for path, digest in PINS.items()}
    writers = json.loads(inputs[WRITERS])
    credentials = json.loads(inputs[CREDENTIALS])
    require(writers["archiveSha256"] == credentials["inputs"]["samsung"]["archiveSha256"] == ARCHIVE,
            "Writer/credential Samsung services archive mismatch")
    methods, raw_pins = load_methods(writers)
    checks = []

    def at(owner, signature, pc, opcode, reference_suffix=None, **attributes):
        name = owner + "->" + signature
        ins = methods[name][pc]
        require(ins["opcode"] == opcode and (reference_suffix is None
                or ins.get("reference", "").endswith(reference_suffix))
                and all(ins.get(k) == v for k, v in attributes.items()), f"{name}@{pc}")
        checks.append({"method": name, "pc": pc, "opcode": opcode})

    def case(owner, signature, switch_pc, payload_pc, op, key, target):
        at(owner, signature, switch_pc, op)
        at(owner, signature, payload_pc, op + "_PAYLOAD")
        payload = methods[owner + "->" + signature][payload_pc]["switchElements"]
        require({"key": key, "offsetFromReferringSwitchPc": target - switch_pc} in payload,
                f"{owner} dispatch {key}")

    at(CONTROLLER, "switchUser(I)Z", 273, "INVOKE_VIRTUAL", "ArrayDeque;->offer(Ljava/lang/Object;)Z")
    at(CONTROLLER, "switchUser(I)Z", 278, "IPUT", "->mTargetUserId:I")
    at(CONTROLLER, "switchUser(I)Z", 316, "CONST_16", literal=120)
    at(CONTROLLER, "switchUser(I)Z", 327, "INVOKE_VIRTUAL", "Handler;->sendMessage(Landroid/os/Message;)Z")
    message = "handleMessage(Landroid/os/Message;)Z"
    case(CONTROLLER, message, 17, 1492, "SPARSE_SWITCH", 120, 211)
    at(CONTROLLER, message, 223, "INVOKE_VIRTUAL", "->startUser(II)Z")
    for pc, opcode, ref in [(11, "INVOKE_VIRTUAL", "ArrayDeque;->poll()Ljava/lang/Object;"),
                            (53, "IPUT", "->mTargetUserId:I"), (58, "MONITOR_EXIT", None),
                            (61, "INVOKE_VIRTUAL", "->switchUser(I)Z")]:
        at(CONTROLLER, "endUserSwitch()V", pc, opcode, ref)
    foreground = "startUserInForegroundWithListener(ILandroid/os/IProgressListener;)Z"
    at(AMS, foreground, 17, "CONST_4", literal=1)
    at(AMS, foreground, 20, "INVOKE_VIRTUAL_RANGE", "->" + NO_CHECKS)
    at(CONTROLLER, NO_CHECKS, 190, "INVOKE_VIRTUAL_RANGE", "->" + START)
    at(CONTROLLER, START, 529, "MONITOR_ENTER")
    at(CONTROLLER, START, 530, "IPUT", "->mCurrentUserId:I")
    at(CONTROLLER, START, 535, "MONITOR_EXIT")
    worker3 = CONTROLLER[:-1] + "$$ExternalSyntheticLambda3;"
    at(CONTROLLER, START, 572, "CONST_4", literal=2, registers=[5])
    at(CONTROLLER, START, 573, "INVOKE_DIRECT", worker3 + "-><init>(I)V", registers=[4, 5])
    at(CONTROLLER, START, 585, "INVOKE_VIRTUAL", "Handler;->post(Ljava/lang/Runnable;)Z", registers=[3, 4])
    case(worker3, "run()V", 5, 608, "PACKED_SWITCH", 2, 170)
    at(worker3, "run()V", 273, "CONST_STRING_JUMBO", "string=onBeforeUserSwitching")
    at(worker3, "run()V", 276, "INVOKE_VIRTUAL", "Ljava/lang/String;)V")
    at(CONTROLLER, START, 619, "IGET_OBJECT", "->mPendingUserStarts:Ljava/util/List;")
    at(CONTROLLER, START, 639, "INVOKE_VIRTUAL", "ArrayList;->add(Ljava/lang/Object;)Z")
    stopped = "finishUserStopped(Lcom/android/server/am/UserState;Z)V"
    worker4 = CONTROLLER[:-1] + "$$ExternalSyntheticLambda4;"
    at(CONTROLLER, stopped, 48, "CONST_4", literal=1, registers=[12])
    at(CONTROLLER, stopped, 666, "INVOKE_DIRECT", worker4 + "-><init>(I)V", registers=[8, 12])
    at(CONTROLLER, stopped, 676, "INVOKE_VIRTUAL", "Handler;->post(Ljava/lang/Runnable;)Z", registers=[7, 8])
    at(CONTROLLER, stopped, 689, "INVOKE_VIRTUAL", "ArrayList;->removeAll(Ljava/util/Collection;)Z")
    case(worker4, "run()V", 3, 158, "PACKED_SWITCH", 1, 107)
    at(worker4, "run()V", 123, "IGET", "->userStartMode:I")
    at(worker4, "run()V", 130, "INVOKE_VIRTUAL_RANGE", "->" + NO_CHECKS)

    def host_call(method, pc, target):
        key = "samsung:" + LSS + "->" + method
        require({"pc": pc, "target": target} in credentials["methodProofs"][key]["calls"], key)
        checks.append({"method": key, "pc": pc, "target": target})

    host_call("unlockUser(I)V", 42, "Landroid/app/IActivityManager;->unlockUser2(ILandroid/os/IProgressListener;)Z")
    host_call("unlockUser(I)V", 49, "Ljava/util/concurrent/CountDownLatch;->await(JLjava/util/concurrent/TimeUnit;)Z")
    worker = inputs[CHECK_OWNER].split(b"public VerifyCredentialResponse checkPin(", 1)[1]
    worker = worker.split(b"public void closeAdapterIngress()", 1)[0]
    require(b"Integer.valueOf(physicalUserId), nullableCallback" in worker
            and b"checkStillBound(" not in worker and b"check.invoke(endpoint, pin," in worker,
            "Held worker invocation edge")

    return {
        "status": "STOCK_WRITER_COUNTEREXAMPLES_VERIFIED_LEASE_REFUSED",
        "leaseAcquired": False,
        "archiveSha256": ARCHIVE,
        "blockingEdges": ["pending_target_in_local_continuation", "foreground_entry_bypasses_switchUser",
                          "physical_current_store_precedes_before_observer", "posted_start_outlives_pending_list"],
        "checkedSourceEdges": checks,
        "heldPins": PINS,
        "rawMethodPins": raw_pins,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-lease", action="store_true", help="require live lease evidence")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 2 if args.require_lease and not result["leaseAcquired"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
