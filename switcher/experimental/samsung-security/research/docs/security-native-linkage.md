# Samsung security JNI construction boundary

**Observed:** the required core SPM native edges are narrower than importing
Samsung's complete native server library. Canonical Android scrypt has matching
Java/JNI wiring and checked native-code equivalence in both supplied captures.
The SID extraction function is byte-identical. **Still missing:** a callable SID
binding for a private imported Samsung SPM and the actual candidate's
class-loader/native-owner placement. No native bridge or runnable authority was
implemented, and no hardware/key/storage acceptance follows from this work.

All work is offline. No OEM ELF, JNI function, service, credential operation or
phone action ran. The existing PC Capstone tool bundled with the parent's
Ghidra package disassembled ARM64 bytes; no tool was installed. Raw selected
ELFs, mini-debug symbols and assembly stay ignored under `firmware/security-native/`.

[The inventory](../inventory/security-native-linkage.json) pins exact Java
methods/access flags, source/reader receipts, ELF method tables, relocation-
checked call edges and native function ranges/hashes. The
[authored driver](../tools/audit_security_native_linkage.py) passes 34 static
assertions over 25 selected/reused Java methods, four native inputs and 18
bounded native-function/window proofs. Counts describe evidence scope, not
construction closure or runtime testing.

The two Samsung ELF members were selected from the existing 20,434,769,920-byte
mounted-OS tar using its immutable hash-pinned regular-file index; their exact
bytes were rehashed. No global extraction occurred. The previous strict
whole-tar proof is reused; this pass did not rehash the 20GB archive. Original
guest members were rehashed in their existing extracted location.

| Exact member | Samsung SHA256 | Original ColorOS SHA256 |
| --- | --- | --- |
| `system/lib64/libandroid_servers.so` | `9482076b93ae97db3cb0e4a2c6e45b93c6dc6fd7d264afe2df7e8bdd25d80a16` | `dc919b691a30f60a6bf1e17aeff3a67b5226a50ebc699a07924c0bb208c8f651` |
| `system/lib64/libandroid_runtime.so` | `f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d` | `edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279` |

These are captured/original inputs, not proof of the installed patched guest.
Samsung services/framework remain pinned to `def967fb…639f6` / `8095a9ae…71fe`;
original guest services/framework to `66d0d51d…df3` / `d5c6b7fd…bcd2`. Full Java
archive and logical-DEX identities remain in each reused/new receipt.

**Observed reached methods and unused declarations:**

| Java edge | Exact source result | Binding implication |
| --- | --- | --- |
| `SyntheticPasswordManager.sidFromPasswordHandle([B)J` | Both real wrappers invoke their own `nativeSidFromPasswordHandle([B)J` directly at DEX PC0. Samsung wrapper is public instance (`0x1`); guest wrapper is protected instance (`0x4`). Native declaration is private instance native (`0x102`) on both. | A guest wrapper is not a public static utility. Delegation needs an actual canonical receiver and a reviewed access seam; constructing another guest SPM solely for this is not an inert workaround. |
| `SyntheticPasswordManager.scrypt([B[BIIII)[B` | Samsung creates canonical `android.security.Scrypt` at PC0 and invokes its public instance wrapper at PC5; original guest does the same at PC0/PC`0xb`. | Preserve this genuine canonical framework dependency. Private Samsung SPM need not privatize Scrypt. |
| `android.security.Scrypt.scrypt([B[BIIII)[B` | Both wrappers directly invoke their package-private instance native (`0x100`), same descriptor and argument order. | Canonical Android runtime supplies this registration, rather than Samsung SPM loading a special crypto library. |
| Samsung Crypto's `nativeKBKDF`, `nativeKDF`, `nativePBKDF2`, `nativeRBG` | Four extra public static native declarations exist. Exact direct-reference scans over all supplied Samsung services classes find zero callers. Reused actual `personalizedHash` uses Java SHA-512; `deriveAesGcmKey` uses that real hash and zeroizes its temporary array. | No required bridge for these four is established by the selected core paths. This does not exclude reflection, external jars, native callers or another library's registration table. |

The four unused declarations are **not** assumed safe merely because they are
uncalled. The actual selected SPM native registrar registers exactly **one**
method: `nativeSidFromPasswordHandle / ([B)J`. Its table does not try to register
those Crypto declarations against a guest class. The inspected Scrypt registrar
likewise registers exactly its one `nativeScrypt / ([B[BIIII)[B` entry. Other
native images/registrars remain outside this bounded claim.

**Observed native registration and Java load route:**

* Saved Samsung `SystemServer.main` loads literal `android_servers` at DEX
  `0x1bd/0x1c0`. Saved original guest `SystemServer.run` loads it at
  `0x12a/0x12c`. These are actual source routes, not new bootstrap suggestions.
* Captured Samsung `libandroid_servers.JNI_OnLoad` calls the exported SPM
  registrar at ELF PC `0x12e138`; guest does so at `0xc1ed8`. Each PLT target is
  checked against its stub instructions and `R_AARCH64_JUMP_SLOT` relocation.
