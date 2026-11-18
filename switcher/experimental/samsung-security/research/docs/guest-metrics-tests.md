# Reproducible authored guest-metrics tests

`tools/test_guest_metrics_producer.py` promotes the earlier independent probe into
a rerunnable PC tool. It uses the **same 27 checks and three malformed metadata
variants**, with no added production hook, changed producer, new source audit or
expanded test count. The reviewed producer, SDK/D8 build, independent review and
historical receipts remain inputs; this tool writes only its new test inventory
and generated `out/guest-metrics-tests/` runs.

Run from this nested project with the existing Python/JDK toolchain:

```powershell
python -B tools/test_guest_metrics_producer.py --build-receipt out/guest-metrics-producer-build/20261105T203639957947Z-2343ce1549274da5b453fe4fac510259/receipt.json
```

The receipt and production class files must already exist. The runner performs
no production rebuild, download, device operation or OEM execution. A different
artifact/profile needs a separately reviewed pin update; there is no arbitrary
caller-provided source/class hash or automatic acceptance of a newer build.

## Exact inputs and isolation

The fixed source SHA256 is
`72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7`.
The actual SDK37 build receipt SHA256 is
`cc4a619a9835ab409274887121ccacd19f2ab91516866234df8a3e3ab1af9d21`.
The runner checks the exact source/class manifest and all three compiled class
hashes, including javac's synthetic private-constructor marker. It copies those
unchanged class bytes into its own fresh run directory. It does not compile the
producer against model classes or modify the compiled producer.

The normal files under `compat/tests/guestmetrics/` are plainly authored model
templates, ending in `.java.template` so they are not ordinary production Java
inputs. They contain no copied Samsung/OPPO implementation or SDK runtime stub.
The five base templates and seven variant templates are byte-identical to the
earlier probe sources. The runner pins them explicitly, materializes `.java`
sources only inside its own out tree, and compiles those authored models/harnesses
using the existing JDK. The templates' matching Binder/DMS/DisplayInfo binary
names provide linkage to the unchanged authored production class; their behavior
is deliberately a model, not an Android or original-service implementation.

Application runtime classpaths contain only fresh staged fixture/variant classes
and the three pinned authored production classes. They contain **no android.jar,
OEM archive/class directory or Android/OEM JNI**. Inherited JVM/classpath option
variables are removed; the application native-library search path is an empty
directory within the run. Normal JDK/JVM execution is still real PC work.
All generated sources, classes, temporary files, stdout/stderr and receipts stay
in `out/guest-metrics-tests/<unique-run>/`.
Each compiler/JVM subprocess also runs with that unique directory as its working
directory, so relative crash/diagnostic outputs resolve there. The earlier
harness/receipt remains preserved under `out/guest-metrics-tests/history/` and
its original run directory; this containment correction changes no model or case.

## What the unchanged cases establish

The main probe checks one getter invocation, exact checked/runtime/Error Throwable
identity even after modeled caller drift, genuine null, wrong display and subclass
refusal, UID/PID drift before publication and after scalar loads, raw signed ints,
quiet-NaN payloads, negative zero, infinities/subnormal bits, immutable scalar-only
Sample retention, cached metadata identity, nested calls and overlapping threads.

The three separately compiled malformed models use a static getter, a return
class with correct fields but the wrong binary name, and a wrong scalar field
type. They must fail preparation. These variants change only authored fixtures;
they are not production mutations, alternative OEM behavior or authentication
simulations. Failure stops publication of a passing result.

The new [test inventory](../inventory/guest-metrics-tests.json) records the actual
relocated run, per-command logs, exact generated definitions, and before/after
source, tool, document, model, JDK, production-class and available frozen-input
pins. A per-run `receipt.json` and `FROZEN.json` retain immutable handles. Pin
guards use explicit exceptions and remain active with optimized Python. Repeated
runs use new output directories and leave earlier receipts unchanged. Historical
probe files are not needed to rerun: their identity is recorded only as a link
to the prior evidence.

This demonstrates authored extractor mechanics under JDK. It does not establish
real Binder/native identity, initialized DMS, installed code, source/epoch/current
subject, feature implementation, display freshness, ART/Android behavior, actual
metrics or security acceptance. DPI bits describe Java values; native-memory,
Parcelable and untested signaling-NaN equivalence are not claimed. Samsung
CompatSandbox/ResourcesManager/configuration/compatibility and boot integration
remain external, as documented in the unchanged
[producer review](guest-metrics-producer-review.md).
