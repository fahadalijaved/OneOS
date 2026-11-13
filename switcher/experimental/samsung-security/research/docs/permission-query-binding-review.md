# Independent prepared permission-query binding review

Status: accepted as a corrected, unselected authored reference-binding component.
Runtime/source/endpoint/cache/BOOT admission remains open. This is a one-shot reference holder, not authority,
permission, cache, boot or Android acceptance. Earlier reviews and the frozen
one-method permission bridge remain unchanged.

## Source state and publication

The exact f0334b37 helper claims UNBOUND->BINDING under its private lock and
releases that lock before original Stub.asInterface conversion. The stored view
is not visible through get until BOUND. Competing and reentrant bind attempts
throw before the outer try, so a refused competitor cannot mark the legitimate
attempt FAILED. Reentrant get also refuses. If that refusal escapes conversion,
the outer attempt catches the same RuntimeException and publishes FAILED.

Null first input claims the attempt before throwing; null conversion and original
RuntimeException/Error also publish terminal FAILED. The original Runtime/Error
object is rethrown unchanged. No later bind or get can turn these failures into
success. No fallback, retry, permission query, identity change or service lookup
occurs. The contract does not claim an Android endpoint from interface shape.

Conversion happens without the helper lock. Success writes the exact nonnull
interface before the volatile BOUND write. A reader's volatile state read provides
visibility of that stored reference. Source/DEX access flags independently prove
that volatile field; the modeled reader tests are not a standalone memory-model
proof, since thread start/latch/join also add synchronization. Under this one-shot
normal control flow no admitted writer later replaces the reference. External
retirement/drain is still required; a previously returned view is not revocable.

## Tests and emitted component

The nine scenarios/42 checks use the actual SDK-compiled helper bytes unchanged.
The modeled original boundary is separate from the compiler-only hidden-API
declaration. Fresh child helper loaders give each scenario new static state
without a production reset/private-state hook; their parent exposes only authored
boundary models. The compiler declaration and SDK/OEM implementations are not
runtime substitutes. No Android loader or original Samsung Stub runs.

The selected fixture edges discriminate the intended failures: null must not
convert; Runtime/Error object identity survives reflection unwrapping; caught
reentrant refusal leaves the outer conversion able to succeed; uncaught refusal
terminates it. The competing-thread join happens while conversion is active,
so holding the helper lock across that boundary fails the case. The latch-held
case checks unready reads/binds and completion after release. Tests never call a
permission method to manufacture success; their view throws if that occurs.

The build uses a compiler-only selected IActivityManager/Stub declaration and
SDK bootclasspath for the helper, then passes only the helper class as D8 program
input. Runtime uses model-classes and the helper-only child directory; compile-api,
SDK, D8 and OEM directories are excluded. Static DEX integrity/definition/member
checks and unchanged helper class hash supply the emitted-identity evidence.
API37/max36 and Java8 compilation warnings remain actual limitations.

## Concrete correction and selection boundary

The initial builder's command environment inherited all JVM/compiler/classpath
options. Explicit classpaths alone do not exclude injected launch/compiler
options. The corrected builder clears CLASSPATH, JAVA_TOOL_OPTIONS, _JAVA_OPTIONS,
JDK_JAVA_OPTIONS and JDK_JAVAC_OPTIONS case-insensitively, with source/API/models
unchanged and the old receipt retained. Cwd is already the owned work directory. No other material
helper or builder defect was found in this bounded source pass.

Public bindOnce is not an ACL, source attestation or admission token. Bootstrap
must establish exact bridge/source/interface realm, current genuine AM/state,
actual caller/role/user/operation, cold/quiesced same-realm cache preparation,
boot-owner order/visibility and lifetime before first binding. This component
retargets no original PC0 or DEX reference table and installs no global/partial
ActivityManager singleton. The source client and actual endpoint must remain
owned through real work/death/drain; process retirement has no hot rebind API.

The inventory pins corrected source/build/test evidence. This reviewer
runs source/metadata checks only, not a compiler or model-suite rerun. Bound model
reference/concurrency behavior does not establish native identity, hardware
permission/authentication, Context/security bootstrap or any device case.

The owner's corrected successor passed the same nine scenarios/42 checks with
all five deliberately invalid option values injected into only the Python
launcher environment; global environment was unchanged. Source f0334b37,
SDK class e32b0c71 and DEX2e9488e2 remain byte-identical to the initial artifacts.
This review verified current/historical pins, model-source identity, helper-only
program definition, private/volatile DEX fields and actual stdout/classpath
metadata. Compiler-only API definitions are absent from the one-class DEX and
model runtime; the helper is absent from the parent model directory and loaded
only from its separate child path. Models implement the exercised boundary,
not full Samsung interface or kernel behavior.

No remaining material source/concurrency/isolation defect was found. Acceptance
is confined to this prepared component; public bind is not an ACL or authority
attestation, and no original framework retarget, real cache preparation, boot
selection, Android behavior or device acceptance follows.
