#!/usr/bin/env python3
"""The phone list for people asking "does it work on my phone?" (owner, 2026-11-06).

    reports/devices.py [--devices docs/devices.json] [--db out/reports/db/reports.jsonl]
                       [--waiting reports/waiting.json] [--md docs/devices.md]
                       [--filters out/telegram/rose_filters.txt] [--days 10]
    reports/devices.py --scan   # findings in out/reports/inbox from phones in neither list

From docs/devices.json (every phone the app knows and the systems it can run, DeviceList.kt) and
the testers' reports (reports/pull.py), one entry per phone name (its variants, e.g. the S26's
Snapdragon, docomo and Exynos builds, together):
  - docs/devices.md, the public list;
  - the group's Rose bot filters: one "/filter (triggers...) reply" per phone, for an admin to
    paste into the group (a filter added again with the same triggers replaces the old one), so
    a message naming a phone gets its answer.
Phones only in the next, unreleased app (--upcoming ID,... --next VERSION, e.g. a35,a54,a16-s166 for 0.4.59)
read "comes with OneOS VERSION" instead of their systems: drop the flags at that release.
Phones in reports/waiting.json (findings sent, no profile: One UI 7 or older, or a tablet) get
the same entry and filter with "not yet" and the One UI their findings showed.
Per system: what recent reports (the last --days days) say, else "tested by the team" (a session
has run there, the app's tested flag), else "not tested yet". Counts and item names only: no
names, notes, contacts or ids, as in docs/compatibility.md.
"""
import argparse
import glob
import json
import os
import re
import zipfile
from collections import defaultdict
from datetime import date, timedelta

# Names the app has for one chip only ("Galaxy S24+ (Exynos)", no Snapdragon S24+ profile): a one-line
# reply names the chip, so the owner of the other one does not read it as theirs.
ONE_CHIP = set()
LINK = ""  # --link https://github.com/fahadalijaved/OneOS/blob/main/docs/devices.md once it is public
# The app's own label for the F8U is the profile's id; people know the phone by its name.
DISPLAY = {"f8u": "Galaxy Z Fold8 Ultra"}
SHORT = {
    "coloros17-findn6": "ColorOS 17 (Find N6)",
    "coloros17-findx9u-in": "ColorOS 17 (Find X9 Ultra)",
    "pixel11fold-yogi": "Pixel 11 Fold",
    "pixel11pro-kodiak": "Pixel 11 Pro",
    "pixel9proxl-komodo": "Pixel 9 Pro XL",
    "infinityx41-findx9u": "Infinity-X 4.1",
    "hyperos-lhasa": "HyperOS",
    "nothingos5-metroid": "Nothing OS 5",
    "oxygenos16-cph2745": "OxygenOS 16",
    "originos7-pd2609ma": "OriginOS 7",
}
CHIP = {
    "SM8850": "Snapdragon 8 Elite Gen 5", "SM8750": "Snapdragon 8 Elite", "SM8650": "Snapdragon 8 Gen 3",
    "SM8550": "Snapdragon 8 Gen 2", "SM6475": "Snapdragon 6 Gen 3",
    "s5e9965": "Exynos 2600", "s5e9955": "Exynos 2500", "s5e9945": "Exynos 2400", "s5e8855": "Exynos 1580",
    "s5e8865": "Exynos 1680",
    "s5e8835": "Exynos 1380", "s5e8535": "Exynos 1330", "MT6789": "Helio G99",
    "s5e8845": "Exynos 1480", "SM8450": "Snapdragon 8 Gen 1", "SM7450": "Snapdragon 7 Gen 1",
}
# Per phone: a chip that shares another's board code, and the 4G/5G a label leaves out.
CHIP_OF = {"s-fe-9945": "Exynos 2400e"}
EXTRA = {"a17": "4G", "a07": "4G"}
ITEMS = [("screen", "Screen"), ("wifi", "Wi-Fi"), ("data", "Mobile data"), ("calls", "Calls"), ("sms", "SMS"),
         ("bluetooth", "Bluetooth"), ("sound", "Sound"), ("camera", "Camera"), ("google", "Google"),
         ("location", "Location"), ("back", "Back to One UI"), ("heat", "Heat"), ("fold", "Both screens")]


