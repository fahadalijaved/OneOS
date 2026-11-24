#!/usr/bin/env python3
"""One UI 9.5 on One UI 8 (set oneui95-a16 r6, oneui8test12): a boot phase that only trips Android 17's attribution check.

On a One UI 8 phone the guest keeps One UI's Android 16 tethering module and takes the image's Android 17
Bluetooth module. At boot phase 1000 the module's NearbyService (ConnectivityServiceInitializer.onBootPhase)
turns BLE scanning on from system_server's own context (DiscoveryProviderManagerLegacy.setBleScanEnabled ->
BluetoothAdapter.enableBLE); Android 17's Bluetooth service refuses a system caller without an attribution
tag ("Missing attribution tag for system component", ServerBinder.getCallerIdentity), and SystemServiceManager
turned that into "Failed to boot service" and a dead system_server (S22 Ultra 64adde45 and be9fe22e). Both of its
boot-phase catches (the direct one in startBootPhase and the init thread pool's lambda) now log and go on when
that is the exception (anywhere in its cause chain); every other exception is thrown as before.

    a16_boot_phase_attribution.py <decoded services.jar dir>   -> prints the smali dirs it changed
"""
import os
import sys

GUARD_REL = "com/android/server/OneOSBootPhaseGuard.smali"
GUARD = """.class public final Lcom/android/server/OneOSBootPhaseGuard;
.super Ljava/lang/Object;
.source "OneOS a16_boot_phase_attribution"


# direct methods
.method public static ignorable(Ljava/lang/Throwable;)Z
    .registers 4

    move-object v0, p0

    :loop
    if-eqz v0, :no

    instance-of v1, v0, Ljava/lang/IllegalArgumentException;

    if-eqz v1, :next

    invoke-virtual {v0}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;

    move-result-object v1

    if-eqz v1, :next

    const-string v2, "Missing attribution tag for system component"

    invoke-virtual {v1, v2}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v1

    if-eqz v1, :next

    const-string v1, "OneOS"

    const-string v2, "onBootPhase: an Android 16 module called an Android 17 service without an attribution tag; ignored (One UI 9.5 on One UI 8)"

    invoke-static {v1, v2, p0}, Landroid/util/Slog;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    const/4 v1, 0x1

    return v1

    :next
    invoke-virtual {v0}, Ljava/lang/Throwable;->getCause()Ljava/lang/Throwable;

    move-result-object v0

    goto :loop

    :no
    const/4 v1, 0x0

    return v1
.end method
"""

SSM_REL = "com/android/server/SystemServiceManager.smali"
SSM_OLD = """    :catch_0
    move-exception p2

    const-string v0, "ISRB_BOOT"
"""
SSM_NEW = """    :catch_0
    move-exception p2

    invoke-static {p2}, Lcom/android/server/OneOSBootPhaseGuard;->ignorable(Ljava/lang/Throwable;)Z

    move-result v0

    if-eqz v0, :oneos_bpg_sync

    invoke-virtual {p1}, Landroid/util/TimingsTraceLog;->traceEnd()V

    iget p2, p0, Lcom/android/server/SystemServiceManager;->mCurrentPhase:I

    goto :goto_3

    :oneos_bpg_sync
    const-string v0, "ISRB_BOOT"
"""
LAMBDA_REL = "com/android/server/SystemServiceManager$$ExternalSyntheticLambda2.smali"
LAMBDA_OLD = """    :catch_0
    move-exception v1

    new-instance v2, Ljava/lang/RuntimeException;
"""
LAMBDA_NEW = """    :catch_0
    move-exception v1

    invoke-static {v1}, Lcom/android/server/OneOSBootPhaseGuard;->ignorable(Ljava/lang/Throwable;)Z

    move-result v2

    if-eqz v2, :oneos_bpg_async

    return-void

    :oneos_bpg_async
    new-instance v2, Ljava/lang/RuntimeException;
"""


def find(root, rel):
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, rel))]
    if len(hits) != 1:
        sys.exit(f"a16_boot_phase_attribution: {rel} in {hits}")
    return hits[0]


def patch(root, rel, old, new, must):
    d = find(root, rel)
    p = os.path.join(root, d, rel)
    s = open(p).read()
    if "OneOSBootPhaseGuard" in s:
        sys.exit(f"a16_boot_phase_attribution: {rel} already patched")
    if s.count(old) != 1 or must not in s:
        sys.exit(f"a16_boot_phase_attribution: {rel}: the catch is not in the expected form ({s.count(old)} matches)")
    open(p, "w").write(s.replace(old, new))
    return d


def main():
    root = sys.argv[1]
    dirs = {patch(root, SSM_REL, SSM_OLD, SSM_NEW, ".method public final startBootPhase("),
            patch(root, LAMBDA_REL, LAMBDA_OLD, LAMBDA_NEW, "SystemService;->onBootPhase(I)V")}
    home = find(root, SSM_REL)
    gp = os.path.join(root, home, GUARD_REL)
    if os.path.exists(gp):
        sys.exit("a16_boot_phase_attribution: OneOSBootPhaseGuard already there")
    with open(gp, "w") as f:
        f.write(GUARD)
    dirs.add(home)
    print("\n".join(sorted(dirs)))


if __name__ == "__main__":
    main()
