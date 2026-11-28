# Retained physical user versus guest runtime lifecycle

**OneOS already supplies substantial guest app-data plumbing. It does not supply
a shared Samsung user/key authority.** A genuine Samsung user can remain running
with CE unlocked while an ordinary lockscreen is locked: the selected source has
separate device-lock/Keystore policy and physical user-stop/key-eviction paths.
That is a supported design distinction, not a current device or all-profile policy
claim. Retention must preserve the real Samsung policy and actual physical state;
it must not import the guest's forced-true CE answer or replay guest boot into the
host user registry.

This card compares **actual selected staged code**, not just the original donor.
Root acquired the three JARs read-only through the init view, checking remote
metadata/hashes and four manifests before/after and local bytes. Acquisition
`ad6b1d7a…` pins services `efb45f5f…` (44,699,364 bytes), framework `5cb16a37…`
and oplus-services `a854468f…`, for installed OneOS0.4.57/code74 profile
`s-ultra-8850/coloros17-findx9u-in/x9u-in-sultra`. The
[inventory](../inventory/retained-guest-user-lifecycle.json) pins the exact paths,
full hashes, raw receipts and 89 instruction/reference checks over 90 method
proofs. Thirty-nine selected method pairs compare against original donor
`66d0d51d…`/framework `d5c6b7fd…`:33 normalized bodies match and6 differ. Four
existing OneOS proxy methods and four peer-read staged guard methods are also
pinned. Counts describe this finite cut, not security coverage.

No JAR was rebuilt, method executed, private user state read or phone action
performed by this worker. Acquired staged bytes are not proof of a loaded guest,
actual object graph, Binder endpoint generation or native effect. PCs are decimal
DEX code units. The older donor-only lifecycle card remains unchanged history.

## What the installed OneOS path already does

The frozen [installed-code profile](installed-oneos-code-profile.md) pins these
packaged script edges; the new method proofs pin the bytecode bridge.

| Existing mechanism | Concrete source / acknowledgement limit |
| --- | --- |
| Guest app-data tree routing | `guest_prepare.sh:5–10` requires the init mount view. Lines3240–3258 bind fourteen host app-data paths to `STAGE/data` counterparts and require dev:inode equality for every existing host path, otherwise exit3. The list includes `/data/app`, `user`, `user_de`, `data→user/0`, media, profiles and sandbox/rollback trees. It is not a blanket bind of host `/data/system` or a copied Samsung registry. |
| Guest root data view | Prepare3260–3265 binds staged data into guest ROOTFS/data and makes that mount private; start pivots root. CE/data-mirror binds at start77–85 are best effort. These are source actions, not observed future execution or whole-thread isolation. |
| Existing canonical native Installer route | Actual `Installer.connect` gets literal `installd`0/3, links death15, invokes **OneOSInstalldProxy.asInterface**23, caches27 and counts down31. There is no new guest/ginstalld publisher/socket alias in these scripts. No separate native daemon is proved. |
| Existing typed OneOS Binder bridge | Proxy constructor retains its actual supplied Binder; createUserData writes `android.os.IInstalld`, UUID/user/serial/flags17–26, transacts code1/flags0 at33, ignores handled Boolean, reads exception37 and recycles its own parcels. This is concrete existing adaptation, not an authored replacement here or backend attestation. |
| Real guest creation call still present | `Installer.createUserData` still invokes IInstalld9. `checkBeforeRemote` has the original isolated=false-return path78/79, ten-second latch wait84/86, timeout throw101, and interrupted-wait continuation to true103. Latch readiness/void return is not data/native completion. |
| App scaffolding | Prepare3564–3626 emits `ensure_app_storage.sh` using guest packages.list, numeric UID ownership and CE/DE/external directories. Start1145–1154 backgrounds a polling loop and logs startup, without completion acknowledgement. Failures and mirror binds can be ignored. This supports the intended guest package tree, not credential policy or per-use key acceptance. |

The ordinary-OneUI observation `2d55a1ae…` adds one qualified fact: init and the
observed installd main process shared mount namespace4026532781 and `/data`
shared:48; the observed system_server main process used4026536359 with `/data`
master:48. Start/namespace checks were stable around the observation; sampling
was not atomic. Different namespaces alone therefore do not establish a retained
private path view. This is neither a future OneOS bind experiment nor all-thread,
Binder/native-authority or propagation-completion proof. Executable hash
`ed618c38…` identifies the observed installd file, not the recipient of a future
Binder request.

