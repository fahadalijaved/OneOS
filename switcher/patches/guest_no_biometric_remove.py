"""Never let the guest delete a fingerprint or face from the phone's sensors by hand.

0.5.18 (owner: fingerprint unlock in the guest from One UI's own enrolments). The guest reaches the phone's
fingerprint and face HALs, and guest_prepare.sh copies One UI's enrolment lists (names and ids only) into the
guest, so its Settings lists One UI's fingerprints. "Delete" there would schedule a RemovalClient whose
startHalOperation() asks the phone's HAL to remove the template from the secure side: One UI's fingerprint
would be gone too. guest_no_biometric_cleanup.py stops the automatic removal at start; this stops the
user-driven one.

Every *RemovalClient.startHalOperation()V under com/android/server/biometrics/sensors (fingerprint and face,
AIDL and HIDL) finishes the client as unsuccessful before it reaches the HAL and logs why. Nothing is removed;
the guest's list is copied again from One UI at the next switch. Exits non-zero when no removal client is
found (an unexpected build), so a set is never built without the guard.

Usage: guest_no_biometric_remove.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

BASE = "Lcom/android/server/biometrics/sensors/BaseClientMonitor;"
CB = "Lcom/android/server/biometrics/sensors/ClientMonitorCallback;"
HEADER = re.compile(r"^\.method (?:(?:public|protected|private|final) )*startHalOperation\(\)V$")
NAME = re.compile(r"(Fingerprint|Face)RemovalClient\.smali$")


def class_of(lines):
    for l in lines:
        if l.startswith(".class "):
            return l.split()[-1]
    return None


def main(root):
    paths = sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
                   if NAME.search(f) and (os.sep + os.path.join("com", "android", "server", "biometrics", "sensors") + os.sep) in os.path.join(d, f))
    if not paths:
        sys.exit("no Fingerprint/FaceRemovalClient.smali found: unexpected build")
    changed = set()
    done = 0
    for path in paths:
        lines = open(path).read().split("\n")
        cls = class_of(lines)
        heads = [i for i, l in enumerate(lines) if HEADER.match(l)]
        if len(heads) != 1 or cls is None:
            sys.exit(f"{path}: startHalOperation() found {len(heads)} times, expected once")
        # mCallback is BaseClientMonitor's; a build may name it through the subclass (R8): use what it uses.
        text = "\n".join(lines)
        family = "\n".join(open(os.path.join(os.path.dirname(path), f)).read() for f in os.listdir(os.path.dirname(path))
                           if f.startswith(os.path.basename(path)[:-6]))
        owner = next((c for c in (BASE, cls) if f"{c}->mCallback:{CB}" in family or f"{c}->mCallback:{CB}" in text), BASE)
        i = heads[0]
        m = re.match(r"\s*\.(locals|registers) (\d+)$", lines[i + 1])
        if not m:
            sys.exit(f"{path}: unexpected startHalOperation header")
        if m.group(1) == "locals" and int(m.group(2)) < 2:
            lines[i + 1] = "    .locals 2"
        j = i + 2
        while lines[j].strip() == "" or lines[j].lstrip().startswith((".param", ".end param", ".annotation", ".end annotation")):
            j += 1
        lines[j:j] = [
            "    # OneOS: the sensors are the phone's; a fingerprint or face listed here is One UI's. Never removed.",
            '    const-string v0, "BiometricsRemoval"',
            "",
            '    const-string v1, "OneOS: removal refused: the phone\'s sensor holds One UI\'s enrolment"',
            "",
            "    invoke-static {v0, v1}, Landroid/util/Slog;->w(Ljava/lang/String;Ljava/lang/String;)I",
            "",
            f"    iget-object v0, p0, {owner}->mCallback:{CB}",
            "",
            "    const/4 v1, 0x0",
            "",
            f"    invoke-interface {{v0, p0, v1}}, {CB}->onClientFinished({BASE}Z)V",
            "",
            "    return-void",
            "",
        ]
        open(path, "w").write("\n".join(lines))
        changed.add(os.path.relpath(path, root).split(os.sep)[0])
        done += 1
        print(f"{cls} startHalOperation: removes nothing", file=sys.stderr)
    for c in sorted(changed):
        print(c)


if __name__ == "__main__":
    main(sys.argv[1])
