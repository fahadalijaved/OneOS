# Retained PIN operation owner review

**PASS for the prepared source, saved SDK/D8 output and authored models only.**
The closed-by-default owner remains unselected. The actual host model workflow
passed 16 scenarios and 67 checks using six unchanged SDK-compiled authored
classes and nine exact dependencies. This review performed static saved-byte
inspection; it did not replay a compiler, model, original credential operation,
Android/OEM/native implementation or device action.

The source gate covers Owner `0e0b892c…` and root-owned Binding bridge
`9ecdc5ba…`. Removing only the typed bridge and its fence field restores exact
prior Binding `48f8080b…`. Existing capture/check and metrics paths remain.
The public factory leaves ingress closed; package-private opening checks the
existing main-thread binding and is lifecycle control, not custody or readiness
proof. Terminal close cannot reopen. A private call is allocated before counting,
and no owner lock spans validation, original invocation or capture checks.

The worker calls the cached original public-final
`verifyCredential(hostPin,derivedUser,0)` exactly once on the same worker/caller.
It adds no identity manipulation, worker hop, direct doVerify entry, retry or
synthetic response. The original retains its permission, enterprise, identity and
parcel-cleanup envelope. Exact target Throwable identity, genuine null and genuine
response survive internal accounting; the helper does not retain or log PIN bytes,
responses or HATs. Models cover public behavior, not original OEM algorithms.

PIN-OWNER-API-01 is resolved: `adapterCallsIdle()` ends after this helper's
invocation/internal cleanup, before later reply serialization or delivery.
The real ingress must separately own and drain its outer RPC/request/reply/response
lifetime. An admitted call may still enter the original method after close.
Neither helper-idle nor close grants native DRAINED or resource disposal.

The saved SDK receipt `9095dc5c…` contains exactly six fresh program definitions
(Binding4/Owner2), nine dependencies and two compiler-only host widget ABI types.
The 18,996-byte DEX is `696ee2a5…`; both ABI projections stay outside DEX/model
runtime. Independent inspection rehashed all 72 delivery pins, compared 29 input
snapshots and decoded the class/DEX closure. SDK37 compilation and D8 emission are
PC evidence; D8's unsupported-API37/max36 warning remains recorded.

The actual model receipt `34c817b4…` has five successful commands: four authored
fixture compilations and one JVM run. Independent saved inspection checked 352
delivery pins, 98 snapshots, 59 sources and all 129 class metadata records across
program6/deps9/F34/C49/control1/tests30. Complete class maps stayed unchanged;
production classes were not recompiled or shaped. The sole same-package fixture
control is excluded from production. Runtime classpaths exclude Android/OEM
implementations, compiler projections and application JNI.

Command metadata needs one qualification. The frozen command plan used
case-sensitive string sorting; the reviewed driver used Windows Path sorting.
Actual F/C javac source argument order therefore differs, while exact source sets,
counts, executables, flags, classpaths and every non-source argument match.
Control/test/model argv are byte-exact. Independent reconstruction matches the
actual source-defined Windows order. The earlier pre-use claim of five byte-exact
planned vectors was too broad; its original record and the inaccurate plan remain
historical. This correction required no target rerun or source change.

Three CLI attempts are known. Worker `6c204c` failed manifest strict resolution
before claim (cause UNKNOWN); root `d6b619` rejected a JDK junction before claim.
Neither started a child compiler/JVM. The sole actual fixture/model pipeline used
canonical E: paths with identical admitted JDK bytes and an isolated helper JDK
binding, retaining strict guards. Root's terminal summary is explicitly a
transcription of its observed same-handle completion, not a raw tool transcript.
Own inspection key-scope and source-order failures are also preserved separately.

The supported architecture continuously retains the same genuine Samsung
LSS/policy/storage/biometric/native family as sole authority. Ordinary stock calls
and original deferred work remain legitimate; no global drain is required merely
to change presentation while those resources remain alive. Actual retirement
requires its own completion contract. Stored serial is not per-call reservation;
legitimate UserState evolution is not frozen after verification.

Real adapter dispatch, caller/worker physical-subject admission, continuous native
custody, outer RPC ownership, ART placement and all PIN/fingerprint/key/data
outcomes remain unassembled or unverified. The old transaction55 client does not
automatically route through this helper. No runtime activation is accepted.

Final author evidence `0c7255d9…` was rehashed across all 457 entries. Historical
source-phase normal cards are preserved as exact beforeimages copied after actual
execution and before report publication; they are not claimed as pre-build copies.
Independent private proofs `3bb16c0c…` and `ad8a59b5…` remain unchanged.
