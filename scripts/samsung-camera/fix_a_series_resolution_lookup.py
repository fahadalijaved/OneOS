"""One UI's camera in a guest on Galaxy A phones: a size its own table does not have, at the lookup itself.

The guest's Samsung Camera is the S26 Ultra's. Its size table (an enum, l9.a2 in that build) has two
lookups, by stored id and by "WxH" text, and both throw IllegalArgumentException
"getResolution : argument is invalid - ..." on a miss. The A phones give it misses the S26 Ultra never
does, and the camera died at launch from one caller after another:

- id -1 ("no size of this camera"): te.c0.S0 (fix_a_series_modes.py), vc.j.U
  (fix_a_series_resolution.py), then te.c0.T from vc.a.get (0.4.83 A16 4G 4181d97f, HyperOS);
- "8000x6000", the A34's 48 MP size: bc.l.c from bc.l's static initializer (0.4.83 A34 f2ab1ca4 ColorOS,
  a342243c HyperOS). The by-text lookup has dozens of callers (29 in te.c0 alone).

So the two lookups themselves stop throwing where there is something sensible to give: before the throw,
the miss goes to oneos.camera.OneOSResolution (helpers/src, helpers/build.sh). By text: the entry of the
same shape with the nearest pixel count (8000x6000 -> 8160x6120, which the label table bc.l.a also has;
the picture-size menu then says 50 MP on a 48 MP sensor). By id: the plain 4000x3000 entry. When the
helper has nothing to give it returns null and the camera throws as before. The two guards of the
earlier patchers stay as they are (they leave their methods before the lookup).

Some of the camera's methods call a lookup to find out whether a value exists and catch the exception
(ac.d.a, restoring a settings backup, tries one size after another; te.c0.u0). A stand-in there would
change what they do on every phone, so they keep the throw: each method that calls a lookup inside a
try range whose handler does anything but release a lock and throw on (a synchronized block's handler,
te.c0.I and te.c0.k) is written by name into the helper's list, and the helper gives a caller on that
list nothing. Only the lookups' direct callers are looked at: a method further up that catches what
such a caller lets through gets the stand-in's result instead of its exception.

The dex file that holds the table has no room for new method references (classes2.dex: 65535 of
65536; a first version with two static helper methods did not assemble). The helper is therefore
reached through its field LOOKUP and BiFunction.apply, which that dex file must already call: one new
field reference, no new method reference. Each lookup gets one more local register.

What a stand-in size does when the camera really takes a picture with it (the A34's 48 MP mode) is not
known: no A phone has run this.

Found by the message string and the methods' shape; every pattern must match exactly once and the
table's names must read as sizes, or nothing is written.

Usage: fix_a_series_resolution_lookup.py <decoded SamsungCamera.apk root>
Prints the smali_* directories (dex files) it changed or added, one per line; the summary goes to stderr.
"""
import os
import re
import sys

MSG = '"getResolution : argument is invalid - "'
HELPER = "Loneos/camera/OneOSResolution;"
FIELD = HELPER + "->LOOKUP:Ljava/util/function/BiFunction;"
APPLY = "Ljava/util/function/BiFunction;->apply(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;"
BOX = "Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;"
MARK = "oneos_resolution_lookup"
CATCHERS = "@oneos-callers-that-catch@"
# What catches an IllegalArgumentException.
CATCHES = ("Ljava/lang/IllegalArgumentException;", "Ljava/lang/RuntimeException;", "Ljava/lang/Exception;",
           "Ljava/lang/Throwable;")
DEFAULT_NAME = '"RESOLUTION_4000X3000"'
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = r"(?:\s*\.line \d+\n|\s*\n)*"
# Instructions whose first operand is the register they write.
WRITES = re.compile(r"^\s*(?:move(?!-exception)\S*|const\S*|new-instance|new-array|check-cast|instance-of|array-length|[is]get\S*|aget\S*"
                    r"|(?:neg|not|add|sub|mul|div|rem|and|or|xor|shl|shr|ushr|int|long|float|double|cmp)\S*) (p0)\b", re.M)


def fail(msg):
    sys.exit("fix_a_series_resolution_lookup: " + msg)


