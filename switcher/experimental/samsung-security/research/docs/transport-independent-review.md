# Transport independent review

Status: final bounded independent PC source/component review accepted.
No runtime authority or phone behavior is accepted.
The full reciprocal PIN/fingerprint, real policy, app-key/CE and recovery goal
remains required. No transport, runtime or phone candidate is selected here.

The three initial shared interfaces provide no default authority, permission
result or source identity. DispatchAuthority.open supplies a synchronous call;
DispatchCall separates admission, original invocation and lease close.
PreparedDispatch is only a cached dispatch entry. Its implementation and owner
must establish the real source object, code, caller and current user/state.

## Concrete acceptance gates

1. The Android entry captures actual Binder UID/PID and flags on the incoming
   thread. It preserves the same data/reply packets without copying, retaining,
   queuing, clearing identity or dispatching through another thread. Cached
   original dispatch preserves the original thrown cause and Binder semantics.
2. Each admitted route translates the exact guest transaction to its source
   transaction using the reviewed wire contract. Matching descriptors alone do
   not authorize dispatch. Unknown routes must fail before acquiring an owner;
   an existing code, object or token is not a permission grant.
3. The call binds guest/source codes, flags, caller, thread and owner generation.
   Invocation cannot substitute another route or borrow an unrelated call.
   Admission remains current immediately before original invocation. Reentrancy,
   retirement, repeated invocation and close failure need explicit accounting.
4. Original failures remain failures, including close-after-invoke handling.
   Lease release does not drain backend callbacks, native sessions or posted
   work. A thrown credential setter can follow partial/complete commit; neither
   close nor a transport exception establishes rollback or permits blind retry.
5. Genuine backend/code, caller policy, user/serial, credential state, storage,
   native endpoints and actual policy readiness remain separately unassembled.
   No allow-all/default permission implementation, fabricated success, NONE or
   zero lockout can fill that gap.
6. Any authored SID JNI binding proves only the documented metadata-format and
   class-registration seam. Process-lifetime anchors, exact target/signature,
   synthetic input policy, ABI/build limits and cleanup must be explicit. No
   OEM target or real handle is to be invoked in these PC checks.
7. Optional Settings retrieval exclusion must close its exact capability/entry
   paths while preserving genuine save/verify, error and credential cleanup.
   An unselected source leaf need not complete the Samsung runtime first.

The paired inventory names the exact files and checks performed. PC tests,
compilation, ARM output and authored fixtures cannot establish Android Binder
identity, permissions, backend construction, hardware authentication or any of
the eighteen device acceptance cases. No OEM, phone, installation or Git action
is part of this review.

## Reviewed source findings

The route table's 33 guest/source pairs were independently compared with the
existing construction-protocol inventory: exact equality, with no missing or
extra pair. This reuses that inventory's wire proofs rather than repeating the
original DEX audit. The frozen core rejects unknown routes before owner creation,
rejects selected oneway/null packets and directly passes the original packets.
Its initial try-with-resources structure had a same-Throwable self-suppression
edge. Root identified that case; the final source now guards close explicitly,
does not suppress an exception onto itself and protects the primary even if
suppression attachment fails. With no primary failure, close failure propagates.
The focused same-instance cases were read, not executed by this reviewer. This
source defect is resolved. No actual Binder execution was performed.

The frozen managed owner binds the call to codes, flags, captured caller, thread
and generation; first invocation attempt is consumed. External admission runs
outside the lock, followed by local retirement/state checks. Close refuses an
active same-call stack and does not release the final backend/anchor. Retirement
can race after invocationActive is set but before the original method body is
entered: an already-admitted call may execute/unwind after retire returns. This
is existing-call accounting, not backend cancellation or drain.

Admission's signature contains no requested user/key/purpose from the packet.
It therefore cannot by itself establish authorization of those payload fields.
The genuine original typed enforcement and correctly bound user/state graph
remain required. A final live check may also fail after a real mutation commits;
that needs uncertain-commit reconciliation rather than transport-level retry.

The frozen cached invoker checks the supplied exact runtime class and canonical
Binder/Parcel method shapes, selecting the most-specific admitted override and
unwrapping its actual InvocationTargetException cause. These are shape and
dispatch-preservation checks; the supplying owner must still authenticate code,
object, loader, initialized policy and native/state ownership.

## Architecture consequence

The implemented Android path needs a genuine original backend object in the
same process, invoked directly in the incoming Binder thread. It makes the
controlled-loader/local-owner construction cut concrete at the transport seam;
it does not prove that Samsung LSS and its user/state/storage/native owners can
be coherently constructed there. Replacing PreparedDispatch with a remote
authority call would change the reviewed no-hop/caller-identity contract and
requires separate evidence. This component cannot make a stopped host Java
authority survive or transparently supply its original kernel caller remotely.

## Frozen transport and Settings findings

