#!/usr/bin/env python3
"""Put every package set's files on the owner's Drive and write app-android/packages/remote.txt.

0.4.41: the APK no longer carries the set files (1.4 GB per series). The app downloads the
files its phone's set needs, by SHA-256, from the owner's Google Drive folder OneOS/files,
where each file is named by its SHA-256. This script:
  1. reads the sets the app packs (app-android/app/build.gradle.kts, packageSets) and their
     lists (app-android/packages/<set>.sha256), checking each built file's hash;
  2. uploads the files Drive does not have yet (rclone remote "gdrive", scope drive.file);
  3. keeps copies of them in OneOS/files2 .. OneOS/files6 (0.4.53: Drive refuses a shared file
     for the rest of the day once too many users downloaded it, and each copy has its own
     limit; server-side copies, nothing is uploaded twice);
  4. uploads the files the GitHub release GH_TAG of GH_REPO lacks, as assets named by their
     SHA-256 (0.4.53: GitHub's CDN has no daily limit; the app tries it first);
  5. uploads the files SourceForge's oneos-mirror project lacks to its folder files/, named by their
     SHA-256 (0.4.65: GitHub's downloads were down for hours on 11-08 and every phone fell on the
     Drive copies, which ran out the same day; SourceForge has no daily limit; the app tries it
     right after GitHub);
  6. writes packages/remote.txt: "<sha256> gh:<tag>,sf,<drive id>,<drive id>,..." for every set file,
     sorted, the OneOS/files id first among the Drive ones, and packages/sizes.txt ("<sha256> <bytes>").
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
# The copies (0.4.53). The app starts at a random one and moves on when Drive refuses it.
MIRROR_DIRS = [f"gdrive:OneOS/files{n}" for n in range(2, 7)]
# GitHub release assets (0.4.53), the app's first source: a repository of their own, so a takedown
# of these OEM binaries could never reach fahadalijaved/OneOS. A release holds at most 1000 assets:
# a new tag (sets-2) before this one fills up.
GH_REPO = "fahadalijaved/OneOS-files"
# On from 0.4.54 (owner: "Drive is still problematic, lets make github repo"); 0.4.53 shipped the
# app side, so turning it on only changes remote.txt.
GH_ENABLED = True
GH_TAG = "sets-1"
GH_MAX_ASSETS = 950
RCLONE = os.environ.get("RCLONE", os.path.expanduser("~/bin/rclone"))
# SourceForge (0.4.65): the upload key the owner added for the image mirror (sourceforge-mirror notes).
SF_ENABLED = True
# The rclone remote of SourceForge's oneos-mirror files/ folder (an sftp remote with the upload login and
# key), kept out of the repository in ~/.oneos-sourceforge-remote like the other credentials; without
# it the SourceForge step is skipped and remote.txt keeps "sf" only if the files are already there.
SF_REMOTE_FILE = os.path.expanduser("~/.oneos-sourceforge-remote")
SF_REMOTE = open(SF_REMOTE_FILE).read().strip() if os.path.isfile(SF_REMOTE_FILE) else None
SF_URL = "https://downloads.sourceforge.net/project/oneos-mirror/files/"
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


def on_drive(folder=REMOTE_DIR):
    """name -> Drive id of every file in [folder] (OneOS/files by default)."""
    listing = json.loads(rclone("lsjson", folder, "--files-only") or "[]")
    return {e["Name"]: (e["ID"], e["Size"]) for e in listing}


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
    ids = {s: [have[s][0]] for s in want}
    for folder in MIRROR_DIRS:
        there = on_drive(folder) if folder_exists(folder) else {}
        need = sorted(s for s in want if s not in there or there[s][1] != os.path.getsize(want[s]))
        if need:
            print(f"{folder}: copying {len(need)} files on Drive")
            with tempfile.NamedTemporaryFile("w", dir=os.path.join(ROOT, "out"), suffix=".txt") as lst:
                lst.write("\n".join(need) + "\n")
                lst.flush()
                rclone("copy", REMOTE_DIR, folder, "--files-from", lst.name, "--transfers", "8")
            there = on_drive(folder)
        short = [s for s in want if s not in there or there[s][1] != os.path.getsize(want[s])]
        if short:
            sys.exit(f"{folder}: {len(short)} files missing or of another size after the copy, e.g. {short[0]}")
        for s in want:
            ids[s].append(there[s][0])
    sf = ""
    if SF_ENABLED:
        if SF_REMOTE:
            sf_upload(want)
            sf = "sf,"
        else:
            print(f"no {SF_REMOTE_FILE}: SourceForge left out of remote.txt")
    if GH_ENABLED:
        github_upload(want)
        lines = [f"{s} gh:{GH_TAG},{sf}{','.join(ids[s])}" for s in sorted(want)]
        head = f"the {GH_REPO} release {GH_TAG}, {'SourceForge oneos-mirror files/, ' if sf else ''}then Drive ids"
    else:
        lines = [f"{s} {','.join(ids[s])}" for s in sorted(want)]
        head = "Drive ids"
    path = os.path.join(PACKAGES, "remote.txt")
    with open(path, "w") as f:
        f.write(f"# sha256 -> sources: {head} (OneOS/files, its copies in OneOS/files2..6), written by scripts/release-files.py\n")
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}: {len(lines)} files, {'GitHub and ' if GH_ENABLED else ''}{1 + len(MIRROR_DIRS)} Drive copies each")
    # packages/sizes.txt (pull request #37): the size of every set file, so the app builds
    # from remote.txt and these without the built set folders (contributors' checkouts).
    path = os.path.join(PACKAGES, "sizes.txt")
    with open(path, "w") as f:
        f.write("".join(f"{s} {os.path.getsize(want[s])}\n" for s in sorted(want)))
    print(f"wrote {path}: {len(want)} sizes")


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:400]}")
    return r


def github_assets():
    """name -> size of every asset of GH_TAG, or None when the release does not exist yet."""
    r = gh("release", "view", GH_TAG, "--repo", GH_REPO, "--json", "assets", check=False)
    if r.returncode != 0:
        if "release not found" in r.stderr.lower():
            return None
        sys.exit(f"{GH_REPO}: {r.stderr.strip()[:400]} (the repository must exist, public, before a release)")
    return {a["name"]: a["size"] for a in json.loads(r.stdout)["assets"]}


def github_upload(want):
    have = github_assets()
    if have is None:
        gh("release", "create", GH_TAG, "--repo", GH_REPO, "--title", f"OneOS set files ({GH_TAG})", "--latest=false",
           "--notes", "Files the OneOS app downloads and checks by SHA-256 (each asset is named by it). "
                      "Not for manual download: the app picks what a phone's system needs.")
        have = {}
    need = sorted(s for s in want if have.get(s) != os.path.getsize(want[s]))
    bad = [s for s in need if s in have]
    if bad:
        sys.exit(f"{GH_REPO} {GH_TAG}: {len(bad)} assets of another size, e.g. {bad[0]}: delete them by hand")
    if len(have) + len(need) > GH_MAX_ASSETS:
        sys.exit(f"{GH_REPO} {GH_TAG} would hold {len(have) + len(need)} assets: start the next tag (GH_TAG)")
    if need:
        size = sum(os.path.getsize(want[s]) for s in need)
        print(f"{GH_REPO} {GH_TAG}: uploading {len(need)} files ({size / 1e9:.2f} GB)")
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "out")) as tmp:
            for s in need:
                os.link(want[s], os.path.join(tmp, s))
            for i in range(0, len(need), 10):
                gh("release", "upload", GH_TAG, *[os.path.join(tmp, s) for s in need[i:i + 10]], "--repo", GH_REPO)
        have = github_assets() or {}
    short = [s for s in want if have.get(s) != os.path.getsize(want[s])]
    if short:
        sys.exit(f"{GH_REPO} {GH_TAG}: {len(short)} files missing after the upload, e.g. {short[0]}")


def sf_files():
    """name -> size of every file in SourceForge's oneos-mirror files/ (empty before the first upload)."""
    r = subprocess.run([RCLONE, "lsjson", SF_REMOTE, "--files-only"], capture_output=True, text=True)
    if r.returncode != 0:
        if "not found" in r.stderr.lower() or "directory not found" in r.stderr.lower():
            return {}
        sys.exit(f"SourceForge listing failed: {r.stderr.strip()[:400]}")
    return {e["Name"]: e["Size"] for e in json.loads(r.stdout or "[]")}


def sf_upload(want):
    have = sf_files()
    need = sorted(s for s in want if have.get(s) != os.path.getsize(want[s]))
    if need:
        size = sum(os.path.getsize(want[s]) for s in need)
        print(f"SourceForge oneos-mirror files/: uploading {len(need)} files ({size / 1e9:.2f} GB)", flush=True)
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "out")) as tmp:
            # Symbolic links, followed by rclone: a hard link to another account's file is refused.
            for s in need:
                os.symlink(os.path.realpath(want[s]), os.path.join(tmp, s))
            rclone("copy", tmp, SF_REMOTE, "--copy-links", "--transfers", "4", "--retries", "5")
        have = sf_files()
    short = [s for s in want if have.get(s) != os.path.getsize(want[s])]
    if short:
        sys.exit(f"SourceForge: {len(short)} files missing or of another size after the upload, e.g. {short[0]}")


def folder_exists(folder):
    parent, name = folder.rsplit("/", 1)
    listing = json.loads(rclone("lsjson", parent, "--dirs-only") or "[]")
    return any(e["Name"] == name for e in listing)


if __name__ == "__main__":
    main()
