"""Project Google's held SDK 37.0 descriptor into local package metadata."""

import hashlib
import json
from pathlib import Path
import uuid
from xml.dom import Node, minidom
from zipfile import ZipFile


ROOT = Path(__file__).absolute().parents[1]
TOOLCHAIN = ROOT.parent / "out/toolchain"
REPOSITORY = TOOLCHAIN / "metadata/android-repository.xml"
ARCHIVE = TOOLCHAIN / "downloads/platform-37.0_r02.zip"
PLATFORM = ROOT / "out/full-apk-build/r-50dc28be/sdk/platforms/android-37.0"
REPOSITORY_SHA = "fb1bd2fcd70b6116519563f1ff96cc578381e4e29237ab05ec8920f0864a7955"
ARCHIVE_SHA = "840b23e827f96e64aea4c89a1194aac3dc5f6bad37edb231c5c795d890330e8d"
REQUIRED_FIELDS = ("type-details", "revision", "display-name", "uses-license")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def child(parent, name):
    nodes = [n for n in parent.childNodes if n.nodeType == Node.ELEMENT_NODE and n.tagName == name]
    require(len(nodes) == 1, f"Expected one official {name}")
    return nodes[0]


def text(node):
    return "".join(n.data for n in node.childNodes if n.nodeType == Node.TEXT_NODE).strip()


def file_digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main():
    source = REPOSITORY.read_bytes()
    require(hashlib.sha256(source).hexdigest() == REPOSITORY_SHA
            and b"<!DOCTYPE" not in source, "Exact held Google repository metadata")
    official = minidom.parseString(source)
    rows = [row for row in official.getElementsByTagName("remotePackage")
            if row.getAttribute("path") == "platforms;android-37.0"]
    require(len(rows) == 1, "Expected official Android 37.0 platform")
    row = rows[0]
    details = child(row, "type-details")
    require(details.getAttribute("xsi:type") == "sdk:platformDetailsType"
            and text(child(details, "api-level")) == "37.0"
            and not text(child(details, "codename"))
            and text(child(details, "extension-level")) == "22"
            and text(child(details, "base-extension")) == "true"
            and text(child(child(row, "revision"), "major")) == "2"
            and child(row, "channelRef").getAttribute("ref") == "channel-0",
            "Expected stable SDK 37.0 revision 2 platform and extension")
    complete = child(child(child(row, "archives"), "archive"), "complete")
    checksum = child(complete, "checksum")
    require(checksum.getAttribute("type") == "sha1"
            and text(child(complete, "url")) == ARCHIVE.name
            and ARCHIVE.stat().st_size == int(text(child(complete, "size")))
            and file_digest(ARCHIVE, "sha1") == text(checksum)
            and file_digest(ARCHIVE) == ARCHIVE_SHA, "Exact published platform archive")
    with ZipFile(ARCHIVE) as archive:
        for name in ("android.jar", "source.properties", "build.prop", "sdk.properties"):
            require((PLATFORM / name).read_bytes() == archive.read("android-37.0/" + name),
                    f"Copied platform differs from official archive: {name}")

    license_ref = child(row, "uses-license").getAttribute("ref")
    licenses = [n for n in official.getElementsByTagName("license")
                if n.getAttribute("id") == license_ref]
    require(license_ref == "android-sdk-license" and len(licenses) == 1,
            "Expected official license reference in metadata")
    common = official.documentElement.getAttribute("xmlns:common")
    local = minidom.getDOMImplementation().createDocument(common, "common:repository", None)
    for name in ("xmlns:common", "xmlns:sdk", "xmlns:xsi"):
        local.documentElement.setAttribute(name, official.documentElement.getAttribute(name))
    local.documentElement.appendChild(local.importNode(licenses[0], True))
    package = local.createElement("localPackage")
    package.setAttribute("path", row.getAttribute("path"))
    package.setAttribute("obsolete", "false")
    for name in REQUIRED_FIELDS:
        package.appendChild(local.importNode(child(row, name), True))
    local.documentElement.appendChild(package)
    descriptor = local.toxml(encoding="utf-8") + b"\n"
    check = minidom.parseString(descriptor)
    installed = child(check.documentElement, "localPackage")
    require(all(child(installed, name).toxml() == child(row, name).toxml()
                for name in REQUIRED_FIELDS), "Local package fields differ from Google metadata")

    run = ROOT / "out/full-apk-sdk37-metadata" / ("r-" + uuid.uuid4().hex[:8])
    run.resolve().relative_to((ROOT / "out").absolute())
    for path in (ROOT, ROOT / "out", run.parent, run):
        require(not path.is_symlink() and not getattr(path, "is_junction", lambda: False)(),
                "Output reparse point refused")
    run.mkdir(parents=True, exist_ok=False)
    package_path = run / "package.xml"
    with package_path.open("xb") as stream:
        stream.write(descriptor)
    require(package_path.read_bytes() == descriptor, "Local metadata readback differs")
    result = {
        "schema": "private-sdk37-local-metadata/v1",
        "status": "PREPARED_UNSELECTED_GOOGLE_LOCAL_PACKAGE",
        "officialRepository": "https://dl.google.com/android/repository/repository2-3.xml",
        "repositorySha256": REPOSITORY_SHA,
        "archiveSha256": ARCHIVE_SHA,
        "archivePublisherSha1": text(checksum),
        "package": "platforms;android-37.0",
        "revision": 2,
        "androidJarSha256": file_digest(PLATFORM / "android.jar"),
        "descriptor": package_path.relative_to(ROOT).as_posix(),
        "descriptorSha256": hashlib.sha256(descriptor).hexdigest(),
        "sdkModified": False,
        "licenseAcceptanceWritten": False,
    }
    receipt = run / "receipt.json"
    with receipt.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"receipt": receipt.relative_to(ROOT).as_posix(), **result}))


if __name__ == "__main__":
    main()
