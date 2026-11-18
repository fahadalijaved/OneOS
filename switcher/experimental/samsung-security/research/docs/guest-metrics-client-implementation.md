# Prepared plain-header RAW guest-metrics client

The root-approved `PreparedGuestMetricsClient` API is implemented and compiled
as an **unselected prepared component**. It supports the explicit plain native
exception-header profile from the frozen
[API proposal](guest-metrics-client.md), not full AppOps/StrictMode header
compatibility or a complete live client. No original framework, BOOT selection,
Context, endpoint publication or guest producer was changed.

Source: `compat/android/com/appleexploit/oneos/security/boot/PreparedGuestMetricsClient.java`,
SHA256 `afd99ebe98a09b209bb7f6a42d23c9d88313597f5d6760105def73213ea625d1`.
`prepare(IBinder)` retains the exact nonnull supplied Binder without a lookup,
probe, callback or IPC. Supplying that object does not authenticate its source,
owner or epoch. `read(int):Snapshot` declares RemoteException and preserves
actual transaction/decoder faults; it performs no retry, cache, identity change
or worker hop. This route projects metadata under the original native caller's
display policy, not credentials or Samsung authority.

## Packet and Snapshot behavior

Each call obtains its own request and reply, writes the fixed v1 descriptor,
version1 and unchanged displayId, checks request size≤512 and calls transaction1
with flags0. A false transact result throws RemoteException before reply parsing.
Only a true result admits a reply size check:4..4096 bytes before any header read.
The client resets only its owned reply, peeks the native exception code, and
explicitly refuses AppOps−127 and StrictMode−128 as unsupported extended headers.
It does not strip headers, forge code0 or disable a platform policy.

Other codes go through genuine Parcel.readException. A nonzero code must throw;
an unexpected normal return becomes BadParcelableException. Code0 requires exact
remaining length12 or32, version1, exact display echo and status0/1. ABSENT must
have no payload; SAMPLE must have exactly the five fixed ints. Trailing,
truncated, mismatched or unsupported replies throw. None becomes absence,
default metrics or readiness. The cap is an accepted-packet byte bound, not a
proof of all native exception-parser allocations/effects.

Each successful read creates an own immutable nested Snapshot. displayId and
isPresent remain available; all five metric getters throw IllegalStateException
for ABSENT. SAMPLE exposes its exact signed ints and DPI bit patterns without
normalization or validity guesses. No guest Sample, DisplayInfo, loader-owned
Parcelable or live producer object crosses into this Snapshot. It does not
attest authority, freshness or final Samsung display metrics.

## Acquisition and cleanup

The first obtain is inside the protected try, before the second obtain. Every
successfully acquired owned Parcel is recycled once, reply then request, through
a guarded cleanup helper. Failure recycling one cannot skip the other attempt.
The original primary Throwable is preserved exactly; a same-instance cleanup
failure is not self-suppressed. Distinct cleanup failures are added as suppressed
when possible, with addSuppressed itself protected so recording failure cannot
replace the primary. Without an earlier primary, the first cleanup failure is
thrown and subsequent distinct cleanup failures can be suppressed onto it.

The private generic rethrow preserves the same Throwable, including a checked
failure, without a RuntimeException cast. A cleanup failure prevents an otherwise
successful return. No Parcel escapes the call; no borrowed Parcel is reset or
recycled. Source/bytecode review of the suppression-failure guard is distinct
from inducing an actual JDK addSuppressed allocation failure; no JDK hooks or
heap-exhaustion experiment is authorized or claimed.

## Actual bounded build

`python -B tools/build_guest_metrics_client.py` compiles only the pinned client
source against the existing SDK37 using source/target8. The explicit three-class
closure is client, Snapshot and its empty synthetic Java8 `$1` constructor-access
marker. The builder checks that marker has no fields, methods or interfaces,
reads actual javap output for constructor access, and verifies the unchanged
class bytes through D8. The output DEX039 contains exactly those definitions;
header, SHA1 signature and Adler32 verify. No SDK, model, endpoint or producer
definition is bundled. The actual D8 API37/max36 warning remains recorded.

The frozen build is
`out/guest-metrics-client/20261105T232440065288Z-3b563848b00248948d801abbf4add9ff`.
Its DEX SHA256 is
`ebd78551d0a59ecf45e4c2e44fd5b6945708c308a2f7c73731f7da2526b2668d`;
the separate unselected DEX JAR is
`388df0633a640cfe55eb3f108d029e58f1c6be68db39c87ee6e8cec1d8577adf`.
Exact class hashes, commands, diagnostics and input pins are in
[the implementation inventory](../inventory/guest-metrics-client-implementation.json).

Every child process uses an owned cwd, TMP/TEMP and explicit JVM home/temp
options, removes all five inherited Java/compiler/classpath option variables,
and is bounded to45 seconds and2MiB output. The parent environment is unchanged.
This builder executes no client model, SDK/OEM/Android implementation or native
Binder operation. Independent modeled review consumes these exact SDK-compiled
classes without recompiling the client; those outcomes have their own review
receipt and cannot establish native/source-owner acceptance.

## Required open compatibility and owner gates

Full AppOps/StrictMode native success headers remain unsupported. The genuine
endpoint can emit them; this client then throws and leaves required consumers
unready. A separately source-proved extension is needed for full header
compatibility. Existing bounded semantics must not be counted as full client
completion.

Actual BOOT insertion and retarget, genuine DMS/phase100 endpoint acquisition,
canonical native caller/Binder/Parcel, source/code/profile/epoch lifetime,
configuration/cache generation, original Samsung metrics calculation and Context
startup remain external and unassembled. Endpoint retirement after reply
admission may precede delivery, so the real consumer must reject stale results
before use. No local Snapshot or Binder alive check supplies that proof. Actual
native delivery, owner retirement/drain, Android/ART and the full security goal
remain unaccepted; no phone action or public credential-route change occurred.
