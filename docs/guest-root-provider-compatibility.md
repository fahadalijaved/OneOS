# Guest root compatibility

The guest uses a common userspace broker rather than importing the host root
manager. It authenticates the caller's peer UID and filesystem root, checks the
current guest package/UID mapping, and defaults to deny. The guest OneOS app has
implicit management access. Other grants are private to that guest.

The arm64 injector starts only the guest zygote child. Its modified NeoZygisk
daemon retains the guest namespace, uses guest grants and does not start a global
monitor or change the host root provider's module-unmount policy. Namespace requests use the authenticated socket peer PID and a pinned namespace
FD after checking the peer's guest filesystem root. A PID supplied in the message
cannot select the cached namespace. The ptrace helper accepts only a target that
is a child of its invoking launcher in the same guest root, and checks again
before injection. Zygisk root flags validate grants against the current guest
package-to-UID mapping, so a reused UID cannot inherit a removed app's grant.

Vector 2.2 is
bundled. Recognizable Zygisk LSPosed distributions can be imported and selected;
Riru layouts require another backend and are rejected. Vector and LSPosed have
not been shown to provide identical APIs, ART support or module compatibility.
Only one selected framework is enabled; disabling it retains its private state.

| Host method | Evidence | Still required |
| --- | --- | --- |
| Modern KernelSU | Fold8 guest boot, root controls and Vector on ColorOS and Pixel; native live policy audit | More driver versions and repeated transitions |
| KernelSU Next | Shares the audited upstream ioctl interface | Exact driver ABI, package tracking and device tests |
| SukiSU and other KSU forks | Several manager package IDs recognized | Fork-specific ABI, tracking and KPM tests |
| Magisk and forks | Existing BusyBox discovery; guest broker independent of MagiskSU | Host daemon/injection lifecycle, live policy audit and device tests |
| APatch | Existing BusyBox discovery; independent guest broker | Version-specific authorization, kernel patch state, policy audit and device tests |

The KernelSU package observer still sees guest processes and can prune its shared
live UID table. OneOS protects the host's persistent allowlist during the session
and audits live allow/deny entries, manager identity and module-unmount flags on
return. If state changed, the existing clean-reboot recovery reloads the protected
host state. Unsupported live audits also require the reboot fallback. This does
not establish cross-provider safety by itself.

Both OSes share a kernel, properties, Binder services, hardware and PID visibility.
A mount namespace cannot contain arbitrary privileged native code or kernel and
SELinux policy changes. Non-framework sepolicy.rule payloads are refused. The
broker does not emulate every root-manager prompt, PTY, pre-init, boot-image or
WebUI API. Arbitrary module side effects are not guaranteed reversible by a
soft restart. Full LSPosed activation and the untested provider rows above remain
runtime compatibility work, not verified support claims.
