#!/usr/bin/env python3
"""One UI 9.5 on One UI 8 (set oneui95-a16 r4, oneui8test7): the image's calls into the connectivity module
that One UI 8's module does not have, each with a fallback.

On a One UI 8 phone the guest keeps One UI's tethering module (its BPF maps; guest_prepare.sh A17_ON_A16), an
Android 16 train (360743340 on the S22s), and the image's framework, services and telephony code is built against
the Android 17 one. The S22 (1c1aab25, oneui8test6) got past the boot class path and the package scan, then
system_server died in its boot phase: "No static method getL4sDeveloperOption(Landroid/content/Context;)I in class
Landroid/net/ConnectivitySettingsManager" (IpConnectivityMetrics.onBootPhase). Every member the image's jars use
from framework-connectivity*.jar and framework-tethering.jar, checked by full signature against the Android 16
release branch's API files (packages/modules/Connectivity android16-release, framework*/api/*current.txt): the
ones below are not there. Each call is put in a try block for java.lang.LinkageError (NoSuchMethodError) with a
handler that does what Android 16 does:

  getL4sDeveloperOption -> 0 (L4S off, the default); setL4sDeveloperOption -> nothing
  NetworkTemplate.Builder() + setTransportType(t) -> NetworkTemplate.Builder(MATCH_WIFI), as the same method's
      other branch
  NetworkStatsManager.querySummary / queryTaggedSummary / querySummaryForDevice (template, start, end, int) -> the
      three-argument call (NetworkPolicyManagerService, MultipathPolicyTracker, StatsPullAtomService)
  ConnectivityManager.onEarlyInit() -> nothing (ActivityThread, every app)
  QosFilter.matchesLocalPrefix / matchesRemotePrefix(IpPrefix, int, int) -> matchesLocalAddress /
      matchesRemoteAddress(the same InetAddress, int, int)

Where One UI's module has the member, the try block costs nothing. Fail-closed: every site must be found exactly
the number of times listed, in the jar it belongs to (services, framework or telephony-common smali tree).

    a16_connectivity_compat.py <decoded jar dir>   -> prints the smali dirs it changed
"""
import os
import re
import sys

MARK = "# OneOS: a16_connectivity_compat"
CATCH = "Ljava/lang/LinkageError;"
CSM = "Landroid/net/ConnectivitySettingsManager;"
NSM = "Landroid/app/usage/NetworkStatsManager;"
NTB = "Landroid/net/NetworkTemplate$Builder;"
QF = "Landroid/net/QosFilter;"
R = r"[vp]\d+"


def l4s_get(m, src):
    return f"    const/4 {m.group('res')}, 0x0\n"


def nothing(m, src):
    return ""


STATS = "Landroid/app/usage/NetworkStats;"
BUCKET = "Landroid/app/usage/NetworkStats$Bucket;"


def query3(name, ret=STATS):
    def fb(m, src):
        last = f"{m.group('bp')}{int(m.group('bn')) - 1}"
        return (f"    invoke-virtual/range {{{m.group('a')} .. {last}}}, {NSM}->{name}(Landroid/net/NetworkTemplate;JJ){ret}\n\n"
                f"    move-result-object {m.group('res')}\n")
    return fb


def builder(m, src):
    # The int for Builder(MATCH_WIFI) needs a register of its own. ColorOS 17's StatsPullAtomService (abhera,
    # coloros22test4 logs-673d188e) keeps the builder and the result in one register (v1): new-instance v1, then
    # const/4 v1 overwrote it and the verifier rejected the class ("tried to get class from non-reference register
    # v1"), so system_server died. Then main() gives the method one more local ({NEWREG}).
    tmp = m.group('tmp') if m.group('tmp') != m.group('res') else "{NEWREG}"
    return (f"    new-instance {m.group('res')}, {NTB}\n\n"
            f"    const/4 {tmp}, 0x4\n\n"
            f"    invoke-direct {{{m.group('res')}, {tmp}}}, {NTB}-><init>(I)V\n")


