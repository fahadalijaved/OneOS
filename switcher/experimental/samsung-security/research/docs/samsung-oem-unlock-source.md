# Captured Samsung OEM-unlock gates

**The captured Settings code hides OEM unlocking when `ro.boot.other.locked` is exactly `"1"`, matching the observed value. This does not establish a way to unlock the bootloader.** Also, the aggregate `isOemUnlockAllowed()` getter can write persistent state, so it must not be used as a read-only probe.

This is a finite static audit of the captured Samsung framework/services and one exact Settings APK, not a native bootloader audit or a change to the security-integration project. [The inventory](../inventory/samsung-oem-unlock-source.json) and [replay auditor](../tools/audit_samsung_oem_unlock_source.py) pin 67 selected methods and 42 assertions. Raw instructions remain ignored. No phone Binder query, APK/service invocation, OEM execution, setter, broadcast, property change, partition access, reboot, flash or unlock operation occurred in this worker.

## Observed state and source identity

Root's read-only observations report SM-S948U1/m3q/SM8850, build `CP2A.260605.016.S948U1UES4BZIG`; flash lock `1`, vbmeta `locked`, verified boot `green`, warranty bit `0`, OEM support property `1`, other lock `1`, KG `0x4` and EM status `0x0`. The FRP property supplied a path string only; that path was never opened. These are observed property values, not hardware attestation. KG/EM numeric meanings remain unassigned here.

Root's fresh six-file observation matches the captured framework SHA `8095a9ae…` and services SHA `def967fb…`. Settings was extracted only from the existing local mounted capture: `/system/priv-app/SecSettings/SecSettings.apk`, 65,683,104 bytes, SHA256 `ae40a4c3a91fc599aa26e8c8e7c6ddfab795fddfed0ae334395006206039b316`, matching its immutable manifest record. The six-file observation did not include current Settings; current-UI equivalence is conditional until that APK is separately hash-matched. Static source behavior and the observed properties are distinct evidence.

## Exact UI and authority boundaries

Captured `com.android.settings.development.OemUnlockPreferenceController.isAvailable()` reads `ro.frp.pst` and `ro.boot.other.locked`. An empty FRP property returns false (PC50→81). Comparing other lock to `"1"` branches PC62→81, returning false before KnoxGuard or manager checks. Otherwise, KnoxGuard `shouldBlockCustomRom()` and manager availability also gate presentation. Thus the captured controller is unavailable for the observed other-lock value. The presence of `ro.oem_unlock_supported=1` does not override this predicate.

Its enabled/summary state additionally consults enterprise recovery/reset policy, carrier allowance, base `no_factory_reset`, first API level and already-unlocked state; updates also disable for KnoxGuard, administrator restrictions and Rampart/Auto Blocker state. These are separate reached branches, not evidence that any one currently permits unlocking. Rendering `updateState()` calls `isOemUnlockedAllowed()`→the aggregate service getter; invoking the controller is not a passive diagnostic.

The captured `OemLockService.onStart()` publishes `oem_lock`. Its constructor chooses available AIDL HAL first, then HIDL, otherwise `PersistentDataBlockLock`. HAL probing uses service lookup/wait paths; constructing this service or calling `isHalPresent()` is not proposed as a passive query. The actual current service instance/backend was not inspected.

The user setter, inspected only as source, enforces `MANAGE_USER_OEM_UNLOCK_STATE`, administrator identity, inactive FRP, system `no_factory_reset` restrictions and carrier allowance before delegating to genuine device allowance and persistent synchronization. Settings UI hiding and these service/backend gates are different. No setter was invoked. Neither UI patching nor changing a reported property is shown to alter bootloader authorization, signature enforcement or actual lock state.

## Getter side effects and one bounded read-only candidate

| Actual OEM service method | Captured behavior / query decision |
| --- | --- |
| `isOemUnlockAllowed()` — transaction 6 | Computes carrier AND device allowance, then calls persistent synchronization at PC34. **Not a read-only probe.** |
| `isOemUnlockAllowedByCarrier()` — transaction 3 | Delegates to chosen HAL or user-restriction fallback. Native HAL behavior/current choice remains unclosed. |
| `isOemUnlockAllowedByUser()` — transaction 5 | Delegates to device allowance. PDB fallback reads a partition byte; HAL alternative remains uninspected native behavior. Excluded from this no-partition scope. |
| `isDeviceOemUnlocked()` — transaction 7 | Permission check and comparison of `ro.boot.flash.locked` to `"0"`; no HAL, PDB, file or setter path in the captured getter. Redundant with properties already observed. |

The aggregate helper's write is conditional: local PDB must exist and the chosen lock must **not** be `PersistentDataBlockLock` (helper PC8/14). It then calls `doSetOemUnlockEnabledLocked` and `computeAndWriteDigestLocked` at PC34/39. The former opens mode `rw`, writes the OEM byte and forces the channel; the latter writes the digest. FRP protection can reject these operations. Even a getter returning false may reach synchronization. Do not substitute the aggregate getter or Settings rendering for a read-only check.

For the already-published genuine endpoint only, the narrowly source-supported read-only OEM-state query is `isDeviceOemUnlocked()Z`: descriptor `android.service.oemlock.IOemLockService`, actual Proxy transaction **7**, synchronous flags **0**, interface-token-only request, `readException()` then `readBoolean()` reply. Stub dispatch and sender constants agree. Permission enforcement requires any of `READ_OEM_UNLOCK_STATE` or `OEM_UNLOCK_STATE`; no caller grant or service presence is assumed. Its complete captured method-call list is permission enforcement, `SystemProperties.get`, `getClass` and string equality. Generic permission machinery/ordinary IPC diagnostics are not hardware attestation. No runnable query command is provided or executed. With unchanged source and property `1`, it returns false and supplies no new unlock-feasibility evidence.

The persistent allow byte is an **allowance** state, not proof of a bootloader transition. Current HAL state, bootloader implementation/fuses/signature policy, model-specific authorized unlock capability and any applicable exploit chain remain unknown. This audit proves a userspace hiding condition and a dangerous getter side effect; it proves neither that the device is permanently impossible to unlock nor that root/Settings edits could unlock it.
