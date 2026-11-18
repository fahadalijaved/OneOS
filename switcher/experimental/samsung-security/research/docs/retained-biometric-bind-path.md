# Retained Samsung biometric service bind path

This is a captured-source chain, not a running host ingress implementation.
The saved-data audit checks 36 exact bodies (31 newly selected, five reused),
61 call edges and the two whole-services direct callers of `bind()`. No OEM
code, Android process, phone operation or source patch ran. The result remains
unselected. Full descriptors, access flags, physical DEX/header locations, body
hashes and receipt/raw pins are in the [inventory](../inventory/retained-biometric-bind-path.json).
PCs below are decimal DEX code-unit offsets, not file offsets.

Inputs are original Samsung framework.jar `8095a9ae…` and services.jar
`def967fb…`. The framework's seven physical DEX files are ordinary 039; services
is the captured 041 container with logical headers 0 and 10057984. These are
original inputs, not proof of currently loaded host or staged guest behavior.

## Genuine origin and callback ownership

The manager constructor retains the supplied Context at PC71, Handler at 78 and
HandlerExecutor at 62. It constructs the bind-timeout lambda with classId4 at
40–41 and stores that exact runnable at 49. `bind()` calls its actual Context's
Executor overload at 57 with the manager itself as ServiceConnection. Its
explicit component is package `com.samsung.android.biometrics.app.setting`,
class `com.samsung.android.biometrics.app.setting.BiometricsUIService`; the
original flags are 603979777 (`0x24000001`). Neither the component nor those
flags authenticate an arbitrary caller.

The reused AuthSession constructor carries the actual token, request/operation,
user, original receiver and session owners, then invokes `openSession` at 241.
The reused SemFpSysUiImpl constructor supplies its genuine manager/context
dependency. `openSession` calls manager `bind()` at 120. These real source
objects are provenance; a copied tag or session integer is insufficient.

An exact whole-services scan finds **two** direct bind callers: that openSession
edge and SemFingerprintServiceExtImpl$$ExternalSyntheticLambda7.run at 28.
The latter obtains the manager singleton at 26, binds at 28 and submits its
original request runnable through `handleRequest` at 41. Its allocation,
scheduling, and enclosing legitimate operation were not traced here. It is not
proved session-free, unused, boot-only or a prewarm path. Requiring a nonempty
AuthSession list as the sole origin would therefore overclaim this evidence.
The historical private collection filename `prewarm-collection.json` is not a
semantic classification.

The actual retained Context's concrete runtime class/loader/user was not
observed. The captured ContextImpl branch below must be bound to the real
manager owner, including any ContextWrapper delegation; no dummy Context or
caller-supplied identity makes that association true.

## Finite normal and process-restart chain

| Exact original owner/method | Body-proved boundary |
| --- | --- |
| ContextImpl.bindService(Intent,int,Executor,ServiceConnection) | Unsigned flag conversion 0; actual Context `getUser` 5; common 14. |
| ContextImpl.bindServiceCommon | LoadedApk dispatcher 30; validate Intent 49; real AM service 90; application thread 96, op package 112, Context user identifier 116; IActivityManager.bindServiceInstance 123. |
| LoadedApk.getServiceDispatcher/Common | Executor wrapper 6; actual Context/ServiceConnection map and original dispatcher; validate context/handler/executor 64; IServiceConnection 67. |
| AMS public/internal bindServiceInstance | Public delegates 23; original isolated-caller check 14, package check 25, actual application ProcessRecord lookup 195; ActiveServices bind 327. Original early policy exits remain. |
| ActiveServices.bindServiceLocked | Actual Binder PID/UID 15/26; retrieve 530; real resolved record after 543; Freecess delay 553; identity clear 1039; bring-up 1628; bind requests 2056/2096; original identity restoration. |
| ActiveServices.retrieveServiceLocked | Real PackageManagerInternal.resolveService 775/1550; missing-result null branch; original exported/permission path and AMS.checkComponentPermission 2132. |
| ActiveServices.bringUpServiceLocked/Inner | Wrapper delegates 32. Existing process lookup 403 and realStart 465/581; missing-process ProcessList start request 887 or AMS start request 923. A null process result leads to bringDown 987 and error return. |
| AMS.startProcessLocked / ProcessList.startProcessLocked | AMS delegates 34; ProcessList creates real ProcessRecord 528 and requests actual process start 794. This stops before the lower start implementation; no fork/PID success claim. |
| ActiveServices.realStartServiceLocked | Genuine application thread scheduleCreateService 117; binding 151; failure/restart scheduling 400. |
| ActiveServices.requestServiceBindingLocked | Original IApplicationThread.Delegator.scheduleBindService 142. |
| ActiveServices.attachApplicationLocked | Actual matching pending ServiceRecord reaches realStart 150. |
| ActiveServices.scheduleServiceRestartLocked | Original restart/auto-create/stopped policy; performScheduleRestart 567. |
| ActiveServices.performScheduleRestartLocked / tryPerformScheduleRestartLocked | Delegate 135; original AnrTimer/callback handling and Handler.postAtTime(restarter,time) 31. |
| ActiveServices.ServiceRestarter.run / performServiceRestartLocked | Original monitored callback dispatch 18; real restarting/connection/client state leads to bringUp 155. |