def qos(name):
    def fb(m, src):
        # The InetAddress the IpPrefix was made from, just above: IpPrefix-><init>(InetAddress, int).
        k = list(re.finditer(r"invoke-direct \{" + R + r", (?P<addr>" + R + r"), " + R +
                             r"\}, Landroid/net/IpPrefix;-><init>\(Ljava/net/InetAddress;I\)V\n", src[:m.start()]))
        if not k:
            sys.exit("a16_connectivity_compat: no IpPrefix(InetAddress, int) before a QosFilter call")
        return (f"    invoke-virtual {{{m.group('obj')}, {k[-1].group('addr')}, {m.group('s')}, {m.group('e')}}}, {QF}->{name}(Ljava/net/InetAddress;II)Z\n\n"
                f"    move-result {m.group('res')}\n")
    return fb


def query_rx(name, ret=STATS):
    return re.compile(r"^    invoke-virtual/range \{(?P<a>" + R + r") \.\. (?P<bp>[vp])(?P<bn>\d+)\}, " + re.escape(NSM) + "->" + name +
                      r"\(Landroid/net/NetworkTemplate;JJI\)" + re.escape(ret) + r"\n\n    move-result-object (?P<res>" + R + r")\n", re.M)


def qos_rx(name):
    return re.compile(r"^    invoke-virtual \{(?P<obj>" + R + r"), " + R + r", (?P<s>" + R + r"), (?P<e>" + R + r")\}, " + re.escape(QF) +
                      "->" + name + r"\(Landroid/net/IpPrefix;II\)Z\n\n    move-result (?P<res>" + R + r")\n", re.M)


L4S_GET = re.compile(r"^    invoke-static \{" + R + r"\}, " + re.escape(CSM) +
                     r"->getL4sDeveloperOption\(Landroid/content/Context;\)I\n\n    move-result (?P<res>" + R + r")\n", re.M)

# (jar, smali file, site, fallback, expected count)
SITES = [
    ("services", "com/android/server/connectivity/IpConnectivityMetrics.smali", L4S_GET, l4s_get, 1),
    ("services", "com/android/server/connectivity/NetdEventListenerService$2.smali", L4S_GET, l4s_get, 1),
    ("services", "com/android/server/connectivity/NetdEventListenerService.smali",
     re.compile(r"^    invoke-static \{" + R + ", " + R + r"\}, " + re.escape(CSM) +
                r"->setL4sDeveloperOption\(Landroid/content/Context;I\)V\n", re.M), nothing, 2),
    ("services", "com/android/server/stats/pull/StatsPullAtomService.smali",
     re.compile(r"^    new-instance (?P<tmp>" + R + "), " + re.escape(NTB) + r"\n\n    invoke-direct \{(?P=tmp)\}, " + re.escape(NTB) +
                r"-><init>\(\)V\n\n    invoke-virtual \{(?P=tmp), " + R + r"\}, " + re.escape(NTB) +
                r"->setTransportType\(I\)" + re.escape(NTB) + r"\n\n    move-result-object (?P<res>" + R + r")\n", re.M), builder, 1),
    ("services", "com/android/server/stats/pull/StatsPullAtomService$$ExternalSyntheticLambda5.smali", query_rx("querySummary"), query3("querySummary"), 1),
    ("services", "com/android/server/stats/pull/StatsPullAtomService$$ExternalSyntheticLambda5.smali", query_rx("queryTaggedSummary"), query3("queryTaggedSummary"), 1),
    # ColorOS 17 makes these two calls in the method itself, not in a lambda (abhera, coloros22test5 logs-6da0d5ce:
    # NoSuchMethodError querySummary(NetworkTemplate, long, long, int) killed system_server on android.bg). One UI
    # 9.5 has none there: 0 or 1.
    ("services", "com/android/server/stats/pull/StatsPullAtomService.smali", query_rx("querySummary"), query3("querySummary"), (0, 1)),
    ("services", "com/android/server/stats/pull/StatsPullAtomService.smali", query_rx("queryTaggedSummary"), query3("queryTaggedSummary"), (0, 1)),
    ("services", "com/android/server/net/NetworkPolicyManagerService$Dependencies.smali", query_rx("querySummary"), query3("querySummary"), 1),
    ("services", "com/android/server/net/NetworkPolicyManagerService$Dependencies.smali",
     query_rx("querySummaryForDevice", BUCKET), query3("querySummaryForDevice", BUCKET), 1),
    ("services", "com/android/server/connectivity/MultipathPolicyTracker$MultipathTracker.smali",
     query_rx("querySummaryForDevice", BUCKET), query3("querySummaryForDevice", BUCKET), 1),
    ("framework", "android/app/ActivityThread.smali",
     re.compile(r"^    invoke-virtual \{" + R + r"\}, Landroid/net/ConnectivityManager;->onEarlyInit\(\)V\n", re.M), nothing, 1),
    ("telephony", "com/android/internal/telephony/data/QosCallbackTracker$1$1.smali", qos_rx("matchesLocalPrefix"), qos("matchesLocalAddress"), 1),
    ("telephony", "com/android/internal/telephony/data/QosCallbackTracker$1$1.smali", qos_rx("matchesRemotePrefix"), qos("matchesRemoteAddress"), 1),
]

