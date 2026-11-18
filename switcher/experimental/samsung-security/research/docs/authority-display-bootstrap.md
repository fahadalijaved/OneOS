# Two eager display reads: prepared process-local contract

The two newly identified Context-construction reads have a bounded source-supported adaptation: translate only Samsung transactions **71→44** and **86→59** to a retained genuine ColorOS DMS Binder, preserving the actual reply. The selected compound OverlayProperties writers/readers match across the captured native libraries after checked address normalization. Samsung also exposes a real process-local `ServiceManager.initServiceCache(Map)` route before Context creation. This supports a **prepared adapter design**, not an installed adapter, admitted live endpoint, complete Context bootstrap or authority readiness.

No runtime adapter source, class, DEX, native bridge, cache installation or IPC was authored/executed in this followup. No OEM code, JNI, ELF, service or phone ran. Prior [A](authority-bootstrap-runtime.md) remains frozen; its no-probe statement describes that earlier cold-authority scope/snapshot. Root's later separate host-only Context probe does not establish this post-switch endpoint/adapter/owner contract.

Evidence is in `inventory/authority-display-bootstrap.json`: 22 new exact DEX bodies, 27 checked edges, four exact Stub case mappings, identical 20-entry ColorSpace.Named order, 22 selected native functions and six paired compound serializer/reader comparisons. Four existing Proxy bodies/transaction flags are reused from A's frozen inventory SHA256 `b527fa96edc027866559e6fe8a54abaf15176af3767486c5d4e246b047f3fccc`. Counts describe static selections, not acceptance cases. Raw method/native data stay ignored in `firmware/authority-display-bootstrap/`.

## Request, dispatch and reply

Both frameworks use descriptor `android.hardware.display.IDisplayManager`, interface token only, no method arguments and synchronous transact flag0. A's original Proxy bodies write the token at PCe, transaction constant at13, call transact at16 and read the actual exception/reply. The selected Stub `onTransact` methods enforce the same descriptor at PCa. Their packed-switch offsets were resolved relative to referring switch PCd, not the payload address.

| Operation | Samsung case | Original ColorOS case | Actual reply after `writeNoException` |
| --- | --- | --- | --- |
| `getPreferredWideGamutColorSpaceId()` | tx71, PC32f | tx44, PC1f4 | `writeInt` at336 /1fb |
| `getOverlaySupport()` | tx86, PC240 | tx59, PC105 | `writeTypedObject(value,1)` at247 /10c |

These two no-argument cases do not enforce trailing-data exhaustion. A proposed narrow adapter may reject extra data as a stricter prepared contract; it must preserve valid original requests. Other transaction codes must be refused, never forwarded unchanged across the number mismatch. A Binder descriptor alone does not establish target identity or code provenance.

The real Samsung and ColorOS `DisplayManagerService$BinderService` methods clear calling identity, read cached state, and restore identity on normal and exceptional paths. There is no permission check in either selected getter or its selected dispatch case. Samsung directly reads `mWideColorSpace`/`mOverlayProperties`; ColorOS's two internal helpers perform the same cached field reads/getId. These paths do not re-query hardware, initialize DMS, create a display or register a listener. Serialization and the consumer's native allocation remain real work. This does not generalize to other display operations or authorize app-security forwarding as UID1000.

The int result is preserved, not converted to a fabricated default. Both exact `ColorSpace.Named.<clinit>` bodies assign the same 20 names/ordinals0–19, including DISPLAY_P3=7. This removes an observed enum-order ambiguity for these sources; it does not prove a live custom color-space ID is valid or prove the effective installed guest code.

## OverlayProperties wire and native ownership

Java `writeTypedObject` supplies an outer Parcelable presence marker. The selected OverlayProperties Java writer supplies a second native-object marker: native pointer0 writes int0; nonzero writes int1 and invokes `nWriteOverlayPropertiesToParcel`. Its CREATOR reads that second marker and only then calls the native reader. Both retain a native allocation through the genuine NativeAllocationRegistry/destructor path. A relay must preserve both layers, nulls, exceptions, sizes and the native payload; it must not reconstruct a boolean-only surrogate or move native pointers between processes.

Actual runtime JNI tables bind `nWriteOverlayPropertiesToParcel(J,Parcel)V` and `nReadOverlayPropertiesFromParcel(Parcel)J` to the selected C++ wrappers. The selected registrar, renaming helper, RegisterNatives leaf, seven-entry tables, class literal and wrapper targets are recorded. Wrappers obtain the real native Parcel, call libgui's `android::gui::OverlayProperties` serializer/reader, allocate the native destination and propagate failures. Genuine original runtime registration/class placement remains a prerequisite; these static tables do not perform it.

