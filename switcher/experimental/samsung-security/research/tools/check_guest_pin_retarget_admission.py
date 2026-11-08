"""Check the held original ColorOS PIN route, without writing or selecting DEX."""
import ast
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
STAGE = "firmware/installed-oneos-staged-code/20261106T021318359707Z-dfb840a7be91477091886e754bfec0be/"
APK = "../firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk"
INGRESS = "out/guest-pin-check-systemserver-ingress/"
SYSTEMUI = "out/guest-pin-systemui-retarget-cut/"
APK_RAW = "firmware/guest-pin-systemui-retarget-cut/"
PARSER = "tools/preserve_dex_code_headers.py"
ARCHIVES = {
    "SystemUI": (APK, 116521421, "0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77",
                 "classes3.dex", 10177500, "793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071"),
    "framework": (STAGE + "framework_patched.jar", 52377761,
                  "5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246",
                  "classes6.dex", 3304704, "47f3b688c6365610afce4f24a03e8f601c7f3f240f73bd03fabee384ab1110a4"),
    "services": (STAGE + "services_patched.jar", 44699364,
                 "efb45f5f061838431387f9c34e4d5c72504a963d0d5bd37f3c4d0ae043854671",
                 "classes2.dex", 10062096, "475fe7b0435add095aec56c719d9cf6491c07212cdae25fa75ce273a82cb10eb"),
}
APK_PROOFS = ("checker", "task", "wrapped", "request")
INGRESS_PINS = {
    "lookup": "c05891665ff1d4351b577ad5192bafe1b879af5c9f53cc0df8ea68c9bf0bb895",
    "proxy": "dd1c84d54c1b86967439e42819126c364c2a95346d31be82efec27d441026c4c",
    "stub": "28e30e6931392b63264002f4e012bfd33434f9d17dd6313686f8c9aa4a443ed0",
    "lss": "4be357338c0e834a35a6673cc3f636cf89f338a29e5518891e618c75387734f0",
    "permission": "c65d145dafe48ad78d40cbac0195929d71be803c80211cc02d869d54f3c3395a",
    "publication": "5bd4e8cf9292e276c4d6d82a87630cd9c62ae10ea2e33e04dc3b80170506c2f2",
}
SOURCE_PINS = {
    PARSER: "943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6",
    "inventory/installed-oneos-code-profile.json": "e868049006a7fcd313b16122a5ef73f3e84640052918c69f92fc07238d16ea9a",
    SYSTEMUI + "IMAGE-MEMBER-READBACK.json": "eeb74c3921925e370baa09be6e1210ed023edd45c69529611b4157b8bd46d728",
    SYSTEMUI + "METHOD-READBACK.json": "99577778898cac82b6b672634643cd989fadcad4081bed0f1e58ce8d487059bc",
    SYSTEMUI + "RAW-CODE-OWNERSHIP.json": "58449cb5d58f246fd344169abc7c6c6f09487b156ccf559d97517b8333dbb6a7",
    SYSTEMUI + "UID-SOURCE-READBACK.json": "570291428b9d75f0e27a406fe5061de3c1f9d2fd30a16c33fa1cec1e852e1b46",
    "out/guest-pin-systemui-task-wrapper/POOL-PREFLIGHT.json": "40d9aa47df587d3006fc3fb5400f9882ff0b2a6a9e86475d60008a6009507daa",
    "out/retained-pin-codec-proof/COMPARISON.json": "a83398d8e0aba2c8cc0a29a920f21a1374484595887e2c877843275134c36cd0",
    "out/retained-pin-caller-chain/READBACK.json": "675e8af1c84aab8a5bf4c58c563c22d4b5cebd597f1a39120d3d95010a555543",
    "out/pin-progress-callback-wire/EVIDENCE.json": "f3dd8571821b0733e660e7d60818a9aebdf28d3fc4721a77b252622927f132ef",
    "compat/android/com/appleexploit/oneos/security/transport/GuestPinCheckRequest.java": "a5fb4e6f6ae6af6aa923865021070eaba9e79e088fa55fd9df2f78b196fc1b61",
    "compat/android/com/appleexploit/oneos/security/transport/PinCheckCompletion.java": "338d8900998c7d008df2462ab89c671842fa83b4e1fbb192892ab8a2a5be0726",
    "compat/android/com/appleexploit/oneos/security/transport/PreparedRetainedPinEndpointClient.java": "dde0022ec22ac66cbf89de43f2f34c12e0bc70b51333d005068a8e1e8b06934f",
    "compat/android/com/appleexploit/oneos/security/authority/PreparedRetainedPinEndpoint.java": "3062e453a50a0d9d609d588af6aa0e4978b29c038597fd8e6aff6b28ac5dcfe6",
}
CALLS = {
    ("checker", "checkCredential"): {65: "oplusCheckCredential"},
    ("checker", "oplusCheckCredential"): {20: "executeOnExecutor"},
    ("task", "doInBackground"): {39: "access$wrapCallback", 43: "checkCredential"},
    ("wrapped", "onCredentialVerified"): {25: "post"},
    ("request", "onEarlyMatched"): {95: "onPasswordChecked"},
    ("request", "onChecked"): {14: "isMatched", 124: "access$setMCheckCredentialTask$p", 336: "onPasswordChecked"},
    ("lookup", "getLockSettings"): {7: "getService", 11: "asInterface"},
    ("proxy", "checkCredential"): {8: "markSensitive", 21: "writeTypedObject", 24: "writeInt",
                                   27: "writeStrongInterface", 36: "transact", 40: "readException"},
    ("stub", "onTransact"): {1078: "asInterface", 1082: "enforceNoDataAvail",
                             1085: "checkCredential", 1089: "writeNoException", 1092: "writeTypedObject"},
    ("lss", "checkCredential"): {0: "checkReadPermission", 3: "clearCallingIdentity",
                                  32: "doVerifyCredential", 36: "restoreCallingIdentity",
                                  39: "zeroizeIfFromParcel", 44: "restoreCallingIdentity", 47: "zeroizeIfFromParcel"},
    ("permission", "checkAccessSecureStoragePermission"): {4: "enforceCallingOrSelfPermission"},
    ("publication", "onStart"): {19: "publishBinderService"},
}
OPCODES = dict(zip(("INVOKE_VIRTUAL", "INVOKE_SUPER", "INVOKE_DIRECT", "INVOKE_STATIC", "INVOKE_INTERFACE"),
                   range(0x6e, 0x73)))
