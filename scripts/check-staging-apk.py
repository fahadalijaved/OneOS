#!/usr/bin/env python3
"""Check the shipped APK's staging pins and payloads, without Android or third-party modules."""
import hashlib
import re
import struct
import sys
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_config(data):
    """Read BuildConfig's actual static field values from a standard DEX."""
    def u32(pos):
        return struct.unpack_from('<I', data, pos)[0]

    def leb(pos):
        value = shift = 0
        while True:
            b = data[pos]
            pos += 1
            value |= (b & 127) << shift
            if b < 128:
                return value, pos
            shift += 7

    strings = []
    for i in range(u32(56)):
        pos = u32(u32(60) + i * 4)
        _, pos = leb(pos)
        strings.append(data[pos:data.index(b'\0', pos)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + i * 4)] for i in range(u32(64))]
    fields = [strings[u32(u32(84) + i * 8 + 4)] for i in range(u32(80))]
    for i in range(u32(96)):
        pos = u32(100) + i * 32
        if types[u32(pos)] != 'Lcom/fahadali/oneos/BuildConfig;':
            continue
        class_data, values = u32(pos + 24), u32(pos + 28)
        count, cursor = leb(class_data)
        for _ in range(3):
            _, cursor = leb(cursor)
        names = []
        index = 0
        for _ in range(count):
            delta, cursor = leb(cursor)
            _, cursor = leb(cursor)
            index += delta
            names.append(fields[index])
        size, cursor = leb(values)
        result = {}
        for name in names[:size]:
            tag = data[cursor]
            cursor += 1
            kind, width = tag & 31, (tag >> 5) + 1
            if kind in (0x1e, 0x1f):  # null / boolean carry no bytes
                result[name] = None if kind == 0x1e else bool(tag >> 5)
                continue
            if kind not in (0, 2, 3, 4, 6, 16, 17, 23, 24, 25, 26, 27):
                raise ValueError(f'unsupported BuildConfig value type {kind}')
            value = int.from_bytes(data[cursor:cursor + width], 'little')
            cursor += width
            result[name] = strings[value] if kind == 23 else value
        return result
    return {}


def verify(path):
    with zipfile.ZipFile(path) as apk:
        names = apk.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate APK entries')
        pins = {}
        for name in names:
            if re.fullmatch(r'classes\d*\.dex', name):
                pins.update(build_config(apk.read(name)))
        root = apk.read('assets/root/oneos_root.sh')
        if pins.get('ROOT_SCRIPT_SHA256') != sha(root) or pins.get('ROOT_SCRIPT_BYTES') != len(root):
            raise ValueError('root script differs from compiled BuildConfig pin/size')
        index = {}
        for line in apk.read('assets/oneos/files/index.txt').decode().splitlines():
            digest, size = line.split()
            if digest in index or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError('invalid or duplicate size index entry')
            index[digest] = int(size)
        checked = set()
        manifests = [n for n in names if n.startswith('assets/oneos/sets/') and n.endswith('.sha256')]
        if 'assets/oneos/sets/scripts.sha256' not in manifests or len(manifests) < 2:
            raise ValueError('missing scripts or package manifests')
        for name in manifests:
            set_id = name.rsplit('/', 1)[1][:-7]
            field = 'SCRIPTS_SHA256' if set_id == 'scripts' else 'SET_' + set_id.upper().replace('-', '_') + '_SHA256'
            manifest = apk.read(name)
            if pins.get(field) != sha(manifest):
                raise ValueError(f'{set_id}: manifest differs from compiled {field}')
            files = set()
            for line in manifest.decode().splitlines():
                if not line or line.startswith('#'):
                    continue
                match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_][A-Za-z0-9._+\-]*)', line)
                if not match or match[2] in files:
                    raise ValueError(f'{set_id}: invalid or duplicate manifest entry')
                digest, filename = match.groups()
                files.add(filename)
                if digest in checked:
                    continue
                info = apk.getinfo('assets/oneos/files/' + digest)
                if index.get(digest) != info.file_size or info.file_size > 268435456:
                    raise ValueError(f'{set_id}/{filename}: missing/wrong size or exceeds root receive limit')
                h = hashlib.sha256()
                with apk.open(info) as payload:
                    for chunk in iter(lambda: payload.read(1024 * 1024), b''):
                        h.update(chunk)
                if h.hexdigest() != digest:
                    raise ValueError(f'{set_id}/{filename}: payload hash mismatch')
                checked.add(digest)
        return len(manifests), len(checked)


if __name__ == '__main__':
    try:
        manifests, payloads = verify(sys.argv[1])
        print(f'Staging integrity OK: {manifests} manifests, {payloads} payloads')
    except (ValueError, KeyError, IndexError, zipfile.BadZipFile) as error:
        sys.exit(f'Staging integrity FAILED: {error}')
