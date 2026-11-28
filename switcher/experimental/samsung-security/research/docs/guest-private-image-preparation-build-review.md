# Private image preparation v2: independent build review

**PASS for source and saved compile/static-ELF evidence only.** The actual artifact is 638,664 bytes, SHA256 `28365340e25e60857a43eb0237c36cbde21eafa328c32030cad99d155a6ea6b4`, from [receipt f7ca48c8](../out/gip-build/r-6385be02/receipt.json). The reviewer did not invoke the producer, compiler, linker, readelf, output, model, kernel, OEM code or phone. User selection remains **offline only**.

The fresh C source review is [7f71297e](../out/guest-private-image-preparation-review/source-v2-pass.json). It covers the changed owner/provider/supervisor source and the new configuration-result/ACK/five-view protocol. It found and closed a missing loop-control device-number guard before the global ioctl. It does not transfer the old v1 lifetime/IPC proof or turn the earlier API ACK into implementation evidence.

The separately reviewed producer is `tools/build_guest_private_image_preparation.py`, SHA256 `1662ad528da9429412f11d2ed8bf9b2c02b95b4337624170deeb06730b332ef4`. Before use, the review closed three defects: reader setup exceptions after Popen could bypass cleanup; the parsed GO and recorded digest could come from different bytes; and the stated nonzero ELF entry was not explicitly enforced. Exact predecessor `6ca0a996` and its source-phase metadata remain in the author's history. The [wrapper source PASS ccf9c307](../out/guest-private-image-preparation-build-review/source-pass.json) requires a separate root GO; it did not authorize the build itself.

Root's actual GO was `635b29f81ed91273beaeae6ca992dd20c1f2b2088b0adf6528b12421a4b681c5`. The saved records show one compiler command and one read-only readelf command, both exit 0, with empty stderr, complete readers and recorded process reaps. Their recorded durations are 1.328 s and 0.079 s. The compiler consumed exactly four staged authored C units and three headers, linked with the listed existing NDK inputs as an Android API31 static PIE. Binary output was captured directly from stdout. No produced executable was started.

| Independently read artifact field | Actual value |
| --- | --- |
| ELF | ELF64, little endian, AArch64, ET_DYN |
| Entry | `0x19680`, matching `_start` in an executable LOAD |
| Tables | 11 program headers, 23 section headers |
| LOAD segments | Four, each aligned to 4096 bytes; no writable executable LOAD |
| Runtime linkage | No PT_INTERP or DT_NEEDED |
| Protection metadata | NX stack, GNU_RELRO with the selected 4 KiB rounded coverage, NOW/PIE; no TEXTREL |

The independent data reader compared all eleven program-header rows, nineteen dynamic rows including NULL, and selected ELF-header values against the saved readelf text. It also compared all full section records with the producer's saved records and all 23 section indices/names with readelf. It checked selected actual entry/API symbols as metadata, without treating their names as runtime authority or proving every instruction's semantics.

The [actual readback proof 45fe4663](../out/guest-private-image-preparation-build-review/actual-output-readback.json) verifies all 32 entries of the actual build freeze, 22 staged source/evidence files, 15 immutable input snapshots and fourteen listed NDK tool/header/CRT/archive pins. These are bounded checks, not a whole-repository or complete sysroot/Windows-loader audit. The first reviewer-only reader attempt stopped at an incorrect parent-directory path before reading the receipt; its script and failure note are preserved. The corrected reader completed without replaying any subject tool.

Executed report inputs are the exact [prebuild Markdown a38b4e3a](../out/gip-build/r-6385be02/inputs/10-guest-private-image-preparation-build.md) and [prebuild inventory a92fb4eb](../out/gip-build/r-6385be02/inputs/11-guest-private-image-preparation-build.json), copied before compilation. Later finalized normal metadata is not relabeled as a compiled input. The executed producer, GO, source review and wrapper review also have immutable snapshots in that run.

This establishes a PC compile/static-ELF component. It does not establish 16 KiB loadability, API37 support, target kernel/LSM acceptance, loop or namespace behavior, SCM credentials at runtime, AUTOCLEAR release, terminal3 behavior, image/writer/security/native ownership, CE/UUID/quota/property requirements, actual drain or full return. `LOCAL_RELEASED_KERNEL_UNCONFIRMED=3` remains incomplete; no phone, installation, activation, restart or broader runtime approval follows.
