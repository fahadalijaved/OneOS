# Bootloader unlock feasibility: current phone

Read-only investigation on November5 local / November6 UTC,2026. No verified
official or public unlock method matching **SM-S948U1 / SM8850 /
S948USQS4BZIG** was found in the bounded primary-source review. This does not
prove that unlocking is impossible. No reboot, unlock, flash, raw-partition
operation or exploit was attempted.

The phone reports locked/green Verified Boot, warranty bit0,
`ro.oem_unlock_supported=1` and `ro.boot.other.locked=1`. Its current Settings APK
matches the captured file exactly. That source's availability check hides the
OEM-unlock control when other.locked is1. Build capability, a visible toggle and
the earlier bootloader's actual authorization are distinct. These Android
properties are not cryptographic hardware attestation.

Existing kernel/root access does not establish control of Samsung's earlier
secure-boot authority. AOSP separates unlock capability from current unlock
permission and describes user confirmation and factory-data reset. Its generic
Fastboot documentation does not establish Samsung command support for this
model. See [AOSP's unlock contract](https://source.android.com/docs/core/architecture/bootloader/locking_unlocking)
and the [official-options review](bootloader-official-options.md).

[Samsung's November bulletin](https://security.samsungmobile.com/securityUpdate.smsb)
lists **SVE-2026-3546 / CVE-2026-21155**, a privately disclosed bootloader
out-of-bounds write before SMR Nov-2026 Release1, with Android14–17 listed.
The phone reports an October5 security patch. Exact affected model/bootloader
revision, whether this binary includes the fix, and a working unlock chain
remain unverified. This is a research lead, not a usable unlock procedure.

The [matched userspace-source review](samsung-oem-unlock-source.md) also found
that aggregate `isOemUnlockAllowed()` can write persistent state. It was not
called. No flag, OEM setting, FRP state, Knox state or credential was changed.
Existing PIN/fingerprint/data preservation remains the project requirement;
no data-erasing architecture change has been approved.

Evidence is pinned in [the inventory](../inventory/bootloader-feasibility.json).
The [public-research review](bootloader-public-research.md) records the exact
limits of the searched demonstrations. A matching original researcher/vendor
revision mapping or an appropriately sourced exact bootloader image is needed
before a more concrete feasibility claim. No such image was acquired here.
