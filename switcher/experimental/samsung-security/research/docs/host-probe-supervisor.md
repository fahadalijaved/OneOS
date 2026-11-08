# Fixed host Context diagnostic supervisor

**PARTIAL_PC_ARM_STATIC_PIE_ONLY_MODELS_UNAVAILABLE.** No phone transfer,
ARM64/Linux process execution, OEM/JNI execution or live selection. This helper owns one child; it is not a general
launcher, security authority or replacement for an external reviewed profile.
The [process-semantics review](host-probe-process-ownership.md) supplies reference
kernel guarantees and limits, not Samsung kernel attestation.

## Fixed profile and wire v1

Future path:
`/data/local/tmp/oneos-host-context-probe-20261106-fbce6bff/host_probe_supervisor`.
Only argument: `--host-context-supervisor-v1`. No caller command/environment args.
The build-generated header contains the nine exact environment values from
saved capture SHA256 `42ee8c3826caf9c69150af07c62348cdaf5f33173a8ed300db0d8f107d47b82a`,
plus only CLASSPATH pointing to that directory's `samsung-context-probe.jar`.
Fixed argv is `/system/bin/app_process64 /system/bin
com.appleexploit.oneos.security.probe.SamsungContextProbe --host-context-probe`.
The profile SHA256 hashes ASCII canonical JSON from the builder's `profile()`:
sorted keys, separators `(',', ':')`. The header and canonical profile are ignored
build outputs; no full captured environment is printed in READY.

stdin accepts only `PERMIT <32 lowercase hex>\n` (40 bytes), or `CANCEL\n`;
accumulated control lines are capped80 bytes. Nonce16bytes comes from nonblocking
getrandom after child setup. Partial/unknown/early/stale input never creates a
permit. After permit admission begins, cancellation can race execution; the
MAY_EXEC latch is set before any internal gate write and never rolled back.

stdout is ASCII NDJSON, line≤8192 bytes, total≤262144 bytes. Common fields are
`v:1,event`. Exact event-specific keys:

| Event | Fields |
| --- | --- |
| READY | nonce,pid,ppid,uid,gid,groups,pdeathsig,domain,ns,profile_sha256,deadline_boottime_ms,remaining_ms,fds |
| OUTPUT | stream (`stdout`/`stderr`),seq (starts1),hex (≤512 chars) |
| PERMIT_ATTEMPTED / EXEC_ATTEMPTED | pid |
| EXEC_ERROR | pid,errno |
| EXEC_PIPE_CLOSED | pid,ambiguous:true |
| SIGNAL | pid,signal,rc,errno |
| HOLD | pid,reason,owned_unreaped |
| REAPED | pid,kind (`exit`/`signal`),status,permit_attempted,exec_attempt_observed,stdout_complete,stderr_complete,cancelled |
| FAIL | reason,errno |

READY uid/gid each contain all four `/proc/self/status` slots real/effective/
saved/filesystem, all1000, crosschecked with getres* first3. Groups is exactly
`[1000]`. ns contains mnt/pid/user labels. fds is ordered framework,services,
app_process,runtime,art,jar; each item contains role,fd,dev,ino,size,mode. fd/mode
are JSON numbers (mode is full decimal st_mode); dev/ino/size are decimal strings.
These six regular files are held read-only and CLOEXEC by the child during the
permit wait, enabling exact `/proc/child/fd/N` hash checks. Metadata alone is not
loaded-code identity or future pathname/exec/mmap attestation.

OUTPUT preserves per-stream byte order and parent capture order only, not a
cross-stream timeline. Combined raw child bytes≤65536; nonblocking queue≤65536
and wire limits include hex/JSON overhead. **OUTPUT is untrusted.** The future
adapter must discard unknown bytes/text and retain only validated authored probe
records/counters; no raw/hex/native logs in final phone receipts.

FAIL reasons: ARGUMENTS,ROOT_OR_PROFILE,CLOCK,SIGNALS,DESCRIPTORS,FORK,CHILD_SETUP,
NONCE_UNAVAILABLE,CLOCK_LOST. HOLD reasons: OWNERSHIP_LOST,NONTERMINAL_WAIT,
UNREAPED,UNREAPED_CLOCK_LOST. REAPED may precede READY on setup failure; this is
cleanup, not diagnostic success. EXEC_PIPE_CLOSED may precede EXEC_ATTEMPTED or
READY and is always ambiguous, never positive exec evidence.

## Ownership and failure boundary

ROOT parent is single-threaded; SIGCHLD is explicitly default without auto-reap.
Unrelated inherited FD3+ copies are closed through a bounded self-FD enumeration
before creating pipes/forking. One exact direct child remains unreaped until a
validated terminal waitpid result. waitid(WEXITED|WNOWAIT|WNOHANG) only observes.
All signals target that owned unreaped fork PID, never a proc-check PID, foreign
process or process group. Terminal reap irreversibly disables signals; unexpected
ownership loss forbids signalling/reacquisition and enters unresolved HOLD.

