# ColorOS Settings fingerprint name logging

The donor Settings row builder reads each fingerprint name twice. The read at
PC 72 supplies the visible title. The separate read at PC 96 feeds
`LogUtils.d` at PC 107. That helper can deliver the message to Android logging
and to the OEM local log writer. Removing the second path preserves the name
that the user sees and the row object used by the original action listener.

The [exact producer](../tools/build_coloros_settings_fingerprint_name_log_leaf.py)
admits only the captured donor Settings APK `33b0173b` and its
`classes2.dex` `f063e7b9`. In
`OplusFingerprintSettings$FingerprintSettingsFragment.addFingerprintItemPreferences(List)`,
it replaces the 24 code units at PCs 86 through 109 with NOPs. The original
method has no try handlers or debug item, and no branch targets the removed
instructions. PC 110 overwrites the removed scratch register `v8` before
the next use. The remaining code never reads `v9`. The title, order,
preference insertion, listener, and original count code remain byte-identical.

The [leaf receipt](../out/settings-fingerprint-name-log-leaf/r-3710aa3f/receipt.json)
records the 5,737,616-byte output DEX `bea7993c`. The locator checks all
26,066 encoded code items in the source DEX for ownership and overlap.
Outside the 48-byte window, only the DEX signature and checksum change. Exact
inverse and roundtrip reproduce the original and output DEX respectively.
An [independent decoder](../out/settings-fingerprint-name-log-review/r-fdc05df4/receipt.json)
confirmed the preserved prefix and tail and the patched normalized body
`57b313cf`. Eight altered source inputs were refused in an
[independent model](../out/coloros-settings-fingerprint-name-log-leaf-review/r-4bc0fb38/receipt.json),
which also refused two branch targets into the cut.
The artifact stays unselected and offline.

The [composed archive receipt](../out/settings-fingerprint-name-log-composition/r-9db92f49/receipt.json)
pins the name-log cut with the earlier Settings RPMB and retrieval-capability
leaves. The three edits own distinct methods in `classes2.dex` and
`classes13.dex`. The remaining 10,547 archive entry payloads are unchanged
and the original entry order is preserved. The ZIP is an unselected PC
code archive.

The cut covers one diagnostic path in the captured donor APK. The genuine
Samsung list still needs a bound caller, admitted user and provider, and
authoritative list readiness. Existing Settings count persistence, clone
lookups and removal callbacks need separate adaptation before they can
consume Samsung reports. In particular, the removal path can treat an empty
requery as zero and change unlock settings. [Report contract](retained-fingerprint-enrollment-report.md)

## Enrollment progress entry diagnostic

The [progress leaf](../tools/build_coloros_settings_fingerprint_progress_log_leaf.py)
removes two instruction ranges, PCs 0–17 and 20–22, from the donor's private
`FingerprintEnrollProcessor.onEnrollProgress(I)V`. They construct and log
the raw remaining-count debug message. PC 18 still loads the tag for the
original invalid-progress warning. The availability gate, stored progress
and completion state, and listener callback keep their exact instructions.
The availability helper still has its own progress diagnostics.

The output DEX `f4217ab6…` changes only that method and its DEX integrity
fields. The inverse restores the exact donor DEX. The composition places
this edit beside the earlier RPMB edit in the same `classes13.dex`, with
independent method ownership and an exact inverse to the common donor.
It changes one of the predecessor ZIP's 10,549 expanded payloads.
[Leaf receipt](../out/settings-fingerprint-progress-log-leaf/r-9da841e2/receipt.json)
· [Composition receipt](../out/settings-fingerprint-progress-log-composition/r-8c80bd26/receipt.json)
