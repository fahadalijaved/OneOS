# Donor runtime APEX for the isolated ColorOS entry

The original Find X9 Ultra IN Full image supplies the exact runtime payload
needed by the OneOS `x9u-in-sultra` set. The audit read 5,521,288 selected bytes
from the held ext4 image. It recovered the outer APEX and `app_process64` from
their original inodes and verified both against the saved extraction. It also
read the original interpreter symlink and empty boot mount targets directly.

| Selected object | Verified fact |
| --- | --- |
| `/system/bin/app_process64` | Inode 8768, AArch64 ELF64, 51,880 bytes, SHA-256 `78d3bf52…`. `PT_INTERP` is `/system/bin/linker64`. |
| `/system/bin/linker64` | Original inode 8947 is a fast symlink to `/apex/com.android.runtime/bin/linker64`. |
| `/system/apex/com.android.runtime.apex` | Original inode 8609, 5,435,392 bytes, SHA-256 `f92cbc75…`. The exact ZIP member `apex_payload.img` is EROFS. |
| Runtime payload | `com.android.runtime` version 1, 5,296,128 bytes, SHA-256 `f45b10cb…`. The raw payload exactly matches the held extraction and OneOS’s IN set entry for `runtime_payload.img`. |
| Runtime `bin/linker64` | The saved extraction contains the 2,640,432-byte ELF64 AArch64 interpreter, SHA-256 `97f31018…`. It has SONAME `ld-android.so`, four 16 KiB-aligned load segments and no `DT_NEEDED` or `PT_INTERP`. |

The [inventory](../inventory/guest-runtime-apex.json) pins the exact inputs and
outputs. The 14.67 GB image hash comes from the prior acquisition. This audit
verified the selected extents and stable file metadata without rehashing the
whole image. The EROFS member hashes use the existing offline extraction and
its recorded file list. A WSL availability check was denied in this shell, so
the EROFS extraction itself was not repeated here.

## Boot placement and libraries

The image has empty root-owned 0755 directories at `/apex` (inode 13) and
`/linkerconfig` (inode 31). The proposed isolated ColorOS child needs an owned
writable scaffold at its image’s `/apex` before creating the mountpoint
`com.android.runtime`. The held EROFS object belongs there read-only, with the
interpreter executable through the original symlink before
`execve("/system/bin/app_process64", …)`. This is placement for the ColorOS
child. The Samsung installd sibling uses the separately captured Samsung
interpreter and library cohort.

OneOS 0.4.58 `guest_prepare.sh` selects `runtime_payload.img` and mounts it
read-only at the same canonical APEX path. Its separate host `/linkerconfig`
recursive bind at lines 334–335 belongs to the legacy preparation path.
Donor `init.rc` creates bootstrap and default config targets at 121–140, then
calls `perform_apex_config` after `apexd-bootstrap` at 156–157 and again at 1663.
The donor source files and actual `linkerconfig` binary are held. The generated
configuration for the future private namespace is still an unbound boot input.

The saved runtime APEX supplies `libc.so`, `libdl.so`, `libm.so` and
`libdl_android.so` under `lib64/bionic`. ELF `DT_NEEDED` links the selected
Bionic cohort to the interpreter’s `ld-android.so` SONAME. Static symbol
readback also found definitions in the linker for every selected unversioned
`__loader_` import in libc (4), libdl (12) and libdl_android (9).

All 14 direct `app_process64` library names have inspected donor AArch64 ELF
candidates with matching SONAME. Nine are in the system extraction. Two,
`libnativeloader.so` and `libsigchain.so`, were read directly from the held
donor ART ext4 payload. The other three are runtime Bionic libraries. Actual
transitive relocation, linker namespaces, APEX alias selection and staged or
loaded bytes remain unproved.

`python -B tools/audit_guest_runtime_apex.py` reproduces the selected-data
record from the held sources. The static audit ran without mounting or executing
any donor image, launcher, APEX binary or device operation.
