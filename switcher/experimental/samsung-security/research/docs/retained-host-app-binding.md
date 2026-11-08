# Captured host to closed app/root link

PreparedRetainedHostAppBinding is a package-private closed-control
association. It opens no credential owner, starts no guest and grants no
authentication or native-view authority. Source review passed, and Root's actual
SDK37 compile passed for the corrected source. This author ran no workflow;
Android/OEM, root/helper, network and device operation remain unexecuted.

Its prepare method requires the actual RetainedPinHostModule, retained Registry
and Family, and protected HostRootLinkProfile. The module's private boot-source
check compares its actual controller/captures; Registry.contextForControl supplies
the Context. There is no caller Context, supplied Binder/UID/source predicate,
public constructor, ready flag or arbitrary app selector. Root owns those shared
bridges and retains the returned binding before calling start.

All lifecycle methods remain package-private: start, checkStillBound and retire
run on the captured canonical main; ping runs off main and never hops to a main
capture check while holding an RPC. state is observational metadata only.
Main admission is fenced before foreign work. No owned monitor spans framework,
PM, Handler, Binder, thread, stream or cleanup calls.

## Genuine startup gates

The actual non-direct-boot-aware app service cannot be assumed available at boot
phase 1000. A separately owned ACTION_USER_UNLOCKED receiver is registered first,
with no package data scheme. Only a fresh real UserManager.isUserUnlocked(user0)
observation under source pre/post checks permits the first hash job. Broadcast
extras do not grant admission; there is no timer/poll or bind retry. Fresh unlock
and source checks precede the one actual bind as well. Unlock here permits app
startup, not authentication/physical-user/native readiness.

The worker obtains real PackageManager package UID/version/current signer and
installed sourceDir, requires a single current signer and single base APK, checks
the actual private service declaration, and hashes the same opened installed APK.
The FD and job/thread owners are retained before subsequent work. Hash bytes and
file length are bounded; no main-thread bulk hash occurs. Exact installed file
identity includes dev/inode/size/full mode/uid/gid/nlink and both timestamp seconds
and nanoseconds. Metadata is checked again after foreign work/callbacks. These
checks compare an actual installed package against policy; they are not loaded
memory attestation or an atomic package/source lease. Split APKs are unsupported.

An explicit ComponentName, actual ServiceConnection and the public
UserHandle.getUserHandleForUid(0) user-zero handle go through
the real Context.bindServiceAsUser. Original AMS/service permission and startup
behavior remains; neither UID1000 nor bind's Boolean alone is source permission
or successful startup. Protected profile absence remains disabled, and the older
capture permit alone does not request app action.

## Callback and control ownership

Connection/Broker and startup ownership are retained before BEGIN. BEGIN is claimed
before the synchronous transaction; unknown return does not mean no app/native
work occurred, and it is never retried. The genuine startup callback requires the
real derived package UID and exact token/version/flags/frame. Its actual Control
Binder is retained before the actual Handler post; QUEUED acknowledges that post,
not a linked state. The callback can precede BEGIN's return.

Only the source-owned main continuation can proceed after BEGIN's actual QUEUED
reply, source/capture/package rechecks and off-main validation of that same Control.
The validation invokes the actual closed PING, not a supplied readiness Boolean;
its explicit state must remain ADMISSION_CLOSED. Main rechecks actual currentness
before recording LINKED_CLOSED. This is a point-in-time closed transport fact,
not authentication, native completion or permission to start a guest.

Package replacement uses a separate package-scheme receiver. Connection loss,
binding death, source refusal or retirement stops local commands. Retire latches
the cutoff first, attempts only the exact owned unbind/unregister/death-recipient
cleanup, and requests close off main through the actual retained Control. A late
callback cannot link after retirement, but its received Control remains retained
for cutoff. Callback/reply/post/registration uncertainty is retained. Unbind,
unlink, REQUEST_CLOSE replies and Java frame counts are not native or queued-work
drain acknowledgments. No borrowed Samsung service is closed or destroyed.

Unknown Binder transactions preserve ordinary Binder behavior; owned client
Parcels are independently recycled once, and onTransact Parcels are borrowed.
No identity clearing, host root shell, security call, global ServiceManager name,
credential payload, native state mutation or fake success is introduced here.

## Actual compile scope

Root's first SDK attempt is retained at
out/closed-root-host-link-build/r-952ad00e/receipt.json. It failed on five uses of
the nonpublic UserHandle.of helper and one nonpublic profile flag. The narrow
reviewed correction uses public getUserHandleForUid(0) and the profile author's
public nonblocking open; no hidden-API projection workaround was added.

Root's successor receipt is
out/closed-root-host-link-build/r-eb2019cc/receipt.json, SHA256 d10896caec8081a647e0df37ea26db5b576b63c9f308e1b0ce650d579aea5dc9.
Its two javac commands exited zero and emitted 55 authored class definitions from
17 production sources. Fourteen definitions belong to this binding. The two
declaration-only widget ABI classes support existing PIN dependencies and are
excluded from production output. Java 8 source/target obsolescence warnings are
retained. No D8, Java program/model, Android, native/helper or device ran in that
workflow. The prepared 54-class model subset excludes only real Spawn; it is not
an executed-model result or a source-set/APK placement proof.

The full source gate is out/closed-root-host-link-review/SOURCE-PASS.json; its
SDK repair successor is PUBLIC-SDK-DELTA-PASS.json in that directory. These
private proofs and actual receipts are pinned one-way in the inventory; earlier
source/card versions and the failed compile remain preserved.

Root owns integration and first-party model execution. Fixtures must traverse the
actual module boot-source path and actual callback/control implementation, using
explicit Android/PM/process models; no private production-field access or fake
module can issue a link. The prototype still depends on the app Broker and does
not transfer native ownership, guarantee host survival/return or satisfy the
eighteen device outcomes. Runtime architecture and phone activation remain open.
