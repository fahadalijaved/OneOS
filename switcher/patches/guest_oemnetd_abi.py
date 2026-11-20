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

0.5.28: the code is chosen at runtime by the phone's One UI (an S26 phone updated to One UI 9.5
numbers IOemNetd like the 9.5 image, a One UI 9.0 phone like host_oemnetd.txt). Each method loads its
row number and calls OneOSOemNetdCodes.code(row) (patches/OneOSOemNetdCodes.java), whose table holds
the method's code in every known One UI's table (0 = not there); guest_prepare.sh writes the phone's
ro.build.version.oneui to /data/system/oneos_oemnetd_host. Run on a proxy patched before 0.5.28, the
same: only the signatures are read.

Usage: guest_oemnetd_abi.py <smali root of services.jar> <oneui>=<table> [<oneui>=<table> ...]
       (e.g. 90000=host_oemnetd.txt 90500=host_oemnetd_95.txt; a bare <table> is One UI 9.0's)
Prints the smali_* directory it changed; nothing when the guest has no IOemNetd.
"""
import os
import re
import sys

PROXY = os.path.join("com", "android", "internal", "net", "IOemNetd$Stub$Proxy.smali")
UNUSED_CODE = 0xFFFFF0  # within FIRST..LAST_CALL_TRANSACTION, far above any IOemNetd method
CODES = "Lcom/android/server/OneOSOemNetdCodes;"
CODES_SMALI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OneOSOemNetdCodes.smali")
PLACEHOLDER = '"@@ONEOS_OEMNETD_TABLE@@"'
TRANSACT = re.compile(r"^\s*invoke-interface \{[vp]\d+, ([vp]\d+), [vp]\d+, [vp]\d+, [vp]\d+\}, "
                      r"Landroid/os/IBinder;->transact\(ILandroid/os/Parcel;Landroid/os/Parcel;I\)Z\s*$")
CONST = r"^(\s*)const(?:/4|/16|/high16)? {reg}, (-?0x[0-9a-f]+|-?\d+)\s*$"


def load(table):
    host = {}
    for line in open(table):
        if line.startswith("#") or not line.strip():
            continue
        code, sig = line.split()
        host[sig] = int(code)
    return host


def main(root, *tables):
    hits = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs
            if os.path.join(d, f).endswith(os.sep + PROXY)]
    if not hits:
        print("IOemNetd: not in this framework", file=sys.stderr)
        return
    if len(hits) != 1:
        sys.exit(f"IOemNetd: {len(hits)} proxies")
    versions, hosts = [], []
    for t in tables:
        v, _, f = t.rpartition("=")
        versions.append(v or "90000")
        hosts.append(load(f))
    if not versions or any(not v.isdigit() for v in versions) or len(set(versions)) != len(versions):
        sys.exit(f"IOemNetd: bad tables {tables}")
    path = hits[0]
    text = open(path).read()
    if CODES in text:
        sys.exit("IOemNetd: the proxy reads its codes at runtime already")
    out, rows, unused = [], [], [0] * len(versions)
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
        ind = rx.match(lines[k]).group(1)
        lines[k:k + 1] = [
            f"{ind}const/16 {reg}, {len(rows):#x}",
            "",
            f"{ind}# OneOS: this phone's IOemNetd code (OneOSOemNetdCodes).",
            f"{ind}invoke-static/range {{{reg} .. {reg}}}, {CODES}->code(I)I",
            "",
            f"{ind}move-result {reg}",
        ]
        row = [h.get(sig, 0) for h in hosts]
        for n, c in enumerate(row):
            unused[n] += c == 0
        rows.append(" ".join(str(c) for c in row))
        out += [header, "\n".join(lines)]
    if not rows:
        sys.exit("IOemNetd: no methods found")
    if len(rows) > 0x7FFF:
        sys.exit("IOemNetd: too many methods")
    open(path, "w").write("".join(out))
    codes = open(CODES_SMALI).read()
    if codes.count(PLACEHOLDER) != 1:
        sys.exit("OneOSOemNetdCodes.smali: the table placeholder is not there once")
    dst = os.path.join(root, os.path.relpath(path, root).split(os.sep)[0], "com", "android", "server", "OneOSOemNetdCodes.smali")
    if os.path.exists(dst):
        sys.exit(f"{dst} exists already")
    with open(dst, "w") as f:
        f.write(codes.replace(PLACEHOLDER, '"' + "\\n".join([" ".join(versions)] + rows) + '"'))
    print(f"IOemNetd: {len(rows)} methods with this phone's codes at runtime; not on " +
          ", ".join(f"One UI {v}: {u}" for v, u in zip(versions, unused)), file=sys.stderr)
    print(os.path.relpath(path, root).split(os.sep)[0])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
