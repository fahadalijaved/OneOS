"""A finger on a Galaxy's optical in-display sensor for a guest whose SystemUI never reports it (0.5.20, ColorOS).

ColorOS shows its fingerprint icon but never calls FingerprintProvider.onPointerDown (OPPO's panel driver tells
OPPO's HAL instead), so on the A36 touching the icon did nothing. OneOSFpTouch reads the touch panel and makes the
onPointerDown/onPointerUp calls itself while a fingerprint client runs; it does nothing without
/data/system/oneos_fp_touch, which guest_prepare.sh writes only for such a guest.

Adds OneOSFpTouch.smali (scripts/build-udfps-smali.sh OneOSFpTouch) into the smallest dex beside the other
helpers and a call to OneOSFpTouch.start(this) before every return of FingerprintProvider's constructors. Needs
guest_seh_touch.py's calls in onPointerDown/onPointerUp for the light and Samsung's request. A jar that already
has it is left as it is.

Usage: guest_fp_touchwatch.py <smali root dir>
Prints the smali_* directories it changed.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.join("com", "android", "server", "biometrics", "sensors", "fingerprint", "aidl", "FingerprintProvider.smali")
HELPER = "Lcom/android/server/biometrics/sensors/fingerprint/aidl/OneOSFpTouch;"


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if os.path.join(d, f).endswith(os.sep + REL)]
    if len(hits) != 1:
        sys.exit(f"expected one {REL}, found {len(hits)}")
    path = hits[0]
    lines = open(path).read().split("\n")
    if any(HELPER in l for l in lines):
        print("guest_fp_touchwatch: already in this jar", file=sys.stderr)
        return
    out, inside, calls = [], False, 0
    for l in lines:
        if l.startswith(".method") and " constructor <init>(" in l:
            inside = True
        elif l.startswith(".end method"):
            inside = False
        if inside and l.strip() == "return-void":
            out += [
                "    # OneOS: a finger on the in-display sensor from the touch panel (OneOSFpTouch).",
                f"    invoke-static {{p0}}, {HELPER}->start(Ljava/lang/Object;)V",
                "",
            ]
            calls += 1
        out.append(l)
    if calls == 0:
        sys.exit(f"{path}: no constructor return found")
    open(path, "w").write("\n".join(out))
    rel_dir = os.path.dirname(os.path.relpath(path, root))
    full = rel_dir.split(os.sep)[0]
    dexes = [d for d in os.listdir(root) if d.startswith("smali")]

    def size(d):
        return sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(os.path.join(root, d)) for f in fs)
    small = min((d for d in dexes if d != full), key=size, default=full)
    dest = os.path.join(root, small, *rel_dir.split(os.sep)[1:])
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "OneOSFpTouch.smali"), os.path.join(dest, "OneOSFpTouch.smali"))
    print(f"FingerprintProvider: OneOSFpTouch.start in {calls} constructor return(s)", file=sys.stderr)
    print(full)
    if small != full:
        print(small)


if __name__ == "__main__":
    main(sys.argv[1])
