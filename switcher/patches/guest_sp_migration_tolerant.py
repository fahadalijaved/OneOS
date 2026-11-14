"""The guest's system_server survives a synthetic password it cannot create.

At boot, LockSettingsService.onThirdPartyAppsStarted() migrates every unsecured
user without a synthetic password (SP) to one: migrateUserToSpWithBoundKeysLocked
calls initializeSyntheticPassword, which imports a key into Keystore. The guest
shares One UI's keystore2; on a Galaxy S26 Ultra with LineageOS 24 (0.5.06,
report b5edb256) the import was refused ("Failed to import secret key", internal
Keystore code 4) and the RuntimeException it came wrapped in killed system_server
on every start: the session went back to One UI after 40 s. An unsecured user
without an SP is the legacy state Android still handles (that is why it migrates
it); the guest has no lock screen credential of its own (guest_no_gatekeeper).
So the call is wrapped: on a RuntimeException the guest logs it and goes on
without an SP; where the import works (Z Fold8 Ultra) nothing changes. Nothing
here touches One UI's keys.

Usage: guest_sp_migration_tolerant.py <smali root dir>
Prints the smali_* directory (dex file) it changed; nothing when the method is
not there (older builds).
"""
import os
import re
import sys

SIG = ".method public final migrateUserToSpWithBoundKeysLocked(I)V"
CALL = re.compile(
    r"^(    invoke-virtual \{(p0|v\d+), (p1|v\d+)\}, Lcom/android/server/locksettings/LockSettingsService;"
    r"->initializeSyntheticPassword\(I\)Lcom/android/server/locksettings/SyntheticPasswordManager\$SyntheticPassword;\n)"
    r"(\n)?"
    r"(    return-void\n)", re.M)


def main():
    root = sys.argv[1]
    suffix = os.path.join("com", "android", "server", "locksettings", "LockSettingsService.smali")
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + suffix)]
    if not hits:
        return
    if len(hits) != 1:
        sys.exit(f"expected one LockSettingsService.smali, found {len(hits)}")
    path = hits[0]
    smali = open(path).read()
    if ":oneos_sp_try_start" in smali:
        sys.exit("LockSettingsService already patched")
    start = smali.find(SIG)
    if start < 0:
        return
    end = smali.find(".end method", start)
    body = smali[start:end]
    m = re.search(r"^    \.locals (\d+)$", body, re.M)
    if not m or int(m.group(1)) < 3:
        sys.exit("migrateUserToSpWithBoundKeysLocked: unexpected locals")
    # v0 and v2 are free at the call (v1 holds the "LockSettingsService" tag, set above it).
    if 'const-string v1, "LockSettingsService"' not in body:
        sys.exit("migrateUserToSpWithBoundKeysLocked: no LockSettingsService tag in v1")
    found = CALL.findall(body)
    if len(found) != 1:
        sys.exit(f"migrateUserToSpWithBoundKeysLocked: expected one initializeSyntheticPassword call, found {len(found)}")
    body = CALL.sub(lambda mm: (
        "    :oneos_sp_try_start\n" + mm.group(1) + "    :oneos_sp_try_end\n"
        "    .catch Ljava/lang/RuntimeException; {:oneos_sp_try_start .. :oneos_sp_try_end} :oneos_sp_catch\n\n"
        + mm.group(5) +
        "\n    :oneos_sp_catch\n"
        "    move-exception v0\n\n"
        '    const-string v2, "OneOS: no synthetic password for this unsecured user (Keystore refused its key); the guest goes on without one"\n\n'
        "    invoke-static {v1, v2, v0}, Landroid/util/Slog;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I\n\n"
        "    return-void\n"), body, count=1)
    smali = smali[:start] + body + smali[end:]
    open(path, "w").write(smali)
    print("LockSettingsService: a refused synthetic password no longer stops system_server", file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    main()
