# Actual old-authority quiescence boundary

**Source result:** the old Samsung LockSettings writer cannot be drained by
renaming/unpublishing a Binder service, waiting for a new router's call count,
taking one Java lock, stopping a process or observing an empty queue. Concrete
original work can outlive the synchronous verification/change call. No existing
comprehensive admission-and-drain API was found in the five inspected owner
declarations. A new real old-system_server hook and worker/native completion
contract remain unimplemented; this card does not authorize installing one.

The [inventory](../inventory/security-authority-quiescence.json) pins 84 focused
method proofs and nine source cards. It reuses the original LSS199, SPM/storage,
construction and native/storage evidence, plus the policy worker's exact
Lambda3 receipt. New reads are limited to direct LocalService, original callback,
receiver, Runnable/deferred-queue and alarm continuations. Samsung services
`def967fb…639f6` is read as its full DEX041 container. Each method has its exact
descriptor, normalized hash, physical DEX/header, reference PCs, monitors and
catches. PCs below are decimal 16-bit code units. No OEM/JNI, phone/ADB or
activation/restart operation ran; no live device state was inspected.

## Concrete synchronous and deferred boundaries

| Actual source | Why its synchronous return/lock is insufficient |
| --- | --- |
| `SPM.unlockLskfBasedProtector` | Normal verification invokes Gatekeeper verify at435 and can **reenroll** at461, save/sync state at518 and later985, and synchronize FRP state. Its early progress callback834 precedes final `verifyChallenge`898. It has no own synchronized-method flag or monitor instructions. Verification and progress cannot be classified as harmless reads or completed operations. |
| `LSS.doVerifyCredential` | Contains real `mSpManager` monitor regions (including enter323), but posts actual BiometricDeferredQueue work567 and integrity work622. Selected branches also make an earlier SPM call87 before that method's first monitor. This is a source-local observation, not a claim about every caller's locks. Releasing a monitor does not acknowledge those posted/native effects. |
| `LockSettingsStorage` | File writes use their actual `mFileWriteLock` (read7/enter9), AtomicFile and Samsung backup work; SQL mutation uses separate database transactions. Write/fsync error paths can log/catch IOException and return void. `closeDatabase()` only invokes SQLiteOpenHelper.close, not producer shutdown, native drain or successful distributed commit. |
| `LSS.unlockUser(int)` | Calls real `IActivityManager.unlockUser2`42, waits **15 seconds** at49 and **ignores the Boolean result**. Actual `$4.onFinished` counts down at11, but method return can follow timeout/interruption without that callback. It additionally posts deferred biometric work86/265. A returned Binder frame does not settle the AM user-unlock operation. |
| `LSS.setLockCredentialWithSpLocked` | Posts original Lambda9 at334 after credential/native-key effects. Its removal branch calls fingerprint `removeAll`82 and face `removeAll`149. Both timed waits85/152 ignore their Boolean results. Credential setter and Runnable returns do not establish completed biometric deletion or durable enrollment metadata. Actual removal callback/provider/native-state disposition remains open here. |
| `BiometricDeferredQueue` | Lambda0 stores actual derived Gatekeeper authentication input for queued work. Lambda1 can request face challenge168, request real HAT through `verifyChallengeInternal`, and issue FP reset317/376, face reset193/237 and BiometricManager reset458. It clears lists243/396/464 after requests. Empty lists and completed Handler dispatch do not acknowledge outstanding challenge/reset/native work. |
| Metrics/StrongAuth | `notifyPasswordMetricsChanged` posts at34/59. Lambda3 performs genuine DPM password reports17/33 and WM report44. StrongAuth has its own main-Looper Handler, message dispatch and AlarmManager listeners; alarm callbacks enqueue new policy work. A service-Handler marker cannot drain that owner. Do not drop required notifications, cancel policy into an unlocked default, or discard deadlines to obtain an empty queue. |

The shared optimized Lambda12 class includes integrity, protector and reboot
escrow branches, including further posts/delays. Retirement must identify the
**actual queued instance/captures/branch**, including `mDoVerifySI`, rather than
treat every object of the class as one completed task. This card does not close
all reboot escrow, Knox/DAR, recoverable-key, scheduler or maintenance callbacks.

## Actual admission roots

A guard on a newly published name does not revoke cached old Binder handles.
The original live Stub/method entries must be covered. Same-process local calls
also have independent entry points: all twelve captured
`LockSettingsService$LocalService` methods were read. Examples are:

