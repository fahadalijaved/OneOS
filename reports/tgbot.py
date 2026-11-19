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
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pull  # noqa: E402  (implausible, session_app, the inbox layout)

from telethon import TelegramClient, events, functions, types  # noqa: E402
from telethon.errors import UserNotParticipantError  # noqa: E402

HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".oneos-tgbot")
DEFAULT_DEST = pull.DEFAULT_DEST
DAILY_MAX = 5
MAX_BYTES = 200 * 1024 * 1024
RECORD = "oneos-report.json"
NAME = re.compile(r"^oneos-report-[A-Za-z0-9_-]{4,80}\.zip$")
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

    async def drop(msg, why, ban=False):
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
        if not doc or not NAME.match(name or "") or doc.size > MAX_BYTES:
            return await drop(msg, f"not a report ({name or 'no file'})")
        if not await member(msg.sender_id):
            return await drop(msg, "not in the OneOS group", ban=True)
        if not counts.take(msg.sender_id):
            await msg.reply(f"{DAILY_MAX} reports a day is the most from one account, send more tomorrow.")
            return await drop(msg, "daily limit")
        data = await client.download_media(msg, file=bytes)
        r = read_record(data)
        if r is None:
            return await drop(msg, "no OneOS record in the zip")
        who = f"@{sender.username}" if getattr(sender, "username", None) else f"id {msg.sender_id}"
        r["receivedAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        why = pull.implausible(data, r.get("logs"))
        if why:
            r["tg"] = {"id": msg.sender_id, "username": getattr(sender, "username", None)}
            _, folder, _ = file_report(a.dest, r, data, name)
            return await drop(msg, f"suspect bundle ({why}) -> {folder}", ban=True)
        # One card per report: the same file (Telegram reuses it, nothing is uploaded again) with the whole
        # summary as its caption, posted by the bot; the user's own post goes.
        card = await client.send_file(reports, msg.media, caption=summary(r, who)[:1024])
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
