"""Keep the guest's StorageManagerService away from the host vold's user keys.

The container shares the host's binder services, so the guest framework's
"vold" is the host's: the one holding the keys of One UI's real users. When
ColorOS's LockSettingsService set up its synthetic password it called
setCeStorageProtection() for user 0 (it failed; had it succeeded, One UI's
user 0 CE key would have been protected with a secret One UI does not know).
The guest's users live in its own staged /data and need no vold keys, so
drop every key-management call; the surrounding Java code carries on as if
they succeeded. Pixel's services.jar also has the AIDL classes themselves
(IVold$Stub.onTransact dispatches to a local implementation, which the guest
never is); they are left alone.

Usage: guest_no_vold_keys.py <smali root dir>
Prints the smali_* directories (dex files) it changed, one per line.
"""
import os
import re
import sys

CALLS = re.compile(
    r"^\s*invoke-interface \{[^}]*\}, Landroid/os/IVold;->"
    r"(createUserStorageKeys|destroyUserStorageKeys|setCeStorageProtection|"
    r"unlockCeStorage|lockCeStorage)\([^)]*\)V\s*$"
)
# One UI 9.5 (S948BXXU6ZZKN): Samsung's "keep storage" key calls, the same kind as
# setCeStorageProtection / unlockCeStorage / lockCeStorage (LockSettingsService,
# TrustManagerService). A dropped call is followed by a nop: TrustManagerService's is the
# only instruction of its try block.
KEEP_CALLS = re.compile(
    r"^\s*invoke-interface \{[^}]*\}, Landroid/os/IVold;->"
    r"(lockKeepKeyStorage|setKeepKeyStorageProtection|unlockKeepKeyStorage)\([^)]*\)V\s*$"
)


def main(root):
    changed_dirs = set()
    removed = 0
    names = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            if os.path.relpath(path, root).split(os.sep, 1)[-1].startswith(os.path.join("android", "os", "IVold")):
                continue  # the AIDL classes themselves
            with open(path) as f:
                lines = f.read().split("\n")
            out = []
            dirty = False
            for line in lines:
                k = KEEP_CALLS.match(line)
                if k:
                    out.append(f"    # OneOS: IVold.{k.group(1)} dropped (host vold holds One UI's keys)\n    nop")
                    dirty = True
                    removed += 1
                    names[k.group(1)] = names.get(k.group(1), 0) + 1
                    print(f"{os.path.relpath(path, root)}: {k.group(1)}", file=sys.stderr)
                    continue
                m = CALLS.match(line)
                if m:
                    out.append(f"    # OneOS: IVold.{m.group(1)} dropped (host vold holds One UI's keys)")
                    dirty = True
                    removed += 1
                    names[m.group(1)] = names.get(m.group(1), 0) + 1
                    print(f"{os.path.relpath(path, root)}: {m.group(1)}", file=sys.stderr)
                else:
                    out.append(line)
            if dirty:
                with open(path, "w") as f:
                    f.write("\n".join(out))
                changed_dirs.add(os.path.relpath(path, root).split(os.sep)[0])
    # One UI 9.5 (S948BXXU6ZZKN): StorageManagerService.lockCeStorage calls
    # IVold.lockCeStorage itself, a sixth call (it would lock One UI's user CE key);
    # the other five are as before, plus Samsung's four keep-storage key calls
    # (KEEP_CALLS). Any other count stops.
    ONEUI85 = {"createUserStorageKeys": 1, "destroyUserStorageKeys": 1,
               "setCeStorageProtection": 2, "unlockCeStorage": 1, "lockCeStorage": 1}
    ONEUI95 = {"createUserStorageKeys": 1, "destroyUserStorageKeys": 1,
               "setCeStorageProtection": 2, "unlockCeStorage": 1, "lockCeStorage": 1,
               "lockKeepKeyStorage": 2, "setKeepKeyStorageProtection": 1, "unlockKeepKeyStorage": 1}
    if removed != 5 and names not in (ONEUI85, ONEUI95):
        sys.exit(f"expected 5 IVold key calls, found {removed}")
    for d in sorted(changed_dirs):
        print(d)


if __name__ == "__main__":
    main(sys.argv[1])
