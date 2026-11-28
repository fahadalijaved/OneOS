# Captured Samsung VM option construction

This bounded offline card closes the native **option-construction** edge left by
the boot-framework card. It does not select a launcher, prove a modified boot
image loadable, or establish an authority process. No OEM instruction, VM, class
initializer or device operation was executed. The boot and quiescence cards are
preserved. `selected=false`.

The input is the existing Samsung `libandroid_runtime.so`, 3,271,648 bytes,
SHA256 `f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d`.
Its ELF/minidebug symbols and existing Capstone 5.0.6 decode seven complete
functions, 2,441 instructions. PCs below are **ELF virtual addresses**, not live
process addresses or DEX PCs. Exact bytes, function hashes, resolved direct/PLT
calls and local ADRP/ADD string-address pairs are retained under
`firmware/authority-vm-options/selected-native.json`. The annotations are bounded
static address pairs, not emulation or whole-function data-flow analysis.

| Actual function | Address | Bytes |
| --- | --- | --- |
| `AndroidRuntime::startVm(JavaVM**,JNIEnv**,bool,bool)` | `0x184058` | 7804 |
| `parseRuntimeOption` | `0x185ed4` | 148 |
| `parseExtraOpts` | `0x186010` | 204 |
| `parseCompilerRuntimeOption` | `0x183e88` | 208 |
| `addOption` | `0x1e5f98` | 48 |
| `AndroidRuntime::start` | `0x1e609c` | 1236 |
| local `JNI_CreateJavaVM` wrapper | `0x1860dc` | 116 |

## What reaches the option list

The reused captured `app_process64` main proof pins the pre-runtime argv loop:
`strdup` at `0x41a4`, `AndroidRuntime::addOption` at `0x41b4`, comparisons of the
leading `'-'` and terminal `"--"` at `0x41f8..0x4218`. The special `-cp` and
`-classpath` one-argument handling is visible in that loop and agrees with the
pinned AOSP mechanism reference. The standalone path passes false as `start`'s
zygote argument at `0x4594`, then calls `start` at `0x4598`. This is existing
captured code, not a prepared command line.

`addOption` stores its option pointer/extraInfo pair at `0x1e5fa8` and appends to
the Vector at `this+8` (`0x1e5fac..0x1e5fb4`). `start` passes the same runtime
object into `startVm` at `0x1e61cc`. The selected construction path retains the
existing option list and appends property-derived entries; it contains no
caller-option reset/deduplication step. At `0x185b78..0x185ba0`, the existing
Vector's array/count become the VM initialization arguments and the local
`JNI_CreateJavaVM` wrapper is called. The initialization structure uses
JNI 1.4 (`0x00010004`) and a zero ignore-unrecognized byte; no permissive
unknown-option acceptance is established.

## Actual image branch and order

1. `runtime_native_boot/profilebootclasspath` is requested via imported
   `GetServerConfigurableFlag` at `0x184894`; `ParseBool` follows at `0x1848fc`.
   The zero-result branch reads `dalvik.vm.profilebootclasspath` using
   `GetBoolProperty(...,false)` at `0x184924`. The profiling path appends its
   five-option group at `0x185c08..0x185c74` and records the selector in `w19`.
   The precise assembly predicates are retained, rather than assuming an enum
   ABI from the unrelated AOSP revision.
2. Samsung requests namespace `runtime_native_boot`, key **`enable_apex_image`**
   (`0x184950/0x184968`, imported call `0x184994`). The profiling selector
   (`0x1849e0`) or comparison with string `"true"` (`0x1849f0/0x1849f4`) branches
   to `0x185bc8`: append **`-Xforcejitzygote`** at `0x185bf8`, then join at
   `0x184a38`. Neither that key nor the current flag value is guessed from
   AOSP constant names. The imported flag helper's own backend is outside this
   card.
3. Otherwise, `dalvik.vm.boot-image` with prefix **`-Ximage:`** is passed to
   `parseRuntimeOption` at `0x184a18`. That helper copies the prefix, reads the
   property into the suffix (`0x185f28`), and appends only if the suffix's first
   byte is nonzero (`0x185f30..0x185f40`). Empty means no explicit image option
   from this branch; the log says default, but no actual selected image path is
   thereby proved.