def guard(body, cls, how, by_id, label):
    """The method body with the helper call before its one throw of MSG, and one more local register."""
    throw = re.compile(r"^(?P<ind>[ \t]*)new-instance (?P<a>v\d+), Ljava/lang/IllegalArgumentException;\n" + SKIP
                       + r"[ \t]*const-string (?P<b>v\d+), " + re.escape(MSG) + r"\n", re.M)
    hits = list(throw.finditer(body))
    if len(hits) != 1:
        fail("%s: the throw with the message found %d times" % (how, len(hits)))
    m = hits[0]
    a, b, ind = m.group("a"), m.group("b"), m.group("ind")
    if a == b:
        fail("%s: one register for the exception and its message" % how)
    before = body[:m.start()]
    if WRITES.search(before) or re.search(r"^\s*move-result\S* p0\b", before, re.M):
        fail("%s: the argument is overwritten before the throw" % how)
    # The throw is reached only by a jump: a label right before it.
    if not re.search(r"^[ \t]*:\w+\n" + SKIP + r"\Z", before, re.M):
        fail("%s: no label right before the throw" % how)
    locs = list(re.finditer(r"^([ \t]*)\.locals (\d+)$", body, re.M))
    if len(locs) != 1 or not 2 <= int(locs[0].group(2)) <= 12 or locs[0].start() > m.start():
        fail("%s: no usable .locals" % how)
    n = int(locs[0].group(2))
    c = "v%d" % n
    if by_id and BOX not in before:
        fail("%s: the method does not box its id (a new method reference)" % how)
    key = (f"{ind}invoke-static {{p0}}, {BOX}\n\n{ind}move-result-object {a}\n\n" if by_id else "")
    add = (f"{ind}# OneOS (fix_a_series_resolution_lookup.py): a size this camera's table does not have gets the\n"
           f"{ind}# nearest entry (oneos.camera.OneOSResolution); with nothing to give, the throw below as before.\n"
           + key +
           f"{ind}invoke-static {{}}, {cls}->values()[{cls}\n\n"
           f"{ind}move-result-object {b}\n\n"
           f"{ind}sget-object {c}, {FIELD}\n\n"
           f"{ind}invoke-interface {{{c}, {a if by_id else 'p0'}, {b}}}, {APPLY}\n\n"
           f"{ind}move-result-object {a}\n\n"
           f"{ind}instance-of {b}, {a}, {cls}\n\n"
           f"{ind}if-eqz {b}, :{label}\n\n"
           f"{ind}check-cast {a}, {cls}\n\n"
           f"{ind}return-object {a}\n\n"
           f"{ind}:{label}\n")
    body = body[:m.start()] + add + body[m.start():]
    return body[:locs[0].start()] + "%s.locals %d" % (locs[0].group(1), n + 1) + body[locs[0].end():]


def rethrows(lines, pos, at):
    """A handler that only releases a lock and throws on what it caught (a synchronized block's)."""
    reg = None
    for _ in range(60):
        if at >= len(lines):
            return False
        s = lines[at]
        if not s or s[0] in ":." or s[0] == "#":
            at += 1
            continue
        m = re.fullmatch(r"move-exception (\w+)", s)
        if m:
            reg = m.group(1)
            at += 1
            continue
        if re.fullmatch(r"monitor-exit \w+", s):
            at += 1
            continue
        m = re.fullmatch(r"goto(?:/16|/32)? (:\w+)", s)
        if m:
            if m.group(1) not in pos:
                return False
            at = pos[m.group(1)]
            continue
        m = re.fullmatch(r"throw (\w+)", s)
        return bool(m) and m.group(1) == reg
    return False


def catchers(root, smali, calls):
    """The methods ("te.c0.u0") that call a lookup where they catch its exception and do not throw it on."""
    found = set()
    for d in smali:
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if not f.endswith(".smali"):
                    continue
                t = open(os.path.join(dp, f), encoding="utf-8").read()
                if not any(c in t for c in calls):
                    continue
                owner = re.search(r"^\.class [^\n]*?L([^;\s]+);$", t, re.M)
                if not owner:
                    fail("%s: no class line" % f)
                for m in re.finditer(r"^\.method [^\n]*?([\w$<>-]+)\([^\n]*\n(.*?)^\.end method$", t, re.M | re.S):
                    lines = [x.strip() for x in m.group(2).split("\n")]
                    sites = [i for i, x in enumerate(lines) if x.startswith("invoke-static") and any(c in x for c in calls)]
                    if not sites:
                        continue
                    pos = {x: i for i, x in enumerate(lines) if x.startswith(":")}
                    for x in lines:
                        c = re.fullmatch(r"\.catch(?:all| (\S+)) \{(:\w+) \.\. (:\w+)\} (:\w+)", x)
                        if not c:
                            if x.startswith(".catch"):
                                fail("%s: a catch line this does not read: %s" % (f, x[:80]))
                            continue
                        if c.group(1) is not None and c.group(1) not in CATCHES:
                            continue
                        if any(l not in pos for l in c.group(2, 3, 4)):
                            fail("%s: a catch line without its labels" % f)
                        if any(pos[c.group(2)] < i < pos[c.group(3)] for i in sites) and not rethrows(lines, pos, pos[c.group(4)]):
                            found.add(owner.group(1).replace("/", ".") + "." + m.group(1))
    return sorted(found)


