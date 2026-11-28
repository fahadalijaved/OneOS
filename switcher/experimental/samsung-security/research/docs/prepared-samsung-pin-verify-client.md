# Prepared remote existing-PIN client

This unselected source component implements one remote Samsung operation. It is
not a guest LockSettings producer, canonical service replacement, authority
attestation or a device-tested integration. No OEM/SDK implementation ran while
preparing it. Compilation and independent source review are pending.

`PreparedSamsungPinVerifyClient.prepare(IBinder,int)` retains an already admitted
genuine Samsung endpoint and one physical PIN subject. `verifyCredential` accepts
the borrowed genuine guest `LockscreenCredential`, requested user and flags.
Only flags zero, an exact PIN object and the bound user are accepted. Both the
local process UID and actual Binder calling UID must equal 1000 before any
request is written. A supplied Binder, integer, loader match or successful
preparation does not establish source identity, user mapping, live custody or
authority generation. Bootstrap must establish and retain those real owners.
Existing retained captures have main-thread checks and no remote endpoint/user
entry API; this component invents no replacement readiness callback.

The concrete native Settings path is the original `ConfirmLockPasswordFragment`:
`handleNext` creates a PIN at PC24, and its internal `mForceVerifyPath` branch
calls `startVerifyPassword` at PC134 with flags zero. The separate PC118 branch
requests a temporary Gatekeeper handle using flags one and is excluded here.
`startVerifyPassword` chooses ordinary verification only when effective and
requested users agree; tied-profile verification is a separate operation.
These Settings bodies and its `android.uid.system` manifest are pinned original
donor evidence, not proof of an installed Settings process's kernel UID. The
client enforces the actual numeric UID condition at invocation and refuses other
principals. It does not distinguish packages sharing UID1000.

The actual staged guest framework `5cb16a37…` Proxy body is identical to the
reviewed donor body `86bd6ddf…`: transaction11, sensitive request, descriptor
`com.android.internal.widget.ILockSettings`, typed credential, user, flags,
synchronous native transaction flags32, real `readException` and typed response.
The staged credential writer `47542d19…` and response reader `19152432…` also
match their earlier reviewed bodies. The client freshly writes that same request
to Samsung transaction55. The original writer encodes type, secret bytes,
invalid-character and unified-profile booleans. The original response reader
preserves code, timeout seconds/nanos, HAT and password handle. No result bits,
timeout, HAT or handle are fabricated, logged, stripped or converted to success.

That is the client's Java call contract. The actual staged BinderProxy first
calls its extension's `overrideFlags` at PC11 and `transact` at PC29; a true
extension result returns at PC35 before `transactNative` at PC231. Consequently,
the Java call alone does not prove native transaction55/flags32 or remote entry.
The active extension and genuine backend path are an explicit admission frontier;
this component neither bypasses that canonical machinery nor treats interception
as proof of a genuine service result.

Samsung's original `verifyCredential` checks its two genuine permissions before
its own identity clear at PC27. Its original PermissionManager returns granted
for appId1000 before consulting its cache/AM. A remote hop changes the PID to
the guest process; it does not preserve arbitrary original app identities.
Under this explicitly narrow same-UID1000 profile, those selected permission
checks depend on the same principal, with no claimed PID preservation. The
client never clears identity or transmits a caller UID as authority. Genuine
Samsung user/FRP/enterprise, protector, rate-limit, StrongAuth, additional-factor,
keystore and CE effects stay in the original service. Verification itself can
produce effects even when its reply is lost.

This operation has no caller-supplied consuming challenge. The original Samsung
SPM `verifyChallenge(GateKeeper,SyntheticPassword,user)` explicitly supplies
challenge zero at PC9 to its real verifier at PC14. Flags-one handle issuance,
`verifyGatekeeperPasswordHandle` with an enrollment challenge, app cryptographic
operations and profile/recovery paths remain separate required work. A matched
response alone is not permission to dismiss keyguard or skip additional factors.

Both Parcels are owned by the client; the credential is borrowed, not retained or
zeroized by it. The request is covered before the second obtain, marked sensitive,
and both owned Parcels are recycled once even after failure. Exact primary
Throwable identity survives cleanup, self-suppression and suppression failure.
An unhandled transaction, missing response, decode error or cleanup failure
throws; none becomes an error/success response or automatic retry. The real
exception decoder runs once, with its original AppOps/StrictMode behavior.
The client makes no claim to bound that decoder's native/serialization behavior.
The caller must keep its borrowed PIN unchanged and unzeroized through the real
writer; the initial `isPin` check is not a concurrent ownership lease.

`prepare` checks canonical guest widget/Parcel/Binder defining-loader consistency
and caches the genuine response CREATOR. Reading CREATOR can initialize the real
response class: its staged initializer constructs OK, OTHER_ERROR and the original
creator. This is future original execution, not initialized-only capture.
Per-call `isPin` also retains the original zeroized-credential guard. These class
checks are placement constraints, never code authentication.

Root approved compiler-only canonical Parcel `markSensitive` and exact widget
ABI projections because public SDK37 omits this original public-final method.
Projections must be pinned to the captured declarations, excluded from all
production definitions and never executed. ART/BOOT/hidden-API access remains a
runtime admission requirement. No reflective or global hidden-API fallback is
present.

The existing 33-route `OriginalStubInvoker` is co-resident and is not used here.
The actual staged future producer seam remains SystemServer's class literal at
PC1712 before `startService`1714. A real replacement must provide both guest
Binder and all required guest-local behavior before onStart returns, own guest
`systemReady` and phases, and handle fail-soft early consumers. This private
client does not satisfy that gate or publish under `lock_settings`. In particular,
it must not replay the retained host's already completed startup lifecycle.
