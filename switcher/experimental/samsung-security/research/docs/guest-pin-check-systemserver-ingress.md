# Guest SystemServer PIN check ingress

The staged guest has an existing place to forward an ordinary PIN check from
ColorOS SystemUI to Samsung. Keep the original `lock_settings` Binder and
transaction 10. Select its already decoded call in `ILockSettings.Stub` and
forward through the actual guest `LockSettingsService` worker. The guest
service must check the original caller before it clears Binder identity.
After the existing clear, that same worker can use the existing private host
code 2 client if its genuine process and incoming host caller both satisfy the
UID 1000 guards. This is a source cut awaiting real caller, subject and Binder
delivery owners. [Edit map](../out/guest-pin-check-systemserver-ingress/EDIT-MAP.json)

| Selected staged source | Observed edge |
| --- | --- |
| Framework `5cb16a37`, `classes6.dex` | `LockPatternUtils.getLockSettings` reads the cached service or looks up `lock_settings` at PC 7 and calls `Stub.asInterface` at 11. The factory uses the local interface if present, otherwise constructs a Proxy. The selected two-process route requires the real remote Binder. |
| `ILockSettings.Stub.Proxy.checkCredential` | Sensitive request at 8, descriptor at 17, credential at 21, user at 24, exact callback interface at 27. Transaction 10 with flags 32 at 36. It reads the remote exception and canonical response before recycling its Parcels. |
| `ILockSettings.Stub.onTransact` | Descriptor at 10, code 10 case at 1062, typed credential, integer user and callback factory at 1078. No trailing data at 1082. Virtual call at 1085 with registers `[9,1,2,3]`, then original exception header and typed result at 1089 and 1092. |
| Services `efb45f5f`, `classes2.dex` | `Lifecycle.onStart` constructs the service at 3 and 9, holds it at 12 and publishes that object under `lock_settings` at 19. This identifies the born receiver in source. It supplies neither readiness nor a credential endpoint lease. |
| `LockSettingsService.checkCredential` | Private `checkReadPermission` at 0 reaches `mContext.enforceCallingOrSelfPermission(ACCESS_KEYGUARD_SECURE_STORAGE, …)`. The original identity clear is at 3. The protected inner invocation at 32 uses the actual receiver, PIN, user, callback and flags 0. Restore and parcel-derived credential zeroization run on normal return and the inner invocation's exception path. |

## Proposed edit

Retarget just Stub case 10's invocation at PC 1085 to a protected virtual
`checkCredentialFromBinder` with the same three parameters and response type.
Declare the default in the framework Stub with ordinary virtual delegation to
`checkCredential`. Override the slot in the exact guest services LSS class for
the selected route. This keeps the framework Stub from linking the services
class, preserves the inherited behavior for other receivers and leaves the
generated Proxy and its transaction envelope intact. Adding the method
references and the override requires fresh DEX verification. The three-unit
retarget shape alone cannot prove the rest of the bridge.

The override should keep the actual permission leaf and admit the original
UID and PID from the Binder stack before the identity clear. Admission must
join the exact retained guest LSS, live selected SystemUI process and this
request to the actual current physical user, with a lifetime covering the
original host operation. SystemUI's shared-user name is
`android.uid.systemui`. Neither that string nor an integer UID or PID
establishes the required live process occurrence. The guest integer is a
request to check, and the host code 2 carries no user field. It needs the
already admitted physical mapping, never a default user substituted for a
miss or an alias. The protected dispatch slot identifies the decoded case in
source and confers no authority by itself. Before selection, close the
slot's callers and any competing local/public path capable of serving the
same selected request. The default-disabled image can retain the exact
existing implementation.

The selected override should keep the original clear/restore region around
one synchronous invocation of the genuine code 2 client. Retain the admitted
occurrence through call, reply and cleanup. Ensure parcel-derived guest
credential cleanup also covers newly introduced pre-clear refusals without
changing borrowed credential ownership or masking the primary failure.
The current guest try begins at PC 32, so a new throwing admission before
PC 3 cannot simply rely on the old handler. The host endpoint separately
closes its decoded PIN. The same guest callback Binder goes through the
canonical host callback factory and the real Samsung `checkCredential`.
Preserve genuine progress before the final response or failure. An
unavailable selected route refuses without local verification, synthesized
result or a repeat of an operation that might already have entered Samsung.
The original guest Stub writes the actual returned typed response, including
null, or lets the failure propagate through the original Binder path.

## Policy and delivery boundary

