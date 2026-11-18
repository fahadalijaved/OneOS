# Callable private-view inputs: static shared cross-build

The separately authorized corrected build passed all structural shared-ELF
checks. The48,344-byte library has **never been loaded or executed**. It exports
exactly the three gvi functions, declares `libdl.so` and `libc.so`, records58
undefined dynamic symbols, and has entry0, NX, RELRO/NOW and four4KiB-aligned
loads. This is compile/static-file evidence only.

The first root-authorized cross-compile produced an ELF without compiler
diagnostics, then **failed static admission** because its entry address was
11036 (`0x2b1c`), whereas the reviewed shared-library profile requires zero.
The attempt stopped before readelf, without a retry, output load or execution.
The source-only report/inventory/freeze are preserved
under `out/guest-private-view-inputs-build/history/source-only-before-failed-05324a94/`.

Corrected provider C5e645e05/header68a7b302 have H's complete source pass ad9a0142. Their d95e8d32
source freeze is preserved byte-exact at the producer's hash-named immutable
provenance path. All six source/header hashes and that review are literal build
inputs. Table accepted producer de990728 before root's separate 5aa6f994 go.
No output load, dlopen, help, exported-function
call, constructor or standalone execution is performed by this producer.

Root selected a callable shared ELF with three actual authored C units:
`guest_private_view_inputs.c`, `guest_private_view_owner.c` and
`guest_private_view_mountinfo.c`, plus their three actual headers. The owner and
parser remain unchanged. `GVO_STANDALONE` is absent. There is no synthetic API
implementation, SDK stub, OEM object, main program or Windows model. The supported
underlying C profile remains a dedicated single-thread, one-shot supervisor; a
shared library does not make it a general Android service embedding interface.

An anonymous authored version script lists only `gvi_open_existing`,
`gvi_begin_view` and `gvi_close` as global, and makes every other symbol local.
The producer stages that literal script and checks its hash before and after
linking. It does not use `-fvisibility=hidden`, which would also hide the intended
exports without source annotations. `gvo_*`, parser and raw internal API exports
are prohibited by exact saved ELF dynamic-symbol admission.

The fixed existing Unity NDK23.1.7779620 targets AArch64 Android API31 with
`-shared -fPIC`, C11/O2, warnings as errors, stack protector and fortify. Root
approved `--no-undefined`, a fixed SONAME `libguest_private_view_inputs.so`,
RELRO/NOW and the prior bounded binary-stdout linker workaround. This differs
from the earlier owner static-PIE build: it uses API31 shared CRT and libc/libdl/
libm stubs. Eleven literal input hashes cover identity, compiler/linker/reader,
shared CRT/stubs and builtins/unwind; they do not attest the entire sysroot,
header or Windows DLL closure.

The raw ELF inspector requires ELF64 little-endian AArch64 ET_DYN with entry0,
no interpreter, NX stack, no WX load, RELRO/NOW, no text relocations or RPATH, the
exact SONAME and exactly three default-visible defined global function symbols
with the names above. The loader-facing DT_SYMTAB/DT_SYMENT must match the section
symbol table's address, offset, size and file-backed load mapping; string-table
descriptions must identify the same bytes and address. Export bodies must fit
actual file-backed executable load extents. `DT_NEEDED` must be a duplicate-free subset of
`{libc.so, libdl.so, libm.so}` containing `libc.so`; any other dependency refuses.
The actual dependency list and every named undefined dynamic symbol are recorded.
These names are not proof of the genuine future loaded libraries, symbol-version
resolution, source/process owner or complete native ABI.

The actual command was `python -B tools/build_guest_private_view_inputs.py
--build`. It created a short unique run only under
`out/gvi-build`, stages byte-identical inputs and uses five local temp/home
environment values. Injection variables are stripped and PATH is child-local.
One clang command and one read-only Windows llvm-readelf command each have a
45-second bound; binary stdout is limited to8MiB, stderr to2MiB, and reader text
to a combined2MiB. Reader errors fail even if the tool exits0. Inputs, producer,
native profile, staged sources, version script and saved ELF hashes are checked
before and after successful inspection. Failure preserves a receipt and stops.
No automatic retry, install, WSL, phone or global setting operation is provided.

The failed run is `out/gvi-build/r-05324a94/receipt.json`, SHA256
`3e9476d64e4c6aabf92aff5fd19cf11a51aaadd31fd4c483684e28a0eec4feb1`.
Its preserved48,344-byte artifact is SHA256
`99abfc29c823587499455322477813fd1f93cd587ba2be6335d8f1c32d1ecfb7`.
Table independently identified the nonzero entry as the local CRT function
`__on_dlclose`; its raw symbol read also found the three intended defined gvi
exports. This is saved-file evidence, not function execution. Later producer
structural/export/dependency checks were not reached and are not assigned PASS.
The zero-entry requirement remains intact; any explicit linker correction needs
separate source review and a new root decision, with this failed run preserved.
Root subsequently selected an explicit linker `--entry=0`, retaining the same
strict ELF gate. That is the only producer source change, confined to linker
argv; no source function, input profile, export/dependency policy or binary bytes
were edited. The old producer and failed report are preserved at
`out/guest-private-view-inputs-build/history/failed-de990-before-entry-zero-correction/`.
Table's immutable7c5822ff exact-delta pass preceded root's5797fcc1 separate go.
The corrected source phase7200/32d6/a108 is preserved byte-exact under
`out/guest-private-view-inputs-build/history/corrected-source-before-success-63200a57/`.
The first failure is not relabeled.

The successful corrected run is `out/gvi-build/r-63200a57/receipt.json`, SHA256
`6fb391c91fa1de87a3435218d21a31591dd48251242838176d6f0c94c907f30f`.
The saved library is SHA256
`83438c2e3c150c0fb1fb6f63072b43b47b326061303bade8f8b290bb48d4d625`.
Compiler exit0 took1.078s with no diagnostics; read-only llvm-readelf exit0 took
0.078s. All pinned inputs, staged sources and the version map matched before and
after validation. Two compilations occurred in total: one failed admission and
one independently authorized corrected attempt; only the corrected attempt ran
readelf, and neither output was loaded or executed.

Table independently parsed and hashed the corrected saved ELF without replaying
the producer, compiler or reader. Proof is
`out/guest-private-view-inputs-build-review/actual-output-check.json`, SHA256
`2846d3c878b20b648a7ed01fa0bede04cf41f332d8db7e96523ac3d2f2efa250`.
The failed artifact differs only at file offsets24 and25; neither binary was
patched. The source and saved-output review accepts static evidence only.

The selected structural profile is4KiB. The failed producer did not reach its
load-alignment reporting gate; the corrected saved ELF did.
Neither the phone's separate observed4096 page size nor an API31 build proves
Android17/API37, runtime loading, kernel/LSM, namespace, descriptor custody,
physical state, image authenticity, native authority, propagation or retirement.
The three functions' genuine side effects and cleanup require separately
authorized runtime evidence. The output remains unselected and unexecuted.
