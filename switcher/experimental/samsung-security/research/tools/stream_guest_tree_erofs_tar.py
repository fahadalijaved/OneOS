"""Stream the sealed donor tree to the held mkfs.erofs full-tar input."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import re
import stat
import sys
import tarfile

import materialize_guest_tree as tree


ROOT = tree.ROOT
BLOCK = 512
END = bytes(2 * BLOCK)
TYPES = {'directory': tarfile.DIRTYPE, 'file': tarfile.REGTYPE, 'symlink': tarfile.SYMTYPE}
require = tree.require


def pad(size):
    return (-size) % BLOCK


def pax_record(key, value):
    require(re.fullmatch(rb'[A-Za-z0-9_.]+', key), 'Invalid PAX key')
    body = b' ' + key + b'=' + value + b'\n'
    size = len(body) + 1
    while len(body) + len(str(size)) != size:
        size = len(body) + len(str(size))
    return str(size).encode('ascii') + body


def needs_binary(fields):
    try:
        for raw in fields:
            raw.decode('utf-8')
    except UnicodeDecodeError:
        return True
    return False


def header(name, kind, mode, uid, gid, size):
    # Only synthetic ASCII names are put in the fixed USTAR fields. PAX
    # carries the actual raw names and arbitrary-length symlink payloads.
    item = tarfile.TarInfo(name)
    item.type, item.mode, item.uid, item.gid, item.size = kind, mode, uid, gid, size
    item.mtime = 0
    return item.tobuf(format=tarfile.USTAR_FORMAT, encoding='ascii', errors='strict')


def frames(plan):
    yield None, b'.', {}, header('.', tarfile.DIRTYPE, 0o755, 0, 0, 0)
    for index, (path, node) in enumerate(plan.items()):
        actual = b'tree' + (b'/' + b'/'.join(path) if path else b'')
        fields = {b'path': actual}
        if node.kind == 'symlink':
            require(node.mode == 0o777 and node.target and b'\0' not in node.target, 'Unselected symlink profile')
            fields[b'linkpath'] = node.target
        if needs_binary(fields.values()):
            fields = {b'hdrcharset': b'BINARY'} | fields
        for name, value in node.attrs:
            fields[b'SCHILY.xattr.' + name] = value
        pax = b''.join(pax_record(key, value) for key, value in fields.items())
        name = f'{index:08x}'
        size = node.size if node.kind == 'file' else 0
        prelude = (header('PaxHeaders/' + name, tarfile.XHDTYPE, 0o644, 0, 0, len(pax)) + pax + bytes(pad(len(pax))) +
                   header('PaxEntries/' + name, TYPES[node.kind], node.mode, node.uid, node.gid, size))
        yield node, actual, fields, prelude


def read_pax(raw):
    result = {}
    pos = 0
    while pos < len(raw):
        blank = raw.index(b' ', pos)
        digits = raw[pos:blank]
        require(re.fullmatch(rb'[1-9][0-9]*', digits), 'Invalid PAX length')
        end = pos + int(digits)
        require(blank + 1 < end <= len(raw) and raw[end - 1:end] == b'\n', 'Invalid PAX record boundary')
        key, sep, value = raw[blank + 1:end - 1].partition(b'=')
        require(sep and key not in result, 'Invalid or duplicate PAX field')
        result[key] = value
        pos = end
    return result


def read_header(raw):
    require(len(raw) == BLOCK and raw[257:263] == b'ustar\0', 'Invalid USTAR block')
    return tarfile.TarInfo.frombuf(raw, encoding='ascii', errors='strict')


def read_frame(raw):
    first = read_header(raw[:BLOCK])
    if first.type != tarfile.XHDTYPE:
        require(len(raw) == BLOCK, 'Unexpected bare header framing')
        return first, {}
    pax_end = BLOCK + first.size
    next_header = pax_end + pad(first.size)
    require(raw[pax_end:next_header] == bytes(pad(first.size)) and len(raw) == next_header + BLOCK,
            'Invalid PAX padding or entry framing')
    return read_header(raw[next_header:]), read_pax(raw[BLOCK:pax_end])


def summarize(plan):
    headers = hashlib.sha256()
    archive_size = len(END)
    count = 0
    for node, actual, expected, prelude in frames(plan):
        item, fields = read_frame(prelude)
        require(fields == expected and fields.get(b'path', b'.') == actual, 'Generated PAX bytes differ on readback')
        if node is None:
            want = (tarfile.DIRTYPE, 0o755, 0, 0, 0)
            require(item.name == '.', 'Unexpected carrier root name')
        else:
            want = (TYPES[node.kind], node.mode, node.uid, node.gid, node.size if node.kind == 'file' else 0)
        require((item.type, item.mode, item.uid, item.gid, item.size) == want and item.mtime == 0,
                'Generated USTAR metadata differs on readback')
        headers.update(prelude)
        archive_size += len(prelude) + item.size + pad(item.size)
        count += 1
    return {'archiveEntries': count, 'donorEntries': count - 1, 'projectedTarBytes': archive_size,
            'metadataFrameSha256': headers.hexdigest()}


def write_all(sink, data):
    rest = memoryview(data)
    while rest:
        count = sink.write(rest)
        require(type(count) is int and 0 < count <= len(rest), 'Short or invalid tar write')
        rest = rest[count:]


def write_zeros(sink, size):
    while size:
        count = min(size, tree.CHUNK)
        write_all(sink, tree.ZERO[:count])
        size -= count


def write_entries(plan, read_at, sink):
    for node, _, _, prelude in frames(plan):
        write_all(sink, prelude)
        if node is None or node.kind != 'file':
            continue
        cursor = 0

        def file_write(offset, chunk):
            nonlocal cursor
            require(cursor <= offset and offset + len(chunk) <= node.size, 'Nonsequential tar payload')
            write_zeros(sink, offset - cursor)
            write_all(sink, chunk)
            cursor = offset + len(chunk)

        tree.emit_payload(node.payload, read_at, file_write)
        write_zeros(sink, node.size - cursor + pad(node.size))


@contextmanager
def held_image(expected):
    path = tree.source.plain(ROOT / expected['path'])

    def named():
        s = path.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_size == expected['bytes'], 'Unexpected named image object')
        return tree.source.identity(s)

    before = named()
    if os.name == 'nt':
        require(list(before) == expected['namedFileIdentity'], 'Saved Windows donor identity differs')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb', buffering=0) as stream:
        initial = os.fstat(stream.fileno())
        require(stat.S_ISREG(initial.st_mode) and tree.source.identity(initial)[:4] == before[:4],
                'Named and held donor image differ')

        def read_at(offset, count):
            require(0 <= offset <= expected['bytes'] - count and 0 < count <= tree.CHUNK, 'Image read outside bound')
            stream.seek(offset)
            return stream.read(count)

        yield read_at
        require(tree.source.identity(os.fstat(stream.fileno())) == tree.source.identity(initial) and named() == before,
                'Image identity changed during tar source read')


def dry_run(plan, image):
    result = summarize(plan)
    paths = ((b'system', b'bin', b'app_process64'), (b'system', b'bin', b'run-as'))
    read_bytes = 0
    with held_image(image) as held:
        def read_sample(offset, count):
            nonlocal read_bytes
            read_bytes += count
            require(read_bytes <= 128 * 1024, 'Dry-run image budget exceeded')
            return held(offset, count)

        for path in paths:
            tree.emit_payload(plan[path].payload, read_sample, lambda offset, raw: None)
    return result | {'status': 'PASS_METADATA_AND_BOUNDED_IMAGE_DRY_RUN_ONLY', 'planSha256': tree.PLAN_SHA,
                     'sampledPayloadSha256': {'/'.join(p.decode() for p in path): plan[path].payload['sha256']
                                               for path in paths}, 'imageBytesRead': read_bytes,
                     'wholeImageRehashed': False, 'tarWritten': False, 'mkfsInvoked': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--stream', action='store_true')
    args = parser.parse_args()
    try:
        require(not args.stream or not sys.stdout.isatty(), 'Refusing a binary tar on an interactive terminal')
        plan, image, _ = tree.load_plan()
        if args.dry_run:
            print(json.dumps(dry_run(plan, image), indent=2))
            return 0
        if os.name == 'nt':
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        sink = sys.stdout.buffer
        with held_image(image) as read_at:
            require(tree.hash_stream(read_at, image['bytes']) == image['sha256'], 'Fresh whole image SHA-256 differs')
            write_entries(plan, read_at, sink)
        # No terminator until every payload and the source identity checks pass.
        write_all(sink, END)
        sink.flush()
        return 0
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f'EROFS tar source refused: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