The final core, managed owner and Android frontend reports accurately separate
their responsibilities. The production core owns route/oneway filtering;
ManagedDispatchAuthority alone is a trusted Java lease scaffold, not a safe IPC
endpoint. Duplicating route filtering there is not required by this reviewed
entry path. Neither generation tokens nor supplied Class objects authenticate
the Samsung service or authorize the packet's requested user/purpose.

The coherent build reports 1,161 core assertions across 52 synthetic scenarios,
87 managed-owner assertions, actual SDK37 wrapper compilation and eleven
authored production DEX definitions. This reviewer read source and evidence;
the build/tests were not rerun. The D8 API37/max36 diagnostic and lack of release-
API, ART, native-caller, reflection-on-device and real-backend acceptance remain
explicit. No SDK/test classes are claimed as production implementations.

The optional retrieval leaf correctly returns false only for the unsupported
OPPO capability. It preserves actual current-credential operations and does not
pretend every old-password UI entry is unreachable. Independent old-mode Intents,
restored state/results, the visible footer, queued work and credential caches
remain separate admission/cleanup work. Genuine Samsung previous-credential
recovery remains a mapped policy; previous PINs must fail ordinary unlock.

Root's Settings composition retains both exact immutable child receipts, edits
distinct methods and preserves all thirteen selection conditions, including the
parent cold-process restriction. This reviewer streamed component/output hashes
and checked that exact condition union without rebuilding byte/Java proofs.
The old RPMB receipt's field-name normalization is allowed only for its exact
name/hash, rejects a conflicting alias and does not weaken new-component rules.
The 128MiB entry bound is explicit only for the exact Settings profile containing
the 123,768,068-byte resource entry; other profiles retain 64MiB, with the same
512MiB total and 20,000-entry limits. The ten composer test sources were read;
they are not ten Android or malformed-DEX tests.

## SID binding review boundary

The authored Java/C binding is a metadata seam, not credential verification. Its
target declaration, exact method/signature, once-attempt state and ready gate
are source-reviewable; its global class anchors do not identify genuine Samsung
code or admit a user/handle. Only authored synthetic targets may run in PC tests.

An early failure can occur before any native GlobalRef exists. Java static self-
references are not independent classloader roots. The reviewer raised this;
the Java contract now explicitly requires an external process-lifetime helper,
target and loader owner before invocation. Native once-state is per admitted
library image and Java state per helper Class, not a universal process singleton.
Later successful GlobalRefs root the reached classes; a failed/uncertain attempt
is not permission to unregister, release or retry through another loader/image.
The successful root run reports 20,066 checks over five fresh-process authored
JNI stages. The host test DLL includes explicit fault hooks and synthetic target
classes; the separate production ARM ELF was built, not executed. Injected
anchor/pre-registration/post-registration failures are not tests of real VM
allocation exhaustion or a real RegisterNatives error return. Source paths for
those actual failures were inspected without exercising them.

Authored source/output pins and the ARM header were checked. The transport DEX
separately passed this reviewer's SHA1, Adler32, file-size and raw class-definition
count checks; eleven definitions do not include SidNativeBinding. Android helper
packaging, original private-SPM registration, loader access and every reached
caller's stable genuine-handle/NONE/zero policy remain unimplemented integration
work. The metadata input policy is explicit authored behavior, not equivalence
to original invalid-input JNI behavior or hardware authorization.

## Final disposition and exact check scope

**Accept the first transport batch as an unselected PC component checkpoint.**
No remaining material source-semantic or scope correction was found in the
frozen core, managed call owner, Android wrappers, SID prepared binding, Settings
capability leaf/composition or root TRANSPORT synthesis. This is not acceptance
of full Stage1 assembly, Android helper packaging, a genuine Samsung authority,
a phone candidate, PR readiness, beta readiness or the full goal. All eighteen
device acceptance cases remain open.

Resolved findings were the same-Throwable close edge, the native early-anchor
qualification, the co-resident transport limit and historical native-run wording.
The exact Settings legacy-schema and larger-entry exceptions retain their
bounded source/profile restrictions. Mandatory original caller checks, current
policy/user/state, secret cleanup, callbacks, cache invalidation and recovery
remain required; optional removal does not waive any core function.

This reviewer manually read the named source/report portions, compared all
33 literal routes with the pinned existing protocol inventory, checked frozen
build/native source pins, streamed component/output identities and the full
Settings condition union, and checked the authored DEX integrity/header/count
and ARM ELF header. Original byte/inverse/resource/body proofs are inherited
from explicitly identified peer evidence, not reproduced wholesale here.
Root/build-worker executions are distinct from these independent read-only
checks. No compiler, test suite, JNI library, OEM code, ADB/phone operation,
installation, setting, reboot or Git command was executed by this reviewer.

This frozen review excludes the subsequent UserInfo conversion, StrongAuth
callback, storage retarget, fingerprint, realm and retrieval-entry-admission
follow-ons. Their presence elsewhere on disk does not enlarge this checkpoint.
