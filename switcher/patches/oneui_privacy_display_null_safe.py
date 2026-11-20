#!/usr/bin/env python3
"""One UI 9.5 set r3: WindowManagerService's Privacy Display calls without a controller.

Set r2 (oneui_no_privacy_display.py) turned CoreRune's FW_PRIVACY_DISPLAY flags off, so
WindowManagerServiceExt.mPrivacyDisplayController is never made. SystemUI keeps its own Privacy
Display screens and still asks: IWindowManager.getPrivacyDisplayCustomAppList threw
NullPointerException (the getClass() null check after the iget) into SystemUI's
ScreenPrivacyDetailViewModel, which crashed it every 3 s on every phone but the S26 Ultra
(11-19 reports on A16, A17, S23, S23 Ultra: 8 to 94 crashes a session).

The binder calls SystemUI and Settings can make get a null check right after the controller is
read: the app list returns an empty ArrayList, the others return. Fail-closed: every method must be
found with exactly one read of the controller, else exit 1.

    oneui_privacy_display_null_safe.py <services smali dir>   -> prints the smali dir it changed
"""
import os
import re
import sys

CLS = "com/android/server/wm/WindowManagerService.smali"
READ = "Lcom/android/server/wm/WindowManagerServiceExt;->mPrivacyDisplayController:Lcom/android/server/wm/PrivacyDisplayController;"
METHODS = {
    "getPrivacyDisplayCustomAppList(I)Ljava/util/List;": "list",
    "requestPrivacyDisplayEnable(ZLjava/lang/String;)V": "void",
    "resetAllPrivacyDisplaySettings()V": "void",
    "setPrivacyDisplayPolicy(ILjava/lang/String;I)V": "void",
}
MARK = "# OneOS: no Privacy Display controller"


def main():
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(hits) != 1:
        sys.exit(f"oneui_privacy_display_null_safe: {CLS} found in {hits or 'no smali dir'}")
    path = os.path.join(root, hits[0], CLS)
    src = open(path).read()
    if MARK in src:
        print(hits[0])
        return
    for sig, kind in METHODS.items():
        m = re.search(r"^\.method [^\n]*" + re.escape(sig) + r"\n(.*?)^\.end method", src, re.M | re.S)
        if not m:
            sys.exit(f"oneui_privacy_display_null_safe: {sig} not found")
        body = m.group(1)
        reads = list(re.finditer(r"^( *)iget-object ([vp]\d+), [vp]\d+, " + re.escape(READ) + r"\n", body, re.M))
        if len(reads) != 1:
            sys.exit(f"oneui_privacy_display_null_safe: {sig} reads the controller {len(reads)} times")
        r = reads[0]
        ind, reg = r.group(1), r.group(2)
        label = ":oneos_pd_" + sig.split("(")[0]
        if kind == "list":
            loc = re.search(r"^ *\.locals (\d+)", body, re.M)
            if not loc or int(loc.group(1)) < 1:
                sys.exit(f"oneui_privacy_display_null_safe: {sig} has no local register")
            ret = (f"{ind}new-instance v0, Ljava/util/ArrayList;\n{ind}invoke-direct {{v0}}, Ljava/util/ArrayList;-><init>()V\n"
                   f"{ind}return-object v0\n")
        else:
            ret = f"{ind}return-void\n"
        guard = f"{r.group(0)}\n{ind}{MARK}\n{ind}if-nez {reg}, {label}\n\n{ret}\n{ind}{label}\n"
        body = body[:r.start()] + guard + body[r.end():]
        src = src[:m.start(1)] + body + src[m.end(1):]
    with open(path, "w") as f:
        f.write(src)
    print(hits[0])


if __name__ == "__main__":
    main()
