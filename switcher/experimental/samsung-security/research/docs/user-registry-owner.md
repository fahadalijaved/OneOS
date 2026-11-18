# Original Samsung user-registry owner cut

Status: source/API proposal, approved for documentation only. No constructor,
OEM code, native service, private registry or phone was executed/read. The
captured Samsung services source is `def967fb…`, identified in
[the derived inventory](../inventory/user-registry-owner.json). Existing
[Gate C](authority-bootstrap-users.md), [typed user binding](security-user-binding.md)
and [state paths](construction-state.md) remain inputs. This card does not supply
a live user authority or permit eager credential cleanup.

## Construction has a smaller seam than full PMS, but two fixes are insufficient

Observed source: `UserManagerService(Context)` creates the genuine
`UserJourneyLogger` and named packages lock, obtains `Context.getCacheDir()` at
PC12 and delegates at22 with null PMS, UserDataPreparer, users array and Persona.
Those nulls are original source choices, not usable stand-ins for reached work.
The production PMS factory instead supplies `Environment.getDataDirectory()`.
The full constructor appends `system/users`; the Context-only cache directory
does not identify the original physical registry.

The full constructor stores PMS230 and UserDataPreparer399, but the first
unconditional concrete PMS demand is handler acquisition254–271. Frozen C
proves the corresponding original producer branch constructs and starts a real
`HandlerThread("UserManagerHandler")`, returning its real handler without reading
PMS/injector. The original UMS MainHandler retains UMS and that Looper. Therefore
a source-preserving handler acquisition retarget can avoid importing PMS just
for this branch. This is a proposal, not a patched DEX or executable factory.

Other eager owners remain real: visibility mediator392, user-type/default
builders401 onward, original Context resources934, registry directories/load,
SystemConfig1057 and package-type allowlist1061, LockPatternUtils1083 and
SettingsObserver1104. The selected visibility/observer constructors do not
establish running/unlocked users or register a substitute lifecycle producer.
`SystemConfig.getInstance()` can construct SystemConfig at27 when absent; its
full cold initialization is an explicit dependency, not proved harmless by this
card. The selected package allowlist computation consumes SystemConfig maps and
source type masks; it does not directly require concrete PMS.

## Original defaults and resources precede registry admission

The constructor obtains global `Resources.getSystem()`405, XML literal
18284553/`0x01170009`409 and runs `UserTypeFactory.customizeBuilders`416 over the
genuine default builders. It constructs validated original UserTypeDetails and
UserProperties, including credential-shareability and profile-visibility defaults.
The selected original factory/default helpers and parsers are pinned; no
handwritten type/default table is proposed. `UserProperties` retains its genuine
type-default relationship; filtered public copies are not LocalService objects.

The existing immutable aapt tables expose concrete collisions:

| Original consumer | Samsung resource | Same numeric ColorOS resource |
| --- | --- | --- |
| global user-type XML18284553 | `xml/config_user_types` | `xml/haptic_feedback_customization` |
| guest-start loader Boolean17891815 | `bool/config_guestUserAutoCreated` | `bool/config_hasPermanentDpad` |

ColorOS's user-type XML is18284550/`0x01170006`. The captured Samsung base XML
contains only the `user-types` root; its version is absent. The original parser
returns its zero default for absent version. This is base-APK evidence, not the
effective live overlay/configuration. Global original-resource resolution must
be selected before loading: a wrapped Context alone does not redirect getSystem.
Matching captured Boolean values (`false` here) does not close resource identity.

## Loading is potentially mutating, and publication occurs too early for a wrapper

Observed source order: `readUserListLP`1010; static singleton publication1013;
SystemConfig/package allowlist; Local UMI publication1076; initial watched state
entry1094/cache invalidation1097; observer; optional emulation; final invalidations
1382–1397; return1400. Construction failure after either publication can leave a
published partial object. Calling the unmodified constructor and checking later
is inadequate.

Before publication, original ResilientAtomicFile recovery can delete competing
or failed copies; read failures can retry and fallback. The fallback optionally
calls Persona.onUserRemoved(-1), creates system user0, sets next serial10,
initializes defaults, and persists user/list files. It must never manufacture
the missing shared authority. Successful loading can mark eligible ephemeral
users partial/removing, upgrade schema/type/restrictions, and rewrite metadata.
`upgradeIfNecessaryLP` invokes original restrictions and user-type migrations;
profile upgrades can call `updateUserRestrictionsInternalLR`. That method
schedules a user write59 and posts original restriction work96/134.

`scheduleWriteUser` uses message1, a2000ms delay25 and real MainHandler; that
handler writes the user list19 or user metadata55 under original locks. These
jobs can survive constructor return. `writeUserListLP` first calls
`setContainerInfo`, which derives the managed/secure-folder user property
`persist.sys.knox.userinfo` and writes it103; list persistence also writes the
Perfetto user list. Even an existing Perfetto list receives permissions and
restorecon. Original write errors can be logged/caught; void return is not an
atomic transaction or durability acknowledgement.

