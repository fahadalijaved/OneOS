# Stage 1 independent construction and authority cut

Status: initial bounded independent review, November 5, 2026. No architecture
selected for execution; no OEM/native code, service, phone operation or Git
operation was executed. The uploaded/current GOAL governs this work. The parent
ColorGlass project remains paused. Existing frozen reviews are unchanged.

## Earliest decision that can invalidate the current candidate

**Inference from observed source:** the first useful decision is a
**pre-construction authority/environment cut**, not a successful constructor or
Binder publication. Before any imported owner is constructed, establish the
actual Context, user graph, class realm, resource policy, filesystem/metadata
view, native-service endpoints and exclusive mutation owner that it will use.
If any reached constructor/initializer binds guest-empty or guest-owned security
state to the shared Samsung hardware, the proposed single-authority candidate is
invalid at that boundary even if classes link and all later caller translation
is correct. This is a falsifiable candidate condition, not proof transplantation
is impossible.

The first-pass source already proves that LockSettings construction starts
threads, registers receivers, creates storage helpers and publishes local state;
verification/startup can migrate or enroll. New streams are tracing still
earlier nested constructors and exact guest startup sites. Therefore checking
the final LSS fields, service name or return value after construction cannot
establish that initialization was safe.

The cut must be concrete: for each reached acquisition, state the exact method,
source PC and guard; actual object/path/endpoint it obtains; source of the live
identity; earliest side effect; owner retained before that effect; abort and
uncertain-progress recovery. A declared class, matching integer user, path
string or mock provider does not fill an entry. No live-state secrets need be
copied into the PC report.

## Independently reread OneOS process and namespace constraints

These are **observed pinned OneOS 0.4.55 source facts**, not facts about the
currently installed guest. Paths are relative to the parent ignored snapshot
`firmware/reference/OneOS/2a5f41043b4a69399cae058bad213cdef7408e88/`.

| Source boundary | Actual source behavior | Consequence/inference |
| --- | --- | --- |
| `switcher/assets/oneos_switch.sh:971,999,1011` | Stops host zygote, kills system_server and maintains host suppression. | Existing host Java LSS/storage/fingerprint objects do not survive by default. A separately constructed service realm and retained existing host process are different proposals. Objects cannot be treated as extracted into another process. |
| `oneos_switch.sh:1406-1418` | Launches guest through `unshare -m`, records its mount namespace and guest root device. | This supplies a mount view, not evidence of a private Binder service namespace or independent hardware security identities. |
| `switcher/assets/guest_prepare.sh:301-309` | Ensures Binder device paths and recursively binds `/dev` into rootfs. | Source supplies no separate private Binder context here; names and native endpoint ownership must be traced rather than inferred from mount isolation. |
| `switcher/assets/guest_start.sh:645-758` | Starts guest vold, selects guarded `gvld` when staged marker is present, checks host-vold and guest-vold PID/name ownership, and refuses known mismatch before framework startup. | Selecting the storage endpoint is already part of OneOS startup. A transplanted Samsung storage dependency must not collapse this separation or make ordinary guest storage startup reach host key/reset operations. The fallback path and installed patched bytes remain distinct unknowns. |
| `switcher/assets/return_to_oneui.sh:78` | Retained-name set includes host vold/IVold, Keystore2, installd and GateKeeper. | Native daemon retention does not retain the Java authority or its process-local LocalServices. |
| `return_to_oneui.sh:214-223,254-283` | Stops suppression, uses broad system_server process matching, then kills guest mount-namespace/root processes. | Renaming a retained service inside the guest namespace/root does not make it survive return. Outside placement still needs explicit cleanup admission and correct data/native owner visibility. |
| `return_to_oneui.sh:341-360,602-707` | Restores bridged host data trees, checks remaining mounts/retained services and requires host framework not to restart prematurely. | Any new authority/state mount or surviving process must be represented in the actual return protocol, rather than surviving through an untracked exception. |

These lines were independently read. Source comments about historical successful
sessions are not new runtime evidence. No source fallback is selected as the
current installed path by this review.
All four switch/prepare/start/return source files were freshly SHA256-matched to
the parent source-pins ledger. Their full hashes are recorded in this review's
inventory; this does not identify current phone files.

## Alternatives at this cut

