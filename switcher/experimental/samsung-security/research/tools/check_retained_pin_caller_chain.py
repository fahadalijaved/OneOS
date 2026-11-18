#!/usr/bin/env python3
"""Read back the fixed, offline PIN chain. A successful readback keeps ingress closed."""

import ast
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import zipfile


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY = "compat/android/com/appleexploit/oneos/security/authority/"
TRANSPORT = "compat/android/com/appleexploit/oneos/security/transport/"
HOST_DEX = "out/retained-view-ingress-host-dex/r-1f7af7d81f40/receipt.json"
HOST_APK = "out/retained-view-ingress-host-package/r-698a94c6149a/receipt.json"
CHECK_BUILD = "out/retained-pin-source-build/r-c0b68b59be5c/receipt.json"
GUEST_INGRESS = "inventory/guest-pin-check-systemserver-ingress.json"
GUEST_UI = "inventory/guest-pin-systemui-retarget-cut.json"
HOST_BODIES = "inventory/credentials.json"
SUBJECT = "inventory/retained-physical-user-worker-boundary.json"
CODECS = "out/retained-pin-codec-proof/COMPARISON.json"
CALLBACK = "out/pin-progress-callback-wire/EVIDENCE.json"
DEX_READER = "tools/test_credential_transport.py"
PINS = {
    HOST_DEX: "9554b9c0da952f340e72491c03cabd0aa2d6a09a77117a7f52d8a640bd12e7fd",
    HOST_APK: "dd37ed39f6e5df34a505bbd6e6fcd9bcdb8201f912275eaae068a78d62ab4711",
    CHECK_BUILD: "952d4e49dcd45073cd2ca6d215094ab8288a7372a05bc777961ae47b7cda7d15",
    GUEST_INGRESS: "0eb4c11f0285ef4c14b94c5ce4b321f532a0ab475d9fb4fbe2e6a6f7bfdc868b",
    GUEST_UI: "5be5884b8bde5ac028186ab2ae11e7cf3c294d84051d23cdd2d245ac1eabb9be",
    HOST_BODIES: "333118f3876c61f641d9a8aae82bd11ed61d6366a28e916ddd58755c4a5ef3b8",
    SUBJECT: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
    CODECS: "a83398d8e0aba2c8cc0a29a920f21a1374484595887e2c877843275134c36cd0",
    CALLBACK: "f3dd8571821b0733e660e7d60818a9aebdf28d3fc4721a77b252622927f132ef",
    DEX_READER: "dc4bd404d0720402faabf367689843b3da8c4d23de8b5614ae95e9fd5db780b3",
    AUTHORITY + "PreparedRetainedPinEndpoint.java": "3062e453a50a0d9d609d588af6aa0e4978b29c038597fd8e6aff6b28ac5dcfe6",
    AUTHORITY + "PreparedRetainedPinCheckOwner.java": "4d3aeab1c80725506cb9f1ec074cc9929ff55fe5251d9abbfe253ef374770e02",
    AUTHORITY + "PreparedRetainedPinOperationOwner.java": "6b84a4d17a3f89d8b8e41e77e889e9f6dea684435075d14026871502e6f4c1bb",
    TRANSPORT + "PreparedSamsungPinVerifyClient.java": "76c6b2b5904776ad242fbb0058a73c516af39fa2e3bba85d9b323a652103e44a",
    TRANSPORT + "PreparedRetainedPinEndpointClient.java": "dde0022ec22ac66cbf89de43f2f34c12e0bc70b51333d005068a8e1e8b06934f",
    TRANSPORT + "GuestPinCheckRequest.java": "a5fb4e6f6ae6af6aa923865021070eaba9e79e088fa55fd9df2f78b196fc1b61",
    TRANSPORT + "PinCheckCompletion.java": "338d8900998c7d008df2462ab89c671842fa83b4e1fbb192892ab8a2a5be0726",
    "out/retained-view-ingress-build/r-2dc4e293/host-src/RetainedPinHostModule.java": "995cc3b864e465ff5c01247c10f1f50320b5ba0d31a422bd1405d12f9f2a0324",
}
CHECK_OWNER = "Lcom/appleexploit/oneos/security/authority/PreparedRetainedPinCheckOwner;"
ENDPOINT = "Lcom/appleexploit/oneos/security/authority/PreparedRetainedPinEndpoint;"
MAX_BYTES = 128 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path, digest, size=None):
    with (ROOT / path).open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES and (size is None or len(data) == size), path + " size")
    require(hashlib.sha256(data).hexdigest() == digest, path + " SHA-256")
    return data


