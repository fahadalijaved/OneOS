# Binder direct-dispatch source constraints

The captured source supports a prepared reflective call to the genuine Samsung
`ILockSettings.Stub.onTransact` on the current Java stack. It does not establish
the incoming Android kernel caller identity, initialized service authority,
permission results, Parcel native provenance or runnable integration.
`inventory/binder-direct-dispatch-source.json` pins **75 bounded methods**,
declarations, exact code-unit reference PCs, catches and existing SDK37 shapes.
No OEM code, Binder native implementation or phone operation was executed.

Inputs are the captured Samsung framework `8095a9ae…` / services `def967fb…`
and original ColorOS framework `d5c6b7fd…` / services `66d0d51d…`. Samsung
services uses its complete DEX041 container, not rebased logical slices. Existing
trust-policy Stub and credential-protocol Proxy receipts are reused. Only missing
named Binder/Parcel/chain bodies were read; native implementations and the rest
of Binder infrastructure are outside this audit.

## Exact service chain and local-interface behavior

Both captured public `LockSettingsService` declarations directly extend
`com.android.internal.widget.ILockSettings$Stub`. **Neither declares
`onTransact`.** Each public abstract Stub directly extends canonical
`android.os.Binder` and declares public
`onTransact(int,Parcel,Parcel,int):boolean` (access `0x1`). Binder's base method
is protected (`0x4`). This pins the supplied classes, not arbitrary future
subclasses or an instance supplied under an unrelated loader.

Both Binder bodies for `attachInterface(IInterface,String)` consist only of
storing `mOwner` at PC0, `mDescriptor` at PC2 and return. There is no owner null
check or realization. `queryLocalInterface` returns the owner for a matching
nonnull descriptor, otherwise null. Thus `attachInterface(null,descriptor)`
can expose the descriptor while returning no local typed interface. Both actual
Stub `asInterface` methods query the local interface and construct their Proxy
when no suitable local interface is returned. Preserve canonical Binder and
Parcel identity; a same-name private copy is insufficient.

Reflect the exact selected signature once during preparation and retain its
actual declaring class/service/loader owner. These supplied Stub methods are
public, so their source shape does not require a protected-method accessibility
override. Runtime hidden-API/access restrictions remain untested. Reflection's
target exception must reach the real outer boundary as its original cause;
`InvocationTargetException`, refusal, false dispatch and service errors must
not become success or a fabricated reply.

## Entry boundary, cursors and identity

| Actual source path | Observed contract |
| --- | --- |
| Local `Binder.transact` on both captures | Public final; no catch. Set incoming data position zero at PC3, virtual `onTransact` at PC6, set reply position zero at PC12 **only on normal return**. It makes no explicit identity-clear call, thread hop or remote IPC in this Java body. Calling all `Binder.transact` paths identity-hopping would be incorrect; remote `IBinder`/native behavior is separate. |
| Direct Stub `onTransact` | Does not provide those cursor rewinds, a kernel entry, Binder wrapper observers or exception serialization. Both Stubs enforce the interface at PC10 for codes 1…0x00ffffff, then dispatch their different transaction tables. No dispatcher catch converts errors to a successful value. |
| Kernel-facing Java `execTransact` wrapper | Wraps native-pointer Parcels at PC0/4, checks RPC, reads native calling UID at PC17 on its applicable path, sets ThreadLocalWorkSource at PC27, then calls `execTransactInternal` (Samsung PC32, ColorOS PC36). It recycles/restores on normal and exceptional exits. These Java calls do not prove what the native pointers, caller identity or initial cursor actually were. |
| `execTransactInternal` | Samsung calls `onTransact` at PC35/48; ColorOS at PC48/63. Both wrap observer/AppOps work. ColorOS additionally reaches `IBinderStaticExt.onTransactStart`, `onTransactEnded` and `onTransactThrewException`; their semantics were not broadened into a separate audit. A direct nested call should not duplicate or claim to replace this existing outer wrapper. |

An **onTransact-entry helper**, as proposed by the frontend worker, should pass
the same untouched packet/cursor to the original Stub. It must not read the
token first and make the original Stub enforce it again at the argument cursor.
Do not add an internal rewind merely because a standalone `transact` method has
one. If another layer reads, clones or re-encodes a packet, that layer instead
owns explicit cursor/header preservation and reply normalization. This source
audit does not prove native entry cursor state or a runtime implementation.

