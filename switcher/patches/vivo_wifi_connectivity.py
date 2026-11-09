"""vivo's Wi-Fi code on One UI's connectivity module (OriginOS 6 CN, PD2609MA).

The CN image's wifi APEX is vivo's own: service-wifi.jar loads
/apex/com.android.wifi/javalib/vivo-service-wifi.jar (VivoWifiServiceFactoryImpl).
That code uses NetworkCapabilities.TRANSPORT_EXTWIFI (11, vivo's second Wi-Fi
station), a transport only vivo's CN tethering module knows (MAX_TRANSPORT 11).
The guest keeps One UI's tethering module (guest_prepare.sh: its BPF maps are One
UI's netd's), whose NetworkCapabilities refuses anything above 10:
VivoWifiInjector.<clinit> threw "Invalid TransportType 11" while WifiService was
made, and system_server died (first CN run, 2026-11-07).

vivo's own overseas builds, which run Google's tethering module, take 1
(TRANSPORT_WIFI) for it: VivoWifiInjector, AccAdapter and VivoExtWifiStateMachine
set TRANSPORT_EXTWIFI to 11 only when ro.vivo.product.overseas is "no". Those
three take the overseas value here (STATIC). Other classes put a literal 11 into
NetworkRequest/NetworkCapabilities builders for vivo's second Wi-Fi network,
which Samsung's Wi-Fi HAL never brings up; they ask for TRANSPORT_TEST (7)
instead (LITERAL): a request nothing matches, so vivo's game, acceleration and
firewall code does not latch onto the main Wi-Fi network. Each literal is
changed only when no path from the call reads the register before writing it.

The same jar calls five methods only vivo's CN connectivity module has (a
NoSuchMethodError in system_server on One UI's; none of the other system_server
or boot class path jars uses anything the image's copies of the modules the guest
takes from One UI have and One UI's lack). MISSING: NetworkAgent.sendNetworkInfoInternal
becomes sendNetworkInfo (vivo's own other branch), explicitlyClear and
ConnectivityManager.flushDnsCache (vivo-only actions) are dropped,
setExemptedFromVpnFiltering and updateThirdAppAccLimit answer false.

vivo's "EXTWIFI" NetworkInfo and NetworkAgentConfig use legacy network type 38
(ConnectivityManager.TYPE_EXTWIFI, CN module only); One UI's NetworkInfo throws
"Invalid network type" above 18. Those take TYPE_WIFI (1), the type that goes
with vivo's overseas transport (LEGACY), with the same all-paths check.

Every pattern must be found as expected, or nothing is written (fail closed).

/system/framework/vivo-service-wifi-ex-impl.jar (loaded into system_server by
vivo-service-wifi-ex.jar) has a literal one too (VivoWifiGameAdapter); with
"impl" only literals are changed there, and a TRANSPORT_EXTWIFI it sets is refused.
vivo-services.jar (system_server) asks for transport 11 too: vivo's app freezer
(am.frozen.state.SystemState.systemReady) killed system_server in the second CN
run. "services" changes its literals the same way; a build without any (the
global image's) is left as it is.

Usage: vivo_wifi_connectivity.py <apktool decoded jar dir> [wifi|impl|services]   (default wifi:
       vivo-service-wifi.jar from the wifi APEX)
Prints the smali_* directories (dex files) it changed.
"""
import os
import re
import sys

SKIP = re.compile(r"^\s*(\.line \d+|\.local .*|\.end local .*|\.restart local .*|\.prologue)?\s*$")
STATIC_CLASSES = {"com/android/server/wifi/VivoWifiInjector",
                  "com/android/server/wifi/acc/AccAdapter",
                  "com/android/server/wifi/dualwifi/VivoExtWifiStateMachine"}
TRANSPORT_CALL = re.compile(r"^\s*invoke-virtual \{(?P<o>[vp]\d+), (?P<r>[vp]\d+)\}, "
                            r"Landroid/net/(?:NetworkRequest\$Builder|NetworkCapabilities\$Builder|NetworkCapabilities);"
                            r"->(?:add|remove)TransportType\(I\)\S+$")
WRITES = re.compile(r"^(const\S*|move-result\S*|move\S*|new-instance|new-array|iget\S*|sget\S*|aget\S*|"
                    r"instance-of|array-length|cmp\S*|\w+-to-\w+|neg-\S+|not-\S+|"
                    r"(?:add|sub|mul|div|rem|and|or|xor|shl|shr|ushr|rsub)-\w+(?:/lit\d+)?)$")


