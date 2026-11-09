"""Check that an image's telephony-common.jar fits oneos-telephony.jar.

Run 43 (Pixel 17 guest): Samsung's RIL sent the guest no
currentSignalStrength indication, and AOSP's SignalStrengthController polls
only for opportunistic subscriptions, so both SIMs kept the all-invalid value
read right after RADIO_POWER on (level 0 for the whole session). The fix is
not a patch of this jar (it is on the boot class path and in the boot image):
TeleService's own TelephonyComponentFactory injection, with an RRO naming
oneos.telephony.OneOSTelephonyComponentFactory in
/system_ext/framework/oneos-telephony.jar for the one component
SignalStrengthController. That factory returns the image's controller and
starts OneOSSignalPoll on it, which sends the controller its
EVENT_POLL_SIGNAL_STRENGTH (7) every 20 s (OneOSTelephonyComponentFactory.smali,
OneOSSignalPollAosp.smali).

There is no ART verifier here, so before scripts/make-overlays.sh builds the
jar, check every assumption it makes about this image:
- TelephonyComponentFactory is public and not final, with a public no-arg
  constructor and a public, non-final, non-static makeSignalStrengthController(GsmCdmaPhone);
- GsmCdmaPhone extends Phone and gets its controller through
  inject(SignalStrengthController.class.getName()).makeSignalStrengthController(this),
  kept in the field its getSignalStrengthController() returns (the poll stops
  when that is not the controller it started on);
- InjectedComponents accepts a jar under /system_ext/ (statvfs read-only check)
  and loads it with a PathClassLoader;
- SignalStrengthController extends Handler; in handleMessage, what=7 asks
  CommandsInterface.getSignalStrength(obtainMessage(9)), and what=9 takes the
  same path as what=6 (radio on -> onSignalStrengthResult);
- the members OneOSSignalPoll uses: Phone.mCi, Phone.getContext(),
  Phone.getSignalStrengthController(), CommandsInterface.getRadioState()I.

Usage: aosp_signal_poll_check.py <apktool -r dir of telephony-common.jar>
Exits non-zero with the reason when anything does not hold.
"""
import os
import re
import sys

PKG = "com/android/internal/telephony/"
T = "Lcom/android/internal/telephony/"
REG = r"[vp]\d+"


def find(root, name):
    rel = os.path.join(*PKG.rstrip("/").split("/"), name)
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + rel)]
    if len(hits) != 1:
        sys.exit(f"expected exactly one {rel}, found {len(hits)}")
    return open(hits[0]).read()


def flags(decl):
    """Access and hidden-API words of a .class/.method/.field line, before the name."""
    return decl.split()[1:-1]


def member(smali, kind, name, what):
    """The one .method/.field line declaring name (with its descriptor)."""
    lines = [l for l in smali.split("\n") if l.startswith(kind + " ") and l.split()[-1] == name]
    if len(lines) != 1:
        sys.exit(f"{what}: expected one declaration of {name}, found {len(lines)}")
    return lines[0]


def need_public(decl, what, static=False):
    f = flags(decl)
    if "public" not in f or "final" in f or ("static" in f) != static:
        sys.exit(f"{what}: not a public{' static' if static else ''} non-final member: {decl.strip()}")


def method_body(smali, name, what):
    decl = member(smali, ".method", name, what)
    start = smali.index(decl + "\n")
    return smali[start:smali.index("\n.end method", start)]


def check_factory(root):
    smali = find(root, "TelephonyComponentFactory.smali")
    cls = smali.split("\n", 1)[0]
    if not cls.startswith(".class ") or "public" not in flags(cls) or "final" in flags(cls) or "abstract" in flags(cls):
        sys.exit(f"TelephonyComponentFactory is not a public, non-final class: {cls}")
    need_public(member(smali, ".method", "<init>()V", "TelephonyComponentFactory"), "TelephonyComponentFactory.<init>()")
    need_public(member(smali, ".method",
                       f"makeSignalStrengthController({T}GsmCdmaPhone;){T}SignalStrengthController;",
                       "TelephonyComponentFactory"), "TelephonyComponentFactory.makeSignalStrengthController")


