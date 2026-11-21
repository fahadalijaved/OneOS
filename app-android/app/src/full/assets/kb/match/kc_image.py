#!/usr/bin/env python3
"""Read arm64e kernel images: fileset entries, chained fixups, function starts and code references."""
import struct

LC_SEGMENT_64, LC_SYMTAB, LC_FUNCTION_STARTS = 0x19, 0x2, 0x26
LC_DYLD_CHAINED_FIXUPS, LC_FILESET_ENTRY = 0x80000034, 0x80000035
PTR_ARM64E_KERNEL, PTR_64_KERNEL_CACHE = 7, 8


class Image:
    """One Mach-O header inside a file; segment file offsets are absolute in that file."""

    def __init__(self, data, at=0):
        self.data, self.at = data, at
        magic, cpu, _, self.kind, count, size = struct.unpack_from('<6I', data, at)
        if (magic, cpu) != (0xfeedfacf, 0x100000c):
            raise ValueError('Expected a 64-bit ARM Mach-O header')
        self.segments, self.sections, self.commands = [], [], []
        self.entries = {}
        offset = at + 32
        for _ in range(count):
            command, length = struct.unpack_from('<II', data, offset)
            self.commands.append((command, offset, length))
            if command == LC_SEGMENT_64:
                name, va, vmsize, fileoff, filesize = struct.unpack_from('<16s4Q', data, offset + 8)
                name = name.rstrip(b'\0').decode()
                self.segments.append({'name': name, 'va': va, 'size': vmsize,
                                      'fileoff': fileoff, 'filesize': filesize, 'command_offset': offset})
                nsects, = struct.unpack_from('<I', data, offset + 64)
                for index in range(nsects):
                    s = offset + 72 + 80 * index
                    sect, seg = (data[s + i:s + i + 16].rstrip(b'\0').decode() for i in (0, 16))
                    va_s, size_s = struct.unpack_from('<QQ', data, s + 32)
                    self.sections.append({'segment': seg, 'name': sect, 'va': va_s, 'size': size_s})
            elif command == LC_FILESET_ENTRY:
                va, fileoff, name_at = struct.unpack_from('<QQI', data, offset + 8)
                end = data.index(b'\0', offset + name_at)
                self.entries[data[offset + name_at:end].decode()] = (va, fileoff)
            offset += length
        self.base = next(s['va'] for s in self.segments if s['fileoff'] == 0 and s['filesize']) \
            if at == 0 else self.segments[0]['va']

    def command(self, kind):
        found = [(offset, length) for command, offset, length in self.commands if command == kind]
        return found[0] if found else None

    def mapped(self):
        return [(s['va'], s['va'] + s['size']) for s in self.segments if s['size'] and s['name'] != '__LINKEDIT']

    def offset(self, va, length=1):
        for s in self.segments:
            if s['va'] <= va and va + length <= s['va'] + s['filesize']:
                return s['fileoff'] + va - s['va']
        raise ValueError(f'Unbacked address {va:#x}')

    def read(self, va, length):
        at = self.offset(va, length)
        return self.data[at:at + length]

    def section(self, va):
        for s in self.sections:
            if s['va'] <= va < s['va'] + s['size']:
                return s
        return None

    def cstring(self, va):
        section = self.section(va)
        if section is None or section['segment'] not in ('__TEXT', '__DATA_CONST') or \
                not section['name'].startswith(('__cstring', '__const', '__os_log')):
            return None
        at = self.offset(va)
        end = self.data.find(b'\0', at, at + 4096)
        if end <= at:
            return None
        raw = self.data[at:end]
        return raw.decode('latin-1') if all(32 <= b < 127 or b in (9, 10) for b in raw) else None

    def symbols(self):
        """Defined section symbols, address -> names."""
        found = self.command(LC_SYMTAB)
        result = {}
        if not found:
            return result
        symoff, count, stroff, _ = struct.unpack_from('<4I', self.data, found[0] + 8)
        for index in range(count):
            strx, kind, _, _, value = struct.unpack_from('<IBBHQ', self.data, symoff + 16 * index)
            if kind & 0xe0 or kind & 0x0e != 0x0e:
                continue
            end = self.data.index(b'\0', stroff + strx)
            result.setdefault(value, []).append(self.data[stroff + strx:end].decode())
        return result

    def absolute_symbols(self):
        """Named N_ABS values; unlike section symbols these do not move with code."""
        found = self.command(LC_SYMTAB)
        result = {}
        if not found:
            return result
        symoff, count, stroff, _ = struct.unpack_from('<4I', self.data, found[0] + 8)
        for index in range(count):
            strx, kind, _, _, value = struct.unpack_from('<IBBHQ', self.data, symoff + 16 * index)
            if kind & 0xe0 or kind & 0x0e != 0x02:
                continue
            end = self.data.index(b'\0', stroff + strx)
            name = self.data[stroff + strx:end].decode()
            if name in result and result[name] != value:
                raise ValueError(f'Conflicting absolute symbol {name}')
            result[name] = value
        return result

    def function_starts(self):
        found = self.command(LC_FUNCTION_STARTS)
        if not found:
            return []
        dataoff, size = struct.unpack_from('<II', self.data, found[0] + 8)
        text = next(s['va'] for s in self.segments if s['name'] == '__TEXT')
        starts, address, at, end = [], text, dataoff, dataoff + size
        while at < end:
            value = shift = 0
            while True:
                byte = self.data[at]; at += 1
                value |= (byte & 0x7f) << shift; shift += 7
                if not byte & 0x80:
                    break
            if not value:
                break
            address += value
            starts.append(address)
        return starts

    def fixups(self):
        """Chained fixups: site va -> (target va, auth, key, diversity, address diversity)."""
        found = self.command(LC_DYLD_CHAINED_FIXUPS)
        if not found:
            return {}
        dataoff, _ = struct.unpack_from('<II', self.data, found[0] + 8)
        _, starts_offset, _, _, imports, _, _ = struct.unpack_from('<7I', self.data, dataoff)
        if imports:
            raise ValueError('Chained fixup imports are not supported')
        table = dataoff + starts_offset
        count, = struct.unpack_from('<I', self.data, table)
        result = {}
        for index in range(count):
            relative, = struct.unpack_from('<I', self.data, table + 4 + 4 * index)
            if not relative:
                continue
            at = table + relative
            _, page_size, fmt, segment_offset, _, pages = struct.unpack_from('<IHHQIH', self.data, at)
            if fmt not in (PTR_ARM64E_KERNEL, PTR_64_KERNEL_CACHE):
                raise ValueError(f'Unsupported chained pointer format {fmt}')
            for page, start in enumerate(struct.unpack_from(f'<{pages}H', self.data, at + 22)):
                if start == 0xffff:
                    continue
                if start & 0x8000:
                    raise ValueError('Multi-start pages are not supported')
                site = self.base + segment_offset + page * page_size + start
                while True:
                    value, = struct.unpack_from('<Q', self.data, self.offset(site, 8))
                    auth = value >> 63
                    if fmt == PTR_64_KERNEL_CACHE:
                        if (value >> 30) & 3:
                            raise ValueError('Only cache level 0 is supported')
                        target, step = self.base + (value & 0x3fffffff), (value >> 51) & 0xfff
                    else:
                        if (value >> 62) & 1:
                            raise ValueError('Chained binds are not supported')
                        offset = value & 0xffffffff if auth else (value & 0x7ffffffffff) | ((value >> 43) & 0xff) << 56
                        target, step = self.base + offset, (value >> 51) & 0x7ff
                    result[site] = (target, auth, (value >> 49) & 3 if auth else None,
                                    (value >> 32) & 0xffff if auth else None, (value >> 48) & 1 if auth else None)
                    if not step:
                        break
                    site += step * 4
        return result


