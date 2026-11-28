# File-backed Prepare and Stop test review

**Matched readiness APKs verified offline. Device test held.** The test would
exercise the verified image, private mount, child-view preparation and normal
Stop on the pinned Galaxy S26 Ultra build. PIN, fingerprint and ColorOS runtime
launch remain later milestones under [GOAL.md](../GOAL.md).

The historical tester could consume its one Prepare attempt before the host
committed the same offer. The matched successor waits for a read-only observation
from that committed host before dispatching Prepare once. Both SDK37 DEX builds,
their debug APKs and the matching 288-byte protected profile passed PC checks.
The new debug signers allow a fresh installation if those package IDs are absent.
An installed package with the old signer needs a separately reviewed path. The
matched native publisher embeds the new profile and its exact hash. The fixed
protected-drop transport now stages that publisher. Live read-only preflight
and a separate review of the exact device actions are still pending.
[Readiness source fixtures](../out/file-stage-tester-ui-review/model/receipt.json) · [Matched APKs and profile](../out/file-stage-readiness-package/r-6c688c4ff1/receipt.json)
[Matched publisher](../out/file-stage-readiness-publisher/r-9501bd2615/receipt.json)

## Staged late process-exit cleanup

The [source-only successor](../tools/compose_file_stage_late_exit_cleanup.py)
changes the exact host worker from the signed test cohort. After an
explicit native local terminal, the original background worker keeps
final cleanup ownership while the exact process-exit observer finishes.
It still closes the socket, metadata read, and raw ancillary rights once.
It closes a validated process descriptor only after a positive exit
observation and actual termination of that observer. Missing or uncertain
observations cannot authorize that close or report local cleanup.

The app's Prepare and Stop calls keep their existing observation deadlines.
A later status read from the same retained attempt can see cleanup finish.
The local cleanup status still depends on the explicit native terminal and
all Java-side ownership checks. Stop acknowledgement and the independent
post-Stop device checks remain separate. This successor is staged on the PC
and has no new signed test cohort.

Four authored JVM cases passed with the original 30-second budget. The
baseline left cleanup unconfirmed and the validated descriptor retained
after a late positive exit. The successor stayed pending until the observer
thread returned, then closed the exact descriptor once and reported local
cleanup. Both versions retained the descriptor on an uncertain poll. SDK37
and D8 emitted the five worker definitions in a 19,148-byte DEX039.
[Build and test receipt](../out/file-stage-late-exit-build/r-56111869/receipt.json)

### Exit before the observer starts

The [startup successor](../tools/compose_file_stage_early_exit_cleanup.py)
records a clean positive exit from the first poll on the validated
descriptor, before any observer start attempt. The original liveness
check still refuses startup. The worker uses that exact descriptor
identity only for its one local close attempt. A mixed or failed poll
retains the descriptor. This path earns no readiness, COMMIT, Prepare,
Stop, or local terminal status.

Ten authored JVM cases passed. The original worker retained the descriptor
after a clean early exit. The successor closed it once while preserving the
original startup refusal. Both workers retained the descriptor after a mixed
poll or a thrown poll. The close-failure case preserved the original refusal
and made one close attempt. Both saved late-exit regressions passed with the
original 30-second budget. SDK37 and D8 emitted the five worker definitions
in a 19,412-byte DEX039. [Build and test receipt](../out/file-stage-early-exit-build/r-fe5a7229/receipt.json)

The complete host DEX combines the five successor worker classes with the
43 exact held host classes. D8 emitted all 48 expected definitions and
excluded both compiler-only declarations. The 133,004-byte DEX remains
unselected. [Full host build receipt](../out/file-stage-early-exit-host-dex/r-cbc36dc3/receipt.json)

### Unsigned host package

The reviewed 48-class DEX is now packaged in the 135,401-byte unsigned host
APK `9109e2b3…`. The package retains the exact compiled manifest, resource
table and three Vector metadata entries. The six stored payloads start on
four-byte boundaries, and the central directory follows the last payload
directly. Replacing the new DEX with the old bytes reproduces the predecessor
archive exactly. A second assembly matched byte for byte. Five rejection
checks covered the old DEX, a malformed replacement DEX, a valid ZIP with a
changed scope, trailing bytes and a signing-block-like gap.
[Package receipt](../out/file-stage-early-exit-host-package/r-ee92517b/receipt.json)
SDK 37 `aapt2` read the exact host package ID, version code 1, version name
`0.0.1-source-only` and minimum and target SDK 37 from the saved archive.
[Manifest readback](../out/file-stage-early-exit-host-package/r-ee92517b/aapt2-readback.json)

