# Samsung fingerprint construction frontier

**Observed:** the original Samsung service can be traced to a concrete provider,
registry and native-session graph. Its construction starts observable work and
can reach enrollment metadata and the HAL before an explicit authentication
request. **Missing:** a source-closed guest assembly, exclusive authority handoff,
correct current enrollment binding, teardown and functioning biometrics. This
report does not establish any of those runtime outcomes.

This is the recorded SM-S948U1/API37 source profile in [GOAL.md](../GOAL.md), not a
fresh device assertion. All work was offline. No OEM/JNI/service code ran, no
device was contacted and no credential/enrollment material was read. Original
ColorOS sources are comparison inputs; patched/installed OneOS remains unproved.

The exact owner/signature, raw path/line, instruction PCs, normalized hashes and
reader receipts are in [construction-fingerprint.json](../inventory/construction-fingerprint.json).
The reproducible authored driver is [audit_fingerprint_construction.py](../tools/audit_fingerprint_construction.py).
It revalidates 18 earlier bodies and 45 newly selected bodies with 22 concrete
source assertions. The scopes overlap earlier research; these counts are not
closure or compatibility scores. Samsung services/framework pins remain
`def967fb…639f6` / `8095a9ae…71fe`; original ColorOS services/framework remain
`66d0d51d…df3` / `d5c6b7fd…bcd2`. Full hashes and immutable declaration-index hashes
are in the inventory. DEX041 logical container headers are preserved unchanged.

From the child project, `python tools/audit_fingerprint_construction.py` validates
the saved evidence and regenerates the derived inventory. The four explicit
`--collect`, `--collect-extra`, `--collect-factory`, `--collect-framework` switches
select bounded source reads with the existing shared reader; they execute no OEM
class. Raw bodies stay ignored under `firmware/construction-fingerprint/`.

**Observed construction and registration order:**

| Boundary | Real inputs and side effects | Evidence, DEX PC |
| --- | --- | --- |
| `FingerprintService(Context)` | Acquires the real `BiometricContext` singleton before delegation. The injected constructor retains AppOps, LockPatternUtils, UserManager-backed state callback, lockout reset dispatcher, listeners, real fingerprint Looper, registry and Samsung extension. | Earlier `FingerprintService.txt:85/101`; context call `0000`, extension constructor `0096`. |
| First `BiometricContext` creation | Requires WindowManager and `statusbar` via `getServiceOrThrow`; creates AuthSessionCoordinator and a context provider. Existing singleton reuse skips this creation. | New `BiometricContext` raw line 3: `0003`, `000c`, `0016`, `002a`, `002e`. |
| Context-provider constructor | Calls real `IStatusBarService.setBiometicContextListener` and `registerSessionListener(3,…)`, then registers a dock receiver. Remote/security registration errors are logged/caught; constructor return is not registration success. | New provider raw line 3: `003f`, `004a`, `0060`; exact constructor descriptor is inventory-pinned. |
| `SemFingerprintServiceExtImpl` | Retains context/handler/registry; initializes display-monitor singleton and enrollment-session monitor. `FP_FEATURE_LOCAL_HBM` guards a real local-HBM controller with UDFPS/sysfs dependencies. | Earlier extension raw line 2: `002e`, `0035`, `0048..0067`. |
| `BiometricService` constructor | Reads real DPM, UserManager, FingerprintManager, FaceManager and trust endpoints; creates secure-settings observer and registration callbacks; obtains camera/privacy, KeyStoreAuthorization, GateKeeper and virtual-device local references; creates Samsung SysUi manager and user-switch observer. | New service raw line 4: managers `001c..005c`, callbacks `015d/0167`, observer update `016a`, crypto `01bd/01c3`, local `01ef`, SysUi `020a`, observer `0222`. |
| `BiometricService.onStart` | Publishes `biometric` before DeviceConfig listener, posted callback and conditional display registrations finish. | Same raw line 6: `0071`, `0093`, `00a2`, `00b9/00c2`. |
| `FingerprintService.onStart` | Publishes `fingerprint`; no provider readiness is implied. | Earlier body `0005`. |
| `AuthService.onStart` | Gets actual biometric/fingerprint Binder endpoints, declared IFingerprint instances and configuration; posts fingerprint registration, later publishes `auth`. Its injected `isHidlDisabled` currently returns literal false. | New AuthService raw line 5: `0004`, `0053..0063`, `00c8`, `01b5`; Injector exact body pinned. |
| Posted AuthService lambda | Creates genuine `FingerprintSensorConfigurations`; chooses AIDL or HIDL configuration and calls fingerprint `registerAuthenticators`. Missing service and RemoteException paths only log. | New lambda1 raw line 3: `000e`, `0013/0017`, `001e`, `0023..0035`. |
| FP registration supplier | Selects source instance/properties and constructs the actual 13-input provider. On a property-cache miss, `getSensorPropForInstance` obtains IFingerprint and invokes HAL `getSensorProps` before provider construction. | Supplier `0019` / `009c`; new framework configuration raw line 4 `0025/002b`. |
| Registry commit | Executes provider supplier first, then resolves biometric service. Registers sensor/authenticator tuples, stores unmodifiable provider/property lists, then broadcasts registration. Null biometric uses a real failure path. | New registry raw line 4: `0000`, `000f`, `0047`, `0054/005a`, `005c`, `0064/0067`. |

The display-monitor constructor itself initializes local lists/state/handler.
It does **not** register display callbacks. Its InstanceHolder initializes the
singleton inline using BiometricHandlerProvider; there is no evidence of a
missing external singleton bootstrap. Actual handler-thread construction belongs
to the coordinated credential/startup trace. The provider callback-dispatcher
type declares no constructor; its actual factory inlines initialization using
`Object.<init>`. Inventing a constructor/provider would change the source graph.

