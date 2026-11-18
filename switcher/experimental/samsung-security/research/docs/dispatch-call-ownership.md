# Synchronous dispatch-call ownership

`ManagedDispatchAuthority<P>` is an authored lifetime component. It retains the
provided `PreparedDispatch<P>` and opaque anchor strongly, and requires a nonnull
trusted admission callback. It is **not an authentication authority**, source
identity proof, prepared-service factory, user-policy implementation or native
drain acknowledgement. Its constructor does not admit an original source, state,
user, resource, key namespace or hardware backend.

```java
new ManagedDispatchAuthority<P>(prepared, anchor, trustedAdmission);
// trustedAdmission.validate(guestCode, sourceCode, callerUid, callerPid, flags)
// must throw on refusal or uncertainty. No default implementation is supplied.
```

Only the trusted integration supplies these dependencies. This is an ordinary
Java component API, not a public IPC endpoint or a caller-provided readiness
boolean. The actual Binder wrapper must capture the real UID/PID and select the
reviewed route. TrustedAdmission governs that transport boundary; it does not
replace validation of a payload's user/profile, credential operation, challenge,
session, policy or authorization at the actual security owner.
The generic owner does not implement the production transaction allowlist or
ONEWAY rejection. Those gates belong to the reviewed production dispatcher;
this owner alone is not a safe IPC frontend or router.

## Call contract

`open` reserves an opening stack, validates externally without holding the owner
lock, then rechecks retirement before publishing a call and incrementing its
synchronous lease count. Failed validation, retirement or allocation unwinds the
opening reservation without publishing a call. Calls capture only owner/thread/
generation identity and route/caller/flag scalars. Each owner has a distinct
private generation identity and cannot be reopened after retirement.

`checkLive` requires the creating thread, an open published token, an active owner
and no active same-call admission/invocation stack. It validates the captured
scalars again and rechecks local lifetime state after the external callback.
Checks may repeat before or after invocation; they are not a policy-ready latch.

The first `invoke` attempt consumes that token's invocation permission, including
a mismatched route/flags or a thrown admission. The exact captured source code
and flags are required. Fresh admission and the local post-admission check precede
one synchronous call to the exact retained dispatcher on the creating thread.
The supplied data/reply objects pass through unchanged; neither owner nor token
stores, copies, queues or logs them. Original boolean results and thrown Throwable
instances propagate without translation. The supplied dispatcher remains
responsible for its own actual data processing and lifetime contracts.

Same-call reentrant check/invoke/close is refused while an admission or invocation
stack is active. Independent nested or concurrent calls require their own tokens
and fresh admission. Admission runs outside the lock, so it can retire the owner;
the post-callback check prevents that reentry from publishing or invoking through
the retired owner.

`close` is creating-thread-only and idempotent after successful closure. It
decrements exactly one synchronous call lease. Wrong-thread or active-stack close
throws without ending that lease; closure may occur after the actual stack has
unwound. It calls no external cleanup and stores/rethrows no earlier failure.
Invocation/admission finally blocks only clear their own active-stack flags,
preserving the primary exception. A router that encounters an additional close
failure remains responsible for preserving/suppressing failures at its own boundary.

## Retirement and backend obligations

`retire()` is idempotent and can run on any thread. It stops new opens and live
checks/admission; it does not cancel admitted original work or wait for it.
Publication and the transition to an admitted invocation linearize under the
owner lock. A concurrent retire can occur after that transition but before the
first instruction of `PreparedDispatch.invoke`: that already-admitted synchronous
invocation may begin its original body **after retire returns** and may unwind
normally. No promise of “no backend call after retirement returns” is made.

A post-invocation live check can fail after original work has completed. In real
integration, that can be an uncertain committed mutation. It is not evidence of
rollback, safe enrollment retry or permission to release native/state owners.

Zero synchronous calls, successful close and retirement are **not** backend,
thread, callback, loader, Binder, cryptographic or native drain. This component
never closes/disposes the borrowed dispatcher or anchor and never clears those
references, even after retirement and zero calls. The integration's process owner
must retain this owner and its actual dependencies until their genuine completion
and recovery contracts permit release. Garbage collection is not a drain protocol.

## Verification scope

[The test](../compat/tests/ManagedDispatchAuthorityTest.java) uses authored Java
dispatch/admission fixtures and synthetic objects. It covers exact argument and
thread binding, a single invocation attempt, repeated close, failed admission,
primary Throwable identity, active-stack reentry, deterministic retirement during
open/check/invoke admission, two concurrent original stacks, and strong retention
of borrowed owners after the local count reaches zero. Reflection checks the
metadata-only token shape; it is not evidence about a genuine backend's behavior.

The build worker's coherent batch passed the owner suite's87 checks, verified
source/test pins before/after, compiled the full authored transport batch with
actual SDK37 wrappers and emitted its authored DEX definitions with isolation.
The existing D8 API37-unsupported/max36 warning remains recorded. Source8/target8
compilation does not claim release-API checking. These checks do not execute the
Android runtime. The worker owns `tools/test_credential_transport.py` and its
receipt under `out/credential-transport/20261105T174349327541Z-fc071d2fd69f46c18753570c7d53870b/`.
[The inventory](../inventory/dispatch-call-ownership.json) pins those inputs and
actual evidence. No Android/OEM class, Binder,
credential, user policy, JNI or hardware operation runs in these tests. There is
no runnable security authority, dispatch route selection or device acceptance in
this component alone.
