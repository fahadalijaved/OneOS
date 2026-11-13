"""Build the reviewed guarded writer overlay as a separate offline Full Debug APK."""

import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import uuid


ROOT = Path(__file__).absolute().parents[1]
R50 = ROOT / "out/full-apk-build/r-50dc28be"
BASE = ROOT / "out/full-apk-build/guarded-writer"
PREVIOUS = "out/full-apk-build/r-50dc28be/metadata-retry-50c32d1e/receipt.json"
DELIVERY = "out/deliverables/OneOS-0.4.58-full-debug-3f06535b.apk.receipt.json"
ORIGINAL = "firmware/debug-download-resvalues-app/receipt.json"
WRITER = "firmware/retained-writer-update-cutoff-app/receipt.json"
REVIEW = "out/retained-writer-app-independent-review/UPDATE-CUTOFF-ACTUAL-OUTPUT-CHECK.json"
RUNNER = "tools/run_full_apk_build.py"
COMMAND = "tools/build_retained_root_handoff.py"
PINS = {
    PREVIOUS: "0524340faae63197bd30d4d6023ae1571e78d2828e46aa072cffd7b717279b8f",
    DELIVERY: "0c23552fe6dcada836aa854d5934530bf83ca574e318013158e988b508b6335e",
    ORIGINAL: "c6c5374388d14d4872ea2300850304edbce7bf5f4735cceac7d245fcd5f31993",
    WRITER: "91e5ee3897a69ab92d7f91a60bdebdc7ae86a78d20424bdf8126614afb5af525",
    REVIEW: "3a853900514e856f3df335ee95bdeb460e2e83e62598376526c979bf1dfe310e",
    RUNNER: "50d8aeefee395571ceadc48c914a148817cf83baea6986effd2681b3a9647eb5",
    COMMAND: "7c55e2c3863924f191c68d16e6a8a46ecf48ce9b7017a39af41e1dc4bc076544",
    "tools/build_guest_private_image_preparation.py":
        "1662ad528da9429412f11d2ed8bf9b2c02b95b4337624170deeb06730b332ef4",
}
APP_GRADLE = "app-android/app/build.gradle.kts"
CHECKSUMS = "app-android/gradle/verification-metadata.xml"
CHECKSUM_SHA = "2ac8326ff598a1f2564e2fdb2f745f35f4768b681c14d20745745e63c232de04"
UPDATER = "app-android/app/src/full/kotlin/com/fahadali/oneos/session/AppUpdater.kt"
ROOT_SCRIPT = "app-android/app/src/full/assets/root/oneos_root.sh"
LAUNCHER = "app-android/core/root/src/main/kotlin/com/fahadali/oneos/core/root/RootScript.kt"
CHANGE_SET = {APP_GRADLE, UPDATER, ROOT_SCRIPT, LAUNCHER}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def plain(path):
    path = Path(path)
    require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(),
            f"Reparse point refused: {path}")
    return path


def contained(path):
    path = Path(path)
    path.relative_to(ROOT)
    for item in (path, *path.parents):
        plain(item)
        if item == ROOT:
            break
    path.resolve().relative_to(ROOT.resolve())
    return path


def owned(path):
    Path(path).relative_to(BASE)
    return contained(path)


def pinned(path, expected, size=None):
    data = contained(path).read_bytes()
    require(digest(data) == expected and (size is None or len(data) == size),
            f"Input differs: {path}")
    return data


