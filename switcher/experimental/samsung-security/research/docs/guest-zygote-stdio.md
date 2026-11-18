# Standard descriptors for the held zygote launcher

The held OneOS 0.4.57 `zygote_exec` can reach its final exec with an absent in-root `/dev/null`. Give it three usable standard descriptors from the owned launch child. This closes one launcher input without adding a device node or changing the private `/dev/socket` view. The child-side binding remains to be integrated. [Source and byte evidence](../inventory/guest-zygote-stdio.json)

## Exact branch

The 891,104-byte launcher has SHA256 `d8096b25…` and comes from the held installed APK asset. Its current staged/loaded identity remains unverified. These are ELF virtual addresses in that exact asset. [Saved launcher profile](../out/guest-entry-exec-profile/PROFILE.md)

| Address | Actual behavior |
| --- | --- |
| `0x242b60–0x242b68` | Select `/dev/null` and `O_RDWR`, then call the open wrapper at `0x25a248`. Its selected path supplies `AT_FDCWD` at `0x25a308` and reaches AArch64 `openat` syscall 56 at `0x289784–0x289788`. |
| `0x242b6c` | Test the sign bit of the open result. Failure jumps directly to `0x242bb0`. It bypasses all three `dup3` attempts and the temporary descriptor close. |
| `0x242b7c`, `0x242b8c`, `0x242b9c` | On open success, attempt `dup3` with flags zero into FDs 0, 1 and 2. The launcher ignores their return values. |
| `0x242bb0–0x242bc4` | Both paths call close on FDs 5 through 1023. The three inherited standard descriptors survive this loop on the open-failure path. The preceding socket setup owns FDs 3 and 4. |
| `0x242c4c` | The original launcher attempts `execve` on `/system/bin/app_process64`. Failure returns 127. |

This scope covers the held wrapper up to that exec call. It leaves later `app_process64`, ART, Zygote descriptor reopening and first-fork behavior open. The saved ColorOS native runtime symbol table identifies `FileDescriptorInfo::ReopenOrDetach` and `FileDescriptorTable::ReopenOrDetach` as bounded follow-up leaves.

## Smallest source-supported binding

The current GVO v3 child creates a private, `NOSUID|NODEV|NOEXEC` tmpfs and its `socket` directory, then validates and retains both directory objects. It supplies no `null` entry. Creating a character node on a `NODEV` mount would still leave that device unusable. The existing child hygiene checks every inherited FD, including 0–2, and preserves only its actual named resources. Its FS-only API supplies no exec transition. [Private dev skeleton](guest-private-dev-skeleton.md)

An integrated launch child should obtain one genuine null-device description from the held inherited root before entering the guest root. The controller owns that actual FD. It maps it to 0–2 with exec inheritance enabled in the child only, then disposes of any extra duplicate under the launch owner's existing close-once rules. The child must resolve low-FD collisions first. The current GVO hygiene can leave control, witness or loop FDs in those slots. Rebinding them without moving or consuming those exact owners would destroy live custody. Stdio assignment belongs after descriptor hygiene and before the first exec, while the child is single-threaded. It leaves the guest `/dev` directory and retained host mounts alone. A pipe, `O_PATH` handle or regular file does not meet the selected null profile.

The isolated [validator](../compat/native/guest_zygote_stdio.c) borrows only FDs 0–2 and accepts only `S_IFCHR` with `st_rdev` major 1/minor 3, `O_RDWR`, no `O_PATH` and no `FD_CLOEXEC`. It requires all three to refer to the same device inode as measured by `st_dev` and `st_ino`. It preserves syscall failure, with `ENODEV` for the wrong device, `EINVAL` for flag violations and `EXDEV` for a different object. It performs no I/O on the devices and never acquires, closes or retargets a descriptor. Equal inode metadata does not establish a shared open file description. The real launcher must retain its actual source FD and exclude replacement through exec. No shared owner API or launch integration changed.

## PC verification

The exact C/header pair compiled once with the existing Android NDK for AArch64 API 31 using C11, `-Wall -Wextra -Werror` and compile-only output. The 1,736-byte ELF relocatable object has SHA256 `d91bb21a…`. Static symbol/relocation inspection found one defined validator and only `fstat`, `fcntl` and `__errno` as undefined functions. Both commands exited 0 with empty diagnostics. The launcher instruction words were rejoined to their exact held ELF load offsets. No executable was linked or run. [Compile and inspection receipt](../out/guest-zygote-stdio/compile-static-v1/receipt.json)
