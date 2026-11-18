"""Check the exact authored research checkpoint, without executing OEM code.

This checks retained file identity. It does not authenticate an arbitrary
manifest or establish Android construction, hardware behavior or security.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def main():
    checkpoint = json.loads((ROOT / "inventory/checkpoint.json").read_text(encoding="utf-8-sig"))
    if checkpoint["schema"] != "oneos-samsung-security-checkpoint/v1":
        raise ValueError("Reviewed checkpoint schema required")
    for name, expected in checkpoint["authoredFiles"].items():
        parts = PurePosixPath(name)
        if parts.is_absolute() or ".." in parts.parts or "\\" in name:
            raise ValueError("Invalid checkpoint path")
        path = ROOT / name
        if path.stat().st_size != expected["bytes"]:
            raise ValueError("Changed checkpoint size: " + name)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected["sha256"]:
            raise ValueError("Changed checkpoint file: " + name)
    print(f"Verified {len(checkpoint['authoredFiles'])} authored checkpoint files; runtime acceptance remains unproved")


if __name__ == "__main__":
    main()