The pinned tester, native controller and protected profile are byte-identical
to the matched readiness inputs. The profile binds the tester and controller.
Using the successor on the device requires fresh exact host signature and
cohort evidence, a current paired-device preflight and a separate phone test
review. The unsigned APK is unselected and ineligible for installation.

### Late Stop acknowledgment

The isolated tester's two-second Stop wait can end while the relay still owns
the one Stop request. The [app source successor](../tools/compose_file_stage_late_stop_ack.py)
retains a validated `QUEUED` reply on the same attempt when the original owner
is still current at receipt. A status refresh samples that historical queue
receipt on the existing worker before a terminal observation can release the
binding. Status alone supplies no acknowledgment. Stop remains one-shot, and
local terminal and completed cleanup remain separate states.

Five service cases passed with the exact predecessor and successor classes and
authored Binder fixtures. The held predecessor received the late reply without
surfacing it. The successor preserved the genuine reply and refused unavailable,
malformed and already retired replies. Thirteen Activity operation model cases
passed, including a terminal sample with the acknowledgment still unknown. Two
app-only SDK 37 builds emitted identical 42,420-byte DEX files with all 30
definitions. The tester successor remains an unselected PC artifact. A new
signed tester would need a matching protected profile and publisher.
[App DEX receipt](../out/file-stage-late-stop-ack-build/r-6d8e6986/receipt.json) · [Service cases](../out/late-stop-ack-worker/exact-classes/receipt.json) · [Activity cases](../out/late-stop-ack-ui-worker/r-74be8c4138/receipt.json)

### Overlapping tester windows

The [Activity successor](../tools/compose_file_stage_activity_lifecycle.py)
tracks each started screen and keeps one process-wide preparation operation.
When a second screen stops, the first can still open Stop and refresh the
same attempt. The original started occurrence and exact dialog guard prevent
old confirmations from acting after a stop and restart. Status refreshes
redraw the started screens and leave stopped screens detached.

Six authored lifecycle cases passed with the exact SDK-compiled Activity.
The predecessor failed the five overlap and stale-dialog cases and passed
ordinary recreation. The successor preserved all 30 program definitions.
All 19 non-Activity class files are byte-identical to the late-acknowledgment
build. The ten nested Activity class files differ only in source line
metadata. [Lifecycle cases](../out/file-stage-activity-lifecycle-model/r-0a5e44c37f/receipt.json) · [SDK build](../out/file-stage-activity-lifecycle-build/r-ccef04ee/receipt.json)

The unselected unsigned tester APK is 45,828 bytes. It contains the new
43,144-byte DEX and the exact prior manifest and resources. SDK 37 badging
confirmed the package, version and sole launcher. The old protected profile
applies to the previous signed tester. A successor device proposal needs a
signed tester, a matching profile and publisher, and live stage and package
review. [Unsigned tester receipt](../out/file-stage-activity-lifecycle-app-package/r-059c9c76/receipt.json) · [Manifest readback](../out/file-stage-activity-lifecycle-app-package/r-059c9c76/aapt2-readback.json)

## Integrated Stop evidence tools

The [integrated cohort verifier](../tools/file_stage_integrated_cohort.py) checks
the exact signed runtime pair `95f75e66` and `dc799194`, its protected profile,
publisher and unchanged `e9cbc101` controller. The
[transcript reviewer](../tools/review_file_stage_observation.py) accepts that
cohort with `--integrated` and keeps the UI result separate from physical
release evidence. A late acknowledged Stop can finish the UI record for the
same attempt. A cleanup caption alone cannot finish it.

