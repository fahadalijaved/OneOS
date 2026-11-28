# Private filesystem view in the direct-host controller

`compat/native/root-view-integration.patch` is an authored delta against the
native C/header in commit `7b7c33e354a02343d511993f5b2cf4b76f8253c2`
(`276f2dc3â€¦` / `72f29a3eâ€¦`). The current core files and full-app build inputs
remain unchanged. Retained composed C/header bytes and exact patch/context/count
verification are under `out/retained-root-view-native/`; no compiler or native
operation ran while authoring this source.

The final patch and composed bytes pass Detail's independent native source
review and Trust's cross-owner custody review. Their immutable source gates are
pinned one-way in the matching inventory. This clears source preparation for
Root's separate PC build; it does not claim an actual composed build result.

The uncompiled patch also corrects membership readback for the captured hybrid
cgroup profile. The original whole-file `0::/` comparison would refuse a valid
unified root row accompanied by v1 rows. Readback is now bounded to fewer than
4096 bytes and at most 64 newline-terminated rows. It requires exactly one v2
`0::/` row and validates canonical positive, unique v1 hierarchy IDs, nonempty
controller lists and absolute printable-ASCII paths. Duplicate v2/IDs, non-root
v2 membership, NUL, malformed rows, missing final newline, overflow and a full
buffer refuse. This is a supported bounded text profile, not every possible
kernel naming profile or a global v1 semantic validator; controller-token
uniqueness is checked within each list. It neither moves a v1 controller nor establishes v1
isolation, a global initial namespace or app/root-manager kill immunity. The
same visible-PID1 namespace, opened cgroup2 mount and self-only write checks
remain unchanged. Captured phone data stays in ignored firmware; only these
derived source facts are recorded here. The first 71-byte capture uses CRLF and
remains historical row-layout evidence. A separate 65-byte binary exec-out
capture preserves LF bytes and the same six-row layout without normalization;
it is the selected byte evidence for the bounded source review. Root observed
client exit0, without a separate remote-exit channel. Neither acquisition is a
native parser test or a view/cgroup-write execution result.

The patch links the actual existing GVI/GVO/parser sources into the same dedicated
controller. It adds VIEW_PREPARE=10, VIEW_STATE=11 and VIEW_QUERY=12 after the
unchanged direct-host COMMIT, preserving ORSH/version2, 64-byte framing and the
single sequence. Both requests have zero payload. VIEW_STATE carries the selected
state, observed flag and three big-endian u64 observations, with zero trailing
bytes. These are retained local progress and last successful observations, not
a fresh query of child/mount liveness or a readiness decision.

Preparation is consumed before the first actual `gvi_open_existing(&owner)`.
The returned pointer is the controller's own retained field even when opening
fails. Only GVI_OK permits the same owner to enter `gvi_begin_view`; its internal
GVO pointer also survives an after-fork failure. No caller supplies a plan,
descriptor, PID, namespace, image-hash claim or readiness predicate. A second
prepare refuses and cuts off instead of reopening or repairing the stage.
The fixed GVI source uses the existing stage and its cached identity checks;
those are not fresh image authentication or exclusive-writer proof.

The controller installs SIGCHLD default with flags0 and remains the sole native
thread/waiter. GVO performs the actual fork/unshare/mount work and owns its child
signals and reap. Its child closes unlisted inherited descriptors, including
the parent's host control socket. There is no extra waiter, shell, guest exec,
parent namespace entry or duplicate supervisor. The signal handler only records
cutoff; it cannot reenter synchronous GVI work. Before another effect or a
successful partial observation, the main thread checks the request budget and
actual control socket. The canonical request/reply worker does not pipeline:
queued input, EOF or a socket error at that checkpoint cuts this request off.
This does not undo an effect that happened inside the synchronous call.

All nonnull-provider exit paths pass through the same actual `gvi_close` before
legacy controller descriptor cleanup or process return. CLOSE, malformed input,
EOF, INT/TERM, failed preparation and failed/lost replies cannot discard that
owner. HOLD and other uncertain returns retain the process and provider and
poll the same close API without a cleanup timeout exit or consumed-FD retry.
After a reply-bearing cutoff, only QUERY can inspect retained drain progress;
an incomplete query can delay the next close poll by the existing whole-frame
budget. No hard child/kernel completion deadline is claimed.

A view-bearing CLOSE replies VIEW_STATE, including CLOSING_HOLD when applicable;
it never uses the old CLOSED response. Actual local terminal0 permits
REFUSED_LOCAL_CLOSED and local shutdown. Terminal3 permanently becomes
LOCAL_KERNEL_UNCONFIRMED and exit3, never full return0 or kernel release.
The original no-provider CLOSED path and PING remain available with their old
local-only meaning. Cached observations remain descriptive tombstone data.
After a delivered HOLD reply, reaching actual terminal0/3 retains the terminal
metadata and live peer for one next valid QUERY, within a fresh 30-second
observation budget. That reply carries the real state5/6 at the next sequence,
then the process exits with its actual local terminal. EOF, signals, invalid
queries or lost replies still leave the host UNKNOWN; it cannot infer a local
terminal or kernel release from exit alone. No unsolicited frame is invented.
The observation budget begins only after local settlement; it never limits HOLD.

The patch requires a new composed native build and matching app packaging pins;
the existing closed-only binary is not an integration artifact. Source review,
PC compilation and authored models remain distinct from actual kernel mounts,
root-manager/cgroup lifetime, initial launch namespace, guest/native service,
image/writer, security or device acceptance. No ColorOS process is launched and
the full reciprocal PIN/fingerprint/app-key/CE outcome remains pending.