| Candidate | What it may avoid | Earliest unresolved cut and evidence needed |
| --- | --- | --- |
| Coherent Samsung family imported into guest, typed guest entry | Could retain original ColorOS presentation and guest public API identity while preserving original Samsung implementation behavior. | Before constructor invocation, resolve original private type/resource/state owners against the guest classpath/Context and real local registry. In particular, identify the object behind Samsung's concrete storage dependency and the actual host/guest vold endpoint. A full Samsung storage lifecycle imported merely to satisfy a cast may introduce a competing owner; a guest storage object that links is not automatically the host authority. |
| Separately constructed Samsung authority realm retained across switches | Can keep Samsung private classes, Context and local registry together instead of resolving every private dependency against guest namesakes. | Must still construct that realm over the right original state/native owners without competing writers. Pin process/root/mount placement, public endpoint publication, authenticated delegation and who starts/stops it. Current cleanup can kill it; surviving native daemons alone do not supply it. |
| Existing Samsung system_server retained | Could preserve actual initialized host Java dependency objects. | Requires concrete alteration of OneOS stop/suppression/return and competing framework service ownership. There is no source proof of a general stop-and-extract mechanism. Retaining it is not ruled out, but is not a default behavior or a free preservation shortcut. |

The alternatives share the mutation/state/native authority obligation. Selecting
a process boundary can move Java identity/resource problems; it cannot eliminate
the credential transaction or endpoint ownership problem. Do not rank designs
by jar count, apparent broker size or compiling classes alone.

## Corroborated peer findings and their exact implications

**Observed source, independently reread with raw hash matches:** the cold
RecoverableKeyStoreManager constructor calls CleanupManager.verifyKnownUsers at
decimal PC 26. Its exception handler catches Exception from that call and
continues. Cleanup compares the actual UserManager serial with stored serials:
removed users or mismatches can lead to snapshot File.delete, application-key
deletion and SQL deletes; a missing stored serial can be written. See
construction-credentials report/inventory and receipts
`20261105T143453265706Z-aa7e67df01d44d989817257c172f5e42` and
`20261105T143820229238Z-0b81fbba47db4a58812b696eea9e3615`.

**Inference:** this is an earlier checked destructive reconciliation than LSS
publication, not proof that every previous acquisition is inert. It is conditional
on cold singleton construction and real recorded/live users. Warm singleton
reuse needs original Context/database/key-provider provenance; clearing it is not
a workaround. Guest user serials over host recoverable-key data can invalidate
the candidate before the final LSS fields are available. A normal constructor
return cannot certify completed reconciliation after contained partial failure.
This is not evidence that the stock OEM runtime has such a mismatch.

**Observed source, independently reread with raw hash match:** selected Samsung
StorageManagerService.connectVold$1 resolves `vold`, links death, calls actual
IVold.setListener at decimal PC 39, then reads getUnlockedUsers at 91. Its reset
path has boot/daemon gates at PCs 35/39 before StorageSessionController.onReset
125 and IVold.reset 163. The state worker's selected receipt is
`20261105T144048134385Z-9c87c1338ba24435b4cb45eab5c23f15`.

**Inference:** importing full StorageManagerService to satisfy a concrete inner
class is active native-listener acquisition, not an inert adapter. Reset is not
unconditional merely because the class exists. An intentionally exclusive new
Samsung storage owner remains a candidate if listener/publication/native state
handoff is actually closed; attaching without that ownership is not closure.

**Observed peer source comparison, report and selected inventory reviewed:**
construction-storage-linkage establishes that Samsung's concrete Class registry
key differs from the guest's abstract key; unchanged LSS also reads original
outer mVold/isHSUMMode and calls a three-argument unlock unlike the guest's
two-argument method. The selected IVold transactions and HAT/HSUM layouts differ.
The eight selected direct concrete-owner references and outer-field accesses
can motivate exact source-derived retargets. They do not prove full Samsung SMS
is mandatory or that a same-name guest object is sufficient. Its `mount` cache
query and actual unlock/protection backend must refer to the same authority;
guest cached-unlocked status must not skip required host work.

**Observed source, independently reread with raw hash matches:** ColorOS
LockPatternUtils.setLockCredential calls the real setter at decimal PC 30;
only its true result reaches guest-only setLockscreenPasswordType at PC 48.
That extension writes `lockscreen.password.type` presentation metadata via
setString; it is not `lockscreen.password_type` credential quality or hardware
verification. The selected extension clears identity and serializes package,
type, user and time. Receipts are
`out/construction-protocol/lockpattern-bodies.json` and
`out/construction-protocol/password-type-extension.json`.

**Inference:** a narrow owned guest-metadata translation may close that missing
Samsung API; inventing a Samsung method or treating the metadata as auth proof
does not. The real setter can commit before later metadata reporting throws a
RuntimeException. UI/transport must reconcile that outcome instead of blindly
retrying with the old PIN. Absence of this OEM API is not a whole-candidate
impossibility proof.