def main(root):
    if not os.path.isdir(root):
        fail("%s is not a folder" % root)
    smali = sorted(d for d in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", d))
    hits = []
    for d in smali:
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if f.endswith(".smali"):
                    p = os.path.join(dp, f)
                    t = open(p, encoding="utf-8").read()
                    if MSG in t:
                        hits.append((d, p, t))
    if len(hits) != 1:
        fail("the size lookup's message found in %d classes" % len(hits))
    d, p, t = hits[0]
    if HELPER in t or MARK in t:
        fail("already patched")
    # The way to the helper must cost this dex file no method reference: it has to call BiFunction.apply already.
    if not any(APPLY in open(os.path.join(dp, f), encoding="utf-8").read()
               for dp, _, fs in os.walk(os.path.join(root, d)) for f in fs if f.endswith(".smali")):
        fail("%s does not call BiFunction.apply yet (the call would be a new method reference)" % d)
    m = re.search(r"^\.class [^\n]*\benum (L[\w/$]+;)$", t, re.M)
    if not m or not re.search(r"^\.super Ljava/lang/Enum;$", t, re.M):
        fail("the class with the message is not an enum")
    cls = m.group(1)
    if not re.search(r"^\.method public static values\(\)\[" + re.escape(cls) + "$", t, re.M):
        fail("the size table has no values()")
    # The helper reads the entries by name: they must be the names it reads.
    names = set(re.findall(r'^\s*const-string(?:/jumbo)? \w+, "(RESOLUTION_\d{2,5}X\d{2,5}(?:_\d+FPS)?)"$', t, re.M))
    fields = set(re.findall(r"^\.field public static final enum (\w+):" + re.escape(cls) + "$", t, re.M))
    if len(fields) < 20 or DEFAULT_NAME.strip('"') not in fields or len(names & fields) * 10 < len(fields) * 9:
        fail("the size table's entries are not named RESOLUTION_<W>X<H> (%d entries, %d read as sizes)" % (len(fields), len(names & fields)))
    methods = list(re.finditer(r"^\.method public static (\w+)\((I|Ljava/lang/String;)\)" + re.escape(cls) + r"\n(.*?)^\.end method\n", t, re.M | re.S))
    by_id = [x for x in methods if x.group(2) == "I" and MSG in x.group(3)]
    by_text = [x for x in methods if x.group(2) != "I" and MSG in x.group(3)]
    if len(by_id) != 1 or len(by_text) != 1:
        fail("the lookups with the message: %d by id, %d by text" % (len(by_id), len(by_text)))
    # Later method first: the earlier one's offsets stay good.
    for x, how, label in sorted(((by_id[0], "by id", MARK + "_id"), (by_text[0], "by text", MARK + "_text")),
                                key=lambda r: -r[0].start()):
        body = guard(x.group(3), cls, how, x.group(2) == "I", label)
        t = t[:x.start(3)] + body + t[x.end(3):]
    keep = catchers(root, smali, [f"{cls}->{x.group(1)}({x.group(2)}){cls}" for x in (by_id[0], by_text[0])])
    if not all(re.fullmatch(r"[\w$<>.-]+", k) for k in keep):
        fail("a caller's name this cannot write into the helper")
    helper = open(os.path.join(HERE, "helpers", "smali", "OneOSResolution.smali"), encoding="utf-8").read()
    if helper.count('" %s "' % CATCHERS) != 1 or helper.count(CATCHERS) != 1:
        fail("helpers/smali/OneOSResolution.smali has no place for the callers that catch (helpers/build.sh)")
    helper = helper.replace(CATCHERS, " ".join(keep))
    open(p, "w", encoding="utf-8").write(t)

    have = [s for s in smali if os.path.exists(os.path.join(root, s, "oneos", "camera", "OneOSResolution.smali"))]
    if have:
        own = have[0]
    else:
        own = "smali_classes%d" % (max(int(s[len("smali_classes"):]) if s != "smali" else 1 for s in smali) + 1)
        os.makedirs(os.path.join(root, own, "oneos", "camera"))
    open(os.path.join(root, own, "oneos", "camera", "OneOSResolution.smali"), "w", encoding="utf-8").write(helper)
    print(d)
    print(own)
    print("fix_a_series_resolution_lookup: %s by id (%s) and by text (%s) in %s ask OneOSResolution (%s) before they throw; %d entries; "
          "%d callers catch a miss themselves and keep it: %s"
          % (cls, by_id[0].group(1), by_text[0].group(1), os.path.relpath(p, root), own, len(fields), len(keep), " ".join(keep) or "-"),
          file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
