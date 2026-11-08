# Retained SystemServer capture diagnostic: independent review

Disposition: **PASS for the bounded source and saved PC APK only**. The reviewed
APK is `OneOS-Retained-Capture-0.0.1.apk`, 21,104 bytes, SHA-256
`bb0eba1047608b153d5a8f072ac334a496a42c32a19abf9fe3661a9dce766355`.
This review grants no installation, scope activation, restart or phone execution.
No Android, Vector hook, OEM class, authentication or native backend ran in this
review. The inventory pins the actual inputs, saved outputs and private proofs.

## Source, API and lifetime

The actual captured Samsung target is public-final
`SystemServiceManager.startBootPhase(TimingsTraceAndSlog,int):void`, not a
`Context,int` overload. Module `bea37efa…` resolves this exact declaration without
initialization using the callback's services loader. Absent/invalid permit returns
before target lookup or hook installation. API102, system-server, UID1000 and
the exact recorded S26 SDK37 properties are restrictions, not source authority.

The installed Vector DEX `b75c8894…` supplies the used declarations. Selected
actual dispatcher bodies show the callback gets its supplied loader and that
PASSTHROUGH rethrows the original hook/proceed Throwable without the alternative
framework Throwable-log path. HookBridge installs before subsequent Java
handle/map work; partial installation can therefore precede a throw. The corrected
module retains an obtained handle and permits capture only after nonnull/exact
handle acknowledgement. Failure leaves any partial hook pass-through; it does
not claim successful installation or safe unhook.

Actual APK DEX `7d8a25d1…` has exactly Module, PermitFile, Capture and
Capture$Metadata. Its sole `Chain.proceed()` is PC0, outside all owned try ranges.
All return-object instructions return its original result register. Original
arguments and timing object are untouched. Only normal return from phase1000 can
reach the once-only attempt; genuine main thread, profile and permit are checked
again. Capture at PC129 is retained at PC133 before `checkStillBound` at PC135.
Only four fixed event codes are logged, with owned Throwable containment. There
are no background jobs, polling, original constructors, credential queries,
unhook or owner release. Hook and candidate remain process-lifetime objects.

The corrected Capture source `26fcbb30…` and exact SDK classes `2b3f547c…` /
`d1849091…` are the separately reviewed component. Its 60 member records,
class/member metadata, instructions, tries and debug information are unchanged
against component DEX `99f24fe8…`. Earlier wrong-SMI source versions are excluded.
The probe does not call the component's package-private future-control getters.

PermitFile `78f6b0eb…` admits only the fixed root:1000 directory0750 and regular
single-link request0440, exact marker/size/EOF, held/named identity checks and
successful owned-FD closes. No arbitrary path or code is accepted. SDK37 lacks
public `O_DIRECTORY`; its removal preserves immediate held-fstat directory/type
and identity checks before request resolution. Trusted root-controlled parents
remain an explicit non-atomic pathname assumption. Finite read-call count is not
a proved wall-clock or filesystem-drain bound. Deleting the permit refuses later
capture; it does not remove an already installed hook or retained candidate.

## Actual artifact and correction history

The binary manifest has only manifest/uses-sdk/application nodes: unique package
`com.appleexploit.oneos.security.retainedcapture`, min/target37, no permission,
activity, service, receiver or provider. The descriptor is API102, static scope
`android`, hot reload disabled. No SDK/API/model/OEM definitions, native libraries,
assets or additional DEX are packaged. D8's actual API37/max36 warning remains.

The six authored payloads, their compressed streams and central metadata match
the immutable unsigned APK. Manual pre-signing padding has an exact byte inverse
to unsigned `30fdc5ae…`: only the five-byte LOCAL extra and necessary offset words
change. Signing adds exactly the pinned SF/RSA/MF files and a resource LOCAL
alignment TLV. Signed `resources.arsc` stays STORED, with exact 13-byte extra
`ffff01000035d9040004000000` and data offset680 (pre-sign672). All six manifest
digests and signature-file section/full-manifest digests match. Signing-block
bounds are parsed independently; cryptographic acceptance comes from the saved
actual apksigner verification, **v3 true, v1 false**, certificate
`ad40f7c185abb46a5ba4798625e3245333987594379e5014aa0c977e69febfc9`.
Actual signature, read-only zipalign and badging commands exited0.

Failed SDK-symbol, native archive-output and strict wrapper attempts remain
separate immutable evidence. Native output crashes have no assigned cause. The
last wrapper stopped at a stale `sdkVersion` key; SDK37 emits `minSdkVersion`.
Independent saved-byte review then caught the unexecuted finalizer's six-entry
and pre-sign-offset assumptions. Root-approved `52567706…` admits only the exact
observed signer additions, preserves all original payload checks and performs
validation only: no subprocess, compilation, linking, signing or APK write.

## Remaining runtime conditions

Vector also has a late SystemServer callback path. HOOK_INSTALLED can occur after
phase1000 and produce no capture that boot; no replay, backfill or restart was
added. Static API/dispatcher evidence does not establish actual early callback,
HookBridge operation or new-module delivery. Permit access/close behavior,
loader/TCCL equality and the component's genuine retained bindings still require
the separately approved real-process observation. CAPTURE_BOUND would describe
only immediate capture/check success, not source identity, user generation,
native ownership, authority readiness, authentication, CE/key access, callback
drain or OneOS switch survival. Actual recovery/disable and process termination
are separate proposal/approval work; no hot teardown is proved here.
