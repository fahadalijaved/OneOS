# Independent architecture and recovery review

Status: initial static review, November 5, 2026. No architecture is accepted and
no phone experiment is authorized. This review owns only its gate artifacts.
The parent ColorGlass implementation remains paused.

## Finding

The smallest useful proof is one Samsung-authorized credential verification,
followed by one existing-enrollment fingerprint authentication and one fresh
authentication-bound cryptographic operation, initiated through genuine ColorOS
presentation. It must preserve the host's credential/protector/enrollment
identities and demonstrate host access after return and a later separately
approved cold boot. A view dismissal, copied PIN, positive Binder response,
matching class, compiled service or authored model cannot establish that proof.

This proof is currently blocked before device execution: no surviving Samsung
credential authority, complete compatible service transplant, isolated guest
hardware namespace or cryptographically authenticated operation path has been
established. The mounted OS capture supplies executable/configuration evidence;
its ten captured roots exclude live `/data` and `/metadata` security state.

## Evidence and its limits

Observed source facts, independently reread from pinned OneOS commit
`2a5f41043b4a69399cae058bad213cdef7408e88`:

* `switcher/assets/oneos_switch.sh:971,999,1011` stops host zygote, kills
  `system_server` and keeps host zygotes stopped. A service in that process does
  not survive merely because its Java definition is available.
* `oneos_switch.sh:614-623` requests global Permissive mode. Preservation of
  authentication identities alone cannot establish a protected security boundary
  while this remains the selected operating policy.
* `switcher/patches/guest_no_gatekeeper.py:59-74,159-176` targets both credential
  setters and exact Gatekeeper enrollment/clear calls. Its `:32-33` description of
  challenge verification as read-only is patch-author commentary, not a proof
  that authentication has no policy/throttle/token/re-enrollment effects.
* `guest_no_weaver.py:30,53-58` replaces the service getter with null. Its account
  of an earlier host slot collision is historical evidence, not a new hardware
  test or a complete collision audit of this image.
* `guest_no_vold_keys.py:23-27,40-46` removes create/destroy/protection/unlock/lock
  user-key calls while callers continue. Therefore caller success cannot prove
  CE storage was unlocked or protected correctly.
* `guest_no_biometric_cleanup.py:59-80` clears unknown-template cleanup work and
  finishes that cleanup client successfully. It neither maps existing Samsung
  enrollment metadata nor demonstrates authentication or every deletion path.
* `return_to_oneui.sh:214,223` kills the stop loop and processes matching
  `system_server`; `:420,435-470,497-509` can select or force reboot;
  `:897-929` checks returned framework stability and user unlock. These are script
  recovery mechanisms, not new acceptance evidence. A retained service named
  `system_server` can also become a target of existing broad cleanup.

All seven directly inspected patch/switch/prepare/return files matched the parent
source-pins.json SHA256 and size on this review. The immutable Samsung capture is
20,434,769,920 bytes, SHA256
`28eb27547fcc96348aa54f614a77aecd8bfcdbf875b61de2dd5279787985d96e`,
per parent `inventory/os-comparison.json`; mounted capture identity does not
certify a stock partition image or current installed guest image.

Inputs: parent `inventory/oneos-feasibility-20261105.md`,
`inventory/os-comparison.json`,
`out/oneos-feasibility-20261105/source-pins.json`, and the exact ignored OneOS
source snapshot under `firmware/reference/OneOS/<commit>/`.

## Alternatives under review