def save(path, value):
    with owned(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def module_overlay(receipt, raw):
    base = ROOT / receipt
    rows = json.loads(raw)["outputs"]
    require(all(row["path"].startswith("overlay/") for row in rows), "Overlay paths")
    files = {row["path"][8:]: pinned(base.parent / row["path"], row["sha256"], row["bytes"])
             for row in rows}
    require(len(files) == len(rows), "Unique overlay members")
    return files


def apply_host_build_fixes(data):
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    sdk = b"    compileSdk { version = release(37) }" + newline
    build_tools = b'    buildToolsVersion = "37.0.0"' + newline
    old = (b"        check(after.isRegularFile && before.fileKey() != null && "
           b'before.fileKey() == after.fileKey()) { "debug metadata identity changed: $f" }')
    new = newline.join([
        b"        check(after.isRegularFile && !OneOsNioFiles.isSymbolicLink(path) &&",
        b"            before.fileKey() == after.fileKey() &&",
        b"            before.size() == data.size.toLong() && after.size() == data.size.toLong() &&",
        b"            before.creationTime() == after.creationTime() &&",
        b'            before.lastModifiedTime() == after.lastModifiedTime()) { "debug metadata identity changed: $f" }',
    ])
    require(data.count(sdk) == 1 and data.count(old) == 1 and build_tools not in data,
            "Exact two proven build anchors")
    result = data.replace(sdk, sdk + build_tools, 1).replace(old, new, 1)
    require(result.replace(build_tools, b"", 1).replace(new, old, 1) == data,
            "Exact build-fix inverse")
    return result


def stage_sources(previous, original, writer, raw_writer):
    original_source = contained(ROOT / previous["sourceTree"])
    pins = previous["sourcePins"]
    require(len(pins) == 511 and set(writer) == set(original) | {UPDATER},
            "Exact original and writer source cohorts")
    sources = {name: pinned(original_source / name, row["sha256"], row["bytes"])
               for name, row in pins.items()}
    for name, data in original.items():
        expected = apply_host_build_fixes(data) if name == APP_GRADLE else data
        require(sources[name] == expected, f"Original APK source lineage differs: {name}")
    stock = raw_writer["stockUpdater"]
    require(len(sources[UPDATER]) == stock["bytes"]
            and digest(sources[UPDATER]) == stock["sha256"], "Original updater bytes")
    prepared = dict(writer)
    prepared[APP_GRADLE] = apply_host_build_fixes(prepared[APP_GRADLE])
    require({name for name, data in prepared.items() if sources[name] != data} == CHANGE_SET,
            "Exactly the four guarded writer source changes")
    sources.update(prepared)
    require(CHECKSUMS not in sources, "Generated verification metadata separate from source pins")
    sources[CHECKSUMS] = pinned(original_source / CHECKSUMS, CHECKSUM_SHA)
    return sources


def verify_tree_pins(base, pins):
    for directory, names, files in os.walk(contained(base), followlinks=False):
        parent = Path(directory)
        for name in names + files:
            plain(parent / name)
    for name, row in pins.items():
        path = base / name
        require(path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                f"Pinned toolchain input differs: {name}")


def run():
    require(os.name == "nt", "Expected approved Windows build toolchain")
    raw = {name: pinned(ROOT / name, expected) for name, expected in PINS.items()}
    previous = json.loads(raw[PREVIOUS])
    delivery = json.loads(raw[DELIVERY])
    require(previous["apkBuilt"] and previous["apkInspected"]
            and previous["terminalInputBoundaryPassed"]
            and delivery["status"] == "PASS_SAVED_FULL_DEBUG_APK_STATIC_AND_SIGNATURE_VERIFIED",
            "Expected verified original Full Debug build")
    original_apk = delivery["apk"]
    pinned(ROOT / original_apk["path"], original_apk["sha256"], original_apk["bytes"])
    for label in ("assemble", "verify-signature"):
        command = previous["commands"][label]
        require(command["exitCode"] == 0 and command["ownedProcessReaped"]
                and command["boundedFailure"] is None, "Expected clean previous build commands")

    runner = runpy.run_path(str(ROOT / RUNNER))
    mirror_path = ROOT / previous["packageMirror"]["receipt"]
    _, mirror_data, _, coordinates, mirror_pins = runner["read_package_mirror"](mirror_path)
    require(digest(mirror_data) == previous["packageMirror"]["sha256"]
            and len(coordinates) == 19 and len(mirror_pins) == 57, "Verified local package mirror")
    initial = json.loads(pinned(R50 / "receipt.json",
        "96360b1e108c79c3df0c2b5bd367187ac5c79552c1a9a253a3e077cd5a45d1c9"))
    sdk = contained(ROOT / previous["sdkRoot"])
    sdk_pins = initial["copiedSdkPins"].copy()
    for name, expected in {
        "platforms/android-37.0/package.xml": "68540346e2e77022b39620dbb99738d0dec3e14b4d15f47c25c02acc17cdd5ea",
        "build-tools/37.0.0/package.xml": "16f8768a5bb8bd55e1873403caca97f48a1660a44832102755dee90a349578fb",
    }.items():
        data = pinned(sdk / name, expected)
        sdk_pins[name] = {"bytes": len(data), "sha256": expected}
    require(not (sdk / "licenses").exists(), "No private SDK license store")
    cache = R50 / "gradle-home/caches/modules-2/files-2.1"
    artifact_pins = previous["resolvedArtifactPins"]
    require(len(artifact_pins) == 851, "Exact saved dependency cohort")
    verify_tree_pins(sdk, sdk_pins)
    verify_tree_pins(cache, artifact_pins)

    sources = stage_sources(previous, module_overlay(ORIGINAL, raw[ORIGINAL]),
                            module_overlay(WRITER, raw[WRITER]), json.loads(raw[WRITER]))
    native = pinned(ROOT / runner["FULL_NATIVE"], runner["FULL_NATIVE_SHA"], 663592)
    work = owned(BASE / ("r-" + uuid.uuid4().hex[:8]))
    work.mkdir(parents=True, exist_ok=False)
    source = owned(work / "source/OneOS")
    project = source / "app-android"
    for name, data in sources.items():
        target = owned(source / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    prior_project = str(ROOT / previous["sourceTree"] / "app-android")
    prior_cache = str(R50 / "project-cache")
    argv = previous["commands"]["assemble"]["argv"].copy()
    require(argv.count(prior_project) == 1 and argv.count(prior_cache) == 1
            and argv.count(":app:assembleFullDebug") == 1
            and "--offline" not in argv and "-Pandroid.builder.sdkDownload=false" in argv,
            "Expected fixed approved full debug command")
    argv[argv.index(prior_project)] = str(project)
    argv[argv.index(prior_cache)] = str(work / "project-cache")
    flag = argv.index("--write-verification-metadata")
    require(argv[flag + 1] == "sha256", "Expected metadata generation flag")
    del argv[flag:flag + 2]
    kotlin_home = "-Pkotlin.project.persistent.dir=" + str(R50 / "kotlin-home")
    require(argv.count(kotlin_home) == 1, "Expected original Kotlin output location")
    argv[argv.index(kotlin_home)] = "-Pkotlin.project.persistent.dir=" + str(work / "kotlin-home")
    argv.extend(["--offline", "-Poneos.retainedWriterGuard=true"])
    require(sha(Path(argv[0])) == runner["JAVA_SHA"], "Same approved JBR")
    env = previous["ownedEnvironment"].copy()
    require(Path(env["ANDROID_HOME"]) == sdk and Path(env["GRADLE_USER_HOME"]) == R50 / "gradle-home",
            "Same private SDK and dependency cache")
    strip = [ast.literal_eval(node.value)
             for node in ast.parse(raw[runner["ENV_PROFILE"]]).body
             if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "STRIP"
                                                    for target in node.targets)]
    require(len(strip) == 1 and isinstance(strip[0], set) and not set(env) & strip[0],
            "Same credential-free process environment")
    require(not any((R50 / "gradle-home/init.d").glob("*"))
            and not (R50 / "gradle-home/gradle.properties").exists(),
            "No private Gradle startup injection")

    # Load only the existing bounded child-ownership helper from its pinned source.
    node = [n for n in ast.parse(raw[COMMAND]).body
            if isinstance(n, ast.FunctionDef) and n.name == "command"]
    require(len(node) == 1, "Exact bounded child command helper")
    limits = [n for n in ast.walk(node[0]) if isinstance(n, ast.Constant) and n.value == 45]
    require(len(limits) == 2, "Expected bounded command timeouts")
    for limit in limits:
        limit.value = 900
    scope = {**runpy.run_path(str(ROOT / COMMAND)), **globals(), "STRIP": strip[0]}
    exec(compile(ast.Module(body=node, type_ignores=[]), COMMAND, "exec"), scope)

    result = {"schema": "retained-writer-full-debug/v1", "status": "FAILED",
              "inputs": PINS, "sourceChanges": sorted(CHANGE_SET), "commands": {},
              "offline": True, "sourceTree": relative(source), "phoneActions": False}
    try:
        result["commands"]["assemble"] = scope["command"](argv, work, env, "assemble")
        require(all((source / name).read_bytes() == data for name, data in sources.items()),
                "Staged source and verification metadata must be conserved")
        verify_tree_pins(sdk, sdk_pins)
        verify_tree_pins(cache, artifact_pins)
        require(not (sdk / "licenses").exists(), "No SDK license store added")
        apks = list((project / "app/build/outputs/apk/full/debug").glob("*.apk"))
        require(len(apks) == 1, "Expected one guarded writer Full Debug APK")
        apk = contained(apks[0])
        result["apk"] = runner["inspect_debug_apk"](
            apk, project, native, sources["app-android/packages/debug-download-assets.tsv"], sources)
        configs = list((project / "app/build/generated").rglob("BuildConfig.java"))
        require(any(b"boolean RETAINED_WRITER_GUARD = true;" in path.read_bytes()
                    for path in configs), "Actual generated full-edition writer guard")
        result["commands"]["verify-signature"] = scope["command"]([
            argv[0], "-Duser.home=" + env["HOME"], "-Djava.io.tmpdir=" + env["TMP"],
            "-jar", sdk / "build-tools/37.0.0/lib/apksigner.jar",
            "verify", "--verbose", "--print-certs", apk,
        ], work, env, "verify-signature")
        result["certificate"] = runner["verified_signer_sha256"](
            (work / "verify-signature.stdout").read_text(encoding="utf-8"))
        require(result["certificate"] == delivery["signerCertificateSha256"]
                and sha(apk) == result["apk"]["sha256"], "Verified debug signer and unchanged APK")
        pinned(ROOT / original_apk["path"], original_apk["sha256"], original_apk["bytes"])
        result.update(status="PASS_OFFLINE_GUARDED_WRITER_APK_STATIC_ONLY",
                      inPlaceUpdateSupported=False, livePreparationVerified=False)
    except BaseException as error:
        result.update(failure=type(error).__name__, message=str(error)[:2048])
        for label in ("assemble", "verify-signature"):
            path = work / (label + ".result.json")
            if path.is_file():
                result["commands"][label] = json.loads(path.read_bytes())
        raise
    finally:
        save(work / "receipt.json", result)
        print(json.dumps({"status": result["status"], "receipt": relative(work / "receipt.json")}),
              flush=True)


if __name__ == "__main__":
    run()
