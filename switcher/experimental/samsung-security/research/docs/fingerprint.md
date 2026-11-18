# Fingerprint authority and transplantation boundary

**Observed source fact:** the supplied Samsung capture declares an AIDL v3 `android.hardware.biometrics.fingerprint.IFingerprint/default` HAL and contains a substantial Samsung Java/provider/native stack for it. It is not necessary to invent a hardware interface from scratch. **Missing evidence:** no working transplantation, live sensor identity, authentication, token acceptance or safe cross-system ownership has been demonstrated. A declaration or a successful callback is insufficient acceptance.

All evidence below is offline. No OEM/JNI/service code ran, no hardware request was sent, no enrollment/credential/template data was read, and no phone or source image changed. The mounted capture excludes `/data` and `/efs`, so it cannot establish existing enrollment IDs, authenticator IDs, credential SIDs or protector state. Parent ColorGlass work stays paused.

## Exact evidence and reproducibility

The source/method/member proofs are in [inventory/fingerprint.json](../inventory/fingerprint.json); the authored reader driver is [tools/audit_fingerprint.py](../tools/audit_fingerprint.py). It consumes exact parent inputs:

| Input | SHA256 |
| --- | --- |
| Samsung `firmware/samsung/runtime-20261104/services.jar` | `def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6` |
| Samsung `firmware/samsung/framework.jar` | `8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe` |
| ColorOS original `system/framework/services.jar` | `66d0d51daf3a0796d8c14e76db134101e9523d91233dfce79df71e775931edf3` |
| ColorOS original `system/framework/framework.jar` | `d5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2` |
| ColorOS original `system/framework/oplus-framework.jar` | `e53b28b80c5481364a7046a049d4bd4efa7f768262887961c1fc02d18c13f8fe` |

Samsung services has one physical DEX041 container with logical headers at `0` and `10057984`. The untouched full-container parser and shared child reader preserve those offsets; no header magic or offsets were patched/rebased. Raw OEM bodies are only under ignored `firmware/fingerprint/`. Inventory records exact owner/signature, normalized body hash, raw method line and reader receipt. The first batch contains 29 types/356 bodies; the supplementary batch and ColorOS extension contain 78 bodies. These overlap and are evidence scopes, not completeness or compatibility scores. Seventeen selected source assertions pass, as do nine selected request/callback sender-shape comparisons.

Twelve selected regular members were read from the existing mounted-OS tar using its immutable hash-pinned manifest. Each member's exact SHA256/size is rechecked; no filesystem-wide extraction or link following occurs. This stream reuses the prior strict whole-tar receipt rather than rereading its 20GB hash. The archive is a mounted view, not certified stock partitions.

Reproduce with the existing JDK/toolchain, from this child project:

```powershell
python tools/audit_fingerprint.py
python tools/audit_fingerprint.py --member vendor/lib64/libsfp_sensor.so --member vendor/lib64/libsfp_teegw.so --member vendor/lib64/libqfp_sensortest.so
python tools/audit_fingerprint.py --bodies
python tools/audit_fingerprint.py --supplement
python tools/audit_fingerprint.py --report
```

The supplement command also audits actual ColorOS `FingerprintExtImpl` and its concrete registry/creator bodies. Rerunning the report validates the immutable raw proofs. No biometric model or device test is claimed.

## Service startup is an authority acquisition

**Observed source facts**, with DEX instruction PCs:

* `FingerprintService.<init>(Context)` obtains `BiometricContext.getInstance(Context)` and delegates to its real injected constructor. That constructor creates the Binder wrapper, AppOps reference, `LockoutResetDispatcher`, `LockPatternUtils`, UserManager-backed `BiometricStateCallback`, authentication listeners and registry. At `0096` it constructs `SemFingerprintServiceExtImpl` with the actual fingerprint handler Looper and registry.
* `FingerprintService.onStart()` publishes the global Binder name `fingerprint` at `0005`. Publication alone does not establish providers/readiness. `registerAuthenticators(FingerprintSensorConfigurations)` posts provider registration to the fingerprint handler. Its actual synthetic supplier selects sensor-instance properties, then invokes the 13-input Samsung `FingerprintProvider` constructor at `009c`. Registry `registerService` registers the resulting sensor/strength/authenticator with `IBiometricService` at `001b`.
* The extension constructor references the real display-state monitor and enroll-session monitor; feature-dependent branches construct local-HBM/UDFPS support. `onBootPhase` posts actual Samsung extension work. The inspected boot lambda has phase-550 display callbacks, secure-setting observers and feature-dependent native/display/touch support. These feature branches must be evaluated from genuine sensor/platform state; neither a generic Samsung class name nor all possible branches proves the actual device is UDFPS.
* **Critical boundary:** `FingerprintProvider.getHalInstance()` calls its real HAL accessor, links death and immediately schedules all-alive-user cleanup/authenticator-ID loading (`00b2..00e5`), including current-user cleanup with the provider callback. It posts HAL-start work before returning. It is not a read-only readiness probe.
* Actual `InternalCleanupClient` obtains its enrolled list, starts enumeration, and its unknown-template cleanup helper can create a removal client and start it. Separately, `BiometricUserState.<init>` can rename legacy metadata before reading it. Even a Java cache/state acquisition may therefore have ownership or migration effects.

