# Goal: shared Samsung security in OneOS ColorOS

Owner: Apple. Agreed delivery scope: November 5, 2026.

**Finished outcome:** genuine ColorOS lockscreen, Settings and app-authentication
screens use Samsung-controlled credentials, fingerprints and security policy.
A security change completed in either OS is the state accepted by the other.
Deliver a reviewable upstream OneOS contribution, then establish the evidence
needed for maintainers to release it for the validated device profile.

**Present state:** the stage-only run verified the isolated image and controller
on the initial phone. A later snapshot matched the controller and checked the
image length. Continuous custody, runtime preparation and shared-security
device acceptance are still open.
[Staging result and later snapshot](PHONE_TEST_DECISION.md)

## 1. What complete means

| User action | Required behavior in both OSes |
| --- | --- |
| Create a PIN in One UI | ColorOS accepts that PIN without setting up a second credential. |
| Create a PIN in ColorOS | One UI accepts it on return. Test this on its own genuinely credential-free baseline. |
| Change the PIN in One UI | The new PIN unlocks both; the earlier PIN fails ordinary unlock in both. |
| Change the PIN in native ColorOS Settings | The new PIN unlocks both after return; earlier PINs fail ordinary unlock. |
| Remove a credential under genuine policy | Both reflect the committed result and its legitimate biometric, storage and key effects. |
| Use an existing Samsung fingerprint | It works in ColorOS and One UI after genuine primary-authentication requirements; switching alone requires no enrollment reset. |
| Enroll or manage a fingerprint in either OS | Both show the authoritative enrollment and supported metadata and can use it. |
| Remove one or all fingerprints in either OS | Removed prints fail in both. Removing one preserves unrelated enrollments. |
| Confirm credentials or use app biometrics | Real caller, user, challenge, confirmation and key policies govern the result in both runtimes. |
| Switch, return or later cold boot | Current credentials, intended encrypted-data access and applicable app keys remain correct. Biometrics obey actual first-unlock policy. |

Samsung's genuine previous-credential recovery is a separate, explicitly mapped
policy path; it must never become an undocumented old-PIN ordinary unlock.
Credential/protector rotation and enrollment-related key invalidation can be
legitimate. Preserve intended policy, rather than promising every key or numeric
identifier remains unchanged.

