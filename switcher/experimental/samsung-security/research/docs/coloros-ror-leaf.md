# Cold-start-only optional ColorOS RoR/SP removal leaf

**Unselected PC artifact. No OEM/Android execution, installation, authentication
acceptance or live callback teardown.** This leaf removes optional ColorOS
resume-on-reboot SP persistence/recovery ingress from the same original SystemUI
APK used by the separate input/RPMB-removal worker. Root owns composition; this
producer never consumes that worker's output or changes any selector.

Run `python -B tools/build_coloros_ror_leaf.py`.
[Inventory](../inventory/coloros-ror-leaf.json) records exact source/patched body
hashes, instruction byte ranges and whole-method ranges for composition, per-DEX
integrity/inverse proofs, actual static-reader receipts and selection conditions.
Raw bodies stay in ignored `firmware/ror-leaf/`; binaries stay in `out/ror-leaf/`.

## Input, output and exact scope

- Original APK SHA256:
  `0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77`.
- Output `out/ror-leaf/SystemUI.ror-removal.unselected.apk`, SHA256:
  `926c6eab784253b4548c77e4e9210fe8a574fb53317764066afc625f1303d927`.
- Nine ordinary DEX039 files with 112-byte headers; only `classes3.dex` and
  `classes8.dex` change. Nine methods have ten edited instruction ranges.
- `selected:false`, `coldStartOnly:true`. All 73,080 original class definitions
  remain; no class, field, method signature or code-item extent is added/removed.

Below, **manager** is
`com.oplus.keyguard.security.verify.OplusKeyguardVerifyManagerExImpl`;
**reboot callback** is its `$checkRpmbWhenReboot$1$1` class. PCs are code units
inside the exact pinned methods, not file offsets.

| Owner/method | Edit | Purpose |
|---|---|---|
| manager constructor | NOP PCs83..113 | Remove cold-dead optional reboot keystore wrapper, password-changed callback and OPPO SP-manager allocations/field writes |
| manager `init(KeyguardUpdateMonitor)` | NOP PCs56..62 | Remove optional SP-callback field loads and registration before any SP can be delivered |
| manager `handleSystemRebooted()` | NOP calls PCs333..335 and337..339 | Remove initial encrypted-SP/entry-retrieval recovery ingress; retain original reboot state and listener handling |
| manager `checkRpmbWhenReboot()` | Return at entry, preserving remaining bytes | Stop optional retrieval scheduling at the common destination used by initial and retry callers |
| manager `checkRpmbWhenRebootWithSP()` | Return at entry, preserving remaining bytes | Stop optional encrypted-SP retrieval **before** its warm-CE shortcut can call `checkLockPatternSuccess` |
| manager `access$checkFromLockPatternChecker(manager,String)` | Return/NOP over first instruction | Stop optional recovered-entry verification/Runnable creation and retry ingress; genuine entered-credential checker is a different path |
| manager `access$checkFormSyntheticPasswordManager(manager,byte[])` | Return/NOP over first instruction | Stop optional SP decryption, retry scheduling and SP-backed CE-unlock Runnable creation |
| reboot callback `onChecked(String,boolean)` | Return/NOP over first instruction | Stop recovered-entry forwarding and failure retry-message100 publication |
| reboot callback `onChecked(boolean,byte[])` | Return/NOP over first instruction | Stop recovered-SP forwarding and failure retry-message100 publication |

These entry guards disable **optional void work**. They do not return an
authentication result, invent a HAT/SP, mark credentials verified or acknowledge
a hardware transaction. Remaining unreachable helper code is not described as
deleted. No live buffer release, unregister or cancellation is implied.

## Source closure and preserved behavior

The reused construction-frontend proofs establish that original `init` registers
an OPPO password-changed callback unconditionally. That callback clears the
PIN-length cache **before** its feature check, then can encrypt supplied SP and
persist it through the optional TEE/RoR channel. Merely forcing feature=false
would still permit unnecessary SP delivery. This leaf removes registration.

An actual whole-APK direct-reference scan finds 233 manager references. The
optional `keyStoreManager` field has only constructor write and SP-recovery read;
`passwordChangedCallback` only constructor write and removed init read;
`syntheticPasswordManager` only constructor write, removed init read and its
synthetic accessor. The accessor's only direct caller is the SP-recovery
Runnable, whose construction is behind the guarded SP-recovery entry. These
bounded cold-source facts justify the optional allocation cut. They are not a
claim about reflection, JNI, malicious privileged processes or other profiles.

