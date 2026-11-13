# Prepared permission-query reference binding

The authored `PermissionQueryBinding` component implements the root-approved
two-method API from [the source retarget proposal](permission-query-retarget.md).
It is compiled and tested as a separate, unselected component. No original
framework instruction, boot configuration, service lookup or permission cache
was changed. BOUND means **a local reference has been bound**, not authority,
permission, security readiness or authentication.

Public final class `com.appleexploit.oneos.security.boot.PermissionQueryBinding`
has `bindOnce(android.os.IBinder):void` and
`get():android.app.IActivityManager`. Its constructor, lock, state and stored
interface are private. It has no reset, replacement, retirement or global
ActivityManager API. Its source SHA256 is
`f0334b37063f80b6ca72247b948c4c020a213f4515e15c03ac5a0b6419677bb9`.

## One-shot publication and failure

bindOnce claims BINDING under its private lock before conversion, then releases
that lock before calling the original Samsung `IActivityManager.Stub.asInterface`.
Conversion may invoke external queryLocalInterface behavior. During conversion,
get and competing or reentrant bind attempts throw IllegalStateException. They
neither wait for conversion nor overwrite its state. If conversion succeeds,
the helper stores the exact returned interface and publishes volatile BOUND.
Readers acquire that state before returning the stored reference.

A null first argument fails with NullPointerException and makes the attempt
terminal. A null conversion result also fails terminally. A conversion's original
RuntimeException or Error is rethrown as the same object after publishing FAILED.
No further bind is allowed after BINDING, BOUND or FAILED. If an external converter
lets a reentrant failure escape, that failure terminates the outer attempt too.
No service fallback, retry, subject rewrite, identity clearing or permission
decision occurs in the helper.

## Actual build and bounded tests

`python -B tools/build_permission_query_binding.py` uses the existing pinned
SDK37/JDK/D8. An authored compiler-only declaration supplies the captured hidden
IActivityManager/Stub ABI under ignored out/. It is not executed and is excluded
from the helper class directory and DEX inputs. DEX inspection verifies exactly
one public final authored class, the two public static methods/private constructor,
private fields, volatile state and the bounded method references. Output DEX039
header, SHA1 signature and Adler32 checks pass. The actual D8 API37/max36 warning
is retained; compilation does not establish ART/API37 runtime acceptance.

Each subprocess uses its owned run directory, scoped TMP/TEMP and explicit JVM
temporary/home options. The runner removes inherited CLASSPATH,
JAVA_TOOL_OPTIONS, _JAVA_OPTIONS, JDK_JAVA_OPTIONS and JDK_JAVAC_OPTIONS from
its child environment; the parent environment is unchanged. This corrects the
initial runner's option-inheritance gap. The earlier builder, report, inventory
and freeze are saved under `out/permission-query-binding/history-initial-freeze/`;
their historical receipt remains at its original immutable run path. The
corrected successor passes with deliberately invalid values injected into all
five variables in its Python launcher's environment; the bounded probe receipt
is `out/permission-query-binding/option-environment-probe.json`. Helper/API/model
sources and the nine scenarios remain unchanged.

The SDK-compiled helper class bytes are held unchanged through D8 and nine JVM
scenarios with 42 checks. These tests use separately authored boundary models;
their runtime classpath excludes SDK implementations, compiler-only API classes,
OEM archives and D8. Every scenario gets a fresh helper loader without reflection
into private state or a production reset API. The tests cover:

- Unbound reads, exact supplied Binder/conversion thread and returned view,
  repeated reads, post-bind rejection and publication to another thread.
- Null-first, null-conversion, RuntimeException and Error failures, preserving
  original throwable identity and refusing later reads/rebinds.
- Reentrant get/bind during conversion, including an uncaught reentrant failure.
- A competing thread finishing get/bind refusal while conversion is still
  running, exposing a lock held across the external boundary.
- A latch-held conversion with concurrent unready reads/binds and publication
  only after conversion completes.

These are tests of authored helper behavior, not execution of the Samsung Stub,
Binder native identity, an Android loader, or an admitted security endpoint. A
test interface's shape or identity is not treated as authority attestation.
Inventory records the exact run handle, logs and final class/DEX hashes.

## Selection conditions remain external

Real bootstrap must supply the exact sourceProtocolBinder of the admitted frozen
PreparedSamsungPermissionBridge, with the actual current guest AM/state generation
retained. The public bind API, IBinder type, descriptor, UID or arbitrary same-name
class cannot authenticate that ownership. The helper statically references only
the required Samsung interface family, canonical IBinder and Java exceptions;
it has no app-only bridge class dependency.

Actual BOOT visibility, shared Samsung IActivityManager identity, boot owner/order,
original PC0 retarget and DEX reference-table producer remain unselected. Cold or
quiesced same-realm original permission-cache preparation requires no earlier
in-flight query or stale accepted result. Existing appId shortcuts and real native
caller/feature role/user/operation checks remain. The helper does not disable the
cache or install a partial ActivityManager singleton.

The external owner must stop admission and drain original calls and nested work
before retiring the process and its real endpoint. An interface already returned
by get cannot be revoked through local state changes. No hot rebind, remote
completion, drain or full authority readiness follows from this prepared component.
