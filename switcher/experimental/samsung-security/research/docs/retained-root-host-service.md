# App service for the closed retained root link

Status: independently reviewed authored source only. No compiler,
model, Binder, Android, native helper or device workflow ran for this component.

`RetainedRootHostService` is the app-side Service, private Broker and private
Control implementation for `ClosedRootLinkProtocol`. The separate manifest merge
fragment declares its exact class with `exported=false`. No existing app manifest,
root launcher, native source, shared protocol or host source is changed here.
There is no credential, guest-start, GVI, host-backend or authentication operation.

## Entry and ownership

`onBind` only returns the actual private Broker. BEGIN requires actual Binder
caller UID1000, synchronous flags0 and a reply Parcel, the exact broker token,
version1, callback Binder, native SHA256 String and size long, and no trailing
data. SHA is exactly64 lowercase hex and size is1..2097152. These restrictions
are transport/admission policy, not proof of genuine host security authority.
Unknown transaction codes preserve the original Binder behavior.

One static startup tombstone is retained before `linkToDeath`, Thread.start or
`RetainedRootSession.begin`. Its callback/death recipient and worker are stored
before fallible registration/start. A same-process service recreation cannot
retry an uncertain birth. A fresh app process is not proof that an earlier root
process was reconciled; this component still cannot open guest/auth admission.

The worker admits one factory call and invokes the existing real
`RetainedRootSession.begin` exactly once. It adopts the actual returned Attempt
before inspecting state or allocating Control. No Process, FD, Attempt or ready
bit is accepted from a caller. If begin throws, its own factory retains its
failed owner. This service never wraps or closes a `currentAttempt()` observation
that might belong to another caller. Retirement racing an already admitted
factory call cannot assert that no process was created; a late return is retained
and requested closed.

## Callback and control

Only the actual returned Attempt can produce CAPTURED with its private Control.
The worker checks actual ADMISSION_CLOSED before attempting that callback. A
callback can race retirement or execute before BEGIN replies; the host must
retain the received Control before posting and recheck its own currentness.
BEGIN returns QUEUED only, never readiness or a completed native handoff.

There is at most one callback attempt, CAPTURED or FAILED/UNAVAILABLE. The sender
uses synchronous canonical Parcel exception framing and requires the exact
QUEUED reply with no trailing data. That reply acknowledges requested delivery,
not a host link or native idle state. Both client Parcels have independent once
recycle contours. Throwable text, credentials and arbitrary failure payloads are
never sent. Bounded payload does not imply a hard Binder-RPC time limit: an
unreturned foreign callback keeps its actual worker/stack retained.

A callback transact/reply can fail after the host already adopted Control. The
service therefore cuts off local ping admission, requests close on the actual
Attempt and retains the startup/control/callback uncertainty. It does not retry
the callback or pretend nondelivery. Actual callback Binder death and service
destruction also retire this same owner. Death-link and worker-start uncertainty
remain retained; this source claims no automatic unlink/stack drain or reset.

Control accepts only UID1000, flags0/reply, exact token/version and no trailing
data. PING invokes that same Attempt.ping on the actual Binder worker, with local
admission checked before and after the call. REQUEST_CLOSE retires local ping
admission and calls actual Attempt.requestClose; QUERY_STATE observes the same
Attempt. Query/close remain available after retirement. Enum states map explicitly
to protocol constants, never through ordinal. A failed actual operation produces
a bounded canonical IllegalStateException reply, not a successful state result.

All owned locks protect only local field/identity decisions. No lock spans
Binder, thread creation/start, Session calls or Parcel/framework work. The native
Session owns its actual channel, self-pidfd, process and drain observations.
REQUEST_CLOSE, a state reply, unbind, service death or a callback acknowledgement
does not establish native exit, Java process reap or completion of other stacks.
The private startup and actual Attempt remain retained rather than claiming
closure from a timer or a stale scalar.

## Integration still required

The host counterpart must derive its real Context/captures and package metadata,
bind this explicit nonexported service, authenticate the actual app callback UID,
and validate late/reentrant callbacks against source-owned main continuations.
The protected host profile, manifest/package selection, actual compiled closure
and genuine captured-host integration are separate inputs. No service/profile
was installed or activated. This closed link neither transfers native control
away from the app broker nor supplies the future host authority or guest runtime.

The bounded independent source disposition is
`out/closed-root-app-review/SOURCE-PASS.json` for actual service6a11 and
manifest79a. The initial1b60 source/doc beforeimages remain under this component's
ignored history. Source review is not compilation or Android lifecycle acceptance.
