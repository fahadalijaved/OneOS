#!/usr/bin/env python3
"""Build the one OneOS APK and its update.json for a GitHub release (0.4.41+).

From 0.4.41 there is one small APK for every phone: the package set files are on the owner's
Drive (scripts/release-files.py) and the app downloads the ones its phone needs; the app updates
itself from the latest GitHub release's update.json (AppUpdate, AppUpdater). This script:
  1. runs scripts/release-files.py (new set files to GitHub and Drive, packages/remote.txt) and, side by
     side, the full test suite (owner rule: green before the release), unless --no-tests;
  2. builds :app:assembleFullRelease without a series and without the set files;
  3. checks the APK: signed with the OneOS release key, no set file inside, under
     AppUpdate.MAX_BYTES;
  4. writes out/release/v<version>/OneOS-<version>.apk and update.json, and prints the
     gh release command (the APK and update.json are the release's assets; the release must be
     the repository's latest, since the app reads releases/latest/download/update.json).

With --test the build goes to the team's test channel instead (Debug settings, "Test updates"):
the APK to the owner's Drive (OneOS/test) and its update.json over OneOS/test/update.json, the
one file the app's test channel reads (AppUpdate.TEST_URL; rclone overwrites it in place, so its
Drive id stays). Nothing goes to GitHub until a build is proven there.

update.json also says which systems the release changes ("systems": the image ids whose set file
lists differ from the previous release's, "*" when the session scripts changed) and, with --notes,
one line for Home; the app's hero then reads "Update for ColorOS 17" on a phone with that system.

Usage: scripts/release-app.py [--no-tests] [--test] [--notes "one line, at most 140 characters"]
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app-android")
GRADLE = os.path.join(APP, "app/build.gradle.kts")
REPO = "fahadalijaved/OneOS"
RCLONE = os.environ.get("RCLONE", os.path.expanduser("~/bin/rclone"))
# The test channel (0.4.56): the owner's own Drive folder OneOS-test, outside the shared OneOS folder,
# each file shared by link only (rclone link). The app reads update.json by its id, a code the owner
# enters in Debug settings; the id is kept in ~/.oneos-test-channel, never in the repository.
TEST_DIR = "gdrive:OneOS-test"
TEST_CODE_FILE = os.path.expanduser("~/.oneos-test-channel")
# Up to 0.4.55 the channel was the public OneOS/test folder, its update.json id hard-coded in the app.
# ONEOS_TEST_LEGACY=1 also publishes there, so a phone on an older build can reach the one with the code.
LEGACY_TEST_DIR = "gdrive:OneOS/test"
LEGACY_TEST_UPDATE_ID = "1v43DlDjts0KhmKZVdMJtZVIIag8SUgk-"
CERT_PREFIX = "37560f7b"
MAX_BYTES = 256 * 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd, cwd=ROOT):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd)}")


def version():
    text = open(GRADLE).read()
    code = re.search(r"^\s*versionCode = (\d+)$", text, re.M)
    name = re.search(r'^\s*versionName = "([0-9.]+)"$', text, re.M)
    if not code or not name:
        sys.exit("no versionCode/versionName in app/build.gradle.kts")
    return int(code.group(1)), name.group(1)


def apksigner():
    home = os.environ.get("ANDROID_HOME", "/opt/android-sdk")
    found = sorted(glob.glob(os.path.join(home, "build-tools", "*", "apksigner")))
    if not found:
        sys.exit("no apksigner under $ANDROID_HOME/build-tools")
    return found[-1]


def check_apk(apk):
    problems = []
    size = os.path.getsize(apk)
    if size > MAX_BYTES:
        problems.append(f"{size} bytes, over {MAX_BYTES}")
    out = subprocess.run([apksigner(), "verify", "--print-certs", apk], capture_output=True, text=True)
    certs = re.findall(r"certificate SHA-256 digest: ([0-9a-f]{64})", out.stdout)
    if out.returncode != 0 or not certs or not all(c.startswith(CERT_PREFIX) for c in certs):
        problems.append(f"not signed with the OneOS release key ({certs or out.stderr.strip()})")
    remote = set()
    rpath = os.path.join(APP, "packages/remote.txt")
    for line in open(rpath):
        if line.strip() and not line.startswith("#"):
            remote.add(line.split()[0])
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if n.startswith("assets/oneos/files/") and n.rsplit("/", 1)[-1] in remote:
                problems.append(f"{n} is a set file (on Drive, not in the APK)")
    return problems


def rclone(*args):
    r = subprocess.run([RCLONE, *args], capture_output=True, text=True)
    if r.returncode != 0:
        err = "\n".join(l for l in r.stderr.splitlines() if "shared Google Drive client_id" not in l)
        sys.exit(f"rclone {' '.join(args[:2])} failed: {err.strip()}")
    return r.stdout


def drive_url(file_id):
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"


def publish_test_to(folder, apk, update, want_id=None, share=True):
    """The APK and update.json to one test folder; returns (APK URL, update.json id)."""
    name = os.path.basename(apk)
    rclone("copyto", apk, f"{folder}/{name}")
    ids = {e["Name"]: e["ID"] for e in json.loads(rclone("lsjson", folder, "--files-only") or "[]")}
    if name not in ids:
        sys.exit(f"{name} is not in {folder} after the upload")
    if share:
        rclone("link", f"{folder}/{name}")
    update = dict(update, apk=drive_url(ids[name]))
    path = apk + ".update.json"
    with open(path, "w") as f:
        json.dump(update, f, indent=2)
        f.write("\n")
    rclone("copyto", path, f"{folder}/update.json")
    ids = {e["Name"]: e["ID"] for e in json.loads(rclone("lsjson", folder, "--files-only") or "[]")}
    if want_id and ids.get("update.json") != want_id:
        sys.exit(f"{folder}/update.json has id {ids.get('update.json')}, the app reads {want_id}")
    if share:
        rclone("link", f"{folder}/update.json")
    return update["apk"], ids.get("update.json")


def publish_test(apk, update):
    """The APK and update.json to the Drive test channel; returns the APK's download URL."""
    code = open(TEST_CODE_FILE).read().strip() if os.path.isfile(TEST_CODE_FILE) else None
    url, uid = publish_test_to(TEST_DIR, apk, update, want_id=code)
    if not code:
        with open(TEST_CODE_FILE, "w") as f:
            f.write(uid + "\n")
        os.chmod(TEST_CODE_FILE, 0o600)
        print(f"Test channel code (for Debug settings; not printed again): {TEST_CODE_FILE}")
    if os.environ.get("ONEOS_TEST_LEGACY") == "1":
        publish_test_to(LEGACY_TEST_DIR, apk, update, want_id=LEGACY_TEST_UPDATE_ID, share=False)
        print(f"also published to the old {LEGACY_TEST_DIR} (ONEOS_TEST_LEGACY=1)")
    return url


