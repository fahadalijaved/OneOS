# Closed Samsung PIN endpoint in the preparation host

The separate unsigned host build contains the retained PIN endpoint in the
same loader cohort as the Samsung check owner. The real boot capture site
uses the already captured binding from the initialized Samsung services
after the original phase-1000 call returns. The original source and
physical system-user checks still bracket preparation. The new capture
owns one reservation before constructing the operation owner, derives the
check owner from that same object, and pairs both with the closed endpoint.

Off-main poison retires the capture before the main-only root-link cleanup.
Each object is adopted before rechecking retirement. If retirement arrived
during construction, the actual returned object stays retained and receives
its terminal local cutoff. The first compiled draft adopted the operation
owner after fallible boot checks. The corrected build moves the reservation
and operation construction into the capture. The corrected fixture passed
16 checks, including retirement during each of the three constructors.

The source transform inverted exactly to the pinned host baseline. The
SDK 37 and D8 build contains the prior 47 definitions plus the closed
capture and PIN endpoint. The APK embeds those 49 definitions and preserves
the other five host package entries. It is unsigned and provides no
published Binder, endpoint opening or credential action. [Build evidence](../inventory/retained-pin-host-cohort.json)

The separate ColorOS caller frame preserves the original `checkCredential`
invocation while sampling the actual incoming Binder identity before the
identity clear. It passed 33 inert JVM checks. The source frame is unbound
to the held case-10 path and carries no caller or subject authority. The
host still needs a selected guest Binder delivery, an actual physical-user
worker lease and one-shot request retirement before a PIN test can be
prepared. [Guest frame verification](../out/guest-pin-caller-frame/REPORT.md)

The donor's default Binder startup opens `/dev/binder`. The isolated
preparation view provides an empty private device tree with a socket
directory. A later startup must establish the actual driver context and
authenticate the guest SystemServer recipient before delivering the held
endpoint. [Binder source check](../out/guest-pin-binder-delivery/REPORT.md)

The paired stock startup audit found that both service managers can set
`servicemanager.ready` after a failed context claim. The selected private
guest design needs a positive claim of its own Binder context, an isolated
property writer and authenticated endpoints in both contexts. [Startup audit](../out/guest-binder-context-startup/REPORT.md)

An offline ARM64 build now contains a detached Binderfs creator. It checks
the child's namespace and verifies that the private device identity matches
the kernel response. The launch owner still needs to attach the device and
bind the real manager's positive context claim. [Creator evidence](../out/guest-binder-context-owner/REPORT.md)

Samsung commits the current user before dispatching its switch observer.
The pending-start list can also become empty while a captured start remains
queued on the handler. The credential check needs a lease owned by the real
foreground and eligibility writers through Samsung's original work and
cleanup. [Physical-user source check](../out/retained-pin-user-lease/LEASE.md)

Foreground starts, queued switches, stops and user eligibility mutations
have distinct original writer paths. User removal reaches LockSettings
and storage key destruction before the removal notification. A shared
lease needs reviewed deferral at the original writer entries before any
of those effects. [Writer entry audit](../out/retained-pin-writer-fence/CUT.md)

The stock switch and shutdown queues resume on their own switch or shutdown
events. One of those paths can change task and display state before queueing.
PIN-active deferral still requires its own reviewed pre-effect owner and
original continuation custody. [Deferral audit](../out/retained-pin-writer-deferral/DEFERRAL.md)
