# Independent guest metrics endpoint review

Status: bounded source and prepared endpoint code accepted, helper only, with
independent authored JDK model checks passing.
No lifecycle hook, publication, service or Android/OEM code was executed. This
card preserves the frozen producer, build, earlier review and test evidence.

## Actual born Binder and phase completion

The independent review read the pinned actual methods selected in
[guest-metrics-endpoint.json](../inventory/guest-metrics-endpoint.json), without
rerunning the original source audit. The proposed owner is grounded in a real
source acquisition edge, not a made-up mBinderService getter or generic ready
interface.

Observed original ColorOS DMS.onStart creates BinderService in v0 at0x15/0x17,
passes that same object to the actual extension0x1c, publishes it as `display`
0x21, publishes both original LocalServices0x28/0x32, and returns0x35. v0 is not
overwritten on this normal tail. Capturing exact this/v0 immediately before
return can therefore retain the original receiver. It must preserve original
extension/publication work and failure behavior; an original thrown start is not
eligible for the proposed normal-tail acquisition hook.

The extension.onStart implementation constructs the original enhancement Binder
and calls the base Binder.setExtension0x0d. It does not retain the base object;
an assumed existing extension field cannot supply that ownership. The selected
BinderService constructor stores the real outer DMS and derives the original
PermissionEnforcer from its actual Context. Preparing the existing extractor
over this born Binder would be metadata work, not another service constructor or
an admitted live endpoint.

Observed phase100 branch compares actual phase argument at0x04, enters real
mSyncRoot, and waits for logical display0 plus VirtualDisplayAdapter. Its success
path leaves that monitor0x25 and jumps0x26 to0xf9. It still calls the original
extension.onBootComplete0xfb, updates logging fields and invokes DeviceState
extension.onBootPhase0x111 before return0x114. Timeout throws0x83; its exception
cleanup also rethrows. The proposed success hook belongs at this final normal
return and only for actual phase100/the same captured DMS. A hook immediately
after the display wait or inside the extension callback would be too early.

This proves the selected DMS method's normal phase completion. It does not prove
every SystemServiceManager phase callback completed, whole guest boot succeeded,
WMS/input/systemReady is ready, the current cache generation is fixed or an
installed hook ran. Later guest failure/death/return must retire the actual
endpoint and its consumer through the real owner.

## Code, loader and lifetime boundary

SystemServer loads/starts/retains the actual DMS Class through its real
SystemServiceManager. The selected Zygote loader path consumes the actual
SYSTEMSERVERCLASSPATH, parent and native-library path. A helper in an unrelated
app DEX or same-name private loader is not visibility proof. The capture,
endpoint and producer dependency closure must be selected for the actual DMS
defining loader with source/DEX/index/type/inverse checks. A retained arbitrary
anchor or class shape cannot replace this admission.

The source card accurately distinguishes pinned OneOS patch-producer intent
from actual rebuilt/installed guest bodies and inherited classpath fallback.
Its nine source files can be pinned, but those original method PCs are not
automatically valid after upstream patches. No unsupported live-source or
generation assertion follows.

The proposed cell must retain the exact DMS, born Binder, extractor, endpoint and
code owner across original work. Capture alone supplies no readiness. Publication
must stay off until actual source-profile admission and the matching normal
phase100 event. Alias collision, re-entry, partial hook/preparation, duplicate
activation, process death and retirement need explicit handling in the eventual
implementation. Stop-new-call/active-stack accounting is not native Binder reply
drain, service shutdown or permission to dispose the borrowed DMS/loader.

## Caller visibility and finite v1 protocol

The reviewed raw getter captures real Binder callingUID before its own original
clear/restore and applies its original access/override policy. An endpoint can
preserve that metadata policy by invoking the frozen extractor once on the
incoming thread without an authored identity clear, handler hop, supplied
caller IDs or system-UID relay. No invented supervisor authorization or UID1000
authority attestation is required or established. A discoverable alias is not
an authority-only channel or private isolation.

The proposed distinct descriptor/version and transaction1 are bounded: flags0,
nonnull reply, interface token, version1, requested displayId, no trailing data;
success has the normal exception envelope plus version/echoed subject/status,
and SAMPLE alone appends the five raw ints. Genuine getter null is ABSENT;
getter failure, unsupported/malformed input, death, false transact and unavailable
endpoint are not absence/default/readiness. The prepared implementation must
bound input bytes before parsing a potentially large token and reject invalid
requests before any getter call. Unknown codes follow ordinary Binder rejection/
super behavior without manufacturing metadata.

An original getter Throwable should retain its exact identity inside the direct
Java call. Across Binder, only supported exception transport meaning can be
promised; arbitrary Throwable object identity and success after transport
uncertainty cannot. No implicit retry or full DisplayInfo Parcelable is proposed.

