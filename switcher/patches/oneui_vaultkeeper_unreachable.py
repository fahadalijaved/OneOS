#!/usr/bin/env python3
"""One UI 9.5 set r6: VaultKeeperService off when the ISehVaultKeeper HAL is not there for the guest.

DmcService's onBootPhase(PHASE_BOOT_COMPLETED) calls VaultKeeperManager (destroy, write), which reaches
VaultKeeperService's native library, and lib vkjni waits for the AIDL HAL
vendor.samsung.hardware.security.vaultkeeper.ISehVaultKeeper/default with no time limit. In the guest
nothing serves that instance, so the boot phase never finished: SystemServer's boot-phase thread logged
"Waited one second for ...ISehVaultKeeper/default" every second after "DmcService$Lifecycle:
PHASE_BOOT_COMPLETED", ActivityManagerService.finishBooting waited on it, Samsung's setup wizard stayed
on SetupWizardPreActionActivity (11-19 reports e8527bc3, 9a0d3d37, 6e473bba: S23 family) and the
watchdog killed system_server after 68 s on the display thread (f82d7be8).

VaultKeeperService already has an unsupported state: mServiceSupport 0 (from nativeGetSystemSolution),
and every method that reaches the HAL checks it first and returns "VaultKeeper not support" at once.
The constructor gets a check after that assignment: when servicemanager has no such service right now
(ServiceManager.checkService, which neither waits nor starts a lazy service), mServiceSupport is 0.
Where the HAL is registered, nothing changes. Fail-closed: the assignment must be found exactly once.

    oneui_vaultkeeper_unreachable.py <services smali dir>   -> prints the smali dir it changed
"""
import os
import re
import sys

CLS = "com/android/server/VaultKeeperService.smali"
FIELD = "Lcom/android/server/VaultKeeperService;->mServiceSupport:I"
INSTANCE = "vendor.samsung.hardware.security.vaultkeeper.ISehVaultKeeper/default"
MARK = "    # OneOS: VaultKeeper unsupported without its HAL (oneui_vaultkeeper_unreachable.py)\n"
ASSIGN = re.compile(r"^    invoke-direct \{p0\}, Lcom/android/server/VaultKeeperService;->nativeGetSystemSolution\(\)I\n"
                    r"(?:\s*\.line \d+\n|\s*\n)*    move-result (v\d+)\n(?:\s*\.line \d+\n|\s*\n)*"
                    r"    iput \1, p0, " + re.escape(FIELD) + r"\n", re.M)


def main():
    root = sys.argv[1]
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if not hits:
        print("oneui_vaultkeeper_unreachable: not present", file=sys.stderr)
        return
    if len(hits) != 1:
        sys.exit(f"oneui_vaultkeeper_unreachable: {CLS} found in {hits}")
    path = os.path.join(root, hits[0], CLS)
    src = open(path).read()
    if MARK in src:
        print(hits[0])
        return
    found = list(ASSIGN.finditer(src))
    if len(found) != 1:
        sys.exit(f"oneui_vaultkeeper_unreachable: the mServiceSupport assignment found {len(found)} times")
    m = found[0]
    reg = m.group(1)
    add = (MARK +
           f"    const-string {reg}, \"{INSTANCE}\"\n\n"
           f"    invoke-static {{{reg}}}, Landroid/os/ServiceManager;->checkService(Ljava/lang/String;)Landroid/os/IBinder;\n\n"
           f"    move-result-object {reg}\n\n"
           f"    if-nez {reg}, :oneos_vk_hal_there\n\n"
           f"    const/4 {reg}, 0x0\n\n"
           f"    iput {reg}, p0, {FIELD}\n\n"
           f"    :oneos_vk_hal_there\n")
    src = src[:m.end()] + add + src[m.end():]
    with open(path, "w") as f:
        f.write(src)
    print(hits[0])


if __name__ == "__main__":
    main()