def family(p):
    """The name a phone is asked about: the label without its variant ("(Exynos)", "5G")."""
    name = DISPLAY.get(p["id"], p["label"])
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"\s+[45]G$", "", name).strip()


def variant(p, others=()):
    """"SM-S938, Snapdragon 8 Elite"; others: longer model numbers under this prefix that are other phones."""
    chip = CHIP_OF.get(p["id"]) or CHIP.get(p["chip"], p["chip"])
    m = re.search(r"\(([^)]*)\)", p["label"])
    extra = [m.group(1)] if (m and p["id"] not in DISPLAY and not m.group(1).startswith(p["model"])
                             and m.group(1).lower() not in chip.lower()) else []
    if re.search(r"\s[45]G\b", p["label"]):
        extra.append(re.search(r"([45]G)", p["label"]).group(1))
    elif p["id"] in EXTRA:
        extra.append(EXTRA[p["id"]])
    model = p["model"] + (f" (not {', '.join(others)})" if others else "")
    return ", ".join([model] + extra + [chip])


def triggers(name):
    """What people type: "s25 ultra", "s25u", "fold7", "z fold 7", "flip5", "a56", "tab s9 fe+"..."""
    base = name.lower().replace("galaxy ", "").strip()
    if "/" in base:  # "Galaxy F55/E55": one phone sold under two names, and people type either
        return sorted({t for part in base.split("/") for t in triggers(part)}, key=lambda t: (len(t), t))
    # No "galaxy ..." forms: Rose matches whole words anywhere in a message, so "s25 plus" already
    # answers "galaxy s25 plus", while a "galaxy s25" trigger would outrank it (the longer one wins).
    out = {base}
    m = re.match(r"^tab (\w+) (fe\+?|lite)$", base)
    if m:
        out.update({f"tab {m.group(1)}{m.group(2)}", f"tab{m.group(1)} {m.group(2)}"})
    m = re.match(r"^z (fold|flip)(\d+)( ultra)?$", base)
    if m:
        kind, num, ultra = m.group(1), m.group(2), m.group(3) or ""
        for t in (f"{kind}{num}", f"{kind} {num}", f"z {kind} {num}", f"z{kind}{num}", f"z{kind} {num}"):
            out.add(t + ultra)
        if ultra:
            out.update({f"{kind}{num}u", f"{kind} {num}u", f"z{kind}{num}u", f"f{num}u"})
    m = re.match(r"^s(\d+)(\+| ultra| edge| fe)?$", base)
    if m:
        num, suf = m.group(1), m.group(2) or ""
        if suf == " ultra":
            out.update({f"s{num}u", f"s{num}ultra", f"s{num} u"})
        elif suf == "+":
            out.update({f"s{num} plus", f"s{num}plus", f"s{num} +"})
        elif suf in (" edge", " fe"):
            out.add(f"s{num}{suf.strip()}")
    return sorted(out, key=lambda t: (len(t), t))


def recent_reports(db, days):
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = defaultdict(lambda: {"n": 0, "home": 0, "tried": 0, "items": defaultdict(lambda: [0, 0]), "last": "", "version": ""})
    if not os.path.exists(db):
        return rows
    for line in open(db):
        if not line.strip():
            continue
        r = json.loads(line)
        c = r.get("checklist")
        if not c or not r.get("sessionId") or (r.get("receivedAt") or "")[:10] < since:
            continue
        key = ((r.get("phone") or {}).get("profile"), r.get("image"))
        row = rows[key]
        row["n"] += 1
        if c.get("start"):
            row["tried"] += 1
            row["home"] += c["start"] == "home"
        for k, answer in (c.get("items") or {}).items():
            if answer in ("works", "problem"):
                row["items"][k][1] += 1
                row["items"][k][0] += answer == "works"
        at = r.get("receivedAt") or ""
        if at >= row["last"]:
            row["last"] = at
            row["version"] = re.sub(r"-(fold|s26|s25|probe)$", "", ((r.get("sessionApp") or r.get("app") or {}).get("version") or ""))
    return rows


TINY = {"coloros17-findn6": "ColorOS N6", "coloros17-findx9u-in": "ColorOS X9U", "infinityx41-findx9u": "Infinity-X",
        "nothingos5-metroid": "Nothing OS"}


