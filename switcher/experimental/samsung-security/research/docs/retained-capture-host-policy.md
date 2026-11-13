# Samsung captured policy supports the v2 permit type

**The captured Samsung source explicitly supports system_server reading a `system_data_file:s0` permit directory/file under `/data/system`.** This is stronger evidence than the earlier unpacked-path search. Actual future labels, effective loaded policy and target-process access remain unproved. No policy, label, source-v2, phone state or request object was changed by this lookup. The prior [access assessment](retained-capture-permit-access.md) and its `76b9e51d…` freeze remain unchanged; this is a separate successor finding.

## Bounded archive binding

Parent `inventory/os-comparison.json` references the immutable Samsung mounted-OS comparison, archive 20,434,769,920 bytes, prior full-stream SHA256 `28eb27547fcc96348aa54f614a77aecd8bfcdbf875b61de2dd5279787985d96e`. The comparison receipt is `c1785505…`; its gzip member manifest is `6654252d…`.

That manifest supplies exact physical paths/sizes/hashes but no byte offsets. With root's explicit permission, the extractor visited **15,280 headers**, sought over unselected payloads, read **8,228,349 header/extension bytes** (cap32MiB), and read **7,182,195 selected payload bytes** (cap8MiB). Ten exact regular-file policy/context members were extracted, individually size/hash checked, to ignored `firmware/retained-capture-host-policy/`. TAR stat identity was unchanged before/after. The existing strict header/path/sparse/duplicate checks were reused. No whole20GB scan, new full archive hash, archive-wide extraction, repull or policy execution occurred. Prior full-stream identity/framing is reused evidence, not a freshly claimed verification of every other byte.

The selected members are platform, system_ext, product, vendor and ODM CIL plus each partition's file-context text. Key inputs are:

| Member | Bytes | SHA256 |
| --- | ---: | --- |
| `system/etc/selinux/plat_sepolicy.cil` | 3,302,558 | `425aba8b73da746a6338a3d42f6dfd20b5bfdd02163928f1aee0b7b333ab03c9` |
| `system/etc/selinux/plat_file_contexts` | 50,429 | `5a8648bf340c742a8507a1937e02ec1e6a22baa0bc457ef39a1db90c7ad52902` |
| `system_ext/etc/selinux/system_ext_sepolicy.cil` | 949,328 | `3ea88731ec5753c3d6803c9cf85cdaeae507bfbb6d64ecdca650438575736b5c` |
| `vendor/etc/selinux/vendor_sepolicy.cil` | 2,571,057 | `774c8b127587293bf8ca5706ec090c16182977ac2273da55e39a6161c29e838c` |

All ten hashes, actual selected header/data offsets, read budgets and stat binding are in the [new inventory](../inventory/retained-capture-host-policy.json) and its immutable extraction receipt. The exact extraction-run producer source is retained separately; adding static audit support did not rewrite that historical receipt or rerun extraction.

## Concrete source access facts

These are lines of the actual captured Samsung platform CIL, not donor/AOSP substitutions:

- **67828:** direct `system_server` → `system_data_file`, **dir** allow includes `read`, `getattr`, `open`, `search`. This covers the helper's relevant directory operation categories, including its O_RDONLY directory open.
- **67833:** direct `system_server` → `system_data_file`, **file** allow includes `read`, `getattr`, `open`.
- **24581:** `domain` → `system_data_root_file`, dir allow includes `getattr/search`; the captured domain attribute includes system_server. This supplies concrete source support for traversing `/data` as observed.
- Relevant file/dir MLS constraints at **459–460 and468–469** are preserved as source evidence. Their level/type conditions must still apply to actual source and target contexts; this tool does not execute a complete composed-policy decision.

Samsung platform file contexts at **490** map the general `/data/(.*)?` pattern to `u:object_r:system_data_file:s0`. The old tmp path has its separate shell-data pattern at **526**. A bounded textual filter checked all **3,308 context patterns** from the five captured partitions against the proposed v2 directory and `request-v1`. Each v2 path matched only platform490, both `system_data_file:s0`; no pattern failed to parse in that filter. This is source-fit evidence, **not libselabel matching/ranking, a type transition, restorecon execution or actual label application**.

Root's separate read-only observation already reports the current system_server domain `u:r:system_server:s0`, filesystem UID/GID1000, global Enforcing and the existing `/data/system` parent labeled `system_data_file:s0`. Together with the direct source allows, the `/data/system` choice is concretely supported. The operator permit still conveys no security authority.

## Exact remaining step

After **separately authorized** creation of the v2 dedicated objects, retain the fixed reviewed path/modes/owner and observe the actual directory and request labels. They must be the intended types/levels; a root creator can have transition/label behavior that a file-context pathname alone does not prove. Then account for any effective loaded-policy/root-overlay difference and the real target-process open/read result. This lookup grants no new creation, relabel, policy change, access attempt, scope, restart or installation permission.

An actual open failure remains a refusal; the helper must not convert it into permit success. Conversely, an allowed source rule is not proof that the callback ran, the runtime capture succeeded, or Samsung credential/native authority is admitted. No source-v2 build needs to wait for this offline finding, and no request contents or credential files were read.

Saved-content verification only:

```text
python tools/audit_retained_capture_host_policy.py --audit
```

The audit passes **28 checks**. No new tool was installed; Python standard-library TAR/text/regex/hash readers performed only static operations.
