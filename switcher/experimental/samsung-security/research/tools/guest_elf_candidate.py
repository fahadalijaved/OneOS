"""Strict metadata framing for the held AArch64 ELF candidate parser."""

import struct


SEARCH_TAGS = {15: "RPATH", 29: "RUNPATH"}


def parse_elf_candidate(raw, parse_held_elf):
    """Preserve the held parser's facts and identify each search override tag."""
    if len(raw) < 64 or raw[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("Incomplete or unsupported ELF64 header")
    elf_type, machine, version = struct.unpack_from("<HHI", raw, 16)
    header_size, entry_size, entry_count = struct.unpack_from("<HHH", raw, 52)
    if (elf_type, machine, version, header_size) != (3, 183, 1, 64):
        raise ValueError("Expected AArch64 ELF64 ET_DYN header")
    table_offset, = struct.unpack_from("<Q", raw, 32)
    if (entry_size != 56 or not 0 < entry_count <= 32 or table_offset < header_size
            or table_offset + entry_count * entry_size > len(raw)):
        raise ValueError("ELF program table outside the declared profile")

    programs = [struct.unpack_from("<IIQQQQQQ", raw, table_offset + index * entry_size)
                for index in range(entry_count)]
    dynamic = [program for program in programs if program[0] == 2]
    if len(dynamic) != 1:
        raise ValueError("Expected exactly one PT_DYNAMIC segment")
    dynamic_offset, dynamic_bytes = dynamic[0][2], dynamic[0][5]
    if not dynamic_bytes or dynamic_bytes % 16 or dynamic_offset + dynamic_bytes > len(raw):
        raise ValueError("PT_DYNAMIC must contain complete records within the file")

    soname_seen = False
    override_tags = []
    for offset in range(dynamic_offset, dynamic_offset + dynamic_bytes, 16):
        tag, = struct.unpack_from("<Q", raw, offset)
        if tag == 0:
            break
        if tag == 14:
            if soname_seen:
                raise ValueError("Duplicate DT_SONAME")
            soname_seen = True
        if tag in SEARCH_TAGS:
            override_tags.append(SEARCH_TAGS[tag])
    else:
        raise ValueError("PT_DYNAMIC has no complete DT_NULL record")

    try:
        parsed = parse_held_elf(raw)
    except (struct.error, ValueError) as error:
        raise ValueError(f"Invalid held ELF metadata: {error}") from error
    overrides = parsed["searchOverrides"]
    if len(overrides) != len(override_tags):
        raise ValueError("Held ELF search override count differs from the dynamic table")
    return {**parsed, "searchOverrideTags": [
        {"tag": tag, "value": value} for tag, value in zip(override_tags, overrides, strict=True)
    ]}
