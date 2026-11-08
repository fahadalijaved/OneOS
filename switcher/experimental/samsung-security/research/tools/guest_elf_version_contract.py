"""Read GNU symbol-version metadata from a bounded little-endian AArch64 ELF."""

from collections import namedtuple
from struct import Struct


_ELF = Struct("<16sHHIQQQIHHHHHH")
_SECTION = Struct("<IIQQQQIIQQ")
_SYMBOL = Struct("<IBBHQQ")
_DYNAMIC = Struct("<qQ")
_VERSYM = Struct("<H")
_NEED = Struct("<HHIII")
_NEED_AUX = Struct("<IHHII")
_DEF = Struct("<HHHHIII")
_DEF_AUX = Struct("<II")
_Section = namedtuple("_Section", "name kind flags address offset size link info alignment entsize")

_TYPES = {
    ".dynsym": 11, ".dynstr": 3, ".dynamic": 6,
    ".gnu.version": 0x6FFFFFFF, ".gnu.version_r": 0x6FFFFFFE, ".gnu.version_d": 0x6FFFFFFD,
}
_VERSION_TAGS = {
    ".gnu.version": (0x6FFFFFF0, None),
    ".gnu.version_r": (0x6FFFFFFE, 0x6FFFFFFF),
    ".gnu.version_d": (0x6FFFFFFC, 0x6FFFFFFD),
}
_VERSION_INDEX = 0x7FFF
_MAX_METADATA = 8 * 1024 * 1024


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _string(table, offset, *, empty=False):
    _need(0 <= offset < len(table), "Invalid ELF string offset")
    end = table.find(b"\0", offset, offset + 4097)
    _need(end >= offset and (end > offset or empty), "Missing or empty ELF string")
    value = table[offset:end].decode("ascii")
    _need(not value or value.isprintable(), "Unsupported ELF string characters")
    return value


def _string_table(raw, section):
    _need(section.kind == 3 and 0 < section.size <= _MAX_METADATA and not section.entsize,
          "Invalid ELF string table")
    table = raw[section.offset:section.offset + section.size]
    _need(table[0] == table[-1] == 0, "Invalid ELF string table terminators")
    return table


def _sections(raw):
    _need(isinstance(raw, bytes) and _ELF.size <= len(raw) <= 128 * 1024**2, "Invalid ELF byte extent")
    ident, kind, machine, version, _, _, offset, _, size, _, _, entry_size, count, names = _ELF.unpack_from(raw)
    _need(ident[:7] == b"\x7fELF\x02\x01\x01" and kind in (2, 3) and machine == 183 and version == 1
          and size == _ELF.size, "Expected little-endian AArch64 ELF64 executable or shared object")
    _need(entry_size == _SECTION.size and 0 < count <= 4096 and 0 < names < count
          and _ELF.size <= offset <= len(raw) - count * entry_size, "Unsupported ELF section table")
    sections = [_Section(*_SECTION.unpack_from(raw, offset + index * entry_size)) for index in range(count)]
    _need(not any(sections[0]), "Unsupported ELF null or extended section record")
    for section in sections[1:]:
        if section.kind != 8:  # SHT_NOBITS has no file-backed extent.
            _need(section.offset <= len(raw) and section.size <= len(raw) - section.offset,
                  "ELF section outside file")
    strings = _string_table(raw, sections[names])
    selected = {}
    alternate_types = set(_TYPES.values()) - {3}
    for index, section in enumerate(sections[1:], 1):
        name = _string(strings, section.name, empty=True)
        if name in _TYPES:
            _need(name not in selected and section.kind == _TYPES[name] and section.flags & 2
                  and 0 < section.size <= _MAX_METADATA and section.address, "Invalid selected ELF section")
            selected[name] = index, section
        else:
            _need(section.kind not in alternate_types, "Unrecognized ELF dynamic metadata section")
    _need(all(name in selected for name in (".dynsym", ".dynstr", ".dynamic")), "Missing ELF dynamic metadata")

    spans = [(_ELF.size, 0), (offset + count * entry_size, offset)]
    spans.extend((section.offset + section.size, section.offset) for _, section in selected.values())
    previous_end = 0
    for end, start in sorted(spans, key=lambda span: span[1]):
        _need(start >= previous_end, "Overlapping ELF metadata sections")
        previous_end = end
    return sections, selected