After LocalService publication, if `Build.isDebuggable()`1114 and
`persist.debug.user_mode_emulation` is nonempty1122–1133, the constructor may
rewrite system type/flags and main-user assignment (`writeUserLP`1254/1322/1365).
No such setting is assumed active or changed here. The guard must cover this
tail and its real inputs rather than assume publication means completion.

## Query owner, Persona policy and lifecycle limits

The selected LocalService roots preserve the original locked registry methods:
main ID, parent ID, UserInfo, full UserProperties and permanent-main-admin.
Running/unlocking queries consume the watched state map. `setUserState` and
LocalService `removeUserState` only update/delete that map and invalidate the
unlocked cache. They are distinct from outer UMS `removeUserState`, which removes
durable user/storage/package state.

Parent/profile/user-list leaves use real UserInfo, original profile-group rules,
partial/removing filters, source names/resources and UserProperties. They are
not equivalent to treating every numeric user0 as the same principal.
`getUserPropertiesInternal` has a virtual-user/DualDAR inner-auth branch10–27;
that realm requires its genuine LockPatternUtils/policy authority. The direct
field scans find6 UserDataPreparer and8 Persona sites in captured services; they
do not establish reflection/all-archive closure.

A concrete required-query blocker remains: public
`getProfileIds(String,IZZ)[I` unconditionally reads Persona24 and calls
`getClass()`26, then consumes `PersonaManagerService.workTabSupportLauncherUids`
29 to select genuine caller-specific filtering. Null Persona fails even for
system callers. The exact static-list scan has3 sites: initial container in
Persona clinit181, read here, replacement in Persona$14.handleMessage851.

The original replacement helper is narrow: real Context PM27 queries MAIN/HOME
activities for user0 with flags786432 at34, selects the two original launcher
package names, queries real IPackageManager PackageInfo with flags64/user0 at98,
and reads actual applicationInfo.uid106. Initializing an empty list is not proof
that this policy population completed. The source-preserving extraction candidate
is this actual producer plus its query policy/update ownership, not a fake
Persona or an assumed empty launcher table. Its refresh/admission/drain and
typed PM protocol still need a selected real provider.

Frozen direct-reference evidence records9 original watched-state producer sites:
UserController start, finish boot, stop, finish stopped, handler and asynchronous
lambdas. The constructor's initial system entry is not a current complete active
runtime snapshot. A genuine ordered lifecycle/CE/user-generation transport must
own initial completeness, concurrent updates, cache invalidation and handoff.

Full lifecycle cannot be advertised from those map methods. For an existing user,
`onBeforeStartUser` unconditionally invokes UserDataPreparer46/48 and package-data
reconciliation60/64; `onBeforeUnlockUser` does so40/43 and has managed DualDAR
storage-policy work. Creation, durable removal, reconcileUsers, quiet-mode,
ASEC, full LifeCycle callbacks and maintenance user77 reach additional real owners.
They must be refused before side effects until supported; no null/no-op service
is a solution. Genuine credential changes are not user creation/removal, and the
required shared PIN/FP/policy outcomes are not waived by this restricted cut.

## Proposed retarget and admission contract

Root approved documenting these seams only:

1. Replace Context-only cache-root acquisition12 with a trusted admitted original
   physical-registry-root supplier; preserve genuine argument factories/nulls.
2. Replace full constructor handler acquisition254–271 with the source-owned real
   HandlerThread/Looper owner; preserve MainHandler and original queued work.
3. Intercept/private-route singleton1013 and LocalServices publication1076 so no
   consumer can reach the object before final construction, queued-work admission
   and failure handling. Keep the original UMI class-key/loader identity exact.
4. Resolve global/Context original resources before loading, and extract or supply
   genuine Persona launcher policy with actual initial/update provenance.

This requires real DEX041 index/type/caller/inverse proofs and root API selection;
no same-size patch, helper signature or runtime class has been implemented here.
Before any constructor, retain the sole physical registry writer/generation,
replace-safe directory authority, source resources/configuration, handler and
publication/failure owner. Original recovery/migration writes require explicit
admission and reconciliation; preserving source behavior is not permission to
silently reset shared state. Old owner retirement must account for queued writes,
restriction callbacks and filesystem/native uncertainty. Empty Binder count,
Java return or suspended threads prove none of that.

The resulting candidate is a genuine original registry/query owner with bounded
lifecycle transport, not a full Samsung PM/AM service import. It remains blocked
on selected physical registry/resources/policy/queued-work/lifecycle authority.
No private XML, credential/enrollment state, raw secrets, saved registry snapshot
or fabricated user was read or created. Live identity, source generation,
write recovery and required cross-OS outcomes remain unverified.
