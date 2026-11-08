# Independent host probe supervisor review

**PARTIAL: source/lifetime and actual ARM ELF shape/profile review passed.
Same-C Windows fixtures are unavailable; no overall component/model or Android
acceptance is granted.** Root chose to preserve this bounded result and stop
compiler retries. The
supervisor is a separate, unselected diagnostic component. Existing host Context
controller/procedure files remain frozen. No phone, OEM or native execution is
part of this review.

The required ownership boundary is the supervisor's one direct fork child. The
single-threaded supervisor must establish SIGCHLD's normal waitable disposition,
without SIG_IGN, SA_NOCLDWAIT or another reaper. A pidfd may identify that child;
alternatively the exact positive fork result remains safe for signalling while
the child is unreaped. Only a matching terminal wait result, checked with
WIFEXITED/WIFSIGNALED, ends ownership: traced-child stop status can be reported
without WUNTRACED and is not a reap. Any successful reap permanently ends
signalling. A failed
or unexpected wait, including ownership loss/ECHILD, must forbid further numeric
signals; it is not permission to reacquire a process through proc. These are
the documented preconditions for safely opening a pidfd after fork, rather than
the previous check-proc-then-kill race. [Linux pidfd_open contract](https://man7.org/linux/man-pages/man2/pidfd_open.2.html)

The child must finish every UID/GID/fs-credential transition before arming
PDEATHSIG, then immediately check the original supervisor parent. Otherwise a
credential change can clear the setting, or the parent can die before installation
without causing a signal. A set-ID or file-capability exec can clear it again;
the exact exec target and effective credential/no-new-privileges behavior need
explicit admission. The paired kernel audit additionally finds secureexec
clearing and a possible SELinux SID-transition producer. A pre-exec query cannot
prove preservation after app_process; selected-kernel/domain evidence remains
open. Parent-owned deadline/reaping must work independently of that claim. Root
accepts this explicit post-exec supervisor-death limit for a qualified PC
component; no crash-proof monitor hierarchy or policy change is requested.
The forking parent thread must remain alive. [Linux parent-death contract](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html)

READY must describe the same child's final dropped UID/GID/groups, observed
domain/namespaces and held-file identities, plus the pinned proposed exec
profile. Native READY has no Cap* fields; zero capabilities and genuine code/view
admission require fresh external checks of this waiting child before PERMIT,
rather than inference from UID1000 or an earlier KSU shell. Only a fully parsed
one-shot permit may admit that child to the fixed exec. Malformed,
partial, duplicate, EOF and cancellation inputs must remain refusal/cleanup;
a lost write acknowledgement does not prove no permit reached the child. An
exec-error channel must distinguish permit delivery, exec failure and later
child exit without allocating a replacement PID or retrying the launch.

The parent must own every pipe and close every unused/inherited endpoint.
Control reads, child output and deadlines must not block the only reaper.
Output/line limits and fixed non-secret metadata remain mandatory. Hex-framed
child bytes are explicitly untrusted transport; the adapter must discard unknown
logs and never persist them as receipt-safe diagnostic fields. A clean
environment must contain the exact reviewed nine host values plus the one JAR
CLASSPATH; arbitrary argv, inherited VM/preload inputs or a generic command mode
would widen this component's scope.

Deadline expiry stops admission and starts exact-child cleanup. TERM, escalation
to KILL and actual wait/reap are separate facts. A signal cannot guarantee bounded
exit of uninterruptible native work. If reaping remains unresolved, the design
must retain or explicitly expose the cleanup owner and forbid another launch;
timer expiry or PC adb exit cannot silently discard that obligation. No process
group, name-only, service, parent or foreign process may be signalled.

The author's design supplies a single root parent, WNOWAIT observation
followed by one terminal waitpid, nonce-bound permit, fixed exec and exact-env
header proposal, and HOLD_UNREAPED after failed cleanup. No requirement-level
blocker remains in the corrected frozen source. Full C `778991a9…` and builder
`1377f060…` were read before build; doc `6f478e5a…` and header `ea6336da…` were
hash-checked. An independent projection of the captured nine environment values
plus CLASSPATH and the four argv tokens reproduces canonical profile `a930f953…`.

Provisional review found and the author corrected the proc parser's cross-line
whitespace consumption, blocking nonce acquisition, unrelated inherited FD leak,
permit enqueue/cancellation guards, synthetic time on clock failure, open gate
after ownership loss and incomplete-output success. The final source also closes
sticky EOF/HUP paths and returns from parent I/O EINTR to the deadline/reap loop.
The proposed pure-C PC fixture path targets the actual shared decision/parser functions, including
adjacent proc UID/GID lines and overflow rejection; they do not exercise Linux
fork/credential/signal/FD syscalls.

Clock loss is a distinct failure policy: close admission/gate, attempt immediate
KILL of the still-owned child and retain HOLD until actual reap. It refuses the
normal two-second grace without inventing a clock or switching to a fallback.
No concrete source blocker remains for the root-gated PC build.

## Actual ARM artifact and unavailable fixtures

The saved 615792-byte ARM artifact has SHA256
`049ed861b5ae2635f4e60e788568f697a9b26ba21860b9045fdc2673b797c9fc`.
An independent byte reader confirms ELF64 little-endian AArch64 ET_DYN, an entry
inside executable file-backed LOAD memory, no interpreter, DT_NEEDED or undefined
dynamic symbols, no writable executable LOAD, a non-executable stack and GNU
RELRO. It resolves941 relative relocations and the actual `host_probe_argv` and
`host_probe_env` object symbols: their ordered four/ten entries and terminal NULLs
match the independently reconstructed profile. Neither binary nor native tools
were executed by this reviewer.

**This is a 4 KiB-oriented output, not a 16 KiB-compatible launch artifact.**
All four LOAD alignments are4096; three LOAD offset/address pairs are incongruent
modulo16384. Device selection requires a genuine matching page-size/loader
profile or a separately reviewed relink. No current Samsung page size or actual
loader success is inferred from this inspection.

The author preserved failed compiler/link receipts and logs. Host linker output
I/O initially failed; a binary stdout attempt then exceeded its initial build
output cap. The later ARM static-PIE compile/inspection succeeded, while the
Windows pure-C DLL link remained unavailable. The two model-only continuations
record permission failure and an unsupported `/noimplib`-as-input failure.
No same-C fixture pass is
claimed, and this reviewer loaded no DLL or reran a compiler, model or binary.
Root stopped additional rebuilds/alternate runtimes rather than waiving that
missing evidence. The paired inventory pins the final partial author record and
the exact failure history.

The source has no remaining concrete defect identified by this bounded review;
the actual Linux credential/fork/wait/signal/FD paths remain unexecuted. Native
syscall permission, Samsung kernel/domain identity, post-exec FD/PDEATHSIG state,
KSU equivalence, full Context/module/cache/callback drain and Android acceptance
remain open. Fresh external Cap*/NoNewPrivs, namespace, code/profile and staging
admission are still mandatory before permit; this component does not select the
old controller or authorize any phone action. The larger security goal remains
active and its owner guards are not waived by this diagnostic's partial result.
