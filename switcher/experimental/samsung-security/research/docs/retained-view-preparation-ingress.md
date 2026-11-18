# Preparation action and retained host relay

The Full app adds an explicit **Prepare ColorOS** confirmation when the
guarded writer profile sets `oneos.retainedViewPreparation=true`. The Full
source defaults to off, and the app service also refuses a claim with the
flag off. The ordinary Switch implementation remains intact. The new action
selects no image and dispatches no legacy switch command.

The app binds its existing nonexported service and claims the exact local
Broker only after that service's original Startup received a successful OFFER
acknowledgment. One retained worker serializes calls to that Startup's host
Callback. A locally timed-out reply does not replay PREPARE. A single STOP can
wait behind an active call and survives expiration of its caller's wait.
If the UI guard declines before PREPARE, the app releases its binding without
sending STOP. Unavailable status can be sampled again without a mutation.

The host records the real synchronous OFFER sender's PID alongside the
captured UID and exact Broker/Offer. The original callback claim and validated
publication are separate so concurrent BEGIN completion cannot consume an
incomplete OFFER. The three app commands use the same Callback with strict
descriptor, version and empty input tail checks. PREPARE and STOP post a
distinct main continuation and retain the existing native owner. STATUS reads
that owner without requesting native work. Only actual local cleanup can
produce status 7. An expected process exit can race a buffered terminal reply,
so an active drain stays pending. Status 8 requires proof that preparation
could not reach native dispatch. A queued reply confirms receipt only.

## Verified on the PC

The four patches applied and reversed against the exact guarded writer and
host SDK source snapshots. The first isolated app compile rejected a Java
method reference because the selected SDK bootclasspath lacks its compiler
bootstrap method. Replacing it with an explicit Runnable passed the same
compiler profile. The final app and host emitted 18 and 47 classes in
separate SDK37 compiles. The Full Debug APK also built offline, passed
signature verification and contains the new app protocol, relay and UI DEX
classes. A separate Gradle task generated the same Full Debug BuildConfig
without the preparation property and verified the flag is false. D8 emitted
exactly the 47 host and shared definitions with the app and compiler-only
classes excluded.
[Evidence index](../inventory/retained-view-preparation-ingress.json)

The matching host APK preserves the five prior manifest and module metadata
payloads and contains the exact 47-definition DEX. Windows `zipalign` crashed
before signing. The preserved continuation aligned the stored entries with
reversible ZIP padding, then verified their raw offsets and the official v3
signature. An independent reader verified the public signature and APK content
digest and matched the app and host callback constants. The host uses a fresh
dedicated debug certificate with no update lineage to the older host APK.

The compiled host profile parser also accepted the current app's exact package,
version, signer and embedded-controller identity and rejected six malformed
inputs. This probe invoked only the parser and wrote no loadable profile.

The paired APKs are PC builds for preparation only. A fixed live stage,
protected lease, and Android Binder and cleanup observations remain open. The
saved installed OneOS release has a different signing certificate.
Private guest startup still needs the active APEX view, generated linker and
classpath outputs, process containment and the original Samsung security
authority. No phone or device acceptance follows from this build.

## Guarded chooser and safe return

The original guarded chooser offered the ordinary Switch action when its
operation reached a local terminal state. That included status 7, which
only observes local cleanup, and status 8, which rules out View Prepare
dispatch. The chooser's in-process attempt reference also starts empty
when the app process starts. None of those observations verifies physical
release of the preparation stage.

The [guarded chooser patch](../compat/handoff-view/app-view-guarded-chooser.patch)
removes the stock Switch shortcut and its callback from the opted-in
preparation chooser. Prepare, View status, Cancel and the existing status
dialog remain available. The ordinary app branch retains the original
`showStock` call and method. This change is limited to this chooser.
The archived chooser offered Switch in four of twelve tested states.
The patched chooser offered it in zero of twelve. The inert fixture
observed the dialog and invoked no launch or service action.
The patched Full Debug source passed the offline `:app:compileFullDebugKotlin`
task in a fresh source tree. The emitted chooser has no stock callback,
the ordinary stock method remains, and reversing the patch recovers the
two normalized input files. This build stops at Kotlin classes.
[Differential fixture](../out/retained-view-chooser-boundary/r-a242f9fe/receipt.json)
· [Full Debug Kotlin receipt](../out/retained-view-guarded-chooser-build/r-2795e9b6/receipt.json)

The held ColorOS input screen has no source-verified protected fallback
for an unavailable Samsung authority. The stock guest return app uses a
legacy watcher and return script that can replace the Samsung framework
generation. The retained preparation Stop only reports its own custody
and cleanup. A real retained return needs guest ingress cutoff, process
and native drain, and acknowledged display and input restoration to the
same Samsung generation.
[ColorOS readiness](coloros-readiness.md#required-coherent-ownership-still-unassembled)
· [Retained return requirements](retained-process-lifetime-plan.md)

The [saved role comparison](../tools/review_saved_retained_host_samples.py)
checks two pinned historical observations offline. Both earlier stat endpoints
agree with the later PID, command, parent and start ticks for all three roles:
Samsung `system_server`, its primary `zygote`, and the separate `zygote_next`.
The earlier capture brackets its own boot ID. The later sample lacks a boot ID
or an open process handle spanning the two observations. This supplies
historical corroboration with no safe-return credit. The saved Stage Stop V2
capture tracks the preparation controller and child, with only a numeric
Samsung SystemServer PID in the tester row. Neither comparison establishes
guest drain or restoration of display and input to the original host.