def _dynamic(raw, selected, strings):
    str_index, str_section = selected[".dynstr"]
    _, sym_section = selected[".dynsym"]
    _, dynamic = selected[".dynamic"]
    _need(dynamic.link == str_index and dynamic.entsize == _DYNAMIC.size and not dynamic.size % _DYNAMIC.size
          and dynamic.size <= 8192 * _DYNAMIC.size, "Invalid ELF dynamic table")
    expected = {5: str_section.address, 6: sym_section.address, 10: str_section.size, 11: _SYMBOL.size}
    tracked = set(expected)
    for name, (address_tag, count_tag) in _VERSION_TAGS.items():
        tracked.add(address_tag)
        if count_tag is not None:
            tracked.add(count_tag)
        if name in selected:
            section = selected[name][1]
            expected[address_tag] = section.address
            if count_tag is not None:
                expected[count_tag] = section.info
    tags, owners, ended = {}, set(), False
    for offset in range(dynamic.offset, dynamic.offset + dynamic.size, _DYNAMIC.size):
        tag, value = _DYNAMIC.unpack_from(raw, offset)
        if ended or not tag:
            _need(not tag and not value, "Unexpected bytes after ELF DT_NULL")
            ended = True
        elif tag in tracked:
            _need(tag not in tags, "Duplicate ELF dynamic metadata tag")
            tags[tag] = value
        elif tag == 1:  # DT_NEEDED
            owners.add(_string(strings, value))
    _need(ended and tags == expected, "ELF dynamic tags and sections disagree")
    return owners


