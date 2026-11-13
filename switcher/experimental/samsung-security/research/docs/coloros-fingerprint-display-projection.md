# Fingerprint display names for ColorOS Settings

`FingerprintEnrollmentPresentation.fromReport` derives display data from a
retained Samsung enrollment report. It returns one of three statuses.

| Status | Meaning for the display consumer |
| --- | --- |
| `UNAVAILABLE` | No report reached the adapter. |
| `REPORTED_EMPTY` | The query returned a report with zero rows. The Samsung wrapper can produce this on refusal or when its provider is missing. |
| `REPORTED_ROWS` | The query reported names. A partial return remains possible. |

Only `REPORTED_ROWS` exposes names. The immutable list preserves order,
duplicates and empty strings. The transport report retains the biometric,
device and group IDs and Samsung's duplicated-image count. The projection
keeps only the names, with no row or report references in its output.
[Projection source](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPresentation.java)
· [Report contract](retained-fingerprint-enrollment-report.md)

## Settings consumer boundary

In the inspected donor APK, `FingerprintSettingsFragment` binds an AndroidX
`PreferenceCategory` at PC 37 of `onCreatePreferences`. Its row builder uses
`SettingJumpWithActionPreference`, reads the name at PC 72 and sets the title
at PC 76. The same row also reaches the click listener at PC 120. Rename and
remove pair a biometric ID with the fragment's separately read user ID.
[Row builder evidence](../out/settings-fingerprint-name-log-review/r-fdc05df4/receipt.json)

Cold creation queues worker message 1007 for the independent OPPO privacy
query. Resume queues message 1010 for `initFingerprintData`, which forwards
rows to the UI and writes the fingerprint count at PC 52. The UI callback
also updates the legacy list cache and sends the list to its controllers.
Other list consumers use it for removal completion and
fingerprint-unlock policy. The original AppLock and PrivateSafe controllers
can disable their fingerprint options when that list is empty. The read-only
preference path needs a separate refresh from the admitted report source.
The OPPO privacy query is a separate compatibility obligation. Native
management requires an authoritative list bound to the live user and sensor.
[Donor consumer audit](fingerprint-frontend-adapter.md)

The staged `Fingerprint(CharSequence, int, int, long)` constructor runs the
guest's extension factory before it returns and calls `init` on the resulting
extension. The selected extension registration remains unverified. The display
projection uses the report's strings directly. Binding the original Settings
view, admitting the live Samsung caller/user/provider, and implementing genuine
management remain separate integration work.

## Dedicated preference section

The [section renderer](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceSection.java)
mounts a single owned category on a manager-bound AndroidX preference screen
on the main Looper. It uses ordinary unkeyed, nonpersistent, nonselectable
rows with no action widget. It builds the category hidden, verifies the exact
ordered rows before revealing it, then reads back the same membership again.
Closing hides and removes its category by identity. The original category,
Add preference, controllers and settings remain outside the renderer.

The donor fingerprint screen is `fingerprint_parent_screen` from
`fingerprint_settings_preferences_oplus.xml`. A future source integration can
mount the category as a sibling of the original categories only for the live
fragment view and admitted subject generation. The caller owns that lifetime,
the current report and retirement before a view or subject change. Mounting
does not perform a query. The existing dashboard refresh can replace the
screen, so the caller needs a current root check and teardown. The donor's
base preference passes a nonempty name to `TextView.setText(CharSequence)`
and hides a blank title. The two no-name states use separate caller-supplied
labels. The donor's setup and count summaries are unsuitable for an ambiguous
zero-row report. Label resources and source call sites are still unselected.

## Offline build

The SDK 37 build emitted a 3,684-byte DEX containing only the projection and its
status enum. Its only report-member references are `rows()` and `Row.name`.
The DEX has no direct Android or OEM type references. This is a compiled
component outside the selected guest and OneOS APK.
[Build receipt](../out/guest-fingerprint-display-build/r-75cff7ea/receipt.json)

The independent JVM model passed 22 checks against the exact projection and
report sources with an inert Parcel model. It checked all three states,
immutable names, order, duplicate and blank names, exact UTF-16, preserved
transport metadata, and the public API. No device or OEM code ran.
[Model receipt](../out/fingerprint-enrollment-presentation-model/r-a5ee20fc/receipt.json)

