# Guest SystemServer fork capture

Status: reviewed PC SDK/D8 plus authored JVM models only, default OFF and unselected. The actual corrected build emitted three authored classes and a 6,872-byte DEX; 16 first-party model cases/249 checks passed against those unchanged classes. No original/OEM/native/Android execution, retarget emission, phone or Git action is included. Root's first SDK attempt compiled the declarations but failed production compilation because private observeZeroChild omitted the checked IOException declaration required by Process.openPidFd. That actual failure is retained; no D8 or models ran in that failed attempt. The corrected source adds only that private throws declaration, contained by the outer observer catch. Root separately ran the corrected compile/D8 and one bounded model workflow; this metadata update changed no source or artifact. The source-phase report/inventory/freeze are preserved before this successor.

`compat/boot/com/android/internal/os/PreparedGuestSystemServerFork.java` implements the two selected package-private forwarding methods. `invokeOriginalForkSystemServer(II[II[[IJJ)I` calls the original package-static `Zygote.forkSystemServer` exactly once before any observer work. Every argument and the actual integer return are preserved. Only its actual zero-result child attempts optional observation; parent/nonzero returns do not inspect the permit or acquire descriptors. An original Throwable never enters an observer catch.

`invokeOriginalZygoteInit(I[J[J[Ljava/lang/String;Ljava/lang/ClassLoader;)Ljava/lang/Runnable;` calls the original once and returns the identical original Runnable. Its finally contains only optional observation; all observation/cleanup faults are contained and cannot replace the original return or Throwable. A normal nonnull returned Runnable and the exact supplied nullable ClassLoader are retained only against the already captured zero child, same actual source thread and same self-process scalar. No original Runnable is wrapped or invoked by the helper. The original `invokeWith`/exec route never reaches this handoff and remains unselected.

There are no allocating field initializers, static observer locks, general preparation APIs, public getters, endpoint registrations, PID/fork-result/ready inputs, arbitrary backend callbacks or argument edits. The initial child record is source-thread confined. Its `failed` bit is sticky/volatile; a foreign-thread invocation can invalidate the record but cannot race a descriptor close with the source thread's open. Cross-thread consumption/publication is not implemented. Strong references do not prove a live native lease.

After the real zero result, the helper retains its private ChildRecord before descriptor acquisition. It then checks and retains exact defining-loader identity shared by both authored helpers and canonical Process/Zygote/ZygoteInit, records the actual source thread/self PID, retains a new GuestForkCapturePermit before its descriptor opens, and reads the fixed operator request. Only a successful exact permit can reach actual `Process.openPidFd(selfPid,0)`. That private scalar comes from `Process.myPid()` in this child, never a caller input. The returned FileDescriptor is assigned before null/valid/currentness checks. Genuine null or any fault makes observation unavailable, with no fake success, fallback or retry.

The default-OFF request is distinct from the host capture/bootstrap requests:

| Object | Exact contract |
| --- | --- |
| Directory | guest `Environment.getDataDirectory()` + `system/oneos-guest-system-server-fork-capture`; root:1000, 0750, directory |
| File | `request-v1`; root:1000, 0440, regular file, one link |
| Bytes | ASCII `CAPTURE_GUEST_SYSTEM_SERVER_FORK_V1\n`, exact length and EOF |

The package-private permit parser reuses the reviewed HostBootstrapPermit contour: bounded `O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK` opens, lstat/fstat object/metadata comparisons before and after a finite bounded read, exact marker and explicit EOF. It writes no file or metadata. No absent/malformed/denied request becomes enablement. This file grants capture only, never source identity, security authority or Android readiness. Actual mounted guest data view, future inode labels, read access and operator provisioning remain external; this source makes no device access claim.

Each descriptor returned by an open is retained in the owning record before fallible checks. Permit descriptors close in finally using actual `android.system.Os.close(FileDescriptor)`. A failed close denies the permit, preserves its descriptor object/attempted flag and never retries it. The child retains that permit object even when unavailable. A captured self pidfd closes only on the source thread after failure; its attempted flag is set before Os.close, and an uncertain close preserves the private record and is never blindly retried. There is no public close/control API or claimed global/native drain. A live linked record intentionally remains retained; later lifetime/consumer transfer is not this component's API. Process termination is the final descriptor owner.

