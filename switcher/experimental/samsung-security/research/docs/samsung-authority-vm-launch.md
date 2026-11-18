# Samsung authority VM: finite cold-launch gate

**A deliberate imageless, explicit-bootclasspath route exists in the captured Samsung ART. A launch recipe is still withheld because its process-local native-property and final-option owners are missing.** This closes a source branch question; it does not select an architecture, supply a runnable command or establish a working VM/Context probe. No ART/OEM/native code or device operation ran.

The frozen [boot-framework](authority-boot-framework.md), [AndroidRuntime options](authority-vm-options.md), [matched ART parser](authority-art-option-selection.md) and scalar diagnostic cards remain untouched. The [new audit](../tools/audit_samsung_authority_vm_launch.py) verifies 40 selected assertions, six new bounded native functions, existing raw option/parser evidence and the exact 61 recorded boot members. Its [inventory](../inventory/samsung-authority-vm-launch.json) contains paths, hashes, PCs, constraints and the finite prerequisites. Raw code remains only in ignored firmware.

## Actual imageless path

All addresses here are captured ELF virtual addresses, not live addresses. The ART input remains `/apex/com.android.art/lib64/libart.so`, SHA `4166f04a…`, 15,010,176 bytes.

| Observed source edge | Exact evidence |
| --- | --- |
| Explicit BootClassPath differs from environment fallback | DoParse saves the explicit-key iterator at `0x597c84/88`; BOOTCLASSPATH reaches SetIfMissing at `0x597cd8`. The default-image branch excludes an explicit key at `0x59835c`. Merely setting BOOTCLASSPATH does not establish this exclusion. |
| ForceJit remains independent | Its actual key generates an Image value or conflicts with an existing Image at `0x5982e4`; late image tokens cannot be assumed to override it. |
| Runtime consumes real parsed Image | Runtime::Init obtains Image at `0x59224c/50`, retaining its vector. |
| Empty image list deliberately skips discovery | ImageSpace::LoadBootImage compares list begin/end at `0x583e70..78`. Empty branches to `0x583f9c`, sets false and returns without FindImageFiles/LoadFromSystem. No fake missing filename or image-validation failure is needed. |
| No image spaces selects original DEX initialization | Runtime compares the actual heap boot-image-space vector at `0x593e9c..a8`. Empty reaches OpenBootDexFiles at `0x5946a8`, then ClassLinker::InitWithoutImage at `0x5946d0`; nonempty takes InitFromBootImage at `0x593eb4`. |
| Initialization still uses genuine source files | OpenBootDexFiles reaches actual DexFileLoader::Open at `0x603f04`; its failure branch is retained. InitWithoutImage also checks that the heap has no image at `0x80a8c8`. |

This selected empty-image path does not require boot-image in-memory compilation: it skips image construction. That is a bounded branch finding, not evidence that arbitrary jars, native owners or Android resources initialize successfully. The full DexFileLoader/linker transitive implementation and actual loaded class bytes have not been executed or attested.

## Argument contract without duplicate precedence

The source-supported candidate has **one explicit complete BootClassPath**, the 61 recorded Samsung entries in their original order, and matching canonical locations if a separate locations option is supplied. `framework.jar` stays at index 5. For this future Context-only probe these are the original captured bytes; this task creates no modified framework cohort. Every selected boot member's manifest identity is recorded, without extracting the whole boot tree again.

Require **no Image and no ForceJitZygote option from any producer**, no competing boot/image/OAT/VDEX fd inputs, and one interpret-mode selection. The captured parser recognizes `-Xint`; it rejects an existing true UseJitCompilation value (`0x5981ac → 0x598460`) and otherwise sets that value false itself (`0x5981c4`). Therefore the candidate can use a single `-Xint` without a competing true JIT value. It does not rely on two contradictory settings being resolved in order. App CLASSPATH remains distinct and cannot replace a boot-defined class or supply reverse helper visibility.