The renderer passed 124 independent JVM checks with inert AndroidX and Looper
models. The earlier source allowed an earlier row to disappear during a later
insertion or the visibility callback while mount still returned success. Both
regressions reproduced against that source. The current section checks every
row before and after reveal and clears its own category on a mismatch. The
models also check passive row flags, sibling isolation and cleanup after a
partial attachment. They do not exercise Android view rendering.
[Renderer model receipt](../out/coloros-fingerprint-preference-render-model/r-383f8232/receipt.json)

The original renderer's SDK 37 and D8 build emitted one definition in a 4,480-byte DEX.
It used five compiler-only declarations based on the donor's Preference API.
Static readback resolved all 20 emitted AndroidX method references against
the held donor declarations. The declaration and projection classes stayed
outside this DEX. The direct cached SESL build failed on Java 24 class files
under Java 21. The first declaration-based attempt stopped before compilation
because its empty classpath directory was missing. The corrected attempt passed.
[Direct attempt](../out/fingerprint-enrollment-preference-build/r-2258ad77/receipt.json)
· [Fallback setup attempt](../out/fingerprint-enrollment-preference-build/r-f097240a/receipt.json)
· [Renderer build receipt](../out/fingerprint-enrollment-preference-build/r-b1241f0a/receipt.json)

## View and subject lifetime

The [preference session](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceSession.java)
owns one passive section for one exact screen and one source-issued subject
occurrence. The main-thread owner issues one latest refresh ticket and consumes
it before changing the screen. Delivery compares the actual screen and subject
by identity. A foreign or superseded ticket cannot update the current section.
A real source change retires the session. Reopening the same screen for the
same numeric user still requires a fresh occurrence and session.

The renderer prepares hidden rows without attaching them, so the session can
hold the exact section before any insertion. It checks freshness before and
after reveal and checks the final row membership and visibility. A reentrant
close retires the session immediately and leaves the active stack responsible
for hiding and removing its own section on return. If cleanup throws, the
session refuses new work and retains the same section for an explicit close.

The donor's `onCreatePreferences` precedes the fragment view. The prospective
owner needs the exact bound screen and view lifecycle after the stock bind.
It must retire before the view stops, is destroyed, or replaces its screen,
and before an actual subject transition. A dashboard refresh can also clear
the same screen object, so identity alone does not identify a new binding.
The original fragment's numeric `mUserId` comes from an Intent and is not the
report's authenticated subject. Bind those source signals separately before
selecting this component. AndroidX schedules its visible-row refresh on a
Handler, so successful tree cleanup does not establish adapter queue drain or
immediate disappearance of cached pixels.

The independent JVM model passed 233 checks against the revised source,
including the original 124 renderer checks. It exercised exact view and
subject matching, superseded and foreign tickets, retirement during attach,
reveal and final readback, and cleanup failure followed by explicit close.
The first strict SDK 37 compile refused the Java lambda because the SDK stub
lacked the compiler's `LambdaMetafactory` method. The corrected source uses
one explicit reveal guard per session.
[Session model](../out/coloros-fingerprint-preference-session-model/r-ca176b95/receipt.json)
· [First SDK attempt](../out/fingerprint-enrollment-preference-session-build/r-526ff54f/receipt.json)

The corrected strict SDK 37 compile succeeded. Its first output review
stopped before D8 because the expected list omitted the renderer's state enum.
The final build used the saved class files and checked all five expected
definitions in a 9,264-byte DEX. The donor preference declarations, projection,
and report stayed outside the emitted DEX.
[Saved compile](../out/fingerprint-enrollment-preference-session-build/r-570222ce/receipt.json)
· [SDK and DEX receipt](../out/fingerprint-enrollment-preference-session-build/r-07454385/receipt.json)

## AndroidX view binding

The [view binding](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceViewBinding.java)
uses the actual AndroidX view lifecycle and a window attachment listener. It
requires the exact fragment view, view lifecycle owner, lifecycle and attached
preference screen. It admits refresh and delivery only after its own observer
sees `ON_START` and the live lifecycle is at least `STARTED`. An already
started registry alone does not prove a reentrantly added observer caught up.
The binding retires permanently on its own stop, destruction or detach.

The caller retains the binding before registration. The binding records each
registration before calling AndroidX because the registry can deliver events
inline. A retirement during registration defers removal until the add returns.
Cleanup failures from observer callbacks leave the binding retired and keep the
exact failed registration or section for explicit close. The original lifecycle
dispatch continues. A later begin or delivery rechecks the actual view, screen
and lifecycle before touching the session. A successful render also rechecks
the view and lifecycle before returning success.

