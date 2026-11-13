# Portable credential dispatch core

The authored portable core now implements the reviewed 33 credential transaction
routes. It forwards opaque request/reply objects synchronously through a supplied
call owner. This is transport implementation, not a Samsung credential service,
working Binder integration or authentication acceptance.

`CredentialRoutes.sourceCode(guestCode)` contains an explicit literal whitelist:
the 33 mappings in [construction-protocol](construction-protocol.md), including
credential check10->54, verification11->55 and setter7->51. Unsupported/OEM-only
methods return -1. The four original framework/services archive hashes are fixed
source-provenance constants. They do not attest a running backend, authorize an
arbitrary class/loader or broaden the supported device/profile. The production
core reads no JSON, filesystem, archive or moving build receipt.

The public API is:

```java
DirectCredentialDispatch<P>(DispatchAuthority<P> authority)
boolean handles(int guestCode)
boolean dispatch(int guestCode, P data, P reply, int flags,
                 int callerUid, int callerPid) throws Throwable
```

An unknown code returns false before packet validation or owner acquisition.
A selected code requires nonnull data/reply, refuses Binder ONEWAY bit1, and
preserves all other flag/caller bits. It obtains one nonnull `DispatchCall`, checks
its liveness, invokes the original dispatcher once with the same objects and
mapped code on the same thread, then checks liveness again before a normal
return. It closes the acquired call exactly once on success or failure.

The returned Boolean is **Binder handled**, never credential match. A source
false remains false. No credential, HAT, handle, policy value or response default
is fabricated. The core neither inspects packets nor copies, queues, logs or
stores them in fields. Its only instance field is the supplied authority. It
performs no reflection, identity clearing, thread hop, service startup or retry.

Guarded close preserves the exact primary check/invoke Throwable. A different
close failure is attached as suppressed when possible; the same instance is not
suppressed onto itself. If attachment itself is unavailable, the primary remains
the propagated failure. With no primary failure, close failure propagates and
prevents a normal handled return. This avoids Java try-with-resources'
self-suppression exception replacing an original failure. An exceptional invoke
does not run the post-success check or manufacture a replacement result.

Failure after original invocation—including retirement at the postcheck or
close failure—does not establish rollback. The original service may have written
a reply or committed a credential change. The real owner must reconcile that
uncertainty; this core never retries or restores old state automatically.

## Verification

The coordinated frozen build receipt is
`out/credential-transport/20261105T174349327541Z-fc071d2fd69f46c18753570c7d53870b/receipt.json`.
[The dispatch inventory](../inventory/credential-dispatch.json) pins it, the three
source/test files and the immutable reviewed protocol snapshot. Source and tool
hashes were verified before and after compilation/execution.

`CredentialDispatchTest` passed **1,161 assertions in 52 synthetic scenarios**.
It independently reads the hash-pinned authored protocol table and exercises all
33 actual route mappings. It also checks unknown-code refusal without an owner,
nonnull/ONEWAY admission, unchanged packet identity/caller/flags/thread, original
false handled status, one-shot invocation, retirement during acquisition/work/
postcheck, nested reentry, exact primary Throwable identity and distinct/same-
instance close failures. Opaque fixtures fail if hashed, compared or stringified.
The fixtures contain no credentials and implement no replica authentication.

The runner uses source8/target8, without the known failing JBR `--release8` path.
The coordinated Android wrappers also compile against SDK37 and D8 emits only
the 11 authored production definitions, excluding tests/SDK stubs. D8's existing
API37-unsupported/max36 diagnostic remains recorded. Source8 class emission and
D8 output do not establish Java8 API compatibility, ART/Binder/kernel-caller
behavior or original Samsung backend acceptance. Only authored JVM tests ran.

## Remaining authority boundary

`DispatchAuthority`/`DispatchCall` are supplied dependencies with no default
permission-granting implementation here. An actual integration must admit the
kernel-authenticated ingress caller, packet's requested user/profile, purpose,
authority generation and challenge/handle ownership; establish original source/
loader/resource/state/native identity; and preserve original Samsung policy.
Passing caller numbers or opening a lease is not proof of those facts. This
opaque core deliberately cannot parse or authenticate the requested user itself.

Actual cache-generation/readiness, protected unknown presentation, Settings
commit reconciliation, native background/callback drain and safe handoff remain
separate owners. Closing this synchronous call ends its lease, not the original
service or asynchronous/native work. Legitimate credential-free/lockout results
must come from the same current authority. No phone action, payload selection,
OEM execution or cross-OS PIN/fingerprint/key/CE acceptance follows from this
component build.
