# Closed DMS parent-hook header preservation

Prepared static component, unselected. Root approved the fixed API and literal finite header contract before implementation. No writer, OEM/native code or device operation ran here. This module does not approve the three-hook artifact, field, instructions, references, debug semantics, metadata, readiness or authority.

`tools/preserve_guest_metrics_parent_headers.py` exports:

```python
preserve_guest_metrics_parent_headers(source: bytes, emitted: bytes,
                                     *, emitted_sha256: str) -> (bytes, receipt)
```

There are no profile, waiver, edited-method or caller-supplied exception parameters. The function writes no files and never changes either input. `emitted_sha256` identifies the supplied bytes; it does not attest their producer. Apply it after **every** forward emission and re-emission, always against the original source bytes. A completely restored inverse uses the separate frozen original-profile preserver; this new profile requires the new dispatch and edited hooks.

The fixed source is complete ordinary DEX039 `classes2.dex`, 10,042,704 bytes, SHA256 `c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f`, from ColorOS services.jar SHA256 `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`. The module hash-checks and reuses only the parser, sealing and byte-whitelist machinery of frozen `preserve_dex_code_headers.py`, SHA256 `943977880527f9cbc21f451c15b887fe5f513c88e9a20fbf3e61717f8068edc6`. That file remains unchanged. The contract is literal module data, not a moving output receipt.

Exactly 46,864 original declared methods, including 45,059 coded methods, must survive with their exact identities, access flags, direct/virtual partitions, code presence, debug presence and class identities. Only one new declared/coded method is admitted: `DisplayManagerService.dispatchOneOsGuestMetricsFromParent(Binder,Parcel,Parcel,int):boolean`, access0, virtual, debug offset0. It makes totals46,865/45,060. Absolute code/debug positions may relocate.

| Method | Original registers/ins/outs/tries/units | Required output |
| --- | --- | --- |
| DMS.onStart()V | 4/1/4/2/57 | 4/1/4/3/65 |
| DMS.onBootPhase(I)V | 12/2/3/5/277 | 12/2/3/6/286 |
| DMS$BinderService.onTransact(int,Parcel,Parcel,int)Z | 7/5/5/0/27 | 7/5/5/0/39 |
| New DMS dispatch | absent | 6/5/6/0/11 |

All other original five-word header tuples remain source-exact after repair. The candidate may differ only in outs before repair; non-outs drift is refused. The parser bounds consumed ordinary039 tables, class data, code, tries and handlers and checks integrity; it is not a general verifier of all DEX data or instruction semantics.

The full method admission and shared-output-word plan complete before allocating the repair buffer. Shared code demanding conflicting outs values is refused. Repair writes only each admitted code_item's source/explicit expected uint16 outs_size at code offset+4, then reseals SHA1 and Adler32 at bytes8..31. An actual byte-difference whitelist verifies that no other byte changed and that size stayed fixed. The repaired bytes are parsed again and the complete fixed profile checked with no remaining outs drift. Source overprovisioning is preserved without a runtime-harmlessness waiver.

Seventeen focused checks passed: fifteen decoded-record guards/positive admission, plus an authored small DEX byte repair/reseal/reparse and rejection of an unrelated instruction-byte change. Record negatives cover missing/extra methods, access, partition, code/debug presence, registers, incoming size, try count, instruction units, class identity and conflicting shared-code demands. These are clearly identified as record probes, not malformed OEM byte fixtures. The byte probes use authored fixtures; no new OEM payload has yet been repaired or accepted by this worker. The receipt is `out/guest-metrics-parent-header-preservation/self-test.json`.

The producer and independent reviewers still own actual instruction/debug forward and inverse maps, exact try/catch behavior, all original metadata/order/reference sets, new field0x42/default-null state, new dispatch body, source code-group relationships, real re-emission and inverse equality. Header success alone cannot admit those obligations. BOOT, lifecycle, source/epoch/currentness and native/runtime acceptance remain external.