| Candidate | Concrete potential | Current blocking obligation |
| --- | --- | --- |
| Import Samsung LockSettings/fingerprint services into ColorOS | Could retain actual Samsung policy implementation while presenting ColorOS UI. | Establish actual constructor/boot-phase/dependency closure, correct Samsung state paths and crypto/native identity, a single registered owner, Binder semantics and caller identities, cancellation/cleanup, and guarded startup without enrollment or key mutation. Copying service classes alone supplies none of these. |
| Retain Samsung authority outside the stopped host framework | Could centralize existing credentials/templates/policy while the guest delegates. | Identify an actual surviving owner and dependencies; prove startup and safe transfer, authenticated client/user/operation protocol, token/Keystore routing, host return handback and death recovery. Current switch kills host system_server; a small broker is a design hypothesis, not an established service. |
| Genuinely isolated guest security | Could avoid shared-state collisions if hardware and software namespaces are real. | Prove independent Gatekeeper SID/protectors, Weaver allocation, template storage, authenticator IDs, Keystore domains and vold user keys. Same user number or app UID offset is no isolation proof. Separate state also needs an explicit shared-credential change design and does not alone meet Samsung-controlled-existing-enrollment requirements. |

No candidate is rejected solely for size or preferred by assumption. A transplant
must count its real dependency closure. A retained authority must count process,
service, resource and recovery ownership. An isolated guest must first prove
actual isolation before changing any existing guard.

## Minimal staged proof, not an execution proposal

1. **Offline candidate boundary.** Pin selected Samsung and guest bytes, exact
   DEX041 containers and logical headers, runtime/service/native paths and every
   changed call. Define one authority, one mapped user and one session owner.
   Explain startup, permissions, cleanup and return; keep original preservation
   guards unless a concrete equally strong replacement is reviewed.
2. **Separately approved disposable-device credential proof.** Establish baseline
   host unlock, CE/key availability and existing identities before switching.
   Require Samsung-authorized credential verification from genuine ColorOS UI;
   reject wrong credentials without dismissal and honor actual throttle/strong-
   auth outcomes. Avoid enrollment, deletion, synchronization or credential
   change in this first proof. Wrong attempts are not read-only and need a
   bounded approved plan that avoids wipe/lockout surprises.
3. **Existing fingerprint and crypto proof.** After real primary authentication
   permits biometrics, use one existing enrollment, one owned session and one
   fresh operation challenge. Verify a correctly configured auth-bound test key
   rejects use without the required authorization, accepts the actual
   authenticated operation and rejects replay/stale/wrong-operation use. Track
   SID, authenticator identity/type, operation/user/application identity, token
   forwarding and native consumer. Keyguard fingerprint success alone does not
   establish app-key authorization; time-based and per-operation authorizations
   must not be conflated. Any required test-app/key creation needs its own
   reviewed device proposal.
4. **Return and reboot proof.** Drain/cancel guest clients and authority ownership
   before host takeover. Prove host PIN, existing enrollment, protected data and
   representative pre-existing auth-bound keys still work after return. Repeat
   the required checks after a separately authorized cold boot, including
   mandatory primary authentication before fingerprint. A warm/unlocked kernel
   session cannot establish cold-boot CE/protector correctness.

This narrows the first integration target; it does not remove end requirements
for shared credential change/synchronization, enrollment lifecycle, profiles,
policy enforcement, routine failure recovery or daily-use security.

## Preservation and failure requirements

Preserve stable credential type and protector/SID/slot associations, existing
enrollment and authenticator identity, host metadata ownership and encrypted
data/key usability. Do not define preservation as byte-identical all-security
state: correct authentication may legitimately update throttling, strong-auth,
token caches or timestamps. The exact authorized mutation set remains to be
derived from Samsung method bodies. A verification-triggered re-enrollment must
be identified and deliberately handled; it is not automatically safe or allowed.

Each accepted operation needs a current authority/session generation, caller and
user binding, actual request/challenge correlation, single terminal result and
real cancellation acknowledgement. Unknown mapping, dependency death, timeout,
HAL reset, authority restart or return-in-progress must block new admission and
invalidate stale UI results. Cancellation requested or callback returned is not
proof hardware clients have drained. Retain ownership until terminal state is
established; do not start host/guest competing sensor or credential owners.

Return needs an exact owner-aware stop path. Existing process-name kills, zygote
stop loops, binder registrations, mount changes and SELinux restore order must
be reviewed against the chosen authority. A positive check before external work
does not allow publication after return or generation replacement. Recovery
cannot rely on the guest UI, a process it is about to kill, or an unbounded wait
for an unavailable authority.