def check_phone(root):
    gsm = find(root, "GsmCdmaPhone.smali")
    if f"\n.super {T}Phone;\n" not in gsm:
        sys.exit("GsmCdmaPhone does not extend Phone")
    # const-class SignalStrengthController -> inject(name) -> makeSignalStrengthController(this),
    # with no other component in between, and the result kept in the field
    # getSignalStrengthController() returns: OneOSSignalPoll stops at its first
    # run when the phone's controller is not the one it was started on.
    m = re.search(r"\n\s*const-class " + REG + ", " + re.escape(T + "SignalStrengthController;") + r"\n"
                  r"((?:(?!\s*const-class ).*\n){0,30}?)"
                  r"\s*invoke-virtual \{" + REG + ", " + REG + r"\}, " + re.escape(T + "TelephonyComponentFactory;->inject(Ljava/lang/String;)") + r".*\n"
                  r"((?:(?!\s*const-class ).*\n){0,10}?)"
                  r"\s*invoke-virtual \{" + REG + r", p0\}, " + re.escape(
                      T + f"TelephonyComponentFactory;->makeSignalStrengthController({T}GsmCdmaPhone;){T}SignalStrengthController;") + r"\n"
                  r"(?:\s*\n)*\s*move-result-object (?P<r>" + REG + r")\n"
                  r"(?:\s*(?:\.line \d+)?\n)*\s*iput-object (?P=r), p0, (?P<f>" + T + r"(?:GsmCdma)?Phone;->\S+:"
                  + re.escape(T + "SignalStrengthController;") + r")\n",
                  gsm)
    if not m:
        sys.exit("GsmCdmaPhone: no inject(SignalStrengthController) -> makeSignalStrengthController(this) -> a field")
    getter = method_body(gsm, f"getSignalStrengthController(){T}SignalStrengthController;", "GsmCdmaPhone")
    if not re.search(r"\n\s*iget-object (?P<r>" + REG + r"), p0, " + re.escape(m.group("f")) + r"\n(?:\s*\n)*\s*return-object (?P=r)\n", getter + "\n"):
        sys.exit(f"GsmCdmaPhone.getSignalStrengthController() does not return {m.group('f')}")

    phone = find(root, "Phone.smali")
    need_public(member(phone, ".field", f"mCi:{T}CommandsInterface;", "Phone"), "Phone.mCi")
    need_public(member(phone, ".method", "getContext()Landroid/content/Context;", "Phone"), "Phone.getContext()")
    need_public(member(phone, ".method", f"getSignalStrengthController(){T}SignalStrengthController;", "Phone"),
                "Phone.getSignalStrengthController()")

    ci = find(root, "CommandsInterface.smali")
    if not ci.split("\n", 1)[0].startswith(".class public interface abstract "):
        sys.exit("CommandsInterface is not a public interface")
    member(ci, ".method", "getRadioState()I", "CommandsInterface")


def check_injection(root):
    smali = find(root, "TelephonyComponentFactory$InjectedComponents.smali")
    for what, pattern in (("a /system_ext/ jar path", r'const-string ' + REG + r', "/system_ext/"'),
                          ("the read-only (statvfs) check", re.escape("Landroid/system/Os;->statvfs(Ljava/lang/String;)")),
                          ("a PathClassLoader", r"new-instance " + REG + r", Ldalvik/system/PathClassLoader;")):
        if not re.search(pattern, smali):
            sys.exit(f"TelephonyComponentFactory$InjectedComponents: does not have {what}")


SSC = T + "SignalStrengthController;"
# The only calls vivo's what=7 tail may make (OriginOS 6 CN): reads, its log and
# its own re-poll. Anything else after the poll is refused.
VIVO_TAIL_CALLS = {
    SSC + "->getUiccCardApplication()" + T + "uicc/UiccCardApplication;",
    T + "Phone;->getServiceStateTracker()" + T + "ServiceStateTracker;",
    "Landroid/telephony/ServiceState;->getState()I",
    T + "Phone;->getPhoneId()I",
    "Ljava/lang/StringBuilder;-><init>()V",
    "Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;",
    "Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;",
    "Ljava/lang/StringBuilder;->toString()Ljava/lang/String;",
    SSC + "->log(Ljava/lang/String;)V",
    SSC + "->queueNextSignalStrengthPoll(Z)V",
}


def check_vivo_poll_tail(smali, tail, label):
    """vivo OriginOS 6 CN: after the AOSP poll, what=7 re-queues its own poll
    (queueNextSignalStrengthPoll) while the screen is on. OneOSSignalPoll's
    sendEmptyMessage(7) every 20 s must not start a second, third... chain:
    accept it only when the tail calls nothing but VIVO_TAIL_CALLS and ends in
    that re-poll, and the re-poll removes every pending what=7 before it queues
    one message with what=7, and never removes or posts callbacks
    (OneOSSignalPoll is a Runnable posted on this handler)."""
    calls = re.findall(r"^invoke-\S+ \{[^}]*\}, (\S+)$", tail, re.M)
    bad = [c for c in calls if c not in VIVO_TAIL_CALLS]
    if bad or not calls or calls[-1] != SSC + "->queueNextSignalStrengthPoll(Z)V":
        sys.exit(f"SignalStrengthController.handleMessage: what=7 ({label}) does more after the poll than "
                 f"vivo's re-poll ({', '.join(bad) or 'it does not end in queueNextSignalStrengthPoll'}):\n{tail}")
    q = method_body(smali, "queueNextSignalStrengthPoll(Z)V", "SignalStrengthController")
    q = "\n".join(l.strip() for l in q.split("\n") if l.strip() and not l.strip().startswith(".line")) + "\n"
    m = re.search(r"\nconst/4 (?P<w>" + REG + r"), 0x7\n"
                  r"invoke-virtual \{p0, (?P=w)\}, Landroid/os/Handler;->hasMessages\(I\)Z\n"
                  r"(?:.*\n){0,4}?"
                  r"invoke-virtual \{p0, (?P=w)\}, Landroid/os/Handler;->removeMessages\(I\)V\n"
                  r"(?::\S+\n)?"
                  r"invoke-virtual \{p0\}, Landroid/os/Handler;->obtainMessage\(\)Landroid/os/Message;\n"
                  r"move-result-object (?P<m>" + REG + r")\n"
                  r"iput (?P=w), (?P=m), Landroid/os/Message;->what:I\n", q)
    if not m:
        sys.exit("SignalStrengthController.queueNextSignalStrengthPoll: does not remove pending what=7 before queueing one")
    rest = q[m.end():]
    sends = re.findall(r"^invoke-virtual \{p0, (" + REG + r")[^}]*\}, Landroid/os/Handler;->(\w+)\(", rest, re.M)
    if (not sends or any(not n.startswith("sendMessage") or r != m.group("m") for r, n in sends)
            or re.search(r"removeCallbacks|->post", rest)
            or re.search(r"^(?:const\S* |move\S* |iput\S* \S+, )" + re.escape(m.group("m")) + r"\b", rest, re.M)):
        sys.exit("SignalStrengthController.queueNextSignalStrengthPoll: queues something other than the one what=7 message")


