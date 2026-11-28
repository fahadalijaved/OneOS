# Caller authority and trust boundary

Offline investigation, November 5, 2026. **No candidate is authorized or working.**
The supplied Samsung services and framework contain usable original authentication
paths, but transplanting their classes does not transplant their caller trust,
user graph, resource identities or storage ownership. The current OneOS source
also deliberately weakens SELinux enforcement during takeover. Those facts must
be resolved before describing a guest service as a Samsung security authority.

## Evidence and reproducibility

Observed source facts below use selected OneOS055 commit
`2a5f41043b4a69399cae058bad213cdef7408e88`, the exact Samsung mounted services
archive SHA256 `def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6`,
Samsung framework `8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe`,
ColorOS services `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`
and ColorOS framework `d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2`.
The mounted Samsung view is not a certified stock partition image. Selected
OneOS055 is a 20-file source subset, not a verified installed guest image.

Run `python -B tools/audit_trust_policy.py` in this nested project. The authored
[inventory](../inventory/trust-policy.json) records input/source hashes, exact
method descriptors, logical DEX041 header offsets, normalized body hashes,
instruction PCs and ignored raw-proof paths. Forty-five selected method bodies
were read across 24 queries. All 166 LockSettings Stub dispatch cases and six
selected credential Proxy transactions independently match the extracted
transaction-name tables: **172 structural cross-checks passed**. This checks
actual method dispatch, not only declaration names. No OEM method was executed.

Raw DEX bodies and optional JADX views remain under ignored
`firmware/trust-policy/`. JADX failed to reconstruct Samsung
`setLockCredentialInternal`; no conclusion here relies on that reconstruction.
The exact DEX body reader supplies the stated method evidence.

## Binder contracts: same descriptor does not mean same service

| Contract | Samsung / ColorOS declared methods | Exact shared descriptors | Same transaction code and name |
|---|---:|---:|---:|
| `ILockSettings` | 104 / 62 | 60 | **0** |
| `IFingerprintService` | 86 / 43 | 43 | 43; Samsung adds 43 |
| `IAuthService` | 23 / 23 | 23 | 23 |
| `IBiometricService` | 21 / 20 | 20 | 20; Samsung adds `semGetPromptInfo` |

Observed: a ColorOS `checkCredential` Proxy transacts code 10, while Samsung's
Stub dispatches code 10 to `setCarrierLockEnabled(I)V`; Samsung credential
checking is code 54. ColorOS `verifyCredential` code 11 reaches Samsung's
`setLockCarrierPassword([BI)V`, while Samsung verification is code 55. The
different parcel layouts may reject some mismatches; rejection is not a safe
translation strategy. An unfiltered pass-through Binder must not be used.

The [ColorOS frontend audit](coloros-frontend.md) independently checks the actual
credential and response parcel writers/readers and the progress callback. Its
selected common path has matching serialized fields; Samsung's private
`mSecret` is not serialized. That is a bounded contract result, not compatibility
of every Parcelable, Samsung extension, fingerprint callback or request flag.
Matching fingerprint/AuthService code numbers alone do not certify these other
parcel layouts or their policy.

The following is a **candidate method boundary**, not an implemented binding or
permission grant. All users must be explicitly selected and tied to the real
Samsung user/protector owner; arbitrary user IDs and OEM-only extensions are
outside the initial boundary.

| Purpose | ColorOS -> Samsung transaction | Candidate authority restriction |
|---|---|---|
| Credential type | `getCredentialType` 15 -> 59 | Status only for the owned user; retain original permission checks |
| Strong-auth status | `getStrongAuthForUser` 28 -> 72 | Return actual Samsung policy; never synthesize permissive flags |
| Primary keypad check | `checkCredential` 10 -> 54 | Real current credential owner; original progress and final result remain distinct |
| Credential confirmation | `verifyCredential` 11 -> 55 | Explicit reviewed flags and purpose; verification itself can trigger state changes |
| Challenge-bound HAT | `verifyGatekeeperPasswordHandle` 13 -> 57 | Same live handle owner/user and actual consuming operation challenge; no general handle oracle |
| Handle release | `removeGatekeeperPasswordHandle` 14 -> 58 | Release only a handle acquired by this owned operation |
| Strong-auth observation | register/unregister tracker 21/22 -> 65/66 | Retained callback owner, exact token, disconnect/drain and real backend state |
| Keyguard fingerprint | authenticate/cancel 5/9 -> 5/9 | Exact request/token/caller/user/operationId; real scheduler, lockout and strong-auth gates |
| Enrollment status | fingerprint list/authenticator ID 17/26 -> 17/26 | Bounded owned-user observation; actual templates stay Samsung-owned |
| Future shared credential change | `setLockCredential` 7 -> 51 | Separate explicitly authorized migration/change design preserving old credential/protectors, rollback and return/reboot acceptance |