OPCODES.update({name + "_RANGE": value + 6 for name, value in tuple(OPCODES.items())})


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capture(path, expected, size=None):
    limit = size if size is not None else 2 * 1024 * 1024
    with (ROOT / path).open("rb") as source:
        data = source.read(limit + 1)
    need(len(data) <= limit and (size is None or len(data) == size) and digest(data) == expected,
         f"Held input differs: {path}")
    return data


def parser(data):
    tree = ast.parse(data, filename=PARSER)
    selected = [node for node in tree.body if getattr(node, "name", None) in {"need", "Dex039"}]
    need([node.name for node in selected] == ["need", "Dex039"], "Parser closure differs")
    namespace = {"hashlib": hashlib, "struct": struct, "zlib": zlib, "MAX_BYTES": 64 * 1024 * 1024}
    exec(compile(ast.Module(body=selected, type_ignores=[]), PARSER, "exec"), namespace)
    return namespace["Dex039"]


def original_dex(profile, parser_type):
    archive, size, sha, member, dex_size, dex_sha = profile
    captured = capture(archive, sha, size)
    with zipfile.ZipFile(io.BytesIO(captured)) as zipper:
        candidates = [entry for entry in zipper.infolist() if entry.filename == member]
        need(len(candidates) == 1 and candidates[0].file_size == dex_size, "Selected DEX member extent")
        data = zipper.read(candidates[0])
    need(len(data) == dex_size and digest(data) == dex_sha, f"Selected DEX differs: {archive}")
    return parser_type(data)


def methods(path, sha, size, member):
    result = {}
    for line in capture(path, sha, size).splitlines():
        row = json.loads(line)
        if row["record"] != "method":
            continue
        body = row["body"]
        raw_body = line.split(b',"body":', 1)[1][:-1]
        need(digest(raw_body) == row["normalizedBodySha256"] and row["physicalDex"] == member
             and row["logicalHeaderOffset"] == 0, f"Decoded body provenance: {path}")
        name = body["signature"].partition("(")[0]
        need(name not in result, f"Ambiguous selected method: {path}/{name}")
        result[name] = row
    return result


