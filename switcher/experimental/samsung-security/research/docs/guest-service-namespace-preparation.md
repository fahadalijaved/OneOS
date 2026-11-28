# Guest ServiceManager integration preparation

**Source/API proposal only; no Java helper, DEX patch, native owner or runtime
namespace was emitted.** The [preparation inventory](../inventory/guest-service-namespace-preparation.json)
reuses exact staged framework `5cb16a37…` evidence: all 19 selected ServiceManager
declarations (including constructors and the native declaration), 17 generated
IServiceManager transactions, and 65 bounded method proofs in total. It checks
saved bytes only. The [prior namespace proof](retained-service-namespace-proof.md)
remains frozen and supplies body/receipt provenance, not a working namespace.

## Proposed production seam

Use the same kernel Binder context and original manager transport. Pair one
actual **in-process** native BackendUnifiedServiceManager route owner with a
small helper visible to the original guest boot classes. The frozen paired
[native source proof](guest-native-service-manager.md) joins both the Java native
manager and defaultServiceManager/native wait at this backend; merely replacing
the C++ default manager misses the Java getter. It places the adapter at the
physical os::IServiceManager argument to unified construction, before use;
the original outer unified cache retains logical keys. That native proof is
a separate peer scope, not a Java proof or an implemented owner. This preparation
pins its final inventory `236e1bc9…` and freeze `abe7aff8…` without rerunning it.

Keep original ServiceManagerNative.asInterface, ServiceManagerProxy and the
generated IServiceManager proxy. Do not install a Java decorator or a separate
Binder broker. The original getService2-to-checkService2 behavior, synchronous
transaction flags0, typed results, RemoteException paths and caller payloads
remain. The native owner performs the sole request/result name translation,
before its own caches and wait/notification operations. Java keeps logical names
and must not apply a second forward translation.

Proposed package-private boot helper, **not implemented**:

```text
Landroid/os/GuestServiceNamespace;
  static requireLogicalName(Ljava/lang/String;)V
  static coldSeed(Ljava/util/Map;)Ljava/util/Map;
  static logicalNotificationName(Ljava/lang/String;)Ljava/lang/String;
```

`requireLogicalName` must consult the actual same installed native route owner;
an unavailable owner or unknown logical name refuses. It accepts no ready flag,
caller role, UID grant, arbitrary route Map or setter. The root-selected fixed
route profile and original publisher/protocol owners are prerequisites. A name
prefix or immutable profile hash does not authenticate a service or authorize
credential use. Helper/JNI binding, boot visibility and same-owner linkage still
need a concrete source/emission contract before implementation.

## Exact Java edits proposed for root selection

| Original method | Exact saved boundary and proposed edit |
| --- | --- |
| ServiceManager.getService(String) | Insert requireLogicalName before original sCache access0/Map.get2. Keep logical cache key, hit return10, raw miss11 and original exception behavior for admitted names. |
| ServiceManager.checkService(String) | Same validation before cache0/2; preserve original hit10 and genuine delegate miss15. |
| ServiceManager.waitForService(String) | Validate logical name before native wait0; retain original JNI/allowBlocking. Native owner maps once. Replacing only sServiceManager would miss this path. |
| ServiceManager.initServiceCache(Map) | Keep original size/IF_NEZ check2/6 and existing nonempty-cache exception. Before original putAll10, coldSeed produces an owned empty Map instead of importing supplied Binder seeds. |
| IServiceCallback.Stub.onTransact | Recipient variant: after original enforceNoDataAvail29, before onRegistration32, inverse only the decoded name register. Preserve original readString21, readStrongBinder25, Binder argument, callback object, dispatch and oneway protocol. |

These are five prospective modified method bodies; no rewrite has been approved
or attempted. getServiceOrThrow continues to use getService. waitForDeclaredService
continues genuine isDeclared then wait. All addService overloads still converge
on the original four-argument delegate. Lists, debug and declaration queries
remain typed original calls with the native owner's exact result projection.
There is no separate Java findService declaration in the 19 selected records;
do not invent a Java hook for native find/check/cache behavior. That coverage
belongs to the actual paired native call graph.
The inventory also marks getIServiceManager creation15 and ActivityThread seed
call49 as **unchanged integration boundaries**, not extra patch targets.

