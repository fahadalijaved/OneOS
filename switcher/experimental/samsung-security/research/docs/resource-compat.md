# Samsung security resources against the supplied ColorOS table

Observed static facts: two of three selected Samsung service resource IDs resolve
to unrelated entries in the supplied ColorOS framework resource APK. The IDs still
have the expected types, so a type-correct read can silently obtain the wrong
meaning. One same-named security boolean also has a different base value; matching
resource names alone would not preserve the Samsung base configuration.

This is an offline base-table comparison, not a measured result from either
runtime's effective Resources/overlays. No framework/OEM code or credential
operation was executed, and no phone state was read or modified for this task.

| Actual Samsung compiled lookup | Samsung base table | ColorOS at the **same numeric ID** | ColorOS entry with the **Samsung name** |
| --- | --- | --- | --- |
| `SemUtils.isKeyguard(Context,String)`, getString17040392 (`0x01040408`) | `string/config_keyguardComponent` = `com.android.systemui/com.android.systemui.keyguard.KeyguardService` | `string/duration_minutes_relative` = `{count, plural, =1 {# minute ago} other {# minutes ago} }` (default) | `0x010402f5`, same keyguard component string |
| `LockSettingsService.<init>(Injector)`, getBoolean17891991 (`0x01110297`) | `bool/config_softwareLskfRateLimiterEnforcing` = **false** | `bool/config_startDreamImmediatelyOnDock` = **true** | `0x01110293`, `config_softwareLskfRateLimiterEnforcing` = **true** |
| `LockSettingsService.migrateUserToSpWithBoundKeysLocked(int)`, getBoolean17891665 (`0x01110151`) | `bool/config_disableWeaverOnUnsecuredUsers` = **false** | Same name and value: **false** | Same ID/name/value |

The aligned third case is a control: neither uniform ID equivalence nor uniform
ID displacement is assumed. Names, IDs, types and default values were derived
independently from both complete resource-table dumps. Only these three selected
facts and their hashes are committed; raw tables remain ignored.

## Actual source edges

All three methods are in the captured Samsung `services.jar` SHA256
`def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6`.

- `SemUtils.isKeyguard(Context,String)` is in logical header0. Literal PC18
  (decimal code units, hex`0x12`) feeds `Resources.getString` immediately at PC21.
  The same body contains `android.permission.USE_BIOMETRIC_INTERNAL`; the resource
  comparison does not replace or grant that permission check.
- `LockSettingsService.<init>(Injector)` is in logical header10,057,984. Literal
  PC`0x1c2` feeds `Resources.getBoolean` at`0x1c5`; the subsequent constructor
  sequence constructs `SoftwareRateLimiter`.
- `migrateUserToSpWithBoundKeysLocked(int)` is in the same second header. Literal
  PC`0x59` feeds `getBoolean` at`0x5c`; the selected method also contains the
  original `config_disableWeaverOnUnsecuredUsers=true` log path.

The audit verifies exact method signatures, body hashes, literal/getter PCs and
the direct register edge. Literal integers and getter method references are also
checked directly from the original full-container DEX code item/tables with the
independent byte reader. No logical header or data offsets are rebased.

## Byte identity and acquisition

| Resource APK | Bytes | SHA256 |
| --- | ---: | --- |
| Captured Samsung `system/framework/framework-res.apk` | 16,899,413 | `86049c09ad8b1c6b955e681093915b4bd7d8b3aa9447066440034a46eb8ce290` |
| Supplied ColorOS `system/framework/framework-res.apk` | 35,173,827 | `52c3fd4e8b251a861b5b0412f62af11749408fcd4561fdbb56b1df1b4bc7cd5e` |

The Samsung APK was copied selectively as one unique regular member from the
already verified immutable mounted-OS tar, into this project's ignored
`firmware/resource-compat/`. Its size/hash was freshly matched to the pinned
physical file index. No symlink, mode, owner or other tar member was extracted.
The full20.4GB tar hash is referenced from the independent capture/comparison
receipt rather than falsely claimed recomputed here. ColorOS bytes are read
directly from the parent supplied extraction. The existing pinned SDK37 AAPT2
dumped both tables; APK/tool/callsite hashes are checked before/after.

Reproduce from the nested project root:

```powershell
python -B tools/audit_security_resources.py
```

`inventory/resource-compat.json` contains exact selected values, configuration
counts/hashes, original callsite proofs and provenance. Raw AAPT2 tables and the
copied APK stay under ignored `firmware/resource-compat/`; logs stay under
`out/resource-compat/`. The common reader sources remain frozen and unchanged.

## Resource-compatible Context boundary

Inference from the observed tables: unchanged Samsung compiled literals cannot
be assumed compatible with a guest Context that resolves the supplied ColorOS
base table. In the keyguard case the same-ID lookup returns a duration string,
not a component name. In the rate-limiter case it returns an unrelated true
boolean; remapping by name still returns a different base-policy default. These
facts invalidate resource-identity equivalence, but do not by themselves establish
a particular runtime exception, authentication bypass or active policy value.

An owned resource-compatible Context, if that architecture is selected, must bind
the intended authority's exact resource identity, configuration and effective
overlay policy for every reached resource lookup. It must retain the real asset/
package lifetime and preserve the independent Binder caller, permission and user
identity checks. Returning a few hard-coded values is not evidence of a complete
resource contract; copying Samsung's false base value into the guest would not
prove preservation of the live Samsung policy and must not be treated as a policy
change authorized by this audit.

Missing evidence: effective RRO/idmap/resource-loader values, installed guest
resource identity, configuration/SKU selection and the full transitive resource
surface of transplanted services. A design retaining the actual Samsung authority
and its real Context may avoid this particular guest-resource lookup boundary;
the finding does not mandate transplantation, a broker or a whole framework.
Credential/protector/HAT/KeyMint namespace and runtime security acceptance remain
separate, unproven contracts.
