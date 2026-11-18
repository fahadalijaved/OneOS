"""A One UI guest never starts KnoxGuard 3.0 (knoxguard_service).

One UI 9.5's SystemServer starts com.samsung.android.knoxguard30.service.KnoxGuard30Service
unless FactoryTest.isFactoryBinary(). In a guest it cannot reach the phone's KnoxGuard TA (One UI's,
kept out of reach on purpose), read that as a fault, and locked the guest's screen: first "Device
locked ... 1100FF02" through the KnoxGuard app, then, with that app hidden, "Security issue
detected ... 8135" from the service itself, asking to turn on mobile data to report to Samsung's
server (A36 runs 9 and 10). The factory-build branch is taken always: the service is not created
or registered, which is the state Samsung's own factory builds run in.

Usage: samsung_no_knoxguard30.py <smali root of services.jar>
Prints the smali_* directory it changed; nothing when the build has no KnoxGuard 3.0.
"""
import os
import re
import sys

PAT = re.compile(
    r"(    invoke-static \{\}, Landroid/os/FactoryTest;->isFactoryBinary\(\)Z\n\n    move-result (v\d+)\n\n)"
    r"    if-nez \2, (:cond_\w+)\n(\n    const-string(?:/jumbo)? \2, \"StartKnoxGuard\"\n)")


def main(root):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + os.path.join("com", "android", "server", "SystemServer.smali"))]
    if len(hits) != 1:
        sys.exit(f"SystemServer.smali: {len(hits)} found")
    text = open(hits[0]).read()
    if "Lcom/samsung/android/knoxguard30/service/KnoxGuard30Service;-><init>" not in text:
        print("KnoxGuard 3.0: not in this build", file=sys.stderr)
        return
    if "OneOS: KnoxGuard 3.0 not started" in text:
        print("KnoxGuard 3.0: already patched", file=sys.stderr)
        return
    found = PAT.findall(text)
    if len(found) != 1:
        sys.exit(f"KnoxGuard 3.0: the factory-build check before StartKnoxGuard found {len(found)} times (one expected)")
    text = PAT.sub(lambda m: m.group(1) + "    # OneOS: KnoxGuard 3.0 not started in a guest (as on a factory build)\n"
                   + f"    goto {m.group(3)}\n" + m.group(4), text)
    open(hits[0], "w").write(text)
    print("KnoxGuard 3.0: knoxguard_service not started (factory-build branch always)", file=sys.stderr)
    print(os.path.relpath(hits[0], root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
