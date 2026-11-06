"""One UI's camera in a guest: its thumbnail opens the guest's gallery.

The camera's thumbnail opens Samsung Gallery's quick view (com.sec.android.gallery3d,
ImageQuickViewActivity, action QUICK_VIEW) by class name. A guest has no Samsung Gallery: the
start throws ActivityNotFoundException, the camera logs "launchGallery : Gallery was disabled!!"
and says no gallery is installed (0.4.58 report f794c15d, Galaxy S25+ in ColorOS).

Each start in that method (startActivityForResult(Intent, int, Bundle) on the camera activity: one
with the thumbnail's scale-up animation, one with the camera's own) goes
to Loneos/camera/OneOSGallery;->startActivityForResult (helpers/src, helpers/build.sh), which tries
it unchanged first (a guest with Samsung Gallery keeps it) and then opens the same picture or video
with a plain ACTION_VIEW and read permission, which the guest's own gallery handles: a secmedia uri
as the same id in MediaStore, a whole collection as the newest DCIM/Camera shot. When that finds no
app either, the original ActivityNotFoundException goes back to the camera, as before.

The helper goes into a dex of its own (a new smali_classesN), as with fix_notification_icon.py; a
camera patched before gets the current helper in place of its own.

Usage: fix_gallery_fallback.py <smali root of the decoded camera APK>
Prints the smali_* directories (dex files) it changed or added, one per line; the summary goes to
stderr.
"""
import os
import re
import shutil
import sys

MARK = '"launchGallery : Gallery was disabled!!"'
CALL = re.compile(r"^(\s*)invoke-virtual \{(v\d+), (v\d+), (v\d+), (v\d+)\}, L[\w/$]+;->startActivityForResult"
                  r"\(Landroid/content/Intent;ILandroid/os/Bundle;\)V\s*$")
HELPER = "Loneos/camera/OneOSGallery;->startActivityForResult(Landroid/app/Activity;Landroid/content/Intent;ILandroid/os/Bundle;)V"

HERE = os.path.dirname(os.path.abspath(__file__))


def main(root):
    if not os.path.isdir(root):
        sys.exit(f"{root} is not a folder")
    hits = []
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".smali"):
                p = os.path.join(d, f)
                if MARK in open(p).read():
                    hits.append(p)
    if len(hits) != 1:
        sys.exit(f"expected one class with {MARK}, found {len(hits)}: {hits}")
    p = hits[0]
    lines = open(p).read().split("\n")
    mark = next(i for i, l in enumerate(lines) if MARK in l)
    start = max(i for i in range(mark) if lines[i].startswith(".method "))
    end = next(i for i in range(mark, len(lines)) if lines[i].startswith(".end method"))
    n = 0
    for i in range(start, end):
        m = CALL.match(lines[i])
        if m:
            lines[i] = f"{m.group(1)}invoke-static {{{m.group(2)}, {m.group(3)}, {m.group(4)}, {m.group(5)}}}, {HELPER}"
            n += 1
    if not n and not any(HELPER in lines[i] for i in range(start, end)):
        sys.exit(f"{p}: no startActivityForResult(Intent, int, Bundle) in launchGallery's method")
    if n:
        open(p, "w").write("\n".join(lines))
    smali = [d for d in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", d)]
    have = [d for d in smali if os.path.exists(os.path.join(root, d, "oneos", "camera", "OneOSGallery.smali"))]
    if have:
        own = have[0]
    else:
        own = "smali_classes%d" % (max(int(d[len("smali_classes"):]) if d != "smali" else 1 for d in smali) + 1)
        os.makedirs(os.path.join(root, own, "oneos", "camera"))
    shutil.copyfile(os.path.join(HERE, "helpers", "smali", "OneOSGallery.smali"), os.path.join(root, own, "oneos", "camera", "OneOSGallery.smali"))
    if n:
        print(os.path.relpath(p, root).split(os.sep)[0])
    print(own)
    print(f"gallery fallback: {n} gallery start(s) in {os.path.relpath(p, root)} to OneOSGallery ({own})", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
