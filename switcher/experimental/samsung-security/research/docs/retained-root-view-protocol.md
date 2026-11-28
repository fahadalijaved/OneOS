# Same-controller private filesystem view

This extends the existing direct-host closed control source. It connects the
actual GVI/GVO filesystem owner to that controller, rather than introducing a
caller-supplied process, descriptor, namespace or readiness decision. It does
not launch ColorOS or open any credential, biometric or guest authority.

The source preimage is Git commit `7b7c33e354a02343d511993f5b2cf4b76f8253c2`.
Its native C is `276f2dc398a9ad4cef5a014cea7f21677ad8f81ecbfc66c82d26911e0b4cc748`,
header `72f29a3e62139cead325a76d27ff6c6d216c1daa986009d6b824b9852f166042`.
Current full-app compilation inputs remain held; new changes are prepared as
authored patches until root integrates them after that compilation.

## Wire extension

Keep ORSH/version2/64-byte framing, exact original handshake/COMMIT and the
single increasing sequence. Add VIEW_PREPARE=10, VIEW_STATE=11 and VIEW_QUERY=12.
Both requests require zero payload and REQUEST status, only after COMMIT. Their
response is VIEW_STATE at the same sequence, ADMISSION_CLOSED status. A prepare
is one-shot, consumed before the first actual GVI call. A duplicate prepare
refuses/cuts off; it never opens another provider or retries a failed attempt.

VIEW_STATE payload contains state u32 at16, observed u32 at20 (exactly0 or1),
namespace inode u64 at24, data group u64 at32 and mirror group u64 at40, all
big-endian. Bytes48-63 are zero. If observed=0, all three observations are zero.
observed=1 is set only from an actual successful gvi_begin_view result and the
three original observations remain descriptive tombstone data after retirement.
It is not evidence of current mount/child liveness: GVI has no live query API.

States: NOT_ATTEMPTED=0, PARTIAL_FILESYSTEM_OBSERVED=1,
NEED_PREPARED_STAGE=2, REFUSED=3, CLOSING_HOLD=4,
LOCAL_KERNEL_UNCONFIRMED=5, REFUSED_LOCAL_CLOSED=6. No state means READY,
guest admission, image authenticity, exclusive writer custody or security.
QUERY reports only retained local progress and the last actual observations.

## Native ownership and cutoff

The dedicated single-thread controller installs SIGCHLD default with flags0
and no competing waiter before calling GVI. It passes its retained pointer
directly to gvi_open_existing and stores nonnull results even on error. It uses
that same owner for the one gvi_begin_view and all subsequent gvi_close calls.
No raw GVO pointer, FD/PID selector, namespace entry, legacy OneOS launcher or
caller-supplied plan is introduced.

Synchronous GVI work can fork/mount before an EOF, signal or deadline is observed.
Observation timeout is not cancellation. Recheck actual control cutoff after
external work and before sending a partial-view observation. A failure/lost reply
does not prove that no child or mount exists; preserve the consumed attempt.

CLOSE, host EOF, invalid frames and INT/TERM cut off ingress, then drain the
actual nonnull GVI owner on its own thread. While gvi_close reports HOLD or an
uncertain result the native process and all actual owners stay alive and poll
that same close API; never exit on a cleanup deadline or retry consumed FDs.
There is no new preparation or security operation during drain. With a live
host channel, QUERY may report CLOSING_HOLD while the actual close is pending.

Without a GVI owner, preserve the existing CLOSED/local-cutoff response. A known
GVI terminal0 permits REFUSED_LOCAL_CLOSED and local controller shutdown. Actual
terminal3 permits LOCAL_KERNEL_UNCONFIRMED and process exit3 only: no CLOSED,
full kernel release or successful return. A live requesting channel receives
VIEW_STATE for a view-bearing CLOSE; later exit/pidfd and local cleanup remain
separate evidence. A lost channel cannot force exit while cleanup remains HOLD.

## Host request and acceptance

The existing genuine Binding gets a package-private, main-only noarg
requestPrivateView. It rechecks its real captured source, package and committed
client before issuing one retained request to the same worker/socket sequence.
There is no automatic post-COMMIT preparation in this source extension. A future
selected runtime must connect the actual user launch action and complete profile;
the method is not a new public source/capability factory or a readiness setter.

The client distinguishes source request, possibly delivered PREPARE, actual
VIEW_STATE and cutoff. Lost/invalid replies retain uncertainty and prohibit a
second prepare. View-bearing CLOSE accepts the explicit local terminal/HOLD
states, never converts them into global cleanup or return success. PING and the
original no-view close retain their source semantics. The actual image/writer,
initial launch namespace, native services, guest exec, property/display/data and
security owners remain mandatory before guest admission. All device acceptance
cases and the full reciprocal PIN/fingerprint/app-key/CE goal remain pending.
