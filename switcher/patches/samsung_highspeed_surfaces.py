"""Samsung Camera's slow motion in an AOSP guest: up to 4 outputs in a constrained high-speed session.

Samsung's camera opens its slow-motion session with three outputs (preview, recorder and a
1280x720 YUV stream for its own analysis). One UI's framework allows that; AOSP's
SurfaceUtils.checkConstrainedHighSpeedSurfaces throws for more than two ("Output target
surface list must not be null and the size must be 1 or 2"), the camera's
createHighSpeedCaptureSession failed and it stayed on a frozen preview (Galaxy A36
LineageOS, 2026-11-15). The guest's camera calls go to One UI's cameraserver
(pixel_camera_abi.py), which takes Samsung's three-stream session as it does in One UI.
Only the count changes: 2 -> 4.
Usage: samsung_highspeed_surfaces.py <decoded framework dir>; prints the smali_classes dir it changed.
"""
import glob
import os
import re
import sys

root = sys.argv[1]
hits = glob.glob(os.path.join(root, 'smali*/android/hardware/camera2/utils/SurfaceUtils.smali'))
if not hits:
    sys.exit(0)
path = hits[0]
s = open(path).read()
m = re.search(r'\.method public static [^\n]*checkConstrainedHighSpeedSurfaces\(Ljava/util/Collection;[^\n]*\n(.*?)\.end method', s, re.S)
if not m:
    sys.exit(0)
body = m.group(1)
pat = re.compile(r'(invoke-interface \{p0\}, Ljava/util/Collection;->size\(\)I\n\s*move-result (v\d+)\n\s*const/4 (v\d+), )0x2(\n\s*if-gt \2, \3, :cond_\w+)')
new, n = pat.subn(r'\g<1>0x4\4', body, count=1)
if n != 1:
    if re.search(r'const/4 v\d+, 0x4\n\s*if-gt', body):
        sys.exit(0)  # already patched
    sys.exit('SurfaceUtils.checkConstrainedHighSpeedSurfaces: the size check is not in the expected form')
s = s[:m.start(1)] + new + s[m.end(1):]
open(path, 'w').write(s)
print(os.path.relpath(path, root).split('/')[0])
