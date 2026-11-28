# Architecture alternatives: paired method review B

**Recommendation after exchanging critiques with reviewer A:** investigate a
**dedicated Samsung-framework authority process** next. Put the ColorOS-protocol
Binder frontend and original Samsung Stub/backend together in that process;
ColorOS clients call the frontend directly. Prefer explicit protocol-specific
service aliases over ambiguous global-name replacement. Keep guest-process
import as the comparison/fallback. This selects the next proof, not a working,
fastest or best-proven full runtime. Stop generic component expansion until the
finite ownership/bootstrap gate below discriminates these placements.

The full [GOAL](../GOAL.md) stays fixed: PIN creation/change/removal from either
OS; existing and newly managed fingerprints in both; genuine primary-auth,
lockout and extra-factor policy; native per-use app crypto and intended CE
storage; cancellation, return and later cold boot. Every candidate is still
unproved against that complete matrix. A correct-PIN callback or imported SPM
class cannot stand in for the other outcomes.

**Current primary-source boundary:** root's pinned official OneOS v0.4.57 is
commit `1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe`; the
[upstream ledger](../inventory/method-review-upstream.json) records eleven initial
and three supplemental immutable files. In that switch source, line971 stops host zygote,
995 kills generic `app_process64`, 996–999 kill zygotes/system_server and1011
suppresses host restarts. Guest-start645–655 describes shared servicemanager
ownership and explicit `gvld` separation. README242–245 gives remove-lock
guidance; actual ScreenLock/LaunchJob code permits a known lock under the explicit
Advanced override, while unknown lock state still blocks. That override permits
launch, not shared authentication. The current producer still applies all four
security guards. Root verified those guards and guest-start remain
byte-identical to0.4.55; prepare/switch changed and are not assumed identical.
The bounded inspected diff concerns watchdog/display behavior, not a demonstrated
shared-security implementation.
These are [source facts](https://github.com/fahadalijaved/OneOS/tree/1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe),
not installed-image or device findings. Upgrade alone is not a demonstrated
solution to the requested shared security.

| Alternative | Full-goal ownership advantage | Main unresolved cost / disqualifier |
| --- | --- | --- |
| **Dedicated Samsung-framework process: strongest next candidate** | Original Samsung boot-framework/value/resource/JNI identities can remain together. A directly called frontend plus same-process original dispatch can preserve the kernel Binder caller without a privileged forwarding hop. | Cold construction still needs genuine Context, users/serials, DPM, LocalServices/storage, policy and fingerprint owners. Bootclasspath is not initialization. Process launch/survival, endpoints, native writers and return/boot remain open. |
| **Guest-process Samsung service import: current baseline** | Existing guest lifecycle and same-process dispatch are available; no extra authority VM/process is required. | Private/canonical type, LPU route, numeric resource and native/local-service collisions remain. Early constructor cleanup can mutate authoritative state before publication. No actual owner graph is assembled. |
| **Keep initialized Samsung host system_server alive** | Preserves original live credential/biometric objects and avoids reconstructing them at each switch. | A different topology: current OneOS kills this owner. Retaining it also retains AM/PM/user/display/storage policy owners, conflicting names and mount views. There is no proved stop-and-extract mechanism for a security-only island. |
| **Narrow Samsung SPM/credential/provider graft into ColorOS services** | Could reduce framework/bootstrap breadth if a genuine transaction boundary exists. | SPM is not a drop-in verify-only object. Create/change/remove, nested derivations, storage, biometric invalidation, StrongAuth and uncertain commits still need exact Samsung semantics. Fingerprints remain a separate full lifecycle. No smaller complete cut is demonstrated. |
| **Native OneOS integration** | Upstream lifecycle/namespace support could benefit any chosen placement. | A delivery layer or process manager is not an existing Samsung security backend. A native HAL-only replacement must still implement original SPM/policy/commit/metadata duties. A cold Samsung Java process managed by OneOS is the first row, not retention or a new native-policy shortcut. |
| **Genuine ColorOS UI over the OneUI runtime** | Lowest security-state reconstruction risk in principle: keep Samsung's original security runtime and change presentation. | Genuine Settings/SystemUI dependencies, privileges and finish semantics still need a substantial UI port. Replacing the full ColorOS guest with presentation changes product scope; it needs an explicit scope decision. The paused ColorGlass work is not proof of that completed UI or permission to resume it. |

**Why the dedicated placement is worth testing:** it changes the location of
frontend/backend co-residence, not the direct-dispatch principle. An extra
process does not inherently add a second Binder hop when clients reach its
frontend directly. By contrast, guest facade→remote privileged backend forwarding
is another design and requires separate trustworthy caller/policy delegation.
The dedicated placement may remove much private-framework/resource adaptation,
but it merely moves service/object/state questions if its Context still resolves
wrong guest endpoints. No tiny independent authority or minimal class list is
proved by the existing inventories.

**Endpoint choice matters.** Publishing ColorOS transaction meanings globally
as `lock_settings` makes an unbound original Samsung LPU cache the wrong protocol.
One candidate keeps the Samsung protocol at its original name and gives ColorOS
an explicit frontend alias with complete consumer retargets. Original Samsung
internal clients can then retain their protocol. The actual publication,
permissions, local-interface behavior and all lookup consumers still need proof.
Routing overlapping transactions by descriptor, package text or shared UID1000
cannot establish which protocol or authority was intended.

**Finite discriminator before a pivot:**

1. Name the exact authority entry/bootstrap and each genuine Context, local
   service, user/serial, policy, storage and FP owner. Bind original physical
   DB/SP/slot/enrollment/key views before class initialization or any constructor
   reconciliation. Identify active first effects and failure retention; do not
   start a second owner over stock LSS as a construction probe.
2. Supply the exact public/internal endpoint map and guest producer/lookup cuts.
   Establish direct ingress, internal Samsung protocol routing, callback/policy
   readiness and app-UID/package/user checks. A Class shape or UID1000 is not
   admission. Preserve actual native operation challenges and key namespaces.
3. Account for the process PID/name/launch phase against OneOS's kill/keeper
   paths, all native listeners and current writers, and conflicting mount views.
   Separate Binder names alone do not isolate shared native hardware or state.
4. Select either an enduring authority with adapted OneUI startup, or an exclusive
   quiesce/reconcile/handoff before stock OneUI reconstruction. Retain committed
   PIN/enrollment changes and legitimate key invalidations, not stale snapshots.
   Later cold boot/first-unlock and real failure tests remain explicit gates.

Disqualify this placement as the preferred next implementation if those owners
require recreating most host system_server, if direct ingress/internal routes
cannot be kept coherent, or if it cannot preserve a single physical writer and
return path. Then compare guest-process import's concrete closure, rather than
substituting fake owners. A smaller graft earns priority only through an equally
complete transaction/ownership cut.

**Effort/performance — inference, unmeasured:** dedicated placement trades fewer
private-platform collisions for a new VM/bootstrap/lifecycle; guest import
trades that process cost for more canonical/private adaptation. Whole-host
retention risks two large frameworks and background owners; narrower grafts may
reduce footprint while increasing semantic rewrite/validation work. Native
language alone guarantees neither lower cost nor lower latency. UI-over-OneUI
avoids authority transfer but can move substantial work into UI compatibility.
There are no measured latency/RAM/idle/thermal comparisons or credible dates.

B initially prioritized initialized retention. A's critique and root's clarified
same-process frontend/backend alternative changed that ranking: retention is now
a separate secondary topology; dedicated cold authority is the first challenger
to guest-process import. Both reviewers reject declaring a winner from method
counts, prepared JNI/DEX leaves or survival of native daemons. The decisive later
functional proof must include real reciprocal mutations, existing/new FPs and
the same fresh per-use cryptographic operation, intended CE access and safe
return/reboot under the documented OneOS platform limitations. No device action,
implementation mutation or architecture acceptance occurred in this review.

Prior protocol/source/removal proofs can be reused. Private-loader or SID-helper
work need not be selected where a genuinely closed canonical Samsung runtime
supplies the corresponding owner; completed work is not a reason to force a
placement.