Child drops supplementary groups, all gids and all uids to1000, rearms PDEATHSIG
after credential transitions, then checks the saved parent. Child waits for its
private permit byte before same-process exec. No shell/grandchild command is used.
Signal dispositions/mask are reset in the child. All control/held-file FDs are
CLOEXEC or closed; standard input becomes `/dev/null`, stdout/stderr owned pipes.

Exact CLOCK_BOOTTIME deadline30s includes setup/permit wait and does not reset
on I/O/EINTR. Deadline/cancel initiates TERM then KILL after2s; this bounds the
decision, not an uninterruptible child's death. The supervisor remains alive in
HOLD until actual reap. Clock loss stops admission, closes the gate and attempts
immediate exact-child KILL, then HOLD/reap; the normal grace guarantee is refused,
with no synthetic clock/fallback. Nonblocking output cannot stall that owner.

Parent-death signalling and inherited FDs can be cleared/revalidated by privileged
or SELinux-changing exec. Preexec PDEATHSIG does not prove postexec cleanup.
Fresh external Cap*/NoNewPrivs/domain/namespace/code/profile admission is mandatory;
UID drop does not imply cap-zero or recreate KSU/system_server equivalence.
Native exit0 requires terminal child exit0, complete observed streams/status and
flushed queue without cancellation/error; even that is not a Context/security
result. Actual validated probe output and independent lifecycle conditions remain.

## PC build/model scope

After source review, `python -B tools/build_host_probe_supervisor.py --build`
uses existing NDK23.1 only, ARM64/API31 static-PIE with no interpreter/DT_NEEDED;
there is no dynamic fallback. ELF is inspected, never executed. The intended
optional fixture path compiles the same shared pure C ownership/control/status
functions to an authored x64 no-CRT Windows DLL for bounded checks; that path
did not complete in the actual result below. The intended fixtures
do not run Linux credentials/fork/wait/signals, Android, OEM or JNI. Old NDK
compilation/model success is not SDK37/device/kernel/SELinux acceptance.

## Frozen partial PC result

Root stopped further linker/backend attempts and relinks. The actual ARM compile
and ELF inspection passed inside the otherwise failed build receipt
`out/host-probe-supervisor/20261106T023347713981Z-0e5e10de435f4e78b6023e99ebb67599/receipt.json`.
That receipt remains **FAILED_PC_BUILD_OR_AUTHORED_FIXTURE** because Windows
same-C fixture linking failed; it was never relabelled a full success.
The separate final [inventory](../inventory/host-probe-supervisor.json) pins the
partial evidence and every failed attempt/continuation. Its summary receipt is
`out/host-probe-supervisor/PARTIAL-RESULT.json`, SHA256
`23926eb1bf783fa9f82d2e495e130fb628fa442f11120992a238bd65a299797f`.

Actual generated artifact `host_probe_supervisor.so` is615,792 bytes, SHA256
`049ed861b5ae2635f4e60e788568f697a9b26ba21860b9045fdc2673b797c9fc`.
Despite the PC storage suffix, it is an **AArch64 ET_DYN static-PIE executable**,
without PT_INTERP or DT_NEEDED, not a shared JNI library. It was not executed.
All four LOAD segments have p_align4096 and4KiB congruence; three are not congruent
modulo16384. Consequently admission is **4KiB-only pending actual selected device
page-size/profile evidence**, not general Android17/16KiB loadability. No relink,
device candidate or controller issuer was selected.

Native C source remained
`778991a903fb161c7ce86f6900bd3efbeb5594b4e200fba2474602c3a05dcb28`.
The exact compiled profile is
`a930f953e7f67d4e91b4c27e6dbb3649003b89c88c1a0123af623b14e7e8df9b`;
generated header is
`ea6336da17fb2c2c6e732dceb7e5be14430fc30683e14761dc1128013eb18ab8`.
The actually executed ARM builder was `e480528a…c003`; its snapshot is preserved
beside that failed receipt. Later command-only COFF-output/CRLF-parser amendments
are identified separately as the current reproduction tool, with no claim they
reran the ARM compile.

Five initial LLD attempts could not open output files; a binary-stdout attempt
then hit the original2MiB command cap. Direct binary capture with strip-debug and
a separate8MiB artifact cap produced the valid ELF. Text output stayed capped2MiB;
no ELF passed through PowerShell text or was printed. No security settings,
exclusions or installation changed. COFF DLL output still failed, including the
two model-only stdout continuations. The authored core object compiled, but
**no fixture DLL loaded, no test cases passed and no fixture waiver is inferred**.

Actual ARM64/API31 preprocessor output pins flags O_RDONLY0, O_ACCMODE3,
O_CLOEXEC524288, FD_CLOEXEC1 and O_LARGEFILE131072. These are target observations,
not desktop guesses; the flags receipt is pinned in the inventory. No native
artifact/profile/mask is bound to a live controller. Parent-death/postexec,
kernel/SELinux, Cap*/namespace and real ownership/cancel/reap behavior remain
unexecuted acceptance obligations.
