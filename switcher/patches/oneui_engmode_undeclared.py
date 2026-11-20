#!/usr/bin/env python3
"""One UI 9.5's engineering-mode client stays off where the phone has no ISehEngmode HAL.

Every engmode call in One UI 9.5 goes through framework.jar's EngineeringModeManager, whose
EngineeringModeNative loads lib.engmodejni.samsung.so; lib.engmode.samsung.so then asks for the AIDL
HAL vendor.samsung.hardware.security.engmode.ISehEngmode/default with AServiceManager_waitForService.
The S23 family's vendor serves only the older HIDL engmode, so the instance is not in the phone's
VINTF manifest, init refuses to start it and every caller waits forever: SecSetupWizard's main thread
(ANR, black setup screen), system_server's android.fg (FactoryBootModeUtils at BOOT_COMPLETED, "ANR in
system") and SettingsProvider handler, SystemUI, diagmonagent (report 4dee9fd6, S23 Ultra).

EngineeringModeNative's constructor gets a check after the library loaded: when servicemanager says
the instance is not declared, mSupportJNI is set false, the state One UI already has when the library
fails to load. isConnected() is then false and every EngineeringModeManager call returns its error
value at once (all of them check isSupport() first). Where the instance is declared (S24 and later),
or the check itself throws, nothing changes.

Usage: oneui_engmode_undeclared.py <apktool -r dir of framework.jar>
Prints the smali_* directory it changed; nothing (and "not present" on stderr) without the class.
Exits 1 when the class is there but its constructor is not the expected shape.
"""
import os
import re
import sys

REL = os.path.join("com", "samsung", "android", "service", "EngineeringMode",
                   "EngineeringModeManager$EngineeringModeNative.smali")
CLASS = "Lcom/samsung/android/service/EngineeringMode/EngineeringModeManager$EngineeringModeNative;"
FIELD = CLASS + "->mSupportJNI:Z"
INSTANCE = "vendor.samsung.hardware.security.engmode.ISehEngmode/default"
MARK = "    # OneOS: engmode off without a declared ISehEngmode (oneui_engmode_undeclared.py)\n"
# The end of the library's try block: the success path returns right after it.
ANCHOR = ("    :try_end_0\n"
          "    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0\n"
          "\n"
          "    return-void\n")


def main(root):
    hits = [d for d in sorted(os.listdir(root))
            if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if not hits:
        print("not present", file=sys.stderr)
        return
    if len(hits) != 1:
        sys.exit(f"oneui_engmode_undeclared: {REL} found in {hits}")
    p = os.path.join(root, hits[0], REL)
    t = open(p).read()
    if MARK in t:
        print(hits[0])
        return
    ms = list(re.finditer(r"^\.method public constructor [^\n]*<init>\(Lcom/samsung/android/service/"
                          r"EngineeringMode/EngineeringModeManager;Landroid/content/Context;\)V\n(.*?)^\.end method",
                          t, re.M | re.S))
    if len(ms) != 1:
        sys.exit(f"oneui_engmode_undeclared: {len(ms)} constructors; not patched")
    m = ms[0]
    body = m.group(1)
    checks = {
        "loads .engmodejni.samsung": 'const-string p1, ".engmodejni.samsung"\n\n    invoke-static {p1}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V\n',
        "sets mSupportJNI true": f"    const/4 p1, 0x1\n\n    .line 131\n    iput-boolean p1, p0, {FIELD}\n",
        "logs with v0 the tag": '    const-string/jumbo v0, "engmode_java_manager"\n',
        "one local": "    .locals 1\n",
    }
    for what, s in checks.items():
        if body.count(s) != 1:
            sys.exit(f"oneui_engmode_undeclared: constructor no longer {what}; not patched")
    if body.count(ANCHOR) != 1 or body.count("return-void") != 2:
        sys.exit("oneui_engmode_undeclared: constructor's success return not found once; not patched")
    add = (MARK +
           f'    const-string/jumbo p1, "{INSTANCE}"\n\n'
           "    :try_start_oneos_em\n"
           "    invoke-static {p1}, Landroid/os/ServiceManager;->isDeclared(Ljava/lang/String;)Z\n\n"
           "    move-result p1\n"
           "    :try_end_oneos_em\n"
           "    .catch Ljava/lang/Throwable; {:try_start_oneos_em .. :try_end_oneos_em} :oneos_em_keep\n\n"
           "    if-nez p1, :oneos_em_keep\n\n"
           "    const/4 p1, 0x0\n\n"
           f"    iput-boolean p1, p0, {FIELD}\n\n"
           '    const-string/jumbo p1, "OneOS: ISehEngmode/default is not declared on this phone, em library off"\n\n'
           "    invoke-static {v0, p1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I\n\n"
           "    :oneos_em_keep\n")
    new = ANCHOR.replace("    return-void\n", add + "    return-void\n")
    body = body.replace(ANCHOR, new)
    t = t[:m.start(1)] + body + t[m.end(1):]
    with open(p, "w") as f:
        f.write(t)
    print(hits[0])
    print("engmode: off when ISehEngmode/default is not declared", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
