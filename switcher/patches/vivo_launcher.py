"""vivo's launcher (BBKLauncher2) stays a bar phone's launcher on a Galaxy Z Fold (0.4.60, X500 Pro Max build).

With ro.vivo.device.type=foldable for the session (guest_props.sh, vivo's fold
mode), the X500 Pro Max's BBKLauncher2 first refused to run (eighth OriginOS
run: its install-compatibility deviceType list is "phone|flip|tablet"), then,
let through, took its foldable paths, whose classes R8 removed from that phone
build (ninth run: ClassNotFoundException AllGroupsRecyclerView inflating
all_groups, 75 crashes, no home). It is kept a phone's launcher instead:
framework.jar's FtDeviceInfo.getDeviceType() answers "phone" in the launcher's
process (patches/vivo_guards.py framework), and the three places the launcher
reads ro.vivo.device.type itself (th/gdi by reflection, zl/gda, IconRedrawManager)
read a name no build sets, ro.oneos.launcher.device_type, so they get their
default (empty or "phone") instead of "foldable".

The property name must be found exactly three times, or nothing is written
(fail closed).

Usage: vivo_launcher.py <apktool decoded BBKLauncher2.apk dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import sys

OLD = '"ro.vivo.device.type"'
NEW = '"ro.oneos.launcher.device_type"'
EXPECTED = 3


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    hits = []
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dirpath, _, files in os.walk(os.path.join(root, d)):
            for f in files:
                if f.endswith(".smali"):
                    p = os.path.join(dirpath, f)
                    n = open(p).read().count(OLD)
                    if n:
                        hits.append((d, p, n))
    total = sum(n for _, _, n in hits)
    if total != EXPECTED:
        sys.exit(f"vivo_launcher: {OLD} found {total} times, {EXPECTED} expected")
    for _, p, _ in hits:
        text = open(p).read()
        if "OneOS (patches/vivo_launcher.py)" in text:
            sys.exit(f"vivo_launcher: {p} already patched")
        lines = []
        for line in text.split("\n"):
            if OLD in line:
                if not line.lstrip().startswith("const-string"):
                    sys.exit(f"vivo_launcher: {OLD} outside a const-string in {p}")
                lines.append("    # OneOS (patches/vivo_launcher.py): the bar phone's launcher keeps its own device type.")
                line = line.replace(OLD, NEW)
            lines.append(line)
        open(p, "w").write("\n".join(lines))
    for d in sorted({d for d, _, _ in hits}):
        print(d)


if __name__ == "__main__":
    main()
