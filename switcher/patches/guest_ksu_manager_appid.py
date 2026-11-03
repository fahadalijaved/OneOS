"""The KernelSU manager keeps One UI's app id in the guest.

KernelSU knows its manager by app id: the kernel crowns the uid One UI's
package manager gave the manager app (me.weishu.kernelsu, 10435 on the F8U),
and only that uid may change the root allowlist and app profiles. A guest's
package manager numbers new apps from 15000 (guest_app_id_offset.py), so a
manager installed in the guest would be just another app. With this patch the
package named by oneos.ksu.mgr_pkg gets the app id in oneos.ksu.mgr_appid
(oneos_switch.sh sets both from One UI's packages.list before the guest boots),
and the manager inside the guest is the manager.

At the entry of AppIdSettingMap.acquireAndRegisterNewAppId(SettingBase): when
that SettingBase is a PackageSetting of that package and the id is One UI's
range (10000..14999, which no guest app takes), the id goes through
registerExistingAppId (the path packages.xml ids take) and is returned; when
that fails (slot taken) or anything does not match, the method runs as before.
The id is One UI's manager's own, so it shares that app's keystore2 namespace
(the reason for 15000): the manager is the same app, signed the same.

Usage: guest_ksu_manager_appid.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

SUFFIX = os.path.join("com", "android", "server", "pm", "AppIdSettingMap.smali")
CLS = "Lcom/android/server/pm/AppIdSettingMap;"
PS = "Lcom/android/server/pm/PackageSetting;"
SB = "Lcom/android/server/pm/SettingBase;"
SP = "Landroid/os/SystemProperties;"
HEADER = re.compile(r"^\.method (?:private |public |protected |final |static |synchronized )*"
                    r"acquireAndRegisterNewAppId\(Lcom/android/server/pm/SettingBase;\)I$")
REGISTER = re.compile(r"^\.method (?:public |final )*registerExistingAppId\(ILcom/android/server/pm/SettingBase;Ljava/lang/Object;\)Z$")


def entry(lines, i):
    """Index of the first line after the header, .locals and the .param blocks."""
    j, in_param = i + 2, False
    while True:
        s = lines[j].strip()
        if in_param:
            in_param = not s.startswith(".end param")
        elif s.startswith(".param ") and j + 1 < len(lines) and lines[j + 1].strip().startswith(".annotation"):
            in_param = True
        elif not (s == "" or s.startswith((".param ", ".prologue"))):
            return j
        j += 1


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + SUFFIX)]
    if len(hits) != 1:
        sys.exit(f"expected one AppIdSettingMap.smali, found {len(hits)}")
    path = hits[0]
    rel = os.path.relpath(path, root)
    with open(path) as f:
        lines = f.read().split("\n")
    if any("oneos_ksu_mgr" in l for l in lines):
        sys.exit(f"{rel}: already patched")
    if not any(REGISTER.match(l) for l in lines):
        sys.exit(f"{rel}: no registerExistingAppId(int, SettingBase, Object); not patched")
    pkg = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
           if os.path.join(d, f).endswith(os.sep + os.path.join("com", "android", "server", "pm", "PackageSetting.smali"))]
    if len(pkg) != 1 or not any(re.match(r"^\.method public (final )?getPackageName\(\)Ljava/lang/String;$", l)
                                for l in open(pkg[0]).read().split("\n")):
        sys.exit(f"{rel}: PackageSetting.getPackageName() not found; not patched")
    heads = [k for k, l in enumerate(lines) if HEADER.match(l)]
    if len(heads) != 1:
        sys.exit(f"{rel}: acquireAndRegisterNewAppId(SettingBase) found {len(heads)} times, expected once")
    i = heads[0]
    m = re.match(r"(\s*)\.locals (\d+)$", lines[i + 1])
    if not m:
        sys.exit(f"{rel}: acquireAndRegisterNewAppId: expected .locals after the header")
    if int(m.group(2)) < 3:
        lines[i + 1] = f"{m.group(1)}.locals 3"
    j = entry(lines, i)
    lines[j:j] = [
        "    # OneOS: the KernelSU manager keeps One UI's app id (the kernel knows it by",
        "    # that uid); oneos.ksu.mgr_pkg / oneos.ksu.mgr_appid, set by oneos_switch.sh.",
        '    const-string v0, "oneos.ksu.mgr_pkg"',
        f"    invoke-static {{v0}}, {SP}->get(Ljava/lang/String;)Ljava/lang/String;",
        "    move-result-object v0",
        "    invoke-virtual {v0}, Ljava/lang/String;->isEmpty()Z",
        "    move-result v1",
        "    if-nez v1, :oneos_ksu_mgr_done",
        f"    instance-of v1, p1, {PS}",
        "    if-eqz v1, :oneos_ksu_mgr_done",
        "    move-object v1, p1",
        f"    check-cast v1, {PS}",
        f"    invoke-virtual {{v1}}, {PS}->getPackageName()Ljava/lang/String;",
        "    move-result-object v1",
        "    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z",
        "    move-result v0",
        "    if-eqz v0, :oneos_ksu_mgr_done",
        '    const-string v0, "oneos.ksu.mgr_appid"',
        "    const/4 v2, 0x0",
        f"    invoke-static {{v0, v2}}, {SP}->getInt(Ljava/lang/String;I)I",
        "    move-result v0",
        "    const/16 v2, 0x2710",
        "    if-lt v0, v2, :oneos_ksu_mgr_done",
        "    const/16 v2, 0x3a98",
        "    if-ge v0, v2, :oneos_ksu_mgr_done",
        f"    invoke-virtual {{p0, v0, p1, v1}}, {CLS}->registerExistingAppId(I{SB}Ljava/lang/Object;)Z",
        "    move-result v2",
        "    if-eqz v2, :oneos_ksu_mgr_done",
        '    const-string v1, "PackageManager"',
        '    const-string v2, "OneOS: KernelSU manager keeps One UI\'s app id"',
        "    invoke-static {v1, v2}, Landroid/util/Slog;->i(Ljava/lang/String;Ljava/lang/String;)I",
        "    return v0",
        "    :oneos_ksu_mgr_done",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"{rel}: acquireAndRegisterNewAppId gives oneos.ksu.mgr_pkg the app id oneos.ksu.mgr_appid", file=sys.stderr)
    print(rel.split(os.sep)[0])


if __name__ == "__main__":
    main(sys.argv[1])
