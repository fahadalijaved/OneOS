# Unpublished credential Binder frontend

`LockSettingsBinderFrontend` and `OriginalStubInvoker` implement an **unselected
Android-facing library component**. They provide no APK, service publication,
backend construction, default authority or authentication result. A genuine
prepared authority and its startup/lifetime owner remain unassembled. The full
cross-OS acceptance matrix remains open.

## Implemented call boundary

The frontend extends canonical `android.os.Binder`. Its constructor accepts the
shared `DirectCredentialDispatch<Parcel>` and calls
`attachInterface(null, "com.android.internal.widget.ILockSettings")`. The null
owner prevents a local `IInterface` shortcut from bypassing transaction mapping.

`onTransact(int, Parcel, Parcel, int)` captures native `Binder.getCallingUid()`
and `getCallingPid()` before any dispatch. A selected code goes to the shared
dispatcher with those values, the same two Parcel references, original flags and
thread. An unselected code goes to `super.onTransact` with unchanged arguments.
The shared dispatcher owns the reviewed route map and per-call authority lease;
for example guest check code 10 maps to source 54. It rejects one-way calls while
preserving other flags, including the actual guest proxy's flag 32. A returned
boolean means the transaction was handled, not that a credential matched or
that policy permits completion.

`OriginalStubInvoker.prepare(Object, Class<?>, Class<?>)` receives an existing
backend and separately source-admitted service/Stub Class identities. It requires:

- The backend's exact runtime Class is the supplied service Class; an unexpected
  subclass cannot add an unnoticed override.
- The supplied Stub is a proper descendant of canonical Binder and an ancestor
  of that service. It declares the canonical
  `onTransact(int, android.os.Parcel, android.os.Parcel, int)` signature.
- Both the Stub entry and actual most-specific entry are concrete instance
  methods returning primitive boolean, with public or protected visibility.
- The most-specific declaring Class is one of the two supplied admitted
  identities. An intermediate override needs a separately extended admission
  contract; this component rejects it rather than silently choosing the Stub.

Preparation caches that actual Method and backend. It does not discover or load
classes by name. If protected/nonpublic access requires `setAccessible(true)`,
refusal fails preparation; there is no alternative dispatch or access bypass.
Invocation calls the cached Method directly on the same backend and thread,
without `IBinder.transact`, identity clearing, posting, parcel cloning, token
parsing, cursor changes or reply construction. The original dispatcher consumes
the token and typed arguments, applies its genuine permissions/policy and writes
its original reply. No Parcel or caller packet is stored by either adapter.

Reflection's `InvocationTargetException` is unwrapped to its actual cause.
`RemoteException`, `RuntimeException` and `Error` leave the frontend as the same
throwable object. A different checked Throwable becomes a `RemoteException` with
a constant diagnostic message and the original cause. This is an explicit
transport failure, not a matched result. Post-call admission or lease-close
failure does not establish rollback of a committed credential operation.

## Observed API/source facts

The source audit in `inventory/binder-direct-dispatch-source.json` records both
frameworks' Binder bodies and original service/Stub declarations. The existing
SDK37 public API has the used Binder/Parcel signatures; protected `onTransact`
declares `RemoteException`. Both captured `LockSettingsService` classes are public,
extend their original `ILockSettings$Stub` and declare no `onTransact` override.
Their public abstract Stub classes declare a public concrete dispatcher. Thus
this profile selects that genuine Stub entry, without skipping a service override.

Actual `attachInterface` stores its owner and descriptor with no null rejection.
Matching `queryLocalInterface` returns that owner, so a null owner returns null.
The common interface transaction writes the descriptor through Binder; it is
not a credential reply with a fabricated `writeNoException` prefix.

Actual **local** Binder `transact` rewinds data to zero, invokes `onTransact`,
then rewinds reply to zero only on normal return. This library starts at the
`onTransact` boundary, after the surrounding transport's entry preparation. It
must not invent a second rewind. Direct invocation alone is not a complete
`transact` implementation and does not normalize a hand-built Parcel at an
arbitrary cursor. Native/remote entry cursors and caller identity still require
runtime evidence. The SDK lacks public `Parcel.markSensitive`; this component
adds no hidden API call and preserves the actual incoming flags.

The captured remote-entry wrapper obtains Parcels from native pointers and
maintains work-source/outer exception handling; the guest wrapper also retains
its OEM transaction hooks. This helper recreates none of those boundaries.
Keeping an existing surrounding entry is distinct from proving its caller,
work-source, cursor or native identity on a running device.

## Required genuine owner and verification limits

Supplying Class identities and passing reflection shape checks **does not
authenticate code**. The external owner must admit the exact source code/loader,
backend, Context, initialized state, device/native profile and current generation;
retain them through real work/drain; enforce caller/user/profile and operation
policy; and issue each live authority lease. UID/PID values alone do not establish
package or user authorization, especially under the documented OneOS shared-UID
and permissive-platform limitations. Direct invokers must remain internal to that
admitted call path.

No synthetic `DispatchAuthority` is supplied. Original lockout, StrongAuth,
additional factors, credential confirmation, callbacks, CE/Keystore and app-key
policy must govern actual results. Original frontend finish/readiness and shared
Settings create/change/remove flows remain required. No original service or OEM
method was executed for this implementation. SDK compilation, authored model
checks and source auditing cannot prove native Binder provenance, permitted
reflection on the target, signing, installed-image identity, hardware behavior
or working cross-OS credentials.

The build worker owns the coherent SDK37 compile receipt. Its outcome is recorded
separately from source/API facts in `inventory/credential-binder-frontend.json`.
The frozen two sources compiled against the actual pinned SDK37, and D8 emitted
only eleven authored production definitions for the complete transport batch.
Both commands exited zero. D8's warning that API37 exceeds its supported maximum
of 36 remains a limitation. Only the separate pure-Java transport/lease models
executed; neither Android wrapper nor an original dispatcher ran.
