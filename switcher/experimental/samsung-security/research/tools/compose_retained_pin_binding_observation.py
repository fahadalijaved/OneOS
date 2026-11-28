"""Stage a trailing physical-user observation after retained host control checks."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path("com/appleexploit/oneos/security/authority")
BASE = Path("compat/android") / PACKAGE / "PreparedRetainedPinBinding.java"
BASE_BYTES = 24405
BASE_SHA256 = "f7f006d2d9db467d46abb1a14f94bcabd63f5e63f6218b1eef43d926729a35ed"
OUT = ROOT / "out/retained-pin-binding-observation"

RESAMPLE = (
    b"        current.same(metadata.readCurrent(current));\n"
    b"        subject.same(metadata.readSubject(current.id, subject));\n"
)
CONTROL = b"        metadata.checkControl();\n"
CAPTURE_TAIL = b"        return new PreparedRetainedPinBinding(metadata, current, subject);\n"
EDITS = (
    (
        b"        Subject subject = metadata.readSubject(current.id, null);\n"
        + RESAMPLE + CONTROL + CAPTURE_TAIL,
        b"        Subject subject = metadata.readSubject(current.id, null);\n"
        + CONTROL + RESAMPLE + CAPTURE_TAIL,
    ),
    (
        b"    public void checkStillBound() {\n" + CONTROL + RESAMPLE + RESAMPLE + CONTROL + b"    }\n",
        b"    public void checkStillBound() {\n" + CONTROL + RESAMPLE + CONTROL + RESAMPLE + b"    }\n",
    ),
)


def replace_once(raw, before, after):
    if raw.count(before) != 1 or after in raw:
        raise ValueError("Exact retained PIN observation anchor changed")
    return raw.replace(before, after, 1)


def reorder(source):
    staged = source
    for before, after in EDITS:
        staged = replace_once(staged, before, after)
    inverse = staged
    for before, after in reversed(EDITS):
        inverse = replace_once(inverse, after, before)
    if inverse != source:
        raise ValueError("Physical-user observation has no exact whole-source inverse")
    return staged


def pin(path, raw):
    return {"path": path.as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def compose():
    original = ROOT / BASE
    if original.resolve(strict=True) != original or not original.is_file():
        raise ValueError("Expected the retained binding source at its exact repository path")
    with original.open("rb") as stream:
        source = stream.read(BASE_BYTES + 1)
    base = pin(BASE, source)
    if base["bytes"] != BASE_BYTES or base["sha256"] != BASE_SHA256:
        raise ValueError("Retained binding source differs from the selected bytes")
    staged = reorder(source)

    if OUT.resolve() != OUT:
        raise ValueError("Expected a repository-local source output")
    OUT.mkdir(exist_ok=True)
    run = OUT / ("r-" + uuid4().hex[:8])
    run.mkdir()
    target = run / PACKAGE / BASE.name
    target.parent.mkdir(parents=True)
    with target.open("xb") as stream:
        stream.write(staged)
    receipt = {
        "schema": "oneos-retained-pin-binding-observation-source/v1",
        "status": "STAGED_RETAINED_PIN_BINDING_OBSERVATION_SOURCE_ONLY",
        "baseSource": base,
        "source": pin(target.relative_to(ROOT), staged),
        "wholeSourceInversePassed": True,
        "selected": False,
        "deviceEligible": False,
        "targetExecuted": False,
    }
    with (run / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(compose(), indent=2))
