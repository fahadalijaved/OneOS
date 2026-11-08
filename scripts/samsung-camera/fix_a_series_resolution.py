"""One UI's camera in a guest on Galaxy A phones: a stored resolution id the S26 Ultra's camera does not know.

vc.j.U (the step that keeps a high picture resolution when another setting changes) reads the
resolution id stored for a setting (te.c0.k1, default vc.e.a) and looks it up with l9.a2.j(int).
On the Galaxy A16 4G the id is -1 (no resolution of this camera for that sensor): te.c0.S0(-1) is
false since fix_a_series_modes.py, so the method went on to l9.a2.j(-1), which threw
IllegalArgumentException "getResolution : argument is invalid - -1" and the camera died at launch
(0.4.63 A16 4G b7b3ec12, ColorOS). An id below 0 now leaves the method the way a resolution that is
not a high one does (its return at the end, nothing stored).

Found by the method's shape (U(Ll9/f0;)V reading KEEP_HIGH_PICTURE_RESOLUTION and calling
l9.a2.j(I) once); fails closed when the code is not the shape it was written for.

Usage: fix_a_series_resolution.py <decoded SamsungCamera.apk root>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

MARK = "oneos_a_series_resolution"
KEY = "->KEEP_HIGH_PICTURE_RESOLUTION:"


def fail(msg):
    sys.exit("fix_a_series_resolution: " + msg)


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
                if not f.endswith(".smali"):
                    continue
                p = os.path.join(dp, f)
                t = open(p, encoding="utf-8").read()
                if KEY not in t:
                    continue
                for m in re.finditer(r"^\.method public final (\w+)\((L[\w/$]+;)\)V\n(.*?)^\.end method\n", t, re.M | re.S):
                    body = m.group(3)
                    if KEY in body and len(re.findall(r"invoke-static \{\w+\}, (L[\w/$]+;)->j\(I\)\1", body)) == 1:
                        hits.append((d, p, t, m))
    if len(hits) != 1:
        fail("the high picture resolution step found %d times" % len(hits))
    d, p, t, m = hits[0]
    if MARK in t:
        fail("already patched")
    body = m.group(3)
    call = re.search(r"^(\s*)invoke-static \{(\w+)\}, (L[\w/$]+;)->j\(I\)\3$", body, re.M)
    # The label right before the method's final return: where a resolution that is not a high one goes.
    end = re.search(r"((?:^\s*:\w+\n)+)(?:\s*\.line \d+\n|\s*\n)*\s*return-void\n(?:\s*\n)*\Z", body, re.M)
    if not call or not end:
        fail("no lookup call or no labelled final return")
    target = re.findall(r":\w+", end.group(1))[0]
    ind, reg = call.group(1), call.group(2)
    guard = (f"{ind}# OneOS (fix_a_series_resolution.py): a resolution id this camera does not know (-1):\n"
             f"{ind}# nothing to keep, as for a resolution that is not a high one.\n"
             f"{ind}if-ltz {reg}, {target}\n\n"
             f"{ind}:{MARK}\n")
    body2 = body[:call.start()] + guard + body[call.start():]
    t = t[:m.start(3)] + body2 + t[m.end(3):]
    open(p, "w", encoding="utf-8").write(t)
    print("fix_a_series_resolution: patched %s (-> %s)" % (os.path.relpath(p, root), target), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
