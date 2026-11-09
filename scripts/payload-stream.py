#!/usr/bin/env python3
"""Extract partitions from the payload.bin of a full A/B OTA zip on a web server, without the zip.

A full OTA stores payload.bin uncompressed in the zip, and each partition's data is a run of
operations at known offsets in it. This reads the zip's central directory and the payload
manifest with HTTP range requests, then hands MysticGSI's own payload extractor
(mysticgsi/tools/extractor/formats/payload.py) a file object that fetches the byte ranges it
reads, so only the partitions asked for are downloaded (vivo's CN OTA: 13 GB zip, about 9 GB
for system, system_ext, product, odm and vendor). The server must answer Range requests.

Usage: mysticgsi/.venv/bin/python scripts/payload-stream.py <ota zip url> <out dir> <partition>[,<partition>...]
(MysticGSI's venv: its package needs protobuf and lz4.)
Writes <out dir>/<partition>.img and prints each partition's name and size.
"""
import importlib
import os
import struct
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK = 32 << 20


def fetch(url, start, end, tries=6):
    """Bytes start..end (inclusive) of url, retried with back-off."""
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status != 206:
                    raise IOError(f"HTTP {r.status} for a range request")
                data = r.read()
            if len(data) != end - start + 1:
                raise IOError(f"short range: {len(data)} of {end - start + 1}")
            return data
        except Exception as e:  # network errors: retry
            if n == tries - 1:
                raise
            print(f"range {start}-{end}: {e}; retrying", file=sys.stderr)
            time.sleep(2 ** n)


def remote_size(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


class HttpFile:
    """Read-only, seekable view of a remote file, read ahead in CHUNK pieces."""

    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0
        self.buf_start, self.buf = 0, b""
        self.fetched = 0

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        out = bytearray()
        while n > 0:
            if not (self.buf_start <= self.pos < self.buf_start + len(self.buf)):
                end = min(self.size, self.pos + max(n, CHUNK)) - 1
                self.buf = fetch(self.url, self.pos, end)
                self.buf_start = self.pos
                self.fetched += len(self.buf)
            o = self.pos - self.buf_start
            take = min(n, len(self.buf) - o)
            out += self.buf[o:o + take]
            self.pos += take
            n -= take
        return bytes(out)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def payload_offset(url, size):
    """Where payload.bin's data starts in the zip (it must be stored, not deflated)."""
    tail = fetch(url, max(0, size - (1 << 20)), size - 1)
    base = size - len(tail)
    e = tail.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack_from("<II", tail, e + 12)
    loc = tail.rfind(b"PK\x06\x07")
    if loc >= 0:
        z64 = struct.unpack_from("<Q", tail, loc + 8)[0]
        cd_size, cd_off = struct.unpack_from("<QQ", tail, z64 - base + 40)
    p = cd_off - base
    while tail[p:p + 4] == b"PK\x01\x02":
        comp, _, _, _, csz, usz, nl, el, cl = struct.unpack_from("<HHHIIIHHH", tail, p + 10)
        lho = struct.unpack_from("<I", tail, p + 42)[0]
        name = tail[p + 46:p + 46 + nl].decode(errors="replace")
        ex = tail[p + 46 + nl:p + 46 + nl + el]
        q = 0
        while q + 4 <= len(ex):
            hid, hsz = struct.unpack_from("<HH", ex, q)
            if hid == 1:
                r = q + 4
                for flag in ("u", "c", "o"):
                    big = {"u": usz, "c": csz, "o": lho}[flag] == 0xFFFFFFFF
                    if big:
                        v = struct.unpack_from("<Q", ex, r)[0]
                        r += 8
                        if flag == "u":
                            usz = v
                        elif flag == "c":
                            csz = v
                        else:
                            lho = v
            q += 4 + hsz
        if name == "payload.bin":
            if comp != 0:
                sys.exit("payload.bin is compressed in the zip: download the zip instead")
            head = fetch(url, lho, lho + 29)
            hnl, hel = struct.unpack_from("<HH", head, 26)
            return lho + 30 + hnl + hel
        p += 46 + nl + el + cl
    sys.exit("no payload.bin in the zip")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    url, out_dir, parts = sys.argv[1], sys.argv[2], set(sys.argv[3].split(","))
    sys.path.insert(0, os.path.join(ROOT, "mysticgsi"))
    payload = importlib.import_module("tools.extractor.formats.payload")
    if payload.pb is None:
        sys.exit("MysticGSI's payload extractor has no protobuf module (pip install protobuf)")
    size = remote_size(url)
    off = payload_offset(url, size)
    http = HttpFile(url, size)
    # The extractor opens its payload by path; give it the remote file instead.
    import builtins
    payload.open = lambda path, mode="r", *a, **k: http if path == "remote" else builtins.open(path, mode, *a, **k)
    # Its check opens the path as a local file: check the magic on the remote one.
    def remote_is_payload(path, offset=0):
        http.seek(offset)
        return http.read(4) == payload.PAYLOAD_MAGIC
    payload.is_payload = remote_is_payload
    t0 = time.time()
    done = payload.extract_payload("remote", out_dir, parts, logger=lambda m: print(m, file=sys.stderr), offset=off)
    for p in sorted(done):
        print(p, os.path.getsize(p))
    print(f"downloaded {http.fetched / 1e9:.2f} GB in {time.time() - t0:.0f} s", file=sys.stderr)
    missing = parts - {os.path.basename(p)[:-4] for p in done}
    if missing:
        sys.exit(f"not in the payload: {sorted(missing)}")


if __name__ == "__main__":
    main()
