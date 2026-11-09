"""vivo's Wi-Fi traffic counters on One UI's BPF maps (OriginOS 6 CN, PD2609MA).

framework-wifi.jar of vivo's own wifi APEX has android.net.wifi.VivoTrafficStats,
whose natives (libvivowifi-service.so -> the APEX's own libnetworkstats.so) read
the kernel's network stats BPF maps with the layout of vivo's CN connectivity
module. The maps are One UI's (its netd and bpfloader pinned them), and the
library aborted on the mismatch (BpfMapRO::abortOnMismatch, SIGABRT in
system_server's VivoWifiFeature thread, fourth CN run).

vivo's overseas builds, which run Google's modules, never call those natives:
every method first checks IS_OVERSEAS (ro.vivo.product.overseas == "yes") and
returns 0 or an empty StatsDetail. Here IS_OVERSEAS is true, whatever the
property says; nothing outside the class calls its natives. The patcher checks
that every method calling a native returns on IS_OVERSEAS before the call.

Usage: vivo_traffic_stats.py <apktool decoded framework-wifi.jar dir>
Prints the smali_* directory it changed.
"""
import os
import re
import sys

CLS = os.path.join("android", "net", "wifi", "VivoTrafficStats.smali")
FLAG = "Landroid/net/wifi/VivoTrafficStats;->IS_OVERSEAS:Z"
NATIVE_CALL = re.compile(r"invoke-static(?:/range)? \{[^}]*\}, Landroid/net/wifi/VivoTrafficStats;->(native\w+)\(")
SKIP = re.compile(r"^\s*(\.line \d+|\.local .*|\.end local .*|\.param .*|\.locals \d+|\.prologue)?\s*$")


def fail(msg):
    sys.exit(f"vivo_traffic_stats: {msg}")


def main():
    if len(sys.argv) != 2:
        fail(__doc__)
    root = sys.argv[1]
    found = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, CLS))]
    if len(found) != 1:
        fail(f"VivoTrafficStats.smali {len(found)} times")
    path = os.path.join(root, found[0], CLS)
    text = open(path).read()
    methods = re.findall(r"^\.method (.*?)\n(.*?)^\.end method", text, re.M | re.S)
    gated = 0
    for decl, body in methods:
        if " native " in f" {decl} " or decl.endswith("<clinit>()V"):
            continue
        calls = NATIVE_CALL.findall(body)
        if not calls:
            continue
        lines = [l.strip() for l in body.split("\n") if not SKIP.match(l)]
        m = re.match(r"sget-boolean (v\d+), " + re.escape(FLAG) + r"$", lines[0]) if lines else None
        # Up to two constants may sit between the read and the branch (not in its register).
        k, b = 1, None
        while m and k < min(len(lines), 4):
            b = re.match(r"if-eqz (v\d+), :(\w+)$", lines[k])
            if b:
                break
            c = re.match(r"const\S* (v\d+), ", lines[k])
            if not c or c.group(1) == m.group(1):
                break
            k += 1
        if not m or not b or b.group(1) != m.group(1):
            fail(f"{decl.split()[-1]} calls {calls[0]} without returning on IS_OVERSEAS first")
        try:
            end = lines.index(":" + b.group(2))
        except ValueError:
            fail(f"{decl.split()[-1]}: no :{b.group(2)}")
        branch = lines[k + 1:end]
        if not branch or not branch[-1].startswith("return") or any(NATIVE_CALL.search(x) or x.startswith(("goto", "if-", ":")) for x in branch):
            fail(f"{decl.split()[-1]}: the IS_OVERSEAS branch does not just return")
        gated += 1
    if gated < 20:
        fail(f"only {gated} methods gated on IS_OVERSEAS (another build?)")
    clinit = re.compile(
        r'(const-string (v\d+), "ro\.vivo\.product\.overseas"\n(?:\s*\n|\s*\.line \d+\n)*'
        r'\s*const-string (v\d+), "no"\n(?:\s*\n|\s*\.line \d+\n)*'
        r'\s*invoke-static \{\2, \3\}, Landroid/os/SystemProperties;->get\(Ljava/lang/String;Ljava/lang/String;\)Ljava/lang/String;\n(?:\s*\n)*'
        r'\s*move-result-object \2\n(?:\s*\n|\s*\.line \d+\n)*'
        r'\s*const-string \3, "yes"\n(?:\s*\n)*'
        r'\s*invoke-virtual \{\3, \2\}, Ljava/lang/Object;->equals\(Ljava/lang/Object;\)Z\n(?:\s*\n)*)'
        r'(\s*move-result \2\n)((?:\s*\n)*\s*sput-boolean \2, ' + re.escape(FLAG) + r'\n)')
    ms = list(clinit.finditer(text))
    if len(ms) != 1:
        fail(f"<clinit>'s IS_OVERSEAS from ro.vivo.product.overseas {len(ms)} times")
    m = ms[0]
    reg = m.group(2)
    new = (f"\n    # OneOS (patches/vivo_traffic_stats.py): the BPF maps are One UI's; vivo's\n"
           f"    # overseas path never reads them.\n    const/4 {reg}, 0x1\n")
    text = text[:m.start(4)] + new + text[m.end(4):]
    if len(re.findall(r"sput-boolean \S+, " + re.escape(FLAG), text)) != 1:
        fail("IS_OVERSEAS is set more than once")
    open(path, "w").write(text)
    print(f"vivo_traffic_stats: IS_OVERSEAS true ({gated} methods return before their native call)", file=sys.stderr)
    print(found[0])


if __name__ == "__main__":
    main()
