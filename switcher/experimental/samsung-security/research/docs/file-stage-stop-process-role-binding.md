# Bind Stop evidence to the observed process roles

This tracks the process-role handoff for the integrated `95f75e66` tester,
`dc799194` host, and `e9cbc101` controller lineage. The selected artifacts
still have no operator-readable process-role receipt for the fresh Partial.
[Integrated build receipt](../out/file-stage-integrated-runtime/app/r-8bd93a75/receipt.json)

## Offline successor

The unselected static ARM64 controller `5cf3b622` captures the exact owned
child's birth after the original Partial admission. It requires two
nonconsuming live checks around the authenticated proc read and leaves the
record empty when the sample is unavailable. The file-backed provider forwards
that record before cutoff. Only the direct successful Prepare reply can carry
the `PSR1` marker, PID and start ticks in its 16-byte trailer. Query, Close,
and drain retain the original zero trailer. The build preserved the carrier
pins and the original controller remains the selected artifact.
[Native build receipt](../out/file-stage-controller-successor-build/r-22e19452/receipt.json)

The offline owner, provider and reply models passed 12, 16 and 30 cases.
The [host decoder](../compat/handoff-host/com/appleexploit/oneos/security/authority/RetainedStopRolePayload.java)
passed 68 cases and read the two exact modeled C frames. This verifies the
handoff format in the PC fixtures. The
[host source transform](../tools/compose_file_stage_stop_role_host.py) also
compiles against SDK 37 for the new controller digest and extent. It uses the
actual sent request kind and retains the child record on the original Prepare
command. Fourteen host transport models passed, including strict Prepare-only
decoding and retention through terminal status.
[Native-to-host wire check](../out/file-stage-stop-role-cross-wire/r-3b1e812f/receipt.json)

### Failed-start cleanup build

Static ARM64 controller `9e485f8f` combines the failed-start cleanup fix with
the same child-birth forwarding. Its 734,192-byte executable passed all 36
compile, link and inspection commands. Only the guard source and header and
the provider source differ from `5cf3b622`. The guard and provider are the only
changed input objects in the final link. The carrier identity and the three
child-birth functions match the previous build's contract.
[Static build receipt](../out/file-stage-controller-successor-build/r-122795bb/receipt.json)

The exact controller reply source passed 21 PC fixture cases. In the new
failed Begin case the modeled provider holds once, then confirms no-child
local closure. Prepare replies `REFUSED`, followed by `CLOSING_HOLD` and
`LOCAL_CLOSED` on successive queries. The reply carries no Partial or role
data, and no child-birth read runs. This verifies the controller's reply path
with a modeled provider and syscalls.
[Reply fixture](../out/file-stage-r22-begin-wire-model/r-0406a832/run-receipt.json)

The matched PC set pairs tester `3717ed60` and host `5eba2ed6` with controller
`9e485f8f`, profile `d6c5540a` and publisher `319cd0eb`. Only `classes.dex`
changed in either APK. The SDK build retained 34 tester and 53 host definitions.
Bytecode readback confirmed that the tester's `begin` and the host's constructor
consume the new digest and 734,192-byte extent. The 12-case host worker fixture
accepted the current profile's role trailer and rejected the previous digest
and extent together and in both mixed combinations.
[SDK build](../out/file-stage-stop-cleanup-sdk-6a3b3d83/r-4a2f4014/receipt.json)
· [Worker fixture](../out/file-stage-stop-cleanup-worker-model-0d94765d/receipt.json)

Both packages passed v2 and v3 signature verification. The 288-byte profile
passed the exact parser round trip and six refusal cases. ELF readback found
that profile once in the publisher. The paired verifier rejected replacement
of the tester, host or publisher with its immediate predecessor. The set is
unselected. Device use still requires a matching active host and verified
custody of the occupied controller slot.
[Matched PC set](../out/file-stage-stop-cleanup-cohort-5301dbda/receipt.json)

## Tester status evidence

The successor uses private callback transaction 6 with an explicit version
and a [fixed 56-byte primitive reply](../compat/handoff-view/app-protocol/com/fahadali/oneos/core/root/RetainedStopStatus.java).
The host brackets the controller birth read with its existing validated
pidfd. It returns the status and optional Prepare record only after rechecking
the caller and retained owner. The tester relays the request on the existing
ordinary work slot and samples its elapsedRealtime before sending and after
decoding the reply. The existing Stop slot and legacy status reply remain
available. Failure to obtain a diagnostic record supplies no evidence.

