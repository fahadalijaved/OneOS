"""Framework resource ids (0x01xxxxxx) an APK uses, checked against two framework-res dumps."""
import re, struct, sys, zipfile, collections

apk, host_dump, guest_dump = sys.argv[1:4]


def ids_in(blob, xml):
    found = collections.Counter()
    n = len(blob)
    # Res_value: size 8, res0 0, type 1 (ref) / 2 (attr) / 7 (dynamic ref) / 8 (dynamic attr)
    for m in re.finditer(rb"\x08\x00\x00[\x01\x02\x07\x08](...)\x01", blob, re.S):
        data = struct.unpack_from("<I", blob, m.start() + 4)[0]
        found[data] += 1
        if not xml and m.start() >= 4:
            key = struct.unpack_from("<I", blob, m.start() - 4)[0]
            if key >> 24 == 0x01:
                found[key] += 1  # a style item's attribute
    if xml:
        o = 8
        while o + 8 <= n:
            typ, hsz, size = struct.unpack_from("<HHI", blob, o)
            if size < 8:
                break
            if typ == 0x0180:
                for k in range((size - hsz) // 4):
                    v = struct.unpack_from("<I", blob, o + hsz + 4 * k)[0]
                    if v >> 24 == 0x01:
                        found[v] += 1
            o += size
    return found


def names(dump):
    d = {}
    for line in open(dump, errors="replace"):
        m = re.match(r"\s*resource 0x(01[0-9a-f]{6}) (\S+)", line)
        if m:
            d[int(m.group(1), 16)] = m.group(2)
    return d


used = collections.Counter()
with zipfile.ZipFile(apk) as z:
    for n in z.namelist():
        if n == "resources.arsc":
            used.update(ids_in(z.read(n), False))
        elif n.endswith(".xml") and (n.startswith("res/") or n == "AndroidManifest.xml"):
            b = z.read(n)
            if b[:2] == b"\x03\x00":
                used.update(ids_in(b, True))
host, guest = names(host_dump), names(guest_dump)
missing, differs, ok = [], [], 0
for i in sorted(used):
    h = host.get(i)
    if h is None:
        continue  # not a real framework id (pattern noise)
    g = guest.get(i)
    if g is None:
        missing.append((i, h))
    elif g != h:
        differs.append((i, h, g))
    else:
        ok += 1
print("framework ids used and known to One UI: %d  same in Nothing: %d  missing in Nothing: %d  different meaning: %d"
      % (ok + len(missing) + len(differs), ok, len(missing), len(differs)))
by = collections.Counter(h.split("/")[0] for _, h in missing)
print("missing by type:", dict(by))
for i, h in missing[:400]:
    print("  MISSING 0x%08x %s" % (i, h))
for i, h, g in differs[:200]:
    print("  DIFFERS 0x%08x one-ui=%s nothing=%s" % (i, h, g))
