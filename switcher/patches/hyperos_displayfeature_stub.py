"""Give HyperOS's DisplayFeatureManager a no-op instance when its service is absent.

miui.hardware.display.DisplayFeatureManager.getInstance() binds
"displayfeature", a system service that HyperOS's system_server registers only
when Xiaomi's vendor HAL (vendor.xiaomi.hardware.displayfeature) is there. On
Samsung's vendor there is no such HAL, the service is never registered, and the
catch of ServiceNotFoundException leaves sInstance null, so getInstance()
returns null. Callers do not check it: SystemUI's fingerprint-on-display
overlay builds a Runnable that calls
DisplayFeatureManager.getInstance().setScreenEffect(17, 1, 1), and on the
HyperOS image the lockscreen crashed in that thread every time the glyph came
up (S25 Ultra, 2026-11-15: NPE in MiuiGxzwOverlayView$$ExternalSyntheticLambda2,
SystemUI restarting in a loop with the FOD icon visible between restarts).

Every method of the class loads mService, guards it with if-eqz/if-nez and only
then calls it (setScreenEffect, getAllEffectScopeApps, getAppEffect, the two
register methods, the app effect setters, the unregister methods), so an
instance whose mService is null is a no-op rather than a crash. The catch now
installs that instance instead of leaving sInstance null: no caller needs a
null check, and the whole class of SystemUI, Settings and app crashes from the
missing service is gone.

Usage: hyperos_displayfeature_stub.py <apktool decoded jar directory>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

CLASS = "miui/hardware/display/DisplayFeatureManager"
METHOD = re.compile(
    r"\.method public static blacklist getInstance\(\)Lmiui/hardware/display/DisplayFeatureManager;\n"
    r"(.*?)\n\.end method\n",
    re.S,
)
# The one Slog.e in the catch block that reports the missing service.
SLOG = "    invoke-static {v2, v3}, Landroid/util/Slog;->e(Ljava/lang/String;Ljava/lang/String;)I\n"
MARK = "# oneos: no displayfeature service"
STUB = (
    "    # oneos: no displayfeature service on this vendor's HAL, so every call is a no-op\n"
    "    # instead of a null getInstance() (hyperos_displayfeature_stub.py)\n"
    "    new-instance v5, Lmiui/hardware/display/DisplayFeatureManager;\n"
    "    const/4 v6, 0x0\n"
    "    invoke-direct {v5, v6}, Lmiui/hardware/display/DisplayFeatureManager;-><init>"
    "(Lmiui/hardware/display/IDisplayFeatureManager;)V\n"
    "    sput-object v5, Lmiui/hardware/display/DisplayFeatureManager;->sInstance:"
    "Lmiui/hardware/display/DisplayFeatureManager;\n"
)


def load(root, cls):
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        p = os.path.join(root, d, cls + ".smali")
        if os.path.isfile(p):
            return p, d
    sys.exit(f"{CLASS}: no {cls}.smali in {root} (another build)")


def main(root):
    if not os.path.isdir(root):
        sys.exit(f"{root}: not a decoded jar directory")
    path, dexdir = load(root, CLASS)
    smali = open(path).read()
    m = METHOD.search(smali)
    if not m:
        sys.exit(f"{CLASS}: getInstance() not as expected (another build)")
    body = m.group(1)
    if body.count(SLOG) != 1:
        sys.exit(f"{CLASS}: getInstance() has {body.count(SLOG)} Slog.e calls, expected 1")
    if MARK in body:
        sys.exit(f"{CLASS}: getInstance() already carries the stub (patched twice)")
    # v5/v6: one past the five locals the method declares.
    if not body.startswith("    .locals 5\n"):
        sys.exit(f"{CLASS}: getInstance() does not declare .locals 5 (another build)")
    newbody = body.replace("    .locals 5\n", "    .locals 7\n", 1).replace(SLOG, SLOG + STUB, 1)
    smali = smali[: m.start(1)] + newbody + smali[m.end(1):]
    with open(path, "w") as f:
        f.write(smali)
    print(dexdir)
    print(f"{CLASS}.getInstance: a null-service instance when displayfeature is absent", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: hyperos_displayfeature_stub.py <apktool decoded jar directory>")
    main(sys.argv[1])
