#!/usr/bin/env python3
"""Read back the exact host PIN request insertion edges. No live request is admitted."""

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AUTHORITY = "compat/android/com/appleexploit/oneos/security/authority/"
BASE = AUTHORITY + "PreparedRetainedPinOperationOwner.java"
ENDPOINT = AUTHORITY + "PreparedRetainedPinEndpoint.java"
CHECK = AUTHORITY + "PreparedRetainedPinCheckOwner.java"
COHORT = "out/retained-pin-host-cohort/r-15a49021/"
CAPTURE = COHORT + "source/RetainedClosedPinHostCapture.java"
MODULE = COHORT + "source/RetainedPinHostModule.java"
COHORT_RECEIPT = COHORT + "receipt.json"
MODEL = "out/retained-pin-check-tests/r-33c30e7c/"
MODEL_RECEIPT = MODEL + "receipt.json"
FIXTURE = MODEL + "src/tests/model/RetainedPinCheckTest.java"
WRITER = "out/retained-pin-writer-deferral/READBACK.json"
PINS = {
    BASE: "6b84a4d17a3f89d8b8e41e77e889e9f6dea684435075d14026871502e6f4c1bb",
    ENDPOINT: "3062e453a50a0d9d609d588af6aa0e4978b29c038597fd8e6aff6b28ac5dcfe6",
    CHECK: "4d3aeab1c80725506cb9f1ec074cc9929ff55fe5251d9abbfe253ef374770e02",
    CAPTURE: "d51ebee906bd08c41c65be0a3d271b2e14789a851cfabac400a2c933ae2ddcd8",
    MODULE: "697fc626de3771740f0adde8bc243c42cce140398910c0b6fdbed10af0fd3c98",
    COHORT_RECEIPT: "0260dffda000b95cfe2f4a9bf83afc939ae455f2724c6302a07de2d634abfab3",
    MODEL_RECEIPT: "6baf10b603840e7817153b9b6bbf7c0c8040cf7c466933a4a34bf4c6b81f9d41",
    FIXTURE: "9b7d81549419054170e74903021dc44e8034ee29baf017aad641f38d84fce1c6",
    WRITER: "f036a669b642fc78fff1caac36ddc25e773cb4c9e4289bd6fcd4dc7170836db7",
}


def read(path, digest):
    with (ROOT / path).open("rb") as source:
        data = source.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024 or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Held source or receipt differs: " + path)
    return data.decode("utf-8")


def check():
    files = {path: read(path, digest) for path, digest in PINS.items()}
    placements = {}

    def edges(path, *anchors):
        cursor = 0
        for anchor in anchors:
            start = files[path].index(anchor, cursor)
            placements.setdefault(path, []).append({"line": files[path].count("\n", 0, start) + 1,
                                                    "source": anchor})
            cursor = start + len(anchor)

    edges(CAPTURE, "if (retired || reserved) throw unavailable();", "reserved = true;",
          "PreparedRetainedPinOperationOwner.prepare(binding)", "operation = preparedOperation;",
          "PreparedRetainedPinCheckOwner.prepare(preparedOperation)", "check = preparedCheck;",
          "PreparedRetainedPinEndpoint.prepareWithCheck(preparedOperation, preparedCheck)",
          "endpoint = preparedEndpoint;", "if (!ready) retire();", "retired = true;")
    edges(MODULE, "retained.closedPin.retire();", "retained.retireClosedRootLinkIfOnMain();",
          "binding.checkSystemUserBootstrapForControl(registry, family);",
          "owner = closedPin.prepare(binding);", "binding.checkSystemUserBootstrapForControl(registry, family);")
    edges(BASE, "state = DERIVING_CHECK;", "state = PREPARED;", "return result;")
    edges(ENDPOINT, "if (code == CHECK_PIN) return onCheckTransact(data, reply, flags);",
          "private boolean onCheckTransact(", "final int callingUid = Binder.getCallingUid();",
          "localRpcStacks++;", "if (callingUid != SYSTEM_UID)", "data.enforceInterface(DESCRIPTOR);",
          "data.readInt() != VERSION", "ownedPin = data.readTypedObject(credentialCreator);",
          "IBinder callbackBinder = data.readStrongBinder();", "data.enforceNoDataAvail();",
          "callbackFactory.invoke(null, callbackBinder)", "checkOwner.checkPin(ownedPin, callback)",
          "reply.writeTypedObject(response, Parcelable.PARCELABLE_WRITE_RETURN_VALUE);",
          "ownedPin.close();", "localRpcStacks--;")
    edges(CHECK, "public VerifyCredentialResponse checkPin(", "Call call = enterCall();",
          "pin.isPin()", "callbackType.isInstance(nullableCallback)", "check.invoke(endpoint, pin,",
          "Integer.valueOf(physicalUserId), nullableCallback", "finishCall(call);",
          "public void closeAdapterIngress()", "state = CLOSED;", "private Call enterCall()",
          "activeCalls++;")
    edges(FIXTURE, "check(!w.idle() && !w.checkIdle());w.rpc();return null;",
          "w.events()==2 && w.checkCalls()==2", "w.closeEndpoint();return null;",
          "w.checkCalls()==1", 'getMethod("fireLate")')

    cohort = json.loads(files[COHORT_RECEIPT])
    model = json.loads(files[MODEL_RECEIPT])
    writer = json.loads(files[WRITER])
    if (cohort["status"] != "PASS_UNSIGNED_CLOSED_PIN_HOST_COHORT" or cohort["endpointPublished"]
            or model["stagedSourcePins"].get(FIXTURE) != PINS[FIXTURE]
            or model["tests"]["checks"] != 258 or model["completionCellUsed"]
            or writer["pinDeferralAdmitted"]):
        raise ValueError("Unexpected held admission evidence")
    return {
        "status": "EXACT_REQUEST_INSERTION_EDGES_VERIFIED_LIVE_ADMISSION_REFUSED",
        "liveRequestAdmission": False,
        "stockWriterUseIssued": False,
        "preparedEndpointPublished": False,
        "hostCohortDex": cohort["dexSha256"],
        "savedModelNestedCheckCalls": 2,
        "sourceEdges": placements,
        "pins": PINS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-live-admission", action="store_true")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2))
    return 2 if args.require_live_admission and not result["liveRequestAdmission"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
