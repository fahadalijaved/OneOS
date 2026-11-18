# Independent reproducible guest-metrics harness review

Accepted as a rerunnable authored JDK model harness for the exact reviewed SDK
artifact. This is not Android, Binder/native identity, live DMS, source/epoch or
Samsung metrics acceptance. No old producer, source audit, SDK build or complete
test suite was rerun by this reviewer.

The runner and all twelve templates were read. The five base and seven malformed
fixture templates are plainly authored and byte-identical to the earlier probe,
including their historical source hashes. Their android/DisplayInfo/DMS names
provide model linkage, not SDK or OEM implementations. They remain .java.template
files; executable/generated sources are materialized only in the fresh out run.

## Exact production and test boundaries

The required source72b0f4cd and immutable SDK build receipt cc4a619a identify the
actual three compiled production classes. The runner copies those bytes and
never compiles the producer against fixtures. Independent metadata checks
confirmed original SDK and staged class hashes/bytes match: producer, scalar
Sample and its empty synthetic access marker. A different build/profile requires
reviewed pins; this is not a portable arbitrary-artifact admission mechanism.

Runtime application classpaths contain only staged production and authored
fixture/variant directories in the unique run. Variant directories deliberately
precede base fixtures for the three malformed shapes. No android.jar, OEM archive
or Android/OEM JNI is added. The native-library directory is empty; normal real
JDK/JVM execution remains. Exact class allowlists still reject extra definitions.
The separately allowed variant DMS$1 is justified: all three actual265-byte
classes are identical synthetic Object subclasses, flags0x1020, with no interface,
field or method. Allowing that exact marker does not replace the remaining guards.

The checks exercise unchanged production logic: one getter call, exact original
Throwable identity despite modeled drift, null/wrong-display/subclass behavior,
UID/PID drift including the final scalar fence, raw Java numeric bits, immutable
scalar retention, prepared metadata reuse, nested invocation and overlapping
threads. The reported27 checks include the five Sample-field checks; they are
not27 independent Android scenarios. Separate static-getter, wrong-return-name
and wrong-field-type models must fail preparation. No production mutation,
authentication simulation or real subject verification is claimed.

## Concrete containment corrections

Two narrow corrections were requested and incorporated:

- Child processes now use cwd=work. Relative JVM diagnostics therefore remain
  anchored to the unique run alongside explicit TMP/TEMP/JVM temporary home.
- The cleared option variables now include JDK_JAVAC_OPTIONS. Static disassembly
  of this installed JDK's compiler Main shows its read at80 and CommandLine.parse
  at86. The original four-variable cleanup omitted this compiler input.

The complete runner diff from the initial submitted snapshot is exactly those
two lines. Fixtures, production classes and all27+3 cases remain unchanged.
Historical snapshots/receipts were retained. The author performed the focused
corrected rerun successfully; this review checked that immutable receipt and
actual stdout hashes rather than rerunning it.

Compilation remains proc:none/implicit:none; runtime directories, explicit Java
options and five removed inherited option variables bound the model application
inputs. Before/after guards use explicit exceptions, not removable Python assert
statements. Source/tool/doc/templates/JDK, original and staged production classes,
fixture classes, generated template bytes and available frozen inputs are checked.
Fourteen existing producer/build/review files matched their recorded hashes.
Generated sources/classes/logs/receipts stay in out; the test's authored inventory
is the intentional normal-file output. No production or historical file is edited.

## Disposition

No remaining material harness defect was found. The review inventory pins the
corrected runner, report, test inventory, twelve templates, exact production
inputs and immutable current run. Ignored evidence records the independent hash,
class-header, classpath, stdout and JDK-option checks. Models establish extractor
mechanics only: actual code/receiver/lifetime/currentness, Binder permissions,
DMS/native/ART behavior and Samsung sandbox/configuration/compatibility/boot
integration remain external. Quiet-NaN bits are Java-value observations, not a
native-memory or untested signaling-NaN guarantee. All device/security acceptance
remains pending. No phone, OEM/Android code, native DMS or Git action occurred.