The two intended future retargets remain exactly the previously reviewed proposal: inner static/range fork at actual staged ZygoteInit PC351 (nine words, three code units), and normal handleSystemServerProcess zygoteInit call PC208 (five words, three code units). No DEX retarget has been emitted here. Equal width is not a DEX-preservation proof. Source/BOOT preload and dependency resolution must be admitted before either original callsite is changed: linkage failures before wrapper entry cannot be contained by the wrapper. Textual package identity in services-C is insufficient.

Compiler-only declarations are NEW under `compat/compile-only/guest-system-server-fork/`: actual package-static Zygote fork ABI, actual public ZygoteInit handoff ABI, and Process myPid/openPidFd ABI. A bounded ZIP-member string inspection found openPidFd absent from existing SDK37's Process.class and both internal classes absent from android.jar; no compiler was invoked. These are authored declarations, not runtime substitutes. A future producer must compile them separately as needed and exclude every declaration from program DEX/runtime model classpaths. The actual compiler and DEX closure is helper + private ChildRecord + permit: exactly three definitions. Three separately compiled ABI declarations stay excluded from DEX and model runtime; the corrected compile reused the exact preceding ABI bytes and did not recompile them.

This source implements only bootstrap occurrence observation. It neither proves SystemServer main completion nor issues a retained host binding or actual BinderProxy subject. Real host issuer/currentness/per-call retirement and cross-process delivery remain separate. Native pidfd support, actual loaded native cohort, future successful request access and descriptor cleanup behavior are unexecuted. The first source incorrectly assumed null BOOT loaders; exact beforeimages are preserved. Captured original ColorOS core-oj Class.getClassLoader returns null only for primitives; a null internal loader for a nonprimitive class selects BootClassLoader.getInstance. Its actual getInstance returns the shared singleton. The corrected code compares canonical loader identity and rechecks the retained identity at handoff; it does not infer code/source authority from loader equality. These donor core bodies do not establish an installed/loaded libcore cohort. The prior source/API proposal and peer proof remain immutable historical inputs; their exact paths and all new source pins are in the matching inventory/private source freeze.


The successful corrected SDK receipt is `out/gsf-build/r-51b2838a/receipt.json` (04597c345a1e2f306b2e31c7105ef6c67236c061aa3927251e851c6d9e31725c). Its actual DEX is 8201cf71e010f674881b3dac7e71a7cef9d05f54a50e3cc6aef08042c4edc06c, 6,872 bytes. Immutable independent saved-byte proof 81164060bb7c2116cff21858e759032117a45e93c02fb66626db31f45228b941 verifies the three classes, exact forwarding ABI/calls, source snapshots, program/projection isolation and DEX integrity without replay. SDK37/D8's maximum-supported-API36 warning remains; this is not API37 runtime acceptance.

The actual model receipt is `out/guest-system-server-fork-tests/r-d07412bf/receipt.json` (2298afd8fb76ce7c55e83f99857e3179871d838539b2ee6c834395edefae4dfd), with immutable independent saved-output proof e858acac51eb15beb150cbef0473190a7fc8ada0f74888cb553cbc27da1b23e0. One -Xint workflow used the unchanged actual three SDK classes plus 14 authored framework fixture classes/one driver and JDK only; no android.jar/OEM/runtime ABI substitute executed. All 16 cases/249 checks passed. Production was not recompiled or byte-shaped at model time; private helper state was not inspected/reset, and no returned Runnable was invoked. The cases cover original return/Throwable/argument identity, OFF/parent branches and modeled permit/pidfd/error/close/cohort effects. Private record linkage is inferred from those source/observable consequences, not a direct inspection claim.

The model self descriptor is a real repository JDK FileInputStream FD. Process/Zygote and directory descriptors/stat are authored fixtures; fixture cleanup closes streams, not native pidfds or Android work. Neither these tests nor the saved-byte review prove a native fork/pidfd lease, actual BOOT/loaded cohort, authentication, host issuer, per-call retirement, Binder delivery or device approval. Retarget packaging is a separate unselected leaf; this source delivery does not select its bytes.

## Original SystemServer Runnable entry

