"""No system_server crash when Do Not Disturb turns on and the phone has no notification light.

ZenModeManagerExtImpl (oplus-services.jar) takes LightsManager.getLight(4)
(LIGHT_ID_NOTIFICATIONS) once at boot, and when Do Not Disturb turns on,
handleZenModeChanged() calls mNotificationLight.turnOff() with no null check.
Samsung's lights HAL has no notification light, so getLight(4) is null and
the guest's system_server died the moment the user turned Do Not Disturb on
(Galaxy Z Flip7, 0.4.55 16e735f2, 23:30:42.536: "FATAL EXCEPTION IN SYSTEM
PROCESS: main ... LogicalLight.turnOff() on a null object reference at
ZenModeManagerExtImpl.handleZenModeChanged(ZenModeManagerExtImpl.java:185)";
OneOS returned to One UI 30 s later). Skip the call when there is no light.

Usage: oplus_zen_light.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

CLS = "Lcom/android/server/zenmode/ZenModeManagerExtImpl;"
CALL = re.compile(
    r"^(    iget-object (v\d+), p0, " + re.escape(CLS) +
    r"->mNotificationLight:Lcom/android/server/lights/LogicalLight;\n)"
    r"(\n)"
    r"(    invoke-virtual \{\2\}, Lcom/android/server/lights/LogicalLight;->turnOff\(\)V\n)",
    re.M)


def main():
    root = sys.argv[1]
    suffix = os.path.join("com", "android", "server", "zenmode", "ZenModeManagerExtImpl.smali")
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + suffix)]
    if len(hits) != 1:
        sys.exit(f"expected one ZenModeManagerExtImpl.smali, found {len(hits)}")
    path = hits[0]
    smali = open(path).read()
    if ":oneos_no_zen_light" in smali:
        sys.exit("ZenModeManagerExtImpl already patched")
    found = CALL.findall(smali)
    if len(found) != 1:
        sys.exit(f"ZenModeManagerExtImpl: expected one mNotificationLight.turnOff() call, found {len(found)}")
    smali = CALL.sub(lambda m: (m.group(1) + m.group(3) +
                                f"    if-eqz {m.group(2)}, :oneos_no_zen_light\n\n" +
                                m.group(4) + "\n    :oneos_no_zen_light\n"), smali)
    open(path, "w").write(smali)
    print("ZenModeManagerExtImpl: notification light turnOff() skipped when there is none", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main()
