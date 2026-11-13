# Prepared ordinary One UI Context observation

**Proposal only: no phone command, child launch, transfer or Context invocation was performed by this preparation.** Root must first choose the read-only launcher preflight, review its actual results, and obtain separate concrete approval before the JAR transfer and probe launch. This observes Context in an additional ordinary-host process while One UI and its original system_server remain running. It does not run under OneOS/ColorOS, use the proposed cold VM gate, or construct a security authority.

## Frozen artifact and current evidence

Use only `out/samsung-context-probe/20261105T191533125222Z-5c0551305cc340c6a912916babe057b3/samsung-context-probe.jar`: **4,588 bytes**, SHA256 `fbce6bff35fe889d3b354f1e3017c19b4960b9468b3a35a9c336d70ddfc6b806`, containing only `classes.dex`. Source SHA is `58e53f216ef472064e9e8d347dd5b733fdba00f1295ce55c6e75aeba488148e8`; builder SHA `1098cdacf427836d03cdfd1ca7d076caecd5d801ba9f34b99fed378df91bb1b4`. Do not rebuild or substitute an output. SDK37 compilation passed, but D8 explicitly supports at most36; this remains an execution qualification, not an ART test.

The saved [live observation](live-host-observation.md) supplies current public Build matches and six named code-file matches through candidate system_server27202's root view. The later Settings observation also matches captured SecSettings and reports security patch2026-10-05. These are named-file/process candidates, not loaded-code, native-owner or coherent-view attestation. Transport12176, port5038, UID0, PID27202 and namespaces are saved observations, never permanent selectors. Refresh their identity and boot ID before using them. The user must be present and ordinary One UI visibly functioning, with no switch/restart/update underway.

## Root-chosen preflight before any transfer

No JAR is needed for this phase. Root may choose a bounded read-only child-identity preflight using existing tools; this document does not execute or authorize it. The reported toybox nsenter help supports `-t` and `-m` but no UID drop. Reported KernelSU su help supports a numeric user plus `-g`, `-G`, `-s` and `-c`. A candidate argv shape is:

```text
/system/bin/toybox nsenter -t HOST_PID -m
  /system/bin/su -g 1000 -G 1000 -s /system/bin/sh -c READ_ONLY_CHILD_SCRIPT 1000
```

This is an argv specification, **not a ready command**: HOST_PID must be the freshly checked numeric candidate, and READ_ONLY_CHILD_SCRIPT must be the root-reviewed fixed script. Confirm exact option parsing against the saved actual CLI help before execution. Do not add `-M`, preserve-environment flags, a forced SELinux context, `--ksu-no-new-privs`, group lists copied from system_server, a UID-changing alternative or a namespace fallback. Those would need their own explicit review. KSU can choose a different namespace/domain/group policy; no preservation is assumed. Existing su authorization/daemon/audit behavior also remains real, not an inert setuid instruction.

The child should emit only bounded, explicitly selected metadata: its PID/PPid and starttime; boot ID; four UID/GID status words; numeric supplementary groups; SELinux current label; mount/PID/user namespace links; CapEff/CapPrm/CapAmb/NoNewPrivs; the fixed named-code hashes below; and only the selected environment variables needed for launch. Read `/proc/$$/...` for that exact shell, not an unbound `pidof` result. Do not dump an entire environment, status, mount table, cmdline, logcat or proc tree. Every proc read has a byte/time cap. Capture parent/target/child identities and namespace links before and after; reject missing/denied/truncated data or drift.

Require actual child UIDs all1000, GIDs all1000, supplementary groups exactly the reviewed `{1000}`, no effective/permitted/ambient capabilities, and a domain **explicitly reviewed from its observed value** for this diagnostic. UID1000 does not imply `system_server` domain or its privileges. Do not relabel or relax SELinux on refusal. Require the child's mount view to equal the chosen ordinary-host target view at the checked endpoints, and both views to match every literal source hash:

| Named path | SHA256 |
| --- | --- |
| `/system/framework/framework.jar` | `8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe` |
| `/system/framework/services.jar` | `def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6` |
| `/system/bin/app_process64` | `08891284f79ebd9411d7ebd2e267bd2c083e8d5a02f2f192629fb126fabfeec8` |
| `/system/bin/vold` | `0b00f386f2056aebd3e0824f67cba35614fdc6e2d2b11414ae34d5a2c33bebb7` |
| `/system/lib64/libandroid_runtime.so` | `f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d` |
| `/apex/com.android.art/lib64/libart.so` | `4166f04af3a71286ed0c8c760f0555a7edf213495f9b32ddc842783287aa91fa` |

