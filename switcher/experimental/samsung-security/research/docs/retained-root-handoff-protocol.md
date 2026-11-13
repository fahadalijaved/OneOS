# Direct Samsung-host control from native process birth

This separate, default-off v2 source design keeps the full shared-security goal.
It replaces an unnecessary two-socket handoff with direct host control: the app
starts the fixed helper and relays its offer, but never owns its control socket.
It grants no guest launch, credential, biometric, filesystem or authority access.
The v1 sources, packaged candidate and public research PR remain unchanged.

## Source and wire contract

The genuine captured host binds the separate full-app service
`com.fahadali.oneos.core.root.RetainedRootHostServiceV2`. Its synchronous BEGIN
transaction captures the actual Binder caller PID and UID before starting work;
UID must be 1000. No request field supplies that identity. A private app launch
owner starts the fixed verified `oneos_retained_root_handoff` image with the sole
flag `--host-control-v2`. It writes that captured tuple in INIT, retains the real
process and streams, and relays the exact native offer through the same retained
host callback. It never opens a native control connection or sends PING/CLOSE.

Binder tokens are `com.fahadali.oneos.IRetainedRootBroker.v2` and
`com.fahadali.oneos.IRetainedRootHost.v2`; version is 2. BEGIN=1. Callback OFFER=1
contains native PID as int and the printable abstract address as String;
FAILED=2 contains UNAVAILABLE=1. Replies contain QUEUED=1, delivery only.
Callbacks are one-shot and retained before scheduling; failure after delivery
does not authorize another spawn. Preserve exact synchronous framing and no-tail
checks. The host verifies its actual app package/profile/callback occurrence.

Native frames are 64 bytes: magic `ORSH`, big-endian version u16=2, kind u16,
sequence u32, status u32, payload[48]. Kinds INIT=1, OFFER=2, IDENTITY=3, PING=4,
PONG=5, CLOSE=6, CLOSED=7, COMMIT=8, COMMITTED=9. REQUEST=0,
ADMISSION_CLOSED=1, LOCAL_CLOSED=2, REFUSED=3. Unused payload is zero.

INIT sequence0/REQUEST contains captured host PID u32 and UID u32=1000.
OFFER sequence0/ADMISSION_CLOSED contains actual native PID u32 and a 42-byte
printable random abstract name (`oneos.orh.` plus 32 lowercase hex digits) with
two trailing zero bytes. Only the exact
host kernel SO_PEERCRED PID/UID can connect. IDENTITY sequence0/ADMISSION_CLOSED
contains actual native PID and exactly one actual self-pidfd via SCM_RIGHTS.
The host retains all received rights before any refusal, validates root peer,
PID, pidfd kind/target/liveness and current captured source, then sends the sole
COMMIT sequence1/REQUEST with zero payload. Native adopts host control
irreversibly before any COMMITTED sequence1/ADMISSION_CLOSED acknowledgement.
Only then may the host use PING/PONG or CLOSE/CLOSED, starting at sequence2.
All request/reply payloads after IDENTITY are zero. No incoming rights are legal.

One absolute budget governs initial association/commit, not a fresh timeout per
byte. A committed closed-admission connection may idle without heartbeats;
an incomplete frame has a bounded whole-frame budget. Lost commit replies mean
uncertain custody, never ready, automatic retry, another spawn or app fallback.
Only the direct host socket can request native close. CLOSED acknowledges local
cutoff; actual pidfd exit and owned cleanup remain separate observations.

## Lifetime and integration bounds

Native must establish its own session/process group, clear inherited parent-death
signal state and explicitly dispose original/duplicated app stdio at commit.
Failure of those operations refuses the path; no shell detachment, blind fork,
numeric PID signaling or fake drain substitutes. HUP from the old launch context
must not revoke committed host control. TERM/INT and actual host socket loss
remain cutoff. Exact ordering and uncertain close disposition need code review.

App delivery retirement, pump EOF and su-wrapper exit are local observations.
After an offer can have reached the host, app cleanup cannot signal the native
process, send a control close, spawn a replacement or claim native termination.
The actual host stores its client before external work and retains uncertain
connect/commit/close progress. Its source/package retirement policy must be
implemented explicitly rather than inferred from app Binder availability.

The actual candidate OneOS root launch source moves itself to
`/sys/fs/cgroup/cgroup.procs` before launch (root asset lines 1068-1070;
switcher asset line 285), explicitly because ActivityManager kills the app's
cgroup when the framework stops. Consequently session separation alone leaves
a known lifetime gap. V2 must either implement and verify fixed self-only
placement or remain unavailable for that switch. A write result alone is weak:
the membership path is relative to the process's cgroup namespace. The native
checks establish equality with the visible PID1 cgroup namespace and that view's
root cgroup2 mount and membership. Those checks can also hold in a nested PID/proc
view; they do not authenticate the global initial namespace. The genuine host
initial PID/proc/cgroup launch view remains an external profile/runtime
prerequisite before guest admission. The kernel
documents PID migration through `cgroup.procs` and namespace-relative membership
in [its cgroup v2 reference](https://cdn.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html).

Own session, cleared parent-death state and even correct self cgroup placement
do not prove independence from root-manager cleanup, physical display ownership
or OneOS's complete switch kill policy. Those remain source/runtime obligations
before guest admission. This design is closed control preparation; all 18 device
acceptance cases and the full reciprocal PIN/fingerprint/app-key/CE outcome
remain open.
