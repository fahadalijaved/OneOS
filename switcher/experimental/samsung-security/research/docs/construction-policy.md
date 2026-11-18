# Captured pre-construction Samsung feature policy

Source/capture evidence only. No OEM class initialization, Android execution,
phone change or effective live-policy query occurred.

Original Samsung `SyntheticPasswordManager.<clinit>()V` reads
`SEC_FLOATING_FEATURE_COMMON_SUPPORT_UNPACK` through `SemFloatingFeature` before
storing `SECURITY_UNPACK`. The actual initializer's literal/getter PCs are 22/25
code units in logical DEX header 10,057,984. The credentials stream pins the
`SemFloatingFeature` singleton, XML load and boolean getter bodies separately.

The exact captured Samsung `system/etc/floating_feature.xml` is 46,211 bytes,
SHA256 `85d71f9af973548ca1dfcebc3186f50bf5a0b2b8eab2426ad89ce452606dcc78`.
The selected feature is absent. The original boolean getter's absent-entry
result is false. The supplied donor's exact path is also absent. Therefore this
particular missing donor file does **not** establish a differing
`SECURITY_UNPACK` value for the captured profile. It is not evidence of complete
Samsung configuration compatibility or permission to force other flags off.

[The audit](../tools/audit_constructor_policy.py) verifies the immutable physical
file index, selects one unique regular tar member with a one-MiB bound, copies
only that member into ignored firmware and freshly verifies its bytes. The
whole capture hash is inherited from the completed capture audit, not claimed
recomputed. No symlink or archive metadata is restored. It also verifies the
actual original SPM initializer receipt, archive and body identity.
The separate original `SemFloatingFeature` parser/getter receipt is pinned too,
including its Java `String.trim()` treatment. Cached runs verify the retained XML
against the pinned member hash and explicitly report that no new tar copy ran.

Reproduce from the nested project root:

```powershell
python -B tools/audit_constructor_policy.py
```

The bounded [inventory](../inventory/construction-policy.json) records the
selected feature, actual source and capture provenance. Raw XML remains ignored
in `firmware/construction-policy/`. Current host/installed guest identity and the
full reached configuration surface still require proof before original class
initialization. Optional OPPO feature removal does not supply Samsung's missing
configuration, user, storage or native owners.