def method_reference(dex, index):
    # The retained parser has already validated table extents and all method IDs.
    def string(index):
        offset = dex.u32(dex.u32(60) + index * 4)
        _, start = dex.uleb(offset, dex.sections[0x2002][1])
        end = dex.data.index(0, start, dex.sections[0x2002][1])
        return dex.data[start:end].decode("ascii")

    def descriptor(index):
        return string(dex.u32(dex.u32(68) + index * 4))

    need(index < dex.u32(88), "Invoke reference outside method table")
    owner, proto, name = struct.unpack_from("<HHI", dex.data, dex.u32(92) + index * 8)
    _, returns, parameters = struct.unpack_from("<III", dex.data, dex.u32(76) + proto * 12)
    args = "" if not parameters else "".join(
        descriptor(dex.u16(parameters + 4 + item * 2)) for item in range(dex.u32(parameters)))
    return f"{descriptor(owner)}->{string(name)}({args}){descriptor(returns)}"


def verify_calls(dex, row, calls):
    body = row["body"]
    key = (body["owner"] + "->" + body["signature"]).encode("ascii")
    entry = dex.methods[key]
    base = entry["codeOffset"]
    regs, _, _, tries, units = entry["header"]
    need(base and entry["flags"] == body["accessFlags"] and regs == body["registerCount"],
         f"Method header mismatch: {key!r}")
    need(sum(item["codeOffset"] == base for item in dex.methods.values()) == 1,
         f"Code item has another declared owner: {key!r}")
    try_start = base + 16 + 2 * (units + (units & 1))
    try_ranges = [struct.unpack_from("<IH", dex.data, try_start + i * 8) for i in range(tries)]
    need(set(try_ranges) == {(item["startPc"], item["codeUnits"]) for item in body["catches"]},
         f"Method try range mismatch: {key!r}")
    instructions = {ins["pc"]: ins for ins in body["instructions"]}
    edges = []
    for pc, expected_name in calls.items():
        ins = instructions[pc]
        at = base + 16 + 2 * pc
        need(0 <= pc <= units - 3 and ins["codeUnits"] == 3, f"Invoke extent at {key!r}:{pc}")
        word, reference, tail = struct.unpack_from("<3H", dex.data, at)
        need(ins["referenceKind"] == "method" and word & 0xff == OPCODES[ins["opcode"]],
             f"Invoke encoding at {key!r}:{pc}")
        if ins["opcode"].endswith("_RANGE"):
            need((word >> 8, tail) == (ins["registerCount"], ins["registerStart"]),
                 f"Invoke range at {key!r}:{pc}")
        else:
            registers = [(tail >> shift) & 15 for shift in (0, 4, 8, 12)] + [(word >> 8) & 15]
            need(word >> 12 <= 5 and registers[:word >> 12] == ins["registers"],
                 f"Invoke registers at {key!r}:{pc}")
        symbol = method_reference(dex, reference)
        need(symbol == ins["reference"] and symbol.partition("->")[2].partition("(")[0] == expected_name,
             f"Invoke reference at {key!r}:{pc}")
        edges.append({"pc": pc, "reference": symbol, "rawHex": dex.data[at:at + 6].hex()})
    return {"method": key.decode(), "index": entry["methodIndex"], "offset": base,
            "header": list(entry["header"]), "tryRanges": try_ranges, "bodySha256": row["normalizedBodySha256"],
            "rawInstructionsSha256": digest(dex.data[base + 16:base + 16 + units * 2]), "calls": edges}


