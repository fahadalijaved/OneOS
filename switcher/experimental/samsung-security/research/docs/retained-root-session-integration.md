# Closed root-session implementation checkpoint

The first root-process/control component now has implemented source, a reviewed
ARM64 build and app-side SDK37 classes, plus 25 passing authored model cases.
It remains a compatibility-tree prototype: it has not been added to OneOS's app
build, installed, activated or exercised as a real root session. The existing
OneOS launch and security guards and upstream draft PR #41 are unchanged.

`RetainedRootSession.begin` creates and retains its own Attempt before spawning.
It cannot wrap a supplied Process or accept a supplied readiness decision. Its
fixed launcher checks a root-owned controller image, holds the same opened image
through metadata/hash verification and exec, and selects only the closed-session
protocol. Build hash/size constrain the image; they grant no host authority.

The native controller implements a real UID0/single-thread source, a fresh
abstract socket, actual peer credentials and self-pidfd transfer through
SCM_RIGHTS. The app-side source adopts that descriptor and validates its kernel
type/target against the peer. Only PING and CLOSE exist. It cannot start a guest,
open the filesystem preparer or invoke Samsung security services. Idle control
waits without requiring a heartbeat; partial frames have an absolute budget.

The lifecycle distinguishes local cutoff, acknowledgement, process exit and
cleanup. A closed-state observation requires validated pidfd exit, the actual
Java child being reaped, completed worker/readers and successful owned cleanup.
Partial creation, duplication and cleanup uncertainty retain the Attempt and
block automatic retry. Socket stream aliases close through one owner. The pidfd
closes through the exact owned descriptor before its wrapper is retired.

Actual Samsung source inspection found that the public two-argument socket
connect method always throws. The implementation uses the supported one-argument
call; that call has no proven bounded cancellation. Observation timeout retains
its worker and resources. The model deliberately throws on the unsupported
overload, rather than inventing successful platform behavior.

The actual [build](retained-root-session-build.md) produced a 596,312-byte
AArch64 static PIE, SHA256
`1cacc47717468c6e91b791126ce011af25dab9bdbde50765ec0a013cea2b116b`,
and ten SDK37 classes. ELF inspection covers 4 KiB alignment only. The compiler,
static reader and Java compiler returned zero with processes reaped. Neither
output was executed during that build. Receipt `83fd1b65...` and independent readback `b7617f9d...` retain
the actual bytes, inputs and logs.

The [model run](retained-root-session-tests.md) passed **25 cases / 241 checks**
against nine unchanged SDK classfiles. Only the authored process-start boundary
and Android public APIs are replaced by explicit first-party models. Real `su`,
native helper, Android/OEM code and kernel pidfds were not executed. The three
fixture/JVM commands returned zero; independent saved-output review `4fcc5218...`
checked the actual `c1e2f2cd...` receipt. These results do not establish Android
socket, SELinux, kernel, process or authentication acceptance.

The remaining runtime connection is still substantial: package and invoke the
source from the full app, join the genuine captured host controller, transfer
real control ownership, assemble guest entry and native lifecycle, and resolve
physical UI/property/data-service ownership. Genuine ColorOS credential/policy
consumers and reciprocal PIN/fingerprint/app-key/CE behavior remain unfinished.
All eighteen device cases remain pending, and phone access remains offline-only.