Reboot is an acceptance boundary and an explicitly unauthorized action here.
Script reboot fallbacks cannot be exercised on the primary phone in this scope.
No live device security state, PIN/hash, protector secret or HAT is needed in a
committed report; do not collect or publish credential material as evidence.

## Concrete independent cross-checks

**Verification is a metadata transaction, not a read-only broker.** Independently
reread the credential worker's initial Samsung SyntheticPasswordManager selected
dump, then corroborated it with the full DEX041 shared-reader receipt
`out/tooling/20261105T123456578906Z-05842b5fac024defad0adda3ef79b5fa/receipt.json`
and its matching raw SHA256. `verifyChallengeInternal` reads the stored
`handle`, calls Gatekeeper verify at code offset `0016`, tests `getShouldReEnroll`
at `0031`, calls actual Gatekeeper `enroll` at `0038`, then saves `handle` at
`0056`, syncs state at `0059` and reverifies at `005c`. This contradicts treating
OneOS patch commentary as evidence that the full verification operation cannot
write. Preserving the blanket enroll suppression while importing this behavior
would change its semantics; lifting the guard without one coherent metadata
transaction owner would expose host identity state. Crash reconciliation and
durable commit order must be specified. Do not assume hardware re-enrollment can
be undone with a Java-side rollback.

**The low-level retained service is not the framework authority.** Startup
worker's retained-name finding was independently reread:
`return_to_oneui.sh:78` pins vold, IVold/default, keystore2, installd and
IGateKeeperService; it does not pin LockSettings/FingerprintService ownership.
`guest_start.sh:106-143` derives guest boot/system-server classpaths and describes
why inherited Samsung lists were unsuitable. Therefore surviving Gatekeeper,
Keystore or HAL daemons do not establish surviving Samsung credential/policy
authority. A service transplant must account for the chosen classloader and
LocalServices graph, not mix whole classpaths by assumption.

**ColorOS's final HAT path is additional OEM behavior.** Independently reread
parent donor decompiled original source, with anchors also listed in
`inventory/coloros-frontend.json`. `OplusLockPatternChecker.java:107-156` schedules
RpmbCheckTask on a matched final response; `:159-175` handles early match by
calling `onPasswordChecked(true,...)`, selecting a user and sending an unlock
broadcast. `RpmbCheckTask.java:30-40` passes GatekeeperHAT to RpmbChecker;
`RpmbChecker.java:65-90` builds a `CE_CMD_PMS_VERIFY` request and calls
`RpmbChannel.processCmdV2`. Therefore a Samsung-compatible checkCredential reply
does not close the genuine frontend contract. Early/final completion ownership,
user switching and this OEM RPMB channel need an explicit reviewed behavior.
These source observations do not establish that RPMB work executes or succeeds
on the selected installed guest, nor that all such OEM paths are enumerated.

**Native inventory does not close native crypto semantics.** The storage worker's
`inventory/storage-keys.json` explicitly labels ELF imports and strings as bounded
evidence, not cryptographic acceptance. Its recorded `/data` and `/metadata`
exclusion agrees with the parent capture roots. Do not promote imported library
names, service registrations or integer namespace declarations into proof of
key isolation, HAT consumption or CE access.

**A provider getter can start cleanup; real success can outlive token failure.**
Independently reread the fingerprint worker's Samsung raw selected dumps, pending
their full shared-reader receipt: `FingerprintProvider.getHalInstance` schedules
noncurrent-user internal cleanup at `00d6`, per-user authenticator-ID loading at
`00db` and current-user cleanup at `00e5`. A hardware-detection probe through this
owner cannot be assumed passive. `AuthenticationClient.onAuthenticated` skips
its local addAuthToken route for BiometricPrompt at `01cf`; the legacy route calls
`KeyStoreAuthorization.addAuthToken` at `01f3`. A nonzero return only logs then
joins continuation `0212`, from which the success callback is still reachable
at `0224`/`0235`. Therefore even an actual Samsung authentication callback is
insufficient evidence that Keystore accepted the token. The correct branch and
the actual auth-bound operation's consumer must be proved independently.

