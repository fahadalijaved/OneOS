"""No ColorOS resolution switch on a panel without ColorOS's density tables.

OplusResolutionManagerFeature (oplus-services.jar) turns the FHD+/QHD+ resolution switch on
when the panel offers modes of two widths, which Samsung's S Ultra and S+ panels do (1080 and
1440). The switch then passes every density through OplusResolutionSwitchImpl.
getDensityForResolution(): a density not listed in the panel's table, ro.density.screenzoom.qdh
(.fdh at FHD+), becomes ro.oplus.density.qhd_default, or 640 when that is unset. In the guest
those are One UI's properties, so neither table exists, and every density became 640: at boot
(resetDensityIfNeed), and again whenever Settings or the user set one ("adjustDensity=640"). The
size chosen in Display size, in Developer options or by OneOS did not survive a boot (0.4.55
reports from the S25 Ultra: "640 kept" in every session; users: "dpi on ColorOS keeps changing
whatever you set").

In init(), after the support checks and before the support is logged, sResolutionSupport is
set back to false when both tables are empty, so the switch is not set up at all and densities
stay as they are set (the Display size list is settingslib's, as on a phone without the switch).
A phone with ColorOS's own tables keeps the switch.

Usage: oplus_resolution_tables.py <smali root dir>
Prints the smali_* directory (dex file) it changed.
"""
import os
import re
import sys

CLASS = "Lcom/android/server/wm/OplusResolutionManagerFeature;"
INIT = ".method public init(Lcom/android/server/wm/WindowManagerService;Landroid/content/Context;)V"
# The support log line and the StringBuilder it starts with (that register is free there).
ANCHOR = re.compile(r"^(    new-instance (v\d+), Ljava/lang/StringBuilder;\n\n"
                    r"    invoke-direct \{\2\}, Ljava/lang/StringBuilder;-><init>\(\)V\n\n"
                    r"    const-string v\d+, \" init support  sResolutionSupport=\")", re.M)


def find(root, rel_suffix):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(rel_suffix)]
    if len(hits) != 1:
        sys.exit(f"{rel_suffix}: {len(hits)} matches")
    return hits[0]


def check_empty(reg, prop):
    return (f"    const-string {reg}, \"{prop}\"\n\n"
            f"    invoke-static {{{reg}}}, Landroid/os/SystemProperties;->get(Ljava/lang/String;)Ljava/lang/String;\n\n"
            f"    move-result-object {reg}\n\n"
            f"    invoke-static {{{reg}}}, Landroid/text/TextUtils;->isEmpty(Ljava/lang/CharSequence;)Z\n\n"
            f"    move-result {reg}\n\n"
            f"    if-eqz {reg}, :oneos_reso_tables\n\n")


def main():
    root = sys.argv[1]
    path = find(root, os.path.join("com", "android", "server", "wm", "OplusResolutionManagerFeature.smali"))
    smali = open(path).read()
    if ":oneos_reso_tables" in smali:
        sys.exit("OplusResolutionManagerFeature already patched")
    start = smali.find(INIT)
    end = smali.find(".end method", start)
    if start < 0 or end < 0:
        sys.exit("OplusResolutionManagerFeature: init(WindowManagerService, Context) not found")
    body = smali[start:end]
    hits = ANCHOR.findall(body)
    if len(hits) != 1:
        sys.exit(f"OplusResolutionManagerFeature.init: {len(hits)} support log lines, expected 1")
    reg = hits[0][1]
    if int(reg[1:]) > 15:
        sys.exit(f"OplusResolutionManagerFeature.init: the free register is {reg}, not a 4-bit one")
    guard = (check_empty(reg, "ro.density.screenzoom.qdh")
             + check_empty(reg, "ro.density.screenzoom.fdh")
             + f"    const/4 {reg}, 0x0\n\n"
             f"    sput-boolean {reg}, {CLASS}->sResolutionSupport:Z\n\n"
             f"    :oneos_reso_tables\n")
    body = ANCHOR.sub(lambda m: guard + m.group(1), body, count=1)
    open(path, "w").write(smali[:start] + body + smali[end:])
    print("OplusResolutionManagerFeature: no resolution switch without ro.density.screenzoom tables", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main()
