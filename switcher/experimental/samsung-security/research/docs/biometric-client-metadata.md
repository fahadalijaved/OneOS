# App-side biometric metadata and direct authority entry

**Source/API proposal only; no helper, converter, protocol implementation or
retarget binary.** The real ColorOS `BiometricPrompt` already retains the
original caller Context and has a narrow authenticate/cancel boundary. Capture
metadata there in the app process, then call a separately versioned Samsung
frontend directly. A privileged guest SystemServer forwarding hop would change
the native caller seen by Samsung. Client metadata is never caller attestation.

The [inventory](../inventory/biometric-client-metadata.json) pins 18 methods:
eight reused from the corrected prompt contract and ten newly selected bodies
in five bounded queries. The auditor verifies 49 source assertions with decimal
DEX code-unit PCs. `python -B tools/audit_biometric_client_metadata.py` checks the
saved receipts; `--collect` requests only named methods. No OEM/Android/native
code or phone operation was executed. These supplied-image facts do not identify
the currently installed OneOS patch.

## Actual Context and operation path

ColorOS `BiometricPrompt.Builder(Context)` stores its exact argument in
`mContext` at 18. It reads that Context's display at 24 and writes the common
PromptInfo display ID at 28. `build()` retains the same Context at 50 and passes
it through the synthetic constructor at 63. The real six-argument prompt
constructor stores it directly at 17, alongside the original fresh Binder token
at 8, original `BiometricPrompt$1` app receiver at 15, original PromptInfo and
button/fallback owners, and supplied `IAuthService` at 27. No application-Context
replacement or Activity unwrapping occurs on this path.

The public crypto entry reaches the private CryptoObject overload. That overload
stores the original object at 0, calls its real `getOpId()` at 4, and passes that
long to the original long-valued authenticate method at 17. The latter compares
the stored object's operation ID with the argument, retains original cancelled
and already-showing checks, and performs the original effective-prompt clone and
authenticator normalization for a nonzero operation. Do not construct another
CryptoObject, drop a nonzero operation ID or replace source normalization with a
new default policy.

Immediately before the captured ColorOS IAuth call, the original method loads:

| Original `authenticateInternal(long,...)` PC | Value |
| --- | --- |
| 113 | Existing `mService` |
| 115 | Original `mToken` |
| 117 | Original app receiver |
| 119 / 121 | Actual `mContext` / its `getPackageName()` |
| 125 / 127 | Exact operation ID / requested user |
| 129 | `IAuthService.authenticate(token,operationId,user,receiver,package,effectivePromptInfo)` |

The actual Context is still in register v0 at that call. The operation's long
result becomes the cancellation listener's request ID at 135. The corresponding
`cancelAuthentication(long)` loads the same prompt's service/token/Context,
obtains its package at 10 and invokes IAuth cancellation at 14. These are precise
retarget sites, not a requirement to replace the whole frontend. An added helper
argument changes DEX register/arity and instruction layout; a later producer must
prove branches, try ranges, wide words and untouched methods independently.

The Builder normally obtains `ServiceManager.getService("auth")` at 35 and wraps
it with IAuth `asInterface`, unless a service was already supplied. A private
route must explicitly cover admission of that supplied-service path too. Merely
renaming the global service or replacing its PromptInfo creator does not carry
the missing client Context metadata.

## Genuine Samsung metadata producer

The inherited Samsung `authenticateInternal` calls `semSetExtraInfo` on its
effective outgoing prompt at 107, before IAuth at 125. That exact producer:

- Queries its real `mContext.getDisplayId()` at 6. Only its actual Exception
  branch selects display 0 at 31; it then writes Sem display ID at 32.
- Tests that same Context with `instanceof Activity` at 37. A true result reads
  actual `Activity.getTaskId()` at 43 and writes Sem task ID at 47. Non-Activity
  returns without that write; a task-query Exception also performs no task write.

Therefore preserve separate outcomes: display value versus the actual source
exception fallback; Activity task value versus non-Activity/no-write versus
task-query exception/no-write. A ContextWrapper around an Activity is not made
an Activity by this source test. Do not unwrap it, infer a task from PID, obtain
the server's display, or label zero as a successfully queried task.

The common PromptInfo display value was produced at Builder construction; the
Sem display is queried again at authentication. They are separate source values,
and one must not overwrite the other. The corrected prompt card's fresh ordinary
non-Sem profile supplies the absence basis for Sem type/privilege/challenge only
on its admitted source path. It does not authorize clearing an existing Sem
request or other security fields. For a fresh ordinary target object, a no-write
task outcome preserves real constructor initialization, not a claimed task ID.

## Proposed private protocol and source cuts

For root API review, use a unique endpoint and descriptor such as
`com.appleexploit.oneos.security.v1.IBiometricClientFrontend`. This is a proposed
namespace, with no published endpoint or assigned transaction numbers here.
Version and profile are explicit and length/framing bounded. Do not modify the
global PromptInfo layout or append Sem fields to a stock IAuth parcel.