The complementary exact **nested Runnable type** scan independently closes that
allocation edge: twelve references, with only one `NEW_INSTANCE`, in guarded
`access$checkFormSyntheticPasswordManager` at PC197. The existing Object
initialization is PC199; no separate nested-constructor reference is invented.
No other donor class allocates it in this scan. Its reused actual `run` body
calls `access$clearPendingLockCheck` at PC2 **before** the SP-manager accessor at
PC7. That helper cancels and clears `mPendingLockCheck`. Thus an already queued
Runnable can affect pending work before accessing the now-unused manager field;
the source entry guards are emphatically not a live-job drain.

Original monitor registration remains: direct
`KeyguardUpdateMonitor.registerCallback` at init PC35 and the alternate main
Handler post at PC53 are preserved. The shared `$init$1` Runnable's mandatory
registration/finish cases are untouched. Original `checkLockPatternSuccess`,
`handleKeyguardDone`, StrongAuth/state handling, first-unlock and genuine finish
methods remain byte-identical. The entire retry Handler remains unchanged,
including message101 verification-state handling. Initial/retry optional
destinations and their callback retry producers are blocked separately.

Reboot/verification flags are not cleared artificially. The retained source
completion path is `OplusKeyguardViewMediatorExImpl.onKeyguardExitFinished` ->
`handleKeyguardDone` at PC111. The latter calls `setIsSystemRebooted(false)` at
PC8; that unchanged helper writes both the reboot flag and
`sp_key_need_verify_on_sys_reboot` false before applying the preferences. This
provides a genuine post-exit clearing path independent of the optional RoR
callback. It does not prove Samsung-backed PIN/finish callback execution or
effective optional-feature/UI behavior on a device.

The genuine typed verifier, credential lifecycle, Samsung policy, app keys and
CE-storage authority are not implemented by this leaf. Ordinary entered-input
RPMB work and extra immutable input copies belong to the separate input leaf;
its edited owners are disjoint from these methods. Root must independently
validate any composition from the literal original APK and preserve the union
of both leaves' selection conditions.

## Actual PC verification

The producer uses the frozen authored DEX039 integrity helper without changing
it. It validates all nine input/output DEX extents, tables/data/map bounds,
SHA1 format signatures and Adler32 checksums. It locates actual encoded methods
and rejects another method overlapping/aliasing an edited instruction range.
Every non-instruction byte outside the required DEX integrity header bytes8..31
is unchanged. Original branch targets, register counts, try regions, handlers,
payloads and instructions outside the exact slices remain unchanged.

Actual dexlib-backed reads of source and output exit0. In the two selected
classes, exactly nine methods change and the other28 normalized bodies match.
The whole archive class count matches. Restoring all saved instruction slices
and resealing reproduces each original modified DEX byte for byte; applying the
cuts again reproduces each patched DEX byte for byte. All8,447 non-target ZIP
entry payloads remain byte-identical. Complete entry proofs are ignored output
metadata referenced by hash from the inventory.

The APK/ZIP is reserialized. Entry-payload equality is not equality of physical
ZIP encoding or APK signature blocks. DEX SHA1 is format integrity, not
authenticity. No APK signing acceptance, ART verification or runtime fault
campaign is claimed. Malformed-byte negative fixtures are unexecuted; the stated
checks are positive actual-byte decode/preservation/inverse proofs.

## Mandatory selection conditions

1. **Cold fresh process only.** No previous registered OPPO SP callback, queued
   recovery Runnable/Handler work or active legacy RoR job may survive. Replacing
   existing instances requires actual disconnect/drain ownership; this leaf
   supplies no hot teardown. In particular, an old SP Runnable can cancel and
   clear a pending lock check before its manager accessor.
2. **Keep genuine cache invalidation.** A real Samsung committed credential
   change must invalidate the ColorOS PIN-length/type caches for the same current
   user and authority generation before consumers resume. Removing the SP callback
   removes its incidental invalidation. That requirement is still open; never
   fabricate or export SP merely to trigger it.
3. **Preserve mandatory policy and data.** First-unlock, StrongAuth, additional
   factors, live user/readiness, current credentials, intended CE access and app
   key policy require the real authority. Unknown remains locked. Removing
   optional RoR must never imply `userPresent` or successful authentication.
4. **Compose only reviewed disjoint cuts.** The separate input/RPMB leaf and
   remaining authority/readiness bindings are still required for their respective
   claims. This leaf is not a complete adapted SystemUI or phone candidate.
