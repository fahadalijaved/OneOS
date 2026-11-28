# Security guards in the acquired OneOS staged JARs

**Observed static result:** the staged OneOS 0.4.57 `x9u-in-sultra` bytes contain
all four bounded preservation-guard behaviors investigated here. They still
contain guest service construction, credential verification and fingerprint HAL
provider paths. These guards prevent selected mutations; they do not establish
a Samsung-authority integration or physical/native completion.

The [inventory](../inventory/installed-oneos-security-guards.json) pins the
acquisition, six original/staged archives, four upstream patch scripts, 50 exact
method records and 36 saved raw proofs. The acquisition is versionCode 74,
`coloros17-findx9u-in`, captured from the staged image through `/proc/1/root`.
Staged services/framework/oplus-services hashes begin `efb45f5f`, `5cb16a37`,
`a854468f`; original services is `66d0d51d`. The compared producer source is
OneOS commit `1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`. Producer comments are
intent evidence only. Neither producer execution nor the presence of staged
JARs establishes which implementation a live guest has loaded.

All PCs below are **decimal DEX code units in the staged method**, unless a
source PC is explicitly given. Exact descriptors, access flags, register counts,
physical DEX/header identities, body hashes, raw hashes and reader receipts are
in the inventory. This report contains derived metadata, not OEM method dumps.

| Guard family | Actual staged behavior | Preserved or unresolved frontier |
| --- | --- | --- |
| Gatekeeper | `LockSettingsService.setLockCredentialInternal(credential,credential,int,boolean)` and `setLockCredentialWithTokenInternalLocked(credential,long,byte[],int)` log at PC4, load false at7 and return at8. Original tails begin9; their catch ranges do not cover the prefix. All four direct `IGateKeeperService.enroll` calls become NOP plus a null response; three `clearSecureUserId` and one `reportDeviceSetupComplete` calls are absent and their captured sites are NOP. | Normal entry refuses credential changes. Three `verifyChallenge` and five `getSecureUserId` invokes remain, plus one `asBinder`. Authentication is not assumed read-only. A null enroll response is not a functioning credential-change implementation. |
| Weaver | `SyntheticPasswordManager.getWeaverServiceLocked():IWeaver` logs at4, loads null at7, returns8. Original getter/configuration tail begins9; prefix is outside its catches. | This proves the one getter's normal path. It does not prove every Weaver owner, cached reference or optional extension is isolated. |
| Vold user keys | The five original direct key calls—create, destroy, protect, unlock and lock CE storage—are absent from staged services. | Their surrounding Java wrappers still return or update state. Physical key protection, unlock and eviction cannot be inferred from them. Many other direct IVold operations remain. |
| Unknown biometric templates | `InternalCleanupClient.startCleanupUnknownHalTemplates()` clears its unknown-template list at2, calls `onClientFinished(this,true)` at15 and returns18; the old removal tail begins19. | This is a successful **skipped-cleanup callback**, not completed HAL reconciliation. Enumeration, sessions, authenticator-ID work and other enroll/remove paths are not shown stopped. |

The two setters and Weaver prefix have no branch into their retained tails on
normal prefix completion. Logging/callback exceptions are not successful results.
The four enroll replacements preserve the original response destination register:
`createLskfBasedProtector` source PC215 becomes staged NOP213/null214;
`newSidForUser` is NOP5/null6; `unlockLskfBasedProtector` NOP435/null436;
`verifyChallengeInternal` NOP49/null50. These are mutation omissions, not evidence
that all retained response-consuming/error paths recover usefully.

## Java completion is not native completion

In staged `StorageManagerService$StorageManagerInternalImpl`:

* `createUserStorageKeys(IZ)V` still appends the user to `mCeUnlockedUsers` at17;
  `destroyUserStorageKeys(I)V` still removes it at17. Their native key calls are
  absent.
* `setCeStorageProtection(I[B)V` reaches a GOTO at6 to its return at11 after
  obtaining the Vold field. No protect invocation occurs.
* `unlockCeStorage(I[B)V` retains the FBE branch and a GOTO at12 to17, then
  appends the user to the watched unlocked-user cache at28 and returns32.
  This is the original guest **two-argument** wrapper, not Samsung's three-argument
  HAT/secret contract.

Outer `StorageManagerService.lockCeStorage(I)V` retains permission, headless/system
user and already-locked checks. Its Vold call site is NOP59; it still removes the
user from `mCeUnlockedUsers` at65. Normal return cannot attest native CE eviction.

Guest `LockSettingsService.lockUser(I)V` is body-identical to the original: it
calls `IStorageManager.lockCeStorage` at30, conditionally calls its own
`lockKeystore` at40, requests StrongAuth at49 and clears cached metrics at55.
Its `LocalService.lockUser` body is also unchanged; the staged Nest bridge calls
the original method. Staged `lockKeystore` still invokes
`KeyStoreAuthorization.onUserStorageLocked(I)I` at2. Its wrapper/native effect and
the actual controlling flag are not established here. A caller's later
`keyEvicted` notification therefore cannot turn the omitted Vold call into a
physical-eviction acknowledgement. Actual staged CE getters, user lifecycle,
preparation, Trust and related wrappers are owned by the separate Power audit.