* Samsung registrar `0x1025c0` uses `FindClass` with exact string
  `com/android/server/locksettings/SyntheticPasswordManager`, then
  `RegisterNatives` with count1 and table `0x1845c8`. Guest registrar `0x9e744`
  uses the same class string, count1 and table `0xde988`. Tables target native
  implementations `0x102700` / `0x9e884` respectively.
* `libandroid_runtime.AndroidRuntime::startReg` walks its real registration
  pointer table. A decoded Android packed relocation places the actual Scrypt
  registrar in that table in each image. The registrar/helper performs
  `FindClass("android/security/Scrypt")` and binds the exact method table to
  native `0x1b2344` / `0x1a5cb4`. This is the platform registration owner; SPM's
  selected initializer and Crypto's selected initializer do not load it.

The bounded APS2 decoder follows the
[AOSP bionic relocation format](https://android.googlesource.com/platform/bionic/+/refs/heads/main/linker/linker_reloc_iterators.h),
blob `c6a8cf620ab2f7d3ea1c7e921f12e06743265fa2`. This supports static format
interpretation, not a claim that current upstream source is the captured linker.

**Observed native behavior:** the SID implementation is exactly 116 bytes on
both sides, SHA256
`5a426f8390432a4986a136ac415d4aa4c401b4a736fb54199b501f6969b4bbc1`.
It uses JNI primitive-array critical acquire/release, reads a 64-bit value at
buffer offset1 and releases with mode2 (`JNI_ABORT`). There is no hardware,
Gatekeeper, user lookup or Keystore call in this function. JNI slot labels are
also checked against the existing pinned PC JNI header. The function performs
no independent handle length/version validation; real caller/handle provenance
remains mandatory. `GateKeeper.getSecureUserId` is not a demonstrated substitute
for extraction from the original specific handle.

Scrypt's 440-byte wrapper (110 instructions) and 7,676-byte core (1,919
instructions) match under a constrained comparison: intra-function branches
become relative offsets; actual PLT/relocation-resolved call names and verified
equal string bytes replace their addresses; every other operand stays intact.
The wrapper calls actual `crypto_scrypt`; the core's imports include
`EVP_sha256` and `PKCS5_PBKDF2_HMAC`. This is stronger than descriptor/string
parity. It does not compare the entire transitive libcrypto implementation,
prove live linker interposition/namespace resolution, or test a cryptographic
operation. No algorithm output was generated from a credential.

**Loader consequence — inference grounded in actual registration:** guest
startup binds the SPM class resolved by its real registrar. It does not bind a
different private same-name SPM automatically. Android documents that
`FindClass` during `JNI_OnLoad` uses the loading class-loader context; outside
that context its search depends on the active Java stack or system loader.
[Android JNI guidance](https://developer.android.com/ndk/guides/jni-tips).
An exported registration symbol alone therefore does not establish a callable
private-class binding, successful loader access or safe native-library reuse.

The concrete candidate choices remain unselected:

| Choice | Source-supported route | Exact missing owner/proof |
| --- | --- | --- |
| Keep genuine canonical Scrypt | Original private SPM can retain its canonical `android.security.Scrypt` call; actual guest Java/JNI wiring and selected native code agree. | Installed-byte identity, deliberate canonical delegation and actual Android runtime/libcrypto initialization. No Samsung `libandroid_runtime` import is justified by this edge. |
| Place Samsung SPM as deliberate canonical owner before registration | Existing one-method registrar can resolve that canonical class when its actual loader can see it and its native descriptor exists. | Exact class replacement/loader/bootstrap arrangement and coherent original SPM nested types/state. A late private jar does not establish this placement. |
| Adapt private Samsung SID call | Retarget that exact wrapper to a reviewed callable helper/registration seam preserving the actual specific-handle extraction. The byte-identical source function narrows that helper to a format operation. | An authored callable implementation, exact class/registration/loader identity, access and failure semantics, source-preservation/admission tests. No native shim, reflective access bypass, registration replay or Java replacement is implemented here. |

Loading all Samsung `libandroid_servers` would also execute its broad actual
`JNI_OnLoad` registration graph and requires its many native dependencies. The
main Java load call alone proves neither that this is mandatory nor that it is
safe/minimal. The isolated source function does not establish an existing
standalone library or an already callable native bridge.

**Remaining feature-dependent frontier:** supplied services also declare SDP
`SdpManagerImpl.nativeOn*` and DualDAR `TZNative.nativeDDAR*` methods. Coordinated
construction/core proofs do not demonstrate a direct call to those natives.
Real DualDAR policy can reach `fetchOuterLayerKey` through the protection/unlock
path; that controller's transitive native registration is not closed here.
These are unresolved conditional owners, not blanket disabled features and not
reasons to import all Knox native components. Required policy remains intact.

Reproduce saved-evidence verification with
`python tools/audit_security_native_linkage.py`. Explicit `--members`, `--java`
and `--elf-analysis` options reproduce the bounded reads/disassembly. No OEM
function is called by any option. This closes selected native source/ABI and
registration questions; private-SID adaptation, hardware verification, authentic
HATs, protected-key/CE behavior and safe handoff remain pending.
