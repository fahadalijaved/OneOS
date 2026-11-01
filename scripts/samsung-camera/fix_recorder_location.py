"""One UI's camera in a guest: MediaRecorder.setLocation after prepare.

AOSP's MediaRecorder refuses setParameters (and so setLocation) once prepared;
One UI's accepts it, and the camera sets the video's location then: every
recording crashed with IllegalStateException (Nothing run 24). Each call goes
to oneos.semcompat.OneOSRecorder.setLocation (compat_extra), which skips the
location when the recorder refuses it.

Usage: fix_recorder_location.py <smali root of the assembled camera>
"""
import os
import re
import sys

# Method name -> its parameter types after the recorder.
METHODS = {"setLocation": "FF", "setOrientationHint": "I"}
CALL = re.compile(r"^(\s*)invoke-virtual(/range)? \{([^}]*)\}, Landroid/media/MediaRecorder;->(setLocation|setOrientationHint)\((FF|I)\)V\s*$")


def main():
    root = sys.argv[1]
    n = 0
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".smali"):
                continue
            p = os.path.join(d, f)
            lines = open(p, encoding="utf-8").read().split("\n")
            changed = False
            for i, l in enumerate(lines):
                m = CALL.match(l)
                if m and METHODS[m.group(4)] == m.group(5):
                    lines[i] = "%sinvoke-static%s {%s}, Loneos/semcompat/OneOSRecorder;->%s(Landroid/media/MediaRecorder;%s)V" % (
                        m.group(1), m.group(2) or "", m.group(3), m.group(4), m.group(5))
                    changed = True
                    n += 1
            if changed:
                open(p, "w", encoding="utf-8").write("\n".join(lines))
    if n == 0:
        sys.exit("no MediaRecorder setLocation/setOrientationHint call found")
    print("MediaRecorder setLocation/setOrientationHint: %d call(s) to OneOSRecorder" % n)


if __name__ == "__main__":
    main()