def fail(msg):
    sys.exit(f"vivo_wifi_connectivity: {msg}")


def code(lines, i):
    """Index of the next instruction line at or after i (no blanks, .line, .local)."""
    while i < len(lines) and SKIP.match(lines[i]):
        i += 1
    return i


def static_site(text, cls):
    """overseas == "no" -> const/16 vA, 0xb, else const/4 vA, 0x1 -> sput TRANSPORT_EXTWIFI."""
    F = r"(?:[ \t]*\n|[ \t]*\.line \d+\n)*"
    pat = re.compile(
        r'const-string(?:/jumbo)? (?P<a>v\d+), "ro\.vivo\.product\.overseas"\n' + F +
        r'[ \t]*const-string(?:/jumbo)? (?P<b>v\d+), "no"\n' + F +
        r'[ \t]*invoke-static \{(?P=a), (?P=b)\}, Landroid/os/SystemProperties;->get\(Ljava/lang/String;Ljava/lang/String;\)Ljava/lang/String;\n' + F +
        r'[ \t]*move-result-object (?P=a)\n' + F +
        r'[ \t]*invoke-virtual \{(?P=b), (?P=a)\}, Ljava/lang/Object;->equals\(Ljava/lang/Object;\)Z\n' + F +
        r'[ \t]*move-result (?P=a)\n' + F +
        r'[ \t]*if-eqz (?P=a), :(?P<c>cond_\d+)\n' + F +
        r'(?P<eleven>[ \t]*const/16 (?P=a), 0xb\n)' + F +
        r'[ \t]*goto :(?P<g>goto_\d+)\n' + F +
        r'[ \t]*:(?P=c)\n' + F +
        r'[ \t]*const/4 (?P=a), 0x1\n' + F +
        r'[ \t]*:(?P=g)\n' + F +
        r'[ \t]*sput (?P=a), L' + re.escape(cls) + r';->TRANSPORT_EXTWIFI:I\n')
    ms = list(pat.finditer(text))
    if len(ms) != 1:
        fail(f"{cls}: the overseas TRANSPORT_EXTWIFI choice {len(ms)} times")
    m = ms[0]
    a = m.group("a")
    new = (f"    # OneOS (patches/vivo_wifi_connectivity.py): vivo's overseas value; One UI's\n"
           f"    # connectivity module has no transport 11.\n    const/4 {a}, 0x1\n")
    return text[:m.start("eleven")] + "\n" + new + text[m.end("eleven"):]


def reads_before_write(lines, mstart, start, reg, end):
    """True when some path from lines[start] reads reg before writing it. Every
    exception handler of the method is walked too (one could cover the call)."""
    labels, handlers = {}, []
    for k in range(mstart, end):
        s = lines[k].strip()
        if re.fullmatch(r":\w+", s):
            labels[s[1:]] = k
        elif s.startswith(".catch"):
            handlers.append(s.split(":")[-1].strip())
    if any(h not in labels for h in handlers):
        return True
    seen, todo = set(), [start] + [labels[h] for h in handlers]
    while todo:
        i = todo.pop()
        while True:
            i = code(lines, i)
            if i >= end or i in seen:
                break
            seen.add(i)
            s = lines[i].strip()
            if s.startswith(":") or s.startswith("."):
                if s.startswith(".catch"):
                    # A handler could see the register: walk it too.
                    h = s.split(":")[-1].strip()
                    if h not in labels:
                        return True
                    todo.append(labels[h])
                i += 1
                continue
            op, _, args = s.partition(" ")
            regs = re.findall(r"\b[vp]\d+\b", args.split('"')[0])
            if reg in regs:
                if WRITES.match(op) and regs[0] == reg and regs.count(reg) == 1:
                    break
                return True
            if op.startswith("return") or op.startswith("throw"):
                break
            if op.startswith("goto"):
                t = args.strip().lstrip(":")
                if t not in labels:
                    return True
                i = labels[t]
                continue
            if op.startswith("if-") or op.startswith("packed-switch") or op.startswith("sparse-switch"):
                if not op.startswith("if-"):
                    return True
                t = args.split(":")[-1].strip()
                if t not in labels:
                    return True
                todo.append(labels[t])
            i += 1
    return False