**Observed earliest state/native boundaries:** provider construction creates
Samsung extension/callback owners (`007e/0084`) and registers statistics and
dangling receivers (`0096/009b`) before even checking for null sensor properties
(`00a0`). AIDL sensor creation converts genuine properties (`0221`), creates the
sensor and scheduler (`022a/0260`), registers SensorList ownership (`02a2`) and
posts handler work (`02b1`). Sensor retains its real properties, token, handler,
context, authenticator-ID map and Samsung lockout implementation; current session
starts null, not as a fabricated active session.

That posted AIDL work is already native acquisition: constructor constant
`v15=3` at `00a8` reaches Lambda9 constructor `02a9`; its switch at `0008`, key 3,
offset 188 lands at `00c4`, calling `getHalInstance` at `00c6`. The existing getter
links death and schedules alive-user cleanup/authenticator-ID loading
(`00d6/00db/00e5`). The HIDL alternative posts Lambda31 class 0, whose `0033`
acquires the adapter's actual `IBiometricsFingerprint` and stores it. HIDL classes
do not prove the captured AIDL/default device runs that branch.

SensorList registers an actual ActivityManager user-switch observer (`000a`).
For the uninitialized-user sentinel it invokes `onUserSwitching(0)` inline
(`0011/0012`). The corresponding provider callback schedules cleanup only if its
real AIDL/HIDL daemon is already nonnull (`0023/0042` guards). Independently,
provider construction iterates each constructed sensor and calls
`FingerprintUtils.getBiometricsForUser(context, 0)` (`02f3..02fa`, literal zero at
`02f9`). The all-registered callback later broadcasts enrollment state for every
alive user, using actual `provider.hasEnrollments(sensorId,userId)`.

**Required design gate — inference:** final sensor/user/storage identity and
exclusive writer ownership must precede property acquisition/provider creation,
not merely `authenticate`. The complementary
[state construction trace](construction-state.md) shows why lazy user-state
creation can migrate metadata or delete/rewrite malformed metadata. Substituting
the selected user for the original literal-zero read is not an audited fix.
Construction failure must retain/drain already registered receivers, observer
callbacks, posts and native cleanup work; an actual teardown protocol remains
missing. The original boot-phase runnable also owns phase-550/600/1000 work,
including settings/display callbacks, feature-dependent TSP/AOD/optical support
and pending metadata operations. Replaying only constructors is insufficient.

**Observed canonical gaps; scoped adaptation:** 125 selected canonical call
references were compared through exact selected framework/services ancestry.
Five host-resolvable descriptors are absent from the selected guest indexes:

| Exact Samsung edge | Required treatment |
| --- | --- |
| `DisplayManagerInternal.registerDisplayStateListener(DisplayStateListener)V` | Called by BiometricService.onStart `00b9` only when the real local service is nonnull (`00b7`). Close the actual required Samsung display behavior through a typed guest adaptation. |
| `registerDisplayBrightnessListener(DisplayBrightnessListener)F` | Same owner `00c2`; additionally guarded by `FP_FEATURE_SUPPORT_DRM_PROPERTY_FOR_BRIGHTNESS` (`00bc/00be`). Genuine sensor/feature evidence decides whether needed. |
| `FingerprintSensorPropertiesInternal.isOpticalType()Z` | Actual body is `sensorType == 3`. Map genuine Samsung property values into ColorOS consumers; no guessed type or default false. |
| `isUltrasonicType()Z` | Actual body is `sensorType == 2`; same requirement. |
| `android.net.Ipv6Parcel$$ExternalSyntheticBUOutline0.m$1(String)V` | Registry's null-biometric failure path. Preserve the real failure semantics with a reviewed private relocation/retarget, not an unrelated OPPO component. |

One further `RemoteException.getMessage` reference is unresolved in both selected
indexes because external Java ancestry is outside the comparison; this is not an
extra ABI-gap finding. Declaration presence proves no implementation semantics.
Other guest jars, resource/API differences and the installed patched guest are
not excluded by this bounded comparison.

**Inference under current steering:** adapt ColorOS to Samsung authority and
properties. Optional OPPO display, progress, gesture or background features can
be unavailable with their ingress/observers safely removed; they need not be
imported for naming parity. Required native illumination/touch/session behavior,
strong-auth, lockout and caller/user policy cannot be suppressed as optional.
Existing `Fingerprint` parcel mismatch also remains: Samsung duplicated-image
count is not ColorOS finger flags. Unsupported enrollment-total progress must not
become fabricated enrollment success. See [frontend contracts](coloros-frontend.md).

The genuine native session boundary remains
`IFingerprint.createSession(sensorId,userId,ISessionCallback) -> ISession`, with
actual session close and `ICancellationSignal.cancel` followed by owned terminal
callbacks. Live sensor ID/type/strength, service version/hash, authenticator IDs,
template reconciliation, resource/sysfs/TSP ownership, typed Samsung UI dispatch
and complete failure cleanup remain unproved. The captured manifest is AIDL v3;
it supplies no live identity or enrollment state.

The next offline acceptance is a single concrete assembly/owner graph that
enforces these pre-init gates and typed adaptations without a competing guest
authority. Later separately authorized device proof must still establish real
existing-enrollment authentication and a genuine nonnull native Keystore
challenge, rejection before fresh auth and completion of the **same** protected
operation with the authentic HAT. Constructor completion, registration callbacks
and success UI cannot substitute for that proof. No functioning biometric or key
acceptance is claimed here.