def artifact(row):
    return read(row["path"], row["sha256"], row["bytes"])


def archive_member(data, entry, digest):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        matches = [row for row in archive.infolist() if row.filename == entry]
        require(len(matches) == 1 and matches[0].file_size <= MAX_BYTES, entry + " ZIP entry")
        content = archive.read(matches[0])
    require(hashlib.sha256(content).hexdigest() == digest, entry + " SHA-256")
    return content


def own_dex_reader(data):
    # Use only the pinned ordinary-DEX declaration reader, with the same hashed bytes.
    tree = ast.parse(data, filename=DEX_READER)
    function, = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "dex_names"]
    namespace = {"struct": struct, "hashlib": hashlib}
    exec(compile(ast.Module(body=[function], type_ignores=[]), DEX_READER, "exec"), namespace)
    return namespace["dex_names"]


def readback():
    captured = {path: read(path, digest) for path, digest in PINS.items()}
    records = {path: json.loads(data) for path, data in captured.items() if path.endswith(".json")}
    parse_names = own_dex_reader(captured[DEX_READER])
    host = records[HOST_DEX]["dex"]
    host_bytes = artifact(host)
    host_names = parse_names(SimpleNamespace(read_bytes=lambda: host_bytes))
    require(host_names == host["definitions"] and len(set(host_names)) == 47, "Host DEX closure")
    require(CHECK_OWNER in host_names and ENDPOINT not in host_names, "Host endpoint absence changed")
    package = records[HOST_APK]
    require(package["dex"] == host, "Host APK receipt DEX")
    require(archive_member(artifact(package["apk"]), "classes.dex", host["sha256"]) == host_bytes,
            "Host APK DEX bytes")

    isolated = records[CHECK_BUILD]["dex"]
    isolated_bytes = artifact(isolated)
    isolated_names = parse_names(SimpleNamespace(read_bytes=lambda: isolated_bytes))
    require(len(set(isolated_names)) == len(isolated_names) == 24, "Separate PIN component closure")
    require(CHECK_OWNER in isolated_names and ENDPOINT in isolated_names, "Separate PIN endpoint missing")

    guest = records[GUEST_INGRESS]
    ui = records[GUEST_UI]
    require(not guest["routeArmed"] and not ui["retargetSelectedOrEmitted"]
            and not ui["liveSelectionObserved"], "Guest selection evidence changed")
    for row in guest["archivePins"].values():
        artifact(row)
    ui_dex, = [row for row in ui["apkDexEntries"] if row["physicalDex"] == "classes3.dex"]
    archive_member(artifact(ui["matchingCachedApk"]), "classes3.dex", ui_dex["physicalDexSha256"])

    proofs = records[HOST_BODIES]["methodProofs"]
    check, = [row for name, row in proofs.items() if name.startswith("samsung:")
              and "/LockSettingsService;->checkCredential(" in name]
    require(check["accessFlags"] == 17 and check["hasCode"] and check["logicalHeaderOffset"] == 10057984,
            "Original host check method shape")
    require(check["bodySha256"] == "a17ca685272cb966f3974ee4eb2dcabf7001272eae165dacc71e2c175075d35b",
            "Original host check body")
    return {
        "status": "OFFLINE_READBACK_PASSED_INGRESS_CLOSED",
        "admitted": False,
        "hostPreparationDex": host["sha256"],
        "hostPreparationApk": package["apk"]["sha256"],
        "hostEndpointDefinitionPresent": False,
        "separateCheckComponentDex": isolated["sha256"],
        "guestSystemUiDex": ui_dex["physicalDexSha256"],
        "guestFrameworkAndServices": {name: row["sha256"] for name, row in guest["archivePins"].items()},
        "hostOriginalCheckBody": check["bodySha256"],
        "missing": ["selected_guest_route", "host_endpoint_publication_and_delivery",
                    "live_caller_and_physical_subject_lease", "single_request_and_callback_custody"],
        "sourceAndEvidencePins": PINS,
    }


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("This readback takes no arguments")
    print(json.dumps(readback(), indent=2))
