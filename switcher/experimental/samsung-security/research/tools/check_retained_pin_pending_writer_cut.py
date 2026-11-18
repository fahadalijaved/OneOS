#!/usr/bin/env python3
"""Read exact Samsung pending-start producer and consumer. Emit only an unselected plan."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = "inventory/retained-physical-user-worker-boundary.json"
ARCHIVE = "../firmware/samsung/runtime-20261104/services.jar"
READER = "tools/audit_samsung_service_code_headers.py"
PINS = {
    INVENTORY: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
    ARCHIVE: "def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6",
    READER: "6352686885bc528a30c62e007748f0ff0a8a2e5055ba719e035b0c5ec5d4564e",
    "out/retained-pin-writer-deferral/READBACK.json":
        "f036a669b642fc78fff1caac36ddc25e773cb4c9e4289bd6fcd4dc7170836db7",
}
UC = "Lcom/android/server/am/UserController;"
LAMBDA = UC[:-1] + "$$ExternalSyntheticLambda4;"
PENDING = UC[:-1] + "$PendingUserStart;"
LISTENER = "Landroid/os/IProgressListener;"
HANDLER = "Landroid/os/Handler;"
FINISH = UC + "->finishUserStopped(Lcom/android/server/am/UserState;Z)V"
RUN = LAMBDA + "->run()V"
START = UC + "->startUserNoChecks(IIII" + LISTENER + ")Z"
POST = HANDLER + "->post(Ljava/lang/Runnable;)Z"
PROPOSED = "Lcom/android/server/am/RetainedPinPendingStartBoundary;"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def retained(path, pin, limit):
    with (ROOT / path).open("rb") as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit and sha(data) == pin, "Exact held bytes required: " + path)
    return data


def normalized(inventory, names):
    methods = {}
    for label in ("uc-core", "uc-worker4"):
        item = inventory["queries"][label]["raw"]
        data = retained(item["path"], item["sha256"], item["bytes"])
        need(len(data) == item["bytes"], "Held body-query length")
        for line in data.splitlines():
            row = json.loads(line)
            if row["record"] != "method":
                continue
            body = row["body"]
            name = body["owner"] + "->" + body["signature"]
            if name not in names:
                continue
            digest = sha(line.split(b',"body":', 1)[1][:-1])
            need(digest == row["normalizedBodySha256"] == inventory["methodProofs"][name]["bodySha256"]
                 and row["physicalDex"] == "classes.dex" and row["logicalHeaderOffset"] == 0
                 and name not in methods, "Exact selected normalized body: " + name)
            methods[name] = body
    need(set(methods) == names, "Whole selected body set")
    return methods


def field(view, index):
    p = view.item("fields", index)
    owner, typ, name = struct.unpack_from("<HHI", view.data, p)
    return view.typ(owner) + "->" + view.string(name) + ":" + view.typ(typ)


def edit_plan(view, method, instructions, edits, new_outs=None):
    """Encode and invert only the local code envelope in memory.

    Invoke method_ids deliberately retain the old numeric index in this
    envelope. The proposed symbolic targets require a later writer/remapper.
    """
    origin = method["codeOffset"]
    end = origin + 16 + 2 * method["header"]["insnsSize"]
    before = view.data[origin:end]
    tentative = bytearray(before)
    inverse = []
    report = []
    for pc, old_opcode, old_regs, new_opcode, new_regs, kind, target in edits:
        insn = instructions[pc]
        position = 16 + 2 * pc
        word, ref = struct.unpack_from("<HH", before, position)
        need(word & 0xff == old_opcode, "Exact raw opcode at " + str(pc))
        if kind == "nibbles":
            actual = [(word >> 8) & 15, word >> 12]
            encoded = new_opcode | (new_regs[0] << 8) | (new_regs[1] << 12)
        elif kind == "byte":
            actual = [word >> 8]
            encoded = new_opcode | (new_regs[0] << 8)
        elif kind == "list":
            arg_words = struct.unpack_from("<H", before, position + 4)[0]
            actual = [(arg_words >> (4 * i)) & 15 for i in range(word >> 12)]
            need(actual == new_regs and word & 0xf00 == 0, "Exact 35c argument encoding")
            encoded = (word & 0xff00) | new_opcode
        elif kind == "range":
            actual = [struct.unpack_from("<H", before, position + 4)[0], word >> 8]
            need(actual[0] == new_regs[0] and new_regs[1] <= 255, "Exact 3rc register start")
            encoded = new_opcode | (new_regs[1] << 8)
        else:
            raise ValueError("Unknown local encoding")
        need(actual == old_regs, "Exact raw operand registers at " + str(pc))
        if kind in ("list", "range"):
            need(view.method(ref)[1] == insn["reference"], "Exact raw method_id reference")
        else:
            original = view.typ(ref) if insn["referenceKind"] == "type" else field(view, ref)
            need(original == insn["reference"], "Exact raw field/type reference")
        inverse.append((position, word))
        struct.pack_into("<H", tentative, position, encoded)
        report.append({"pc": pc, "codeUnits": insn["codeUnits"], "oldOpcode": insn["opcode"],
                       "oldRegisters": old_regs, "newOpcode": {
                           0x71: "INVOKE_STATIC", 0x77: "INVOKE_STATIC_RANGE"
                       }.get(new_opcode, insn["opcode"]), "newRegisters": new_regs,
                       "oldReference": insn["reference"], "newReference": target or insn["reference"]})

    if new_outs is not None:
        need(struct.unpack_from("<H", before, 4)[0] == 6 and new_outs == 7, "Exact outgoing word increase")
        inverse.append((4, 6))
        struct.pack_into("<H", tentative, 4, new_outs)
    widths = {position + i for position, _ in inverse for i in range(2)}
    need(len(tentative) == len(before) and all(a == b or n in widths
         for n, (a, b) in enumerate(zip(before, tentative))), "Only planned code/header units differ")
    for position, word in inverse:
        struct.pack_into("<H", tentative, position, word)
    need(tentative == before, "Complete code header and instruction inverse")
    return {"source": method, "sourceCodeEnvelopeSha256": sha(before),
            "edits": report, "newOutsSize": new_outs, "localInverse": True,
            "newMethodIdsResolved": False}


def verify():
    inventory = json.loads(retained(INVENTORY, PINS[INVENTORY], 1024 * 1024))
    need(inventory["archiveSha256"] == PINS[ARCHIVE], "Original archive identity")
    retained("out/retained-pin-writer-deferral/READBACK.json",
             PINS["out/retained-pin-writer-deferral/READBACK.json"], 1024 * 1024)
    source = retained(READER, PINS[READER], 64 * 1024)
    nodes = [n for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
             and n.name in ("need", "digest", "View")]
    ns = {"hashlib": hashlib, "struct": struct, "WANTED": {UC, LAMBDA}}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), READER, "exec"), ns)
    jar = retained(ARCHIVE, PINS[ARCHIVE], 64 * 1024 * 1024)
    with zipfile.ZipFile(io.BytesIO(jar)) as z:
        entries = [e for e in z.infolist() if e.filename == "classes.dex"]
        need(len(entries) == 1 and entries[0].file_size == 28157552, "Exact original physical member")
        dex = z.read(entries[0])
    dex_pin = "6c9ac3f92a14050900b5fe9502a726cd186011a4342cb2a76c7ba5288e42c973"
    need(sha(dex) == dex_pin, "Original intact physical DEX041")
    view = ns["View"](dex, 0)
    _, raw_methods = view.selected()
    bodies = normalized(inventory, {FINISH, RUN, START})
    pc = {name: {i["pc"]: i for i in body["instructions"]} for name, body in bodies.items()}
    producer, consumer = pc[FINISH], pc[RUN]
    need(raw_methods[FINISH]["codeOffset"] == 3999968 and raw_methods[FINISH]["header"]["outsSize"] == 9
         and raw_methods[RUN]["codeOffset"] == 3976764 and raw_methods[RUN]["header"] ==
         dict(registersSize=8, insSize=1, outsSize=6, triesSize=0, insnsSize=174),
         "Original raw code headers")
    need(producer[609]["opcode"] == "MONITOR_ENTER" and producer[609]["registers"] == [1]
         and producer[666]["reference"] == LAMBDA + "-><init>(I)V" and producer[666]["registers"] == [8, 12]
         and producer[48]["literal"] == 1 and producer[48]["registers"] == [12]
         and producer[669]["reference"] == LAMBDA + "->f$0:Ljava/lang/Object;" and producer[669]["registers"] == [0, 8]
         and producer[671]["reference"] == LAMBDA + "->f$1:Ljava/lang/Object;" and producer[671]["registers"] == [6, 8]
         and producer[673]["reference"] == "Ljava/lang/invoke/VarHandle;->storeStoreFence()V"
         and producer[676]["reference"] == POST and producer[676]["codeUnits"] == 3
         and producer[679]["reference"] == "Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z"
         and producer[689]["reference"] == "Ljava/util/ArrayList;->removeAll(Ljava/util/Collection;)Z"
         and producer[692]["opcode"] == "MONITOR_EXIT"
         and dict(startPc=610, codeUnits=85, exceptionType=None, handlerPc=683) in bodies[FINISH]["catches"],
         "Actual accepted runnable, ignored post return and subsequent remove under stock lock")
    need({"key": 1, "offsetFromReferringSwitchPc": 104} in consumer[158]["switchElements"]
         and consumer[3]["opcode"] == "PACKED_SWITCH" and consumer[107]["registers"] == [0, 7]
         and consumer[109]["registers"] == [1, 0] and consumer[110]["reference"] == UC
         and consumer[118]["reference"] == "Ljava/lang/Object;->getClass()Ljava/lang/Class;"
         and consumer[118]["registers"] == [1] and consumer[129]["registers"] == [3]
         and consumer[129]["literal"] == 0 and consumer[130]["reference"] == START
         and consumer[130]["codeUnits"] == 3 and consumer[133]["opcode"] == "RETURN_VOID"
         and all(not 107 < i.get("targetPc", -1) <= 133 for i in consumer.values())
         and not bodies[RUN]["catches"], "Exact isolated class-id 1 consumer branch")
    need([consumer[n]["reference"] for n in (112, 114, 116, 121, 123, 125, 127)] ==
         [LAMBDA + "->f$1:Ljava/lang/Object;", PENDING,
          UC + "->EXCEPTION_TEMPLATE_CANNOT_START_USER_WHEN_NOT_READY:Ljava/lang/String;",
          PENDING + "->userId:I", PENDING + "->userStartMode:I",
          PENDING + "->autoStopUserInSecs:I", PENDING + "->unlockListener:" + LISTENER],
         "Exact field identity and preserved side effects")

    producer_plan = edit_plan(view, raw_methods[FINISH], producer, [
        (676, 0x6e, [7, 8], 0x71, [7, 8], "list", PROPOSED + "->post(" + HANDLER + LAMBDA + ")Z"),
    ])
    consumer_plan = edit_plan(view, raw_methods[RUN], consumer, [
        (112, 0x54, [7, 7], 0x54, [0, 7], "nibbles", None),
        (114, 0x1f, [7], 0x1f, [0], "byte", None),
        (116, 0x62, [0], 0x62, [2], "byte", None),
        (121, 0x52, [2, 7], 0x52, [2, 0], "nibbles", None),
        (123, 0x52, [4, 7], 0x52, [4, 0], "nibbles", None),
        (125, 0x52, [5, 7], 0x52, [5, 0], "nibbles", None),
        (127, 0x54, [6, 7], 0x54, [6, 0], "nibbles", None),
        (130, 0x74, [1, 6], 0x77, [1, 7], "range",
         PROPOSED + "->resume(" + UC + "IIII" + LISTENER + LAMBDA + ")Z"),
    ], new_outs=7)
    need(pc[START][190]["opcode"] == "INVOKE_VIRTUAL_RANGE"
         and pc[START][190]["registerCount"] == 7
         and pc[START][190]["reference"].startswith(UC + "->startUserInternal("),
         "Shared foreground cut remains a distinct stock call")
    return {"status": "PENDING_START_TRANSFORM_AUDITED_EXCLUSION_REFUSED", "sourcePins": PINS,
            "physicalDexSha256": dex_pin, "producer": producer_plan, "consumer": consumer_plan,
            "sourceBoundaries": {"producerMonitor": 609, "post": 676, "pendingRemoval": 689,
                                 "consumerEntry": 107, "start": 130, "callerWriterCut": 190},
            "occurrence": "Same actual Handler, class-id 1 Runnable, UserController and PendingUserStart",
            "openObligations": ["Exclusive custody through original post, reentry and actual dispatch",
                                "Real same-Handler release and cancellation policy for a parked occurrence",
                                "Separate synchronous foreground, queued-switch, stop and UMS coverage",
                                "Closed same-services-cohort helper and checked DEX method-ID remap"],
            "liveWriterExclusion": False, "stockDexEdited": False, "pinAdmission": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-exclusion", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(), indent=2))
    return 2 if args.require_exclusion else 0


if __name__ == "__main__":
    raise SystemExit(main())
