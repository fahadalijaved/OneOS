#!/usr/bin/env python3
"""Build and verify a detached hash image for the fixed dm-verity v1 profile."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SCHEMA = "guest-tree-verity-recipe/v1"
BLOCK = 4096
DIGEST = 32
FANOUT = BLOCK // DIGEST
MAX_DATA_BYTES = 64 * 1024**3
MAX_PREFIX_BLOCKS = 4096
MAX_RECIPE_BYTES = 4096
HASH_CHUNK = 1024**2
HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
RECIPE_KEYS = {"schema", "dataBytes", "dataSha256", "salt", "hashStartBlock"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def required_digest(value, role):
    if not isinstance(value, str) or HEX_DIGEST.fullmatch(value) is None:
        raise ValueError(f"{role} must be exactly 32 lowercase hexadecimal bytes")
    return value


def inside_repo(name):
    path = Path(name).absolute()
    if ".." in path.parts or not path.is_relative_to(ROOT):
        raise ValueError("Input and output paths must be inside the repository")
    return path


def checked_path(path, directory=False):
    """Inspect every lexical component without following reparse points."""
    for component in reversed((path, *path.parents)):
        entry = component.lstat()
        if stat.S_ISLNK(entry.st_mode) or getattr(entry, "st_file_attributes", 0) & 0x400:
            raise ValueError("Symlink or reparse path refused")
        is_directory = directory or component != path
        if not (stat.S_ISDIR(entry.st_mode) if is_directory else stat.S_ISREG(entry.st_mode)):
            raise ValueError("Unexpected path type")
    if path.resolve() != path:
        raise ValueError("Path identity changed")
    return entry


def common_identity(entry):
    return entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns


def stable_identity(entry):
    return common_identity(entry), entry.st_ctime_ns, entry.st_mode, entry.st_nlink


@contextmanager
def checked_input(path, size=None, max_size=None):
    initial_path = checked_path(path)
    if (size is not None and initial_path.st_size != size) or (
        max_size is not None and initial_path.st_size > max_size
    ):
        raise ValueError("Input size differs from the admitted bound")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        initial_fd = os.fstat(stream.fileno())
        if not stat.S_ISREG(initial_fd.st_mode) or not initial_fd.st_ino or (
            common_identity(initial_fd) != common_identity(initial_path)
        ):
            raise ValueError("Opened file differs from its checked pathname")
        yield stream
        final_fd = os.fstat(stream.fileno())
        final_path = checked_path(path)
        if stable_identity(initial_fd) != stable_identity(final_fd) or (
            stable_identity(initial_path) != stable_identity(final_path)
        ):
            raise ValueError("Input changed during observation")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate recipe member")
        result[key] = value
    return result


def read_recipe(path, digest):
    required_digest(digest, "Recipe SHA-256")
    with checked_input(path, max_size=MAX_RECIPE_BYTES) as stream:
        raw = stream.read(MAX_RECIPE_BYTES + 1)
    if len(raw) > MAX_RECIPE_BYTES or sha256(raw) != digest:
        raise ValueError("Recipe bytes differ from the exact external pin")
    recipe = json.loads(raw.decode("ascii"), object_pairs_hook=unique_object)
    if not isinstance(recipe, dict) or set(recipe) != RECIPE_KEYS or recipe["schema"] != SCHEMA:
        raise ValueError("Unexpected recipe schema")
    for role in ("dataSha256", "salt"):
        required_digest(recipe[role], role)
    size, start = recipe["dataBytes"], recipe["hashStartBlock"]
    if type(size) is not int or not BLOCK <= size <= MAX_DATA_BYTES or size % BLOCK:
        raise ValueError("Data size must be a bounded positive multiple of 4096")
    if type(start) is not int or not 0 <= start <= MAX_PREFIX_BLOCKS:
        raise ValueError("Hash start block is outside the supported bound")
    return recipe


def read_exact(stream, size):
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("Incomplete input block")
    return data


def write_exact(stream, data):
    if stream.write(data) != len(data):
        raise OSError("Incomplete output block")


def hash_block(salt, data):
    digest = hashlib.sha256(salt)
    digest.update(data)
    return digest.digest()


def output_layout(data_blocks, start):
    """Build order is leaf to root. Physical offsets put the root first."""
    lengths = []
    count = data_blocks
    while count > 1:
        count = (count + FANOUT - 1) // FANOUT
        lengths.append(count)
    position = start
    reversed_layout = []
    for length in reversed(lengths):
        reversed_layout.append((position, length))
        position += length
    return list(reversed(reversed_layout))


def build_blocks(data, output, recipe):
    blocks = recipe["dataBytes"] // BLOCK
    start = recipe["hashStartBlock"]
    salt = bytes.fromhex(recipe["salt"])
    layout = output_layout(blocks, start)
    data_hash = hashlib.sha256()

    zero_chunk = bytes(min(start * BLOCK, HASH_CHUNK))
    remaining = start * BLOCK
    while remaining:
        length = min(remaining, len(zero_chunk))
        write_exact(output, zero_chunk[:length])
        remaining -= length

    if not layout:
        first = read_exact(data, BLOCK)
        data_hash.update(first)
        root = hash_block(salt, first)
    else:
        source = data
        source_start, source_count = 0, blocks
        for target_start, target_count in layout:
            for group in range(target_count):
                first = group * FANOUT
                count = min(FANOUT, source_count - first)
                source.seek((source_start + first) * BLOCK)
                node = bytearray(BLOCK)
                for slot in range(count):
                    child = read_exact(source, BLOCK)
                    if source is data:
                        data_hash.update(child)
                    offset = slot * DIGEST
                    node[offset:offset + DIGEST] = hash_block(salt, child)
                output.seek((target_start + group) * BLOCK)
                write_exact(output, node)
            source = output
            source_start, source_count = target_start, target_count
        output.seek(start * BLOCK)
        root = hash_block(salt, read_exact(output, BLOCK))

    if data.read(1) or data_hash.hexdigest() != recipe["dataSha256"]:
        raise ValueError("Data bytes differ from the exact recipe pin")
    return root.hex()


def verify_blocks(data, hash_image, recipe, trusted_root):
    """Read from the expected root down to every independently hashed block."""
    blocks = recipe["dataBytes"] // BLOCK
    salt = bytes.fromhex(recipe["salt"])
    root = bytes.fromhex(required_digest(trusted_root, "Root digest"))
    if not any(root):
        raise ValueError("Zero is not an admitted root digest")

    # Independently derive each level size from the kernel's shift formula.
    depth = ((blocks - 1).bit_length() + 6) // 7
    counts = [(blocks + (1 << shift) - 1) >> shift for shift in range(7 * depth, 0, -7)]
    starts = []
    position = recipe["hashStartBlock"]
    for count in counts:
        starts.append(position)
        position += count
    if os.fstat(hash_image.fileno()).st_size != position * BLOCK:
        raise ValueError("Unexpected exact hash image length")

    remaining = recipe["hashStartBlock"] * BLOCK
    while remaining:
        length = min(remaining, HASH_CHUNK)
        if any(read_exact(hash_image, length)):
            raise ValueError("Nonzero hash image prefix")
        remaining -= length

    data_hash = hashlib.sha256()

    def check_data(wanted):
        child = read_exact(data, BLOCK)
        data_hash.update(child)
        if hashlib.sha256(salt + child).digest() != wanted:
            raise ValueError("Data block does not match authenticated parent")

    def check_node(level, index, wanted):
        hash_image.seek((starts[level] + index) * BLOCK)
        node = read_exact(hash_image, BLOCK)
        if hashlib.sha256(salt + node).digest() != wanted:
            raise ValueError("Hash block does not match authenticated parent")
        last = level + 1 == depth
        first = index * 128
        total = blocks if last else counts[level + 1]
        slots = min(128, total - first)
        if slots <= 0 or any(node[slots * 32:]):
            raise ValueError("Unexpected nonzero hash block padding")
        for slot in range(slots):
            child = node[slot * 32:(slot + 1) * 32]
            if last:
                check_data(child)
            else:
                check_node(level + 1, first + slot, child)

    if depth:
        check_node(0, 0, root)
    else:
        check_data(root)
    if data.read(1) or data_hash.hexdigest() != recipe["dataSha256"]:
        raise ValueError("Data bytes differ from the exact recipe pin")

    hash_image.seek(0)
    image_digest = hashlib.sha256()
    remaining = position * BLOCK
    while remaining:
        length = min(remaining, HASH_CHUNK)
        image_digest.update(read_exact(hash_image, length))
        remaining -= length
    if hash_image.read(1):
        raise ValueError("Unexpected trailing hash image bytes")

    return {
        "format": 1,
        "algorithm": "sha256",
        "dataBlockBytes": BLOCK,
        "hashBlockBytes": BLOCK,
        "dataBlocks": blocks,
        "mappedBytes": recipe["dataBytes"],
        "mappedSectors": recipe["dataBytes"] // 512,
        "dataSha256": recipe["dataSha256"],
        "hashStartBlock": recipe["hashStartBlock"],
        "hashBlocks": sum(counts),
        "hashImageBytes": position * BLOCK,
        "hashImageSha256": image_digest.hexdigest(),
        "rootDigest": trusted_root,
        "salt": recipe["salt"],
        "levelsRootToLeaf": [
            {"startBlock": start, "blocks": count} for start, count in zip(starts, counts)
        ],
    }


def verify_file(data_path, image_path, recipe, trusted_root):
    with checked_input(data_path, size=recipe["dataBytes"]) as data:
        with checked_input(image_path) as hash_image:
            a, b = os.fstat(data.fileno()), os.fstat(hash_image.fileno())
            if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
                raise ValueError("Data and detached hash image cannot be the same file")
            return verify_blocks(data, hash_image, recipe, trusted_root)


def claim_output(name):
    path = inside_repo(name)
    if path == OUT or not path.is_relative_to(OUT):
        raise ValueError("Build output must be a new directory beneath out")
    checked_path(path.parent, directory=True)
    path.mkdir()
    checked_path(path, directory=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="mode", required=True)
    build = subcommands.add_parser("build")
    verify = subcommands.add_parser("verify")
    for command in (build, verify):
        command.add_argument("--recipe", required=True)
        command.add_argument("--recipe-sha256", required=True)
        command.add_argument("--data", required=True)
    build.add_argument("--out", required=True)
    verify.add_argument("--hash-image", required=True)
    verify.add_argument("--root-digest", required=True)
    args = parser.parse_args()
    try:
        recipe_path, data_path = inside_repo(args.recipe), inside_repo(args.data)
        recipe = read_recipe(recipe_path, args.recipe_sha256)
        if args.mode == "build":
            target = claim_output(args.out)
            image = target / "hash.img"
            with checked_input(data_path, size=recipe["dataBytes"]) as data:
                with image.open("x+b") as output:
                    root = build_blocks(data, output, recipe)
                    output.flush()
                    os.fsync(output.fileno())
        else:
            image, root = inside_repo(args.hash_image), args.root_digest
        proof = verify_file(data_path, image, recipe, root)
        if read_recipe(recipe_path, args.recipe_sha256) != recipe:
            raise ValueError("Recipe changed before result")
        result = {
            "schema": "guest-tree-verity-result/v1",
            "status": "BUILT_AND_VERIFIED" if args.mode == "build" else "VERIFIED",
            "recipeSha256": args.recipe_sha256,
            **proof,
        }
        text = json.dumps(result, indent=2) + "\n"
        if args.mode == "build":
            checked_path(target, directory=True)
            with (target / "receipt.json").open("x", encoding="ascii", newline="\n") as receipt:
                receipt.write(text)
                receipt.flush()
                os.fsync(receipt.fileno())
        print(text, end="")
    except (OSError, ValueError, RecursionError) as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