In the held donor, `bindPreferences` sets the stock adapter at PC 14 and
attaches the screen at PC 17 before calling `onBindPreferences` at PC 20.
The no-screen branch also reaches PC 20. A future exact fragment hook must
join the actual adapter, screen and view after a genuine bind. It must retire
before unbind, same-screen rebuild or authenticated subject change. The view
binding consumes an opaque subject occurrence supplied by that future owner.
No donor call site or Samsung report source has been selected for this binding.

The strict SDK 37 and D8 build emitted one authored definition in a 5,448-byte
DEX. Static readback resolved nine AndroidX methods and four Lifecycle enum
fields against the held donor declarations. The independent JVM model passed
358 checks, including the prior 233 renderer and session checks. The added
cases exercise synchronous registration, start-level/event disagreement,
same-object reopen, detach and stop, and exact cleanup after failure. No
Android or OEM code ran.
[SDK and DEX receipt](../out/fingerprint-enrollment-preference-view-binding-build/r-e2c7942e/receipt.json)
· [View binding model](../out/coloros-fingerprint-preference-view-binding-model/r-fb28e32e/receipt.json)

## Stock adapter capture

The [bind capture](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceBindCapture.java)
tracks one exact stock bind. It takes the screen and adapter returned by the
original factory and checks the actual fragment view, lifecycle owner, screen,
list and installed adapter after the stock bind returns. The null-screen
path has no adapter receipt. A nested bind invalidates the outer attempt and
cannot publish while the outer stock stack can still replace its adapter.
An original throw aborts the exact attempt. The capture supplies a view
witness only. It does not open a report session or change the preference tree.

The SDK 37 and D8 build emitted the four capture definitions together with the
ten prior authored UI definitions. All 32 AndroidX method references resolved
against the held donor declarations. The independent JVM model passed 459
checks, including 101 new checks for stock adapter identity, overlap, abort,
reentry and stale proof refusal.
[Combined helper](../out/fingerprint-enrollment-preference-bind-capture-build/r-cc879d09/receipt.json)
· [Capture model](../out/coloros-fingerprint-preference-bind-capture-model/r-17bf0477/receipt.json)

The [static producer](../tools/prepare_guest_fingerprint_preference_bind_retarget.py)
targets only the exact donor fingerprint fragment. The bind and adapter
overrides retain the stock calls. The optional capture retires before a
changed screen or view teardown and at the stock unbind callback. The original
`onCreatePreferences` entry also retires it before the same-screen rebuild.
The unbind callback itself follows the donor's adapter detachment, which is
why the screen and view-teardown entries have their own earlier cuts.
The emitted split has six added methods and one changed original call. The
raw reader checked 26,066 original methods under symbolic reindexing, and
the inverse recovered 46,800 normalized records. It also checked the optional
field's six reads and zero writes or field handles. The reader refused
in-memory changes to the stock try range, rethrow register, forwarding
registers and an unrelated original instruction. The separate 14-definition helper fits the
held donor's 14-member DEX inventory without class collisions.
[Donor split and readback](../out/guest-fingerprint-preference-bind-retarget/r-c3842ee9/receipt.json)

The field remains unset in this dormant split. The separate fragment-owned
split below adds the field initializer. No APK was assembled, selected or
loaded.

## Report delivery owner

The [report owner](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceReportOwner.java)
uses the fragment held by the capture and the exact `BoundView` issued for its
stock adapter. The caller supplies the identity of a locally published subject
occurrence. On the main thread, the view binding and session check that both
identities are current at refresh and delivery and around reveal. A failed
source check retires the report owner permanently. Only the latest exact
refresh ticket may be consumed. Its report is projected into passive names,
reported empty, or unavailable.

The caller retains the exact owner for delivery and for retrying any failed
close. Before a subject transition, the live source must close that owner in
order. Readback alone cannot detect a subject transition that returns to the
same identity between reads. The authenticated Samsung report source is still
open. The caller owns report provenance and the live source lifetime.

The existing dormant retarget producer pins the original capture source
snapshot beside its held helper receipt. The successor source adds an
internal fragment getter for the report owner. Its classes must be built
together with the guarded session and view binding.

