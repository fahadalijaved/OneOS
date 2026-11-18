# Authority binding and code-generation review

Status: completed bounded source/code-generation review; authority remains unselected. Prior bootstrap/bindings/display reviews
remain frozen. This pass covers the new display-info/Context cut, guest-local
method/event mapping, no-edit DEX041 emission, UMS queries, policy data/updates,
real ColorOS biometric UI and original-authority quiescence.

## Independently checked result: no-edit code generation

The source-preserving writer passes for exactly original UserManagerService and
LockSettingsService top-level definitions. Independent reads of the intact
28,157,552-byte input verified both DEX041 header/container identities, class
counts and the two descriptors at logical header10,057,984. No source slicing,
rebasing or magic change is used to admit the original input.

The three normalized JSONL outputs are physically identical. All612 record hashes
match their normalized content and receipt member map. The two266,472-byte DEX039
outputs are byte-identical with valid SHA1, Adler32, file size and class count2;
their SHA256 is80c379a3a0a9f6b94bfb45d78904fda8a1a827b46a9e7bc0f6495d8e13b2cef0.
This reviewer ran no compiler or writer.

Source review includes field/method partitions and access, typed encoded initial
values, annotation/parameter/debug information, exact references/registers/
branches/payloads and try handlers. Empty source hidden-API restrictions are
corroborated by absence of map type0xf000 in both original maps; that does not
exercise preservation of nonempty restrictions. Equality remains bounded by the
represented metadata and shared decoding/normalization. It is not an inverse to
the original physical041 bytes, a complete cohort or ART verification.

One concrete correction is resolved: newly generated DEX binaries now go to
ignored out/, while normalized OEM bodies remain in ignored firmware/. The
bounded rerun retained identical output bytes and preserved historical evidence.

## Acceptance boundary

The other six cards identify precise source boundaries; none implements its
proposed runtime owner or adapter. Matching local method signatures do not settle changed return/token
semantics or event completion. A registry data view does not supply active
user/CE lifecycle; persisted policy fields do not replace their update/aggregation
owners. A real ColorOS UI needs authentic session/user/terminal callbacks rather
than a synthetic success sink. Name removal, process signals and zero authored
call counts do not quiesce original cached Binder callers or already issued
native enrollment/protector/storage work.

## New concrete owner findings

The Context continuation pins a real incompatibility: Samsung getDisplayInfo7
and guest1 serialize59 versus58 top-level fields. The source-only refresh/axis
slots are not safe zero defaults. A smaller raw-metrics projection is only a
proposal: five fields are the direct getAppMetrics read set, while the original
preceding CompatSandbox path can alter dimensions. Its real transform/inputs or
a proved no-effect guard must also be accounted for. Configuration, compatibility
and font scaling must apply once; already-scaled guest metrics are insufficient.
The source owner clarified that this transform reads no additional raw DisplayInfo
fields: it uses the actual ActivityThread sandbox configuration/flag and writes
dimensions from its bounds. That state can differ from the ResourcesManager
configuration used by the later calculation. Five raw values can therefore be
a sufficient data shape without being final Samsung metrics. Snapshot coherence
and those two original consumer states remain unproved; no extractor code is
approved by that shape alone.

The proposed callsite is ContextImpl in original boot/framework code. A helper
signature on the app classpath does not replace that callsite, establish boot
classloader visibility or select matching boot-image/compiled code. Actual
process-scoped framework rewrite/admission remains open, independently of the
services.jar two-class generator and the unmodified host-only Context probe.

The UMS card identifies four real construction seams, rather than a ready query
wrapper: physical registry root, handler ownership, publication through the end
of construction/queued work, and original resource/Persona policy. Global user-
type resource IDs collide; Persona is unconditionally dereferenced by a required
profile query and its launcher-UID filter has an actual PM-backed producer.
An empty table or a post-constructor check does not close that owner.

The policy card preserves actual updates, not just data getters. Samsung failure
reporting synchronizes an authoritative LSS failure count; the guest plain report
does not. Retry/duplicate reports can repeat admin/wipe effects. Password history
also depends on the same source salt/hash-factor/history, and original metrics
reporting posts a policy tail. SecureLockDevice memory/status and queued file
completion are distinct. No policy provider is implemented by that source card.