def compact(system, row):
    """"⚠️ HyperOS 6/8": a system's mark and started/tries for one line per phone."""
    name = TINY.get(system["image"]) or SHORT.get(system["image"], system["label"])
    if row and row["n"]:
        mark, _ = status(system, row)
        if row["tried"]:
            return f"{mark} {name} {row['home']}/{row['tried']}"
        return f"{mark} {name} ({row['n']})"
    return f"✅ {name} team" if system["tested"] else f"🔲 {name}"


def status(system, row):
    """(emoji, text) for one system on one phone."""
    if row and row["n"]:
        issues = [label for k, label in ITEMS if row["items"].get(k) and row["items"][k][0] * 2 < row["items"][k][1]]
        n = row["n"]
        reports = f"{n} report{'s' if n != 1 else ''}"
        if row["tried"] and row["home"] == 0:
            mark, text = "❌", f"did not start ({reports}, OneOS {row['version']})"
        elif row["tried"] and row["home"] < row["tried"]:
            mark, text = "⚠️", f"started in {row['home']} of {row['tried']} ({reports}, OneOS {row['version']})"
        else:
            mark, text = "✅", f"starts ({reports}, OneOS {row['version']})"
        if issues:
            text += "; problems reported: " + ", ".join(issues)
        return mark, text
    if system["tested"]:
        return "✅", "tested by the team"
    return "🔲", "not tested yet"


def waiting_text(w):
    seen = f"; the latest findings from it showed One UI {w['oneui']}" if w.get("oneui") else ""
    if w.get("tablet"):
        return f"no tablets so far{seen}"
    return f"OneOS needs One UI 8 or newer (Android 16 or 17){seen}. Send findings again after the update"


def build(devices, rows, upcoming=(), nxt="", waiting=()):
    longer = [m for w in waiting for m in w["models"]]
    fams = {}
    for p in devices["phones"]:
        if not p.get("enabled", True):
            continue
        fams.setdefault(family(p), []).append(p)
    entries = []
    ONE_CHIP.clear()
    ONE_CHIP.update(name for name, phones in fams.items()
                    if len(phones) == 1 and re.search(r"\((Exynos|Snapdragon|MediaTek)\)", phones[0]["label"]))
    for name, phones in fams.items():
        variants = []
        for p in phones:
            others = [m for m in longer if m.startswith(p["model"]) and m != p["model"]]
            if p["id"] in upcoming:
                variants.append((variant(p, others), [("🔜", "Coming", f"with OneOS {nxt} (on One UI 9), not in the current app yet",
                                                        f"🔜 with OneOS {nxt}")]))
                continue
            lines = []
            for s in p["systems"]:
                row = rows.get((p["id"], s["image"]))
                mark, text = status(s, row)
                lines.append((mark, SHORT.get(s["image"], s["label"]), text, compact(s, row)))
            variants.append((variant(p, others), lines))
        entries.append((name, variants))
    by_name = {name: variants for name, variants in entries}
    for w in waiting:
        # A tablet on One UI 8.5 does not "need 8": it waits because it is a tablet.
        brief = ("tablet" + (f" (One UI {w['oneui']})" if w.get("oneui") else "") + ", not supported yet") if w.get("tablet") \
            else (f"One UI {w['oneui']} now, needs 8" if w.get("oneui") else "needs One UI 8")
        line = [("🕓", "Not yet", waiting_text(w), "🕓 " + brief)]
        if w.get("variantOf"):
            by_name[w["variantOf"]].append((w["variant"], line))
        else:
            assert w["name"] not in by_name, w["name"]
            entries.append((w["name"], [(w.get("variant") or ", ".join(w["models"]), line)]))
    entries.sort(key=lambda e: e[0])
    return entries


TITLE = "Which phones OneOS runs on"


def slug(text):
    return re.sub(r"[^a-z0-9 _-]", "", text.lower()).replace(" ", "-")


def anchors(entries):
    """Each entry's anchor on GitHub: github-slugger numbers a repeated slug (S25+ after S25 = -1)."""
    seen, out = {slug(TITLE): 1}, {}
    for name, _ in entries:
        base = slug(name)
        n = seen.get(base, 0)
        out[name] = base if n == 0 else f"{base}-{n}"
        seen[base] = n + 1
    return out


