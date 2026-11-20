#!/usr/bin/env python3
"""OneOS reports through Telegram (0.5.24): the OneOSReports group, read by @OneOSReportsBot.

The app makes the report zip (the redacted log bundle plus `oneos-report.json`, the record the
Send screen filled in) and shares it into the OneOSReports group from the user's own Telegram:
no key, token or server address in the app, and Telegram itself says who posted it. The group
lets members post files only (slow mode 5 minutes, joining by request). This bot, logged in as
@OneOSReportsBot over MTProto with XGram's API app (no 20 MB download limit, no open port, no
Cloudflare), then for every post:

  * deletes anything that is not a OneOS report zip;
  * deletes the post and bans the sender when they are not a member of the main OneOS group;
  * deletes posts past DAILY_MAX a day from one account;
  * downloads the zip, reads its record and files it exactly like reports/pull.py did
    (out/reports/inbox/<day>/<reportId>/ with report.json and the zip, db/reports.jsonl);
    a bundle of random characters (pull.implausible) goes to suspect/ and its post is deleted;
  * posts it again as one card (the same file, the summary as its caption) and deletes the user's post.

Join requests to the reports group are approved for members of the main group, declined otherwise.

    reports/tgbot.py [--dest DIR]

Reads ~/.oneos-signin-bot (the bot token), ~/.oneos-tg-api (api_id, api_hash on two lines),
~/.oneos-reports-group (the reports group id) and ~/.oneos-tg-group (chat_id= of the main group),
never printing them. Session and state live in ~/.oneos-tgbot/. One copy runs at a time (flock).
"""
import argparse
import asyncio
import datetime
import fcntl
import hashlib
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull  # noqa: E402  (implausible, session_app, the inbox layout)
import notify  # noqa: E402  (findings_message: the Probe card text)

from telethon import TelegramClient, events, functions, types  # noqa: E402
from telethon.errors import UserNotParticipantError  # noqa: E402

HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".oneos-tgbot")
DEFAULT_DEST = pull.DEFAULT_DEST
DAILY_MAX = 5
MAX_BYTES = 200 * 1024 * 1024
RECORD = "oneos-report.json"
NAME = re.compile(r"^oneos-report-[A-Za-z0-9_-]{4,80}\.zip$")
# The session logs zip the app also shares (Logs > Share): no record of ours, its own report.json inside.
LOGS = re.compile(r"^oneos-logs-([A-Za-z0-9-]{4,40})(?: ?\(\d+\))?\.zip$")
# The OneOS Probe's findings zip (FindingsBundle.kt): findings-<model>-<date>.zip, report.json schema oneos.findings/1.
FINDINGS = re.compile(r"^findings-[A-Za-z0-9_.-]{1,60}-\d{4}-\d{2}-\d{2}(?: ?\(\d+\))?\.zip$")
HOW = ("Only OneOS report zips go here. In OneOS open the session, tap Send report, "
       "then pick this group in Telegram. The logs zip from Share and the Probe's findings zip work too.")
ID_OK = set("abcdefghijklmnopqrstuvwxyz0123456789-")
START = {"home": "reached the home screen", "logo": "stuck on the boot logo", "black": "black screen", "back": "came back by itself"}


def secret(name, lines=1):
    with open(os.path.join(HOME, name)) as f:
        v = f.read().split()
    if len(v) < lines:
        sys.exit(f"~/{name} is incomplete")
    return v[:lines] if lines > 1 else v[0]


def log(msg):
    print(f"{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}", flush=True)


class Counts:
    """Posts per account per UTC day, on disk so a restart does not reset them."""

    def __init__(self, path):
        self.path = path
        try:
            with open(path) as f:
                self.d = json.load(f)
        except (OSError, ValueError):
            self.d = {}

    def take(self, uid):
        day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        self.d = {k: v for k, v in self.d.items() if k.endswith(day)}
        k = f"{uid}:{day}"
        if self.d.get(k, 0) >= DAILY_MAX:
            return False
        self.d[k] = self.d.get(k, 0) + 1
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.d, f)
        os.replace(tmp, self.path)
        return True


