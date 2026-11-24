#!/usr/bin/env python3
"""One UI 9.5 on One UI 8 (set oneui95-a16 r5, oneui8test11): an empty android.net.ConnectivityCallListenerService.

The image's framework-res.apk declares that class as an InCallService of the system package ("android"),
and Telecom binds every InCallService when a call starts. The class is Android 17's connectivity module's
(framework-connectivity); on a One UI 8 phone the guest keeps One UI's Android 16 module, which has no such
class: at the S22's first call (oneui8test10 40176409) system_server died in handleCreateService
("Didn't find class android.net.ConnectivityCallListenerService"), the guest went down and the phone hung.
Here the class exists in services.jar (on system_server's class path) as a plain InCallService that does
nothing; the call itself goes on as before. Fail-closed: the jar must be services.jar and must not have it.

    a16_call_listener_stub.py <decoded services.jar dir>   -> prints the smali dir it changed
"""
import os
import sys

REL = "android/net/ConnectivityCallListenerService.smali"
SMALI = """.class public Landroid/net/ConnectivityCallListenerService;
.super Landroid/telecom/InCallService;
.source "OneOS a16_call_listener_stub"


# direct methods
.method public constructor <init>()V
    .registers 1

    invoke-direct {p0}, Landroid/telecom/InCallService;-><init>()V

    return-void
.end method
"""


def main():
    root = sys.argv[1]
    dirs = sorted(d for d in os.listdir(root) if d.startswith("smali"))
    home = [d for d in dirs if os.path.isfile(os.path.join(root, d, "com/android/server/SystemServer.smali"))]
    if len(home) != 1:
        sys.exit(f"a16_call_listener_stub: {root} is not services.jar ({home})")
    if any(os.path.exists(os.path.join(root, d, REL)) for d in dirs):
        sys.exit("a16_call_listener_stub: ConnectivityCallListenerService already in the jar")
    path = os.path.join(root, home[0], REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(SMALI)
    print(home[0])


if __name__ == "__main__":
    main()