These are typed option constraints, not a prepared command. No repeated-option assignment rule is assumed, and no nonexistent-image or `-Xint`-alone workaround is proposed. An explicit boot key suppresses default-image insertion only when neither AndroidRuntime nor another producer has already supplied Image/ForceJit.

## Native property producer is the remaining owner

AndroidRuntime appends property-derived options after caller argv. Actual `dalvik.vm.usejit` becomes `-Xusejit:` at `0x184ef0..0x184f08`. Profiling or exact-true `enable_apex_image` can append ForceJit; nonempty `dalvik.vm.boot-image` can append Image. General `dalvik.vm.extra-opts` is a later ASCII-space token source, followed by image-compiler and other options. A late flag is not proof of the final vector.

One newly acquired local-tar member closes the imported server-flag producer: `/system/lib64/server_configurable_flags.so`, SHA `69dde39d705ae09a98dc17e1ed77d040d85dd8400dbdb42440ff0ae81f941169`, 36,392 bytes. Its actual C++ GetServerConfigurableFlag at `0x45b8` constructs `persist.device_config.` plus namespace, dot and key (`0x4794`, `0x47f8`), then calls genuine `android::base::GetProperty` at `0x4938`. The reached keys therefore include `persist.device_config.runtime_native_boot.profilebootclasspath` and `persist.device_config.runtime_native_boot.enable_apex_image`. No new network fetch occurred; original mount-capture manifest/hash evidence identifies the file, not its future live linker binding.

The finite missing owner must control or genuinely capture, before native initialization, the original read view for those keys plus `dalvik.vm.profilebootclasspath`, `dalvik.vm.boot-image`, `dalvik.vm.usejit`, `dalvik.vm.execution-mode` and `dalvik.vm.extra-opts`. Required outcomes are the original nonforce/nonimage branch and no conflicting mode/JIT/token additions. Empty image/JIT/extra-option inputs are source-supported absence semantics, but this card provides no process-local property implementation or assumed boolean-enum mapping. Shell environment and Java `-D` arguments are not established replacements for these native reads. Namespace isolation alone does not rewrite property-service state.

A paired property-view investigation owns the actual property_get/GetProperty/libc/linker boundary. An explicitly reviewed source-owned AndroidRuntime final-vector seam is an alternative if that boundary cannot provide an isolated view: the existing captured instructions place the original vector/count into VM initialization arguments at `0x185b78..0x185b9c`, immediately before the direct local JNI wrapper call at `0x185ba0`. A future gate there would need its own complete preservation/admission contract; an exported-symbol preload alone must not be assumed to replace a direct local call. Neither gate nor interposition is implemented here. No global property reset, LD_PRELOAD assumption or policy-false provider is introduced.

## Exact admission still required

Before a non-auth Context-only probe can be proposed, require:

1. A reviewed isolated native-property/read owner or actual source-owned final-option seam, then the **complete final JavaVMOption vector** and actual JNI-to-libart binding. The vector must satisfy all unique-option constraints above, including late producers.
2. The final process-local Samsung code/APEX/native/resource/linker and root/environment view before VM creation. The recorded host has 61 boot entries and ART APEX aliases; OneOS guest_start derives different guest classpaths. A host-looking path or snapshot does not attest the future namespace. Do not redirect credential ANDROID_DATA or share unexplained ART-cache writes as a shortcut.
3. A separately reviewed Context-only entry and genuine metrics/configuration/application input owner, with no authentication, enrollment, credential writes or service publication. The scalar diagnostic has no caller and supplies none of that initialization. A non-auth goal is not a side-effect-free execution claim: original AndroidRuntime/native registration, Binder thread startup and Context first effects still require explicit ownership.

Keeping the original Samsung authority alive would avoid creating this second cold VM and reselecting its boot/image cohort. It still needs a real retention/admission/drain/return design across OneOS's current kill boundary and the genuine guest security/presentation transports. This card selects neither route.

Recheck with `python -B tools/audit_samsung_authority_vm_launch.py`. It performs static verification only. Optional `--capture` reproduces the single named local-tar acquisition and six selected-function decodes; it does not launch ART or execute any OEM code.
