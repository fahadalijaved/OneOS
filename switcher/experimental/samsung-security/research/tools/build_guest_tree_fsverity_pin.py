#!/usr/bin/env python3
"""Compute the exact offline fs-verity SHA-256 file digest and descriptor."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys


BLOCK = 4096
DIGEST = 32
FANOUT = BLOCK // DIGEST
READ_BYTES = 4 * 1024**2
SALT_BYTES = 32
SHA256_COMPRESSION_BYTES = 64
HEADER = struct.Struct("<BBBBIQ")
DESCRIPTOR_BYTES = 256
IO_SOURCE = "build_guest_tree_verity.py"
IO_SHA256 = "6c6aee1d4d18bfe4cdc4475db7bab98aebd70de6974de22b88ea16e8755fd23e"


def load_checked_io():
    path = Path(__file__).resolve().with_name(IO_SOURCE)
    with path.open("rb") as stream:
        source = stream.read(64 * 1024 + 1)
    if hashlib.sha256(source).hexdigest() != IO_SHA256:
        raise ValueError("Checked file I/O source differs from the selected pin")
    context = {"__file__": str(path), "__name__": "guest_tree_fsverity_checked_io"}
    exec(compile(source, str(path), "exec"), context)
    return context


def checked_salt(text):
    if len(text) % 2 or re.fullmatch(r"[0-9a-f]{0,64}", text) is None:
        raise ValueError("Salt must be zero to 32 bytes of lowercase hexadecimal")
    return bytes.fromhex(text)


def block_counts(size):
    counts = []
    blocks = (size + BLOCK - 1) // BLOCK
    while blocks > 1:
        blocks = (blocks + FANOUT - 1) // FANOUT
        counts.append(blocks)
    return counts


def stream_measurement(stream, size, salt):
    """One sequential read, retaining at most one pending node per level."""
    counts = block_counts(size)
    pending = [bytearray() for _ in counts]
    emitted = [0 for _ in counts]
    initial = hashlib.sha256(salt.ljust(SHA256_COMPRESSION_BYTES, b"\0") if salt else b"")
    raw_sha = hashlib.sha256()
    zeros = memoryview(bytes(BLOCK))
    root = None

    def hash_block(block):
        digest = initial.copy()
        digest.update(block)
        if len(block) != BLOCK:
            digest.update(zeros[:BLOCK - len(block)])
        return digest.digest()

    def push(level, digest):
        nonlocal root
        while level < len(pending):
            node = pending[level]
            node.extend(digest)
            if len(node) < BLOCK:
                return
            digest = hash_block(node)
            node.clear()
            emitted[level] += 1
            level += 1
        if root is not None:
            raise ValueError("Inconsistent Merkle root count")
        root = digest

    remaining = size
    while remaining:
        wanted = min(remaining, READ_BYTES)
        data = stream.read(wanted)
        if len(data) != wanted:
            raise ValueError("Incomplete pinned image read")
        raw_sha.update(data)
        chunk = memoryview(data)
        for offset in range(0, len(chunk), BLOCK):
            push(0, hash_block(chunk[offset:offset + BLOCK]))
        remaining -= wanted
    if stream.read(1):
        raise ValueError("Image extends past the pinned length")

    for level, node in enumerate(pending):
        if node:
            push(level + 1, hash_block(node))
            node.clear()
            emitted[level] += 1
    if size == 0:
        root = bytes(DIGEST)
    if root is None or emitted != counts:
        raise ValueError("Inconsistent Merkle level geometry")
    return raw_sha.hexdigest(), root, counts


def make_descriptor(size, salt, root):
    descriptor = bytearray(DESCRIPTOR_BYTES)
    HEADER.pack_into(descriptor, 0, 1, 1, 12, len(salt), 0, size)
    descriptor[16:48] = root
    descriptor[80:80 + len(salt)] = salt
    return bytes(descriptor)


def check_descriptor(descriptor, size, salt):
    if len(descriptor) != DESCRIPTOR_BYTES:
        raise ValueError("Descriptor must be exactly 256 bytes")
    version, algorithm, block_log, salt_size, reserved, data_size = HEADER.unpack_from(descriptor)
    if (version, algorithm, block_log) != (1, 1, 12):
        raise ValueError("Unsupported fs-verity version, hash algorithm or block size")
    if salt_size != len(salt) or descriptor[80:80 + salt_size] != salt:
        raise ValueError("Descriptor salt differs from the selected salt")
    if reserved or any(descriptor[48:80]) or any(descriptor[80 + salt_size:]):
        raise ValueError("Descriptor reserved fields or unused digest/salt bytes are nonzero")
    if data_size != size:
        raise ValueError("Descriptor file length differs from the pin")
    if size == 0 and any(descriptor[16:48]):
        raise ValueError("Empty file descriptor requires the zero Merkle root")


def level_layout(counts):
    start = 0
    levels = []
    for count in reversed(counts):
        levels.append({"startBlock": start, "blocks": count})
        start += count
    return levels


def write_exclusive(path, data):
    with path.open("xb") as stream:
        if stream.write(data) != len(data):
            raise OSError("Incomplete output write")
        stream.flush()
        os.fsync(stream.fileno())


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--image", required=True)
    cli.add_argument("--image-bytes", required=True, type=int)
    cli.add_argument("--image-sha256", required=True)
    cli.add_argument("--salt", default="")
    cli.add_argument("--expect-fsverity-digest")
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out")
    mode.add_argument("--verify-descriptor")
    args = cli.parse_args()
    try:
        io = load_checked_io()
        size = args.image_bytes
        if not 0 <= size <= io["MAX_DATA_BYTES"]:
            raise ValueError("Image length is outside the offline bound")
        pin = io["required_digest"](args.image_sha256, "Image SHA-256")
        expected_digest = args.expect_fsverity_digest
        if expected_digest is not None:
            io["required_digest"](expected_digest, "Expected fs-verity digest")
        salt = checked_salt(args.salt)
        image = io["inside_repo"](args.image)
        selected_descriptor = None
        if args.verify_descriptor:
            path = io["inside_repo"](args.verify_descriptor)
            with io["checked_input"](path, size=DESCRIPTOR_BYTES) as stream:
                selected_descriptor = stream.read(DESCRIPTOR_BYTES + 1)
            check_descriptor(selected_descriptor, size, salt)

        with io["checked_input"](image, size=size) as stream:
            image_sha, root, counts = stream_measurement(stream, size, salt)
        if image_sha != pin:
            raise ValueError("Image bytes differ from the exact SHA-256 pin")
        descriptor = make_descriptor(size, salt, root)
        check_descriptor(descriptor, size, salt)
        if selected_descriptor is not None and selected_descriptor != descriptor:
            raise ValueError("Descriptor does not match the authenticated image Merkle root")
        digest = hashlib.sha256(descriptor).hexdigest()
        if expected_digest is not None and expected_digest != digest:
            raise ValueError("Computed fs-verity digest differs from the external pin")

        result = {
            "schema": "guest-tree-fsverity-pin/v1",
            "status": "BUILT_OFFLINE" if args.out else "VERIFIED_OFFLINE",
            "hashAlgorithm": "sha256",
            "descriptorVersion": 1,
            "blockBytes": BLOCK,
            "imageBytes": size,
            "imageSha256": image_sha,
            "salt": salt.hex(),
            "merkleRoot": root.hex(),
            "merkleTreeBytes": sum(counts) * BLOCK,
            "levelsRootToLeaf": level_layout(counts),
            "descriptorBytes": DESCRIPTOR_BYTES,
            "fsVerityDigest": digest,
            "checkedIoSourceSha256": IO_SHA256,
        }
        text = json.dumps(result, indent=2) + "\n"
        if args.out:
            folder = io["claim_output"](args.out)
            saved = folder / "descriptor.bin"
            write_exclusive(saved, descriptor)
            with io["checked_input"](saved, size=DESCRIPTOR_BYTES) as stream:
                readback = stream.read(DESCRIPTOR_BYTES + 1)
            check_descriptor(readback, size, salt)
            if readback != descriptor:
                raise ValueError("Written descriptor bytes differ from the verified descriptor")
            write_exclusive(folder / "receipt.json", text.encode("ascii"))
        print(text, end="")
    except (OSError, ValueError) as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