def read_record(data):
    """The app's record inside the posted zip, or None. Untrusted: bounded read of one member."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if RECORD not in z.namelist() or z.getinfo(RECORD).file_size > 64 * 1024:
                return None
            r = json.loads(z.read(RECORD).decode("utf-8", "replace"))
    except (zipfile.BadZipFile, ValueError):
        return None
    if not isinstance(r, dict) or r.get("schema") != "oneos.report/1":
        return None
    rid = r.get("reportId")
    if not isinstance(rid, str) or not 4 <= len(rid) <= 80 or set(rid) - ID_OK:
        return None
    return r


def read_logs(data, sid):
    """A record for a bare session logs zip (oneos.logbundle/1 report.json inside), or None."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.endswith("/report.json") or n == "report.json"]
            if len(names) != 1 or z.getinfo(names[0]).file_size > 256 * 1024:
                return None
            b = json.loads(z.read(names[0]).decode("utf-8", "replace"))
    except (zipfile.BadZipFile, ValueError):
        return None
    if not isinstance(b, dict) or b.get("schema") != "oneos.logbundle/1":
        return None
    rid = "logs-" + "".join(c for c in sid.lower() if c in ID_OK)[:40]
    out = b.get("outcome") if isinstance(b.get("outcome"), dict) else {}
    s = lambda v: v if isinstance(v, str) and len(v) <= 200 else None
    return {
        "schema": "oneos.report/1", "reportId": rid, "kind": "session-logs",
        "image": s(b.get("image")), "phone": {"label": s(b.get("profile"))},
        "app": b.get("app") if isinstance(b.get("app"), dict) else {},
        "note": " ".join(x for x in (s(out.get("kind")), s(b.get("bootReason"))) if x),
        "logs": {"kind": "session", "name": f"oneos-logs-{sid}.zip", "bytes": len(data)},
    }