def markdown(entries, today):
    out = [f"# {TITLE}", "",
           "Every phone the OneOS app supports, and for each system what testers reported in the last days "
           "(✅ started every time, ⚠️ started on some tries, ❌ did not start, then the checklist items most of them "
           "marked as a problem), what the team tested (✅ tested by the team), "
           "🔲 not tested yet, or 🔜 comes with the next update; 🕓 phones that sent findings but need One UI 8 "
           "or newer first, or are tablets. Generated by `reports/devices.py` from the app's phone list and the reports sent "
           "from the app (**Send to the OneOS team**): counts only.", "",
           f"Updated {today}. Every system is still experimental: read the warnings in the [README](../README.md) first.", ""]
    for name, variants in entries:
        out += [f"## {name}", ""]
        for v, lines in variants:
            if len(variants) > 1:
                out += [f"**{v}**", ""]
            else:
                out += [f"{v}", ""]
            out += ["| System | Status |", "|---|---|"]
            out += [f"| {sysname} | {mark} {text} |" for mark, sysname, text, _ in lines]
            out.append("")
    return "\n".join(out)


# Only phrases that don't run into a phone's name ("does it work on my s25 ultra" must get the S25 Ultra).
OVERVIEW = ["which phones", "what phones", "which devices", "supported phones", "supported devices", "phone list",
            "device list", "devices list"]
RANK = {"✅": 5, "⚠️": 4, "❌": 3, "🔲": 2, "🔜": 1, "🕓": 0}


def filters(entries, today):
    """One filter per phone name, and one for "which phones?" with every name and its best result."""
    names, later = [], []
    anchor = anchors(entries)
    for name, variants in entries:
        # Each model's best system; models that differ (A16 4G and 5G) show each mark.
        marks = sorted({max((l[0] for l in ls), key=RANK.get) for _, ls in variants}, key=RANK.get, reverse=True)
        tried = [m for m in marks if m in ("✅", "⚠️", "❌", "🔲")]
        marks = tried or marks  # models still to come or waiting don't change a tried phone's mark
        if marks == ["🕓"]:
            later.append(name.replace("Galaxy ", ""))
        elif len(marks) == 1:
            names.append(f"{marks[0]} {name}")
        else:
            names.append(f"{''.join(marks)} {name} (differs by model)")
    if later:
        names.append("\n🕓 Not yet (One UI 8 needed, or a tablet): " + ", ".join(later))
    cmds = ["/filter (" + ", ".join(f'"{t}"' for t in OVERVIEW) + ") 📱 Phones OneOS supports\n"
            "✅ started for testers or the team, ⚠️ started on some tries, ❌ did not start, 🔲 not tested yet, "
            "🔜 next update\n\n"
            + "\n".join(names) + "\n\nWrite your phone's name (e.g. s25 ultra, fold7) to see each system."
            + (f"\nFull list: {LINK}" if LINK else "")]
    for name, variants in entries:
        reply = [f"📱 {name}"]
        for v, lines in variants:
            if len(variants) > 1:
                reply.append(f"\n{v}:")
            else:
                reply.append(v)
            reply += [f"{mark} {sysname}: {text}" for mark, sysname, text, _ in lines]
        if LINK:
            reply.append(f"\nFull list: {LINK}#{anchor[name]}")
        if any(mark in "✅⚠️❌🔲" for _, ls in variants for mark, _, _, _ in ls):
            reply.append("Tried one? Tell us from the OneOS app: Send to the OneOS team.")
        trig = ", ".join(f'"{t}"' if " " in t else t for t in triggers(name))
        cmds.append(f"/filter ({trig}) " + "\n".join(reply))
    return cmds


def exact(cmd):
    """A phone filter that answers only a message that is exactly one of its triggers (Rose's
    "exact:" type), so a sentence that merely names a phone gets no reply (owner, 2026-11-08: the
    filters filled the chat). The "which phones" overview keeps matching anywhere."""
    m = re.match(r"/filter \(([^)]*)\) ", cmd)
    trig = [t.strip().strip('"') for t in m.group(1).split(",")]
    if any(t in OVERVIEW for t in trig):
        return cmd
    return "/filter (" + ", ".join(f'"exact:{t}"' for t in trig) + ") " + cmd[m.end():]


