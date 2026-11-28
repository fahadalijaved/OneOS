# Prepared seven-helper bundle

This unselected packaging step combines seven already compiled authored helper
definitions into a separate DEX/JAR. It does not modify the original services
archive, select a class loader, emit source hooks or enable the projection.

The literal inputs are the three SDK classes from the fixed-OFF parent-cell
build receipt `95b5d928249b093a1a878143939fb911c7b93dbebc284b18942603a9b14ebf1f`
and the four SDK classes from the sanitized producer/endpoint receipt
`70fd78a9cb122ecf6db119bad5738a3473eef71a9c66c461b6c9c560487c9627`:

- `PreparedGuestMetricsParentCell`, its `PhaseDisposition` and
  `RetirementDisposition` enums.
- `PreparedGuestMetricsProducer`, its immutable `Sample` and the original
  empty Java 8 `$1` access marker, plus `PreparedGuestMetricsEndpoint`.

The builder pins every original class byte sequence, both immutable receipt
files, the existing JDK Java executable, SDK 37 library, D8 JAR and pure inspection
helper. It copies only these seven classes into an exclusive output directory;
there is no javac command or source recompilation. The SDK JAR is D8 library
input only. Compiler API classes, authored dependency models, tests, OEM classes
and ParentClient are excluded from program inputs and emitted definitions.

`tools/build_guest_metrics_helper_bundle.py` requires an explicit reviewed
source freeze under `out/guest-metrics-helper-bundle/`. It strips `CLASSPATH`,
`JAVA_TOOL_OPTIONS`, `_JAVA_OPTIONS`, `JDK_JAVA_OPTIONS` and
`JDK_JAVAC_OPTIONS` from the child environment. Cwd, TMP, TEMP, JVM temporary
directory and JVM user home belong to its unique output directory. D8 has a
45-second timeout, bounded termination wait and 2 MiB combined output limit.
Original inputs/tools and the seven copied classes are checked before and after.

The output checks require exactly the seven expected DEX definitions, valid
DEX header/checksums, and the exact five public fixed-OFF cell bodies. A bounded
Cell-only parser verifies null/false literal returns and the two enum types'
`OFF` returns, without reading absent class data on the empty `$1` marker. It
also requires the five private controller bodies to remain private and present;
none is executed by this build. The deterministic stored JAR contains only
`classes.dex`. Actual D8 diagnostics, including its SDK 37/maximum 36 warning,
belong to the immutable run receipt; emission is not API 37/ART acceptance.

H reviewed the complete runner `f4e4d43d…` and this card before the authorized
single D8-only run. The outer process and D8 exited 0. Exactly seven authored
definitions were emitted; all original/copy/tool pins remained stable. The
Cell-only byte proof passed for all five public fixed-OFF wrappers and retained
the five private controllers without executing them. The run used:

```text
python -B tools/build_guest_metrics_helper_bundle.py --freeze out/guest-metrics-helper-bundle/SOURCE-FREEZE.json
```

The immutable receipt is
`out/guest-metrics-helper-bundle/20261106T010206436165Z-b58fefe14ac64199be1948e64047da4e/receipt.json`,
SHA256 `fdd4f61908be3ff473654d6121b625a942dcd91468df6a4fa5fcfc6eac6c5504`.
The [inventory](../inventory/guest-metrics-helper-bundle.json) is its identical
derived copy. The 14,292-byte DEX has SHA256
`11fd05dcd1a69ce6b8fb0e585f5ae573c8cbadc929713a29afcf36d0831dc7c8`;
the 14,412-byte single-entry JAR has SHA256
`6cdfca8588e457ceb30ba2ecfd47e65b2da93e34952b054e8b754dced8920e10`.
The actual warning was: “An API level of 37 is not supported by this compiler.
Please use an API level of 36 or earlier.” No repeat build was needed.

The seven guest helpers have a future separate-DEX, same-actual-DMS-services-loader
placement contract. Source/code/native/profile/current-parent and retirement
admission remain unassembled. ParentClient has a separate future BOOT/caller
realm and is not included here. No Android helper, dependency model, OEM code,
JNI, service, phone or runtime candidate executes in this packaging step.
