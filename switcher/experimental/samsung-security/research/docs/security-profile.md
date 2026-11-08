# Read-only device-profile preparation

The [collector](../tools/collect_security_profile.py) observes bounded nonsecret
identity and OS-file facts. It does not admit a security stack, verify loaded
classes, authenticate a native service, or establish Android/cryptographic
acceptance. No credential, synthetic-password, enrollment, slot, user-secret,
HAL getter, fingerprint dump, application data or environment content is read.
No property, setting, file, service or phone state is deliberately changed.

## Commands and transport boundary

From this nested project:

```powershell
python -B tools/collect_security_profile.py
```

The default only lists already known ADB transports. It uses the existing parent
`out/toolchain/android-sdk/platform-tools/adb.exe` and port5038, after checking
that the localhost server port is reachable. It never explicitly starts/resets a
server, pairs/connects a device, requests root, installs, reboots or switches OS.
The precheck is not atomic: if the server exits afterward, the normal ADB client
could start a server. The tool does not claim a race-free no-autostart guarantee.

Only after root coordinates a particular read-only collection:

```powershell
python -B tools/collect_security_profile.py --collect
python -B tools/collect_security_profile.py --collect --serial ALREADY_CONNECTED_SERIAL
```

Automatic selection requires exactly one listed transport in `device` state.
An explicit serial must identify one already trusted, connected transport.
Offline, unauthorized, absent, duplicated and ambiguous selections are refused.
There is no discovery or connection fallback. Neither command grants permission
for normal-flow security tests, writes or disruptive device tests.

A separately coordinated observation can explicitly inspect a known trusted
serial even when its active property view differs or is unresolved:

```powershell
python -B tools/collect_security_profile.py --inspect-serial ALREADY_CONNECTED_SERIAL
```

This mode never automatically chooses a device and cannot combine with
`--collect`/`--serial`. It runs only the same nonsecret OS/proc allowlist. It
records the unchanged strict property decision as match or mismatch/unresolved;
`profileAdmitted` is always false, including when that subset matches. A mismatch
keeps the observation unresolved, rather than declaring another profile
supported. There is no additional path, property, privilege or command freedom.

Each invocation creates an exclusive timestamp/UUID folder beneath ignored
`out/security-profile/`, with `profile.json`. PC output is confined to that tree.
Missing server, denial, malformed/oversized output, failed remote commands and
unsupported properties/paths are unresolved facts, never successful defaults.
Exit0 means a completed observation/list, not security acceptance; exit2 denotes
unresolved/partial observation. Source/tool failure can fail earlier without a
receipt. Outputs have no credential material.

## Exact allowlist and provenance

The collector verifies the pinned OneOS055 source files before and after use:
`guest_start.sh` SHA896b72cc…, `guest_prepare.sh` SHAdee53391… and
`oneos_switch.sh` SHAc2a86046…. Their complete hashes and the existing ADB binary
hash are retained in the observation. Source files are read as evidence only.

**Property-policy source boundary:** exact2a `oneos_switch.sh` line1138 invokes
`guest_props.sh add` after mounting the guest. Root fetched that exact commit's
helper as data from official OneOS raw GitHub, using normal Windows/.NET TLS
verification, without a TLS bypass. The retained 63,145 bytes have SHA256
`f8164fd19314936cabb11bfa73f3038e6a85f0a62f57c2feec9d4b37df27083a`.
The source URL, raw path and bounded derived facts are recorded in
[security-profile-source.json](../inventory/security-profile-source.json).
The helper remains ignored data; it was not executed. The collector verifies its
exact hash before and after observations, without changing the parent snapshot.

Exact helper lines101–109 build the host-key set; empty non-persist values count
as unset. Generic import skips keys present in that set at147. Lines702–709 apply
the added keys using resetprop. The inspected explicit overrides concern other
keys, including audio, CPU ABI and hardware; there is no explicit override of
`ro.product.model`, `ro.build.version.sdk` or `ro.build.display.id` in this helper.
Thus source supports preservation of their existing nonempty host values on
this generic route, **not** a claim that ColorOS always spoofs them. Missing/empty
host values can still come from guest properties. Existing override-state files,
other code, installed patches and live outcomes were not read or authenticated.
An incomplete, changed or different property view can block strict collection,
which is why explicit non-admitting inspection is separate. No blanket global
property-identity or supported-profile claim follows from the source.

