# Independent RAW guest-metrics client proposal review

Status: proposal acceptable with its explicit restricted-header profile; root's
API/bounds approval and subsequent code review remain pending. No client code,
SDK build or model test was executed for this review. Earlier endpoint, producer,
source and harness artifacts remain unchanged.

## Independently checked exception-header source

This review read the six selected actual Parcel bodies from the reused immutable
Samsung/ColorOS raw sources identified in
[guest-metrics-client.json](../inventory/guest-metrics-client.json). It did not
rerun a broad source audit or execute those implementations.

Both `readException()` bodies call `readExceptionCode` at0, return for code0,
otherwise read the message and delegate to the actual exception path. Both
readExceptionCode bodies recognize AppOps−127 and StrictMode−128. A StrictMode
header whose declared size is0 logs at29, then explicitly returns0 at36/37.
Consequently, blindly calling readException and accepting a remaining v1 ABSENT
body can convert `[−128,0,...]` into apparent success.

Both `writeNoException()` bodies can prefix AppOps and gathered StrictMode data.
Extended success headers can therefore be genuine; this review does not label
them malformed merely because the proposed first client profile rejects them.
The inspected bodies are platform Java header routines; native primitive parsing,
allocation behavior and actual Binder transport are not executed/proved here.

## Proposed exchange and result boundary

The proposed client strongly retains the provided nonnull IBinder and performs
one synchronous transaction1 using fresh owned request/reply Parcels. Preparation
does no IPC, descriptor/aliveness probe, lookup or source attestation. The request
uses the exact descriptor, version1 and unchanged displayId, within the endpoint's
512-byte limit. There is no service-name retry, identity clear, worker hop,
supplied caller identity or guest Producer.Sample dependency.

False transact, death, remote/platform exception, unsupported header and malformed
payload must throw; only a completely validated status0 packet yields ABSENT.
The client cannot infer endpoint/code/epoch/currentness from a true transaction
or a returned Snapshot.

The proposed4…4096-byte total reply cap must be checked before decoding **any**
header, including an error. Four bytes rather than a success-packet minimum
allows the genuine platform error path to be reached. A larger real error remains
an explicit oversize failure, not absence/truncation. This cap bounds accepted
packet bytes; it does not establish every platform decoder's allocations/effects.

Within the proposed restricted profile, peek the owned reply's first int and reset
only that owned reply. Reject−127/−128 explicitly, including the zero-size
StrictMode case, before delegating. For plain0, use the genuine readException
decoder, then require exactly12 or32 remaining bytes for the v1 envelope. For
other nonzero codes, use that genuine exception decoder and propagate its actual
error; if it unexpectedly returns, throw rather than accept a success body.
Do not forge a zero header, skip arbitrary platform headers or treat unsupported
extended success as ABSENT.

After plain success, validate version1, echoed requested displayId, status0/1 and
the matching exact length. ABSENT has12 bytes and no metrics; SAMPLE has32 bytes
and the five original int values. Truncated, oversized, mismatched or trailing
data cannot publish a Snapshot. Raw signed ints/DPI bit patterns require no
normalization or guessed display-ID range.

The proposed immutable host Snapshot owns only primitive data and presence state.
All five metric accessors throw when absent; internal storage zeros cannot escape
as usable dimensions/density/DPI defaults. Its API contains no guest-private
type or synthetic full DisplayInfo. This separates absence from a usable raw
sample without fabricating authority or final Samsung metrics.

## Acquisition, cleanup and unresolved integration

The first returned Parcel must be covered before obtaining the second. Attempt
every acquired owned Parcel's recycle exactly once on every path; one cleanup
failure must not skip the other. Preserve an existing primary Throwable even
when cleanup throws that same instance, and avoid self-suppression replacing it.
If no primary exists, cleanup failure prevents a successful Snapshot return.
No request/reply is retained after the call; only owned packets may be reset or
recycled. These are required code-review conditions, not executed native cleanup
evidence.

No material proposal defect was found. The explicit compatibility limit matters:
an otherwise genuine AppOps/StrictMode-prefixed success or oversized error leaves
the required consumer unready until a separately proved extension is selected.
The current proposal cannot claim complete platform exception-header support.

Root still must approve the4096-byte/plain-header profile and exact API before
implementation. Actual retained endpoint/phase100/source/code/loader/epoch,
canonical Binder/Parcel identity, retirement/death and consumer-generation fences
remain external. An admitted-before-retire reply can arrive later; no alive probe
or scalar Snapshot replaces that owner. BOOT selection, Samsung CompatSandbox,
ResourcesManager/configuration/compatibility calculations and full security
bootstrap remain unassembled. No Android/OEM/native/phone or authentication
acceptance follows from this source/API proposal review.