The [Stop record reviewer](../tools/review_integrated_file_stage_stop.py) joins
the completed transcript to an elapsedRealtime bound, both prior process
births, four direct lookup results, and measurements of the original held
carrier before and after Stop. It checks the referenced process and ioctl
records for diagnostics. The V1 lookup lines carry process identifiers and
results, with no timing or reader-context binding. Other V1 references lack
a defined raw schema for the normalized timing and visibility claims. The
reviewer now holds every V1 result after the existing checks, with CLI exit 2.
The old reviewer reproduced false acceptance with contradictory raw timing
or visibility. Five focused checks cover the hold and raw PID mismatch.
Physical release acceptance still requires a trusted live capture bound to
the same Stop attempt.

The [native process probe](../out/file-stage-stop-proc-probe/r-6b8a65e9/receipt.json)
builds as a static ARM64 executable. It uses a held procfs root and returns
direct lookup `ENOENT` separately from failures after a process directory is
opened. The target's global PID-view mode requires the exact saved compressed
Samsung kernel configuration, which has PID and user namespaces disabled. A
separate comparison checks the actual reader's visibility in the admitted proc
view. No probe has run on the phone. The integrated join passed one matching
model and five raw-record mismatch cases. Component tests separately cover the
process, carrier and transcript comparisons.

The [native carrier observer](../compat/native/guest_tree_stop_observer.c)
retains the original read-only stage and carrier descriptors across a bounded
wait. It measures fs-verity on the same carrier descriptor in each window.
After the second measurement it checks the empty backing directory on physical
F2FS and obtains direct `ENOENT` for the three guard markers. It publishes the
second window and the closing frame only after releasing its descriptors.
The [587,896-byte static ARM64 build](../out/file-stage-stop-observer-build/r-60cb41ee/receipt.json)
has SHA-256 prefix `231953d2`. Offline checks cover 17 observer lifecycle cases,
72 wait cases and 65 decoder cases.

The [saved carrier capture reviewer](../tools/review_saved_stop_carrier_capture.py)
joins both measurements to the pinned fs-verity digest, the actual staged V2
publication and the saved stage and guard directory identities. Nine checks
used the pinned staging records and synthetic capture frames.

The [combined V2 observer](../compat/native/guest_tree_stop_session.c) retains
both live process births with pidfds and uses one authenticated procfs root
throughout the run. Each post-Stop probe requires a readable retained pidfd on
both sides of a direct proc lookup returning `ENOENT`. The two probe pairs
bracket carrier measurement, backing and marker readback, and carrier descriptor
closure. The observer samples its actual boot, process birth, credentials,
mount namespace and time namespace and compares them across the run. The
[V2 decoder](../tools/file_stage_stop_session_capture.py) checks the ordering,
pidfd identity and original raw line locations. The saved capture reviewer
accepts this format with `--session-v2` and still grants stage-match credit only.
The [610,344-byte static ARM64 build](../out/file-stage-stop-observer-v2-build/r-224dc9ba/receipt.json)
has SHA-256 prefix `f424d987`. Its main passed 30 offline lifecycle models and
the decoder passed 57 offline checks. Seven integration checks used the existing
staging receipt and modeled captures. The ARM64 executable remains unexecuted.

Live acceptance still needs a trusted capture transport, current proc visibility,
and the exact clock and process roles from the fresh Partial and its Stop.
The target kernel enables time namespaces, so the UI and native boottime samples
need a same-namespace or equivalent clock proof. The existing tester does not
expose its verified controller and child roles with the observed Partial.
The [role-binding design](file-stage-stop-process-role-binding.md) specifies the
private read-only handoff for the next matched cohort.

## Historical pinned PC inputs

| Input | Size | SHA-256 prefix | Evidence |
| --- | ---: | --- | --- |
| ColorOS EROFS carrier | 13,890,850,816 bytes | `094ff7e7` | [Full filesystem readback](../out/guest-tree-erofs-image-readback/r-c06d34d3/receipt.json) |
| ARM64 installer with embedded controller | 1,387,248 bytes | `7eac4c58` | [Static installer build](../out/guest-tree-carrier-installer/r-e5d9aea8/receipt.json) |
| Compact ARM64 controller | 746,760 bytes | `803691c5` | [Static controller build](../out/tree-retained-controller/r-b40000a8/receipt.json) |
| `com.fahadali.oneos.viewprep.filetree` tester APK | 49,356 bytes | `28bf08bb` | [Signature and build verification](../out/file-stage-prepare-app-build-review/verify-dad1e3ec/receipt.json) |
| `com.appleexploit.oneos.security.retainedguard` host APK | 139,689 bytes | `50413f66` | [Host build and scope](../out/retained-view-ingress-host-package/r-698a94c6149a/receipt.json) |
| Exact protected host profile | 288 bytes | `74e8623b` | [Offline profile](../out/file-stage-preparation-app/protected-profile-candidate/receipt.json) |
| ARM64 protected profile publisher | 602,736 bytes | `2f7d5466` | [Publisher build](../out/guest-tree-host-profile-publisher/r-272b9115/receipt.json) |

