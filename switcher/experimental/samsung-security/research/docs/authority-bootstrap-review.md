# Finite authority bootstrap independent review

Status: final bounded source review; the finite bootstrap gate is not closed.
This review tests a concrete
bootstrap sequence and its earliest effects. It does not select an architecture,
run constructors or grant phone/test permission. Prior reviews remain frozen.

## Existing source falsifiers

| Proposed sequence | Concrete failure of that sequence | What would settle this cut |
| --- | --- | --- |
| Construct cold LSS, then provide user/state admission | Its cold RecoverableKeyStoreManager runs CleanupManager.verifyKnownUsers synchronously before later LSS setup. Genuine serial mismatch/missing-user paths delete key/database state; exceptions can be logged while construction continues. | Select the actual user/serial, default KeyStore backend and authoritative data owners before the first manager construction; show the real factory/source path and failure boundary. A later trusted-admission callback is insufficient. |
| Use the fingerprint provider/HAL getter as a harmless readiness probe | First connection/reconnection schedules internal cleanup and loads authenticator IDs for alive users. Existing metadata constructors also have conditional migration effects. | Admit exact users, enrollment/state paths, sole scheduler/session/native ownership before the first effect. Do not execute the probe to discover whether it is safe. |
| Obtain the concrete storage owner by starting another SMS | Original connection installs a vold listener; boot-connected work can reset/reannounce users and native state. This is active ownership, not a cast adapter. | Retain a coherent genuine owner or supply the actual narrow native/status adapter with its exact branch/error/commit contract. An interface proposal alone does not initialize it. |
| Give a process Samsung bootclasspath and call it an authority | Class availability establishes neither Context/Resources, user/policy/local services, actual native endpoints nor initialized state. Private LPU also has an instance-cached source-protocol service lookup. | Show exact runtime/Context factory, selected dependencies and first-use ordering. A separate process can host facade and backend together; co-residence need not mean guest system_server. |
| Treat StrongAuth registration plus a query as initial readiness | Existing registration replays only stored entries, has no complete marker or consumer-application acknowledgement, and the query reads a separate cache without a non-strong snapshot. | Supply an actual same-authority policy owner and source-owned initial/application ordering contract, preserving higher-factor state. Defaults, silence and successful registration do not settle it. |
| Preserve host Java security simply because native daemons survive | Current OneOS stops host system_server. Retained Gatekeeper/Keystore/vold do not retain its Java policy/cache objects. | Demonstrate the selected process survives the exact switch/return kill and namespace rules, with exclusive state/native writers and actual drain/recovery. Process naming or daemon availability alone is insufficient. |

These are disqualifiers for the stated sequences, not proofs that every
standalone-Samsung or guest-import design is impossible. Conditional source
branches must remain conditional. Captured base feature values and installed
effective policy/profile are different evidence. Matching protocols, class
names, bootclasspath or an opaque prepared-owner parameter cannot close an
unimplemented owner.

The seven frozen slices identify concrete source paths and specific missing
owners, as recorded below. None supplies a complete selected bootstrap. No broad repeat audit, OEM/JNI execution,
phone action, installation, setting, reboot or Git operation is part of this work.

## Seven-slice result

**Accept the bounded source findings; do not accept the current proposal as an
executable bootstrap.** This failure is present in source/code ownership before
asking for hardware acceptance. It is not merely the absence of a phone test.

| Slice | Actual finite result | First remaining source/owner cut |
| --- | --- | --- |
| A: runtime and Context | Real system Context path exists without SystemServer.main/run. Looper/native registration, module/renderer/font/Application effects and initial fresh ApplicationInfo are pinned. | Eager Samsung display71/86 does not match guest44/59; reached display-info semantics, full original environment and real metadata producer remain unbound. No cold-authority entry is emitted. |
| B: endpoints and guest lifecycle | Three selected guest literal lookups, original lifecycle suppression, source/guest protocol separation and exact early local consumers are identified. | Existing33routes lack systemReady26→70. No real guest-local18-method proxy/control channel exists; only8 exact declarations,3 changed and7 absent internal signatures. It must exist before TrustManager/APM startup, not after publication. |
| C: users | Context-only UMS's null-PMS edge is concrete; the selected handler factory can potentially be replaced by an owned real HandlerThread/Looper. | No selected sole original registry/type/default-policy loader, active user/serial/CE lifecycle or loaded Supervision/role provider. Registry recovery can delete/upgrade/write before publication. UserInfoWire and copied user0 do not supply these. |
| D: storage | Native46/59/60 dispatch and policy inputs are source-closed for the selected image; no whole SMS startup is necessary merely to marshal them. | No provider binds actual original endpoint/image/generation, physical user, HSUM/FBE/firstAPI, coherent status and operation disposition before LSS. No helper or marshaller implements that join. |
| E: biometrics | Finite FP→Biometric→Auth dependency order, early callbacks/provider/native/metadata effects and deferred Samsung UI binding are explicit. | Actual Context/managers/local/remote interfaces, alive users/state and sole scheduler/HAL ownership must precede provider/property access. Publication and a returned constructor do not settle registry/policy/UI readiness. |
| F: policy | Concrete DPM, DeviceStateCache, Supervision and SecureLockDevice producers and exact client calls are pinned. PM feature-cache absence has a valid original fallback. | No genuine loaded/current policy family or implemented typed projection is selected. AM unlockUser2 uses208 versus205; matching two DPM or notification sends does not validate the remaining manager/payload graph. |
| G: handoff | A candidate hook before switch1087, after Java kills and before data-view changes, is precisely located. Guarded host-vold and conditional return branches are explicit. | No launcher/view supervisor, old-writer/native quiescence, admitted new generation or return retirement exists. Current default/failsafe reboot behavior does not prove the required owned no-reboot return. |