def scan(devices, waiting, inbox):
    """Findings zips from phones with no profile and no waiting.json entry: what each showed."""
    known = [(m.strip(), p["codename"]) for p in devices["phones"] for m in p["model"].split(",")]
    wait = [m for w in waiting for m in w["models"]]
    for z in sorted(glob.glob(os.path.join(inbox, "*", "findings*", "*.zip"))):
        try:
            with zipfile.ZipFile(z) as zf:
                names = [n for n in zf.namelist() if n.endswith("summary.txt")]
                text = zf.read(names[0]).decode(errors="replace") if names else ""
        except (zipfile.BadZipFile, OSError) as e:
            print(f"{z}: unreadable ({e})")
            continue
        line = lambda k: (re.search(rf"^{k}:\s*(.*)$", text, re.M) or [None, "?"])[1].strip()
        m = re.match(r"(\S+) \(([^)]*)\)", line("Phone"))
        if not m:
            print(f"{z}: no Samsung phone line ({line('Phone')})")
            continue
        model, code = m.groups()
        if any(model.startswith(k) and code == c for k, c in known) or any(model.startswith(k) for k in wait):
            continue
        print(f"{model} ({code}) | {line('Chip')} | One UI {line('One UI')} | Android {line('Android')} | {z}")


LEGEND = "✅ starts every time · ⚠️ some tries · ❌ did not start · 🔲 not tested · 🔜 next update · n/m = started in n of m tries"
GROUPS = [("s-22", "Galaxy S22", r"^Galaxy S22"),
          ("s-old", "Galaxy S23 and S24", r"^Galaxy S2[34]"), ("s-new", "Galaxy S25 and S26", r"^Galaxy S2[56]"),
          ("fold", "Galaxy Z Fold", r"^Galaxy Z Fold"), ("flip", "Galaxy Z Flip", r"^Galaxy Z Flip"),
          ("a", "Galaxy A, F and M", r"^Galaxy [AMF]\d")]