The tester uses its own app ID and a fresh, repository-local debug signer.
The protected profile binds its exact APK, signer, version and compact native
controller. The existing host supports the same authenticated ORH2 protocol.
It opens one profile per process and requires the exact user-0 app plus the
actual Binder caller and process identities. Its APK declares static `android`
scope. The independent cohort check matched the offline installer and APK pins, exact
embedded controller bytes and current carrier file identity.
[App source transform](../compat/app-integration/file-stage-preparation/README.md) · [Offline cohort](../out/file-stage-prepare-test-cohort/receipt.json)

## Read-only preflight

The most recent check did not find a unique online ADB device. An online
preflight needs to verify the pinned build, existing root read access, free
space on the active F2FS `/data` mount, and the exact namespaces and ownership
of the fixed isolated paths. It also needs the installed package hashes and
signing compatibility for the tester and host, the current host activation
state, the bootstrap permit and the protected `/data/system/oneos_retained_root_link_v2` slot.

The [read-only preflight](../tools/check_file_stage_device_preflight.py)
queries the existing paired ADB service directly, checks the exact fingerprint
before reading the isolated paths, and requires a framed remote exit. The
inventory shell checks its own boot, mount namespace and credentials against
the initially admitted identity before and after its reads. Only the resulting
comparison is saved. The package check distinguishes an enabled user-0 package
from a package only reported by the all-user known and uninstalled query. An
empty all-user result is evidence for review of a fresh install. Device package
admission remains a separate check. Unknown, disabled and historical package
states hold the test. The host's current SystemServer activation is separate.
The signed host checks its separate bootstrap permit at SystemServer startup
and again during capture. Preflight samples the permit directory and file,
including the file hash. A missing or different permit holds the sequence.
Review actual host activation and profile consumption separately from the file
sample and static scope. [Current host and operator audit](../out/file-stage-current-operator-review/FINDINGS.md)
[ADB shell framing](https://android.googlesource.com/platform/system/core/+/refs/heads/android10-gsi/adb/shell_protocol.h) · [AOSP package query](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/core/java/com/android/server/pm/PackageManagerShellCommand.java#974)

The [PC sequence review](../tools/review_file_stage_sequence.py) reads only a
saved v4 preflight receipt. A positive observation must bind the inventory to
its shell identity, be at most two minutes old and report host activation as
unverified. The review requires an empty
stage and drop, the expected mount and storage profile, and exact package and
profile dispositions. It rechecks the [local cohort](../tools/check_file_stage_local_cohort.py)
against the exact build receipts and embeds that result in the review record.
The small artifacts are rehashed. The carrier file is checked against its prior
whole-file readback and the verity descriptor. The transfer must still rehash
the full carrier before releasing its final bytes. The record sets `mayExecute`
to false. A profile already matching the
new cohort takes the readback path. The publisher is a separate operation
because it can write if the slot is absent. A different profile, package
collision, or missing observation holds the sequence.

For a fresh stage, the bootstrap requires both fixed and temporary isolated
stage and lease names to be absent. A stage from an earlier verified attempt
needs its own exact ownership and outcome evidence. An existing host profile
with unknown or different bytes blocks this test cohort. An exact installed
match satisfies the file input without another write. A new profile needs an
absent-only publication under the protected parent with an independently
checked final file. The current host process must actually observe it.

The separate publisher embeds the exact signed tester profile. On the pinned
device build it opens a new anonymous F2FS inode, verifies and syncs it, and
uses one no-replace link from that held descriptor. An exact existing profile
takes the read-only match path. The syscall, target permissions and later
profile consumption still need approved runtime evidence.
[Publisher model](../out/guest-tree-install-host-profile/model-3f3b3f41/receipt.json)

## Actions for the eventual approval

1. Verify `/data/local` is on the expected root-protected `/data` mount. Use a
   fresh `/data/local/.oneos-file-stage-803691c5` for the two pinned executables.
   Transfer both on the same granted shell and verify their exact bytes before
   execution. Run the selected bootstrap command only for a verified fresh
   stage. V2 uses `--bootstrap-empty-stage-with-witness` and carries both
   reported directory identities into later observations. The bootstrap
   publishes the empty stage and its dedicated
   lease through no-replace renames. The image installer and controller
   installer require the actual protected stage and exclusive writer guard.
2. The original V1 staging sequence uses `--install-preparation-controller`
   and `--install-verified-carrier`. The bound V2 candidate uses one shell
   with the retained stage and guard for both bound commands. It requires
   independent controller verification before the carrier grant and compares
   the publication witness with a separate read-only fs-verity observation
   before profile publication. Both versions stream the same 13.9 GB carrier.
   The phone needs space for the carrier, the 109 MB fs-verity tree and
   allocation headroom. The PC feed withholds the final chunk until source
   validation. The installer requires exact length and EOF, verifies the raw
   digest, enables and measures fs-verity, and publishes `guest.erofs` once.
   [Feed contract](../out/guest-tree-install-feed/CONTRACT.md)
3. Select only the APK and host-scope actions required by the live preflight.
   Confirm the tester and matching profile are present before host activation.
   The host takes one package hash attempt for its current SystemServer process.
   A new host installation or framework activation needs explicit review,
   including any required framework restart. A different installed signer or
   existing protected profile needs a separate decision before deployment.
4. Open the separate tester and record one confirmed Prepare prompt. The
   host's own BEGIN starts the controller independently of confirmation. Record
   controller association when it is actually observed. The tester waits for
   internal readiness and sends Prepare once. Require primary **Partial
   filesystem view observed.** and the Prepare acknowledgment from the same
   attempt before confirming one Stop. Require its Stop acknowledgment and
   primary **Local cleanup observed.** Status samples can skip the intermediate
   **Local terminal observed. Cleanup still pending.** caption. Preserve every
   line because a previous partial caption can remain below the primary line
   or under an unavailable-status warning. Confirm the same stage, carrier and
   released view with independent device evidence.
   [Current attempt order](../out/file-stage-current-attempt-order/ORDER.md) · [Signed Stop observation audit](../out/file-stage-stop-observation-audit/REPORT.md)

The [PC transcript checker](../tools/review_file_stage_observation.py) accepts a
normalized `oneos-file-stage-current-ui/v1` record under
`out/file-stage-current-ui-evidence/`. Bind it to the verified local cohort and
record the full widget lines, one attempt label, and monotonic elapsed time.
The checker distinguishes persistent acknowledgment footers from repeated
confirmations. Record the native dispatch timestamp, process association and
filesystem cleanup separately from its transcript result. [Inert transcript checks](../out/file-stage-current-evidence-tests/r-3bb4f242/receipt.json) · [Independent post-Stop evidence](../out/file-stage-current-stop-readback/REPORT.md)

A publish result needs the exact operation's single `PUBLISHED_CLOSED` frame
and successful installer exit. Carrier publication additionally needs the
producer's exact source receipt and successful exit. A missing response,
disconnect or `HOLD` preserves uncertainty. Recovery starts with read-only
inspection of the same stage, process and marker. The first proposal should
test normal Stop before a separately reviewed disconnect case. Both profile
publisher generations emit the same terminal lines. Attribute the line to the
same held executable and read back the exact matched profile before advancing.
[Terminal audit](../out/file-stage-terminal-review/REVIEW.md)

The [carrier receiver](../tools/guest_tree_carrier_receiver.py) selects the
current paired transport ID. The same raw shell checks the exact build, boot,
mount namespace and opened installer descriptor before it waits for a fresh
grant. After the grant it repeats those checks and hashes the held descriptor
again before executing it. The PC waits for that shell's READY frame before
it sends image bytes. This source has an import-only entry for a separately
approved coordinator. The [protected-drop receiver](../tools/guest_tree_protected_drop_receiver.py)
binds both executable snapshots to the shell before its grant. It requires
publication acknowledgment, remote exit zero and EOF, then reobserves the same
published directory generation before handing it to the carrier receiver.
The two-artifact sender passed 18 local socket cases. Four additional local
socket cases exercised the receiver handoff, wrong device identity, closure
before grant and a refused READY. Target shell, filesystem and SELinux behavior
still need device evidence.
[Matched protected-drop sender tests](../out/guest-tree-protected-drop-transfer/r-367f4b9857/receipt.json)

Long read-only and receiver scripts now use a bounded ADB shell bootstrap. It
receives the exact ASCII source on the same socket, verifies its size and SHA-256,
then starts the original script. The bootstrap request fits the legacy ADB
transport limit. The protected receiver still requires HELLO before it can send
a grant. Nine local socket cases checked the short and streamed paths and refused
invalid sources. Actual Android shell behavior remains unverified.
[ADB forwarding limit review](../out/guest-tree-shell-admission-review/REVIEW.md)

The [shell-v2 engine](../tools/guest_tree_shell_v2_transfer.py) holds back its
last data frame until the exact PC producer has exited zero and its exact
source receipt has been verified. It then sends that frame and one close-stdin
packet. Completion requires the installer acknowledgement and the actual
remote zero-exit packet followed by EOF. Local socket fixtures exercised the
grant, binary stream and terminal evidence. Thirty transport cases passed,
including two concurrent observations of EOF before final validation. Device
execution, transport permissions and staging recovery still need target evidence.
[Shell-v2 framing](https://android.googlesource.com/platform/system/core/+/refs/heads/android10-gsi/adb/shell_protocol.h) · [Transport tests](../out/guest-tree-shell-v2-transfer/SAVED-READBACK.json) · [Receiver integration](../out/guest-tree-carrier-receiver-tests/final-receipt.json)

The final installer passed 25 inert carrier and acknowledgement cases,
including rejection of regular-file output before stage acquisition. The
bootstrap and controller publication leaves passed separate tests. The compact
controller's refusal cleanup passed 20 extracted protocol fixtures, including
one valid final query after a fast refusal with a retained provider.
[Installer checks](../out/guest-tree-carrier-installer-review/successor-509f3ff4/receipt.json) · [Protocol checks](../out/file-stage-refusal-query-review/SAVED-READBACK.json)

The first approved staging attempt reached the target root shell and created
the protected installer directory. It stopped before writing either executable.
The [post-attempt preflight](../out/file-stage-device-preflight/r-3cf0cd72/receipt.json)
also observed the carrier, profile and APKs absent. The corrected inode parser
passed read-only Android checks. The fresh-only receiver holds on the existing
directory. See [the current phone-test decision](../PHONE_TEST_DECISION.md).

Before advancing to profile publication, bind the carrier grant to the exact
stage and guard from controller readback. The existing V1 terminal frame carries
no inode witness. A separate V2 source path now exports the mount, device,
inode, size and nanosecond timestamps from the final verified publication.
It emits that record only after local close and guard release succeed. The PC
parser binds the expected size and requires the producer receipt, remote exit
and EOF before reporting the witness. It describes the earlier publication.
The separate read-only observer checks the fixed named file and its open
descriptor before and after the kernel fs-verity measurement. It compares
the digest with the pinned descriptor and reports the observed identity only
after close. The PC compares all nine identity fields after caller verification
of the shell, executable, terminal outcome, boot and mount namespace. This
joins the two observations at their verified boundaries. V2 deployment and
same-boot readback on the phone remain open.
Before either APK install, revalidate the protected profile at package
admission. Host activation and Prepare and Stop still await device evidence.

The full bound V2 build passed using the repository's existing binary stdout
link recipe. Static inspection verified the 1,396,112-byte AArch64 static PIE,
the bound guard and identity symbols, seven verbs and the embedded controller
and carrier pins. The artifact is selected for offline V2 review only.
The PC-only cohort checker accepts `--carrier-protocol v2` to rehash that
exact linked installer, its receipt and the shared controller, carrier,
publisher and signed APK inputs. The result is review evidence with
`mayExecute: false`. The default cohort retains the existing V1 selection.
The drop renderer, pinned payload, inventory, receiver and readback renderer
now use the same explicit installer profile. Offline checks reject mixed
receipts and preserve the existing V1 rendered bytes. Both V2 grant methods
refuse before sending data. A later unselected build has native bound
controller and carrier commands. They duplicate the inherited stage and guard
descriptors before opening any paths. The installer checks the earlier
directories against the current held ones after the lease check and before
creating the writer marker. The direct API also refuses closed descriptor
slots before it can allocate any new ones.

The bound V2 renderer opens the stage and guard once and checks the same names
and descriptors at both grant boundaries. It checks the controller child's
exit and combined output before offering the second grant. The carrier inherits
the same descriptors. A private coordinator requires an independent controller
check between the two grants, drives the transfer and decodes the separate
readback shell's exit and EOF before comparison. The readback renderer checks
the earlier stage and guard around the exact pinned observer. The read-only
preflight and sequence review now carry an explicit matching V2 marker.
The V2 adapter retains the exact controller and readback commands when it
opens the waiting carrier shell. Both observers use that retained target. The
controller observer checks the files, stage lease and absent guard markers
inside the same target and directory checks, then decodes exit and EOF.
Offline tests cover late bytes after exit and transport drift.
The [post-removal V2 preflight](../out/file-stage-device-preflight/r-f80d969d/receipt.json)
confirmed a fresh staging layout. The user-approved attempt verified both
protected-drop binaries, then stopped during native startup. The
[post-attempt preflight](../out/file-stage-device-preflight/r-ded93d12/receipt.json)
found both exact binaries and no stage, carrier, profile or APKs. Even the
read-only and invalid-verb probes returned exit 139. The original ELF had
relative relocations for startup pointers and no interpreter. See the
[phone-test decision](../PHONE_TEST_DECISION.md) for the corrected offline
native outputs and remaining matched-build review.
The V2 bootstrap emits stage and guard mount, device and inode identities
after verified close. The host parser requires exact exit and EOF, and the
bound commands check those mount and directory identities. The native
carrier rechecks the controller's fixed file and SHA-256 under the same
guard lease before image creation. The staged coordinator captures the reply
on the same pinned target and checks it against independent inventory. It
requires matching carrier publication and readback before profile publication,
then rehashes the held profile on each APK install shell before READY. Its
V2 grant remains held. The saved drop collision model stops before opening
the protected drop.
[Bound build](../out/guest-tree-carrier-installer/r-1728ceb3/receipt.json) ·
[Bootstrap tests](../out/file-stage-v2-local-cohort/check_bootstrap.py) ·
[Six inert admission checks](../out/file-stage-bound-guard-model/r-6cf37262/receipt.json) ·
[Offline shell and frame checks](../out/file-stage-bound-shell-model/r-a116d0c4/receipt.json) ·
[In-memory transport checks](../out/file-stage-bound-shell-model/check_bound_transport.py) ·
[Coordinator checks](../out/file-stage-bound-shell-model/check_bound_coordinator.py) ·
[Bound adapter checks](../out/file-stage-bound-shell-model/check_bound_adapter.py) ·
[Staging coordinator checks](../out/file-stage-live-staging/check_v2_stage.py) ·
[Controller observer checks](../out/file-stage-bound-shell-model/check_bound_controller.py) ·
[Sequence checks](../out/file-stage-v2-local-cohort/check_sequence.py)
Five parser and seven comparison checks passed, including fragmented delivery,
separation from V1 and rejection of inode or mount substitution.
[Profile fixture](../out/file-stage-v2-local-cohort/check_pins.py) ·
[Parser fixture](../out/file-stage-carrier-witness-model/check_witness.py) ·
[Readback comparison fixture](../out/file-stage-carrier-witness-model/check_readback.py)

If READY is lost before the transfer begins, the receiver can now stop and
reap its exact PC feeder and close both local pipes. It preserves the remote
phase so a local exit cannot count as remote publication, cleanup or refusal.
[Five local subprocess cases](../out/file-stage-feed-cancel/r-4f5035c5/receipt.json)
passed, including refusal after transfer start. The fixture used no device.