Corrected IVold owner scans contain **80 original / 63 staged reference records**:
two type checks each and **78 / 61 direct invokes**. No new caller/member site
appears. Five removed invokes are the key operations above; twelve others include
prepare/destroy user storage, partition/format/move, shutdown, checkpoint and
user-removal operations. This report does not ascribe all seventeen changes to
the five-call key guard. Remaining IVold operations include user start/stop,
mounts, reset, keyguard-state notifications and OEM sensitive-key operations;
their complete ownership is outside this bounded audit.

## Producers and consumers still present

Actual staged `SystemServer.startOtherServices(TimingsTraceAndSlog)` contains
these conditional startup sites:

| Staged edge | PC | Integration implication |
| --- | ---: | --- |
| Start guest `LockSettingsService$Lifecycle` | 1714 | Replace/suppress the genuine producer before constructor effects, not only after Binder publication. |
| Read `lock_settings`, apply guest `ILockSettings.Stub.asInterface` | 1720 / 1724 | An endpoint replacement must preserve the selected guest protocol and caller/user checks. |
| Start guest `FingerprintService`; cast result | 4399 / 4403 | A different result requires exact cast adaptation; merely skipping a call is insufficient. |
| Start guest `BiometricService` / `AuthService` | 4417 / 4432 | Registration/session producers require explicit ownership or replacement. |
| `LockSettingsInternal.onThirdPartyAppsStarted()` | 6537 | Guest-local lifecycle consumers still need a real owned local bridge. |

The staged LSS lifecycle `onStart` installs AndroidKeyStoreProvider, constructs
guest LSS at9, stores it and publishes `lock_settings` at19. Constructor effects
are not cancelled by preservation guards or by changing the global service name.
Presence of these sites is not proof of live branch values or runtime startup.
Earlier original-donor startup PCs are not substituted for these staged PCs.

Guest `FingerprintService.onStart()` and
`fingerprint.aidl.FingerprintProvider.getHalInstance()` are body-identical to
the original. Publication of `fingerprint`, HAL lookup/death handling and the
provider's cleanup scheduling at257 remain in the captured source. A cleanup
guard does not settle scheduler/native work or establish a sole backend owner.
No HAL getter was executed in this audit.

Original and staged framework `ILockSettings$Stub.onTransact(int,Parcel,Parcel,int)`
are body-identical: public, 569 instructions, zero catch records, classes6.dex,
logical header0, body hash `73fee992794c386d1592c64fec17505e472904606f605cd89bd7149fcab44dce`.
The public LSS credential setter body is also unchanged, while its internal
callee now refuses changes. This is selected dispatch equality, not proof that
all 33 backend routes, Proxy implementation or an installed adapter are equal.

The bounded staged `oplus-services` owner scans find zero Gatekeeper invokes,
one Weaver `getConfig` invoke, and eighteen IVold invokes, none of the five key
operations. The unchanged `SyntheticPasswordManagerExtImpl.triggerChannelOpen()`
gets Weaver from its wrapper at6, takes the non-null branch at12 and calls
`getConfig` at21. Its null path returns. This is not a demonstrated bypass of the
guarded getter: the concrete wrapper supplier/cache/lifetime was not closed.
Optional OPPO removal must include such producers/callbacks when unsupported;
reflection, JNI, other protocols and all remaining extension behavior were not
inventoried here.

## Required replacement boundary and verification

**Inference for the proposed integration:** keep the existing preservation
guards until an equally strong owned replacement exists. A sole Samsung
authority requires guest LSS producer/lifecycle replacement before construction,
the genuine guest-local lifecycle bridge, selected protocol routing, explicit
FP/Biometric/Auth producer ownership and real native/state completion. Required
StrongAuth, finish-factor, user and key policies must remain genuine. Do not
remove guards to make the guest setters succeed, interpret cache/status as
native completion, or treat the retained verification paths as harmless probes.
Cached Binder/local references and already-issued asynchronous/native work need
the separately documented admission/drain contract.

The authored [auditor](../tools/audit_installed_oneos_security_guards.py) rechecks
archive/source/collection hashes, saved reader receipts/raw files, all selected
method metadata and 32 bounded assertions. It imports no project implementation
and executes no producer, reader, OEM code, service or device command:

```text
python tools/audit_installed_oneos_security_guards.py
```

Two initial `IVold;->` prefix-selector queries are retained as excluded query
records: that API uses exact member matching, so their zero results are not
absence evidence. Corrected owner scans provide the findings above. No guards
were removed, no JAR was rebuilt, and no runtime/security case is accepted.