Cold empty-seed is the smallest proposed policy that avoids renaming a host
Binder into a guest cache. Preserve null input failure; do not silently turn a
null Map into successful initialization. No live cache is cleared or migrated.
The original empty-cache test is not proof of one initialization or a current
generation: an empty seed leaves it empty and the original test can permit a
later empty initialization. Actual cold process/route-owner lifetime must come
from the native/bootstrap owner. Every required discarded seeded endpoint must
be genuinely resolvable from the selected manager before app startup. If a
required seed is not, this profile is unavailable; no fabricated fallback or
name-based Binder identity comparison repairs it. Selective seed optimization
needs a separately proved real Map producer and retained endpoint identity.

## Callback identity and restart

Registration should pass the **same original callback Binder**. A wrapper that
receives a manager callback and forwards to an arbitrary remote callback adds a
transaction and changes the final receiver's kernel caller identity. Native
code, lack of clearCallingIdentity and lack of a worker do not remove that
problem. Therefore the paired proposal now prefers inverse mapping at original
recipient entry points: Java Stub and the selected original C++/NDK receivers.
Each calls the same immutable native mapping owner exactly once; no forwarding
wrapper is needed. Build owns the actual C++/NDK recipient source proof.

Direct-local/manual/custom/remote recipients outside those admitted entry points
remain a selection blocker. The decoded name is naming data, not permission to
trust the callback Binder. The original manager, service Binder, callback and
policy still govern. The native and Java owners must not both invert one event.
Original callback registration identity is preserved for any real removal;
there is no new wrapper identity to reconstruct on reconnect.

The captured ServiceManagerProxy explicitly throws RemoteException for
unregisterForNotifications, registerClientCallback and tryUnregisterService.
Preserve those failures. Generated transactions8/14/15 below it are not proof
of removal support or drain. A fixed process-lifetime route owner avoids live
profile replacement, but neither it nor service-name death automatically
acknowledges outstanding callbacks. Actual register-then-throw, death,
re-registration and process retirement ownership remains required. Reconnect
must resolve through the same installed policy; it cannot reuse a stale native
manager/cache or imported host handle.

## All 17 protocol routes, without permission fabrication

The inventory carries each exact request writer/result-reader/CREATOR sequence
and code1–17 from the original generated guest/host wire proof. Binder/Parcel,
payload Binder, flags and original direct calls stay canonical. No new
CallerContext, calling UID/PID, clear-identity call, worker or intermediary
Binder process is proposed.

Codes1–5 need one exact service-name mapping; code6 needs genuine list projection
with order/collision rules; code7 needs the recipient decision above. Codes9–13
must retain actual declaration/APEX/connection truth and query semantics:
interface, instance and APEX strings are not generic service-name prefixes.
An alias cannot manufacture VINTF declaration, APEX ownership or connection
address. Code16 needs source-supported typed debug-row projection, not a guessed
Parcelable copy. The native implementation must close these contracts before
calling its mapping complete.

Code17 is particularly explicit: actual checkServiceAccess transports
CallerContext followed by two String positions. Existing body evidence does
not establish both strings' semantic roles. Neither is rewritten here and no
permission is granted from a prefix or package/UID allowlist. An aliased code17
route stays blocked until its actual native argument semantics are established.
Original policy remains authoritative.

Finally, ServiceManagerProxy.asBinder exposes its original context Binder, and
ProcessState handle0 remains physical. Raw Binder transactions, foreign/native
clients and unadmitted caches can bypass a Java name gate. This is a cooperative
source integration seam, not hard isolation from privileged callers. Root must
select the complete native placement, publisher suppression, protocol/local
lifecycle and endpoint ownership before a runtime candidate. No binderfs split,
proxy daemon, running service, security acceptance or architecture pivot follows.

Recheck/prepare saved proposal metadata only:

```powershell
python tools/prepare_guest_service_namespace.py --output out/guest-service-namespace-preparation/recheck.json
```

No old auditor, extractor, compiler, writer, OEM class or phone tool is invoked.
