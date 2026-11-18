# Executed host tests for guest zygote stdio

The actual validator passed 53 stable-custody scenarios and 1,189 assertions under the authored host metadata model. The production C and header are byte-identical to the Android API 31 compile-only inputs. The model exercised the actual validator's decisions while replacing `fstat` and `fcntl` with test functions. It did not acquire, close or reassign a real descriptor. [Earlier source and compile analysis](guest-zygote-stdio.md)

The fixtures cover the real null profile, non-character types, wrong major/minor including high device-number bits, read-only/write-only/invalid access flags, `O_PATH` and `FD_CLOEXEC`. The inode tests distinguish equal inode numbers on different backing devices and different inode numbers on one backing device, including differences in high bits. For each slot, the fixtures also inject `EBADF` from `fstat`, `EINTR` from `F_GETFL` and `EIO` from `F_GETFD` and check the exact returned error and last metadata operation. The mock rejects any additional descriptor number, operation, retry or out-of-order call. [Test source](../compat/tests/native/guest_zygote_stdio_test.c)

One separate observation deliberately violates custody. After the successful `fstat` of FD 1, the mock substitutes a regular file with the same access and descriptor flags. The validator returns success from the observations it received even though the model's FD 1 now has a different type. This demonstrates why the launch owner must prevent concurrent table changes. A second metadata sample still leaves a gap before exec. Under the selected stable-custody contract, the focused tests found no implementation defect requiring a source change.

## Integration point

The current GVO public API, `gvo_begin(const struct gvo_plan *, struct gvo_owner **)` and `gvo_receive_partial(struct gvo_owner *, struct gvo_observation *)`, accepts only the existing witnesses and returns copied observations. The owned child's `close_unlisted(int keep1, int keep2, int keep3, int keep4)` retains only the named control, witness and loop slots. It includes FDs 0–2 in the sweep. After publishing the partial view, the current child loop accepts cancellation and terminates. There is no existing exec branch or stdio owner in that API. [Current GVO implementation](../compat/native/guest_private_view_owner.c)

The expected future glue is private to the real launch-child path. The proposed signature carries the source FD as a consumed ownership cell and keeps cleanup uncertainty separate from the operation error:

```c
static int gvo_install_zygote_stdio_for_exec(int *owned_null_fd, int *close_error);
```

- Acquire and retain the genuine null description from the admitted inherited root. The caller owns a source FD numbered at least 3. Run after the existing child descriptor sweep, or explicitly account for the source cell in a reviewed successor to that sweep.
- Before writing slots 0–2, move any live control, witness or loop cell in those slots to an owned higher descriptor and update the actual cell, or retire it through the existing owner. The current `close_cell(int *)` consumes the cell before attempting close, and `tracked_close_cell(int *, int *)` preserves the primary `errno` while recording the first cleanup error. Do not silently overwrite a live owner with `dup3`.
- In the private single-threaded descriptor table, bind the same actual description to 0–2 with checked `dup3(source, target, 0)`. Consume the extra source descriptor exactly once. A partial install or uncertain close keeps exec closed and follows the existing actual child cleanup and wait obligation.
- Call the existing `oneos_guest_zygote_stdio_validate(void)` after source retirement and immediately before the fixed exec. No shared descriptor table, descriptor-changing signal handler or callback may intervene between binding, validation and exec. FDs 3–4 and the held launcher's later close loop retain their separately documented meanings.

This signature is an integration proposal. The validator remains a read-only fixed-slot check. No GVO source or public declaration changed, and the test does not cover real Linux device operations, exec inheritance or later Zygote forks.

## Actual host run

The existing pinned MSYS2 UCRT GCC 15.2.0 toolchain compiled the actual validator and the authored model in one Windows workflow. Its two commands exited 0 with empty stderr. The first-read C/header/model/runner bytes were retained in the unique run directory. The new runner reused the existing mountinfo harness's captured command helper and tool pins. The saved executable is 139,893 bytes, SHA256 `915c32cb4ccd44e7472125a078ba6b9bfeaa77bcf7baaef379b80c5b2b2c75ee`. A separate saved readback rehashed the eight source pins, eight snapshots, 30 tool pins, command logs and executable without replay. [Host run receipt](../out/guest-zygote-stdio-tests/r-fb25e320/receipt.json)
