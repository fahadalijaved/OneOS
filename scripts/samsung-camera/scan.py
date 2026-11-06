"""Which classes and members Samsung Camera references that a guest framework lacks.

Usage: scan.py <universe jar dir(s), comma separated> <camera files...>
"""
import struct, sys, zipfile, glob, os, collections


def uleb(b, o):
    r = s = 0
    while True:
        x = b[o]; o += 1
        r |= (x & 0x7f) << s; s += 7
        if x < 0x80:
            return r, o


class Dex:
    def __init__(self, b):
        self.b = b
        u = lambda o: struct.unpack_from("<I", b, o)[0]
        self.nstr, self.ostr = u(0x38), u(0x3C)
        self.ntyp, self.otyp = u(0x40), u(0x44)
        self.nproto, self.oproto = u(0x48), u(0x4C)
        self.nfld, self.ofld = u(0x50), u(0x54)
        self.nmeth, self.ometh = u(0x58), u(0x5C)
        self.ncls, self.ocls = u(0x60), u(0x64)
        self._s = {}

    def s(self, i):
        if i in self._s:
            return self._s[i]
        off = struct.unpack_from("<I", self.b, self.ostr + 4 * i)[0]
        _, o = uleb(self.b, off)
        e = self.b.index(b"\0", o)
        v = self.b[o:e].decode("utf-8", "replace")
        self._s[i] = v
        return v

    def t(self, i):
        return self.s(struct.unpack_from("<I", self.b, self.otyp + 4 * i)[0])

    def proto(self, i):
        o = self.oproto + 12 * i
        _, ret, poff = struct.unpack_from("<III", self.b, o)
        ps = []
        if poff:
            n = struct.unpack_from("<I", self.b, poff)[0]
            ps = [self.t(struct.unpack_from("<H", self.b, poff + 4 + 2 * k)[0]) for k in range(n)]
        return "(" + "".join(ps) + ")" + self.t(ret)

    def field(self, i):
        c, ty, n = struct.unpack_from("<HHI", self.b, self.ofld + 8 * i)
        return self.t(c), self.s(n) + ":" + self.t(ty)

    def method(self, i):
        c, p, n = struct.unpack_from("<HHI", self.b, self.ometh + 8 * i)
        return self.t(c), self.s(n) + self.proto(p)

    def classes(self):
        for k in range(self.ncls):
            o = self.ocls + 32 * k
            ci, _, sup, ioff, _, _, cdo, _ = struct.unpack_from("<8I", self.b, o)
            name = self.t(ci)
            supn = self.t(sup) if sup != 0xFFFFFFFF else None
            ifs = []
            if ioff:
                n = struct.unpack_from("<I", self.b, ioff)[0]
                ifs = [self.t(struct.unpack_from("<H", self.b, ioff + 4 + 2 * j)[0]) for j in range(n)]
            members = set()
            if cdo:
                o2 = cdo
                sf, o2 = uleb(self.b, o2); inf, o2 = uleb(self.b, o2)
                dm, o2 = uleb(self.b, o2); vm, o2 = uleb(self.b, o2)
                for cnt, kind in ((sf, "f"), (inf, "f"), (dm, "m"), (vm, "m")):
                    idx = 0
                    for _ in range(cnt):
                        d, o2 = uleb(self.b, o2); idx += d
                        _, o2 = uleb(self.b, o2)
                        if kind == "m":
                            _, o2 = uleb(self.b, o2)
                            members.add(self.method(idx)[1])
                        else:
                            members.add(self.field(idx)[1])
            yield name, supn, ifs, members


def dexes_of(path):
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if n.startswith("classes") and n.endswith(".dex"):
                yield Dex(z.read(n))


def load(paths):
    defs = {}
    # A boot class path list next to the jars (build-cached.sh: nt/.bcp.txt): only its jars and the APEX jars
    # define the guest's classes, boot class path first.
    bcp = set()
    for d in {os.path.dirname(p) for p in paths}:
        f = os.path.join(d, ".bcp.txt")
        if os.path.isfile(f):
            bcp |= {l.strip() for l in open(f) if l.strip()}
    if bcp:
        paths = [p for p in paths if os.path.basename(p) in bcp] + [p for p in paths if os.path.basename(os.path.dirname(p)) == "apex"]
    for p in paths:
        try:
            for d in dexes_of(p):
                for name, sup, ifs, mem in d.classes():
                    if name not in defs:
                        defs[name] = (sup, ifs, mem)
        except zipfile.BadZipFile:
            pass
    return defs


def main():
    udirs = sys.argv[1].split(",")
    cam = sys.argv[2:]
    upaths = [p for d in udirs for p in glob.glob(os.path.join(d, "*.jar"))]
    universe = load(upaths)
    camdefs = load(cam)
    # The platform's own packages come from the boot class path; everything else
    # the app bundles (androidx, gson, kotlin...) is the app's copy, whatever
    # another jar of the image carries.
    PLATFORM = ("Landroid/", "Ljava/", "Ljavax/", "Ldalvik/", "Llibcore/", "Lcom/android/",
                "Lorg/apache/", "Lorg/json/", "Lorg/xml/", "Lorg/w3c/", "Lsun/")
    alldefs = dict(universe)
    for k, v in camdefs.items():
        if k not in universe or not k.startswith(PLATFORM):
            alldefs[k] = v
    universe = {k: v for k, v in universe.items() if k.startswith(PLATFORM) or k not in camdefs}

    def has(cls, member, seen=None):
        seen = seen or set()
        if cls in seen or cls not in alldefs:
            return None if cls not in alldefs else False
        seen.add(cls)
        sup, ifs, mem = alldefs[cls]
        if member in mem:
            return True
        for nxt in ([sup] if sup else []) + ifs:
            if nxt and nxt in alldefs and has(nxt, member, seen):
                return True
        return False

    def base(t):
        return t.lstrip("[")

    miss_cls = collections.Counter()
    miss_mem = collections.Counter()
    for p in cam:
        for d in dexes_of(p):
            for i in range(d.ntyp):
                t = base(d.t(i))
                if t.startswith("L") and t not in alldefs:
                    miss_cls[t] += 1
            refs = [d.method(i) for i in range(d.nmeth)] + [d.field(i) for i in range(d.nfld)]
            for c, m in refs:
                c = base(c)
                if not c.startswith("L") or c in camdefs and c not in universe and has(c, m):
                    continue
                if c not in alldefs:
                    continue  # counted as a missing class
                if has(c, m) is False:
                    miss_mem[(c, m)] += 1
    print("CAMERA CLASSES DEFINED:", len(camdefs), " UNIVERSE CLASSES:", len(universe))
    by_pkg = collections.Counter()
    for t in miss_cls:
        by_pkg[t.rsplit("/", 1)[0]] += 1
    print("\nMISSING CLASSES:", len(miss_cls))
    for pkg, n in by_pkg.most_common():
        print("  %4d  %s" % (n, pkg))
    print("\nMISSING MEMBERS ON PRESENT CLASSES:", len(miss_mem))
    by_cls = collections.defaultdict(list)
    for (c, m) in miss_mem:
        by_cls[c].append(m)
    for c in sorted(by_cls, key=lambda c: -len(by_cls[c])):
        print("  %s (%d): %s" % (c, len(by_cls[c]), ", ".join(sorted(by_cls[c])[:6]) + (" ..." if len(by_cls[c]) > 6 else "")))
    with open("missing_classes.txt", "w") as f:
        f.write("\n".join(sorted(miss_cls)))
    with open("missing_members.txt", "w") as f:
        f.write("\n".join("%s->%s" % k for k in sorted(miss_mem)))


main()