**Observed root captured-policy proof, inventory reviewed:** the selected
Samsung floating_feature.xml lacks COMMON_SUPPORT_UNPACK and its selected
Boolean parse is false. No corresponding exact donor path is present. This
does not establish a difference for that selected SECURITY_UNPACK feature or
prove a live policy value. It removes a speculative feature-mismatch blocker;
the original class-initialization Context/configuration owner remains open.

**Observed state report/inventory reviewed:** guest preparation can delete staged
Weaver/SP/database records and recursively alter staged ownership; it must finish
before original authority state is bound. The guest's conditional `/metadata`
tmpfs is a separate view from Samsung's literal password-slot map. Context's
system-package database special case and static Environment helpers resolve
through different inputs, so a Context wrapper alone does not close the view.
Original Samsung backup/restore roots, user serials and enrollment metadata must
be included narrowly; optional OPPO databases need not be imported. This remains
a proposed physical binding, not a selected mount or live identity.

**Inference from the reviewed write behavior:** single-file/inode retention is
not a demonstrated binding because actual AtomicFile replaces the base path by
rename; merging all `system/users/<u>` would also merge guest Settings. The exact
directory/path adapter must preserve create/rename/recovery semantics while
separating guest presentation data. No live slot or credential state was read.

## Latest scope: adapt ColorOS and remove unsupported optional OPPO work

The user's new instruction explicitly permits removing optional OPPO-only
integrations, UI and background work when no supported Samsung route exists.
This supersedes any interpretation that an enabled unsupported OPPO consumer
must always be transplanted. Full reciprocal Samsung-controlled PIN/fingerprint,
actual policy, app-key and storage functions remain required.

The source-supported removal frontier should precede acquisition/retention:
close unsupported feature entry points, callback registrations, task construction,
credential/HAT/SP retention, retries and late delivery. Do not leave an advertised
capability with fabricated success. If original state is already owned, its real
cleanup/drain still precedes release. Optional RoR/RPMB removal must not remove
Samsung StrongAuth, actual keyguard user-present ordering or core credential
setter/verification. Peer frontend proofs and exact guards are being reviewed;
no patch/removal has been implemented by this report.

**Observed source independently reread with raw hash matches:** ColorOS
LockPatternUtils type-cache apply catches RemoteException and returns boxed -1
at decimal PC 27; lockout-cache apply catches it and returns Duration.ZERO at
PC 27. Their exact raw proofs are retained through
`out/construction-protocol/type-cache.json` and `lockout-cache.json`.
Adapting guest admission
must preserve explicit unknown/locked state on unavailable, foreign or stale
authority rather than accepting those defaults. Existing defaults are not
proof of current installed behavior or a demonstrated runtime bypass.

New owner reports and inventories will be reviewed at these boundaries without
duplicating their audits. Mistaken blockers already rejected remain rejected:
null CHECK_CAST alone does not prove constructor failure; the biometric-handler
singleton initializes itself; partial early progress exists on both OEMs; the
original ColorOS extra-factor finish guard exists. None supplies a false closure.

## Evidence that settles Stage 1's architecture cut

Require one pinned construction schedule covering the actual selected guest
startup path and each reached nested constructor before its first effect. It
must contain canonical/private class decisions, concrete real object/state and
native-service bindings, source-defined mutation admission, lifecycle/death/drain
and return ownership, plus explicit unresolved entries. Demonstrate why each
selected active initialization can use its original policy without guest-empty
metadata or a second authority. Reject the proposed assembly if this cannot be
done; compare the alternative precisely at the unresolved cut.

A complete source construction/ownership plan can settle whether a candidate is
ready for a bounded offline implementation. It cannot establish live owner
identity, hardware/HAT acceptance, native cryptographic behavior, correct current
installed patches, crash resilience or reciprocal PIN/fingerprint acceptance.
Those retain the separate normal-device/upstream-fault/beta gates from GOAL.
Existing accepted platform limits do not excuse incorrect feature ownership.

## Final cross-stream disposition and the separate metadata leaf

The reviewed construction synthesis and completed peer reports preserve the
required reciprocal PIN/fingerprint, policy, app-key, CE and recovery scope.
No reviewed source result establishes a complete executable construction plan,
runtime-selected process placement, current installed guest or a device result.
The exact reviewed snapshot hashes and actual checks are in the paired inventory.

The completed startup report now pins the original guest's four producer sites,
fingerprint returned-object cast and phase/immediate-consumer order. This closes
the original-source callsite uncertainty only. In particular, boot-time
ILockSettings.systemReady and LockSettingsInternal.onThirdPartyAppsStarted are
additional real contracts beyond the bounded 33 frontend protocol operations.
Binder publication or frontend mapping alone cannot close the lifecycle/local
owner. The report explicitly leaves installed patched sites, unfollowed compiler
delegates, independent SystemServer extension hooks and real readiness open.

