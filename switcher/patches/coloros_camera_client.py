#!/usr/bin/env python3
"""ColorOS's (and HyperOS's) camera client name for One UI's cameraserver.

ColorOS's CameraManager.openCameraDeviceUserAsync gives the camera service the
app's component ("net.sourceforge.opencamera/net.sourceforge.opencamera.MainActivity",
ICameraManagerExt.extendGetComponentName) as the AttributionSource package name,
for every app but OPPO's own camera ("use componentName"); OPPO's cameraserver
takes it apart. One UI's, which a guest shares, hands it to the app ops check
as it is, finds no such package for the uid and refuses every open: "Camera 0:
Access for ... has been restricted", "Could not initialize client from HAL"
(S25 Ultra, S25+, A56 reports, 0.4.29 to 0.4.36). The package name goes in
instead: the context's op package name, as ColorOS does for its own camera.
HyperOS writes "<package>&<top activity>" back into the AttributionSourceState's
packageName (S25+ report ff576992: "net.sourceforge.opencamera&...MainActivity");
that write is dropped, the package name stays the app's.

Usage: coloros_camera_client.py <smali root holding android/hardware/camera2/CameraManager.smali>
"""
import os
import re
import sys

COMP = re.compile(r"^(\s*)invoke-interface \{(v\d+)\}, Landroid/hardware/camera2/ICameraManagerExt;->extendGetComponentName\(\)Ljava/lang/String;\s*$")
CTX = re.compile(r"^\s*iget-object v\d+, (v\d+), Landroid/hardware/camera2/CameraManager;->mContext:Landroid/content/Context;\s*$")
SETPKG = "Landroid/content/AttributionSource$Builder;->setPackageName(Ljava/lang/String;)"


def main():
    root = sys.argv[1]
    path = None
    for d, _, fs in os.walk(root):
        if d.endswith(os.path.join("android", "hardware", "camera2")) and "CameraManager.smali" in fs:
            path = os.path.join(d, "CameraManager.smali")
    if not path:
        sys.exit("no android/hardware/camera2/CameraManager.smali under %s" % root)
    lines = open(path, encoding="utf-8").read().split("\n")
    if any("oneos_camera_client" in l for l in lines):
        print("already patched")
        return
    n = 0
    i = 0
    while i < len(lines):
        m = COMP.match(lines[i])
        if m:
            # The next instructions: move-result-object vX, then (within a few
            # lines) setPackageName taking vX. Only that use is changed; the
            # component in the log line stays.
            j = next((k for k in range(i + 1, min(i + 4, len(lines))) if lines[k].strip().startswith("move-result-object")), None)
            if j is not None:
                out = lines[j].split()[1]
                use = next((k for k in range(j + 1, min(j + 6, len(lines))) if SETPKG in lines[k] and (" " + out + "}" in lines[k] or ", " + out + "}" in lines[k])), None)
                if use is not None:
                    # "this": the register an earlier mContext load in the method reads from.
                    start = max(k for k in range(i) if lines[k].startswith(".method"))
                    this = next((CTX.match(lines[k]).group(1) for k in range(i, start, -1) if CTX.match(lines[k])), None)
                    if this is None:
                        sys.exit("no mContext load before line %d" % i)
                    ind = m.group(1)
                    lines[i:j + 1] = [
                        ind + "# oneos_camera_client: the package name, not the component (patches/coloros_camera_client.py)",
                        ind + "iget-object %s, %s, Landroid/hardware/camera2/CameraManager;->mContext:Landroid/content/Context;" % (out, this),
                        ind + "invoke-virtual {%s}, Landroid/content/Context;->getOpPackageName()Ljava/lang/String;" % out,
                        ind + "move-result-object %s" % out,
                    ]
                    n += 1
        i += 1
    # HyperOS: <package> + "&" + <activity> written back to packageName.
    for i in range(len(lines)):
        if re.match(r'^\s*const-string v\d+, "&"\s*$', lines[i]):
            for k in range(i + 1, min(i + 20, len(lines))):
                if re.match(r"^\s*iput-object v\d+, v\d+, Landroid/content/AttributionSourceState;->packageName:Ljava/lang/String;\s*$", lines[k]):
                    lines[k] = "    # oneos_camera_client: the app's package name stays (patches/coloros_camera_client.py): " + lines[k].strip()
                    n += 1
                    break
    if n == 0:
        sys.exit("no extendGetComponentName -> setPackageName nor package&activity in %s" % path)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    print("patched %s: %d client name(s)" % (os.path.relpath(path, root), n))


if __name__ == "__main__":
    main()