ROOT_SCRIPT = os.path.join(APP, "app/src/full/assets/root/oneos_root.sh")


def set_fingerprints(apk):
    """{list name: sha256 of its text} for every set list and scripts.sha256 the APK carries."""
    out = {}
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if n.startswith("assets/oneos/sets/") and n.endswith(".sha256"):
                out[n.rsplit("/", 1)[-1].removesuffix(".sha256")] = hashlib.sha256(z.read(n)).hexdigest()
    return out


def images_of_sets():
    """{set id: image ids} from the root script's pair_set table ("<profile> <image>") echo <set> ;;)."""
    out = {}
    for prof, image, set_id in re.findall(r'^\s*"([a-z0-9-]+) ([a-z0-9-]+)"\) echo ([a-z0-9-]+) ;;', open(ROOT_SCRIPT).read(), re.M):
        out.setdefault(set_id, set()).add(image)
    return out


def changed_systems(code, now):
    """The systems this release changes against the newest earlier release here, or None (no earlier one)."""
    best = None
    for path in glob.glob(os.path.join(ROOT, "out/release/v*/sets.json")):
        d = json.load(open(path))
        if d.get("versionCode", 0) < code and (best is None or d["versionCode"] > best["versionCode"]):
            best = d
    if best is None:
        return None
    before = best["lists"]
    if now.get("scripts") != before.get("scripts"):
        return "*"
    images = images_of_sets()
    changed = set()
    for set_id, h in now.items():
        if set_id != "scripts" and before.get(set_id) != h:
            changed |= images.get(set_id, set())
    return ",".join(sorted(changed))