Replacing the guest inner verifier preserves the original guest outer
permission and uses the original Samsung PIN check with its own policy and
side effects. The staged guest inner method separately contains FRP and repair
branches, an `mSpManager` monitor, a rate-limiter call tied to the current
protector, and Oplus remote verification and derivation edges. Selecting the
ordinary physical PIN route requires an explicit disposition of that guest
policy. Running the guest verifier as a preliminary check or failure fallback
would run a second credential backend. FRP, repair, other users, profiles,
alternate factors and guest-to-host key/CE or policy equivalence are outside
this cut.

The client checks both `Process.myUid()` and `Binder.getCallingUid()` at
dispatch. The host endpoint checks its real incoming Binder UID before
decoding. That host guard alone does not identify the selected guest
SystemServer among UID 1000 holders. Selection needs authenticated private
Binder delivery from the actual retained host issuer to the exact guest
SystemServer, accepted callback reachability in the selected Binder realm,
and current physical subject custody through the call and source loss.
The prior guest fork/handoff records are source prerequisites for that
delivery. A pidfd carries no Binder handle. No runtime issuer, device path
or end-to-end result follows from the offline source evidence.
[Guest delivery boundary](retained-pin-guest-delivery.md)
· [Physical-user worker boundary](retained-physical-user-worker-boundary.md)
· [Host check integration](retained-pin-check-integration.md)
· [Callback wire](pin-progress-callback-wire.md)

The original Samsung call and the previously tested host code 2 component
were reused as source evidence. This audit only read the staged archives and
checked the static call and cleanup edges. No guest or host execution, OEM
code execution, credential input, production patch or Binder publication
occurred. [Inventory](../inventory/guest-pin-check-systemserver-ingress.json)

## Stock forwarding source model

Two authored method fragments establish the proposed Java dispatch shape. The
framework Stub's protected default calls its public virtual `checkCredential`
once with the decoded arguments. It declares `RemoteException`, matching the
captured interface. The guest service override invokes the existing
`GuestPinCallerFrame` with `this` and those same arguments. The frame forwards
to the original public service method. The fragments are staged only into
authored JVM models. [Framework method](../compat/guest-pin-delivery/case10-stock/ILockSettingsStub.java.inc) · [Service method](../compat/guest-pin-delivery/case10-stock/LockSettingsService.java.inc)

The [runner](../tools/test_guest_pin_case10_stock.py) compiles the modeled
framework classes in a parent loader and the service model in a child loader
with the two unchanged SDK-compiled frame classes. `javap` confirmed the exact
descriptor, argument loads, one forwarding call and direct result return in
each fragment. The framework listing contains no service dependency. All seven
model cases passed. They exercise the ordinary default, same-receiver caller
observation before clear, unavailable and nested observation, permission and
operation failures, and direct local calls. The model also refuses trailing
data before reaching the slot. [Model and static readback](../out/guest-pin-case10-stock-model/r-65301913/receipt.json)

The current device archives still have their original call sites. Actual ART
class resolution, helper initialization, Binder caller identity, and parcel
cleanup need their own evidence. Initialization can fail before the frame's
observation handler is entered. A later implementation must establish loader
and initialization closure before selecting the slot. Retrying the stock call
after a forwarding exception could run the original method twice. Host delivery
and physical-user admission remain open.

### Scoped observation after permission

The [caller-frame successor](../tools/compose_guest_pin_preclear_observation.py)
can give the permission-success source edge one opaque observation. It
matches the exact active request and incoming caller before opening the
scope. The token carries no credential or owner fields. It can be rechecked
on the same worker during the synchronous observer and expires when that
observer returns or throws. A later identical request or restored Binder
identity cannot revive it. The old Boolean remains a snapshot for the stock
model. The successor adds no transaction or Samsung dispatch.

The SDK 37 class build passed, and the seven saved stock-dispatch cases
passed with its exact classes. The runtime placement still needs the original
permission-success edge between the captured PCs 0 and 3, the actual SystemUI
process occurrence and separate Samsung physical-user custody. The source
model cannot supply these owners. [SDK build and stock regression](../out/guest-pin-preclear-observation-build/r-ec31c27e/receipt.json)

Seven additional JVM cases passed with the same SDK classes. They cover the
restored-identity tail, permission denial, identical successive requests,
foreign threads, nested dispatch, live identity changes and observer failure.
The original modeled verifier still runs once. [Scoped observation tests](../out/guest-pin-preclear-observation-model/r-7693112e/receipt.json)
