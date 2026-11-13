# Private retained PIN endpoint review

**PASS for reviewed source, saved SDK/D8 output and authored models only.** The
endpoint/client remain unselected and initially closed. Independent saved review
verified 42 scenarios and 312 checks, with the same two SDK-compiled program
classes and fifteen dependencies. This reviewer ran static inspections only;
Root performed the compiler and authored JVM workflows.

The host uses its canonical credential CREATOR, invokes the retained operation
Owner once on the same worker/caller, then uses the original response writer.
No adapter user/flags are accepted on the wire. Returned host credentials close
in finally through validation, original-call and writer failures; the borrowed
guest PIN is not closed or retained. Host data/reply Parcels remain framework
owned. The client attempts each of its two acquired Parcel recycles once,
including partial acquisition and primary/self-suppression failures.

Exact local RuntimeException/RemoteException/Error survive cleanup; unexpected
checked failures are explicitly translated to a fixed RemoteException with local
cause. Throwable identity across real Binder is not claimed. The source uses the
four pinned original payload codecs; the source comparison does not execute them
or establish native transport compatibility. No default Duration, HAT omission,
synthetic success, identity hop or retry is added.

Endpoint close does not open or close the shared Owner. Already admitted calls
may continue; only admitted Java onTransact stacks are counted. The original
Binder wrapper can serialize errors and recycle borrowed Parcels after that
stack ends. Idle grants no reply-delivery, queue/native drain or disposal proof.
Final references retain the Owner while the endpoint lives; actual process-life
retention and genuine guest handle delivery remain controller obligations.
UID1000, descriptor, raw Binder and loader checks restrict the profile without
proving source/caller/physical-subject authority.

The SDK receipt efc0a287 contains exactly two fresh definitions in DEX cc5e435a
(7,652 bytes), fifteen individually pinned current dependencies and three excluded
compiler-only ABI projections. Independent inspection checked 36 snapshots,
five staged sources and twenty classfiles, DEX checksums/closure and all three
source-defined command vectors. Current Bindingf7 dependencies are explicit;
older Binding9ec SDK evidence was not substituted. Recorded SDK37/D8 warnings
remain PC limitations, not Android/hidden-API acceptance.

The separate model receipt 9595ee57 records five successful commands and actual
42/312 output. Independent saved inspection checked 100 project snapshots, two
canonical JDK snapshots, 75 staged sources, all 173 classfiles and six unchanged
class maps (program2/deps15/F70/C48/control1/tests37). All command vectors match
reviewed source ordering, with bounded logs, reaped direct children and no
recorded reader/cleanup failure. No production compile, D8 or shaping occurred
in this model run. Compiler projections are distinct from the authored boundary
models and absent from program/dependency runtime artifacts.

The models deliberately use boolean/marker token Parcels and direct Binder
calls, not OEM wire/HAT/Duration algorithms or native exception framing. They
exercise refusal, nullable return, exact local errors, cleanup, concurrent/reentrant
frames, shared Owner independence and Owner-idle while a reply stack remains
active. The harness tracks/releases/joins workers; an uncertain join retains
owners/loaders and cannot yield PASS. Its successful cleanup is authored-model
evidence, never native-worker or original-authority drain.

Pre-use review corrected live-path helper loading and role binding in the SDK
runner, uncertain-join cleanup in the harness, and external JDK retention/recheck
in the model runner. Original packets and own inspection corrections remain
preserved. No target workflow was replayed by the reviewer. Parent-reported
terminal observations are labeled as such, not represented as raw transcripts.

Real guest issuer/routing, caller and worker physical-subject admission,
continuous original/native custody, outer RPC lifetime and complete reciprocal
PIN/fingerprint/key/data outcomes remain unassembled or unverified. Legitimate
stock requests can continue on the same retained Samsung authority; this adapter
adds no global drain prerequisite merely for a presentation switch. Source-phase
report copies preserve exact hashes with honest after-execution/before-publication
timing. No runtime activation or phone action is accepted.

The immutable execution configuration remains inventory/retained-pin-endpoint-tests.json
(36469ff1), preserving the exact reviewed runner/gate binding. Actual status lives
in the separate retained-pin-endpoint-tests-actual.json; its historical preparation
status and earlier documentation pin are not presented as current test results.
The final author delivery529 and exact22 normal-file list were independently
rehashed. This publication references only immutable private proofs, without a
mutual review-hash cycle.