The [tester display](../tools/compose_file_stage_stop_status_activity.py)
keeps its status captions separate from the diagnostic row. It retains the
first eligible Partial on the same Operation and Prepare attempt. A terminal
row requires the matching role, acknowledged Stop and fresh cleanup status.
Redrawing the screen preserves the original sample bounds.

The diagnostic row starts with `ONEOS_STOP_ROLE_V1` and `partial` or
`terminal`. Its decimal fields are Prepare sequence, app PID, SystemServer
PID, controller PID and ticks, child PID and ticks, unsigned child mount
namespace inode, Partial sample start and end, Stop request time, and terminal
sample start and end. The last three fields are zero in a Partial row.
Independent capture still has to bind the displayed row, proc view and clocks
to the actual tester and observer on the same run.
The [saved-capture reviewer](../tools/review_saved_stop_carrier_capture.py)
can compare both displayed process births with the retained native session
and the exact staged carrier. It reports a record match only. Eight offline
join cases passed, including a refusal for a different process birth.

The [combined SDK 37 and D8 build](../out/file-stage-stop-status-build/r-c032e8ba/receipt.json)
produced tester DEX `9334a677` and host DEX `51bd5260` with one identical
schema source. The controller reader, schema, worker, callback and Activity
fixtures passed 17, 108, 9, 22 and 7 offline cases respectively. The DEX files
are the inputs to the signed PC set below.

## Signed PC test set

The [matched set receipt](../out/file-stage-stop-status-package/verified/r-da2fd9ca/receipt.json)
pins the signed tester `b36225ee`, signed host `fb6484ab`, controller
`5cf3b622`, protected profile `2a4d009c`, static profile publisher
`4f125f23`, and native observer `f424d987`. Both APKs passed v2 and v3
signature checks. Independent APK readback confirmed the exact DEX and retained
manifests and Android-only host scope. The profile binds the tester, its
certificate and the exact controller. The publisher contains that profile once.
Both APKs use fresh debug certificates. An earlier APK with the same package
and a different certificate cannot receive this set as an in-place update.

The set is verified offline and remains unselected. Staging, live host
activation, trusted observer capture and device acceptance remain separate.

## Live test prerequisites

The current read-only inventory identifies controller `e9cbc101` at the fixed
executable path and neither test package is listed. The prior PC tester pins
`5cf3b622` and the cleanup tester pins `9e485f8f`. The existing installer
publishes only to an empty slot. The tester can hold an executable descriptor
before Prepare takes the stage lease, so marker absence alone cannot prove that
replacing the file is safe. Any future staging proposal needs verified old
artifact custody and the exact launch and view owners accounted for.
[Current read-only inventory](../out/file-stage-device-preflight/r-931ccc48/receipt.json) · [Controller installer](../compat/native/guest_tree_install_controller.c)

The host registers at SystemServer startup and loads its protected profile once.
The reviewed module disables hot reload. Under the current no-restart constraint,
a live test requires a verified matching host already running or a reviewed
activation path into the running SystemServer. The repository has no verified
path of that kind. The earlier tester-only proposal pins different artifacts
and excludes host activation. [Phone test decision](../PHONE_TEST_DECISION.md)

## Existing ownership

