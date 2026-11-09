"""vivo's vendor HALs looked up without waiting (OriginOS on a Samsung vendor).

vivo's code waits (ServiceManager.waitForService / waitForDeclaredService) for HALs
only vivo's vendor partition has: vendor.vivo.hardware.vcode.IVcode (tenth CN run:
542 one-second waits in system_server; HalEventTransfer.connectToProxy holds its lock
while it waits, forever), vlight, sectee, ... and Unisoc's vendor.sprd ones. On a
Samsung vendor they never come: the calling thread blocks for good. Each such call
whose name is a literal "vendor.vivo." or "vendor.sprd." HAL becomes
ServiceManager.checkService (same signature: the binder, or null at once); every
caller already handles null (asInterface(null), null checks), as a wait that ends
without a service would give them.

Usage: vivo_no_wait.py <apktool decoded jar dir>
Prints the smali_* directories it changed (none when there is nothing to change).
"""
import os
import re
import sys

WAIT = re.compile(r"^(\s*)invoke-static \{([vp]\d+)\}, Landroid/os/ServiceManager;->(waitForService|waitForDeclaredService)"
                  r"\(Ljava/lang/String;\)Landroid/os/IBinder;$")
NAME = re.compile(r'^\s*const-string(?:/jumbo)? ([vp]\d+), "(vendor\.(?:vivo|sprd)\.[^"]+)"$')
SKIP = re.compile(r"^\s*(\.line \d+|\.local .*|\.end local .*)?\s*$")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    dirs, names = set(), {}
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if not f.endswith(".smali"):
                    continue
                p = os.path.join(dp, f)
                lines = open(p).read().split("\n")
                changed = False
                for i, l in enumerate(lines):
                    m = WAIT.match(l)
                    if not m:
                        continue
                    # The register's value: the nearest earlier instruction writing it.
                    j = i - 1
                    while j >= 0 and SKIP.match(lines[j]):
                        j -= 1
                    n = NAME.match(lines[j]) if j >= 0 else None
                    if not n or n.group(1) != m.group(2):
                        continue
                    lines[i] = (f"{m.group(1)}# OneOS (patches/vivo_no_wait.py): {n.group(2)} is vivo's vendor's; no wait on a Samsung vendor.\n"
                                f"{m.group(1)}invoke-static {{{m.group(2)}}}, Landroid/os/ServiceManager;->checkService(Ljava/lang/String;)Landroid/os/IBinder;")
                    names[n.group(2)] = names.get(n.group(2), 0) + 1
                    changed = True
                if changed:
                    open(p, "w").write("\n".join(lines))
                    dirs.add(d)
    if names:
        print("vivo_no_wait: " + ", ".join(f"{k} x{v}" for k, v in sorted(names.items())), file=sys.stderr)
    print("\n".join(sorted(dirs)))


if __name__ == "__main__":
    main()
