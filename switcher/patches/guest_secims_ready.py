#!/usr/bin/env python3
"""Samsung IMS hears that telephony is ready for a call's callbacks once telephony attaches to it.

Samsung's VoLTE app (com.sec.imsservice, in the guest when ONEOS_GUEST_SEC_IMS=1) keeps a call
session's onEnded and onError until telephony says it is ready for them
(ImsCallSessionEventListener.needSkipUntilTelephonyReady: "Telephony not ready to handle ims
callbacks. Postpone onEnded()"). One UI's telephony says so through Samsung's
ImsCallSessionImpl.notifyReadyToHandleImsCallbacks(); a guest's telephony has no such call, so
the end of a call never reached it: on the Z Fold8 with the Pixel 11 Fold build (Spectrum,
report 4bb83bcd) a declined call went on ringing in the Phone app, every further decline timed
out ("VerifyCallStateChangeTransaction timeout"), and no other call could be placed.

Telephony attaches to a session through IImsCallSession.setListener (ImsCall.attachSession for
incoming calls, ImsCall.start for outgoing ones). In the guest framework's
com.android.ims.internal.IImsCallSession$Stub.onTransact, right after the setListener call, the
session's own public notifyReadyToHandleImsCallbacks() is called by reflection when the
session's class has one (only Samsung's does); anything that goes wrong there is caught and the
transaction goes on as before. No Samsung code is copied; nothing changes for other IMS apps.

Fail closed: onTransact must call setListener exactly once, followed by the reply's
writeNoException(), with three scratch registers (v1-v3, or three added locals when onTransact
has fewer than four) that neither the reply nor the method's return uses; otherwise nothing is written.

Usage: guest_secims_ready.py <apktool decoded framework.jar dir>
Prints the smali_* directory it changed (nothing when the class is absent).
"""
import os
import re
import sys

REL = os.path.join("com", "android", "ims", "internal", "IImsCallSession$Stub.smali")
STUB = "Lcom/android/ims/internal/IImsCallSession$Stub;"
MARK = "oneos_secims_ready"


def fail(msg):
    sys.exit("guest_secims_ready: " + msg)


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, REL))]
    if not hits:
        print("guest_secims_ready: no IImsCallSession$Stub; unchanged", file=sys.stderr)
        return
    if len(hits) != 1:
        fail("IImsCallSession$Stub in %d dex dirs" % len(hits))
    d = hits[0]
    p = os.path.join(root, d, REL)
    t = open(p, encoding="utf-8").read()
    if MARK in t:
        fail("already patched")
    ms = [m for m in re.finditer(r"^\.method ([^\n]*) onTransact\(ILandroid/os/Parcel;Landroid/os/Parcel;I\)Z\n(.*?)^\.end method\n",
                                 t, re.M | re.S)]
    if len(ms) != 1:
        fail("onTransact found %d times" % len(ms))
    m = ms[0]
    body = m.group(2)
    loc = re.search(r"^\s*\.locals (\d+)$", body, re.M)
    if not loc:
        fail("onTransact has no .locals")
    nloc = int(loc.group(1))
    # Scratch registers: v1-v3 where the method has them (dead after setListener), else three
    # new locals after the method's own (R8 builds such as Infinity-X keep onTransact small).
    regs = ("v1", "v2", "v3") if nloc >= 4 else tuple("v%d" % (nloc + i) for i in range(3))
    if nloc < 4 and nloc + 3 + 5 > 16:
        fail("no room for three more registers in onTransact")
    call = re.compile(r"^(\s*)invoke-virtual \{p0, (\w+)\}, " + re.escape(STUB)
                      + r"->setListener\(Landroid/telephony/ims/aidl/IImsCallSessionListener;\)V\n"
                      r"((?:\s*\.line \d+\n|\s*\n)*)"
                      r"(\s*invoke-virtual \{(\w+)\}, Landroid/os/Parcel;->writeNoException\(\)V\n"
                      r"(?:\s*\.line \d+\n|\s*\n)*\s*goto(?:/16|/32)? :(\w+)\n)", re.M)
    c = list(call.finditer(body))
    if len(c) != 1:
        fail("setListener + writeNoException found %d times in onTransact" % len(c))
    c = c[0]
    scratch = set(regs)
    if c.group(5) in scratch:
        fail("the reply parcel is in a scratch register")
    ret = re.search(r"^\s*:" + re.escape(c.group(6)) + r"\n(?:\s*\.line \d+\n|\s*\n)*\s*return (\w+)\n", body, re.M)
    if not ret or ret.group(1) in scratch:
        fail("the transaction's return register is not known or is a scratch register")
    ind = c.group(1)
    r1, r2, r3 = regs
    hook = (f"{ind}# OneOS (patches/guest_secims_ready.py): telephony attached to the session; Samsung IMS\n"
            f"{ind}# keeps onEnded/onError until it hears so (notifyReadyToHandleImsCallbacks, Samsung's only).\n"
            f"{ind}:{MARK}_start\n"
            f"{ind}invoke-virtual {{p0}}, Ljava/lang/Object;->getClass()Ljava/lang/Class;\n"
            f"{ind}move-result-object {r1}\n"
            f"{ind}const-string {r2}, \"notifyReadyToHandleImsCallbacks\"\n"
            f"{ind}const/4 {r3}, 0x0\n"
            f"{ind}new-array {r3}, {r3}, [Ljava/lang/Class;\n"
            f"{ind}invoke-virtual {{{r1}, {r2}, {r3}}}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;\n"
            f"{ind}move-result-object {r1}\n"
            f"{ind}const/4 {r3}, 0x0\n"
            f"{ind}new-array {r3}, {r3}, [Ljava/lang/Object;\n"
            f"{ind}invoke-virtual {{{r1}, p0, {r3}}}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;\n"
            f"{ind}:{MARK}_end\n"
            f"{ind}.catch Ljava/lang/Throwable; {{:{MARK}_start .. :{MARK}_end}} :{MARK}_after\n"
            f"{ind}:{MARK}_after\n")
    pos = c.start(4)
    body2 = body[:pos] + hook + body[pos:]
    if nloc < 4:
        body2 = body2[:loc.start()] + loc.group(0).replace(".locals %d" % nloc, ".locals %d" % (nloc + 3)) + body2[loc.end():]
    t = t[:m.start(2)] + body2 + t[m.end(2):]
    open(p, "w", encoding="utf-8").write(t)
    print("guest_secims_ready: %s/%s: setListener tells the session telephony is ready" % (d, REL), file=sys.stderr)
    print(d)


if __name__ == "__main__":
    main()