The final frontend review also preserves corrections for static credential-cache
retention, all twelve selected input-string setters and both getter/task paths,
capability-bearing diagnostics, and mixed background work carrying credential/
Intent owners. It distinguishes preventing cold registration from disconnecting
and draining existing callbacks. These are source removal obligations, not proof
that a flag, private no-op or completed source scan releases those owners.

The smaller Samsung-owner alternative is legitimate, but cannot simply omit an
eager constructor and declare its policy/reconciliation obligations unnecessary.
Each removed original owner needs reached-caller and required-policy treatment.
Conversely, no whole Samsung storage service, server, OPPO RPMB trustlet or
reboot-escrow acquisition is proved mandatory just by a class name or later
optional branch. Conditional display/feature/native requirements retain their
actual guards. The root's selected UNPACK absence/false proof removes that
specific speculative policy-difference claim only.

The frontend removal register has useful source boundaries: remove optional SP
callback registration before material is delivered, optional RPMB task allocation
and entered-text retention before posting, and optional Settings challenge/HAT
side work before acquisition. Replace incidental PIN-length/cache invalidation
with genuine authority notifications. Preserve original credential operations,
strong-auth/additional-factor/confirmation/finish guards, required enrollment
challenge and user-present ordering. Complete late callback, retry and all exposed
alternate-caller closure remains a prerequisite, not a built adaptation.

The separate ColorOS audit-metadata leaf is acceptable **only as an unselected
PC code leaf**. Its selected method first calls the actual setter; only a true
result reaches optional PCs 38-51. Replacing that region with NOPs preserves the
actual setter, false return, true return and original setter-exception path;
it removes optional package/type/user/time audit reporting rather than creating
authentication success. It does not implement the Samsung setter, uncertain-
commit resolution, NONE/ZERO readiness or any other required service.

Its receipt requires excluding the optional dotted-key producer/logging consumer
from the selected family, or removing the exact read/log slice while preserving
independent timeout work. That condition is mandatory, not a completed consumer
removal or permission to delete the entire hook. The leaf remains `selected=false`
with no Android/ART/JAR-signing, installed-image, hardware or phone acceptance.

This reviewer performed a small independent byte check before root assigned byte
review to the build worker: source/output archive hashes, only classes6 payload
changed, exact 28 zeroed bytes at PCs 38-51, unchanged bytes outside that slice
and DEX integrity headers, original-equivalent inverse and valid input/output DEX
integrity fields. No producer/build or OEM execution was rerun. Those checks do
not establish ART acceptance, full parser coverage or source-semantic closure.
The final producer documentation additionally qualifies its negative probes as
decoded-JSON-record admission tests. Actual-byte altered-branch, try/handler and
method-code-alias negative fixtures remain unexecuted. Positive real-byte inverse
and integrity evidence does not substitute for those missing negative fixtures
or runtime failure tests. This reviewer did not run them.

The earliest assembly gate remains:

1. Finish destructive guest staging and its final metadata/root/mount setup.
2. Bind the actual current physical user/serial/core state and native owners,
   including path-replacement semantics and original backup/recovery routes.
3. Establish admitted class/resource/Context and exclusive mutation ownership
   before first class initialization, nested cleanup or biometric acquisition.
4. Construct the selected real owners with their effects retained; do not treat
   contained errors, posted work or Binder publication as readiness/drain.
5. Apply same-authority original policy/user state before admitting guest callers;
   then retain exact operation, cancellation, reconciliation and return ownership.

This is an inferred ordering requirement from selected source, not an implemented
lease or scheduler. Unresolved physical bindings, private/canonical rewrites,
native ABI/JNI registration, secret lifetimes, caller delegation, callback and
return cleanup still prevent full Stage 1 closure. Optional code removal and a
byte-preserved leaf do not weaken that conclusion. Normal-phone and controlled-
upstream fault evidence remain separate later GOAL gates.

**Final disposition:** accept CONSTRUCTION and the named peer artifacts as a
bounded source/adaptation checkpoint, and the metadata leaf as unselected PC-only
work. No material remaining scope contradiction or false source closure was found
after the documented frontend/protocol/negative-scope corrections. This accepts
neither full Stage 1 closure nor any runtime/code selection. The paired inventory
lists the exact reviewed document/source pins and distinguishes this reviewer's
actual hash/pointer/byte checks from stream assertions merely read in reports.
No additional audit streams, OEM execution, phone work or Git action occurred.