def filters_grouped(entries):
    """Few replies for the group: one per series, each phone one line; every phone name still a trigger.
    Phones that only wait for One UI 8 share one "not yet" reply."""
    cmds = filters(entries, "")[:1]  # the "which phones" overview
    later, later_trig = [], []
    # A supported phone outside every series would lose its reply (and get a /stop) without a word:
    # the S22s did, between their OxygenOS 16 profiles (0.4.67) and 0.4.83.
    alone = [name for name, variants in entries
             if not all(l[0] == "🕓" for _, ls in variants for l in ls) and not any(re.match(rx, name) for _, _, rx in GROUPS)]
    assert not alone, ("no Rose series for", alone)
    for key, title, rx in GROUPS:
        body, trig = [], []
        for name, variants in entries:
            if not re.match(rx, name):
                continue
            if all(l[0] == "🕓" for _, ls in variants for l in ls):
                continue
            short = name.replace("Galaxy ", "")
            for v, ls in variants:
                parts = v.split(", ")
                fam = next((f for f, k in (("Snapdragon", "Snapdragon"), ("Exynos", "Exynos"), ("MediaTek", "Helio"),
                                           ("MediaTek", "Dimensity")) if k in v), "")
                net = [x for x in parts[1:] if x in ("4G", "5G")]
                label = short if len(variants) == 1 and name not in ONE_CHIP else f"{short} ({', '.join([parts[0].replace(' (not ', ', not ').rstrip(')')] + net + ([fam] if fam else []))})"
                body.append(f"{label}: " + " · ".join(l[3] for l in ls))
            trig += triggers(name)
        if not body:
            continue
        reply = f"📱 OneOS on {title}\n{LEGEND}\n\n" + "\n".join(body) + \
            "\n\nTried one? Tell us from the OneOS app: Send to the OneOS team."
        cmds.append("/filter (" + ", ".join(f'"{t}"' if " " in t else t for t in trig) + ") " + reply)
    for name, variants in entries:
        if all(l[0] == "🕓" for _, ls in variants for l in ls):
            ls = variants[0][1]
            later.append(f"{name.replace('Galaxy ', '')}: {ls[0][3][2:]}")
            later_trig += triggers(name)
    if later:
        cmds.append("/filter (" + ", ".join(f'"{t}"' if " " in t else t for t in later_trig) + ") 🕓 Not yet on OneOS\n"
                    "OneOS systems are Android 16 (One UI 8) and Android 17 (One UI 9), so a phone needs One UI 8 or newer "
                    "(tablets are not supported yet). "
                    "What the findings sent from these showed:\n\n" + "\n".join(later)
                    + "\n\nGot One UI 8 or 9 now? Send findings again from OneOS Probe.")
    for c in cmds:
        assert len(c) < 4000, (len(c), c[:60])
    return cmds


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--devices", default="docs/devices.json")
    ap.add_argument("--db", default="out/reports/db/reports.jsonl")
    ap.add_argument("--md", default="docs/devices.md")
    ap.add_argument("--filters", default="out/telegram/rose_filters.txt")
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--per-phone", action="store_true", help="one Rose reply per phone instead of one per series")
    ap.add_argument("--link", default="", help="the public docs/devices.md URL, once published")
    ap.add_argument("--match", choices=("exact", "anywhere"), default="exact",
                    help="exact (default): a phone's reply only for a message that is just its name "
                         "(Rose's exact: filters); anywhere: also inside any sentence (Rose's default)")
    ap.add_argument("--upcoming", default="", help="profile ids only in the next, unreleased app")
    ap.add_argument("--next", default="", help="that app's version")
    ap.add_argument("--waiting", default="reports/waiting.json")
    ap.add_argument("--scan", action="store_true", help="list findings from phones in neither list, then stop")
    ap.add_argument("--inbox", default="out/reports/inbox")
    ap.add_argument("--in-group", default="reports/rose_triggers.txt",
                    help="the triggers pasted into the group last time (one per line): dropped ones get a /stop")
    a = ap.parse_args()
    today = date.today().isoformat()
    devices = json.load(open(a.devices))
    waiting = json.load(open(a.waiting))["phones"] if os.path.exists(a.waiting) else []
    if a.scan:
        return scan(devices, waiting, a.inbox)
    upcoming = {x for x in a.upcoming.split(",") if x}
    if upcoming and not a.next:
        ap.error("--upcoming needs --next")
    entries = build(devices, recent_reports(a.db, a.days), upcoming, a.next, waiting)
    open(a.md, "w").write(markdown(entries, today) + "\n")
    os.makedirs(os.path.dirname(a.filters), exist_ok=True)
    global LINK
    LINK = a.link
    cmds = filters(entries, today) if a.per_phone else filters_grouped(entries)
    if a.match == "exact":
        cmds = [exact(c) for c in cmds]
    raw = [t.strip().strip('"') for c in cmds for t in re.match(r"/filter \(([^)]*)\)", c).group(1).split(",")]
    trig = [t.removeprefix("exact:") for t in raw]
    assert len(trig) == len(set(trig)), "a trigger in two filters"
    old_raw = [l.strip() for l in open(a.in_group)] if os.path.exists(a.in_group) else []
    old = [l.removeprefix("exact:") for l in old_raw]
    dropped = sorted(set(old) - set(trig) - {""})
    # A trigger that changes type (plain <-> exact:) is removed first, so its old filter cannot
    # stay beside the new one.
    retyped = sorted(set(old_raw) - set(raw) - {""} - set(dropped))
    dropped = sorted(set(dropped) | set(retyped))
    if dropped:  # a trigger no longer generated would keep its old reply in the group
        cmds.insert(0, "/stop (" + ", ".join(f'"{t}"' if " " in t else t for t in dropped) + ")")
    with open(a.filters, "w") as f:
        f.write("\n\n".join(cmds) + "\n")
    with open(os.path.join(os.path.dirname(a.filters), "rose_triggers.txt"), "w") as f:
        f.write("\n".join(raw) + "\n")
    # Free Rose: 200 filters per chat, and every trigger is one.
    print(f"{len(entries)} phones: {a.md}; {len(cmds)} commands, {len(trig)} triggers of Rose's 200"
          f"{f', /stop for {len(dropped)} dropped' if dropped else ''} in {a.filters}")


if __name__ == "__main__":
    main()