def read_findings(data):
    """A record for a Probe findings zip (oneos.findings/1 report.json inside), or None.

    The report id is the zip's SHA-256 (first 16), so the same zip sent again is caught as a repeat."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.endswith("/report.json") or n == "report.json"]
            if len(names) != 1 or z.getinfo(names[0]).file_size > 2 * 1024 * 1024:
                return None
            b = json.loads(z.read(names[0]).decode("utf-8", "replace"))
    except (zipfile.BadZipFile, ValueError):
        return None
    if not isinstance(b, dict) or b.get("schema") != "oneos.findings/1":
        return None
    s = lambda v: v if isinstance(v, str) and len(v) <= 200 else None
    dev = b.get("device") if isinstance(b.get("device"), dict) else {}
    app = b.get("app") if isinstance(b.get("app"), dict) else {}
    return {
        "schema": "oneos.report/1", "reportId": "findings-" + hashlib.sha256(data).hexdigest()[:16],
        "kind": "probe-findings", "phone": {"model": s(dev.get("model")), "label": s(dev.get("device"))},
        "app": {k: app.get(k) for k in ("id", "version", "versionCode") if isinstance(app.get(k), (str, int))},
        "note": " ".join(x for x in ("probe verdict", s(b.get("verdictLabel")) or s(b.get("verdict"))) if x),
        "logs": {"kind": "probe", "bytes": len(data)},
    }


def findings_card(data, r, who):
    """The Phone-reports text (notify.findings_message) for a findings zip, else the plain summary."""
    try:
        if not os.path.isfile(os.path.join(notify.REPO, "docs", "devices.json")):
            # Deployed as out/tgbot/: the checkout's docs/ are two levels up.
            up = os.path.dirname(notify.REPO)
            if os.path.isfile(os.path.join(up, "docs", "devices.json")):
                notify.REPO = up
        text = notify.findings_message(io.BytesIO(data), r)
    except Exception:  # noqa: BLE001 (the card text is optional)
        text = None
    if not text:
        return summary(r, who)
    return f"{text}\nreport {r['reportId']} · {who}"


def summary(r, who):
    phone = (r.get("phone") or {}).get("label") or (r.get("phone") or {}).get("model") or "?"
    lines = [f"📱 {phone}"]
    if r.get("imageName") or r.get("image"):
        lines.append(f"💿 {r.get('imageName') or r.get('image')}")
    app = (r.get("app") or {}).get("version")
    c = r.get("checklist") or {}
    if c.get("start"):
        lines.append(f"🚀 {START.get(c['start'], c['start'])}")
    items = c.get("items") or {}
    works = [k for k, v in items.items() if v == "works"]
    probs = [k for k, v in items.items() if v == "problem"]
    if works:
        lines.append("✅ " + ", ".join(works))
    if probs:
        lines.append("⚠️ " + ", ".join(probs))
    note = (r.get("note") or "").strip()
    if note:
        lines.append("📝 " + (note[:400] + "…" if len(note) > 400 else note))
    lines.append(f"OneOS {app} · report {r['reportId']} · {who}")
    return "\n".join(lines)


def file_report(dest, r, data, zname):
    """Like pull.collect: report.json and the zip under inbox/ (or suspect/), one line in db/reports.jsonl."""
    rid = r["reportId"]
    day = r["receivedAt"][:10]
    why = pull.implausible(data, r.get("logs"))
    box = "inbox"
    if why:
        r["suspect"] = why
        box = "suspect"
    ran = pull.session_app(data)
    if ran:
        r["sessionApp"] = ran
    folder = os.path.join(dest, box, day, rid)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, zname), "wb") as f:
        f.write(data)
    with open(os.path.join(folder, "report.json"), "w") as f:
        json.dump(r, f, indent=2)
        f.write("\n")
    if not why:
        db = os.path.join(dest, "db", "reports.jsonl")
        os.makedirs(os.path.dirname(db), exist_ok=True)
        with open(db, "a") as f:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    return box, folder, why


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", default=DEFAULT_DEST)
    a = ap.parse_args()
    os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
    lock = open(os.path.join(STATE_DIR, "lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return  # already running
    api_id, api_hash = secret(".oneos-tg-api", 2)
    token = secret(".oneos-signin-bot")
    reports_id = int(secret(".oneos-reports-group"))
    with open(os.path.join(HOME, ".oneos-tg-group")) as f:
        main_id = int(dict(l.strip().split("=", 1) for l in f if "=" in l)["chat_id"])
    counts = Counts(os.path.join(STATE_DIR, "counts.json"))
    client = TelegramClient(os.path.join(STATE_DIR, "bot"), int(api_id), api_hash)
    await client.start(bot_token=token)
    reports = await client.get_input_entity(reports_id)
    main_group = await client.get_input_entity(main_id)
    log("running")

    async def member(uid):
        try:
            p = await client(functions.channels.GetParticipantRequest(main_group, uid))
        except UserNotParticipantError:
            return False
        return not isinstance(p.participant, (types.ChannelParticipantBanned, types.ChannelParticipantLeft))

    async def tell(msg, text):
        """A short reply to the poster, removed again after two minutes so the group stays reports only."""
        try:
            m = await msg.reply(text)
        except Exception:
            return
        async def later():
            await asyncio.sleep(120)
            try:
                await m.delete()
            except Exception:
                pass
        asyncio.ensure_future(later())

    async def drop(msg, why, ban=False, say=None):
        if say:
            await tell(msg, say)
        await msg.delete()
        if ban:
            await client.edit_permissions(reports, msg.sender_id, view_messages=False)
        log(f"dropped {msg.id} from {msg.sender_id}: {why}{' (banned)' if ban else ''}")

    @client.on(events.NewMessage(chats=reports_id))
    async def on_post(ev):
        msg = ev.message
        if msg.out or not msg.sender_id or msg.sender_id < 0:
            return
        sender = await msg.get_sender()
        if getattr(sender, "bot", False):
            return
        doc = msg.document
        name = next((x.file_name for x in (doc.attributes if doc else []) if isinstance(x, types.DocumentAttributeFilename)), "")
        logs = LOGS.match(name or "")
        probe = FINDINGS.match(name or "")
        if not doc or not (NAME.match(name or "") or logs or probe) or doc.size > MAX_BYTES:
            return await drop(msg, f"not a report ({name or 'no file'})", say=HOW)
        if not await member(msg.sender_id):
            return await drop(msg, "not in the OneOS group", ban=True)
        if not counts.take(msg.sender_id):
            return await drop(msg, "daily limit", say=f"{DAILY_MAX} reports a day is the most from one account, send more tomorrow.")
        data = await client.download_media(msg, file=bytes)
        r = read_logs(data, logs.group(1)) if logs else read_findings(data) if probe else read_record(data)
        if r is None:
            return await drop(msg, "no OneOS record in the zip", say="That zip has no OneOS record in it. " + HOW)
        if probe:
            name = re.sub(r" ?\(\d+\)(?=\.zip$)", "", name)
            r["logs"]["name"] = name
        if logs or probe:
            if logs:
                name = f"oneos-logs-{logs.group(1)}.zip"
            if any(os.path.isdir(os.path.join(a.dest, "inbox", d, r["reportId"])) for d in (os.listdir(os.path.join(a.dest, "inbox")) if os.path.isdir(os.path.join(a.dest, "inbox")) else [])):
                return await drop(msg, f"already have {r['reportId']}", say="Got this one already, thanks.")
        who = f"@{sender.username}" if getattr(sender, "username", None) else f"id {msg.sender_id}"
        r["receivedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        why = pull.implausible(data, r.get("logs"))
        if why:
            r["tg"] = {"id": msg.sender_id, "username": getattr(sender, "username", None)}
            _, folder, _ = file_report(a.dest, r, data, name)
            return await drop(msg, f"suspect bundle ({why}) -> {folder}", ban=True)
        # One card per report: the same file (Telegram reuses it, nothing is uploaded again) with the whole
        # summary as its caption, posted by the bot; the user's own post goes.
        text = findings_card(data, r, who) if probe else summary(r, who)
        card = await client.send_file(reports, msg.media, caption=text[:1024])
        await msg.delete()
        r["tg"] = {"id": msg.sender_id, "username": getattr(sender, "username", None), "post": f"https://t.me/c/{str(reports_id)[4:]}/{card.id}"}
        box, folder, _ = file_report(a.dest, r, data, name)
        log(f"{box} {r['reportId']} from {who} -> {folder}")

    @client.on(events.Raw(types.UpdateBotChatInviteRequester))
    async def on_join(u):
        peer = getattr(u.peer, "channel_id", None)
        if peer is None or -1000000000000 - peer != reports_id:
            return
        ok = await member(u.user_id)
        await client(functions.messages.HideChatJoinRequestRequest(reports, u.user_id, approved=ok))
        log(f"join request {u.user_id}: {'approved' if ok else 'declined (not in the OneOS group)'}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
