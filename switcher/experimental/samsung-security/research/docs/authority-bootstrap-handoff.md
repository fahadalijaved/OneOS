# Authority bootstrap gate G: OneOS 0.4.57 launch and handoff

**Result: a precise candidate source slot exists; a safe executable handoff does
not yet exist.** Place a proposed authority-launch/view-preservation hook
immediately before `oneos_switch.sh` **line1087** (`guest_prepare.sh`), after the
host Java kill and keeper installation. This is an integration proposal, not a
running process or an assertion that killing the previous writer is sufficient.
No authority PID, endpoint owner, native generation or live mount was observed;
the phone is offline. No downloaded script was executed.

The [inventory](../inventory/authority-bootstrap-handoff.json) pins the current
fourteen-source OneOS **v0.4.57**, commit
`1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`, plus one specifically missing
[immutable return script](https://raw.githubusercontent.com/fahadalijaved/OneOS/1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe/switcher/assets/return_to_oneui.sh).
Its SHA256 is `04eec2a0b855ddbb89035b6c2d7daeb086e7a094a31be274c3213f79a89b0a03`.
All raw source stays ignored under firmware. The authored audit verifies 15
source hashes and 28 bounded ordering/branch facts. These are source facts, not
evidence of the installed guest or successful device behavior.

## Why this launch slot, and what it does not provide

| Current source edge | Consequence for a dedicated Samsung authority |
| --- | --- |
| Switch971/979 stops host zygotes; 995 kills generic `app_process64`; 999 kills `system_server` | A Java authority launched before this window can be killed. Renaming it is not ownership or a safe bypass. SIGKILL does not acknowledge a partially completed credential/native operation. |
| Switch1011 installs a 0.2-second polling keeper stopping host zygotes and selected display/audio processes | An independently launched process must have its own lifetime. The polling loop is not a proof that an automatic stock restart can never overlap the new writer. |
| Switch1087 calls guest preparation | **Candidate hook immediately before this call**, after the kill/keeper/watchdog work. Preserve the Samsung view here, before preparation replaces host data paths. There is no current hook, launcher or admission barrier. |
| Prepare3240–3268 binds staged app/user/user_de/media/resource-cache and other bridge trees over host `/data` paths, then binds staged data into guest root | Waiting until guest launch is too late to assume a clean Samsung application/resource/data view. Preserve real physical credential/slot/enrollment/user/key state, not a copy or a blanket bind of host data into the guest. |
| Switch1149 calls `guest_props.sh add` | A mount namespace does not isolate the shared property service. Late Samsung feature/policy queries require an admitted intended view; merely inheriting old environment variables does not establish that. This pass pins the call/order, not every property-helper write. |
| Switch1418 launches guest takeover with `unshare -m`; guest-start13–48 makes mounts private, pivots root and detaches old root | Launching the Samsung authority inside this guest view is unsuitable. Its observed native/config/state paths would be guest paths. |
| Guest-start106–125 derives guest classpaths; 615 can mount fresh tmpfs on `/metadata` | Keep actual admitted Samsung app_process/bootclasspath/system-server sources, APEX/resources/linker/native view independently. The guest's derived classpath and new password-slot mount are not that view. A bootclasspath is not a genuine Context or initialized service graph. |

**Required proposal:** after real old-writer retirement, a supervisor would
create/retain an independent Samsung code/resource/native/data view before1087
and launch the admitted authority there. Exact UID/domain, executable/source
profile, actual PID/start identity, namespace/root and Binder service handles
must belong to that supervisor. Neither a process name nor a PID file is proof.
This report supplies no launcher or root automation.

A blanket frozen/private mount clone is not a completed solution: legitimate
Samsung vold/CE mount changes still need the correct visibility, while guest
bridge overlays must not replace authority paths. Shared Binder names,
properties and hardware remain global concerns. Context, users/serials,
PackageManager/DPM/local services, policy, native registration and FP construction
are the separate scope-A graph; the early original cleanup effects must have
correct bindings **before construction**. No empty owner or new whole
system_server is implied by this slot.

## Source-bound sole-writer and native contract

The proposed generation cut is:

1. **Before stock stop971:** close new stock credential/enrollment mutations and
   obtain actual operation/native-session drain or reconcile every uncertain
   commit. Retain real user/source/state/endpoint ownership. Current switch
   baseline545 records return state; it is not this acknowledgement.
2. **After kill999, before new construction:** establish that the prior Java
   writer and any in-flight native work can no longer mutate under its old
   generation. Inhibit producer restart/duplicate publication. Neither signal
   delivery, a sleep, a dead Java PID nor an unchanged native PID proves this.
3. **Before guest construction/UI:** admit the new actual service generation
   only after genuine construction, native/state ownership and applied current
   policy. Scope B proposes canonical **Samsung-protocol `lock_settings`** plus
   guest alias **`oneos_coloros_lock_settings`**, both entering the same authority
   process directly. Complete guest lookup cuts, original LSS/FP producer
   suppression and guest-local lifecycle adapters must precede their original
   constructors. Alias publication is not readiness or a boot/user channel.

These are required owner transitions, not a newly implemented Boolean or shell
ticket. Actual scope objects must bind the live service/source/user/native
generation and reject stale work after callbacks. Unknown state must retain
protected presentation; it must not become NONE, zero lockout or UI success.
Gate G cannot substitute for scope A's construction or B's endpoint/lifecycle
proofs, and it contains no runtime gate implementation.

Existing native preservation matters. Prepare1249–1281 selects a matched guarded
vold/service.incremental pair and records guest alias **gvld**; guest-start679–709
checks original vold PID/name and its consumers before starting guest vold738.
The fallback explicitly lets guest vold take canonical **vold**, with no in-place
return. That fallback is incompatible with this preserved-Samsung-native
candidate; actual selected build/branch remains unverified. Do not restart or
replace stock vold/keystore2 to make a probe proceed.

Return baseline78 lists `vold`, `android.system.vold.IVold/default`,
`android.system.keystore2.IKeystoreService/default`, `installd` and
`android.service.gatekeeper.IGateKeeperService`. It also records boot ID,
properties, APEX and linkerconfig views. It does **not** establish actual
fingerprint/Weaver/KeyMint session generations, a new authority's native lease,
fresh HAT/key authorization or ownership of pending storage writes. Native
Binder death and cancellation/drain/reconnect effects require their real owners.
OneOS keepers and the global media/composer/native changes also continue around
guest startup; their mere coexistence is not a completed Samsung policy owner.

## Return: retire first, then reconstruct stock

Unchanged return has no new-authority shutdown channel. It stops recorder and
keepers at193–223, broad-kills command lines matching `system_server` at225,
and SIGKILLs processes matching guest namespace/root device at256–285. A
naively named or guest-root authority could disappear here before reconciliation.
Removing the keeper at216 also cannot serve as the new writer's retirement ack.

**Proposed required pre-return cut:** before this force-teardown section, close
new ingress, preserve endpoints needed for real completion/cancel, drain owned
credential/FP/native/storage/callback work, and resolve committed-versus-uncertain
writes. Retire the exact dedicated authority generation and prove it cannot
republish or write. Its code/state views and native anchors stay retained through
their actual obligations. Process death, endpoint absence, SIGKILL or a copied
credential snapshot is not equivalent. An unresolved operation blocks an owned
safe handoff; there is no implemented no-reboot recovery contract here.

The existing **conditional in-place** source order then provides insertion
constraints:

1. Restore original host data bridges343–363 and detach stage mounts389–416.
   Protected-state comparison368–386 is **logging only**, not commit
   reconciliation or credential rollback.
2. Gate A689–709 compares selected native endpoint PIDs to baseline and rejects
   premature stock Java start. Add the real authority-retirement/source/state
   generation proof before stock reconstruction; unchanged native PIDs alone
   do not prove it.
3. Restore properties and baseline SELinux before stock processes710–753;
   rebuild required native display/audio/media services. Gate B859–874 requires
   no guest-root processes and expected native services present.
4. Return892 restarts zygote_next where applicable; 894 restarts netd and
   897–907 starts stock zygotes. Original stock system_server/LSS/FP then
   reconstruct over the **current committed Samsung state**, after the
   dedicated writer is retired. Keeping it active would require a different
   stock producer-suppression design. Restore code/mounts, never an older PIN,
   protector, enrollment or key snapshot.
5. Gate C910–942 watches one stock system_server PID and user0 unlock/launcher
   plus30 seconds. It is not acceptance of reciprocal PIN changes, fresh app
   authentication, encrypted data or fingerprint behavior.

**No no-reboot claim:** return422 defaults to reboot; in-place requires explicit
mode, same-boot baseline and teardown checks. Failure can select reboot/shutdown
or enter the explicit failsafe498–517. The current source therefore does not
prove the requested owned return without an agent reboot. No mode, property,
reboot, mount or guard was changed in this work.

Gate G remains open until the actual launcher/view/native generation and both
writer handoffs exist alongside A/B construction/producer proofs. Live installed
profile, PID/endpoints/mounts and all GOAL acceptance remain pending. Parent
ColorGlass stays paused.

Recheck only static evidence with
`python tools/audit_authority_bootstrap_handoff.py`. This tool reads/hashes source
files and emits derived JSON; it never invokes any downloaded script or phone
operation.