**Inference:** copying `FingerprintService` alone cannot produce a self-contained secure service. A real transplant must close its registry, scheduler, user/profile, strong-auth, framework/resource, Samsung extension, native/session and metadata dependencies, and suppress the competing guest authority through a reviewed owner design. This does not prove that the entire Samsung framework is required; it identifies concrete edges that cannot be replaced by dummy objects.

## Actual HAL/native declarations

**Observed captured-file facts:**

* `vendor/etc/vintf/manifest/vendor.samsung.hardware.biometrics.fingerprint-service.xml` declares AIDL version `3`, `IFingerprint/default`.
* Its init rc declares `vendor.fingerprint-default`, executable `/vendor/bin/hw/vendor.samsung.hardware.biometrics.fingerprint-service`, class `late_start`, user `system`, groups `system input`.
* `init.fingerprint.rc` names several alternative device nodes and data directories, including `/dev/esfp0`, `/dev/goodix_fp`, `/dev/qbt2000_*`, `/data/vendor/misc/qti_fp/...`, `/data/vendor/biometrics` and `/efs/biometrics`. These are declarations for possible platform paths, not proof of which sensor is fitted or which private directory is active.
* The daemon's ELF imports include `dlopen`, `dlsym` and Binder extension support; its strings name `MakeFingerprint`, `MakeSehFingerprint` and `/apex/com.samsung.android.biometrics.fingerprint/lib64/libsfp_sensor.so`. The captured `vendor/lib64/libsfp_sensor.so` depends on the standard fingerprint-v3 library, Samsung `ISehFingerprint`-v1 library, `libsfp_teegw.so` and `libqfp_sensortest.so`, in addition to platform libraries. TEE gateway linkage includes `libminkdescriptor.so` and DMA-buffer support; strings refer to a fingerprint trustlet path and secure-world commands.

**Inference / missing evidence:** the dynamic loader and secure-world backend are real additional dependencies, not resolved by the daemon's small direct `DT_NEEDED` list. Static ELF linkage/strings do not establish a native call graph or successful runtime loading. The capture's fingerprint APEX records include its manifest but no file at the literal APEX sensor-library/trustlet paths; a vendor library exists. Fallback/dynamic mount resolution and complete TEE/native closure remain unproven. No secret/trustlet execution was attempted. The declared AIDL version is known; live daemon version/hash, sensor ID/type/strength and actual session are not.

## Identity, signed token and policy chain

**Observed source facts:** `FingerprintStartUserClient.startHalOperation()` uses the real client `mSensorId` and `mTargetUserId` when calling `IFingerprint.createSession(sensorId,userId,SemFpAidlResponseHandler)` at `0015`. Sensor properties and session version come from the actual HAL/configuration path. HIDL adapter classes are also present, but their presence does not show that the captured AIDL/default declaration uses HIDL at runtime.

`FingerprintUtils.getInstance$1(sensorId)` names `settings_fingerprint_<sensorId>.xml`; per-user state uses `Environment.getUserSystemDirectory(userId)`. The Samsung XML reads/writes finger ID, name, group ID, device ID and duplicated-image count. Provider authenticator-ID lookup is a per-user map and can return default zero before loading. A cached zero is not an authenticated hardware identity. `SemUtils.getUserOrWorkProfileId` contains actual work-profile, Knox app-separation/dual-app and credential-owner policy. Copying user number `0` does not reproduce this authority or the credential SID.

The actual success carrier serializes the HAL-supplied `HardwareAuthToken` through `HardwareAuthTokenUtils.toByteArray` and delivers it to `AuthenticationClient.onAuthenticated`. That method distinguishes legacy and BiometricPrompt handling:

