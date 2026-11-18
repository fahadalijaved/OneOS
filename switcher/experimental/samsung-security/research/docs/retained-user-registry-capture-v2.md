# Storage identity cross-check successor

Status: **unselected, capture-only successor**. The original capture report,
inventory, receipt and 157-file manifest remain unchanged. Exact v1 source and
builder beforeimages are preserved in
`out/retained-user-registry-capture-v2/history/v1/`. The v1 diagnostic APK
finalizer completed before canonical source changed. This document records a
narrow same-process identity comparison, not new authority or readiness.

V2 adds only this package-private API to the production Java source:

```java
void checkStorageOwnersForControl(Object actualSms, Object actualSmi) {
    checkStillBound();
    require(actualSms == owners[11] && actualSmi == owners[10], "storage owners differ");
}
```

The original owner array stores the actual retained SMS at index 11 and its
concrete local implementation at index 10. The existing main-only consistency
check executes first and retains its original errors. A mismatch throws the
fixed IllegalStateException; it cannot refresh roots or return an owner. The
public capture/check APIs, original metadata/root selection, loader rules and
five read-access preparations are unchanged. Companion access still requires
the same runtime package, including defining classloader.

This closes a specific prospective composition gap: a self-consistent security
family with SMS A / SMI A could otherwise share the captured SSM and loader while
the registry retained SMS B / SMI B. The family must supply its actual stored
references to this method before using that composition. Identity agreement
does not authenticate code, attest native ownership, freeze future mutation or
issue a source/policy generation. It has no retirement or drain effect.

The successor builder uses separate `out/retained-user-registry-capture-v2/` and
`inventory/retained-user-registry-capture-v2.json` paths. It retains the original
isolated SDK compile/D8/model boundary. New authored model cases admit the same
actual pair, reject an internally parent-linked alternate pair despite shared
SSM/loader, reject mixed/null pairs, preserve refusal after captured-root drift,
and reject worker-thread or foreign-defining-loader access. They execute the
unchanged SDK-compiled production classes, with authored runtime models only.

Production source SHA256:
`521ebfdf2f5c5d5a1c37508d455e3e9b9040dad1ec9b956baf4e99aa8da76454`.
Builder SHA256:
`9771a4a220b1072c8810daaa5bf81bbc6af6baa25864051a7b1ee76854327350`.
The normalized-text production diff is
`out/retained-user-registry-capture-v2/source-v1-v2.diff`; the original source
contract remains `ef1f6ae4…` / inventory `40c27af0…` with its six actual
publication key/value/parent proofs. V1 source used LF and this successor uses
CRLF; the byte hashes record that formatting difference explicitly. No
unchanged-byte claim is made for the source or newly compiled output.

After independent source/model-design clearance, the single approved run
completed with exit 0 at
`out/retained-user-registry-capture-v2/20261106T035214175168Z-bb7e88e8130640029e5bf4a87a4b7f5b/`.
The receipt and successor inventory share SHA256
`52068829cc583174347277fd8db05bf6ab51a422811426ae15567b0fc71cc99c`.
All nine command stages completed with exit 0. The exact SDK-compiled outer
class SHA256 is
`8c23983a42f11f8c4f1c11594c4504ca34ba5aac3288d09ad2887d3723c4ccae`;
Metadata is
`096443d1f339f6ff3589cf6eb9b7b94eeecf910296cc27ddbc113a4a93824b03`.
Both were unchanged before/after D8 and model execution. The 12,904-byte DEX039
has precisely those two authored definitions and verified integrity, SHA256
`b355a1a81b42afc229f84cec18c60f299795c947bcc974c27e1256db83425586`.
D8's API37 unsupported/max36 warning remains in the actual log.

The actual compiled classes passed **64 scenarios / 84 checks** using the fifty
authored model source files. The prior acquisition, exact publication keys,
owner links, replacement, loader and access cases remain; the new comparison
cases exercise the actual package-private method through an authored peer in
the same runtime package. A peer loaded separately fails IllegalAccessError.
All inherited five-variable environment sanitation, owned cwd/temp/home,
empty-native directory and 45-second/2-MiB per-command limits remain. No SDK or
OEM runtime input appears on the model runtime classpath. Independent saved
output review is tracked separately, without a second production run.

