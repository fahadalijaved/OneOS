# Retained PIN guest delivery: real SystemServer fork occurrence

Status: source/API proposal only, unselected. No production source, DEX, native helper, launcher, device or Git change was made. This proposal records a bootstrap process occurrence; it grants no authentication or LockSettings authority.

The smallest useful next component is a BOOT-visible, source-selected forwarding helper at the actual SystemServer fork and normal SystemServer Runnable handoff. Creating a self pidfd in the actual zero-result child avoids an invented descriptor-inheritance channel through the packaged launcher or zygote fork sanitizer. The preparer's existing owned child is insufficient: its later zygote SystemServer child is a different occurrence.

The inspected Java archive is the actual acquired staged `framework_patched.jar`, SHA256 `5cb16a378d41301c2d41d4653f7dc63c54b732516353f331f0316e2c237f6246`. Its acquisition does not establish which image is currently loaded. The native JNI read is from the separately captured original ColorOS donor `libandroid_runtime.so`, SHA256 `edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279`; a matching staged/loaded native cohort remains unproved.

## Exact original source seams

In `classes5.dex`, private static `ZygoteInit.forkSystemServer(String,String,ZygoteServer):Runnable` calls package-static `Zygote.forkSystemServer(II[II[[IJJ)I` at PC351, a three-code-unit static/range invocation of nine words, registers v8 through v16. PC354 obtains its actual integer result. PC356 branches on nonzero to the original null return at PC375/376. Only zero continues through the existing second-zygote wait, closes the actual ZygoteServer socket at PC367, invokes `handleSystemServerProcess` at PC370 and returns its actual Runnable at PC374. Existing argument/capability catches and all original calls stay original.

The called `Zygote.forkSystemServer` runs `ZygoteHooks.preFork` at PC0, the actual native fork at PC3, sets the current thread priority after the returned result, calls `postForkCommon` at PC15 and returns that result at PC18. A forwarding wrapper must invoke this whole original method exactly once. It must not reproduce the fork, accept its result from a caller, or surround it with an observation monitor.

In `handleSystemServerProcess`, a nonnull `mInvokeWith` selects `WrapperInit.execApplication` at PC176. That path is unselected for the proposed record and does not pass the normal handoff. The normal branch obtains the actual cached/created SystemServer ClassLoader at PC187, conditionally installs it as the current thread context loader at PC197, and calls `ZygoteInit.zygoteInit(I[J[J[Ljava/lang/String;Ljava/lang/ClassLoader;)Ljava/lang/Runnable;` at PC208. This is three code units and five argument words, registers `[v1,v3,v4,v5,v0]`. PC211/212 returns the same result. Nullable original loader/result semantics are preserved; a missing optional record is never replaced with an invented runnable or loader.

The actual `zygoteInit` performs its original log/common/native initialization, then `RuntimeInit.applicationInit` at PC16. `applicationInit` passes the actual parsed startClass/startArgs and supplied loader to `findStaticMain` at PC41. `findStaticMain` calls `Class.forName(startClass,false,loader)` at PC1, resolves and validates the real public static main, and creates the original MethodAndArgsCaller at PC37/39. Original `ZygoteInit.main` calls the outer fork method at PC455, receives that same Runnable at PC458, tests it at PC459, and invokes its `run()` at PC461. The source links the actual returned handoff to the original run site; the proposed record does not claim the run has completed or initialized LockSettings.

## Self pidfd ABI and ownership

Actual staged `android.os.Process` declares public static `openPidFd(int,int):FileDescriptor`, public static final `myPid():int`, public static `supportsPidFd():boolean`, and private static native `nativePidFdOpen(int,int):int` in `classes3.dex`.

`myPid` calls the actual `Os.getpid`. `openPidFd` returns genuine null if the cached support probe reports unsupported; it rejects nonzero flags, creates a FileDescriptor, invokes `nativePidFdOpen(pid,flags)`, assigns the returned raw descriptor with `setInt$`, and returns it. An ErrnoException becomes an IOException with the cause. The support probe attempts IoUtils.closeQuietly on its own probe descriptor and caches false only for ENOSYS; another errno still caches supported. Therefore support=true is not an owned pidfd or permission/readiness proof. The wrapper must use the actual returned descriptor and cannot substitute a scalar or fabricated success.

The donor JNI method table binds `nativePidFdOpen` with signature `(II)I` to address 2336664. The selected 76-byte function passes the JNI pid/flags arguments to `pidfd_open`, returns the successful raw descriptor without dup/close, or obtains errno and throws the JNI error. Java owns the descriptor after its FileDescriptor adoption. The captured native request is not a kernel execution test or a matching-loaded-library assertion. No descriptor is acquired before the fork. The inspected Java normal handoff contains no explicit exec invocation; nativeZygoteInit and downstream native exec absence were not proved. FD_CLOEXEC behavior was not observed on a running kernel and is not used as evidence of delivery.

