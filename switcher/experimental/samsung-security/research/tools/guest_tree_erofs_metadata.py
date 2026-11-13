"""Encode flat EROFS metadata for the selected 4 KiB donor image."""

import struct


BLOCK_SIZE = 4096
DIRECTORY_ENTRY = struct.Struct("<QHBB")
EXTENDED_INODE = struct.Struct("<4HQ4IQ2I16x")
SECURITY_XATTR = struct.Struct("<BBH")
XATTR_HEADER_SIZE = 12
SECURITY_INDEX = 6
SECURITY_NAMES = {
    b"security.capability": b"capability",
    b"security.selinux": b"selinux",
}
MODE_TYPES = {"file": 0o100000, "directory": 0o040000, "symlink": 0o120000}
DIRECTORY_TYPE = 2
FILE_TYPES = (1, DIRECTORY_TYPE, 7)


def uint(value, bits, field):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f"Invalid EROFS {field}")
    return value


def directory_block(entries):
    name_offset = len(entries) * DIRECTORY_ENTRY.size
    records = bytearray()
    names = bytearray()
    for name, nid, file_type in entries:
        records.extend(DIRECTORY_ENTRY.pack(nid, name_offset + len(names), file_type, 0))
        names.extend(name)
    records.extend(names)
    return records


def directory_bytes(nid, parent_nid, children):
    """Encode names in raw byte order, with zero fill between logical blocks."""
    entries = [
        (b".", uint(nid, 64, "directory nid"), DIRECTORY_TYPE),
        (b"..", uint(parent_nid, 64, "parent nid"), DIRECTORY_TYPE),
    ]
    names = {b".", b".."}
    for name, child_nid, file_type in children:
        if (type(name) is not bytes or not 1 <= len(name) <= 255
                or b"/" in name or b"\0" in name or name in names):
            raise ValueError("Invalid or repeated EROFS directory name")
        if type(file_type) is not int or file_type not in FILE_TYPES:
            raise ValueError("Unselected EROFS directory entry type")
        names.add(name)
        entries.append((name, uint(child_nid, 64, "child nid"), file_type))
    entries.sort(key=lambda entry: entry[0])

    output = bytearray()
    group_start = 0
    group_size = 0
    for index, (name, _, _) in enumerate(entries):
        entry_size = DIRECTORY_ENTRY.size + len(name)
        if group_size + entry_size > BLOCK_SIZE:
            output.extend(directory_block(entries[group_start:index]))
            output.extend(bytes(BLOCK_SIZE - group_size))
            group_start = index
            group_size = 0
        group_size += entry_size
    output.extend(directory_block(entries[group_start:]))
    return bytes(output)


def inline_xattrs(attrs):
    """Encode only the two selected security attributes, without shared entries."""
    if type(attrs) is not tuple:
        raise ValueError("Expected an EROFS xattr tuple")
    if not attrs:
        return b""
    entries = {}
    for key, value in attrs:
        if type(key) is not bytes or key not in SECURITY_NAMES or key in entries:
            raise ValueError("Unselected or repeated EROFS xattr key")
        if type(value) is not bytes or len(value) >= 1 << 16:
            raise ValueError("Invalid EROFS xattr value")
        entries[key] = value
    # No name filter or shared attribute IDs.
    output = bytearray(XATTR_HEADER_SIZE)
    for key in sorted(entries):
        name = SECURITY_NAMES[key]
        value = entries[key]
        output.extend(SECURITY_XATTR.pack(len(name), SECURITY_INDEX, len(value)))
        output.extend(name)
        output.extend(value)
        output.extend(bytes(-len(output) % 4))
    return bytes(output)


def extended_inode(node, nlink, raw_blkaddr, xattr_body):
    """Encode the 64-byte extended flat-plain inode before its xattr body."""
    if node.kind not in MODE_TYPES:
        raise ValueError("Unselected EROFS inode kind")
    mode = MODE_TYPES[node.kind] | uint(node.mode, 12, "permission mode")
    if type(xattr_body) is not bytes:
        raise ValueError("Expected EROFS xattr body bytes")
    xcount = 0
    if xattr_body:
        if len(xattr_body) <= XATTR_HEADER_SIZE or len(xattr_body) % 4:
            raise ValueError("Invalid EROFS xattr body size")
        xcount = uint(1 + (len(xattr_body) - XATTR_HEADER_SIZE) // 4, 16, "xattr count")
    links = uint(nlink, 32, "link count")
    if not links:
        raise ValueError("EROFS inode must have a link")
    return EXTENDED_INODE.pack(
        1, xcount, mode, 0,
        uint(node.size, 64, "size"),
        uint(raw_blkaddr, 32, "data block address"), 0,
        uint(node.uid, 32, "uid"), uint(node.gid, 32, "gid"),
        0, 0, links,
    )
