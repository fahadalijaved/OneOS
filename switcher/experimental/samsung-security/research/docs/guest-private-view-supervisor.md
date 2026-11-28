# Fixed-stage filesystem supervisor v2: source prepared

**V2 compiled and statically reviewed only; no execution.** The old7dfa source and its source/compile
proofs remain exact historical beforeimages in pre-v2-source/Git749. Existing
owner/provider/parser artifacts do not prove this changed caller. Default
invocation is no-op; only exact --prepare-fs-view selects effectful preparation.
No raw FD/path/PID/hash/token/command options, exec, native daemon, OneOS script,
setns/chroot, capability setup or phone operation exists.

open_existing is read-only adoption; begin_view calls the actual gvo fork/private
namespace/loop configuration/image mounts. SIGCHLD is default flags0/no auto-reap;
no threads or competing waiter are created. INT/TERM/HUP handlers set one flag,
SIGPIPE is ignored, and the actual opaque provider/gvo owner remains retained
on every nonnull error path. Parent never enters or mounts the child namespace.

The BOOTTIME30s decision budget, stdin cancellation and synchronous-call limits
are unchanged: flags/EOF cannot safely reenter open/begin, so they are observed
immediately after return. The original gvo budget is separate; kernel scheduling/
blocking/suspend prevent any hard process-death or cleanup deadline. Cleanup
polls actual gvi_close; unknown commit/close/reap remains HOLD indefinitely,
never a timeout success or numeric-PID/FD recovery.

New terminal3 is handled explicitly: emit LOCAL_RELEASED_KERNEL_UNCONFIRMED and
exit3, never CLOSED_REAPED/exit0/full return acceptance. It means actual local
resource release and reap only, with deferred kernel loop release unobserved.
Known no-own-configuration refusal emits REFUSED_NO_OWN_CONFIGURATION_CLOSED
and a nonzero operational exit. The default no-op can return0. HOLD is emitted
once; no unknown child/native text or user/state material is logged. Nonblocking
bounded authored frames are not delivery proof; exit3 is still no transport,
security, functional or kernel-cleanup acceptance.

Fresh complete source/IPC review and separately gated static build/output review
passed, within the limited scope below.
User explicitly chose OFFLINE ONLY: no ADB/install/settings/restart/phone/OEM or
helper execution. Image/stage/loop-writer, native/security/UUID/CE/quota/property,
real drain and return admission remain unclosed.

## Actual compiled/static-reviewed component boundary

The complete C source proof is immutable7f71297e at
`out/guest-private-image-preparation-review/source-v2-pass.json`. The exact
reviewed source phase6196 is preserved unchanged, including a hash-named copy
in the successor producer inputs. Historical report paths resolve to exact
beforeimages recorded in
`out/guest-private-image-preparation-build/history/pre-static-result-reports/REPORT-MAPPING.json`.
Neither the source proof nor the phase was refreshed to imply this later result.

Root authorized ONE actual PC pipeline using wrapper1662 and GO635b29f8.
`out/gip-build/r-6385be02/receipt.json` SHA
`f7ca48c8a0176495ba2cb3f65786311c3a31af9c30767d92e21d0e286b2b7677`
records compiler/readelf exits0/0 (1.328s/0.079s), empty diagnostics and exact
executed source/header/report/review/GO snapshots. The actual638,664-byte ELF
`out/gip-build/r-6385be02/guest_private_image_preparation` is SHA
`28365340e25e60857a43eb0237c36cbde21eafa328c32030cad99d155a6ea6b4`.
It was never executed, including default/help. No DSO or harness was built.

Independent saved-output proof
`out/guest-private-image-preparation-build-review/actual-output-readback.json`
SHA45fe46639b86f5b80c051a3f1f4de5601a2982e396a8ad49c5eb6fe5d589fde0
rehashed actual evidence and independently compared ELF/readelf metadata without
replaying tools. Actual ELF has11 program headers/23 sections, static-PIE shape,
nonzero RX entry, no interpreter/NEEDED/TEXTREL, NX/no W+X, RELRO+NOW and4096 LOAD
geometry. This is not16KiB/API37/kernel/LSM/loop/SCM/namespace propagation or actual
close/terminal3/runtime acceptance. Kernel release remains explicitly UNCONFIRMED;
no native/security/writer/drain/return or launch gate closes. User chose offline
only; no phone/ADB/install/setting/restart/OEM execution occurred.
