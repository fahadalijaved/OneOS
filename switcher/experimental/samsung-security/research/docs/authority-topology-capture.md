# Prepared read-only authority topology capture

The collector is staged for a later root-coordinated phone observation. **It has
not invoked ADB, probed a server, or inspected a device during preparation.**
Default and self-test modes are PC-only. Existing implementation, retention,
native and quiescence cards are unchanged; no architecture or authority is
selected by this tool.

From this nested project, local preparation is:

```powershell
python -B tools/collect_authority_topology.py
python -B tools/collect_authority_topology.py --self-test
```

These write only this stream's ignored plan/check/freeze outputs (self-test
also regenerates its authored inventory). The future collection command, **not
run now**, is:

```powershell
python -B tools/collect_authority_topology.py --collect --transport-id EXISTING_NUMERIC_ID --label host_before
```

Root supplies the numeric ID of an already trusted, connected transport on
existing server **5038**, without this tool discovering, connecting or pairing
one. Labels `host_before`, `oneos`, `host_return` are operator annotations, not
OS identity or authorization. There is no `devices` command or serial argument,
and no device serial/IMEI property is collected or stored. No ADB command is
executed merely to check this staged command's syntax.

## Reused transport and profile boundary

The exact existing `collect_security_profile.py` module supplies its bounded
PC-child output/timeout runner and inspection-only public profile assessment.
The module SHA256 is
`1da6a75fa2301865bcf42a36c82bc99de2b7d37063696fcc21fce512a25d1fac`.
Its default/list/serial collection flow and legacy OneOS source validation are
not executed. The parent repo-local `adb.exe` is pinned at
`b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f`.
Its help text at binary offset6456317 identifies `-t ID` as transport-ID
selection; this was inspected as bytes, without invoking ADB.
Future collection checks existing localhost5038, then `adb -t ID get-state`.
It does not request root or change privilege; inaccessible facts remain errors.
As with the existing profile tool, the server precheck is not atomic: normal
ADB-client autostart after a server-exit race remains possible. No explicit
start/reset/root/connect/pair command exists.

Profile fields are the same strict Samsung model/API/display-ID/build-fingerprint
subset interpreted in **inspection-only** mode. Missing/mismatched facts remain
unresolved and `profileAdmitted=false`, even if collection can continue. Selected
zygote/native init-service property keys are public state observations, not
endpoint or security-generation attestation. No full property enumeration occurs.

## Fixed read allowlist

| Observation | Scope and limit |
| --- | --- |
| Owner candidates | All `pidof` results for init; known primary/secondary/next zygote/app_process names; system_server; vold; keystore2; service/hwservicemanager; captured fingerprint executable basename. PID1 is separately included. No first-PID choice. |
| Process identity | Exact `/proc/PID/stat` before/after: comm, PPid, state and starttime; filtered status Name/Tgid/Pid/PPid, all four UID/GID values and thread count; executable symlink. No cmdline, environment, FD enumeration, stack or memory. |
| Threads | Up to512 task entries per candidate, each with its own mount-namespace read status and root device/inode metadata. Cap/read failures are explicit. The task glob is not an atomic complete-thread snapshot. |
| Selected same-TID views | Main thread plus representatives of distinct namespace/root pairs, at most4. Exact task starttime/namespace before/after, task cgroup, selected mountinfo rows and fixed OS-path `stat` metadata. Not every thread's full view is inspected. |
| Selected mountpoints | `/`, `/system`, `/apex`, `/data`, `/data/system`, `/data/user`, `/data/user_de`, `/linkerconfig`, `/metadata`. Only mount ID/parent/device/root/mountpoint and propagation IDs; filesystem sources/options are omitted. No directory or database enumeration. |
| Selected OS metadata | Device/inode/size only for framework.jar/services.jar, system vold, active-APEX libart.so, linkerconfig text and `/data`, through the selected `/proc/PID/task/TID/root`. No contents/hashes of those OS artifacts or data-tree files are read. |
| Sampling context | Boot-session UUID before/after and existing transport UID. A boot-session UUID is not a hardware serial. |

The fingerprint name comes from the already captured RC, SHA256
`a30e7ac20cb1d593437bc4c8eee4baa94783d73267bca1667ef197b65443244a`:
service `vendor.fingerprint-default` runs
`/vendor/bin/hw/vendor.samsung.hardware.biometrics.fingerprint-service`.
Name matching remains a candidate lookup; no HAL getter or service call is made.
A truncated/changed argv, hidden proc entries, permissions or a different build
can conceal a process. A `no_match_returned` result is not proof no owner exists.

Only fixed templates and validated numeric PID/TID operands are accepted.
Remote programs are pidof/getprop/cat/id/readlink/stat/awk/printf with fixed
read-only shell conditionals/loops. There is no arbitrary command/path option,
su/root exploit, service/dumpsys/cmd call, package query, ptrace, namespace entry,
mount, property/setting write, kill, install or restart. Credential/SP/HAT/
enrollment data, slots, user-private databases, serial/IMEI and process secrets
are excluded. The `/data/system` observation is a selected mount row only.

## Bounds, errors and interpretation

At most32 distinct PIDs are inspected; all returned candidates within the query
bound are recorded. A larger set stops process inspection explicitly. A query
has a20-second PC-child timeout and hard stdout/stderr cap (largest128KiB).
The collection budget is512 queries,180 seconds after transport preflight, and
8MiB including conservative charges for failed/capped queries. The thread loop
also has a fixed512-entry bound. Terminating a timed-out PC ADB child does not
prove the remote read ended instantly; it sends no remote kill command.

Denials, missing files, command/parser errors, output caps and moving identities
remain explicit unresolved results. Role and thread lookups repeat; selected
task starttime/namespace and process starttime/PPid are compared at endpoints.
Different namespace/root pairs remain separate. Observations are retained for
comparison, never silently promoted to one coherent process or authority view.
Matching endpoints cannot exclude changes between reads or after completion.

Output is exclusively repo-local
`out/authority-topology-capture/<timestamp-uuid>/observation.json` (or unresolved
failure metadata), with a32MiB per-artifact cap. No output-directory override is accepted. Exit2 denotes
unresolved/moving/capped observations; exit0 is a completed bounded observation,
not security/profile acceptance. Preflight failure has no successful observation.

This snapshot cannot show an inherited parent-death signal through proc alone;
there is no ptrace fallback. Nor can it prove init/zygote kill behavior, service
survival across OneOS, exclusive writers, native session/completion ownership,
Binder caller identity, concurrency, drain, loaded-code selection or credential
acceptance. Those six-owner/bootstrap gates remain open. The root controls any
later execution when a trusted transport is available; staging this script adds
no modifying runtime authorization.

Static tests exercise candidate enumeration, PID/starttime and task namespace/
root differences, denied/capped data, command/path injection refusal, fixed
transport construction and query budgets using authored fixtures only. The
frozen inventory contains `actualObservation=null` and `adbInvoked=false`.
