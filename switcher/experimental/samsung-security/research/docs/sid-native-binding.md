# Prepared SID JNI binding

**Delivered:** an authored ARM64 JNI library and a prepared Java binding entry
point, with genuine execution of the authored Windows JNI test library against
an authored synthetic target. **Unbound:** the actual private Samsung SPM class,
its admitted code/loader/state realm and the complete security authority. No OEM
class/native code, ARM64 library, phone or hardware operation was executed.
This function extracts SID metadata; it does not verify credentials or HATs.

The implementation is [sid_bridge.c](../compat/native/sid_bridge.c) and
[SidNativeBinding.java](../compat/src/com/appleexploit/oneos/security/compat/SidNativeBinding.java).
The [builder](../tools/build_sid_native_binding.py),
[synthetic JNI test](../compat/tests/SidNativeBindingTest.java),
[synthetic target](../compat/tests/SidSyntheticTarget.java) and
[inventory](../inventory/sid-native-binding.json) preserve source/output pins.
The unchanged [portable helper](password-handle-sid.md) is the PC oracle; its
earlier independent ByteBuffer tests establish the extraction vectors separately.

**Prepared API:**

```java
SidNativeBinding.loadAndBindOnce(absoluteLibraryPath, admittedTargetClass);
```

The caller must first admit the genuine library bytes/path, helper/target class
identities, loader arrangement and fresh, unbound target. This API implements no
such source admission. Its structural preflight requires the provided Class to
declare exactly a private, nonstatic, native
`nativeSidFromPasswordHandle(byte[]):long`. It does not find or construct an OEM
class, realize an SPM provider or use a matching class name as evidence.

`System.load` executes in the helper's loader. Normal JNI name resolution reaches
the authored helper's private static `bind0(Class)`, which receives the actual
helper Class and the explicitly supplied target Class. The C registrar acquires
helper/target GlobalRefs before registering the single exact method descriptor
`([B)J` on that target. It uses no canonical SPM `FindClass`, Samsung bootstrap
replay or whole `libandroid_servers` import. With a future admitted real private
SPM target, its original instance wrapper can remain unchanged; this delivery
does not perform that binding or any DEX retarget.

**Metadata behavior:** after binding is ready, the native method checks null and
minimum length9, acquires JNI primitive-array critical access, reads bytes1..8
as an unchanged little-endian 64-bit pattern and releases with JNI_ABORT. Zero,
negative Java long patterns and the header/tail bytes do not become authorization
decisions. Null throws a message-free NullPointerException; a short input throws
IllegalArgumentException with a constant data-free message. Critical acquisition
failure preserves a pending exception or throws OutOfMemoryError. No handle or
result is placed in global/class state, logged or mutated. The caller owns the
input and must prevent concurrent modification. Original valid-input equivalence
and the deliberately safe invalid-input policy remain scoped as described in
[the source/native proof](security-native-linkage.md); no getSecureUserId
substitution or handle-authenticity claim is introduced.

**Lifetime and failure contract:**

| Boundary | Actual owner/result |
| --- | --- |
| Before entry | An external admitted owner must retain helper, target and loaders for process lifetime. Java self/static references do not independently root their owning loader. |
| Java entry | A synchronized one-attempt flag is set before System.load; helper/target Class references are retained and never cleared. A later public call refuses, including after load/bind failure. |
| Native entry | Atomic compare/exchange permits one attempt in this admitted native image. There is no reset, rebind, unregister, release or hot-drain API. |
| Failure before first GlobalRef | No native GC root is established; target registration has not occurred. External process-lifetime ownership remains necessary. |
| Target GlobalRef failure | The helper GlobalRef stays held; registration has not occurred. Any pending allocation exception is preserved. |
| Registration failure or uncertain progress | Both GlobalRefs stay held. Error/exception paths do not publish ready; a potentially bound target call refuses before reading metadata. |
| Successful registration | Ready is published with release ordering; target reads acquire that state. Both GlobalRefs remain for the process lifetime, rooting the helper/loading code and target class. |