All original runtime limitations remain: actual ART access, admitted live
placement/code, coherent user/policy generation, native/filesystem custody,
producer fencing, guest lifecycle and device security cases remain external.
No OEM/SDK runtime, native method, phone action or global change is authorized
or performed by this component's PC build.

## UMS cached storage owner successor

The held Samsung `UserManagerService.mStorageManagerInternal` is a public
instance field of the exact concrete `StorageManagerInternalImpl` type.
In `onBeforeUnlockUser`, the read at PC 132 branches at PC 134 directly to the
same field at PC 146 when populated. The null branch obtains the concrete
class from `LocalServices` and stores it at PC 144. The same field has
independently verified lazy fills in user creation and state removal. The
actual SMS lifecycle publishes its concrete SMI at PC 537. A populated
different UMS cache can therefore bypass the published storage owner.
[Pinned Samsung method evidence](../inventory/samsung-user-registry-lifecycle.json)

The [current capture source](../compat/android/com/appleexploit/oneos/security/authority/PreparedRetainedUserRegistryCapture.java)
checks that cached reference after validating the published SMI and its SMS
parent. It rejects a different observed object, including a different SMI
with the same SMS parent. Null preserves the existing capture behavior. The
check reads the public field and leaves it untouched. The cache is outside the
18-reference retained record, so a transition from null to the same exact
SMI does not count as a change to the retained graph.

This proves the authored check for sampled Java object identity. A null
sample leaves the cached link unresolved. The field is nonvolatile, so the
two reads provide no atomic snapshot or continuous lifetime proof. Actual
ART admission, native storage, CE state, handoff and drain remain open. The
historical v2 APK and source/build pins remain held, and the new source is
unselected for a device candidate.

The SDK 37/D8 successor emitted two authored definitions and preserved the
existing member signatures and flags, including `contextForControl()`.
Removing the three added lines recovers the exact immediate predecessor
`c88d076a…`. The two-cohort JVM model passed 72 scenarios and 109 checks on
each compiled cohort. The predecessor admits the two foreign-cache shapes at
capture and recheck. The successor rejects all four mismatches, preserves
null and admits the exact populated SMI.
[Successor build](../out/retained-user-registry-cache-identity-build/r-fbe5fe25/receipt.json)
· [Two-cohort model](../out/retained-user-registry-smi-model/r-75e55e036f/receipt.json)

## User-data preparer cached storage owner

The exact Samsung `UserDataPreparer` also has a public, nonvolatile field of
the same concrete SMI type. Its `prepareUserDataLI` reads `mSmInternal` at
PC 51 and branches to PC 65 when populated, bypassing the lookup and cache
write. It then calls the cached object's SMS parent at PC 72. Its
`destroyUserDataLI` takes the same pattern from PC 58 to PC 72, then reaches
the cached object's SMS parent and `mVold`. This is a second independent
consumer of the published storage owner.
[Pinned method readback](../out/tooling/20261106T025907355416Z-040ccb64a64f4a98984cf7f460462543/receipt.json)

The current capture checks each populated cache independently against the
same published SMI. It leaves both null values untouched. The record still
retains 18 original references and adds no method signature or access
override. Dynamic storage-user connections and queued app-data callbacks
have distinct owner lifetimes outside this check.

The full 17-source host-control SDK 37 build includes both cache checks.
Independent readback verified 55 program classes and two compiler-only
definitions. Only the capture's Metadata class differs from the held
full-cohort predecessor. The prior registry-only DEX still covers only the
UMS check. The two-cohort model passed 80 scenarios and 134 checks per
cohort. It demonstrated four preparer mismatch cases the UMS-only build
accepted and the full successor rejects. The full successor remains offline
and unselected.
[Full cohort build](../out/closed-root-host-link-cache-identity-build/r-75cad368/receipt.json)
· [Two-cohort preparer model](../out/retained-user-registry-preparer-cache-model/r-68be32efde/receipt.json)
