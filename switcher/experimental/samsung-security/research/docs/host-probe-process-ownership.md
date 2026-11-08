# Native host probe process ownership

The smallest source-supported owner is a single-threaded native supervisor that
forks its own child, prevents automatic/foreign reaping, keeps that exact child
unreaped through signaling, and consumes its terminal status once. This closes
the PID-reuse race of a proc-read followed by a foreign numeric kill. It does
not establish signal permission, termination latency, post-exec parent-death
protection or Android/Context acceptance. The supervisor implementation/build
review belongs to its author and independent code reviewer; this report audits
the operating-system contract, not their eventual binary.

No matching NDK process headers or kernel implementation appeared in the bounded
existing repository/toolchain searches. Evidence below uses official Linux
man-pages, Linux v6.6 reference source and commit-specific AOSP headers. These
are reference interfaces/implementations, **not identification of the captured
Samsung kernel, libc, SELinux policy or currently loaded code**. No downloaded
source-byte hash, installed NDK completeness or actual syscall support is claimed.

An unreaped direct fork child reserves its PID even if it exits before
`pidfd_open`, provided SIGCHLD is not explicitly ignored, SA_NOCLDWAIT is absent
and nobody else reaps it. That documented guarantee supports numeric signaling
under the same strict ownership conditions; it does not support arbitrary
PID/starttime selectors. Use SIGCHLD=SIG_DFL with flags0 before fork and one
waiter, rather than confusing SIGCHLD's default action with explicit SIG_IGN.
[pidfd_open](https://man7.org/linux/man-pages/man2/pidfd_open.2.html)

Linux v6.6 corroborates the mechanism: `exit_notify` creates a zombie unless
auto-reap applies; `wait_task_zombie` with WNOWAIT leaves it waitable, while the
consuming path moves it to DEAD and releases it. `__unhash_process` detaches PID
identities during release. No later numeric signal may follow the consuming
wait. Unexpected ECHILD loses this ownership proof and must disable numeric
signals, not fall back to a proc lookup.
[exit.c](https://github.com/torvalds/linux/blob/v6.6/kernel/exit.c#L1028-L1138),
[wait semantics](https://man7.org/linux/man-pages/man2/waitpid.2.html)

`waitid(P_PID,child,...)` with WEXITED|WNOHANG|WNOWAIT is a useful observation
operation: zero the siginfo first, distinguish no event from matching terminal
status, and retry EINTR within the existing deadline. One successful terminal
waitpid consumes status and latches REAPED before further work. Positive waitpid
alone is insufficient: traced-child stops can be reported even without
WUNTRACED. Require WIFEXITED or WIFSIGNALED; a nonterminal status retains the
owner and enters refusal/cancellation handling. These are direct consequences
of the [wait contract](https://man7.org/linux/man-pages/man2/waitpid.2.html).

A pidfd is an optional stable reference rather than permission or a reaper.
`pidfd_open(child,0)` creates a CLOEXEC descriptor; flags0 process semantics
avoid newer thread/group extensions. `pidfd_send_signal(fd,sig,NULL,0)` prevents
PID-reuse targeting, but can fail with bad descriptor, unsupported/invalid
operation, namespace mismatch or permission denial. Kernel signal dispatch
still reaches credential and LSM checks. The selected AOSP header declares both
wrappers since API31; that is ABI evidence only. An unexpected failure cannot
become a successful signal or silent permission-bypass fallback.
[pidfd_send_signal](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html),
[kernel signal permission path](https://github.com/torvalds/linux/blob/v6.6/kernel/signal.c#L775-L822),
[AOSP header at b2b11f68](https://android.googlesource.com/platform/bionic/+/b2b11f689b92226003bfeadf60c9e4f6fbe09859/libc/include/sys/pidfd.h)

Parent-death signaling must be armed by the child: fork clears it. Effective or
filesystem UID/GID changes clear it, so an early arm is insufficient after
dropping credentials. Arm again after all selected group/UID/GID/capability
operations, check the result and then compare getppid with the parent saved
before fork. A parent already lost before arming will not generate a retroactive
signal. The parent is specifically the forking thread, so keep that thread alive.
[PR_SET_PDEATHSIG](https://man7.org/linux/man-pages/man2/PR_SET_PDEATHSIG.2const.html),
[credential commit](https://github.com/torvalds/linux/blob/v6.6/kernel/cred.c#L438-L456)

**Pre-exec parent-death checks cannot promise post-exec protection.** Linux
`begin_new_exec` clears the setting for secureexec. More strongly, SELinux
`selinux_bprm_committing_creds` clears it whenever the new SID differs from the
old SID, independently of noatsecure permission or setuid/file-capability mode
bits. That same path revalidates inherited descriptors and can replace
unauthorized ones. Ordinary executable mode and PR_GET_PDEATHSIG before exec do
not resolve either issue for app_process. The actual exec-domain/native profile
must be established separately, or supervisor-death-after-exec remains uncertain.
Do not force a domain, weaken policy or change the frozen probe to hide this gap.
[exec.c](https://github.com/torvalds/linux/blob/v6.6/fs/exec.c#L1256-L1260),
[SELinux commit path](https://github.com/torvalds/linux/blob/v6.6/security/selinux/hooks.c#L2322-L2335)

Pipes are byte streams: EOF means all writer references closed, not child exit.
Both fork branches must close unused ends; control/error descriptors use
CLOEXEC and only selected stdio survives. POLLIN and HUP may coexist, so consume
bounded buffered data before handling EOF. Parent output can itself block when
the PC stops reading; use deadline-aware nonblocking output and handle EPIPE
without SIGPIPE killing the owner before cleanup. An exec-error pipe reports
written errno on failure, but its EOF also fits a child killed before exec or an
exec-time descriptor closure. EOF alone is not exec acknowledgement.
[pipes](https://man7.org/linux/man-pages/man7/pipe.7.html),
[poll](https://man7.org/linux/man-pages/man2/poll.2.html),
[exec descriptor behavior](https://man7.org/linux/man-pages/man2/execve.2.html)

Recommended bounded protocol, an authored design inference from these facts:

1. Establish the one-thread/one-waiter/SIGCHLD contract and bounded pipes before
   fork. Capture parent identity and fixed reviewed argv/environment. The child
   owns no arbitrary executable path or extra shell intermediary.
2. The child closes unrelated FDs, performs the selected namespace/credential
   operations, rearms parent-death signaling after the drop and checks its parent.
   It emits bounded nonce-bound facts/READY and waits for an exact internal permit.
   An error, truncated token, EOF or expired deadline before admission exits.
3. The parent drains output and monitors PC input, child state and one absolute
   deadline in the same loop. Only admitted actual facts permit the single
   execution request. No fresh deadline is granted for partial input or EINTR.
4. Mark execution possible before attempting permit delivery. Cancellation
   racing an already delivered permit can follow exec; report uncertainty rather
   than claiming Android initialization never began. Original Context effects
   are not undone by killing or deleting the staged JAR.
5. On cancel, EOF, malformed/oversized data or deadline, stop admission and signal
   only the owned unreaped positive PID or admitted pidfd. TERM and its fixed
   grace precede KILL while that ownership still holds. A returned signal is not
   a termination acknowledgement.
6. Consume terminal wait status once, latch REAPED and prohibit every later
   signal. If terminal exit cannot be observed, report HOLD_UNREAPED and retain
   the native owner; no repeat, removal or generic timeout claim releases it.

For a suspend-inclusive duration use an absolute CLOCK_BOOTTIME budget;
CLOCK_MONOTONIC excludes suspend. Recompute remaining time after interruptions,
partial I/O and resume. A clock cannot make the supervisor execute during system
suspend or guarantee a child exits from uninterruptible native work. The timeout
bounds admission/cancellation decisions, not guaranteed process death.
[clock semantics](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

Terminal direct-child wait status does not prove that separately forked
descendants, remote Binder callbacks, modules, cache writes or native service
effects have drained. Neither a shell timeout nor stopping local adb transfers
the remote child's lifetime to the PC. Loaded kernel/libc/policy identity,
post-exec UID/domain/FD/PDEATHSIG state, actual syscall/permission behavior,
the final implementation and separately approved device evidence remain open.
No process fixture, supervisor binary, phone command, ADB or OEM execution was
performed by this semantics audit.