- The tester reads the controller PID from its owned launch stream's single
  `NATIVE_OFFER`. The host verifies that PID against the connected root
  socket's kernel peer credentials, the ORH2 identity frame, and the target
  of the actual retained pidfd. Only this joined identity qualifies as the
  controller role. A launch PID, `Process` handle, or process name alone can
  identify a wrapper, a stale process, or a different occurrence.
  [Tester launch](../out/file-stage-confirmation-lifecycle-build/r-ff4de804/app/src/RetainedRootOfferLaunch.java#L100) · [Host identity and pidfd](../out/file-stage-early-exit-source/r-3050eec6/RetainedHostNativeControlV2.java#L193)
- The native owner takes the exact child PID from its fork. It admits the
  Partial only after receiving that child's kernel-authenticated message,
  checking its actual proc and mount view, and retaining its rights. The
  controller's ORH2 state frame carries the observed flag and three view
  fields, including the child mount namespace inode. It carries no child
  PID or process start ticks. The app status callback returns a scalar from
  the exact retained `AppView` under the existing caller check.
  [Native child](../out/guest-tree-root-attach/r-95b38f3d/src/guest_tree_control_owner.c#L324) · [Partial admission](../out/guest-tree-root-attach/r-95b38f3d/src/guest_tree_control_owner.c#L398) · [ORH2 reply](../out/tree-retained-controller/r-b40000a8/source/retained_root_handoff.c#L695) · [Host status](../out/file-stage-readiness-build/r-98658bf067/host/src/PreparedRetainedHostNativeBindingV2.java#L827)

## Bounded handoff

1. At the existing native Partial admission, sample the exact child's PID and
   proc start ticks under the same ownership and view checks. Carry that
   immutable birth record on the authenticated native-to-host response along
   with the observed mount identity and original Prepare reply sequence. Use
   an explicitly distinguished response format for a matched cohort. The
   current parser requires bytes 48 through 63 to be zero and must continue
   to reject an unexpected format. Failed attribution leaves evidence held
   while preserving the existing Prepare and Stop lifecycle.
   [Current response parser](../out/file-stage-early-exit-source/r-3050eec6/RetainedHostNativeControlV2.java#L316)
2. Join the child record to the host's validated controller PID and its
   proc birth while that pidfd still names a live controller. Retain one
   immutable observation on the same native control and `AppView`. The
   host can read its own SystemServer birth and the app birth for the
   validated Binder caller, or join separately captured birth tuples to
   those exact PIDs in the same run. Independently bracket these reads with
   the same boot and admitted proc view. The app's actual UID and resumed
   component are additional cross-checks. A process-name lookup alone
   cannot substitute for the recorded Binder peers.
   [Host caller and retained owner](../out/file-stage-readiness-build/r-98658bf067/host/src/PreparedRetainedHostNativeBindingV2.java#L664) · [App's Binder caller](../out/file-stage-confirmation-lifecycle-build/r-ff4de804/app/src/RetainedRootHostServiceV2.java#L109)
3. Extend the existing private status path with a bounded, versioned
   read-only record for the same `ViewAttempt`. Return the Partial status
   and its immutable process-role record together. Recheck the exact
   broker, offer, caller PID/UID, and `AppView` after any work outside the
   owner lock. Use a non-authorizing capture handle tied to that single
   attempt and observation. Carry that handle with the fresh UI Partial
   and subsequent Stop/terminal observations. The record contains metadata
   only and carries no socket name, file descriptor, Binder capability, or
   credential data. It adds no public endpoint, native command, or control
   path. The existing serial worker continues to own Prepare and Stop.
   [Private app attempt](../out/file-stage-confirmation-lifecycle-build/r-ff4de804/app/src/RetainedRootHostServiceV2.java#L61)

## Capture and terminal rules

- Capture the admitted fresh Partial and verify both recorded native births
  are still live before the operator confirms Stop. Bind PID, start ticks,
  boot, proc view and child mount identity. For a kernel without PID
  namespaces, require the pinned global PID-view proof. Do not infer the
  owned child from a name search or hand-entered PID. Release observation
  references to guest mounts and namespaces before Stop. Retain only the
  independent observer's read-only physical host references.
- Preserve a fresh same-handle Stop acknowledgment and cleanup caption,
  then begin the independent post-Stop interval after the terminal sample's
  device-boottime upper bound. Join the tester and observer time namespaces or
  independently prove matching boottime offsets. The exact target kernel
  enables time namespaces. Probe the two earlier numeric PIDs at both
  boundaries in the admitted proc view. PID reuse, masking, an unavailable
  status, or owner replacement holds the result. A retained Partial record
  after cutoff supplies correlation only. A cleanup caption or pidfd exit
  supplies neither process absence nor physical release evidence.
  [Independent readback contract](../out/file-stage-current-stop-readback/REPORT.md)
- An Activity redraw may reuse the existing local `Operation` and handle.
  App or SystemServer rebirth, broker replacement, or a changed host/control
  binding invalidates the join. Do not reattach historical records to a new
  occurrence. Any wire or APK change requires a freshly matched and reviewed
  controller, tester, host, profile and publisher before a later test
  proposal. The profile must bind the exact tester signer and APK and the
  controller digest. Existing stage or install approvals do not select this
  successor.
