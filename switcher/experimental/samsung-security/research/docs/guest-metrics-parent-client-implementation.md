# Prepared native-parent metrics client

PreparedGuestMetricsParentClient implements root's approved **unselected prepared
component**: prepareParent(IBinder), read(int):own immutable Snapshot, internally
fixed transaction0x00fe0001 and existing v1 RAW metadata. The supplied Binder and
Snapshot do not attest source, authority, native caller, epoch or readiness.
No lookup, wrapper, generic transaction, reflection, retry, cache, worker hop or
epoch callback is added. The earlier afd99ebe client remains unchanged.

Source SHA256: d4096fa5cdb043367376b9f842a22705f4612efed720b320125abc79c65577b4.

## Explicit SDK gate and hidden-ABI compilation

The pinned SDK37 public Parcel API has hasFileDescriptors(int,int) but no
hasBinders method. Root approved direct canonical Parcel.hasBinders(II), using an
**authored compiler-only Parcel ABI projection** before SDK37 on this component's
compiler bootclasspath. The captured Samsung public method returns the actual
nativeHasBindersInRange(JII) result; body SHA25663d1a2b46d05f3e79295aa02883c25796d3c848674878a210f9effb04f2ec705.

Projection template SHA256:10f9837e3c9f1f3abc5c15e4094b7a1eb7cf0c60306b525a52ea5389804ec0a1.
All16 method/constructor descriptors and access flags are checked against the
original declarations. Its private(J) constructor is an actual original member.
Class-file ACC_SUPER is normalized against DEX flags; no other class access bit
is relaxed. The projection is generated/compiled separately under ignored out/,
never executed or packaged. Actual client bytecode directly invokes the canonical
Parcel range methods. SDK inputs are immutable.

This is **SDK37 plus compiler-only hidden ABI**, not unqualified SDK37 API,
hidden-API, ART or BOOT acceptance. Exactly four authored definitions enter D8;
no Parcel/SDK/projection/model/producer definition enters its input/output or the
independent model runtime. Actual canonical runtime method/native identity and
caller/source/profile admission remain external.

The original stopped SDK gate receipt/log remain under sdk-api; its old report
and inventory are saved in sdk-api/gate-history. The first projection-validator
run stopped before client compilation because it compared JVM49 directly with
DEX17; the corrected validator normalizes only ACC_SUPER0x20. Its failed run and
validation-stop.json remain preserved. Client/projection source did not change.

## Structural preflight before genuine policy

Each read owns fresh request/reply Parcels. It writes the fixed descriptor,
version1 and unchanged displayId, checks request size<=512 and calls only
0x00fe0001 with flags0. False transact throws before parsing. Reply size4..65536
is checked before header decoding; this is a finite admission limit, not a bound
on every legal Android header or variable source-writer output.

The private Cursor walks one optional AppOps-127 prefix, followed by plain0,
an ordinary exception, or one StrictMode-128 success header. Positive aligned
header sizes are at least8, bounded and exactly consumed. AppOps has a bounded
nonnegative count, each nullable String16 and three long words. StrictMode has
count0..3 and bounded stack/frame/tag vectors. Serializable class names and byte
spans are walked structurally; no Violation, ObjectInputStream or policy handler
runs during preflight. Opaque serialized bytes remain untouched.

String16 validates null/character length, widened padding arithmetic, terminator
and exact native returned length/cursor. A bounded owned-word terminator read
uses cached canonical ByteOrder.nativeOrder only for representation, not endpoint
or process attestation. Native hasBinders/hasFileDescriptors range predicates
refuse objects in inspected headers and success scalars. Ordinary error tails,
including native sidecars, remain untouched. No marshalling/reconstruction occurs.

The entire exact12/32-byte success payload/version/echo/status/tail is validated
before effects; the cursor records the expected native decoder end. Then only
the original owned reply is reset and genuine readException runs **once**.
Original AppOps callbacks, real StrictMode deserialization/local-stack/current
thread policy and errors remain untouched. A nonzero ordinary exception reader
returning normally fails. Normal success requires the expected decoder position
and unchanged total size, then repeats payload/version/echo/status/tail checks
before constructing Snapshot. Failure never becomes ABSENT/default or a retry.
The original owner must establish currentness after decoder effects before use;
no client lock or worker hop surrounds those effects.

Snapshot has private final fields and guarded RAW int/DPI-bit accessors. Genuine
ABSENT exposes only displayId/isPresent; every metric getter throws. Values are
not normalized or represented by a guest Producer.Sample.

## Default string helper and cleanup

Actual pooled Parcel.obtain resets ReadWriteHelper.DEFAULT at36/38. The fresh
constructor sets DEFAULT9/11, then init(J) only initializes native pointer/owner
fields without replacing the helper. DEFAULT is created as the exact base helper;
its readString16 calls readString16NoHelper then nativeReadString16. Six narrow
source proofs are pinned in the receipt. These establish the selected source
path, not runtime helper/native identity acceptance or arbitrary-class attestation.

The protected try covers the first obtain before the second. Both acquired owned
Parcels are recycled once, reply then request, even if another cleanup fails.
Preserve the exact primary Throwable, skip self-suppression, guard distinct
suppression recording and throw the first cleanup failure without a primary.
Generic rethrow performs no RuntimeException cast. No borrowed packet is reset
or recycled and no Parcel escapes.

## Actual bounded build and required open work

python -B tools/build_guest_metrics_parent_client.py passed in
out/guest-metrics-parent-client/20261105T235945104798Z-9318f0db5aed41c8a447d3bd6228c646.
Source/target8 output is exactly client, Cursor, Snapshot and an empty Java8
constructor-access marker. Source/projection/dependencies remain pinned before
and after inspection/D8. DEX039 signature/checksum verify; its SHA256 is
c7bea7b47740700451d772a538910c9be22e083c5979df94b0cf398a83dccaae,
and unselected DEX JAR is
c10668bf4afdc2ee2f507efdc240e84269644c26eb8ac224c6416833282f509e.
The actual D8 API37/max36 warning remains recorded.

Child tools clear all five inherited JVM/compiler/classpath option variables,
use owned cwd/TMP/TEMP/JVM temp/home and45-second/2MiB bounds. No SDK/OEM/client
runtime or model executes in this builder. Independent modeled review consumes
these exact four classes without recompilation or projection/SDK runtime; its
separate receipt owns those outcomes.

Full genuine native header/serialization/policy behavior, actual range predicates,
ART/hidden-API/BOOT, current native parent/caller/source/profile/epoch lifetime,
real consumer admission after effects, parent-cell/lifecycle integration and
Samsung metrics/Context assembly remain required open work. Compilation and
modeled packets do not complete the client or security goal. No original
firmware, global state, credential route or phone was changed.