## Proposed typed component, before implementation

Proposed package-private BOOT helper: `com.android.internal.os.PreparedGuestSystemServerFork`. Its only source-entry methods are:

```java
static int invokeOriginalForkSystemServer(
    int uid, int gid, int[] gids, int runtimeFlags, int[][] rlimits,
    long permittedCapabilities, long effectiveCapabilities);

static Runnable invokeOriginalZygoteInit(
    int targetSdk, long[] disabledChanges, long[] enabledChanges,
    String[] argv, ClassLoader actualLoader);
```

The first descriptor remains `(II[II[[IJJ)I`; the second remains `(I[J[J[Ljava/lang/String;Ljava/lang/ClassLoader;)Ljava/lang/Runnable;`. The uid/gid and other original inputs are forwarded, not interpreted as admission. There is no PID, fork-result, ready flag, arbitrary backend getter or configured source callback parameter. The private record has no public/raw backend or pidfd export API.

The first entry invokes the original Zygote method exactly once. Nonzero returns unchanged with no pidfd acquisition. Original thrown objects escape unchanged; observation is outside that call's failure contour. Only the real zero-result child, after the original post-fork handling, may create its one private record on that same source thread, then call `Process.openPidFd(Process.myPid(),0)`. Allocate/adopt the record before the open; store a successfully returned FileDescriptor directly before fallible validation. Null, observation error, duplicate occurrence or failed linkage permanently prevents optional publication. Never retry the fork or manufacture an absent capture as success.

The second entry invokes original `ZygoteInit.zygoteInit` once. It returns the exact original Runnable object and preserves the exact original Throwable. After a normal result, contained observation may link only the already-owned zero-child record, same source thread/process, exact returned Runnable and exact supplied nullable ClassLoader. It neither wraps nor replaces that Runnable. A null or mismatched/duplicate handoff cannot become usable. No observation lock spans the original methods, class loading, JNI or future foreign metadata calls. A source-thread-only initial record avoids introducing a cross-fork inherited observation monitor; later cross-thread consumption requires its own reviewed publication/lifetime contract.

Suggested private states are `NO_RECORD -> CHILD_SELF_OWNED -> NORMAL_HANDOFF_LINKED`, with terminal `UNAVAILABLE`/close-uncertain disposition and no reset. The record and descriptor remain privately retained on uncertain cleanup. Closing must consume the one owned descriptor once and preserve a terminal uncertainty if close fails; process termination closes remaining owned descriptors. No unrelated resource or preparer-child drain is claimed by this local state. A source implementation must specify its exact close primitive and compiled hidden-API boundary before a build.

Wrapper class initialization/linkage itself precedes body entry and cannot be contained by a catch inside that body. Consequently the source hook must be selected only with a prepared, preloaded BOOT-visible helper closure, or remain an original no-edit call. This is an explicit producer/packaging obligation, not a claim that an unresolved static call preserves an original exception. `Zygote.forkSystemServer` is package-static: matching textual package in services-C is insufficient; the helper must share the actual BOOT runtime package/loader, or a separately reviewed access bridge is required. The existing services-C policy helper cohort does not satisfy that placement.

## Decision and remaining producer boundary

Root can select one finite implementation: the two forwarding methods and private self-process/Runnable record above, initially unselected/default disabled, plus separately reviewed exact two-call retargets. No inherited launcher control channel or second idle native child is needed for this occurrence producer. Retarget/profile preservation still needs actual full DEX/header/debug/try/pool proof when authored; equal instruction widths alone are not that proof.

The record establishes only that this source-selected fork actually returned zero and that the same process/thread reached the original normal SystemServer Runnable handoff. It is not SystemServer initialization, current physical security ownership, a host-issued binding, successful credential verification or ready Binder delivery. The later finite integration must bind a real retained host issuer/per-call retirement to this private occurrence and to the actual cross-process BinderProxy subject. A pidfd may be transferred as an FD under separately owned transport; SCM_RIGHTS is not a Binder-handle transfer. No such transport or authority issuance is implemented here.

The existing v3 owner still has seven filesystem capabilities and one preparer child, private empty `/dev` plus socket directory, CONFIG-only acknowledgement and CANCEL-only child loop. PARTIAL is parent-validated/adopted; there is no existing PARTIAL_ACK. The packaged launcher's FD closing and the unassembled runnable device/Binder/property/code profile remain external to this source proposal. They are prerequisites to enabled entry, not a reason to invent a ready boolean or postpone this bounded source component.

Evidence paths and hashes are recorded in `inventory/retained-pin-guest-delivery.json` and the private frozen manifest. The static readers executed only first-party parsing code. One native table-location attempt failed before raw output; its exact history is retained alongside the corrected bounded two-function read. No original Java/native method, compiler, launcher, kernel namespace operation or device action ran.
