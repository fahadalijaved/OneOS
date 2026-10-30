#!/usr/bin/env python3
"""Collect the reports sent from the OneOS app (reports/worker.js) onto the team's server.

    reports/pull.py [--dest DIR] [--keep]

For each record in the service: fetch it, fetch its zip's parts, join them and
check the SHA-256 the app sent, then file it as

    DIR/inbox/<received date>/<report id>/report.json   (the record)
    DIR/inbox/<received date>/<report id>/<zip name>    (the logs or findings, if any)

and add the record to DIR/db/reports.jsonl (every report ever collected, one
line each: docs/compatibility.md is counted from it). Only then are the record
and its parts deleted from the service (--keep leaves them). A report whose
parts are missing or do not match is left in the service and tried again next
time; the service drops anything after 30 days.

Reads the service's address from ~/.oneos-reports-url and its admin key from
~/.oneos-reports-admin-key (mode 600; never printed). Prints one line per report
collected. The zips are untrusted data: unpack each into its own folder and
read them with python -I, as with any upload.
"""
import argparse
import hashlib
import io
import zipfile
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~")
DEFAULT_DEST = "/srv/projects/OneOS/out/reports"
ID_OK = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def read_secret(name):
    path = os.path.join(HOME, name)
    with open(path) as f:
        value = f.read().strip()
    if not value:
        sys.exit(f"{path} is empty")
    return value


class Service:
    def __init__(self, base, key):
        self.base = base.rstrip("/")
        self.key = key

    def call(self, method, path, **params):
        url = f"{self.base}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, method=method, headers={"Authorization": f"Bearer {self.key}", "User-Agent": "oneos-reports-pull/1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()

    def keys(self, prefix):
        cursor, out = None, []
        while True:
            params = {"prefix": prefix}
            if cursor:
                params["cursor"] = cursor
            page = json.loads(self.call("GET", "/v1/list", **params))
            out += [k["name"] for k in page["keys"]]
            cursor = page.get("cursor")
            if not cursor:
                return out


def session_app(data):
    """The app of the log bundle in `data` (its own report.json), or None.

    The zip is a tester's upload: read the one member by exact name, bounded,
    and never extract to disk.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(bytes(data))) as z:
            names = [n for n in z.namelist() if n.endswith("/report.json") or n == "report.json"]
            if len(names) != 1:
                return None
            info = z.getinfo(names[0])
            if info.file_size > 256 * 1024:
                return None
            app = json.loads(z.read(names[0]).decode("utf-8", "replace")).get("app")
    except Exception:
        return None
    if not isinstance(app, dict):
        return None
    v, c = app.get("version"), app.get("versionCode")
    if not isinstance(v, str) or not re.fullmatch(r"[0-9A-Za-z.+_-]{1,32}", v):
        return None
    return {"version": v, "versionCode": c if isinstance(c, int) else None}


def collect(svc, name, dest, keep):
    record = json.loads(svc.call("GET", "/v1/get", key=name))
    rid = record.get("reportId", "")
    if not rid or set(rid) - ID_OK:
        return f"skipped {name}: bad report id"
    day = (record.get("receivedAt") or "unknown")[:10]
    folder = os.path.join(dest, "inbox", day, rid)
    os.makedirs(folder, exist_ok=True)
    logs = record.get("logs")
    parts = []
    if logs:
        zname = os.path.basename(logs.get("name") or "logs.zip")
        data = bytearray()
        for i in range(int(logs["parts"])):
            key = f"part:{rid}:{i}"
            try:
                data += svc.call("GET", "/v1/get", key=key)
            except urllib.error.HTTPError as e:
                return f"waiting {rid}: part {i} not there ({e.code})"
            parts.append(key)
        if len(data) != logs["bytes"] or hashlib.sha256(data).hexdigest() != logs["sha256"]:
            return f"waiting {rid}: the parts do not match the record (size or SHA-256)"
        with open(os.path.join(folder, zname), "wb") as f:
            f.write(data)
        # The version the SESSION ran on, which is not always the version that
        # sent it: a Z Fold7 report of 2026-10-30 was sent from 0.4.31 and held a
        # 0.4.19 ColorOS session the phone still had stored, so the compatibility
        # table credited an old run to the new release. The log bundle records its
        # own app in report.json; keep it beside the record under sessionApp.
        ran = session_app(data)
        if ran:
            record["sessionApp"] = ran
    with open(os.path.join(folder, "report.json"), "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    db = os.path.join(dest, "db", "reports.jsonl")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    seen = set()
    if os.path.exists(db):
        with open(db) as f:
            seen = {json.loads(line).get("reportId") for line in f if line.strip()}
    if rid not in seen:
        with open(db, "a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    if not keep:
        svc.call("POST", "/v1/delete", key=name)
        for key in parts:
            svc.call("POST", "/v1/delete", key=key)
    phone = (record.get("phone") or {}).get("label") or (record.get("phone") or {}).get("model")
    start = (record.get("checklist") or {}).get("start")
    kind = "findings" if logs and logs.get("kind") == "probe" else "full log" if logs and logs.get("full") else "short log"
    size = f"{logs['bytes'] / 1048576:.1f} MB {kind}" if logs else "no logs"
    # Say loudly when the session predates the app that sent it: "Send to the
    # OneOS team" sends the session the phone has stored, which can be many
    # releases old (Z Fold7, 2026-10-30: 0.4.31 sent a 0.4.19 session). Those are
    # not evidence about the build we just shipped and must not be read as such.
    sent = record["app"]["version"]
    ran = (record.get("sessionApp") or {}).get("version")
    ver = f"OneOS {sent}"
    if ran and ran.split("-")[0] != sent.split("-")[0]:
        ver = f"OneOS {sent} !! STALE SESSION: it ran on {ran}, not {sent} !!"
    return f"new {rid}: {phone}, {record.get('imageName') or record.get('image')}, {ver}, start {start}, {size} -> {folder}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", default=DEFAULT_DEST)
    ap.add_argument("--keep", action="store_true", help="leave the reports in the service")
    a = ap.parse_args()
    svc = Service(read_secret(".oneos-reports-url"), read_secret(".oneos-reports-admin-key"))
    for name in svc.keys("report:"):
        try:
            print(collect(svc, name, a.dest, a.keep), flush=True)
        except (urllib.error.URLError, ValueError, KeyError) as e:
            print(f"error {name}: {e}", flush=True)


if __name__ == "__main__":
    main()
