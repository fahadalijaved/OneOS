# Process-local bootstrap property and final-option boundary

**Recommendation: use the captured AndroidRuntime final-option callsite as the
primary construction boundary.** A two-getter process-local property interposer
is a source-supported alternative, conditional on real loader/ABI admission.
Preloading an exported `JNI_CreateJavaVM` replacement does not intercept the
captured internal call. No interposer, native gate, patched ELF, launcher or
runnable phone command is implemented or selected here.

The [inventory](../inventory/samsung-vm-property-view.json) pins six exact ELF
inputs, seven newly selected native functions/1,464 instructions, 35 instruction
assertions, symbol visibility/version/relocation metadata and reused VM/ART
evidence. `python -B tools/audit_samsung_vm_property_view.py` verifies saved
native spans and current source hashes. `--capture` disassembles only the selected
functions; `--extract` obtains four exact regular files from the already supplied
local tar. No OEM/native/ART execution or global property change occurred.
Addresses below are captured ELF virtual addresses, not live process pointers.

## Actual getter paths

| Captured consumer | Actual source edge |
| --- | --- |
| AndroidRuntime ordinary/extra VM options | Imported `property_get`; its libcutils body calls `__system_property_get` through PLT at `0xd9a4` |
| `android::base::GetProperty` | Calls `__system_property_find` through PLT at `0x17668`; null goes to the default branch at `0x1766c`; present property invokes `__system_property_read_callback` at `0x17680` |
| `android::base::GetBoolProperty` | Calls that GetProperty through PLT at `0x181a0`, then original ParseBool/default behavior |
| Server-configurable flags | Reused actual body builds `persist.device_config.` plus namespace/key and calls base GetProperty at `0x4938` |
| Bionic property wrappers | Actual find/get/read-callback exports tail-call their real SystemProperties implementations; they do not route through the libcutils getter |

Thus `property_get` alone misses the base/server-flag path. Intercepting only
`__system_property_get` has the same coverage gap. A read-callback-only hook also
cannot supply a missing property when the original find returned null. No
synthetic `prop_info` object or replacement shared property area is needed by the
narrow higher-level candidate, and none is proposed.

The smallest demonstrated getter set is `property_get` plus the exact C++ symbol:

`_ZN7android4base11GetPropertyERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEES9_`

Both corresponding exports/imports are strong, default-visible and unversioned
in the selected libcutils/libbase/AndroidRuntime files. GetBoolProperty's actual
PLT edge and the server-flag edge make the second getter relevant to both flag
paths. This is mechanical call coverage, not a claim that a future preload has
won every relocation or is an admitted selected library.

The C++ function uses the captured Android libc++ `std::__1::string` ABI; its body
retains the result address from x8 at `0x17648`. A C-string shim, desktop C++
library or borrowed temporary string is not that ABI. Delegation must preserve
the genuine original target, return/default/exception/storage behavior and avoid
recursion. Low-level libc find/get are versioned `LIBC`; read-callback is
`LIBC_O`. These constraints remain if a lower interception boundary is chosen.

The selected getters contain no environment-to-property conversion. Supplying
ordinary environment variables named after VM properties, or Java `-D` system
properties, is not a demonstrated replacement for these native calls. Effective
property values were not captured or executed by this investigation.

## Scope of an intentional bootstrap view

The paired [launch card](samsung-authority-vm-launch.md) identifies these native
inputs to the no-image/interpret route:

- `persist.device_config.runtime_native_boot.profilebootclasspath`
- `dalvik.vm.profilebootclasspath`
- `persist.device_config.runtime_native_boot.enable_apex_image`
- `dalvik.vm.boot-image`
- `dalvik.vm.usejit`
- `dalvik.vm.execution-mode`
- `dalvik.vm.extra-opts`

