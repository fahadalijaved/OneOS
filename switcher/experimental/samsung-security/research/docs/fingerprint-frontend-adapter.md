# Bounded fingerprint presentation adapter contract

**Source-supported proposal, unimplemented:** convert the common template
identity into an original ColorOS `Fingerprint`; retain genuine authentication,
enrollment and challenge payloads. Remove unsupported OPPO clone routing and
progress extras at their consumers. There is no adapter binary, service,
hardware operation or runtime acceptance from this report. Native Settings,
fingerprint management, user policy and protected app operations remain required.

The input profiles and exact method/hash/PC receipts are in
[the inventory](../inventory/fingerprint-frontend-adapter.json). The existing
fingerprint and construction reports supply parcel/property/native proofs. The
new audit reads only 32 missing methods across ten selected role/classes;
`python -B tools/audit_fingerprint_frontend_adapter.py` rechecks their saved raw
receipts and source assertions. `--collect` requests those bounded methods, with
no whole-archive reference scan. Raw bodies remain ignored under
`firmware/fingerprint-frontend-adapter/`.

## Exact common identity conversion

The original parcel shapes below were already proved in `fingerprint.json`.
The final equal-width integer is **not interchangeable**.

| Wire field/order | Samsung meaning | ColorOS treatment |
| --- | --- | --- |
| String name | Source template display name | Preserve actual name/null semantics; never derive authorization from it |
| Int biometric ID | Source template ID | Preserve exact ID, not list position or a new ID |
| Long device ID | Source identifier's device ID | Preserve exact value; not a universal user/display/sensor mapping |
| Int group ID | Source identifier's group ID | Preserve exact value; never replace explicit authenticated user with this field |
| Final int | Samsung duplicated-image count | Retain in Samsung authority/metadata; do not relabel as OPPO flags |
| ColorOS final int | OPPO extension finger flags | The original four-argument constructor supplies its neutral default zero; usable only after unsupported flag-dependent consumers are unavailable |

The feasible typed conversion is the **existing ColorOS constructor contract**:
`Fingerprint(sourceName, sourceGroupId, sourceBiometricId, sourceDeviceId)`.
Its extension initializes flags to zero. Do not replay the Samsung parcel into
the ColorOS creator or cast same-named classes across loaders. Decode using the
admitted source type and construct using the admitted guest type. Preserve a
genuine null object where the original callback permits it; do not manufacture
a zero-ID template. A consumer requiring a nonnull object must deny an
unsupported/null path safely. This contract does not authorize converting an
unknown OPPO classification into “main user.”

The constructor actually uses `ExtLoader.create(IFingerprintExt, this)`; the
runtime owner must admit the real selected extension/registry as well. Zero is
the observed concrete source default, not proof obtained merely because a
constructor returned or a same-named extension exists.

There is direct original-consumer precedent: Settings
`FingerprintUtils.getFingerListFromUser()` reconstructs standard `Fingerprint`
objects from name/group/id/device at PCs 137, 164 and 193, after separately
partitioning `OplusFingerprint` objects by clone policy. Thus common tuple
conversion itself needs no invented fingerprint flags.

## The flags are also security policy

The separate `OplusFingerprint` type and OEM multiuser endpoint must not be
confused with the standard `Fingerprint` extension. Settings
`isSystemCloneFingerprint` tests `getFingerFlags() & 0x10000000` at PCs 0/4/6.
SystemUI `OplusSwitchUserUtil.isSubUserFingerprint…` tests the same bit plus
template ID. `switchToUserByFp` chooses the OEM clone user or literal user zero,
then reaches `switchToUser` at PC52. The successful-authentication OEM hook
actually calls this path at PC401, with additional family/underage/clone policy
branches in the same original method.

**Required removal/adaptation boundary:** mark unsupported OPPO system-clone
fingerprint enrollment/routing unavailable, remove its controls, list-provider
requests, classification cache, success-hook routes and dependent consumers.
Preserve genuine Samsung current-user/profile/admin policy and actual callback
user; do not replace the entire successful-authentication hook with a constant
return or force a target user. Full caller/cache teardown closure for that removal
is not claimed here. Other OPPO family/privacy/quick-launch features need their
own supported/unavailable treatment before their paths can be admitted.

Hiding a clone menu is insufficient. `getFingerListFromUser()` unconditionally
calls `OplusMultiUserFingerprintManager.getEnrolledFingerprints(myUserId,-1)`
at PC34, even for the ordinary system-user list. Its exception paths can produce
empty lists. Native Settings must instead receive the real Samsung enrollment
list for the genuinely bound target user and sensor; transport failure must
remain unavailable, never a falsely credential-free/enrollment-free list.
The no-argument helper's implicit `myUserId` contract also requires explicit
caller/target-user ownership. `initFingerprintData` additionally queries
`getSystemCloneBiometricId`; suppressing only list partitioning leaves that
separate OEM query and dependent UI alive.

