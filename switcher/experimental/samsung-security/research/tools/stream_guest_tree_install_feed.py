#!/usr/bin/env python3
"""Feed the exact reviewed guest EROFS carrier to a binary stdout pipe."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


IMAGE = "out/guest-tree-erofs-pc/r-3d0dc2ef/guest.erofs"
IMAGE_BYTES = 13_890_850_816
IMAGE_SHA256 = "094ff7e7ac1148fab732719d2e04a943fbbcc0d7d0ae67ad62d898b552eb365d"
FSVERITY_DIGEST = "9b2b664582360dec660e3e25c840104c16b1e1a9cb4aadbf8f467e200c525ba9"
READBACK = (
    "out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json",
    "92e2f8199da955cf4b8ddc15cf99b4ab978c133d3f9284535ad3c500fa0d5e6e",
)
VERITY = (
    "out/guest-tree-fsverity-pin/carrier-r-3d0dc2ef/receipt.json",
    "7c185c512782ac04ebb32dad878d9f85d361b2edec4d3f18afb52c8591c2299a",
)
INDEPENDENT_VERITY = (
    "out/guest-tree-fsverity-pin/carrier-r-3d0dc2ef/INDEPENDENT-DESCRIPTOR.json",
    "377ef52fe2d64215a8565f274a41ef5053af4b9c56b927155ec504310c112db6",
)
DESCRIPTOR = "out/guest-tree-fsverity-pin/carrier-r-3d0dc2ef/descriptor.bin"
IO_SHA256 = "6c6aee1d4d18bfe4cdc4475db7bab98aebd70de6974de22b88ea16e8755fd23e"
CHUNK = 4 * 1024**2
MAX_RECEIPT = 64 * 1024


class FeedArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        super().print_help(sys.stderr if file is None else file)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_checked_io():
    path = Path(__file__).resolve().with_name("build_guest_tree_verity.py")
    with path.open("rb") as stream:
        data = stream.read(MAX_RECEIPT + 1)
    if digest(data) != IO_SHA256:
        raise ValueError("Checked file I/O source differs from the selected pin")
    scope = {"__file__": str(path), "__name__": "guest_tree_install_feed_checked_io"}
    exec(compile(data, str(path), "exec"), scope)
    return scope


def pinned_bytes(io, path, expected, limit):
    with io["checked_input"](io["ROOT"] / path, max_size=limit) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit or digest(data) != expected:
        raise ValueError(f"Authoritative bytes changed: {path}")
    return data


def pinned_record(io, pin):
    raw = pinned_bytes(io, *pin, MAX_RECEIPT)
    return json.loads(raw.decode("ascii"), object_pairs_hook=io["unique_object"])


def identity(entry):
    return (entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns, entry.st_ctime_ns)


def authenticate_profile(io):
    readback = pinned_record(io, READBACK)
    verity = pinned_record(io, VERITY)
    independent = pinned_record(io, INDEPENDENT_VERITY)
    descriptor = pinned_bytes(io, DESCRIPTOR, FSVERITY_DIGEST, 256)
    image = readback["image"]
    named = image["identity"]
    if (readback["schema"] != "oneos-guest-tree-erofs-image-readback/v1"
            or readback["status"] != "PASS_SEALED_EROFS_RAW_DONOR_READBACK_ONLY"
            or readback["carrierProfile"] != "donor-tree-and-selected-core-apex"
            or readback["mountObserved"] is not False or readback["stageEligible"] is not False
            or image["path"] != IMAGE or image["bytes"] != IMAGE_BYTES or image["sha256"] != IMAGE_SHA256
            or len(named) != 5 or any(type(value) is not int for value in named)
            or not named[1] or named[2] != IMAGE_BYTES):
        raise ValueError("Readback does not identify the selected unmounted carrier")
    if (verity["schema"] != "guest-tree-fsverity-pin/v1" or verity["status"] != "BUILT_OFFLINE"
            or verity["hashAlgorithm"] != "sha256" or verity["descriptorVersion"] != 1
            or verity["blockBytes"] != 4096 or verity["salt"] != ""
            or verity["descriptorBytes"] != 256 or verity["checkedIoSourceSha256"] != IO_SHA256):
        raise ValueError("Unsupported offline fs-verity profile")
    for proof in (verity, independent):
        if (proof["imageBytes"] != IMAGE_BYTES or proof["imageSha256"] != IMAGE_SHA256
                or proof["fsVerityDigest"] != FSVERITY_DIGEST):
            raise ValueError("Carrier readback and fs-verity evidence disagree")
    if (len(descriptor) != 256 or descriptor[:8] != bytes((1, 1, 12, 0, 0, 0, 0, 0))
            or int.from_bytes(descriptor[8:16], "little") != IMAGE_BYTES
            or descriptor[16:48].hex() != verity["merkleRoot"] or any(descriptor[48:])):
        raise ValueError("Fs-verity descriptor differs from the selected carrier profile")
    return io["ROOT"] / IMAGE, tuple(named)


def stdout_pipe():
    fd = sys.stdout.fileno()
    if sys.stdout.isatty() or os.isatty(fd):
        raise ValueError("Binary carrier output to an interactive terminal is refused")
    if not stat.S_ISFIFO(os.fstat(fd).st_mode):
        raise ValueError("Binary carrier requires a dedicated stdout pipe")
    if os.name == "nt":
        import msvcrt
        msvcrt.setmode(fd, os.O_BINARY)
    return fd


def write_all(write, data):
    rest = memoryview(data)
    while rest:
        count = write(rest)
        if type(count) is not int or not 0 < count <= len(rest):
            raise OSError("Invalid carrier pipe write progress")
        rest = rest[count:]


def stream_source(io, path, named, expected_bytes, expected_sha, write, record_source):
    """Keep the last nonempty chunk until every source check and close succeeds."""
    if expected_bytes <= 0:
        raise ValueError("The carrier must have a positive length")
    hashed = hashlib.sha256()
    remaining = expected_bytes
    with io["checked_input"](path, size=expected_bytes) as source:
        if (identity(io["checked_path"](path)) != named
                or identity(os.fstat(source.fileno()))[:4] != named[:4]):
            raise ValueError("Held carrier does not match the authoritative named identity")
        while remaining > CHUNK:
            chunk = source.read(CHUNK)
            if len(chunk) != CHUNK:
                raise ValueError("Carrier ended before its pinned length")
            hashed.update(chunk)
            write_all(write, chunk)
            remaining -= CHUNK
        tail = source.read(remaining)
        if len(tail) != remaining or source.read(1):
            raise ValueError("Carrier does not end at its pinned length")
        hashed.update(tail)
        actual = hashed.hexdigest()
        if actual != expected_sha:
            raise ValueError("Carrier SHA-256 differs from its authoritative raw pin")
    if identity(io["checked_path"](path)) != named:
        raise ValueError("Named carrier changed before final pipe release")
    record_source(actual, expected_bytes, len(tail))
    write_all(write, tail)


def write_source_receipt(path, image, size, actual_sha, tail_bytes):
    result = {
        "schema": "guest-tree-install-feed-source/v1",
        "status": "PC_SOURCE_AUTHENTICATED_TAIL_NOT_YET_RELEASED",
        "image": image,
        "imageBytes": size,
        "imageSha256": actual_sha,
        "fsVerityDigest": FSVERITY_DIGEST,
        "withheldTailBytes": tail_bytes,
        "namedAndHeldIdentityVerified": True,
        "readbackReceiptSha256": READBACK[1],
        "fsVerityReceiptSha256": VERITY[1],
        "independentDescriptorReceiptSha256": INDEPENDENT_VERITY[1],
        "checkedIoSourceSha256": IO_SHA256,
        "requiresProducerExitZeroAndReceiverAck": True,
    }
    raw = (json.dumps(result, indent=2) + "\n").encode("ascii")
    with path.open("xb") as receipt:
        if receipt.write(raw) != len(raw):
            raise OSError("Incomplete source receipt write")
        receipt.flush()
        os.fsync(receipt.fileno())
    return raw


def main():
    cli = FeedArgumentParser(description=__doc__)
    cli.add_argument("--receipt-dir", required=True, help="Exclusive new directory beneath repository out")
    args = cli.parse_args()
    try:
        sink = stdout_pipe()
        io = load_checked_io()
        path, named = authenticate_profile(io)
        folder = io["claim_output"](args.receipt_dir)

        def source_receipt(actual, size, tail):
            if authenticate_profile(io) != (path, named):
                raise ValueError("Authoritative profile changed before tail release")
            io["checked_path"](folder, directory=True)
            receipt = folder / "source-receipt.json"
            raw = write_source_receipt(receipt, IMAGE, size, actual, tail)
            with io["checked_input"](receipt, size=len(raw)) as saved:
                if saved.read(len(raw) + 1) != raw:
                    raise ValueError("Written source receipt differs from the authenticated result")

        stream_source(io, path, named, IMAGE_BYTES, IMAGE_SHA256,
                      lambda data: os.write(sink, data), source_receipt)
        return 0
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"Carrier feed refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