All runtime gates remain unmet. These are static contradictions and requirements
for the root architecture decision, not permission to run the proposed proof.

## Bounded typed-facade candidate review

Follow-up: independent raw-body cross-check after static reader parity review.
`out/tooling/actual-parity.json` records an independent decoder without dexlib
agreeing with all 448 selected Samsung/ColorOS LockSettingsService methods plus
60 VerifyCredentialResponse methods from the two frameworks: 508 methods,
17,250 instructions, 9,139 references, 1,813 branch targets, 782 literals, 711
catch handlers and three switch payloads. This validates that evidence tool's
traced serialization scope, not service startup, framework-wide compatibility or
hardware behavior. Exact framework receipts below have pinned raw hashes; their
field/register/control flow was independently reread. The independent framework
parity extension specifically covers VerifyCredentialResponse, not every Proxy,
Stub, creator or credential type in this report.
The independent decoder did not bit-decode register operands; positive array
payload coverage was zero. Reading register flow in the shared raw output is a
manual review of that output, not an independent register-operand decoder proof.

**Observed source fact: raw Binder forwarding is incompatible.** In
`inventory/coloros-frontend.json` selectedRawProofs and derivedRawContracts,
ColorOS checkCredential Proxy writes transaction 10 at decimal PC 32 and calls
transact at PC 36; Samsung writes 54 at the corresponding PCs. Both use the
descriptor `com.android.internal.widget.ILockSettings`. Samsung Stub's switch at
PC 13 maps key 10 by offset 2045 to PC 2058, where the branch reads an int, calls
`enforceNoDataAvail` at PC 2063, then invokes `setCarrierLockEnabled` at PC 2066.
The normal ColorOS credential parcel contains more fields, so the observed
enforce-no-trailing-data check should reject that request before the carrier
mutation. The finding is wrong dispatch/rejection, not proof that forwarding
this normal parcel changes carrier state. Transaction-name tables in
`inventory/trust-policy.json` agree with this actual branch.

**Observed source fact: the traced value layouts support explicit conversion.**
Both credential writers trace type int, credential byte array, invalid-character
Boolean and unified-profile Boolean. Both response writers trace response-code
int, timeout seconds long, timeout nanos int, HAT byte array and password-handle
long; the creators consume those fields in that order. The selected predicates
use match code 0 and duplicate code 3. The progress Proxy uses transaction 1,
oneway, without arguments on both sides. This evidence closes those selected
wire fields; it does not close every state, private field, policy interface,
callback lifetime or same-name Java type across loaders.

**Inference: a typed facade avoids this particular dispatch error.** A facade
that implements the guest's actual Stub, decodes the guest request, creates the
real types expected by the selected Samsung implementation and invokes that
method, or its Samsung Proxy's correct transaction, need not forward transaction
10 to Samsung's Binder. It must encode the result as the guest type and retain
the real progress callback contract. Thus the transaction mismatch is not by
itself a reason to reject transplantation or a retained authority. This is a
specific architectural route around one proven incompatibility; no facade has
been constructed or shown runnable.

**Observed policy fact: privileged self is not the original caller.** Samsung
LockSettingsService.checkCredential calls checkReadPermission at PC 0 before
clearCallingIdentity at PC 3. The permission helper enforces
ACCESS_KEYGUARD_SECURE_STORAGE. Samsung FingerprintService's selected
canUseFingerprint body first checks biometric permission, then gives actual
Binder UID 1000 or SemUtils.isKeyguard a fast path before ordinary
current-user/profile, AppOps 78/55 and foreground checks. SemUtils.isKeyguard
checks USE_BIOMETRIC_INTERNAL and compares opPackageName to a component package
read from numeric resource 17040392 through its Context. AuthServiceImpl instead
captures caller UID/PID/user and performs its checks before clearCallingIdentity
at PC 236 and operation forwarding at PC 259. These exact trust-policy raw
bodies were independently reread.

