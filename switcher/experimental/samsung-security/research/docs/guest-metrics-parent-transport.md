# RAW metrics through the original DMS Binder

**Source-supported next proposal:** carry the private v1 metrics request on the **actual original DMS BinderService**, using an unused transaction intercepted before its normal descriptor check. The same source-owned lifecycle cell then calls the frozen Endpoint locally. This removes the new alias and its publication/readback race. It does not prove the actual parent/code/generation, complete lifecycle assembly or Android execution, and it selects no runtime change.

The conditional [alias lifecycle proposal](guest-metrics-lifecycle.md) remains frozen history. Its observation that ServiceManager can suppress publication errors remains correct; this proposal simply adds no such publication. [The new inventory](../inventory/guest-metrics-parent-transport.json) pins five narrowly selected original bodies, six reference assertions and exact dispatch/branch checks, reusing the 36 factory assertions and nine OneOS source files. Run `python -B tools/audit_guest_metrics_parent_transport.py --read --report` for static verification. No OEM class, Android service, phone or publication ran.

## Actual collision and interception cut

Proposed code: **`0x00fe0001`** (16646145), reserved only within the selected versioned source profile. It is not a universal vendor-extension allocation.

| Actual captured method | Verified source |
| --- | --- |
| ColorOS `DisplayManagerService$BinderService.onTransact` | Existing public override, 16 instructions. PC0 invokes original IDisplayManager.Stub; only if unhandled does it consult `this$0.mDmsExt` and call its onTransact at12. PCs are hexadecimal in this card. |
| ColorOS `IDisplayManager$Stub.onTransact` | For codes1…0xffffff it enforces original `android.hardware.display.IDisplayManager` token at a **before** its switch. Dispatch keys are exactly1…72. |
| Actual `DisplayManagerServiceExtImpl.onTransact` | Logs and switches only code10111; unknown defaults return false. It has no catch-all metadata handler. |
| Actual `Binder.onTransact` | Its Java body recognizes INTERFACE1598968902, DUMP1598311760 and SHELL1598246212, otherwise returns false at ad/ae. None equals the candidate. |

The candidate is absent from this complete selected Java dispatch chain. An attempted query for optimized Stub.getMaxTransactionId failed because that method is absent; the actual dispatch body supplies the proof instead. Its failure log remains distinct. Other releases, later OneOS patch outputs and installed bytes require new collision/source admission. No unknown live Binder is to be probed with this transaction number.

The new branch **must precede existing BinderService PC0**. Putting it after original Stub dispatch is unsound: a genuine v1 metrics token would first fail the original display descriptor enforcement even though the high code is not in that Stub's switch. The prefix handles only the exact reserved code. Every other code enters the identical original 16-instruction body, preserving normal display calls, exceptions, standard Binder controls and existing vendor10111 fallback. Do not change attachInterface, descriptor, queryLocalInterface, Binder extension or global `display`.

## Minimum source/member footprint

Retain the source-supported born-Binder capture at original DMS.onStart's normal tail, after32/before35, and actual successful phase100 completion at original onBootPhase return114. The real vendor calls, default-display wait/timeout and existing tail run first. The cell owns that actual DMS/actual born Binder pair and the frozen Producer/Endpoint, not a second service or arbitrary lookup result.

Propose these **unimplemented** additions:

1. One private DMS lifecycle-cell field, as in the prior proposal; OFF/null means the private transport is unavailable.
2. One package-private DMS method, conceptually `boolean dispatchOneOsGuestMetricsFromParent(Binder actualBorn, Parcel data, Parcel reply, int flags) throws RemoteException`. It reads its own private cell field, then supplies actual `this` plus the actual born Binder/borrowed packets to that cell. A missing/inactive/retired cell returns unhandled false; it must not return ABSENT/default/readiness.
3. An exact-code prefix in the **existing** BinderService.onTransact. It obtains actual `this$0` and calls the added DMS method, passing actual BinderService `this`. This avoids assuming an inner class can directly access a newly private outer field without an appropriate source accessor. The five-word call fits the existing seven-register method; a new DMS dispatch method can place cell+owner+born+packets+flags in six contiguous registers. These are register-budget observations, not an emitted retarget/inverse proof.
4. Cell API conceptually `boolean dispatchFromParent(Object actualDms, Binder actualBorn, Parcel data, Parcel reply, int flags) throws RemoteException`, accepting only its exact retained pair while its phase100 state is ACTIVE. The only target is its internally retained, actual final `PreparedGuestMetricsEndpoint`; no caller supplies another IBinder or a Boolean admission callback.

The normal phase100 hook activates that owned Endpoint once; it no longer asks for an alias candidate, invokes publication, performs ServiceManager readback or calls finishPublication. Activation states capture/phase readiness only. Original global DMS publication is untouched; obtaining and admitting the real current parent remains external. The original addService's normal return is still not a new proof that the parent is discoverable or current.

The complete authored lifecycle/Endpoint/Producer/Sample/Java8 marker dependency closure belongs in the **actual DMS defining services loader**, with canonical Binder/Parcel identity. The existing default-OFF build-owned profile proposal remains conditional: the OneOS candidate producer must generate/pin it with exact original/patched source, new members, helper closure and inverse proof. No app-only helper, source-name match or arbitrary duplicate loader qualifies. Three existing method bodies would change (`onStart`, `onBootPhase`, BinderService.onTransact), plus the field/new DMS method and authored cell. No new runtime code, configuration producer or DEX edit was emitted here.

