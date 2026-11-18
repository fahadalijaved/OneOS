# Independent prepared RAW guest-metrics client implementation review

Status: root-approved prepared plain-header helper accepted after source and
independent authored JDK model review. Full native-header compatibility remains
required open before integration/full-goal acceptance. Earlier endpoint, producer,
source and harness artifacts remain unchanged. No Android/OEM implementation ran.
This is the implementation review; the separate frozen proposal review remains
at [guest-metrics-client-review.md](guest-metrics-client-review.md) with its original
document/inventory pins unchanged.

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

## Approved code and exact-class model review

Root approved the restricted profile and exact API. The reviewed source is
`compat/android/com/appleexploit/oneos/security/boot/PreparedGuestMetricsClient.java`,
SHA256 `afd99ebe98a09b209bb7f6a42d23c9d88313597f5d6760105def73213ea625d1`.
No material code defect was found and no production change/test hook was needed.
The proposal review predating approval is preserved in the own ignored
`proposal-phase-snapshot/` and `HISTORICAL-PROPOSAL.json`.

Code review confirms the first acquire occurs inside the protected try, the
second failure still reaches first-packet cleanup, and reply/request recycling
is attempted in reverse acquisition order. The catch preserves the primary;
cleanup returns that primary, skips same-instance suppression, and catches a
failure recording distinct suppression. Without a primary it throws the first
cleanup failure rather than delivering a Snapshot. No packet is cached or
retained by the client.

Actual SDK37-compiled authored class bytes were used unchanged: client
`daefb86d28ba3300c37fb907f66414bb8b4724a747babcb2bbdc0d40604d9811`,
Snapshot `1df1392bafdbbcbfca7cde769a27f599deda4f154abfb41a825c36495c932dc6`,
and the empty Java8 access marker
`bdd9252e61e37b22d305e3c39a5b9b4daa0d9df279b11e2c221b15e2dacc875b`.
The exact build receipt is
`9f3f7780270d02a82120bec391efe8e52e6b39d0151bf6d7127b66cf93c9bbd2`.
The test did not recompile the client or execute SDK/OEM classes.

Forty-five focused checks passed through the public API. They cover retained
endpoint/no preparation IPC, one exact request/exchange, raw values and immutable
Snapshot, all absent metric guards, false/death/ordinary-error/nonzero-decoder
return distinctions, reply bounds before decode, unsupported−127/−128, strict
version/echo/status/body/trailing data, first/second acquire/write failures, both
cleanup attempts, original and same-instance failure identity, disabled
suppression, no-primary cleanup preventing SAMPLE/ABSENT return, and concurrent/
reentrant ownership of separate packets/results.

The five fixture sources implement plainly authored IBinder/Parcel/exception
models, not Android pooling, byte encoding, native allocation, death or platform
exception construction. Model readException controls exercise the client call
boundary; actual platform header behavior remains the separate source proof
above. Runtime classpaths contain only fresh model classes and the three pinned
authored client classes, with no android.jar/OEM archive/class directory.
Subprocesses clear all five inherited Java/compiler/classpath variables and use
their own cwd, temp/home and empty application-native search directory.

Suppression-recording failure has a distinct static proof. Actual javap of the
tested client shows addSuppressed at bytecode27, inside a Throwable catch covering
25…30 with handler33. The cleanup helper has no explicit athrow, and generic
rethrow has no runtime cast. A failure inside final JDK addSuppressed was **not**
runtime injected: that would require prohibited hooks or VM heap exhaustion.
Self-suppression and disabled suppression were exercised without those actions.

Per-run model sources/classes, commands, outputs and before/after pins are in
`out/guest-metrics-client-review/`; the derived inventory records the exact probe
receipt. These results establish authored Java mechanics, not native protocol,
resource drain or live source/authority identity.

## Required open integration

Full AppOps/StrictMode native success headers remain unsupported and **required**
before integration/full-goal completion. Real extended success packets currently
fail explicitly and leave required consumers unready. This helper is not a full
native-header client, functioning BOOT route or waiver of compatibility work.

Actual retained endpoint/phase100/source/code/loader/epoch,
canonical Binder/Parcel identity, retirement/death and consumer-generation fences
remain external. An admitted-before-retire reply can arrive later; no alive probe
or scalar Snapshot replaces that owner. BOOT selection, Samsung CompatSandbox,
ResourcesManager/configuration/compatibility calculations and full security
bootstrap remain unassembled. No Android/OEM/native/phone or authentication
acceptance follows from this source/API proposal review.
