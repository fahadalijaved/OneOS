# Final VM options: constructive owner proposal

**Propose a default-off gate inside a process-private derivative of the original Samsung libandroid_runtime.** One original BL would reach an authored gate; the gate would retain the original protected JNI wrapper and original nativehelper/backend selection. This is a pre-code API and binary-layout proposal. No gate, patched ELF, launcher, enabled profile or runnable command exists. Root still selects the architecture and reviews this contract before implementation.

The [auditor](../tools/audit_samsung_vm_final_options.py) and [inventory](../inventory/samsung-vm-final-options.json) pin actual ABI/layout, ten newly selected functions and the source-derived classification contract. Frozen [VM3](samsung-authority-vm-launch.md), [property-view](samsung-vm-property-view.md), scalar and earlier cards remain unchanged. All PCs below are ELF virtual addresses. Only static parsers/disassemblers run.

## Exact call and retained backend

Captured app_process64 has a real `DT_NEEDED` dependency on libandroid_runtime.so. Samsung runtime SHA `f77d49dc…` constructs the complete final vector before **BL `0x185ba0 → 0x1860dc`**. JNI_CreateJavaVM is a global **STV_PROTECTED** export, so replacing a preloaded symbol is not an owner for this internal call.

At that call, x0/x1 are the original JavaVM**/JNIEnv** output pointers and x2 is the actual JavaVMInitArgs at x29−0xa8. Its layout is version:int at 0, nOptions:int at 4, options:pointer at 8 and ignoreUnrecognized:boolean at 16; native size is 24 bytes. The source writes JNI **1.4 / 0x10004**, not 1.6, and false ignoreUnrecognized. Each JavaVMOption tuple is 16 bytes: optionString pointer, then extraInfo pointer. The source handles a negative return at `0x185ba8`; successful entry and return semantics must stay original.

The protected wrapper runs pthread_once at `0x18610c`, then dispatches slot `0x300820`. Its actual initializer (`0x174c2c`, 720 bytes) dlopens **libnativehelper.so** and binds JNI_CreateJavaVM as table index 3; BindSymbol writes `base 0x300808 + index*8`. Keep that wrapper, once state, table and failure paths unchanged.

The locally captured ART-APEX nativehelper (`d974e14e…`, 51,496 bytes) forwards JNI_CreateJavaVM through its genuine g_impl. JniInvocationInit obtains a library name, dlopens it and resolves JNI_CreateJavaVM at `0x623c`. Original selection considers ART_TEST_ON_VM/ART_TEST_ON_SBC, ro.debuggable, persist.sys.dalvik.vm.lib.2 and libartd availability. It can occur **before** the final callsite. A name, nonnull function pointer or embedded hash is not proof of the selected live nativehelper/libart. The gate preserves that selection; actual original native/backend/namespace admission remains mandatory.

## Loading and placement

Before executing the future dedicated process, its reviewed private mount/code owner would select the derivative at the original runtime-library path. The ordinary captured app_process dependency would map it before main/VM creation. No new DSO, preload, DT_NEEDED entry, constructor, exported gate symbol, GOT rewrite or global mount/property edit is proposed. This depends on an actual admitted private namespace and source file; it is not supplied by this card.

The source has thirteen program headers ending at 0x318, immediately followed by notes. There is no spare header slot. Instead, its existing RX segment ends at **0x2d0cd8**; the next RW segment begins at **0x2d4000**. The intervening 13,096 file bytes are zero. The auditor checks both proposed regions against sections, dynamic/sized minidebug symbols, 6,322 RELA/APS2 target/addend records and **10,443 independently expanded Android RELR slots plus their in-place addends**; none intersects. A gate aligned at **0x2d0ce0** has a strict **13,088-byte** code/read-only-profile budget. Its direct BL displacement fits AArch64's range.

A future producer could extend only that existing RX filesz/memsz within the gap and replace the one BL. Keep segment flags/alignment, all old symbols/imports/relocations and RELRO unchanged. Reserve sixteen genuinely new owned state bytes after the final original RW BSS end, **0x300ab0**, by extending its memsz; never use an original global or RX memory as writable state. This proposal produces no such bytes.

The source GNU property bits are BTI|PAC. New entry/frame/return code must preserve BTI/PAC, original stack alignment, SP/LR and callee-saved x19–x29. A tail transfer avoids leaving a new gate frame across VM creation. Own construction-phase unwind metadata still needs producer proof. The RX extension can add mapped pages on a 4 KiB system even though its old rounded end already reaches 0x2d4000 at 16 KiB; no unchanged-page-footprint claim is made. Actual linker segment/page/SELinux admission, code fit, derivative build identity and exact ELF inverse remain open. If the gate does not fit, stop for another layout review.

## Default-off admission and storage

The immutable embedded profile defaults to **DISABLED**. That path tails directly to the original wrapper with x0/x1/x2/SP/LR unchanged, without parsing, allocation or state mutation. An enabled profile requires a separately reviewed artifact selected by the genuine private launch owner; there is no environment/property/Java-option activation protocol. Process name, caller PC and expected hashes alone do not authenticate that owner or the loaded cohort.

For the owned enabled call, require the actual module/caller return `0x185ba4`, reviewed profile, exact JNI frame and a complete bounded vector. An owned NEW→BUILDING→ISSUED state rejects concurrent/reentrant/repeated creation. Refusal returns a negative JNI error through the source failure branch and never reports VM success or changes output pointers.

