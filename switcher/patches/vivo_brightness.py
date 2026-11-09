"""vivo's brightness on a bar phone's tables in fold mode (OriginOS 6 CN, PD2609MA).

In fold mode (ONEOS_GUEST_VIVO_FOLD=1: ro.vivo.device.type=foldable, vivo's
device states 0 CLOSE / 1 OPEN) vivo-framework.jar's brightness code takes the
"unfolded" tables whenever the device state is not 0: BaseNitCurve through
com.vivo.sensor.common.SensorInfo.getDeviceState() (luxNitSectionUnFold...),
BrightMapping through its own deviceState (BrightMappingUnFold). A bar phone's
build has only the normal tables: system_server died in
BaseNitCurve.calcNitBrightnessUnFold (NullPointerException, BrightnessLux thread)
at the first light sensor event with automatic brightness on (ninth CN run, a
fresh /data). The three state sources the brightness and sensor code reads answer 0
(the normal tables) here: SensorInfo.getDeviceState() (BaseNitCurve is its only
caller), InfoManager.getDeviceState() (BrightnessImpl, CurveConfig, BrightnessConfig,
CctFusionLux; vivo-services' LcmBrightness, ApparentBrightness and proximity
calibration: brightness and sensor tables only), and BrightMapping's static
deviceState setter (its FoldListener's only way in) keeps 0.

Every pattern must be found exactly as expected, or nothing is written.

Usage: vivo_brightness.py <apktool decoded vivo-framework.jar dir>
Prints the smali_* directories it changed.
"""
import os
import re
import sys

SENSOR_INFO = os.path.join("com", "vivo", "sensor", "common", "SensorInfo.smali")
BRIGHT_MAPPING = os.path.join("com", "vivo", "common", "brightmapping", "BrightMapping.smali")
INFO_MANAGER = os.path.join("com", "vivo", "sensor", "info", "InfoManager.smali")
NOTE = "    # OneOS (patches/vivo_brightness.py): a bar phone's build has only the normal brightness tables.\n"
DEVTYPE = re.compile(r"    invoke-static \{\}, Landroid/util/FtDeviceInfo;->getDeviceType\(\)Ljava/lang/String;\n\n"
                     r"    move-result-object ([vp]\d+)\n")


def fail(msg):
    sys.exit(f"vivo_brightness: {msg}")


def find(root, rel):
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, rel))]
    if len(hits) != 1:
        fail(f"{rel} {len(hits)} times")
    return hits[0], os.path.join(root, hits[0], rel)


def replace_method(text, decl_re, body_re, new_body, what):
    ms = list(re.finditer(r"^(\.method " + decl_re + r"\n)(.*?)^\.end method\n", text, re.M | re.S))
    if len(ms) != 1:
        fail(f"{what}: {len(ms)} methods")
    m = ms[0]
    body = "\n".join(l for l in m.group(2).split("\n") if l.strip() and not l.strip().startswith(".line")) + "\n"
    if not re.fullmatch(body_re, body):
        fail(f"{what}: not the body this was written for:\n{body}")
    return text[:m.start()] + m.group(1) + new_body + ".end method\n" + text[m.end():]


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    dirs = set()
    # SensorInfo.getDeviceState(): iget mDeviceState; return it -> 0.
    d, p = find(root, SENSOR_INFO)
    t = open(p).read()
    t = replace_method(t, r"public (?:[\w-]+ )*getDeviceState\(\)I",
                       r"\s*\.locals 1\n\s*iget v0, p0, Lcom/vivo/sensor/common/SensorInfo;->mDeviceState:I\n\s*return v0\n",
                       "    .locals 1\n\n" + NOTE + "    const/4 v0, 0x0\n\n    return v0\n", "SensorInfo.getDeviceState")
    open(p, "w").write(t)
    dirs.add(d)
    # InfoManager.getDeviceState(): sget deviceState; return it -> 0.
    d, p = find(root, INFO_MANAGER)
    t = open(p).read()
    t = replace_method(t, r"public static (?:[\w-]+ )*getDeviceState\(\)I",
                       r"\s*\.locals 1\n\s*sget v0, Lcom/vivo/sensor/info/InfoManager;->deviceState:I\n\s*return v0\n",
                       "    .locals 1\n\n" + NOTE + "    const/4 v0, 0x0\n\n    return v0\n", "InfoManager.getDeviceState")
    open(p, "w").write(t)
    dirs.add(d)
    # BrightMapping: the synthetic setter -$$Nest$sfputdeviceState(I)V (sput p0) keeps 0.
    d, p = find(root, BRIGHT_MAPPING)
    t = open(p).read()
    sputs = re.findall(r"^\s*sput (\S+), Lcom/vivo/common/brightmapping/BrightMapping;->deviceState:I$", t, re.M)
    if len(sputs) != 2:
        fail(f"BrightMapping.deviceState is set {len(sputs)} times (the initial 0 and the setter expected)")
    t = replace_method(t, r"static (?:[\w-]+ )*-\$\$Nest\$sfputdeviceState\(I\)V",
                       r"\s*\.locals 0\n(?:\s*\.param p0.*\n)?\s*sput p0, Lcom/vivo/common/brightmapping/BrightMapping;->deviceState:I\n\s*return-void\n",
                       "    .locals 0\n\n" + NOTE + "    const/4 p0, 0x0\n\n    sput p0, Lcom/vivo/common/brightmapping/BrightMapping;->deviceState:I\n\n    return-void\n",
                       "BrightMapping.-$$Nest$sfputdeviceState")
    # Nothing else in the class may write it.
    for f in sorted(os.listdir(os.path.dirname(p))):
        if f.startswith("BrightMapping") and f.endswith(".smali") and f != "BrightMapping.smali":
            if re.search(r"sput \S+, Lcom/vivo/common/brightmapping/BrightMapping;->deviceState:I", open(os.path.join(os.path.dirname(p), f)).read()):
                fail(f"{f} writes BrightMapping.deviceState directly")
    open(p, "w").write(t)
    dirs.add(d)
    # The sensor config's device type (InfoImpl, RootConfig): "phone", so fold mode 1
    # (ro.vivo.device.type=foldable) keeps the phone build's config root and curves
    # (F8U runs 14-15: "UnFoldRootConfig ... read driver ic failed", the inner panel's
    # backlight stuck at its first level). Two reads in each, nothing else.
    for rel in (os.path.join("com", "vivo", "sensor", "info", "InfoImpl.smali"),
                os.path.join("com", "vivo", "sensor", "config", "RootConfig.smali")):
        d, p = find(root, rel)
        t = open(p).read()
        total = t.count("Landroid/util/FtDeviceInfo;->getDeviceType()Ljava/lang/String;")
        t, k = DEVTYPE.subn(lambda m: NOTE + f'    const-string {m.group(1)}, "phone"\n', t)
        if total != 2 or k != 2:
            fail(f"{rel}: {total} getDeviceType() reads, {k} in the expected form (2 expected)")
        open(p, "w").write(t)
        dirs.add(d)
    print("vivo_brightness: SensorInfo/InfoManager.getDeviceState() and BrightMapping's device state stay 0 (normal tables); "
          "InfoImpl/RootConfig device type phone", file=sys.stderr)
    print("\n".join(sorted(dirs)))


if __name__ == "__main__":
    main()