ServiceRecord/HostingRecord and the original ConnectionRecord binding carry real
framework state. Their generic signatures do not attest a live biometric
session, and this audit does not prove that framework provenance is unused.
The delayed restart path needs the same admitted connection/record association;
a transient thread-local reason cannot alone cover its later Handler callback.
Original resolution, user mapping, caller/package/exported/permission, delay and
restart policy must continue to execute.

## Failure remains genuine

ContextImpl interprets negative AM results as SecurityException (throw152), zero
as false (133–134), positive as true; RemoteException is rethrown from the system
server at 155–159. Its unsupported null-PackageInfo helper branch was not opened
here, so this card does not assign that helper a guessed exception contract.

The manager does not consume the boolean returned by Context.bindService57:
the next instruction at 60 is a constant. Normal return, including false, sets
waiting and posts its real 3000ms timeout at 69. Its Exception handler calls
sendConnectionError(-2) at 102, which posts the original error runnable at 26.
The classId4 timeout selects the default lambda branch (switch keys only 0–3),
reports notifySysUiErrorEvent(0,2,2) at 17 and unbinds at 20. Error delivery walks
the original sessions and invokes SysUiListener.onError at 35.

onServiceConnected removes the exact timeout at 8, updates waiting/connected
fields at 12/15, decodes the genuine interface at 17, handles a null interface,
links death at 45 and posts original pending work. Disconnect reports the
original error and cleans up; binderDied posts onto the original Handler.
unBind calls the actual Context.unbindService at 54 and preserves original
cleanup/catches. Neither fake-connected state nor an invented successful
callback is a valid restriction response. A bind refusal/error is not proof of
complete UI recovery or authentication failure presentation.

## Smallest source-supported restriction boundary

A narrow protected-service admission proposal can correlate the **actual**
manager bind immediately before PC57 with its genuine dispatcher/connection,
then check the resolved service in ActiveServices after retrieve530 and the
non-null ServiceRecord branch, before later bring-up/process work. It must bind
to real Context, caller, user, endpoint, connection and current owner lifetime;
it must cover both observed origin families rather than accepting public
reason strings, booleans, UID membership or the package name alone. Keep the
correlation attached to the original record/binding through pending attach,
restart, death and genuine unbind. An authored correlator/admission owner and
this lifecycle association have **not** been implemented or proved.

That service boundary is a concrete next code location, not a complete
foreground-host restriction. Ordinary activity/task foreground restriction
belongs to separate ATMS admission; its exact activity entry bodies were not
audited here. Denying all host process creation at ProcessList would also deny
the source-proved legitimate missing/restarting biometric service. Freezing host
frameworks would stop required callbacks. Preserve this genuine service path
while separately owning ordinary foreground admission, display/input/power,
guest handoff and safe return. No full call-origin coverage, policy readiness,
authentication result or device acceptance follows from this card.

Recheck saved evidence only:

```powershell
python tools/audit_retained_biometric_bind_path.py --output out/retained-biometric-bind-path/recheck.json
```

The collector recovery note records a wrapper count-key error after two reader
jobs had already succeeded; their immutable receipts were reused without a
second query. The auditor reads those saved records and source hashes only.