| Proposed operation | Required content and result |
| --- | --- |
| Authenticate V1 | Original token Binder, operation long, real requested user/package, original app receiver Binder; complete effective common prompt payload under the reviewed schema; separate display/task producer outcomes; returns only the genuine authority's request ID |
| Cancel V1 | The same admitted frontend/session binding, original token/package and genuine returned request ID; invokes original Samsung cancellation policy |

The app-side helper must execute in the calling app, retaining a per-request
binding to the same admitted endpoint/authority epoch. It receives the actual
Context at authenticate PC129 and pairs cancellation PC14 with that binding.
Locally it also needs the original CancellationSignal (v19 in this captured
method) and prompt-owned request state; the existing IAuth argument list carries
neither. A bare invoke-target swap cannot implement that handoff. Context and
CancellationSignal stay in the client and are not serialized as remote owners.
A private prompt-owned state cell avoids recovering a current global session;
its acquisition, callbacks, release and endpoint-death behavior remain to be
implemented and reviewed. It must not move authentication through guest SS,
clear Binder identity, substitute caller UID/PID fields or silently retry against
a different authority after an uncertain call.

The private payload must preserve all real common prompt security values,
including confirmation, authenticators, fallback/profile/Identity Check and
background/enrollment behavior. Nested admission remains conditional: in
particular IdentityCheckInfo's clear-fallback/double-auth fields depend on the
actual flag profiles. Encode admitted semantics/presence explicitly; do not
replay a foreign parcel with an unknown flag layout. Unsupported populated
payloads require an explicit unsupported result, not silent field loss. The
same applies to real app callback Binder schema and executor ownership, which
the prior prompt report leaves open. This is not whole-app compatibility.

The Samsung frontend must construct the genuine target-side prompt and call
the admitted original `AuthService$AuthServiceImpl.authenticate` directly on the
same native Binder entry thread before any identity clear or post. The selected
source obtains native calling user/UID/PID at 62/66/70, applies permissions,
AppOps at 113, foreground policy at 135 and original internal/advanced/Sem
permission checks, then clears identity at 236 and calls genuine BiometricService
at 259. Preserve this ordering; directly entering BiometricService would skip
those gates. A Java method call alone is not native-identity proof: real Binder,
Context/permission/package/user/foreground owners and source object/code/loader
admission are still mandatory.

The selected AuthService body does not directly query Sem display/task fields.
That bounded absence does not establish all downstream validation. Display/task
values remain untrusted client claims produced by the helper, including when an
app supplies a custom Context. Actual server owners must establish applicable
task/display/user/caller admissibility before resource or policy effects. No
prepared client codec, class name, numeric metadata or `isSystemCaller` field is
an attestation of permission.

## Cancellation handoff that the patch must close

There is a concrete source-supported lost-cancel interleaving on a fresh prompt:

1. The original long authenticate method passes its cancellation check at 30.
2. Cancellation completes during the remote call at 129. `CancellationSignal`
   sets `mIsCanceled=true` at 8 while no new request listener is installed.
3. After the returned request is captured, `setOnCancelListener` at 140 sees the
   cancelled flag and synchronously invokes that listener (its own PC20).
4. `OnAuthenticationCancelListener.onCancel` tests `mIsPromptShowing` at 2/8 and
   can return at 15, because authenticate writes that flag only afterward at 144.

This is a conditional source interleaving, not an observed device failure. It
means an authenticate-call-only retarget cannot establish preserved cancellation.
Setting a UI-showing flag early would not prove a displayed UI or solve request
ownership.

The private route needs a request-pending cell and cancellation listener before
the remote operation, without a fabricated request ID. Cancellation latches
there; when the genuine ID arrives, it cancels that exact request using the same
retained endpoint/token/package. Replace the private route's post-reply listener
installation and showing-gated cancellation decision with that explicit handoff;
keep original UI state and client callback behavior as their separate contracts.
Retain owners across synchronous callbacks, cancellation/return races, failure
after possible admission and late terminal callbacks. A cancellation return does
not acknowledge native or callback drain. A transport exception with unknown
server commit cannot become local success, a guessed ID or a fresh retry.

The selected original Samsung cancel entry performs its actual permission check
at 37 before identity clear at 45 and original backend cancel at 53. The private
frontend must reach that real policy path with the original native caller; it
must not substitute an unconditional cancel success.

Before code, root must review the private protocol/profile, direct original
auth/cancel admission, client pending-request ownership and callback completion
contract. Later acceptance requires actual Binder UID/PID/user evidence and the
same protected native crypto operation, plus cancellation during the remote call,
reply/listener installation and UI replacement. Confirmation/additional-factor,
StrongAuth, original ColorOS presentation, UDFPS and the full GOAL remain intact
and unaccepted by this static proposal.
