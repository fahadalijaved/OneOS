# Separate preparation stage for a future coexistence test

The full debug OneOS build uses the installed release's package name and a
different certificate. A preparation companion with its own app identity can
preserve the installed app, provided its controller and all fixed preparation
inputs use a separately owned stage. The stock release uses the original stage
and does not participate in this lease. A separate stage still needs a test
window without concurrent stock switch or return operations.

The source changes select `/data/local/tmp/oneos-viewprep` and
`/dev/oneos-retained-viewprep` for both adoption and re-open. The child-private
root, data and mirror retain their original meaning. Clang rejected four
string-pointer expressions under `-Werror`. Array indexing corrected those
expressions without changing the paths or warning policy. The corrected
static ARM64 controller compiled and was inspected offline. The isolated app
relay requires the exact preprovisioned controller at the sibling path and
does not invoke the old stock-stage installer. This controller is separate
from the controller already packaged in the Full app.

The companion uses `com.fahadali.oneos.viewprep` with one launcher and the
existing nonexported V2 service. Only an explicit confirmation begins the
local binding. Java and D8 compiled the exact preparation code into 30 DEX
definitions. The first AAPT2 attempt crashed while writing a ZIP. The source
and DEX were retained. A manifest-only directory link then passed and its
binary XML confirms version code 1 and SDK 37. The signed app APK contains
only the linked manifest, resource table and DEX. Independent readback
verified its v3 signature and matched the app and host protocol constants.
The real host parser accepted the app's exact package, signer and APK hash
with the separately built controller. This was a PC syntax check.

The PC stage plan specifies eleven independently owned target objects. A full
read of the held 14,669,168,640-byte image reproduced the saved SHA-256. The
bounded ext4 inspection confirmed the required data, mirror and empty device
directories. The target's identity sidecar still depends on the actual copied
image's stat tuple. The readback checker matched a synthetic sibling snapshot,
rejected ten altered snapshots, and refused the historical stock snapshot.
Live lease and target content verification remain open.

The isolated controller also has a compiled successor that stops admitting
the first Prepare two minutes after host commit. It caps pre-Prepare frames
without changing the drain after a preparation attempt. Expiry takes the
existing controller cleanup path. The host still has to observe the actual
exit and its own resource cleanup. The successor passed the PC identity check
with the signed companion and host, and has no selected device profile.

An approved smoke would still need actual stage objects, loop and lease
custody, matching app identity, and cleanup evidence. The active drain can
reach kernel-release-unconfirmed after partial preparation. A loop clear
request or a status failure during rundown cannot prove final release. The
same-disk observation audit does not authorize removing the reservation.
The detached-sample parser passed 178 inert cases and compiled for ARM64.
It checks the sequence brackets and accepts only a narrow old-attachment
observation when its caller already owns the identity and complete reads.
Explicit loop creation and later numeric removal also require exclusion
across both index-reuse windows. A separate UI patch suppresses a stale Stop
after terminal status is observed by the worker. It remains outside the
signed companion.

The guest input verifiers staged four APEX module candidates and a classpath
subset of five fragments and 29 JARs. Follow-up checks identified the exact
tethering and Wi-Fi Java providers and modeled the held donor's SDK filtering
and wildcard ordering. The selected module view, generated linker and
classpath outputs, process writer confinement, and Samsung security authority
remain open. [Evidence index](../inventory/retained-view-isolated-stage.json)
