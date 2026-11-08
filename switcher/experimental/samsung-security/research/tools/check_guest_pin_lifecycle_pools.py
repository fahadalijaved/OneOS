"""Check the raw identifier union for the unselected donor PIN lifecycle DEX."""
import argparse
import ast
import collections
import hashlib
import json
from pathlib import Path
import struct
import zipfile
import zlib

ROOT = Path(__file__).absolute().parents[1]
SOURCE_SHA = "793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071"
HELPER_SHA = "2a22b567f46f7b6d3beee281f0c99f52de4359e1debd23773f5cf89752a81e4f"
SOURCE_APK_SHA = "0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77"
MAX_BYTES = 16 * 1024 * 1024
CONTROLLER = b"Lcom/oplus/keyguard/security/view/OplusKeyguardAbsKeyInputViewController;"
CHECKER = b"Lcom/oplus/keyguard/security/OplusLockPatternChecker;"
SLOT = b"Lcom/oplus/keyguard/security/GuestPinCheckRequest$Slot;"
FIELD = b"oneos$pinSlot"
CONTROLLER_METHOD = b"oneos$retirePinAtLifecycleEntry"
CHECKER_METHOD = b"oneos$retirePinForController"
BRIDGE_PROTO = (b"V", (CONTROLLER,))
NO_INDEX = 0xffffffff
READERS = {
    "tools/preflight_guest_metrics_parent_payload.py": (
        "d076c60a4c16774e1a8b75377661caf814a4eb4a72420f4082bc493dc4dce9ea", {"need", "uleb", "Dex"}),
    "tools/prepare_guest_locksettings_proxy_retarget.py": (
        "a5492ba8dcd69edc9d62c24e2c200e487baedfc5ad1e271a3d055a6a1da1394a", {"raw_ids"}),
    "tools/prepare_guest_policy_init_retarget.py": (
        "596a6c498ec3dd09c36d9244a1bfe7c56551e93cb91875c43d89ecdd52faa878", {"ordered_ids", "raw_map"}),
    "tools/audit_coloros_raw_debug_baseline.py": (
        "1f534cd230d0a2605baed71abf8afebf2f0868186fd9204a0090a9ea666123b0", {"RawDebug"}),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounded(path, limit=MAX_BYTES):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    need(0 < len(data) <= limit, f"Input size outside bound: {path}")
    return data


def load_readers():
    scope = {"need": need, "digest": digest, "struct": struct, "hashlib": hashlib,
             "json": json, "zlib": zlib, "collections": collections}
    for name, (expected, symbols) in READERS.items():
        raw = bounded(ROOT / name, 128 * 1024)
        need(digest(raw) == expected, f"Read-only parser input changed: {name}")
        tree = ast.parse(raw, filename=name)
        tree.body = [n for n in tree.body
                     if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in symbols]
        need(len(tree.body) == len(symbols) and {n.name for n in tree.body} == symbols,
             f"Exact read-only parser definitions missing: {name}")
        exec(compile(tree, name, "exec", dont_inherit=True), scope)
    return scope


def utf16(value):
    return value.replace(b"\xc0\x80", b"\0").decode("utf-8", "surrogatepass").encode("utf-16-be", "surrogatepass")


def symbolic(dex, readers):
    rows = readers["raw_ids"](dex)
    readers["ordered_ids"](dex, {"raw_ids": lambda _: rows})
    strings = dex.strings
    need(all(length == len(utf16(value)) // 2 for value, (length, _) in
             zip(strings, rows["stringsWithUtf16Length"])), "Raw string UTF-16 size differs")
    types = [strings[index] for index in rows["typeStringIndices"]]
    protos = []
    for shorty, result, (present, args) in rows["protoShortyResultAndParams"]:
        descriptor = types[result], tuple(types[arg] for arg in args)
        short = lambda type_name: b"L" if type_name[:1] in (b"L", b"[") else type_name
        need(bool(args) == present and strings[shorty] ==
             short(descriptor[0]) + b"".join(short(arg) for arg in descriptor[1]),
             "Raw proto shorty or parameter-list presence differs")
        protos.append(descriptor)
    fields = {(types[owner], strings[name], types[value]) for owner, value, name in
              rows["fieldClassTypeNameIndices"]}
    methods = {(types[owner], strings[name], protos[proto]) for owner, proto, name in
               rows["methodClassProtoNameIndices"]}
    classes = {}
    for owner, flags, parent, (present, interfaces), file in rows["classStructuralIndices"]:
        need(owner < len(types) and (parent == NO_INDEX or parent < len(types))
             and (file == NO_INDEX or file < len(strings)), "Raw class-def index differs")
        classes[types[owner]] = (
            flags, None if parent == NO_INDEX else types[parent], present,
            tuple(types[index] for index in interfaces), None if file == NO_INDEX else strings[file],
        )
    return {"strings": set(strings), "types": set(types), "protos": set(protos),
            "fields": fields, "methods": methods, "classes": classes}


def expected_union(original, helper):
    need(not original["classes"].keys() & helper["classes"].keys(), "Helper class collision")
    result = {kind: original[kind] | helper[kind] for kind in
              ("strings", "types", "protos", "fields", "methods")}
    field = CHECKER, FIELD, SLOT
    methods = {(CONTROLLER, CONTROLLER_METHOD, BRIDGE_PROTO),
               (CHECKER, CHECKER_METHOD, BRIDGE_PROTO)}
    need(field not in result["fields"] and not methods & result["methods"],
         "Additive bridge or field collides")
    need({CONTROLLER, CHECKER, SLOT, b"V"} <= result["types"], "Bridge type absent from held inputs")
    result["strings"].update({FIELD, CONTROLLER_METHOD, CHECKER_METHOD, b"VL"})
    result["protos"].add(BRIDGE_PROTO)
    result["fields"].add(field)
    result["methods"].update(methods)
    result["classes"] = original["classes"] | helper["classes"]
    return result


def compare_members(source, helper, target):
    def declarations(dex):
        entries = {r["descriptor"]: (r["partition"], r["accessFlags"], bool(r["codeOffset"]))
                   for r in dex.members}
        need(len(entries) == len(dex.members), "Duplicate encoded member declaration")
        return entries
    originals, helpers = declarations(source), declarations(helper)
    need(not originals.keys() & helpers.keys(), "Encoded helper member collision")
    expected = originals | helpers
    suffix = "(" + CONTROLLER.decode("ascii") + ")V"
    expected[CONTROLLER.decode("ascii")+"->"+CONTROLLER_METHOD.decode("ascii")+suffix] = (
        "directMethods", 0x0a, True)
    expected[CHECKER.decode("ascii")+"->"+CHECKER_METHOD.decode("ascii")+suffix] = (
        "virtualMethods", 0x11, True)
    expected[CHECKER.decode("ascii")+"->"+FIELD.decode("ascii")+":"+SLOT.decode("ascii")] = (
        "instanceFields", 0x02, False)
    need(declarations(target) == expected, "Candidate declaration delta differs")


def validate(source, helper, candidate):
    """Validate exact held inputs and a candidate. The result covers pools/maps/declarations."""
    for raw in (source, helper, candidate):
        need(isinstance(raw, bytes) and 112 <= len(raw) <= MAX_BYTES, "Ordinary DEX input byte bound")
    need(digest(source) == SOURCE_SHA and digest(helper) == HELPER_SHA, "Held donor/helper bytes differ")
    readers = load_readers()
    base, addition, result = (readers["Dex"](raw) for raw in (source, helper, candidate))
    original, supplemental, actual = (symbolic(dex, readers) for dex in (base, addition, result))
    expected = expected_union(original, supplemental)
    for kind, planned in expected.items():
        need(actual[kind] == planned, f"Unexpected raw {kind} union")
    for kind in ("types", "protos", "fields", "methods"):
        need(len(actual[kind]) <= 65536, f"16-bit pool overflow: {kind}")
    compare_members(base, addition, result)
    source_sections = {r["type"] for r in base.map}
    helper_sections = {r["type"] for r in addition.map}
    candidate_sections = {r["type"] for r in result.map}
    need(candidate_sections == source_sections | helper_sections
         and 0xf000 not in candidate_sections, "Unexpected map section or HAPI")
    map_proof = readers["raw_map"](result, {"Debug": readers["RawDebug"]})
    return {"status": "PASS_GUEST_PIN_LIFECYCLE_RAW_POOLS_AND_MAP_ONLY",
            "sourceSha256": SOURCE_SHA, "helperSha256": HELPER_SHA,
            "candidateSha256": digest(candidate), "candidateBytes": len(candidate),
            "poolCounts": result.counts,
            "addedPoolCountsOverDonor": {k:len(actual[k])-len(original[k]) for k in actual},
            "map": map_proof, "selected": False, "deviceEligible": False}


def source_input(path):
    if path.suffix.lower() != ".apk":
        return bounded(path)
    with path.open("rb") as stream:
        need(hashlib.file_digest(stream, "sha256").hexdigest() == SOURCE_APK_SHA,
             "Held donor APK digest differs")
        stream.seek(0)
        with zipfile.ZipFile(stream) as apk:
            entries = [row for row in apk.infolist() if row.filename == "classes3.dex"]
            need(len(entries) == 1 and entries[0].file_size <= MAX_BYTES, "Unique donor classes3 entry required")
            return apk.read(entries[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Held classes3.dex or exact donor SystemUI APK")
    parser.add_argument("helper", type=Path, help="Held relocated lifecycle helper DEX")
    parser.add_argument("candidate", type=Path, help="Standalone emitted DEX")
    args = parser.parse_args()
    print(json.dumps(validate(source_input(args.source), bounded(args.helper), bounded(args.candidate)), indent=2))


if __name__ == "__main__":
    main()