Therefore a direct call on the inbound Binder thread, an executor call after a
thread hop and a cross-process call through a privileged facade have different
caller semantics. The design must choose and substantiate one path, authenticate
the original caller/user/operation before clearing identity or losing that
context, and prevent privileged self from silently replacing ordinary caller
policy. Guest permission grants, resource contents and shared UID 1000 cannot
serve as proof of a Samsung-approved keyguard client. This does not require
forging Binder identity; it requires an explicit authenticated delegation
boundary if the original identity cannot reach Samsung's own check unchanged.
The frozen `docs/credentials.md` additionally records Samsung's
onCredentialVerified secure-lock-device branch awaiting an additional factor.
Thus even genuine primary-credential progress must preserve the active policy
state; it cannot justify unconditional ColorOS dismissal in that branch.

**Observed startup fact: a loader does not supply LocalServices ownership.**
In the shared Samsung LockSettingsService constructor receipt
`out/tooling/20261105T123454212027Z-7bee1deb9d7c403087492c4d788a2cd6/receipt.json`,
decimal PCs 643/645/649 load the concrete
StorageManagerService$StorageManagerInternalImpl Class, query LocalServices and
cast; PCs 653/655/659 do the same for SupervisionManagerInternal. LocalServices'
actual getService body obtains an object from its static ArrayMap using the
Class argument. With a distinct child-owned Class key the guest registration is
not that key; with the guest's canonical Class key, any returned object is the
guest's real registration, whose state/data authority still needs proof. A null
lookup can survive CHECK_CAST and be stored; the lookup alone does not establish
an immediate construction exception. No running constructor was observed.

The suspected BiometricHandlerProvider singleton prerequisite was explicitly
checked and rejected as a hard external-startup blocker. Its actual clinit
constructs and stores the singleton at decimal PCs 0/2/5; the callback-handler
getter calls getNewHandler at PC 14 if no cached handler exists. See
`out/tooling/20261105T124423797747Z-d6f58ba967d74062bd39d6b1d1fb3066/receipt.json`,
independently reread. The LSS constructor itself starts ServiceThreads at decimal
PCs 402 and 857, registers receivers at 526 and 940, constructs storage helpers
and publishes its LocalService at 1024. Therefore construction is active owned
work, not a safe passive compatibility probe. These facts establish real
dependency and cleanup obligations, but no demonstrated immediate nonsecurity
dependency that proves all isolated construction impossible. The still-open
boundary is the actual compatible Context/user/storage/supervision/local-service
and lifecycle graph, rather than an assumed whole system_server requirement.

The bounded startup inventory also shows that equal SystemService class names
do not close SystemServiceManager ABI: Samsung startServiceFromJar returns void,
while the selected guest declaration returns SystemService. These are actual
different descriptors, but this review has not established that this exact
method is on the chosen candidate's required path. Do not promote declaration
difference into a claimed exercised failure.

The candidate therefore remains **plausible for further offline closure, not
runnable or security accepted**. It avoids raw Binder misdispatch only. It still
needs compatible original dependencies, one live credential metadata/policy
transaction owner, correct Context/LocalServices/state/native owners, protected
delegation, callback/death/drain semantics and an explicit ColorOS RPMB-channel
decision. No published early-success callback can be retracted by merely
returning an error later; the real early and final source contracts must remain
coherent. Unmapped user/service operations must remain unsupported rather than
fall through to guest policy. The original preservation guards stay in force.

**Minimal crypto-proof correction.** Independently reread the storage worker's
KeyStoreCryptoOperationUtils.getOrMakeOperationChallenge raw receipt
`out/tooling/20261105T123736498302Z-a701adaf9c8e4408a301c00b483aac36/receipt.json`;
its raw SHA256 matches inventory/storage-keys.json. When native
KeyStoreOperation.getChallenge is null, it returns SecureRandom.nextLong instead
at decimal PCs 27-35. A nonzero CryptoObject operation ID alone is therefore not
proof of a native auth-required challenge. The first crypto proof must establish
the real native operation's challenge and required key authorization metadata,
then demonstrate rejection before authorization and completion of that same
fresh operation after genuine authorization. A warm unlocked key or random
fallback ID cannot close the auth-bound-crypto gate.

