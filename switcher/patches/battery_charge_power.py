"""The charger's power from Samsung's own nodes in the guest's BatteryService (0.5.31).

A Galaxy's kernel publishes no current_max or voltage_max for its chargers, so the health HAL (One UI's,
vendor.samsung.hardware.health-service) reports maxChargingCurrentMicroamps and
maxChargingVoltageMicrovolts as 0 and every guest takes a Samsung fast charger for a slow one: no
"Charging rapidly" and no fast-charging animation (owner's A36, HyperOS 4 Global, 11-20: 45 W Super Fast
Charging with direct charging on, "Max charging current: 0").

BatteryService.update(HealthInfo), where every HAL update arrives, now first calls
OneOSChargePower.fill(info) (OneOSChargePower.smali, copied into com/android/server): with a charger
online and no maximum from the HAL, it fills one in from /sys/class/power_supply/battery/charging_type
(see the helper). The call sits at the method's entry in its own try/catch Throwable, so not even a
NoClassDefFoundError or VerifyError of the helper reaches the HAL callback; invoke-static/range takes p1
whatever the register count.

A services.jar without BatteryService.update(Landroid/hardware/health/HealthInfo;)V is left alone: a
warning on stderr, nothing on stdout, exit 0.

Usage: battery_charge_power.py <smali root dir> <helper smali>
Prints the smali_* directory (dex) it changed.
"""
import os
import re
import shutil
import sys

CLS = os.path.join("com", "android", "server", "BatteryService.smali")
HEAD = ".method public update(Landroid/hardware/health/HealthInfo;)V"
CALL = """    :oneos_charge_try_start
    invoke-static/range {p1 .. p1}, Lcom/android/server/OneOSChargePower;->fill(Landroid/hardware/health/HealthInfo;)V
    :oneos_charge_try_end
    .catch Ljava/lang/Throwable; {:oneos_charge_try_start .. :oneos_charge_try_end} :oneos_charge_catch

    :oneos_charge_done
"""
HANDLER = """
    :oneos_charge_catch
    move-exception v0

    goto :oneos_charge_done
"""
MARK = "OneOSChargePower"


def skip(why):
    print(f"battery_charge_power: {why}; BatteryService left alone", file=sys.stderr)
    sys.exit(0)


def main(root, helper):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + CLS)]
    if not hits:
        skip("no BatteryService in this services.jar")
    if len(hits) != 1:
        sys.exit(f"expected exactly one {CLS}, found {len(hits)}")
    path = hits[0]
    smali = open(path).read()
    if MARK in smali:
        sys.exit("BatteryService already patched")
    methods = [m for m in re.finditer(r"^\.method [^\n]*\n.*?^\.end method\n", smali, re.M | re.S)
               if m.group(0).split("\n", 1)[0] == HEAD]
    if len(methods) != 1:
        skip(f"{len(methods)} methods '{HEAD}'")
    m = methods[0]
    lines = m.group(0).split("\n")
    regs = [i for i, l in enumerate(lines) if re.fullmatch(r"    \.locals \d+", l)]
    if len(regs) != 1:
        skip("update() has no single .locals line")
    lines[regs[0]] = f"    .locals {max(1, int(lines[regs[0]].split()[1]))}"
    # The first line after the directives (.locals, .param ... .end param, annotations, .prologue).
    i, inside = 1, False
    while i < len(lines):
        s = lines[i].strip()
        if inside:
            inside = not s.startswith(".end ")
        elif s.startswith(".param") and not s.endswith(";") and i + 1 < len(lines) and lines[i + 1].strip().startswith(".annotation"):
            inside = True
        elif s.startswith(".annotation"):
            inside = True
        elif s == "" or s.startswith((".locals", ".param", ".end param", ".prologue")):
            pass
        else:
            break
        i += 1
    if i >= len(lines) - 1:
        skip("update() has no code")
    body = "\n".join(lines[:i]) + "\n" + CALL + "\n".join(lines[i:])
    end = body.rindex(".end method")
    body = body[:end] + HANDLER.lstrip("\n") + "\n" + body[end:]
    open(path, "w").write(smali[:m.start()] + body + smali[m.end():])
    # The helper goes in the dex with the fewest classes: BatteryService's own can sit at the 65536 reference
    # limit (Nothing OS A set: "Unsigned short value out of range: 65536" with the helper beside it); a call
    # across dex files is what multidex is for.
    dirs = sorted((sum(len(fs) for _, _, fs in os.walk(os.path.join(root, d))), d) for d in os.listdir(root)
                  if (d == "smali" or d.startswith("smali_classes")) and os.path.isdir(os.path.join(root, d)))
    hdir = dirs[0][1]
    dest = os.path.join(root, hdir, "com", "android", "server")
    os.makedirs(dest, exist_ok=True)
    shutil.copy(helper, os.path.join(dest, "OneOSChargePower.smali"))
    print(f"BatteryService.update: OneOSChargePower.fill (the charger's power from Samsung's charging_type), helper in {hdir}", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])
    if hdir != os.path.relpath(path, root).split(os.sep)[0]:
        print(hdir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