The full matrix remains in [PLAN.md](PLAN.md#required-cross-os-acceptance-matrix)
and [security-requirements.json](inventory/security-requirements.json): PIN-01
through PIN-07, FP-01 through FP-05, APP-01, DATA-01, FAIL-01, RETURN-01, BOOT-01
and RELEASE-01. All 18 cases are pending device evidence.

Inventory every exposed security function: password/pattern, profiles and admin
policy, remote lock, recovery, additional factors, face authentication and OEM
security/RPMB consumers. Each needs a supported, safely unavailable or unresolved
status. Unresolved required behavior blocks completion; a limitation disclosure
does not turn broken PIN, fingerprint, app-key or recovery behavior into success.
Do not claim blanket Samsung/ColorOS feature compatibility from these tests.

## 2. First supported target and security claim

Start with Apple's captured Galaxy S26 Ultra SM-S948U1 profile: One UI 9,
Android 17/API 37, build `CP2A.260605.016.S948U1UES4BZIG`. The November 8
read-only refresh matched the Samsung framework and services hashes and
identified stock OneOS 0.4.59/code 85 and its 49-row stage manifest. The exact
installed APK and staged files are point observations. Retained live authority
and loaded guest code still need verification before a device candidate.
[Current installed profile](docs/installed-oneos-code-profile.md#current-0459--code-85-baseline)

The historical source investigation pins OneOS 0.4.55 at
`2a5f41043b4a69399cae058bad213cdef7408e88`. Original Samsung/ColorOS inputs are
identified by [the input ledger](inventory/inputs.json), with the parent capture
recorded in `../inventory/os-comparison.json`. The 0.4.57/code 74 APK and
staged JARs are the earlier baseline. The exact Git revision of the current
installed APK remains unassigned. Use the installed bytes to establish the
implementation, and rebase and audit an upstream candidate against a newly
pinned OneOS revision before submission.

Admit only an explicitly validated host, guest, patch and native-service profile.
Fail safely on mismatches. Other Samsung builds, devices, donor ROMs or Android
versions are separate compatibility work and require their own evidence. A
general adapter design may be reusable; broad support is not the first release
promise. Bootloader unlocking is not a prerequisite or an authorized action.

Apple chose **working shared-security functionality with documented existing
OneOS platform limitations**. Restoring global SELinux Enforcing behavior or
stock-equivalent overall security is not a prerequisite for this contribution.
Disclose the pinned OneOS permissive SELinux and relaxed privileged-permission
behavior, its implications, and the effective policy observed during tests.

The feature must nevertheless enforce its own caller/user/profile, operation,
challenge and authority-generation checks and preserve genuine Samsung lockout,
StrongAuth, additional-factor, biometric, storage and key policies. Unknown
authorization fails closed. Functioning authentication does not establish
isolation from privileged/root compromise, enforcing SELinux protection or a
security boundary between shared system UIDs. No fabricated authentication,
blanket signature bypass or permissive authorization default is acceptable.

## 3. Architecture and interfaces to establish

Apple's later November 5 direction is to **adapt the ColorOS side to Samsung's
working security APIs**. Remove optional OPPO-only integrations that have no
supported Samsung binding, including their UI entry points, registration,
background work and dependent callbacks. Record each removed feature and its
source-supported removal boundary. Preserve genuine ColorOS presentation for
supported behavior. Shared PIN/fingerprint lifecycle, actual authentication
policy, app-key and encrypted-storage behavior remain required; removing a
required security gate or reporting fake success cannot satisfy this direction.

Use **one logical Samsung authority, authoritative state and current writer**.
This is not PIN/hash replication, credential-database copying or a second guest
enrollment store. OneOS normally stops Samsung's Java framework, so an authority
cannot simply be assumed to survive the switch.

The first candidate is a coherent original Samsung security service family with
an exact guest-compatible typed interface. Prove actual constructors/factories,
startup replacement, private/canonical classes, resources, local services,
storage and native owners. Select a retained authority instead only if concrete
construction and handoff evidence supports it. Record the choice and reject an
incomplete closure before attempting a device candidate.

The implementation contract must cover:

- Typed credential and biometric dispatch, original caller identity across hops,
  exact user/profile mapping, real result/error/cancellation behavior and fresh
  challenges. Existing evidence includes incompatible Binder transaction codes;
  opaque forwarding of a matching interface name is invalid.
- Real Samsung Gatekeeper/Weaver, fingerprint, Keystore/KeyMint and vold
  ownership, including maintenance writes during initialization or verification.
  A successful-looking UI callback is not cryptographic acceptance.
- Resource/Context policy and native ColorOS policy/cache readiness before
  authentication can complete. Preserve original additional-factor gating.
- Exclusive mutation and handoff: stop ingress, drain actual operations and
  callbacks, reconcile uncertain outcomes, then transfer ownership. Lost replies
  can follow committed writes. No assumed atomic hardware rollback, blind retry
  or stale credential restore is permitted.
- Intended CE storage, user and app-UID/key namespaces for each runtime. Do not
  merge app databases or expose the whole host data tree to simulate sharing.
- Persistent default-off controls and a tested disable/return path. Disabling
  incompatible code must not expose a protected ColorOS session as unlocked
  swipe. Roll back code only in a way that preserves the latest credential and
  authoritative native state.

Use bounded, protected, non-secret diagnostics. Users enter credentials directly
on-device. Never log or copy plaintext credentials, synthetic passwords,
authentication tokens or private keys into PC artifacts or synchronization
storage. Cache verified metadata away from event paths, bound callback lifetimes
and queues, and measure startup, authentication latency, idle CPU/memory and
thermal behavior against matched baselines before claiming performance parity.

## 4. Milestones from the current investigation

The detailed engineering sequence is [PLAN.md](PLAN.md). These are completion
gates, not calendar promises. Stop after an accepted device milestone for Apple's
test and feedback; don't turn approval for one build into approval for another.

| Stage | Concrete deliverable | Gate to advance | Current status |
| --- | --- | --- | --- |
| 0. Exact baseline | Host/guest/native profile, security-surface inventory and recovery baseline | Original source, patch intent and installed bytes distinguished; missing live facts recorded | Installed APK and staged code identified; isolated carrier verified; loaded guest/native closure open |
| 1. Authority and ownership | Version-pinned executable construction, dispatch, resource, state and handoff design | All real owners selected; unknown bindings remain blocked; one-writer and uncertain-write recovery reviewed | Isolated stage observed; continuous custody, runtime authority and handoff remain open |
| 2. Default-off candidate | Reproducible systemless implementation with compatibility admission, diagnostics and safe recovery | Offline provenance, build/link/resource checks and meaningful negative/failure models pass; exact device proposal prepared | Isolated stage provisioned; Prepare and Stop and full integration remain open |
| 3. Existing PIN | Native ColorOS keypad uses the real existing Samsung credential | Correct/wrong PIN, actual policy, protected operation and safe One UI return verified | No device acceptance |
| 4. Existing fingerprints | Native ColorOS and app authentication use original Samsung enrollments | Fresh authentication-bound key operation, primary-auth policy, cancellation and return verified | No device acceptance |
| 5. PIN lifecycle | Creation, changes and removal initiated in either OS | Separate NONE baselines, both change directions, old-PIN ordinary rejection, key/data effects and roundtrips verified | No device acceptance |
| 6. Fingerprint lifecycle | Enrollment, supported management, remove-one/remove-all in either OS | Both see committed state; real authenticator/key policies and unrelated enrollment preservation verified | No device acceptance |
| 7. Upstream delivery and release evidence | Reviewable PR package plus independently tracked beta-readiness evidence | Apply the separate PR and beta gates below; maintainers own rollout | Both gates open |

Parallelize closed, disjoint work on startup, state/keys, protocol/trust/resources,
ColorOS frontend, PIN lifecycle, fingerprint lifecycle, build integration and
independent verification. Root owns common APIs, architecture, integration,
evidence and local Git. Sol is the default; Astra requires a concrete unresolved
Sol attempt. Preserve the existing source audits rather than repeating broad
firmware extraction. Do not estimate percent complete from method or test counts.
Re-estimate delivery after actual construction and device gates; no credible
whole-project completion date is established.

## 5. PR-ready contribution versus beta-release-ready feature

### PR-ready handoff to OneOS

Apple will submit the PR. Preparing the contribution does not authorize a remote,
push, publication, message to maintainers or change to the installed OneOS app.
The handoff requires:

- Reviewable implementation of the declared required behavior for the exact
  initial profile, reproducible build/provisioning steps, dependency and artifact
  manifests, compatibility admission and a reviewed state/ownership design.
- Authored integration code, local provisioning tools, tests, documentation and
  profile/hash metadata suitable for upstream review. Obtain proprietary inputs
  locally from the user's matching firmware/device; keep OEM archives, native
  binaries, decompiled implementations and generated payloads out of public Git
  and the PR. No credential/enrollment material or personal identifiers belong
  in the contribution or shared evidence.
- Passing offline checks and separately approved normal-flow device evidence for
  the claimed behavior: bidirectional PIN and fingerprint lifecycles, app/key/CE
  behavior, switch/return and performance. A claim without evidence remains
  explicitly unverified; code or planning alone is not a feature-ready PR.
- Exact known limitations, recovery/disable and update instructions, supported
  profile, test/evidence matrix and draft PR description. List outstanding
  controlled fault tests and cold-boot work as pending where applicable.

A research/draft PR may seek help earlier, but must be labeled research/draft,
not the completed feature. The user decides whether to submit it. Upstream
review, merge, release timing, beta channels and invitations belong to the OneOS
maintainers; their participation has not been secured or presumed.

### Beta-release-ready evidence

The required normal-flow matrix must pass on the declared profile. In addition,
controlled testers supplied by the OneOS team must demonstrate interruption and
recovery at actual credential-write, enrollment/removal, cleanup, callback and
handoff boundaries, including service/HAL death, uncertain completion and stale
generation rejection. Verify the current credential, authoritative enrollments,
intended data/keys and safe return after each relevant outcome. No conflicting
writer, false success, silent enrollment loss or stale state restoration passes.

Apple chose the current phone for separately approved normal-flow tests. Do not
deliberately interrupt credential writes, inject faults, force reboots or run
destructive recovery experiments on that primary phone. Plan controlled fault
tests for suitable upstream test devices with a matching validated stack;
without that evidence, beta readiness remains open. Upstream may define a
restricted testing channel, but that does not itself satisfy this release gate.

BOOT-01 requires later, explicitly agreed user-controlled cold-boot testing with
manual root restoration. Normal-use acceptance also requires measured budgets,
repeated switch/return results, accurate limitation disclosures and maintainer
review of the evidence and release decision. Privacy-sanitized reproduction and
issue-reporting instructions must accompany the contribution. New profiles or
updates require renewed admission and relevant regression tests.

## 6. Tracking, permission and completion

[TASKS.md](TASKS.md) tracks work. The requirements ledger records per-case
evidence; it must distinguish static/source, authored-model, build, normal-device,
controlled-fault and maintainer acceptance. No case becomes passed because this
goal was written or a checkpoint hash verifies.

Planning and PC work grant no phone installation, activation, settings,
credential/enrollment changes or framework restart. Prepare the exact artifact,
actions and recovery proposal before requesting the applicable approval.
Existing OneOS-owned phone files/data remain untouched; any needed exception
requires explicit concrete approval or a separately owned systemless test layout.
Never flash, write raw partitions, automate root or reboot the phone. Later
user-controlled cold-boot acceptance is not agent reboot permission.

This goal governs the nested Samsung-security project. The parent ColorGlass
bridge and its active goal remain paused. The project is **PR-ready** only when
the PR handoff criteria are met; **beta-release-ready** only when the additional
required evidence and maintainer acceptance exist. Neither status is achieved
today. The immediate engineering deliverable remains Stage 1's complete
construction/authority/handoff design.
