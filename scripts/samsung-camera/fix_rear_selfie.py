"""One UI's camera in a guest: hiding the Rear Selfie guide without a guide.

Rear Selfie shows a guide on the cover panel (a Presentation on the second
display) while the unfolded phone uses a rear camera as a selfie camera. In a
guest only one panel is on at a time, so the guide's view binding is never
made; hiding it on a fold or a stop read a field of the null binding and the
camera crashed ("Attempt to read from field 'android.widget.ImageView n8.e8.a'
on a null object reference in method 'void p9.c.b()'", run 20, twice). The hide
now skips the views when there is no binding.

Found by the method's own log text ("hideRearSelfieGuideView"); the obfuscated
names change with each camera version.

Usage: fix_rear_selfie.py <smali root (the rewritten camera's out/camera/dec_SamsungCamera or a full decompile)>
"""
import os
import re
import sys

MARK = '"hideRearSelfieGuideView"'
LOAD = re.compile(r"^\s*iget-object (v\d+), v\d+, (L[\w/$]+;)->a:(L[\w/$]+;)\s*$")


def main():
    root = sys.argv[1]
    hits = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".smali"):
                p = os.path.join(d, f)
                with open(p, encoding="utf-8") as fh:
                    if MARK in fh.read():
                        hits.append(p)
    if len(hits) != 1:
        sys.exit("expected one class with %s, found %d" % (MARK, len(hits)))
    path = hits[0]
    lines = open(path, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if MARK in l)
    m0 = max(i for i in range(start) if lines[i].startswith(".method"))
    end = next(i for i in range(start, len(lines)) if lines[i].startswith(".end method"))
    if any("oneos_rear_selfie" in l for l in lines[m0:end]):
        print("%s: already patched" % path)
        return
    for i in range(start, end):
        m = LOAD.match(lines[i])
        if not m:
            continue
        # The next instruction (blank and .line lines skipped).
        k = next((j for j in range(i + 1, end) if lines[j].strip() and not lines[j].strip().startswith(".")), None)
        if k is not None and "->a:Landroid/widget/ImageView;" in lines[k] and lines[k].split(",")[1].strip() == m.group(1):
            reg = m.group(1)
            last_ret = max(j for j in range(i, end) if lines[j].strip() == "return-void")
            lines.insert(last_ret, "    :oneos_rear_selfie_none")
            lines.insert(i + 1, "    if-eqz %s, :oneos_rear_selfie_none" % reg)
            open(path, "w", encoding="utf-8").write("\n".join(lines))
            print("patched %s (null guide binding: skip)" % os.path.relpath(path, root))
            return
    sys.exit("no guide binding load in the hide method of %s" % path)


if __name__ == "__main__":
    main()
