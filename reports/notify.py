#!/usr/bin/env python3
"""A Phone reports message with what a probe's findings say about the phone (owner, 2026-11-07).

The report service's own ping (reports/worker.js) has only the model and the app version, and
testers send findings from Probe builds of every age. pull.py calls findings_message() for each
new findings zip it collects and posts the result to the group's Phone reports topic through the
group's bot: model and codename, chip, One UI, Android, kernel, root, bootloader, CPU features,
the probe's blocks and warnings, and what OneOS makes of it (a profile, the waiting list, or new
and on One UI 9 or not). Nothing personal: no serial, ids, SSID, note or contact (the probe
redacts those from summary.txt already, and none of these lines carries them).

    reports/notify.py <findings.zip> [--send]   prints the message (and sends it with --send)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def _summary(zf):
    names = zf.namelist()
    s = next((n for n in names if n.endswith("/summary.txt") or n == "summary.txt"), None)
    u = next((n for n in names if n.endswith("cpu/uname.txt")), None)
    text = zf.read(s).decode(errors="replace") if s else ""
    uname = zf.read(u).decode(errors="replace") if u else ""
    return text, uname


def _field(text, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def _status(model, code, oneui_code):
    """What OneOS makes of the phone: its profile, the waiting list, or new."""
    try:
        devices = json.load(open(os.path.join(REPO, "docs", "devices.json")))["phones"]
        waiting = json.load(open(os.path.join(HERE, "waiting.json")))["phones"]
    except (OSError, ValueError, KeyError):
        devices, waiting = [], []
    for p in devices:
        if code == p.get("codename") and any(model.startswith(m.strip()) for m in p["model"].split(",")):
            systems = ", ".join(s["label"].split(",")[0] for s in p["systems"])
            return f"✅ Supported: {p['label']} ({systems})"
    for w in waiting:
        if any(model.startswith(m) for m in w["models"]):
            return f"🕓 On the waiting list ({w['name']}): needs One UI 9"
    if oneui_code >= 90000:
        return "🆕 New phone on One UI 9: a profile can be added"
    return "🕓 Not yet: on One UI 8.x or older, OneOS needs One UI 9 (Android 17)"


def findings_message(zip_path, record=None):
    with zipfile.ZipFile(zip_path) as zf:
        text, uname = _summary(zf)
    if not text:
        return None
    phone = _field(text, "Phone")
    m = re.match(r"(\S+) \(([^)]*)\)", phone)
    model, code = (m.group(1), m.group(2)) if m else (phone, "")
    oneui = _field(text, "One UI")
    oc = re.search(r"\((\d+)\)", oneui)
    oneui_code = int(oc.group(1)) if oc else 0
    android = _field(text, "Android")
    build = _field(text, "Build")
    bm = re.search(r"/([A-Za-z0-9_.]+):(?:user|userdebug|eng)/", build)
    incr = bm.group(1) if bm else ""
    kernel = uname.split()[2] if len(uname.split()) > 2 else ""
    root = _field(text, "Root")
    root_short = root.split(";")[0] if root else "none"
    manager = re.search(r"(kernelsu ksud [^;)]*\)?|magisk[^;]*|apatch[^;]*)", root, re.I)
    boot = _field(text, "Boot")
    feats = _field(text, "Features")
    verdict = _field(text, "Verdict")
    blocks = re.findall(r"^\s*\[(BLOCK|WARN )\]\s*(.+)$", text, re.M)
    am = re.search(r"^App (\S+)", text, re.M)
    app = (record or {}).get("app", {}).get("version") or (am.group(1) if am else "?")
    lines = [f"🔎 Findings: {model} ({code}) · {app}",
             f"Chip: {_field(text, 'Chip')}",
             f"One UI {oneui.split(' ')[0] or '?'} · Android {android.split(',')[0] or '?'} · {incr}",
             f"Kernel: {kernel or '?'}",
             f"Root: {root_short}{' (' + manager.group(1) + ')' if manager else ''}",
             f"Boot: {boot or '?'}",
             f"CPU: {feats.replace(', BF16', ' | BF16') if feats else '?'}",
             f"Probe verdict: {verdict or '?'}"]
    for kind, what in blocks[:6]:
        lines.append(f"{'⛔' if kind == 'BLOCK' else '⚠️'} {what}")
    lines.append(_status(model, code, oneui_code))
    return "\n".join(lines)


def send(text):
    """sendMessage to the Phone reports topic; the token stays in a file, never in argv."""
    token = open(os.path.expanduser("~/.oneos-tg-bot")).read().strip()
    ids = dict(l.strip().split("=", 1) for l in open(os.path.expanduser("~/.oneos-tg-group")) if "=" in l)
    data = urllib.parse.urlencode({"chat_id": ids["chat_id"], "message_thread_id": ids["reports_thread"],
                                   "text": text, "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("ok", False)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    msg = findings_message(sys.argv[1])
    print(msg)
    if "--send" in sys.argv[2:] and msg:
        print("sent" if send(msg) else "not sent")
