"""One UI's camera in a guest on Galaxy A phones: a sensor crop the S26 Ultra's camera does not know.

te.c0.u0 (the camera's "getSensorCropResolution") maps a resolution to its sensor crop by
name through a table, then looks the crop up by name (l9.a2.k(String)). On the Galaxy A56
the crop is "3184x2388", which the S26 Ultra's camera has no entry for: k threw
IllegalArgumentException "getResolution : argument is invalid - 3184x2388" and the camera
died at launch ("Unable to start activity", 0.4.61 A56 fda1b80b, after
fix_a_series_modes.py had fixed the -1 id). An unknown crop name now gives the resolution
itself (no crop) instead.

Found by the method's message ("getSensorCropResolution : Argument is wrong = "); fails
closed when the code is not the shape it was written for.

Usage: fix_a_series_crop.py <decoded SamsungCamera.apk root>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

MSG = '"getSensorCropResolution : Argument is wrong = "'
MARK = "oneos_a_series_crop"


def fail(msg):
    sys.exit("fix_a_series_crop: " + msg)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = []
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if f.endswith(".smali"):
                    p = os.path.join(dp, f)
                    t = open(p, encoding="utf-8").read()
                    if MSG in t:
                        hits.append((d, p, t))
    if len(hits) != 1:
        fail("the sensor crop lookup found in %d classes" % len(hits))
    d, p, t = hits[0]
    if MARK in t:
        fail("already patched")
    ms = [m for m in re.finditer(r"^\.method public static (\w+)\((L[\w/$]+;)\)\2\n(.*?)^\.end method\n", t, re.M | re.S)
          if MSG in m.group(3)]
    if len(ms) != 1:
        fail("the sensor crop method found %d times" % len(ms))
    m = ms[0]
    cls = m.group(2)
    body = m.group(3)
    loc = re.search(r"^(\s*)\.locals (\d+)$", body, re.M)
    if not loc:
        fail("no .locals")
    n = int(loc.group(2))
    keep = "v%d" % n
    call = re.compile(r"^(\s*)invoke-static \{(p0|v\d+)\}, " + re.escape(cls) + r"->(\w+)\(Ljava/lang/String;\)" + re.escape(cls)
                      + r"\n(?:\s*\.line \d+\n|\s*\n)*(\s*)move-result-object (\w+)\n", re.M)
    cs = list(call.finditer(body))
    if len(cs) != 1:
        fail("the lookup by name found %d times in the method" % len(cs))
    c = cs[0]
    ind = c.group(1)
    wrapped = (f"{ind}:{MARK}_try_start\n" + body[c.start():c.end()].rstrip("\n") + "\n"
               f"{ind}:{MARK}_try_end\n"
               f"{ind}.catch Ljava/lang/IllegalArgumentException; {{:{MARK}_try_start .. :{MARK}_try_end}} :{MARK}_catch\n")
    body2 = body[:c.start()] + wrapped + body[c.end():]
    body2 = body2[:loc.start()] + f"{loc.group(1)}.locals {n + 1}\n\n{loc.group(1)}move-object {keep}, p0" + body2[loc.end():]
    body2 = body2.rstrip("\n") + (f"\n\n{ind}# OneOS (fix_a_series_crop.py): a crop this camera does not know: the resolution itself.\n"
                                  f"{ind}:{MARK}_catch\n{ind}return-object {keep}\n")
    t = t[:m.start(3)] + body2 + t[m.end(3):]
    open(p, "w", encoding="utf-8").write(t)
    print("fix_a_series_crop: patched %s" % os.path.relpath(p, root), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
