# Direct captured-host native control, v2

Status: actual separate authored host sources, independently reviewed at source
level. No compiler, model, Android/OEM/native helper or device workflow ran here.
V1 sources and their packaged candidate remain unchanged. This is closed control,
not a credential, guest, filesystem or security-authority grant.

## Actual issuer and source path

The package-private `PreparedRetainedHostNativeBindingV2.prepare` requires the
actual `RetainedPinHostModule`, retained Registry and Family, and protected V2
profile. Its constructor is private. It reuses the genuine private controller's
`checkRootLinkForControl` pair checks, Registry/Family currentness, derived actual
SystemContext/PM/UserManager, original main thread/Looper and helper cohort checks.
No caller Context, Process, FileDescriptor, native PID/name or ready flag can
construct an admitted binding. Root's separate same-FQCN module variant retains
this exact binding before `start`; the canonical module is not edited here.

`HostRootLinkProfileV2` preserves the reviewed protected-file parser, with only
its class, fixed `/data/system/oneos_retained_root_link_v2` and version2 changed.
The normal source has CRLF; its inverse is compared to the V1 LF projection,
not misreported as raw byte identity. Missing final file disables; other failures
remain failures. It is immutable policy, never source or live authority proof.

The actual source owns user0-unlock registration/sample ordering, bounded worker
hash of the same opened installed APK, current signer/version/UID/source-path
checks and explicit private ServiceV2 binding. This user0 app-transport selection
does not select a credential subject or manufacture user-zero authentication.
BEGIN is claimed once and runs on an owned worker, so main never waits for that
Binder RPC. Callback-before-BEGIN-return is retained until its real QUEUED result.

## Offer and direct native owner

Only the actual expected app UID may send the exact V2 callback token/version,
flags0/reply and one OFFER or bounded UNAVAILABLE. OFFER stores its incoming
record before reading/validating fields or posting. It carries native PID and
bounded abstract name only, never an app Control Binder or supplied descriptor.
Its QUEUED reply is posting acknowledgement, not native readiness.

After actual main source/package checks, that binding creates and retains one
`RetainedHostNativeControlV2` before its worker starts or a socket is acquired.
The internal constructor's scalar offer fields are not authority: `start` checks
that this very client is already owned by the actual captured binding. The client
uses the one-argument LocalSocket connect, since the captured timeout overload
is unimplemented. A blocked call remains retained rather than becoming a fake
timeout completion. It verifies real root peer credentials/PID and receives
IDENTITY plus exactly one real pidfd. Every actual ancillary array is retained
before any validation/allocation that can fail; originals and the duplicate
wrapper remain separately owned. The pidfd's actual kind, target and liveness
are checked through its own bounded proc metadata and kernel poll.

One absolute 30-second association budget covers connect observation, identity,
the main commit gate and COMMIT/COMMITTED. Every blocking read sets the remaining
whole-budget timeout. No trickle-byte reset exists. Socket writes/connect may
still block in the actual platform implementation; their stacks/resources remain
owned, and no hard syscall-preemption guarantee is claimed.

After IDENTITY, only an actual main continuation can recheck the original
module/Registry/Family and live package, then issue this client's private one-shot
COMMIT credit. COMMIT is seq1. A valid COMMITTED reply, another liveness observation
and a final main source/package check can mark `HOST_LINKED_CLOSED`. That state is
point-in-time source/control association, not future physical freshness or auth.
PING/CLOSE then start at seq2 on the same host-owned socket worker. There is no
app Binder control proxy, generic command, second listener or writer transfer.

## Retirement and uncertainty

Actual app transport loss before an adopted offer fails the startup. After a
complete authenticated offer and actual BEGIN QUEUED, app disconnect/death and
BIND_AUTO_CREATE reconnect are recorded without replacing the original broker,
issuing another BEGIN or revoking native control merely for app liveness. Their
main notices still recheck genuine source and package. Actual package replacement,
removal/change or source retirement cuts off commands and requests direct native
close. All package-event branches schedule cleanup, including pre-native loss.

The host owns an actual pidfd exit observer, with one reused poll struct/array and
250ms idle polls. Unexpected positive non-POLLIN events fail rather than spin.
PING checks liveness and local admission before/after the real round trip. Main
never runs capture checks on workers; no owned lock spans foreign Binder, Context,
PM, thread, socket, descriptor or callback operations.

Any possibly delivered COMMIT is retained before writing its first byte. Lost or
malformed COMMITTED means uncertainty: no retry, replacement spawn or app fallback.
Only the host socket requests CLOSE after known commit. Precommit retirement
closes the owned channel rather than inventing an unsupported CLOSE handshake.
Unknown commit disposition also closes that channel, whose loss is the current
closed-only native cutoff; it is not a general drain contract for future effects.

Socket streams borrow the sole socket close authority. Actual owned raw rights,
metadata reads and pidfd wrapper have consumed-once cleanup and uncertain owners;
no numeric signalling, wrapper reset or native-parent reap is invented. The host
is not the native parent. CLOSED ACK is local cutoff only; actual pidfd exit and
own worker/observer completion remain separate observations. Timeouts, blocked
stacks and close errors keep their private owners retained. Strong references do
not independently prove a live native lease across helper/loader loss.

Native session/PDEATHSIG/stdio/cgroup preparation and app offer-only custody are
separately authored/reviewed components. The shared codec and protected-profile
checks are not whole app placement, root-manager survival, a source-installed
module, guest startup or platform-security acceptance. All eighteen shared PIN,
fingerprint, app-key, CE and return acceptance cases remain pending.

Immutable source dispositions are
`out/retained-root-handoff-review/trust/HOST-SOURCE-PASS.json` and
`out/retained-root-handoff-review/java/SOURCE-PASS.json`, both for Binding9561,
Clientf9df and Profile020c. They are source gates, not compilation or execution.
