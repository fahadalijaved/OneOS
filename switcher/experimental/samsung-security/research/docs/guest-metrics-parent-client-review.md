# Parent metrics client independent review

Accepted as an **unselected prepared component only**. No material production
defect was found in the frozen `PreparedGuestMetricsParentClient` source
`d4096fa5cdb043367376b9f842a22705f4612efed720b320125abc79c65577b4`.
This review does not select a parent Binder, implement the parent cell, change
BOOT, or establish native/Android/serialization/security acceptance.

The source retains its supplied parent, owns two fresh Parcels, and makes one
synchronous transaction at fixed `0x00fe0001`. First acquisition is inside the
protected region. False dispatch and thrown failures cannot become ABSENT.
Request size is bounded before dispatch; reply size4..65536 is bounded before
header reading. This finite profile need not accept every legal Android header.

The structural cursor admits at most one AppOps prefix, followed by plain
success, a StrictMode success header, or an ordinary error. Positive aligned
header sizes include their own size word, stay inside the containing range and
must be exactly consumed. Counts and UTF-16/blob padding use bounded arithmetic.
String terminators, returned character lengths and native cursor positions are
checked. Violation serialized bytes are opaque: preflight does not deserialize
them, replace classes, sanitize policy values or reconstruct the reply.

Direct canonical Binder/FD range predicates cover inspected header and success
spans. Ordinary exception tails retain their native sidecars and pass untouched
to the real exception reader. Before success effects, the exact12/32-byte v1
envelope, display echo, status and tail are checked. The owned reply is then
reset and genuine `readException()` runs once. Its original effects and failures
remain intact. Normal completion must match the predicted decoder end and
original total, followed by a second envelope check. Decoder reentry carries no
client lock. Current source/epoch/consumer admission after effects is external.

Snapshot owns seven private final primitive fields; all five metric accessors
throw for genuine ABSENT. Present values retain their raw five int patterns.
No Producer type, Parcel, list, guest DisplayInfo or mutable metric cache is
retained. Both owned cleanup attempts run even after another cleanup throws.
Exact primary identity wins; self-suppression is skipped and distinct suppression
recording is guarded. Without a primary, cleanup failure prevents publication.
The actual compiled catch table covers `addSuppressed`; no artificial JDK hook
or heap-exhaustion test was used to claim a suppression-allocation failure.

The source-pinned fresh reply uses the original default string helper. Pooled
`obtain()` resets DEFAULT at36/38; the fresh constructor sets it at9/11 before
`init(J)`, whose body does not overwrite it. DEFAULT is the actual base helper;
its string method reaches `readString16NoHelper` and nativeReadString16. These
are source facts, not live helper/native identity or arbitrary-owner admission.

The compiler gate was independently checked using actual class-file and DEX
parsers, frozen raw source and build logs. All16 compiler-only Parcel member
descriptors/access flags match original declarations, including private `(J)`
construction and public `hasBinders(II)Z`. Only DEX CONSTRUCTOR and JVM ACC_SUPER
representation flags are normalized at their corresponding scopes. The actual
selected `hasBinders` body delegates to `nativeHasBindersInRange(JII)Z`.
Production bytecode invokes canonical Parcel range methods directly. Exactly
four authored class52 and DEX039 definitions exist, including the validated
empty constructor marker. Projection/SDK/model definitions are absent from D8
program output. This is **SDK37 plus source-pinned compiler-only hidden ABI**;
the SDK37 public API alone cannot compile this source. Actual ART hidden-API and
canonical runtime method admission remain open. D8's API37/max36 warning remains.

The isolated JDK run passed49 meaningful authored cases on the exact existing
four compiled production classes, without recompiling production. Cases cover
plain/combined headers, nullable/odd/even/unicode strings, full outer violation
vectors, opaque blobs, exact65536-byte success, malformed counts/lengths/NULs,
sidecars, decoder cursor/size/envelope drift, original error identity, false
dispatch, acquisition/cleanup faults, absent accessors/raw bits, nested calls and
overlapping same-client reads. The Parcel model is an authored byte buffer with
an explicit effect/cursor/error decoder boundary; it is not Android's decoder,
ObjectInputStream, Binder driver or native object table. Opaque bytes in these
models are placeholders, not genuine serialized Violation objects.

Runtime classpaths contain only fresh authored models and unchanged production
classes. No android.jar, compiler projection, OEM archives/classes or JNI were
loaded. All five inherited JVM/compiler option inputs were removed, with owned
cwd/temp/home and an empty application native-library directory. Historical
focused runs remain intact; the final49-case receipt and exact before/after pins
are referenced by the paired inventory.

Required external work includes genuine parent/cell and phase ownership,
canonical BOOT/class/native/hidden-API identity, actual range predicate and full
native header/serialization/policy interoperability, current caller/display
visibility/source epoch after effects, and real consumer configuration/lifetime.
Neither this Snapshot nor a successful authored packet attests those conditions.
No phone, original implementation, credential state or frozen earlier component
was changed.
