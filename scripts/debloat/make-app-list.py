"""The Debloater's app list (0.5.32) from the research lists in docs/debloat/*.tsv.

Writes app-android/app/src/full/assets/debloat/apps.tsv: the apps rated Safe (🟢) or Caution (🟡), one line each,
  <S|C> TAB <package> TAB <label> TAB <KiB> TAB <image ids, comma> TAB <folders, ;> TAB <reason> TAB <m or empty>
The last column marks an app MysticGSI's own debloat removes from that system's builds (docs/debloat/mysticgsi-<list>.txt,
folder names; 0.5.32, owner: the old debloated ColorOS build ran smoother). Such an app rated Keep (🔴) by the research's
automatic rules is offered as Caution all the same, its reason saying so, except the few in MYSTIC_NEVER.
Keep (🔴) apps are not listed: the app never offers them. Resource overlays and any folder that is not an app's
own (the same rule as the root script's debloat_path_ok and guest_prepare.sh's) are dropped; an app left with
no folder is dropped. Run it again after the lists change; the unit tests check the asset against the rule.

Usage: make-app-list.py [docs/debloat] [app-android/app/src/full/assets/debloat/apps.tsv]
"""
import os
import re
import sys

CONTAINERS = ("app", "priv-app", "del-app", "del-app-pre", "data-app")
NOT_LAST = set(CONTAINERS) | {"overlay", "framework", "lib", "lib64", "bin", "etc", "apex", "system", "product",
                              "system_ext", "vendor"}
CHARS = re.compile(r"^[A-Za-z0-9._/+-]+$")
PKG = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+$")
SIZE = re.compile(r"^\s*([0-9.]+)\s*(KB|MB|GB)\b")
RATING = {"🟢": "S", "🟡": "C"}
# The research list each MysticGSI folder list applies to.
MYSTIC = {"coloros.tsv": "mysticgsi-coloros.txt"}
# Never offered, whatever the rating: OPPO's camera (OneOS hides it itself whenever Samsung Camera runs) and ColorOS's
# Always-On Display, which OneOS's AOD and panoramic AOD work targets and the lock screen's fingerprint circle came
# with (A36, 11-21: hidden with MysticGSI's list, no circle on the lock screen; owner: keep it).
NEVER = {"com.oplus.camera", "com.oplus.aod"}


def path_ok(p):
    if not p.startswith("/") or len(p) > 200 or not CHARS.match(p):
        return False
    if "//" in p or "/." in p or p.endswith("/"):
        return False
    parts = p.split("/")[1:]
    if parts[0] in {'apex', 'odm', 'metadata', 'cache', 'sys', 'vendor', 'sdcard', 'mnt', 'proc', 'debug_ramdisk', 'dev', 'storage', 'data'} or parts[-1] in NOT_LAST:
        return False
    return any(c in CONTAINERS for c in parts[:-1])


def kib(notes):
    m = SIZE.match(notes)
    if not m:
        return 0
    return int(float(m.group(1)) * {"KB": 1, "MB": 1024, "GB": 1024 * 1024}[m.group(2)])


def clean(s):
    return " ".join(s.replace("\t", " ").split())


def main(src, out):
    rows, dropped = [], 0
    for name in sorted(os.listdir(src)):
        if not name.endswith(".tsv"):
            continue
        mystic = set()
        if name in MYSTIC and os.path.isfile(os.path.join(src, MYSTIC[name])):
            mystic = {l.strip() for l in open(os.path.join(src, MYSTIC[name]), encoding="utf-8") if l.strip() and not l.startswith("#")}
        with open(os.path.join(src, name), encoding="utf-8") as f:
            head = f.readline().rstrip("\n").split("\t")
            col = {c: i for i, c in enumerate(head)}
            for line in f:
                c = line.rstrip("\n").split("\t")
                if len(c) < len(head):
                    continue
                rating = RATING.get(c[col["rating"]])
                pkg = c[col["package"]]
                folders = [p for p in c[col["folder"]].split(";") if p]
                if pkg in NEVER:
                    continue
                in_mystic = any(f.rstrip("/").split("/")[-1] in mystic for f in folders)
                reason = clean(c[col["reason"]])
                if not rating and in_mystic and c[col["rating"]] == "🔴":
                    rating = "C"
                    reason = "Removed by MysticGSI's own debloat (rated Keep by rule: " + re.sub(r"\s*\[auto:[^]]*\]", "", reason) + ")"
                if not rating or not PKG.match(pkg):
                    continue
                good = [p for p in folders if path_ok(p)]
                if not good:
                    dropped += 1
                    continue
                rows.append((rating, pkg, clean(c[col["label"]]) or pkg, str(kib(c[col["notes"]])),
                             c[col["images"]].replace(" ", ""), ";".join(good), reason, "m" if in_mystic else ""))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("# OneOS Debloater list: scripts/debloat/make-app-list.py from docs/debloat/*.tsv\n")
        for r in sorted(rows, key=lambda r: (r[0] != "S", r[2].lower(), r[1])):
            f.write("\t".join(r) + "\n")
    print(f"{len(rows)} apps ({sum(r[0] == 'S' for r in rows)} safe, {sum(r[7] == 'm' for r in rows)} MysticGSI removes) -> {out}; {dropped} left out (no app folder)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/debloat",
         sys.argv[2] if len(sys.argv) > 2 else "app-android/app/src/full/assets/debloat/apps.tsv")
