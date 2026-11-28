#!/usr/bin/env python3
"""Prepare the explicit cooperative writer app source profile from held inputs."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = "tools/prepare_retained_writer_app.py"
BASE = "firmware/debug-download-resvalues-app"
DESTINATION = "firmware/retained-writer-app"
GRADLE = "overlay/app-android/app/build.gradle.kts"
ROOTSH = "overlay/app-android/app/src/full/assets/root/oneos_root.sh"
LAUNCHER = "overlay/app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootScript.kt"
NATIVE = "out/retained-root-view-guard-build/r-d86f158c/oneos_retained_root_view_guard"
NATIVE_SHA = "4fb54644c1f97a64e76f057ba69e787aa28de5f9d5f9a9c696873f673f35afaa"
WRITER_KT = "firmware/root-view-writer/overlay-RootScript.kt.after"
WRITER_SH = "firmware/root-view-writer/overlay-oneos_root.sh.after"
PINS = {
    BASE + "/receipt.json": "c6c5374388d14d4872ea2300850304edbce7bf5f4735cceac7d245fcd5f31993",
    "out/full-apk-remote-assets-review/resvalues-actual/ACTUAL-OUTPUT-CHECK.json":
        "0fb88f7d3560aeef62f4baa1a9e16b05cd74911426c6c44da84a5a41e57dbe06",
    "compat/handoff-view/root-view-writer.patch":
        "4153d76510f32a4b28f6b0e0614bb87ba6ef694795b34b5b6c41442d22f386cd",
    "out/root-view-writer-review/trust/SOURCE-PASS.json":
        "25008b5b9f99479f8c13e5a7fd1fbd3b5e0de4a3ca60e1e2290a0336a21d676e",
    WRITER_KT: "1fe5a6155523d6eac4e25e66fd3030dc680ec71de045f59fd152276dc87d57eb",
    WRITER_SH: "8ad71449df990e74f32b10e50621693b7e71fa45fe0a41e3e09559761fe5027b",
    "out/retained-root-view-guard-build/r-d86f158c/receipt.json":
        "6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a",
    NATIVE: NATIVE_SHA,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, data):
    return {"path": path, "bytes": len(data), "sha256": sha(data)}


def repo_path(name):
    path = PurePosixPath(name)
    require(path.parts and path.as_posix() == name and
            all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) and part not in (".", "..")
                for part in path.parts), f"invalid relative path {name!r}")
    current = ROOT
    for part in path.parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
                f"link or reparse point at {current}")
    return current


def read(name, expected, size=None):
    path = repo_path(name)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, f"nonprivate file {name}")
    require(info.st_size <= 2_097_152 and (size is None or info.st_size == size),
            f"unexpected size for {name}")
    data = path.read_bytes()
    require(len(data) == info.st_size and sha(data) == expected, f"input changed: {name}")
    return data


def capture():
    held = {name: read(name, digest) for name, digest in PINS.items()}
    receipt = json.loads(held[BASE + "/receipt.json"])
    require(receipt["schema"] == "debug-download-resvalues-app-source-preparation/v1" and
            receipt["status"] == "SOURCE_ONLY_MODULE_RESVALUES_ENABLED" and
            receipt["nativePins"] == {"path": NATIVE, "sha256": NATIVE_SHA, "bytes": 663592},
            "unexpected base profile")
    rows = receipt["outputs"]
    names = [row["path"] for row in rows]
    require(len(names) == len(set(names)) == 14 and
            all(name.startswith("overlay/app-android/") for name in names) and
            {GRADLE, ROOTSH, LAUNCHER}.issubset(names), "unexpected overlay paths")
    originals = {
        row["path"]: read(BASE + "/" + row["path"], row["sha256"], row["bytes"])
        for row in rows
    }
    return held, originals


def unique_cut(data, start, end):
    require(data.count(start) == data.count(end) == 1, "reviewed source cut is ambiguous")
    first = data.index(start)
    last = data.index(end, first + len(start))
    return data[first:last]


def apply(data, edits, *, allow_existing=False):
    for old, new, count in edits:
        require(data.count(old) == count and (allow_existing or new not in data),
                f"unexpected edit anchor: {old[:70]!r}")
        data = data.replace(old, new)
    return data


def normalize(data, original):
    linebreak = b"\r\n" if b"\r\n" in original else b"\n"
    return data.replace(b"\r\n", b"\n").replace(b"\n", linebreak)


def lease_check(guard, fd):
    # Reconfirm the named and held objects after acquiring the actual lock.
    compare = (b'''[ "$(stat -Lc '%d:%i:%f:%u:%g:%s:%h' /proc/self/fd/@FD@ @FD@<&@FD@)" = "$(stat -c '%d:%i:%f:%u:%g:%s:%h' "$RWW/lease")" ] || rww_refuse
/system/bin/flock -xn @FD@ @FD@<&@FD@ || rww_refuse
rww_profile && rww_no_view || rww_refuse''').replace(b"@FD@", fd)
    checked = (b'''rww_same_lease() {
    rww_held=$(stat -Lc '%d:%i:%f:%u:%g:%s:%h' /proc/self/fd/@FD@ @FD@<&@FD@) || return 1
    rww_named=$(stat -c '%d:%i:%f:%u:%g:%s:%h' "$RWW/lease") || return 1
    [ -n "$rww_held" ] && [ "$rww_held" = "$rww_named" ]
}
rww_same_lease || rww_refuse
/system/bin/flock -xn @FD@ @FD@<&@FD@ || rww_refuse
rww_profile && rww_same_lease && rww_no_view || rww_refuse''').replace(b"@FD@", fd)
    return apply(guard, [(compare, checked, 1)])


def compose(held, originals):
    writer_kt = normalize(held[WRITER_KT], b"")
    writer_sh = normalize(held[WRITER_SH], b"")
    prologue = b"    /** Actual fixed lease before any original bootstrap/stage write. */"
    path_line = b"    private val PATH = Regex("
    main = b"# --- Main ---------------------------------------------------------------------"
    kt_guard = lease_check(unique_cut(writer_kt, prologue, path_line), b"8")
    sh_guard = lease_check(unique_cut(writer_sh, b"# Fixed cooperative lease.", main), b"3")
    before_close = b'    if [ "$rww_open" = 1 ]; then'
    kt_guard = apply(kt_guard, [(before_close, b'''    if [ "$rww_rc" = 0 ]; then
        rww_profile && rww_same_lease && rww_no_view || rww_rc=4
    fi
''' + before_close, 1)])
    selfupdate = (b'''if [ "$1" = selfupdate ]; then
    echo "@@REFUSED self-update unavailable in the retained writer profile"
    exit 2
fi
''')
    kt_guard = apply(kt_guard, [(b"set -- @ARGS@\n", b"set -- @ARGS@\n" + selfupdate, 1)])
    sh_guard += selfupdate + b"\n"

    selection = b"return (if (verb == Verb.INSTALL_CLOSED_CONTROLLER"
    stage_cleanup = b'    exit "$rc"\n}\ntrap cleanup EXIT'
    child_fds = b'''if @SH@ "$RUN" "$@" 3<&- 4<&4 5<&- 6>&-; then rc=0; else rc=$?; fi'''
    stock_exec = b'''exec @SH@ "$F" "$@"'''
    native_pin = b"val retainedHandoffBytes = 663592L\n"
    gradle_gate = b'''
// This separate source profile requires both explicit debug selections.
check(providers.gradleProperty("oneos.retainedWriterGuard").orNull == "true" &&
    debugDownloadMetadataEnabled && !retainedHandoffPath.isNullOrBlank() &&
    retainedControllerPath == null) {
    "retained writer profile requires retainedWriterGuard=true, debugDownloadMetadata=true, and the guarded v2 controller only"
}
'''
    edits = {
        LAUNCHER: [
            (selection, selection.replace(b"return (if", b"return (WRITER_TEMPLATE + (if"), 1),
            (b" INSTALL_TEMPLATE else TEMPLATE)\n", b" INSTALL_TEMPLATE else TEMPLATE))\n", 1),
            (path_line, kt_guard + path_line, 1),
            (stage_cleanup, b'    if rww_finish "$rc"; then rc=0; else rc=$?; fi\n' + stage_cleanup, 1),
            (child_fds, child_fds.replace(b"3<&-", b"3<&8").replace(b"6>&-;", b"6>&- 8<&-;"), 1),
            (stock_exec, b'''if @SH@ "$F" "$@" 3<&8 8<&-; then rww_rc=0; else rww_rc=$?; fi
rww_finish "$rww_rc"; exit $?''', 2),
        ],
        ROOTSH: [(main, sh_guard + main, 1)],
        GRADLE: [(native_pin, native_pin + gradle_gate, 1)],
    }
    forward = dict(originals)
    for name, cuts in edits.items():
        original = originals[name]
        cuts = [(normalize(old, original), normalize(new, original), count)
                for old, new, count in cuts]
        forward[name] = apply(original, cuts)
        inverse = [(new, old, count) for old, new, count in reversed(cuts)]
        require(apply(forward[name], inverse, allow_existing=True) == original,
                f"inverse differs for {name}")
    return forward, sorted(edits)


def emit():
    source = repo_path(PRODUCER).read_bytes()
    held, originals = capture()
    forward, changed = compose(held, originals)
    output = repo_path(DESTINATION)
    output.mkdir(exist_ok=False)
    receipt = {
        "schema": "retained-writer-app-source-preparation/v1",
        "status": "SOURCE_ONLY_COOPERATIVE_WRITER_APP_OVERLAY",
        "producer": pin(PRODUCER, source),
        "inputs": [pin(name, data) for name, data in held.items()],
        "baseOutputs": [pin(name, data) for name, data in originals.items()],
        "outputs": [pin(name, data) for name, data in forward.items()],
        "changedBaseFiles": changed,
        "unchangedBaseFiles": sorted(set(originals) - set(changed)),
        "wholeFileInverseExact": True,
        "nativePins": pin(NATIVE, held[NATIVE]),
        "properties": {
            "oneos.retainedWriterGuard": "true",
            "oneos.debugDownloadMetadata": "true",
            "oneos.retainedHandoffFile": NATIVE,
        },
        "preprovision": {
            "directory": "/dev/oneos-retained-view",
            "lease": "/dev/oneos-retained-view/lease",
            "owner": "0:0",
            "directoryMode": "0700",
            "leaseMode": "0600",
            "leaseBytes": 0,
            "leaseLinks": 1,
            "createdByThisProducerOrApp": False,
        },
        "excluded": ["selfupdate", "existing unguarded writers", "provisioning", "runtime activation"],
    }
    for name, data in forward.items():
        target = repo_path(DESTINATION + "/" + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        require(target.read_bytes() == data, f"output readback changed: {name}")
    require(capture() == (held, originals) and repo_path(PRODUCER).read_bytes() == source,
            "input readback changed")
    with (output / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-writer", action="store_true", required=True)
    parser.parse_args()
    emit()