# Android 17 replaced NetworkStatsManager's manager-wide poll switches (setPollOnOpen/setPollForce) with a flags int on
# every query, behind the flag useNetstatsPerQueryFlags. One UI 8's module only has the switches; with the flag on, the
# fallbacks above drop the int (0 = no poll) and the manager's default polls on every open. ColorOS 17 on the S22 Ultra
# (abhera, coloros22test6 logs-e99d05d4): Wi-Fi on -> NetworkPolicyManagerService's queries polled, each poll
# broadcast NETWORK_STATS_UPDATED, which queried again: 4 to 95 polls a second for 20 s, then system_server died.
# The flag read as false at its readers, so each takes its Android 16 path (NetworkPolicyManagerService then calls
# setPollOnOpen(false)). (jar, smali file, site, replacement, expected count: 0 or 1 where a build may not have it.)
NSPQ = re.compile(r"^    invoke-static \{\}, Lcom/android/internal/hidden_from_bootclasspath/android/net/platform/flags/Flags;"
                  r"->useNetstatsPerQueryFlags\(\)Z\n\n    move-result (?P<res>" + R + r")\n", re.M)
REPLACE = [
    ("services", "com/android/server/net/NetworkPolicyManagerService$Dependencies.smali", NSPQ, (0, 1)),
    ("services", "com/android/server/connectivity/MultipathPolicyTracker$MultipathTracker.smali", NSPQ, (0, 1)),
    ("services", "com/android/server/stats/pull/StatsPullAtomService.smali", NSPQ, (0, 2)),
]


# Which jar a decoded tree is: a class only that jar has.
KIND = {
    "services": "com/android/server/SystemServer.smali",
    "framework": "android/app/ActivityThread.smali",
    "telephony": "com/android/internal/telephony/Phone.smali",
}


def find(root, rel):
    hits = [d for d in sorted(os.listdir(root)) if d.startswith("smali") and os.path.isfile(os.path.join(root, d, rel))]
    if len(hits) > 1:
        sys.exit(f"a16_connectivity_compat: {rel} found in {hits}")
    return hits[0] if hits else None


