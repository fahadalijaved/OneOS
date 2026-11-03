"""One UI's camera in a guest: a bar phone's resources at most 411dp wide.

The camera is the Z Fold8 Ultra's build, with complete layout sets for other
Samsung screens (sw480dp-xxxhdpi, sw536dp-xxhdpi, ...). A bar phone whose One UI
is zoomed out gets the same scale in the guest (S25 Ultra at density 329 on 1080
px: 525dp), so Android picked sw480dp-xxxhdpi, a layout made for another screen:
the shutter row sat half a screen to the left (cut off at the edge in portrait,
at the bottom in landscape; 0.4.37 report 360d6276, Nothing OS, and the same in
ColorOS). At One UI's default zoom an S Ultra is about 411dp wide.

The camera activity's base context now carries an override of only
smallestScreenWidthDp (411) when the phone has fewer than two device states (a
bar phone, as semDisplayDeviceType decides) and is wider than that. A fold keeps
its real widths (its inner screen needs the large layouts). The override is a
delta, so the resources follow rotations as before.

Found by class name (com.sec.android.app.camera.Camera); its superclass is read
from the file, since the obfuscated names change with each camera version.

Usage: fix_bar_width.py <smali root (proj_SamsungCamera or a full decompile)>
"""
import os
import re
import sys

CAMERA = "com/sec/android/app/camera/Camera.smali"
HELPER = "Loneos/camera/OneOSBarWidth;"
CAP = 411

HELPER_SMALI = """.class public final Loneos/camera/OneOSBarWidth;
.super Ljava/lang/Object;
.source "OneOSBarWidth.smali"


.method public static wrap(Landroid/content/Context;)Landroid/content/Context;
    .locals 4

    :try_start
    invoke-virtual {p0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;
    move-result-object v0
    invoke-virtual {v0}, Landroid/content/res/Resources;->getConfiguration()Landroid/content/res/Configuration;
    move-result-object v0
    iget v0, v0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I
    const/16 v1, CAPHEX
    if-le v0, v1, :keep
    const-string v0, "device_state"
    invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;
    move-result-object v0
    invoke-static {v0}, Landroid/hardware/devicestate/IDeviceStateManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/hardware/devicestate/IDeviceStateManager;
    move-result-object v0
    invoke-interface {v0}, Landroid/hardware/devicestate/IDeviceStateManager;->getDeviceStateInfo()Landroid/hardware/devicestate/DeviceStateInfo;
    move-result-object v0
    iget-object v0, v0, Landroid/hardware/devicestate/DeviceStateInfo;->supportedStates:Ljava/util/ArrayList;
    invoke-virtual {v0}, Ljava/util/ArrayList;->size()I
    move-result v0
    const/4 v2, 0x2
    if-ge v0, v2, :keep
    new-instance v0, Landroid/content/res/Configuration;
    invoke-direct {v0}, Landroid/content/res/Configuration;-><init>()V
    iput v1, v0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I
    invoke-virtual {p0, v0}, Landroid/content/Context;->createConfigurationContext(Landroid/content/res/Configuration;)Landroid/content/Context;
    move-result-object v0
    const-string v2, "OneOSSem"
    const-string v3, "bar phone: the camera's resources at smallestScreenWidthDp CAPDEC"
    invoke-static {v2, v3}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    return-object v0
    :try_end
    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :keep

    :keep
    return-object p0
.end method
""".replace("CAPHEX", hex(CAP)).replace("CAPDEC", str(CAP))

ATTACH = """
.method protected attachBaseContext(Landroid/content/Context;)V
    .locals 0

    invoke-static {p1}, %s->wrap(Landroid/content/Context;)Landroid/content/Context;
    move-result-object p1
    invoke-super {p0, p1}, %s->attachBaseContext(Landroid/content/Context;)V
    return-void
.end method
"""


def main():
    root = sys.argv[1]
    dirs = sorted((d for d in os.listdir(root) if re.fullmatch(r"smali(_classes\d+)?", d)),
                  key=lambda d: int(d[len("smali_classes"):]) if d != "smali" else 1)
    cam = [os.path.join(root, d, CAMERA) for d in dirs if os.path.isfile(os.path.join(root, d, CAMERA))]
    if len(cam) != 1:
        sys.exit("fix_bar_width: %d copies of %s under %s" % (len(cam), CAMERA, root))
    src = open(cam[0]).read()
    if HELPER in src:
        print("fix_bar_width: already patched")
        return
    if re.search(r"^\.method .*attachBaseContext\(Landroid/content/Context;\)V", src, re.M):
        sys.exit("fix_bar_width: Camera has its own attachBaseContext now; patch it by hand")
    sup = re.search(r"^\.super (L[\w/$]+;)", src, re.M).group(1)
    open(cam[0], "w").write(src.rstrip("\n") + "\n" + ATTACH % (HELPER, sup))
    last = dirs[-1]
    n = 2 if last == "smali" else int(last[len("smali_classes"):]) + 1
    out = os.path.join(root, "smali_classes%d" % n, "oneos", "camera")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "OneOSBarWidth.smali"), "w").write(HELPER_SMALI)
    print("fix_bar_width: Camera (super %s) wraps its base context; helper in smali_classes%d" % (sup, n))


if __name__ == "__main__":
    main()
