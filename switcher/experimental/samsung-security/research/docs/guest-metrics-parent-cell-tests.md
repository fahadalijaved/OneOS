# Parent cell: isolated authored dependency models

**PASS: 184 checks in fourteen fresh-loader scenarios, one reviewed compile/model run.** This successor harness tests the unchanged three actual SDK-compiled `PreparedGuestMetricsParentCell` classes. The public artifact remains fixed OFF. Private controller methods are invoked explicitly by reflection under dependency **models**, not a public ON build, Android runtime or genuine DMS.

All nine authored Java templates are under `compat/tests/guestmetricsparentcell/`; the runner is `tools/test_guest_metrics_parent_cell.py`. H reviewed those sources before the one bounded compile/model run. A pre-run provenance correction added staged-source/modelclass hashes; no unreviewed run occurred. No production source, bytecode, proposal, helper, DEX or build was changed/recompiled. No production mode/fault hook or field setter was added or used.

## Exact runtime boundary

The literal production input is the three SDK classes from the accepted `20261105T235347266409Z-c8e784b363294f2983b35a5462234d4a` build, receipt SHA256 `95b5d928249b093a1a878143939fb911c7b93dbebc284b18942603a9b14ebf1f`. The input class hashes are Cell`49d73046…`, PhaseDisposition`39582244…` and RetirementDisposition`c6563236…`, recorded in full by the runner/receipt. They are copied byte-for-byte into an owned input directory and checked before/after.

Runtime consists only of those classes, thirteen explicitly authored model/driver definitions and JDK. There is **no android.jar, frozen compiled Producer/Endpoint implementation or OEM code on runtime classpath**. The modeled Android API names are labeled PC models in their sources. They match the ABI used by the cell and supply controlled scheduling/faults; they do not implement original reflection, caller identity, Parcel framing or endpoint protocol/policy.

Each of fourteen scenarios gets a fresh URLClassLoader with the JDK platform loader as parent. All three cell classes and the model/control types must resolve in that child; the application loader is not its parent. Owned workers are joined before closing each case loader. This isolation resets class-owned claims naturally; no production static field is reset.

## Finite assertions to exercise

| Scenario | Bug it should distinguish |
| --- | --- |
| Public OFF | All five wrappers short-circuit null/invalid inputs, no owner claim or model call. Instance dispatch uses a separately labeled synthetic private-constructor object; that object's retention is not OFF factory evidence. |
| Preclaim retirement / phase before capture | Missing tombstone, accepting late capture or phase100 without its source-order prerequisite. |
| Ordinary lifecycle/refusals | Duplicate capture/phase, wrong owner/born pair, altered borrowed packet/flags/code, false→success, repeated retirement. |
| Preparation failure | Losing the failed claim, constructing a second backend or treating failure as ready. |
| Retire during preparation | COMPLETE while preparation can still create an Endpoint. |
| Late Endpoint | Failure to adopt/retire the exact object returned after retirement was requested. |
| Phase while preparing | Queued implicit late activation instead of terminal refusal. |
| Retire during activation | ACTIVE commit after a normal activation call returns late; lost activation credit despite retire acknowledgement. |
| Activation failure | Repeated activation or failed state becoming dispatchable. |
| Retire during admitted dispatch | Dropping the use credit after Endpoint retirement, before the actual local call returns. A previously admitted model result may finish later. |
| Blocked retire | COMPLETE before the exact retirement action returns normally, or retrying while it is in flight. |
| Uncertain cleanup with primary fault | Inferring success from model state despite a thrown post-state fault, retrying uncertainty, losing retained objects or masking the exact primary dispatch exception. |
| Foreign-thread/reentrant seams | Holding owner lock across Producer.prepare, Endpoint.prepare/activate/protocolBinder/transact/retire; same-thread duplicate capture and wrong-owner callbacks taking over. |

Latches place the actual controller at each dependency seam; tests assert PENDING and action counts while the worker is blocked, then release/join it. A separate foreign thread tries status admission at each seam. Same-thread reentry alone would not detect a held reentrant Java monitor. Probe failures are retained in the **model control**, so production containment cannot hide a failed lock probe.

The model Endpoint's configurable post-state fault exercises the cell's acknowledgement/UNCERTAIN handling. It does not inject an error into the frozen real Endpoint or demonstrate VM failure handling. No exhaustive asynchronous interleaving/native fault/GC/Android identity or source-admission coverage is claimed. Not-practical actual Endpoint failure contours remain source/byte-review evidence.

## Execution controls and evidence

The explicit source freeze pins the nine templates and test runner. Before execution it must carry the actual H/root review reference. `--check-only` validates pins without compiling/running; the normal `--freeze` command compiles only authored fixtures against the copied three cell classes, then runs the JDK-only driver. It refuses unexpected model definitions or emitted cell duplicates. Sourcepath discovery, processors and implicit source compilation are disabled.

Both child commands strip the five JVM/compiler environment variables and use explicit pinned JDK paths, unique owned cwd, task-local TMP/TEMP/JVM home/tmp, a45-second deadline and2MiB combined output bound. Every source/tool/original SDK/copy pin is rechecked afterward. Logs, copied inputs, model classes and result receipts belong only to ignored `out/guest-metrics-parent-cell-tests/`.

The staged `.java` bytes are checked against the exact reviewed templates before compilation and after execution. All thirteen model/driver class hashes are captured before execution and rechecked afterward, separately from the three immutable SDK cell copies. The receipt records each map; original-template stability alone does not stand in for staged/compiled-byte stability.

The [inventory](../inventory/guest-metrics-parent-cell-tests.json) separates public OFF evidence from the private-entry model cases. Model counts are not Android, public ON, parent/source/phase/loader authority, native/global drain, Samsung metrics, PIN/FP/crypto/CE or device acceptance.

## Actual result

The one outer harness process exited0; authored-fixture javac and model JVM each exited0. Receipt: `out/guest-metrics-parent-cell-tests/20261106T001452002178Z-00c773da29a64b2283da8697f2f0f326/receipt.json`, SHA256 `e641700896803877b8380376ed2049c05d340c56b3d401027afa550297a2d4d6`. The immutable reviewed source freeze is SHA256 `0e83df86cd350063c8333978a07733a9f53a41eb9497c255f6e8bac20afa0e5b`; the runner is `f999a60e81b822edef33619b1683440dcbac3f871fc6e7a6eacbbcbe5b17c5f4`.

One public OFF scenario passed8 checks, including the separately labeled synthetic private-constructor dispatch fixture. Thirteen explicitly reflected private-controller scenarios passed176 checks. Every case verified the fresh platform-parent child realm; all owned model workers returned. The six foreign-thread probes completed, and the exact primary modeled dispatch exception survived the model's post-state retirement fault and retained UNCERTAIN disposition without retry.

All nine staged source hashes, thirteen compiled model/driver class hashes, original SDK input pins and three byte-identical copied SDK classes were verified before/after. No frozen dependency implementation, android.jar or OEM code was on runtime classpath. Only fixture compilation occurred; no production class was recompiled. Java source8/bootstrap-classpath warnings are recorded. No repeat compile/model run was needed.

These results establish only the bounded public-OFF and private-controller mechanics under authored dependencies. Real Endpoint VM failure injection, all possible schedules, native Binder/caller/Parcel behavior, original DMS admission, public ON and the full security GOAL remain untested here. The harness verified its literal runner inputs before/after; H independently checked nineteen protected component, proposal, source and build files at that review snapshot. This evidence does not claim a check of the whole 377-artifact baseline.