def literal_sites(text, rel):
    lines = text.split("\n")
    changed = 0
    for i, l in enumerate(lines):
        m = re.match(r"^(\s*)const/16 ([vp]\d+), 0xb$", l)
        if not m:
            continue
        j = code(lines, i + 1)
        c = TRANSPORT_CALL.match(lines[j]) if j < len(lines) else None
        if not c or c.group("r") != m.group(2) or c.group("o") == m.group(2):
            continue
        end = next(k for k in range(j, len(lines)) if lines[k].startswith(".end method"))
        mstart = max(k for k in range(0, i) if lines[k].startswith(".method "))
        if reads_before_write(lines, mstart, j + 1, m.group(2), end):
            fail(f"{rel}:{i + 1}: {m.group(2)} (transport 11) is read again after the call")
        lines[i] = (f"{m.group(1)}# OneOS (patches/vivo_wifi_connectivity.py): vivo's second Wi-Fi (transport 11)\n"
                    f"{m.group(1)}# does not exist on One UI's connectivity module; TRANSPORT_TEST matches nothing.\n"
                    f"{m.group(1)}const/4 {m.group(2)}, 0x7")
        changed += 1
    return "\n".join(lines), changed


NA = "Landroid/net/NetworkAgent;->"
CM = "Landroid/net/ConnectivityManager;->"
MISSING = {
    NA + "sendNetworkInfoInternal(Landroid/net/NetworkInfo;)V": ("swap", NA + "sendNetworkInfo(Landroid/net/NetworkInfo;)V"),
    NA + "explicitlyClear(I)V": ("drop", None),
    CM + "flushDnsCache(I)V": ("drop", None),
    CM + "setExemptedFromVpnFiltering([I)Z": ("false", None),
    CM + "updateThirdAppAccLimit(II)Z": ("false", None),
}
# Call sites in the PD2609MA build's vivo-service-wifi.jar.
MISSING_SITES = {"wifi": {NA + "sendNetworkInfoInternal(Landroid/net/NetworkInfo;)V": 4, NA + "explicitlyClear(I)V": 4,
                          CM + "flushDnsCache(I)V": 6, CM + "setExemptedFromVpnFiltering([I)Z": 1,
                          CM + "updateThirdAppAccLimit(II)Z": 1},
                 "impl": {}, "services": {}}


# service-wifi.jar's WifiNetworkAgent extends NetworkAgent and defines neither
# NetworkAgent method: a call through it resolves to NetworkAgent's.
SUBCLASSES = {"Landroid/net/NetworkAgent;": ("Lcom/android/server/wifi/WifiNetworkAgent;",)}


def missing_calls(text, counts):
    lines = text.split("\n")
    for i, l in enumerate(lines):
        m = re.match(r"^(\s*)invoke-virtual \{([^}]*)\}, (L[^;]+;)->(\S+)$", l)
        if not m:
            continue
        ind, regs, cls, mem = m.groups()
        target = next((k for k in MISSING if k.split("->")[1] == mem and
                       (k.split("->")[0] == cls or cls in SUBCLASSES.get(k.split("->")[0], ()))), None)
        if target is None:
            continue
        how, other = MISSING[target]
        if how == "swap":
            other = cls + "->" + other.split("->")[1]
        how, other = MISSING[target]
        counts[target] = counts.get(target, 0) + 1
        note = f"{ind}# OneOS (patches/vivo_wifi_connectivity.py): {target.split('->')[1].split('(')[0]} is vivo's CN connectivity module's only"
        if how == "swap":
            lines[i] = f"{note}\n{ind}invoke-virtual {{{regs}}}, {other}"
        elif how == "drop":
            lines[i] = f"{note}; dropped"
        else:
            j = code(lines, i + 1)
            r = re.match(r"^\s*move-result ([vp]\d+)$", lines[j]) if j < len(lines) else None
            if r:
                lines[i] = f"{note}; false"
                lines[j] = f"{ind}const/4 {r.group(1)}, 0x0"
            else:
                lines[i] = f"{note}; dropped"
    return "\n".join(lines)


LEGACY_CALLS = re.compile(r"^\s*invoke-(?:direct|virtual) \{(?P<regs>[^}]*)\}, "
                          r"(?P<t>Landroid/net/NetworkInfo;-><init>\(IILjava/lang/String;Ljava/lang/String;\)V|"
                          r"Landroid/net/NetworkAgentConfig\$Builder;->setLegacyType\(I\)Landroid/net/NetworkAgentConfig\$Builder;)$")
LEGACY_SITES = {"wifi": 7, "impl": 0, "services": 0}


