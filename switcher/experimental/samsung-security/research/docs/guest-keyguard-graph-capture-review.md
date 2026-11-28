# Guest keyguard graph capture: independent PC output review

**PASS for the authored SDK37 compilation and isolated DEX only.** One producer workflow, receipt `7be55157`, compiled source `d32795c6` into two fresh Java8 class files and a 12,312-byte DEX `364852bb`. Both saved compiler/D8 results exited0. This review read saved inputs and bytes; it did not recompile, invoke D8, execute models or load/run the helper, SDK/OEM or native code. The component remains unselected, with no device action or Android acceptance.

The source gate is immutable `47b095b9`. Its constrained API has only opaque `captureExisting()/checkStillBound()`,24 exact declaring Fields and twelve retained graph references, including a deliberately nullable service identity. No getter, readiness/user scalar, raw owner or invocation handle is exported. Whole-source review and the exact pre-use final-root correction are preserved separately; no old source/API PASS is substituted for actual emitted evidence.

The saved javac command compiles exactly one staged source with SDK37 as bootclasspath, an empty program classpath, disabled annotation processing and implicit compilation, and source/target8. D8 receives exactly the two fresh class files as program inputs and android.jar only as a library. Independent class and DEX decoding confirms the outer/Metadata definition closure, Java class version52 and the public two-method API. SDK, original service, projected OEM and model definitions are absent from program output. DEX039 header, SHA-1 and Adler32 checks pass. The saved D8 warning says API37 is unsupported and requests36 or earlier; emitted output does not resolve that limitation.

Independent class-file and DEX instruction decoding resolves compiler-generated access bridges and checks the actual final order:

| Method | Java byte offsets: placement → roots | DEX code-unit PCs: placement → roots |
| --- | --- | --- |
| captureExisting | 22 → 27 | 16 → 19 |
| checkStillBound | 39 → 50 | 29 → 36 |
| Metadata.readOwners | 452 → 458 | 281 → 284 |

No later invocation follows these selected checks, except the outer capture object's own constructor in the factory. The compiled original-map monitor contains only cached field reads/identity guards and two canonical ArrayMap.get calls in both formats. There is no placement/graph checker, class loading, policy/backend operation or original getService call under that monitor. These checks establish selected emitted ordering, not atomic all-field consistency or general compiler/runtime correctness.

The actual34-file build freeze and all12 executed input snapshots were rehashed. The executed driver, manifest, root GO, staged Java and source snapshot match their receipt identities; the two class hashes and DEX definition inventory match independently decoded bytes. Saved argv, logs, bounded-drain/reap records and all five JVM/classpath environment removals were checked. The authoritative terminal records one run, no retry and exit0; the actual build comprises javac and D8 only, with modelsExecuted=false.

Before the build, source-phase author reports `ca0da2dc`/`16cf222b` and manifest `68f5e0dc` were copied into immutable build-plan inputs and again into the executed run's snapshots. Those exact bytes remain the execution evidence. Later status reports must not be represented as compiled inputs. The earlier source-only review/FROZEN and initial97b beforeimages remain unchanged. This review's first private decoder had a Python syntax-spacing error before any input read; that script is retained, and the corrected static decoder produced the independent readback. There was no producer or artifact retry.

Actual guest bootstrap/code and vendor-loader admission, ART access, original policy-init normal-return issuer, selected-user/connection callback acknowledgement, source-loss subscription and native/policy ownership remain external or unimplemented. Observed references and loader identities grant no operation, lifetime or authentication lease. The immutable [saved-output proof](../out/guest-keyguard-graph-capture-review/actual/actual-output-check.json) records these component limits directly, without a mutual normal-report dependency.
