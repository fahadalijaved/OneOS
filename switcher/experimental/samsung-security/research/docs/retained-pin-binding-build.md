# Retained PIN binding: PC build and authored models

The one root-authorized run passed: exactly four new SDK-compiled class52
definitions and four DEX definitions, with313 checks across82 authored scenarios.
The four old capture SDK classes remained byte-identical. This is PC component
and model evidence, not working Android PIN verification. ColorOS's bed11a4d
prebuild review preceded root's separate cc1d14de go. The actual command was:
`python -B tools/build_retained_pin_binding.py --build`.
There is no automatic build or test path, phone operation, OEM invocation or
native DLL supplied to the worlds.
The e9b5/8afb/31fd source-phase report/inventory/freeze are preserved under
`out/retained-pin-binding-build/history/source-only-before-actual-a030d221/`.

Only `PreparedRetainedPinBinding.java`32c76cfe is a production compiler input.
The actual output is exactly four Java8/class52 definitions: the outer class,
`$Current`, `$Subject` and `$Metadata`. The frozen first-party class-name/shape
parsers established the actual names, file paths, flags and members. Any
additional definition, including an empty synthetic marker, refuses; the runner
does not switch Java versions or silently discard classes.

The registry capture's two actual SDK classes8c23983a/096443d1 and family's two
actual SDK classesdcf55c45/963c3e94 are literal inputs, bound to original
receipts52068829/e2bf02e8. Their exact two-file original directories and receipt
class maps are checked, and fresh dependency directories receive byte-identical
copies. Original sources521ebfdf/74ac4249 are protected inputs, never compiled.
No pass boolean substitutes for the literal class/receipt identity. These four
classes are compiler/D8 classpath metadata and actual runtime dependencies;
they are never modeled replacements or D8 program definitions.

Javac uses the existing pinned JDK, SDK37 bootclasspath, source8/target8,
`-proc:none`, `-implicit:none` and an empty sourcepath. No hidden-ABI projection
is needed for this reflective binding. D8 sees only the four newly compiled
class files as program inputs, the four old classes as classpath and SDK as
library. Ordinary DEX039 integrity and the exact four new definitions are
mandatory. SDK, OEM, old captures and fixture classes are excluded. The known
API37/maximum36 D8 diagnostic is required in the saved output, not waived.

The immutable MODEL-BASE01402a24 supplies39 existing first-party Java world
sources from the old e2bf run. It is data; neither old producer is invoked.
Trust's three new templates are overrides069b05b4, Worldaa43d89a and Test4292e34e.
Twelve JSON overrides replace four baseline paths and add eight. Together with
the new world and test, the complete intended staged cohort is50 Java files:
one production,23 framework F,25 server C and one test launcher. Raw pinned base,
production, World and Test bytes are preserved; each JSON text gets one appended
LF. All paths and intended byte hashes are checked before the first compiler,
saved in PRECOMPILER, and freshly enumerated afterward.

Framework fixtures compile on the JDK alone. Server worlds compile against F;
the test launcher also compiles against F. Before runtime, every compiled file
must be a class52 file whose binary name matches its path and intended fixture
namespace. Complete maps are saved for new classes, both old-class copies and
all three model class directories. Runtime's parent classpath is only tests+F;
the authored launcher creates C and O, where O receives the unchanged new SDK
classes and both unchanged old SDK capture pairs. SDK, D8, DEX, compiler API
and OEM bytes are absent from runtime paths. The native-library directory must
remain empty; no fake native DLL is created or loaded.

The actual binding mechanics are exercised by synthetic current users0/3/7,
including user0 with serial41, both permitted modeled lifecycle states, record/
serial/type/marker mutations, container/trap replacement, same local UMS and
private endpoint relationships, classloader/thread refusal and post-observer
drift. Monitor models assert the correct lock without nesting. The held retained
old-monitor cases require refusal before acquisition after a lock field changes,
with bounded release/join cleanup. These are object/ownership/selection tests,
not a mocked PIN verifier or authentication result.

The frozen828fb9ef command helper uses its reviewed private-clientadfa recipe:
own cwd, JVM temp/home, empty native path,512MiB heap, five inherited JVM/compiler
option variables removed,45-second commands and2MiB logs. Generated artifacts
and receipts stay under ignored `out/retained-pin-binding-build`. PREMODEL saves
actual class maps before the one test-main invocation; success requires fresh
source/class/DEX/dependency maps and input/producer hashes afterward. Failure
saves its receipt and stops, without automatic repair or rerun.

The saved actual run is
`out/retained-pin-binding-build/20261106T084412502587Z-a030d221108f4e1e83eeb0e12be55c85/receipt.json`,
SHA256 `3fc115d817ed6b102b4db50ecc8d9740ecda82db3078dd87fe839e5912346c9d`.
Its12,868-byte DEX039 is SHA256
`eb28d9d9ff55a5776b9e16523f4a8153a133dc31ce561fce23c5d6d895a404d4`.
All six commands exited0, without a retry or harness/source fix. Four compiler
invocations produced the new binding and authored F/C/test worlds; D8 ran once
and the authored test main ran once. Compiled model maps contain28 F,45 C and13
test classes. Complete50-source and new/old/model class closures matched freshly
before and after execution. The old source/classes/receipts were unchanged.

Actual diagnostics retain the D8 API37/max36 warning, Java8 source/target
obsolescence warnings, the host model bootstrap-classpath warning and the test's
deprecated-reflection note. They are not Android/API37 compiler acceptance.
Only authored Java model/binding/capture code executed, with own F/C types and
JDK dependencies; no SDK implementation, OEM code, Android native library or
phone operation ran.

ColorOS independently checked the saved class/DEX bytes, complete maps and
commands without replay. Immutable proof is
`out/retained-pin-binding-review/actual-output-check.json`, SHA256
`56630930676a3aa24b391e340cd005e36a89940b198ca000a1921ad26a9aa46a`.
Its direct class-code read confirms the guard before monitor acquisition and
each modeled container access, with monitor cleanup handlers present.

This pass establishes authored mechanics and compiler isolation only. It does
not establish genuine Android source admission, Binder delivery,
hidden-API/ART access, current user/policy epochs, native/CE leases, PIN/HAT/key
acceptance, guest client creation, endpoint publication or real cleanup/drain.
All existing captures, client, diagnostic and root checkpoint remain unchanged.