def legacy_sites(text, rel):
    """const/16 vN, 0x26 used only as the type argument of the next NetworkInfo
    constructor or setLegacyType call (a few instructions on, nothing else
    touching vN), and not read after it."""
    lines = text.split("\n")
    changed = 0
    for i, l in enumerate(lines):
        m = re.match(r"^(\s*)const/16 ([vp]\d+), 0x26$", l)
        if not m:
            continue
        reg, j, steps = m.group(2), i + 1, 0
        while True:
            j = code(lines, j)
            if j >= len(lines) or steps > 6:
                j = None
                break
            s = lines[j].strip()
            if s.startswith(":") or s.startswith(".") or s.startswith("goto") or s.startswith("if-"):
                j = None
                break
            c = LEGACY_CALLS.match(lines[j])
            if c:
                break
            if re.search(r"\b" + reg + r"\b", s):
                j = None
                break
            j += 1
            steps += 1
        if j is None:
            continue
        regs = [x.strip() for x in c.group("regs").split(",")]
        if len(regs) < 2 or regs[1] != reg or regs.count(reg) != 1:
            continue
        end = next(k for k in range(j, len(lines)) if lines[k].startswith(".end method"))
        mstart = max(k for k in range(0, i) if lines[k].startswith(".method "))
        if reads_before_write(lines, mstart, j + 1, reg, end):
            fail(f"{rel}:{i + 1}: {reg} (legacy type 38) is read again after the call")
        lines[i] = (f"{m.group(1)}# OneOS (patches/vivo_wifi_connectivity.py): legacy type 38 (vivo's EXTWIFI) is\n"
                    f"{m.group(1)}# unknown to One UI's connectivity module; TYPE_WIFI, as with vivo's overseas transport.\n"
                    f"{m.group(1)}const/4 {reg}, 0x1")
        changed += 1
    return "\n".join(lines), changed


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in ("wifi", "impl", "services")):
        fail(__doc__)
    root = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) == 3 else "wifi"
    want = STATIC_CLASSES if mode == "wifi" else set()
    out, dirs, statics, literals, counts, legacies = {}, set(), set(), 0, {}, 0
    for d in sorted(os.listdir(root)):
        if not d.startswith("smali"):
            continue
        for dp, _, fs in os.walk(os.path.join(root, d)):
            for f in fs:
                if not f.endswith(".smali"):
                    continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, os.path.join(root, d))[:-len(".smali")]
                text = open(p).read()
                new = text
                if "->TRANSPORT_EXTWIFI:I" in text and re.search(r"^\s*sput \S+, L\S+;->TRANSPORT_EXTWIFI:I$", text, re.M):
                    if rel not in want:
                        fail(f"{rel} sets a TRANSPORT_EXTWIFI this was not written for")
                    new = static_site(new, rel)
                    statics.add(rel)
                new, n = literal_sites(new, rel)
                literals += n
                new = missing_calls(new, counts)
                new, n = legacy_sites(new, rel)
                legacies += n
                if new != text:
                    out[p] = new
                    dirs.add(d)
    if statics != want:
        fail(f"overseas choices found in {sorted(statics)}, expected {sorted(want)}")
    if literals == 0 and mode != "services":
        fail("no literal transport 11 found (another build?)")
    if legacies != LEGACY_SITES[mode]:
        fail(f"{legacies} legacy type 38 sites, expected {LEGACY_SITES[mode]}")
    if counts != MISSING_SITES[mode]:
        fail(f"calls to vivo-only connectivity methods {counts}, expected {MISSING_SITES[mode]}")
    for p, t in out.items():
        if re.search(r"const/16 [vp]\d+, 0xb\n(?:\s*\n|\s*\.line \d+\n)*\s*invoke-virtual \{[vp]\d+, [vp]\d+\}, Landroid/net/\S+->(?:add|remove)TransportType", t):
            fail(f"{p}: a transport 11 left")
    for p, t in out.items():
        if any(re.search(r"^\s*invoke-\S+ \{[^}]*\}, L[^;]+;->" + re.escape(k.split("->")[1]) + "$", t, re.M) for k in MISSING):
            fail(f"{p}: a vivo-only connectivity call left")
    for p, t in out.items():
        open(p, "w").write(t)
    print(f"vivo_wifi_connectivity: TRANSPORT_EXTWIFI -> 1 in {len(statics)} classes (vivo's overseas value), "
          f"{literals} literal transport 11 -> TRANSPORT_TEST, vivo-only connectivity calls {counts}, {legacies} legacy type 38 -> TYPE_WIFI", file=sys.stderr)
    print("\n".join(sorted(dirs)))


if __name__ == "__main__":
    main()