Hashing vold is code-view evidence only; never invoke it. Obtain the actual host BOOTCLASSPATH/DEX2OATBOOTCLASSPATH, Android/APEX root variables and any required namespace/loader environment from a root-reviewed fixed-key observation. Do not source `/data/system/environ/classpath` as shell code or replace missing facts with the old61-path cohort. The captured init export path and old cohort are provenance, not this child's current environment. A bare inherited adb/su environment, or an empty environment without an admitted BCP, is insufficient. The root review must select an exact child environment allowlist and literal values, including treatment of preload/library/module inputs. Missing facts keep launch on HOLD. This preflight starts no app_process or Android Context and writes no phone file.

## Separately approved staging and launch

The proposed new phone directory is exactly `/data/local/tmp/oneos-host-context-probe-20261106-fbce6bff`; final owner0:1000, mode0750. Final JAR path is that directory plus `/samsung-context-probe.jar`, owner0:1000, mode**0444**. First prove the directory absent and parent/view identity unchanged; refuse an existing path, symlink or unexpected owner. Root stages only within the admitted target mount view, initially inaccessible to the child, verifies4,588B/full SHA, then applies final modes. An adb push to another namespace's same spelling is not staging proof. Rehash from both the selected root view and actual UID1000 view. Do not install an APK, set a property, change SELinux, chmod a shared directory, replace a host file or create a module.

The final reviewed environment sets **CLASSPATH only to that JAR**, and the executable/main/sole argument are:

```text
CLASSPATH=/data/local/tmp/oneos-host-context-probe-20261106-fbce6bff/samsung-context-probe.jar
/system/bin/app_process64 /system/bin
  com.appleexploit.oneos.security.probe.SamsungContextProbe --host-context-probe
```

These are the exact selected invocation tokens inside the admitted UID1000 child. The complete environment argv must be materialized from preflight and root-reviewed before asking for launch approval; the above fragment is not a complete runnable launcher. No `--zygote`, `--system-server`, hidden-API exemption, VM image/JIT override, authority bootstrap or guest classpath is added.

For the actual launch, repeat admission **in the same fresh UID1000 shell that will exec app_process**. Emit a bounded READY record, retain that shell PID/starttime through exec, and wait on the PC-controlled pipe. Root's controller sends its one-shot permit only after actual identity/domain/groups/namespace, environment, code and JAR checks pass. On malformed facts, closed pipe or missing permit, exit before exec. A prior successful child does not admit this child. This handshake/supervisor is a required root-reviewed implementation step; no launcher has been authored or tested by this card.

## Deadline, output and process-only cleanup

The proposed PC controller uses a30-second total launch deadline, separately bounded preflight reads, and capped pipes. It stores only the exact authored JSON schema (one line, at most2,048 bytes), validated field types/public fixed Build strings/booleans/PID/UID, the exact exit status and bounded supervisor metadata. Unknown stdout/stderr is counted and discarded, never stored as stack traces, raw logcat, tokens or private paths. Unexpected/multiple records, output caps or transport failure fail the observation. There is no claim that transitive framework logging itself is secret-free.

On timeout, signal only the still-matching owned child PID/starttime/boot ID with TERM, wait2seconds, then KILL only after identity recheck. Never use `killall`, a name-only selector, a process-group kill or a system_server/zygote/adbd/service kill. Losing identity/transport means HOLD and retain the cleanup obligation; killing PC adb alone is not remote termination. Repeated launches are forbidden until the exact own child and launcher have exited. Native uninterruptible work can outlast a signal; record that uncertainty rather than restarting the phone or security stack.

After confirmed own-process exit, root may remove only the exact staged JAR and `rmdir` the exact now-empty dedicated directory if those actions were included in approval. No recursive cleanup or cache deletion. ART/framework cache writes or original module/callback effects are not undone by deleting the JAR. Verify ordinary One UI and the original process identities remain available through separately bounded read-only observation; never reboot, switch, activate a module, change a setting or use root restoration as recovery for this probe.

The source really prepares a main Looper and calls original systemMain/getSystemContext/getApplication, with font, native, Binder, module, resources/display, configuration/callback and possible cache effects. Full transitive effects/drain are unproved. Exit0 means only synchronous `CONTEXT_OBSERVED_ONLY`; false identity booleans are observations. REFUSED_OR_FAILED, denial or hang is retained as failure. No cold-authority, full Context ownership, PIN/fingerprint, app-key, CE, recovery or performance acceptance follows.