def _record(table, offset, layout, spans):
    _need(not offset % 4 and 0 <= offset <= len(table) - layout.size, "Invalid GNU version record extent")
    _need(len(spans) < len(table) // 8, "Too many GNU version records")
    spans.append((offset, offset + layout.size))
    return layout.unpack_from(table, offset)


def _next(offset, delta, final, minimum):
    _need(delta == 0 if final else delta >= minimum and not delta % 4, "Invalid GNU version chain link")
    return offset + delta


def _complete(table, spans):
    cursor = 0
    for start, end in sorted(spans):
        _need(start == cursor, "Unaccounted or overlapping GNU version records")
        cursor = end
    _need(cursor == len(table), "Trailing GNU version record bytes")


def _hash(value):
    result = 0
    for byte in value.encode("ascii"):
        result = (result << 4) + byte
        high = result & 0xF0000000
        result = (result ^ (high >> 24)) & ~high
    return result


def _requirements(table, count, strings, owners):
    result, seen, spans = {}, set(), []
    offset = 0
    for row in range(count):
        version, aux_count, name, aux_offset, following = _record(table, offset, _NEED, spans)
        _need(version == 1 and aux_count > 0 and aux_offset >= _NEED.size, "Unsupported GNU Verneed record")
        owner = _string(strings, name)
        _need(owner in owners and owner not in seen, "Invalid GNU Verneed dependency owner")
        seen.add(owner)
        aux = offset + aux_offset
        for index in range(aux_count):
            expected_hash, flags, symbol_index, name, next_aux = _record(table, aux, _NEED_AUX, spans)
            symbol_index &= _VERSION_INDEX
            name = _string(strings, name)
            _need(symbol_index > 1 and symbol_index not in result and not flags & ~2
                  and _hash(name) == expected_hash, "Invalid GNU Vernaux metadata")
            result[symbol_index] = owner, name
            aux = _next(aux, next_aux, index + 1 == aux_count, _NEED_AUX.size)
        offset = _next(offset, following, row + 1 == count, _NEED.size)
    _complete(table, spans)
    return result


def _definitions(table, count, strings):
    result, parents, spans = {}, set(), []
    offset = 0
    for row in range(count):
        version, flags, symbol_index, aux_count, expected_hash, aux_offset, following = _record(table, offset, _DEF, spans)
        _need(version == 1 and not flags & ~3 and 0 < symbol_index <= _VERSION_INDEX
              and symbol_index not in result and (symbol_index == 1) == bool(flags & 1)
              and aux_count > 0 and aux_offset >= _DEF.size, "Unsupported GNU Verdef record")
        aux = offset + aux_offset
        for index in range(aux_count):
            name, next_aux = _record(table, aux, _DEF_AUX, spans)
            name = _string(strings, name)
            if index == 0:
                _need(_hash(name) == expected_hash, "Invalid GNU Verdef hash")
                result[symbol_index] = name
            else:
                parents.add(name)
            aux = _next(aux, next_aux, index + 1 == aux_count, _DEF_AUX.size)
        offset = _next(offset, following, row + 1 == count, _DEF.size)
    _complete(table, spans)
    _need(1 in result and len(set(result.values())) == len(result) and parents <= set(result.values()),
          "Missing or ambiguous GNU Verdef names")
    return result


def read_version_contract(raw):
    """Return versioned imports/exports, declared versions and unversioned names.

    Import rows use dynsym order and their weak bit comes from symbol binding.
    A hidden versym bit selects the same explicit version name. Unversioned
    exports contain actual global-index entries only. The result describes
    metadata and does not choose providers or check relocation resolution.
    """
    sections, selected = _sections(raw)
    str_index, str_section = selected[".dynstr"]
    sym_index, dynsym = selected[".dynsym"]
    strings = _string_table(raw, str_section)
    owners = _dynamic(raw, selected, strings)
    _need(dynsym.link == str_index and dynsym.entsize == _SYMBOL.size and not dynsym.size % _SYMBOL.size
          and 0 < dynsym.info <= dynsym.size // _SYMBOL.size <= 262144, "Invalid ELF dynsym table")
    _need(not any(_SYMBOL.unpack_from(raw, dynsym.offset)), "Invalid ELF null symbol")
    count = dynsym.size // _SYMBOL.size
    versym = selected.get(".gnu.version")
    if versym:
        versym = versym[1]
        _need(versym.link == sym_index and versym.entsize == _VERSYM.size and not versym.info
              and versym.size == count * _VERSYM.size and _VERSYM.unpack_from(raw, versym.offset) == (0,),
              "Invalid GNU versym table")

    tables = []
    for name in (".gnu.version_r", ".gnu.version_d"):
        if name not in selected:
            tables.append((b"", 0))
            continue
        section = selected[name][1]
        _need(versym is not None and section.link == str_index and not section.entsize
              and 0 < section.info <= _VERSION_INDEX, "Invalid GNU version record section")
        tables.append((raw[section.offset:section.offset + section.size], section.info))
    needs = _requirements(*tables[0], strings, owners)
    definitions = _definitions(*tables[1], strings) if tables[1][1] else {}
    _need(not needs.keys() & definitions.keys(), "Conflicting GNU version indexes")

    requirements, exports, unversioned_exports = {}, set(), set()
    unversioned_undefined = 0
    for index in range(1, count):
        name, info, other, location, _, _ = _SYMBOL.unpack_from(raw, dynsym.offset + index * _SYMBOL.size)
        binding, visibility = info >> 4, other & 3
        _need((binding == 0) == (index < dynsym.info)
              and (location < len(sections) or location in (0xFFF1, 0xFFF2)), "Unsupported ELF symbol declaration")
        version = _VERSYM.unpack_from(raw, versym.offset + index * _VERSYM.size)[0] & _VERSION_INDEX if versym else 1
        name = _string(strings, name, empty=True)
        if location == 0:
            _need(name and binding in (1, 2) and visibility == 0 and version != 0, "Unsupported undefined ELF symbol")
            if version == 1:
                unversioned_undefined += 1
            else:
                _need(version in needs, "Undefined symbol refers to an unknown GNU version")
                owner, tag = needs[version]
                requirements.setdefault(owner, []).append((name, tag, binding == 2))
        else:
            _need(version <= 1 or version in definitions, "Defined symbol refers to an unknown GNU version")
            if version and binding in (1, 2) and visibility in (0, 3):
                _need(name, "Unnamed public ELF symbol")
                if version == 1:
                    unversioned_exports.add(name)
                else:
                    exports.add((name, definitions[version]))
    return {
        "requirements": requirements,
        "exports": exports,
        "versions": {name for index, name in definitions.items() if index != 1},
        "unversioned_undefined": unversioned_undefined,
        "unversioned_exports": unversioned_exports,
        "has_versym": versym is not None,
    }
