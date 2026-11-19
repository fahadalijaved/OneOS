"""A One UI guest's IOemNetd calls with One UI's transaction codes.

com.android.internal.net.IOemNetd is Samsung's extension of netd (Knox firewall and VPN rules,
tethering, traffic stats). netd is One UI's process, shared with the guest. One UI 9.5
(S948BXXU6ZZKN) has 234 methods where One UI 9.0 has 212, numbered differently from code 13 on,
so the guest's calls reached other host methods: SemWifiTrafficPoller's startTrafficStatsController
came back as a NullPointerException and took system_server down (A36, run 8); a misrouted call
could as well have changed One UI's firewall.

In the guest's IOemNetd$Stub$Proxy (services.jar), the code each method passes to
IBinder.transact becomes:
  - the host's code, when the host table (host_oemnetd.txt, One UI's own proxy) has a method of
    the same name and signature;
  - UNUSED_CODE otherwise: netd answers "unknown transaction", runs nothing, and the caller reads
    an empty reply (default values).
Every method must have exactly one constant feeding its transact, or nothing is written.

Usage: guest_oemnetd_abi.py <smali root of services.jar> <host_oemnetd.txt>
Prints the smali_* directory it changed; nothing when the guest has no IOemNetd.
"""
import os
import re
import sys

PROXY = os.path.join("com", "android", "internal", "net", "IOemNetd$Stub$Proxy.smali")
UNUSED_CODE = 0xFFFFF0  # within FIRST..LAST_CALL_TRANSACTION, far above any IOemNetd method
TRANSACT = re.compile(r"^\s*invoke-interface \{[vp]\d+, ([vp]\d+), [vp]\d+, [vp]\d+, [vp]\d+\}, "
                      r"Landroid/os/IBinder;->transact\(ILandroid/os/Parcel;Landroid/os/Parcel;I\)Z\s*$")
CONST = r"^(\s*)const(?:/4|/16|/high16)? {reg}, (-?0x[0-9a-f]+|-?\d+)\s*$"


def main(root, table):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + PROXY)]
    if not hits:
        print("IOemNetd: not in this framework", file=sys.stderr)
        return
    if len(hits) != 1:
        sys.exit(f"IOemNetd: {len(hits)} proxies")
    host = {}
    for line in open(table):
        if line.startswith("#") or not line.strip():
            continue
        code, sig = line.split()
        host[sig] = int(code)
    path = hits[0]
    text = open(path).read()
    out, kept, moved, unused = [], 0, 0, 0
    parts = re.split(r"(?m)^(\.method [^\n]*\n)", text)
    out.append(parts[0])
    for i in range(1, len(parts), 2):
        header, body = parts[i], parts[i + 1]
        m = re.match(r"\.method [^\n]*?(\S+\([^)]*\)\S+)\n", header)
        sig = m.group(1)
        lines = body.split("\n")
        tx = [k for k, l in enumerate(lines) if TRANSACT.match(l)]
        if not tx:
            out += [header, body]
            continue
        if len(tx) != 1:
            sys.exit(f"IOemNetd.{sig}: {len(tx)} transact calls")
        reg = TRANSACT.match(lines[tx[0]]).group(1)
        rx = re.compile(CONST.format(reg=re.escape(reg)))
        cs = [k for k in range(tx[0] - 1, -1, -1) if rx.match(lines[k])]
        writes = [k for k in range(cs[0] + 1 if cs else 0, tx[0]) if re.search(rf"\b{re.escape(reg)}\b", lines[k])]
        if not cs or writes:
            sys.exit(f"IOemNetd.{sig}: no single constant feeds transact's code")
        k = cs[0]
        old = int(rx.match(lines[k]).group(2), 0)
        new = host.get(sig, UNUSED_CODE)
        if sig in host:
            moved += new != old
            kept += new == old
        else:
            unused += 1
        lines[k] = f"{rx.match(lines[k]).group(1)}const {reg}, {new:#x}"
        out += [header, "\n".join(lines)]
    text2 = "".join(out)
    if unused + moved + kept == 0:
        sys.exit("IOemNetd: no methods found")
    open(path, "w").write(text2)
    print(f"IOemNetd: {kept} codes unchanged, {moved} renumbered to One UI's, {unused} not on One UI (unknown transaction)",
          file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
