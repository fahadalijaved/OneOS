# Genuine extended-header decoding after bounded preflight

**Recommendation:** an admitted successor can use the original Samsung
`Parcel.readException()` once after a strict structural walk of the original
owned reply. Preserve actual AppOps notifications and StrictMode policy handling.
Do not strip prefixes, forge code0, disable policy, deserialize twice or replace
Java serialization. The current client afd99ebe remains unchanged and explicitly
restricted; this source proposal produces no production successor or runtime
acceptance.

The auditor pins37 bodies and35 selected source assertions, including the relevant
donor writers, Samsung readers and serialization/native boundaries. Its Python
framing model accepts9 outer-envelope cases and refuses24 malformed cases.
Those are authored byte fixtures, not executed Parcel/SDK/OEM code. In particular,
the fixture serialized bytes are opaque placeholders, not valid decoded
Violations. The raw bodies remain only in ignored firmware.

## Actual writer/reader contract

Both source Parcel envelopes permit **one optional AppOps prefix first**, then
the normal exception code or a StrictMode success header. No repeated-prefix loop
is present in Samsung readExceptionCode. StrictMode success itself returns code0
after its body; there is **no additional EX_NONE integer** following that body.

| Header | Actual fields and relevant source sites |
| --- | --- |
| AppOps−127 | Donor prefix writer13 writes the tag;21 reserves length;28 writes entry count. Each entry writes String attribution40 and exactly three long words54..73, padding short BitSets with zero. The stored length at86 is end−lengthFieldPosition, so it includes its own4-byte size field. Samsung reader discards that size at0, reads count3 and loops String11 plus three longs15..29. |
| StrictMode−128 | Donor writeNoException writes the tag and size placeholder, calls writeGatheredViolationsToParcel, then stores end−lengthFieldPosition. The latter writes count=min(list.size,3) at19..24; a null list writes0. Each ViolationInfo is written at36; the gathered list is cleared afterward45. |
| StrictMode reader | Samsung readExceptionCode reads size19 but only checks nonzero23. Size0 logs29 and returns0 at36/37. A nonzero size calls the real StrictMode reader33; it does not use the declared size to fence that reader. The latter reads count19 and loops until count, without the donor's three-record cap. |

Thus `[-128,0,...v1]` can pass an unguarded original decoder as success. Negative
counts and mismatched positive size fields can also escape the original loop/
length checks. These are structural failure cases for this versioned metadata
channel; ordinary Android header compatibility does not justify accepting them.
The real decoder should follow complete preflight, not serve as preflight itself.

## Concrete preflight and real-decoder sequence

Use the original owned reply and a reviewed finite total bound M, before reading
any header. Preserve all ordinary exception behavior and the current acquisition,
cleanup, endpoint and caller contract. A future private preflight result records
whether the terminal code denotes success and its expected decoder-end position;
it is not a request/authority/readiness token.

1. Bound dataSize and every cursor operation. Inspect an optional−127 prefix:
   require a positive, four-byte-aligned size of at least8, wholly within the
   reply; nonnegative count; exactly a nullable String16 plus24 bytes per entry;
   and an exact end matching that size. Check count against remaining/minimum
   entry size28 before looping. Reject another−127 tag afterward.
2. Accept the next ordinary exception code, plain0, or one−128 header. For−128,
   require the same positive/aligned/exact size discipline and count0..3, matching
   the actual donor writer. Reject zero size and overrun/negative/mismatched sizes
   before invoking any effectful header reader.
3. Walk each ViolationInfo's outer structure below without constructing or
   deserializing a Violation. Bound all nested counts before loops; use checked
   wide arithmetic or subtraction-based remaining checks for lengths/alignment.
   For String16, bound encoded character count before a native string read,
   require the expected null/length and exact cursor advance under the admitted
   canonical string helper. Do not normalize string contents or DPI values.
4. On a success terminal, validate the **entire** exact12/32-byte v1 application
   payload, version, display echo, status and trailing-data absence before policy
   effects. Record the expected native decoder end. On an ordinary nonzero
   exception, preserve its bounded original error tail for the genuine reader;
   do not decode it as metrics or invent an exception replacement success.
5. Reset only the original owned reply to0 and invoke genuine Samsung
   readException **once**. Let all actual exceptions propagate. An ordinary
   nonzero code returning normally is a protocol failure. For normal success,
   require the real decoder's position to equal the predicted end, then retain
   strict v1 payload/version/echo/status checks before returning an own Snapshot.

