"""ColorOS's sound trigger on a phone with no sound-trigger HAL: give up, as AOSP does.

ColorOS's SoundTriggerModule.attachToHal has an OPPO branch for Qualcomm and MediaTek
platforms (Build.isQcomPlatform() / isMtkPlatform()): it creates the HAL in a loop and
catches every RuntimeException ("Failed to init SoundTriggerHal."), with no limit and no
pause, until a HAL comes. The guest sets ro.boot.hardware=qcom on non-Qualcomm phones
for its zygote's libqti_performance preload (guest_props.sh), so that branch runs on
Exynos too. The Galaxy A16 5G and A17 5G (Exynos 1330) have no sound-trigger HAL at all
(no AIDL soundtrigger3 declared, no HIDL ISoundTriggerHw): the lookup threw
java.util.NoSuchElementException every ~2 ms on system_server's main thread, and the
Android Watchdog killed system_server after 60 s (0.4.60 reports db905397, c5714609,
97615a93, 551350e1: GUEST_DEAD at 110-280 s).

The catch now rethrows a NoSuchElementException (no such HAL on this phone: retrying
cannot help); SoundTriggerMiddlewareImpl.<init> catches it ("Failed to add a
SoundTriggerModule instance") and boot goes on without sound trigger, as AOSP's own
attachToHal does. Any other failure (a HAL that is declared but not up yet) is retried
as before.

Prints the smali_* directories it changed; nothing when the image has no such branch
(AOSP, Pixel). Fails if the branch is there but not in the form this was written for.

Usage: oplus_soundtrigger_no_hal.py <apktool decoded services.jar dir>
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "soundtrigger_middleware", "SoundTriggerModule.smali")
MSG = '"Failed to init SoundTriggerHal."'
MARK = "oplus_soundtrigger_no_hal"


def fail(msg):
    sys.exit("oplus_soundtrigger_no_hal: " + msg)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if not hits:
        return
    if len(hits) != 1:
        fail("SoundTriggerModule in %d dex dirs" % len(hits))
    d = hits[0]
    p = os.path.join(root, d, REL)
    t = open(p, encoding="utf-8").read()
    if MSG not in t:
        return  # AOSP's attachToHal: nothing retries
    if MARK in t:
        fail("already patched")
    ms = list(re.finditer(r"^\.method private attachToHal\(\)V\n(.*?)^\.end method\n", t, re.M | re.S))
    if len(ms) != 1:
        fail("attachToHal()V found %d times" % len(ms))
    body = ms[0].group(1)
    if body.count(MSG) != 1:
        fail("the retry message is in attachToHal %d times" % body.count(MSG))
    # move-exception vX / (.local, .line) / const-string vY, MSG / invoke-static {vT, vY, vX}, Log;->w(...)
    pat = re.compile(r"(^\s*move-exception (v\d+)\n(?:\s*\.local [^\n]*\n|\s*\.line \d+\n|\s*\n)*)(\s*const-string (v\d+), "
                     + re.escape(MSG) + r"\n)", re.M)
    mm = list(pat.finditer(body))
    if len(mm) != 1:
        fail("the catch with the retry message is not the code this was written for (%d matches)" % len(mm))
    m = mm[0]
    exc, tmp = m.group(2), m.group(4)
    if exc == tmp:
        fail("the exception and the message share a register")
    after = body[m.end():]
    if not re.match(r"(?:\s*\.line \d+\n|\s*\n)*\s*invoke-static \{\w+, %s, %s\}, Landroid/util/Log;->w\(" % (tmp, exc), after):
        fail("the retry message is not logged with the caught exception")
    ins = ("    # OneOS (patches/%s.py): no sound-trigger HAL on this phone (NoSuchElementException):\n"
           "    # give up, as AOSP does; SoundTriggerMiddlewareImpl catches it. Other failures retry.\n"
           "    instance-of %s, %s, Ljava/util/NoSuchElementException;\n\n"
           "    if-eqz %s, :%s_retry\n\n"
           "    throw %s\n\n"
           "    :%s_retry\n" % (MARK, tmp, exc, tmp, MARK, exc, MARK))
    body = body[:m.end(1)] + ins + body[m.end(1):]
    t = t[:ms[0].start(1)] + body + t[ms[0].end(1):]
    open(p, "w", encoding="utf-8").write(t)
    print("oplus_soundtrigger_no_hal: %s/%s: attachToHal gives up without a HAL" % (d, REL), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