The guarded session and view binding passed 389 model checks, including 31
focused checks for source invalidation, reentrant close and exact listener
cleanup.
[Guard model receipt](../out/fingerprint-enrollment-preference-source-guard-model/r-49ee0041/receipt.json)

The combined owner passed 580 offline JVM checks, including 121 new checks for
stale tickets, exact bind and subject identity, reentrant invalidation during
reveal and late callbacks. The strict SDK 37 and D8 build emitted 17 authored
definitions. All 32 AndroidX method references and four lifecycle enum fields
resolved against the held donor declarations. A separate scan found no class
collisions with the donor APK's 78,960 definitions. The successor remains
unselected and no Android or OEM code ran.
[Owner model receipt](../out/coloros-fingerprint-preference-report-owner-model/r-52f7656c/receipt.json)
· [SDK and DEX receipt](../out/fingerprint-enrollment-preference-report-owner-build/r-0e334783/receipt.json)

## Stock teardown custody

The successor capture claims one exact report owner before the owner registers
any listener. A new bind, reset, screen change, teardown or failed live-bind
read invalidates the old witness before closing its owner. The stock hook
contains cleanup failures so the original Settings call can proceed. Reentry
during that cleanup cannot start another passive owner. A genuine later stock
bind can issue its own witness while the prior owner is still held. The new
witness can start a display only after the old owner's physical cleanup is
confirmed.

The acknowledgement requires the owned section and both registrations to be
absent and the relevant stacks to have returned. A nested `close()` can return
before the outer registration or render settles. Failed or deferred cleanup
retains the exact old owner for retry. A normal stop or window detach can be
reaped at the next claim. If the stock witness still matches after restart
or reattachment, a fresh display owner can use it with a fresh refresh ticket.

This establishes report retirement and preference-tree cleanup in the model.
The donor adapter posts a main-handler sync after hierarchy changes. Any
already bound recycler holder has a separate lifetime, so frame-level
retirement still requires device evidence. Live capture issuance, authenticated
report delivery and ordered subject changes still need integration.

The local completion checks passed 430 offline JVM checks, including 41 new
cases. The combined custody model passed 702, including 122 new cases for
same-root teardown, nested stock calls, cleanup failures and exact retry.
[Cleanup acknowledgement model](../out/fingerprint-enrollment-preference-cleanup-ack-model/r-5cc8287a/receipt.json)
· [Custody model](../out/coloros-fingerprint-preference-report-custody-model/r-c31bafb7/receipt.json)

The successor SDK 37 and D8 build has 17 definitions. All seven method
descriptors referenced by the dormant wrappers resolve to public instance
code. The definitions are disjoint from the donor's 78,960 definitions. The
successor remains unselected and has only offline evidence.
[SDK and DEX receipt](../out/fingerprint-enrollment-preference-retirement-build/r-fc479fc4/receipt.json)

## Fragment-owned capture split

The optional `--fragment-owned` producer emits a separate Settings
`classes2.dex` for the 17-definition helper. The first original
`onCreatePreferences` super call is the creation seam. In the held donor,
AndroidX initializes the preference manager before reaching that call. Normal
initial view binding follows in `onViewCreated`. The only other direct caller
on this AndroidX hierarchy is the existing posted bind handler. The private
field retains a successful capture through view recreation because the same
fragment can rebuild its view without rerunning preference creation.

The forwarder stores the capture only after the exact constructor returns.
When it finds an existing capture, it retires its witness and report owner
before stock preference creation. The optional setup catch covers code units
0–14. Its handler rejoins the original super call at 15 with the original
arguments. The stock call is outside the catch. A failed initial constructor
leaves the field unset until another genuine preference-creation call. This
describes the emitted control flow after class loading, with Android verifier
and runtime behavior still open.

The independent reader found six field reads, one write at code unit 9 and
zero handles. The inverse recovered all 46,800 normalized original records.
It separately checked all 26,066 original coded methods. Rebuilding the
dormant mode produced its byte-identical `733bb927…` output. Eight raw-byte
negative checks rejected wrong catch coverage, skipped stock calls, an
incorrect constructor, a second field write and cross-cohort helper inputs.
The opt-in split remains unselected. A real report source, connection to the
readiness subscription below, Android loading and release packaging are still
open.
[Fragment-owned split](../out/guest-fingerprint-preference-owner-retarget/r-6bf1c267/receipt.json)
· [Negative checks](../out/guest-fingerprint-preference-bind-fragment-review/r-48372b46/receipt.json)
· [Dormant replay](../out/guest-fingerprint-preference-bind-retarget/r-de4b81e5/receipt.json)

