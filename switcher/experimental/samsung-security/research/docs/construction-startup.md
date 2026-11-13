# Original ColorOS security startup replacement boundary

**Observed source result:** the previously unpinned original guest startup sites are now identified. **Remaining gap:** no replacement, Samsung construction closure or policy-readiness gate is implemented. The installed OneOS patched image is not identified by this work.

Input: original ColorOS `system/framework/services.jar`, SHA256 `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3`; canonical framework input `d5c6b7fd…`. The shared static reader preserves each physical DEX/header and normalized method body. These original services use DEX039; the sites below have logical header offset0. PCs are method-relative 16-bit code-unit offsets, **not** archive byte offsets. [construction-startup.json](../inventory/construction-startup.json) contains exact signatures, code hashes, reference PCs and pinned raw receipts. No OEM/JNI/service code ran.

## Exact original creation sites

All four sites are in `classes.dex`, `SystemServer.startOtherServices(TimingsTraceAndSlog)`:

| Role | Actual class literal | Actual `SystemServiceManager.startService(Class)` | Immediate contract |
| --- | --- | --- | --- |
| LockSettings | `0x06b0`: `LockSettingsService$Lifecycle` | `0x06b2` | `lock_settings` lookup at `0x06b8`, guest `ILockSettings.Stub.asInterface` at `0x06bc`. |
| Fingerprint | `0x112d`: `FingerprintService` | `0x112f` | Returned object is cast to the original guest implementation at `0x1133`. |
| Biometric | `0x113f`: `BiometricService` | `0x1141` | Original onStart calls its Injector's publication method at `0x14`. |
| Auth | `0x114e`: `AuthService` | `0x1150` | Original onStart gets `biometric`, initiates authenticator registration and calls its Injector's publication method. |

The fingerprint path is conditional: the package manager tests `android.hardware.fingerprint` at `0x10f4–0x10f9`; `0x1124` skips its start when false. Face/iris have their own feature branches. Neither a feature declaration nor a service class proves an actual Samsung provider is ready.

**Executed cast constraint:** fingerprint's result is moved to v0 at `0x1132`, checked against the original ColorOS FingerprintService at `0x1133`, and v0 is overwritten by the next service's string at `0x1138`. The intervening straight-line span does not retain/use v0. An authored lifecycle returning another class must explicitly adapt this cast with preservation proof. Subclassing the old guest implementation merely to pass it would execute the unwanted guest constructor.

The LockSettings/Biometric/Auth start results are not retained through corresponding implementation casts at these sites. LockSettings is immediately consumed through its **canonical guest Binder contract**, rather than through the returned lifecycle object.

## Creation really invokes lifecycle work

The actual guest manager resolves a public Context constructor and calls `startService(SystemService)`. That method records the class/service before calling real `SystemService.onStart` at `0x37`. Therefore replacing only a Binder registration after the original start is too late to prevent old constructor/onStart work.

Original ColorOS LockSettings lifecycle is in `classes2.dex`: onStart installs AndroidKeyStoreProvider (`0x0`), constructs `LockSettingsService(Context)` (`0x9`) and publishes `lock_settings` (`0x13`). Its onBootPhase forwards through the actual nest bridge (`0x5`) to the original service. A replacement must own the complete lifecycle and local publication; it must not leave a second guest service/observer/migration owner behind.

Original fingerprint onStart directly publishes `fingerprint` (`0x5`). Auth/Biometric Injector methods contain canonical names `auth` and `biometric` and delegate to their actual `access$000` publication helpers. Those tiny final compiler-helper bodies were not separately followed in this bounded scope; the selected SystemService publication bodies and the delegate edges are retained as evidence. No missing helper is treated as successful publication.

## Real readiness, phase and immediate-consumer order

Observed direct phase calls in the supplied services archive:

| Phase | Actual caller and PC |
| --- | --- |
| 100 | `SystemServer.startBootstrapServices` `0x213` |
| 200 | `SystemServer.startOtherServices` `0x2df` |
| 480 | Same method `0x1610` |
| 500 | Same method `0x167f` |
| 520 | Same method `0x1842` |
| 550 | `SystemServer.lambda$startOtherServices$6` `0x18` |
| 600 | Same callback `0x18e` |
| 1000 | `ActivityManagerService.finishBooting` `0x7e` |

Important actual edges:

