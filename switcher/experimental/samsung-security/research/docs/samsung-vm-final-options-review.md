# Independent final-options proposal review

**No remaining concrete defect found in the bounded pre-code proposal.** It is a coherent source-supported option for root's architecture decision, conditional on the prerequisites below. This review approves neither a native implementation nor an enabled artifact, process launch, loaded backend or working authority. No gate or patched ELF was emitted, and no OEM/native/ART code ran.

The reviewed [proposal](samsung-vm-final-options.md), its [inventory](../inventory/samsung-vm-final-options.json) and auditor are frozen by exact hashes in this [review inventory](../inventory/samsung-vm-final-options-review.json). The independent readers only inspect captured bytes and existing finite receipts; the proposal producer was not rerun.

## Actual source and layout

Independent readback verifies all ten newly selected bodies and four reused bodies against literal original ELF bytes, function hashes and decoded instruction streams. All 66 selected source assertions pass. Existing call/literal annotations remain inherited evidence after byte/decode parity; the three selected mapped scalar strings are independently read from source bytes.

The real call is BL `0x185ba0 → 0x1860dc`, returning to `0x185ba4`; its signed-negative branch remains at `0x185ba8`. The target is the actual global **STV_PROTECTED** JNI export. The 24-byte JNI 1.4 frame and 16-byte option tuples are source facts. The retained wrapper's once initializer dlopens nativehelper and binds table index 3, slot `0x300820`. Captured nativehelper subsequently chooses/loads the backend. Retaining this chain preserves behavior; it does not attest the live helper, namespace or ART selection.

Independent ELF checks confirm thirteen headers ending at `0x318`, immediately followed by notes. There is no spare header. The all-zero gap is `0x2d0cd8..0x2d4000`; aligned entry `0x2d0ce0` leaves **13,088 bytes** for authored code and immutable profile. Its direct branch displacement fits. No source section, 8,307 defined dynamic/minidebug symbol entries, 6,322 RELA/APS2 records or 10,443 expanded RELR slots/addends intersects the gap or proposed new sixteen BSS bytes at `0x300ab0`. Original BSS remains intact. Those sixteen bytes add no mapped page at either 4 KiB or 16 KiB; the RX extension can add up to three 4 KiB pages. These are static footprint facts, not loader acceptance.

The source GNU property bits advertise BTI|PAC and original startVm uses PACIASP. Future code must prove actual entry/indirect-target, frame, callee-saved-register, stack alignment and unwind behavior. Keeping note bits does not establish that new instructions satisfy them. Captured linker startup/property lookup evidence does not prove modified LoadSegments, page permissions, SELinux or private mount admission; these remain explicit prerequisites.

## Parser and lifetime closure

The revised contract correctly follows **ProcessSpecialOptions before TokenRange**. Hook rows remain byte-for-byte tuple-identical but are omitted from the classification shadow. Groups are formed in that projected stream. Thus `[-Xcompiler-option, exit(nonnull), -Xusejit:true]` must retain every raw tuple: usejit text is compiler payload. Adjacent-raw filtering, raw occurrence counts and family-prefix rewriting fail this case.

The exact controlled grammars, bool domain, legacy source modes, opaque special/fd/zygote refusals and three preserved registered exceptions are now explicit. Protected group values take precedence over controlled-family refusal. All original groups must close **before** appending owned selections; a dangling group must refuse instead of consuming the appended BCP or `-Xint`. Reclassifying the complete final projection must prove unique top-level BCP/Interpret, matching optional locations, no conflicting top-level selection and unchanged unrelated tuple pointers/order. Unknown unrelated options still reach original validation. This is a reviewed contract, not a tested parser implementation.

Actual hook extraInfo null rules and unchanged callback pointers are retained. Changed controlled rows require null extraInfo. The copied frame changes only count/options pointer; original x0/x1, borrowed strings, unrelated extraInfo and relative order remain original. Owned arena retention and borrowed caller lifetime are separate obligations. Failed/uncertain creation cannot permit retry or premature release.

## Required before implementation or selection

Root must choose the exact API/profile. An implementation then needs bounded arithmetic/string/count checks, one-shot synchronization, allocation/refusal paths, complete projection tests, actual code fit, original-byte/inverse proofs and ABI/BTI/PAC/unwind review. Default DISABLED must tail directly to the original wrapper with untouched x0/x1/x2/SP/LR and no parsing, allocation or state mutation.

An enabled artifact additionally needs a genuine cold private-process launcher, admitted mount/namespace/cohort and actual nativehelper/backend ownership before VM creation. Caller PC, profile/hash, NEW state, process name and UID 1000 cannot establish these. The original callsite is also reachable by ordinary source launches; a private flag cannot prove another path has never created a VM. No authentication, key, CE, Context-readiness or full-goal acceptance follows from this review.