## Effective guards: guest status is not physical truth

The selected staged UMS beforeStart/beforeUnlock, guest controller
beforeUnlock49→UMI77→continuation114, all selected Trust methods and Injector
concrete-owner caches are body-identical to donor. Those real guest app-runtime
operations still exist. Their downstream semantics are changed:

| Actual staged method | Exact behavior |
| --- | --- |
| SMS.isCeStorageUnlocked | **const true0; return1.** Old locked-cache code remains unreachable at2. The unchanged framework helper/controller checks therefore cannot establish actual CE state. |
| SMS.prepareUserStorageInternal | Native IVold.prepareUserStorage is removed. The real wrapper can return normally without physical preparation. Original ignored-error policy also remains. |
| InternalImpl.markCeStoragePrepared / isCeStoragePrepared | Actual lock plus Set.add/contains remains. A genuine Java bookkeeping update does not acknowledge native CE preparation. |
| UserDataPreparer | Real ID/serial, original Environment paths, serial checks and Installer.createUserData101 remain. Missing serial may be set; an existing mismatch still throws134. The inner method can log/catch and return void. Terminal recovery wipe is replaced with a OneOS log303/305. |
| UserDataPreparer.destroyUserDataLI | Immediate return0; old file/native cleanup is unreachable. Installer.destroyUserData's remote destruction is separately removed. These are preservation guards, not completed deletion. |
| SMS.lockCeStorage | Native call becomes NOP59 but the guest unlocked cache is removed65. |
| InternalImpl.unlockCeStorage | GOTO12→17 skips the native call while the guest unlocked cache is appended28. |

Shade's exact staged reads show LSS.lockUser and its LocalService bridge still
match donor: IStorageManager.lockCeStorage30, conditional Keystore lock40,
StrongAuth49 and metrics removal55 remain. The unchanged controller can then
call keyEvicted39 despite suppressed native CE eviction. That callback therefore
is **not a physical eviction acknowledgement** in the current staged profile.
No preservation guard should be removed merely because a real Samsung object
was captured.

Guest app preparation is real work, not a pure query. BeforeUnlock still invokes
its vendor storage-normalization hook13, UserDataPreparer57, local prepared mark67
and its **guest PMS** reconciliation97. Actual PMInternalBase forwards to
AppDataHelper; that helper iterates guest writable volumes under its guest PMS
install lock48 and calls its original deeper reconciliation54. This is not
evidence that the retained host PMS package set can replace the guest package
set. The deeper helper/vendor policies and native runtime views remain explicit
frontiers, rather than invented no-ops.

## Keep three truthful states separate

1. **Samsung physical user/registry:** the original admitted UMS user, serial,
   profile/type policy, real active host UserController occurrence and SMS/native
   CE generation. If that user really remains running/unlocked, its host state
   stays genuine. Guest boot is not a new host-user boot. Do not seed default0,
   copy registry state or forward guest set/remove blindly into host UMI.
2. **Guest application runtime:** the actual guest UserController/UserState
   instance and source ordering around app-data preparation and progress. Guest
   state0→3 describes that runtime's progress, not a second Samsung physical/key
   authority. Its concrete guest UMS cast/cache cannot accept a remote or
   private-loader Samsung UMS. A typed source adaptation must bind identities
   and local responsibilities; it cannot call cached foreign Java objects.
3. **Device lock / authenticated keys:** actual keyguard, trust, StrongAuth,
   biometric/profile and Keystore policy. Guest refresh reads its WM keyguard192.
   Samsung refresh separately reads its own WM keyguard150; calling refresh alone
   would reread that old view. Samsung setDeviceLocked retains real DualDAR
   hooks71/80, trust agents, Keystore141 and listeners/profile work. Required
   enterprise policy may impose extra locking; ordinary separation is not an
   unconditional all-profile exemption.

The selected actual Trust device-lock paths do not stop the UserController or
perform the explicit physical CE-eviction operation. Thus ordinary screen lock
does not require fabricating host stopping/booting states. But a real source-owned
guest keyguard view must reach the same Samsung policy owner; UID1000, an arbitrary
Boolean callback or an old host WM cache does not provide that binding.

