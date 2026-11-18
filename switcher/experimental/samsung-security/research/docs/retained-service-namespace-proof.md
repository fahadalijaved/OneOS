# Retained services: actual guest namespace boundary

**Source-supported conclusion:** the installed OneOS profile uses targeted
aliases and per-service proxies in a shared physical service environment. The
examined guest Java ServiceManager chain is not a complete guest namespace.
Replacing only `sCache` or `sServiceManager` cannot isolate the retained Samsung
endpoints. The next small implementable delimiter is a guest-only publication
reservation guard; a working namespace still needs the source cuts below.

This is a proposal, not a patch, live owner or architecture selection. Source
inputs are actual staged framework `5cb16a37â€¦`, staged services `efb45f5fâ€¦`,
Samsung framework `8095a9aeâ€¦` and the installed APK0.4.57/code74 scripts, bound
by the frozen [installed profile](installed-oneos-code-profile.md). Loaded guest
code and effective native driver/manager recipients remain unverified. The
[inventory](../inventory/retained-service-namespace-proof.json) pins every raw
receipt/body and script; raw OEM instructions remain under ignored firmware.

## Exact Java paths

| Operation | Actual staged source path and boundary |
| --- | --- |
| `getService(String)` / `checkService(String)` | `ServiceManager` reads `sCache` at PC0 and original-name `Map.get` at PC2, returning a hit at PC10. Misses reach `rawGetService` at11 or `IServiceManager.checkService2` at15. A proxy-only change misses existing cache hits. Remote errors still yield the original logged/null behavior; null cannot become security readiness. |
| Raw lookup | `rawGetService` invokes `IServiceManager.getService2` at12. `ServiceManagerProxy.getService2` then calls its own `checkService2` at0, which delegates unchanged name to `mServiceManager`. This wrapper behavior is distinct from the generated proxy's direct getService2 transaction2. |
| Manager acquisition | `getIServiceManager` obtains `BinderInternal.getContextObject` at7, `allowBlocking`11 and `ServiceManagerNative.asInterface`15, caching the interface at19. That factory constructs `ServiceManagerProxy`; its constructor stores the context Binder but separately obtains native `getNativeServiceManager` at6 and converts it at14. `asBinder` returns the stored context Binder. Native implementation/recipient identity is not inferred from these names. |
| Wait | `waitForService` calls **native** `waitForServiceNative` at0 and `allowBlocking`4; it bypasses both Java cache and `sServiceManager`. `waitForDeclaredService` checks `isDeclared`0 before wait6. Both Samsung and guest use this path. |
| Add | All three `ServiceManager.addService` overloads converge on `(String,IBinder,boolean,int)`, whose delegate is PC4. The actual staged `SystemService.publishBinderService` overloads forward the same name. No examined method applies a guest alias. |
| List/debug | `listServices` asks the delegate with dump flags15; `getServiceDebugInfo` directly delegates. Returned names are not projected to a guest view. A future logical view must resolve host-name/guest-alias collisions, preserve genuine identities and account for typed debug results. |
| Declaration/APEX/connection | `isDeclared`, `getDeclaredInstances`, `updatableViaApex`, `getUpdatableNames` and `getConnectionInfo` delegate unchanged arguments. An interface-instance query is not an arbitrary service-name prefix operation; no invented VINTF declaration is permissible. |
| Notification | `registerForNotifications` delegates unchanged name/callback at4. Actual host/guest callback Proxy code1 is **oneway String + IBinder**, with interface/trailing checks in each Stub. A physical alias must be mapped back to the subscriber's logical name while preserving the actual Binder. |
| Removal/client tracking | Both original `ServiceManagerProxy` implementations explicitly throw `RemoteException` for `unregisterForNotifications`, `registerClientCallback` and `tryUnregisterService`; the real generated AIDL methods exist below. Registration support is not removal/drain acknowledgement. Do not bypass this difference with a no-op or fabricated callback. |
| Cache import | The captured framework's sole direct init-cache xref is `ActivityThread.ApplicationThread.bindApplication`: incoming Map register35 reaches `initServiceCache` at49. That method checks cache-empty at6 then copies `putAll` at10, without per-entry endpoint admission. Actual Map production/currentness and cold process ownership must precede use; clearing an old cache is not reference drain. |

