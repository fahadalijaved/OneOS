"""Verify pinned offline inputs; never load or execute their OEM implementations.

The committed manifest is a reviewed-input record, not external authenticity or
runtime compatibility proof. The large mounted tar keeps its earlier capture
receipt; this small-input verifier does not claim to rehash that entire archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
PARENT = PROJECT.parent
SCHEMA = "oneos-samsung-security-inputs/v1"


def input_path(relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Normalized relative input path required")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or not parts.parts or any(p in ("..", ".") for p in parts.parts):
        raise ValueError("Input must stay inside the parent project")
    candidate = (PARENT / Path(*parts.parts)).resolve(strict=True)
    candidate.relative_to(PARENT.resolve(strict=True))
    if not candidate.is_file():
        raise ValueError("Regular input file required: " + relative)
    return candidate


def verify_record(record: dict) -> dict:
    relative, expected = record["path"], record["sha256"]
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("Exact lowercase SHA256 required")
    path = input_path(relative)
    before = path.stat()
    if before.st_size != record["bytes"]:
        raise ValueError("Input size changed: " + relative)
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError("Input changed while reading: " + relative)
    if actual != expected:
        raise ValueError("Input hash changed: " + relative)
    return {"id": record["id"], "path": relative, "bytes": after.st_size, "sha256": actual}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", default="out/root/input-verification.json")
    args = parser.parse_args()
    manifest_path = PROJECT / "inventory/inputs.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != SCHEMA or manifest.get("parentRoot") != "..":
        raise ValueError("Reviewed input manifest schema/root required")
    records = manifest["files"]
    ids = [r["id"] for r in records]
    paths = [r["path"] for r in records]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise ValueError("Duplicate input identity/path")
    verified = [verify_record(record) for record in records]
    target = (PROJECT / args.receipt).resolve()
    target.relative_to((PROJECT / "out").resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "schema": "oneos-security-input-verification/v1",
        "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": verified,
        "mountedTarRehashed": False,
        "oemCodeExecuted": False,
        "androidRuntimeExecuted": False,
        "phoneActions": False,
        "limits": ["Hashes establish selected byte identity, not service compatibility or security acceptance"],
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(verified)} pinned files; no OEM execution or phone actions")


if __name__ == "__main__":
    main()