This is **once per admitted native image and Java helper Class**, not a universal
process singleton. Different copies/images/loaders can have independent statics.
The future genuine owner must forbid those duplicates and preexisting target
bindings. Static Java references alone do not make failed loading/first-anchor
allocation survive unloading. This prepared mechanism does not solve service
handoff, active OEM operation drain or a later process's authority admission.

**Actual successful build/test evidence:** root executed the frozen builder with
exit0 in the unique run
`out/sid-native-binding/20261105T175452592590Z-19124afa57ae400baa546223b800ce52/`.
The existing pinned Unity NDK23.1.7779620 compiler/headers were used; nothing was
installed. Every build creates a new UTC+UUID output directory, prints its run
handle, uses local TMP/TEMP and Java temp/home properties, and bounds each
subprocess to 30 seconds.

| Artifact | Actual proof |
| --- | --- |
| Production ARM64 `liboneos_sid_bridge.so` | 4,680B, SHA256 `70862b9e7bae8ae85c39c107b4f18a997ec4fc92a857f5e403f7fd976ee9b38e`. Little-endian AArch64 shared ELF, sole exported helper bind0 symbol, no undefined dynamic symbols or DT_NEEDED dependencies. Built, not executed. |
| Authored Windows test DLL | 4,608B, SHA256 `36c5f16fb0e4c6ff15a04a4accb4322a013cb28c22c561deb4dd40199191fa65`. Built by the same existing clang plus `ld.lld -flavor link /dll /noentry /nodefaultlib`; no CRT/platform imports. Contains test-only injection/anchor observation exports absent from the ARM production export list. |
| Actual host JNI | Five fresh JVMs with `-Xcheck:jni`, 20,066 synthetic checks total; no JNI warning/fatal lines. Only authored helper, synthetic target and test classes were loaded from the output class directory. No Android/OEM class was loaded or invoked. |

The baseline checks genuine RegisterNatives dispatch, 10,000 random arrays
against the portable Java oracle, fixed/zero/sign patterns, malformed rejection,
nonmutation, structural target rejection, exact GlobalRef class identities and
Java/native repeat refusal. GlobalRef type/identity is observed through test-only
native hooks. The four **injected** failures are distinct:

| Stage | Injection | Observed native anchor mask |
| --- | --- | ---: |
| 0 | Ordinary successful registration/readiness | 63 |
| 1 | Synthetic OOM before helper GlobalRef allocation | 4 |
| 2 | Synthetic OOM after helper anchor, before target allocation | 21 |
| 3 | Synthetic failure before RegisterNatives | 55 |
| 4 | Synthetic failure after successful registration, before ready | 55 |

The mask distinguishes attempted/ready, presence of each anchor and confirmed
GlobalRef identity. Stage4 actually calls the registered target and observes
fail-closed refusal. These do **not** force real NewGlobalRef exhaustion or a
nonzero RegisterNatives return. Handling of actual pending exceptions and
registration errors is source reviewed; those VM faults were not runtime
exercised. The production ELF uses classic JNI with minimum compile target
Android21, not API37/device acceptance. Platform loader/namespace and genuine
private-realm execution remain pending.

**Historical attempts remain distinct:** three earlier worker-context ARM link
attempts failed with output `Permission denied`; a worker host link attempt also
failed that way, while ARM/COFF object compilation succeeded. Their retained
triage logs remain at the old `out/sid-native-binding/arm64/` and `host/` paths.
Those attempts did not execute JNI and have not been assigned success. Root's
later direct link of the same object to the same output path succeeded without
source/path/security changes or escalation. The complete root-context run then
succeeded with the frozen final builder and its unique output directory. The
environmental difference is unassigned. Unique directories preserve all prior
triage files and do not overwrite their logs.

Reproduce the bounded build with
`python tools/build_sid_native_binding.py`; inspect its printed run handle and
actual exit/result. A failed later run is not covered by this saved passing
receipt. No phone candidate, real SPM registration, credential verification,
signed-token acceptance, app-key operation or shared-security completion is
claimed by these artifacts.
