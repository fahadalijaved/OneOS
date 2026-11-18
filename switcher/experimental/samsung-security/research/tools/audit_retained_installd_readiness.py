#!/usr/bin/env python3
"""Join the saved installd startup and acquisition records without executing them."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
NATIVE = "firmware/retained-installd-native-owner/"
LIFECYCLE = "firmware/retained-guest-user-lifecycle/"
PINS = {
    "image": (NATIVE + "20261106T024945006359Z-7b005bf1d2054ec4821a3e3ebdfdf978/installd",
              "ed618c386528c0b9890c67cbdcb22e1c194f44b034d8e36be2d7f2217fef7dfc"),
    "decoded": (NATIVE + "static/selected-native.json",
                "073ce4abb6ed496693e57a529b7a6e7c9d24d8785df7f20135db5ea79a02f776"),
    "elf": (NATIVE + "static/elf.json",
            "897ee77644a17a8f7c2ef97d77588a06c5cb8a29620ff9c6c86cd90b014d108a"),
    "host": ("firmware/retained-installd-routing/20261106T025342086100Z-a111ad98353d4c4990934cf47dfba64a.jsonl",
             "0a867a4bb726e01ad698a221fac1606cc227531ca5e2edefe2e88dafe56d7229"),
    "stage": (LIFECYCLE + "20261106T022002388272Z-8d84ce4a70ff43e1a42658e2c6b9af03.jsonl",
              "762dad02979c56ee4f1b0c3fe41519ecf649cd6d72b83ea5c0a84ce6ba149e72"),
    "proxy": (LIFECYCLE + "20261106T022152585065Z-116bffe9945144c4bc1f9c504ee94438.jsonl",
              "72e4ea7e108bff23ad8d1f5a9abbacb6bc13b8b652a4c1d09626ddf8a097acd0"),
    "installed": ("inventory/installed-oneos-code-profile.json",
                  "e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a"),
    "alias": ("inventory/guest-installd-alias-review.json",
              "500623f38c39d3662703eb35bedfef76f7db6d0d9e4c67efee99bba15506861d"),
    "launch": ("inventory/guest-native-launch-profile.json",
               "0e6980ecdad5877f74360cb76b900bf853970bbfc09b71265b2929104aa6bc72"),
    "property": ("inventory/retained-property-view-plan.json",
                 "c108299ed2b0b68a116d465af59c657bc393e2afb2f22ff609ab4b70b0cb8cce"),
}

NATIVE_EDGES = {
    0x261FC: {
        0x2622C: ("bl", "defaultServiceManager"),
        0x26238: ("add", "installd"),
        0x2633C: ("mov", "w3, wzr"),
        0x26340: ("mov", "w4, #8"),
        0x26348: ("blr", "x8"),
        0x26390: ("cbnz", "w19, #0x26430"),
        0x263A4: ("bl", "startThreadPool"),
        0x263AC: ("bl", "giveThreadPoolName"),
        0x263D8: ("mov", "w1, #1"),
        0x263E8: ("bl", "GetBoolProperty"),
        0x263F4: ("adr", "x9, #0x98334"),
        0x263F8: ("stlrb", "w8, [x9]"),
        0x26430: ("mov", "w0, w19"),
    },
    0x3F8C4: {
        0x3F954: ("adr", "x8, #0x98334"),
        0x3F958: ("ldarb", "w8, [x8]"),
        0x3F95C: ("tbz", "w8, #0, #0x3fa20"),
        0x3FA44: ("b", "Status2okEv"),
    },
    0x8AAF8: {
        0x8B070: ("bl", "fs_write_atomic_int"),
        0x8B090: ("bl", "InstalldNativeService5startEv"),
        0x8B094: ("cbnz", "w0, #0x8b180"),
        0x8B098: ("bl", "IPCThreadState4selfEv"),
        0x8B0A0: ("bl", "joinThreadPool"),
    },
}

INSTALLER = "Lcom/android/server/pm/Installer;"
PROXY = "Lcom/android/server/pm/OneOSInstalldProxy;"
JAVA_EDGES = (
    ("host", INSTALLER, "connect()V",
     "39b17a7cbad4bf8033bcb10b8a9613ea68686eb35b5bd72e34e25bbc6ecfcc1f",
     {0: "string=installd", 3: "ServiceManager;->getService", 21: "linkToDeath",
      28: "IInstalld$Stub;->asInterface", 32: "->mInstalld:", 36: "countDown",
      44: "invalidateMounts", 51: "setFirstBoot"}),
    ("host", INSTALLER, "checkBeforeRemote()V",
     "9c3cb82ce103cd02095f24457801f1ebd735491caf5441c730955e58f4d38c0f",
     {68: "CountDownLatch;->await", 83: "THROW", 84: "RETURN_VOID"}),
    ("stage", INSTALLER, "connect()V",
     "dd34d2788d57ed89bff48967c32ad02f458e02715f452798d96f9c47aad9236c",
     {0: "string=installd", 3: "ServiceManager;->getService", 15: "linkToDeath",
      23: "OneOSInstalldProxy;->asInterface", 27: "->mInstalld:", 31: "countDown",
      34: "invalidateMounts", 37: "executeDeferredActions", 46: "afterInstalldConnected",
      71: "postDelayed"}),
    ("proxy", PROXY, "asInterface(Landroid/os/IBinder;)Landroid/os/IInstalld;",
     "ce0113f6e14919f21abb85ae91a711a2801a9465da6cc0df8940b157a7f03ee7",
     {0: "IF_NEZ", 3: "RETURN_OBJECT", 6: "-><init>(Landroid/os/IBinder;)V",
      9: "RETURN_OBJECT"}),
    ("proxy", PROXY, "createUserData(Ljava/lang/String;III)V",
     "42389e0adfea0c3f2f805d01d77cd18761039f763a4da9584392d9cc2ec8b8fd",
     {14: "writeInterfaceToken", 33: "IBinder;->transact", 37: "readException"}),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, description):
    if not condition:
        raise ValueError(description)


def main():
    payloads = {}
    inputs = {}
    for role, (relative, expected) in PINS.items():
        data = (ROOT / relative).read_bytes()
        require(digest(data) == expected, f"input identity drift: {role}")
        inputs[role] = {"path": relative, "sha256": expected, "bytes": len(data)}
        payloads[role] = data

    decoded = json.loads(payloads["decoded"])
    require(decoded["sourceSha256"] == inputs["image"]["sha256"], "decoded image mismatch")
    native = []
    for start, edges in NATIVE_EDGES.items():
        function, = (row for row in decoded["functions"] if row["address"] == start)
        offset = function["fileOffset"]
        image_slice = payloads["image"][offset:offset + function["bytes"]]
        instructions = function["instructions"]
        require([row["pc"] for row in instructions] ==
                list(range(start, start + function["bytes"], 4)), "native range drift")
        require(b"".join(bytes.fromhex(row["bytes"]) for row in instructions) == image_slice
                and digest(image_slice) == function["sha256"], "native bytes mismatch")
        rows = {row["pc"]: row for row in instructions}
        for pc, (mnemonic, detail) in edges.items():
            row = rows[pc]
            require(row["mnemonic"] == mnemonic and
                    any(detail in row.get(key, "") for key in
                        ("operands", "targetSymbol", "literal")), f"native edge {pc:#x}")
        native.append({"symbol": function["symbol"], "address": hex(start),
                       "bodySha256": function["sha256"],
                       "anchors": {hex(pc): [op, detail] for pc, (op, detail) in edges.items()}})

    bss, = (row for row in json.loads(payloads["elf"])["sections"] if row["name"] == ".bss")
    require(bss["type"] == 8 and bss["address"] <= 0x98334 < bss["address"] + bss["bytes"],
            "cache address outside NOBITS")
    records = {role: [json.loads(line) for line in payloads[role].splitlines()]
               for role in ("host", "stage", "proxy")}
    java = []
    for role, owner, signature, expected, edges in JAVA_EDGES:
        method, = (row for row in records[role] if row["record"] == "method" and
                   row["body"]["owner"] == owner and row["body"]["signature"] == signature)
        require(method["normalizedBodySha256"] == expected, f"body drift: {role} {signature}")
        rows = {row["pc"]: row for row in method["body"]["instructions"]}
        for pc, detail in edges.items():
            require(detail in rows[pc].get("reference", "") or detail == rows[pc]["opcode"],
                    f"DEX edge {role} {signature} {pc}")
        java.append({"inputRole": role, "method": owner + "->" + signature,
                     "bodySha256": expected, "dex": method["physicalDex"],
                     "logicalHeaderOffset": method["logicalHeaderOffset"], "anchors": edges})

    stage, = (row for row in json.loads(payloads["installed"])["stagedCodeArtifacts"]
              if row["name"] == "services_patched.jar")
    result = {
        "schema": "retained-installd-readiness-source-join/v1",
        "status": "STATIC_SOURCE_JOIN_ONLY_BARRIER_UNIMPLEMENTED",
        "inputs": inputs,
        "stagedServices": {key: stage[key] for key in ("name", "bytes", "sha256")},
        "native": native,
        "cache": {"elfAddress": "0x98334", "section": ".bss", "sectionType": bss["type"],
                  "store": "0x263f8", "load": "0x3f958", "zeroReturnsOk": "0x3fa44"},
        "java": java,
        "candidateProducerEdge": "main successful start fallthrough at 0x8b098",
        "candidateConsumerEdge": "before guest Installer.connect first getService at PC 3",
        "limits": ["Source records only", "No executable, Binder, Android or device ran",
                   "No startup, process, property value or Binder identity attested"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
