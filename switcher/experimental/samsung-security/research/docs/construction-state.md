# Stage 1: authoritative state, paths and handoff

This closes selected **static path and startup-mutation edges**, not a runnable
authority or a live physical binding. It follows [GOAL.md](../GOAL.md), including
the choice to adapt native ColorOS and remove unsupported optional OPPO UI/work.
No phone, credential/enrollment files, OEM code or native service ran. All live
identities and cryptographic acceptance remain unknown. The derived inventory is
[construction-state.json](../inventory/construction-state.json); exact raw-body
handles and source hashes accompany every checked assertion. Existing
[storage/key](storage-keys.md), [credential construction](construction-credentials.md)
and [fingerprint construction](construction-fingerprint.md) findings remain
separate dependencies.

Reproduce the bounded checks with `python -B tools/audit_state_binding.py` from
the nested project. This verifies pinned archives/source files and retained raw
receipt hashes, then regenerates authored metadata. It executes only the static
reader and authored checks.

## Concrete path resolution

The same path string can name different files in the host and guest. Both actual
Samsung and ColorOS `ContextImpl.getDatabasesDir()` special-case package `android`
to literal `/data/system` (PC7/21); other packages use `getDataDir()/databases`.
`getDatabasePath(name)` uses that directory for a relative name. Samsung
`SQLiteOpenHelper.getDatabaseLocked` calls its retained Context's
`getDatabasePath` at PC82, then opens the result. LSS's actual DatabaseHelper
passes `locksettings.db`, version3, WAL disabled, as already pinned in the
credential audit. Thus an actual system-package Context selects namespace-relative
`/data/system/locksettings.db`; the supplied dump does not identify its live mount.
A device-protected Context changes flags/data-dir selection, but does not change
the `android` database special case.

Both framework `Environment` implementations initialize their data root from
`ANDROID_DATA`, default `/data`; `getEnvPath` calls `System.getenv`, and selected
`prep` overloads return their input. Their static directory helpers do not ask
the service Context. Capturing a correct Context cannot alone redirect these
helpers, hardcoded `/metadata`, or Samsung's literal backup roots. Environment
initialization and the process's mount namespace are part of the binding.

| State | Source-selected path/identity | Required ownership |
| --- | --- | --- |
| Credential DB | System Context path above; original helper/SQLite caches and transactions | One original credential authority, current physical database |
| SP state | `Environment.getDataSystemDeDirectory(u)/spblob`, normally `/data/system_de/<u>/spblob`; Samsung virtual-user alternative under `system/users/<u>/spblob`; `%016x.<state>` protector files | Same logical user/profile, current protector selection, original key aliases and secure identities |
| Weaver slot map | Literal `/metadata/password_slots/slot_map`; mode derives from `ro.gsid.image_running` | Same actual hardware slots, current SP inventory and original mode; never assign a new guest slot pool |
| Fingerprint metadata | `Environment.getUserSystemDirectory(u)/settings_fingerprint_<sensor>.xml`, normally `/data/system/users/<u>/…`; legacy `settings_fingerprint.xml` in the same directory | Same original user/sensor/enrollment and authenticator authority; XML does not contain hardware enrollment secrets |
| Core SP backup/recovery | `/data/sec_backup_de/<u>/spblob`; original SP tree; transient `.bnr` beside a file | Same current trusted recovery policy and protector inventory |
| Core DB backup/recovery | Actual returned backup name `/data/system/locksettings.db.bak` | Same authority; do not infer a different return path from the helper's separate mkdir of `/data/sec_backup_sys_de/locksetting/` |
| Native state | Actual retained vold/keystore2/Gatekeeper/KeyMint/Weaver/fingerprint owners; locksettings key namespace103, vold namespace100 | Original physical key/FBE/hardware authority, separate from Java user numbers and Linux UIDs |
| User registry | Actual IDs, profile ownership and serial numbers | Original user identity before cleanup or storage reconciliation; physical registry binding not closed here |

