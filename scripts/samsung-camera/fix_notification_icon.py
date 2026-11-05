"""One UI's camera in a guest: notification icons the guest's status bar can draw.

The camera's notification icons (drawable/saving_notification and the others in res/*.bmp) are
Samsung's SPR vectors ("SPR\\0" files), which only One UI's framework decodes. The camera draws them
in its own window through the compat layer, but a guest's SystemUI cannot: posting the video
recording's foreground notification failed with "Couldn't create icon StatusBarIcon(icon=Icon(typ=
RESOURCE pkg=com.sec.android.app.camera id=0x7f080d0d))", and Android crashed the camera with
BadForegroundServiceNotificationException (0.4.55 report 3715fe57, S25 Ultra, ColorOS: no video).

Every call of the platform's Notification.Builder.setSmallIcon (int, int + level, Icon) in the
camera goes to Loneos/camera/OneOSNotify;, which sets the framework's own camera icon
(android.R.drawable.ic_menu_camera, from the "android" package every SystemUI loads). The
register lists stay as they were: an invoke-virtual {builder, args} becomes invoke-static with the
builder as the first argument.

The helper goes into a dex of its own (a new smali_classesN), not beside the calls: the S26
Ultra camera's classes2.dex already has 65535 method ids, and the helper's own methods and the
framework calls it makes went over the 65536 a dex can hold. The calling dex only trades the
three setSmallIcon references for the helper's three.

Usage: fix_notification_icon.py <smali root of the decoded camera APK>
Prints the smali_* directories (dex files) it changed or added, one per line; the summary goes to
stderr.
"""
import os
import re
import sys

HELPER = "Loneos/camera/OneOSNotify;"
NB = "Landroid/app/Notification$Builder;"
CALLS = {
    f"{NB}->setSmallIcon(I){NB}": f"{HELPER}->setSmallIcon({NB}I){NB}",
    f"{NB}->setSmallIcon(II){NB}": f"{HELPER}->setSmallIcon({NB}II){NB}",
    f"{NB}->setSmallIcon(Landroid/graphics/drawable/Icon;){NB}": f"{HELPER}->setSmallIcon({NB}Landroid/graphics/drawable/Icon;){NB}",
}

HELPER_SMALI = """.class public final Loneos/camera/OneOSNotify;
.super Ljava/lang/Object;
.source "OneOSNotify.smali"


.method public static setSmallIcon(Landroid/app/Notification$Builder;I)Landroid/app/Notification$Builder;
    .locals 1
    sget v0, Landroid/R$drawable;->ic_menu_camera:I
    invoke-virtual {p0, v0}, Landroid/app/Notification$Builder;->setSmallIcon(I)Landroid/app/Notification$Builder;
    move-result-object v0
    return-object v0
.end method

.method public static setSmallIcon(Landroid/app/Notification$Builder;II)Landroid/app/Notification$Builder;
    .locals 1
    sget v0, Landroid/R$drawable;->ic_menu_camera:I
    invoke-virtual {p0, v0, p2}, Landroid/app/Notification$Builder;->setSmallIcon(II)Landroid/app/Notification$Builder;
    move-result-object v0
    return-object v0
.end method

.method public static setSmallIcon(Landroid/app/Notification$Builder;Landroid/graphics/drawable/Icon;)Landroid/app/Notification$Builder;
    .locals 2
    const-string v0, "android"
    sget v1, Landroid/R$drawable;->ic_menu_camera:I
    invoke-static {v0, v1}, Landroid/graphics/drawable/Icon;->createWithResource(Ljava/lang/String;I)Landroid/graphics/drawable/Icon;
    move-result-object v0
    invoke-virtual {p0, v0}, Landroid/app/Notification$Builder;->setSmallIcon(Landroid/graphics/drawable/Icon;)Landroid/app/Notification$Builder;
    move-result-object v0
    return-object v0
.end method
"""


def main(root):
    if not os.path.isdir(root):
        sys.exit(f"{root} is not a folder")
    pat = re.compile(r"invoke-virtual(/range)? \{([^}]*)\}, (" + "|".join(re.escape(k) for k in CALLS) + r")")
    changed = 0
    files = 0
    dirs = set()
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            s = open(p).read()
            if "setSmallIcon" not in s:
                continue
            n = 0

            def sub(m):
                nonlocal n
                n += 1
                return f"invoke-static{m.group(1) or ''} {{{m.group(2)}}}, {CALLS[m.group(3)]}"
            s2 = pat.sub(sub, s)
            if n:
                open(p, "w").write(s2)
                changed += n
                files += 1
                dirs.add(os.path.relpath(p, root).split(os.sep)[0])
    if not changed:
        sys.exit("no Notification.Builder.setSmallIcon call found")
    smali = [d for d in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", d)]
    for d in smali:
        if os.path.exists(os.path.join(root, d, "oneos", "camera", "OneOSNotify.smali")):
            sys.exit(f"OneOSNotify.smali is already there ({d})")
    n = max(int(d[len("smali_classes"):]) if d != "smali" else 1 for d in smali) + 1
    own = f"smali_classes{n}"
    out = os.path.join(root, own, "oneos", "camera")
    os.makedirs(out)
    open(os.path.join(out, "OneOSNotify.smali"), "w").write(HELPER_SMALI)
    for d in sorted(dirs) + [own]:
        print(d)
    print(f"notification small icons: {changed} call(s) in {files} file(s) to OneOSNotify ({own})", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
