#!/usr/bin/env python3
"""One UI 9.5 set r5: WindowManagerService always makes its PrivacyDisplayController.

Set r2 turned CoreRune's FW_PRIVACY_DISPLAY flags off (oneui_no_privacy_display.py), and
WindowManagerService's constructor makes the controller only under that flag. Fourteen classes of
services.jar use WindowManagerServiceExt.mPrivacyDisplayController; r3 null-checked the four binder
calls in WindowManagerService (oneui_privacy_display_null_safe.py), but others read it unguarded:
Transition.collectVisibleChange read mPrivacyDisplayApplied on null at a display configuration change,
"FATAL EXCEPTION IN SYSTEM PROCESS: android.display", and One UI 9.5's system died 1 to 6 minutes in
(11-19 reports d972589b S23 on 0.5.25, b978fbbd A26, 81846c57 S23 Ultra).

The controller is made whatever the flag says: the S26 Ultra's own object, idle with every Privacy
Display flag off (nothing turns it on), and each of those reads gets "not applied". Fail-closed: the
flag read must be found exactly once, right before the controller's new-instance, else exit 1.

    oneui_privacy_display_controller_always.py <services smali dir>   -> prints the smali dir it changed
"""
import os
import re
import sys

CLS = "com/android/server/wm/WindowManagerService.smali"
MARK = "# OneOS: PrivacyDisplayController made whatever FW_PRIVACY_DISPLAY says"
GATE = re.compile(
    r"^( *)sget-boolean (v\d+), Lcom/samsung/android/rune/CoreRune;->FW_PRIVACY_DISPLAY:Z\n"
    r"(\s*)if-eqz \2, (:cond_\w+)\n"
    r"(\s*)new-instance v\d+, Lcom/android/server/wm/PrivacyDisplayController;\n", re.M)


def main():
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(hits) != 1:
        sys.exit(f"oneui_privacy_display_controller_always: {CLS} found in {hits or 'no smali dir'}")
    path = os.path.join(root, hits[0], CLS)
    src = open(path).read()
    if MARK in src:
        print(hits[0])
        return
    found = list(GATE.finditer(src))
    if len(found) != 1:
        sys.exit(f"oneui_privacy_display_controller_always: the controller's flag gate found {len(found)} times")
    m = found[0]
    ind, reg = m.group(1), m.group(2)
    flag = m.group(0).splitlines(True)[0]
    src = src[:m.start()] + f"{ind}{MARK}\n{ind}const/4 {reg}, 0x1\n" + src[m.start() + len(flag):]
    with open(path, "w") as f:
        f.write(src)
    print(hits[0])


if __name__ == "__main__":
    main()