4. Ordinary runtime/compiler options follow. For example,
   `odsign.verification.success=false` takes the `-Xdeny-art-apex-data-files`
   append path (`0x184b38..0x184b70`, `0x185cf0..0x185d00`). This is another
   input affecting permissible ART artifacts, not observed current state.
5. `dalvik.vm.extra-opts` is read at `0x185564`, parsed at **`0x185574`** with
   null prefix (`x2=0` at `0x185570`). `parseExtraOpts` skips/splits on ASCII
   space `0x20`, writes NUL at a separator (`0x186060`), and appends tokens in
   order at `0x186084`; it is not a shell parser with quoting/escape expansion.
   A nonnull prefix is separately appended before each token at `0x1860d4`.
6. Image compiler options follow the general extra options:
   `dalvik.vm.image-dex2oat-Xms/Xmx`, filter, threads, ISA settings and
   image flags (`0x185588..0x185760`), then locale and other runtime entries.
   The image-compiler runtime helper emits prefix, `--runtime-arg`, prefix,
   value (`0x183eec..0x183f30`); these are compiler arguments, not a selected
   image file. General extra options are therefore late, but not the last
   additions to the list.

A caller `-Ximage:...` and a property-generated image/force-JIT entry can coexist
in that list. **Append order is proved; effective duplicate/conflict precedence
for the captured Samsung ART is not.** The local JNI wrapper uses `pthread_once`
at `0x18610c`, then an indirect function slot at `0x300820` (`0x18611c/0x186124`).
This card does not resolve that slot to a selected live `libart` or audit its
parser.

## Boot classpath and in-memory compilation limits

There is no direct `-Xbootclasspath` or `-Xallowinmemorycompilation` string
construction in the selected `startVm` address annotations. This bounded
negative observation does not exclude caller/extra-option input or downstream
ART handling. The captured public metadata supplies a 61-entry BOOTCLASSPATH
with `framework.jar` at index 5; it supplies neither this proposed process's
effective environment nor a VM property snapshot. Its nine query names are
recorded in the inventory. No new property or `/proc` read was performed.

Primary references already captured under `firmware/authority-boot-framework/`
explain mechanisms, **not a matched Samsung implementation**:

- [AOSP app_main.cpp, pinned revision](https://android.googlesource.com/platform/frameworks/base/+/1cdfff555f4a21f71ccc978290e2e212e2f8b168/cmds/app_process/app_main.cpp#215)
  describes the argv loop; [AndroidRuntime.cpp](https://android.googlesource.com/platform/frameworks/base/+/1cdfff555f4a21f71ccc978290e2e212e2f8b168/core/jni/AndroidRuntime.cpp#724)
  describes property appending.
- [Pinned ART parsed_options.cc](https://android.googlesource.com/platform/art/+/6484611fd45e69db9f33f98bfd6864014b030ecf/runtime/parsed_options.cc#688)
  treats explicit bootclasspath differently from BOOTCLASSPATH fallback; lines
  764–782 reject image plus force-JIT, infer in-memory permission for a zygote,
  and conditionally select a default image. A standalone process is not proved
  to receive zygote-derived permission. Parser support for an explicit flag is
  not proof its compilation prerequisites/resources are present.

The existing boot card's coherent whole-BCP/helper visibility, matching image/
OAT/VDEX and data-cache obligations remain. `-Xint` alone does not replace an
already selected boot definition. App-classpath-only helpers remain insufficient.

## Concrete remaining gate

Before selecting a launch recipe, obtain the exact future process's argv,
environment, ordered VM options and relevant flag/property values; resolve the
matched Samsung ART parser and actual selected images/data caches. Then prove
the modified framework and complete helper closure before first boot-class
resolution, with preserved Samsung APEX/library/mount identities. The candidate
process-local view before OneOS prepare line 1087 still does not isolate global
properties or Binder; real guest display production is later. No global property
override, alternate ANDROID_DATA, compiler invocation or ready launcher is
prepared here. The original-authority admission/drain/native-completion cut
before OneOS `ctl.stop` line 971 remains independently open.

Recheck: `python tools/audit_authority_vm_options.py`. Static capture, only if
needed: `python tools/audit_authority_vm_options.py --capture`. The ordinary
recheck verifies exact binary/function bytes, 43 instruction assertions, reused
app-process proof, primary-source hashes and preserved-card pins, then writes
only this stream's inventory/check/freeze metadata. No ART parser, OEM VM or
launch acceptance is claimed.
