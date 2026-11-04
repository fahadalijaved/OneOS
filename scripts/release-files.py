#!/usr/bin/env python3
"""Put every package set's files on the owner's Drive and write app-android/packages/remote.txt.

0.4.41: the APK no longer carries the set files (1.4 GB per series). The app downloads the
files its phone's set needs, by SHA-256, from the owner's Google Drive folder OneOS/files,
where each file is named by its SHA-256. This script:
  1. reads the sets the app packs (app-android/app/build.gradle.kts, packageSets) and their
     lists (app-android/packages/<set>.sha256), checking each built file's hash;
  2. uploads the files Drive does not have yet (rclone remote "gdrive", scope drive.file);
  3. writes packages/remote.txt: "<sha256> <drive file id>" for every set file, sorted.
The folder OneOS is shared by link, so its files are readable without a Google account.
Not on GitHub: the sets hold OEM binaries (Samsung Camera, ColorOS and Xiaomi jars).

Usage: scripts/release-files.py [--dry-run]
Needs ~/bin/rclone (or $RCLONE) and ~/.config/rclone/rclone.conf with the gdrive remote.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADLE = os.path.join(ROOT, "app-android/app/build.gradle.kts")
PACKAGES = os.path.join(ROOT, "app-android/packages")
REMOTE_DIR = "gdrive:OneOS/files"
RCLONE = os.environ.get("RCLONE", os.path.expanduser("~/bin/rclone"))
SHA_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9_][A-Za-z0-9._+-]*)$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rclone(*args):
    r = subprocess.run([RCLONE, *args], capture_output=True, text=True)
    err = "\n".join(l for l in r.stderr.splitlines() if "shared Google Drive client_id" not in l)
    if r.returncode != 0:
        sys.exit(f"rclone {' '.join(args[:2])} failed: {err.strip()}")
    return r.stdout


def sets():
    text = open(GRADLE).read()
    found = re.findall(r'"([a-z0-9-]+)" to \(File\(repoRoot, "([^"]+)"\)', text)
    if not found:
        sys.exit("no packageSets in build.gradle.kts")
    return found


def wanted():
    """sha256 -> built file, for every file of every set (checked against its list)."""
    out = {}
    for sid, d in sets():
        lst = os.path.join(PACKAGES, f"{sid}.sha256")
        for line in open(lst):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            m = SHA_LINE.match(line)
            if not m:
                sys.exit(f"{lst}: not a sha256sum line: {line}")
            sha, name = m.groups()
            path = os.path.join(ROOT, d, name)
            if sha in out:
                continue
            if not os.path.isfile(path):
                sys.exit(f"{sid}: {path} is missing (build the sets first)")
            if sha256(path) != sha:
                sys.exit(f"{sid}: {path} is not the file packages/{sid}.sha256 names")
            out[sha] = path
    return out


def on_drive():
    """name -> Drive id of every file in OneOS/files."""
    listing = json.loads(rclone("lsjson", REMOTE_DIR, "--files-only") or "[]")
    return {e["Name"]: e["ID"] for e in listing}


def main():
    dry = "--dry-run" in sys.argv[1:]
    want = wanted()
    have = on_drive()
    missing = sorted(s for s in want if s not in have)
    size = sum(os.path.getsize(want[s]) for s in missing)
    print(f"{len(want)} set files, {len(missing)} not on Drive yet ({size / 1e9:.2f} GB)")
    if missing and not dry:
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "out")) as tmp:
            for s in missing:
                os.link(want[s], os.path.join(tmp, s))
            rclone("copy", tmp, REMOTE_DIR, "--ignore-existing", "--transfers", "4", "--drive-chunk-size", "128M")
        have = on_drive()
    if dry:
        return
    lost = [s for s in want if s not in have]
    if lost:
        sys.exit(f"{len(lost)} files still not on Drive after the upload, e.g. {lost[0]}")
    lines = [f"{s} {have[s]}" for s in sorted(want)]
    path = os.path.join(PACKAGES, "remote.txt")
    with open(path, "w") as f:
        f.write("# sha256 -> Drive file id (folder OneOS/files), written by scripts/release-files.py\n")
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}: {len(lines)} files")


if __name__ == "__main__":
    main()
