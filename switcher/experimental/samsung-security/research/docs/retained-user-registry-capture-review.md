# Retained user-registry capture review

**PASS for the corrected, unselected capture component and its bounded PC evidence.** No remaining material scoped defect was found. The initial source clearances were superseded after another reviewer found the wrong storage Class key. Corrected source, all six actual publication key/value/parent flows, the saved SDK/D8 outputs and authored model evidence have now been independently reviewed. This does not establish a running authority, a native endpoint, a coherent security generation or device acceptance.

The reviewed component is `PreparedRetainedUserRegistryCapture`, source SHA-256 `26fcbb3089715aad31a40d17d74cb5ab9ea940d6950e88261f725722b1c0fb0f`. The corrected source contract is [retained-user-registry-binding.md](retained-user-registry-binding.md), SHA-256 `ef1f6ae4de8523d9e27f7b4d3a602d3f1fc211b979d54de9bbb1aac91a86ae03`, with inventory `40c27af0b3b8b2b80ca2c4af3e2f237b13393df8ac966e892ae187ca3ab160c1`.

Independent saved-raw readback checks all 29 field descriptors, field flags and declaring-class access flags, and verifies the source contract's input, query, receipt and raw hashes. A separate static inspection of the authored code confirms the 28 relationship fields plus the private cached Zygote loader, all six prepared LocalServices class keys, and the exact access-preparation list. Neither checker invokes the collector or original code.

Four concrete defects were corrected before any component compilation:

| Finding | Source-specific issue | Correction |
| --- | --- | --- |
| RUC-01 | `UserController$Injector` is package-private; its three public fields need access preparation as well as the PMI parent field. | The corrected contract individually records the three descriptors/access flags and the code prepares only those exact reads under root's bounded authority. |
| RUC-02 | The first implementation required a final UMI parent field, flags 4113; the real field is nonfinal, flags 4097. | The literal source modifiers now match 4097. |
| RUC-03 | The first implementation never cached its SMI class key and would query LocalServices with null. | Metadata preparation now caches the actual concrete key before any owner query. |
| RUC-04 | The earlier code and model used an abstract storage key and model inheritance that disagree with Samsung's publication. My first static pass checked field shapes/cache presence but omitted publication Class-register lineage; another reviewer found this error. | Code/model now use only the concrete key in C, with Object-only SMI value. All six source publications and parent producers were read independently. The preserved old source fails the source-derived key-set check; an authored wrong-key model also fails. Earlier clearances remain superseded history. |

SMS lifecycle uses concrete key/value/add PCs 533/535/537; LSS constructor uses the same concrete key/get/cast/store PCs 643/645/649/651. The old abstract type remains only an explicitly labeled negative-model marker. This does not claim whole-archive absence of every hypothetical reflective alias.

The two earlier implementation defects are preserved in the private authored-source snapshot `out/retained-user-registry-capture-review/history/prebuild-3c9cdd3b15d097bad1ce0c20b974bc02528aba81130385cb7e9eef294df28883.java.txt`. No author/shared source was edited by this reviewer.

The loader rule follows this Samsung profile's actual placement. Original Zygote uses its cached system-server loader for the startup thread; original SystemServer prepares the main Looper. Samsung LocalServices is defined in boot-framework `8095a9ae…`, classes6, while the core services belong to the cached server loader. The implementation requires those exact class identities and loader relationships, the existing main thread/Looper, and the existing private Zygote cache. It accepts no caller-supplied owner, hash, UID, readiness flag or fallback loader.

The six actual keys and value producers are below. C is the cached original server loader; F is the original Binder/framework loader. PCs are decimal; full raw/receipt hashes and producer edges are in the review inventory and private readback.

| Key | Actual value / parent producer | Publication |
| --- | --- | --- |
| `UserManagerInternal` in C | UMS LocalService; allocation123, parent128, UMS field133 | key1072, field1074, add1076 |
| `PackageManagerService` in C | The actual PMS constructor receiver, register1 from parameter27 | key474, add476 |
| `android.content.pm.PackageManagerInternal` in F | New concrete PMI427; constructor429 receives PMS; its parent write is constructor3, base parent5 | key425, add432 |
| Concrete `StorageManagerService$StorageManagerInternalImpl` in C | Allocation170, SMS parent175, SMS field200; Object superclass, no interfaces | key533, field535, add537 |
| `android.app.ActivityManagerInternal` in F | New AMS LocalService2025, constructor2027, AMS field2030; local constructor parent0 | key166, field168, add170 |
| `SystemServiceManager` in C | Allocation509, constructor513, SystemServer field516 | key527, field529, add531 |

Capture uses the six canonical LocalServices roots, original UMS singleton getter and original boot predicate, then checks parent/crosslinks twice and retains 18 references privately. A later check compares the same retained references and cached metadata; it never refreshes a stale record. Injector caches must already be populated. It invokes no constructors, provider/cache-miss getters, remote/service-name lookup, current-user/serial/profile query, CE/native status, enrollment or state writer. Original local RuntimeException/Error identities survive reflective invocation; unsupported checked faults refuse capture.

Root selected two package-private control bridges before the first build: the exact retained SystemServiceManager and cached server loader. Both call `checkStillBound` before returning. Java runtime-package access requires the same package and defining class loader; these are integration accessors, not public API or authentication authority. The earlier source `eec6be0f…` and its review checkpoint remain historical private snapshots.

The one corrected PC build's receipt is `out/retained-user-registry-capture/20261106T030902567133Z-b65df5309fc1409d824f36ba63beb3e4/receipt.json`, SHA-256 `f352aa64bdd1f3a88e99c7322dd1a1d2d426dbacca06cdb7584323cf58803ad4`. Independent saved-file inspection confirms exactly two authored class52 definitions and two DEX039 definitions (`99f24fe8…`), all 50 generated authored model sources, all nine command logs and unchanged compiled production hashes. No reviewer build/model rerun was needed. The initial draft builder's imported output-root guard, output-key parsing and native search-path containment were corrected before execution.

The isolated authored models report 53 scenarios/73 checks: exact 18 retained references, roots/parents/cache replacement, source descriptors/modifiers/access, the wrong abstract SMI key, main/CCL refusal, original RuntimeException/Error identity, and same-loader versus foreign-loader control access. They execute the unchanged SDK-compiled authored classes using authored Binder/Looper/service models only. The SDK/OEM archives and JNI are excluded from the runtime classpath; generated work uses the owned cwd/temp/home, empty application-native path, 512 MiB heap, five cleared JVM/compiler environment inputs, 45-second command limit and 2 MiB output bound. Model fixtures are not genuine Android objects or runtime acceptance. D8's API37 unsupported/max36 warning is retained.

The original boot predicate means only `mCurrentPhase >= 1000`. It does not prove phase-callback completion or native/lifecycle drain. A misplaced early call can initialize the LocalServices utility before refusing missing roots; the contract explicitly excludes a universal no-class-initialization promise. Real fully-booted source placement remains an external requirement. Repeated reference reads detect observed drift but are not an atomic transaction across independently changing services.

The captured `mVold` reference is not endpoint attestation; the Java references confer no native/process/path ownership, revocation or drain guarantee. No public service getters are exposed. The bootstrap still must own the original process/code/state/native producers, real user/policy admission and return/handoff. The installed guest services `efb45f5f…` differs from the donor; this component's host evidence remains Samsung services `def967fb…` and framework `8095a9ae…`. Nothing here removes the staged guest guards or proves authentication, FBE/app-key continuity, generation readiness or phone acceptance.
