# Prepared RAW guest-metrics client API proposal

**Proposal only, pending root API approval.** No client Java, build, framework
retarget or BOOT selection has been produced. The client will consume only the
frozen PreparedGuestMetricsEndpoint v1 from a separately admitted retained Binder.
The endpoint applies the real native caller's display-visibility policy; this
metadata route is neither credential authentication nor authority attestation.

## Exact proposed API

Public final `com.appleexploit.oneos.security.boot.PreparedGuestMetricsClient`:

- `public static PreparedGuestMetricsClient prepare(android.os.IBinder endpoint)`
  rejects null and strongly retains that exact object; no lookup, descriptor
  probe, alive check, publication, cache, callback registration or IPC.
- `public Snapshot read(int displayId) throws android.os.RemoteException`
  makes one synchronous transaction against that same retained Binder. It never
  retries or silently substitutes another endpoint.
- Public static final immutable nested `Snapshot` has `displayId()`,
  `isPresent()`, `appWidth()`, `appHeight()`, `logicalDensityDpi()`,
  `physicalXDpiBits()` and `physicalYDpiBits()`. All fields/constructors are
  private. Every metric accessor throws IllegalStateException for genuine ABSENT;
  no usable zero/default metrics are exposed for absence. SAMPLE retains all five
  ints exactly, including arbitrary signed integers and DPI bit patterns. No
  conversion, normalization, positivity check or second field read is added.

Each read returns its own Snapshot, including an explicit absent snapshot only
for a fully validated status0 response. There is no Producer.Sample dependency,
guest class reference or serialization of a full DisplayInfo. A Java8 private
nested-constructor access marker, if emitted, belongs to the explicitly inspected
authored output closure; no SDK/producer/model definition may enter that DEX.

## Wire and explicit bounds

Descriptor: `com.appleexploit.oneos.security.IGuestDisplayMetrics.v1`.
Use fresh owned request/reply Parcels, write that token, int version1 and the
unchanged requested displayId. Refuse a request larger than the endpoint's512-byte
limit. Invoke exactly transaction1, flags0, nonnull reply. A false transact result
throws RemoteException and is never parsed as absence. Death and actual transact
exceptions propagate. No native identity clear, worker hop or caller UID/PID
substitution is introduced.

After a true transact result, validate the complete reply dataSize **before any
header decoding**: at least4 and at most4096 bytes. The4096 limit is a proposed
client admission limit, not a guarantee about every platform exception reply.
Reset only the owned reply to position0, read the first exception-header int, then
reset that owned reply to0 for the real platform readException decoder.

The first supported profile accepts a **plain exception header**:

| Header/result | Required action |
| --- | --- |
| code0 | Invoke genuine Parcel.readException, then validate the exact v1 success envelope below. |
| AppOps−127 / StrictMode−128 | Throw explicit unsupported-header BadParcelableException before delegating; never skip, forge a zero header or accept as ABSENT. This includes StrictMode size0. |
| Other nonzero code | Invoke genuine Parcel.readException and propagate its actual exception. If it unexpectedly returns, throw BadParcelableException; no success payload may be accepted. |

This deliberately does **not** claim AppOps/StrictMode extended-success-header
compatibility. Genuine endpoint writeNoException can emit those prefixes. Such a
reply leaves the consumer unready with an explicit unsupported failure until a
separately source-proved bounded header extension is approved. Oversized errors
likewise fail explicitly instead of becoming absence or truncated metrics.
The byte cap bounds the received packet accepted for decoding; it is not a proof
of all platform exception-parser allocations, effects or native validity.

For code0 only, after native decoding require exactly12 or32 remaining bytes
before scalar parsing. Read version1, echoed requested displayId and status0/1.
Status0 requires exactly12 initial remaining bytes and no tail. Status1 requires
exactly32 and reads exactly the five ints in endpoint order. Reject version/echo,
status/length mismatch, truncation and any trailing byte. Only then construct the
immutable Snapshot. Checking sizes first avoids relying on native readInt to
throw on a short scalar packet. DisplayId is never rewritten or range-guessed.

## Actual exception-header source basis

Reused immutable raw Parcel evidence is in the original binder-direct-dispatch
Samsung and ColorOS proofs. Both readException bodies call readExceptionCode at0,
return only for code0, otherwise read the message and delegate to the platform
exception constructor/throw path. Both readExceptionCode bodies recognize
AppOps−127 at4/6 and StrictMode−128 at15/17. Their zero-sized StrictMode branch
logs at29 and returns0 at36/37. Therefore a naive readException plus remaining
length check can accept a malformed `[−128,0,...v1status0]` as absence.

Both writeNoException bodies call the genuine AppOps prefix producer at0 and
check gathered StrictMode violations at3. A client cannot assume every valid
native success header is exactly four bytes. The restricted profile rejects the
unimplemented extended cases explicitly; it does not redefine them as invalid
Android replies. No OEM/native exception method is executed for this proposal.

## Parcel failure and lifetime ownership

Cover the first acquired Parcel immediately, so failure obtaining the second
still recycles the first. Attempt recycling every successfully acquired owned
Parcel exactly once on every path, including a second obtain/write/transact/header
or scalar-decode failure. Cleanup must preserve an existing primary Throwable,
including a cleanup failure that is that same instance; distinct cleanup failures
can be suppressed without replacing the primary. If no primary exists, a cleanup
failure prevents successful return. Failure recycling one packet must not skip
attempting the other. Only owned Parcels are reset/recycled; none escape or are
retained after read. No partial reply or cleanup outcome becomes ABSENT.

Real bootstrap owns exact endpoint/code/profile, canonical Binder/Parcel identity,
source process/epoch and lifetime. A caller supplying an arbitrary Binder to
prepare does not authenticate it. The client performs no isBinderAlive claim or
service-name reacquisition and does not infer source or display freshness from a
returned Snapshot. Endpoint retirement can occur after its reply-admission fence;
the real consumer must reject stale results according to its actual owner/epoch
before use. Cancellation/death/native delivery/drain remain external.

Actual BOOT visibility, retained genuine guest DMS/phase100 endpoint, original
caller/display policy, configuration/cache generation, Samsung consumer metrics
calculation and Context construction remain unassembled. Required absent or
unavailable display input leaves that consumer unready. Root must approve this
restricted header profile and API before client implementation/build begins.
