# Rerunnable parent-client model checks

The single relocated replay passed all49 unchanged authored cases with exit0.
Its immutable receipt is
`out/guest-metrics-parent-client-tests/20261106T005252672270Z-a7513178bfb641adac60ef538c89acea/receipt.json`,
SHA256 `9c5a99d0270d40d826b17f52a01f01a275f357afe39a19208c41e1877bdbfeb0`.
The paired [inventory](../inventory/guest-metrics-parent-client-tests.json)
records exact before/after source, tool, template, class and JDK pins.

Run from this project using the existing Python and JDK:

```powershell
python -B tools/test_guest_metrics_parent_client.py
```

The runner requires the exact four already-compiled production class files under
`out/guest-metrics-parent-client/20261105T235945104798Z-9318f0db5aed41c8a447d3bd6228c646/classes`.
It refuses missing or mismatched inputs and never recompiles production. Those
ignored inputs were built with **SDK37 plus the source-pinned compiler-only
hidden Parcel ABI projection**. This qualification remains intact; the test
does not establish official public-SDK coverage, hidden-API or ART acceptance.
Production source remains `d4096fa5...`; the existing builder, implementation
review and all earlier plain/parent-client sources and receipts are unchanged.

Five authored templates under `compat/tests/guestmetricsparentclient/` are exact
byte copies of the final independent49-case probe's staged sources, identified
by historical receipt `b1c413b7...`. The ParentClientProbe harness and four
android.os API-name models are entirely authored; no SDK/OEM implementation is
copied. Literal hashes configure the runner. Historical receipt hashes are
provenance only and do not supply moving configuration.

The existing cases exercise plain, AppOps and StrictMode outer framing; nullable,
odd/even and Unicode String16 models; full outer violation vectors and opaque
serialized spans; exact65,536-byte success; rejected counts, sizes, terminators
and native-object-range models; once-only modeled decoder effects and subsequent
cursor/size/envelope rechecks; ordinary error-tail preservation; original failure
identity; first/second acquisition and both cleanup attempts; absent accessors,
raw int/DPI bits, nested reads and overlapping same-client reads. Their logic
has not been expanded or changed. Opaque blob bytes are placeholders, not real
serialized Violation objects.

Only the templates compile, with source/target8, annotation processing and
implicit compilation disabled. Exactly nine authored model classes are admitted,
including five android.os model definitions. Original/staged production bytes
are checked against literal hashes; all compiled/staged classes have their
actual binary identities checked. The four unchanged production classes and
fresh authored model output are the complete runtime classpath. No android.jar,
compiler projection, OEM archive/class or JNI is admitted at runtime. The direct
canonical range predicate calls resolve to **models** during this test.

Each javac/javap/java subprocess uses the existing pinned bounded command helper:
all five JVM/compiler/classpath option environment inputs are removed
case-insensitively, cwd/TMP/TEMP/JVM home/temp belong to its unique run, the
application native-library directory is empty, the timeout is45seconds and
combined streaming output is capped at2MiB. Global environment settings are not
changed. The actual compiled cleanup contour also confirms addSuppressed at27
is covered by Throwable25..30→33, without a cleanup athrow or generic-rethrow
cast. That is static bytecode evidence; no JDK suppression hook or heap
exhaustion is used.

Native Parcel strings, serialized class compatibility, native sidecars and
predicates, Binder/exception behavior, policy effects, BOOT/hidden-API admission,
the genuine DMS parent/source epoch and parent/consumer lifetime remain open.
Passing authored packets do not attest Android interoperability, authority or
security acceptance. See the frozen
[implementation review](guest-metrics-parent-client-review.md).
