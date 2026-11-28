# Retained root handoff: independent native source review

The separate, default-off v2 native source passes bounded static review for PC compilation. This accepts closed-control source preparation only. No compiler, native executable, OEM code, workflow, model or phone ran during this review.

Reviewed source: `compat/native/retained_root_handoff.c` (`276f2dc3…`) and its header (`72f29a3e…`). Canonical v1 C/header remain byte-identical (`4bdad3e7…` / `bbb3eb84…`). The [protocol](retained-root-handoff-protocol.md) and inventory give exact identities; private gate and readback are under `out/retained-root-handoff-review/native/`.

The native controller accepts only the exact INIT-associated host PID/UID through kernel peer credentials. This restricts association; it does not authenticate source or grant authority. The app has no control socket. IDENTITY sends one actual self-pidfd; a positive partial send never repeats the rights. Delivered unexpected incoming rights are retained before refusal.

Exact COMMIT sequence1 irreversibly latches host control before app stdio retirement and COMMITTED. Both duplicated pipes and original stdin/stdout/stderr receive one close attempt; uncertainty prevents acknowledgement. PING/CLOSE start at sequence2. Lost or partial acknowledgements cannot restore app control or authorize a retry/replacement. Host commit progress remains uncertain until independently resolved.

The controller checks its own session/process group and clears inherited parent-death state. Committed HUP is ignored; TERM/INT and host socket loss remain cutoff. Initial work shares one absolute budget; committed idle has no heartbeat requirement. Userspace deadlines do not promise cancellation of a blocked syscall. There is no native fork, child reaping, numeric PID/group signal or foreign-process kill.

The self-only cgroup operation writes `0` once through a held cgroup2 root descriptor, reads exact root membership, and refuses before OFFER on placement/readback/close uncertainty. Review finding ORH-NS-01 narrowed the claim: equality with visible PID1 and that view's root mount also holds in a jointly nested PID/proc/cgroup view. Root selected this qualification; no new kernel interface or fabricated global-namespace proof was added. A genuine initial host launch view remains an external profile/runtime prerequisite.

Native pidfd exit, app-owned Process waiting, CLOSED and resource drain remain distinct. Complete host/app custody, root-manager and switch kill policy, real namespace/LSM behavior, native resources and all 18 device acceptance cases remain unaccepted. No guest, PIN or other security operation is introduced.
