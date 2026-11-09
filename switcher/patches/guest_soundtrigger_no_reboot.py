"""A sound-trigger HAL that refuses a model is not rebooted (the guest's audio stays up).

SoundTriggerHalEnforcer.handleException reboots the sound-trigger HAL for any exception
that is neither a RecoverableException nor a dead HAL. On a Galaxy the sound-trigger HAL
lives in One UI's audio HAL process: Pixel's Now Playing (com.google.android.as) loads a
generic model Samsung's HAL refuses ("loadSoundModel ... status -22", a
ServiceSpecificException INTERNAL_ERROR), system_server rebooted the HAL, the audio HAL
process died ("HAL instance died, audio server is restarting") and took the guest's
audioserver with it, and Now Playing loaded the model again after each restart: 13 HAL
reboots in 9 minutes on an S25 Ultra (Pixel 9 Pro XL, 0.4.62 299c4a01), every video
recording fell in an audio outage ("AudioSystem could not query the input buffer size",
MediaRecorder prepare failed, "Error saving the recording (-11)").

A ServiceSpecificException (the HAL's own answer: it is alive) is now thrown on without
the reboot, so that one model fails to load and nothing else; a dead HAL and any other
exception are handled as before.

Prints the smali_* directory it changed; nothing when the class is not there. Fails if
the method is there but not in the form this was written for.

Usage: guest_soundtrigger_no_reboot.py <apktool decoded services.jar dir>
"""
import os
import re
import sys

REL = os.path.join("com", "android", "server", "soundtrigger_middleware", "SoundTriggerHalEnforcer.smali")
MSG = '"Exception caught from HAL, rebooting HAL"'
MARK = "oneos_st_no_reboot"


def fail(msg):
    sys.exit("guest_soundtrigger_no_reboot: " + msg)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if not hits:
        return
    if len(hits) != 1:
        fail("SoundTriggerHalEnforcer in %d dex dirs" % len(hits))
    d = hits[0]
    p = os.path.join(root, d, REL)
    t = open(p, encoding="utf-8").read()
    if MARK in t:
        fail("already patched")
    ms = [m for m in re.finditer(r"^\.method (?:public |private |protected )?(?:final )?handleException\(Ljava/lang/RuntimeException;\)Ljava/lang/RuntimeException;\n(.*?)^\.end method\n",
                                 t, re.M | re.S)]
    if len(ms) != 1:
        fail("handleException found %d times" % len(ms))
    m = ms[0]
    body = m.group(1)
    if body.count(MSG) != 1 or body.count("->reboot()V") != 1:
        fail("handleException is not the code this was written for")
    # const-string vX, MSG ... invoke Slog.e ... invoke-virtual {p0}, ...->reboot()V ... throw p1
    cm = re.search(r"^(\s*)const-string (v\d+), " + re.escape(MSG) + r"$", body, re.M)
    tm = re.search(r"->reboot\(\)V\n(?:\s*\.line \d+\n|\s*\n)*\s*throw (p1)\n", body)
    if not cm or not tm:
        fail("no message register or no throw of the caught exception after the reboot")
    ind, reg = cm.group(1), cm.group(2)
    ins = (f"{ind}# OneOS (patches/guest_soundtrigger_no_reboot.py): the HAL answered (a refused model):\n"
           f"{ind}# no reboot, the audio HAL process (One UI's) stays up.\n"
           f"{ind}instance-of {reg}, p1, Landroid/os/ServiceSpecificException;\n\n"
           f"{ind}if-eqz {reg}, :{MARK}_reboot\n\n"
           f"{ind}throw p1\n\n"
           f"{ind}:{MARK}_reboot\n")
    body = body[:cm.start()] + ins + body[cm.start():]
    t = t[:m.start(1)] + body + t[m.end(1):]
    open(p, "w", encoding="utf-8").write(t)
    print("guest_soundtrigger_no_reboot: %s/%s: no HAL reboot for a refused request" % (d, REL), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