These paths are code facts with stated defaults, not observations of private
directories. The mounted OS capture excludes `/data`, `/metadata`, vendor EFS
and hardware state. No current protector IDs, SIDs, slots or enrollments were
read. `fakeUserId=u+100000`, aliases and filenames cannot establish those live
identities. Authoritative state must retain legitimate changes and invalidations;
numeric identities are not promised immutable across genuine policy operations.

## OneOS mount and preservation boundaries

Four source files are pinned at OneOS commit
`2a5f41043b4a69399cae058bad213cdef7408e88`. The installed guest is unverified.

* `guest_prepare.sh` fixes stage `/data/local/tmp/oneos`, requires init's mount
  namespace and refuses mounts under staged data before destructive preparation.
  Lines2462–2465 remove staged SP files, `locksettings.db` and its sidecars and
  `gatekeeper.*.key` if staged `*.weaver` exists. Lines2508–2509 recursively relax
  mode/ownership on staged system/misc trees. Canonical state must never be bound
  into these trees during preparation.
* Lines3233–3249 bind configured staged application trees over host `/data/*`
  targets and compare device/inode identities. Line3253 binds the stage's data
  to guest-root `/data`; line3259 makes that mount private. This protects selected
  host app trees from host daemons serving the guest; it does not merge the host
  credential authority into guest data.
* `oneos_switch.sh`1407 launches the guest in a separate mount namespace and
  records that namespace/root device. `guest_start.sh`13 makes mounts recursively
  private, pivots root, then44–48 detaches/checks absence of `/postinstall`.
  Line615 **conditionally mounts a fresh tmpfs over `/metadata`** for aconfig.
  On that successful branch Samsung's hardcoded slot path resolves into guest
  tmpfs, unless an explicit later narrow binding replaces it. The failure branch
  does not prove a correct slot map either.
* Prepare39 requires external staged `bridges.sh`;41 validates only five required
  entries. This file is absent from the selected current20-file source capture.
  Return345 has a14-entry fallback that excludes credential `system`/`system_de`
  and native key directories, but346 can source a different staged list. Its
  deployed content is unknown. Do not substitute a historical checkout's file.
* Return341–360 restores/checks host application mounts before host restart.
  The switch/return `host_state` functions hash FRP and record selected gatekeeper
  and APEX filenames/sizes/times. That is neither credential-state continuity
  proof nor a hardware commit/drain acknowledgement. No such function was run.

The authority graph must therefore bind **narrow original core state** to one
writer, while ColorOS presentation preferences, staged app data and unsupported
optional OPPO-only databases remain guest-owned. There is no whole-`/data` bind
proposal. Optional RPMB/RoR state needs preservation only if a proven retained
core route requires it. Original Samsung recovery roots above have an actual
selected core route and cannot simply be replaced by an empty guest directory.

## Mutation begins before a verification request

The following require final state/user/native bindings before attachment:

1. Frozen SPM initialization performs real Weaver config acquisition and refreshes
   the slot map from SP protector inventory. The selected virtual-user conflict
   path can remove Weaver state. An empty guest map/tree is not a passive attach.
2. `BiometricUserState` constructor probes the target path, then conditionally
   renames the legacy file (PC66) before reading (91). Parse failure can delete
   the file (58) and enqueue an AsyncTask rewrite (84). Its retained write Runnable
   uses AtomicFile start18/finish58/fail74. The fingerprint constructor audit
   traces provider construction to user0 metadata access before return. Bind
   before provider construction, not merely before authentication/enrollment.
3. The credential construction audit closes cold recoverable-key cleanup before
   LSS publication: unavailable/mismatched user serials can remove DB rows,
   snapshots and application-key entries. A guest user0 with a different serial
   is unsafe even if a Java cast succeeds.