| Fact | Allowed read and source basis |
| --- | --- |
| Active property view | Ten explicit `getprop` keys: model/device/manufacturer, SDK/release/security patch, build ID/display ID/incremental/fingerprint. No property enumeration or serial property. The strict check compares model SM-S948U1, API37 and display ID CP2A.260605.016.S948U1UES4BZIG with the recorded [GOAL](../GOAL.md) baseline. Missing/mismatched values stop strict `--collect` before file/PID reads. Explicit inspection records that same negative/unresolved decision while continuing only allowed observations; it does not establish another supported target. |
| Active OS files | Hash-only `/system/framework/services.jar`, `framework.jar`, optional `oplus-services.jar`, `/system/bin/vold`, `/system/build.prop`. The input ledger records the framework archives; guest_start lines690–691 identify service/vold paths and switch line1115 identifies build.prop. |
| Staged OS files | The same five fixed suffixes beneath `/data/local/tmp/oneos/rootfs`, from guest_prepare lines2–3 and guest_start line12. These are **source defaults**, not proof that this directory is a live guest or supplies its loaded code. |
| Mount namespace | `readlink /proc/self/ns/mnt`, `/proc/1/ns/mnt`; bounded `/proc/self/mountinfo`, returning only selected OS-role mountpoints. Source: guest_prepare lines7–8 and switch lines73–74. No mount, namespace entry or symlink enumeration occurs. |
| Actual process-root view | `pidof system_server`, at most two distinct numeric PIDs, a process lookup used by switch line1518 and elsewhere. For each, read exact `/proc/PID/ns/mnt`, nonsecret process identity `/proc/PID/stat` starttime, and hashes of `/proc/PID/root/system/framework/{services,framework,oplus-services}.jar` plus `/proc/PID/root/system/bin/vold`. Compare PID starttime/namespace before and after; compare PID set and essential properties again at the end. No arbitrary PID/file input, environment, process memory or user-data path is accepted. |

Each hash operation requires a regular, nonempty file no larger than128MiB and
refuses final symlinks or resolved paths outside the explicit OS/staged allowlist.
The `/proc/PID/root` magic-link prefix is deliberately authorized for those exact
OS suffixes. Missing/inaccessible mappings remain unresolved. The collector
does not use root/escalation or traverse other symlink paths to make them work.
Process-root hashes identify bytes visible there, **not actual classpath
selection or already loaded code**. Matching PIDs/namespaces/property snapshots
detect some movement; they do not make the observation atomic, prevent every
in-place file race, or certify one authority generation. A moved process clears
its process-file facts and leaves an explicit unresolved identity.

Each ADB child has a20-second timeout, with concurrent bounded stdout/stderr
drain. Properties/hash output are capped at1KiB, PID list64B, namespace128B,
process stat4KiB and mountinfo512KiB. Failed exit or stderr invalidates the query.
Hashes/properties must match their exact expected output grammar.

## Local validation and current execution boundary

```powershell
python -B tools/test_security_profile.py
```

Fourteen local tests exercise ambiguous/offline/unauthorized transport refusal,
explicit selection, injection/oversize rejection, PID count/reuse identity,
secret-path rejection, profile mismatch, and real authored child-process output,
stderr, exit-failure and timeout bounds. They also check strict mismatch stops,
non-admitting inspection classifications and mandatory explicit inspection
selection. They invoke no ADB or OEM code.

The first actual list-only attempt is recorded at
`out/security-profile/20261105T153206984149Z-df3c7f814e124b89ab72bb024eae42ae/profile.json`.
The sandbox rejected its localhost precheck with WinError10013 **before ADB was
invoked**. Its unresolved result is not a current no-device observation. No
remote collection has run. A later successful list or coordinated collection
must be evaluated as its own timestamped observation.
