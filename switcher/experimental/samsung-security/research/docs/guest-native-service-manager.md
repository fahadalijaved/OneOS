# Guest native ServiceManager: one shared backend placement

**Bounded source proof and integration proposal only.** No patch, library build,
OEM/native execution, Binder publication, namespace operation or phone action ran.
Original captured donor libbinder47100120, libbinder_ndk70ebb035 and runtimeedfd170c
are exact byte inputs; actual staged/loaded native cohort identity is unproved.
The old Java/native boundary report is [retained-service-namespace-proof.md](retained-service-namespace-proof.md).
Raw original code stays in ignored firmware/guest-native-service-manager/.

The implementable placement is a source-owned, guest-only in-process
os::IServiceManager adapter at the physical delegate argument passed into
BackendUnifiedServiceManager construction, before its cache begins use. The
[finite API proposal](../out/guest-native-service-manager/API-PROPOSAL.md) sets
out the exact next native integration contract. It is not a selected implementation.

## Actual captured edges

| Path | Exact captured native evidence (ELF virtual PCs) |
| --- | --- |
| Java wait bypass | runtime JNI wait calls defaultServiceManager at0x13a2e4, loads virtual slot0x40 at0x13a2f4, invokes at0x13a2fc; no Java cache/decorator on that path. |
| NDK wait/get/add/register | libbinder_ndk calls defaultServiceManager at0x1605c/0x16768/0x246b4/0x247e0 before its original virtual delegate calls. |
| Java native proxy | runtime getNativeServiceManager calls private impl helper at0x13a3b4. Helper body at binder0x99218 branches at0x9921c to getBackendUnifiedServiceManager0x887f0. |
| Default native manager | Its cold once callback calls the SAME backend getter at0x886e0, then creates CppBackendShim retaining that backend. |
| Incomplete alternative | setDefaultServiceManager shares default's once flag0xec340; callback sets its success byte only if it wins, otherwise actual __android_log_assert0x932f0. It neither replaces the separate unified once flag0xec288 nor Java private helper. |
| Physical context | ProcessState.getContextObject sets handle0 at0x6beec and calls getStrongProxyForHandle at0x6befc. Unified constructor lambda gets actual context0x6b14c, converts os::IServiceManager0x6b158 and constructs unified backend0x6b1ec. |
| Cache | Backend getService2/checkService2 call returnIfCached0x79ee8/0x799f0 BEFORE the physical delegate and later updateCache0x79ff0/0x79b28. Immutable cold mapping/lifetime must cover this cache, not merely uncached names. |
| Fork boundary | Actual childPostFork sets byte0xf8 at0x992b0 and closes driver0x992b4. This method body is not evidence that an arbitrary inherited adapter/cache is safe or that the required zygote call site has executed. |

Original CppBackendShim.waitForService contains a real registration waiter,
condition-variable waits, repeated checks and deferred unregister, not polling a
Java map. Its actual callback stores the original Binder and flushes commands;
NDK notification has its own local registration object and delete path. No new
fake notification, immediate-success wait, timeout-default, cached sentinel or
no-op removal is permitted. The saved raw code includes these paths, local
callback bodies, add/list/debug, physical cache paths and typed access method.

The selected proposal keeps original unified logical cache keys outside the
physical-name adapter. Both Java proxy and C++/NDK shim then use one immutable
profile. Java must gate before cache hits and native wait and admit a cold empty
app seed, preserving original getService2/checkService2 and error behavior. It
must not also prefix requests. Actual aliases still need genuine publishers and
physical ServiceManager/SELinux permissions; shared names remain physical.
Code17 CallerContext plus its two strings has not acquired semantic positional
proof here; do not rewrite both. Declaration/interface-instance/APEX and debug
metadata projections must be exact or remain selection blockers.

Callback inversion occurs exactly once at ORIGINAL selected receiver Stub/Bn
entries (Java Stub, Cpp RegistrationWaiter, NDK NotificationRegistration), with
the original callback Binder and real service Binder preserved. A generic native
forwarding wrapper can add an outgoing transaction to a remote original callback
and change kernel caller identity; same-thread/no-clearIdentity is insufficient.
Arbitrary remote receivers remain unclosed, not transparently wrapped. Original
registration/removal/death behavior and actual active-callback drain remain owed.

This is process-lifetime cold integration, no hot swap/unload. Source-selected
code must reach the guest native cohort before loading; do not initialize the
manager early in zygote merely to install policy. Actual first-use/fork/descendant
closure is still required. The adapter delegates in-process, does not become a
privileged service-method forwarding daemon, and makes no UID/PID authority claim.
Physical handle0 and exposed Java context Binder remain physical: this is manager
adaptation, not adversarial hard isolation. UDS/accessor/nondefault Binder contexts
are not silently included. No new Binder context/binderfs mechanism is justified
by these source paths.

Next concrete prerequisite is exact original platform-private C++ headers/ABI
for os::IServiceManager/Service/RefBase/libc++ and a reviewed original-libbindercode
insertion or relink producer. The current NDK compiler alone does not supply that
platform closure; declarations, guessed vtables or compiler stubs do not implement
it. The tool captured59 selected functions and verified87 bounded source/byte/edge
conditions. Those counts are audit scope, not runtime readiness or isolation.
