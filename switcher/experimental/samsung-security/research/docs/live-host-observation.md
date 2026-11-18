# Saved live host observation

The phone has returned connected, superseding the earlier away assumption. Root
captured read-only metadata on November6 UTC; this report uses **local saved
reports only** and issued no ADB commands. It admits no runtime/security profile.
The [inventory](../inventory/live-host-observation.json) pins the three reports,
rechecked collector/profile/ADB/fingerprint-init inputs and six locally rehashed
recorded code files. The corrected ColorOS no-edit baseline remains untouched.

## Observed build and named code files

The topology capture00:21:05–00:22:06 UTC reports **SM-S948U1, SDK37**, display
`CP2A.260605.016.S948U1UES4BZIG`. Its fingerprint is
`samsung/m3quew/m3q:17/CP2A.260605.016/S948U1UES4BZIG_OYM4BZIG:user/release-keys`.
These match recorded property literals, including the unexecuted host Context
probe's fingerprint guard. Public properties are not hardware attestation and
can survive/spoof a guest view; they do not identify an authority or authorize a
Context test.

At00:25:42 UTC, root hashed the following six named files through candidate
system_server PID27202's root view. All six values match the actual recorded
inputs rehashed locally for this report:

| Named file | SHA256 prefix | Recorded bytes |
| --- | --- | ---: |
| /system/framework/framework.jar | 8095a9aeda27b790 | 54,708,192 |
| /system/framework/services.jar | def967fbcb9498d5 | 28,190,402 |
| /system/bin/app_process64 | 08891284f79ebd94 | 51,856 |
| /system/bin/vold | 0b00f386f2056aeb | 1,490,936 |
| /system/lib64/libandroid_runtime.so | f77d49dcfae7271e | 3,271,648 |
| /apex/com.android.art/lib64/libart.so | 4166f04af3a71286 | 15,010,176 |

Full hashes and local paths are in the inventory. These are **named file matches**,
not measurements of loaded memory, resolved classes/JNI, active native owners,
kernel state or cryptographic identity. The saved code-hash stat identity matched
at its endpoints; this is not an atomic state claim.

## Process and namespace candidates

The saved transport reports UID0. Process UID values below come from saved status;
names, executable paths, ancestry and namespaces remain **candidates**, not Binder
or native-endpoint ownership authentication. Namespace labels omit only the
common `mnt:[…]` notation in this table.

| Candidate PID / role | PPid | UID | Sampled mount namespace(s) |
| --- | ---: | ---: | --- |
| 1 / init | 0 | 0 | 4026532781 and 4026531841 across sampled tasks |
| 279 / init | 1 | 0 | 4026532781 |
| 1100 / servicemanager | 1 | 1000 | 4026532781 |
| 1159 / vold lookup | 1 | 0 | 4026531841 |
| 1271 / keystore2 | 1 | 1017 | 4026531841 |
| 27126 / zygote_next | 1 | 0 | 4026532781 |
| 27129 / zygote64 lookup | 1 | 0 | 4026536358 |
| 27202 / system_server | 27129 | 1000 | 4026536359 |
| 29324 / Samsung fingerprint service lookup | 1 | 1000 | 4026532781 |

The zygote64 and system_server candidates both resolve executable
`/system/bin/app_process64`; candidate1159's comm is `binder:1159_2` while its
saved exe is `/system/bin/vold`. No name/exe match is upgraded to an endpoint
owner. No pidof match for other names is not proof that a service is absent.

The system_server status reports556threads, but both enumerations stop at the
512-thread cap. Its later code-hash stat reports573threads. These were different,
bounded observation times; no complete thread view or invariant count follows.
All nine process identities matched at sampled endpoints, role results and boot
IDs matched before/after, but **every selected coherent-view admission remains
false**. Thread enumeration, namespace/mount reads and endpoint checks are not
atomic; no parent-death, cross-switch survival or concurrency proof was obtained.

There are seven `unresolved` JSON records: missing/invalid
`init.svc.zygote_secondary`, plus three failed libart metadata reads (PID1/TID277,
PID1159/TID1159, PID1271/TID1271), each also recorded in the query log. Thus the
seven records include three duplicates; they are not seven distinct command
failures. Missing/denied views remain unresolved, not empty or supported.

## Boot-property boundary

At00:33:04 UTC, public properties report `ro.boot.flash.locked=1`,
`ro.boot.vbmeta.device_state=locked`, verifiedbootstate `green`, veritymode
`enforcing`, and `ro.oem_unlock_supported=1`. `sys.oem_unlock_allowed` and
`ro.boot.kg.state` were not reported. Warranty bit0, KG0x4 and bootloader string
`S948USQS4BZIG` are recorded values without interpretation here.

**OEM unlock supported1 does not prove unlockability**, an available permission,
an OEM-toggle state or hardware/Knox status. These public properties are not
attestation. No reboot, unlock, flash, partition operation or device change is
authorized or performed by this report.

No hardware/authentication, PIN change, fingerprint, auth-bound app crypto, CE,
Context/service construction, recovery, mutation or performance test occurred.
The user is exploring bootloader feasibility read-only; phone availability alone
does not grant new actions or close the full security goal.