Old-authority quiescence has concrete counterexamples: timed AM and biometric
waits ignore their Boolean results, lists can clear after issuing asynchronous
native work, and alarm/integrity/metrics/DPM work can outlive the original frame.
The actual cut is before the first stock zygote stop, not just before a new
process launches. New counters cannot retroactively own preexisting work.

## Local control and genuine UI events

The full 18-operation local proposal closes the former signature-only gap at
source level. It preserves real argument reorder, nullable authoritative metrics,
actual token activation and original exceptions. The guest clear wrapper always
returns true after its real manager clears; Samsung's actual wrapper clears and
posts the same StrongAuth reason removal. Translating its normal completion to
true is therefore supported as wrapper completion, without claiming applied
policy, native completion or readiness. I checked those saved raw bodies.

The proposal still needs real source-owned lockUser and platform RoR control,
including the concrete RecoverySystem event owner. All 18 local operations are
required in this proposal; the old optional OPPO RoR removal does not remove
platform RoR. No private transport or local proxy is implemented. Escrow
activation can occur before add returns; registration ownership must precede
entry, and host(user,handle) must become guest(handle,user). Callback loss after
activation leaves uncertainty. A token setter may change Settings before false,
or commit before its post-change work throws. Automatic retry is unsupported.
Verify-tail state listeners can throw after actual authentication effects; their
user events are neither HAT proof nor applied guest policy. The ten-int metrics
snapshot is scoped to selected read-only consumers, preserving secure-user null.

The biometric UI card provides a real candidate event surface, not a synthetic
success channel. Guest prompt-shown at PC179 precedes actual show at316; only the
real current dialog's animated-in callback carries the source-representable
startFingerprint boolean. Samsung's hardcoded vendor-ready true loses the guest
false-delay behavior. Critically, stale ingress must be rejected BEFORE invoking
original BiometricService$2.onDialogAnimatedIn: it removes the watchdog at14,
before its posted current-session check. The report now explicitly preserves
this ordering. A stale callback can otherwise cancel a replacement timeout.

A genuine canonical guest Binder carrier is still needed because the actual
source callback's asBinder returns null. The outer source AuthSession still
opens the companion UI even when a per-sensor BiometricPrompt branch skips its
own helper. Show-only or blanket-helper removal does not close that graph.
Effective prompt schemas, outbound notifications, current main-thread dialog
identity, terminal credential/factor policy, token escrow and native overlay/
HBM/pointer/cancellation ownership remain unimplemented. Native HAT submission,
app callback, displayed UI and actual protected-key operation acceptance remain
separate outcomes.

## Disposition and actual checks

Accept the seven cards as bounded source evidence and the two-definition writer
as a verified generation prerequisite. No remaining report supplies an actual
Context binding, initialized sole UMS/policy/storage/native owner, local control
channel, biometric UI adapter or old-authority drain. The earliest decisive
construction cut is still real Context/resources/boot-callsite admission before
any security constructor can mutate state. Passing it would enable a next
bounded construction proof; it would not certify those downstream owners.
There is no new evidence here selecting guest import or a separate process as
the completed architecture, or proving either requires all system_server.

This reviewer read the seven cards and their inventories/tools, inspected the
writer and bounded selected saved local/UI bodies, and independently checked
physical DEX/container/output and normalized-record identities. I did not rerun
the seven producer audits, compiler, writer or full corpus. The inventory pins
the actual inputs and the two ignored independent check receipts. The generated
DEX placement correction and pre-watchdog UI clarification are resolved. No
material source contradiction remains in this reviewed snapshot; actual owner
construction and runtime acceptance remain open.

New raw display producer, prompt wire, boot rewrite, permission and statusbar
follow-ups are separate WIP, excluded from this frozen review. Earlier bootstrap,
bindings and display reviews remain unchanged. No OEM/Android/JNI execution,
phone/ADB, install, configuration or Git action is part of this review. All 18
device acceptance cases and the full reciprocal PIN/fingerprint goal remain open.
