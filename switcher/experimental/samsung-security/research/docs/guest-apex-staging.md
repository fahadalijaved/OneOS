# Exact donor runtime and ART APEX staging inputs

The PC staging step selects the existing payload files for the OneOS 0.4.58
`x9u-in-sultra` cohort. The [receipt](../out/guest-apex-staging/receipt.json)
is the input manifest. It records the source paths and hashes without copying
either payload or creating a mount.

| OneOS input | Held bytes and filesystem | Module identity | Canonical target |
| --- | --- | --- | --- |
| `runtime_payload.img` | 5,296,128 bytes, EROFS, SHA-256 `f45b10cb…` | `com.android.runtime`, version 1 | `/apex/com.android.runtime` |
| `art_payload.img` | 31,633,408 bytes, ext4, SHA-256 `391e25c0…` | `com.android.art`, version 371000140 | `/apex/com.android.art` |

Both full hashes match the exact OneOS IN set entries. The runtime payload
matches the original APEX ZIP member. Its held extracted manifest matches the
outer manifest. The ART compressed wrapper contains the exact held
`original.apex`, which contains the exact held payload. The wrapper and inner
manifest agree on module name and version. The inner manifest also matches the
bytes read directly from inode 81 in the actual ART filesystem. The stage tool
checks regular file framing, exact extents, filesystem magic and AVB footer
bounds. AVB signature verification remains outside this step.

The [runtime audit](guest-runtime-apex.md) read empty `/apex` inode 13 and the
interpreter symlink directly from the donor image. OneOS’s matching preparer
selects the canonical paths at lines 3853, 3933 and 3935. Its loop at 3924–3928
handles versioned directories only when they already exist. The manifest
records `/apex/com.android.runtime@1` and `/apex/com.android.art@371000140` as
conditional names for the same respective payload hashes. Neither alias was
observed in the donor image or selected for a future mount. The compressed
wrapper filename does not determine the ART mount name.

A future isolated child must retain the actual selected payload files and
verify their namespace-local attachments under the admitted guest root.
Read-only loop attachment, mount readback, any needed version alias, the active
APEX list, and the effective `/linkerconfig` remain separate runtime inputs.
This manifest covers the two named payloads. It does not establish the complete
APEX cohort or readiness to launch.

Run `python -B tools/stage_guest_apex_inputs.py --stage` to create the receipt
once. Run `python -B tools/stage_guest_apex_inputs.py --verify` to rederive the
same bytes and check the saved receipt. Both commands exited 0 for the current
artifact. [Byte pins](../inventory/guest-apex-staging.json)