def main():
    root = sys.argv[1]
    kinds = [k for k, rel in KIND.items() if find(root, rel)]
    if len(kinds) != 1:
        sys.exit(f"a16_connectivity_compat: {root} is not one of services, framework, telephony-common ({kinds})")
    kind = kinds[0]
    files = {}
    for site_kind, rel, rx, fallback, want in SITES:
        if site_kind != kind:
            continue
        d = find(root, rel)
        if d is None:
            # ONEOS_A16CC_ABSENT_OK=1 also covers a class the build does not have (ColorOS 17 has no
            # NetdEventListenerService$2: it makes no L4S call anywhere).
            if os.environ.get("ONEOS_A16CC_ABSENT_OK") == "1":
                print(f"a16_connectivity_compat: {rel} not in this {kind} jar, nothing to guard", file=sys.stderr)
                continue
            sys.exit(f"a16_connectivity_compat: {rel} not in this {kind} jar")
        path = os.path.join(root, d, rel)
        if path not in files:
            src = open(path).read()
            if MARK in src:
                sys.exit(f"a16_connectivity_compat: {rel} already patched")
            files[path] = [d, src, 0]
        d, src, n = files[path]
        found = list(rx.finditer(src))
        # ONEOS_A16CC_ABSENT_OK=1 (0.5.51, ColorOS 17's jars for One UI 8): a site that is not there at all is a call
        # this build does not make (ColorOS's IpConnectivityMetrics has no L4S option), so nothing to guard; any other
        # count than expected still stops the patch.
        if len(found) == 0 and os.environ.get("ONEOS_A16CC_ABSENT_OK") == "1":
            print(f"a16_connectivity_compat: {rel}: no such call in this build, nothing to guard", file=sys.stderr)
            continue
        if len(found) not in (want if isinstance(want, tuple) else (want,)):
            sys.exit(f"a16_connectivity_compat: {rel}: {len(found)} sites, expected {want}")
        if not found:
            continue
        for m in reversed(found):  # from the last site back, so earlier offsets stay right
            n += 1
            tag = f"oneos_a16cc_{n}"
            fb = fallback(m, src)
            if "{NEWREG}" in fb:
                start = src.rfind("\n.method ", 0, m.start())
                lm = re.compile(r"^    \.locals (\d+)$", re.M).search(src, start, m.start())
                if start < 0 or not lm:
                    sys.exit(f"a16_connectivity_compat: {rel}: no .locals for a site that needs a free register")
                k = int(lm.group(1))
                if k >= 16:
                    sys.exit(f"a16_connectivity_compat: {rel}: .locals {k}, no free low register for the fallback")
                fb = fb.replace("{NEWREG}", f"v{k}")
                src = src[:lm.start()] + f"    .locals {k + 1}" + src[lm.end():]
                shift = len(f"    .locals {k + 1}") - (lm.end() - lm.start())
                m = rx.search(src, m.start() + shift)
            end = src.find("\n.end method\n", m.end())
            if end < 0:
                sys.exit(f"a16_connectivity_compat: {rel}: no .end method after a site")
            src = src[:end + 1] + f"\n    :{tag}_h\n" + fb + f"\n    goto :{tag}_e\n" + src[end + 1:]
            src = (src[:m.start()] + f"    {MARK}\n    :{tag}_s\n" + m.group(0) + f"\n    :{tag}_e\n"
                   f"    .catch {CATCH} {{:{tag}_s .. :{tag}_e}} :{tag}_h\n" + src[m.end():])
        files[path] = [d, src, n]
    for site_kind, rel, rx, want in REPLACE:
        if site_kind != kind:
            continue
        d = find(root, rel)
        if d is None:
            continue
        path = os.path.join(root, d, rel)
        if path not in files:
            src = open(path).read()
            if MARK in src:
                sys.exit(f"a16_connectivity_compat: {rel} already patched")
            files[path] = [d, src, 0]
        d, src, n = files[path]
        found = list(rx.finditer(src))
        if len(found) not in want:
            sys.exit(f"a16_connectivity_compat: {rel}: {len(found)} useNetstatsPerQueryFlags reads, expected {want}")
        for m in reversed(found):
            src = src[:m.start()] + f"    {MARK} (useNetstatsPerQueryFlags: false)\n    const/4 {m.group('res')}, 0x0\n" + src[m.end():]
        files[path] = [d, src, n]
    for path, (d, src, n) in files.items():
        with open(path, "w") as f:
            f.write(src)
    if not files:
        sys.exit(f"a16_connectivity_compat: nothing to change in this {kind} jar")
    print("\n".join(sorted({d for d, _, _ in files.values()})))


if __name__ == "__main__":
    main()
