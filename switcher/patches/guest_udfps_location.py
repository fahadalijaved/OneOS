"""The in-display fingerprint sensor's place for the guest, from the phone (0.5.18).

Samsung's fingerprint HAL gives a guest framework no sensor location, so the guest's SystemUI kept the sensor at
0,0 with no size (Nothing OS on the owner's A36: "fingerprintSensorLocation=Point(0, 0)", udfpsBounds empty,
shouldListenForUdfps=false): it never drew the sensor or sent the HAL its finger-down events, and touches were
acquired but never matched. FingerprintProvider.getWorkaroundSensorProps, which the AIDL provider asks before the HAL's
props (an image's own sfps resource answer wins over the HAL there), first asks OneOSUdfps.props(): the location
guest_prepare.sh wrote to /data/system/oneos_udfps from the phone's own sysfs, or null, and the method goes on as
before.

Adds OneOSUdfps.smali (scripts/build-udfps-smali.sh) next to FingerprintProvider and the hook at the method's entry.
A jar that already has the hook is left as it is.

Usage: guest_udfps_location.py <smali root dir>
Prints the smali_* directory it changed.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.join("com", "android", "server", "biometrics", "sensors", "fingerprint", "aidl", "FingerprintProvider.smali")
HELPER = "Lcom/android/server/biometrics/sensors/fingerprint/aidl/OneOSUdfps;"
HEAD = re.compile(r"^\.method (?:[a-z]+ )*getWorkaroundSensorProps\(Landroid/content/Context;\)Ljava/util/List;$")


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if os.path.join(d, f).endswith(os.sep + REL)]
    if len(hits) != 1:
        sys.exit(f"expected one {REL}, found {len(hits)}")
    path = hits[0]
    lines = open(path).read().split("\n")
    if any(HELPER in l for l in lines):
        print("guest_udfps_location: already in this jar", file=sys.stderr)
        return
    heads = [i for i, l in enumerate(lines) if HEAD.match(l)]
    if len(heads) != 1:
        sys.exit(f"{path}: getWorkaroundSensorProps(Context) found {len(heads)} times, expected once")
    i = heads[0]
    m = re.fullmatch(r"\s*\.locals (\d+)", lines[i + 1])
    if not m or int(m.group(1)) < 1:
        sys.exit(f"{path}: unexpected getWorkaroundSensorProps header")
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
            break
    lines[j:j] = [
        "    # OneOS: the phone's own sensor place (Samsung's HAL gives the guest none); null: the image's answer.",
        f"    invoke-static {{}}, {HELPER}->props()Ljava/util/List;",
        "",
        "    move-result-object v0",
        "",
        "    if-eqz v0, :oneos_udfps_image",
        "",
        "    return-object v0",
        "",
        "    :oneos_udfps_image",
    ]
    open(path, "w").write("\n".join(lines))
    shutil.copyfile(os.path.join(HERE, "OneOSUdfps.smali"), os.path.join(os.path.dirname(path), "OneOSUdfps.smali"))
    print("FingerprintProvider.getWorkaroundSensorProps: the phone's sensor place first (OneOSUdfps)", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