## Preference view readiness

The donor binds preferences during `onViewCreated`. `Fragment.performStart`
calls stock `onStart`, then the fragment registry, then the view registry.
Starting another observer inline during the view's `ON_START` can leave it
at `CREATED` until the donor registry finishes dispatch. During window
detach, the donor invokes its listener snapshot before clearing attach info.
An attachment predicate can still read true inside that callback.

The [readiness subscription](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceReadySignal.java)
is explicitly started for one exact `BoundView`. Capture retains it separately
from the report owner. It waits for its own view `ON_START`, posts one exact
main-handler pulse and rechecks the current bind, live window attachment and
view lifecycle before notifying. Stop or detach invalidates the old pulse.
The same bound view can produce a fresh signal after start or attachment if
the witness still matches. A stock rebuild invalidates the witness and closes
both passive owners. Failed or deferred cleanup retains the exact subscription
until its listener and pulse custody is clear.

The callback conveys view readiness only. A source still has to explicitly
subscribe after obtaining the live bind witness, provide the genuine subject
and report, and retire its report owner before changing that subject. The
fragment-owned split above continues to pin the earlier helper. This separate
successor has no selected Settings entry that subscribes to readiness.

The model passed 839 offline JVM checks. It exercises the observed event,
coalescing, stale pulses after stock rebind, failed cleanup, and retirement
while a post is in flight. In the reentry model, a stop followed by start
during a getter invalidates the running pulse even when the getter returns
`STARTED`. One fresh pulse can notify after the old one settles.
[Readiness model](../out/coloros-fingerprint-preference-ready-pulse-reentry-model/r-0446b091/receipt.json)

The SDK 37 and D8 build emitted 21 definitions. The compiler-only lifecycle
declaration includes the exact donor `DESTROYED` enum field, which the prior
projection omitted. The readiness classes include one empty Java 8 constructor
marker. The original constructor and all seven wrapper methods resolve in this
helper, and its definitions are disjoint from the donor's 78,960 definitions.
[Readiness build](../out/fingerprint-enrollment-preference-ready-signal-build/r-eba71a23/receipt.json)

## Passive report feed

The [feed](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceFeed.java)
joins the exact readiness subscription to a report owner for one bound view
and subject occurrence. Each readiness notification advances the phase.
The feed clears the prior request before any owner transition, waits for
the old owner's cleanup acknowledgement, and retains the new owner before
starting it. The same view can reopen after a genuine later start or attach.
A stock rebind requires a new feed for its new `BoundView`.

The source receives an opaque request wrapping the exact latest refresh.
It can respond inline or later on a settled main-queue turn. Inline delivery
consumes the request before rendering and nested refresh is refused. A newer
request supersedes the previous one. The feed checks its phase around the
subject read and supplies that guard to the renderer. Explicit null completion
renders unavailable. An empty report renders the reported-empty label.

The source owns authoritative subject and report provenance. It must close the
feed before replacing the subject, including a switch that later returns to
the same identity. It calls manual refresh or asynchronous delivery from a
settled main-queue turn and does not pump nested main-loop dispatch. Teardown
attempts both child closes and keeps their exact owners through deferred or
failed cleanup. This successor is unselected. The live donor subscription and
the Samsung report producer remain open.

The combined model passed 1,026 offline JVM checks, including 187 new checks
for queued opening, inline and late delivery, request supersession, lifecycle
reentry, subject replacement and cleanup failure.
[Feed model](../out/coloros-fingerprint-preference-feed-model/r-0c8bcf8c/receipt.json)

The SDK 37 and D8 build emitted 26 definitions, with 17 predecessor classes
byte-identical. The unchanged fragment-owned split's capture constructor and
seven wrapper methods resolve against this helper. Its definitions are
disjoint from the 78,960 donor definitions. The separate helper has no Android
execution, APK assembly or device acceptance.
[Feed build](../out/fingerprint-enrollment-preference-feed-build/r-6d623f8d/receipt.json)

## Stock bind source attachment

The [source binding](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceFeedBinding.java)
holds one explicitly attached report source on the capture. It can attach
before the first stock bind or adopt an already verified current view. The
stock finish hook offers a witness only after the original bind has returned
and the capture has cleared its bind and checking state. A failed optional
setup cannot change that stock return. No source attaches automatically.

