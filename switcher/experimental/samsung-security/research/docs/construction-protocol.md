# Credential protocol construction boundary

This is a bounded static closure of the PIN/readiness/policy transport needed by
the selected native ColorOS frontend and Settings. It is not an implemented
adapter, complete service construction, installed-image identity or Android
acceptance. GOAL.md governs: inherited OneOS platform limitations are disclosed;
global SELinux Enforcing is not a new prerequisite. Genuine feature admission,
Samsung policy, secret protection and fail-closed behavior remain mandatory.

Reproduce the derived report with `python -B tools/audit_credential_protocol.py`.
`--collect` rereads the stream's fixed exact queries using the existing reader;
it requires the locally provisioned inherited proof receipts. Raw OEM bodies
remain ignored in `firmware/construction-protocol/`. The
[inventory](../inventory/construction-protocol.json) pins archives, reader tools,
raw proofs, exact descriptors, argument provenance, service permission/identity
edges and the prior actual Stub dispatch proofs. No OEM code executes.

## Actual reached surface and typed mapping

Observed actual-body scans find 395 Settings references to `LockPatternUtils`
(322 method, 72 type and one field), zero direct Settings `ILockSettings` calls,
310 SystemUI references to `LockPatternUtils` (217 method and 93 type), and three
direct SystemUI `ILockSettings` calls. These are instruction-reference counts,
not distinct workflows or completion counts.
Settings is the original donor APK SHA256
`33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b`.
The framework, services and SystemUI hashes are recorded in the inventory.

The selected bounded protocol has **33 common operations**. Each has identical
guest/host method descriptor, actual Proxy payload argument provenance and
Parcel IO ordering, with its own different transaction number. An authored
negative swap of the real setter's new/previous credential provenance is rejected.
This is stronger than declaration matching; it is not a hardware or runtime test.
The inventory gives every full descriptor, parameter/result type and body proof.

| Operations | ColorOS -> Samsung transaction | Required meaning |
|---|---|---|
| `getCredentialType`, `hasSecureLockScreen` | 15->59, 50->94 | Real user credential type versus service capability; neither an unavailable default nor proof of readiness |
| `getPinLength`, `refreshStoredPinLength` | 16->60, 17->61 | Actual PIN metadata; refresh can write/sync the protector state |
| `prepareToVerifyCredential`, `checkCredential` | 9->53, 10->54 | Real preparation; credential/user/progress -> complete response, not Boolean success |
| `verifyCredential`, `verifyTiedProfileChallenge` | 11->55, 12->56 | Real credential, user and reviewed flags; tied-profile semantics require the actual relationship |
| `verifyGatekeeperPasswordHandle`, `removeGatekeeperPasswordHandle` | 13->57, 14->58 | Same live authority's owned temporary handle, actual consuming challenge and selected user; exact release |
| `setLockCredential` | 7->51 | New credential, previous credential and real user -> actual committed result; covers NONE creation/removal under original policy |
| `getLockoutEndTime`, `getStrongAuthForUser` | 30->74, 28->72 | Actual elapsed-time deadline and genuine current StrongAuth flags |
| `registerStrongAuthTracker`, `unregisterStrongAuthTracker` | 21->65, 22->66 | Same live Binder tracker, initial state applied, bounded/drained callbacks |
| `requireStrongAuth`, `userPresent` | 23->67, 27->71 | Privileged original policy effects, never arbitrary frontend clearing/unlock signals |
| `reportSuccessfulBiometricUnlock`, `scheduleNonStrongBiometricIdleTimeout` | 24->68, 25->69 | Actual strong/non-strong event and owned user; preserve Samsung policy |
| `setSeparateProfileChallengeEnabled`, `isUseOneLockSettingEnabled` | 19->63, 20->64 | Original enabled state, old credential and profile ownership |
| `removeCachedUnifiedChallenge`, `tryUnlockWithCachedUnifiedChallenge` | 52->96, 51->95 | Actual profile cache owner; no guest unlocked-cache substitution |
| `getHashFactor`, `hasPendingEscrowToken` | 18->62, 29->73 | Secret history factor remains on device; authoritative escrow state is not activation authority |
| `unlockUserKeyIfUnsecured`, `resetKeyStore` | 59->103, 8->52 | Original secure-state/lifecycle checks; key reset is destructive and separately admitted only when a required native workflow needs it |
| `getBoolean`, `getLong`, `getString` | 4->48, 5->49, 6->50 | Exact key/default/user semantics; narrow reached keys and purposes |
| `setBoolean`, `setLong`, `setString` | 1->45, 2->46, 3->47 | Real permission-checked writes; per-key OEM effects still differ |

Profile/escrow/reset rows are explicit conditional ownership requirements, not a
generic capability offered to the frontend. Unused OEM, key-recovery and remote
validation methods are outside this bounded mapping; no broad Samsung interface
is exposed because it shares a descriptor.

Selected credential wire order remains type, byte array, invalid-character flag,
unified-profile flag. Response wire order remains code, timeout seconds/nanos,
HAT, temporary handle. Both `ParcelDuration` writers/readers also use seconds and
nanos. Credential NONE/PIN/password constructors and the common reply predicates
are pinned. Preserve actual errors, duplicate/retry/too-short statuses and HATs;
never synthesize a handle or interpret a final failure as progress success.
`verifyCredential` flag1 requests the real temporary handle; other repair/recovery
flags require their own explicit reviewed admission. Native Settings' subsequent
handle verification is covered by the frontend stream.

## Caller checks and state semantics

