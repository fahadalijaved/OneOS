# Minimal retained-host property profile: independent review

**A complete guest property runtime is not yet a proven prerequisite.** The existing plan establishes that shared mutation plus broad restore is incoherent with a live retained host. It does not establish an unavoidable required guest/Samsung value conflict. Prefer testing a finite source-adapted profile that preserves genuine host values, removes optional OPPO property-driven actions, and admits guest additions only with explicit ownership. This is an initial candidate, not functional ColorOS boot evidence or a selected implementation.

## Concrete smaller cut: optional OPPO boot-clock action

Four bounded static queries read actual staged `oplus-services_patched.jar` SHA `a854468f…`: one declaration, two exact methods and one exact interface-reference query. No OEM class or native method ran.

`OplusNewNetworkTimeUpdateServiceFeature.checkSystemTime()V` reads `persist.sys.device_first_boot` with default **true** at PC16. Its first-boot flag also depends on `isBootFromOplusOta()`; no actual branch outcome is assumed. It writes that property to `0` at43/55 and can call `SystemClock.setCurrentTimeMillis` at178. Even a false first-boot value does not exclude its independent `currentTimeMillis < 50,000,000` path. Thus a private property area or forced false value alone does not fence this non-property clock-setting request. The calendar month is feature-dependent, so the script's “1 January” description is not universally exact.

The actual `NetworkTimeUpdateServiceExtImpl.checkSystemTime()V` wrapper contains exactly four instructions: lazy-feature getter0, result3, interface call4 and void return7. A source-supported candidate is to exclude this optional OPPO boot-clock action **before its getter**, preserving genuine Samsung time authority. This removes the identified override rationale without fabricating a clock-set result or altering credential/StrongAuth/encryption policy. It is not a patch or proof that all guest clock writers are closed. The one matching interface reference is local to this archive, not complete reflection/native/other-archive reachability.

## Host-preserving profile and actual blockers

The current generic `guest_props` importer already skips host-defined names at147 and excludes selected security/crypto/boot/attestation families at154–159. These are useful constraints, not permission to import every remaining value. An absent key can still affect a reader's default; an OPPO prefix does not prove host non-use. Explicit exceptions bypass the generic importer.

A minimal candidate would:

- Preserve genuine host identity, privilege, crypto, user, credential and biometric inputs, with no donor debug/security defaults or copied policy values.
- Remove global property imports/overrides and broad restore together. Supply necessary guest-specific configuration through individually admitted source seams; remove unsupported optional consumers rather than modify host values for their parity.
- Admit a shared additive guest key only after its exact value/default, required reader, real writer, persistent owner, lifecycle and applicable host effects are established. No key is approved by this review. Prefer owned guest configuration when global-property ownership is unproved.
- Retain deliberately shared init/hardware commands only through their genuine reviewed control owner; they are not ordinary guest configuration to redirect indiscriminately.

This does **not** mean merely deleting today's writes makes the unchanged launcher work. Actual `guest_start`703 requires `persist.sys.disable_rescue` true;704 refuses true `persist.sys.enable_rescue`. Preserving different genuine host values therefore refuses that unchanged path. Resolve the actual guest rescue/recovery consumer and owner before adapting the guard; never just remove it or weaken real Samsung recovery/policy. The source comment is not independent proof of the entire crashrecovery call graph.

Runtime writers remain relevant too: the earlier staged user-data proof writes `sys.user.<id>.ce_available`. Neither its name nor guarded native calls prove physical Samsung CE state. Its real lifecycle/state owner remains necessary; suppression or synthetic availability is not a valid shortcut.

## Broad restore has no safe “added-only” substitute

`restore-persist --added-only` skips saved-value replacement at978/979, but still runs the unfiltered deletion loop970–975. A legitimate retained-host persistent key created after the snapshot can be deleted. Normal restore can also overwrite a later legitimate host update, including the previously source-proved Samsung UMS `persist.sys.knox.userinfo` writer. Prefix filtering and a trusted snapshot do not identify the author of a change. Do not retain these algorithms as guest-owned cleanup; avoid shared writes or establish actual per-key ownership and writer retirement.

The decisive falsifier for this minimal candidate is a required, non-removable consumer that needs an incompatible value while a genuine host/shared-native consumer needs another value, with no valid narrower source/protocol adaptation. That has not been demonstrated. A private native property runtime remains an option if such evidence appears, and would need its own bootstrap, persistent-write and callback ownership. Current missing manifest/default/consumer evidence proves neither that runtime's necessity nor property-free boot.

Power's final [minimal-cut card](retained-property-minimal-cut.md), document `80e1c62c…`/inventory `b5a7193d…`, is coherent with this disposition. Its eleven-file/776-key donor bag is explicitly a candidate, not installed ordering, host absence or required-consumer proof. This review did not repeat that catalog or its48 assertions. Its clock wording now correctly stops at the non-property API request; downstream/native execution remains unproved. No broader property service, additive key or runtime route is admitted by either card.

All prior frozen files remain unedited by this review; this is not a fresh verification of the entire662-file checkpoint. Only new reports, ignored proof metadata and four static-reader outputs were written. No phone action, property write, original service execution, compile, model replay or boot test occurred. All18 full-goal device cases remain pending.
