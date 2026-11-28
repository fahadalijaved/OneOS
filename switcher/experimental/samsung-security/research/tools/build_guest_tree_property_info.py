"""Serialize the complete three-file donor-only property_info input cohort offline."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import struct


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out/guest-tree-property-info-full"
DEFAULT = ("u:object_r:default_prop:s0", "string")
UNSET = (None, None)
MISSING = 0xFFFFFFFF
LIMIT = 1024 * 1024
NAME = re.compile(r"(?:[A-Za-z0-9_:@+$-]+\.)*[A-Za-z0-9_:@+$-]+\.?")
LABEL = re.compile(r"u:object_r:[a-zA-Z0-9_]+:s0")
SCALARS = {"bool", "int", "uint", "double", "string"}
SCOPE = "out/guest-tree-property-partition-closure/receipt.json"
SCHEMA = "out/guest-tree-property-info/fixture-v1/receipt.json"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def plain(info):
    return not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400


def read_fixed(path, size):
    before = path.lstat()
    require(plain(before) and stat.S_ISREG(before.st_mode) and before.st_size == size,
            f"Plain exact-size input: {path}")
    with path.open("rb") as stream:
        raw = stream.read(size + 1)
    after = path.lstat()
    require(len(raw) == size and plain(after) and
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            "Input stable through bounded read")
    return raw


@dataclass(frozen=True)
class Rule:
    name: str
    exact: bool
    value: tuple


def parse_contexts(raw):
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(b"#"):
            continue
        fields = line.decode("ascii").split()
        require(len(fields) >= 2, "Property name and SELinux context")
        name, context = fields[:2]
        exact = len(fields) > 2 and fields[2] == "exact"
        require((NAME.fullmatch(name) or (name == "*" and not exact)) and len(name) <= 256 and
                len(name.split(".")) <= 24 and (not exact or not name.endswith(".")) and
                LABEL.fullmatch(context), "Pinned property-context name/label profile")
        require(len(fields) == 2 or fields[2] in ("exact", "prefix"), "Known match token")
        types = fields[3:]
        require(not types or (len(types) == 1 and types[0] in SCALARS) or
                (len(types) >= 2 and types[0] == "enum"), "Known held type tokens")
        result.append(Rule(name, exact, (context, " ".join(types) or None)))
    return result


@dataclass
class Node:
    value: tuple = UNSET
    children: dict = field(default_factory=dict)
    prefixes: dict = field(default_factory=dict)
    exact: dict = field(default_factory=dict)


def make_tree(rules):
    root = Node(DEFAULT)
    seen = set()
    for rule in rules:
        identity = (rule.name, rule.exact)
        require(identity not in seen, f"Duplicate {'exact' if rule.exact else 'prefix'} {rule.name}")
        seen.add(identity)
        parent, *parts = root, *rule.name.split(".")
        for part in parts[:-1]:
            parent = parent.children.setdefault(part, Node())
        name = parts[-1]
        if not name:
            parent.value = rule.value
        else:
            matches = parent.exact if rule.exact else parent.prefixes
            matches[name] = rule.value
    return root


def serialize(root, rules):
    context_ids = {v: i for i, v in enumerate(sorted({DEFAULT[0], *(r.value[0] for r in rules)}))}
    type_ids = {v: i for i, v in enumerate(sorted({"", DEFAULT[1], *(r.value[1] or "" for r in rules)}))}
    raw = bytearray(24)

    def append(data):
        start = len(raw)
        raw.extend(data)
        raw.extend(b"\0" * (-len(raw) % 4))
        require(len(raw) <= LIMIT, "Serialized property_info capacity")
        return start

    def words(values):
        return append(struct.pack(f"<{len(values)}I", *values)) if values else 0

    def string(value):
        return append(value.encode("ascii") + b"\0")

    def table(values):
        start = append(bytes((len(values) + 1) * 4))
        refs = [string(value) for value in values]
        struct.pack_into(f"<{len(refs) + 1}I", raw, start, len(refs), *refs)
        return start

    def entry(name, value):
        context, kind = value
        offset = append(bytes(16))
        struct.pack_into("<4I", raw, offset, string(name), len(name),
                         context_ids.get(context, MISSING), type_ids.get(kind, MISSING))
        return offset

    def node(name, tree):
        offset = append(bytes(28))
        own = entry(name, tree.value)
        prefixes = [entry(n, tree.prefixes[n]) for n in sorted(tree.prefixes, key=lambda n: (-len(n), n))]
        exact = [entry(n, tree.exact[n]) for n in sorted(tree.exact)]
        children = [node(n, tree.children[n]) for n in sorted(tree.children)]
        struct.pack_into("<7I", raw, offset, own, len(children), words(children),
                         len(prefixes), words(prefixes), len(exact), words(exact))
        return offset

    contexts, types = table(context_ids), table(type_ids)
    trie = node("root", root)
    struct.pack_into("<6I", raw, 0, 1, 1, len(raw), contexts, types, trie)
    return bytes(raw)


def decode(raw):
    """Walk offset structures and reconstruct source rules without writer state."""
    require(24 <= len(raw) <= LIMIT and len(raw) % 4 == 0, "Bounded binary frame")
    occupied = bytearray(len(raw) // 4)

    def claim(at, count):
        require(at % 4 == 0 and count > 0 and at + count * 4 <= len(raw), "In-bounds aligned record")
        first = at // 4
        require(not any(occupied[first:first + count]), "Disjoint serialized records")
        occupied[first:first + count] = b"\1" * count

    def words(at, count):
        claim(at, count)
        return struct.unpack_from(f"<{count}I", raw, at)

    def string(at):
        require(24 <= at < len(raw), "Valid text offset")
        end = raw.find(b"\0", at, at + 513)
        require(end >= at, "Terminated string")
        slots = (end - at + 4) // 4
        claim(at, slots)
        require(not any(raw[end:at + 4 * slots]), "No data in string padding")
        return raw[at:end].decode("ascii")

    def table(at):
        count, = words(at, 1)
        require(0 < count <= 4096, "Bounded string table")
        values = tuple(string(ref) for ref in words(at + 4, count))
        require(tuple(sorted(set(values))) == values, "Sorted unique string table")
        return values

    version, minimum, size, c_ref, t_ref, root = words(0, 6)
    require((version, minimum, size) == (1, 1, len(raw)), "Exact v1 area framing")
    contexts, types = table(c_ref), table(t_ref)
    observed = {}
    counts = Counter()

    def entry(at):
        ref, length, ci, ti = words(at, 4)
        name = string(ref)
        require(len(name) == length and name and "." not in name and
                (ci == MISSING or ci < len(contexts)) and (ti == MISSING or ti < len(types)),
                "Exact serialized name/index bounds")
        return name, (contexts[ci] if ci != MISSING else None, types[ti] if ti != MISSING else None)

    def record(name, exact, value):
        key = (name, exact)
        require(key not in observed and value[0] is not None, "Unique actual serialized rule")
        observed[key] = value

    def offsets(at, count):
        require(count <= 4096 and bool(at) == bool(count), "Bounded count and offset pair")
        return words(at, count) if count else ()

    def walk(at, stem, depth):
        require(depth <= 24, "Bounded trie depth")
        counts["nodes"] += 1
        own, nc, children, np, prefixes, ne, exact = words(at, 7)
        name, value = entry(own)
        if depth == 0:
            require(name == "root" and value == DEFAULT, "Original root defaults")
        else:
            require(NAME.fullmatch(name), "Valid trie segment")
            stem += name + "."
            if value != UNSET:
                record(stem, False, value)
                counts["dottedPrefixes"] += 1
        matches = []
        for ref in offsets(prefixes, np):
            key, meta = entry(ref)
            record(stem + key, False, meta)
            matches.append((key, meta))
        require([len(k) for k, _ in matches] == sorted((len(k) for k, _ in matches), reverse=True),
                "Longest prefix first")
        terminal = {}
        for ref in offsets(exact, ne):
            key, meta = entry(ref)
            record(stem + key, True, meta)
            terminal[key] = meta
        offspring = dict(walk(ref, stem, depth + 1) for ref in offsets(children, nc))
        require(len(offspring) == nc and list(offspring) == sorted(offspring), "Ordered unique child edges")
        counts["partialPrefixes"] += np
        counts["exact"] += ne
        return name, (value, matches, terminal, offspring)

    _, decoded = walk(root, "", 0)
    require(all(occupied), "All serialized bytes reachable")
    return decoded, observed, counts, (len(contexts), len(types))


def override(old, new):
    return tuple(previous if replacement is None else replacement
                 for previous, replacement in zip(old, new))


def lookup(decoded, key):
    current = UNSET
    while True:
        own, prefixes, exact, children = decoded
        current = override(current, own)
        for prefix, value in prefixes:
            if key.startswith(prefix):
                current = override(current, value)
                break
        first, dot, rest = key.partition(".")
        if dot and first in children:
            decoded, key = children[first], rest
        else:
            return override(current, exact.get(key, UNSET))


def verify_rules(raw, rules, critical):
    tree, actual, counts, table_sizes = decode(raw)
    expected = {(rule.name, rule.exact): rule.value for rule in rules}
    require(len(expected) == len(rules) and actual == expected, "All original rules round trip exactly")
    # Flat reference: use source stems to reproduce native inheritance, without
    # constructing the writer trie or consuming its order/offsets.
    dotted = {r.name: r.value for r in rules if not r.exact and r.name.endswith(".")}
    partial = defaultdict(list)
    exact = {r.name: r.value for r in rules if r.exact}
    for r in rules:
        if not r.exact and not r.name.endswith("."):
            partial[r.name.rpartition(".")[0]].append(r)

    def reference(key):
        result = DEFAULT
        segments = key.split(".")
        for n in range(len(segments)):
            stem = ".".join(segments[:n])
            result = override(result, dotted.get(stem + ".", UNSET))
            matches = [r for r in partial[stem] if key.startswith(r.name)]
            if matches:
                result = override(result, max(matches, key=lambda r: len(r.name)).value)
        return override(result, exact.get(key, UNSET))

    probes = set(critical)
    for r in rules:
        probes.add(r.name if r.exact or not r.name.endswith(".") else r.name[:-1])
        if not r.exact:
            probes.add(r.name + "oneos_readback")
    probes.add("oneos_property_info_unknown_test")
    require(all(lookup(tree, key) == reference(key) for key in probes),
            "All selected rule probes agree with independent source matching")
    return {"counts": dict(counts), "contextTableCount": table_sizes[0], "typeTableCount": table_sizes[1],
            "exactRuleRoundTrips": len(rules), "lookupProbeCount": len(probes),
            "criticalKeyMetadata": {key: lookup(tree, key) for key in sorted(critical)}}


def derive():
    pins = {}

    def load(name, size, expected):
        raw = read_fixed(ROOT / name, size)
        require(digest(raw) == expected, f"Exact held source {name}")
        pins[name] = {"bytes": size, "sha256": expected}
        return raw

    closure = json.loads(load(SCOPE, 8812, "51035239d621deb1b5af68e409f3a5e1c8d78bccd7476ec42d13a92eb461a875"))
    schema = json.loads(load(SCHEMA, 5898, "20ab070525549d3db9dabe27ffb06103471905c8389d66261f8ec33a8067a764"))
    require(closure["completeDonorSourceCohort"] is True and closure["actualStagedContextCohort"] is None
            and closure["hostContextsUsed"] is False and closure["compilerInputOrder"] == [
                row["source"] for row in closure["contextSlots"] if row["status"] == "PRESENT_DONOR_CONTEXT"]
            and [row["firstAbsentComponent"] for row in closure["contextSlots"]
                 if row["status"] == "ABSENT_IN_BARE_DONOR_ROOT"] == ["/vendor/etc", "/vendor/odm"],
            "Exact donor-only sources with two proved absent slots")
    require(schema["nativeSchema"]["rootDefaults"] == {"context": DEFAULT[0], "type": DEFAULT[1]},
            "Original default policy metadata")
    init = load("../firmware/donor/extracted/system/bin/init", 2888328,
                "8db6b39facd5af0745d9bd27c588dacedb6ae5e21a87870644d0b49d33e19757")
    libc = load("../firmware/donor/apex/005-com.android.runtime/files/lib64/bionic/libc.so", 1550096,
                "c9057b270a62b45b0dcae87e5d6a187a2dde1e7f86f8a2e0d68f2eb180e57d99")
    additional = {
        "init": {0x105DC8: "f3900194", 0x16A454: "402b0054", 0x16A45C: "f5031f2a",
                 0x16A468: "f32a00b4", 0x16A9BC: "35008052", 0x16B458: "20040036",
                 0x16B798: "02d50494", 0x16B7D0: "770000b4", 0x16B82C: "88130036",
                 0x16BAA0: "b70700b4", 0x16BB18: "00feff35", 0x16BBFC: "00feff35",
                 0x16BC08: "e80700b5", 0x16C644: "8a0100b4", 0x16C674: "16008012",
                 0x16C92C: "1a0d00b9", 0x16C9CC: "131100b9", 0x16CB10: "131500b9", 0x16CBA8: "1c1900b9"},
        "libc": {0xA2B4C: "820640b9", 0xA2B30: "80030034", 0xA2BA4: "880a40b9",
                 0xA2BEC: "080d40b9", 0xA2CE8: "75ffff97", 0xA2D70: "76ee0194",
                 0xA2DD0: "48ef0194", 0xA2DD4: "e0030034", 0xA2E60: "080940b9", 0xA2E94: "080d40b9"},
    }
    for raw, old, new in ((init, "writerPcBytes", "init"), (libc, "readerPcBytes", "libc")):
        require(all(raw[int(pc, 16):int(pc, 16) + 4].hex() == code
                    for pc, code in schema["nativeSchema"][old].items()), "Same donor v1 schema instructions")
        require(all(raw[pc:pc + 4].hex() == code for pc, code in additional[new].items()),
                "Exact prefix, type inheritance and parser native anchors")
    require(init.startswith(b"Duplicate prefix match detected for '", 0x13F34) and
            init.startswith(b"Duplicate exact match detected for '", 0x2C4AF), "Original duplicate failures")

    rules = []
    rows_per_file = []
    for name in closure["compilerInputOrder"]:
        pin = closure["pins"][name]
        selected = parse_contexts(load(name, pin["bytes"], pin["sha256"]))
        rows_per_file.append(len(selected))
        rules.extend(selected)
    require(rows_per_file == [1431, 822, 2], "Exact full rule counts")
    boot = json.loads(load("out/guest-tree-boot-properties/receipt.json", 13744,
        "e7e458a1541ee25f7a5b5432a12ec6e2fd76c0809c50fb2c37d53ed0b901985e"))
    critical = set(boot["declarationsInElevenPinnedFiles"])
    critical.update(("ro.build.version.sdk_full", "ro.build.version.known_codenames", "zygote.critical_window.minute"))
    artifact = serialize(make_tree(rules), rules)
    verified = verify_rules(artifact, rules, critical)
    require(verified["criticalKeyMetadata"]["ro.build.version.sdk"] ==
            ("u:object_r:build_prop:s0", "int") and verified["criticalKeyMetadata"]["ro.build.version.codename"] ==
            ("u:object_r:build_prop:s0", "string"), "Selected boot schema stays exact")
    receipt = {
        "schema": "oneos-guest-tree-full-property-info/v1",
        "status": "FULL_DONOR_ONLY_CONTEXT_BINARY_VERIFIED_OFFLINE",
        "toolSha256": digest(Path(__file__).read_bytes()), "pins": pins,
        "compilerInputOrder": closure["compilerInputOrder"], "rowsPerFile": rows_per_file,
        "nativeSchemaAnchors": additional,
        "output": {"bytes": len(artifact), "sha256": digest(artifact)},
        "readback": verified,
        "scope": "Original v1 schema and lookup semantics for the unchanged three-file donor cohort. Serializer byte order is authored and deterministic.",
        "hostContextsUsed": False, "effectiveValues": None, "runtimePropertyInfoAdmitted": False,
        "entryAdmitted": False, "targetExecuted": False,
    }
    return artifact, rules, critical, (json.dumps(receipt, indent=2) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        artifact, rules, critical, receipt = derive()
        for directory in (OUT.parent, OUT, OUT / "donor-v1"):
            if args.stage:
                directory.mkdir(exist_ok=directory != OUT / "donor-v1")
            info = directory.lstat()
            require(plain(info) and stat.S_ISDIR(info.st_mode), "Plain private output directory")
        for name, expected in (("property_info.donor.bin", artifact), ("receipt.json", receipt)):
            path = OUT / "donor-v1" / name
            if args.stage:
                with path.open("xb") as stream:
                    stream.write(expected)
            saved = read_fixed(path, len(expected))
            if name.endswith(".bin"):
                verify_rules(saved, rules, critical)
            require(saved == expected, f"Exact saved artifact: {name}")
            print(f"{path.relative_to(ROOT).as_posix()} {len(saved)} {digest(saved)}")
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        parser.exit(2, f"Refused: {error}\n")


if __name__ == "__main__":
    main()