Stock retirement first clears the witness and cuts off the old feed's request
admission. Capture then closes the exact report and readiness owners. The
source binding retains the old feed until its composite cleanup is complete.
A later genuine bind can offer a replacement while keeping the same source
registration. If an offer overlaps setup or prior cleanup, an explicit source
refresh can arm the current witness after cleanup settles. Explicit source
close retires its registration and attempts exact cleanup.

In the held donor, view recreation or a changed nonnull screen can lead to a
fresh stock bind. A same-root XML reset may retire the old feed without
scheduling another bind. The display then waits for a genuine later bind. An
aborted bind, null screen, or stale adapter supplies no witness.

The SDK 37 and D8 build emitted 27 definitions and carried 17 byte-identical
classes. Its definitions are disjoint from the 78,960 donor definitions. The
held fragment-owned split is byte-identical and its capture constructor and
seven wrapper methods resolve against this separate helper. The private donor
field still has no selected source attachment call. Live Samsung report
provenance, Android loading and device behavior remain open.
[Source attachment build](../out/fingerprint-enrollment-preference-feed-binding-build/r-16944ab9/receipt.json)

The combined model passed 1,165 offline JVM checks, including 139 for source
attachment before and after a stock bind, same-view rebind, late replies,
failed or deferred cleanup, and rearming after exact acknowledgement.
[Source attachment model](../out/coloros-fingerprint-preference-feed-binding-model/r-1c449e50/receipt.json)

## Donor source access

The optional `--source-access` split pairs the exact 27-definition helper
with one additional fragment method. `oneos$getPreferenceBind()` is
package-private and final. Its two instructions read the exact private
capture field and return the stored reference. It can return null before
preference creation or after the optional constructor fails. It does not
allocate or start a capture, change the field, or start a feed. A direct
caller needs the donor fragment's runtime package and defining loader.

The accessor name is absent from all 14 original Settings DEX members. The
new split contains seven field reads, the same one creation write and zero
field handles. An independent scan found zero accessor calls. Both earlier
producer modes reproduced their saved DEX bytes and independent readbacks.
The source-access reader rejected all six in-memory negative variants,
including public visibility, altered registers, an extra write and mismatched
helper or candidate inputs.
[Source-access split](../out/guest-fingerprint-preference-source-access-retarget/r-951960aa/receipt.json)
· [Negative cases](../out/guest-fingerprint-preference-source-access-review/r-0660196a/receipt.json)
· [Dormant replay](../out/guest-fingerprint-preference-bind-retarget/r-ed728741/receipt.json)
· [Fragment-owned replay](../out/guest-fingerprint-preference-owner-retarget/r-53857c40/receipt.json)

Stock `OplusFingerprintSettings` routes to the fragment by class name. It
holds no instance for report delivery. A future same-package source needs the
exact created fragment and a settled main-queue turn. It must retain its own
source registration and the same capture, then use the exact current bind
when the view becomes ready. The accessor carries reference identity only.
It supplies no Samsung report authority or live attachment.

The original donor Settings APK declares `com.android.settings` with shared
UID `android.uid.system`. API 37 `apksigner verify` validated the held
original's v3 signature. A modified APK needs a separately proven compatible
signing and loading path. The split is unselected and no APK was assembled.
[Original donor signature](../out/guest-fingerprint-settings-signer-review/r-cfd0125b/receipt.json)

### Prepare a binding for the created fragment

The same-package source entry takes the exact donor fingerprint fragment
and an explicitly supplied subject and report listener. It runs on the
main thread and waits for the canonical AndroidX fragment lifecycle to
reach `CREATED`. The donor creates the capture before calling stock
`onCreatePreferences`. `Fragment.performCreate` calls stock `onCreate`
at PC 21 and sends `ON_CREATE` at PC 34 after it returns. A nonnull
capture alone is therefore insufficient to admit a source.

The entry calls the held package-private accessor and checks the capture's
own fragment by identity. It returns the existing feed binding for the
caller to retain before `start()`. Preparation does not publish a claim,
request a report, poll the subject or change preferences. The existing
binding owns the one capture claim and rejects requests retired by stock
view replacement. The caller must close the exact binding when the
fragment or source subject retires and retain it through failed cleanup.
[Source entry](../compat/guest-fingerprint-display/com/oplus/settings/feature/fingerprint/OneOsFingerprintDisplaySource.java) · [Capture](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceBindCapture.java)

