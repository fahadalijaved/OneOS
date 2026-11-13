#!/usr/bin/env python3
"""Close update and detached-lease escapes in the selected writer profile."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = "tools/prepare_retained_writer_app.py"
PREDECESSOR_SHA = "37dc8d54f8a196cc86eb33a4c46eaa2937e9edff547ed382dc01c7308053f301"
BASE = "firmware/retained-writer-app"
RECEIPT = BASE + "/receipt.json"
RECEIPT_SHA = "4d1be9a5dd557af1699247b14fd4a1021dad5c194158d97806d10c06a2396ab6"
DESTINATION = "firmware/retained-writer-update-cutoff-app"
UPDATER = "app-android/app/src/full/kotlin/com/fahadali/oneos/session/AppUpdater.kt"
STOCK_UPDATER = "firmware/oneos-pr/OneOS/" + UPDATER
STOCK_SHA = "87b948ce94a561c837e48ef0df29e0749a3b7ee7533f81aebc3e12b28451064e"
UPDATER_OVERLAY = "overlay/" + UPDATER
PRODUCER = "tools/prepare_retained_writer_update_cutoff.py"


def load_writer_tools():
    path = ROOT / PREDECESSOR
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PREDECESSOR_SHA:
        raise ValueError("writer preparation source changed")
    scope = {"__name__": "held_writer_tools", "__file__": str(path)}
    exec(compile(raw, str(path), "exec"), scope)
    return scope, raw


def capture(tools):
    require, read = tools["require"], tools["read"]
    previous = read(RECEIPT, RECEIPT_SHA)
    receipt = json.loads(previous)
    require(receipt["schema"] == "retained-writer-app-source-preparation/v1" and
            receipt["status"] == "SOURCE_ONLY_COOPERATIVE_WRITER_APP_OVERLAY" and
            receipt["producer"]["sha256"] == PREDECESSOR_SHA, "unexpected writer profile")
    rows = receipt["outputs"]
    originals = {
        row["path"]: read(BASE + "/" + row["path"], row["sha256"], row["bytes"])
        for row in rows
    }
    require(len(rows) == len(originals) == 14 and UPDATER_OVERLAY not in originals and
            all(name.startswith("overlay/app-android/") for name in originals),
            "unexpected writer overlay closure")
    return receipt, previous, originals, read(STOCK_UPDATER, STOCK_SHA)


def compose(tools, originals, stock):
    gradle = tools["GRADLE"]
    rootsh = tools["ROOTSH"]
    updater = b"""    private fun refuseGuardedUpdate(): Boolean {
        if (!BuildConfig.RETAINED_WRITER_GUARD) return false
        confirmIntent = null
        update(State(Phase.FAILED, message = "Self-update is unavailable in the retained writer profile."))
        return true
    }

"""
    confirm = (b"    /** Android installer's confirmation again (the user left it); a new install when there is none. */\n"
               b"    fun confirm(ctx: Context) {\n")
    install = b"    fun install(ctx: Context) {\n"
    result = b"    private fun onInstallerResult(ctx: Context, intent: Intent) {\n"
    build_config = b'            buildConfigField("long", "ROOT_SCRIPT_BYTES", "${rootBytes.size}L")\n'
    legacy_launch = b'        </dev/null >>"$STAGE/takeover_app.log" 2>&1 &\n'
    edits = {
        gradle: [(build_config, build_config +
                  b'            buildConfigField("boolean", "RETAINED_WRITER_GUARD", "true")\n', 1)],
        rootsh: [(legacy_launch, legacy_launch.replace(b'2>&1 &', b'2>&1 3<&- &'), 1)],
        UPDATER_OVERLAY: [
            (confirm, updater + confirm + b"        if (refuseGuardedUpdate()) return\n", 1),
            (install, install + b"        if (refuseGuardedUpdate()) return\n", 1),
            (result, result + b"        if (BuildConfig.RETAINED_WRITER_GUARD) return\n", 1),
        ],
    }
    forward = dict(originals)
    for name, changes in edits.items():
        original = stock if name == UPDATER_OVERLAY else originals[name]
        normalized = [(tools["normalize"](old, original), tools["normalize"](new, original), count)
                      for old, new, count in changes]
        forward[name] = tools["apply"](original, normalized)
        inverse = [(new, old, count) for old, new, count in reversed(normalized)]
        tools["require"](tools["apply"](forward[name], inverse, allow_existing=True) == original,
                         f"inverse differs for {name}")
    return forward


def emit():
    tools, prior_source = load_writer_tools()
    repo_path, pin, require = tools["repo_path"], tools["pin"], tools["require"]
    source = repo_path(PRODUCER).read_bytes()
    previous, receipt_raw, originals, stock = capture(tools)
    forward = compose(tools, originals, stock)
    destination = repo_path(DESTINATION)
    destination.mkdir(exist_ok=False)
    for name, raw in forward.items():
        output = repo_path(DESTINATION + "/" + name)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(raw)
        require(output.read_bytes() == raw, f"output readback changed: {name}")
    require(capture(tools) == (previous, receipt_raw, originals, stock) and
            repo_path(PREDECESSOR).read_bytes() == prior_source and
            repo_path(PRODUCER).read_bytes() == source, "input readback changed")
    receipt = {
        "schema": "retained-writer-update-cutoff-app-source-preparation/v1",
        "status": "SOURCE_ONLY_COOPERATIVE_WRITER_APP_WITH_UPDATE_AND_DETACH_CUTOFFS",
        "producer": pin(PRODUCER, source),
        "baseReceipt": pin(RECEIPT, receipt_raw),
        "baseProducer": pin(PREDECESSOR, prior_source),
        "stockUpdater": pin(STOCK_UPDATER, stock),
        "baseOutputs": [pin(name, raw) for name, raw in originals.items()],
        "outputs": [pin(name, raw) for name, raw in forward.items()],
        "changedBaseFiles": [tools["GRADLE"], tools["ROOTSH"]],
        "addedOverlayFiles": [UPDATER_OVERLAY],
        "unchangedBaseFiles": sorted(set(originals) - {tools["GRADLE"], tools["ROOTSH"]}),
        "exactInverse": True,
        "properties": previous["properties"],
        "nativePins": previous["nativePins"],
        "preprovision": previous["preprovision"],
        "cuts": ["AppUpdater.confirm", "AppUpdater.install", "AppUpdater.onInstallerResult",
                 "rootsh.do_launch detached child FD3"],
    }
    with (destination / "receipt.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-update-cutoff", action="store_true", required=True)
    parser.parse_args()
    emit()