## Actually reached callback payloads

| Boundary | Proven payload and delivery | Required adaptation |
| --- | --- | --- |
| Authentication success, receiver transaction 3 | `(Fingerprint, userId, isStrongBiometric)`, one-way; existing sender proof | Convert only the template tuple. Preserve the actual user/strength and the original request's CryptoObject. No HAT is in this UI callback. |
| ColorOS `FingerprintCallback.sendAuthenticatedSucceeded` | Constructs `AuthenticationResult(retainedCryptoObject, fingerprint, user, strong)` at PC21; callback at 26 | Bind the result to the same real request/native key operation; never substitute a new CryptoObject or infer key acceptance from success |
| ColorOS receiver success | `com.android.systemui` invokes callback inline at PC70; other packages use HandlerExecutor at 85 | Preserve both original scheduling paths; capture and validate source callback provenance before any handoff |
| Enrollment, receiver transaction 1 | `(Fingerprint, remaining)`, one-way on both senders | Convert the nested object before guest decoding. The original manager receiver posts only `remaining`; `sendEnrollResult` calls `onEnrollmentProgress(remaining)` at 34. It does not convey template identity to that progress listener. |
| Challenge, receiver transaction 8 | `(sensorId, userId, long challenge)`, one-way on both senders | Preserve sensor/user/challenge exactly. ColorOS internally uses `(long,int,int)` then restores `(int,int,long)` at the public challenge callback. Do not swap roles or generate a replacement challenge. |
| Removal and management | Original removal callback carries `(Fingerprint, remaining)`; Settings uses real IDs for rename/remove | Preserve genuine per-request completion/error behavior and requery the authoritative list; no removal success from an empty local list |

The existing authenticate/detect/cancel request and acquired/detected/failure/error
sender proofs remain bounded evidence. Detect is not authentication. Standard
lockout/error semantics must remain genuine. Vendor acquired/help/animation codes
have no general Samsung-to-OPPO semantic map here: remove unsupported vendor
visual branches or supply a separately proved mapping. Never turn an unknown
vendor event into a match, enrollment completion, cleared lockout or fabricated
OPPO-specific help message.

Settings `FingerprintEnrollProcessor.onEnrollProgress` calls its OPPO animation
range filter at PC23 **before** updating remaining and `mDone`. Only accepted
actual `remaining==0` sets done at PC52. The filter depends on OPPO animation
counts; `startEnrollment` separately queries unsupported OEM total-times before
the genuine enroll call. Remove/adapt that total/percentage/circle dependency
and its progress gate; preserve actual nonnegative remaining events, genuine
terminal zero, error/cancel and listener delivery. The original `steps==-1`
fallback derives steps from first observed remaining, but this is not proof of
a Samsung vendor total. An indeterminate progress presentation is preferable
until real total semantics exist. No synthetic zero or timeout-based completion.

## Required identities and remaining proof

The owner must bind request Binder token/returned request ID, callback endpoint,
operation generation, real sensor, actual user/profile, display and cancellation
signal. Callback arguments do not independently prove that ownership. Check
genuine origin at Binder entry and current admission again before delayed
delivery. The original safe auth callback checks a weak monitor and bound session
before running at PC59. Enrollment's weak processor reference alone is not a
session-generation proof. A cancel return is not terminal callback/HAL drain.
Local in-process delivery needs the admitted direct source/request edge instead
of a supposed remote Binder caller. Shared system UID or a handler thread's own
UID alone never authenticates a callback. Enrollment progress lacks a user or
request ID in its payload, so its receiver/session ownership supplies those roles.

Sensor ID comes from the admitted source provider/session and live registered
properties. Display ID comes from the genuine admitted request/display. Preserve
legitimate source selection/default semantics; never replace missing identities
with zero. Optical/ultrasonic methods consume actual sensorType values 3/2; type
is not strength. Fingerprint device/group fields cannot replace those identities.
Required touch, display, geometry and illumination behavior is not an optional
animation and remains unbound for the real sensor.

Enrollment retains its genuine gatekeeper-handle/HAT, sensor/user challenge and
revocation chain. App authentication retains the exact protected operation ID,
key namespace and authentic token policy. The existing legacy Samsung success
path can notify after failed Keystore token deposit, so this UI conversion proves
neither token acceptance nor key use. Genuine authority, callbacks, vendor-code
mapping, unsupported-feature removal and runtime ownership remain unassembled.
No firmware, metadata, enrollment or phone state was changed.
