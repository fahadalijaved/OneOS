# Rerunnable RAW client model checks

The single replay completed with exit0 and all45 checks passing. Its receipt is
`out/guest-metrics-client-tests/20261105T234155006880Z-555009d68b824755ab20e920141d67aa/receipt.json`,
SHA256 `384de17f0ef5667aafa4650701dc8a635ca548794152d416b47629d49bdf556c`.
The fixed three production class files and all admitted inputs were unchanged.

Run from this project with the existing Python/JDK:

```powershell
python -B tools/test_guest_metrics_client.py
```

The runner never compiles the production client. It verifies and stages the exact
three existing SDK37-compiled client class files from the immutable
`out/guest-metrics-client/20261105T232440065288Z-3b563848b00248948d801abbf4add9ff/classes`
directory. If these ignored inputs are unavailable, it refuses; this is a
replay of identified compiled bytes, not a source rebuild shortcut.

Five authored templates in `compat/tests/guestmetricsclient/` are byte-identical
copies authorized by their owner from the original independent 45-check review:
one ClientProbe harness and four android.os model sources. Compilation emits
11 authored model classes, including six android.os types. Literal source,
template, class and tool hashes configure admission; no moving build inventory
or receipt supplies configuration. The historical SDK and Table receipt hashes
are recorded as provenance only.

Only model sources are compiled, with source/target8, annotation processing and
implicit compilation disabled. Runtime classpath contains the staged three
production classes and authored models only: no android.jar, OEM classes,
producer, endpoint or Android native libraries. The existing pinned command
boundary strips CLASSPATH, JAVA_TOOL_OPTIONS, _JAVA_OPTIONS, JDK_JAVA_OPTIONS
and JDK_JAVAC_OPTIONS case-insensitively. Every subprocess uses a unique output
cwd, local TMP/TEMP/JVM home/temp, an empty application native-library directory,
a 45-second timeout and a combined streaming 2MiB output cap.

The unchanged cases exercise strict packet/header/count handling, genuine
absence versus sample projection, original exception identity, both cleanup
attempts, same-instance/disabled suppression, factory/write/recycle faults,
reentry and latch-controlled concurrency. Factory OutOfMemoryError objects are
synthetic faults, not actual heap exhaustion. Actual compiled javap instructions
also establish that addSuppressed at offset27 is covered by Throwable25..30→33;
no failure is injected into the final JDK method. This is a static catch-contour
proof separate from model execution.

Successful execution publishes a unique out receipt and the authored
[test inventory](../inventory/guest-metrics-client-tests.json), with before/after
source, original/staged production, model and JDK pins. The original review,
production build, source and class files remain untouched.

These checks do not execute native Parcel/Binder or establish UTF/string
serialization, Android exception headers, Binder death, VM exhaustion, genuine
endpoint/bootstrap/source-generation ownership or security acceptance.
AppOps/StrictMode headers remain unsupported and must be closed before an
integrated full-goal consumer. See the
[implementation review](guest-metrics-client-implementation-review.md).