The actual staged KeyStoreAuthorization onDeviceLocked/onDeviceUnlocked wrappers
also match donor. They attempt the real IKeystoreAuthorization calls7, return
service-specific errors or connection-error4, and their Trust caller does not
consume that return status. They are not the SMS forced-true guard, but neither
their Java return nor notification delivery proves key authorization. Retaining
both host and guest Trust publishers without selecting one genuine physical-user
policy source could race contradictory native lock notifications. This policy
producer must be bound, rather than assumed harmless because CE remains unlocked.

The legitimate already-done case is narrow: original **Samsung** LSS
unlockCeStorage queries its own actual CE owner7 and returns29 if already
unlocked, before FBE/native unlock work. Never substitute the staged guest's
constant true or force that branch. Host authentication still needs actual
credential/HAT/Keystore/StrongAuth effects and original policy. No blanket
beforeUnlock or package-preparation no-op follows from CE being unlocked.

## Source/API/control contract and first missing owner

These are responsibilities for root selection, not implemented endpoints:

| Occurrence | Required real typed work / terminal meaning |
| --- | --- |
| Begin/continue guest runtime user | Bind its exact source UserState/current user to the genuine Samsung user/serial/profile; retain actual guest package/Installer/data owners. Execute the guest app-data duties once in their admitted view. Preserve original current-object/CE/order/progress checks; do not run both PMS preparations against one redirected backend. A posted worker, void helper, guest prepared Set or state3 is not native data readiness. |
| Verify/change credentials or authenticate | Invoke the retained genuine Samsung credential/fingerprint authority under original caller/user/challenge/policy ownership. Its legitimate already-unlocked CE branch may occur naturally. Do not manufacture a host lifecycle event, signed token, app-key result or success from guest state. |
| Lock/unlock the screen | Admit the actual guest keyguard source/view into original Samsung Trust/StrongAuth/biometric/profile/Keystore policy, including unchanged-state/DualDAR behavior. Keep the physical user running only where actual policy permits. No user-stop callback is substituted. |
| Actually stop/evict the shared physical user | One genuine authority performs original ordered physical CE/Keystore/StrongAuth work with real outcome and child acknowledgement. Both runtimes must reflect that real disposition. The host cannot simultaneously be claimed genuinely running/unlocked. Current guarded guest callbacks do not satisfy this contract. |
| Retire only the guest VM / return | Close guest lifecycle/Installer/app work ingress and own its queued, active, failed and native-uncertain work. Do not remove host UMI state or announce physical keyEvicted merely because the guest VM disappears. A distinct source-selected runtime-retirement acknowledgement is required if physical eviction is intentionally absent. Restore the native/path view before retained host app-data producers resume. |

There is no complete cancel/drain API in this cut. Retiring while preparation is
queued or executing cannot become complete from cancel issuance, a Handler marker
or the callback alone. Original operations may have issued mutations before a
failure/return. Preserve their exact outcomes; do not retry unknown work or use
a new helper's counter as global completion.

**Earliest exact missing owner:** the admitted **data-view/native-writer split**
before packaged init-view app-data overmounts and subsequent Installer requests.
OneOS's existing proxy, staged tree and scaffolding should be reused as concrete
inputs. They were designed alongside host Java teardown; they do not establish
that a retained PMS/UMS/SMS cohort can continue future app-data work against its
original view while the same canonical native installd is redirected for guest
requests. Capture/private references alone do not preserve those future paths.
Retained Trust's actual guest-keyguard input is a second concrete policy binding.

Therefore an executable retained lifecycle endpoint is **not yet source-closed**.
The next engineering action is an offline source/control contract for exactly
this existing Installer/proxy + fourteen-tree handoff, including which real
producer is paused/routed and what its actual completion means, paired with the
source-owned retained cohort capture. If the native/data responsibilities cannot
be separated without duplicate writers or false outcomes, reject this retention
cut. Do not author another cold UMS, generic admission callback or broad no-op
facade. Root owns selection; no architecture pivot or runtime hook is supplied.

Recheck saved evidence only:
`python -B tools/audit_retained_guest_user_lifecycle.py --report`.
Explicit `--capture`/`--capture-stage` collect only the bounded declared selectors
and reused receipts; neither executes original methods or changes the phone.