The captured native compound layout is size-prefixed and contains:

| Compound | Observed serialized layout |
| --- | --- |
| OverlayProperties | vector of present SupportedBufferCombinations objects; mixed-color-spaces bool; optional vector of present LutProperties objects. |
| SupportedBufferCombinations | Four int32 vectors in object-field order. |
| LutProperties | Two int32 fields, then a counted vector of four-byte elements written as raw data. No new semantic label is assigned to those raw element bits. |

Samsung libgui SHA256 is `3f241a05183cbced5d82a05b162d02ef6b90a0f81b970b22711ebf0293a43443`; ColorOS is `b99957d724a1364c7d52727c61c0d76372eb0e083ebbe243272c1a9e66e0e765`. Only the indexed 2,135,792-byte Samsung libgui member was acquired; no tree extraction occurred. Existing pinned libandroid_runtime inputs were reused.

All six compound write/read functions match after normalization: **929 instructions per side**, with instruction order, registers and non-address immediates preserved. Local branches become function-relative targets; external calls resolve to checked symbols; ADRP/LDR pairs are matched to actual named vtable GOT relocations. No generic address-instruction deletion is used. Nested write/read virtual slots were separately verified against both libraries' relocations. This closes the selected compound field-order/control-flow comparison, including nested nullable/LUT fields. It does not certify the entire native environment, primitive libbinder implementations, linker/ART execution, real service initialization or hardware data. No native function was invoked.

## Exact prepared API and install order

Proposed API, **not implemented**: `PreparedSamsungDisplayBridge.prepare(IBinder retainedGenuineGuestDms)` returns an owner with `IBinder sourceProtocolBinder()`. The raw Binder parameter is not admission. A future genuine bootstrap owner must establish the actual endpoint, effective guest code/profile, initialized DMS generation, process/mount/native view and retained lifetime before issuing it. The wrapper remains process-local and must not be published globally or exported as a Binder handle.

For exactly71/86, the wrapper would enforce the source descriptor, flag0, nonnull reply and no arguments; create a new canonical Parcel containing the genuine guest descriptor; call only44/59 on the retained genuine endpoint; and allow that remote transact to fill the original reply Parcel. The original Samsung Proxy then reads the genuine exception/value. The wrapper must not add a second `writeNoException`, parse/recast a foreign Java OverlayProperties, synthesize null/success/default metrics, or reacquire another generation by service name. A false transact, exception, endpoint death or uncertain completion cannot become a successful cached property. Required bounds and real death/retirement ownership still belong to the unassembled bootstrap owner.

Actual Samsung `ServiceManager.<clinit>` constructs its process-local cache and a dummy Binder and reads logging properties. `initServiceCache` checks cache size at PC2; empty cache receives `putAll` at PCa; nonempty cache reaches the selected helper that throws IllegalStateException. `getService` reads this cache at PC2 and returns a nonnull cached Binder directly, before `rawGetService` at PCb. Installing the wrapper under key `display` therefore changes this process's lookup without `addService` or a public/global `display` replacement. It does not replace existing manager singletons.

The **root bootstrap owner** must compose the complete admitted cache map and call this genuine installer once, before Resources/ActivityThread/Context and before any DisplayManagerGlobal singleton exists. A display-only helper should not consume the one install opportunity needed by other required endpoints. Capture the genuine remote before inserting the wrapper, never recursively resolve `display` afterward. Do not clear or mutate the cache reflectively, simulate absent display, hide a nonempty cache, retry a partial install or claim that cache emptiness attests source identity. The map/API is a one-time bootstrap mechanism, not a hot-swap/drain protocol.

This two-case wrapper still refuses the subsequent display-info/cache/callback operations reached by resource metrics. It cannot yet complete Context construction, and none of A's registry/font/metadata/user/policy/state/handoff gates are discharged. The next implementation decision is narrowly whether root admits this prepared two-case transport and assigns its real endpoint/bootstrap owner; broader display compatibility is not silently included.

Reproduce static checks with `python tools/audit_authority_display_bootstrap.py --read`, `--native`, `--compare-native`, then `--summarize`. The summary redoes the native comparison and verifies raw/receipt/A/source identities. No phone, Android or OEM execution is part of these commands.