* Non-BiometricPrompt, nontrivial-token handling calls `KeyStoreAuthorization.addAuthToken([B)` at `01f3`.
* A nonzero deposit result logs an error then still reaches success callbacks (`0200 -> 0212 -> 0224/0235`). Thus even a real OEM legacy success callback does not prove Keystore acceptance.
* BiometricPrompt handling skips that local deposit and forwards token bytes through `ClientMonitorCallbackConverter`/sensor receiver. Its later `AuthSession`/dismissal and Keystore path is a separate owner chain; see the storage/key and trust reports.

`semAuthenticate` retains permission/current-user/profile/AppOps/foreground and Samsung privilege policy. Its keyguard branch consults actual `LockPatternUtils.getStrongAuthForUser` with encrypted/lockdown checks. Lockout includes the real `AuthSessionCoordinator`/multi-biometric state and Samsung per-user/integrated attempt tracking, reset receiver and alarm handling. Neither transplant nor presentation may create independent “unlocked” or cleared-lockout state.

## Selected ColorOS Binder overlap and a semantic mismatch

**Observed source fact:** the supplied Samsung and ColorOS sender bodies agree for these selected interfaces:

| Call | Transaction | Binder mode |
| --- | ---: | --- |
| `authenticate` | 5 | synchronous |
| `detectFingerprint` | 6 | synchronous |
| `cancelAuthentication` | 9 | synchronous |
| `cancelFingerprintDetect` | 10 | synchronous |
| receiver acquired / success / detected / failed / error | 2 / 3 / 4 / 5 / 6 | oneway |

Top-level interface tokens, primitive/typed-object ordering and reply shapes match for these nine pairs. `FingerprintAuthenticateOptions` also has the selected field order and writer flags `4` (ignore enrollment), `128` (mandatory biometrics), `32` (optional attribution) and `64` (optional vendor reason) on both sides. This is a bounded sender/parcel finding; endpoint policy, complete Binder surfaces and nested vendor-reason semantics are not thereby certified.

**Concrete mismatch:** nested `Fingerprint` writes the same name/id/device/group prefix and one final integer on both OSes, but Samsung's last integer is `mDuplicatedImgCount`; actual ColorOS `FingerprintExtImpl` reads/writes `mFingerFlags`. The actual `BaseCommonCoreRegistryFoundation.registerDeviceServiceExts` and its synthetic creator register/construct that concrete extension; this is supplied-source registration evidence, not proof of current guest initialization. Equal parcel width is not semantic interchangeability. An adapter must define the authentic meaning required by original ColorOS flag consumers rather than relabel a Samsung count. [ColorOS frontend contracts](coloros-frontend.md) also retain real callback/session/user/strong-auth/dismissal requirements.

## Cancellation and candidate boundaries

**Observed source fact:** Samsung authentication stop invokes the retained `ICancellationSignal.cancel()` at `0045` and normally returns at `0048` without finishing that client itself. Scheduler cancellation matches Binder token/request ID and marks or cancels the actual operation. Session stop calls `ISession.close`; `onSessionClosed` posts the real scheduler continuation, which calls the retained `StopUserClient.onUserStopped` and clears it. A cancel request, queue absence or close return alone does not prove that HAL callbacks, queued work or session ownership drained.

The source supports comparing these designs; none is implemented here:

1. **Real Samsung fingerprint-service cluster transplanted into the guest — inference.** Preserve the original provider, Samsung policy, real metadata and native authority under one service/scheduler. Selected Binder overlap helps presentation integration. Concrete blockers are class/framework/resource ownership, bootstrap and BiometricService registration, template migration/cleanup ownership, genuine user/strong-auth state and Keystore namespace/operation binding.
2. **Retain a Samsung service authority and adapt ColorOS presentation — inference.** Keeps existing provider/session/metadata policy together. Requires a demonstrated retained process/service lifetime during OneOS switching, typed callbacks and the parcel semantic correction; a boolean broker or forged keyguard caller is insufficient.
3. **Reuse the real Samsung standard HAL below a different guest service — inference.** The manifest provides a real AIDL route, but this also transfers responsibility for Samsung extensions, template reconciliation, policy and cancellation. It is not evidence that a stock guest provider can safely borrow the live hardware with its staged metadata.

The smallest next offline proof is a source-closed candidate service/loader/bootstrap graph with one chosen template/user/scheduler owner and exact cross-framework parcel adaptation. Future separately approved device feasibility must then demonstrate one existing-enrollment operation, actual sensor/user/authenticator/credential identities, a **genuine nonnull native Keystore operation challenge** for an authentication-bound test key, failure before fresh authentication and completion of that same operation after its genuine signed token. A random fallback operation ID or callback is insufficient. Cancellation and host credential/enrollment/CE behavior after return must also be checked. Credential/enrollment changes and synchronization remain later explicit requirements; this first operation would not complete them.
