"""Validate the saved preparation cohort's identity and the real host profile parser offline."""

import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import uuid
import zipfile


ROOT = Path(__file__).absolute().parents[1]
INDEX = "inventory/retained-view-preparation-ingress.json"
WRITER_TOOL = "tools/build_retained_writer_debug.py"
PREVIOUS_MANIFEST = "out/guarded-writer-install-review/INSTALL-CONTAINMENT.json"
RELEASE_COMPARE = "out/full-apk-actual-signer-review/UPDATE-COMPATIBILITY.json"
PROBE = "compat/models/retained-view-profile/RetainedViewProfileProbe.java"
CONTROLLER = "assets/root/oneos_retained_root_handoff"
PROFILE_CLASS = "com/appleexploit/oneos/security/authority/HostRootLinkProfileV2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    require(digest((ROOT / WRITER_TOOL).read_bytes()) ==
            "f1ea975bec69092bd32fd85ab37574c84879b26b468f6055bc70c424b5f6ea1c",
            "Exact existing path and pin helpers")
    writer = runpy.run_path(str(ROOT / WRITER_TOOL))
    pinned = writer["pinned"]
    contained = writer["contained"]
    relative = writer["relative"]
    index = json.loads(contained(ROOT / INDEX).read_bytes())
    expected = {
        "apk": "57cd32299db8561f10f4c7031d1754860926bf9b60a71f42bd52c9ffacac95fb",
        "apkBuild": "82b189032640633f9f5161ea5045e74bc8a9a3c3f9b99788d408b45a99625ad9",
        "sdkCompile": "621a3f712028582463e5cbd3500bfd49cf87c53910689b72d6596df49dd60f44",
        "hostDexBuild": "9554b9c0da952f340e72491c03cabd0aa2d6a09a77117a7f52d8a640bd12e7fd",
        "hostDex": "54955e1321d252deb20947c9b10933f3639e31b89b1a03522a7156c95725c745",
    }
    observed = {}
    for name, sha in expected.items():
        row = index[name]
        require(row["sha256"] == sha, "Selected preparation input changed: " + name)
        observed[name] = pinned(ROOT / row["path"], sha, row.get("bytes"))
    build = json.loads(observed["apkBuild"])
    dex = json.loads(observed["hostDexBuild"])
    sdk = json.loads(observed["sdkCompile"])
    require(build["status"] == "PASS_OFFLINE_APP_PREPARATION_APK_ONLY"
            and build["apk"]["sha256"] == expected["apk"]
            and dex["status"] == "PASS_PC_RETAINED_VIEW_INGRESS_HOST_DEX_ONLY"
            and dex["dex"]["sha256"] == expected["hostDex"]
            and dex["sdkReceipt"]["sha256"] == expected["sdkCompile"]
            and "L" + PROFILE_CLASS + ";" in dex["dex"]["definitions"], "Exact app and host cohort")

    before = json.loads(pinned(ROOT / PREVIOUS_MANIFEST,
        "9417d6e0879e3026f311838ab0e7a25954374b566c39e0b865ee579c6f40c502"))["candidate"]
    release = json.loads(pinned(ROOT / RELEASE_COMPARE,
        "2380ea7e2ebda95addd097fee5a3a134bad0349aa070553849a426276e8e115f"))
    app = contained(ROOT / index["apk"]["path"])
    with zipfile.ZipFile(app) as archive:
        manifest = archive.read("AndroidManifest.xml")
        native = archive.read(CONTROLLER)
    require(digest(manifest) == before["binaryManifest"]["sha256"] and
            len(manifest) == before["binaryManifest"]["bytes"], "Binary manifest equals independently decoded source")
    require(digest(native) == build["apk"]["packagedNativeSha256"] and
            len(native) == build["apk"]["packagedNativeBytes"], "Actual controller identity")
    meta_pin = before["outputMetadata"]
    metadata = json.loads(pinned(app.parent / "output-metadata.json", meta_pin["sha256"], meta_pin["bytes"]))
    package = metadata["applicationId"]
    elements = metadata["elements"]
    require(package == before["package"] == release["package"] and len(elements) == 1
            and elements[0]["outputFile"] == app.name and elements[0]["versionCode"] == before["versionCode"],
            "Exact package, signer comparison subject and version")
    sign = build["commands"]["verify-signature"]
    require(sign["exitCode"] == 0 and sign["ownedProcessReaped"], "Actual signer check finished")
    stdout = sign["stdout"]
    verification = pinned(ROOT / stdout["path"], stdout["sha256"], stdout["bytes"]).decode("utf-8")
    signer = build["certificate"]
    require(signer == release["candidateCertificateSha256"] == index["apk"]["debugSignerSha256"]
            and signer in verification and signer != release["installedCertificateSha256"],
            "Real app debug signer differs from installed release")

    host = sdk["cohorts"]["host"]
    class_rows = {name: row for name, row in host["classes"].items()
                  if name == PROFILE_CLASS + ".class" or name.startswith(PROFILE_CLASS + "$")}
    require(len(class_rows) == 3, "Exact parser class closure")
    tools = dex["tools"]
    tool_paths = {key: Path(tools[key]["path"]) for key in ("java", "androidJar")}
    for key, path in tool_paths.items():
        data = path.read_bytes()
        require(len(data) == tools[key]["bytes"] and digest(data) == tools[key]["sha256"],
                "Same approved Java or SDK input")

    work = contained(ROOT / "out/retained-view-profile-candidate" / ("r-" + uuid.uuid4().hex[:8]))
    work.mkdir(parents=True, exist_ok=False)
    for name, row in class_rows.items():
        output = work / "classes" / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pinned(ROOT / host["classDirectory"] / name, row["sha256"], row["bytes"]))
    source = work / Path(PROBE).name
    source.write_bytes(contained(ROOT / PROBE).read_bytes())
    fields = [package, signer, expected["apk"], str(elements[0]["versionCode"]), digest(native), str(len(native))]
    java = tool_paths["java"]
    argv = [str(java), "-Duser.home=" + str(work), "-Djava.io.tmpdir=" + str(work),
            "-cp", os.pathsep.join([str(work / "classes"), str(tool_paths["androidJar"])]), str(source), *fields]
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
    env.update(TMP=str(work), TEMP=str(work), TMPDIR=str(work), PATH=str(java.parent))
    result = subprocess.run(argv, cwd=work, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                            timeout=35, check=False)
    (work / "probe.stdout").write_bytes(result.stdout)
    (work / "probe.stderr").write_bytes(result.stderr)
    require(result.returncode == 0 and not result.stderr and result.stdout.strip() ==
            b"PASS exact V2 profile roundtrip and six format refusals", "Actual saved parser probe failed")
    require(writer["sha"](app) == expected["apk"], "APK identity preserved")
    receipt = {
        "status": "PASS_PC_PROFILE_SYNTAX_ONLY_RELEASE_IDENTITY_BLOCKED",
        "inputs": expected,
        "parsedFields": dict(zip(("package", "signer", "apk", "code", "native", "bytes"), fields)),
        "probeSourceSha256": digest(source.read_bytes()),
        "profileClassSha256": class_rows[PROFILE_CLASS + ".class"]["sha256"],
        "probeExit": result.returncode,
        "formatRefusals": 6,
        "verifiedInstalledReleaseInPlaceUpdate": False,
        "protectedLoadInvoked": False,
        "deviceProfileWritten": False,
    }
    output = work / "receipt.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(relative(output), writer["sha"](output))


if __name__ == "__main__":
    main()
