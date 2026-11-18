"""Check the saved controller, host module and standalone view build join."""

import hashlib
import json
from pathlib import Path, PureWindowsPath
import struct
import zipfile


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = "out/retained-root-view-guard-build/r-d86f158c"
MODULE = "out/retained-guard-module-preparation/r-ea9310713eea"
SUPERVISOR = "out/gdv-build/r-afb1c08e"
APP = "firmware/debug-download-resvalues-app"
APP_JAVA = "overlay/app-android/app/src/full/java/com/fahadali/oneos/core/root"
PROVIDER = ("guest_private_view_inputs", "guest_private_view_owner", "guest_private_view_mountinfo")


def require(condition, failure):
    if not condition:
        raise ValueError(failure)


def verified(path, expected_hash, expected_size=None):
    raw = (ROOT / path).read_bytes()
    require(expected_size is None or len(raw) == expected_size, f"size changed: {path}")
    require(hashlib.sha256(raw).hexdigest() == expected_hash, f"hash changed: {path}")
    return raw


def receipt(directory, expected_hash):
    return json.loads(verified(f"{directory}/receipt.json", expected_hash))


def artifact(pin):
    return verified(pin["path"], pin["sha256"], pin["bytes"])


def native_program(pin, command, entry_source):
    raw = artifact(pin)
    require(raw[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<HH", raw, 16) == (3, 183),
            "expected ELF64 LE AArch64 ET_DYN")
    args = command["argv"]
    require(command["exitCode"] == 0 and command["ownedProcessReaped"], "native compile not recorded successful")
    require("--target=aarch64-linux-android31" in args and "-static-pie" in args,
            "unexpected native target or link profile")
    require(all("GVO_STANDALONE" not in arg for arg in args), "unexpected GVO entry")
    units = [PureWindowsPath(arg).name for arg in args if arg.endswith(".c")]
    require(units == [entry_source, *(name + ".c" for name in PROVIDER)], "unexpected native units")
    return units


def main():
    controller_sha = "6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a"
    controller = receipt(CONTROLLER, controller_sha)
    module = receipt(MODULE, "b05b38e8e57006d348c8430e694b7215b346b035783c768da38c4d83f12a37e6")
    supervisor = receipt(SUPERVISOR, "d9abd9dcee1125f500b4e7435bde7386f950202eeddeb7067082ef6271a8d10d")
    app = receipt(APP, "c6c5374388d14d4872ea2300850304edbce7bf5f4735cceac7d245fcd5f31993")
    controller_units = native_program(controller["artifact"], controller["commands"]["compile-native"],
                                      "retained_root_handoff.c")
    supervisor_units = native_program(supervisor["artifact"], supervisor["commands"][0],
                                      "guest_private_view_supervisor.c")

    controller_pins = {PureWindowsPath(path).name: digest
                       for path, digest in controller["stagedSourcePins"].items()}
    verified(f"{CONTROLLER}/native-src/retained_root_handoff.c", controller_pins["retained_root_handoff.c"])
    supervisor_main = "guest_private_view_supervisor.c"
    verified(f"{SUPERVISOR}/src/{supervisor_main}", supervisor["sources"][f"compat/native/{supervisor_main}"])
    source_comparison = {}
    for name in PROVIDER:
        for extension in (".c", ".h"):
            filename = name + extension
            left = controller_pins[filename]
            right = supervisor["sources"][f"compat/native/{filename}"]
            verified(f"{CONTROLLER}/native-src/{filename}", left)
            verified(f"{SUPERVISOR}/src/{filename}", right)
            require((left == right) == (name != PROVIDER[0]), f"unexpected provider pairing: {filename}")
            source_comparison[filename] = {"controller": left, "supervisor": right}

    require(module["sdkReceipt"] == {"path": f"{CONTROLLER}/receipt.json", "sha256": controller_sha},
            "module is from a different SDK build")
    groups = controller["logicalClassGroups"]
    program = module["programClasses"]
    require(len(program) == 44 and program == groups["host"] | groups["sharedProtocol"],
            "unexpected module program cohort")
    require(len(groups["app"]) == 13 and module["excludedAppClasses"] == groups["app"]
            and not program.keys() & groups["app"].keys(), "app cohort crossed module boundary")
    for name, digest in program.items():
        verified(f"{CONTROLLER}/classes/{name}", digest)
        verified(f"{MODULE}/classes/{name}", digest)
    artifact(module["apk"])
    dex = artifact(module["dex"])
    with zipfile.ZipFile(ROOT / module["apk"]["path"]) as apk:
        require(apk.read("classes.dex") == dex and dex[:8] == b"dex\n039\0", "different module DEX")
        require(len(apk.namelist()) == 6 and set(apk.namelist()) == module["payloadPins"].keys(),
                "unexpected module payload")

    overlay = {item["path"]: item for item in app["outputs"]}
    gradle = overlay["overlay/app-android/app/build.gradle.kts"]
    gradle_source = verified(f"{APP}/{gradle['path']}", gradle["sha256"], gradle["bytes"]).decode()
    native = controller["artifact"]
    for literal in (f'val retainedHandoffSha256 = "{native["sha256"]}"',
                    f'val retainedHandoffBytes = {native["bytes"]}L',
                    'providers.gradleProperty("oneos.retainedHandoffFile").orNull'):
        require(gradle_source.count(literal) == 1, "app native selection drift")
    require(app["nativePins"] == native and app["nativeDefaultOff"] is True
            and app["writerPatchOrViewRouteAdded"] is False, "unexpected app preparation boundary")

    app_sources = {}
    for name in ("RetainedRootOfferCommand", "RetainedRootOfferLaunch", "RetainedRootOfferSpawn",
                 "RetainedRootHostServiceV2", "RetainedHostControlProtocol"):
        filename = name + ".java"
        app_pin = overlay[f"{APP_JAVA}/{filename}"]
        original = verified(f"{APP}/{app_pin['path']}", app_pin["sha256"], app_pin["bytes"])
        sdk = verified(f"{CONTROLLER}/java-src/{filename}", controller_pins[filename])
        if name == "RetainedRootHostServiceV2":
            setup = (b"                com.fahadali.oneos.session.RetainedHandoffControllerSetup"
                     b".ensureInstalled(service, sha, bytes);\n"
                     b"                if (!mayDeliver()) { notifyHost(null); return; }\n")
            require(original.count(setup) == 1 and original.replace(setup, b"", 1) == sdk,
                    "app service differs beyond the setup and delivery check")
        elif name == "RetainedHostControlProtocol":
            view_kinds = b"    public static final int VIEW_PREPARE = 10, VIEW_STATE = 11, VIEW_QUERY = 12;\n"
            require(sdk.count(view_kinds) == 1 and sdk.count(b"kind > VIEW_QUERY") == 1
                    and sdk.replace(view_kinds, b"", 1).replace(b"kind > VIEW_QUERY", b"kind > COMMITTED", 1)
                    == original, "app codec differs beyond the host-only VIEW extension")
        else:
            require(original == sdk, f"app launcher source mismatch: {filename}")
        app_sources[filename] = {"overlay": app_pin["sha256"], "sdk": controller_pins[filename]}

    print(json.dumps({
        "status": "PASS_SAVED_BUILD_PAIRING_ONLY",
        "controller": native, "module": module["apk"], "supervisor": supervisor["artifact"],
        "controllerUnits": controller_units, "supervisorUnits": supervisor_units,
        "providerSourceComparison": source_comparison,
        "pairedModuleDefinitions": len(program), "appOverlay": APP, "overlayNativeSelection": gradle,
        "appJavaSourceComparison": app_sources,
        "standaloneSupervisorInControllerBuild": False,
        "viewOrWriterRouteAddedByAppOverlay": app["writerPatchOrViewRouteAdded"],
        "runtimeCustodyEstablishedByCheck": False,
    }, indent=2))


if __name__ == "__main__":
    main()