Captured `getCallingUid()` / `getCallingPid()` are public static final **native**
(`0x119`), with no Java body to prove kernel behavior. `getCallingUidOrThrow`
also consults `isDirectlyHandlingTransaction` / `hasExplicitIdentity` before
reading UID. Preserving a Java Thread object or prohibiting an authored executor
hop does not prove these native conditions or original caller provenance.
No adapter identity clear/restore or synthesized caller UID/PID is justified.
Genuine service operations retain their original permission checks and their
own subsequent legitimate identity-clear/restore behavior.

## Parcel, common transactions and exceptions

Both native-interface-token wrappers delegate `writeInterfaceToken` to
`nativeWriteInterfaceToken` and `enforceInterface` to `nativeEnforceInterface`.
Do not infer token/native header semantics from a Java string alone. The original
Stub subsequently calls `enforceNoDataAvail` at individual argument boundaries;
the selected body rejects remaining data with `BadParcelableException` (Samsung
uses a pinned outline helper). Forwarding an unread canonical packet preserves
that check. The existing 33-operation protocol proof, rather than same-name
descriptors alone, governs which transaction numbers can be translated.

The actual guest `checkCredential` Proxy obtains its data Parcel with its Binder
at PC4, calls `markSensitive` PC8 and sends integer **flags 32** at PC34/36. A
filter accepting only flags zero would reject this real caller. This audit pins
that numeric value, not an unexamined field initializer. `markSensitive()` is a
public final captured method delegating to `nativeMarkSensitive`; it is **absent
from the public/protected SDK37 Parcel shape**, as is the public SDK symbol
`FLAG_CLEAR_BUF`. An untouched forwarding helper need not introduce any hidden
markSensitive call. If it creates replacement Parcels, sensitivity and transport
metadata need explicit captured-API/native ownership; skipping them is not a
proven substitute. Buffer erasure is not proved by the native wrapper declaration.

`readCallingWorkSourceUid` and `replaceCallingWorkSourceUid` likewise delegate to
native methods. WorkSource is accounting context, not an authenticated caller
credential. Preserve its source packet/outer lifecycle; never authorize from a
supplied work-source UID.

For `INTERFACE_TRANSACTION` (1598968902), the generated Stubs fall through to
Binder. Samsung Binder reads its descriptor at PC6 and writes **one String** at
PC10, returning true; ColorOS uses PC12/16 after register moves. No
`writeNoException` prefix belongs to this branch. Handle the frontend's own
descriptor locally and explicitly. Unrecognized transactions must not
accidentally expose Samsung extensions or inherited dump/shell operations.

The Stub itself serializes normal service results, including its normal
`writeNoException` calls. It does not catch service errors. Samsung's actual
`execTransactInternal` catches `RemoteException`/`RuntimeException`: the one-way
bit branches to logging/unhandled handling; synchronous error handling resets
reply size PC120 and cursor PC123 before `writeException` PC135. The ColorOS
outer wrapper has analogous handling plus its extension hook. Local
`Binder.transact` lacks that exception marshal and propagates the Java failure.
A direct helper must preserve which outer contract actually owns the call.

`Parcel.writeException` does not represent every Throwable. Its exception-code
selector handles specific canonical exception classes and admits Parcelable
exception serialization only under its actual class-loader comparison. Unknown
exceptions can rethrow/wrap rather than producing a valid reply. `readException`
also reads AppOps/StrictMode headers through `readExceptionCode` and throws the
decoded error. Do not prepend a second success header, swallow a target error,
or promise arbitrary private Samsung exceptions are wire-compatible. Fatal
Throwable cleanup is not the same as marshaling all Errors as service replies.

## SDK proof and remaining integration obligations

Existing `android-37.0/android.jar` was inspected using existing JBR `javap
-protected -s`. Its exact `Binder.onTransact` shape is protected boolean with
the four expected parameters and `throws android.os.RemoteException`.
`attachInterface`, `queryLocalInterface`, final `transact`, UID/PID and WorkSource
APIs are available. The inventory pins the SDK jar, javap binary, output hash and
selected descriptors. Captured DEX Throws annotations are not decoded by the
shared reader; do not invent a separate Stub throws-annotation proof.

The proposed direct frontend still needs genuine current service construction,
canonical/private class admission, real Binder caller/permission evidence,
selected-user/authority-generation and policy readiness, operation/callback
ownership, exact packet/flags behavior, and protected recovery on failure.
Static declarations and same-stack dispatch do not establish those conditions,
Samsung hardware acceptance or cross-OS security. Parent ColorGlass remains
paused; this audit changes no service, source payload or selected runtime.

Recheck existing receipts and input pins with
`python tools/audit_binder_direct_dispatch.py`. `--collect` regenerates only this
fixed named source/SDK query set. Raw source output stays in
`firmware/binder-direct-dispatch/`; SDK output and receipts stay in
`out/binder-direct-dispatch/`.
