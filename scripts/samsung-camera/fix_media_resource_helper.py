"""SemMediaResourceHelper without its native library (Galaxy A36 camera, LineageOS, 0.5.14).

One UI's framework class (copied into oneos-camera-compat.jar with the other host
classes) loads libmediaresourcehelper.so in <clinit>. That library needs Samsung's
libmedia.so (aidl com.samsung.android.media.BnResourceManagerObserverClient), which no
guest has, so binding One UI's copy cannot work either. The A-series camera creates the
helper when video starts: "UnsatisfiedLinkError: dlopen failed: library
libmediaresourcehelper.so not found" in SemMediaResourceHelper.<clinit>, the camera
closed on every switch to video (A36 LineageOS, 2026-11-15).

The camera uses only createInstance, setVideoCapacityErrorListener and release. Here
the library is not loaded and each native method becomes a Java one: no-ops, and a
codec capacity of 0x10000 (never short), so no capacity error is ever raised.
Usage: fix_media_resource_helper.py <compat smali dir>
"""
import os
import re
import sys

path = os.path.join(sys.argv[1], 'com/samsung/android/media/SemMediaResourceHelper.smali')
if not os.path.exists(path):
    print('SemMediaResourceHelper: not in this build')
    sys.exit(0)
s = open(path).read()

load = re.compile(r'\n[ \t]*(?:\.line \d+\n[ \t]*)?const-string(?:/jumbo)? v0, "mediaresourcehelper"\n\n?[ \t]*invoke-static \{v0\}, Ljava/lang/System;->loadLibrary\(Ljava/lang/String;\)V\n')
s, n = load.subn('\n', s)
if n != 1 and 'loadLibrary' in s:
    sys.exit('SemMediaResourceHelper: loadLibrary not found in the expected form')

bodies = {'V': '    .locals 0\n\n    return-void\n',
          'I': '    .locals 1\n\n    const/high16 v0, 0x10000\n\n    return v0\n'}


def repl(m):
    head, name, ret = m.group(1), m.group(2), m.group(3)
    head = re.sub(r' native(?= )', '', head, count=1)
    return '%s\n%s.end method' % (head, bodies[ret])


native = re.compile(r'(\.method [^\n]* native [^\n]*?(native_\w+)\([^)]*\)([VI]))\n(?:(?!\.end method).)*?\.end method', re.S)
s, k = native.subn(repl, s)
if ' native ' in s:
    sys.exit('SemMediaResourceHelper: a native method is left')
open(path, 'w').write(s)
print('SemMediaResourceHelper: library load removed (%d), %d native methods made Java' % (n, k))