`requireStrongAuth` 23 -> 67, `userPresent` 27 -> 71, arbitrary settings writes,
escrow/recovery, password resets, fingerprint enroll/remove/removeAll,
challenge generation for enrollment and lockout-reset APIs are **not** granted
by the presentation boundary. Any original service-internal use needs its real
policy owner; presenting a UI is not authority to call these on demand. Shared
credential changes remain an end requirement, not a reason to bypass their
existing OneOS preservation guards.

## Original caller and user checks that must survive

Observed Samsung `LockSettingsService` behavior:

- `checkCredential` body `a17ca685272cb966...` calls `checkReadPermission` before
  clearing Binder identity. `checkReadPermission` and `checkWritePermission`
  enforce `ACCESS_KEYGUARD_SECURE_STORAGE` through the service's Context.
- `verifyCredential` body `cdc7297d767c7dad...` accepts
  `ACCESS_KEYGUARD_SECURE_STORAGE` or `SET_AND_VERIFY_LOCKSCREEN_CREDENTIALS`
  before clearing identity at PC27. The rejection helper really throws
  `SecurityException`: `Task$$ExternalSyntheticBUOutline0.m(String)` body
  `e424fcbcf4c58ec9...` is independently read, so JADX's following unreachable
  `return null` must not be mistaken for the denial contract.
- `setLockCredentialWithIgnoreNotifyIfNeeded` body `296f05dec951e8fa...` checks
  secure-lock capability and those permissions, with the special
  `SET_INITIAL_LOCK`/empty-old-credential case; it retains basic credential,
  FRP, tied-profile and enterprise handling. These are not UI-selectable bypasses.
- `doVerifyCredential` body `6e3eb8ea9b478d6f...` distinguishes actual user,
  virtual/enterprise, previous-credential, FRP and repair paths. It uses the real
  synthetic-password protector/rate limiter and requests strong auth on positive
  timeout. `onCredentialVerified` body `12044666c6274a38...` reaches actual
  keystore and CE-storage unlocks; secure-lock-device mode deliberately awaits
  its second factor before full strong-auth unlock. Replacing these effects
  with UI dismissal would lose policy and data/key semantics.

Observed Samsung `AuthService$AuthServiceImpl.authenticate` body
`1adba09941164ce6...` captures Binder UID/PID and calling user before identity is
cleared. A same-user call needs `USE_FINGERPRINT` or `USE_BIOMETRIC`; a different
user requires `USE_BIOMETRIC_INTERNAL`. It checks AppOps operation78, foreground,
nonnull request owners and PromptInfo test/internal/advanced/Samsung privileged
requirements. Only after these checks does it clear identity (PC236) and forward
the original operationId and user to `IBiometricService.authenticate` (PC259).
The internal BiometricService Stub independently enforces
`USE_BIOMETRIC_INTERNAL` with calling UID/PID.

Observed Samsung fingerprint `canUseFingerprint` body `dc092f0f3e7e8bd6...`
checks biometric permission, then admits fixed calling UID1000 or actual keyguard
identity; ordinary callers must also satisfy current-user/profile, AppOps78/55
and requested foreground policy. `SemUtils.isKeyguard` body
`e1dae1d16dbd3316...` requires **both** `USE_BIOMETRIC_INTERNAL` and the package
named by a component resource loaded with numeric ID17040392 (PC18), rather than
a name-only claim. `semAuthenticate` body `6b6144857a31a34f...` retains Samsung
strong-auth/encrypted/lockdown checks, privileged-attribute filtering, provider
selection and sensor-specific internal permission. No blanket permission,
system-UID or package-name substitution is acceptable proof of legitimate caller
authority.

Inference: copying these bodies into guest `system_server` changes what Context,
PermissionEnforcer, PackageManager, AppOps, ActivityManager/UserManager,
LocalServices and resource ID17040392 mean. Their original policies may now be
evaluated against guest grants, users and component values. A separate forwarding
process also changes Binder's observed caller to that process. It must validate
the actual ingress caller before privileged forwarding and preserve owned
operation/user identity without treating arbitrary parcelled UID claims as
kernel-authenticated identity. The intended endpoint cannot be a generic system
UID proxy for all Samsung security methods.

## Challenge and authentication-token routing

Observed `verifyGatekeeperPasswordHandle` body `d5e51fa41dea7de8...` checks secure
storage permission at PC0, retrieves the real temporary password from its own
`mGatekeeperPasswords`, returns `OTHER_ERROR` when absent, and invokes its own
SyntheticPasswordManager at PC44. Handle IDs are meaningful only with that live
service's map, user/protector storage and retained lifetime.