4. `LSS.systemReady` reaches `migrateLockSettingsDB` and `migrateSpblob` as pinned
   by the credential stream. The former checks DB integrity/current protector
   and may set backup/restore flags. Actual `setLong` routes to storage `setString`;
   the flag arrays select synchronous DB restore at PC62 or backup168. Exact
   whole-services direct-reference scans find this one caller for each operation.
   The SP path initializes BnR policy, selects current/backup protectors and can
   back up or reconcile files. `SPBnRManager.checkIntegrity` can invoke both
   backup and restore lists. This is original trusted recovery, not permission
   to replay a guest DB or make a PC secret backup.
5. An absent DB can run original DatabaseHelper.onCreate, whose property-dependent
   branch writes `lockscreen.disabled` for user0. Missing authoritative state must
   fail admission before a fresh DB can be interpreted as an unsecured user.
6. Importing full Samsung StorageManagerService to satisfy LSS's concrete storage
   cast has additional effects: Lifecycle.onStart publishes its concrete local
   service at537 and `mount` Binder638, then connects vold646. Connect resolves
   service name `vold`, links death22 and sets listener39 before querying unlocked
   users91. Daemon-connected/boot-completed handler paths reach reset. When boot
   and daemon flags permit, reset calls `IVold.reset`163, sends UserManager
   ID/serial/profile data via `onUserAdded`208/215 and restores user state.
   A second ordinary storage-service startup against host vold is an active
   listener/reset takeover. Its prevention or deliberate exclusive transfer is
   still an implementation dependency, not supplied by cast compatibility.

## Exact acquisition and transfer cut

Required design, **not an implemented lease**: finish guest destructive staging;
identify actual patched bytes, process/native owners and mount graph; acquire one
exclusive authority generation before any eager owner above; install the narrow
physical state bindings after the final guest metadata mount and before authority
construction. Retain original users/profiles/serials, policy, code, native owners
and state-path ownership as one binding. Reject absence, replacement or mismatch
before enabling either mutation ingress or a misleading unsecured UI.

The binding must preserve path replacement semantics, not just one inode. Actual
Samsung `AtomicFile.finishWrite` syncs its stream then renames the `.new` path
onto the base path (PC26/28/30). A single-file bind or retained old inode is
therefore not a demonstrated solution. Fingerprint metadata shares the broader
`system/users/<u>` parent with guest settings; binding that whole parent would
also merge unrelated presentation state. The exact directory/path adapter must
preserve original create/rename/recovery behavior while keeping those guest
settings separate. This adapter remains unimplemented.

Before transfer, close new mutation ingress and generation-bound callbacks, then
account for actual in-flight verification/reenrollment, SP upgrades, recovery,
enrollment/removal, metadata writes and native transactions. SP AtomicFile writes,
optional directory fsync and SQLite transactions define separate local write
sequences; the slot map uses its own stream write, and fingerprint writes are
asynchronous. Actual AtomicFile logs failed sync/rename rather than making its
void return a durable-success receipt. None establishes one atomic transaction across Weaver/Gatekeeper,
KeyMint, vold, SQLite, XML and SP files. Ordinary return, cancelling a Job, killing
system_server or removing a mount does not prove those owners drained.

Only a reconciled current generation can release the writer to the successor.
If a trusted operation may have committed but its response or durable-write
acknowledgement is uncertain, block competing startup/mutation and preserve the
current physical state. Determine the committed result through a source-supported
original recovery/query path; do not retry enrollment blindly, reset slots,
restore an old database or assume hardware rollback. The concrete operation
ledger, completion acknowledgements and uncertain-commit reconciliation are still
open. Keep the feature disabled/fail closed until they exist.

Live non-secret evidence still needed includes actual installed bridge/patch
identity, each process's mount namespace and `ANDROID_DATA`, directory device/inode
bindings, service Binder/process ownership and original user/profile/serial
mapping. Collect no file contents or enrollment/protector secrets. Later accepted
device cases must prove reciprocal changes, legitimate old-credential rejection,
fingerprint management, fresh operation-bound key use and intended CE/app-data
continuity after return/reboot. Already-unlocked CE or a previously authorized key
cannot establish fresh authentication. No controlled fault test or beta-ready
claim follows from this static cut.
