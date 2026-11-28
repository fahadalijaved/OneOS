# Private-view supervisor: static cross-build

The single root-authorized supervisor cross-build passed without compiler
diagnostics. The resulting executable has **never been run**, including its
no-argument/default path, help, setup or cleanup. Table's source pass579b0137
preceded root's separate d1cf656e one-build go. Source-phase report/inventory/
freeze e112/b8b4/c221 are preserved byte-exact under
`out/guest-private-view-supervisor-build/history/source-only-before-actual-d43d18a4/`.

The seven literal source/header inputs are supervisor C7dfa2c6f, provider
C5e645e05/header68a7b302, owner C1026094b/header463b79db and parser
C7cf383c2/header8c8e2025. The four actual C units compile together; no stub,
fixture, SDK declaration, OEM object, prior shared library or prebuilt owner
output is substituted. `GVO_STANDALONE` is absent, so only the supervisor's
original authored `main` is selected. There is no shared-library export map or
`--entry=0` override: the real executable entry must lie in an executable load.

Shade's source-only review25f84e4d and supervisor source freeze875ac516 are
preserved byte-exact as hash-named producer inputs. Provider source reviewad9a0142
is also pinned. These are source/provenance gates, not image authentication,
current process/resource admission or evidence that a function was executed.
The supervisor's synchronous open/begin and indefinite HOLD/cleanup limits remain
the original reviewed behavior; compilation cannot prove their runtime outcomes.

The actual command was
`python -B tools/build_guest_private_view_supervisor.py --build`.
The existing Unity NDK23.1.7779620 targets AArch64 Android API31 using C11/O2,
warnings as errors, PIE, stack protector, fortify and static-PIE linking with
RELRO/NOW. The compiler/reader wrappers, sanitized child environment, bounds and
raw executable-entry ELF inspector are reused unchanged from reviewed8f4c4845.
Twelve literal NDK identity/tool/CRT/static-library/builtins/unwind hashes are
checked; this is not a complete header/sysroot/Windows-loader closure.

One clang command captures the bounded binary stdout through the existing
`--no-mmap-output-file` recipe, with no failed output-path trial or fallback.
Only Windows llvm-readelf subsequently reads headers, program headers and dynamic
tags. Both commands have45-second bounds. Binary stdout is capped at8MiB and
stderr at2MiB; reader text has a combined2MiB cap. Read/close exceptions refuse
success even if the child exits0. The short unique cwd and all generated sources,
temporary/home directories, artifact, logs and receipts remain under
`out/gvs-build`; the five temp/home environment values are child-local.
Original sources/producer/provenance/native inputs and staged copies must match
before and after successful admission. Failure preserves the attempt and stops.
No automatic retry, installation, WSL, phone or global settings change is present.

The static inspector requires ELF64 little-endian AArch64 ET_DYN with a genuine
executable entry load, no interpreter or DT_NEEDED, NX stack, no WX load,
GNU_RELRO/NOW and no TEXTREL. Actual load alignment is recorded under the4KiB
profile, including lld's rounded RELRO coverage. Neither API31 nor separately
observed4096 phone pages establish Android17/API37 or runtime loadability.

The actual run is `out/gvs-build/r-d43d18a4/receipt.json`, SHA256
`496b95d2fb9b9a4ddc77feefbcfde875bd1ac12afd69abd7b2cab93dc757e9f7`.
The633,680-byte `guest_private_view_supervisor` has SHA256
`b57fcc0d024e640798346529539fc4d3627ea0fca8c35e93d53000d256c6be15`.
Compiler exit0 took1.250s with empty diagnostics; read-only llvm-readelf exit0
took0.078s. All13 source/producer/provenance inputs,12 native inputs and7 staged
copies matched before and after validation. No retry or source change occurred.
The saved ELF has11 program headers and four4KiB-aligned LOAD segments, with
entry103872 in file-backed `_start`, NX, RELRO/NOW and no interpreter, needed
library, WX load or text relocation.

Table independently hashed and parsed the saved output without replaying any
compiler, reader, producer or executable. Its immutable proof is
`out/guest-private-view-supervisor-build-review/actual-output-check.json`, SHA256
`2d548e6369e4b981c06bae19eeebf85dda2c0977de49eff7e93aed2c6613996c`.

This successful cross-build proves compilation and those structural ELF
properties only. Actual loading, libc startup, signals, stdin/output delivery,
provider adoption, fork/mount/IPC, kernel/LSM behavior, descriptor custody,
physical state, native authority, propagation and real close/reap/drain remain
unexecuted. The output remains unselected and is never run by this producer.