Observed `SyntheticPasswordManager.verifyChallengeInternal` body
`40107076d0689493...` calls real Gatekeeper `verifyChallenge` at PC22 with user,
challenge, retained handle and secret, examines response code, and places the
actual payload in the HAT response at PC41. It also has a
`getShouldReEnroll` branch (PC49) calling **real enroll** (PC56), persisting the
replacement handle and reverifying. Thus a verification path is not inherently
free of state mutation. OneOS's selected `guest_no_gatekeeper.py` leaves
verification calls but suppresses enroll calls; its comment describing verify
as read-only cannot establish mutation-free Samsung behavior.

Observed `BiometricService.handleAuthenticationSucceeded` body
`57ce607a05d07f4a...` resolves the current session/request (PC8), checks actual
sensor strength (PC50), and retains `mTokenEscrow` only on the strong-biometric
branch (PC81). `handleOnDismissed` body `e503650c970d3414...` resolves the current
request again and calls `KeyStoreAuthorization.addAuthToken` with the returned
credential attestation or retained biometric token (PC248/299). It can continue
after logging the token-installation return; a client success callback therefore
does not prove an authentication-bound key was authorized.

Missing runtime evidence: fresh real challenge/operationId binding, authenticated
HAT signature/SID/type/timestamp acceptance, native Keystore/KeyMint delegation,
replay rejection, expired/cancelled/wrong-user request rejection, and persistent
use of pre-existing authentication-bound app keys. A future acceptance experiment
must start from an operation that demonstrably refuses authorization, authenticate
the exact fresh operation through Samsung, then observe its real cryptographic
completion. An already unlocked timeout key, copied token, matching SID field,
successful Binder return or dismissed lockscreen cannot distinguish that result.
See the independent review and storage/key audit for the corresponding gates.

## OneOS preservation and global policy

Observed selected OneOS055 source:

- `guest_prepare.sh` lines301-312 mounts binderfs when absent and recursively
  binds `/dev`; `guest_start.sh` lines647-655 explicitly deals with a shared
  servicemanager, separate `gvld` name and permissive-only registration policy.
  Mount namespaces alone do not provide a separate security-service namespace.
- `oneos_switch.sh` line999 kills host `system_server`. A retained Samsung Java
  authority needs a concrete surviving/new lifetime owner; the unchanged switch
  cannot keep the previous LockSettings/BiometricService process alive.
- `oneos_switch.sh` lines614-624 deliberately executes global `setenforce 0`;
  `return_to_oneui.sh` lines749-751 restores recorded enforcing state and invokes
  failsafe on mismatch. This is source behavior, not proof of the current phone's
  state or a completed safe return. Source says guest system_server uses
  `u:r:system_server:s0` against Samsung policy. It does not create an isolated
  guest SELinux policy domain. Permissive MAC is not evidence that original
  permission checks or hardware cryptographic requirements passed.
- `oneos_switch.sh` lines750-751 sets `ro.control_privapp_permissions=log`.
  This is an additional allowlist/boot-policy relaxation; it must not be described
  as making platform signing certificates identical or granting every signature
  permission. Actual permission definitions/grants and signer ownership remain
  to be attested for the eventual candidate.
- Current producer invokes `guest_app_id_offset.py` and writes the `appid15000`
  marker. Current preparation rejects old low ordinary app UIDs only in its
  enabled/staged-GMS branch. The supplied older039 patch implementation pads
  new normal app allocation to15000; pre-existing package IDs, fixed system
  shared UIDs (including1000) and isolated UID space are not globally remapped.
  It mitigates ordinary keystore UID collision, not all shared-kernel authority.
- Current producer invokes the scoped `guest_sec_ims_signature.py` workaround;
  selected docs tie it to `com.sec.imsservice` and the staged read-only IMS path.
  The supplied older039 body also recognizes its `/system`-prefixed path form.
  That older body is not proof of the selected055 patch implementation or
  installed output. Neither form authorizes a general Samsung platform-signature
  bypass for authentication components.

The existing no-Weaver/no-Gatekeeper/no-biometric-cleanup/storage/keystore
maintenance/user guards must remain until a concretely owned replacement proves
equivalent preservation. Re-enabling foreign cleanup or writes merely because
Samsung classes now load would expose host enrollment/protector/key state before
its storage graph and user policy are established. Global permissive operation,
same UID1000, imported native daemons and matching Binder descriptors do not
collectively establish the required security boundary.

**Runtime status:** no Android startup, service replacement, caller grant,
credential verification, enrollment/key access, SELinux change or phone action
was performed by this investigation.
