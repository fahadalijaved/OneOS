"""One UI's camera in a guest on Galaxy S phones whose front camera has no sensor crop: the selfie never starts.

The S26 Ultra's camera keeps a table of normal-angle size -> sensor-crop size (te.f0.g), filled from
the phone's cameradata, and looks it up both ways:
- te.c0.S "getNormalAngleResolutionBySensorCropAngle": the normal-angle size whose crop is the given one;
- te.c0.u0 "getSensorCropResolution": the crop of the given normal-angle size (an unknown crop NAME is
  already caught there and gives the size itself; fix_a_series_crop.py was written for that case).
Both throw IllegalArgumentException when the size is not in the table at all, and none of their callers
catches it. The camera calls them for the front camera whenever its "sensor crop" (cropped selfie)
setting is on, which it is by default. On the Galaxy S24 FE (10 MP front, 3648x2736, no crop mode, so
no table entry) S threw "getNormalAngleResolutionBySensorCropAngle : Argument is wrong =
RESOLUTION_3648X2736" while the first preview request was being built and the camera stayed black: no
photo, no video (reports 44afc238, 0.5.31, and 97db2ff1, 0.5.32, ColorOS 17). A size the table does
not have now gives the size itself in both lookups: with no crop, the normal angle and the crop are
the size the sensor gives. Phones where the camera works never reach the changed paths.

Found by the methods' messages; fails closed when the code is not the shape it was written for (one
static method Resolution -> Resolution per message, which still throws with p0's name, p0 untouched on
every path to the throw). The getNormalAngle... lookup must be there; getSensorCrop... is patched when
present (an older camera build may not have it).

Usage: fix_sensor_crop_tables.py <decoded SamsungCamera.apk root>
Prints the smali_* directories it changed.
"""
import os
import re
import sys

MSGS = [('"getNormalAngleResolutionBySensorCropAngle : Argument is wrong = "', "oneos_sensor_crop_normal", True),
        ('"getSensorCropResolution : Argument is wrong = "', "oneos_sensor_crop_crop", False)]
WRITES = re.compile(r"^\s*(?:move-result-object|move-object(?:/from16|/16)?|sget-object|iget-object|const-string|const/\w+|const|"
                    r"check-cast|new-instance|aget-object) p0\b.*\n", re.M)


def fail(msg):
    sys.exit("fix_sensor_crop_tables: " + msg)


def patch(t, msg, mark):
    if mark in t:
        fail("already patched (%s)" % mark)
    ms = [m for m in re.finditer(r"^\.method public static (\w+)\((L[\w/$]+;)\)\2\n(.*?)^\.end method\n", t, re.M | re.S)
          if msg in m.group(3)]
    if len(ms) != 1:
        fail("the method with %s found %d times" % (msg, len(ms)))
    m = ms[0]
    body = m.group(3)
    if body.count(msg) != 1:
        fail("%s more than once in %s" % (msg, m.group(1)))
    # The throw: new-instance vX, IllegalArgumentException ... const-string msg ... Enum.name() of p0 ... throw.
    th = [x for x in re.finditer(r"^(\s*)new-instance (v\d+), Ljava/lang/IllegalArgumentException;\n", body, re.M)
          if msg in body[x.end():].split("throw", 1)[0]]
    if len(th) != 1:
        fail("the throw with %s found %d times in %s" % (msg, len(th), m.group(1)))
    t0 = th[0]
    upto = body[t0.end():].split("throw", 1)[0]
    if not re.search(r"invoke-virtual \{p0\}, Ljava/lang/Enum;->name\(\)Ljava/lang/String;", upto):
        fail("the throw in %s does not name p0: p0 may not hold the resolution there" % m.group(1))
    # p0 must still be the argument at the throw: every write to p0 before it has to sit in a straight
    # run of code (no label, branch or exit in between; try markers do not end it, a caught exception
    # leaves by the handler) that ends in return-object p0.
    head = body[:t0.start()]
    for w in WRITES.finditer(head):
        run = []
        for line in head[w.end():].splitlines():
            s = line.strip()
            if not s or s.startswith((".line", "#", ":try_", ".catch")):
                continue
            run.append(s)
            if s.startswith((":", "goto", "if-", "return", "throw", "packed-switch", "sparse-switch")):
                break
        if not run or run[-1] != "return-object p0":
            fail("p0 is overwritten before the throw in %s: %s" % (m.group(1), w.group(0).strip()))
    ind = t0.group(1)
    add = (f"{ind}# OneOS (fix_sensor_crop_tables.py): a size the sensor crop table does not have: the size itself.\n"
           f"{ind}:{mark}\n{ind}return-object p0\n\n")
    body2 = body[:t0.start()] + add + body[t0.start():]
    return t[:m.start(3)] + body2 + t[m.end(3):], m.group(1)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    files = {}
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if f.endswith(".smali"):
                    p = os.path.join(dp, f)
                    t = open(p, encoding="utf-8").read()
                    if any(msg in t for msg, _, _ in MSGS):
                        files[p] = (d, t)
    dirs = set()
    for msg, mark, required in MSGS:
        hits = [p for p, (_, t) in files.items() if msg in t]
        if len(hits) != 1:
            if not hits and not required:
                print("fix_sensor_crop_tables: no %s in this camera, left out" % msg, file=sys.stderr)
                continue
            fail("%s found in %d classes" % (msg, len(hits)))
        p = hits[0]
        d, t = files[p]
        t, name = patch(t, msg, mark)
        files[p] = (d, t)
        open(p, "w", encoding="utf-8").write(t)
        dirs.add(d)
        print("fix_sensor_crop_tables: patched %s (%s)" % (os.path.relpath(p, root), name), file=sys.stderr)
    for d in sorted(dirs):
        print(d)


if __name__ == "__main__":
    main()
