#!/usr/bin/env python3
"""Select Samsung's app-private PDI fallback on the Fold8 One UI 9.5 donor."""

import re
import sys
from pathlib import Path

CLASS = Path("com/samsung/android/security/SemPassStorageManager.smali")
ENTRY = re.compile(
    r"(?m)(^\.method public static(?: whitelist)? "
    r"getInstance\(\)Lcom/samsung/android/security/SemPassStorageManager;\n)"
    r"    \.locals 1\n"
    r"(?=\n    \.line 120\n"
    r"    invoke-static \{\}, Lcom/samsung/android/security/SemPassStorageManager;->isKeepSupport\(\)Z)"
)

GUEST_FALLBACK = """    .locals 4

    # Samsung PDI 7.4.01.9's Moneta process must use its native app-private fallback.
    sget-object v0, Landroid/os/Build;->MODEL:Ljava/lang/String;
    const-string v1, "SM-F971B"
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :oneos_pass_native

    invoke-static {}, Landroid/app/Application;->getProcessName()Ljava/lang/String;
    move-result-object v0
    const-string v1, "com.samsung.android.smartsuggestions:moneta"
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v0
    if-eqz v0, :oneos_pass_native

    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;
    move-result-object v0
    if-eqz v0, :oneos_pass_native

    invoke-virtual {v0}, Landroid/app/Application;->getApplicationInfo()Landroid/content/pm/ApplicationInfo;
    move-result-object v0
    iget-wide v0, v0, Landroid/content/pm/ApplicationInfo;->longVersionCode:J
    const-wide v2, 740109000
    cmp-long v0, v0, v2
    if-nez v0, :oneos_pass_native

    const/4 v0, 0x0
    return-object v0

    :oneos_pass_native
"""


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_fold8_pdi_framework.py <apktool decoded directory>")
    root = Path(sys.argv[1])
    matches = [directory / CLASS for directory in root.glob("smali*") if (directory / CLASS).is_file()]
    if len(matches) != 1:
        raise SystemExit("expected exactly one SemPassStorageManager class")
    path = matches[0]
    source = path.read_text()
    updated, count = ENTRY.subn(lambda match: match[1] + GUEST_FALLBACK, source)
    if count != 1:
        raise SystemExit("unexpected SemPassStorageManager.getInstance donor")
    path.write_text(updated)
    print(path.relative_to(root).parts[0])


if __name__ == "__main__":
    main()
