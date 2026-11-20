"""HyperOS's quick charge type from Samsung's charger nodes (0.5.31).

MiuiBatteryServiceImpl (miui-services.jar) asks Xiaomi's charger service (miui.util.IMiCharge) for the quick
charge type that SystemUI's charging animation and "Super charging" go by; a Galaxy has no such service, so
every charger was a plain one (owner's A36, HyperOS 4 Global, 45 W Super Fast Charging, no animation). Every
result of IMiCharge.getQuickChargeType() now goes through OneOSMiCharge.quickChargeType(String)
(OneOSMiCharge.smali, in the dex with the fewest classes), which keeps the service's answer when it has one.

Usage: miui_quick_charge.py <smali root dir of miui-services.jar> <helper smali>
Prints the smali_* directories (dex files) it changed. No call site: a warning, nothing printed, exit 0.
"""
import os
import re
import shutil
import sys

CALL = re.compile(r"^(\s*)invoke-(?:virtual|interface)(?:/range)? \{[^}]*\}, Lmiui/util/IMiCharge;->getQuickChargeType\(\)Ljava/lang/String;\n"
                  r"(\s*\n)*\s*move-result-object ([vp]\d+)\n", re.M)
WRAP = ("{ind}invoke-static/range {{{r} .. {r}}}, Lcom/android/server/OneOSMiCharge;->quickChargeType(Ljava/lang/String;)Ljava/lang/String;\n\n"
        "{ind}move-result-object {r}\n")


def main(root, helper):
    changed = set()
    n = 0
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p).read()
            if "IMiCharge;->getQuickChargeType()" not in s or "OneOSMiCharge" in s:
                continue
            out, k = CALL.subn(lambda m: m.group(0) + "\n" + WRAP.format(ind=m.group(1), r=m.group(3)), s)
            if k:
                open(p, "w").write(out)
                n += k
                changed.add(os.path.relpath(p, root).split(os.sep)[0])
    if not n:
        print("miui_quick_charge: no IMiCharge.getQuickChargeType() call; left alone", file=sys.stderr)
        return
    dirs = sorted((sum(len(fs) for _, _, fs in os.walk(os.path.join(root, d))), d) for d in os.listdir(root)
                  if (d == "smali" or d.startswith("smali_classes")) and os.path.isdir(os.path.join(root, d)))
    hdir = dirs[0][1]
    dest = os.path.join(root, hdir, "com", "android", "server")
    os.makedirs(dest, exist_ok=True)
    shutil.copy(helper, os.path.join(dest, "OneOSMiCharge.smali"))
    changed.add(hdir)
    print(f"IMiCharge.getQuickChargeType: {n} call(s) through OneOSMiCharge (helper in {hdir})", file=sys.stderr)
    for c in sorted(changed):
        print(c)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
