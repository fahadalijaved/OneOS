# Captured Samsung host to closed OneOS root session

This source batch connects the genuine retained-host bootstrap to an explicit
OneOS app service and its actual closed root-session factory. It is a PC-side
compatibility-tree implementation. No app build, installed service, root session,
guest launch or authentication is established by these sources.

The private normal-boot controller retains the new binding before starting it.
The binding rechecks that same module's private boot occurrence, Registry and
Family; a caller-supplied Context, readiness predicate or UID cannot replace them.
Its Context is borrowed from the already-captured UMS/preparer relationship.
The original PIN operation owner remains closed.

A separate protected `/data/system/oneos_retained_root_link` profile is required.
The older capture permit alone does not bind the app or start root work. The
profile constrains the package, current signer, installed APK, version and native
image. It is admission policy rather than proof of loaded code or live authority.
Package verification and APK hashing run on an owned worker; SystemServer's main
thread owns source admission and actual connection callbacks.

The app service remains unavailable before user unlock. The captured host first
registers a genuine unlock receiver, then checks
`UserManager.isUserUnlocked(UserHandle.getUserHandleForUid(0))`. Only that current framework result
starts the one hash/bind attempt; a broadcast alone cannot do so. The unlock and
package filters are separate. This avoids treating boot-phase completion as CE
or app readiness and leaves the app's direct-boot declaration unchanged.

Android's actual explicit service binding is the transport. The app's service
is unexported, performs no root operation on bind and accepts its closed protocol
only from the actual system UID. Its private startup retains the callback and
worker before calling `RetainedRootSession.begin` once. Only that factory's
actual returned Attempt can supply the private Control Binder. No arbitrary
Process, descriptor, supplied Attempt or text launch acknowledgement is accepted.

The shared versioned wire has only BEGIN, CAPTURED/FAILED and PING/REQUEST_CLOSE/
QUERY_STATE. It uses synchronous canonical Binder/Parcel framing. QUEUED means
delivery requested, not a live session or completed cleanup. The host adopts an
incoming callback before posting to main and rechecks its real source and package
before admitting commands. Loss of a reply or connection never justifies a new
spawn. Original Samsung service objects remain borrowed.

The control remains app-owned. App death, Binder acknowledgement, unbind or local
cutoff is not proof of native exit or complete drain. Real native-control custody
must transfer before guest admission; this source batch does not implement that
transfer. Process/property/display/data ownership, guest entry, genuine ColorOS
consumer wiring and all reciprocal PIN/fingerprint/app-key/CE outcomes remain
open. All eighteen device cases remain pending. The current offline-only decision
remains in force, and the initial upstream draft is unchanged by this local batch.

The actual seventeen-source SDK37 cohort now compiles: 55 authored definitions
(39 host, 15 app, one shared protocol), with 54 unchanged model inputs excluding
only the real Spawn boundary. Receipt
`out/closed-root-host-link-build/r-eb2019cc/receipt.json` (`d10896ca...`)
records both compiler commands returning zero with their processes reaped.
Compiler-only widget declarations and libXposed API102 stay outside the program
output. This is SDK compilation, not app/Vector APK assembly or Android loading.

The first compiler attempt remains failed in `r-952ad00e` (`04ef61b9...`). It
exposed the unavailable public-SDK `UserHandle.of` and `O_DIRECTORY` assumptions.
The corrected source uses public `getUserHandleForUid(0)` and a nonblocking
read-only parent open with the existing actual directory/identity checks.
Bounded independent source review `95c3c8dd...` covers those exact repairs.
Independent saved-output review `6f61b708...` verifies the actual compile.

The actual-source integration models now pass **27 scenarios / 242 checks**
against the unchanged 54-class input. Receipt
`out/closed-root-host-link-tests/r-a6eee388/receipt.json` (`f2df32d9...`)
records three fixture compilations and one JVM command, all returning zero with
their processes reaped. Only Spawn and explicit authored Android framework APIs
are replaced. No original Android/OEM implementation or native controller runs.
Independent saved-output review `d98be117...` verifies those results, source and
class maps, cleanup records and preserved failure histories without replay.

Both failed model attempts remain preserved (`1ce346d4...`, `a47fffe8...`). The
harness first mishandled the expected uncertain-close exception, then retried
that already-attempted close during cleanup. The corrected harness explicitly
requires the actual error and retained UNRESOLVED state, preserves service cutoff,
and does not retry the uncertain close. No production source was changed to make
those tests pass. Independent correction review is `ea4493fc...`.

The unlock cases model deferred binding and its genuine-framework query, but do
not mutate the old captured PIN Binding's user-state snapshot. They therefore do
not independently discriminate an accidental stale-PIN-Binding guard. The actual
Registry/Family-only source guard is separately source-reviewed. These are
authored lifecycle tests, not Android Binder, CE, native or authentication evidence.
