# Unselected Android SID helper payload

**Built:** a separate, bounded wrapper containing only the authored
`SidNativeBinding` DEX, the frozen production ARM64 bridge and a derived JSON
manifest. **Not assembled:** genuine helper/native source and path admission,
the chosen class-loader/process owner, or the real private Samsung SPM target.
This payload is unselected, is not an APK, and was not installed or executed.
Metadata extraction remains separate from credential/HAT verification.

The [producer](../tools/build_sid_android_payload.py) and
[inventory](../inventory/sid-android-payload.json) record exact inputs, commands,
tool hashes and output checks. This producer compiles exactly one source file:
`compat/src/com/appleexploit/oneos/security/compat/SidNativeBinding.java`.
It does not compile or package tests, synthetic targets, the portable oracle,
SDK definitions, original Samsung/ColorOS code or another authored transport.

**Immutable producer inputs:**

| Input | Literal SHA256 |
| --- | --- |
| `SidNativeBinding.java` | `a47fc8c877ac3575b39599fb024e8f0cda2b20ea0ec2765a55f825486b8e51d7` |
| `compat/native/sid_bridge.c`, provenance only | `bb81f1435b5f26001e734e758c2d12dcfe286107f375c0efb639e57fb1c32989` |
| Frozen production ARM64 library | `70862b9e7bae8ae85c39c107b4f18a997ec4fc92a857f5e403f7fd976ee9b38e` |

The library is read from the literal successful native run
`out/sid-native-binding/20261105T175452592590Z-19124afa57ae400baa546223b800ce52/arm64/liboneos_sid_bridge.so`.
It is neither rebuilt nor selected through a moving output receipt. The Java,
C, native image, producer and all compiler/inspection inputs are rehashed before
and after packaging. The earlier native-binding reports/outputs stay unchanged.

Actual build run:
`out/sid-android-payload/20261105T180756840150Z-22f3f606129d46c1abc3277505afb52f/`.
Its ZIP is 10,197B, SHA256
`9e0ce6d2bd4d233b2e400e56960eb7bb606a84ed107153e8627d0b2c7b2c3277`.
It has exactly three regular, unencrypted, stored entries:

| Entry | Size | SHA256 |
| --- | ---: | --- |
| `classes.dex` | 2,556B | `634110e525c7c6bbe774955a885f44c451412290323e6488ff8687b7b504feff` |
| `lib/arm64-v8a/liboneos_sid_bridge.so` | 4,680B | `70862b9e7bae8ae85c39c107b4f18a997ec4fc92a857f5e403f7fd976ee9b38e` |
| `payload.json` | 2,593B | `de1c3480c100349c0b5552c4f002d2568fafadeedad13c56061fc97f9587a5b8` |

The wrapper is bounded to128KiB; DEX/native entries to64KiB each and manifest
to16KiB. Exact names/count, regular-file metadata, entry bounds and bytes are
read back and checked. ZIP timestamps are fixed; the inner manifest excludes the
current run path/time and contains derived input/tool/entry identities, not an
authenticity grant. An external JSON record cannot replace genuine code/source
admission or the future owner's reviewed embedded pins.

**Observed byte validation:** the DEX039 checksum/signature, tables, class data
and method declarations are checked with a bounded reader for this own D8 output.
Unknown/new container formats fail; there is no header patch or rebasing path.
Its sole class definition is
`Lcom/appleexploit/oneos/security/compat/SidNativeBinding;`. The four methods are
its initializer, private constructor, public static declared-synchronized
`loadAndBindOnce(String,Class):void`, and private static native
`bind0(Class):void`. The native declaration has exact flags `0x10a`, descriptor
`(Ljava/lang/Class;)V` and no code item. No SDK/test/oracle/OEM definition enters
the DEX.

The frozen native image is checked again as little-endian AArch64 shared ELF.
Its sole dynamic export is the corresponding authored helper `bind0` JNI entry;
no undefined dynamic symbols or DT_NEEDED entries exist. Full defined-symbol and
literal checks reject the synthetic test/fault-hook names. The payload includes
the production ARM64 image, never the Windows DLL or its test-only exports.

**Compiler limitations remain explicit:** existing SDK37 `android.jar`
(`bf1b4387…53f177`) is the javac bootclasspath and D8 library input; source8/
target8 yields class52. This is stub type checking, not a Java8 release-API check,
ART verification, hidden-API access or proof of real loader/native resolution.
The pinned D8 (`a26ee562…7637d`) receives requested minimum API37 and actually
reports:

> Warning: An API level of 37 is not supported by this compiler. Please use an API level of 36 or earlier

The exact diagnostic is retained in the manifest, inventory and run log. Emission
of these bytes does not establish API37 compiler/runtime acceptance. The native
image's earlier Android21/classic-JNI compile target is not a lower-platform or
API37 support promise for the complete payload.

The prior authored Windows JNI result in [sid-native-binding.md](sid-native-binding.md)
remains separate evidence. This packaging run executes only PC compilation,
D8 and static ELF inspection tools. It does not load the helper/native image or
an OEM class. No phone, ARM, ART, Binder, credential, HAT or app-key operation ran.

Reproduce from the nested project with
`python tools/build_sid_android_payload.py`. Each run prints a fresh UTC+UUID
handle under its own output tree, uses task-local TMP/TEMP and Java temp/home,
and limits every subprocess to30 seconds. The next integration still needs
genuine code/path/source admission, one admitted helper/image identity, external
process-lifetime retention before binding, correct private-SPM target/state and
actual Android/native acceptance. Packaging does not satisfy those contracts.
