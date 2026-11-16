"""A Galaxy's optical in-display fingerprint sensor for the guest, driven as One UI drives it (0.5.18).

The guest's SystemUI sends the phone's fingerprint HAL onPointerDown/onPointerUp, and the HAL captured on them, but
every image failed until the panel's local HBM spot was lit and Samsung's extension was told of the touch
(OneOSSehTouch; owner's A36, Nothing OS: IDENTIFY_SUCCESS with both, never without). FingerprintProvider.onPointerDown
and onPointerUp first call OneOSSehTouch.down() and up(), which do nothing on a phone without
/data/system/oneos_fp_lhbm (guest_prepare.sh writes it for an optical sensor with local HBM).

Adds OneOSSehTouch.smali (scripts/build-udfps-smali.sh OneOSSehTouch) next to FingerprintProvider and the two calls
at the methods' entries. A jar that already has them is left as it is.

Usage: guest_seh_touch.py <smali root dir>
Prints the smali_* directory it changed.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.join("com", "android", "server", "biometrics", "sensors", "fingerprint", "aidl", "FingerprintProvider.smali")
HELPER = "Lcom/android/server/biometrics/sensors/fingerprint/aidl/OneOSSehTouch;"
SIG = "(JILandroid/hardware/biometrics/fingerprint/PointerContext;)V"


def entry(lines, i):
    j = i + 2
    while True:
        s = lines[j].strip()
        if s.startswith(".param") or s in ("", ".end param"):
            j += 1
        elif s.startswith(".annotation"):
            while lines[j].strip() != ".end annotation":
                j += 1
            j += 1
        else:
            return j


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if os.path.join(d, f).endswith(os.sep + REL)]
    if len(hits) != 1:
        sys.exit(f"expected one {REL}, found {len(hits)}")
    path = hits[0]
    lines = open(path).read().split("\n")
    if any(HELPER in l for l in lines):
        print("guest_seh_touch: already in this jar", file=sys.stderr)
        return
    for name, call in (("onPointerDown", "down"), ("onPointerUp", "up")):
        head = re.compile(r"^\.method (?:[a-z]+ )*" + name + re.escape(SIG) + "$")
        heads = [i for i, l in enumerate(lines) if head.match(l)]
        if len(heads) != 1:
            sys.exit(f"{path}: {name}{SIG} found {len(heads)} times, expected once")
        i = heads[0]
        if not re.fullmatch(r"\s*\.(locals|registers) \d+", lines[i + 1]):
            sys.exit(f"{path}: unexpected {name} header")
        j = entry(lines, i)
        lines[j:j] = [
            f"    # OneOS: local HBM and Samsung's finger {call} request first, as One UI (OneOSSehTouch).",
            f"    invoke-static {{}}, {HELPER}->{call}()V",
            "",
        ]
    open(path, "w").write("\n".join(lines))
    # FingerprintProvider's dex is at the 65536 method limit on Nothing OS (the two calls overflowed it): the helper
    # goes into the smallest dex, and OneOSUdfps (guest_udfps_location.py) moves there too, which frees its
    # references in the full one.
    rel_dir = os.path.dirname(os.path.relpath(path, root))
    full = rel_dir.split(os.sep)[0]
    dexes = [d for d in os.listdir(root) if d.startswith("smali")]
    def size(d):
        return sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(os.path.join(root, d)) for f in fs)
    small = min((d for d in dexes if d != full), key=size, default=full)
    dest = os.path.join(root, small, *rel_dir.split(os.sep)[1:])
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(os.path.join(HERE, "OneOSSehTouch.smali"), os.path.join(dest, "OneOSSehTouch.smali"))
    udfps = os.path.join(os.path.dirname(path), "OneOSUdfps.smali")
    if small != full and os.path.exists(udfps):
        shutil.move(udfps, os.path.join(dest, "OneOSUdfps.smali"))
    if small != full:
        print(small)
    print("FingerprintProvider.onPointerDown/onPointerUp: local HBM and Samsung's touch request first (OneOSSehTouch)",
          file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
