# Composed ColorOS code adaptations

**Built on PC; unselected and cold-process-only.** These are code-reader archives,
not signed/installable APKs, a working Samsung authority or a phone candidate.
No Android/OEM class, JNI or authentication operation executes during composition.

The [composer](../tools/compose_coloros_ui_removals.py) combines exact reviewed
leaves from the same immutable original input. It uses literal source and
component-receipt hashes, never the moving project checkpoint as a producer
input. A component proof change requires an explicit reviewed pin update.

| Original input | Combined changes | Retained boundary |
| --- | --- | --- |
| ColorOS SystemUI, 73,080 original classes | [Input RPMB leaf](coloros-rpmb-input-leaf.md) and [RoR/SP leaf](coloros-ror-leaf.md) | Genuine credential creation/results, normal/multiuser task cleanup, mandatory keyguard registration, real finish/StrongAuth and independent handler behavior remain preserved. |
| ColorOS framework, 38,870 original classes | [Post-PIN audit leaf](coloros-pin-metadata-leaf.md) and [error-propagation leaf](coloros-readiness.md) | Genuine setter/result and normal credential/lockout values remain. Throw propagation does not itself implement protected unknown-state UI or recovery. |
| ColorOS Settings, 78,960 original classes | [Settings RPMB leaf](coloros-settings-rpmb-leaf.md) and [retrieval capability leaf](coloros-retrieval-capability-leaf.md) | Genuine current-credential operations and independent UI/job behavior remain. Only the unsupported OPPO capability is unavailable; independent old-mode entry and retained credential/job owners remain open. |

The Settings profile normalizes the historical RPMB leaf's differently named
`selectionConditions` only for its exact frozen name/hash. Every condition is
retained under the stronger parent cold restriction. No other receipt may use
that exception, and a conflicting condition alias is refused. The Settings
profile explicitly allows a 128MiB entry for the admitted original's
123,768,068-byte `resources.arsc`; existing profiles keep their 64MiB entry bound.
The expanded archive bound remains 512MiB and the entry-count bound stays20,000.

Reproduce from the nested project:

```powershell
python -B tools/compose_coloros_ui_removals.py --profile systemui
python -B tools/compose_coloros_ui_removals.py --profile framework
python -B tools/compose_coloros_ui_removals.py --profile settings
python -B tools/test_coloros_composition.py
```

The generated wrappers stay in `out/coloros-ui-removal-composition/`.
The bounded inventories are
[SystemUI](../inventory/coloros-ui-removal-composition-systemui.json),
[framework](../inventory/coloros-ui-removal-composition-framework.json) and
[Settings](../inventory/coloros-ui-removal-composition-settings.json).

The Settings output is SHA256
`3e4800f1573e89359757a7b565d9ee4291f2e83ed3f4e71e4c7677f37ce9b88e`.
Its two components edit distinct encoded methods in `classes13.dex` and
`classes2.dex`. Every original payload is read back; inverse/roundtrip and all
78,960 class definitions are preserved. This is a code artifact, not a signed
APK or evidence of runtime-safe removal.

## Composition proof and review corrections

All original entry names/order and payloads are admitted. Non-DEX payload edits,
DEX extent changes and edits outside original method instructions are refused;
only the required DEX039 SHA1/Adler integrity fields are recomputed. Each edited
byte span must have exactly one non-aliased encoded-method owner. Two components
cannot change the same method, even at disjoint instruction bytes. Each
component's original source/branch/try/semantic proof remains necessary.

Independent review found and root corrected a partial-alias bug: containment by
one method did not exclude intersection with another. The current checker counts
every intersecting method. The review also led to resolved artifact/output
containment and strict condition-list/boolean checks, preventing a string from
becoming a list of individual characters or numeric zero from replacing false.

Restoring all edited instruction spans and resealing each DEX reproduces the
original bytes; reapplying reproduces the composed bytes. All output payloads
are reopened and compared. Exact source/component/utility pins are checked again
after composition. ZIP physical encoding and platform APK/JAR signatures are
not preserved or accepted by these checks.

The ten regression tests distinguish actual sealed DEX byte checks from
interval models. Actual-byte cases cover positive leaf equality, disjoint edits
to the same method, a code-header edit outside instructions and invalid DEX
integrity. Partial alias and adjacent-range cases are authored interval-model
tests. Condition-type and resolved `..` escape checks are local tool checks.
They are not Android/ART, live-callback, credential-write or hardware tests.
The two added cases check complete legacy Settings condition retention and
refuse an ambiguous alias; an unrecognized receipt pin gets no schema exception.

## Conditions carried forward

Composition retains the union of component selection conditions and adds a
strict fresh-process boundary. The original audit-metadata and Settings RPMB
receipts predate an explicit cold-only field; only their exact frozen hashes
are admitted under this stronger parent restriction. No arbitrary missing
cold-only declaration passes.

No original callback/job/service may already be active. In particular, the old
SP-recovery Runnable clears/cancels pending authentication before reaching a
guarded accessor; entry edits do not stop an already queued old job. Real
disconnect/drain is required for any future live transition.

The combined SystemUI cuts do not change PackageManager's feature declarations
or remove every optional recovery control. Unsupported capability/UI admission,
genuine Samsung committed-change PIN-cache invalidation, stale user/authority
generation handling, protected unknown-state presentation and safe return remain
required. Settings worker/Intent/credential retention, its static reuse cache,
old-password retrieval and mixed-job ownership remain separate open work.

The Samsung process, Context/user/policy, state and native endpoint bindings,
full reciprocal PIN/fingerprint lifecycle, app-key/CE behavior and every device
acceptance case in [GOAL.md](../GOAL.md) remain unproved. This composition cannot
be selected merely because its byte-preservation checks pass.