def check_controller(root):
    smali = find(root, "SignalStrengthController.smali")
    if "\n.super Landroid/os/Handler;\n" not in smali:
        sys.exit("SignalStrengthController does not extend Handler")
    body = method_body(smali, "handleMessage(Landroid/os/Message;)V", "SignalStrengthController")
    sw = re.findall(r"\n\s*packed-switch " + REG + r", (:\S+)\n", body)
    if len(sw) != 1:
        sys.exit(f"SignalStrengthController.handleMessage: expected one packed-switch, found {len(sw)}")
    m = re.search(r"\n\s*" + re.escape(sw[0]) + r"\n\s*\.packed-switch 0x1\n((?:\s*:\S+\n)+)\s*\.end packed-switch", body)
    if not m:
        sys.exit("SignalStrengthController.handleMessage: the switch does not start at what=1")
    labels = m.group(1).split()
    if len(labels) < 9:
        sys.exit(f"SignalStrengthController.handleMessage: only {len(labels)} cases")
    # The case labels in the code, not in the switch table at the end.
    code = body[:m.start()]

    def block(label, stop):
        """The instructions from label up to the first stop line (no .line, no blanks)."""
        start = re.search(r"\n\s*" + re.escape(label) + r"\n", code)
        if not start:
            sys.exit(f"SignalStrengthController.handleMessage: no {label}")
        out = []
        for line in code[start.end():].split("\n"):
            line = line.strip()
            if not line or line.startswith(".line"):
                continue
            if re.match(stop, line):
                break
            out.append(line)
        return "\n".join(out) + "\n"

    # what=7 starts with getSignalStrength(obtainMessage(9)), nothing before it
    # that could return or branch away. AOSP's case is only that; vivo's CN build
    # re-queues its own poll after it (check_vivo_poll_tail).
    poll = block(labels[6], r"(return-void|goto|:)")
    m7 = re.match(r"(?:iget-object " + REG + ", p0, " + re.escape(T) + r"\S+;->mCi:" + re.escape(T + "CommandsInterface;") + r"\n)?"
                  r"const/16 (?P<w>" + REG + r"), 0x9\n"
                  r"invoke-virtual \{p0, (?P=w)\}, L\S+;->obtainMessage\(I\)Landroid/os/Message;\n"
                  r"move-result-object " + REG + r"\n"
                  r"invoke-interface \{" + REG + ", " + REG + r"\}, "
                  + re.escape(T + "CommandsInterface;->getSignalStrength(Landroid/os/Message;)V") + r"\n", poll)
    if not m7:
        sys.exit(f"SignalStrengthController.handleMessage: what=7 ({labels[6]}) is not getSignalStrength(obtainMessage(9)):\n{poll}")
    if m7.end() != len(poll):
        check_vivo_poll_tail(smali, block(labels[6], r"return-void")[m7.end():], labels[6])
    if labels[8] != labels[5]:
        sys.exit(f"SignalStrengthController.handleMessage: what=9 ({labels[8]}) is not handled like what=6 ({labels[5]})")
    result = block(labels[8], r"return-void")
    if "CommandsInterface;->getRadioState()I" not in result or "->onSignalStrengthResult(" not in result:
        sys.exit(f"SignalStrengthController.handleMessage: what=9 ({labels[8]}) does not check the radio and call onSignalStrengthResult")


def main(root):
    check_factory(root)
    check_phone(root)
    check_injection(root)
    check_controller(root)
    print("telephony-common.jar: TelephonyComponentFactory injection, SignalStrengthController what=7/9 and "
          "the Phone members OneOSSignalPoll uses are as expected", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.rsplit("Usage: ", 1)[1])
    main(sys.argv[1])