In the donor `FragmentStateManager.create`, `performCreate` at PC 61
precedes `dispatchOnFragmentCreated` at PC 68. An exact-manager callback
there can supply the created instance. The fragment's own `ON_DESTROY`
in `performDestroy` precedes stock `onDestroy` and can retire the source.
The view's `ON_DESTROY` retires the current feed while allowing a later
view to bind. No stock lifecycle body is changed by this entry. A live
Settings fragment callback, authenticated report issuer, compatible
Settings loading and Android execution remain open.

The JVM fixture passed 223 focused checks and the existing 1,240 binding
and 43 multi-row cleanup checks. It refused pre-creation, destroyed,
off-main and foreign-capture entry, and rejected late replies after view,
fragment or subject replacement. Removing the identity check in a test
copy failed the foreign-capture case.
[JVM receipt](../out/coloros-fingerprint-display-source-model/r-dfe8746e/receipt.json)

## Refresh after a failed stock rebind cleanup

A stock rebind can retire the old feed and publish a new view while the
optional category's cleanup throws. Previously, manual refresh forwarded
to that retired feed and could remain stuck until another rebind. The source
binding now remembers the retired feed. Explicit refresh retries its exact
cleanup, waits for acknowledgement, and reads the current bound view again
before arming a new request. Old replies remain retired throughout.

The differential JVM fixture reproduced the failure on the predecessor
after its 1,165 existing checks. The successor passed 1,204 checks, including
reentry during cleanup and source close before a replacement could arm.
SDK 37 compilation and D8 emitted the same 27 definitions, with 26 class
files byte-identical and the donor wrapper's public call targets unchanged.
[Differential model](../out/coloros-fingerprint-feed-retirement-retry/receipt.json)
· [SDK build](../out/fingerprint-enrollment-preference-feed-binding-recovery-build/r-2be64797/receipt.json)

## Combined Settings code archive

The offline composition carries the original 14 DEX members, with reviewed
changes in two of them, plus the rebuilt helper in `classes15.dex`.
It relocates the two existing `classes2.dex` edits into the source-access
split by their exact method and instruction locations. The inverse recovers
the exact structural split. The `classes13.dex` member retains both the
RPMB and progress-log edits. The manifest, resources and other existing
payloads remain byte-identical to the donor. The 15 DEX members contain
78,987 unique definitions, including the 27 authored helper definitions.

This unsigned code archive remains unselected. Compatible Settings signing
and loading, the actual same-package caller, and an authenticated enrollment
report source still need proof before the passive UI can run in ColorOS.
[Composition receipt](../out/settings-fingerprint-display-composition/r-7edf896b/receipt.json)

## Settings package verification and OneOS delivery

