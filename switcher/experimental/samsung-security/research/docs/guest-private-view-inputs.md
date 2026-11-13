# Fixed-stage inputs v2: image/data source prepared

**V2 compiled and statically reviewed only; unexecuted and not selected for runtime.** Public three-call
metadata-only API remains open_existing/begin_view/close. The older gvi5e645/
header68a7 source, independent review and8343 shared artifact are historical;
exact beforeimages are in the pre-v2-source history/Git749. No old compile or
review proves the changed image/profile/protocol source. Parser is unchanged.

open_existing is read-only input adoption: fixed /data/local/tmp/oneos stage,
system.raw, system.raw.id and staged data, with no-follow/CLOEXEC custody. It no
longer requires a parent-mounted rootfs or opens a loop/root mount. Stage/image/ID
remain root-owned and not writable by group/others. Staged data uses the EXACT
1000:1000/0771 producer profile (installed guest_prepare2907-2908), not root-only
or arbitrary accepted UID/mode. No chown/chmod/relabel/copy/rebuild occurs. Host
/data same object, mounted descendants and symlink components refuse.

Original bounded three-token ID/stat freshness remains cached staging evidence:
size,64 lowercase digest characters, canonical dev:inode:size:mtime. Accepted
delimiters are space/tab/CR/LF. Held objects and fixed paths are rechecked; no
fresh image hash, immutable contents or writer exclusion is claimed. Root's
saved0ec098 observation describes init's namespace only; an unmounted rootfs
proves nothing about image receiver directories. Absence returns NEED_PREPARED_STAGE,
other unsupported/denied profiles refuse; no automatic preparer or stage writes.

begin_view is EFFECTFUL: constructs the new internal image/data plan and retains
the actual gvo owner before any failure cleanup, including after-fork errors.
Parent adopts loop candidate before fork; child owns private configuration/mount
preparation and final view transfer. No gvo pointer, raw descriptor or PID is
exported; success copies only namespace inode and two peer groups. Nested/repeated
begin and reopen cannot erase the live handle.

close preserves HOLD and actual inputs whenever underlying configure commit,
local close or child reap is unknown. Only known underlying terminal0 (no own
configuration) or explicit3 (child reaped, all local capabilities closed, kernel
release UNCONFIRMED) permits provider-input closure. It then consumes each own
input cell once. If ALL those closes are known, terminal3 remains3 forever in
an opaque non-reusable tombstone. It cannot become0/full cleanup; local close
uncertainty retains HOLD. No numeric FD retry, foreign loop clear or new attempt.

Root APIc34f/ACK3a603 selects source implementation only. Complete v2 source/lifetime/IPC review and the separately authorized compiler/
static-artifact review passed, within the limited scope below. One new static compile plus read-only readelf ran; no
test/helper/OEM/kernel/phone action ran. User chose OFFLINE ONLY. Full
native/security/image identity/CE/quota/property/writer/drain/return admission
remains external and unclosed.

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
