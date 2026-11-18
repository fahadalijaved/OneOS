# Direct-host root control: native source

The separate `retained_root_handoff.c` / `.h` implement the closed-only ORSH v2
contract. Both independent source reviews accept the exact source for a
root-selected PC build. No compilation or native execution is claimed here.
The v1 controller, its packaged image and existing producer remain unchanged.

The default invocation returns without I/O or root effects. The only active
argument is `--host-control-v2`; the intended output name is
`oneos_retained_root_handoff`. The active path requires real/effective UID0,
single-thread ownership and the inherited FD3 to identify the executing image.
It establishes its own session/process group and clears/readbacks inherited
parent-death signal state, refusing unsupported launch profiles without forking.

Before OFFER it attempts one fixed self-only cgroup placement. Retained namespace
FDs must identify the same cgroup namespace as visible PID1. An opened cgroup2
directory at `/sys/fs/cgroup` is tied by its own fdinfo mount ID to a mountinfo
record with root `/` and that exact mountpoint. The opened `cgroup.procs` must
belong to that filesystem. One write of `0\n` moves only the writer; no supplied
PID/path is accepted, and a failed/short write is uncertain and never retried or
rolled back. Exact membership `0::/\n`, namespace/directory identity and all seven
owned descriptor closes are checked before proceeding.

These checks establish the **visible PID1 proc/cgroup view**, which may itself
be nested. They do not authenticate the global initial namespace. The genuine
host's initial PID/proc/cgroup launch profile remains an external prerequisite
before guest admission. Session separation, parent-death clearing and this
placement also do not prove immunity from root-manager cleanup, later cgroup
movement or the complete OneOS switch policy. The active path really changes
its own session/signal/cgroup state; it is not an observational probe.

The app sends INIT containing the actual BEGIN host PID/UID1000 and relays the
fresh random OFFER only. Native accepts a single direct socket whose kernel
peer credentials match that association; neither the tuple nor the address is
authority attestation. It sends its actual self-pidfd once with IDENTITY. After
a positive partial `sendmsg`, remaining bytes use ordinary send and never repeat
the right. Unexpected received rights are adopted before rejection/cleanup.

Association and COMMIT share one absolute 30-second budget. COMMIT sequence1
requires the exact zero-payload frame. Native checks observed app input loss,
signals and deadline, then irreversibly latches host control. This userspace
latch is not an atomic global ordering of concurrent app death and socket data.
The original 0/1/2 and duplicated app streams are consumed/closed before sending
COMMITTED. A lost or failed acknowledgement cannot restore app control and is
not permission to retry or launch another controller. No app control socket
exists. Committed HUP is ignored; TERM/INT or actual host socket loss cuts off.

Only PING/CLOSE sequence2 onward are accepted after commit. A committed idle
socket needs no heartbeat; an incomplete frame has a whole-frame budget.
CLOSED acknowledges local cutoff, not completed descriptor cleanup, native exit,
wrapper reap or resource drain. Close dispositions are consumed before syscall;
uncertain closes are retained until process exit and never retried after possible
FD reuse. User-space deadline checks do not prove a hard kernel syscall bound.

This source contains no guest launch, GVI operation, credential or biometric
operation, Android authority transfer, numeric PID signaling, fork or reap.
The host/app Java integration, native syscall/runtime behavior, real launch
namespace and all device acceptance cases remain separate. Immutable review
handles and exact source pins are in the matching inventory; the source freeze
retains the bytes used by this report rather than a moving artifact receipt.
