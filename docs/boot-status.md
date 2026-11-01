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
A compositor restart can still leave a short black gap; the renderer cannot draw
while no compositor exists or across a kernel reboot.

Run `python3 scripts/test-boot-status.py` for the event parser and cleanup tests.
Android emulator testing verified the isolated native entry layer; a full device
boot/return cycle is still needed. The device hub failed before final guest and
return UI verification.

The redesigned guest builds as `:guest:assembleDebug` (version 0.3). Official
host payloads still pin the original release-signed `OneOSGuest.apk`. Shipping
this guest in those payloads requires the existing OneOS release key and the
normal package hash updates. A debug guest must not replace that pinned artifact
or bypass its signature checks. Updating only the host does not update the
bundled guest APK or the phone's existing stage.