The held guest framework calls the outer fork at `ZygoteInit.main` PC 455,
checks the returned Runnable at PC 459, and calls its original `run()` at
PC 461. The held `RuntimeInit` constructs that Runnable from the resolved
SystemServer main method and its original arguments. The selected run lies
within the original catch-all range. This is the source edge for observing
entry to the exact linked Runnable. [Held startup trace](../firmware/retained-pin-guest-delivery/20261106T172504447891Z-2725e0be0fbf49af929d0630c4088e0e/selected.jsonl)

The [staged source successor](../tools/compose_guest_system_server_runnable.py)
reserves the run entry once, with the original zero-child record, exact
Runnable, source thread, self PID, BOOT loader cohort and retained descriptor.
It checks local currentness again after reading the PID. The original
Runnable still runs once per invocation, with its original Throwable.
An admitted run retains its descriptor until the original stack returns or
throws. A nested observation can retire the record without closing the
descriptor while that admitted stack is active. The final source-thread
cleanup makes one close attempt and contains its own failure.

The SDK37 build and D8 emitted three definitions in a 7,444-byte DEX039
with SHA-256 `8df9055bdbae790ef686a8d7173c54394fd3428ba10f9a7c659cac07083018d1`.
The permit class matched its predecessor byte for byte. Six authored JVM
cases passed 68 checks, including nested entry, an original throw with
uncertain cleanup, and retirement during PID readback. The build keeps
the D8 API 37 warning. [Build and test receipt](../out/guest-system-server-runnable-build/r-d44385f8/receipt.json)

The previous 16-case fork and handoff fixture also passed all 249 checks
against the successor's three SDK classes, using the same saved fixture
bytecode. [Regression receipt](../out/guest-system-server-runnable-build/r-67291731/receipt.json)

This is a child-local entry observation. Connecting it to a verified running
guest still needs the original in-process service owners. The guest AMS
creates its own PID-map record with the same application Binder as its
retained ActivityThread. Its SystemServiceManager can also be compared with
the one published in guest LocalServices. A phase field alone cannot prove
completion of callbacks after its write. The staged observer remains
unselected and no startup callsite was edited for this successor.

## Staged Activity Manager registration

Static readback of the captured staged ColorOS services JAR `efb45f5f…`
matches the original donor on the selected `startBootstrapServices`,
`setSystemProcess` and `addPidLocked` bodies. The staged framework evidence
comes from `framework_patched.jar` `5cb16a37…`. The checks below apply to those
saved bytes. [Source evidence](../inventory/guest-ams-startup-source.json)

`SystemServer.run` stores the newly constructed `SystemServiceManager`, then
publishes that same field under its class key in `LocalServices` at PC 371.
Bootstrap passes the original manager to the AMS lifecycle and its setter.
Later code needs the actual current objects from the same guest process and
startup occurrence to verify these identities.

`AMS.setSystemProcess` attempts `activity` Binder publication at PC 5. The
staged `ServiceManager.addService` implementation catches `RemoteException`
and returns, so a normal caller return needs separate Binder publication
evidence. Later, AMS activates the self-PID record using `ApplicationThreadDeferred`
around the actual system `ActivityThread.mAppThread`. The PID map put occurs
before the remaining process-map callbacks, LRU and OOM work, and AppOps
registration. The wrapper stores the underlying thread and delegates `asBinder()`
to it. An equal application Binder can establish that linkage at observation
time. [Staged service publication proof](../inventory/retained-service-namespace-proof.json)

The original bootstrap path calls `setSystemProcess` at PC 738. PC 741 is its
normal continuation. The staged archive has one direct `Watchdog.init` caller,
at PC 758 on that path. It receives the AMS reloaded from the original
SystemServer field and writes `Watchdog.mActivity` at its first instruction.
The staged archive reference scan finds that one direct writer. This gives a
source-backed lower bound for a future observation of the same live startup
occurrence. Watchdog receiver registration and vendor callbacks still follow
the write. The live source generation, object identities and thread visibility
have yet to be established.

`SystemServiceManager.startBootPhase` stores its new phase before the serial
callbacks and before waiting on parallel callbacks. Credential and native
readiness require their own observations. In the staged default DevicePolicy
path, the constructor reads the guest `LockSettingsInternal` well before the
locked-boot broadcast, so that broadcast is too late to establish that the
first observed policy consumer received a correctly bound service.

Run `python -B tools/check_guest_ams_startup_source.py` to revalidate the pinned
source evidence. The result records static source facts only. Runtime observation
and device eligibility remain false.