The blocking contour is ordered. Establish the actual runtime/view and valid
Context-manager contracts; select real user/state/local/policy/native owners;
then permit constructors and their first effects. Guest producer suppression,
local publication and lifecycle/control admission must precede their original
eager consumers. Biometric property-cache misses, constructor migration and
cleanup belong inside that admission, not a later authenticate gate. Return
requires all source/guest/private/lifecycle ingress to stop and real work to
settle before stock reconstructs over current committed state. No opaque
trusted-owner argument or successful shell launch fills any of those steps.

## Important conditional distinctions

No full PMS/AM requirement follows solely from the UMS constructor's current
handler edge. No full Samsung display/system_server follows solely from A's
proxy mismatch. A narrow genuine source adaptation remains possible, but no
selected implementation closes those cuts here. Nullable captures, absent
optional modalities and conditional source feature branches are not treated as
unconditional fatal errors or permission to fabricate false/null policy.

F's empty DeviceStateCache behavior is especially conditional: absent provisioning
can defer cleanup; an unrelated provisioned/unmanaged cache can select a different
path. After remaining original guards, escrow destruction at238/241 is real.
Neither zero admin history, fresh disabled SecureLockDevice state nor guest
supervision defaults prove the original policy was loaded. Required factor and
finish behavior cannot be removed as optional OPPO work.

D's native59 reports tracked UserPolicies IDs under the native lock. It is not
authentication, protection commit, CE I/O, key acceptance or drain. The native
receiver accepts UID1000/root, which supplies no physical-user/source provenance.
Native unlock accepts empty/! token text; the original Java HAT/firstAPI branch
and SP verification must remain genuine. Force-null and a universal nonempty-HAT
requirement would both misstate that source. An unidentified Binder must not be
probed with59 to discover its version.

E's parse-recovery claim was challenged and resolved by existing state evidence:
readStateSyncLocked has File.delete58, AsyncTask.execute84 and invalid-state101;
its retained writer reaches AtomicFile start/finish/fail18/58/74. No new query was
needed. UDFPS phase550 settings/TSP work remains feature/state conditional.
The outer SysUi manager constructor has no direct bind, while openSession reaches
the real Samsung service bind later; neither fact proves all transitive effects
or an operational endpoint.

Both proposed Binder protocols must enter the shared retirement owner. A raw
Samsung backend publication would leave legitimate/stale source-protocol callers
outside a guard applied only to the guest alias. Actual private local calls and
lifecycle/background work require their own coherent ownership as well. Exact
name/descriptor/Class matches do not implement those channels.
The eighteen guest declarations define the local adapter surface, not eighteen
independently mandatory feature outcomes. Any supported/unavailable choice must
close its actual callers; required listeners, factor policy and credential/key
functions cannot become empty compatibility stubs.

## Comparison with guest import

The dedicated process remains a candidate, not an established best architecture.
It can remove private framework/value/native registration collisions, but it
introduces original-framework manager calls against global guest services; A's
display and F's AM mismatch are demonstrated examples. A guest import can reuse
initialized guest Context/common managers, but retains the proven Samsung member,
resource-policy, type/creator, native-registration and LocalServices adaptation
frontiers. Both need the same real state/policy and exclusive handoff. The
fallback does not pass merely because the dedicated candidate remains open.

There is no evidence here that recreating the entire Samsung system_server is
intrinsically necessary, nor that a tiny native verifier meets the goal. The
finite next falsifier is an actual selected implementation of the named Context,
local/lifecycle, user/policy and native-provider cuts; another list of class names
or admission interfaces would leave the same gate unclosed. Body/class counts,
a compiled frontend and architecture agreement cannot substitute for it.

## Separate host-only Context probe

The later SamsungContextProbe is an accepted **conditional PC compile artifact**
for a future separately approved ordinary-OneUI observation, with original host
services alive. It is not the cold/post-switch entry whose absence A recorded.
A's frozen no-probe statement is historical to that source scope; the separate
host-only artifact neither changes its source findings nor closes its gate.
The display follow-up is also outside this seven-slice review.

Its exact argument, UID1000, recorded Build-property subset and fresh Looper/
ActivityThread checks precede systemMain. Added narrow source receipts pin the
field/getter and Build initialization APIs; class initialization is not inert.
Properties and the output's declared hostOnly restriction do not authenticate
framework/mount/OS identity. A future launch requires actual external host-view
admission and separate permission after the user returns to the network.

The authored code performs no explicit LSS/SPM/UMS/FP/DPM/key/user/CE lookup,
settings/file-write or publication, and prints bounded public facts/booleans.
Original native/Typeface/module effects remain explicit and transitive purity is
unproved. System.exit is process termination, not A's normal-main-return path
or graceful callback drain. Reflection denial fails without hidden stubs or an
access exemption. SDK37/D8 output, including the API37/max36 warning, is not
Android execution, caller provenance, complete application metadata or authority
readiness. No phone transfer, launch, UID change, ADB polling or restart occurred
in this review, and none is authorized by accepting this artifact.

## Final boundary

The paired inventory records exact seven-slice and probe input pins, selected
checks and inherited proof limits. This reviewer ran no source assertion suite,
compiler, Android/OEM/JNI constructor, hardware/auth call, phone/ADB operation,
installation, configuration change or Git command. Prior frozen reviews remain
unchanged. All eighteen device cases, default-off authority selection, PR/beta
readiness and the full reciprocal PIN/fingerprint/key/CE/return goal remain open.
