# Guest policy-init completion: independent source review

The implementation, SDK/D8 output and corrected authored model workflow pass
independent source/saved-output review. The actual model result is 14 cases and
122 checks. This remains an unselected PC component result, not an emitted
retarget, Android or native acceptance result.

The [private source proof](../out/guest-policy-init-completion-review/SOURCE-PASS.json)
(`66ef85e7`) pins helper5eecae58, Graph9e11d7a0 and projections e7d42b36/e7580d3b.
Removing only the approved package-private graph comparison bridge reproduces
the preserved d32795c6 graph source text; existing capture/check algorithms are
unchanged. That does not transfer the old graph's compiled artifacts to the
changed source.

The wrapper contains one unconditional direct virtual `policy.init(context,
window)` call per entered wrapper. It preserves original arguments, thread and
dispatch. Its finally path contains observer failures, so the exact original
Throwable propagates without wrapping or suppression. Disabled, failed,
duplicate and reentrant observation do not skip or retry the original call.
The wrapper is effectful if activated: it forwards real policy initialization.
Only the review was read-only; no original operation executed here.

Global entry history and activity begin even when no observer is installed.
Late/racing preparation refuses. Saturated counters poison observation rather
than becoming an accepted zero. Unique normal return, unchanged source tuple,
same slot and no active invocation are required to publish the private immutable
record. Duplicate/reentrant/late/failed entry poisons the one-shot state. No
public ready setter, raw record/owner getter or reset/rearm path exists.

Main controls reject a wrong thread before acquiring their busy fence. The
original init, reflection metadata work and graph bridge run outside the
observer lock. After graph checks, the same slot, phase, busy state, entry count,
activity, private occurrence and retained graph are checked again before
success. Reentry cannot clear another acquired control fence. Logical close
retains owners and retires observation; it cancels or drains no original work.

Metadata preparation uses the admitted initialized main/C/F source cohort and
three individually prepared read fields: private-static cached SystemServer
loader (flags10), declaring WMS.mPolicy (0), and declaring WMS.mContext (16).
Their actual saved declarations were checked. Preparation uses no live
WMS/WMG/map/graph, backend constructor, provider or original init invocation.
The invocation checks use WMS's declaring context, not the Oplus shadow or
pre-init PWM/extension/delegate fields.

The actual selected policy interface is public/abstract/interface1537, extends
canonical framework WindowManagerPolicyConstants, and declares the public
abstract init descriptor1025. The nested funcs and framework constants are also
interfaces1537. Two projection Java files preserve those three declarations
and the used method while explicitly omitting unused members. They contain no
implementations. Saved build evidence now proves all three projection definitions excluded
from program DEX. Runtime used separately compiled first-party interfaces,
not the compiler-projection directory or android.jar. The three abstract model
interface classfiles are byte-identical to the compiler ABI classes; provenance
and actual classpaths distinguish them, not byte inequality.

The required topology is actual services C for helper, graph and policy/funcs,
with canonical framework classes. Loader consistency is not code/source
attestation. The exact first-call retarget, helper resolution before entry,
admitted source placement and ART/private-field access remain external gates.
The actual compiler/DEX closure is helper3 plus Graph2: five classfile52
definitions and exactly five ordinary DEX039 definitions, 19,988 bytes, hash
47bbb120. Compiler ABI output contains the separate three interfaces. SDK37
compilation used source/target8; the known D8 API37-unsupported/max36 warning
remains recorded. This does not establish Android API or runtime acceptance.

This records one synchronous policy.init normal return. It proves neither
WMS.onInitReady/boot completion nor posted work, SystemUI/user/connection,
native policy, authentication or an atomic lifetime lease. Separate fixture and actual-workflow reviews are recorded below. The reviewer
ran no compiler, models, OEM/Android code, network or phone/ADB operation and
changed no shared production sources.


The SDK receipt7fb7e587 and its54-pin saved freeze were rehashed along with
16 retained input snapshots and four staged Java files. Independent classfile
and DEX parsing confirms the five program definitions and three ABI interfaces.
The actual helper bytecode has exactly one interface init call (three argument
words) covered by a catch-all finally region. The graph calls occur outside the
helper's inline monitor regions. Three recorded compiler/D8 commands returned0;
the independently captured outer terminal is0. No Java tool was replayed.

The first model attempt failed at driver compilation: an unbraced case9 local
`graph` conflicted with a case11 declaration. This peer source review missed
that Java scope error. Failed receipt4e964d78 and its no-model-JVM artifacts
remain preserved; the original bf39 fixture/fbb source pass is historical.
The only correction renames the case11 local and its two uses, adding21 bytes.
All other25 sources and test contracts remain unchanged. The corrected
26dea5f9/80a33ddf source received separate delta review2d9cd9e0 and a separately
authorized workflow. No failed attempt is relabeled as passing.

Corrected receipt91c3acdd records14 cases/122 checks and five commands0. Saved
readback rehashed153 frozen entries,52 retained snapshots and26 staged sources.
Program5 originals/copies remain byte-equal to the SDK result. Actual model
classes are F17/C16/V4/driver5;24 declaring fields and four natural synthetic
parent fields, InnerClasses/EnclosingMethod and interface ancestry were
independently parsed. There was no SDK recompile or classfile shaping. The
runtime argv uses only its JDK driver and owned program/F/C/V paths with -Xint;
the helpers and typed policy belong to C, Constants to F, and vendor to V!=C.
Models implement synthetic field/link/counter behavior, not original policy or
Android Handler scheduling. Only the selected14 cases are covered; broader
model-plan categories and saturation/allocation failure stay outside this run.

Stable private evidence is SDK proofd5bfd267 and model proof994d086f. Source-phase
peer cards da12750f/43801880 and their freeze3604935f were copied and verified
before this actual-status update under the peer history directory. Current
normal cards depend only on immutable private evidence; no reciprocal author
normal-report hash cycle is introduced.
