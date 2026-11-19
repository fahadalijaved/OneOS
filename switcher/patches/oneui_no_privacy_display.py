"""One UI 9.5's Privacy Display stays off on phones without its panel.

Privacy Display is the Galaxy S26 Ultra's panel feature. One UI 9.5's framework.jar sets its flags
(com.samsung.android.rune.CoreRune FW_PRIVACY_DISPLAY, FW_PARTIAL_PRIVACY_DISPLAY,
FW_SUPPORT_PRIVACY_DISPLAY_FOR_APPLOCK, FW_PRIVACY_DISPLAY_*) to true at build time, not from the
phone's floating features, so every phone running it took the feature's paths (window manager,
display, transitions, app lock) against a panel that has none. They are set false at the end of
CoreRune's static initializer, before anything reads them (framework and services read them with
sget; nothing has them inlined).

Usage: oneui_no_privacy_display.py <apktool -r dir of framework.jar>
Prints the smali_* directory it changed; nothing (and "not present" on stderr) without the flags.
"""
import os
import re
import sys

CLASS = "Lcom/samsung/android/rune/CoreRune;"
FIELD = re.compile(r"^\.field public static final [^\n]*?\b(FW_(?:PARTIAL_|SUPPORT_)?PRIVACY_DISPLAY[A-Z_]*):Z$", re.M)
MARK = "    # OneOS: Privacy Display off (oneui_no_privacy_display.py)\n"


def main(root):
    for d, _, fs in os.walk(root):
        if "CoreRune.smali" not in fs:
            continue
        p = os.path.join(d, "CoreRune.smali")
        t = open(p, errors="replace").read()
        if not t.split("\n", 1)[0].endswith(" " + CLASS):
            continue
        fields = FIELD.findall(t)
        if not fields:
            break
        if MARK in t:
            print(os.path.relpath(p, root).split(os.sep)[0])
            return
        m = re.search(r"^\.method static constructor [^\n]*<clinit>\(\)V\n(.*?)^\.end method", t, re.M | re.S)
        if not m:
            sys.exit(f"{p}: no static initializer; not patched")
        body = m.group(1)
        if body.count("return-void") != 1:
            sys.exit(f"{p}: <clinit> returns {body.count('return-void')} times; not patched")
        add = MARK + "    const/4 v0, 0x0\n" + "".join(f"    sput-boolean v0, {CLASS}->{f}:Z\n" for f in fields) + "\n"
        body = body.replace("    return-void", add + "    return-void")
        t = t[:m.start(1)] + body + t[m.end(1):]
        open(p, "w").write(t)
        print(os.path.relpath(p, root).split(os.sep)[0])
        print(f"Privacy Display off: {' '.join(fields)}", file=sys.stderr)
        return
    print("not present", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
