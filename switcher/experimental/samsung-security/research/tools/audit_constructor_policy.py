"""Pin one Samsung pre-construction feature from the captured OS, without OEM execution.

Copies only an exact regular XML member into ignored firmware/. The capture's
whole-tar hash is inherited; the selected member is freshly hash-verified.
"""
import gzip
import hashlib
import json
import tarfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
FEATURE = "SEC_FLOATING_FEATURE_COMMON_SUPPORT_UNPACK"
MEMBER = "system/etc/floating_feature.xml"
REPORT = PARENT / "out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/report.json"
REPORT_SHA = "c1785505f9f01ac922c48dc31e3fd8e2489630a9730489fc5bd27dcfaf9a8733"
XML_SHA = "85d71f9af973548ca1dfcebc3186f50bf5a0b2b8eab2426ad89ce452606dcc78"
SPM_SHA = "def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6"
BODY_SHA = "8333af13ad4aa856f7510052ff423324b568a517aae3a5c8ddf75daa7a8cc1c8"
FEATURE_RECEIPT = "out/tooling/20261105T143820960848Z-4e0c2a667b4d4a618badfbdc2d4f5c09/receipt.json"
FEATURE_RECEIPT_SHA = "1b9da1e123541c6d227a03dad7794aff3222b018dc33bf608919ccccfd8557af"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    if sha(REPORT) != REPORT_SHA:
        raise ValueError("Frozen physical-index report differs")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    manifest = REPORT.parent / "samsung-manifest.jsonl.gz"
    if sha(manifest) != report["outputs"][manifest.name]:
        raise ValueError("Physical file manifest differs")
    with gzip.open(manifest, "rt", encoding="utf-8") as stream:
        selected = [row for line in stream if (row := json.loads(line))["path"] == MEMBER]
    if len(selected) != 1 or selected[0]["kind"] != "file" or selected[0]["sha256"] != XML_SHA:
        raise ValueError("One exact regular feature file required")
    record = selected[0]
    if not 0 < record["size"] <= 1024 * 1024:
        raise ValueError("Selected XML size outside bound")
    archive = PARENT / report["samsungArchive"]
    before = archive.stat()
    if before.st_size != 20434769920:
        raise ValueError("Named capture size differs")
    rawdir = ROOT / "firmware/construction-policy"
    rawdir.mkdir(parents=True, exist_ok=True)
    dest = rawdir / "samsung-floating_feature.xml"
    freshly_copied = False
    if not dest.exists():
        partial = rawdir / (uuid.uuid4().hex + ".partial")
        with tarfile.open(archive, "r:") as tar:
            members = [item for item in tar if item.name.rstrip("/") == record["originalPath"]]
            if len(members) != 1 or not members[0].isfile() or members[0].size != record["size"]:
                raise ValueError("Only the exact unique regular member may be copied")
            with tar.extractfile(members[0]) as source, partial.open("xb") as output:
                output.write(source.read(record["size"] + 1))
        if partial.stat().st_size != record["size"] or sha(partial) != XML_SHA:
            raise ValueError("Selected member bytes differ")
        partial.rename(dest)
        freshly_copied = True
    if dest.stat().st_size != record["size"] or sha(dest) != XML_SHA:
        raise ValueError("Retained XML bytes differ")
    after = archive.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Capture changed during selected read")

    query_path = ROOT / "out/construction-credentials/receipts.json"
    queries = json.loads(query_path.read_text(encoding="utf-8"))["queries"]
    queries = [q for q in queries if q["class"] == "com.android.server.locksettings.SyntheticPasswordManager"]
    if len(queries) != 1:
        raise ValueError("Exact SPM source query required")
    receipt_path = ROOT / queries[0]["receipt"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw = ROOT / receipt["raw"]
    if receipt["archiveSha256"] != SPM_SHA or sha(Path(receipt["archive"])) != SPM_SHA or sha(raw) != receipt["rawSha256"]:
        raise ValueError("Original SPM archive/raw identity differs")
    rows = [row for line in raw.read_text(encoding="utf-8").splitlines()
            if (row := json.loads(line))["record"] == "method" and row["body"]["signature"] == "<clinit>()V"]
    if len(rows) != 1 or rows[0]["normalizedBodySha256"] != BODY_SHA:
        raise ValueError("Selected source initializer differs")
    instructions = {item["pc"]: item for item in rows[0]["body"]["instructions"]}
    if instructions[22]["reference"] != "string=" + FEATURE or instructions[25]["reference"] != "Lcom/samsung/android/feature/SemFloatingFeature;->getBoolean(Ljava/lang/String;)Z":
        raise ValueError("Selected feature/getter source edge differs")
    feature_receipt_path = ROOT / FEATURE_RECEIPT
    if sha(feature_receipt_path) != FEATURE_RECEIPT_SHA:
        raise ValueError("Frozen SemFloatingFeature source receipt differs")
    feature_receipt = json.loads(feature_receipt_path.read_text(encoding="utf-8"))
    feature_raw = ROOT / feature_receipt["raw"]
    if sha(feature_raw) != feature_receipt["rawSha256"] or sha(Path(feature_receipt["archive"])) != feature_receipt["archiveSha256"]:
        raise ValueError("Feature getter/parser archive or raw bytes differ")
    feature_methods = [row for line in feature_raw.read_text(encoding="utf-8").splitlines()
                       if (row := json.loads(line))["record"] == "method"]
    feature_bodies = {row["body"]["signature"]: row for row in feature_methods}
    load = {item["pc"]: item for item in feature_bodies["loadFeatureFile()V"]["body"]["instructions"]}
    if load[98]["reference"] != "Ljava/lang/String;->trim()Ljava/lang/String;":
        raise ValueError("Original XML scalar trimming differs")
    elements = [element for element in ET.parse(dest).getroot().iter() if element.tag == FEATURE]
    if len(elements) > 1:
        raise ValueError("Ambiguous selected feature")
    literal = elements[0].text if elements else None
    if literal is not None and len(literal) > 32:
        raise ValueError("Selected feature scalar outside bound")
    # Java String.trim removes only characters <= U+0020, not all Unicode space.
    parsed_literal = literal.strip("".join(chr(value) for value in range(33))) if literal is not None else None
    result = {
        "schema": "samsung-constructor-policy/v1",
        "classification": "Captured XML and source initializer only; live policy and executable binding unproved",
        "capture": {"report": REPORT.relative_to(PARENT).as_posix(), "reportSha256": REPORT_SHA,
                    "manifestSha256": sha(manifest), "archiveSha256Inherited": report["samsungArchiveSha256"],
                    "wholeArchiveHashFreshlyRecomputed": False, "selectedMember": MEMBER,
                    "selectedBytes": record["size"], "selectedSha256": XML_SHA,
                    "copiedFromTarThisRun": freshly_copied, "retainedMemberHashFreshlyVerified": True},
        "source": {"archiveSha256": SPM_SHA, "owner": "Lcom/android/server/locksettings/SyntheticPasswordManager;",
                   "method": "<clinit>()V", "bodySha256": BODY_SHA, "logicalHeaderOffset": rows[0]["logicalHeaderOffset"],
                   "featureLiteralPc": 22, "getterPc": 25, "receipt": receipt_path.relative_to(ROOT).as_posix(),
                   "receiptSha256": sha(receipt_path), "raw": raw.relative_to(ROOT).as_posix(), "rawSha256": sha(raw)},
        "featureParserSource": {"receipt": FEATURE_RECEIPT, "receiptSha256": FEATURE_RECEIPT_SHA,
                                "archiveSha256": feature_receipt["archiveSha256"],
                                "raw": feature_raw.relative_to(ROOT).as_posix(), "rawSha256": sha(feature_raw),
                                "selectedMethods": [{"method": name, "bodySha256": feature_bodies[name]["normalizedBodySha256"]}
                                                    for name in ["<init>()V", "loadFeatureFile()V", "getBoolean(Ljava/lang/String;)Z"]]},
        "selectedFeature": {"name": FEATURE, "presentInCapturedXml": bool(elements), "literal": literal,
                            "capturedBooleanParseResult": parsed_literal is not None and parsed_literal.lower() == "true"},
        "suppliedDonorExactPathPresent": (PARENT / "firmware/donor/extracted" / MEMBER).exists(),
        "limits": ["One selected feature only; no full feature-policy closure",
                   "Missing donor path does not prove an active policy difference for the selected feature",
                   "Preserve owned Samsung configuration before original class initialization; do not infer live state from archive defaults"],
        "oemCodeExecuted": False, "phoneChanged": False,
        "toolSha256": sha(Path(__file__).resolve()),
    }
    (ROOT / "inventory/construction-policy.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"inventory": "inventory/construction-policy.json", "selectedFeature": result["selectedFeature"],
                      "suppliedDonorExactPathPresent": result["suppliedDonorExactPathPresent"], "oemCodeExecuted": False}))


if __name__ == "__main__":
    main()
