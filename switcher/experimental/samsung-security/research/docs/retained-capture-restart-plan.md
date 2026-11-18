# Proposed framework restart for the capture diagnostic

This selects a concrete test mechanism for later review and fresh approval. It
has not been executed. No full reboot, fallback restart, process-name kill or
change to OneOS/root/SELinux policy is authorized by this document.

The proposed single control request is `setprop ctl.restart zygote`, through the
already authorized root ADB shell on the pinned existing server/transport. The
captured device configuration declares `service zygote` with app_process64,
`--zygote --start-system-server`. Fresh read-only properties identify ro.zygote
as zygote64 and that service as running. The exact RC is retained under
`firmware/retained-capture-preflight/20261106T035920132957Z-bb1aaa13839844bcab41f08f2934abb6/`,
SHA256 `55d71c63fcccb7b84664593f0bb1aebe7b54b07a04cea32b84427657b733debc`.

The control-property interpretation follows AOSP's
[property service](https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/property_service.cpp):
it authorizes ctl requests and passes the action and named service to init. The
[init control map](https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/init.cpp)
maps restart to that service's restart operation. In the reviewed
[service implementation](https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/service.cpp),
a running service is stopped and marked for restart; its onrestart commands run.
These upstream sources were read November 5, 2026 (Gitiles blob IDs
83e9a0da35c3ac14a9ed772bf419116135888ec3,
920b926dcd26f3dd8661e869168d552c5db7170e and
56300205d293d346627a20fe2158bf9992b5b023 respectively). They establish upstream
semantics, not byte equivalence with Samsung's installed init executable or
proof that the request is currently permitted.

This is a framework restart with wider effects than SystemUI. The actual RC's
onrestart list also invokes FUSE abort, wakes the screen/takes a wake lock and
restarts audio, camera, media, netd, wificond and perfmond, plus a running media
tuner. Apps will close and wireless ADB may disconnect. Existing zygote_next is
not separately controlled. No assurance of temporary-root survival or uninterrupted
connectivity is inferred from source configuration.

The same RC also declares a configurable critical window with target
`zygote-fatal`. The reviewed upstream implementation excludes a requested manual
restart from its critical-crash count, but Samsung's actual failure policy has
not been established here. Do not promise absence of automatic failure actions.

Before presenting the exact build for approval, verify the current ordinary
One UI/profile, init/zygote/SystemServer identities, observed RC hash, root and
Vector state, permitted own-file layout and readable main log channel. Record
boot identity and SystemServer start identity privately. The proposal must name
this command and its effects and request one fresh framework-restart approval
under parent AGENTS.md rule 2, alongside the exact rule 3 phone changes.

After approval, issue the request at most once. An error, disconnect or timeout
does not authorize issuing it again. Use bounded read-only observation to check
unchanged boot identity and a new SystemServer start identity, then inspect only
the diagnostic's fixed result codes. Denial, missing delivery, absent root or
uncertain completion ends the test as inconclusive. Never substitute a full
reboot, repeated restart, re-root, policy change or kill command. Cleanup may
remove only approved owned request files and disable the approved module; a
remaining process-lifetime hook is not unloaded by that cleanup.
