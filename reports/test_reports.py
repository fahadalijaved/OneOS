"""python3 -m unittest discover -s reports: the collector and the compatibility table."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))
import compat  # noqa: E402
import pull  # noqa: E402


def record(rid="8aea312c31b8821d-3f2a", **over):
    r = {
        "schema": "oneos.report/1", "reportId": rid, "receivedAt": "2026-10-30T09:00:00.000Z",
        "app": {"id": "com.fahadali.oneos", "version": "0.4.29-s25", "versionCode": 46, "series": "s25"},
        "phone": {"model": "SM-S938B", "device": "pa3q", "profile": "s-ultra-8750", "label": "Galaxy S25 Ultra"},
        "image": "infinityx41-findx9u", "imageName": "Infinity-X 4.1", "sessionId": "8aea312c31b8821d",
        "checklist": {"start": "home", "items": {"screen": "works", "wifi": "works", "calls": "problem", "camera": "not_tried"}},
        "note": "calls drop", "contact": "@tester", "logs": None,
    }
    r.update(over)
    return r


class FakeService:
    def __init__(self, store):
        self.store = store
        self.deleted = []

    def call(self, method, path, **params):
        if path == "/v1/delete":
            self.deleted.append(params["key"])
            return b"{}"
        if params["key"] not in self.store:
            raise urllib.error.HTTPError("x", 404, "not found", {}, None)
        return self.store[params["key"]]


class PullTest(unittest.TestCase):
    def test_collects_joins_checks_and_deletes(self):
        data = b"PK" + os.urandom(3000)
        logs = {"kind": "session", "name": "oneos-logs-8aea.zip", "full": False, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "parts": 2}
        rid = "8aea312c31b8821d-3f2a"
        name = f"report:2026-10-30T09:00:00.000Z:{rid}"
        svc = FakeService({name: json.dumps(record(logs=logs)).encode(), f"part:{rid}:0": data[:1000], f"part:{rid}:1": data[1000:]})
        with tempfile.TemporaryDirectory() as d:
            line = pull.collect(svc, name, d, keep=False)
            self.assertTrue(line.startswith("new 8aea312c31b8821d-3f2a: Galaxy S25 Ultra, Infinity-X 4.1, OneOS 0.4.29-s25, start home"))
            folder = os.path.join(d, "inbox", "2026-10-30", rid)
            with open(os.path.join(folder, "oneos-logs-8aea.zip"), "rb") as f:
                self.assertEqual(data, f.read())
            self.assertEqual(svc.deleted, [name, f"part:{rid}:0", f"part:{rid}:1"])
            # Collected twice (a retry): one line in the db.
            pull.collect(svc, name, d, keep=True)
            with open(os.path.join(d, "db", "reports.jsonl")) as f:
                self.assertEqual(1, len(f.readlines()))

    def test_waits_for_missing_or_wrong_parts(self):
        data = b"x" * 10
        rid = "8aea312c31b8821d-3f2a"
        name = f"report:t:{rid}"
        good = {"kind": "session", "name": "a.zip", "full": True, "bytes": 10, "sha256": hashlib.sha256(data).hexdigest(), "parts": 1}
        with tempfile.TemporaryDirectory() as d:
            svc = FakeService({name: json.dumps(record(logs=good)).encode()})
            self.assertIn("part 0 not there", pull.collect(svc, name, d, keep=False))
            svc = FakeService({name: json.dumps(record(logs=good)).encode(), f"part:{rid}:0": b"y" * 10})
            self.assertIn("do not match", pull.collect(svc, name, d, keep=False))
            self.assertEqual(svc.deleted, [])
            svc = FakeService({name: json.dumps(record(rid="../../etc-abcd")).encode()})
            self.assertIn("bad report id", pull.collect(svc, name, d, keep=False))


class CompatTest(unittest.TestCase):
    def test_counts_by_version_phone_and_system(self):
        recs = [
            record(),
            record(rid="b-0001", checklist={"start": "home", "items": {"screen": "works", "wifi": "problem", "calls": "problem"}}),
            record(rid="c-0002", checklist={"start": "black", "items": {}}),
            record(rid="d-0003", app={"version": "0.4.28-s26", "versionCode": 45}, phone={"label": "Galaxy S26 Ultra"}),
            record(rid="e-0004", checklist=None),
            record(rid="f-0005", phone={"label": "<script>"}, imageName="| bad |"),
            # OneOS Probe: no session, an empty checklist; not counted.
            record(rid="g-0006", sessionId=None, phone={"label": "Galaxy Z Flip5"}, checklist={"start": None, "items": {"wifi": "not_tried"}}),
        ]
        md = compat.render(recs, today="2026-10-30")
        self.assertLess(md.index("## OneOS 0.4.29"), md.index("## OneOS 0.4.28"))
        row = next(l for l in md.splitlines() if l.startswith("| Galaxy S25 Ultra | Infinity-X 4.1 |"))
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[2:7], ["3", "⚠️ 2/3", "✅ 2/2", "⚠️ 1/2", "–"])
        self.assertEqual(cells[7], "❌ 0/2")
        self.assertIn("| Other phone | Other system |", md)
        self.assertNotIn("Galaxy Z Flip5", md)
        for private in ("calls drop", "@tester", "SM-S938B", "8aea312c", "<script>"):
            self.assertNotIn(private, md)

    def test_no_reports(self):
        self.assertIn("No reports yet.", compat.render([], today="2026-10-30"))
        self.assertEqual("0.4.29", compat.version_of({"version": "0.4.29-fold"}))


if __name__ == "__main__":
    unittest.main()