The captured stock OneOS 0.4.59/code 85 package lists 30 payloads for
`x9u-in-sultra`. Its two APK rows are `KeKeThemeSpace_patched.apk` and
`OneOSGuest.apk`. Those rows and the 19 script rows reconstruct the observed
49-row stage manifest. The root receiver limits each ordinary payload to
268,435,456 bytes. The captured package supplies no Settings replacement slot.
The running guest's Settings path, hash and signer still need observation.
[Installed package and stage evidence](installed-oneos-code-profile.md#current-0459--code-85-baseline)

The donor Settings package is `com.android.settings`, version code 17000000,
with shared UID `android.uid.system`. The original donor passed API 37 v3
verification with the pinned certificate `e4980240…`. The donor's general
dashboard tile registry requires a category, which the fingerprint fragment
lacks. Its preference screen and controller factories are built into Settings.
A compatible replacement needs authorized signing and a reviewed provisioning
path for this guest profile. [Donor signature](../out/guest-fingerprint-settings-signer-review/r-cfd0125b/receipt.json)
· [Android signing and shared UIDs](https://source.android.com/docs/security/features/apksigning)

SDK 37 `zipalign -P 16 4` produced a 280,288,020-byte unsigned signing
input with SHA-256 `ee74b341…`. The stored native library offsets and other
ZIP alignment passed the read-only check. All 10,550 expanded payloads,
compression methods and entry order match the reviewed code archive. The
aligned input exceeds the stock receive limit by 11,852,564 bytes. The
alignment result covers archive offsets. Native ELF and Android runtime
acceptance remain open.
[Alignment and verification receipt](../out/guest-settings-apk-verification/r-aaf9927f-snapshot/receipt.json)

The [offline verifier](../tools/verify_guest_settings_apk.py) requires a
separately reviewed whole-file digest for the candidate. Its `display`
profile checks the entire payload and manifest against the reviewed archive,
then requires the exact donor signer under API 37 and checks alignment on
the same private, hash-verified copy. The original donor passed the separate
`donor-control` profile. The aligned display archive matched the payload
and was refused at the cryptographic signature check. Eight malformed signer
outputs and five malformed ZIP cases were refused. A successful future
offline check still leaves PackageManager shared-UID admission and live
loading to verify.

## Retire cached row titles

The donor AndroidX adapter schedules its visible-list rebuild. It can still
hold an authored row after the category is detached. A later bind reads
that row's current title. Without a scrub, it can copy a previous report's
name again after the old section acknowledged cleanup.

The [section owner](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceSection.java)
now enters its closing state before calling AndroidX. It clears the titles
of the exact owned rows, including rows in a category that Settings already
detached. Close succeeds after the category is detached and every owned
title reads back null. A failure retains a retryable retired section. A
nested close cannot acknowledge cleanup, and a retired section cannot show
again. Stock rows stay outside the scrub.

The donor's later bind hides an empty title without copying the old name.
An already-bound text view or a cached accessibility node has its own
lifetime. This closes the stale row-title path after acknowledged cleanup.
Visual retirement of existing holders still needs Android evidence.

The predecessor passed the original 1,204 modeled checks, then failed
when the retained adapter row supplied a retired name. The successor
passed 1,240 checks, including 36 focused checks for detached rows, a
transient setter failure, nested close, final title readback, retry and
stock row identity. SDK 37 and D8 retained all 27 definitions and the
donor-facing bridge ABI. The only changed classes are the section and its
private state enum.
[Differential fixture](../out/coloros-fingerprint-row-title-retirement/r-953b0028/receipt.json)
· [SDK build](../out/fingerprint-enrollment-preference-section-sdk-build/r-4eec9e9a/receipt.json)

The [archive refresher](../tools/refresh_coloros_settings_display_helper.py)
replaced only `classes15.dex` and verified the other 10,549 payloads
against the prior code ZIP. The 280,288,448-byte unsigned result passed
SDK 37 alignment checks. The verifier's `display` profile now pins the
updated payload. The donor control passed, the old display helper failed
payload comparison, and the new unsigned archive reached the signature
check and was refused.
[Aligned archive receipt](../out/settings-fingerprint-display-retirement/r-e0576fde/receipt.json)
· [Current verifier receipt](../out/guest-settings-apk-verification/r-e0576fde-display/receipt.json)

### Continue retirement after a failed row update

The donor `Preference.setTitle` writes `mTitle` before synchronously
notifying its listener. The adapter sends the row change to RecyclerView,
whose observer can throw during layout or scroll. This can clear the
current row and leave later rows untouched under the earlier cleanup loop.
The successor attempts every exact owned row, then independently attempts
to hide and detach the category from its original screen. It preserves the
first thrown failure and records later distinct failures on it. The owner
must retry the same section and read back detachment and null titles before
it acknowledges cleanup. A failure still prevents replacement.

The predecessor reproduced the skipped later rows and visible category.
The successor passed 43 focused checks, including an error before the
title write and a donor-shaped notification error after it. The model also
passed the 1,240-check suite with its earlier attachment expectations
updated to reflect the deliberate hide-and-detach attempt on failure.
[Predecessor](../out/coloros-fingerprint-multi-row-close-model/r-47a4bcc5/receipt.json) · [Successor](../out/coloros-fingerprint-multi-row-close-model/r-fcebab11/receipt.json)

SDK 37 compilation and D8 retained all 27 helper definitions. Only the
section class changed in the compiled class set, with its public ABI
preserved. This successor is an unselected helper build. The aligned
archive above still contains the earlier helper, and compatible Settings
signing and delivery remain open. A donor rebind hides the empty title
without erasing the prior text buffer. RecyclerView text and accessibility
nodes already bound before retirement still need separate Android verification.
[Section source](../compat/android/com/appleexploit/oneos/security/transport/FingerprintEnrollmentPreferenceSection.java) · [SDK receipt](../out/fingerprint-enrollment-preference-section-sdk-build/r-2382b931/receipt.json)