def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def scan(code, pc, with_origins=False):
    """Branch targets, resolved adrp-based addresses and a relocation-masked shape of one function."""
    calls, refs, shape, pages = [], [], [], {}
    for offset in range(0, len(code) - 3, 4):
        word, = struct.unpack_from('<I', code, offset)
        here = pc + offset
        if word & 0x7c000000 == 0x14000000:
            target = here + signed(word & 0x3ffffff, 26) * 4
            calls.append((here, target, bool(word >> 31)))
            shape.append(word if pc <= target < pc + len(code) else word & 0xfc000000)
            pages.clear()
            continue
        if word & 0x9f000000 == 0x90000000:
            immediate = signed(((word >> 5) & 0x7ffff) << 2 | ((word >> 29) & 3), 21)
            pages[word & 31] = ((here & ~4095) + (immediate << 12), here)
            shape.append(word & 0x9f00001f)
            continue
        if word & 0x9f000000 == 0x10000000:
            ref = (here, here + signed(((word >> 5) & 0x7ffff) << 2 | ((word >> 29) & 3), 21), 'adr')
            refs.append(ref + (None, 0) if with_origins else ref)
            shape.append(word & 0x9f00001f)
            pages.pop(word & 31, None)
            continue
        base = (word >> 5) & 31
        if word & 0xff800000 == 0x91000000 and base in pages:
            shift = 12 if word & 0x400000 else 0
            ref = (here, pages[base][0] + (((word >> 10) & 0xfff) << shift), 'add')
            refs.append(ref + (pages[base][1], shift) if with_origins else ref)
            shape.append(word & 0xffc003ff)
            pages.pop(word & 31, None)
            continue
        if word & 0x3b000000 == 0x39000000 and base in pages:
            size = word >> 30
            if word & 0x04800000 == 0x04800000:
                size = 4
            ref = (here, pages[base][0] + (((word >> 10) & 0xfff) << size), 'ldst')
            refs.append(ref + (pages[base][1], size) if with_origins else ref)
            shape.append(word & 0xffc003ff)
            # A load can replace the register that held the page. Dropping a
            # store's source register is conservative and also handles SIMD
            # encodings without pretending to perform full register analysis.
            pages.pop(word & 31, None)
            continue
        shape.append(word)
        # Never carry a guessed register value through a clobber or control
        # flow merge. Only the recognized straight-line operations above keep
        # page provenance; an unknown instruction terminates that evidence.
        pages.clear()
    return calls, refs, shape
