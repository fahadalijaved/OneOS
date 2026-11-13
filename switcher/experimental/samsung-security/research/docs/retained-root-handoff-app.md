# Direct-host v2 app launch and offer relay

This separate source candidate implements the app side of the
[direct-host protocol](retained-root-handoff-protocol.md). It leaves the v1
service/session, installer and current OneOS app patch unchanged. Nothing here
opens credential, guest, filesystem or other security admission.

`RetainedRootHostServiceV2` accepts only synchronous version-2 BEGIN with an
actual Binder UID 1000 and positive calling PID on SDK 37. It captures that tuple
before scheduling; request fields cannot supply it. Strict interface, version
and trailing-data checks precede one retained process-wide startup. The callback
and death recipient are retained before registration or thread start. QUEUED
reports startup delivery only. It is not a source, process or authority receipt.

The private launch owner invokes its own `su` ProcessBuilder through
`RetainedRootOfferSpawn`. The fixed command verifies the opened root-owned image
`/data/local/tmp/oneos/bin/oneos_retained_root_handoff` against bounded build size
and SHA-256, then executes that same descriptor with `--host-control-v2`.
Directory/image checks are a build-selection contour, not an atomic namespace
lease or host attestation. This source neither installs that new image nor
reuses the v1 installer. Actual v2 packaging, staging and manifest publication
remain separate integration prerequisites.

Before fallible follow-up work the owner retains the actual Process, each pipe,
each pump and each thread. A marker precedes ProcessBuilder creation, preserving
uncertain partial birth even if no Process is returned. It writes the captured
host PID/UID in INIT and keeps stdin open. It validates the complete 64-byte
native OFFER, including its PID, exact 42-byte address and two zero tail bytes,
before retaining and relaying it to the original callback. The callback may
precede BEGIN's reply. There is at most one callback attempt and no replacement
spawn after refusal, timeout, lost reply or callback uncertainty.

The app has no LocalSocket, native PING/CLOSE, numeric signaling or Process
destroy path. Service destruction and callback death retire delivery only.
After a possible offer the host may have committed even if the callback reply
was lost. Native precommit timeout and the host's direct control connection own
that lifecycle; app retirement cannot independently cancel it.

Full-offer stdout EOF and empty stderr EOF are expected observations when native
disposes app stdio. The retained worker still reaps the actual Java child. Only
actual wrapper reap, returned reader starts, joined/finished readers, normal EOF
on both and a retained full offer permit one independent close attempt per local
stream. Each close disposition is consumed before the call; failure remains
uncertain without retry. Otherwise streams and workers remain retained. Wrapper
exit, pipe EOF and local close receipts do not establish native exit, host drain
or commit. Wait deadlines bound observation, not cancellation or worker lifetime.

Source reviews and future SDK/model evidence are distinct. No Android, root,
native or device workflow ran during this authoring. Real Binder/package/source
admission, native peer/pidfd/commit checks, self cgroup placement and root-manager
or switch kill behavior belong to their own owners. Own-session separation
alone proves no app-death survival. All reciprocal PIN/fingerprint/app-key/CE
requirements and device acceptance remain open.