Retirement needs a precise reply-admission/commit cutoff. It must reject a result
that loses admission during the original getter. A reply already admitted before
retirement may still be transmitted or received afterward; Java stack count0 or
retire return cannot retract native Binder buffers. The actual client/endpoint
death/source generation owner must enforce downstream currentness. This is a
required implementation qualification, not an observed runtime defect in the
source-only card.

## Prepared code and authored model review

The root-approved new source
`PreparedGuestMetricsEndpoint.java` has SHA256
`a3e01dc99c4a879640e55ac0416859abba12dea47cd447824e6e4f329d6466ed`.
Independent code review found no material defect. The frozen Producer remains
`72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7`.
No production change or test hook was needed.

The exact API retains the nonnull prepared producer, returns the same Binder,
starts PREPARED/inactive, allows one activation and makes retirement terminal/
idempotent. Activation is explicitly not a source/phase100 receipt. Under its
own lock it admits/counts ACTIVE code1 calls before validation; `finally`
decrements after validation, capture, reply construction or failure. Inactive
refusals and superclass unknown-code handling are excluded. Strong producer/code
retention remains after retirement/count0; no backend is disposed.

Flags/reply and0…512-byte checks precede token parsing, then descriptor/version/
displayId/trailing-data checks precede the one capture. Capture and Parcel work
are outside the own lock. The locked ACTIVE recheck is the reply-admission fence:
retired-before-fence refuses success/ABSENT; admitted-before-retire may construct
or deliver its reply later. Sample is a local immutable five-int projection.
No original visibility override, UID allowlist, identity clear, handler hop,
second getter, service lookup or publication was introduced.

Original capture RemoteException, RuntimeException and Error are thrown directly.
Other checked helper faults become a fixed-message RemoteException with the
original cause. The normal reply prefix is written only after the fence. A
reply-writing failure can leave partial output and is not a successful/ABSENT
transaction. Borrowed Parcels are not retained/recycled/reset by this helper;
ordinary reads advance the request's read position.

Independent authored models executed the **unchanged actual SDK37-compiled four
production class files**, initially from build receipt
`830f95e4127b0b82b828d53a9a35a80e3713ef79030d6fc2d9c71c2d89f7ccf8`.
The later build-environment correction produced receipt
`70fd78a9cb122ecf6db119bad5738a3473eef71a9c66c461b6c9c560487c9627`;
all four class byte hashes, DEX and jar are identical. This successor build's
sanitized compiler provenance is separate from the model execution receipt;
identical class bytes did not require another model run. Endpoint class SHA256
is `29be2b02bbf7530ec4bb69b590996355fe462616f79a8cec0e547ce3b8de1ba7`.

Thirty-four focused checks passed. They cover inactive/one-time activation,
terminal retirement, exact SAMPLE/ABSENT ordering, size-before-token, malformed
flags/token/version/subject/trailing input, original supported Throwable identity
and checked-cause retention even when the getter retires before throwing,
caller/subject failures not becoming ABSENT, reentry, counting during validation/
reply faults, and source retention after count0. A blocking getter/concurrent
retire test verifies capture is outside the lock and retired-before-fence loses
the reply. A first-reply-write retirement verifies the already-admitted reply
can complete. No test treats zero count as native/global drain.

The isolated Binder/Parcel/identity/DMS/DisplayInfo implementations are plainly
authored models under ignored `out/guest-metrics-endpoint-review/`, not OEM code
or executable SDK stubs. Runtime classpaths contain only fresh model classes and
the four unchanged authored production classes, excluding android.jar and OEM
archives/classes. Subprocesses use their own run cwd/temp/home/empty application
native search path, with all five known inherited JVM/compiler/classpath option
variables cleared. Per-run source/class hashes are retained; the source-phase
review predating code is preserved in `source-phase-snapshot/` and
`HISTORICAL-SOURCE.json`.

The Parcel model is a typed-value list with an independently controlled size
report. Its512-byte case tests the Java bound predicate, **not native Parcel
encoding, token headers, byte-size correspondence or exception serialization**.
Direct-Java Throwable identity is likewise not a cross-process identity claim.
The latest exact model receipt is recorded in the derived inventory; prior
intermediate receipt/model bytes remain preserved separately.

## Remaining acceptance boundary

The actual lifecycle hooks/publication remain unimplemented. Existing extractor,
harness and main frozen integration files were not changed by this endpoint
review. The prepared helper has no invented source owner or authority attestation.

Real DMS/code/feature implementation/source epoch/physical display admission,
Samsung CompatSandbox, ResourcesManager/configuration/compatibility calculation,
boot-visible consumer retarget, full process-local cache installation and full
security outcomes remain external. No Android/native identity, endpoint,
hardware metrics or authentication acceptance is claimed.
