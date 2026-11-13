# Fixed-stage supervisor source review

**PASS for the bounded authored caller source only.** Reviewed supervisor C
`7dfa2c6fdd5a83684b6f22af8dd05ce8f15865f86204a8c22ab9b395864d3602`
against source freeze `875ac516a2a73f74df2c2e03640771f97c0629331199d6a5691c3e5e3cb90c8d`.
The [review inventory](../inventory/guest-private-view-supervisor-review.json)
pins exact inputs and individual source findings. No compiler, helper, fixture,
syscall/namespace process, OEM code or phone operation was run in this review.
This disposition permits a separate root build decision; it is not that decision.

The entire 5911-byte supervisor was read. Its three gvi call boundaries were
checked against the unchanged input-owner source/header `5e645e05…/68a7b302…`
and terminal gvo ownership/reaping contract `1026094b…/463b79db…`. This does not
repeat or expand the complete mount, input authenticity, IPC or parser review.
The source owner, input provider and parser all match the supplied freeze.

The no-argument path reports fixed NO_OPERATION and returns without installing
signal policy, opening inputs or creating a view. Its bounded frame helper can
set stdout O_NONBLOCK and attempt a write; this is not a claim of zero syscalls
or unchanged output-descriptor status. The only operational argument sequence
is exactly `--prepare-fs-view`. Any extra argument or different option refuses.
There are no arbitrary path/FD/PID/hash options, environment selectors, command
grammar, native-service invocation, exec, setns or chroot operations in this
caller. The internally fixed-stage provider remains a separate source contract.

Before input acquisition, operational main sets SIGCHLD to SIG_DFL with zero
flags, removes inherited auto-reaping behavior, ignores SIGPIPE, and installs
flag-only INT/TERM/HUP handlers before clearing the signal mask. It creates no
threads and calls no wait/reaper itself. gvi/gvo additionally check their
dedicated one-thread profile, with gvo requiring the SIGCHLD disposition. Thus
this source introduces no competing waiter; it does not attest absence of a
foreign tracer or hostile process changes. Its handler never accesses the
opaque owner, closes resources or reenters begin/close.

`gvi_open_existing` is read-only adoption of already-existing stage objects;
`gvi_begin_view` performs actual child fork/unshare/mount preparation through
gvo. The distinction is explicit in source and documentation. Once open stores
a nonnull handle, all subsequent open/begin failures, stop/deadline/clock/input
events, and output failures converge on `close_owner`. A null handle can return
without a close obligation. A nonnull handle remains in main's local cell and
is never dropped or replaced. There is one open and at most one begin call.

At close, only actual `gvi_close == GVI_OK` authorizes exit and CLOSED_REAPED
output. The input owner first obtains actual gvo known-close/reap before it
closes provider descriptors. Positive HOLD and negative results both retain
the sole supervisor indefinitely with a polling delay. Permanent uncertain
close does not become success, timeout exit or numeric-FD retry: consumed
descriptor cells remain governed by the existing gvi/gvo contracts. This can
retain a process forever; that is intentional uncertainty retention, not a
bounded cleanup guarantee. Supervisor death, SIGKILL and external controller
recovery are not solved here.

The CLOCK_BOOTTIME deadline is established before input adoption, with overflow
and invalid-clock checks. Before begin and after its synchronous return, stop
flags, any stdin event, clock error or expired budget enter close. The held-view
loop checks remaining budget and polls stdin in at most 100ms slices. Any
input/HUP/EOF/invalid descriptor or poll error requests close. The unchanged
three-function API has no safe asynchronous cancel call: signals only record
intent during open/begin, and stdin/deadline are acted on after return. Its
30-second budget is a decision policy, not a hard process, syscall, reaping or
cleanup deadline. Suspend time counting does not promise execution in suspend.

Frames are fixed authored NDJSON, at most 384 bytes per call, with no queue or
write retry. No raw native error, path, user, token or image identity is exposed.
The held frame carries only namespace inode and two peer-group integers, which
are observations, not authenticated launch capabilities. Operational partial
or failed writes lead to close and prevent exit0; incomplete transport does
not prove delivery. The no-argument diagnostic intentionally ignores its write
result and returns0, so the document's output-failure condition is interpreted
as the operational path, not diagnostic delivery assurance.

No material scoped defect was found. Image/source admission, native/process
launch, namespace propagation receivers, property and security authority, CE,
quota, runtime cancellation and actual phone acceptance remain separate gates.
The prepared caller neither supplies those owners nor emits READY_FOR_LAUNCH.