Do not hold a client lock across that original decoder. AppOps readAndLogNotedAppops
calls real OnOpNotedCallback at60 and the message collector at122; without a
callback it records actual unforwarded operations. StrictMode creates a local
stack, constructs real ViolationInfo29, adds that stack32 and invokes actual
AndroidBlockGuardPolicy.handleViolationWithTimingAttempt45. Real callback,
logging, exception or penalty behavior must remain. Reentry/retirement after
these effects requires the real owner/epoch check before consumer use. A failed
decoder never becomes ABSENT and is not silently retried.

## Violation outer structure and trusted serialization

Donor ViolationInfo.writeToParcel writes:

1. Serializable violation: class-name String plus opaque byte-array stream, via
   Parcel.writeSerializable2. That method gets the actual object's runtime class
   name, uses real ObjectOutputStream.writeObject28 and writes its byte array38;
   null follows the actual null-string branch.
2. Binder-stack vector count, then each frame-array count; every frame is three
   Strings (class, method, file) and line int.
3. Four ints (penalty, duration, loop number, animation count), two longs
   (uptime, instance count), action String and nullable String-array tags.

The Samsung ViolationInfo reader consumes that same outer order, using real
readSerializable(loader,Violation.class)28, nested frame arrays47 and tags137.
The prewalker skips the serialized byte span according to its bounded length;
it does not call ObjectInputStream, rebuild an object or interpret a penalty.
All vector counts must fit their containing header: stacks need at least4 bytes
each, frames at least16, and tags at least4. The actual original reader retains
its own type, class-loader, stream and policy behavior.

Samsung Parcel.readSerializableInternal reads the class name, performs its
source type checks, creates the byte array71 and calls ObjectInputStream.readObject85.
Its original Parcel$2 resolver uses the selected real class loader. This is the
same **admitted genuine writer/original platform reader trust contract used by
AIDL**, not a reason to rewrite Java serialization or require a proof of the
whole platform's allocation behavior. The packet cap/outer walk does not claim
to bound every allocation or effect inside deserialization.

The two captured base `android.os.strictmode.Violation` definitions have identical
class/interface, field and method declaration shapes: Throwable superclass,
mHashCode/mHashCodeValid and the same six method signatures/flags. No explicit
serialVersionUID field is declared there. Some method-body hashes differ; those
differences alone do not establish a serialization mismatch. Runtime class names
come from actual source-produced objects, not a client-invented allowlist.
There is no evidence here of a forced base-class incompatibility. A concrete
encountered subclass/stream incompatibility should receive a targeted check;
the genuine decoder's class/UID/stream error must propagate. Actual cross-image
deserialization acceptance remains untested, without imposing a speculative
whole-Throwable-graph audit as a prerequisite to preparing this design.

## Native sidecars and size profile

These successful metadata/header writers use scalars, Strings and serialized
byte arrays, with no native Binder or FD object fields. A byte-only model cannot
prove native object-table absence: marshalling bytes do not encode the complete
Binder/FD sidecar contract. Samsung hasBinders/hasFileDescriptors and their
range variants delegate to actual native predicates; marshall and createByteArray
are native-backed too. The selected Java bodies do not implement those natives.

Prefer an owned-Parcel primitive walk with native hasBinders(offset,length) and
hasFileDescriptors(offset,length) refusal for the inspected headers and success
scalar regions. These predicates are format guards, not source attestation.
Do not require or strip object-free **ordinary error tails**: they belong to the
genuine exception decoder. A whole-byte marshall model is only suitable when
the complete packet is known object-free; it must not reconstruct a packet and
lose sidecars. Actual canonical native Parcel identity/framing and its fresh
string helper remain the platform admission basis, not an invented Java scan
for object-looking bytes or a requirement to replace Binder/native code.

The source writers have variable strings and serialized objects. The current
4096-byte cap is a client admission limit, not a source bound on all genuine
extended headers. Choose and review the successor's finite M explicitly, retain
failure for oversized packets and validate genuine representative headers under
the actual profile. This report does not assert that arbitrary legal native
replies fit4096 or an invented universal transaction-size bound.

No production edit is approved by this report. Root must review the exact
successor parser/size profile, preservation/cleanup and independent malformed,
decoder-position, callback/reentry and native-sidecar tests before selection.
Actual endpoint/source/epoch lifetime, BOOT/Context assembly and native Android
header acceptance remain required open work. The frozen restricted client and
all prior builds remain unchanged.
