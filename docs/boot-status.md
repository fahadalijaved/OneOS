# Boot and return handoff

Settings → Experimental → **Verbose boot**, beside VoLTE and camera fix,
controls live status on both entry into a guest and return to One UI. It is off
by default. `LaunchJob` passes a strict boolean to the root launcher, which writes
`ONEOS_VERBOSE_BOOT` only after its normal launch checks. The return reuses that
session's choice.

`GapSplashActivity` draws the OneOS icon/title before teardown. The guest's
`ReturnSplashActivity` posts its first frame before writing the existing return
request. The static launcher shortcut **Return to One UI** opens the same
confirmation as the app button and Quick Settings tile; cancelling writes no
request. Volume-key returns also get the root handoff layer.

The optional root renderer (`OneOSBootStatus.dex`, rebuilt with
`scripts/build-boot-status.sh`) uses a SurfaceControl layer independently of
ActivityManager. `boot_status.sh` watches actual Android event-buffer messages
and reports the session scripts' init service requests. Return teardown also
reports processes immediately before signalling them. These are observed events
and requested operations, not synthetic progress or guaranteed service readiness.

The status directory is `$STAGE/data/oneos_bootui` (guest: `/data/oneos_bootui`).
Entry and return use separate generation tokens. The supervisor reconnects when
the compositor changes and stops at the new framework's display-ready event or
boot animation completion, with a ten-minute upper bound. The original frozen
splash is retained when the live renderer is unavailable. Reboot fallback,
return keys, the return watchdog and stage/signature/hash checks are unchanged.
On return, the last splash frame is held before stopping ColorOS's framework,
with a return wakelock acquired before teardown. The vendor-composer hold has
an independent 180-second recovery guard and is released before One UI's
composer restarts, or before either reboot fallback. The interval without a
compositor is static; live events resume when One UI's compositor is available.
The renderer cannot draw across a kernel reboot.

Run `python3 scripts/test-boot-status.py` for the event parser and cleanup tests.
The owner verified both entry and return on the physical Fold8 with the
0.4.38 debug host/stage pair, including the retained return frame. That pair
also included the updated guest APK. This validates the tested Fold8/Find N6
path; the compositor-hold fallback is not verified on other devices. The
subsequent merge of upstream 0.4.37 has source/build checks recorded in the PR,
and has not been installed over that accepted device pair.

The redesigned guest builds as `:guest:assembleDebug` (version 0.4). Official
host payloads still pin the original release-signed `OneOSGuest.apk`. Shipping
this guest in those payloads requires the existing OneOS release key and the
normal package hash updates. A debug guest must not replace that pinned artifact
or bypass its signature checks. Updating only the host does not update the
bundled guest APK or the phone's existing stage.

Guest 0.4 also refreshes the return launcher shortcut when an existing staged
system app retains an older shortcut cache, and removes dividers from its
single-item cards. Release integration must sign/rebuild this guest and update
the package-set hashes before distributing the new guest UI.

For a local debug-only guest update trial, `-Poneos.testPackagesDir=<folder>`
selects an explicit copy of the package manifests. The local payload folders
carry the rebuilt guest and those manifests pin its exact SHA-256. Both the
compiled list pins and packaged asset lists use that copy; normal release
manifests stay unchanged. The build rejects this override for any Release task.
