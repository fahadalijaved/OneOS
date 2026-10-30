#!/usr/bin/env python3
"""docs/compatibility.md from the collected reports (public: counts only).

    reports/compat.py [--db out/reports/db/reports.jsonl] [--out docs/compatibility.md]

One table per OneOS version (newest first; the series APKs of a version count
together), one row per phone and system, from every report with a checklist:
how many reports, how many reached the home screen, and per item how many said
it works of those that tried it. Notes, contacts, models and ids never appear.
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import date

ITEMS = [
    ("screen", "Screen"), ("wifi", "Wi-Fi"), ("data", "Mobile data"), ("calls", "Calls"), ("sms", "SMS"),
    ("bluetooth", "Bluetooth"), ("sound", "Sound"), ("camera", "Camera"), ("google", "Google"),
    ("location", "Location"), ("back", "Back to One UI"), ("heat", "Heat"), ("fold", "Both screens"),
]
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+()_-]{0,47}$")


def version_of(app):
    """0.4.29-s25 -> 0.4.29 (the series APKs of one version are one release)."""
    return re.sub(r"-(fold|s26|s25|probe)$", "", app.get("version", "?"))


def ran_on(record):
    """The version the session ran on, which is not always the one that sent it.

    "Send to the OneOS team" sends the session the phone has stored, and that can
    predate the installed app: a Z Fold7 report of 2026-10-30 came from 0.4.31
    carrying a 0.4.19 session. reports/pull.py copies the log bundle's own app
    into sessionApp; count by that where it exists, so a release is credited only
    with runs that were actually made on it.
    """
    return version_of(record.get("sessionApp") or record.get("app") or {})


def cell(works, tried):
    if tried == 0:
        return "–"
    mark = "✅" if works == tried else "❌" if works == 0 else "⚠️"
    return f"{mark} {works}/{tried}"


def safe(label, fallback):
    return label if isinstance(label, str) and LABEL.match(label) else fallback


def table(records):
    rows = defaultdict(lambda: {"n": 0, "home": 0, "start": 0, "items": defaultdict(lambda: [0, 0]), "last": ""})
    codes = {}
    for r in records:
        c = r.get("checklist")
        # A session's report only: OneOS Probe's phone reports have no session and no answers.
        if not c or not r.get("sessionId"):
            continue
        v = ran_on(r)
        codes[v] = max(codes.get(v, 0), r.get("app", {}).get("versionCode", 0))
        phone = safe((r.get("phone") or {}).get("label"), "Other phone")
        system = safe(r.get("imageName"), "Other system")
        row = rows[(v, phone, system)]
        row["n"] += 1
        if c.get("start"):
            row["start"] += 1
            row["home"] += c["start"] == "home"
        for key, answer in (c.get("items") or {}).items():
            if answer in ("works", "problem"):
                row["items"][key][1] += 1
                row["items"][key][0] += answer == "works"
        row["last"] = max(row["last"], (r.get("receivedAt") or "")[:10])
    return rows, codes


def render(records, today=None):
    rows, codes = table(records)
    out = [
        "# OneOS compatibility",
        "",
        "What testers reported from the OneOS app (**Send to the OneOS team** on the Last session screen), "
        "by OneOS version, phone and system. Each cell is how many reports said it works, of the reports that tried it "
        "(✅ all, ⚠️ some, ❌ none, – nobody tried it yet). **Started** counts the reports that reached the home screen. "
        "Only the answers are counted here: no names, notes or phone details.",
        "",
        f"Updated {today or date.today().isoformat()}. Every system is still experimental: read the warnings in the [README](../README.md) first.",
        "",
    ]
    if not rows:
        out += ["No reports yet.", ""]
        return "\n".join(out)
    head = ["Phone", "System", "Reports", "Started"] + [label for _, label in ITEMS] + ["Last report"]
    for v in sorted(codes, key=lambda x: codes[x], reverse=True):
        out += [f"## OneOS {v}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for (rv, phone, system), row in sorted(rows.items()):
            if rv != v:
                continue
            cells = [phone, system, str(row["n"]), cell(row["home"], row["start"])]
            cells += [cell(*row["items"][key]) if key in row["items"] else "–" for key, _ in ITEMS]
            cells.append(row["last"] or "–")
            out.append("| " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="/srv/projects/OneOS/out/reports/db/reports.jsonl")
    ap.add_argument("--out", default="docs/compatibility.md")
    a = ap.parse_args()
    records = []
    try:
        with open(a.db) as f:
            records = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        pass
    with open(a.out, "w") as f:
        f.write(render(records))
    print(f"{a.out}: {len(records)} reports")


if __name__ == "__main__":
    main()