The generated guest/Samsung proxy table is source-derived, synchronous flags0:

| Code | Methods |
| --- | --- |
| 1â€“4 | getService, getService2, checkService, checkService2 |
| 5â€“8 | addService, listServices, registerForNotifications, unregisterForNotifications |
| 9â€“13 | isDeclared, getDeclaredInstances, updatableViaApex, getUpdatableNames, getConnectionInfo |
| 14â€“17 | registerClientCallback, tryUnregisterService, getServiceDebugInfo, checkServiceAccess |

The inventory compares exact top-level request writer/result-reader/CREATOR
calls for all17; it does not infer native server version, policy or nested
Parcelable field compatibility from descriptors. No raw transaction bridge is
proposed. Name routing would retain the original calls and errors.

## Existing OneOS mechanisms and the collision

Installed `guest_prepare.sh`308â€“318 uses the existing binderfs nodes and rbinds
host `/dev` into the guest; mount privacy does not itself establish a new Binder
driver context. The switch preserves native audio/camera users and removes the
host system_server; it does not demonstrate two live Java namespaces. Return's
`HOST_NAMES` protects canonical vold, IVold/default, keystore2, installd and
Gatekeeper names. These are source guards, not current endpoint attestation.
No exchange of handles or original callers across distinct Binder contexts is
assumed here.

The real targeted exception is `gvld`: prepare1257â€“1273 binds the paired vold/
incremental payloads and writes the marker; start selects/checks that name and
explicitly rejects enforcing policy for its current service-label profile.
Actual staged `SMS.connectVold` has literal gvld at0, lookup3, death registration15,
IVold conversion25, cache29 and listener35. That body confirms a targeted lookup;
it does not prove the effective native library/daemon/view. Existing Installer
still looks up **installd** at0/3, then uses `OneOSInstalldProxy.asInterface`23:
that proxy adapts a service protocol and retains the received Binder, rather than
providing a manager-wide namespace. Physical native ownership remains explicit.

The actual staged LSS lifecycle constructs LSS at9, then names **lock_settings**
at14 and publishes at19. Samsung's original lifecycle also publishes that canonical
name. Retaining Samsung therefore requires an actual guest producer/local-
lifecycle replacement and a genuine guest-protocol endpoint; a lookup alias
cannot prevent duplicate construction or local-service side effects. Existing
[local contract](local-locksettings-contract.md) obligations remain intact.

## One next engineering seam

Propose an offline guest-only `checkCanonicalPublication(String)` call at the
start of actual `ServiceManager.addService(String,IBinder,boolean,int)`, before
its original PC0/4 acquisition/delegate. For the first fixed profile it throws
for reserved canonical `lock_settings`; all other original arguments/behavior
pass unchanged. It is a reservation delimiter, **not a working namespace or safe
guest boot**. LSS already constructs before publication, so root must separately
select its pre-constructor/local lifecycle replacement before any real guest run.
This guard has no caller-supplied grant, UID role guess, service fabrication,
identity clear, worker hop or transaction rewrite. Samsung8095 and the native
manager remain unchanged. No guard or binary was built here.

After root selects the genuine endpoint profile, the smallest complete Java cut
must cover get/check **before cache**, the real one-time cache Map producer,
native-wait input, publication, list/debug projection, and notification name/
Binder identity plus real removal/drain. Shared native names stay physical;
guest-only names need actual admitted publishers and protocol adapters. Proposed
`oneos_coloros_lock_settings` remains an unpublished candidate from the earlier
endpoint card, not a ready service. Native clients/CLI, cached old handles and
host Samsung code must not be silently redirected. Original caller/user/UID,
permissions, lockout/StrongAuth and key policy are separate authorities.

The static auditor passes199 assertions over140 selected/reused method proofs
(including native declaration boundaries).
Its initial assumption of identical host/guest callback Stub PCs failed; the
auditor was corrected to their actual IF_EQ versus packed-switch layouts, while
wire parity remained true. That history is retained. No OEM/Android/native code,
OneOS script, phone operation, patch, global namespace mutation or canonical
payload change ran. No device case or runtime namespace is accepted.
