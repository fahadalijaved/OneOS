# ColorOS adaptation checkpoint

This continues the full [shared-security goal](GOAL.md) from local checkpoint
`8e18349`. Apple's direction is unchanged: adapt genuine ColorOS to Samsung's
working security APIs; remove optional unsupported OPPO integrations with their
callers, UI and background work. Required reciprocal PIN/fingerprint, real
policy, app-key, encrypted-data and recovery behavior remain the end state.

## Code now prepared on PC

| Component | Actual prepared change | Still required before use |
| --- | --- | --- |
| [SystemUI input RPMB](docs/coloros-rpmb-input-leaf.md) | Removes twelve extra input-copy calls and both normal/multiuser optional RPMB task allocations, retaining genuine input, results, null task writes, cleanup and finish paths. | Cold fresh owners, complete unsupported-feature/UI admission and a genuine Samsung backend. |
| [SystemUI SP/RoR](docs/coloros-ror-leaf.md) | Removes optional SP callback/constructor work and guards optional reboot-recovery/retry ingress. | Genuine committed-change cache invalidation; no queued legacy callback/job. Supported-capability UI remains separate. |
| [Settings RPMB](docs/coloros-settings-rpmb-leaf.md) | Removes only the private optional RPMB call and its misleading success diagnostic from the mixed job. | Existing worker/Intent/credential owners, static reuse cache, old retrieval and retained metadata remain accounted for. |
| [Settings fingerprint names](docs/coloros-settings-fingerprint-name-log.md) | Removes the separate enrollment-name diagnostic from the native row builder and preserves the visible title and row actions. | The Samsung query needs its actual Settings caller, provider and user. Count and clone consumers remain separate. |
| [Framework error propagation](docs/coloros-readiness.md) | Rethrows the original caught exception instead of converting it to new NONE/zero query values; normal paths remain. | Protected unknown-state UI, cache generation, exact authority/user identity and owned recovery remain unassembled. |

Each artifact is **unselected, PC-only and restricted to a cold process**.
They preserve source operation/result paths; they do not implement a Samsung
credential service or prove a phone can authenticate. Component byte integrity,
preservation, inverse/roundtrip and refusal-check scopes are documented per leaf.

The [composition](docs/coloros-ui-removal-composition.md) combines the two
SystemUI leaves and combines the earlier optional post-PIN audit leaf with the
framework error leaf. It refuses shared-method ownership and carries every
component condition forward. The generated ZIPs are code-reader artifacts,
not signed/installable APKs. No phone payload or original OneOS guard is selected.

## Backend construction narrowed by source evidence

[Native linkage](docs/security-native-linkage.md) pins the actual SID and
scrypt paths. SID extraction is byte-identical across the captured systems and
parses handle metadata, not hardware authentication. Canonical native
registration does not bind a private same-name Samsung SPM. A precise private
SID call binding remains necessary; whole Samsung native-library import is not
established as a requirement.

An authored [PasswordHandleSid helper](docs/password-handle-sid.md) now implements
the source-closed format extraction for stable nonnull handles of at least nine
bytes, with explicit rejection of malformed inputs. PC oracle/mutation checks
and independent review cover that domain only. It has not been retargeted into
the original private SPM and supplies no authentication or hardware decision.

[User and Context binding](docs/security-user-binding.md) identifies genuine
`UserManager(Context,IUserManager)` as the small client boundary. The matching
selected Binder codes do not make UserInfo replies interchangeable: Samsung's
extra attributes field and policy methods must be retained. Constructing another
UserManagerService can create default users and write its registry. The actual
authoritative server, application Context, local policy, lifecycle and handoff
owners remain open; no arbitrary serial snapshot is substituted.

These results narrow required adapters. They do not supply the live Samsung
authority/state/native graph that [CONSTRUCTION.md](CONSTRUCTION.md) requires.

## Current device boundary and next work

The [read-only profile collector](docs/security-profile.md) is prepared for an
already trusted ADB connection. Local transport/parser tests pass. A worker's earlier
socket-blocked list attempt remains unresolved; a newer root list-only run
successfully observed an empty device list. It collected no device facts and
issued no remote shell command. The fresh receipt is pinned by this checkpoint.

An explicit non-admitting inspection mode can collect the same bounded OS facts
for a named trusted transport while recording a mismatched/unresolved property
view. Strict profile collection remains unchanged. Neither mode admits a security
profile from properties or file hashes alone; only list mode has run here.

Current host, installed patched guest, mount namespaces, selected users/serials
and native endpoints still need evidence. Continue closing the private SID,
typed user/storage/policy and process/loader bindings, unsupported capability/UI
cuts, same-authority cache notification and protected recovery. The complete
default-off runtime candidate and all 18 device cases remain pending.

No OEM/JNI execution, phone install, setting change, reboot, root automation,
remote publication or parent ColorGlass resume occurred in this batch. The
goal remains active; this is an implementation/source checkpoint, not completion.