Construct a private anonymous arena containing a copied 24-byte InitArgs and stable cloned tuples. Change only count/options pointer in the cloned frame. Preserve each unrelated original tuple's optionString pointer, extraInfo pointer and relative order; borrowed source strings keep their **original** caller lifetime. Owned replacement storage and arena remain retained through actual callee consumption and conservatively until process exit. Do not free/retry after uncertain creation, including a negative return after effects. Restore entry SP/LR/registers, forward x0/x1 unchanged and x2 as the clone, then tail-B `0x1860dc`; the original wrapper returns directly to `0x185ba4` and original hooks remain in force.

## Complete source-matched vector transformation

Native properties and their original option producers run unchanged. Never clear dalvik.vm.extra-opts. Classification must reproduce the relevant **source ordering**, rather than edit matching substrings:

1. Make a shadow token index that omits only source-recognized exit/vfprintf/sensitiveThread/abort hook rows. Keep those raw tuples, pointers and order unchanged in the output. Active input containing opaque `bootclasspath`, `compilercallbacks` or `imageinstructionset` specials is refused; no fake DexFileList, callback or ISA is substituted.
2. In that projected token stream, honor the four actual two-token grammars: `-cp _`, `-classpath _`, `-Xcompiler-option _`, `-Ximage-compiler-option _`. Protect their value rows even across retained hook tuples. Missing values or unclosed syntax refuse. No shell parsing, quote expansion or splitting within an original option string is introduced.
3. Normalize only recognized **top-level** bootclasspath/location, image, force-JIT, interpretation and usejit selections. Nonnull extraInfo on a changed row, opaque boot fd/image/OAT/VDEX inputs and zygote-mode inputs refuse this standalone candidate. Preserve all unrelated tuples exactly. Append one reviewed complete explicit bootclasspath and one `-Xint`; locations, if emitted, must match. Require no Image, ForceJit or true UseJit selection, without assuming duplicate precedence.
4. Independently verify the entire final projection, group roles, counts, unchanged tuple identities/order and unique owned selections before issuing the original call. Finite allowed syntax and all failure branches need review in the future producer; this auditor transforms no real vector.

The finite accepted profile is explicit. `_` below denotes one parameter **inside the same option string**, not an extra tuple. A colon-list has nonempty bounded components; this is the candidate's declared accepted subset, not a claim of every ART input form.

| Exact top-level source grammar | Accepted input and proposed action |
| --- | --- |
| `-Xbootclasspath:_` | The exact root-approved complete input list (currently original captured ordered 61); otherwise refuse. Replace selections with one approved output list. |
| `-Xbootclasspath-locations:_` | Exact approved input locations/count; otherwise refuse. Output omitted or exactly one matching list. |
| `-Ximage:_` | Nonempty colon-list; empty/malformed/unclosed input refuses. Remove top-level image selection. |
| `-Xforcejitzygote` | Exact token only; remove. |
| `-Xint` | Exact token; normalize to one appended token. |
| `-Xint:portable`, `-Xint:fast`, `-Xint:jit` | The three actual legacy AndroidRuntime producer strings; remove top-level tokens. Other suffixes refuse. |
| `-Xusejit:_` | Exactly `true` or `false`; remove top-level selection and retain original Interpret→false behavior. The actual builder binds these two bool values. |

Refuse these exact specials: `bootclasspath`, `compilercallbacks`, `imageinstructionset`; these source patterns: `-Xbootclasspathfds:_`, `-Xbootclasspathimagefds:_`, `-Xbootclasspathvdexfds:_`, `-Xbootclasspathoatfds:_`; and exact `-Xzygote`/`-Xprimaryzygote` mode tokens. Do not infer subject, DEX pointers or ISA from their absence. Before checking unmatched family lookalikes, preserve the separate registered `-Ximage-dex2oat`, `-Xnoimage-dex2oat` and `-Xzygote-max-boot-retry=_` options unchanged for original validation. The four two-token groups and their protected values also take precedence. Remaining unmatched **top-level** names beginning with the bootclasspath/image/noimage/forcejit/int/usejit/zygote/primaryzygote families refuse; this rule never reaches a protected payload.

The hook whitelist is exact: exit, vfprintf and abort require nonnull extraInfo as their original source does; sensitiveThread preserves its actual nullable extraInfo. All hook tuples remain identical. Unrelated rows, including their extraInfo, remain for original ART validation. A changed controlled row with nonnull extraInfo refuses.

**Close every original projected group before appending owned tokens.** If a group lacks its original value, reject; the new bootclasspath or `-Xint` must never become that value. Reproject the complete proposed output and require exactly one **top-level** BCP and Interpret, matching optional locations, zero top-level Image/ForceJit/UseJit, no forbidden special/fd/zygote forms, no pending group and exact correspondence of every unrelated tuple's original pointers/order. Raw occurrence counts do not establish this.

**Discriminating counterexample:** raw `[-Xcompiler-option, exit-hook, -Xusejit:true]` projects to `[-Xcompiler-option, -Xusejit:true]`. Actual ProcessSpecialOptions runs at `0x597bc8` **before** CmdlineParser at `0x597be8`; the usejit text is compiler payload and all three tuples must survive. An adjacent-raw or prefix-only filter is wrong. The actual TokenRange constructor copies the vector's strings; it is not a license to reinterpret shell text.

The proposal is constructive but conditional: root API selection, authored gate/arena/one-shot code, exact source-only ELF producer/inverse, private load/cohort/backend admission, linker/BTI/PAC/unwind checks and the non-auth Context input owners remain required. No authentication or credential operation is proposed, and no runtime readiness follows.