Observed: ordinary credential/database/type/PIN/lockout/status/tracker methods
require `ACCESS_KEYGUARD_SECURE_STORAGE`, directly or through read/write/have/
database helpers. Samsung `checkCredential` performs its read check at PC0 before
clearing Binder identity at PC3. `verifyCredential` checks secure-storage or
`SET_AND_VERIFY_LOCKSCREEN_CREDENTIALS` at PC3/13 before clearing at PC27.
Samsung's public setter delegates to its real
`setLockCredentialWithIgnoreNotifyIfNeeded`: secure-storage or set-and-verify
permission, or `SET_INITIAL_LOCK` with an empty old credential, precedes identity
clearing. Preserve secure-lock, FRP, enterprise and old-credential policy as well.

Biometric-success reporting and non-strong idle scheduling require
`MANAGE_BIOMETRIC`. The original `hasSecureLockScreen` getter only returns the
initialized capability field; it contains no original caller permission check
and proves no user is credential-free. Each operation's inventory entry records
both original service bodies and their actual permission/identity edges.

The new frontend boundary must validate the kernel-authenticated ingress caller,
package, selected user/profile, authority generation, purpose and operation before
any thread hop or identity clearing. Preserve original checks as well; a later
Samsung service seeing a forwarding process's system UID is not proof that the
original caller was admitted. No generic metadata database access is implied.
Password-history factors, credentials, handles and HATs remain on device and
outside diagnostics/PC artifacts.

Observed semantic differences matter even with identical transport. Samsung's
lockout query may reconcile original DB deadlines before consulting its real
rate limiter. Refreshing PIN length can rewrite/sync password-data state.
Samsung `userPresent` performs its own StrongAuth effects; ColorOS's same method
calls a different original unlock helper. Invoke the selected real Samsung
semantics, not both incompatible backend implementations. DevicePolicyManager,
TrustManager, user/profile policy and ColorOS RPMB are separate reached contracts;
they are not silently satisfied by these 33 Binder mappings.

## Exact ColorOS-side adaptations required

**CP-01: preserve real postcommit truth.** Original
`LockPatternUtils.setLockCredential` body
`c6f0ba72dc78f9c351632cbd4a470d29d681ba50c7eade5c6952f3159923f069`
calls the real setter at PC30. False returns at PC37. Only after true, it calls
guest-only `setLockscreenPasswordType` at PC48; a RemoteException becomes a
RuntimeException at PC59. A naïve common-method bridge can commit the new PIN and
then report failure. Blind retry would be incorrect.

The helper has no direct Samsung method. Its actual ColorOS extension body
`51a8df5c4564605c91d3060a3acf5257fc1c0008cb49aa678634cd7210ba7ebc`
clears identity and writes **optional audit metadata** key
`lockscreen.password.type`, value `package_type_user_wallclock`. This is not
the required quality key `lockscreen.password_type`. Exact literal scans find no
Settings/SystemUI/framework consumers; oplus-services has only the producer and
`hookOnSystemReady` read/log consumer. That read value only enters the log. The
same hook also has independent timeout work, so removing the whole hook is wrong.

Under the user's latest adaptation/removal scope, the narrow proposed leaf
removes only LPU PCs38..51 and excludes/removes the optional audit producer/log
consumer from the selected stack. Keep actual setter PC30, false PC37, true
PC52/53 and real error PC54..62. Do not import an OPPO backend or add Samsung
metadata writes solely to preserve this optional notification. Do not erase
required credential type, length, policy, storage or commit readback. Literal
scans are bounded archive evidence; dynamic/other-package consumers must remain
outside the claimed validated profile until checked.

The other guest-only interface method, `sanitizePassword`, is an actual empty
log-and-return body in this donor and has no directly reached Settings/SystemUI
caller in these scans. It needs no fabricated Samsung implementation. Exclude its
unused path or document this exact non-authentication behavior if later reached.

**CP-02: unavailable never means NONE.** ColorOS credential cache
`LockPatternUtils$1.apply(Integer)` body `04b5a5473b4c8c0c...` catches
`RemoteException` and returns boxed **-1** at PC27. `getActivePasswordQuality`
reaches this cached credential-type path. Add authority/user/generation readiness
before mode selection, reject stale cache generations, and block protected
presentation while unknown. Changing only Binder exceptions is insufficient:
this stock fallback consumes them. Never turn unavailable into None/swipe.

**CP-03: unavailable never means no lockout.** Lockout cache
`LockPatternUtils$2.apply(Integer)` body `e2bf187e88f264ab...` catches
`RemoteException` and returns **Duration.ZERO** at PC27. Preserve an explicit
unknown/locked admission state outside that fallback, invalidate/reacquire after
authority or user changes, and require actual current deadline before enabling
entry. StrongAuth and additional-factor readiness must likewise precede any
initial permissive cached default. These are source-backed patch requirements,
not implemented readiness/callback owners.

One Settings call references `setLockoutAttemptDeadline(II)J`, absent from the
captured LockPatternUtils class (whose superclass is Object). This is a bounded
additional archive/API mismatch, not a claim that the path runs or fails on the
phone. Identify that caller's actual reachability or adapt its policy contract
before claiming that exposed path supported; do not invent a lockout deadline.

**Present status:** 33 typed symbolic payload comparisons, 66 transaction-literal
checks, the old/new-credential negative and exact postcommit/fallback assertions
pass. Construction, effective installed API/profile, readiness owners, callbacks,
real PIN changes, app keys/CE storage and phone acceptance remain open.
