# Full-app closed-controller setup

This source adds only the fixed controller-file installation step reached from
the admitted closed BEGIN service worker, before RetainedRootSession.begin.
It is not ordinary prepare/launch, a UI action, Probe support, root-process
readiness or host/guest authority. This author ran no build, shell/helper,
Android/OEM, network or device workflow. The phone remains untouched.

The authored source mirror is
compat/app-integration/RetainedControllerSetup.kt; its full-flavor copy is in the
OneOS checkout. Original whole Kotlin files and their baselines stay in ignored
firmware only. The accompanying first-party delta specification identifies the
RootScript, RootVerbs and narrowly extended RootShell changes without importing
their whole third-party sources into normal files.

## Fixed request and assets

RetainedControllerSetup.ensureInstalled(actualAppContext, expectedHash, expectedSize)
is a one-shot worker call. It retains its Attempt before framework work, rejects
main-thread entry, and requires the approved request to match the full build's
RETAINED_CONTROLLER_SHA256/RETAINED_CONTROLLER_BYTES. The fixed asset is
root/oneos_retained_root_session; missing/disabled build pins fail before root.
It snapshots exactly 1..2097152 bytes, rejects short/extra bytes, verifies SHA256,
and retains that snapshot through the actual feed/outcome. No arbitrary source
file, destination path, command or caller-supplied result is accepted.

The only new verb is INSTALL_CLOSED_CONTROLLER / install-closed-controller.
Its arguments are exactly canonical decimal size 1..2097152 and 64 lowercase
hex SHA256. RootScript's separate SCRIPT_DATA mode is used only by this verb:
RootVerbs writes the actual AppAssets-verified root-script prefix first, then
the pinned native snapshot. Other stdin modes keep their existing meaning.

## Bootstrap without repairing or activating OneOS

The dedicated launcher requires the existing fixed stage and bin to be root's,
nonlink, non-group/other-writable directories. A prepared stage is a real feature
prerequisite: it never creates/chowns/repairs/migrates it or calls legacy BEGIN.
It does not replace bin/oneos_root.sh, even if the installed normal script is
old or absent. It creates one exclusive private temporary directory, snapshots
and verifies the pinned script prefix there, and runs that script as a child
with the remaining native bytes on stdin. Parent cleanup affects only its own
verified temporary script/directory; uncertainty prevents successful return.

Android mksh user redirections are single-digit. The parent reserves only
previously unused descriptors 3/4/5/6, retains actual stage/bin/temp/script
anchors, and the child borrows bin4 for its private script path while closing
only owned child copies 3/5/6. It never blindly closes other inherited slots.
The install handler independently reserves/refuses 5..9, requires the exact
remaining native bytes and EOF, verifies the payload, refuses a different
existing image and uses atomic no-clobber publication. Same-image installation
is verified idempotence, not permission to overwrite an active/orphan image.
The handler never executes the controller. Its sole success line is
@@OK closed-controller-installed.

## Outcome and uncertain ownership

RootVerbs now serializes its actual current-shell claim so programmatic setup
cannot overwrite or cancel another UI root owner. Cancel does not target the
installer. The one installer invocation permanently retains its actual shell,
prefix, feed, result/error and progress. For this invocation only, RootShell
retains the process-attempt marker before ProcessBuilder and actual returned
Process/feed/helper Threads before start. Default legacy retention behavior is
unchanged; the first uncertain legacy shell is retained and disables this new
installer. No retry or public reset/drain getter is added.

FILE_ACKNOWLEDGED is derived only after complete actual combined feed, no feed
failure, exact prefix+native byte count, one fixed ACK, exit zero, and no
error/cancel/kill/refused/failed disposition. Setup independently checks its own
native-feed completion and the same strict result. Duplicate ACKs are rejected.
PipeClosed/throw-after-write, missing ACK/exit, timeout and unknown creation do
not become successful installation. The actual owner and uncertainty remain.

This is a file-commit observation only. Existing RootShell bounded waits/joins
do not prove all helper threads or descendants drained, and no text ACK grants
native custody. The service rechecks retirement after setup and then invokes
the genuine session factory, which must independently open/verify the fixed
image and capture its real socket peer/pidfd. No installed-file Boolean replaces
that source construction, and no host/security/guest admission is opened.

The full-only generated asset/build pins, service call-site placement, native
handler, focused Kotlin/shell tests, APK packaging and Android/native/device
acceptance have separate owners/evidence. Optional native build-property absence
leaves ordinary Full/Probe builds available but this reached setup unavailable.
No successful compilation, model result, APK or runtime claim is made here.