1. Before phase480, `startOtherServices` checks the retained LockSettings interface (`0x15f7`) and calls real `ILockSettings.systemReady()` (`0x15f9`). This is active initialization/migration/policy work, not a readiness boolean.
2. After phase520, SystemServer passes `SystemServer$$ExternalSyntheticLambda8` to `ActivityManagerService.systemReady` (`0x195f`). The inspected Runnable/compiler bridge reaches the real boot lambda. AMS invokes the Runnable at `0x1a1` on the normal path, or `0x2b` when already ready; the callback contains phases550/600.
3. After that call returns, SystemServer looks up canonical `LockSettingsInternal` (`0x1980`), casts it (`0x1985`) and, if non-null, calls `onThirdPartyAppsStarted()` (`0x1989`). It then calls `startSystemUi` (`0x1996`).
4. The original local-service callback invokes its LockSettings nest bridge. The separately selected outer `onThirdPartyAppsStarted` method includes user-state removal/creation and synthetic-password/bound-key/Weaver migrations. The tiny nest bridge was not separately followed here. Replacing `lock_settings` alone while leaving the original local owner and its maintenance path is not an established single-authority design.
5. `finishBooting` checks `mBootAnimationComplete` (`0x1a`); when incomplete it records `mCallFinishBooting` and returns. Do not force phase1000 or remove this finish gate to make an imported provider appear ready.

The guest manager supports serial/parallel phase callbacks, submits parallel work and waits on actual `Future.get` (`0x13a`); an exception is wrapped/thrown. Preserve that dispatch/dependency contract. It does not acknowledge native work or child operations merely posted by a callback. Source null checks/catch paths also mean continued boot is not proof that the intended security service succeeded.

Auth illustrates the distinction: onStart calls `registerAuthenticators` (`0x73`); that routine obtains the canonical fingerprint Binder (`0x1c`) and calls `registerFingerprintSensors` (`0x20`). The latter posts to the fingerprint Handler (`0x20`); its selected actual registration lambda invokes `IFingerprintService.registerAuthenticators(FingerprintSensorConfigurations)` (`0x2b`). The posted Runnable's final compiler bridge was not separately followed here. A posted task or void registration return is not provider/sensor/policy readiness.

## Canonical contracts and OPPO removal boundary

**Proposed source-supported replacement:** replace these original service producers before their constructors/onStart run. Authored lifecycles/facades can preserve guest `SystemService`, Binder and LocalServices identities while routing to the genuine, fully owned Samsung service family. Required canonical roles are `lock_settings`/`ILockSettings`, `LockSettingsInternal`, `fingerprint`/`IFingerprintService`, `biometric`/`IBiometricService`, and `auth`/`IAuthService`. Preserve their actual startup, user, finish, StrongAuth, result and cancellation contracts; no empty success/readiness implementation is supplied.

This cuts the replaced producer's original vendor-specific subgraph along that startup path. Observed examples are original LockSettings' `ILockSettingsServiceExt.hookOnSystemReady` (`systemReady@0x8b`) and multi-app hook (`onBootPhase@0xc`), and original fingerprint's extension `onBootCompleted` (`onBootPhase@0xc`, phase1000). These old extension notifications need not be executed merely to retain a ColorOS implementation after its core duty has moved to Samsung. The genuine replacement must still perform the required Samsung/core policy and completion work.

This is not proof that multi-app/profile policy can be discarded. Required profile/StrongAuth/additional-factor behavior needs a real mapping; an unsupported optional profile/component must be made consistently unavailable before requests can authorize authentication, not treated as an allowed user or successful gate.

**Not proved safely removable:** independent `ISystemServerExt` bootstrap/core/other/systemReady hooks, including `startOtherServices@0x15b1` and `systemReady@0x1881`. Their implementations were not read here. Do not blanket-delete the whole extension, classify a generic platform AgentAuth/additional-factor service as OPPO-only by name, or remove a required denial/finish gate. Independently reached optional UI/background/API components require an explicit supported/unavailable/removal mapping and consumer changes; this report certifies no such global cleanup.

## Remaining construction bindings and status

The original guest callsite gap is closed for these immutable original bytes. Remaining work includes the exact installed/patched OneOS target; coherent facade publication and canonical parcel/protocol handling; original Samsung constructor/Context/resource/local/storage/native owners; exclusive state/writer handoff; and a real policy/provider readiness barrier **before** UI authentication is admitted. The original phase/local-consumer ordering must be retained or deliberately remapped with actual completion semantics.

No source patch, payload, native startup, device test or readiness placeholder was produced. Full Stage1 construction/authority closure remains open. Old ColorGlass work stays paused.

Recheck existing evidence without OEM execution: `python tools/audit_guest_startup.py`. Fresh bounded collection: `python tools/audit_guest_startup.py --collect --extend`. Raw methods stay under ignored `firmware/construction-startup/`, except the explicitly reused credentials receipt; generated artifacts stay under ignored `out/construction-startup/` and the shared reader's `out/tooling/` cache.
