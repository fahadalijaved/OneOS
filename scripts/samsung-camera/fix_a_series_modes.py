"""One UI's camera in a guest on Galaxy A phones: settings the S26 Ultra's camera does not know.

The guest's Samsung Camera is the S26 Ultra's (samcam_bar.tar). The A phones' own camera
settings name things that camera has no table entry for, and it crashed at launch
(0.4.59 reports, ColorOS / HyperOS / Nothing OS on the A26, A27, A35, A36, A56):

- "getResolution : argument is invalid - -1" (IllegalArgumentException in l9.a2.j, from
  te.c0.S0 on CamSettingBackgroundHandlerThread): the stored resolution id is -1 (no
  resolution of that camera matches), and the static check "is this resolution one of
  the special ones" looked it up anyway. An id below 0 now answers "no".
- "There is no matched ShootingModeIdByName with : LIVE_FOCUS_LITE" (NullPointerException
  in te.l0.a, in te.l0's static initializer, so ExceptionInInitializerError in
  Camera.onCreate): the A phones' feature table names a shooting mode the S26 Ultra's
  camera does not have. An unknown name now gets the answer an absent or empty entry
  already gets (-1: no such mode on that side).

Both are found by the methods' own message strings; the obfuscated names change with
each camera version. Every pattern must match exactly once, or nothing is written.

Usage: fix_a_series_modes.py <decoded SamsungCamera.apk root>
Prints the smali_* directories it changed (repatch-fixes.sh puts back only those dex files).
"""
import os
import re
import sys

RES_MSG = '"getResolution : argument is invalid - "'
MODE_MSG = '"There is no matched ShootingModeIdByName with : "'
MARK = "oneos_a_series"


def fail(msg):
    sys.exit("fix_a_series_modes: " + msg)


def smali_files(root):
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if f.endswith(".smali"):
                    yield d, os.path.join(dp, f)


def methods(text):
    return list(re.finditer(r"^\.method ([^\n]*)\n(.*?)^\.end method\n", text, re.M | re.S))


def code(body):
    """The instructions of a method body, without .line/.local and blank lines."""
    return [l.strip() for l in body.split("\n") if l.strip() and not re.match(r"\s*\.(line|local|end local|param|end param)\b", l)]


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    texts = {}
    res_cls, mode_hits = [], []
    for d, p in smali_files(root):
        t = open(p, encoding="utf-8").read()
        if RES_MSG in t or MODE_MSG in t:
            texts[p] = (d, t)
        if RES_MSG in t:
            m = re.search(r"^\.class [^\n]*?(L[\w/$]+;)$", t, re.M)
            # The lookup by id: static j(I)L<this class>; with the message.
            for mm in methods(t):
                if re.match(r"public static \w+\(I\)" + re.escape(m.group(1)) + "$", mm.group(1)) and RES_MSG in mm.group(2):
                    res_cls.append((m.group(1), re.match(r"public static (\w+)\(", mm.group(1)).group(1)))
        if MODE_MSG in t:
            mode_hits.append(p)
    if MARK in "".join(t for _, t in texts.values()):
        fail("already patched")
    if len(res_cls) != 1:
        fail("the resolution lookup by id was found %d times" % len(res_cls))
    if len(mode_hits) != 1:
        fail("the shooting mode lookup was found in %d classes" % len(mode_hits))
    cls, by_id = res_cls[0]
    changed = {}

    # 1. static X(I)Z = T(lookup(id)): an id below 0 answers false.
    call = "invoke-static {p0}, %s->%s(I)%s" % (cls, by_id, cls)
    hits = []
    for d, p in smali_files(root):
        t = changed.get(p, (None, None))[1] or open(p, encoding="utf-8").read()
        if call not in t:
            continue
        for mm in methods(t):
            if not re.match(r"public static (?:final )?\w+\(I\)Z$", mm.group(1)):
                continue
            c = code(mm.group(2))
            if len(c) == 6 and c[0] == ".locals 0" and c[1] == call and c[2] == "move-result-object p0" \
                    and re.fullmatch(r"invoke-static \{p0\}, L[\w/$]+;->\w+\(" + re.escape(cls) + r"\)Z", c[3]) \
                    and c[4] == "move-result p0" and c[5] == "return p0":
                hits.append((d, p, t, mm))
    if len(hits) != 1:
        fail("the 'special resolution' check on an id was found %d times" % len(hits))
    d, p, t, mm = hits[0]
    body = mm.group(2)
    i = body.index(call)
    body = (body[:i] + "if-ltz p0, :%s_res_unknown\n\n    # OneOS (fix_a_series_modes.py): an unknown resolution (-1) is not a special one.\n    " % MARK
            + body[i:] + "\n    :%s_res_unknown\n    const/4 p0, 0x0\n\n    return p0\n" % MARK)
    t = t[:mm.start(2)] + body + t[mm.end(2):]
    changed[p] = (d, t)

    # 2. The shooting mode by name: an unknown name is -1, like an absent entry.
    p = mode_hits[0]
    d, t = changed.get(p) or texts[p]
    ms = [mm for mm in methods(t) if MODE_MSG in mm.group(2)]
    if len(ms) != 1:
        fail("the shooting mode message is in %d methods" % len(ms))
    mm = ms[0]
    body = mm.group(2)
    cast = re.findall(r"^(\s*)check-cast (p1|v\d+|p\d+), Ljava/lang/Integer;$", body, re.M)
    req = re.findall(r"invoke-static \{(\w+), \w+\}, Ljava/util/Objects;->requireNonNull\(Ljava/lang/Object;Ljava/lang/String;\)Ljava/lang/Object;", body)
    neg = re.findall(r"^(\s*)const/4 (\w+), -0x1\n(?:\s*\.line \d+\n|\s*\n)*\s*return \2$", body, re.M)
    if len(cast) != 1 or len(req) != 1 or req[0] != cast[0][1] or len(neg) != 1:
        fail("the shooting mode lookup is not the code this was written for (casts %d, requireNonNull %d, -1 returns %d)"
             % (len(cast), len(req), len(neg)))
    reg = cast[0][1]
    body = re.sub(r"^(\s*check-cast %s, Ljava/lang/Integer;)$" % re.escape(reg),
                  r"\1\n\n    # OneOS (fix_a_series_modes.py): a mode this camera does not have (LIVE_FOCUS_LITE on the A phones) is -1.\n    if-eqz %s, :%s_mode_unknown" % (reg, MARK),
                  body, count=1, flags=re.M)
    body = re.sub(r"^(\s*const/4 \w+, -0x1\n(?:\s*\.line \d+\n|\s*\n)*\s*return \w+)$", r"    :%s_mode_unknown\n\1" % MARK, body, count=1, flags=re.M)
    t = t[:mm.start(2)] + body + t[mm.end(2):]
    changed[p] = (d, t)

    for p, (d, t) in changed.items():
        open(p, "w", encoding="utf-8").write(t)
        print("fix_a_series_modes: patched %s" % os.path.relpath(p, root), file=sys.stderr)
    print("\n".join(sorted({d for d, _ in changed.values()})))


if __name__ == "__main__":
    main()
