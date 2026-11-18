# Method review: choose the next proof, not a presumed winner

**Recommendation:** challenge the present guest-process import with a
**dedicated Samsung-framework authority process first**, hosting both the
ColorOS-facing Binder frontend and the genuine Samsung Stub/backend. Keep
guest-process import as the comparison/fallback. The current route is **not
proved the best method**, and neither placement has an executable authority.
Pause further generic leaf expansion until the finite bootstrap gate below.

This is an investigation priority, not a selected runtime, completion estimate
or permission to change the phone. It preserves the whole [GOAL](../GOAL.md) and
[PLAN](../PLAN.md), including both directions of PIN creation/change/removal,
fingerprint authentication/enrollment/removal, current policy, fresh per-use
app-key authorization, intended CE access, switch/return and later approved cold
boot. A working keypad, old enrollment callback or already unlocked volume is
not a substitute. Optional OPPO removal cannot remove these obligations.

## Evidence that affects the choice

The review baseline is root's recorded `c3649e2` construction/component work,
supplemented by the pinned reports in
[method-review-current.json](../inventory/method-review-current.json). No Git
operation or broad source audit was performed for this review.

Root's fresh official-source snapshot identifies OneOS main/release
**v0.4.57**, commit `1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`, committed
November5 14:33UTC and released15:08:10UTC. See the
[upstream input ledger](../inventory/method-review-upstream.json) and
[official release](https://github.com/fahadalijaved/OneOS/releases/tag/v0.4.57).
This is a recorded source snapshot, not the installed version or a claim about
all future upstream changes.

Its four selected security-preservation patches, guest startup and README remain
byte-identical to the audited0.4.55 inputs. The current switch still stops host
zygotes, kills `system_server`, and maintains zygote suppression. It also kills
generic `app_process64`: a proposed separate authority cannot merely be launched
early and assumed to survive. The README still requires removing the screen
lock for ordinary switching. This is guidance/default behavior, **not proof that
launch with a lock is impossible**: the current ScreenLock gate can warn and
allow a known lock when Advanced `allowScreenLock=true`; unknown state still
blocks, and LaunchJob supplies the actual preference. That override does not
implement shared guest authentication. The current overlay producer still
applies all four preservation guards. Changed preparation/switch code is not an
upgrade that establishes shared credentials. No upgrade/install is recommended
here.

Existing source evidence separates real choices from apparent shortcuts:

- Cold LSS/recoverable-key construction can reconcile/delete state before
  publication; fingerprint acquisition can read/migrate metadata and schedule
  native cleanup before an explicit authentication request. Construction is not
  a passive probe of existing data.
- Guest-process import must close canonical/private classes, actual JNI target
  binding, resources, concrete LocalServices/storage edges and every first-use
  Samsung LockPatternUtils route. A matching class/service name supplies none
  of these owners.
- Direct transport requires frontend and source dispatcher to execute in the
  **same incoming Binder process/thread**. It does not require that process to
  be guest system_server. A dedicated process containing both is compatible in
  principle; a guest frontend forwarding to a separate privileged backend is a
  different caller-admission design.
- UserInfo conversion preserves data, not authoritative users. StrongAuth/factor
  callback registration does not establish an applied initial policy snapshot.
  Metadata helpers and successful offline builds cannot select the architecture.

## Alternatives against the full goal

| Method | Genuine advantage / minimum cut | Dominant risk and unresolved work | Decision |
| --- | --- | --- | --- |
| **Dedicated Samsung-framework process; direct ColorOS frontend and Samsung backend co-resident** | Keep the genuine service family and incoming kernel caller while avoiding mixing Samsung boot-framework/JNI/resource identities with the guest's. Retarget guest clients to an explicit frontend endpoint; bootstrap a coherent original framework/service realm. | This is **cold import**, not retained initialized state. Real Context/application Context, users/serials, DPM/supervision, storage, biometric/display dependencies, native endpoints and one writer remain to be selected. Process/mount lifetime, global lookups, original initialization effects and return ownership can still defeat it. | **First challenger to falsify.** Promising placement, not a smaller proven dependency graph. |
| **Current import inside guest process with typed ColorOS adapters** | Preserves existing OneOS guest topology and direct caller frame; adapts clients rather than rewriting their UI. Needs exact guest startup replacement plus a coherent private Samsung service/type cohort. | Cold state maintenance plus private/canonical collisions, resource policy, local keys, JNI/classloader and internal global-protocol routing. Loader isolation/source packaging is not ART-proved; bootstrapping real owners is unfinished. | **Fallback/comparison baseline**, not automatically discarded or declared best because components exist. |
| **Narrow Samsung credential/SPM graft into guest services** | Potentially less service bootstrap and framework replacement if a complete behavioral cut exists. | A verify-only leaf omits creation/rotation/removal, legitimate migration, StrongAuth/additional factors, recoverable/profile policy, biometric invalidation, CE/key changes, notifications and uncertain commits. Grafting these into guest LSS can become a larger semantic rewrite than retaining the family. | Reconsider only with a source-closed full mutation/policy/key cut demonstrably smaller. No hash-copy or success-only route. |
| **Retain initialized Samsung authority/host runtime beside guest** | Existing users, service objects, resource/native registrations and state ownership need not be reconstructed at every switch. | Retaining full host system_server also retains AM/PM/UserManager/storage/display and background owners. Binder names alone do not isolate mount/data views, native listeners, app identity or UI. There is no proved stop-and-extract mechanism; an object cannot simply move to another process. Current switch explicitly destroys this lifetime. | Separate **secondary topology** if cold bootstrap fails. Not equivalent to the dedicated cold realm. |
| **Genuine ColorOS frontends over live OneUI runtime, as in paused parent direction** | Strongest security-state simplification: ordinary Samsung policy/native/CE owners remain running. | Genuine ColorOS SystemUI, Settings and app-auth UI still need real framework/resource/lifecycle compatibility. The parent does not provide that complete product. Replacing the requested full OneOS ColorOS session with UI transplantation may change scope. | Explicit product-scope fork needing Apple's decision and a genuine-UI compatibility proof. No silent pivot to a theme or reduced feature set. |
| **OneOS-native security changes / upstream integration** | Appropriate place for startup, endpoint routing, exclusive handoff, preservation guards and default-off recovery to participate coherently. | This is a delivery/topology mechanism, not an existing Samsung authority. Native-language rewriting or removing guard patches does not supply Samsung state, policy, fresh tokens or key/storage effects. Current upstream still excludes ordinary locked switching. | Required cooperation/provisioning work for the chosen method; **not an upgrade-only sixth backend**. |

There is no evidence-backed whole-project ETA. Dedicated placement may reduce
class-realm work but lose that advantage to bootstrap/global dependencies;
retention may reduce state reconstruction but require a much larger OS ownership
fork. A quick existing-PIN demonstration would not settle either cost for the
full lifecycle/crypto goal.

## Finite next gate: one complete bootstrap slice in two placements

Prepare one bounded, source-backed bootstrap/ownership card for the dedicated
realm and the guest-process baseline. Use the same required behaviors, not
different reduced demonstrations. Each card must name the real producer, ABI,
state generation, lifetime and failure owner for these five boundaries:

1. **Process and code realm:** launch slot relative to OneOS's kill/keeper rules;
   actual source views, classpath, canonical/private types, resource/config and
   native registration target. The dedicated proposal must explain how a genuine
   Context is obtained without silently starting a second whole system_server.
2. **Direct ingress and internal routes:** guest frontend and original Stub in
   one process/thread; explicit endpoint/protocol ownership for every reached
   lookup, including actual Samsung LPU instances before their first getter.
   One option is Samsung-protocol `lock_settings` plus a separate ColorOS alias
   and exact guest lookup retargets. This remains a proposal. Never choose a
   protocol by descriptor, package guess or shared UID1000. An extra forwarding
   Binder hop would need a different reviewed delegation/authorization contract.
3. **Before earliest maintenance:** genuine application Context and resources,
   original user/serial/profile and local policy owners, exact credential/slot/
   enrollment paths, Keystore/Gatekeeper/Weaver/vold identities and sole writer.
   Put this barrier before recoverable cleanup/provider acquisition, not only
   before `checkCredential`. No empty/default owner or whole-host-data bind.
4. **Publication and current policy:** exact boot/user phases, callbacks and
   applied initial StrongAuth/factor state, current sensor/native operation and
   cache generations. A returned constructor, registered listener or call lease
   closing does not acknowledge readiness or backend/session drain.
5. **Return and uncertain writes:** block ingress, drain real work, reconcile
   committed-or-uncertain outcomes, then transfer the sole writer to stock
   OneUI. Keeping an external authority alive through return requires adapting
   stock startup; killing it before return requires a real handoff. An endpoint
   alias alone solves neither. Restore code, never an older credential state.

**Reject/stop the dedicated placement** if its Context/local/native graph only
closes by recreating an uncontrolled host server, if global routes or native
writers conflict, or if no owned launch/return lifetime exists. **Reject/stop the
guest placement** if its class/resource/JNI/internal-route closure requires
unreviewed fallback or altered security semantics. A missing binding is a failed
gate, not an invitation to replace it with a stub.

If one closes and the other fails, choose the closed placement for the next
reviewed prototype. If both close, prefer the one requiring fewer security
semantic rewrites and less mutable-authority relocation, then test that claimed
advantage. If neither closes, escalate the explicit retained-runtime/product
choice; do not expand leaves indefinitely or quietly shrink GOAL.

The cards are the first bounded **offline falsifiers**, not runtime acceptance. The
next discriminating runtime proof, only after a concrete default-off artifact,
recovery plan and separate approval, must exercise the selected genuine
authority/Context/user/native route and original caller. It must then advance
to a fresh per-use key operation that initially refuses authorization, real
Samsung authentication and completion of that same operation, with policy and
intended CE observations and safe return. Later reciprocal mutations, enrollment,
recovery and approved cold boot still must pass; no static/bootstrap-only result
settles them. Disruptive mutation faults belong to controlled upstream testers,
not Apple's primary phone without authorization.

## Peer critique and reuse

Reviewer A initially prioritized retaining initialized Samsung authority to
avoid repeated cold cleanup. Reviewer B challenged the hidden AM/PM/mount/native
owners retained with host system_server; A withdrew any presumed retention win.
Root clarified the dedicated-process/no-extra-hop alternative. Both reviewers
then prioritized that **cold-import placement**, with guest import as fallback,
and kept full initialized-host retention distinct. B also required explicit
alias/internal-route and return ownership rather than UID-based multiplexing.

At freeze both agree on this next-proof priority, not on a proved fastest/best
working architecture. The Context/dependency size, real live state/caller/native
closure and comparative performance remain unknown; no factual disagreement is
hidden by claiming consensus on those outcomes.

Reuse the frozen readers, ABI/state/policy reports, optional OPPO cuts, typed
dispatch, UserInfo field converter and native metadata work when their exact
profiles and placement contracts apply. A dedicated co-resident process can
reuse direct dispatch; a two-hop remote design cannot inherit its caller-frame
proof. Optional UI leaves do not supply authority; neither metadata helpers nor
their test counts justify continuing an otherwise failed architecture.
Private SID/rebinding or loader-barrier work may be unnecessary in a coherent
Samsung realm; do not select it merely because it has already been written.
No parent work was resumed and no source implementation, phone or Git state
changed in this review.
