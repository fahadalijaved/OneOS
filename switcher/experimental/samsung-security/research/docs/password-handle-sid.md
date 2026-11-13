# Portable password-handle SID metadata extraction

**Implemented and PC verified:**
`com.appleexploit.oneos.security.compat.PasswordHandleSid.extract(byte[])`
returns the unchanged 64-bit little-endian pattern in bytes1 through8. It has
no fields, copies, logging, input mutation or retained input/result. It accepts
zero and negative Java `long` bit patterns without treating either as an error.
The caller owns the array and must prevent concurrent modification.

This is metadata extraction. It does not validate a password handle, verify a
credential/HAT, query Gatekeeper, authorize a user or replace
`GateKeeper.getSecureUserId`. No original SPM method has been retargeted and no
Android/OEM/native execution occurred.

The authored [helper](../compat/src/com/appleexploit/oneos/security/compat/PasswordHandleSid.java),
[synthetic tests](../compat/tests/PasswordHandleSidTest.java),
[test runner](../tools/test_password_handle_sid.py) and
[receipt](../inventory/password-handle-sid.json) are separate from ignored
generated classes/logs under `out/password-handle-sid/`.

**Exact source basis:** the pinned Samsung services archive is SHA256
`def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6`.
Its public instance `SyntheticPasswordManager.sidFromPasswordHandle([B)J`
body, logical DEX041 header offset10057984, has normalized SHA256
`303d9eabab04649322cc62bbc9f911b0ac0fcef4c5160a5177ee001f49ec2eca`.
The complete body directly invokes its private native at DEX PC0, moves the
wide result at PC3 and returns at PC4. It has no Java null guard or catches.

The actual one-entry JNI table points to the inspected native function at
ELF address `0x102700` in captured Samsung `libandroid_servers.so`, SHA256
`9482076b93ae97db3cb0e4a2c6e45b93c6dc6fd7d264afe2df7e8bdd25d80a16`.
Its 116 bytes hash to
`5a426f8390432a4986a136ac415d4aa4c401b4a736fb54199b501f6969b4bbc1`,
identical to the original guest function. On this little-endian ARM64 image it
acquires primitive-array critical access, loads 64 bits from offset1 and
releases with JNI_ABORT. The exact table, source/raw hashes and instruction
proofs are revalidated by the runner from the frozen
[native-linkage inventory](../inventory/security-native-linkage.json).

**Equivalence domain:** nonnull arrays with at least nine bytes, stable during
the call. Within this domain the helper reads the same eight bits-per-byte
pattern. It neither checks nor changes version/header/trailing bytes; being
long enough is not evidence of a genuine, complete or authenticated handle.
The original caller must still supply the actual handle for the intended
protector/user operation.

**Explicit authored invalid-input policy:** null throws `NullPointerException`
through `Objects.requireNonNull(handle)` with no message; a nonnull array shorter
than nine bytes throws `IllegalArgumentException` with a constant data-free
message. Neither becomes a zero SID. Original null or short JNI behavior is
not reproduced or claimed equivalent. A null native buffer can represent a
failed critical-array acquisition with a pending exception; it is not a proven
null-input success sentinel. The
[JNI contract](https://docs.oracle.com/en/java/javase/21/docs/specs/jni/functions.html#getprimitivearraycritical-releaseprimitivearraycritical)
requires a nonnull array for critical access.

Run from the nested project:

```powershell
python tools/test_password_handle_sid.py
```

The actual passing PC run covers 40,368 valid synthetic inputs, ten malformed
inputs and 80,769 checks. Fixed endian/offset vectors, zero/min/max/all-one/
alternating/single-bit patterns and 20,000 seeded random arrays use an independent
little-endian `ByteBuffer` oracle. Header/tail variation and every successful or
rejected array check verify nonmutation. Reflection verifies the field-free,
final, private-constructor/static-entry shape. `javap` verifies no field stores
or array allocation and only the expected constructor/null-check/exception calls.
Seven separately compiled incorrect variants are rejected: wrong offset,
endianness, signed-byte extension, null-as-zero, short-as-zero, mutation and
retention. All inputs are generated test data; no real handle or secret is read.

The existing Windows JBR compiles with source8/target8 and exits0, producing
class-file version52. Its earlier `--release8` attempt emitted classes but failed
compiler resource cleanup, so release-API checking is not claimed. Compiler
warnings/options, executable hashes, source hashes, class hash and actual test
results are recorded. This is PC Java verification, not Android/D8/loader
acceptance or hardware equivalence testing.

Every subprocess uses task-local TMP/TEMP and runs under
`out/password-handle-sid/`. Java test/version commands receive explicit
`java.io.tmpdir`/`user.home` properties; javac and javap receive the corresponding
`-J-D` options. Each process has a 30-second timeout; a timeout fails the runner
and cannot count as a rejected mutant. No global environment or HOME variable is
changed. The regenerated inventory records these exact options and boundaries.

**Future retarget obligation:** deliberately replace only PC0's
`invoke-direct {receiver,handle}, nativeSidFromPasswordHandle([B)J` inside the
original instance wrapper with an exact static helper call passing `handle`.
Preserve the instance wrapper ABI, wide-result/return and foreign code. Before
selection, prove every reached caller satisfies the equivalence precondition;
preserve legitimate NONE/zero-SID paths separately rather than sending a null
sentinel through this helper. Pin the chosen helper payload and its visibility
from the private SPM loader, prevent shadow copies, and obtain actual DEX
instruction/inverse/caller proofs. No bytecode edit or runtime binding is part
of this delivery.
