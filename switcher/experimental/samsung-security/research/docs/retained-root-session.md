# Closed app-owned root session

This is source-only preparation of an actual process/control producer. It does
not join a retained Samsung owner, start a guest, or grant host/source permission.
No helper, root command, Android/OEM implementation, compiler or model ran while
authoring these files. SDK, native and first-party model evidence remain separate.

`RetainedRootSession.begin(expectedSha256, expectedBytes)` retains its own Attempt
before external placement checks or thread/process creation. It accepts only a
lowercase build hash and a bounded helper size, not a Process, path, environment,
argv, descriptor or ready flag. The hash/size select build bytes, not authority.
Its package-private Spawn calls the Root-owned fixed RetainedRootCommand builder
and then exactly `new ProcessBuilder("su", "-c", command).start()`.
The command checks the fixed root-owned artifact and retains fd3 through hash and
exec; the native entry independently compares fd3 with its actual executable.
Those source checks still require actual artifact/runtime admission.

The public blocking methods begin, Attempt.ping and Attempt.close refuse the app
main thread. currentAttempt, state and requestClose only expose/retire the actual
retained owner; they do not issue a capability. A preparation fence exists before
Looper observation so reentrant begin cannot start another producer. A preflight
failure before any Thread.start attempt can restore only the prior known-terminal
owner. Once Thread.start is attempted, a throw cannot establish that no child
exists: the current Attempt remains retained and unresolved. There is no public
reset, forced-success, supplied-process factory or numeric signal method.

## Transport and source custody

One retained worker owns creation, handshake, sequential PING/CLOSE and cleanup.
Two separately retained pumps capture the one 64-byte stdout OFFER and discard
stderr/unknown output with bounded counters. Thread references precede start;
each stream/process/socket is retained before the next fallible acquisition.
Unexpected output poisons the attempt; raw output is never logged or returned.

INIT derives actual Process.myPid/myUid. Frames follow the shared 64-byte ORSC
big-endian v1 protocol. Java connects to the bounded abstract name, compares
actual LocalSocket peer UID0/PID with OFFER, and adopts the actual ancillary
array before validating even its count. The one received descriptor is duplicated
using public PFD.dup; all actual raw extras remain owned for independent cleanup.
The captured platform dup implementation can allocate after duplicating the
kernel descriptor. Duplication is marked uncertain before that call and cleared
only after the returned PFD is retained. A throw keeps the attempt unresolved;
cleanup of visible descriptors cannot prove an unreturned duplicate was closed.
A real proc readlink must identify a pidfd and bounded fdinfo must contain exactly
one Pid field matching that socket peer. Only completion of this full check sets
the private pidfdValidated flag; readability of a rejected regular-file FD cannot
become exit proof. FileDescriptor integer reflection and caller-supplied FD
numbers are absent. A consumed proc-read close is never retried after uncertainty.
Ancillary retrieval also follows a failed socket read; any unreturned ancillary
ownership remains explicit uncertainty. The input/output socket streams are
borrowed views: only the socket has close authority, consumed before its one
fallible close. Cleanup never retries that FD through a stream alias.
Pidfd cleanup retains the PFD's exact FileDescriptor object, consumes its close
disposition, and calls public Os.close once. Only a normal return with that same
object reporting invalid permits subsequent PFD wrapper cleanup. A throw or
still-valid descriptor retains uncertainty; the wrapper is not used as a retry.
The public Os.close result is the syscall receipt boundary, not PC kernel proof.

The native idle policy does not require a heartbeat. Explicit PING/CLOSE are
serialized, have increasing nonwrapping sequences and exact zero padding; partial
socket reads update their timeout to the remaining frame observation deadline.
The native first-readable-frame deadline and Java observer waits are each bounded.
The actual captured platform's two-argument connect overload always throws;
this code uses its implemented one-argument connect. That call has no supported
timeout. Public Java connect, process/stream creation or writes are not claimed forcibly interruptible:
an observation timeout retires admission and retains the worker/Attempt rather
than treating blocked work as stopped. No lock spans framework calls, spawn,
stream/socket operations, original process waits or thread joins.

## Closure is an observation, not an ACK

requestClose is a terminal local cutoff. The worker requests actual protocol
CLOSE when the captured channel permits it, then closes the local channel.
A CLOSED frame, EOF, timer, interrupt, wrapper exit or cancelled wait alone is
insufficient. State.CLOSED requires all of:

* actual validated pidfd POLLIN exit observation, with no poll error;
* own Java Process timed wait reporting completion;
* both actual pump threads joined and finished;
* worker itself observed no longer alive;
* successful owned stream/socket/FD cleanup, including all raw-rights attempts.

The pidfd and unsettled stream owners stay retained on unresolved exit/reap/join.
No second helper is admitted while the current owner is unresolved. A failed
close is retained as uncertainty, not repeated on a potentially consumed/reused
descriptor. Cleanup failures preserve the primary actual Throwable and bounded
suppression; no original error is converted to an authority result. The source
propagates the exact InterruptedException from an owned wait; it does not restore
the interrupt flag by invoking an overridable Thread method under its monitor.
It does not claim native/kernel acceptance, a global process drain or a completed
recovery mechanism for an unresolved creation.

Public SDK37 declaration evidence in out/retained-root-session-api verifies the
used API surface without hidden projections. It does not prove Android ancillary
consume/reset/close behavior or kernel semantics. The native source and fixed
launcher are separately owned/reviewed. First-party tests may replace only public
Android APIs and the authored Spawn boundary; their Process/FD facts remain
explicit models. Build workflows and actual execution are Root-owned.

The host Binder join, actual guest handoff, private-view lifetime, compositor,
input/display/property/security-backend ownership and all 18 device outcomes
remain unassembled. Existing PIN/capture components and app/session scripts are
unchanged. This is not a selected runtime or an enabled OneOS feature.
