# Admission-closed retained root controller

Status: independently reviewed authored source only. No compiler, helper, Android/OEM implementation,
socket operation, root command or device workflow ran for this component.

`compat/native/retained_root_session.c` implements the native side of Root's
`retained_root_session_protocol.h`. No arguments returns zero without descriptors,
signals or output. The sole explicit argument is `--closed-session-v1`; other
arguments fail. The explicit path requires real/effective UID0 and exactly one
entry in the actual `/proc/self/task` directory. Those restrictions do not grant
host security authority or prove future mount capabilities.

Before opening that directory or acquiring another descriptor, explicit entry
adopts inherited fd3 and compares `fstat(3)` with `stat("/proc/self/exe")`: both
must be regular files with the same device/inode. The fixed app root command
verifies and executes this same opened image through `/proc/self/fd/3`. Native
consumes fd3 once before further acquisition, without retry on close failure.
Default no-arg entry never touches it. This prevents a pathname replacement
between image checking and execution; it does not authenticate a host issuer.

## Actual source behavior

The private stack controller exists before acquisition. It retains the image,
each duplicated standard stream, listener, accepted peer, self pidfd and received right
before fallible validation. It also retains the task-directory stream before
enumeration. There are no threads, forks, execs, mounts, namespace operations,
properties, GVI calls, guest launch or host backend operations.

INIT is read from stdin; OFFER is written to stdout. The native side generates
16 bytes with real nonblocking `getrandom`, with no time/PID/weak fallback, and
binds an abstract AF_UNIX stream listener. Its 42-character name is
`oneos.ors.` followed by 32 lowercase hexadecimal characters. OFFER carries that
printable name without the kernel abstract-address leading NUL, then zero
padding. No filesystem socket is created or unlinked.

The first accepted peer must have real `SO_PEERCRED` PID/UID equal to INIT's
fields. INIT remains an untrusted transport association, not proof of the app's
parent, a host issuer, source provenance or permission. A wrong first peer fails
the session; the controller does not keep accepting until an assertion matches.

Only after that comparison does `syscall(SYS_pidfd_open, getpid(), 0)` acquire a
real native self descriptor. There is no integer syscall fallback or simulated
descriptor. IDENTITY sends one actual SCM_RIGHTS descriptor with its 64-byte
frame. A positive partial `sendmsg` is continued with plain sends, never by
resending the right. The controller retains its own descriptor copy until close.
The descriptor establishes a process reference, not executable/source authority.

## Fixed wire contract

All frames are 64 bytes: `ORSC`, version u16, kind u16, sequence u32, status u32,
then 48 payload bytes. Integers are big-endian. INIT uses sequence0/status0 and
PID/UID followed by zero padding. OFFER and IDENTITY use sequence0/status1;
IDENTITY carries native PID followed by zero padding and exactly one right.
The shared header is authoritative for kind/status numeric values.

Requests after IDENTITY are only PING or CLOSE, status0, zero payload and exactly
the next sequence starting at1. PONG is status1; CLOSED is status2 with the same
sequence. No wrap, generic action, caller selector, JOIN, START or VERIFY exists.
PING at UINT32_MAX is refused rather than permitting a wrapped next request.
Malformed headers, padding, unknown kinds, ancillary data, EOF, interruption and
timeouts fail. Any received SCM_RIGHTS descriptors are adopted before refusal
and cleanup, including rights delivered alongside truncated ancillary data.
The selected Linux contract closes rights discarded by control-buffer truncation.

One absolute 30-second deadline covers INIT through identity delivery. The closed
controller can then remain idle without a heartbeat: it waits for actual socket
input, peer EOF/HUP or a termination signal in 250ms poll slices. On readable
input, a fresh 30-second deadline covers the complete request and reply; trickled
bytes and EINTR do not reset it. Nonblocking descriptors and bounded poll slices
permit signal cutoff. This is an I/O budget, not a hard scheduler or syscall
preemption guarantee. This idle policy is solely for the present closed transport;
it supplies no retirement policy for future admitted GVI, guest or host resources.

## Close and failure

CLOSE cuts off local admission, closes the listener and native self-pidfd copy,
then writes CLOSED while the actual control descriptor still exists. The common
cleanup then closes the peer and duplicated streams. Therefore CLOSED is a local
control acknowledgement, never proof of complete FD cleanup, native exit, a
Java process reap or unrelated work/descendant drain. The caller must observe the
real pidfd exit and its own process/thread/stream cleanup separately.

Each close is consumed before the syscall and is attempted once. EINTR or other
close errors retain an uncertain private disposition and are never blindly
retried against a potentially reused integer. Directory-close failures are also
latched. Cleanup attempts the remaining owners; any cleanup failure yields exit3,
while other refusal/protocol failures yield exit2. Only the successful local
CLOSE path plus successful owned cleanup returns0. Process exit is the final
kernel reclamation boundary; no live native lease is claimed from retained data.

## Integration boundary

The app author owns the fixed verified root executable path, actual spawn,
bounded streams, socket-peer and pidfd validation, and retained failed Attempt.
This native component does not validate its executable hash or create that app
source. A matching UID/PID, descriptor, ACK or code hash cannot open host authority.
The genuine host-controller join and guest SystemServer delivery remain separate
unimplemented operations. Existing native owners/supervisors and OneOS launch,
switch, return and security guards are unchanged.

The source targets the existing NDK23/API31 AArch64 profile. Table's read-only
header inspection found declarations for the selected socket, random and pidfd
syscall interfaces. No compilation, kernel/SELinux support, app placement, runtime
acceptance, public PR inclusion or device readiness follows from this source.

Independent source review is recorded in
`out/retained-root-native-review/SOURCE-PASS.json` (857c source), followed by
`LIVE-IDLE-DELTA-PASS.json` (4bda source). The latter verifies the exact inverse
of the idle-only change. These are source dispositions, not build/runtime proofs.
