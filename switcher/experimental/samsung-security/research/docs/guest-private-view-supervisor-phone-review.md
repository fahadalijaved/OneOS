# Filesystem-view diagnostic: held on real prepared inputs

**HELD_ON_REAL_PREPARED_INPUTS. No installation or run is proposed now.** Root's
read-only preflight rules out the currently observed inputs. No approval question,
guardian, controller infrastructure, source/profile change or phone action is
included. The separate pending25KB warm diagnostic proposal remains unchanged;
its approval would not authorize this633,680-byte executable or namespace test.

Root's preflight is
`out/private-view-preflight/20261106T073934127550Z-6f44db874f894d7db3e9633f5252edf0/observation.json`,
SHA256 `0ec09812240a802357b5583053d8565f68b0b3f8f266c598d9419fd1fdca98d6`.
Its ten saved stdout/stderr streams were hash-checked offline; no new phone
query was made by this worker. It observes UID/GID0 and `u:r:ksu:s0`.

| Observed input in init's view | Current frozen source requirement | Decision |
|---|---|---|
|471 mount rows, no mount at `/data/local/tmp/oneos/rootfs`; that pathname is an ordinary root-owned directory|An actual private read-only ext4 loop image mount, root `/`, with matching backing-image identity|Not prepared|
|`rootfs/data` and `rootfs/data_mirror` absent|Both actual image target directories already present|Not prepared|
|Stage `data` and `data/user/0`: UID/GID1000, mode0771|`gvi`'s current root-owned guarded data object, without group/other write|Rejected source profile|
|`system.raw`:14,669,168,640B, root:root0644; cached ID stat tuple matches|Held image/ID plus real loop ioctl/topology/read-only checks|Cached freshness only; no current image-root mount or fresh content-authentication proof|

These are init-view observations, not proof of the future diagnostic process's
namespace or all other namespaces. No alternate view is admitted or selected.
`gvi_open_existing` has no staging/mount fallback, and the observed data fails its
`root_object` guard. This is source refusal analysis, not an executed refusal.
Running it merely to reproduce the already-known missing-input outcome is not
the next action. Do not create empty stand-ins, bypass an overlay refusal, chown
or chmod OneOS data, mount an image globally, relabel, restore root or run a
OneOS preparation script to make the profile pass.

The frozen candidate is
`out/gvs-build/r-d43d18a4/guest_private_view_supervisor`,633,680B, SHA256
`b57fcc0d024e640798346529539fc4d3627ea0fca8c35e93d53000d256c6be15`.
Its API31/NDK23.1 static-PIE build has4KiB load alignment and independent static
review2d548e63. It has never been executed. The separate observed4096 phone page
size does not establish Android17/API37, SELinux, syscall or runtime compatibility.

For a future separately reviewed proposal, reserve only a **new, absent** sibling
directory `/data/local/tmp/oneos-samsung-security-fsview-b57fcc0d-20261106-01`
(requested root:root0700) and its exact `guest_private_view_supervisor` binary
(requested root:root0500). Those modes, label, absence and execution access are
not observed or approved. A future transfer must verify size/hash readback before
any execution; name collision refuses instead of replacing files. No installer,
OneOS-owned path write or persistent service is needed. Future bounded protocol
records belong in the repository's ignored output, not OneOS data. No directory,
binary, FIFO, script, log, guardian or control process is created by this proposal.

The sole prospective operational command is exactly:

```sh
# NOT AUTHORIZED OR RUNNABLE WITH THE OBSERVED INPUTS
exec /data/local/tmp/oneos-samsung-security-fsview-b57fcc0d-20261106-01/guest_private_view_supervisor --prepare-fs-view
```

No raw path/FD/PID, arbitrary command, user or policy argument is accepted. This
must not be put behind `timeout`, a parent kill-on-timeout, automatic retry or
disconnect-and-forget wrapper. An eventual reviewed operator must retain the
actual supervisor and its transport through cleanup. Any stdin input/EOF/HUP or
handled stop signal requests shutdown; it is not an acknowledgment. Open/begin
are synchronous, so the request is acted on after they return. The30-second
BOOTTIME decision budget is not a hard process/reap bound. The original gvo
cleanup owns its exact child, normally TERM then2s/KILL; unresolved cleanup or a negative
close result retains the supervisor indefinitely in HOLD. Do not signal by a
rediscovered PID, repeat begin, delete files or kill the owner to meet a PC timer.
Only the actual authored CLOSED_REAPED frame plus owned terminal completion can
support cleanup acknowledgment; transport loss, expiry or silence cannot. The
durable operator/control lifetime remains deferred while inputs are blocked.

If a future admitted run reaches begin, gvo forks one first-party child. That
child unshares a mount namespace and makes it recursively PRIVATE before binds. It retains source
witnesses before shadowing `/data`, creates new data peers and the user0 legacy
alias, then a private tmpfs mirror with only `data_ce`/`data_de` scaffolding and
new peers. Five namespace/root/data/mirror descriptors return over private
SCM_RIGHTS; the parent owns them until actual close/reap. No parent namespace
change, original OEM/native service, OneOS script, authentication, credential,
policy, root-stack, reboot or restart operation is part of the candidate. The
authored backing-directory writes are confined to the new child tmpfs, not
OneOS files. There is no claim that read access has zero filesystem accounting
effects or that disposing namespaces reverses persistent state.

The next engineering action is a source-owned private fresh-image preparation
and its real lifetime, plus a source-proven UID/GID1000/mode0771 data profile
with genuine object/writer ownership. No chown or fake ownership substitute is
acceptable. That may require new source, a new binary/hash and a superseding
proposal; b57 and all current sources remain frozen. Only after those inputs,
the operator lifetime and new reviews close may root consider a fresh explicit
user approval for transfer and effectful execution. No automatic question is
requested while the existing diagnostic approval is pending. Even a future
filesystem result would not prove bootability, shared PIN/fingerprint, CE/key
security, native authority or platform integration.
