"""Compose exact, reviewed app and host VIEW changes in a fresh PC build tree."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy
import uuid
import zipfile


ROOT = Path(__file__).absolute().parents[1]
WRITER = "tools/build_retained_writer_debug.py"
WRITER_SHA = "f1ea975bec69092bd32fd85ab37574c84879b26b468f6055bc70c424b5f6ea1c"
WRITER_BUILD = "out/full-apk-build/guarded-writer/r-87e72aa0/receipt.json"
WRITER_BUILD_SHA = "5540b5b2de9b2389b76b33712adbddd2be38ae02a4eb6324b67d1c59be655fed"
SDK_BUILD = "out/retained-root-view-guard-build/r-d86f158c/receipt.json"
SDK_BUILD_SHA = "6c67ec7388f1d64e5a82eeb4f17aa7a23880a9d15c3f3a26bc74a8017d841f0a"
PATCH_HELPER = "tools/prepare_retained_view_app.py"
PATCH_HELPER_SHA = "032ebf7c6252a5b061664f5d6fb2bc7f1a4c54ea2a969743ceb5037ba3dea018"
COMPAT = "compat/handoff-view/"
PROTOCOL = "com/fahadali/oneos/core/root/RetainedViewAppProtocol.java"
PROTOCOL_SHA = "18f157d6e4642c7a5b094ca7cc9feabfa16af2e02ba66e013b5f0748f788597f"
FULL = "app-android/app/src/full/"
SERVICE = FULL + "java/com/fahadali/oneos/core/root/RetainedRootHostServiceV2.java"
CONFIRM = FULL + "kotlin/com/fahadali/oneos/ui/SwitchConfirm.kt"
STRINGS = FULL + "res/values/strings.xml"
APP_GRADLE = "app-android/app/build.gradle.kts"
HOST_BINDING = "PreparedRetainedHostNativeBindingV2.java"
HOST_CONTROL = "RetainedHostNativeControlV2.java"
PATCHES = {
    "app-view-relay.patch": ((SERVICE,), "08641354da293c4ddf44396bf9f83db4b6ef52aeec78a00b12bbfeebf33198f7"),
    "app-view-ui.patch": ((CONFIRM, STRINGS), "a268cf501679d9a28487a58c74e5b925366955befa0962cc501f6fa86a28b413"),
    "host-view-app-ingress.patch": ((HOST_BINDING,), "e0423c6b1b58450c548fedcd06768edff89b684b92ae5bf317114abff0c2b783"),
    "host-view-app-status.patch": ((HOST_CONTROL,), "1fa36c20c412186766f656e07c50a51879f38cc9ce336d6d387c73a28f791710"),
}


def add_default_off_flag(data):
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    anchor = b'            buildConfigField("boolean", "RETAINED_WRITER_GUARD", "true")' + newline
    addition = newline.join([
        b'            buildConfigField("boolean", "RETAINED_VIEW_PREPARATION",',
        b'                (providers.gradleProperty("oneos.retainedViewPreparation").orNull == "true").toString())',
        b'',
    ])
    if data.count(anchor) != 1 or b"RETAINED_VIEW_PREPARATION" in data:
        raise ValueError("Expected one exact Full writer configuration anchor")
    return data.replace(anchor, anchor + addition, 1)


def build_app(work, app_root, app, writer, old, previous, native, base):
    """Compile a separate explicit preparation APK using the verified offline cache."""
    require = writer["require"]
    pinned = writer["pinned"]
    root50 = writer["R50"]
    sdk = writer["contained"](ROOT / previous["sdkRoot"])
    initial = json.loads(pinned(root50 / "receipt.json",
        "96360b1e108c79c3df0c2b5bd367187ac5c79552c1a9a253a3e077cd5a45d1c9"))
    sdk_pins = initial["copiedSdkPins"].copy()
    for name, digest in {
        "platforms/android-37.0/package.xml": "68540346e2e77022b39620dbb99738d0dec3e14b4d15f47c25c02acc17cdd5ea",
        "build-tools/37.0.0/package.xml": "16f8768a5bb8bd55e1873403caca97f48a1660a44832102755dee90a349578fb",
    }.items():
        data = pinned(sdk / name, digest)
        sdk_pins[name] = {"bytes": len(data), "sha256": digest}
    gradle_home = root50 / "gradle-home"
    cache = gradle_home / "caches/modules-2/files-2.1"
    artifact_pins = previous["resolvedArtifactPins"]
    require(len(artifact_pins) == 851, "Exact saved dependency cohort")

    def boundary():
        writer["verify_tree_pins"](sdk, sdk_pins)
        writer["verify_tree_pins"](cache, artifact_pins)
        require(not (sdk / "licenses").exists() and not any((gradle_home / "init.d").glob("*"))
                and not (gradle_home / "gradle.properties").exists(), "Private SDK/Gradle boundary")
        for name, data in app.items():
            pinned(app_root / name, writer["digest"](data), len(data))

    boundary()
    old_project = ROOT / old["sourceTree"] / "app-android"
    old_work = (ROOT / WRITER_BUILD).parent
    project = app_root / "app-android"
    argv = old["commands"]["assemble"]["argv"].copy()
    for before, after in (
        (str(old_project), str(project)),
        (str(old_work / "project-cache"), str(work / "project-cache")),
        ("-Pkotlin.project.persistent.dir=" + str(old_work / "kotlin-home"),
         "-Pkotlin.project.persistent.dir=" + str(work / "kotlin-home")),
    ):
        require(argv.count(before) == 1, "Exact predecessor command argument")
        argv[argv.index(before)] = after
    require("--offline" in argv and "-Poneos.retainedWriterGuard=true" in argv
            and all("retainedViewPreparation" not in value for value in argv), "Safe exact offline build")
    argv.append("-Poneos.retainedViewPreparation=true")
    runner = runpy.run_path(str(ROOT / writer["RUNNER"]))
    require(writer["sha"](Path(argv[0])) == runner["JAVA_SHA"], "Same approved JBR")
    env = previous["ownedEnvironment"].copy()
    strip_nodes = [node for node in ast.parse(base[runner["ENV_PROFILE"]]).body
                   if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STRIP"
                                                           for t in node.targets)]
    require(len(strip_nodes) == 1, "One pinned environment profile")
    strip = ast.literal_eval(strip_nodes[0].value)
    require(Path(env["ANDROID_HOME"]) == sdk and Path(env["GRADLE_USER_HOME"]) == gradle_home
            and not set(env) & strip, "Same credential-free environment")

    command_file = writer["COMMAND"]
    nodes = [node for node in ast.parse(base[command_file]).body
             if isinstance(node, ast.FunctionDef) and node.name == "command"]
    require(len(nodes) == 1, "Exact bounded command helper")
    limits = [node for node in ast.walk(nodes[0]) if isinstance(node, ast.Constant) and node.value == 45]
    require(len(limits) == 2, "Exact existing timeout sites")
    for limit in limits:
        limit.value = 900

    def owned(path):
        Path(path).relative_to(work)
        return writer["contained"](path)

    def save(path, result):
        with owned(path).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")

    scope = {**runpy.run_path(str(ROOT / command_file)), **writer, "owned": owned, "save": save, "STRIP": strip}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), command_file, "exec"), scope)
    result = {"status": "FAILED", "offline": True, "commands": {}, "phoneActions": False,
              "sourceReceiptSha256": writer["sha"](work / "receipt.json")}
    try:
        result["commands"]["assemble"] = scope["command"](argv, work, env, "assemble")
        boundary()
        apks = list((project / "app/build/outputs/apk/full/debug").glob("*.apk"))
        require(len(apks) == 1, "One actual preparation APK")
        apk = owned(apks[0])
        result["apk"] = runner["inspect_debug_apk"](
            apk, project, native, app["app-android/packages/debug-download-assets.tsv"], app)
        expected_classes = {
            b"Lcom/fahadali/oneos/core/root/RetainedViewAppProtocol;",
            b"Lcom/fahadali/oneos/core/root/RetainedRootHostServiceV2$ViewAttempt;",
            b"Lcom/fahadali/oneos/ui/PrepareColorOsUi;",
        }
        observed = set()
        with zipfile.ZipFile(apk) as archive:
            for member in result["apk"]["dex"]:
                observed.update(runner["dex_defined_classes"](archive.read(member)) & expected_classes)
        require(observed == expected_classes, "Actual app protocol, relay and preparation UI in APK DEX")
        result["preparationClasses"] = sorted(name.decode("ascii") for name in observed)
        config = project / "app/build/generated/source/buildConfig/full/debug/com/fahadali/oneos/BuildConfig.java"
        require(b"boolean RETAINED_VIEW_PREPARATION = true;" in config.read_bytes(),
                "Actual generated opt-in field")
        result["commands"]["verify-signature"] = scope["command"]([
            argv[0], "-Duser.home=" + env["HOME"], "-Djava.io.tmpdir=" + env["TMP"],
            "-jar", sdk / "build-tools/37.0.0/lib/apksigner.jar", "verify", "--verbose", "--print-certs", apk,
        ], work, env, "verify-signature")
        result["certificate"] = runner["verified_signer_sha256"](
            (work / "verify-signature.stdout").read_text(encoding="utf-8"))
        require(result["certificate"] == old["certificate"] and writer["sha"](apk) == result["apk"]["sha256"],
                "Verified unchanged debug APK and signer")
        result["status"] = "PASS_OFFLINE_APP_PREPARATION_APK_ONLY"
    except BaseException as failure:
        result["failure"] = type(failure).__name__
        result["message"] = str(failure)[:1024]
        raise
    finally:
        save(work / "apk-receipt.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble-app", action="store_true", help="Compile an explicit opt-in Full Debug APK offline.")
    args = parser.parse_args()
    if any(len(digest) != 64 for _, digest in PATCHES.values()):
        raise ValueError("All four patches must have exact reviewed pins")
    if WRITER_SHA != hashlib.sha256((ROOT / WRITER).read_bytes()).hexdigest():
        raise ValueError("Writer build source changed")
    writer = runpy.run_path(str(ROOT / WRITER))
    pinned = writer["pinned"]
    require = writer["require"]
    digest = writer["digest"]
    contained = writer["contained"]
    rel = writer["relative"]
    pinned(ROOT / PATCH_HELPER, PATCH_HELPER_SHA)
    apply_patch = runpy.run_path(str(ROOT / PATCH_HELPER))["apply_patch"]

    old = json.loads(pinned(ROOT / WRITER_BUILD, WRITER_BUILD_SHA))
    sdk = json.loads(pinned(ROOT / SDK_BUILD, SDK_BUILD_SHA))
    require(old["status"] == "PASS_OFFLINE_GUARDED_WRITER_APK_STATIC_ONLY"
            and sdk["status"] == "PASS_ROOT_GUARD_VIEW_COMPOSED_NATIVE_STATIC_AND_SDK_ONLY",
            "Exact terminal predecessor generations")
    old_apk = old["apk"]
    pinned(ROOT / old_apk["path"], old_apk["sha256"], old_apk["bytes"])
    native = sdk["artifact"]
    require(native["sha256"] == old_apk["packagedNativeSha256"], "Same selected controller")
    native_bytes = pinned(ROOT / native["path"], native["sha256"], native["bytes"])
    base = {name: pinned(ROOT / name, pin) for name, pin in writer["PINS"].items()}
    previous = json.loads(base[writer["PREVIOUS"]])
    original = writer["ORIGINAL"]
    overlay = writer["WRITER"]
    app = writer["stage_sources"](
        previous, writer["module_overlay"](original, base[original]),
        writer["module_overlay"](overlay, base[overlay]), json.loads(base[overlay]),
    )
    for name, data in app.items():
        pinned(ROOT / old["sourceTree"] / name, digest(data), len(data))
    host = {}
    for name in (HOST_BINDING, HOST_CONTROL):
        key = "compat/handoff-host/com/appleexploit/oneos/security/authority/" + name
        info = sdk["compiledSourceInputs"][key]
        expected = (ROOT / SDK_BUILD).parent / "java-src" / name
        require(ROOT / info["stagedPath"] == expected, "Exact compiled host source path")
        host[name] = pinned(expected, info["compiledSha256"])

    for name, (targets, expected) in PATCHES.items():
        sources = app if all(target in app for target in targets) else host
        before = {target: sources[target] for target in targets}
        patch = pinned(ROOT / COMPAT / name, expected)
        after = apply_patch(patch, before)
        require(after != before and apply_patch(patch, after, inverse=True) == before,
                "Exact reversible source change: " + name)
        sources.update(after)
    app[APP_GRADLE] = add_default_off_flag(app[APP_GRADLE])
    added = FULL + "java/" + PROTOCOL
    require(added not in app, "New protocol has a distinct Full source path")
    app[added] = pinned(ROOT / COMPAT / "app-protocol" / PROTOCOL, PROTOCOL_SHA)

    work = contained(ROOT / "out/retained-view-ingress" / ("r-" + uuid.uuid4().hex[:8]))
    work.mkdir(parents=True, exist_ok=False)

    def publish(directory, sources):
        for name, data in sources.items():
            target = contained(directory / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)

    app_root = work / "source/OneOS"
    host_root = work / "host"
    publish(app_root, app)
    publish(host_root, host)
    java = {Path(name).name: app_root / name for name in (SERVICE, added)}
    java.update({name: host_root / name for name in host})
    manifest = {
        "schema": "retained-view-ingress-sources/v1",
        "sources": {name: {"path": rel(path), "sha256": writer["sha"](path)} for name, path in java.items()},
    }
    receipt = {
        "status": "PASS_EXACT_PREPARATION_SOURCE_COMPOSITION_ONLY",
        "appSourceTree": rel(app_root),
        "writerBuildReceipt": WRITER_BUILD_SHA,
        "sdkBuildReceipt": SDK_BUILD_SHA,
        "appSourcePins": {name: {"bytes": len(data), "sha256": digest(data)} for name, data in app.items()},
        "appViewDefaultEnabled": False,
        "compiled": False,
        "phoneActions": False,
    }
    for name, result in (("java-sources.json", manifest), ("receipt.json", receipt)):
        with (work / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(rel(work / "java-sources.json"), flush=True)
    if args.assemble_app:
        build_app(work, app_root, app, writer, old, previous, native_bytes, base)


if __name__ == "__main__":
    main()
