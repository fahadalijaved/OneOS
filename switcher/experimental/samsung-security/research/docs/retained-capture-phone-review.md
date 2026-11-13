# Retained capture v1: proposed phone diagnostic

**Proposal only. No permission requested or phone action performed here.** Root
must finish fresh read-only preflight, exact command/channel selection and final
review before asking Apple. This tests existing-object capture only: **0 of 18
full-goal gates**, no authentication, native/storage operation or OneOS switch.

## Exact artifact and action boundary

- Package `com.appleexploit.oneos.security.retainedcapture`, versionCode1,
  versionName `0.0.1-diagnostic`; **21,104 bytes**.
- APK SHA256 `bb0eba1047608b153d5a8f072ac334a496a42c32a19abf9fe3661a9dce766355`;
  [PC validation](../inventory/retained-capture-probe.json), receipt `95d8eb9e…`.
- Local certificate SHA256 `ad40f7c185abb46a5ba4798625e3245333987594379e5014aa0c977e69febfc9`;
  actual SDK verification v3=true/v1=false.
- Exact capture source `26fcbb30…`; no later capture/control API successor.
  Four authored DEX definitions, no OEM/SDK/model definitions.
- Vector API102, **only android / System Framework scope**, SystemServer callback;
  no SystemUI/other app scope. Default OFF while the dedicated request is absent.

## Preflight and fresh approval gates

Root must verify the same already trusted device on the existing ADB server,
ordinary OneUI rather than a ColorOS session, current root/Vector availability,
SDK37, SM-S948U1, DISPLAY `CP2A.260605.016.S948U1UES4BZIG` and the recorded
fingerprint/code-source profile. Property matches alone do not establish source
or authority. Record current SystemServer identity/boot identity, exact installed
module state and the new permit path's absence or verified ownership. Abort on
ambiguity or an unexpected existing package/file. Do not reset/re-root anything.

Two operational items remain **unselected**: the exact source/device-verified
normal framework-softrestart mechanism, and Vector's actual module-log channel.
The API declaration does not prove logcat-tag delivery. Root must select and pin
both before final permission; no ctl.restart/killall/manager CLI is guessed here.
Fresh preflight must also assess observed file contexts/access; actual
SystemServer permit readability and early callback delivery remain unproven.

[Parent AGENTS.md hard rules 2–3](../../AGENTS.md) require Apple's **fresh yes** for
this exact install, enable/scope, permit creation/removal and module-disable plan,
and **one normal framework soft restart**. Prior UniRoot auto-root OFF confirmation
is accepted; do not ask again or change it. Full reboot is forbidden. No second
restart, fallback, retry, root exploit, global policy/relabel or setting change
is included. Root alone presents the final permission question after readiness.

## Proposed single test, only after that approval

1. Install the exact APK and verify installed bytes/hash/certificate/version.
   Enable only this package in Vector with android/System Framework scope; keep
   its request absent. Do not alter other modules or accept an automatic restart.
2. Prepare only `/data/local/tmp/oneos-samsung-security-capture`, uid0/gid1000,
   exact0750, nonsymlink directory. Its sole request `request-v1` must be a
   nonsymlink regular uid0/gid1000 file, exact0440, link count1, exactly **25 ASCII
   bytes** `CAPTURE_USER_REGISTRY_V1\n` (one final newline). Verify metadata/content;
   never reuse an unreviewed path or touch `/data/local/tmp/oneos`/OneOS data.
   Root readback is not proof that the SystemServer SELinux domain can read it.
3. Start the selected bounded observation, then perform **exactly one** freshly
   approved normal framework soft restart. Verify changed SystemServer identity
   with unchanged boot identity. Do not full-reboot or automatically restart again.
4. In the verified module channel retain only tag `OneOSRetainedCapture` and the
   fixed codes `HOOK_INSTALLED`, `INSTALL_REFUSED`, `CAPTURE_BOUND`,
   `CAPTURE_REFUSED`; discard unknown text/raw Throwables/user/state logs.
   Source requires original normal phase1000 completion and actual main thread;
   its original call proceeds outside the diagnostic catch. Late delivery may
   install a hook after phase1000 and **never capture that boot**. Silence is
   inconclusive, not disabled/capture proof. Refusal/missing callback/read denial
   ends the test without replay, policy changes, polling or another restart.
5. Remove only the exact owned request and disable only this module in Vector,
   as covered by the fresh approval. Verify absence and disabled configuration;
   leave its package and empty owned directory unless removal is separately
   approved. Stop observation; report only bounded result codes/identity checks.

## Cleanup and meaning of a result

Removing the request prevents later capture admission, and disabling prevents
loading in a future process. **The existing pass-through hook and any retained
capture remain until that SystemServer process ends.** No active-stack unhook,
owner destruction or APK unload is claimed. A further restart to unload them
needs a new yes; it is not bundled into cleanup. If this limited cleanup is
unacceptable, do not run the one-restart proposal.

CAPTURE_BOUND means immediate source-checked object binding only. It does not
prove native/generation/lifetime ownership, preserved state, credentials,
fingerprints, CE/app keys, switch survival or full security readiness. Stop and
return to PC review on instability; never treat loss of ADB/root or a silent
module as successful recovery. No deliberate crash/fault test is included.