## Direct local delegation and borrowed packets

Prefer the frozen Endpoint unchanged. After exact parent/cell admission, invoke **that owned local Endpoint's** `protocolBinder().transact(1, data, reply, flags)`. Preserve original flags, so its existing flags0/non-null-reply/512-byte-before-token/version/subject/trailing-data checks remain effective. Its descriptor is `com.appleexploit.oneos.security.IGuestDisplayMetrics.v1`; the request and fixed raw-five reply are unchanged. A private-code failure/unhandled result never falls back to the original display descriptor parser or becomes a successful empty/default metric result.

Actual ColorOS `Binder.transact` is public final (flags0x11), eight instructions, with no catch region. It performs:

- At3, if nonnull, `data.setDataPosition(0)`.
- At6, a direct Java virtual `onTransact` on the same Binder object.
- At c, **only on normal return**, if nonnull, `reply.setDataPosition(0)`; then it returns the actual Boolean.

There is no BinderProxy/native IPC call, Handler hop or explicit clear/restore identity in this path. The owned Endpoint really is that local final Binder class; this observation would not hold for an arbitrary supplied IBinder proxy. Same-thread direct call preserves the incoming native caller frame in the selected Java path; it is not a fresh Android/native caller test. The Producer still performs its actual same-thread callingUID/PID checks and original DMS getter policy.

**End-to-end packet positions are not immutable.** Canonical local transact intentionally resets borrowed data/reply positions as above. The frozen Endpoint itself still neither recycles nor resets them. On exceptional return, the reply reset is skipped and packets remain at the point reached; parent transport must not silently rewind/clear/retry. It forwards actual Boolean/reply/errors. Supported original RemoteException/RuntimeException/Error propagate; the Endpoint's checked-fault conversion remains its fixed-message RemoteException with cause. Binder exception serialization is distinct from Java Throwable object identity across processes. Native outer dispatch/Parcel effects remain unexecuted acceptance work.

No extra wrapper Binder or public metadata endpoint is published. The actual parent still answers ordinary IDisplayManager and its genuine OPPO extension; a private v1 token/high code provides dispatch separation, **not endpoint/source or Samsung authority attestation**. The original getter supplies only what that real incoming caller is allowed to see; no UID/PID parameters, identity clear, new grant, fake absence or security capability is added.

## Required fixed-code client binding

The frozen `com.appleexploit.oneos.security.boot.PreparedGuestMetricsClient` source SHA256 `afd99ebe98a09b209bb7f6a42d23c9d88313597f5d6760105def73213ea625d1` currently calls `endpoint.transact(1,…)`. It **cannot be pointed directly at this parent**: original DMS transaction1 is its ordinary display-info operation, not this private protocol. No frozen client file was changed.

Propose a separately source-approved `PreparedGuestMetricsClient.prepareParent(IBinder retainedRealDms)` factory with an **internally fixed** `0x00fe0001` mode. Keep the standalone Endpoint code1 factory distinct. Do not accept a caller-supplied transaction number. Retain the actual parent and obtain the request Parcel for that same target, preserving existing v1 parsing/length/exception/cleanup/absent rules. An extra local wrapper used only to translate1→high would introduce another Binder identity and `Parcel.obtain(target)`/markForBinder target question; it is unnecessary here and is not proposed.

The current client's plain exception-header profile rejects extended StrictMode/AppOps headers. A fixed-code factory does not establish those live Android header conditions or relax its decoder. Source/currentness/parent generation and actual boot visibility remain separate client admission. This factory/transport mode is proposal-only: no new client source, bytecode or artifact was emitted.

## Lifetime, retirement and remaining gate

The selected cell remains one per actual DMS/born pair and admitted helper Class/loader. It retains the original source objects and Endpoint; it neither reconstructs DMS nor swaps in a wrapper at global `display`. A phase mismatch, pre-capture/disabled state or actual retired cell cannot dispatch the private metadata request. The private protocol is unavailable until original phase100 work genuinely completes; an available reply still says nothing about final Samsung metrics or physical freshness.

Retirement first closes new parent admission, then applies the **actual Endpoint.retire**. A cell Boolean change alone is not the Endpoint reply fence: calls already leaving the cell could enter the still-active Endpoint during that interval. A completed retire must include the actual Endpoint retirement; prior reply-admitted results may still be constructed/delivered later. Neither endpoint nor parent Java-frame counts prove native Binder, DMS, callback, consumer or global drain. Keep active/uncertain owners and client instance/epoch checks; do not reuse a retired cell or parent name as a fresh generation.

Original parent death invalidates transport. A live old Binder can also outlast service replacement, so identity/death alone is not physical-display/cache currentness. The actual parent source/profile/defining loader, current DMS lifecycle/generation, configuration and client-instance admission remain required. The existing eager two-read bridge, Samsung CompatSandbox/RM/configuration/CompatibilityInfo, boot-helper visibility/callsite selection and full process-local display map remain separate.

This approach is sound at the **selected source/API boundary** and materially avoids the newly introduced alias acknowledgement problem. It does not prove a working lifecycle cell, installed source hook, Android native dispatch, runnable Context or security integration. Root API approval and independent implementation/retarget review are required before code. The old alias proposal is preserved as conditional history; no earlier frozen file was changed.
