# Guest private-view owner: static cross-build

The one root-authorized cross-build passed. The generated owner ELF has **never
been executed**. H accepted producer8f4c4845 after the initial output-reader error
handling was corrected; root's separate c9e297b6 go preceded the invocation. The
source-only report/inventory and b2a0a3b1 source freeze are preserved under
`out/guest-private-view-owner-build/history/source-only-before-actual-374d4d8f/`.
The earlier d976 producer and source plan are also preserved. The existing
portable parser tests remain separate evidence and do not test this owner's
syscalls or lifecycle.

The actual command was `python -B tools/build_guest_private_view_owner.py --build`.
It stages exactly owner C1026094b/header463b79db and parser C7cf383c2/header8c8e2025,
with literal full hashes in the producer. It compiles the actual authored C,
including `GVO_STANDALONE`; no stub, replacement parser, fixture/model or OEM
implementation is supplied. This builds the original authored one-shot
supervisor interface, without running even its no-argument or help path.

The fixed Windows toolchain is the existing Unity NDK23.1.7779620. Readiness
b3bb372b and the immutable successful host-supervisor command b847163c are pinned
provenance, rather than moving inventories or selected output receipts. The old
supervisor source, captured Android environment, Windows fixture and runtime
behavior are not consumed. The new producer embeds twelve literal pins covering
NDK identity, clang/lld/readelf, API31 CRT/libc/libdl/libm and compiler-rt/unwind.
These are a bounded input profile, **not the complete header/sysroot/DLL closure**.

The single clang invocation targeted `aarch64-linux-android31`, C11/O2,
warnings as errors, PIE, stack protector and fortify. Static-PIE linking uses
lld, garbage collection, RELRO/NOW and the previously successful
`--no-mmap-output-file` plus binary stdout route. Python saves that bounded stream
directly as the generated owner ELF. There is no ordinary output-path attempt,
retry, runtime test or fallback compiler. A separate invocation of the pinned
Windows `llvm-readelf` only reads ELF headers, program headers and dynamic tags.

Both commands have 45-second bounds. Binary stdout is capped at8MiB and stderr
at2MiB; text inspection has a combined2MiB cap. The new short unique cwd,
temporary directory and home reside under `out/gvo-build`. The five child-local
TMP/TEMP/TMPDIR/HOME/USERPROFILE values stay there; compiler injection variables
are removed and PATH is local. No global environment changes occur. The producer
records the command, terminal status and logs, hashes all four staged sources,
and checks the original source/producer/provenance and twelve native input hashes
before and after successful read-only output admission. Failed commands preserve
their receipt and stop.

The structural ELF checks require ELF64 little-endian AArch64 ET_DYN, a valid
executable entry load, no interpreter or DT_NEEDED, no writable executable load,
an explicit NX stack, GNU_RELRO and NOW without TEXTREL. Actual load alignments
are reported. lld's rounded RELRO coverage is checked against writable mapping
extents using this profile's4KiB granule. This does not establish16KiB loadability,
Android17/API37 compatibility, runtime relocation or security behavior.

The saved run is `out/gvo-build/r-374d4d8f/receipt.json`, SHA256
`0e235c3332c9edd3786fa2211b67368037617b6eb0c23faf327efde66c308473`.
Compiler exit0 took1.562s with empty stderr; the read-only reader exited0 in0.094s.
No reader exception, overflow, retry or source repair occurred. All listed inputs
and staged sources matched before and after validation.

The resulting624,376-byte `guest_private_view_owner` is SHA256
`8094a8c7ae646c657d122cfb9d7c21ab0913d9be2d43df72d276cf3381cfe896`.
The actual ELF passes the structural checks above: four PT_LOAD segments each
have alignment4096, with no interpreter/needed library, NX stack, no WX load and
RELRO/NOW. These facts do not establish16KiB compatibility or runtime behavior.

H independently read the saved inputs, commands and ELF without replaying the
compiler, reader or output. Source proof is
`out/guest-private-view-owner-build-review/source-pass.json` (e988294f); saved
output proof is `out/guest-private-view-owner-build-review/actual-output-check.json`
(a44db5b3). The review accepts compile/static-ELF evidence only.

Source review of the owner's topology and IPC is external to this build review.
The genuine image/data provider, kernel/LSM support, received-resource identities,
native and property owners, propagation, actual cancellation/reap and future
launch/drain remain unassembled. No phone or aa74 action is included. A successful
cross-build establishes compilation and these static ELF properties only; it
does not select or authorize running this component.