## Final bounded integration review

Disposition: **accept the root plan as an offline investigation candidate with
the stated open contracts**. This accepts its research boundary and evidence
qualifications only. It selects no runtime architecture, proves no executable
service closure and accepts no phone, credential, biometric, storage or key
behavior. All twelve gates retain their prior status. No new source stream was
opened in this integration pass.

Reviewed root architecture/candidate-plan, completed startup-import,
resource-compat and strong-auth-gating reports and inventories. No material
contradiction was found in the root candidate. The relevant qualifications are:

* **Base resources are not effective policy.** Two selected same-ID meaning
  collisions and one same-name base-value difference do not establish live
  RRO/idmap/configuration/SKU policy or an executed bypass. Copying Samsung's
  false base rate-limiter value would not prove preservation of its current
  policy or authorize a policy change. The root correctly requires an owned
  effective resource environment rather than hard-coded answers.
* **Original ColorOS extra-factor frontend and finish guard exist.** The finish
  body, independently reread with matching raw hash, reads enabled at decimal
  PC 391, pending at 413, returns without finish at 434 when enabled and not
  pending, and has its later finish invocation at 602. The keypad callback
  requests that original dismissal path. An early password-success event is not
  itself unconditional final finish. Preserve the original factor view,
  controller, confirmation and policy gates.
* **Partial progress exists in both OEMs.** The selected inventory records
  Samsung progress/unwrap/SP-challenge PCs 834/861/898 and ColorOS
  865/899/948. Emission order is not a delivery-order guarantee. The earlier
  early/final concern is an integration ownership/readiness requirement, not a
  newly demonstrated timing vulnerability, unauthenticated OEM callback,
  Samsung-only timing mismatch or missing ColorOS factor presentation.
* **False seeds are not applied authority.** Independently reread the repository
  body and matched its raw hash: it boxes/emits false before registering the
  status listener. Enabled state, selected-user StrongAuth, authentication,
  confirmation/ready state and the original consumers must be applied from the
  same authority. Neither registration return nor an initial service notification
  proves callbackFlow/stateIn/JavaAdapter application. Unknown, stale or wrong-
  user state must remain unsupported.
* **Pending disable is not full-factor acknowledgement.** The selected Samsung
  disableSecureLockDevice body was independently reread with matching raw hash.
  At decimal PCs 104-108 it can record pending disable when authentication is
  incomplete. A disable call/return or local ColorOS pending/ready value cannot
  stand in for actual Samsung policy/key/unlock completion. The root and final
  strong-auth report preserve that distinction.

The root's preferred typed guest interface with a coherent Samsung service/state
authority is a constrained next investigation. A retained-authority alternative
remains legitimate at unresolved ownership cuts. No whole-framework import or
tiny broker is assumed necessary. Holding an **already received genuine**
progress event until final primary result and policy readiness is expressly an
unimplemented design requiring its real ordering/lifetime/cancellation contract;
it is not approval to synthesize progress from code 0 or wait for full unlock in
a way that prevents the real factor stage.

One concrete evidence-attribution correction was raised and **resolved**. The
startup table's Samsung lifecycle edge had been described as an exact guest
replacement point. Its corrected row now pins Samsung's boundary and explicitly
leaves the actual guest hook/order to separate source evidence. The revised
startup report SHA256 is
`9f3fd4471040ae03a280f60c4fb2e91f88440c2c5a098fc36324e29aaee64491`,
independently verified. No body-audit replay or source expansion was needed.
The root architecture already left those guest sites unresolved.

Remaining acceptance is the existing gate set: executable startup/dependency
closure, authentic caller/user and applied policy state, one coherent mutation/
data/native owner, semantic OEM/RPMB conversions, actual drain/recovery, and
separately authorized credential/fingerprint/crypto/CE/host-return/cold-boot
evidence. Static resource facts and an existing genuine factor guard close none
of those runtime gates. Reviewed input pins are recorded in review-gates.json.