def main():
    evidence = {path: capture(path, sha) for path, sha in SOURCE_PINS.items()}
    dex_type = parser(evidence[PARSER])
    groups = {}
    observations = {}
    for role, profile in ARCHIVES.items():
        dex = original_dex(profile, dex_type)
        if role == "SystemUI":
            queries = json.loads(evidence[SYSTEMUI + "METHOD-READBACK.json"])["queries"]
            names = APK_PROOFS
            for name in names:
                raw = queries[name]["stdout"]
                need(raw["path"] == APK_RAW + name + ".jsonl", "SystemUI proof locator")
                rows = methods(raw["path"], raw["sha256"], raw["bytes"], profile[3])
                need({(row["body"]["signature"], row["normalizedBodySha256"]) for row in rows.values()}
                     == {(row["signature"], row["normalizedBodySha256"]) for row in queries[name]["methods"]},
                     "SystemUI saved normalized proof")
                groups[name] = rows
            pool = json.loads(evidence["out/guest-pin-systemui-task-wrapper/POOL-PREFLIGHT.json"])
            need(pool["targetDexSha256"] == profile[5] and pool["pools"]["methods"] == dex.u32(88)
                 and pool["emitted"] is False and not dex.maps.get(0xf000), "Original unedited pool")
        else:
            names = ("lookup", "proxy", "stub") if role == "framework" else ("lss", "permission", "publication")
            for name in names:
                sel = json.loads(capture(INGRESS + "selected-" + name + ".json", INGRESS_PINS[name]))
                member = [row for row in sel["physicalLogicalDex"] if row["physicalDex"] == profile[3]]
                need(len(member) == 1 and member[0]["physicalDexSha256"] == profile[5]
                     and sel["archiveSha256"] == profile[2] and sel["readerExitCode"] == 0,
                     f"Staged query archive join: {name}")
                groups[name] = methods(sel["raw"], sel["rawSha256"], sel["rawBytes"], profile[3])
        observations[role] = [verify_calls(dex, groups[group][method], calls)
                              for (group, method), calls in CALLS.items() if group in names]

    raw_archives = json.loads(evidence[SYSTEMUI + "RAW-CODE-OWNERSHIP.json"])["archives"]
    owned, = (members["classes3.dex"]["methods"] for name, members in raw_archives.items()
              if name.endswith("SystemUI.apk"))
    for observed in observations["SystemUI"]:
        prior = owned[observed["method"]]
        need(prior["rawInstructionSha256"] == observed["rawInstructionsSha256"]
             and prior["code"]["header"] == observed["header"]
             and prior["code"]["codeOffset"] == observed["offset"]
             and prior["code"]["methodIndex"] == observed["index"], "SystemUI prior raw code owner")
    checker = observations["SystemUI"][1]
    need(checker["header"] == [14, 6, 8, 0, 24] and checker["calls"][0]["rawHex"] == "6e3040068009",
         "Original three-word AsyncTask start")

    task = groups["task"]["doInBackground"]["body"]
    need(task["catches"] == [{"startPc": 27, "codeUnits": 40,
                             "exceptionType": "Landroid/os/RemoteException;", "handlerPc": 68}],
         "Original worker catch")
    stub = {ins["pc"]: ins for ins in groups["stub"]["onTransact"]["body"]["instructions"]}
    cases = [item for item in stub[1308]["switchElements"] if item["key"] == 10]
    need(stub[13]["targetPc"] == 1308 and len(cases) == 1
         and 13 + cases[0]["offsetFromReferringSwitchPc"] == 1062, "Original transaction 10 case")
    proxy = {ins["pc"]: ins for ins in groups["proxy"]["checkCredential"]["body"]["instructions"]}
    need((proxy[32]["literal"], proxy[34]["literal"]) == (10, 32), "Original transaction code and flags")
    lss = groups["lss"]["checkCredential"]["body"]
    need(lss["catches"] == [{"startPc": 32, "codeUnits": 4, "exceptionType": None, "handlerPc": 43}],
         "Original guest restore and cleanup scope")
    selection = json.loads(evidence["inventory/installed-oneos-code-profile.json"])
    stage = selection["actualStageSelector"]
    image = json.loads(evidence[SYSTEMUI + "IMAGE-MEMBER-READBACK.json"])
    need((stage["versionCode"], stage["profile"], stage["set"], stage["image"])
         == (74, "s-ultra-8850", "x9u-in-sultra", "coloros17-findx9u-in")
         and selection["manifestEquality"]["exactEquality"]
         and image["cachedApk"]["sha256"] == ARCHIVES["SystemUI"][2], "Historical stage selection join")

    return {
        "status": "PASS_HELD_ORIGINAL_PIN_SOURCE_EDGES_ONLY",
        "routeAdmission": "REFUSED_MISSING_ACTUAL_OWNERS_AND_SELECTED_INTEGRATION",
        "stage": stage,
        "archives": {role: dict(zip(("path", "bytes", "sha256", "member", "memberBytes", "memberSha256"), profile))
                     for role, profile in ARCHIVES.items()},
        "verifiedOriginalCalls": observations,
        "evidencePins": SOURCE_PINS,
        "ingressSelectionPins": INGRESS_PINS,
        "originalGuestTransaction": {"code": 10, "flags": 32},
        "separatePrivateCheckTransaction": {"code": 2, "flags": 32, "selectedInGuest": False},
        "missing": [
            "Current selected runtime and exact source-owned task, callback and result-delivery hooks",
            "Actual live SystemUI caller occurrence and guest LSS before Binder identity clear",
            "Authenticated private host endpoint publication and delivery to the exact guest SystemServer",
            "Current physical subject lease covering the real Samsung call and explicit policy disposition",
            "Selected Binder/callback realm, source retirement and real queue/native custody",
        ],
        "productionBytesWritten": False,
        "oemOrDeviceExecution": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2))
    except (OSError, ValueError, TypeError, KeyError, IndexError, struct.error, zipfile.BadZipFile) as error:
        sys.exit(f"Held source proof refused: {error}")
