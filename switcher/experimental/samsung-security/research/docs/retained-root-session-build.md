# Retained root session: PC build

The combined producer passed once with the held native and Java sources. Root's tool `ab2f79` ended0; no compiled output ran. The saved receipt is `out/retained-root-session-build/r-c535d79a/receipt.json` (`83fd1b65...`). Independent saved-output review `b7617f9d...` checked the actual files without replay.

The build ran one existing NDK API31 AArch64 cross-compile, read-only `llvm-readelf`, and SDK37 `javac`; all three commands ended0. Actual commands, environment, diagnostics, six normal source/header inputs, three source-review proofs, 26 captured input snapshots and exact executed producer are retained. Compiler warnings remain in the saved logs. No D8 phase was selected.

| Output | Actual result |
| --- | --- |
| Native controller | 596,312 bytes; SHA256 `1cacc47717468c6e91b791126ce011af25dab9bdbde50765ec0a013cea2b116b` |
| Static ELF admission | AArch64 ET_DYN static PIE, no interpreter/NEEDED, NX stack, no writable-executable LOAD, RELRO/NOW; selected4KiB LOAD geometry |
| Real Java | Ten Java8 class definitions from Session, Spawn, Protocol and Command; public SDK37 declarations only |
| Model input copies | Nine byte-identical classes; only real `RetainedRootSessionSpawn.class` excluded for the separately authored process fixture boundary |

The observed Java map was recorded before checking its source-derived closure, including the natural Java8 private-access marker and worker Runnable. No ABI projection, saved program-class input or class shaping was used. Full class and artifact hashes are in `inventory/retained-root-session-build.json`.

This proves compilation and static shape only. It does not prove 16KiB Android loading, kernel/pidfd/SELinux behavior, actual root-session setup/closure, the host-controller join, guest handoff, app packaging or any of the18 device cases. Native helper, Android/OEM/JNI implementations and phone operations were not executed. Model results belong to their separate workflow and are not claimed here. The closed controller publishes no host or guest authority.