- `createNewUser` reaches AndroidKeyStoreMaintenance and initializes SP;
  `removeUser` / `clearStorageForUser` reach real state removal.
- Token credential change/unlock delegates into original mutating methods and
  `onCredentialVerified`; it does not traverse a new public Binder frontend.
- Local StrongAuth refresh, secure-lock-device and reboot-escrow methods
  schedule/perform real work. `onThirdPartyAppsStarted` performs user/state
  maintenance.

Actual Lifecycle user/boot callbacks, DeviceProvisionedObserver and Receiver$3
are further roots. Receiver$3 can reach separate-profile challenge change548;
its other branches reach DAR/native work. Constructor-registered maintenance
callbacks and other conditional feature owners have not been completely closed.
An uncovered root blocks the claim of complete admission, even if ordinary PIN
requests are counted correctly. Do not infer purity from a method's name.

The captured LSS declares `closeSession(String)`, but its body performs
recoverable-key session cleanup for the caller; it is not global retirement.
SPM, StrongAuth and BiometricDeferredQueue declare no quiesce/shutdown/drain/
pause/stop/close method in these captured classes. This is a bounded declaration
finding, not a claim that every framework lifecycle mechanism was audited.

## Minimal proposed control seam, still unimplemented

1. Bind the control to the **actual old service/graph/source/native generation**
   in old system_server. Close new original Binder **and** local/lifecycle/event
   admission before irreversible work. Replacing ServiceManager lookup alone
   does not cover retained handles or direct Java calls. Preserve original
   caller/user permissions and protected UI behavior; no synthetic NONE,
   no-lockout, success or policy clearing is permitted during retirement.
2. Retain each already-admitted operation and its actual original child work:
   service Handler tasks, StrongAuth messages/alarms, biometric queue/challenge/
   removal callbacks, AM unlock listener, DPM/user work and native/storage calls.
   New producer events must be fenced or transferred without losing genuine
   policy. A counter is useful only after those real producers/children are
   enrolled; zero router calls or one posted queue marker is not that proof.
3. A coordinator outside the queues/monitors it awaits obtains actual terminal
   acknowledgements and reconciles uncertainty. Do not wait for a Handler from
   that same Handler or manufacture callback completion. Delayed/nested posts,
   already-dispatched alarms and external native work can outlive a marker.
4. Observe native issue/outcome and persistence at the real boundaries, including
   original caught/void paths. Existing storage proof shows lost replies can
   follow mutation and status getters do not reconcile key protection,
   durability or per-use authorization. Gatekeeper/Weaver, keystore, vold and
   fingerprint operations require their own legitimate completion or recovery
   ownership. Retain uncertain outcomes rather than blindly retrying them.

No root module, method hook, control Binder, retirement API, generic stop/drain
helper or distributed completion implementation is supplied by this analysis.
Ordinary reflection/class-shape checks do not install a hook into already loaded
original methods. Exact producer closure, installation/access, native callback/
session/persistence acknowledgement and protected failure/return remain open.

## OneOS placement and alternatives

Old-owner quiescence must complete **before v0.4.57 switch971**, the first
`ctl.stop zygote`, which can remove the old owner before explicit kills995/999.
The proposed new-authority launch slot before1087 is too late to drain it.
The keeper1011 polls; it is not a sole-writer acknowledgement. On return, the
same real retirement must precede force teardown193–229/guest-root kills and
stock reconstruction894–907. Root's frozen handoff facts/source hashes are
reused; no old G files were edited or scripts executed.

The source supports reviewing instrumentation at the concrete old-owner and
worker boundaries above, but no complete control currently exists. Retaining
the genuine initialized Samsung authority avoids transferring its unfinished
operations, yet current OneOS kills its system_server; preserving its real
dependencies and excluding conflicting framework producers requires a different
admitted topology. Treating SIGKILL or ordinary crash/startup reconciliation as
the handoff has no supplied proof of atomic recovery across SP/native/key/
enrollment state, and does not establish the requested owned no-reboot return.

**Current cut remains open.** No new writer may be called safe merely because
the old process stopped, a property changed, a new endpoint was published,
SPM/file locks were acquired, queues looked empty or a native getter answered.
No architecture is declared impossible, and no required behavior is waived.
Parent ColorGlass stays paused.

Recheck static evidence with
`python tools/audit_security_authority_quiescence.py`. `--collect` only repeats
the fixed narrow static queries; it performs no OEM loading, hardware getter,
phone/ADB call, activation, install or Git operation.
