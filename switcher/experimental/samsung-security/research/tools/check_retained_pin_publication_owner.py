#!/usr/bin/env python3
"""Check the held Samsung bootstrap owner. This offline input cannot admit publication."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY = "compat/android/com/appleexploit/oneos/security/authority/"
MODULE = "out/retained-view-ingress-build/r-2dc4e293/host-src/RetainedPinHostModule.java"
BINDING = AUTHORITY + "PreparedRetainedPinBinding.java"
BASE = AUTHORITY + "PreparedRetainedPinOperationOwner.java"
CHECK = AUTHORITY + "PreparedRetainedPinCheckOwner.java"
ENDPOINT = AUTHORITY + "PreparedRetainedPinEndpoint.java"
CALLER = "out/retained-pin-caller-chain/READBACK.json"
WRITERS = "inventory/retained-physical-user-worker-boundary.json"
PINS = {
    MODULE: "995cc3b864e465ff5c01247c10f1f50320b5ba0d31a422bd1405d12f9f2a0324",
    BINDING: "f7f006d2d9db467d46abb1a14f94bcabd63f5e63f6218b1eef43d926729a35ed",
    BASE: "6b84a4d17a3f89d8b8e41e77e889e9f6dea684435075d14026871502e6f4c1bb",
    CHECK: "4d3aeab1c80725506cb9f1ec074cc9929ff55fe5251d9abbfe253ef374770e02",
    ENDPOINT: "3062e453a50a0d9d609d588af6aa0e4978b29c038597fd8e6aff6b28ac5dcfe6",
    CALLER: "675e8af1c84aab8a5bf4c58c563c22d4b5cebd597f1a39120d3d95010a555543",
    WRITERS: "53c702b74d46b2baad6ac1b53d4638fae2566edfa35c4c878902ec38312e8284",
}


def read(path, expected):
    with (ROOT / path).open("rb") as source:
        data = source.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(path + " does not match held evidence")
    return data.decode("utf-8")


def ordered(source, *anchors):
    cursor = 0
    for anchor in anchors:
        found = source.find(anchor, cursor)
        if found < 0:
            raise ValueError("Held source edge differs: " + anchor)
        cursor = found + len(anchor)


def check():
    files = {path: read(path, digest) for path, digest in PINS.items()}
    module = files[MODULE]
    ordered(module, 'getDeclaredMethod("startBootPhase", timing, int.class)',
            "result = chain.proceed();", "require(currentPhase.getInt(receiver) < 1000);",
            "if (normal && entry.candidate)", "currentPhase.getInt(entry.receiver) == 1000",
            "attempted = true;", "controller = created;", "created.capture(this);")
    ordered(module, "private void capture(RetainedPinHostModule module)",
            "registry = PreparedRetainedUserRegistryCapture.captureExisting();",
            "registry.systemServiceManagerForControl() == source.receiver",
            "registry.systemServerLoaderForControl() == module.servicesLoader",
            "family = PreparedRetainedSecurityFamilyCapture.captureExisting(registry);",
            "binding = PreparedRetainedPinBinding.captureExisting(registry, family);",
            "binding.checkSystemUserBootstrapForControl(registry, family);",
            "owner = PreparedRetainedPinOperationOwner.prepare(binding);",
            "binding.checkSystemUserBootstrapForControl(registry, family);")
    ordered(files[BINDING], "void checkSystemUserBootstrapForControl(",
            "require(current.id == 0 && subject.id == 0", "metadata.checkSystemUserBootstrap(subject);")
    ordered(module, "private void poison()", "failed = true; retained = controller;",
            "retained.retireClosedRootLinkIfOnMain()")
    ordered(module, "private void retireClosedRootLinkIfOnMain()", "Thread.currentThread() != source.thread",
            "if (retained != null) retained.retire();")
    for path, close, idle in ((ENDPOINT, "closeIngress", "localRpcStacksIdle"),
                              (CHECK, "closeAdapterIngress", "adapterCallsIdle"),
                              (BASE, "closeAdapterIngress", "adapterCallsIdle")):
        ordered(files[path], f"public void {close}()", "synchronized (lock)", "state = CLOSED;",
                f"public boolean {idle}()")
    caller = json.loads(files[CALLER])
    if (caller["status"] != "OFFLINE_READBACK_PASSED_INGRESS_CLOSED"
            or caller["admitted"] or caller["hostEndpointDefinitionPresent"]):
        raise ValueError("Caller evidence is not the held closed cohort")
    return {
        "status": "HELD_BOOTSTRAP_OWNER_PROVED_PUBLICATION_REFUSED",
        "publicationAllowed": False,
        "owner": "private HostBootstrapController after original phase-1000 normal return",
        "subject": "same captured system-user0 main-thread observation, no worker lease",
        "heldPreparationEndpoint": "absent",
        "approvedSession": None,
        "blockers": ["worker_physical_subject_lease", "authenticated_guest_binder_delivery",
                     "actual_request_occurrence_and_retirement"],
        "pins": PINS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-publication", action="store_true",
                        help="return failure unless publication is admitted")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 2 if args.require_publication and not result["publicationAllowed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