A future getter view would match exact keys under an admitted bootstrap policy,
delegating every unrelated key and its original behavior unchanged. Desired
false/empty values would be an **intentional local launch policy**, not evidence
that genuine global properties had those values. It must not override SDK,
codename, product, credential, biometric, user, permission or security identity
properties to manufacture a source or authority profile. The separately pinned
original BCP candidate still needs its genuine profile/ownership admission.

`extra-opts` is an original ASCII-space token stream. Blanketing it with empty
text could discard unrelated options. Preserve non-bootstrap tokens and reject
conflicting selectors, or use an explicitly reviewed exact transformation.
The same applies to argv and options appended later. Getter interception alone
does not establish the final ordered JavaVMOption vector or matching ART result.

## Real linker restrictions

The captured linker obtains `AT_SECURE` (23) at `0x1a5fcc/0x1a5fd0` and branches
at `0x1a5fd4`: only zero reaches the environment-reading path at `0x1a64e8`.
There it reads `LD_LIBRARY_PATH` and `LD_PRELOAD`; the latter's getenv call is
`0x1a650c`. The secure path supplies no preload string. Captured file metadata
does not establish a future process's auxiliary-vector value, SELinux/domain,
namespace or path admission. This report supplies no preload launch command.

AndroidRuntime, libcutils and libbase have immediate binding flags and RELRO
constraints. The selected AndroidRuntime has DF_BIND_NOW and DF_1_NOW, without
DT_SYMBOLIC; its libc dependencies also impose their own version rules. The
linker's own DF_FLAGS includes SYMBOLIC. A present environment string or an ELF
export therefore does not prove the intended consumers resolved to a helper.
Actual same-family native dependencies, permitted helper path, namespace/global
lookup order, symbol versions, C++ ABI and early initialization remain gates.
No late GOT patch or writable-RELRO assumption is made.

## Concrete counterexample and smaller source-owned seam

AndroidRuntime's own `JNI_CreateJavaVM` is a **protected** dynamic definition
(`STV_PROTECTED=3`, value `0x1860dc`, size 116). `startVm` calls it with a direct
BL at `0x185ba0`, not through a PLT relocation. A same-name exported preload
cannot preempt this internal protected reference. Lack of DT_SYMBOLIC does not
change that fact.

The fully constructed original argument boundary is immediately before that BL:

| Captured instruction span | Observed role |
| --- | --- |
| `0x185b74/7c/80` | JNI version `0x10004` stored at argument-struct offset 0 |
| `0x185b78/84/88` | Original mOptions array obtained and stored at offset 8 |
| `0x185b90/9c` | Original vector count stored at offset 4 |
| `0x185b94` | x2 points to that original JavaVMInitArgs |
| `0x185b98` | Original ignoreUnrecognized false at offset 16 |
| `0x185ba0` | Direct original wrapper call with original x0/x1 outputs and x2 arguments |
| `0x185ba8` | Original negative-result branch |

A source-owned, default-off same-runtime boundary can therefore validate the
complete vector before delegating to this exact original wrapper. This avoids
pretending that native properties came from environment variables, and avoids a
new property getter's scope reaching unrelated consumers. Any intentional
bootstrap-only option transformation must retain every unrelated option's order,
string, extraInfo pointer and callback owner; strings alone are not the complete
JavaVMOption contract. No generic prefix filter is approved here.

The paired final-options stream owns actual placement, activation, native ABI,
vector transformation, lifetime and inverse proofs. The observed Runtime LOADs
are 16KiB-aligned, with GNU AArch64 BTI|PAC feature value 3; its startVm entry is
PACIASP. Header/note facts were supplied to that owner, without claiming loader
acceptance of a modified segment. Any gate must preserve caller SP/LR, original
error disposition and argument/callback lifetimes. The wrapper's once/table
dispatch must stay original; its indirect target is not by itself an attestation
that a particular real ART library has been admitted.

This is a constructive next source boundary, not a working launch owner.
The original boot cohort/native view, matching ART option grammar, controlled
complete final vector, actual process/realm admission and later Context/native
acceptance remain required. No original security service or VM was started, and
no original authority, global property or device state was replaced.