def main():
    args = sys.argv[1:]
    notes = None
    if "--notes" in args:
        i = args.index("--notes")
        notes = args[i + 1].strip() if i + 1 < len(args) else ""
        if not notes or len(notes) > 140 or '"' in notes or "\\" in notes:
            sys.exit("--notes: one line of at most 140 characters, without quotes or backslashes")
    tests = "--no-tests" not in sys.argv[1:]
    test_channel = "--test" in sys.argv[1:]
    code, name = version()
    print(f"OneOS {name} (versionCode {code})")
    # The set-file uploads (GitHub, then six Drive copies: about half an hour for a set rebuild) and the
    # test suite (20-25 minutes) run side by side: the tests do not read packages/remote.txt, which
    # release-files.py writes at its end and only the release packaging task checks. Both must pass
    # before the APK is built.
    files_cmd = [sys.executable, os.path.join(ROOT, "scripts/release-files.py")]
    print("+", " ".join(files_cmd), "(in the background)", flush=True)
    files = subprocess.Popen(files_cmd, cwd=ROOT)
    test_rc = 0
    if tests:
        print("+ ./gradlew test --continue", flush=True)
        test_rc = subprocess.run(["./gradlew", "test", "--continue"], cwd=APP).returncode
    if files.wait() != 0:
        sys.exit("failed: " + " ".join(files_cmd))
    if test_rc != 0:
        sys.exit("failed: ./gradlew test --continue")
    run(["./gradlew", ":app:assembleFullRelease"], cwd=APP)
    built = sorted(glob.glob(os.path.join(APP, "app/build/outputs/apk/full/release/*.apk")), key=os.path.getmtime)
    if not built:
        sys.exit("no release APK was built")
    problems = check_apk(built[-1])
    if problems:
        sys.exit("the APK is not releasable:\n  " + "\n  ".join(problems))
    dest = os.path.join(ROOT, "out/release", f"v{name}")
    os.makedirs(dest, exist_ok=True)
    apk = os.path.join(dest, f"OneOS-{name}.apk")
    shutil.copyfile(built[-1], apk)
    update = {
        "versionCode": code,
        "versionName": name,
        "apk": f"https://github.com/{REPO}/releases/download/v{name}/OneOS-{name}.apk",
        "bytes": os.path.getsize(apk),
        "sha256": sha256(apk),
    }
    lists = set_fingerprints(apk)
    with open(os.path.join(dest, "sets.json"), "w") as f:
        json.dump({"versionCode": code, "lists": lists}, f, indent=2)
    systems = changed_systems(code, lists)
    if systems is not None:
        update["systems"] = systems
    if notes:
        update["notes"] = notes
    print(f"systems changed against the previous release: {systems if systems is not None else 'unknown (no earlier release here)'}")
    with open(os.path.join(dest, "update.json"), "w") as f:
        json.dump(update, f, indent=2)
        f.write("\n")
    print(f"\n{apk}: {update['bytes'] / 1e6:.1f} MB, sha256 {update['sha256']}")
    if test_channel:
        url = publish_test(apk, dict(update))
        print(f"Test channel: {TEST_DIR}/update.json now offers {name} ({url})")
        return
    print("Release (the APK and update.json as assets, marked latest):")
    print(f"  gh release create v{name} {apk} {dest}/update.json --repo {REPO} --latest "
          f"--title 'OneOS {name}' --notes-file out/release-notes/v{name}.md")


if __name__ == "__main__":
    main()
